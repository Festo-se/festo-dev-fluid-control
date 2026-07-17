"""Tests that exercise the real test-config.json calibration data.

These tests use the actual coefficients from the test deployment config
to ensure calibration math, liquid-class loading, and dispense/aspirate
operations behave correctly with production data.  PGVA, VAEM, and ``sleep``
are still mocked — no hardware required.

test-config.json topology recap
----------------------------------
dispenser component
    channels        : 1, 2  (active_valve_terminals [1, 2])
    channel-count   : 2
    liquid classes  : water, ethylene-glycol10%, third-liquid-class
    processes       : dispense only  (no aspirate calibration)
    pressures       : 70 mbar for all dispense classes

pipettor component
    channels        : 1-8  (active_valve_terminals [1..8])
    channel-count   : 8
    calibration keys: "1"-"8"  (channel-index offset from terminal IDs)
    liquid classes  : water, ethylene-glycol10%
    processes       : dispense + aspirate
    pressures       : dispense 70 mbar, aspirate -100 mbar
"""

import json
from pathlib import Path

import pytest

from fluid_control import Dispenser, Pipettor
from fluid_control.fluid_control import PressureOverLiquidControl

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# Config file existence and structure
# ---------------------------------------------------------------------------


class TestTestConfigFile:
    def test_fixture_file_exists(self):
        assert (FIXTURES_DIR / "test-config.json").is_file()

    def test_fixture_file_is_valid_json(self):
        with (FIXTURES_DIR / "test-config.json").open() as fh:
            data = json.load(fh)
        assert isinstance(data, dict)

    def test_component_config_key_present(self, test_config):
        assert "component_config" in test_config

    def test_dispenser_component_present(self, test_config):
        assert any(
            v.get("component_class") == "dispenser"
            for v in test_config["component_config"]["components"].values()
        )

    def test_pipettor_component_present(self, test_config):
        assert any(
            v.get("component_class") == "pipettor"
            for v in test_config["component_config"]["components"].values()
        )


# ---------------------------------------------------------------------------
# test dispenser — initialization
# ---------------------------------------------------------------------------


class TestTestDispenserInit:
    def test_creates_dispenser_instance(self, test_dispenser):
        assert isinstance(test_dispenser, Dispenser)

    def test_channel_count_is_two(self, test_dispenser):
        assert test_dispenser.channel_count == 2

    def test_active_channels_are_one_and_two(self, test_dispenser):
        assert test_dispenser.active_channels == [1, 2]

    def test_active_valve_count_is_two(self, test_dispenser):
        assert test_dispenser.active_valve_count == 2

    def test_pgva_ip_from_config(self, test_dispenser):
        assert test_dispenser.pressure_control_config.ip == "192.168.10.102"

    def test_vaem_ip_from_config(self, test_dispenser):
        assert test_dispenser.valve_control_config.ip == "192.168.10.27"

    def test_pgva_port_from_config(self, test_dispenser):
        assert test_dispenser.pressure_control_config.port == 502

    def test_vaem_port_from_config(self, test_dispenser):
        assert test_dispenser.valve_control_config.port == 502


# ---------------------------------------------------------------------------
# test dispenser — liquid classes and calibration
# ---------------------------------------------------------------------------


TEST_DISPENSER_LIQUID_CLASSES = ["water", "ethylene-glycol10%", "third-liquid-class"]


class TestTestDispenserLiquidClasses:
    def test_all_three_liquid_classes_present(self, test_dispenser):
        assert set(test_dispenser.get_liquid_classes()) == set(TEST_DISPENSER_LIQUID_CLASSES)

    @pytest.mark.parametrize("liquid_class", TEST_DISPENSER_LIQUID_CLASSES)
    def test_pressures_populated_for_each_class(self, test_dispenser, liquid_class):
        assert liquid_class in test_dispenser.pressures

    @pytest.mark.parametrize("liquid_class", TEST_DISPENSER_LIQUID_CLASSES)
    def test_dispense_pressure_is_70_mbar(self, test_dispenser, liquid_class):
        assert test_dispenser.pressures[liquid_class]["dispense"] == 70

    @pytest.mark.parametrize("liquid_class", TEST_DISPENSER_LIQUID_CLASSES)
    def test_timing_functions_exist_for_both_channels(self, test_dispenser, liquid_class):
        for ch in ["1", "2"]:
            entry = test_dispenser.valve_control_timing_functions[liquid_class]["dispense"][ch]
            assert callable(entry["slope"])
            assert callable(entry["intercept"])

    def test_water_dispense_flow_offset_ch1(self, test_dispenser):
        # flow_coefficients["1"]["flow_offset"] = 0.826181241, channel_index_coeff=0
        # → slope is constant 0.826181241 regardless of active_channels
        slope_fn = test_dispenser.valve_control_timing_functions["water"]["dispense"]["1"]["slope"]
        assert slope_fn(1) == pytest.approx(0.826181241)
        assert slope_fn(8) == pytest.approx(0.826181241)

    def test_water_dispense_flow_offset_ch2(self, test_dispenser):
        slope_fn = test_dispenser.valve_control_timing_functions["water"]["dispense"]["2"]["slope"]
        assert slope_fn(1) == pytest.approx(0.878542698)

    def test_water_dispense_volume_offset_ch1(self, test_dispenser):
        # intercept = 0.321305707 * active_channels + (-4.857648804)
        intercept_fn = test_dispenser.valve_control_timing_functions["water"]["dispense"]["1"]["intercept"]
        assert intercept_fn(2) == pytest.approx(0.321305707 * 2 + (-4.857648804))

    def test_water_dispense_opening_time_positive_for_50ul(self, test_dispenser):
        slope = test_dispenser.valve_control_timing_functions["water"]["dispense"]["1"]["slope"](2)
        intercept = test_dispenser.valve_control_timing_functions["water"]["dispense"]["1"]["intercept"](2)
        assert int(slope * 50 + intercept) > 0

    def test_no_aspirate_process_in_dispenser_calibration(self, test_dispenser):
        """test dispenser config has no aspirate calibration block."""
        assert "aspirate" not in test_dispenser.valve_control_timing_functions["water"]


