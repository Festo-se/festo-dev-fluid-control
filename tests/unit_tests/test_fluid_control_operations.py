"""Unit tests for fluid-control operations: dispense, aspirate, mix, get_status,
direct_command, eject_tips, pickup_tips.

All tests run without hardware — PGVA, VAEM, and ``sleep`` are mocked via the
``dispenser`` and ``pipettor_instance`` fixtures defined in ``conftest.py``.

Key mock invariants:
- ``pressure_control.set_output_pressure(pressure=X)`` updates shared state;
  ``get_output_pressure()`` returns that state, causing ``_wait_output_pressure``
  to resolve on its first poll iteration.
- ``valve_control.get_status()["Readiness"] == 0`` causes the dispense retry
  loop inside ``_handle_liquid`` to exit on the first call.
- ``sleep`` is a no-op so valve-timing waits are instantaneous.
"""

from unittest.mock import call

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _set_pressure_values(mock_pressure) -> list[int]:
    """Collect all values passed to set_output_pressure (handles both
    positional and keyword call forms used in production code)."""
    result = []
    for c in mock_pressure.set_output_pressure.call_args_list:
        result.append(c.args[0] if c.args else c.kwargs["pressure"])
    return result


# ---------------------------------------------------------------------------
# Dispense
# ---------------------------------------------------------------------------


class TestDispense:
    _DISPENSE_CMD = {1: {"volume": 100, "liquid_class": "water"}}

    def test_calls_set_output_pressure_with_calibration_pressure(self, dispenser):
        dispenser.dispense(self._DISPENSE_CMD)
        pressure_calls = [c.kwargs["pressure"] for c in dispenser.mock_pressure.set_output_pressure.call_args_list]
        assert 70 in pressure_calls

    def test_calls_set_output_pressure_with_zero_after_operation(self, dispenser):
        dispenser.dispense(self._DISPENSE_CMD)
        pressure_calls = [c.kwargs["pressure"] for c in dispenser.mock_pressure.set_output_pressure.call_args_list]
        assert 0 in pressure_calls

    def test_calls_select_valve_for_each_channel(self, dispenser):
        dispenser.dispense(self._DISPENSE_CMD)
        dispenser.mock_vaem.select_valve.assert_called_with(valve_id=1)

    def test_calls_set_valve_switching_time_for_each_channel(self, dispenser):
        dispenser.dispense(self._DISPENSE_CMD)
        dispenser.mock_vaem.set_valve_switching_time.assert_called()
        call_kwargs = dispenser.mock_vaem.set_valve_switching_time.call_args.kwargs
        assert call_kwargs["valve_id"] == 1

    def test_opening_time_is_int(self, dispenser):
        dispenser.dispense(self._DISPENSE_CMD)
        call_kwargs = dispenser.mock_vaem.set_valve_switching_time.call_args.kwargs
        assert isinstance(call_kwargs["opening_time"], int)

    def test_calls_open_selected_valves(self, dispenser):
        dispenser.dispense(self._DISPENSE_CMD)
        dispenser.mock_vaem.open_selected_valves.assert_called()

    def test_calls_deselect_valve_for_each_channel_after_operation(self, dispenser):
        dispenser.dispense(self._DISPENSE_CMD)
        dispenser.mock_vaem.deselect_valve.assert_any_call(1)

    def test_status_is_clear_after_success(self, dispenser):
        dispenser.dispense(self._DISPENSE_CMD)
        assert dispenser.fluid_control_status.code == 0

    def test_multi_channel_dispense_selects_all_channels(self, dispenser):
        cmd = {
            1: {"volume": 100, "liquid_class": "water"},
            2: {"volume": 150, "liquid_class": "water"},
        }
        dispenser.dispense(cmd)
        dispenser.mock_vaem.select_valve.assert_any_call(valve_id=1)
        dispenser.mock_vaem.select_valve.assert_any_call(valve_id=2)

    def test_multi_channel_deselects_all_channels(self, dispenser):
        cmd = {
            1: {"volume": 100, "liquid_class": "water"},
            2: {"volume": 150, "liquid_class": "water"},
        }
        dispenser.dispense(cmd)
        dispenser.mock_vaem.deselect_valve.assert_any_call(1)
        dispenser.mock_vaem.deselect_valve.assert_any_call(2)

    def test_get_status_called_on_valve_control_during_dispense(self, dispenser):
        initial_count = dispenser.mock_vaem.get_status.call_count
        dispenser.dispense(self._DISPENSE_CMD)
        assert dispenser.mock_vaem.get_status.call_count > initial_count

    def test_unknown_liquid_class_raises_value_error(self, dispenser):
        cmd = {1: {"volume": 100, "liquid_class": "lava"}}
        with pytest.raises(ValueError, match="not contained"):
            dispenser.dispense(cmd)

    def test_inactive_channel_raises_value_error(self, dispenser):
        cmd = {99: {"volume": 100, "liquid_class": "water"}}
        with pytest.raises(ValueError, match="active channel"):
            dispenser.dispense(cmd)

    def test_negative_volume_raises_value_error(self, dispenser):
        cmd = {1: {"volume": -1, "liquid_class": "water"}}
        with pytest.raises(ValueError, match="greater than or equal to zero"):
            dispenser.dispense(cmd)

    def test_opening_time_scales_with_volume(self, dispenser):
        """Larger volume must produce a larger opening time."""
        dispenser.dispense({1: {"volume": 50, "liquid_class": "water"}})
        time_50 = dispenser.mock_vaem.set_valve_switching_time.call_args.kwargs["opening_time"]

        dispenser.mock_vaem.reset_mock()

        dispenser.dispense({1: {"volume": 200, "liquid_class": "water"}})
        time_200 = dispenser.mock_vaem.set_valve_switching_time.call_args.kwargs["opening_time"]

        assert time_200 > time_50


