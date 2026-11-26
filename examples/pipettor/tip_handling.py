# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""
Tip pickup and ejection.

Tip handling requires a mounted (non-static) pipettor: the mount arm (a motion
axis) jogs down onto the tips until engagement stalls the motion, and pneumatic
actuation is used to eject. The mount arm and the lateral axes to disable during
engagement are obtained from a connected [`Gantry`][applied_motion.applied_motion.Gantry]
(``gantry.axes`` maps axis names to [`Axis`][applied_motion.Axis] instances) and
passed to the constructor.

Both operations return an [`OperationResult`][fluid_control.fluid_control.OperationResult]
whose ``code`` is ``0`` on success.

Run with::

    python examples/pipettor/tip_handling.py

Uses the configurator package's canonical superset. Its hardware addresses are
illustrative and must be checked before connecting.
"""

from fluid_control import Pipettor, load_example_config


def main() -> None:
    """Pick up tips, then eject them, printing each operation result."""
    with Pipettor(config=load_example_config(), component_id="pipettor_1") as pipettor:
        pickup_result = pipettor.pickup_tips(duration=0.5)
        print(f"pickup: code={pickup_result.code}, message={pickup_result.message!r}")

        eject_result = pipettor.eject_tips()
        print(f"eject: code={eject_result.code}, message={eject_result.message!r}")


if __name__ == "__main__":
    main()
