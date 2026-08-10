# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG
# SPDX-License-Identifier: MIT

"""
Composable super-CLI example: a liquid-handling system consuming sub-CLIs.

This script demonstrates how a higher-level system (here a stand-in
"liquid-handling system", ``lhs``) can consume the fluid-control command group
and expose it hierarchically under its own namespace, alongside a sibling
``gantry`` namespace.  The same pattern lets a real system mount the command
groups exported by any number of component packages and route to them by name::

    lhs> pipettor dispense 1 50 water     # -> fluid-control group
    lhs> pipettor gantry home             # -> fluid-control's own gantry child
    lhs> gantry where                     # -> sibling gantry namespace

The composition relies only on the transportable
[`CommandGroup`][fluid_control.cli.compose.core.CommandGroup] contract: each package
returns a group, and the parent mounts it with
[`CommandGroup.add_child`][fluid_control.cli.compose.core.CommandGroup.add_child].

Run it (requires the ``cli`` extra and a valid config)::

    python examples/composable_cli.py --config micro-dispenser-config.json --component-id micro-dispenser --gantry-config gantry.json
"""

import argparse
import json
from pathlib import Path

from applied_motion.applied_motion import Gantry

from fluid_control import Dispenser, Pipettor
from fluid_control.cli.commands import build_gantry_group, build_group
from fluid_control.cli.compose.core import CommandGroup
from fluid_control.cli.compose.repl import run_repl
from fluid_control.cli.session import FluidControlSession
from fluid_control.fluid_control import PressureOverLiquidControl


def build_liquid_handling_cli(session: FluidControlSession) -> CommandGroup:
    """
    Compose a liquid-handling root group from a fluid-control session.

    Mounts the full fluid-control command group under ``pipettor`` and the
    mount-arm motion commands under a sibling ``gantry`` namespace, illustrating
    how a super-CLI consumes and re-exposes component sub-CLIs.

    Args:
        session: A [`FluidControlSession`][fluid_control.cli.session.FluidControlSession]
            wrapping the connected component (and optional gantry).

    Returns:
        The composed root [`CommandGroup`][fluid_control.cli.compose.core.CommandGroup].

    """
    root = CommandGroup("lhs", help="Liquid-handling system commands")
    root.add_child(build_group(session), name="pipettor")
    if session.gantry is not None:
        root.add_child(build_gantry_group(session), name="gantry")
    return root


def _load_component(config: dict, component_id: str) -> PressureOverLiquidControl:
    """
    Instantiate the fluid-control component named in the config.

    Args:
        config: The parsed fluid-control configuration dictionary.
        component_id: The component ID key to instantiate.

    Returns:
        A [`PressureOverLiquidControl`][fluid_control.fluid_control.PressureOverLiquidControl]
        instance (Dispenser or Pipettor) per the config's ``component_class``.

    """
    parsed = config.get("component_config", config)
    component_class = parsed["components"][component_id].get("component_class", "dispenser")
    if component_class == "pipettor":
        return Pipettor(config=config, component_id=component_id)
    return Dispenser(config=config, component_id=component_id)


def main() -> None:
    """Entry point for the composable liquid-handling CLI example."""
    parser = argparse.ArgumentParser(description="Composable liquid-handling CLI example.")
    parser.add_argument("--config", required=True, type=Path, help="Fluid-control config JSON path.")
    parser.add_argument("--component-id", required=True, help="Component ID key inside the config.")
    parser.add_argument("--gantry-config", type=Path, default=None, help="Optional gantry config JSON path.")
    parser.add_argument("--gantry-id", default="gantry_1", help="Gantry component ID (default: gantry_1).")
    parser.add_argument("--mount-axis", default="Z", help="Mount-arm axis name (default: Z).")
    args = parser.parse_args()

    with args.config.open() as fh:
        config = json.load(fh)
    component = _load_component(config, args.component_id)

    gantry = None
    if args.gantry_config is not None:
        gantry = Gantry.from_config(args.gantry_config, name=args.gantry_id)

    session = FluidControlSession(component, gantry=gantry, mount_axis_name=args.mount_axis)
    run_repl(build_liquid_handling_cli(session), prompt="lhs> ")


if __name__ == "__main__":
    main()