# ---------------------------------------------------------------------------
# Aspirate (tested via Pipettor — Dispenser overrides aspirate to raise)
# ---------------------------------------------------------------------------


class TestAspirate:
    _ASPIRATE_CMD = {1: {"volume": 100, "liquid_class": "water"}}

    def test_calls_set_output_pressure_with_aspirate_pressure(self, pipettor_instance):
        pipettor_instance.aspirate(self._ASPIRATE_CMD)
        pressure_calls = [
            c.kwargs["pressure"]
            for c in pipettor_instance.mock_pressure.set_output_pressure.call_args_list
        ]
        assert -100 in pressure_calls

    def test_calls_select_valve_for_channel(self, pipettor_instance):
        pipettor_instance.aspirate(self._ASPIRATE_CMD)
        pipettor_instance.mock_vaem.select_valve.assert_called_with(valve_id=1)

    def test_calls_open_selected_valves(self, pipettor_instance):
        pipettor_instance.aspirate(self._ASPIRATE_CMD)
        pipettor_instance.mock_vaem.open_selected_valves.assert_called()

    def test_calls_deselect_valve_after_operation(self, pipettor_instance):
        pipettor_instance.aspirate(self._ASPIRATE_CMD)
        pipettor_instance.mock_vaem.deselect_valve.assert_any_call(1)

    def test_status_clear_after_success(self, pipettor_instance):
        pipettor_instance.aspirate(self._ASPIRATE_CMD)
        assert pipettor_instance.fluid_control_status.code == 0

    def test_aspirate_does_not_use_dispense_readiness_loop(self, pipettor_instance):
        """Aspirate path calls open_selected_valves exactly once (no retry loop)."""
        initial_count = pipettor_instance.mock_vaem.open_selected_valves.call_count
        pipettor_instance.aspirate(self._ASPIRATE_CMD)
        assert pipettor_instance.mock_vaem.open_selected_valves.call_count == initial_count + 1


