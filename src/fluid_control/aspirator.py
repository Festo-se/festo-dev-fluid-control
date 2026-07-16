# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""
Festo Aspirator module containing Aspirator class and support functions.

Configurable class for aspirating applications.
For now, this class assumes use of a Festo VAEM and PGVA for valve and
pressure control respectively. Optional hooks in development for proporional pressure regulation
using a VEAB connected to a Festo PLC and communicated with via socket using an API
in the style of the Festo Easy Postioning API and integrated via support in the
festo-applied-motion library.
"""

import logging

from fluid_control.fluid_control import PressureOverLiquidControl
from applied_motion import Axis

logger = logging.getLogger(__name__)


class Aspirator(PressureOverLiquidControl):
    """
    Aspirator class for modular aspirating applications.

    Driver for a Festo aspirator, e.g. VTOI, VTOE, VTOF.
    Currently, there are hard-coded dependencies on the festo-pgva and festo-vaem drivers
    for their respective hardware modules.
    """

    component_type: str = "aspirator"

    def __init__(
        self,
        config: dict,
        component_id: str = "aspirator_1",
        mount_arm: Axis | None = None,
        disable_axes: tuple[Axis, ...] = (),
        pressure_control=None,
        valve_control=None,
    ):
        """
        Initialize Aspirator class.

        Args:
            config (dict): Aspirator configuration.
            component_id (str): Key of this Aspirator instance inside
                ``config["components"]``. Defaults to ``"aspirator_1"``.
            mount_arm (Axis | None, optional): Mobile arm the aspirator is mounted on, if one exists. Defaults to None.
            disable_axes (tuple, optional): Tuple of Axis objects to disable when doing specified actions. Defaults to ().
                NOTE: Some physical systems do not enable this because the gantry is operated by coordinated motor action.
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

    def aspirate(self, aspirate_dict: dict) -> None:
        """
        Aspirate liquid across one or more valve controller channels.

        Args:
            aspirate_dict (dict): Mapping of channel IDs to channel-operation parameters.

        """
        logger.info(f"ASPIRATE START: {aspirate_dict}")
        # TODO: Enable ability to set timing PER CLASS
        self._handle_liquid(aspirate_dict, process="aspirate")
