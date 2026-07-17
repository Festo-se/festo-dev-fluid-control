# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""Pipettor module exposing the Pipettor class for multi-channel tip-based liquid handling."""

import logging

from fluid_control.capabilities import AspirateMixin, DispenseMixin, MixMixin, TipHandlingMixin
from fluid_control.fluid_control import PressureOverLiquidControl
from applied_motion import Axis
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
    """

    component_type: str = "pipettor"

    def __init__(
        self,
        config: dict,
        component_id: str = "pipettor_1",
        mount_arm: Axis | None = None,
        disable_axes: tuple[Axis, ...] = (),
        pressure_control=None,
        valve_control=None,
    ):
        """
        Initialise the Pipettor from an instrument configuration dict.

        Args:
            config (dict): Full instrument configuration; the component keyed
                by ``component_id`` is extracted and used.
            component_id (str): Key of this pipettor instance inside
                ``config["components"]``. Defaults to ``"pipettor_1"``.
            mount_arm (Axis | None, optional): ``Axis`` used for tip pickup/eject motion.
                If ``None`` the pipettor is static. Defaults to None.
            disable_axes (tuple, optional): Axes to disable during tip engagement moves.
                Defaults to ``()``.
            pressure_control: Instance of already-instantiated pressure control device.
                Opinionated choice that this is a PGVA with some support for
                PLC-controlled VEAB at present.
            valve_control: Instance of already-instantiated valve control device.
                Opinionated choice that this is a VAEM with some support for single valves controlled
                by the DO pin on the PGVA at present.

        """
        super().__init__(
            config,
            component_id=component_id,
            mount_arm=mount_arm,
            disable_axes=disable_axes,
            pressure_control=pressure_control,
            valve_control=valve_control,
        )