# ---------------------------------------------------------------------------
# test dispenser — operations
# ---------------------------------------------------------------------------


class TestTestDispenserOperations:
    @pytest.mark.parametrize("liquid_class", TEST_DISPENSER_LIQUID_CLASSES)
    def test_dispense_each_liquid_class_channel1(self, test_dispenser, liquid_class):
        test_dispenser.dispense({1: {"volume": 100, "liquid_class": liquid_class}})
        test_dispenser.mock_vaem.select_valve.assert_called_with(valve_id=1)

    @pytest.mark.parametrize("liquid_class", TEST_DISPENSER_LIQUID_CLASSES)
    def test_dispense_uses_70mbar_pressure(self, test_dispenser, liquid_class):
        test_dispenser.mock_pressure.set_output_pressure.reset_mock()
        test_dispenser.mock_pressure.set_output_pressure.side_effect = (
            lambda pressure: test_dispenser.mock_pressure.get_output_pressure.__class__
        )
        # Re-wire the pressure tracking side_effect after the reset
        state = {"p": 0}
        test_dispenser.mock_pressure.set_output_pressure.side_effect = lambda pressure: state.update({"p": pressure})
        test_dispenser.mock_pressure.get_output_pressure.side_effect = lambda: state["p"]

        test_dispenser.dispense({1: {"volume": 100, "liquid_class": liquid_class}})

        pressures_used = [c.kwargs["pressure"] for c in test_dispenser.mock_pressure.set_output_pressure.call_args_list]
        assert 70 in pressures_used

    def test_dispense_both_channels_simultaneously(self, test_dispenser):
        test_dispenser.dispense({
            1: {"volume": 100, "liquid_class": "water"},
            2: {"volume": 150, "liquid_class": "water"},
        })
        test_dispenser.mock_vaem.select_valve.assert_any_call(valve_id=1)
        test_dispenser.mock_vaem.select_valve.assert_any_call(valve_id=2)

    def test_dispenser_aspirate_raises_not_implemented(self, test_dispenser):
        with pytest.raises(NotImplementedError):
            test_dispenser.aspirate({1: {"volume": 100, "liquid_class": "water"}})

    def test_status_clear_after_dispense(self, test_dispenser):
        test_dispenser.dispense({1: {"volume": 100, "liquid_class": "water"}})
        assert test_dispenser.fluid_control_status.code == 0


# ---------------------------------------------------------------------------
# test pipettor — initialization
# ---------------------------------------------------------------------------


class TestTestPipettorInit:
    def test_creates_pipettor_instance(self, test_pipettor):
        assert isinstance(test_pipettor, Pipettor)

    def test_channel_count_is_eight(self, test_pipettor):
        assert test_pipettor.channel_count == 8

    def test_active_channels_are_one_through_eight(self, test_pipettor):
        assert set(test_pipettor.active_channels) == set(range(1, 9))

    def test_active_valve_count_is_eight(self, test_pipettor):
        assert test_pipettor.active_valve_count == 8

    def test_pgva_ip_from_config(self, test_pipettor):
        assert test_pipettor.pressure_control_config.ip == "192.168.0.23"

    def test_vaem_ip_from_config(self, test_pipettor):
        assert test_pipettor.valve_control_config.ip == "192.168.0.27"


# ---------------------------------------------------------------------------
# test pipettor — liquid classes and calibration
# ---------------------------------------------------------------------------


TEST_PIPETTOR_LIQUID_CLASSES = ["water", "ethylene-glycol10%"]


