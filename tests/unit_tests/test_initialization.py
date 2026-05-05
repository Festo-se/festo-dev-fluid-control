"""Unit tests for Dispenser and Pipettor initialization.

Covers:
- PGVA / VAEM constructors called with the config-derived IP, port, unit_id
- Active channel count wired correctly from config
- ``deselect_valve`` called once per channel during __init__
- Pressure and valve module name guards raise NotImplementedError
- ``pressures`` dict fully populated after init
- Timing functions built for all liquid-class × process combinations
- Static vs. non-static mode derived from mount_arm presence
"""

from unittest.mock import MagicMock

import pytest

from fluid_control import Dispenser, Pipettor
from fluid_control.fluid_control import PressureOverLiquidControl


class TestDispenserInit:
    def test_creates_instance(self, dispenser):
        assert isinstance(dispenser, Dispenser)

    def test_is_subclass_of_pressure_over_liquid_control(self, dispenser):
        assert isinstance(dispenser, PressureOverLiquidControl)

    def test_is_static_true_without_mount_arm(self, dispenser):
        assert dispenser.is_static is True

    def test_active_valve_count_matches_config(self, dispenser):
        assert dispenser.active_valve_count == 2

    def test_channel_count_matches_config(self, dispenser):
        assert dispenser.channel_count == 2

    def test_active_channels_match_config(self, dispenser):
        assert dispenser.active_channels == [1, 2]

    def test_pgva_constructor_called_once(self, mocker, dispenser_config):
        pgva_cls = mocker.patch("fluid_control.fluid_control.PGVA")
        mocker.patch("fluid_control.fluid_control.VAEM")

        Dispenser(config=dispenser_config)

        pgva_cls.assert_called_once()

    def test_pgva_initialized_with_correct_ip(self, mocker, dispenser_config):
        pgva_cls = mocker.patch("fluid_control.fluid_control.PGVA")
        mocker.patch("fluid_control.fluid_control.VAEM")

        Dispenser(config=dispenser_config)

        config_arg = pgva_cls.call_args.kwargs["config"]
        assert config_arg.ip == "192.168.10.102"

    def test_pgva_initialized_with_correct_port(self, mocker, dispenser_config):
        pgva_cls = mocker.patch("fluid_control.fluid_control.PGVA")
        mocker.patch("fluid_control.fluid_control.VAEM")

        Dispenser(config=dispenser_config)

        config_arg = pgva_cls.call_args.kwargs["config"]
        assert config_arg.port == 502

    def test_pgva_initialized_with_correct_unit_id(self, mocker, dispenser_config):
        pgva_cls = mocker.patch("fluid_control.fluid_control.PGVA")
        mocker.patch("fluid_control.fluid_control.VAEM")

        Dispenser(config=dispenser_config)

        config_arg = pgva_cls.call_args.kwargs["config"]
        assert config_arg.unit_id == 1

    def test_vaem_constructor_called_once(self, mocker, dispenser_config):
        mocker.patch("fluid_control.fluid_control.PGVA")
        vaem_cls = mocker.patch("fluid_control.fluid_control.VAEM")

        Dispenser(config=dispenser_config)

        vaem_cls.assert_called_once()

    def test_vaem_initialized_with_correct_ip(self, mocker, dispenser_config):
        mocker.patch("fluid_control.fluid_control.PGVA")
        vaem_cls = mocker.patch("fluid_control.fluid_control.VAEM")

        Dispenser(config=dispenser_config)

        config_arg = vaem_cls.call_args.kwargs["config"]
        assert config_arg.ip == "192.168.10.27"

    def test_vaem_initialized_with_correct_port(self, mocker, dispenser_config):
        mocker.patch("fluid_control.fluid_control.PGVA")
        vaem_cls = mocker.patch("fluid_control.fluid_control.VAEM")

        Dispenser(config=dispenser_config)

        config_arg = vaem_cls.call_args.kwargs["config"]
        assert config_arg.port == 502

    def test_deselect_valve_called_for_each_channel_on_init(self, mocker, dispenser_config):
        mocker.patch("fluid_control.fluid_control.PGVA")
        vaem_cls = mocker.patch("fluid_control.fluid_control.VAEM")
        mock_vaem_inst = vaem_cls.return_value

        Dispenser(config=dispenser_config)

        assert mock_vaem_inst.deselect_valve.call_count == 2
        mock_vaem_inst.deselect_valve.assert_any_call(valve_id=1)
        mock_vaem_inst.deselect_valve.assert_any_call(valve_id=2)

    def test_pressures_dict_populated_after_init(self, dispenser):
        assert "water" in dispenser.pressures
        assert "dispense" in dispenser.pressures["water"]
        assert "aspirate" in dispenser.pressures["water"]
        assert dispenser.pressures["water"]["dispense"] == 70
        assert dispenser.pressures["water"]["aspirate"] == -100

    def test_timing_functions_populated_after_init(self, dispenser):
        assert "water" in dispenser.valve_control_timing_functions
        assert "dispense" in dispenser.valve_control_timing_functions["water"]
        assert "aspirate" in dispenser.valve_control_timing_functions["water"]

    def test_timing_functions_have_slope_and_intercept_per_channel(self, dispenser):
        for channel in ["1", "2"]:
            entry = dispenser.valve_control_timing_functions["water"]["dispense"][channel]
            assert callable(entry["slope"])
            assert callable(entry["intercept"])

    def test_non_pgva_pressure_module_raises_not_implemented(self, mocker, dispenser_config):
        mocker.patch("fluid_control.fluid_control.PGVA")
        mocker.patch("fluid_control.fluid_control.VAEM")
        # Must not contain the substring 'pgva'; the guard uses 'pgva' not in name
        dispenser_config["components"]["dispenser_1"]["control_modules"]["pressure"]["name"] = "mass-flow-controller"

        with pytest.raises(NotImplementedError):
            Dispenser(config=dispenser_config)

    def test_non_vaem_valve_module_raises_not_implemented(self, mocker, dispenser_config):
        mocker.patch("fluid_control.fluid_control.PGVA")
        mocker.patch("fluid_control.fluid_control.VAEM")
        # Must not contain the substring 'vaem'; the guard uses 'vaem' not in name
        dispenser_config["components"]["dispenser_1"]["control_modules"]["valve"]["name"] = "digital-output"

        with pytest.raises(NotImplementedError):
            Dispenser(config=dispenser_config)


