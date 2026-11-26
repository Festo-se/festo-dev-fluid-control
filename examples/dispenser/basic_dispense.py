# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""
Basic single-channel dispense.

Instantiates a [`Dispenser`][fluid_control.Dispenser] from the bundled example
configuration and dispenses a fixed volume of water on one channel.

Run with::

    python examples/dispenser/basic_dispense.py

Requires a reachable PGVA and VAEM at the addresses in the configuration. Check
the illustrative addresses in the canonical configuration before running on
hardware, or provide your own Spec 4.0 configuration.
"""

from fluid_control import Dispenser, load_example_config


def main() -> None:
    """Dispense 25 uL of water on channel 1."""
    with Dispenser(config=load_example_config(), component_id="dispenser_1") as dispenser:
        dispenser.dispense({1: {"volume": 25.0, "liquid_class": "water"}})


if __name__ == "__main__":
    main()
