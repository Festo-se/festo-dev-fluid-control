# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""
Macro-dispenser driven by an external pressure regulator.

The macro-dispenser configuration regulates pressure through an already-initialised
motion controller (a VEAB channel on a Festo gantry) instead of a standalone PGVA.
Pre-initialised ``pressure_control`` and ``valve_control`` objects are passed to the
constructor to skip internal hardware initialisation and to share the single VAEM
connection with the micro-dispenser.

This example loads a full instrument configuration (which defines the gantry, the
micro-dispenser, and the macro-dispenser) from the repository configuration file.
Replace the path with your own configuration before running on hardware.

Run with::

    python examples/dispenser/macro_dispenser_external_pressure.py

Requires reachable hardware and the ``festo-dev-applied-motion`` package.
"""

import json
from pathlib import Path

from applied_motion import Gantry

from fluid_control import Dispenser, PressureControl

# Full instrument config at the repository root (defines gantry + both dispensers).
_CONFIG_PATH = Path(__file__).resolve().parents[2] / "test-fluid-configs.json"


def main() -> None:
    """Dispense on the macro-dispenser using a shared VAEM and an external regulator."""
    with _CONFIG_PATH.open("r", encoding="utf-8") as fh:
        config = json.load(fh)

    components = config["component_config"]

    # The gantry provides the VEAB pressure regulator.
    gantry = Gantry.from_config(components)

    # The micro-dispenser owns the VAEM connection.
    micro_dispenser = Dispenser(config=components, component_id="micro-dispenser")

    # The macro-dispenser re-uses the VAEM and regulates pressure via the gantry.
    macro_dispenser = Dispenser(
        config=components,
        component_id="macro-dispenser",
        pressure_control=PressureControl(gantry),
        valve_control=micro_dispenser.valve_control,
    )

    macro_dispenser.dispense({2: {"volume": 50.0, "liquid_class": "water"}})


if __name__ == "__main__":
    main()