class TestPipettorInit:
    def test_creates_instance(self, pipettor_instance):
        assert isinstance(pipettor_instance, Pipettor)

    def test_is_subclass_of_pressure_over_liquid_control(self, pipettor_instance):
        assert isinstance(pipettor_instance, PressureOverLiquidControl)

    def test_is_static_true_without_mount_arm(self, pipettor_instance):
        assert pipettor_instance.is_static is True

    def test_is_static_false_with_mount_arm(self, mocker, eight_channel_pipettor_config):
        mocker.patch("fluid_control.fluid_control.PGVA")
        vaem_cls = mocker.patch("fluid_control.fluid_control.VAEM")
        # VAEM mock must have deselect_valve to avoid AttributeError during init
        vaem_cls.return_value.get_status.return_value = {"Readiness": 0}

        mock_arm = MagicMock()
        instance = Pipettor(config=eight_channel_pipettor_config, mount_arm=mock_arm)

        assert instance.is_static is False
        assert instance.mount_arm is mock_arm

    def test_active_valve_count_matches_config(self, pipettor_instance):
        assert pipettor_instance.active_valve_count == 8

    def test_channel_count_matches_config(self, pipettor_instance):
        assert pipettor_instance.channel_count == 8

    def test_deselect_valve_called_for_all_eight_channels(self, mocker, eight_channel_pipettor_config):
        mocker.patch("fluid_control.fluid_control.PGVA")
        vaem_cls = mocker.patch("fluid_control.fluid_control.VAEM")
        mock_vaem_inst = vaem_cls.return_value

        Pipettor(config=eight_channel_pipettor_config)

        assert mock_vaem_inst.deselect_valve.call_count == 8
        for ch in range(1, 9):
            mock_vaem_inst.deselect_valve.assert_any_call(valve_id=ch)

    def test_pressures_populated_for_all_liquid_classes(self, pipettor_instance):
        assert "water" in pipettor_instance.pressures

    def test_timing_functions_populated_for_all_eight_channels(self, pipettor_instance):
        dispense_funcs = pipettor_instance.valve_control_timing_functions["water"]["dispense"]
        assert set(dispense_funcs.keys()) == {str(i) for i in range(1, 9)}
