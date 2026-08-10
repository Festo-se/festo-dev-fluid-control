# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG
# SPDX-License-Identifier: MIT

"""
Generic ``prompt_toolkit`` REPL driver for [`CommandGroup`][fluid_control.cli.compose.repl.CommandGroup] trees.

This module requires the interactive extras (``prompt_toolkit`` and ``rich``)
and provides a single reusable driver, [`run_repl`][fluid_control.cli.compose.repl.run_repl], that any package can
use to run its (possibly composed) command tree.  It is deliberately kept apart
from [`fluid_control.cli.compose.core`][fluid_control.cli.compose.core] so the core registry stays importable
without any optional dependencies.

The driver supplies the built-in ``help``, ``quit`` and ``exit`` verbs and a
[`NamespaceCompleter`][fluid_control.cli.compose.repl.NamespaceCompleter] that offers hierarchical tab-completion across nested
namespaces.  All command output is produced by the individual command handlers;
the driver only renders help and dispatch errors.
"""

import logging

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console

from fluid_control.cli.compose.core import (
    CommandError,
    CommandGroup,
    UnknownCommandError,
    UsageError,
)

logger = logging.getLogger(__name__)

_RESERVED_CMDS = ["help", "quit", "exit"]


class NamespaceCompleter(Completer):
    """
    Hierarchical tab-completer that walks a [`CommandGroup`][fluid_control.cli.compose.repl.CommandGroup] tree.

    As the user types, the completer navigates into matched child namespaces and
    offers the child groups and commands available at the current depth, plus the
    reserved verbs at the root level.

    Args:
        root: The root [`CommandGroup`][fluid_control.cli.compose.repl.CommandGroup] to complete against.

    Attributes:
        root: The bound root group.

    """

    def __init__(self, root: CommandGroup) -> None:
        """
        Initialise the completer for a command tree.

        Args:
            root: The root [`CommandGroup`][fluid_control.cli.compose.repl.CommandGroup] to complete against.

        """
        self.root = root

    def get_completions(self, document, complete_event):  # noqa: ANN001, ANN201, D102
        text = document.text_before_cursor
        tokens = text.split()
        at_word_boundary = text == "" or text.endswith(" ")
        consumed = tokens if at_word_boundary else tokens[:-1]
        partial = "" if at_word_boundary else tokens[-1].lower()

        group = self.root
        for token in consumed:
            key = token.lower()
            if key in group.children:
                group = group.children[key]
            else:
                # Reached a command or its arguments — no namespace completions.
                return

        options = list(group.children.keys()) + list(group.commands.keys())
        if group is self.root:
            options = options + _RESERVED_CMDS
        for option in options:
            if option.startswith(partial):
                yield Completion(option, start_position=-len(partial))


def render_help(root: CommandGroup) -> str:
    """
    Render an aggregated help listing for a command tree.

    Args:
        root: The root [`CommandGroup`][fluid_control.cli.compose.repl.CommandGroup] to describe.

    Returns:
        A multi-line string listing every namespace and command, followed by the
        reserved verbs.

    """
    lines = ["[bold cyan]Commands[/]"]
    lines.extend(f"  {line}" for line in root.format_help())
    lines.append("  help    Show this reference")
    lines.append("  quit    Exit")
    return "\n".join(lines)


def run_repl(  # noqa: C901
    root: CommandGroup,
    prompt: str = "> ",
    console: Console | None = None,
    intro: bool = True,
) -> None:
    """
    Run an interactive REPL over a (possibly composed) command tree.

    Provides tab-completion and command history, dispatches each line to *root*,
    and renders dispatch errors uniformly.  The built-in ``help`` verb prints the
    aggregated command listing; ``quit``/``exit`` leave the loop.

    Args:
        root: The root [`CommandGroup`][fluid_control.cli.compose.repl.CommandGroup] to dispatch against.
        prompt: The prompt string shown before each input.  Defaults to ``"> "``.
        console: Optional [`Console`][rich.console.Console] for output.  A new one
            is created when omitted.
        intro: When ``True`` (default), print the aggregated help on startup.

    """
    console = console or Console()
    session: PromptSession[str] = PromptSession(
        history=InMemoryHistory(),
        completer=NamespaceCompleter(root),
    )

    if intro:
        console.print(render_help(root))

    while True:
        try:
            raw = session.prompt(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Exiting.[/]")
            break

        if not raw:
            continue

        tokens = raw.split()
        head = tokens[0].lower()

        if head in ("quit", "exit"):
            break
        if head == "help":
            console.print(render_help(root))
            continue

        try:
            root.dispatch(tokens)
        except UsageError as exc:
            console.print(f"[red]✗[/] {exc}")
        except UnknownCommandError as exc:
            console.print(f"[red]✗[/] {exc}  (type [green]help[/])")
        except NotImplementedError as exc:
            console.print(f"[yellow]![/] Not supported: {exc}")
        except AttributeError as exc:
            # e.g. a gantry-dependent command invoked without a gantry configured.
            console.print(f"[yellow]![/] Not available: {exc}")
        except (KeyError, ValueError, IndexError, RuntimeError, CommandError) as exc:
            console.print(f"[red]✗[/] {exc}")
        except Exception as exc:  # noqa: BLE001 - REPL must not die on handler errors
            logger.exception("Unexpected error processing command %r", raw)
            console.print(f"[red]✗[/] Unexpected error: {exc}")


__all__ = ["NamespaceCompleter", "render_help", "run_repl"]
