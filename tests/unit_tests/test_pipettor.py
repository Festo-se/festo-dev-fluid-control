"""Unit tests specific to the ``Pipettor`` subclass.

``Pipettor`` is a thin wrapper around ``PressureOverLiquidControl`` that passes
``id="pipettor"`` to the superclass.
"""

import pytest

from fluid_control import Pipettor
from fluid_control.fluid_control import PressureOverLiquidControl


class TestPipettorClassHierarchy:
    def test_is_instance_of_pipettor(self, pipettor_instance):
        assert isinstance(pipettor_instance, Pipettor)

    def test_is_instance_of_pressure_over_liquid_control(self, pipettor_instance):
        assert isinstance(pipettor_instance, PressureOverLiquidControl)


class TestPipettorAspirate:
    def test_aspirate_does_not_raise_not_implemented(self, pipettor_instance):
        """Pipettor.aspirate is inherited from PressureOverLiquidControl and must
        not raise NotImplementedError (unlike Dispenser)."""
        # Should not raise — any other exception would still fail the test
        pipettor_instance.aspirate({1: {"volume": 50, "liquid_class": "water"}})


class TestPipettorMix:
    def test_mix_succeeds_when_static(self, pipettor_instance):
        """Mixing does not require a motion arm — a static pipettor may mix."""
        assert pipettor_instance.is_static is True
        pipettor_instance.mix({1: {"volume": 50, "liquid_class": "water"}}, cycles=1)
        # One aspirate + one dispense pass → two valve selections
        assert pipettor_instance.mock_vaem.select_valve.call_count == 2

    def test_mix_runs_all_cycles_when_static(self, pipettor_instance):
        pipettor_instance.mix({1: {"volume": 50, "liquid_class": "water"}}, cycles=3)
        # 3 cycles × (aspirate + dispense) → six valve selections
        assert pipettor_instance.mock_vaem.select_valve.call_count == 6


class TestPipettorDispense:
    def test_dispense_executes_without_raising(self, pipettor_instance):
        pipettor_instance.dispense({1: {"volume": 100, "liquid_class": "water"}})

    def test_dispense_status_clear_after_success(self, pipettor_instance):
        pipettor_instance.dispense({1: {"volume": 100, "liquid_class": "water"}})
        assert pipettor_instance.fluid_control_status.code == 0
