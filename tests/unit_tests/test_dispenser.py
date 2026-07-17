"""Unit tests specific to the ``Dispenser`` subclass.

``Dispenser`` composes ``DispenseMixin`` onto ``PressureOverLiquidControl``,
so it supports ``dispense`` but not ``aspirate``, ``mix``, ``eject_tips``, or
``pickup_tips``.  The base engine declares those capabilities as stubs that
raise ``NotImplementedError``, so a dispenser exposes the methods but rejects
them at call time.  Everything else is inherited.
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


class TestDispenserCapabilityAbsence:
    """A dispenser is composed with ``DispenseMixin`` only, so aspirate, mix, and
    tip-handling operations reject at call time with ``NotImplementedError``."""

    def test_aspirate_raises_not_implemented(self, dispenser):
        with pytest.raises(NotImplementedError):
            dispenser.aspirate({1: {"volume": 10.0, "liquid_class": "water"}})

    def test_mix_raises_not_implemented(self, dispenser):
        with pytest.raises(NotImplementedError):
            dispenser.mix({1: {"volume": 10.0, "liquid_class": "water"}}, 3)

    def test_eject_tips_raises_not_implemented(self, dispenser):
        with pytest.raises(NotImplementedError):
            dispenser.eject_tips()

    def test_pickup_tips_raises_not_implemented(self, dispenser):
        with pytest.raises(NotImplementedError):
            dispenser.pickup_tips(0.5)


class TestDispenserDispenseInherited:
    def test_dispense_is_callable(self, dispenser):
        assert callable(dispenser.dispense)

    def test_dispense_executes_without_raising(self, dispenser):
        dispenser.dispense({1: {"volume": 100, "liquid_class": "water"}})
