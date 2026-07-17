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

    The ``aspirate`` operation is provided by :class:`~fluid_control.capabilities.AspirateMixin`.

    Construction is handled entirely by
    :class:`~fluid_control.fluid_control.PressureOverLiquidControl`; ``component_id``
    defaults to ``"aspirator_1"`` (derived from ``component_type``).
    """

    component_type: str = "aspirator"
