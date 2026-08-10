# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""
Interactive CLI REPL for Festo fluid-control components.

Provides a ``prompt_toolkit``-powered REPL for manual operation of
[`Dispenser`][fluid_control.Dispenser] and [`Pipettor`][fluid_control.Pipettor]
components.

[`FluidControlSession`][fluid_control.cli.cli.FluidControlSession] is the backend-agnostic
session wrapper; it has no dependency on ``prompt_toolkit`` or ``rich``
and can be used programmatically without an interactive terminal.

The interactive REPL ([`fluid_control.cli.cli`][fluid_control.cli.cli]) and the
``fluid-control-cli`` entry point require the ``cli`` optional-dependency
extra::

    pip install festo-dev-fluid-control[cli]

Typical usage::

    from fluid_control.cli import FluidControlSession

    session = FluidControlSession(component, gantry=gantry, mount_axis_name="Z")
    session.set_pressure(70)
    session.valve_timed(channel=1, time_ms=500, pressure=70)

To launch the interactive REPL::

    fluid-control-cli --config micro-dispenser-config.json --component-id micro-dispenser
"""

from fluid_control.cli.session import FluidControlSession
from fluid_control.cli.commands import build_gantry_group, build_group
from fluid_control.cli.cli import run_repl

__all__ = ["FluidControlSession", "build_gantry_group", "build_group", "run_repl"]
