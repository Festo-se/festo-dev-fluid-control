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

from fluid_control.capabilities import DispenseMixin
from fluid_control.fluid_control import PressureOverLiquidControl


class Dispenser(DispenseMixin, PressureOverLiquidControl):
    """
    Dispenser class for modular dispensing applications.

    Driver for a Festo dispenser, e.g. VTOI, VTOE, VTOF.
    Currently, there are hard-coded dependencies on the festo-pgva and festo-vaem drivers
    for their respective hardware modules.

    The ``dispense`` operation is provided by [`DispenseMixin`][fluid_control.capabilities.DispenseMixin].

    Construction is handled entirely by
    [`PressureOverLiquidControl`][fluid_control.fluid_control.PressureOverLiquidControl]; ``component_id``
    defaults to ``"dispenser_1"`` (derived from ``component_type``).

    Examples:
        Load an instrument configuration and dispense 25 uL of water on channel 1:

        >>> import json
        >>> from fluid_control import Dispenser
        >>> with open("micro-dispenser-config.json") as fh:
        ...     config = json.load(fh)
        >>> dispenser = Dispenser(config=config, component_id="micro-dispenser")
        >>> dispenser.dispense({1: {"volume": 25.0, "liquid_class": "water"}})

        Use as a context manager to guarantee the instrument is returned to a
        safe state on exit, even if an exception is raised:

        >>> with Dispenser(config=config, component_id="micro-dispenser") as dispenser:
        ...     dispenser.dispense({1: {"volume": 30.0, "liquid_class": "water"}})

    """

    component_type: str = "dispenser"
