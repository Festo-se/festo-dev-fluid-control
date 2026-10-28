# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""
Multi-channel dispense.

Dispenses different volumes on two channels in a single [`Dispenser.dispense`][Dispenser.dispense]
call. All channels are armed before the valve controller is triggered, so they
fire in parallel.

Run with::

    python examples/dispenser/multi_channel_dispense.py

Requires a reachable PGVA and VAEM at the addresses in the configuration.
"""

from configurator import Configurator, Registry
from fluid_control import example_config_path
from fluid_control.configurator_adapter import fluid_control_registrations


def main() -> None:
    """Dispense water on channels 1 and 2 simultaneously."""
    with Configurator.bootstrap(
        example_config_path(), "micro-dispenser", Registry.compose(*fluid_control_registrations())
    ) as result:
        dispenser = result.instance
        dispenser.dispense(
            {
                1: {"volume": 10.0, "liquid_class": "water"},
                2: {"volume": 15.0, "liquid_class": "water"},
            }
        )


if __name__ == "__main__":
    main()
