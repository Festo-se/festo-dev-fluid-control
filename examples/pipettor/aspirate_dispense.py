# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""
Aspirate then dispense with a pipettor.

Instantiates a [`Pipettor`][fluid_control.Pipettor] from the bundled example
configuration and performs a simple transfer: aspirate a volume, then dispense it.
Both operations use the same ``liquid_class`` calibration but different processes
(``aspirate`` / ``dispense``) with their own calibrated pressures.

Run with::

    python examples/pipettor/aspirate_dispense.py

Requires a reachable PGVA and VAEM at the addresses in the configuration.
"""

from fluid_control import Pipettor, load_example_config


def main() -> None:
    """Aspirate 50 uL of water on channel 1, then dispense it."""
    config = load_example_config()

    with Pipettor(config=config, component_id="pipettor") as pipettor:
        pipettor.aspirate({1: {"volume": 50.0, "liquid_class": "water"}})
        pipettor.dispense({1: {"volume": 50.0, "liquid_class": "water"}})


if __name__ == "__main__":
    main()
