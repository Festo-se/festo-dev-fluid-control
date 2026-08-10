# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG
# SPDX-License-Identifier: MIT

"""
Command-group definitions for the fluid-control CLI.

This module turns the imperative methods on
[`FluidControlSession`][fluid_control.cli.session.FluidControlSession] into a composable
[`CommandGroup`][fluid_control.cli.compose.core.CommandGroup].  The resulting group can
be run standalone by [`fluid_control.cli.cli`][fluid_control.cli.cli] or mounted as a child of a
super-CLI's root group (e.g. a liquid-handling system exposing this component
under ``pipettor``).

Gantry / mount-arm motion commands are collected into their own child group so
that, when composed, they appear under a ``gantry`` namespace
(e.g. ``gantry home``).
"""

import functools
import logging
from collections.abc import Sequence

from fluid_control.cli.compose.core import Command, CommandGroup, UsageError
from fluid_control.cli.render import console, location_table, print_result, status_table
from fluid_control.cli.session import FluidControlSession, _DEFAULT_VELOCITY

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fluid-control command handlers
# ---------------------------------------------------------------------------


def _cmd_valve(session: FluidControlSession, args: Sequence[str]) -> None:
    """
    Handle ``valve <channel> <time_ms> [pressure]``.

    Args:
        session: The bound fluid-control session.
        args: Argument tokens after the ``valve`` verb.

    Raises:
        UsageError: If fewer than two arguments are supplied.

    """
    if len(args) < 2:
        raise UsageError("Usage: valve <channel> <time_ms> [pressure_mbar]")
    channel = int(args[0])
    time_ms = int(args[1])
    pressure = int(args[2]) if len(args) > 2 else 0
    print_result(session.valve_timed(channel, time_ms, pressure))


def _cmd_direct(session: FluidControlSession, args: Sequence[str]) -> None:
    """
    Handle ``direct <ch1:ms1> [ch2:ms2 ...] pressure=<mbar>``.

    Args:
        session: The bound fluid-control session.
        args: Argument tokens after the ``direct`` verb.

    Raises:
        UsageError: If no arguments, an unrecognised token, or no channel:time
            pairs are supplied.

    """
    if not args:
        raise UsageError("Usage: direct <ch1:ms1> [ch2:ms2 ...] pressure=<mbar>  (e.g. direct 1:500 2:400 pressure=70)")
    channel_times: dict[int, int] = {}
    pressure = 0
    for token in args:
        if token.lower().startswith("pressure="):
            pressure = int(token.split("=", 1)[1])
        elif ":" in token:
            ch_str, ms_str = token.split(":", 1)
            channel_times[int(ch_str)] = int(ms_str)
        else:
            raise UsageError(f"Unrecognised token {token!r} — use ch:ms format or pressure=N")
    if not channel_times:
        raise UsageError("No channel:time pairs supplied")
    print_result(session.direct(channel_times, pressure))


def _cmd_dispense(session: FluidControlSession, args: Sequence[str]) -> None:
    """
    Handle ``dispense <channel> <volume_uL> <liquid_class>``.

    Args:
        session: The bound fluid-control session.
        args: Argument tokens after the ``dispense`` verb.

    Raises:
        UsageError: If fewer than three arguments are supplied.

    """
    if len(args) < 3:
        raise UsageError("Usage: dispense <channel> <volume_uL> <liquid_class>")
    print_result(session.dispense(int(args[0]), float(args[1]), args[2]))


def _cmd_aspirate(session: FluidControlSession, args: Sequence[str]) -> None:
    """
    Handle ``aspirate <channel> <volume_uL> <liquid_class>`` (Pipettor only).

    Args:
        session: The bound fluid-control session.
        args: Argument tokens after the ``aspirate`` verb.

    Raises:
        UsageError: If fewer than three arguments are supplied.

    """
    if len(args) < 3:
        raise UsageError("Usage: aspirate <channel> <volume_uL> <liquid_class>")
    print_result(session.aspirate(int(args[0]), float(args[1]), args[2]))


def _cmd_mix(session: FluidControlSession, args: Sequence[str]) -> None:
    """
    Handle ``mix <channel> <volume_uL> <liquid_class> <cycles>``.

    Args:
        session: The bound fluid-control session.
        args: Argument tokens after the ``mix`` verb.

    Raises:
        UsageError: If fewer than four arguments are supplied.

    """
    if len(args) < 4:
        raise UsageError("Usage: mix <channel> <volume_uL> <liquid_class> <cycles>")
    print_result(session.mix(int(args[0]), float(args[1]), args[2], int(args[3])))


