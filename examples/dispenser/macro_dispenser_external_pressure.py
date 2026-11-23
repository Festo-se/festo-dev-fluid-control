# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""
Select the generator when a component also declares regulator data.

The configurator superset's ``dispenser_1`` declares both
``pressure_generator`` and ``pressure_regulator``. Fluid-control currently
constructs the PGVA from ``pressure_generator``; it does not automatically
consume the regulator declaration. The file name is retained for source
continuity, but this example demonstrates generator selection only.

The addresses are illustrative. Do not run this example against hardware until
they have been checked and replaced for the target instrument.
"""

from fluid_control import Dispenser, example_config_path


def main() -> None:
    """Construct the canonical dispenser through its pressure generator."""
    with Dispenser(config=example_config_path(), component_id="dispenser_1") as dispenser:
        print(f"Selected PGVA at {dispenser.pressure_control_config.ip}:{dispenser.pressure_control_config.port}")


if __name__ == "__main__":
    main()
