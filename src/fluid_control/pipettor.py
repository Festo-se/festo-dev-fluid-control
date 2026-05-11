# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""Pipettor module exposing the Pipettor class for eight-channel tip-based liquid handling."""

import logging

from fluid_control.fluid_control import PressureOverLiquidControl
from applied_motion import Axis
# from configurator import dynamic_importer

logger = logging.getLogger(__name__)

logging.getLogger("pymodbus").setLevel(logging.WARNING)


class Pipettor(PressureOverLiquidControl):
    """
    Festo Eight-channel pressure-over-liquid pipettor.

    All fluid-handling logic is implemented in ``PressureOverLiquidControl``;
    this class binds it to the ``"pipettor"`` component key in the config.
    """

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
            mount_arm: ``Axis`` used for tip pickup/eject motion.
                If ``None`` the pipettor is static. Defaults to None.
            disable_axes (tuple): Axes to disable during tip engagement moves.
                Defaults to ``()``.

        """
        super().__init__(
            config,
            mount_arm,
            disable_axes,
            component_type="pipettor",
            component_id=component_id,
            pressure_control=pressure_control,
            valve_control=valve_control,
        )
