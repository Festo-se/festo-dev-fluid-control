# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG
# SPDX-License-Identifier: MIT

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
``loglevel [OFF|DEBUG|INFO|WARNING|ERROR|CRITICAL]``          Show or change current log level
``help``                                                       Print this command reference
``quit``                                                       Exit the REPL
=============================================================  ================================================
"""

import argparse
import json
import logging
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from prompt_toolkit.completion import WordCompleter

from applied_motion.applied_motion import Gantry
from applied_motion.cli.compose.repl import run_repl as _run_group_repl
from applied_motion.cli.theme import festo_console
from configurator import RuntimeRegistry
from fluid_control.cli.commands import build_group
from fluid_control.cli.logging_utils import LOG_LEVEL_CHOICES, configure_logging
from fluid_control.cli.session import FluidControlSession, _TOP_LEVEL_CMDS
from fluid_control import Aspirator, Dispenser, Pipettor

console = festo_console()

logger = logging.getLogger(__name__)


class _OfflineAxis:
    """Minimal axis stub used when a configured gantry cannot connect."""

    def __init__(self, name: str) -> None:
        self.name = name

    def move(self, position: float, velocity: float, **kwargs) -> bool:
        raise RuntimeError("No gantry connection available")

    def home(self) -> bool:
        raise RuntimeError("No gantry connection available")

    def get_current_axis_position(self) -> float:
        return 0.0

    def is_homed(self) -> bool:
        return False

    def stopped(self) -> bool:
        return True

    def acknowledge_faults(self) -> None:
        return None

    def enable_powerstage(self) -> None:
        return None

    def disable_powerstage(self) -> None:
        return None

    def current_position(self) -> float:
        return 0.0

    def current_velocity(self) -> float:
        return 0.0

    def jog_task(
        self,
        jog_positive: bool = True,
        jog_negative: bool = False,
        incremental: bool = False,
        duration: float = 0.0,
    ) -> bool:
        raise RuntimeError("No gantry connection available")

    def ready_for_motion(self) -> bool:
        return False


class _OfflineGantry(Gantry):
    """Fallback gantry object used when the configured hardware is unavailable."""

    def __init__(self, axis_names: list[str], error: str) -> None:
        self.axes = {name: _OfflineAxis(name) for name in axis_names}
        self.concurrent_axes = None
        self._backend = None
        self._bootstrap_error = error

    def home(self) -> None:
        logger.warning("Offline gantry: home skipped because no connection is available")

    def move_to(self, movements: Any, timeout: int | None = None, concurrent: bool = False) -> None:
        raise RuntimeError(f"No gantry connection available: {self._bootstrap_error}")

    def supports_teach(self) -> bool:
        return False

    def teach_pos(self, pos_id: int) -> None:
        raise RuntimeError(f"Teach commands unavailable: {self._bootstrap_error}")

    def teach_tray(self, tray_id: int, tray_pos: int) -> None:
        raise RuntimeError(f"Teach commands unavailable: {self._bootstrap_error}")

    def get_location(self) -> dict[str, float]:
        return {name: 0.0 for name in self.axes}

    def list_commands(self) -> list[str]:
        return []


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


def _resolve_mount_axis_name(component: Mapping[str, Any]) -> str | None:
    """Extract the configured mount axis name from a selected component view."""
    mount_axis = component.get("mount_axis")
    if isinstance(mount_axis, dict):
        return mount_axis.get("name") if isinstance(mount_axis.get("name"), str) else None
    if isinstance(mount_axis, str):
        return mount_axis
    return None


def _bootstrap_gantry(
    component: Mapping[str, Any],
    registry: RuntimeRegistry,
    gantry_config_path: Path | None,
    gantry_id: str,
    mount_axis: str,
) -> tuple[Gantry | None, str]:
    """Resolve an explicit or mounted gantry through the component runtime.

    Args:
        component: Selected fluid component mapping.
        registry: Runtime shared by the selected fluid component.
        gantry_config_path: Optional explicit gantry configuration path.
        gantry_id: Gantry name used with an explicit path.
        mount_axis: CLI fallback mount-axis name.

    Returns:
        A gantry instance (or offline fallback) and the resolved mount-axis name.
    """
    gantry: Gantry | None = None
    resolved_mount_axis = mount_axis

    if gantry_config_path is not None:
        console.print(f"[dim]Loading gantry config:[/] {gantry_config_path}")
        try:
            gantry = Gantry.from_config(gantry_config_path, name=gantry_id, registry=registry)
            console.print(f"[festo.ok]✓[/] Gantry connected: [bold]{gantry!r}[/]")
        except Exception as exc:
            console.print(f"[yellow]![/] Could not connect gantry: {exc}")
            console.print(
                "[dim]Continuing with an offline gantry stub — motion commands will remain unavailable until a connection is restored.[/]"
            )
            gantry = _OfflineGantry([], str(exc))
        return gantry, resolved_mount_axis

    mount_gantry = component.get("mount_gantry")
    discovered_gantry_id = mount_gantry.get("name") if isinstance(mount_gantry, dict) else None
    if not isinstance(discovered_gantry_id, str) or not discovered_gantry_id:
        return None, resolved_mount_axis

    console.print(f"[dim]Bootstrapping gantry from config:[/] {discovered_gantry_id}")
    try:
        gantry = Gantry(name=discovered_gantry_id, registry=registry)
        console.print(f"[festo.ok]✓[/] Gantry connected: [bold]{gantry!r}[/]")
        configured_mount_axis = _resolve_mount_axis_name(component)
        if configured_mount_axis is not None:
            resolved_mount_axis = configured_mount_axis
    except Exception as exc:
        console.print(f"[yellow]![/] Could not connect gantry from component config: {exc}")
        console.print(
            "[dim]Continuing with an offline gantry stub — motion commands will remain unavailable until a connection is restored.[/]"
        )
        axis_names: list[str] = []
        view = registry.views.get(discovered_gantry_id)
        axes_cfg = view.get("axes") if view is not None else None
        if isinstance(axes_cfg, dict):
            axis_names = [axis_name for axis_name in axes_cfg if isinstance(axis_name, str)]
        gantry = _OfflineGantry(axis_names, str(exc))
        configured_mount_axis = _resolve_mount_axis_name(component)
        if configured_mount_axis is not None:
            resolved_mount_axis = configured_mount_axis

    return gantry, resolved_mount_axis


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
        default="OFF",
        choices=LOG_LEVEL_CHOICES,
        metavar="LEVEL",
        help="Python logging level (default: OFF).",
    )
    args = parser.parse_args()

    configure_logging(args.log_level)

    console.print(f"[dim]Loading fluid-control config:[/] {args.config}")
    try:
        # TODO: use configurator functionality instead?
        config = json.loads(args.config.read_text(encoding="utf-8"))
        normalized = config.get("component_config", config)
        components = normalized.get("components", {})
        component_config = components[args.component_id]
        component_type = args.component_type
        if component_type == "auto":
            component_type = component_config.get("component_class", component_config.get("component_type"))
        component_class = {"dispenser": Dispenser, "pipettor": Pipettor, "aspirator": Aspirator}.get(component_type)
        if component_class is None:
            raise ValueError(f"Unsupported component type: {component_type!r}")
        component = component_class(config=config, component_id=args.component_id)
    except Exception as exc:
        console.print(f"[red]✗[/] Failed to load config: {exc}")
        sys.exit(1)

    console.print(f"[dim]Initialising {component_type} [bold]{args.component_id!r}[/]…[/]")
    console.print(f"[festo.ok]✓[/] Component ready: [bold]{component!r}[/]")

    # Optionally connect to a gantry
    gantry, mount_axis_name = _bootstrap_gantry(
        component_config,
        cast(RuntimeRegistry, component.registry),
        args.gantry_config,
        args.gantry_id,
        args.mount_axis,
    )

    session = FluidControlSession(component, gantry=gantry, mount_axis_name=mount_axis_name)
    try:
        run_repl(session)
    finally:
        component.close()


if __name__ == "__main__":
    main()
