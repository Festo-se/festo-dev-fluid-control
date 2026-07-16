"""Hardware / integration tests for festo-dev-fluid-control against test hardware.

Uses the configuration from ``tests/fixtures/test-config.json``:
    dispenser  — PGVA 192.168.10.102, VAEM 192.168.10.27, 2 channels
    pipettor   — PGVA 192.168.0.23,   VAEM 192.168.0.27,  8 channels

These tests are skipped automatically unless ``FESTO_HARDWARE_TESTS=1`` is
set in the environment.  Run with::

    FESTO_HARDWARE_TESTS=1 uv run pytest -m hardware -v

All tests are marked ``@pytest.mark.hardware`` and excluded from the default
``-m "not hardware"`` run.
"""

import pytest

from fluid_control import Dispenser, Pipettor


pytestmark = pytest.mark.hardware


# ---------------------------------------------------------------------------
# Dispenser (2-channel, test config)
# ---------------------------------------------------------------------------


class TestHardwareDispenserConnectivity:
    def test_instantiates_as_dispenser(self, test_hardware_dispenser):
        assert isinstance(test_hardware_dispenser, Dispenser)

    def test_get_status_returns_expected_keys(self, test_hardware_dispenser):
        status = test_hardware_dispenser.get_status()
        assert set(status.keys()) == {"pressure", "vaem", "fluid_control_status"}

    def test_get_status_pgva_value_is_dict(self, test_hardware_dispenser):
        status = test_hardware_dispenser.get_status()
        assert isinstance(status["pressure"], dict)

    def test_get_status_vaem_value_is_dict(self, test_hardware_dispenser):
        status = test_hardware_dispenser.get_status()
        assert isinstance(status["vaem"], dict)

    def test_dispenser_status_clear_after_init(self, test_hardware_dispenser):
        status = test_hardware_dispenser.get_status()
        assert status["fluid_control_status"] == 0


class TestHardwareDispenserOperations:
    def test_dispense_water_channel1_does_not_raise(self, test_hardware_dispenser):
        test_hardware_dispenser.dispense({1: {"volume": 50, "liquid_class": "water"}})

    def test_dispense_status_clear_after_water_channel1(self, test_hardware_dispenser):
        test_hardware_dispenser.dispense({1: {"volume": 50, "liquid_class": "water"}})
        assert test_hardware_dispenser.fluid_control_status.code == 0

    def test_dispense_water_channel2_does_not_raise(self, test_hardware_dispenser):
        test_hardware_dispenser.dispense({2: {"volume": 50, "liquid_class": "water"}})

    def test_dispense_both_channels_simultaneously(self, test_hardware_dispenser):
        test_hardware_dispenser.dispense({
            1: {"volume": 50, "liquid_class": "water"},
            2: {"volume": 50, "liquid_class": "water"},
        })
        assert test_hardware_dispenser.fluid_control_status.code == 0

    def test_dispense_ethylene_glycol_channel1(self, test_hardware_dispenser):
        test_hardware_dispenser.dispense({1: {"volume": 50, "liquid_class": "ethylene-glycol10%"}})
        assert test_hardware_dispenser.fluid_control_status.code == 0

    def test_aspirate_raises_not_implemented(self, test_hardware_dispenser):
        with pytest.raises(NotImplementedError):
            test_hardware_dispenser.aspirate({1: {"volume": 50, "liquid_class": "water"}})


# ---------------------------------------------------------------------------
# Pipettor (8-channel, test config)
# ---------------------------------------------------------------------------


class TestHardwarePipettorConnectivity:
    def test_instantiates_as_pipettor(self, test_hardware_pipettor):
        assert isinstance(test_hardware_pipettor, Pipettor)

    def test_get_status_returns_expected_keys(self, test_hardware_pipettor):
        status = test_hardware_pipettor.get_status()
        assert set(status.keys()) == {"pressure", "valve", "fluid_control_status"}

    def test_pipettor_status_clear_after_init(self, test_hardware_pipettor):
        status = test_hardware_pipettor.get_status()
        assert status["fluid_control_status"] == 0


class TestHardwarePipettorOperations:
    def test_dispense_water_channel1_does_not_raise(self, test_hardware_pipettor):
        test_hardware_pipettor.dispense({1: {"volume": 50, "liquid_class": "water"}})

    def test_dispense_status_clear_after_water_channel1(self, test_hardware_pipettor):
        test_hardware_pipettor.dispense({1: {"volume": 50, "liquid_class": "water"}})
        assert test_hardware_pipettor.fluid_control_status.code == 0

    def test_aspirate_water_channel1_does_not_raise(self, test_hardware_pipettor):
        test_hardware_pipettor.aspirate({1: {"volume": 50, "liquid_class": "water"}})

    def test_aspirate_status_clear_after_water_channel1(self, test_hardware_pipettor):
        test_hardware_pipettor.aspirate({1: {"volume": 50, "liquid_class": "water"}})
        assert test_hardware_pipettor.fluid_control_status.code == 0


# ---------------------------------------------------------------------------
# Tip handling — hardware tests not applicable without a mount_arm
#
# ``eject_tips`` and ``pickup_tips`` require a non-static Pipettor, i.e. one
# constructed with a ``mount_arm`` argument.  The current test-config.json
# pipettor component is operated without a mount arm (``is_static=True``),
# so calling either method raises ``NotImplementedError`` on live hardware
# exactly as it does in the unit tests.
#
# To add hardware tip-handling tests:
#   1. Wire the Pipettor's motor axis into a fixture that passes a real
#      ``mount_arm`` object (e.g. a festo-edcon-enabled axis driver instance).
#   2. Add ``test_hardware_pipettor_with_arm`` fixture to conftest.py,
#      gated on ``FESTO_HARDWARE_TESTS=1`` and additional env vars for the
#      axis IP / node ID.
#   3. Add tests modelled on the mocked ``TestEjectTips`` /
#      ``TestPickupTips`` classes in ``tests/unit_tests/test_fluid_control_operations.py``.
# ---------------------------------------------------------------------------

