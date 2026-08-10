# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""
Festo Aspirator module containing Aspirator class and support functions.

Configurable class for aspirating applications.
For now, this class assumes use of a Festo VAEM and PGVA for valve and
pressure control respectively. Optional hooks in development for proportional pressure regulation
using a VEAB connected to a Festo PLC and communicated with via socket using an API
in the style of the Festo Easy Positioning API and integrated via support in the
festo-applied-motion library.
"""

from fluid_control.capabilities import AspirateMixin
from fluid_control.fluid_control import PressureOverLiquidControl


class Aspirator(AspirateMixin, PressureOverLiquidControl):
    """
    Aspirator class for modular aspirating applications.

    Driver for a Festo aspirator, e.g. VTOI, VTOE, VTOF.
    Currently, there are hard-coded dependencies on the festo-pgva and festo-vaem drivers
    for their respective hardware modules.

    The ``aspirate`` operation is provided by [`AspirateMixin`][fluid_control.capabilities.AspirateMixin].

    Construction is handled entirely by
    [`PressureOverLiquidControl`][fluid_control.fluid_control.PressureOverLiquidControl]; ``component_id``
    defaults to ``"aspirator_1"`` (derived from ``component_type``).

    Examples:
        Aspirate 40 uL of water on channel 1:

        >>> import json
        >>> from fluid_control import Aspirator
        >>> with open("aspirator-config.json") as fh:
        ...     config = json.load(fh)
        >>> aspirator = Aspirator(config=config, component_id="aspirator")
        >>> aspirator.aspirate({1: {"volume": 40.0, "liquid_class": "water"}})

    """

    component_type: str = "aspirator"
