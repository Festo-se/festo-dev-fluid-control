# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""Pipettor module exposing the Pipettor class for multi-channel tip-based liquid handling."""

import logging

from fluid_control.capabilities import AspirateMixin, DispenseMixin, MixMixin, TipHandlingMixin
from fluid_control.fluid_control import PressureOverLiquidControl
# from configurator import dynamic_importer

logger = logging.getLogger(__name__)

logging.getLogger("pymodbus").setLevel(logging.WARNING)


class Pipettor(AspirateMixin, DispenseMixin, MixMixin, TipHandlingMixin, PressureOverLiquidControl):
    """
    Festo multi-channel pressure-over-liquid pipettor.

    Composes the full set of fluid-handling capabilities onto the
    [`PressureOverLiquidControl`][fluid_control.fluid_control.PressureOverLiquidControl] engine:

    - ``aspirate`` from [`AspirateMixin`][fluid_control.capabilities.AspirateMixin]
    - ``dispense`` from [`DispenseMixin`][fluid_control.capabilities.DispenseMixin]
    - ``mix`` from [`MixMixin`][fluid_control.capabilities.MixMixin]
    - ``pickup_tips`` / ``eject_tips`` from [`TipHandlingMixin`][fluid_control.capabilities.TipHandlingMixin]

    Construction is handled entirely by
    [`PressureOverLiquidControl`][fluid_control.fluid_control.PressureOverLiquidControl]; ``component_id``
    defaults to ``"pipettor_1"`` (derived from ``component_type``).

    Examples:
        Aspirate, mix, then dispense on a mounted pipettor:

        >>> import json
        >>> from fluid_control import Pipettor
        >>> with open("pipettor-config.json") as fh:
        ...     config = json.load(fh)
        >>> pipettor = Pipettor(config=config, component_id="pipettor")
        >>> pipettor.aspirate({1: {"volume": 50.0, "liquid_class": "water"}})
        >>> pipettor.mix({1: {"volume": 20.0, "liquid_class": "water"}}, cycles=3)
        >>> pipettor.dispense({1: {"volume": 50.0, "liquid_class": "water"}})

    """

    component_type: str = "pipettor"
