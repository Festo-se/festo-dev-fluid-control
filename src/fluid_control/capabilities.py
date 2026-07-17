# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""
Capability mixins for pressure-over-liquid fluid-handling devices.

Each mixin contributes a single public operation (or a cohesive group of
operations) and delegates into the engine primitives provided by
:class:`~fluid_control.fluid_control.PressureOverLiquidControl` (e.g.
``_handle_liquid``, ``_require_arm``, ``_disable_lateral_axes``). Mixins are pure
``object`` subclasses at runtime and are never instantiated directly; concrete
devices compose them onto the engine.

At type-check time the mixins are treated as subclasses of
``PressureOverLiquidControl`` so that references to engine members resolve,
while at runtime they remain lightweight traits with no base of their own.
"""

import logging
from typing import TYPE_CHECKING

from fluid_control.fluid_control import ChannelCommand, OperationResult

logger = logging.getLogger(__name__)

# Tip-ejection actuation parameters (see per-line TODOs for future parameterisation).
_EJECT_ACTUATION_CYCLES = 3
_EJECT_MAX_PRESSURE_MBAR = 449
_EJECT_MIN_PRESSURE_MBAR = -449

# Tip-pickup stall-detection parameters.
_PICKUP_STALL_DELTA_MM = 0.5
_PICKUP_STALL_CONSECUTIVE = 2

if TYPE_CHECKING:
    from fluid_control.fluid_control import PressureOverLiquidControl

    _EngineBase = PressureOverLiquidControl
else:
    _EngineBase = object


class DispenseMixin(_EngineBase):
    """Adds pressure-over-liquid dispensing to a device."""

    def dispense(self, dispense_dict: dict[int, ChannelCommand]) -> None:
        """
        Dispense liquid across one or more valve controller channels.

        Args:
            dispense_dict (dict): Mapping of channel IDs to channel-operation parameters.

        """
        logger.info(f"DISPENSE START: {dispense_dict}")
        # TODO: Enable ability to set timing PER CLASS
        self._handle_liquid(dispense_dict, process="dispense")


class AspirateMixin(_EngineBase):
    """Adds pressure-over-liquid aspiration to a device."""

    def aspirate(self, aspirate_dict: dict[int, ChannelCommand]) -> None:
        """
        Aspirate liquid across one or more valve controller channels.

        Args:
            aspirate_dict (dict): Mapping of channel IDs to channel-operation parameters.

        """
        logger.info(f"ASPIRATE START: {aspirate_dict}")
        # TODO: Enable ability to set timing PER CLASS
        self._handle_liquid(aspirate_dict, process="aspirate")


class MixMixin(_EngineBase):
    """Adds mixing (repeated aspirate/dispense) to a device."""

    def mix(self, mix_dict: dict[int, ChannelCommand], cycles: int) -> None:
        """
        Aspirate and dispense repeatedly to mix liquid in the channels.

        Args:
            mix_dict (dict): Mapping of channel IDs to channel-operation parameters.
            cycles (int): Number of aspirate/dispense cycles to execute.

        """
        logger.info(f"MIX START: {mix_dict}")

        for _ in range(cycles):
            self._handle_liquid(mix_dict, "aspirate")
            # TODO: Raise fluid_control arms so no bubbles
            self._handle_liquid(
                mix_dict, "dispense"
            )  # TODO: This needs to be an instance attribute dictionary that ensures all liquid is clear.


class TipHandlingMixin(_EngineBase):
    """Adds tip pickup and ejection to a device that has a motion axis."""

    def eject_tips(self) -> OperationResult:
        """Eject tips from the fluid control module."""
        # TODO: How to consider static, mechanical, deck-based, fixed-point ejection mode
        # Make optional?
        # class Ejector
        # if ejector is not None:
        #   ....
        # TODO: Minimum: Add warning that this class assumes a co-mounted, dynamic tip ejection mechanism. Others are not yet supported.
        logger.info("EJECT TIPS START")
        self._require_arm()
        self.fluid_control_status.set_busy()
        self._disable_lateral_axes()
        try:
            for cycle in range(_EJECT_ACTUATION_CYCLES):
                logger.debug(
                    f"Eject tips: actuation cycle {cycle + 1}/{_EJECT_ACTUATION_CYCLES}"
                )  # TODO: Parameterize the total number of eject cycles for testing
                self._wait_output_pressure(
                    _EJECT_MAX_PRESSURE_MBAR
                )  # TODO: Change to Pressure Control Library max pressure. Will need slight modificiation of PGVA library
                self.pressure_control.trigger_actuation_valve(10)
                self.pressure_control.trigger_actuation_valve(1000)
                self._wait_output_pressure(
                    _EJECT_MIN_PRESSURE_MBAR
                )  # TODO: Change to Pressure Control Library min pressure. Will need slight modificiation of PGVA library
                self.pressure_control.trigger_actuation_valve(10)
                self.pressure_control.trigger_actuation_valve(2000)
            self.pressure_control.set_output_pressure(0)
            self.fluid_control_status.set_clear()
            self._enable_lateral_axes()
            logger.info("EJECT TIPS COMPLETE")
            return OperationResult(self.fluid_control_status.get_status(), "Tips ejected successfully")
        except Exception as e:
            logger.error(f"EJECT TIPS FAILED: {e}")
            self.fluid_control_status.set_error()
            self._enable_lateral_axes()
            return OperationResult(self.fluid_control_status.get_status(), str(e))

    def _pickup_action(self, duration: float) -> None:
        """Jog the mount arm downward until tip engagement stalls its motion."""
        arm = self._require_arm()
        delta = _PICKUP_STALL_DELTA_MM  # mm — FestoAxis.current_position() returns mm
        arm.acknowledge_faults()  # TODO: We need a way to NOT dig this deep into internals of the edcon library
        # self.mount_arm.disable_powerstage()
        current_position = arm.current_position()
        logger.debug(f"_pickup_action: start position={current_position}, duration={duration}, delta={delta}")
        repeat = True
        count = 0
        self._disable_lateral_axes()
        while repeat:
            arm.acknowledge_faults()
            arm.enable_powerstage()
            arm.jog_task(
                True, False, duration=duration
            )  # TODO: Passing all the way to jog_task defeats the purpose of the axis class and make the parameters passed / API confusing. Think of a way to fix this.
            # self.mount_arm.position_task(position=5000, velocity=duration, absolute=False, nonblocking=False)
            # self.mount_arm.jog_task(True, False, duration=0.5)
            new_position = arm.current_position()
            movement = abs(new_position - current_position)
            logger.debug(f"_pickup_action: new_position={new_position}, movement={movement}, stall_count={count}")
            if movement <= delta:
                count += 1
                current_position = new_position
            else:
                current_position = new_position
            if count >= _PICKUP_STALL_CONSECUTIVE:  # TODO: Parameterize this for testing
                logger.debug("_pickup_action: stall detected — tip engagement complete")
                repeat = False
        self._enable_lateral_axes()
        arm.acknowledge_faults()

    def pickup_tips(self, duration: float) -> OperationResult:
        """
        Pick up tips with the fluid_control.

        Args:
            duration (float): Duration in seconds of each downward jog toward the tips.

        """
        logger.info(f"PICKUP TIPS START: duration={duration}")
        self._require_arm()
        self.fluid_control_status.set_busy()
        try:
            self._pickup_action(duration=duration)
            self.fluid_control_status.set_clear()
            logger.info("PICKUP TIPS COMPLETE")
            return OperationResult(self.fluid_control_status.get_status(), "Tips picked up successfully")
        except Exception as e:
            logger.error(f"PICKUP TIPS FAILED: {e}")
            self.fluid_control_status.set_error()
            return OperationResult(self.fluid_control_status.get_status(), str(e))
