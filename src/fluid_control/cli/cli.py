# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""
Interactive REPL for manual operation of Festo fluid-control components.

Requires the ``cli`` optional-dependency extra::

    pip install festo-dev-fluid-control[cli]

Launch via the installed entry point::

    fluid-control-cli --config micro-dispenser-config.json --component-id micro-dispenser

Or directly::

    python -m fluid_control.cli.cli --config micro-dispenser-config.json --component-id micro-dispenser

Commands
--------
The REPL accepts the following commands (tab-completion and command history
are provided by ``prompt_toolkit``):

=============================================================  ================================================
Command                                                        Effect
=============================================================  ================================================
``valve <ch> <ms> [pressure]``                                 Open one valve for *ms* milliseconds
``direct <ch1:ms1> [ch2:ms2 ...] pressure=<mbar>``            Multi-channel direct command (bypass calibration)
``dispense <ch> <vol_uL> <liquid_class>``                      Dispense volume on channel
``aspirate <ch> <vol_uL> <liquid_class>``                      Aspirate volume on channel (Pipettor only)
``mix <ch> <vol_uL> <liquid_class> <cycles>``                  Mix aspirate/dispense cycles
``pressure <mbar>``                                            Set output pressure and wait for it to stabilise
``raise <position_mm> [velocity_mm_s]``                        Move mount arm up by delta mm (relative)
``lower <position_mm> [velocity_mm_s]``                        Move mount arm down by delta mm (relative)
``move <axis> <position_mm> [velocity_mm_s]``                  Move named gantry axis to absolute position
``where``                                                      Print current mount-arm / gantry position
``home``                                                       Home the gantry (if connected)
``enable``                                                     Enable powerstage on disable_axes
``disable``                                                     Disable powerstage on disable_axes
``pickup <duration_s>``                                        Pick up tips (Pipettor only)
``eject``                                                      Eject tips (Pipettor only)
``classes``                                                    List available liquid classes
``channels``                                                   List active valve channels
``status``                                                     Show fluid-control, pressure, and valve status
``help``                                                       Print this command reference
``quit``                                                       Exit the REPL
=============================================================  ================================================
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from prompt_toolkit.completion import WordCompleter
from rich.console import Console

from applied_motion.applied_motion import Gantry
from applied_motion.cli.compose.repl import run_repl as _run_group_repl
from fluid_control import Dispenser, Pipettor
from fluid_control.cli.commands import build_group
from fluid_control.cli.session import FluidControlSession, _TOP_LEVEL_CMDS
from fluid_control.fluid_control import PressureOverLiquidControl

console = Console()
logger = logging.getLogger(__name__)


def _build_completer(axis_names: list[str]) -> WordCompleter:
    """
    Build a tab-completer seeded with all top-level commands and axis names.

    Args:
        axis_names: List of axis name strings from the connected gantry.

    Returns:
        A [`WordCompleter`][prompt_toolkit.completion.WordCompleter] for the REPL.

    """
    return WordCompleter(
        _TOP_LEVEL_CMDS + axis_names,
        ignore_case=True,
        sentence=True,
    )


def run_repl(session: FluidControlSession) -> None:
    """
    Launch the interactive fluid-control REPL.

    Builds the composable fluid-control command group (with the ``gantry``
    child namespace when a gantry is configured) and runs it through the shared
    [`run_repl`][fluid_control.cli.compose.repl.run_repl] driver, which provides
    tab-completion, command history, and hierarchical dispatch.

    Args:
        session: A [`FluidControlSession`][fluid_control.cli.session.FluidControlSession]
            instance wrapping a connected fluid-control component.

    """
    root = build_group(session)
    _run_group_repl(root, prompt="fluid> ", console=console)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point for the ``fluid-control-cli`` CLI command."""
    parser = argparse.ArgumentParser(
        prog="fluid-control-cli",
        description="Interactive REPL for Festo fluid-control components.",
    )
    parser.add_argument(
        "--config",
        required=True,
        type=Path,
        metavar="PATH",
        help="Path to the fluid-control JSON configuration file.",
    )
    parser.add_argument(
        "--component-id",
        required=True,
        metavar="ID",
        help="Component ID key inside config['components'] (e.g. 'micro-dispenser').",
    )
    parser.add_argument(
        "--component-type",
        default="auto",
        choices=["auto", "dispenser", "pipettor"],
        help=("Component type to instantiate.  'auto' (default) reads 'component_class' from the config."),
    )
    parser.add_argument(
        "--gantry-config",
        type=Path,
        metavar="PATH",
        default=None,
        help="Path to a gantry JSON configuration file for mount-arm motion commands.",
    )
    parser.add_argument(
        "--gantry-id",
        metavar="ID",
        default="gantry_1",
        help="Gantry component ID key inside gantry config (default: gantry_1).",
    )
    parser.add_argument(
        "--mount-axis",
        metavar="NAME",
        default="Z",
        help="Axis name in the gantry that acts as the mount arm (default: Z).",
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        metavar="LEVEL",
        help="Python logging level (default: WARNING).",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.WARNING),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Load fluid-control config
    console.print(f"[dim]Loading fluid-control config:[/] {args.config}")
    try:
        with args.config.open() as fh:
            fc_config: dict = json.load(fh)
    except Exception as exc:
        console.print(f"[red]✗[/] Failed to load config: {exc}")
        sys.exit(1)

    # Determine component type
    component_type = args.component_type
    if component_type == "auto":
        parsed = fc_config.get("component_config", fc_config)
        try:
            component_type = parsed["components"][args.component_id].get("component_class", "dispenser")
        except KeyError:
            console.print(f"[red]✗[/] Component ID {args.component_id!r} not found in config.")
            sys.exit(1)

    # Instantiate the component
    console.print(f"[dim]Initialising {component_type} [bold]{args.component_id!r}[/]…[/]")
    try:
        if component_type == "pipettor":
            component: PressureOverLiquidControl = Pipettor(
                config=fc_config,
                component_id=args.component_id,
            )
        else:
            component = Dispenser(
                config=fc_config,
                component_id=args.component_id,
            )
    except Exception as exc:
        console.print(f"[red]✗[/] Failed to initialise component: {exc}")
        sys.exit(1)

    console.print(f"[green]✓[/] Component ready: [bold]{component!r}[/]")

    # Optionally connect to a gantry
    gantry: Gantry | None = None
    if args.gantry_config is not None:
        console.print(f"[dim]Loading gantry config:[/] {args.gantry_config}")
        try:
            gantry = Gantry.from_config(args.gantry_config, name=args.gantry_id)
            console.print(f"[green]✓[/] Gantry connected: [bold]{gantry!r}[/]")
        except Exception as exc:
            console.print(f"[yellow]![/] Could not connect gantry: {exc}")
            console.print("[dim]Continuing without gantry — axis commands will be unavailable.[/]")

    session = FluidControlSession(component, gantry=gantry, mount_axis_name=args.mount_axis)
    run_repl(session)


if __name__ == "__main__":
    main()
