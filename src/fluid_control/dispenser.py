# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""
Festo Dispenser module containing Dispenser class and support functions.

Configurable class for dispensing applications.
For now, this class assumes use of a Festo VAEM and PGVA for valve and
pressure control respectively.

"""

import logging
from typing import NoReturn

from fluid_control.fluid_control import PressureOverLiquidControl
from festo_gantry.gantry import FestoAxis

logger = logging.getLogger(__name__)


class Dispenser(PressureOverLiquidControl):
    """
    Dispenser class for modular dispensing applications.

    Driver for a Festo dispenser, e.g. VTOI, VTOE, VTOF.
    Currently, there are hard-coded dependencies on the festo-pgva and festo-vaem drivers
    for their respective hardware modules.
    """

    def __init__(
        self,
        config: dict,
        component_id: str = "dispenser_1",
        mount_arm: FestoAxis | None = None,
        disable_axes: tuple[FestoAxis, ...] = (),
    ):
        """
        Initialize Dispenser class.

        Args:
            config (dict): Dispenser configuration.
            component_id (str): Key of this dispenser instance inside
                ``config["components"]``. Defaults to ``"dispenser_1"``.
            mount_arm (FestoAxis | None, optional): Mobile arm the dispenser is mounted on, if one exists. Defaults to None.
            disable_axes (tuple, optional): Axes to disable when doing specified actions. Defaults to ().

        """
        super().__init__(config, mount_arm, disable_axes, component_type="dispenser", component_id=component_id)

    def aspirate(self, aspirate_dict: dict) -> NoReturn:
        """
        Aspirate liquid from a source.

        Args:
            aspirate_dict (dict): Dictionary with the dispense channels as keys and the dispense parameters as values.

        Raises:
            NotImplementedError: This method is not currently implemented for dispensing

        """
        logger.debug(f"aspirate called on Dispenser (not supported). Call arg: {aspirate_dict=}")
        raise NotImplementedError("Dispenser is not configured to aspirate.")

    def mix(self, mix_dict: dict, cycles: int) -> NoReturn:
        """
        Aspirate and dispense repeatedly to mix liquid in the channels.

        Args:
            mix_dict (dict): Mapping of channel IDs to channel-operation parameters.
            cycles (int): Number of aspirate/dispense cycles to execute.

        Raises:
            NotImplementedError: Not implemented if aspirate functionality not implemented (dispenser)

        """
        logger.debug(f"mix called on Dispenser (not supported). Call arg: {mix_dict=}, {cycles=}")
        raise NotImplementedError("Dispenser is not configured to mix.")

    def eject_tips(self) -> NoReturn:
        """
        Eject tips from the dispenser.

        Raises:
            NotImplementedError: This method is not implemented for dispensing. Dispensers do not have tips.

        """
        logger.debug("eject_tips called on Dispenser (not supported).")
        raise NotImplementedError("Dispenser cannot use tips.")

    def pickup_tips(self, duration: float) -> NoReturn:
        """
        Pickup tips with the dispenser.

        Raises:
            NotImplementedError: This method is not implemented for dispensing. Dispensers do not have tips.

        """
        logger.debug(f"pickup_tips called on Dispenser (not supported). duration: {duration}")
        raise NotImplementedError("Dispenser cannot use tips.")
