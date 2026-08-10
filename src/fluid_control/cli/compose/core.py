# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG
# SPDX-License-Identifier: MIT

"""
Composable, transportable command-registry core for interactive CLIs.

This module has **no third-party dependencies** (no ``prompt_toolkit``, no
``rich``) so it can be imported, composed, and unit-tested without any optional
extras installed.  The interactive REPL driver lives in
[`fluid_control.cli.compose.repl`][fluid_control.cli.compose.repl].

The core abstraction is the [`CommandGroup`][fluid_control.cli.compose.core.CommandGroup]: a named node that holds a set
of leaf [`Command`][fluid_control.cli.compose.core.Command] objects and a set of child [`CommandGroup`][fluid_control.cli.compose.core.CommandGroup] nodes.
Because a group can mount another group under a name, a super-CLI can consume the
command groups exported by other packages and expose them hierarchically::

    root = CommandGroup("lhs")
    root.add_child(fluid_control_group, name="pipettor")
    root.add_child(gantry_group, name="gantry")
    # -> "pipettor dispense 1 50 water"  and  "gantry home"

The module is intentionally self-contained so it can later be extracted verbatim
into a standalone ``festo-dev-cli-compose`` distribution shared across packages.
"""

import logging
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass

logger = logging.getLogger(__name__)

CommandHandler = Callable[[Sequence[str]], None]
"""Type alias for a command handler: takes the argument tokens, returns ``None``."""


class CommandError(Exception):
    """Base error for command dispatch or execution failures."""


class UsageError(CommandError):
    """Raise when a command is invoked with missing or invalid arguments."""


class UnknownCommandError(CommandError):
    """Raise when a token matches neither a child group nor a local command."""


@dataclass
class Command:
    """
    A single named leaf command in a [`CommandGroup`][fluid_control.cli.compose.core.CommandGroup].

    Args:
        name: The verb used to invoke the command (matched case-insensitively).
        handler: Callable invoked with the remaining argument tokens.
        usage: One-line usage string shown in help and on [`UsageError`][fluid_control.cli.compose.core.UsageError].
        help: Short human-readable description shown in aggregated help.
        completions: Optional zero-argument callable returning argument-value
            completion candidates (e.g. liquid classes).  Defaults to ``None``.

    Attributes:
        name: The command verb.
        handler: The bound handler callable.
        usage: Usage string.
        help: Description string.
        completions: Optional argument-completion provider.

    """

    name: str
    handler: CommandHandler
    usage: str = ""
    help: str = ""
    completions: Callable[[], list[str]] | None = None

    def __repr__(self) -> str:
        """
        Return a unique, readable representation of the command.

        Returns:
            String of the form ``Command(name='dispense')``.

        """
        return f"Command(name={self.name!r})"


