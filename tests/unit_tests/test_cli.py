"""Unit tests for [`FluidControlSession`][fluid_control.cli.session.FluidControlSession].

Every public method on ``FluidControlSession`` is tested here.  All hardware
dependencies (PGVA, VAEM, Gantry axes) are replaced by ``MagicMock`` objects.
``_build_completer`` and ``_print_result`` (from the REPL module) are only
tested when ``prompt_toolkit`` and ``rich`` are importable.
"""

from collections import deque
from unittest.mock import MagicMock
import importlib
import importlib.util

import pytest

from fluid_control.cli.session import FluidControlSession, _TOP_LEVEL_CMDS
from fluid_control import Dispenser, Pipettor
from fluid_control.fluid_control import OperationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_gantry(axis_names: list[str] | None = None) -> MagicMock:
    """Return a MagicMock that looks like a [`Gantry`][applied_motion.applied_motion.Gantry].

    Args:
        axis_names: Names to populate ``gantry.axes`` with.  Defaults to
            ``["X", "Y", "Z"]``.

    Returns:
        Configured [`MagicMock`][unittest.mock.MagicMock] gantry stub.
    """
    if axis_names is None:
        axis_names = ["X", "Y", "Z"]
    gantry = MagicMock()
    gantry.axes = {name: MagicMock() for name in axis_names}
    gantry.get_location.return_value = {name: 0.0 for name in axis_names}
    return gantry


# ---------------------------------------------------------------------------
# FluidControlSession construction
# ---------------------------------------------------------------------------


class TestFluidControlSessionInit:
    def test_stores_component(self, dispenser):
        session = FluidControlSession(dispenser)
        assert session.component is dispenser

    def test_gantry_defaults_to_none(self, dispenser):
        session = FluidControlSession(dispenser)
        assert session.gantry is None

    def test_mount_axis_name_defaults_to_z(self, dispenser):
        session = FluidControlSession(dispenser)
        assert session.mount_axis_name == "Z"

    def test_custom_gantry_and_axis_stored(self, dispenser):
        gantry = _make_mock_gantry()
        session = FluidControlSession(dispenser, gantry=gantry, mount_axis_name="W")
        assert session.gantry is gantry
        assert session.mount_axis_name == "W"


# ---------------------------------------------------------------------------
# Valve / pressure operations
# ---------------------------------------------------------------------------


class TestValveTimed:
    def test_calls_direct_command_correctly(self, dispenser):
        session = FluidControlSession(dispenser)
        dispenser.direct_command = MagicMock(return_value=[0, "Direct command executed successfully"])
        result = session.valve_timed(channel=1, time_ms=500, pressure=70)
        dispenser.direct_command.assert_called_once_with(channel_times={1: 500}, pressure=70)
        assert result[0] == 0

    def test_default_pressure_is_zero(self, dispenser):
        session = FluidControlSession(dispenser)
        dispenser.direct_command = MagicMock(return_value=[0, "ok"])
        session.valve_timed(channel=1, time_ms=200)
        dispenser.direct_command.assert_called_once_with(channel_times={1: 200}, pressure=0)

    def test_returns_result_list(self, dispenser):
        session = FluidControlSession(dispenser)
        dispenser.direct_command = MagicMock(return_value=[0, "Direct command executed successfully"])
        result = session.valve_timed(1, 100, 50)
        assert isinstance(result, list)
        assert len(result) == 2


class TestDirect:
    def test_passes_channel_times_and_pressure(self, dispenser):
        session = FluidControlSession(dispenser)
        dispenser.direct_command = MagicMock(return_value=[0, "ok"])
        session.direct({1: 300, 2: 400}, pressure=80)
        dispenser.direct_command.assert_called_once_with(channel_times={1: 300, 2: 400}, pressure=80)

    def test_returns_result_from_direct_command(self, dispenser):
        session = FluidControlSession(dispenser)
        dispenser.direct_command = MagicMock(return_value=[0, "Direct command executed successfully"])
        result = session.direct({1: 300}, pressure=70)
        assert result[0] == 0


