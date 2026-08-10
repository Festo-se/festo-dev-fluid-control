# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""
Direct valve-timing command for building calibration.

[`Dispenser.direct_command`][Dispenser.direct_command] bypasses volume calibration entirely and sends
raw pressure and valve-opening times. Pair it with a gravimetric balance to
measure dispensed volumes at known opening times, then fit the slope/intercept
coefficients for your configuration's ``calibration`` block.

This is intended for *building* calibration data, not for production dispensing.

Run with::

    python examples/dispenser/direct_command_calibration.py

Requires a reachable PGVA and VAEM at the addresses in the configuration.
"""

from fluid_control import Dispenser, load_example_config


def main() -> None:
    """Open channel 1 for a sweep of opening times at a fixed pressure."""
    config = load_example_config()

    with Dispenser(config=config, component_id="micro-dispenser") as dispenser:
        for opening_time_ms in (80, 100, 120, 140):
            result = dispenser.direct_command(
                channel_times={1: opening_time_ms},
                pressure=70,
            )
            print(f"{opening_time_ms} ms -> code={result.code}, message={result.message!r}")


if __name__ == "__main__":
    main()
