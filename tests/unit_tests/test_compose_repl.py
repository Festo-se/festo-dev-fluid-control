# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""Unit tests for the composable REPL driver helpers.

Covers [`render_help`][fluid_control.cli.compose.repl.render_help] and
[`NamespaceCompleter`][fluid_control.cli.compose.repl.NamespaceCompleter].  The whole module is
skipped when ``prompt_toolkit`` is not importable, since the driver depends on
the interactive extras.
"""

import importlib.util

import pytest

from fluid_control.cli.compose.core import Command, CommandGroup

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("prompt_toolkit") is None,
    reason="prompt_toolkit not installed — skipping REPL driver tests",
)


def _sample_root() -> CommandGroup:
    """Return a small root group with one command and a gantry child."""
    child = CommandGroup("gantry", help="Motion")
    child.add_command(Command("home", lambda args: None, usage="home", help="Home axes"))
    child.add_command(Command("where", lambda args: None, usage="where", help="Positions"))
    root = CommandGroup("root")
    root.add_command(Command("status", lambda args: None, usage="status", help="Show status"))
    root.add_child(child)
    return root


class TestRenderHelp:
    def test_lists_commands_and_namespaces(self):
        from fluid_control.cli.compose.repl import render_help

        text = render_help(_sample_root())
        assert "status" in text
        assert "gantry" in text
        assert "home" in text
        assert "quit" in text


class TestNamespaceCompleter:
    def test_completes_top_level(self):
        from prompt_toolkit.document import Document

        from fluid_control.cli.compose.repl import NamespaceCompleter

        completer = NamespaceCompleter(_sample_root())
        completions = [c.text for c in completer.get_completions(Document("stat"), None)]
        assert "status" in completions

    def test_completes_reserved_at_root(self):
        from prompt_toolkit.document import Document

        from fluid_control.cli.compose.repl import NamespaceCompleter

        completer = NamespaceCompleter(_sample_root())
        completions = [c.text for c in completer.get_completions(Document("he"), None)]
        assert "help" in completions

    def test_completes_nested_after_namespace(self):
        from prompt_toolkit.document import Document

        from fluid_control.cli.compose.repl import NamespaceCompleter

        completer = NamespaceCompleter(_sample_root())
        completions = [c.text for c in completer.get_completions(Document("gantry "), None)]
        assert "home" in completions
        assert "where" in completions

    def test_no_completions_past_a_command(self):
        from prompt_toolkit.document import Document

        from fluid_control.cli.compose.repl import NamespaceCompleter

        completer = NamespaceCompleter(_sample_root())
        completions = [c.text for c in completer.get_completions(Document("status "), None)]
        assert completions == []
