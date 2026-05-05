"""Unit tests for calibration math and configuration parsing.

These tests are purely computational — no hardware, no I/O, no mocking of
timing-sensitive behaviour.  They verify:

- ``_slope_intercept_func`` produces correct linear outputs
- Timing functions stored in ``valve_control_timing_functions`` compute
  expected slope / intercept values
- ``set_pressures`` extracts the right pressure for each liquid class × process
- ``get_liquid_classes`` returns all top-level calibration keys
- All validators raise ``ValueError`` on out-of-range inputs
- ``_validate_liquid_class`` raises ``ValueError`` for unknown classes
"""

import pytest


class TestSlopeInterceptFunc:
    def test_returns_callable(self, dispenser):
        fn = dispenser._slope_intercept_func(2.0, 5.0)
        assert callable(fn)

    def test_correct_output_nonzero_coeff(self, dispenser):
        fn = dispenser._slope_intercept_func(2.0, 5.0)
        assert fn(3) == pytest.approx(11.0)  # 2.0 * 3 + 5.0

    def test_correct_output_zero_coeff(self, dispenser):
        fn = dispenser._slope_intercept_func(0.0, 7.5)
        assert fn(100) == pytest.approx(7.5)

    def test_correct_output_at_zero(self, dispenser):
        fn = dispenser._slope_intercept_func(2.0, 5.0)
        assert fn(0) == pytest.approx(5.0)

    def test_correct_output_negative_offset(self, dispenser):
        fn = dispenser._slope_intercept_func(1.0, -3.0)
        assert fn(10) == pytest.approx(7.0)


class TestTimingFunctions:
    """Verify that the timing functions stored during __init__ produce
    the expected slope and intercept values for known inputs."""

    def test_dispense_slope_ch1_matches_flow_coefficients(self, dispenser):
        # flow_coefficients["1"] = {"channel_index_coeff": 0.0, "flow_offset": 0.826181241 + 1 * 0.01}
        expected_flow_offset = 0.826181241 + 1 * 0.01
        slope_fn = dispenser.valve_control_timing_functions["water"]["dispense"]["1"]["slope"]
        # With channel_index_coeff=0.0, slope is constant regardless of active_channels
        assert slope_fn(1) == pytest.approx(expected_flow_offset)
        assert slope_fn(8) == pytest.approx(expected_flow_offset)

    def test_dispense_intercept_ch1_matches_volume_offset_coefficients(self, dispenser):
        # volume_offset_coefficients["1"] = {"channel_index_coeff": 0.321305707, "volume_offset": -4.857648804 - 1 * 0.1}
        coeff = 0.321305707
        offset = -4.857648804 - 1 * 0.1
        intercept_fn = dispenser.valve_control_timing_functions["water"]["dispense"]["1"]["intercept"]
        assert intercept_fn(2) == pytest.approx(coeff * 2 + offset)

    def test_aspirate_functions_stored_for_all_channels(self, dispenser):
        for ch in ["1", "2"]:
            entry = dispenser.valve_control_timing_functions["water"]["aspirate"][ch]
            assert "slope" in entry
            assert "intercept" in entry

    def test_timing_function_is_deterministic(self, dispenser):
        fn = dispenser.valve_control_timing_functions["water"]["dispense"]["1"]["slope"]
        assert fn(4) == fn(4)

    @pytest.mark.parametrize("active_channels", [1, 2, 4, 8])
    def test_dispense_opening_time_positive_for_reasonable_volume(self, dispenser, active_channels):
        """Opening time must be positive for any realistic volume."""
        ch = "1"
        volume = 100
        slope = dispenser.valve_control_timing_functions["water"]["dispense"][ch]["slope"](active_channels)
        intercept = dispenser.valve_control_timing_functions["water"]["dispense"][ch]["intercept"](active_channels)
        opening_time = int(slope * volume + intercept)
        assert opening_time > 0, (
            f"Opening time {opening_time} not positive for volume={volume}, "
            f"active_channels={active_channels}"
        )


class TestSetPressures:
    def test_dispense_pressure_water(self, dispenser):
        assert dispenser.pressures["water"]["dispense"] == 70

    def test_aspirate_pressure_water(self, dispenser):
        assert dispenser.pressures["water"]["aspirate"] == -100

    def test_pressures_keys_match_calibration_keys(self, dispenser):
        cal_keys = set(dispenser.config["calibration"].keys())
        assert set(dispenser.pressures.keys()) == cal_keys

    def test_set_pressures_updates_in_place(self, dispenser):
        dispenser.config["calibration"]["water"]["dispense"]["parameters"]["pressure"] = 999
        dispenser.set_pressures()
        assert dispenser.pressures["water"]["dispense"] == 999


class TestGetLiquidClasses:
    def test_returns_known_liquid_class(self, dispenser):
        assert "water" in dispenser.get_liquid_classes()

    def test_return_count_matches_calibration_keys(self, dispenser):
        assert len(list(dispenser.get_liquid_classes())) == len(dispenser.config["calibration"])


class TestValidateLiquidClass:
    def test_known_class_does_not_raise(self, dispenser):
        dispenser._validate_liquid_class("water")  # must not raise

    def test_unknown_class_raises_value_error(self, dispenser):
        with pytest.raises(ValueError, match="not contained"):
            dispenser._validate_liquid_class("ethanol")

    def test_empty_string_raises_value_error(self, dispenser):
        with pytest.raises(ValueError):
            dispenser._validate_liquid_class("")


class TestValidateVolume:
    def test_zero_volume_does_not_raise(self, dispenser):
        dispenser._validate_volume(0, channel=1)  # boundary — allowed

    def test_positive_volume_does_not_raise(self, dispenser):
        dispenser._validate_volume(250, channel=1)

    def test_negative_volume_raises_value_error(self, dispenser):
        with pytest.raises(ValueError, match="greater than or equal to zero"):
            dispenser._validate_volume(-1, channel=1)


class TestValidateChannel:
    def test_active_channel_does_not_raise(self, dispenser):
        for ch in dispenser.active_channels:
            dispenser._validate_channel(ch)  # must not raise

    def test_inactive_channel_raises_value_error(self, dispenser):
        with pytest.raises(ValueError, match="active channel"):
            dispenser._validate_channel(99)

    def test_zero_channel_raises_value_error(self, dispenser):
        # 0 is not in active_channels [1, 2]
        with pytest.raises(ValueError):
            dispenser._validate_channel(0)


class TestValidateOpeningTime:
    def test_positive_time_does_not_raise(self, dispenser):
        dispenser._validate_opening_time(1, channel=1)

    def test_large_time_does_not_raise(self, dispenser):
        dispenser._validate_opening_time(10_000, channel=1)

    def test_zero_time_raises_value_error(self, dispenser):
        with pytest.raises(ValueError, match="greater than zero"):
            dispenser._validate_opening_time(0, channel=1)

    def test_negative_time_raises_value_error(self, dispenser):
        with pytest.raises(ValueError):
            dispenser._validate_opening_time(-50, channel=1)
