# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""Unit tests for the fluid-control command-group builders.

Covers [`build_group`][fluid_control.cli.commands.build_group] and
[`build_gantry_group`][fluid_control.cli.commands.build_gantry_group]: that dispatching a
command line routes to the correct
[`FluidControlSession`][fluid_control.cli.session.FluidControlSession] method with parsed
arguments, that the ``gantry`` child namespace is mounted only when a gantry is
configured, and that argument validation raises
[`UsageError`][fluid_control.cli.compose.core.UsageError].

The session is a [`MagicMock`][unittest.mock.MagicMock] so these tests isolate the
command-parsing/routing layer from session and hardware internals.
"""

from unittest.mock import MagicMock

import pytest

from fluid_control.cli.commands import build_gantry_group, build_group
from fluid_control.cli.compose.core import UnknownCommandError, UsageError


def _make_session(with_gantry: bool = True) -> MagicMock:
    """Return a MagicMock standing in for a FluidControlSession.

    Args:
        with_gantry: When ``False``, ``session.gantry`` is set to ``None`` so
            the gantry child namespace is not mounted.

    Returns:
        A configured [`MagicMock`][unittest.mock.MagicMock] session.
    """
    session = MagicMock()
    if not with_gantry:
        session.gantry = None
    session.get_liquid_classes.return_value = ["water"]
    session.get_channels.return_value = [1, 2]
    session.get_status.return_value = {"fluid_control_status": 0}
    session.valve_timed.return_value = [0, "ok"]
    session.direct.return_value = [0, "ok"]
    session.dispense.return_value = [0, "Dispense complete"]
    session.aspirate.return_value = [0, "Aspirate complete"]
    session.mix.return_value = [0, "Mix complete"]
    session.pickup_tips.return_value = [0, "ok"]
    session.eject_tips.return_value = [0, "ok"]
    session.where.return_value = {"Z": 0.0}
    session.move_axis.return_value = {"Z": 50.0}
    session.raise_arm.return_value = {"Z": 10.0}
    return session


class TestBuildGroupStructure:
    def test_registers_core_commands(self):
        group = build_group(_make_session())
        for name in ("valve", "direct", "dispense", "aspirate", "mix", "pressure", "status", "pickup", "eject"):
            assert name in group.commands

    def test_mounts_gantry_child_when_gantry_present(self):
        group = build_group(_make_session(with_gantry=True))
        assert "gantry" in group.children

    def test_no_gantry_child_when_gantry_absent(self):
        group = build_group(_make_session(with_gantry=False))
        assert "gantry" not in group.children

    def test_dispense_carries_liquid_class_completions(self):
        group = build_group(_make_session())
        assert group.commands["dispense"].completions is not None
        assert group.commands["dispense"].completions() == ["water"]


class TestFluidCommandDispatch:
    def test_valve_parses_and_calls(self):
        session = _make_session()
        build_group(session).dispatch(["valve", "1", "500", "70"])
        session.valve_timed.assert_called_once_with(1, 500, 70)

    def test_valve_default_pressure(self):
        session = _make_session()
        build_group(session).dispatch(["valve", "1", "500"])
        session.valve_timed.assert_called_once_with(1, 500, 0)

    def test_valve_missing_args_raises_usage(self):
        session = _make_session()
        with pytest.raises(UsageError):
            build_group(session).dispatch(["valve", "1"])

    def test_dispense_parses_types(self):
        session = _make_session()
        build_group(session).dispatch(["dispense", "1", "50", "water"])
        session.dispense.assert_called_once_with(1, 50.0, "water")

    def test_aspirate_parses_types(self):
        session = _make_session()
        build_group(session).dispatch(["aspirate", "2", "80", "water"])
        session.aspirate.assert_called_once_with(2, 80.0, "water")

    def test_mix_parses_cycles(self):
        session = _make_session()
        build_group(session).dispatch(["mix", "1", "60", "water", "3"])
        session.mix.assert_called_once_with(1, 60.0, "water", 3)

    def test_direct_parses_pairs_and_pressure(self):
        session = _make_session()
        build_group(session).dispatch(["direct", "1:500", "2:400", "pressure=70"])
        session.direct.assert_called_once_with({1: 500, 2: 400}, 70)

    def test_direct_rejects_bad_token(self):
        session = _make_session()
        with pytest.raises(UsageError):
            build_group(session).dispatch(["direct", "oops"])

    def test_direct_requires_pairs(self):
        session = _make_session()
        with pytest.raises(UsageError):
            build_group(session).dispatch(["direct", "pressure=70"])

    def test_pressure_sets_value(self):
        session = _make_session()
        build_group(session).dispatch(["pressure", "70"])
        session.set_pressure.assert_called_once_with(70)

    def test_pickup_parses_duration(self):
        session = _make_session()
        build_group(session).dispatch(["pickup", "0.5"])
        session.pickup_tips.assert_called_once_with(0.5)

    def test_eject_calls_session(self):
        session = _make_session()
        build_group(session).dispatch(["eject"])
        session.eject_tips.assert_called_once()

    def test_unknown_command_raises(self):
        session = _make_session()
        with pytest.raises(UnknownCommandError):
            build_group(session).dispatch(["frobnicate"])


class TestGantryCommandDispatch:
    def test_home_routes_through_namespace(self):
        session = _make_session()
        build_group(session).dispatch(["gantry", "home"])
        session.home.assert_called_once()

    def test_where_routes_through_namespace(self):
        session = _make_session()
        build_group(session).dispatch(["gantry", "where"])
        session.where.assert_called_once()

    def test_move_parses_axis_and_position(self):
        session = _make_session()
        build_group(session).dispatch(["gantry", "move", "z", "50", "15"])
        session.move_axis.assert_called_once_with("Z", 50.0, 15.0)

    def test_raise_uses_positive_delta(self):
        session = _make_session()
        build_group(session).dispatch(["gantry", "raise", "10"])
        session.raise_arm.assert_called_once_with(10.0, pytest.approx(10.0))

    def test_lower_negates_delta(self):
        session = _make_session()
        build_group(session).dispatch(["gantry", "lower", "10"])
        args = session.raise_arm.call_args[0]
        assert args[0] == pytest.approx(-10.0)

    def test_enable_and_disable(self):
        session = _make_session()
        group = build_group(session)
        group.dispatch(["gantry", "enable"])
        group.dispatch(["gantry", "disable"])
        session.enable_axes.assert_called_once()
        session.disable_axes.assert_called_once()

    def test_move_missing_args_raises_usage(self):
        session = _make_session()
        with pytest.raises(UsageError):
            build_group(session).dispatch(["gantry", "move", "Z"])


class TestBuildGantryGroup:
    def test_contains_motion_commands(self):
        group = build_gantry_group(_make_session())
        for name in ("move", "raise", "lower", "where", "home", "enable", "disable"):
            assert name in group.commands
