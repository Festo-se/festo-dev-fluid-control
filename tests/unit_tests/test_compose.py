# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""Unit tests for the composable command-registry core.

Covers [`Command`][fluid_control.cli.compose.core.Command] and
[`CommandGroup`][fluid_control.cli.compose.core.CommandGroup]: dispatch to local
commands, hierarchical routing into child groups, path discovery, help
formatting, dunder behaviour, and the error contract.  These tests exercise the
dependency-free core only and do not require ``prompt_toolkit`` or ``rich``.
"""

import pytest

from fluid_control.cli.compose.core import (
    Command,
    CommandGroup,
    UnknownCommandError,
    UsageError,
)


def _record(sink: list) -> "callable":
    """Return a handler that appends its received args to *sink*."""

    def handler(args):
        sink.append(list(args))

    return handler


class TestCommand:
    def test_repr_is_stable(self):
        cmd = Command("home", lambda args: None)
        assert repr(cmd) == "Command(name='home')"

    def test_defaults(self):
        cmd = Command("home", lambda args: None)
        assert cmd.usage == ""
        assert cmd.help == ""
        assert cmd.completions is None


class TestAddAndDispatch:
    def test_dispatch_calls_local_command_with_args(self):
        sink: list = []
        group = CommandGroup("root")
        group.add_command(Command("dispense", _record(sink)))
        group.dispatch(["dispense", "1", "50", "water"])
        assert sink == [["1", "50", "water"]]

    def test_dispatch_is_case_insensitive(self):
        sink: list = []
        group = CommandGroup("root")
        group.add_command(Command("Home", _record(sink)))
        group.dispatch(["HOME"])
        assert sink == [[]]

    def test_empty_tokens_is_noop(self):
        group = CommandGroup("root")
        group.dispatch([])  # must not raise

    def test_unknown_command_raises(self):
        group = CommandGroup("root")
        with pytest.raises(UnknownCommandError, match="frobnicate"):
            group.dispatch(["frobnicate"])

    def test_handler_usage_error_propagates(self):
        def handler(args):
            raise UsageError("Usage: x")

        group = CommandGroup("root")
        group.add_command(Command("x", handler))
        with pytest.raises(UsageError):
            group.dispatch(["x"])

    def test_add_command_returns_command(self):
        group = CommandGroup("root")
        cmd = Command("x", lambda args: None)
        assert group.add_command(cmd) is cmd


class TestHierarchicalRouting:
    def test_routes_into_child_group(self):
        sink: list = []
        child = CommandGroup("gantry")
        child.add_command(Command("home", _record(sink)))
        root = CommandGroup("root")
        root.add_child(child)
        root.dispatch(["gantry", "home"])
        assert sink == [[]]

    def test_child_args_passed_through(self):
        sink: list = []
        child = CommandGroup("gantry")
        child.add_command(Command("move", _record(sink)))
        root = CommandGroup("root")
        root.add_child(child)
        root.dispatch(["gantry", "move", "Z", "50"])
        assert sink == [["Z", "50"]]

    def test_add_child_custom_name(self):
        child = CommandGroup("fluid")
        root = CommandGroup("root")
        root.add_child(child, name="pipettor")
        assert "pipettor" in root.children
        assert "fluid" not in root.children

    def test_child_shadows_like_named_command(self):
        child_sink: list = []
        cmd_sink: list = []
        child = CommandGroup("status")
        child.add_command(Command("show", _record(child_sink)))
        root = CommandGroup("root")
        root.add_command(Command("status", _record(cmd_sink)))
        root.add_child(child)
        root.dispatch(["status", "show"])
        assert child_sink == [[]]
        assert cmd_sink == []

    def test_unknown_child_command_raises(self):
        child = CommandGroup("gantry")
        root = CommandGroup("root")
        root.add_child(child)
        with pytest.raises(UnknownCommandError):
            root.dispatch(["gantry", "nope"])


class TestDiscovery:
    def test_iter_paths_lists_namespaced_commands(self):
        child = CommandGroup("gantry")
        child.add_command(Command("home", lambda args: None))
        child.add_command(Command("where", lambda args: None))
        root = CommandGroup("root")
        root.add_command(Command("status", lambda args: None))
        root.add_child(child)
        paths = set(root.iter_paths())
        assert ("status",) in paths
        assert ("gantry", "home") in paths
        assert ("gantry", "where") in paths

    def test_format_help_indents_children(self):
        child = CommandGroup("gantry", help="Motion")
        child.add_command(Command("home", lambda args: None, usage="home", help="Home axes"))
        root = CommandGroup("root")
        root.add_command(Command("status", lambda args: None, usage="status", help="Show status"))
        root.add_child(child)
        lines = root.format_help()
        assert any(line.startswith("status") for line in lines)
        assert any(line.startswith("gantry") for line in lines)
        assert any(line.startswith("  home") for line in lines)


class TestDunders:
    def test_contains_matches_commands_and_children(self):
        child = CommandGroup("gantry")
        root = CommandGroup("root")
        root.add_command(Command("status", lambda args: None))
        root.add_child(child)
        assert "status" in root
        assert "gantry" in root
        assert "GANTRY" in root
        assert "missing" not in root
        assert 123 not in root

    def test_len_counts_commands_plus_children(self):
        child = CommandGroup("gantry")
        root = CommandGroup("root")
        root.add_command(Command("a", lambda args: None))
        root.add_command(Command("b", lambda args: None))
        root.add_child(child)
        assert len(root) == 3

    def test_repr_reports_counts(self):
        root = CommandGroup("fluid")
        root.add_command(Command("a", lambda args: None))
        assert repr(root) == "CommandGroup(name='fluid', commands=1, children=0)"
