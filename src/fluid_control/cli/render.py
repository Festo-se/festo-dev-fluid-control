# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG
# SPDX-License-Identifier: MIT

"""
Rich rendering helpers shared by the fluid-control CLI command handlers.

These helpers require the ``rich`` extra and are kept separate from the command
definitions so both the interactive entry point
([`fluid_control.cli.cli`][fluid_control.cli.cli]) and the command handlers
([`fluid_control.cli.commands`][fluid_control.cli.commands]) can reuse them without a circular import.
"""

from collections.abc import Sequence

from rich.console import Console
from rich.table import Table, box

from fluid_control.fluid_control import OperationResult

console = Console()


def print_result(result: OperationResult | Sequence[int | str]) -> None:
    """
    Print a fluid-control result to the console with status styling.

    Args:
        result: An [`OperationResult`][fluid_control.fluid_control.OperationResult]
            ``(code, message)`` (or any two-element ``[status_code, message]``
            sequence) as returned by fluid-control operations.  Status code
            ``0`` is clear (success), ``1`` is error, ``2`` is busy.

    """
    if not result:
        return
    code = result[0] if result else 1
    message = str(result[1]) if len(result) > 1 else ""
    if code == 0:
        console.print(f"[green]✓[/] {message}")
    elif code == 2:
        console.print(f"[yellow]~[/] {message}")
    else:
        console.print(f"[red]✗[/] {message}")


def status_table(status: dict) -> Table:
    """
    Render a fluid-control status dict as a Rich table.

    Args:
        status: Status dict as returned by
            [`PressureOverLiquidControl.get_status`][fluid_control.fluid_control.PressureOverLiquidControl.get_status].

    Returns:
        A [`Table`][rich.table.Table] ready for console output.

    """
    table = Table(show_header=True, header_style="bold cyan", box=box.SIMPLE, padding=(0, 1))
    table.add_column("Key", style="bold")
    table.add_column("Value", justify="left")
    for key, value in status.items():
        table.add_row(str(key), str(value))
    return table


def location_table(loc: dict[str, float]) -> Table:
    """
    Render an axis-position dict as a Rich table.

    Args:
        loc: Mapping of axis name → position in mm.

    Returns:
        A [`Table`][rich.table.Table] ready for console output.

    """
    table = Table(show_header=True, header_style="bold cyan", box=box.SIMPLE, padding=(0, 1))
    table.add_column("Axis", style="bold")
    table.add_column("Position (mm)", justify="right")
    for axis, pos in loc.items():
        table.add_row(axis, f"{pos:.3f}")
    return table


__all__ = ["console", "location_table", "print_result", "status_table"]