# ---------------------------------------------------------------------------
# Mix
# ---------------------------------------------------------------------------


class TestMix:
    def test_raises_not_implemented_when_static(self, dispenser):
        assert dispenser.is_static is True
        with pytest.raises(NotImplementedError, match="not configured to mix"):
            dispenser.mix({1: {"volume": 100, "liquid_class": "water"}}, cycles=1)

    def test_raises_not_implemented_when_static_on_pipettor(self, pipettor_instance):
        assert pipettor_instance.is_static is True
        with pytest.raises(NotImplementedError, match="static"):
            pipettor_instance.mix({1: {"volume": 50, "liquid_class": "water"}}, cycles=2)


# ---------------------------------------------------------------------------
# get_status
# ---------------------------------------------------------------------------


class TestGetStatus:
    def test_returns_dict(self, dispenser):
        result = dispenser.get_status()
        assert isinstance(result, dict)

    def test_contains_exactly_three_keys(self, dispenser):
        result = dispenser.get_status()
        assert set(result.keys()) == {"pressure", "valve", "fluid_control_status"}

    def test_calls_get_status_word_on_pressure_control(self, dispenser):
        dispenser.get_status()
        dispenser.mock_pressure.get_status_word.assert_called()

    def test_calls_get_status_on_valve_control(self, dispenser):
        initial_count = dispenser.mock_vaem.get_status.call_count
        dispenser.get_status()
        assert dispenser.mock_vaem.get_status.call_count > initial_count

    def test_pgva_value_is_backend_return_value(self, dispenser):
        dispenser.mock_pressure.get_status_word.return_value = {"Status": "TestValue"}
        result = dispenser.get_status()
        assert result["pressure"] == {"Status": "TestValue"}

    def test_vaem_value_is_backend_return_value(self, dispenser):
        dispenser.mock_vaem.get_status.return_value = {"Readiness": 0, "TestKey": "TestVal"}
        result = dispenser.get_status()
        assert result["valve"]["TestKey"] == "TestVal"

    def test_pipettor_status_is_numeric_code(self, dispenser):
        result = dispenser.get_status()
        assert isinstance(result["fluid_control_status"], int)


# ---------------------------------------------------------------------------
# eject_tips / pickup_tips
# ---------------------------------------------------------------------------


class TestEjectTips:
    def test_raises_not_implemented_when_static(self, dispenser):
        assert dispenser.is_static is True
        with pytest.raises(NotImplementedError, match="cannot use tips"):
            dispenser.eject_tips()

    def test_raises_not_implemented_when_static_on_pipettor(self, pipettor_instance):
        with pytest.raises(NotImplementedError, match="static"):
            pipettor_instance.eject_tips()

    def test_returns_success_tuple(self, pipettor_with_arm):
        result = pipettor_with_arm.eject_tips()
        assert result == [0, "Tips ejected successfully"]

    def test_status_clear_after_success(self, pipettor_with_arm):
        pipettor_with_arm.eject_tips()
        assert pipettor_with_arm.fluid_control_status.code == 0

    def test_pressurizes_to_449_mbar_each_cycle(self, pipettor_with_arm):
        pipettor_with_arm.eject_tips()
        pressures = _set_pressure_values(pipettor_with_arm.mock_pressure)
        assert pressures.count(449) == 3  # once per cycle

    def test_depressurizes_to_minus_449_mbar_each_cycle(self, pipettor_with_arm):
        pipettor_with_arm.eject_tips()
        pressures = _set_pressure_values(pipettor_with_arm.mock_pressure)
        assert pressures.count(-449) == 3  # once per cycle

    def test_resets_pressure_to_zero_after_all_cycles(self, pipettor_with_arm):
        pipettor_with_arm.eject_tips()
        pressures = _set_pressure_values(pipettor_with_arm.mock_pressure)
        assert pressures[-1] == 0

    def test_triggers_actuation_valve_twelve_times(self, pipettor_with_arm):
        # 3 cycles × 4 trigger calls (10, 1000, 10, 2000) = 12
        pipettor_with_arm.eject_tips()
        assert pipettor_with_arm.mock_pressure.trigger_actuation_valve.call_count == 12


