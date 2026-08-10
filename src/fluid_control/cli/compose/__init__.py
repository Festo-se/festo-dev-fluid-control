# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG
# SPDX-License-Identifier: MIT

"""
Composable, transportable command-registry framework for interactive CLIs.

The [`fluid_control.cli.compose.core`][fluid_control.cli.compose.core] submodule provides the dependency-free
registry ([`Command`][fluid_control.cli.compose.Command], [`CommandGroup`][fluid_control.cli.compose.CommandGroup] and error types) that packages
use to describe and compose their commands.  The
[`fluid_control.cli.compose.repl`][fluid_control.cli.compose.repl] submodule provides a generic
``prompt_toolkit`` REPL driver and requires the interactive extras.

This subpackage is self-contained by design so it can later be lifted verbatim
into a standalone ``festo-dev-cli-compose`` distribution shared across packages.
"""

from applied_motion.cli.compose import (
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