class CommandGroup:
    """
    A composable namespace of commands and nested child groups.

    A group dispatches a token sequence by matching the first token against its
    child groups first, then its local commands.  Child groups let a parent CLI
    mount another package's command group under a name, giving hierarchical,
    discoverable command routing (e.g. ``gantry home``).

    Args:
        name: The group's own name (used as the default mount key in a parent).
        help: Short description shown when the group is listed in a parent.

    Attributes:
        name: The group name.
        help: The group description.
        commands: Mapping of command name → [`Command`][fluid_control.cli.compose.core.Command].
        children: Mapping of child mount name → child [`CommandGroup`][fluid_control.cli.compose.core.CommandGroup].

    """

    def __init__(self, name: str, help: str = "") -> None:
        """
        Initialise an empty command group.

        Args:
            name: The group's own name.
            help: Short description of the group.  Defaults to ``""``.

        """
        self.name = name
        self.help = help
        self.commands: dict[str, Command] = {}
        self.children: dict[str, CommandGroup] = {}
        logger.debug("CommandGroup created: name=%s", name)

    def add_command(self, command: Command) -> Command:
        """
        Register a leaf command on this group.

        Args:
            command: The [`Command`][fluid_control.cli.compose.core.Command] to register.  Its name is stored
                lower-cased for case-insensitive matching.

        Returns:
            The registered [`Command`][fluid_control.cli.compose.core.Command] (for chaining).

        """
        self.commands[command.name.lower()] = command
        return command

    def add_child(self, group: "CommandGroup", name: str | None = None) -> "CommandGroup":
        """
        Mount a child group under a name, enabling hierarchical composition.

        Args:
            group: The child [`CommandGroup`][fluid_control.cli.compose.core.CommandGroup] to mount.
            name: Mount key.  Defaults to ``group.name``.  Stored lower-cased.

        Returns:
            The mounted child [`CommandGroup`][fluid_control.cli.compose.core.CommandGroup] (for chaining).

        """
        key = (name or group.name).lower()
        self.children[key] = group
        logger.debug("CommandGroup %s mounted child under %r", self.name, key)
        return group

    def dispatch(self, tokens: Sequence[str]) -> None:
        """
        Route a token sequence to a child group or a local command.

        Child groups are matched before local commands, so a mounted namespace
        name shadows a like-named local command.

        Args:
            tokens: The whitespace-split command line.  Empty sequences are
                ignored.

        Raises:
            UnknownCommandError: If the leading token matches neither a child
                group nor a local command.
            CommandError: Propagated from a command handler.

        """
        if not tokens:
            return
        head = tokens[0].lower()
        rest = tokens[1:]
        if head in self.children:
            self.children[head].dispatch(rest)
            return
        if head in self.commands:
            self.commands[head].handler(rest)
            return
        raise UnknownCommandError(f"Unknown command: {tokens[0]!r}")

    def iter_paths(self, prefix: Sequence[str] = ()) -> Iterator[tuple[str, ...]]:
        """
        Yield the fully-qualified path of every command in the tree.

        Args:
            prefix: Internal accumulator of parent namespace names.  Callers
                normally omit this.

        Yields:
            Tuples of namespace names ending in a command name, e.g.
            ``("gantry", "home")``.

        """
        for name in self.commands:
            yield (*tuple(prefix), name)
        for child_name, child in self.children.items():
            yield from child.iter_paths((*tuple(prefix), child_name))

    def format_help(self, indent: int = 0) -> list[str]:
        """
        Build indented help lines for this group and all descendants.

        Args:
            indent: Current indentation depth in namespace levels.  Callers
                normally omit this.

        Returns:
            A list of formatted help lines (namespaces then commands, recursing
            into children).

        """
        pad = "  " * indent
        lines: list[str] = []
        for cmd in self.commands.values():
            usage = cmd.usage or cmd.name
            suffix = f"    {cmd.help}" if cmd.help else ""
            lines.append(f"{pad}{usage}{suffix}")
        for child_name, child in self.children.items():
            header = f"{pad}{child_name}"
            if child.help:
                header = f"{header}    {child.help}"
            lines.append(header)
            lines.extend(child.format_help(indent + 1))
        return lines

    def __contains__(self, name: object) -> bool:
        """
        Return whether *name* is a local command or child group name.

        Args:
            name: Candidate name to test (matched case-insensitively).

        Returns:
            ``True`` if *name* is a registered command or child group.

        """
        if not isinstance(name, str):
            return False
        key = name.lower()
        return key in self.commands or key in self.children

    def __len__(self) -> int:
        """
        Return the number of local commands plus child groups.

        Returns:
            Count of direct commands and children (non-recursive).

        """
        return len(self.commands) + len(self.children)

    def __repr__(self) -> str:
        """
        Return a unique, readable representation of the group.

        Returns:
            String of the form
            ``CommandGroup(name='fluid', commands=9, children=1)``.

        """
        return f"CommandGroup(name={self.name!r}, commands={len(self.commands)}, children={len(self.children)})"


__all__ = [
    "Command",
    "CommandError",
    "CommandGroup",
    "CommandHandler",
    "UnknownCommandError",
    "UsageError",
]