class TestPickupTips:
    def test_raises_not_implemented_when_static(self, dispenser):
        with pytest.raises(NotImplementedError, match="cannot use tips"):
            dispenser.pickup_tips(duration=0.5)

    def test_raises_not_implemented_when_static_on_pipettor(self, pipettor_instance):
        with pytest.raises(NotImplementedError, match="static"):
            pipettor_instance.pickup_tips(duration=0.5)

    def test_returns_success_tuple(self, pipettor_with_arm):
        result = pipettor_with_arm.pickup_tips(duration=0.5)
        assert result == [0, "Tips picked up successfully"]

    def test_status_clear_after_success(self, pipettor_with_arm):
        pipettor_with_arm.pickup_tips(duration=0.5)
        assert pipettor_with_arm.fluid_control_status.code == 0

    def test_jogs_arm_four_times_before_stall_exit(self, pipettor_with_arm):
        # TIP_RACK_POSITIONS = [0, 5000, 10000, 10300, 10500]
        # 2 large movements (no stall) + 2 small movements (stall count → 2 > 1 → exit)
        pipettor_with_arm.pickup_tips(duration=0.5)
        assert pipettor_with_arm.mock_arm.jog_task.call_count == 4

    def test_queries_position_five_times(self, pipettor_with_arm):
        # current_position() called once before the loop + once per iteration (4)
        pipettor_with_arm.pickup_tips(duration=0.5)
        assert pipettor_with_arm.mock_arm.current_position.call_count == 5

    def test_engages_after_descent_to_realistic_tip_rack_depth(self, pipettor_with_arm):
        # All 5 TIP_RACK_POSITIONS are consumed during pickup — one pre-loop
        # query plus one per jog iteration.  A further call raises StopIteration,
        # confirming the method traversed the full descent sequence.
        pipettor_with_arm.pickup_tips(duration=0.5)
        import pytest as _pytest
        with _pytest.raises(StopIteration):
            pipettor_with_arm.mock_arm.current_position()

    def test_jog_called_with_downward_direction(self, pipettor_with_arm):
        pipettor_with_arm.pickup_tips(duration=0.5)
        for call in pipettor_with_arm.mock_arm.jog_task.call_args_list:
            # jog_task(True, False, duration=<seconds>) — first positional arg is forward/down
            assert call.args[0] is True

    def test_acknowledges_faults_on_arm(self, pipettor_with_arm):
        pipettor_with_arm.pickup_tips(duration=0.5)
        assert pipettor_with_arm.mock_arm.acknowledge_faults.called

    def test_enables_powerstage_during_jog_loop(self, pipettor_with_arm):
        pipettor_with_arm.pickup_tips(duration=0.5)
        assert pipettor_with_arm.mock_arm.enable_powerstage.called


# ---------------------------------------------------------------------------
# direct_command
# ---------------------------------------------------------------------------


