# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""Pipettor module exposing the Pipettor class for multi-channel tip-based liquid handling."""

import logging

from fluid_control.dispenser import Dispenser
from fluid_control.aspirator import Aspirator
from applied_motion import Axis
# from configurator import dynamic_importer

logger = logging.getLogger(__name__)

logging.getLogger("pymodbus").setLevel(logging.WARNING)


class Pipettor(Aspirator, Dispenser):
    """
    Festo Eight-channel pressure-over-liquid pipettor.

    All fluid-handling logic is implemented in ``PressureOverLiquidControl``;
    this class binds it to the ``"pipettor"`` component key in the config.
    """

    def __init__(
        self,
        config: dict,
        component_id: str = "pipettor_1",
        mount_arm: Axis | None = None,
        disable_axes: tuple[Axis, ...] = (),
        pressure_control=None,
        valve_control=None,
    ):
        """
        Initialise the Pipettor from an instrument configuration dict.

        Args:
            config (dict): Full instrument configuration; the component keyed
                by ``component_id`` is extracted and used.
            component_id (str): Key of this pipettor instance inside
                ``config["components"]``. Defaults to ``"pipettor_1"``.
            mount_arm: ``Axis`` used for tip pickup/eject motion.
                If ``None`` the pipettor is static. Defaults to None.
            disable_axes (tuple): Axes to disable during tip engagement moves.
                Defaults to ``()``.
            pressure_control: Instance of already-instantiated pressure control device.
                Opinionated choice that this is a PGVA with some support for
                PLC-controlled VEAB at present.
            valve_control: Instance of already-instantiated valve control device.
                Opinionated choice that this is a VAEM with some support for single valves controlled
                by the DO pin on the PGVA at present.

        """
        super(Dispenser, self).__init__(
            config,
            component_type="pipettor",
            component_id=component_id,
            mount_arm=mount_arm,
            disable_axes=disable_axes,
            pressure_control=pressure_control,
            valve_control=valve_control,
        )

    def mix(self, mix_dict: dict, cycles: int) -> None:
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

    def eject_tips(self) -> list[int | str]:
        """Eject tips from the fluid control module."""
        # TODO: How to consider static, mechanical, deck-based, fixed-point ejection mode
        # Make optional?
        # class Ejector
        # if ejector is not None:
        #   ....
        # TODO: Minimum: Add warning that this class assumes a co-mounted, dynamic tip ejection mechanism. Others are not yet supported.
        logger.info("EJECT TIPS START")
        if self.is_static:
            raise NotImplementedError(
                "Axis not configured, fluid_control is configured to be static. Pass in the attachment axis to the constructor if this was done in error"
            )
        self.fluid_control_status.set_busy()
        self._disable_xy_axes()
        try:
            for cycle in range(3):
                logger.debug(
                    f"Eject tips: actuation cycle {cycle + 1}/3"
                )  # TODO: Parameterize the total number of eject cycles for testing
                self._wait_output_pressure(
                    449
                )  # TODO: Change to Pressure Control Library max pressure. Will need slight modificiation of PGVA library
                self.pressure_control.trigger_actuation_valve(10)
                self.pressure_control.trigger_actuation_valve(1000)
                self._wait_output_pressure(
                    -449
                )  # TODO: Change to Pressure Control Library min pressure. Will need slight modificiation of PGVA library
                self.pressure_control.trigger_actuation_valve(10)
                self.pressure_control.trigger_actuation_valve(2000)
            self.pressure_control.set_output_pressure(0)
            self.fluid_control_status.set_clear()
            self._enable_xy_axes()
            logger.info("EJECT TIPS COMPLETE")
            return [self.fluid_control_status.get_status(), "Tips ejected successfully"]
        except Exception as e:
            logger.error(f"EJECT TIPS FAILED: {e}")
            self.fluid_control_status.set_error()
            self._enable_xy_axes()
            return [self.fluid_control_status.get_status(), str(e)]

    def _pickup_action(self, duration: float) -> None:
        if self.is_static or self.mount_arm is None:
            raise NotImplementedError(
                "Axis not configured, fluid_control is configured to be static. Pass in the attachment axis to the constructor if this was done in error"
            )
        delta = 0.5  # mm — FestoAxis.current_position() returns mm
        self.mount_arm.acknowledge_faults()  # TODO: We need a way to NOT dig this deep into internals of the edcon library
        # self.mount_arm.disable_powerstage()
        current_position = self.mount_arm.current_position()
        logger.debug(f"_pickup_action: start position={current_position}, duration={duration}, delta={delta}")
        repeat = True
        count = 0
        self._disable_xy_axes()
        while repeat:
            self.mount_arm.acknowledge_faults()
            self.mount_arm.enable_powerstage()
            self.mount_arm.jog_task(
                True, False, duration=duration
            )  # TODO: Passing all the way to jog_task defeats the purpose of the axis class and make the parameters passed / API confusing. Think of a way to fix this.
            # self.mount_arm.position_task(position=5000, velocity=duration, absolute=False, nonblocking=False)
            # self.mount_arm.jog_task(True, False, duration=0.5)
            new_position = self.mount_arm.current_position()
            movement = abs(new_position - current_position)
            logger.debug(f"_pickup_action: new_position={new_position}, movement={movement}, stall_count={count}")
            if movement <= delta:
                count += 1
                current_position = new_position
            else:
                current_position = new_position
            if count > 1:  # TODO: Parameterize this for testing
                logger.debug("_pickup_action: stall detected — tip engagement complete")
                repeat = False
        self._enable_xy_axes()
        self.mount_arm.acknowledge_faults()

    def pickup_tips(self, duration: float) -> list[int | str]:
        """Pick up tips with the fluid_control."""
        logger.info(f"PICKUP TIPS START: duration={duration}")
        if self.is_static:
            raise NotImplementedError(
                """Axis not configured, fluid_control is configured to be static. Pass in the attachment axis to the constructor 
                during instantiation or specify the attached axis via the configuration file if this was done in error"""
            )
        self.fluid_control_status.set_busy()
        try:
            self._pickup_action(duration=duration)
            self.fluid_control_status.code = 0
            logger.info("PICKUP TIPS COMPLETE")
            return [self.fluid_control_status.get_status(), "Tips picked up successfully"]
        except Exception as e:
            logger.error(f"PICKUP TIPS FAILED: {e}")
            self.fluid_control_status.set_error()
            return [self.fluid_control_status.get_status(), str(e)]
