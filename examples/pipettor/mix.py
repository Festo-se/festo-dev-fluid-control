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

from configurator import Configurator, Registry
from fluid_control import example_config_path
from fluid_control.configurator_adapter import fluid_control_registrations


def main() -> None:
    """Mix 20 uL up and down for 3 cycles on channel 1."""
    with Configurator.bootstrap(
        example_config_path(), "pipettor", Registry.compose(*fluid_control_registrations())
    ) as result:
        pipettor = result.instance
        pipettor.mix({1: {"volume": 20.0, "liquid_class": "water"}}, cycles=3)


if __name__ == "__main__":
    main()
