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

    python examples/composable_cli.py --component-id pipettor_1
"""

import argparse
import json
from pathlib import Path

from applied_motion import Gantry

from fluid_control import Aspirator, Dispenser, Pipettor, load_example_config
from fluid_control.cli.commands import build_gantry_group, build_group
from fluid_control.cli.compose.core import CommandGroup
from fluid_control.cli.compose.repl import run_repl
from fluid_control.cli.session import FluidControlSession


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


def main() -> None:
    """Entry point for the composable liquid-handling CLI example."""
    parser = argparse.ArgumentParser(description="Composable liquid-handling CLI example.")
    parser.add_argument("--config", type=Path, default=None, help="Optional fluid-control config JSON path.")
    parser.add_argument("--component-id", default="pipettor_1", help="Component ID key inside the config.")
    parser.add_argument("--gantry-config", type=Path, default=None, help="Optional gantry config JSON path.")
    parser.add_argument("--gantry-id", default="gantry_1", help="Gantry component ID (default: gantry_1).")
    parser.add_argument("--mount-axis", default="Z", help="Mount-arm axis name (default: Z).")
    args = parser.parse_args()

    config = load_example_config() if args.config is None else json.loads(args.config.read_text(encoding="utf-8"))
    normalized = config.get("component_config", config)
    component_config = normalized["components"][args.component_id]
    component_type = component_config.get("component_class", component_config.get("component_type"))
    component_class = {"dispenser": Dispenser, "pipettor": Pipettor, "aspirator": Aspirator}.get(component_type)
    if component_class is None:
        parser.error(f"Unsupported component type for {args.component_id!r}: {component_type!r}")

    with component_class(config=config, component_id=args.component_id) as component:
        gantry = None
        if args.gantry_config is not None:
            gantry = Gantry.from_config(args.gantry_config, name=args.gantry_id, registry=component.registry)
        else:
            mount_gantry = component_config.get("mount_gantry")
            gantry_name = mount_gantry.get("name") if isinstance(mount_gantry, dict) else None
            if isinstance(gantry_name, str) and gantry_name:
                gantry = Gantry(name=gantry_name, registry=component.registry)

        session = FluidControlSession(component, gantry=gantry, mount_axis_name=args.mount_axis)
        run_repl(build_liquid_handling_cli(session), prompt="lhs> ")


if __name__ == "__main__":
    main()
