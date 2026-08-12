# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""
Backend-agnostic fluid-control session for manual operation.

This module is intentionally free of ``prompt_toolkit`` and ``rich``
dependencies so it can be imported and unit-tested without those packages
installed.  The interactive REPL is in [`fluid_control.cli.cli`][fluid_control.cli.cli].
"""

import functools
import logging
from collections import deque

from applied_motion.applied_motion import Gantry
from fluid_control.fluid_control import ChannelCommand, OperationResult, PressureOverLiquidControl

logger = logging.getLogger(__name__)


class GantryNotConfiguredError(AttributeError):
    """
    Raise when a gantry-dependent method is called without a gantry.

    Subclasses [`AttributeError`][builtins.AttributeError] because the underlying failure is an
    attempted attribute access on ``None`` (``self.gantry`` is unset), while
    remaining precisely catchable by callers that only care about this case.
    """


def require_attr(attr):
    """Raise [`GantryNotConfiguredError`][fluid_control.cli.session.GantryNotConfiguredError] via this decorator if ``self.<attr>`` is ``None``."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if getattr(self, attr) is None:
                raise GantryNotConfiguredError(
                    f"No gantry configured: method '{func.__name__}' is disabled because '{attr}' was not provided."
                )
            return func(self, *args, **kwargs)

        return wrapper

    return decorator


_DEFAULT_VELOCITY: float = 10.0  # mm/s — sensible default for slow, manual moves

_TOP_LEVEL_CMDS: list[str] = [
    "valve",
    "direct",
    "dispense",
    "aspirate",
    "mix",
    "pressure",
    "raise",
    "lower",
    "move",
    "where",
    "home",
    "enable",
    "disable",
    "pickup",
    "eject",
    "classes",
    "channels",
    "status",
    "loglevel",
    "help",
    "quit",
    "exit",
]


