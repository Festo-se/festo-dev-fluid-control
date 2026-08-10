# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""
Mixing by repeated aspirate/dispense.

[`Pipettor.mix`][Pipettor.mix] repeatedly aspirates and dispenses the same volume to mix the
liquid in the channel. The number of aspirate/dispense cycles is given by
``cycles``.

Run with::

    python examples/pipettor/mix.py

Requires a reachable PGVA and VAEM at the addresses in the configuration.
"""

from fluid_control import Pipettor, load_example_config


def main() -> None:
    """Mix 20 uL up and down for 3 cycles on channel 1."""
    config = load_example_config()

    with Pipettor(config=config, component_id="pipettor") as pipettor:
        pipettor.mix({1: {"volume": 20.0, "liquid_class": "water"}}, cycles=3)


if __name__ == "__main__":
    main()
