# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""
Context-manager usage and status inspection.

Demonstrates the recommended integration pattern: use the device as a context
manager so pressure is released and valves are closed on exit, even if an
exception is raised. Also shows querying the configured liquid classes and the
instrument status.

Run with::

    python examples/dispenser/context_manager.py

Requires a reachable PGVA and VAEM at the addresses in the configuration.
"""

from fluid_control import Dispenser, load_example_config


def main() -> None:
    """Dispense within a context manager and print liquid classes and status."""
    config = load_example_config()

    with Dispenser(config=config, component_id="micro-dispenser") as dispenser:
        print("Liquid classes:", list(dispenser.get_liquid_classes()))

        dispenser.dispense({1: {"volume": 30.0, "liquid_class": "water"}})

        status = dispenser.get_status()
        print("Fluid-control status:", status["fluid_control_status"])
    # Pressure released and valves closed here, on __exit__.


if __name__ == "__main__":
    main()