class TestTestPipettorLiquidClasses:
    def test_two_liquid_classes_present(self, test_pipettor):
        assert set(test_pipettor.get_liquid_classes()) == set(TEST_PIPETTOR_LIQUID_CLASSES)

    @pytest.mark.parametrize("liquid_class", TEST_PIPETTOR_LIQUID_CLASSES)
    def test_dispense_pressure_is_70_mbar(self, test_pipettor, liquid_class):
        assert test_pipettor.pressures[liquid_class]["dispense"] == 70

    @pytest.mark.parametrize("liquid_class", TEST_PIPETTOR_LIQUID_CLASSES)
    def test_aspirate_pressure_is_minus_100_mbar(self, test_pipettor, liquid_class):
        assert test_pipettor.pressures[liquid_class]["aspirate"] == -100

    def test_dispense_timing_functions_built_for_calibration_keys_1_through_8(self, test_pipettor):
        """Calibration uses string keys '1'-'8' (channel-index notation)."""
        dispense = test_pipettor.valve_control_timing_functions["water"]["dispense"]
        assert set(dispense.keys()) == {str(i) for i in range(1,9)}

    def test_aspirate_timing_functions_built_for_calibration_keys_1_through_8(self, test_pipettor):
        aspirate = test_pipettor.valve_control_timing_functions["water"]["aspirate"]
        assert set(aspirate.keys()) == {str(i) for i in range(1,9)}

    def test_water_dispense_flow_coeff_ch1_matches_config(self, test_pipettor):
        # channel_index_coeff=0.0038281, flow_offset=0.826181241
        slope_fn = test_pipettor.valve_control_timing_functions["water"]["dispense"]["1"]["slope"]
        assert slope_fn(8) == pytest.approx(0.0038281 * 8 + 0.826181241)

    def test_water_aspirate_flow_coeff_ch1_matches_config(self, test_pipettor):
        # channel_index_coeff=0.006111421, flow_offset=1.312909499
        slope_fn = test_pipettor.valve_control_timing_functions["water"]["aspirate"]["1"]["slope"]
        assert slope_fn(8) == pytest.approx(0.006111421 * 8 + 1.312909499)

    @pytest.mark.parametrize("ch_key", [str(i) for i in range(1,9)])
    def test_dispense_opening_time_positive_at_100ul(self, test_pipettor, ch_key):
        """Every channel must produce a positive opening time for a real dispense volume."""
        slope = test_pipettor.valve_control_timing_functions["water"]["dispense"][ch_key]["slope"](8)
        intercept = test_pipettor.valve_control_timing_functions["water"]["dispense"][ch_key]["intercept"](8)
        opening_time = int(slope * 100 + intercept)
        assert opening_time > 0, f"Negative opening time {opening_time} for channel key '{ch_key}'"


# ---------------------------------------------------------------------------
# test pipettor — operations
# ---------------------------------------------------------------------------


class TestTestPipettorOperations:
    def test_dispense_channel1_water(self, test_pipettor):
        test_pipettor.dispense({1: {"volume": 100, "liquid_class": "water"}})
        test_pipettor.mock_vaem.select_valve.assert_called_with(valve_id=1)

    def test_aspirate_channel1_water(self, test_pipettor):
        test_pipettor.aspirate({1: {"volume": 100, "liquid_class": "water"}})
        test_pipettor.mock_vaem.select_valve.assert_called_with(valve_id=1)

    def test_dispense_status_clear_after_success(self, test_pipettor):
        test_pipettor.dispense({1: {"volume": 100, "liquid_class": "water"}})
        assert test_pipettor.fluid_control_status.code == 0

    def test_aspirate_status_clear_after_success(self, test_pipettor):
        test_pipettor.aspirate({1: {"volume": 100, "liquid_class": "water"}})
        assert test_pipettor.fluid_control_status.code == 0

    def test_dispense_ethylene_glycol_uses_correct_pressure(self, test_pipettor):
        state = {"p": 0}
        test_pipettor.mock_pressure.set_output_pressure.side_effect = lambda pressure: state.update({"p": pressure})
        test_pipettor.mock_pressure.get_output_pressure.side_effect = lambda: state["p"]

        test_pipettor.dispense({1: {"volume": 100, "liquid_class": "ethylene-glycol10%"}})

        pressures_used = [
            c.kwargs["pressure"]
            for c in test_pipettor.mock_pressure.set_output_pressure.call_args_list
        ]
        assert 70 in pressures_used

    def test_aspirate_ethylene_glycol_uses_correct_pressure(self, test_pipettor):
        state = {"p": 0}
        test_pipettor.mock_pressure.set_output_pressure.side_effect = lambda pressure: state.update({"p": pressure})
        test_pipettor.mock_pressure.get_output_pressure.side_effect = lambda: state["p"]

        test_pipettor.aspirate({1: {"volume": 100, "liquid_class": "ethylene-glycol10%"}})

        pressures_used = [
            c.kwargs["pressure"]
            for c in test_pipettor.mock_pressure.set_output_pressure.call_args_list
        ]
        assert -100 in pressures_used
