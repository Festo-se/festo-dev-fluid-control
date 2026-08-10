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

from applied_motion.cli.compose.core import (  # noqa: F401,F403
    Command,
    CommandError,
    CommandGroup,
    CommandHandler,
    UnknownCommandError,
    UsageError,
)

__all__ = [
    "Command",
    "CommandError",
    "CommandGroup",
    "CommandHandler",
    "UnknownCommandError",
    "UsageError",
]