class FluidControlSession:
    """
    Backend-agnostic session wrapper for manual fluid-control operations.

    Wraps a [`PressureOverLiquidControl`][fluid_control.fluid_control.PressureOverLiquidControl]
    instance (Dispenser or Pipettor) with optional
    [`Gantry`][applied_motion.applied_motion.Gantry] support for mount-arm motion.
    Has no dependency on ``prompt_toolkit`` or ``rich``; it can be used
    programmatically without an interactive terminal.

    Args:
        component: The [`PressureOverLiquidControl`][fluid_control.fluid_control.PressureOverLiquidControl]
            instance to control.
        gantry: Optional connected [`Gantry`][applied_motion.applied_motion.Gantry] for
            mount-arm motion commands.  Required for ``raise``/``lower``/``move``
            and ``home`` commands.
        mount_axis_name: Name of the axis in *gantry* that acts as the mount arm
            (raise/lower axis).  Defaults to ``"Z"``.

    Attributes:
        component: The bound fluid-control component.
        gantry: The bound gantry, or ``None`` if not provided.
        mount_axis_name: Name of the mount arm axis.

    """

    def __init__(
        self,
        component: PressureOverLiquidControl,
        gantry: Gantry | None = None,
        mount_axis_name: str = "Z",
    ) -> None:
        """
        Initialise a session for the given fluid-control component.

        Args:
            component: The
                [`PressureOverLiquidControl`][fluid_control.fluid_control.PressureOverLiquidControl]
                instance to control.
            gantry: Optional connected [`Gantry`][applied_motion.applied_motion.Gantry]
                for mount-arm motion commands.  Defaults to ``None``.
            mount_axis_name: Name of the mount arm axis in *gantry*.
                Defaults to ``"Z"``.

        """
        self.component = component
        self.gantry = gantry
        self.mount_axis_name = mount_axis_name
        logger.debug(
            "FluidControlSession created: component=%r, gantry=%r, mount_axis=%s",
            component,
            gantry,
            mount_axis_name,
        )

    # ------------------------------------------------------------------
    # Valve / pressure operations
    # ------------------------------------------------------------------

    def valve_timed(self, channel: int, time_ms: int, pressure: int = 0) -> OperationResult:
        """
        Open a single valve for a fixed duration.

        Wraps [`PressureOverLiquidControl.direct_command`][fluid_control.fluid_control.PressureOverLiquidControl.direct_command]
        for the common single-channel case.

        Args:
            channel: Valve channel ID (must be in active channels).
            time_ms: Valve opening duration in milliseconds.  Must be > 0.
            pressure: Output pressure in mbar to hold during the operation.
                Defaults to ``0`` (neutral).

        Returns:
            ``[status_code, message]`` from the underlying direct command.

        """
        logger.info("valve_timed: channel=%d, time_ms=%d, pressure=%d", channel, time_ms, pressure)
        return self.component.direct_command(channel_times={channel: time_ms}, pressure=pressure)

    def direct(self, channel_times: dict[int, int], pressure: int) -> OperationResult:
        """
        Send a multi-channel raw valve command, bypassing volume calibration.

        Args:
            channel_times: Mapping of channel ID → opening time in ms.
            pressure: Output pressure in mbar for the operation.

        Returns:
            ``[status_code, message]`` from the underlying direct command.

        """
        logger.info("direct: channel_times=%s, pressure=%d", channel_times, pressure)
        return self.component.direct_command(channel_times=channel_times, pressure=pressure)

    def dispense(self, channel: int, volume_ul: float, liquid_class: str) -> OperationResult:
        """
        Dispense a volume on a single channel.

        Args:
            channel: Valve channel ID.
            volume_ul: Volume to dispense in microlitres.
            liquid_class: Liquid class key matching a calibration entry.

        Returns:
            ``[status_code, message]`` describing the outcome.

        """
        logger.info("dispense: channel=%d, volume_ul=%.2f, liquid_class=%r", channel, volume_ul, liquid_class)
        dispense_dict: dict[int, ChannelCommand] = {channel: {"volume": volume_ul, "liquid_class": liquid_class}}
        self.component.dispense(dispense_dict)
        return OperationResult(self.component.fluid_control_status.get_status(), "Dispense complete")

    def aspirate(self, channel: int, volume_ul: float, liquid_class: str) -> OperationResult:
        """
        Aspirate a volume on a single channel (Pipettor only).

        Args:
            channel: Valve channel ID.
            volume_ul: Volume to aspirate in microlitres.
            liquid_class: Liquid class key matching a calibration entry.

        Returns:
            ``[status_code, message]`` describing the outcome.

        Raises:
            NotImplementedError: If the component does not support aspiration
                (e.g. a [`Dispenser`][fluid_control.Dispenser]).

        """
        logger.info("aspirate: channel=%d, volume_ul=%.2f, liquid_class=%r", channel, volume_ul, liquid_class)
        aspirate_dict: dict[int, ChannelCommand] = {channel: {"volume": volume_ul, "liquid_class": liquid_class}}
        self.component.aspirate(aspirate_dict)
        return OperationResult(self.component.fluid_control_status.get_status(), "Aspirate complete")

    def mix(self, channel: int, volume_ul: float, liquid_class: str, cycles: int) -> OperationResult:
        """
        Mix by repeatedly aspirating and dispensing on a channel.

        Args:
            channel: Valve channel ID.
            volume_ul: Volume per cycle in microlitres.
            liquid_class: Liquid class key matching a calibration entry.
            cycles: Number of aspirate/dispense cycles.

        Returns:
            ``[status_code, message]`` describing the outcome.

        Raises:
            NotImplementedError: If the component does not support mixing
                (e.g. a static [`Dispenser`][fluid_control.Dispenser]).

        """
        logger.info(
            "mix: channel=%d, volume_ul=%.2f, liquid_class=%r, cycles=%d",
            channel,
            volume_ul,
            liquid_class,
            cycles,
        )
        mix_dict: dict[int, ChannelCommand] = {channel: {"volume": volume_ul, "liquid_class": liquid_class}}
        self.component.mix(mix_dict, cycles)
        return OperationResult(self.component.fluid_control_status.get_status(), f"Mix complete ({cycles} cycle(s))")

    def set_pressure(self, pressure_mbar: int) -> None:
        """
        Set output pressure and block until it stabilises.

        Args:
            pressure_mbar: Target pressure in mbar.

        """
        logger.info("set_pressure: %d mbar", pressure_mbar)
        self.component._wait_output_pressure(pressure_mbar)

    # ------------------------------------------------------------------
    # Axis / gantry operations
    # ------------------------------------------------------------------

    @require_attr("gantry")
    def move_axis(self, axis_name: str, position_mm: float, velocity: float = _DEFAULT_VELOCITY) -> dict[str, float]:
        """
        Move a gantry axis to an absolute position.

        Args:
            axis_name: Name of the axis as registered in the gantry.
            position_mm: Target position in mm (absolute).
            velocity: Move speed in mm/s.  Defaults to ``10.0``.

        Returns:
            Gantry location dict after the move completes.

        Raises:
            GantryNotConfiguredError: If no gantry is configured.
            KeyError: If *axis_name* is not registered with the gantry.

        """
        logger.info("move_axis: axis=%s, position=%.3f mm, velocity=%.1f mm/s", axis_name, position_mm, velocity)
        axis = self.gantry.axes[axis_name]  # type: ignore[ty:unresolved-attribute]
        clamped = max(axis.min_position, min(axis.max_position, position_mm))
        if clamped != position_mm:
            logger.warning(
                "move_axis: position %.3f mm clamped to %.3f mm (axis limits [%.3f, %.3f])",
                position_mm,
                clamped,
                axis.min_position,
                axis.max_position,
            )
        if abs(clamped - self.gantry.get_location()[axis_name]) < 1e-3:  # type: ignore[ty:unresolved-attribute]
            return self.gantry.get_location()  # type: ignore[ty:unresolved-attribute]
        self.gantry.move_to(  # type: ignore[ty:unresolved-attribute]
            deque([{axis_name: {"position": clamped, "velocity": velocity}}]),
        )
        return self.gantry.get_location()  # # type: ignore[ty:unresolved-attribute]

    @require_attr("gantry")
    def raise_arm(self, delta_mm: float, velocity: float = _DEFAULT_VELOCITY) -> dict[str, float]:
        """
        Move the mount arm by a relative offset from its current position.

        TODO: add flag for checking if axis is mounted inverted and support for positioning
        Reads the current axis position and applies *delta_mm* as a signed
        offset.  Positive values move the arm in the positive axis direction;
        negative values move it in the opposite direction.

        The ``raise`` REPL command passes a positive delta; the ``lower``
        command passes a negative delta.  Absolute moves can be achieved with
        [`move_axis`][move_axis] directly.

        Args:
            delta_mm: Relative move distance in mm.  Positive = higher encoder
                count; negative = lower encoder count.
            velocity: Move speed in mm/s.  Defaults to ``10.0``.

        Returns:
            Gantry location dict after the move completes.

        Raises:
            GantryNotConfiguredError: If no gantry is configured.

        """
        current = self.gantry.get_location()  # type: ignore[ty:unresolved-attribute]
        new_position = current[self.mount_axis_name] + delta_mm
        return self.move_axis(self.mount_axis_name, new_position, velocity)

    @require_attr("gantry")
    def where(self) -> dict[str, float]:
        """
        Return the current position of all gantry axes.

        Returns:
            Mapping of axis name → position in mm.

        Raises:
            GantryNotConfiguredError: If no gantry is configured.

        """
        return self.gantry.get_location()  # type: ignore[ty:unresolved-attribute]

    @require_attr("gantry")
    def home(self) -> None:
        """
        Home all axes on the gantry.

        Raises:
            GantryNotConfiguredError: If no gantry is configured.

        """
        logger.info("home: homing all gantry axes")
        self.gantry.home()  # type: ignore[ty:unresolved-attribute]

    def enable_axes(self) -> None:
        """
        Enable the powerstage on the component's ``disable_axes`` list.

        Raises:
            NotImplementedError: If the component is static (no axes configured).

        """
        logger.info("enable_axes: enabling powerstage on disable_axes")
        self.component._enable_lateral_axes()

    def disable_axes(self) -> None:
        """
        Disable the powerstage on the component's ``disable_axes`` list.

        Raises:
            NotImplementedError: If the component is static (no axes configured).

        """
        logger.info("disable_axes: disabling powerstage on disable_axes")
        self.component._disable_lateral_axes()

    # ------------------------------------------------------------------
    # Tip operations (Pipettor)
    # ------------------------------------------------------------------

    def pickup_tips(self, duration: float) -> OperationResult:
        """
        Pick up tips by driving the mount arm downward until stall detection.

        Args:
            duration: Jog duration in seconds per stall-detection cycle.

        Returns:
            ``[status_code, message]`` from the pickup operation.

        Raises:
            NotImplementedError: If the component is static or does not support
                tip pickup (e.g. a [`Dispenser`][fluid_control.Dispenser]).

        """
        logger.info("pickup_tips: duration=%.2f s", duration)
        return self.component.pickup_tips(duration)

    def eject_tips(self) -> OperationResult:
        """
        Eject tips using pneumatic actuation.

        Returns:
            ``[status_code, message]`` from the eject operation.

        Raises:
            NotImplementedError: If the component does not support tip ejection
                (e.g. a [`Dispenser`][fluid_control.Dispenser]).

        """
        logger.info("eject_tips: ejecting tips")
        return self.component.eject_tips()

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        """
        Return combined fluid-control, pressure, and valve status.

        Returns:
            Status dict from
            [`PressureOverLiquidControl.get_status`][fluid_control.fluid_control.PressureOverLiquidControl.get_status].

        """
        return self.component.get_status()

    def get_liquid_classes(self) -> list[str]:
        """
        Return all available liquid class names.

        Returns:
            List of liquid class name strings from the current calibration config.

        """
        return list(self.component.get_liquid_classes())

    def get_channels(self) -> list[int]:
        """
        Return the list of active valve channel IDs.

        Returns:
            List of active channel integers.

        """
        return list(self.component.active_channels)
