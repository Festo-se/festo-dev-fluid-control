# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""
Basic single-channel dispense.

Instantiates a [`Dispenser`][fluid_control.Dispenser] from the bundled example
configuration and dispenses a fixed volume of water on one channel.

Run with::

    python examples/dispenser/basic_dispense.py

Requires a reachable PGVA and VAEM at the addresses in the configuration. Replace
``load_example_config()`` with your own configuration (for example
``json.load(open("micro-dispenser-config.json"))``) before running on hardware.
"""

from configurator import Configurator, Registry
from fluid_control import example_config_path
from fluid_control.configurator_adapter import fluid_control_registrations


def main() -> None:
    """Dispense 25 uL of water on channel 1."""
    with Configurator.bootstrap(
        example_config_path(), "micro-dispenser", Registry.compose(*fluid_control_registrations())
    ) as result:
        dispenser = result.instance
        dispenser.dispense({1: {"volume": 25.0, "liquid_class": "water"}})


if __name__ == "__main__":
    main()