def _cmd_pressure(session: FluidControlSession, args: Sequence[str]) -> None:
    """
    Handle ``pressure <mbar>``.

    Args:
        session: The bound fluid-control session.
        args: Argument tokens after the ``pressure`` verb.

    Raises:
        UsageError: If no pressure value is supplied.

    """
    if not args:
        raise UsageError("Usage: pressure <mbar>")
    pressure = int(args[0])
    session.set_pressure(pressure)
    console.print(f"[green]✓[/] Pressure set to [bold]{pressure}[/] mbar")


def _cmd_classes(session: FluidControlSession, args: Sequence[str]) -> None:
    """
    Handle ``classes`` — list configured liquid classes.

    Args:
        session: The bound fluid-control session.
        args: Unused argument tokens.

    """
    classes = session.get_liquid_classes()
    if classes:
        for lc in classes:
            console.print(f"  [cyan]{lc}[/]")
    else:
        console.print("[dim]No liquid classes configured.[/]")


def _cmd_channels(session: FluidControlSession, args: Sequence[str]) -> None:
    """
    Handle ``channels`` — list active valve channels.

    Args:
        session: The bound fluid-control session.
        args: Unused argument tokens.

    """
    console.print(f"  Active channels: [cyan]{session.get_channels()}[/]")


def _cmd_status(session: FluidControlSession, args: Sequence[str]) -> None:
    """
    Handle ``status`` — show combined fluid-control status.

    Args:
        session: The bound fluid-control session.
        args: Unused argument tokens.

    """
    console.print(status_table(session.get_status()))


# ---------------------------------------------------------------------------
# Gantry / mount-arm command handlers
# ---------------------------------------------------------------------------


def _cmd_move(session: FluidControlSession, args: Sequence[str]) -> None:
    """
    Handle ``move <axis> <position_mm> [velocity_mm_s]``.

    Args:
        session: The bound fluid-control session.
        args: Argument tokens after the ``move`` verb.

    Raises:
        UsageError: If fewer than two arguments are supplied.

    """
    if len(args) < 2:
        raise UsageError("Usage: move <axis> <position_mm> [velocity_mm_s]")
    axis_name = args[0].upper()
    position = float(args[1])
    velocity = float(args[2]) if len(args) > 2 else _DEFAULT_VELOCITY
    console.print(location_table(session.move_axis(axis_name, position, velocity)))


def _cmd_raise(session: FluidControlSession, args: Sequence[str]) -> None:
    """
    Handle ``raise <delta_mm> [velocity_mm_s]`` — move mount arm up.

    Args:
        session: The bound fluid-control session.
        args: Argument tokens after the ``raise`` verb.

    Raises:
        UsageError: If no delta is supplied.

    """
    if not args:
        raise UsageError("Usage: raise <delta_mm> [velocity_mm_s]")
    delta = float(args[0])
    velocity = float(args[1]) if len(args) > 1 else _DEFAULT_VELOCITY
    console.print(location_table(session.raise_arm(delta, velocity)))


def _cmd_lower(session: FluidControlSession, args: Sequence[str]) -> None:
    """
    Handle ``lower <delta_mm> [velocity_mm_s]`` — move mount arm down.

    Args:
        session: The bound fluid-control session.
        args: Argument tokens after the ``lower`` verb.

    Raises:
        UsageError: If no delta is supplied.

    """
    if not args:
        raise UsageError("Usage: lower <delta_mm> [velocity_mm_s]")
    delta = -float(args[0])
    velocity = float(args[1]) if len(args) > 1 else _DEFAULT_VELOCITY
    console.print(location_table(session.raise_arm(delta, velocity)))


def _cmd_where(session: FluidControlSession, args: Sequence[str]) -> None:
    """
    Handle ``where`` — print current axis positions.

    Args:
        session: The bound fluid-control session.
        args: Unused argument tokens.

    """
    console.print(location_table(session.where()))


def _cmd_home(session: FluidControlSession, args: Sequence[str]) -> None:
    """
    Handle ``home`` — home all gantry axes.

    Args:
        session: The bound fluid-control session.
        args: Unused argument tokens.

    """
    session.home()
    console.print("[green]✓[/] All axes homed.")


def _cmd_enable(session: FluidControlSession, args: Sequence[str]) -> None:
    """
    Handle ``enable`` — enable the powerstage on the component axes.

    Args:
        session: The bound fluid-control session.
        args: Unused argument tokens.

    """
    session.enable_axes()
    console.print("[green]✓[/] Powerstage enabled.")


def _cmd_disable(session: FluidControlSession, args: Sequence[str]) -> None:
    """
    Handle ``disable`` — disable the powerstage on the component axes.

    Args:
        session: The bound fluid-control session.
        args: Unused argument tokens.

    """
    session.disable_axes()
    console.print("[green]✓[/] Powerstage disabled.")


# ---------------------------------------------------------------------------
# Tip command handlers (Pipettor)
# ---------------------------------------------------------------------------