class TestDispense:
    def test_calls_component_dispense_with_correct_dict(self, dispenser):
        session = FluidControlSession(dispenser)
        dispenser.dispense = MagicMock()
        session.dispense(channel=1, volume_ul=100.0, liquid_class="water")
        dispenser.dispense.assert_called_once_with({1: {"volume": 100.0, "liquid_class": "water"}})

    def test_returns_status_and_message(self, dispenser):
        session = FluidControlSession(dispenser)
        dispenser.dispense = MagicMock()
        result = session.dispense(1, 50.0, "water")
        assert isinstance(result, OperationResult)
        assert len(result) == 2
        assert result[1] == "Dispense complete"


class TestAspirate:
    def test_calls_component_aspirate_with_correct_dict(self, pipettor_instance):
        session = FluidControlSession(pipettor_instance)
        pipettor_instance.aspirate = MagicMock()
        session.aspirate(channel=1, volume_ul=80.0, liquid_class="water")
        pipettor_instance.aspirate.assert_called_once_with({1: {"volume": 80.0, "liquid_class": "water"}})

    def test_raises_not_implemented_for_dispenser(self, dispenser):
        session = FluidControlSession(dispenser)
        with pytest.raises(NotImplementedError):
            session.aspirate(1, 50.0, "water")


class TestMix:
    def test_calls_component_mix_with_correct_args(self, pipettor_with_arm):
        session = FluidControlSession(pipettor_with_arm)
        pipettor_with_arm.mix = MagicMock()
        session.mix(channel=1, volume_ul=60.0, liquid_class="water", cycles=3)
        pipettor_with_arm.mix.assert_called_once_with({1: {"volume": 60.0, "liquid_class": "water"}}, 3)

    def test_returns_cycle_count_in_message(self, pipettor_with_arm):
        session = FluidControlSession(pipettor_with_arm)
        pipettor_with_arm.mix = MagicMock()
        result = session.mix(1, 60.0, "water", 5)
        assert "5" in result[1]


class TestSetPressure:
    def test_calls_wait_output_pressure(self, dispenser):
        session = FluidControlSession(dispenser)
        dispenser._wait_output_pressure = MagicMock()
        session.set_pressure(70)
        dispenser._wait_output_pressure.assert_called_once_with(70)


# ---------------------------------------------------------------------------
# Gantry / axis operations
# ---------------------------------------------------------------------------


class TestRequireGantry:
    def test_raises_runtime_error_when_no_gantry(self, dispenser):
        session = FluidControlSession(dispenser)
        with pytest.raises(AttributeError, match="No gantry configured"):
            session.where()

    def test_decorated_method_proceeds_when_gantry_configured(self, dispenser):
        gantry = _make_mock_gantry(["Z"])
        gantry.get_location.return_value = {"Z": 0.0}
        session = FluidControlSession(dispenser, gantry=gantry)
        assert session.where() == {"Z": 0.0}


class TestMoveAxis:
    def test_calls_move_to_with_correct_deque(self, dispenser):
        gantry = _make_mock_gantry(["X", "Y", "Z"])
        session = FluidControlSession(dispenser, gantry=gantry, mount_axis_name="Z")
        session.move_axis("Z", 50.0, 15.0)
        gantry.move_to.assert_called_once()
        call_args = gantry.move_to.call_args
        movements: deque = call_args[0][0]
        assert len(movements) == 1
        item = movements[0]
        assert item == {"Z": {"position": 50.0, "velocity": 15.0}}

    def test_returns_gantry_location(self, dispenser):
        gantry = _make_mock_gantry(["Z"])
        gantry.get_location.return_value = {"Z": 50.0}
        session = FluidControlSession(dispenser, gantry=gantry)
        loc = session.move_axis("Z", 50.0)
        assert loc == {"Z": 50.0}

    def test_raises_when_no_gantry(self, dispenser):
        session = FluidControlSession(dispenser)
        with pytest.raises(AttributeError):
            session.move_axis("Z", 50.0)