class TestDirectCommand:
    def _set_vaem_ready(self, dispenser):
        """Override Readiness to 1 so the direct_command while-loop exits."""
        dispenser.mock_vaem.get_status.return_value = {
            "Status": 1,
            "Error": 0,
            "Readiness": 1,  # 1 = ready  →  direct_command while-loop exits
            "OperatingMode": 1,
            **{f"Valve{i}": 0 for i in range(1, 9)},
        }

    def test_calls_select_valve(self, dispenser):
        self._set_vaem_ready(dispenser)
        dispenser.direct_command({1: 100}, pressure=50)
        dispenser.mock_vaem.select_valve.assert_any_call(valve_id=1)

    def test_calls_set_valve_switching_time(self, dispenser):
        self._set_vaem_ready(dispenser)
        dispenser.direct_command({1: 100}, pressure=50)
        dispenser.mock_vaem.set_valve_switching_time.assert_any_call(valve_id=1, opening_time=100)

    def test_calls_open_selected_valves(self, dispenser):
        self._set_vaem_ready(dispenser)
        dispenser.direct_command({1: 100}, pressure=50)
        dispenser.mock_vaem.open_selected_valves.assert_called()

    def test_calls_set_output_pressure_with_requested_pressure(self, dispenser):
        self._set_vaem_ready(dispenser)
        dispenser.direct_command({1: 100}, pressure=50)
        pressure_calls = [
            c.kwargs["pressure"]
            for c in dispenser.mock_pressure.set_output_pressure.call_args_list
        ]
        assert 50 in pressure_calls

    def test_returns_success_tuple_with_valid_inputs(self, dispenser):
        """``direct_command`` with valid channel/pressure inputs returns status 0
        and the success message string."""
        self._set_vaem_ready(dispenser)
        result = dispenser.direct_command({1: 100}, pressure=50)
        assert result == [0, "Direct command executed successfully"]

    def test_deselects_all_channels_after_operation(self, dispenser):
        self._set_vaem_ready(dispenser)
        dispenser.direct_command({1: 100, 2: 200}, pressure=50)
        dispenser.mock_vaem.deselect_valve.assert_any_call(1)
        dispenser.mock_vaem.deselect_valve.assert_any_call(2)

    def test_sets_pressure_to_negative_one_after_valves_open(self, dispenser):
        self._set_vaem_ready(dispenser)
        dispenser.direct_command({1: 100}, pressure=50)
        pressure_calls = [
            c.kwargs["pressure"]
            for c in dispenser.mock_pressure.set_output_pressure.call_args_list
        ]
        assert -1 in pressure_calls

    def test_invalid_channel_returns_error_tuple(self, dispenser):
        self._set_vaem_ready(dispenser)
        result = dispenser.direct_command({99: 100}, pressure=50)
        assert result[0] == 1
        assert isinstance(result[1], str)

    def test_invalid_opening_time_returns_error_tuple(self, dispenser):
        self._set_vaem_ready(dispenser)
        result = dispenser.direct_command({1: 0}, pressure=50)
        assert result[0] == 1
        assert isinstance(result[1], str)


# ---------------------------------------------------------------------------
# PressureOverLiquidControl dunder methods / protocols
# ---------------------------------------------------------------------------


class TestPressureOverLiquidControlRepr:
    def test_repr_is_string(self, dispenser):
        assert isinstance(repr(dispenser), str)

    def test_repr_contains_class_name(self, dispenser):
        assert "Dispenser" in repr(dispenser)

    def test_repr_contains_component_type(self, dispenser):
        assert "dispenser" in repr(dispenser)



class TestPressureOverLiquidControlLen:
    def test_len_equals_channel_count(self, dispenser):
        assert len(dispenser) == dispenser.channel_count

    def test_len_dispenser_is_two(self, dispenser):
        assert len(dispenser) == 2

    def test_len_pipettor_is_eight(self, pipettor_instance):
        assert len(pipettor_instance) == 8


class TestPressureOverLiquidControlIter:
    def test_iter_yields_active_channels(self, dispenser):
        assert list(dispenser) == dispenser.active_channels

    def test_iter_count_matches_active_valve_count(self, dispenser):
        assert len(list(dispenser)) == dispenser.active_valve_count

    def test_iter_pipettor_yields_all_eight_channels(self, pipettor_instance):
        assert list(pipettor_instance) == list(range(1, 9))


class TestPressureOverLiquidControlContains:
    def test_active_channel_is_contained(self, dispenser):
        for ch in dispenser.active_channels:
            assert ch in dispenser

    def test_inactive_channel_not_contained(self, dispenser):
        assert 99 not in dispenser

    def test_zero_not_contained(self, dispenser):
        assert 0 not in dispenser