def _cmd_pickup(session: FluidControlSession, args: Sequence[str]) -> None:
    """
    Handle ``pickup <duration_s>`` — pick up tips (Pipettor only).

    Args:
        session: The bound fluid-control session.
        args: Argument tokens after the ``pickup`` verb.

    Raises:
        UsageError: If no duration is supplied.

    """
    if not args:
        raise UsageError("Usage: pickup <duration_s>")
    print_result(session.pickup_tips(float(args[0])))


def _cmd_eject(session: FluidControlSession, args: Sequence[str]) -> None:
    """
    Handle ``eject`` — eject tips (Pipettor only).

    Args:
        session: The bound fluid-control session.
        args: Unused argument tokens.

    """
    print_result(session.eject_tips())


# ---------------------------------------------------------------------------
# Group builders
# ---------------------------------------------------------------------------


def build_gantry_group(session: FluidControlSession) -> CommandGroup:
    """
    Build the ``gantry`` command group bound to a session's mount arm.

    Args:
        session: The [`FluidControlSession`][fluid_control.cli.session.FluidControlSession]
            whose gantry and mount arm the commands operate on.

    Returns:
        A [`CommandGroup`][fluid_control.cli.compose.core.CommandGroup] named ``gantry``
        containing motion and powerstage commands.

    """
    group = CommandGroup("gantry", help="Mount-arm / gantry motion commands")
    group.add_command(
        Command("move", functools.partial(_cmd_move, session), "move <axis> <position_mm> [velocity]", "Move axis")
    )
    group.add_command(
        Command("raise", functools.partial(_cmd_raise, session), "raise <delta_mm> [velocity]", "Raise mount arm")
    )
    group.add_command(
        Command("lower", functools.partial(_cmd_lower, session), "lower <delta_mm> [velocity]", "Lower mount arm")
    )
    group.add_command(Command("where", functools.partial(_cmd_where, session), "where", "Print axis positions"))
    group.add_command(Command("home", functools.partial(_cmd_home, session), "home", "Home all axes"))
    group.add_command(Command("enable", functools.partial(_cmd_enable, session), "enable", "Enable powerstage"))
    group.add_command(Command("disable", functools.partial(_cmd_disable, session), "disable", "Disable powerstage"))
    return group


def build_group(session: FluidControlSession) -> CommandGroup:
    """
    Build the composable command group for a fluid-control session.

    Registers the fluid-control verbs (valve, direct, dispense, aspirate, mix,
    pressure, classes, channels, status) and tip verbs (pickup, eject) as leaf
    commands, and mounts the gantry motion commands under a ``gantry`` child
    namespace when a gantry is configured on *session*.

    Args:
        session: The [`FluidControlSession`][fluid_control.cli.session.FluidControlSession] to
            expose as a command group.

    Returns:
        A [`CommandGroup`][fluid_control.cli.compose.core.CommandGroup] named ``fluid``
        that can be run standalone or mounted into a super-CLI's root group.

    """
    group = CommandGroup("fluid", help="Festo fluid-control commands")
    group.add_command(
        Command("valve", functools.partial(_cmd_valve, session), "valve <ch> <ms> [pressure]", "Open one valve timed")
    )
    group.add_command(
        Command(
            "direct",
            functools.partial(_cmd_direct, session),
            "direct <ch:ms ...> pressure=<mbar>",
            "Multi-channel raw command",
        )
    )
    group.add_command(
        Command(
            "dispense",
            functools.partial(_cmd_dispense, session),
            "dispense <ch> <vol_uL> <liquid_class>",
            "Dispense volume",
            completions=session.get_liquid_classes,
        )
    )
    group.add_command(
        Command(
            "aspirate",
            functools.partial(_cmd_aspirate, session),
            "aspirate <ch> <vol_uL> <liquid_class>",
            "Aspirate volume (Pipettor)",
            completions=session.get_liquid_classes,
        )
    )
    group.add_command(
        Command(
            "mix",
            functools.partial(_cmd_mix, session),
            "mix <ch> <vol_uL> <liquid_class> <cycles>",
            "Aspirate/dispense mix cycles",
            completions=session.get_liquid_classes,
        )
    )
    group.add_command(
        Command("pressure", functools.partial(_cmd_pressure, session), "pressure <mbar>", "Set output pressure")
    )
    group.add_command(Command("classes", functools.partial(_cmd_classes, session), "classes", "List liquid classes"))
    group.add_command(Command("channels", functools.partial(_cmd_channels, session), "channels", "List valve channels"))
    group.add_command(Command("status", functools.partial(_cmd_status, session), "status", "Show status"))
    group.add_command(Command("pickup", functools.partial(_cmd_pickup, session), "pickup <duration_s>", "Pick up tips"))
    group.add_command(Command("eject", functools.partial(_cmd_eject, session), "eject", "Eject tips"))

    if session.gantry is not None:
        group.add_child(build_gantry_group(session), name="gantry")

    return group


__all__ = ["build_gantry_group", "build_group"]