class TestRaiseArm:
    def test_delegates_to_move_axis_with_mount_axis(self, dispenser):
        gantry = _make_mock_gantry(["Z"])
        gantry.get_location.return_value = {"Z": 20.0}
        session = FluidControlSession(dispenser, gantry=gantry, mount_axis_name="Z")
        session.raise_arm(10.0, 5.0)
        gantry.move_to.assert_called_once()
        movements: deque = gantry.move_to.call_args[0][0]
        assert movements[0] == {"Z": {"position": 30.0, "velocity": 5.0}}

    def test_lower_moves_in_negative_direction(self, dispenser):
        gantry = _make_mock_gantry(["Z"])
        gantry.get_location.return_value = {"Z": 40.0}
        session = FluidControlSession(dispenser, gantry=gantry, mount_axis_name="Z")
        session.raise_arm(-10.0)  # negative delta = lower
        movements: deque = gantry.move_to.call_args[0][0]
        assert movements[0]["Z"]["position"] == pytest.approx(30.0)

    def test_default_velocity_is_ten(self, dispenser):
        gantry = _make_mock_gantry(["Z"])
        gantry.get_location.return_value = {"Z": 0.0}
        session = FluidControlSession(dispenser, gantry=gantry)
        session.raise_arm(10.0)
        movements: deque = gantry.move_to.call_args[0][0]
        assert movements[0]["Z"]["velocity"] == 10.0


class TestWhere:
    def test_returns_gantry_location(self, dispenser):
        gantry = _make_mock_gantry(["X", "Y", "Z"])
        gantry.get_location.return_value = {"X": 1.0, "Y": 2.0, "Z": 3.0}
        session = FluidControlSession(dispenser, gantry=gantry)
        loc = session.where()
        assert loc == {"X": 1.0, "Y": 2.0, "Z": 3.0}

    def test_raises_when_no_gantry(self, dispenser):
        session = FluidControlSession(dispenser)
        with pytest.raises(AttributeError):
            session.where()


class TestHome:
    def test_calls_gantry_home(self, dispenser):
        gantry = _make_mock_gantry()
        session = FluidControlSession(dispenser, gantry=gantry)
        session.home()
        gantry.home.assert_called_once()

    def test_raises_when_no_gantry(self, dispenser):
        session = FluidControlSession(dispenser)
        with pytest.raises(AttributeError):
            session.home()


class TestEnableDisableAxes:
    def test_enable_calls_internal_method(self, dispenser):
        session = FluidControlSession(dispenser)
        dispenser._enable_lateral_axes = MagicMock()
        session.enable_axes()
        dispenser._enable_lateral_axes.assert_called_once()

    def test_disable_calls_internal_method(self, dispenser):
        session = FluidControlSession(dispenser)
        dispenser._disable_lateral_axes = MagicMock()
        session.disable_axes()
        dispenser._disable_lateral_axes.assert_called_once()

    def test_enable_raises_not_implemented_for_static(self, dispenser):
        """Static dispenser has no axes — should propagate NotImplementedError."""
        session = FluidControlSession(dispenser)
        # Restore real method to confirm static check fires
        dispenser._enable_lateral_axes = Dispenser._enable_lateral_axes.__get__(dispenser, type(dispenser))
        with pytest.raises(NotImplementedError):
            session.enable_axes()

    def test_disable_raises_not_implemented_for_static(self, dispenser):
        session = FluidControlSession(dispenser)
        dispenser._disable_lateral_axes = Dispenser._disable_lateral_axes.__get__(dispenser, type(dispenser))
        with pytest.raises(NotImplementedError):
            session.disable_axes()


# ---------------------------------------------------------------------------
# Tip operations
# ---------------------------------------------------------------------------


class TestPickupTips:
    def test_calls_component_pickup_tips(self, pipettor_with_arm):
        session = FluidControlSession(pipettor_with_arm)
        pipettor_with_arm.pickup_tips = MagicMock(return_value=[0, "Tips picked up successfully"])
        result = session.pickup_tips(0.5)
        pipettor_with_arm.pickup_tips.assert_called_once_with(0.5)
        assert result[0] == 0

    def test_raises_not_implemented_for_static_dispenser(self, dispenser):
        session = FluidControlSession(dispenser)
        with pytest.raises(NotImplementedError):
            session.pickup_tips(0.5)


