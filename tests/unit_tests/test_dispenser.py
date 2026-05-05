"""Unit tests specific to the ``Dispenser`` subclass.

``Dispenser`` is a thin subclass of ``PressureOverLiquidControl`` which 
overrides the ``aspirate``, ``eject_tips``, and ``pickup_tips`` method behaviour, 
so that they always raise ``NotImplementedError`` (dispensers may not be configured 
to aspirate and cannot manipulate tips).  Everything else is inherited.
"""

import pytest

from fluid_control import Dispenser
from fluid_control.fluid_control import PressureOverLiquidControl


class TestDispenserClassHierarchy:
    def test_is_instance_of_dispenser(self, dispenser):
        assert isinstance(dispenser, Dispenser)

    def test_is_instance_of_pressure_over_liquid_control(self, dispenser):
        assert isinstance(dispenser, PressureOverLiquidControl)

    def test_is_not_instance_of_object_only(self, dispenser):
        assert not type(dispenser) is object


class TestDispenserAspirateOverride:
    def test_aspirate_raises_not_implemented(self, dispenser):
        with pytest.raises(NotImplementedError, match="not configured to aspirate"):
            dispenser.aspirate({1: {"volume": 100, "liquid_class": "water"}})

    def test_aspirate_raises_regardless_of_channel(self, dispenser):
        with pytest.raises(NotImplementedError):
            dispenser.aspirate({2: {"volume": 50, "liquid_class": "water"}})

    def test_aspirate_raises_with_empty_dict(self, dispenser):
        with pytest.raises(NotImplementedError):
            dispenser.aspirate({})

    def test_aspirate_raises_with_none(self, dispenser):
        with pytest.raises(NotImplementedError):
            dispenser.aspirate(None)


class TestDispenserDispenseInherited:
    def test_dispense_is_callable(self, dispenser):
        assert callable(dispenser.dispense)

    def test_dispense_executes_without_raising(self, dispenser):
        dispenser.dispense({1: {"volume": 100, "liquid_class": "water"}})