class TestPressureOverLiquidControlEquality:
    def test_equal_to_itself(self, dispenser):
        assert dispenser == dispenser

    def test_not_equal_to_different_component_type(self, dispenser, pipettor_instance):
        assert dispenser != pipettor_instance

    def test_returns_not_implemented_for_non_fluid_control(self, dispenser):
        result = dispenser.__eq__("not-a-fluid-control")
        assert result is NotImplemented


class TestPressureOverLiquidControlHash:
    def test_hash_returns_int(self, dispenser):
        assert isinstance(hash(dispenser), int)

    def test_usable_as_dict_key(self, dispenser):
        d = {dispenser: "value"}
        assert d[dispenser] == "value"

    def test_same_config_same_hash(self, mocker, dispenser_config):
        # Build two independent instances from identical config
        from unittest.mock import MagicMock
        from fluid_control import Dispenser

        def _make_instances():
            state = {"pressure": 0}
            mock_pressure = MagicMock()
            mock_pressure.set_output_pressure.side_effect = lambda pressure: state.update({"pressure": pressure})
            mock_pressure.get_output_pressure.side_effect = lambda: state["pressure"]
            mock_vaem = MagicMock()
            mock_vaem.get_status.return_value = {"Readiness": 0, **{f"Valve{i}": 0 for i in range(1, 9)}}
            mocker.patch("fluid_control.fluid_control.PGVA", return_value=mock_pressure)
            mocker.patch("fluid_control.fluid_control.VAEM", return_value=mock_vaem)
            mocker.patch("fluid_control.fluid_control.sleep")
            return Dispenser(config=dispenser_config)

        d1 = _make_instances()
        d2 = _make_instances()
        assert hash(d1) == hash(d2)


class TestPressureOverLiquidControlContextManager:
    def test_enter_returns_self(self, dispenser):
        result = dispenser.__enter__()
        assert result is dispenser

    def test_context_manager_enter_returns_self(self, dispenser):
        with dispenser as d:
            assert d is dispenser

    def test_exit_sets_pressure_to_zero(self, dispenser):
        with dispenser:
            pass
        pressure_calls = _set_pressure_values(dispenser.mock_pressure)
        assert pressure_calls[-1] == 0

    def test_exit_deselects_all_channels(self, dispenser):
        with dispenser:
            pass
        for ch in range(1, dispenser.channel_count + 1):
            dispenser.mock_vaem.deselect_valve.assert_any_call(valve_id=ch)

    def test_exit_clears_status(self, dispenser):
        dispenser.fluid_control_status.set_error()
        with dispenser:
            pass
        assert dispenser.fluid_control_status.code == 0

    def test_exit_returns_false(self, dispenser):
        result = dispenser.__exit__(None, None, None)
        assert result is False

    def test_exit_does_not_suppress_exceptions(self, dispenser):
        with pytest.raises(ValueError):
            with dispenser:
                raise ValueError("test error")


class TestWaitValveControlReady:
    def test_exits_when_readiness_is_truthy(self, dispenser):
        """_wait_valve_control_ready polls get_status until Readiness is truthy."""
        dispenser.mock_vaem.get_status.return_value = {
            "Status": 1,
            "Error": 0,
            "Readiness": 1,
            "OperatingMode": 1,
            **{f"Valve{i}": 0 for i in range(1, 9)},
        }
        dispenser._wait_valve_control_ready()  # must not block
        dispenser.mock_vaem.get_status.assert_called()

    def test_polls_get_status_at_least_once(self, dispenser):
        dispenser.mock_vaem.get_status.return_value = {
            "Status": 1,
            "Error": 0,
            "Readiness": 1,
            "OperatingMode": 1,
            **{f"Valve{i}": 0 for i in range(1, 9)},
        }
        initial = dispenser.mock_vaem.get_status.call_count
        dispenser._wait_valve_control_ready()
        assert dispenser.mock_vaem.get_status.call_count > initial

