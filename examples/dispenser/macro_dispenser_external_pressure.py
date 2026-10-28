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

from pathlib import Path

from applied_motion import Gantry
from configurator import Configurator, Registry

from fluid_control import Dispenser, PressureControl
from fluid_control.configurator_adapter import fluid_control_registrations

# Full instrument config at the repository root (defines gantry + both dispensers).
_CONFIG_PATH = Path(__file__).resolve().parents[2] / "test-fluid-configs.json"


def main() -> None:
    """Dispense on the macro-dispenser using a shared VAEM and an external regulator."""
    registry = Registry.compose(*fluid_control_registrations())
    with Configurator.bootstrap(_CONFIG_PATH, "micro-dispenser", registry) as result:
        micro_view = result.views["micro-dispenser"]
        macro_view = micro_view.require_relationship("macro-dispenser")

        # The gantry provides the VEAB pressure regulator.
        gantry = Gantry.from_config(micro_view.root)

        # The micro-dispenser owns the VAEM connection.
        micro_dispenser = result.instance

        # The macro-dispenser re-uses the VAEM and regulates pressure via the gantry.
        macro_dispenser = Dispenser(
            config={"components": {macro_view.name: macro_view.data}},
            component_id=macro_view.name,
            pressure_control=PressureControl(gantry),
            valve_control=micro_dispenser.valve_control,
        )
        macro_dispenser.dispense({2: {"volume": 50.0, "liquid_class": "water"}})
        macro_dispenser.close()


if __name__ == "__main__":
    main()
