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
    :class:`~fluid_control.fluid_control.PressureOverLiquidControl` engine:

    - ``aspirate`` from :class:`~fluid_control.capabilities.AspirateMixin`
    - ``dispense`` from :class:`~fluid_control.capabilities.DispenseMixin`
    - ``mix`` from :class:`~fluid_control.capabilities.MixMixin`
    - ``pickup_tips`` / ``eject_tips`` from :class:`~fluid_control.capabilities.TipHandlingMixin`

    Construction is handled entirely by
    :class:`~fluid_control.fluid_control.PressureOverLiquidControl`; ``component_id``
    defaults to ``"pipettor_1"`` (derived from ``component_type``).
    """

    component_type: str = "pipettor"