class TestEjectTips:
    def test_calls_component_eject_tips(self, pipettor_with_arm):
        session = FluidControlSession(pipettor_with_arm)
        pipettor_with_arm.eject_tips = MagicMock(return_value=[0, "Tips ejected successfully"])
        result = session.eject_tips()
        pipettor_with_arm.eject_tips.assert_called_once()
        assert result[0] == 0

    def test_raises_not_implemented_for_dispenser(self, dispenser):
        session = FluidControlSession(dispenser)
        with pytest.raises(NotImplementedError):
            session.eject_tips()


# ---------------------------------------------------------------------------
# Introspection
# ---------------------------------------------------------------------------


class TestGetStatus:
    def test_delegates_to_component_get_status(self, dispenser):
        session = FluidControlSession(dispenser)
        dispenser.get_status = MagicMock(return_value={"fluid_control_status": 0})
        status = session.get_status()
        dispenser.get_status.assert_called_once()
        assert "fluid_control_status" in status


class TestGetLiquidClasses:
    def test_returns_list_of_strings(self, dispenser):
        session = FluidControlSession(dispenser)
        classes = session.get_liquid_classes()
        assert isinstance(classes, list)
        assert "water" in classes

    def test_returns_all_configured_classes(self, pipettor_instance):
        session = FluidControlSession(pipettor_instance)
        classes = session.get_liquid_classes()
        assert len(classes) >= 1


class TestGetChannels:
    def test_returns_active_channel_list(self, dispenser):
        session = FluidControlSession(dispenser)
        channels = session.get_channels()
        assert isinstance(channels, list)
        assert 1 in channels
        assert 2 in channels

    def test_returns_all_eight_for_pipettor(self, pipettor_instance):
        session = FluidControlSession(pipettor_instance)
        channels = session.get_channels()
        assert len(channels) == 8
        assert list(range(1, 9)) == sorted(channels)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


class TestBuildCompleter:
    """Tests for _build_completer — skipped when prompt_toolkit is not installed."""

    @pytest.fixture(autouse=True)
    def _require_prompt_toolkit(self):
        """Skip this class entirely if prompt_toolkit is not importable."""
        if importlib.util.find_spec("prompt_toolkit") is None:
            pytest.skip("prompt_toolkit not installed — skipping completer tests")

    def test_includes_all_top_level_commands(self):
        from fluid_control.cli.cli import _build_completer

        completer = _build_completer([])
        for cmd in _TOP_LEVEL_CMDS:
            assert cmd in completer.words

    def test_includes_axis_names(self):
        from fluid_control.cli.cli import _build_completer

        completer = _build_completer(["X", "Y", "Z"])
        assert "X" in completer.words
        assert "Y" in completer.words
        assert "Z" in completer.words

    def test_empty_axis_names_does_not_crash(self):
        from fluid_control.cli.cli import _build_completer

        completer = _build_completer([])
        assert completer is not None


class TestPrintResult:
    """Tests for _print_result — skipped when rich is not installed."""

    @pytest.fixture(autouse=True)
    def _require_rich(self):
        if importlib.util.find_spec("rich") is None:
            pytest.skip("rich not installed — skipping _print_result tests")

    def test_does_not_raise_for_success(self, capsys):
        from fluid_control.cli.render import print_result

        print_result([0, "All done"])

    def test_does_not_raise_for_error(self, capsys):
        from fluid_control.cli.render import print_result

        print_result([1, "Something failed"])

    def test_does_not_raise_for_busy(self, capsys):
        from fluid_control.cli.render import print_result

        print_result([2, "Still running"])

    def test_handles_empty_list(self, capsys):
        from fluid_control.cli.render import print_result

        print_result([])

    def test_handles_result_with_no_message(self, capsys):
        from fluid_control.cli.render import print_result

        print_result([0])
