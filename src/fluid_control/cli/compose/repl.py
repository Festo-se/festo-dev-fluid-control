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

from applied_motion.cli.compose.repl import *  # noqa: F401,F403

__all__ = ["NamespaceCompleter", "render_help", "run_repl"]
