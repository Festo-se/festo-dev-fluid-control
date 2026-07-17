# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""
Festo Dispenser module containing Dispenser class and support functions.

Configurable class for dispensing applications.
For now, this class assumes use of a Festo VAEM and PGVA for valve and
pressure control respectively. Optional hooks in development for proportional pressure regulation
using a VEAB connected to a Festo PLC and communicated with via socket using an API
in the style of the Festo Easy Positioning API and integrated via support in the
festo-applied-motion library. This will be separated into a dedicated pressure-control
backend in a future revision.
"""

import logging

from fluid_control.capabilities import DispenseMixin
from fluid_control.fluid_control import PressureOverLiquidControl
from applied_motion import Axis

logger = logging.getLogger(__name__)


class Dispenser(DispenseMixin, PressureOverLiquidControl):
    """
    Dispenser class for modular dispensing applications.

    Driver for a Festo dispenser, e.g. VTOI, VTOE, VTOF.
    Currently, there are hard-coded dependencies on the festo-pgva and festo-vaem drivers
    for their respective hardware modules.

    The ``dispense`` operation is provided by :class:`~fluid_control.capabilities.DispenseMixin`.
    """

    component_type: str = "dispenser"

    def __init__(
        self,
        config: dict,
        component_id: str | None = None,
        mount_arm: Axis | None = None,
        disable_axes: tuple[Axis, ...] = (),
        pressure_control=None,
        valve_control=None,
    ):
        """
        Initialize Dispenser class.

        Args:
            config (dict): Dispenser configuration.
            component_id (str | None): Key of this dispenser instance inside
                ``config["components"]``. Defaults to ``f"{component_type}_1"`` (e.g. ``"dispenser_1"``).
            mount_arm (Axis | None, optional): Mobile arm the dispenser is mounted on, if one exists. Defaults to None.
            disable_axes (tuple, optional): Axes to disable when doing specified actions. Defaults to ().
            pressure_control: Instance of already-instantiated pressure control device.
                Opinionated choice that this is a PGVA with some support for
                PLC-controlled VEAB at present.
            valve_control: Instance of already-instantiated valve control device.
                Opinionated choice that this is a VAEM with some support for single valves controlled
                by the DO pin on the PGVA at present.

        """
        if component_id is None:
            component_id = f"{self.component_type}_1"
        super().__init__(
            config,
            component_id=component_id,
            mount_arm=mount_arm,
            disable_axes=disable_axes,
            pressure_control=pressure_control,
            valve_control=valve_control,
        )
