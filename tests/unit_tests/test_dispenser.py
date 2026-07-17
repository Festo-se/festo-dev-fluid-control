"""Unit tests specific to the ``Dispenser`` subclass.

``Dispenser`` composes ``DispenseMixin`` onto ``PressureOverLiquidControl``,
so it exposes ``dispense`` but not ``aspirate``, ``mix``, ``eject_tips``, or
``pickup_tips`` — a dispenser simply does not have those capabilities.
Everything else is inherited.
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
    """A dispenser is composed with ``DispenseMixin`` only, so it must not
    expose aspirate, mix, or tip-handling operations at all."""

    def test_has_no_aspirate_method(self, dispenser):
        assert not hasattr(dispenser, "aspirate")

    def test_has_no_mix_method(self, dispenser):
        assert not hasattr(dispenser, "mix")

    def test_has_no_eject_tips_method(self, dispenser):
        assert not hasattr(dispenser, "eject_tips")

    def test_has_no_pickup_tips_method(self, dispenser):
        assert not hasattr(dispenser, "pickup_tips")


class TestDispenserDispenseInherited:
    def test_dispense_is_callable(self, dispenser):
        assert callable(dispenser.dispense)

    def test_dispense_executes_without_raising(self, dispenser):
        dispenser.dispense({1: {"volume": 100, "liquid_class": "water"}})
