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

from fluid_control import Dispenser, example_config_path


def main() -> None:
    """Dispense 25 uL of water on channel 1."""
    with Dispenser(config=example_config_path(), component_id="micro-dispenser") as dispenser:
        dispenser.dispense({1: {"volume": 25.0, "liquid_class": "water"}})


if __name__ == "__main__":
    main()
