"""Unit tests for [`DeviceConfig`][fluid_control.device_config.DeviceConfig].

Covers component resolution (wrapped and unwrapped configs), derived channel
values, interface parsing, valve error-handling aggregation, and the live
calibration accessors.  No hardware is required; only plain config dicts.
"""

import pytest

from fluid_control.device_config import DeviceConfig, InterfaceConfig


@pytest.fixture()
def device_config(dispenser_config):
    return DeviceConfig(dispenser_config, "dispenser_1")


class TestResolution:
    def test_resolves_unwrapped_config(self, dispenser_config):
        cfg = DeviceConfig(dispenser_config, "dispenser_1")
        assert cfg.raw is dispenser_config["components"]["dispenser_1"]

    def test_resolves_component_config_wrapper(self, dispenser_config):
        wrapped = {"component_config": dispenser_config}
        cfg = DeviceConfig(wrapped, "dispenser_1")
        assert cfg.raw is dispenser_config["components"]["dispenser_1"]

    def test_stores_component_id(self, device_config):
        assert device_config.component_id == "dispenser_1"

    def test_missing_component_raises_key_error(self, dispenser_config):
        with pytest.raises(KeyError):
            DeviceConfig(dispenser_config, "does_not_exist")


class TestDerivedChannels:
    def test_active_channels(self, device_config):
        assert device_config.active_channels == [1, 2]

    def test_active_valve_count(self, device_config):
        assert device_config.active_valve_count == 2

    def test_channel_count(self, device_config):
        assert device_config.channel_count == 2

    def test_eight_channel(self, eight_channel_pipettor_config):
        cfg = DeviceConfig(eight_channel_pipettor_config, "pipettor_1")
        assert cfg.active_channels == list(range(1, 9))
        assert cfg.active_valve_count == 8
        assert cfg.channel_count == 8


class TestInterfaces:
    def test_pressure_interface(self, device_config):
        iface = device_config.pressure_interface
        assert iface.name == "pgva"
        assert iface.interface_type == "tcp/ip"
        assert iface.ip == "192.168.10.102"
        assert iface.port == 502
        assert iface.unit_id == 1

    def test_valve_interface(self, device_config):
        iface = device_config.valve_interface
        assert iface.name == "vaem"
        assert iface.interface_type == "tcp/ip"
        assert iface.ip == "192.168.10.27"
        assert iface.port == 502

    def test_valve_unit_id_is_always_one(self, dispenser_config):
        # The recorded uuid is 2 but the VAEM is always addressed on unit id 1.
        dispenser_config["components"]["dispenser_1"]["control_modules"]["valve"]["uuid"] = 99
        cfg = DeviceConfig(dispenser_config, "dispenser_1")
        assert cfg.valve_interface.unit_id == 1

    def test_interface_config_is_frozen(self, device_config):
        with pytest.raises(AttributeError):
            device_config.pressure_interface.ip = "10.0.0.1"


class TestValveErrorHandling:
    def test_true_when_all_valves_enabled(self, device_config):
        assert device_config.valve_error_handling is True

    def test_false_when_any_valve_disabled(self, dispenser_config):
        valve_types = dispenser_config["components"]["dispenser_1"]["control_modules"]["valve"]["valve_type"]
        valve_types["1"]["type"]["error-handling"] = False
        cfg = DeviceConfig(dispenser_config, "dispenser_1")
        assert cfg.valve_error_handling is False


class TestCalibrationAccessors:
    def test_calibration_returns_live_mapping(self, dispenser_config):
        cfg = DeviceConfig(dispenser_config, "dispenser_1")
        assert cfg.calibration is dispenser_config["components"]["dispenser_1"]["calibration"]

    def test_calibration_reflects_in_place_edits(self, dispenser_config):
        cfg = DeviceConfig(dispenser_config, "dispenser_1")
        dispenser_config["components"]["dispenser_1"]["calibration"]["water"]["dispense"]["parameters"]["pressure"] = 999
        assert cfg.calibration["water"]["dispense"]["parameters"]["pressure"] == 999

    def test_liquid_classes(self, device_config):
        assert set(device_config.liquid_classes()) == {"water"}

    def test_build_pressures(self, device_config):
        pressures = device_config.build_pressures()
        assert pressures == {"water": {"dispense": 70, "aspirate": -100}}

    def test_flow_coefficients(self, device_config):
        coeffs = device_config.flow_coefficients("water", "dispense")
        assert set(coeffs.keys()) == {"1", "2"}
        assert "flow_offset" in coeffs["1"]

    def test_volume_offset_coefficients(self, device_config):
        coeffs = device_config.volume_offset_coefficients("water", "dispense")
        assert set(coeffs.keys()) == {"1", "2"}
        assert "volume_offset" in coeffs["1"]


def test_interface_config_fields():
    iface = InterfaceConfig(name="pgva", interface_type="tcp/ip", ip="1.2.3.4", port=502, unit_id=1)
    assert (iface.name, iface.interface_type, iface.ip, iface.port, iface.unit_id) == (
        "pgva",
        "tcp/ip",
        "1.2.3.4",
        502,
        1,
    )
