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

Requires reachable hardware and the ``festo-dev-applied-motion`` package. This
uses a full instrument configuration (defining the gantry and the pipettor) from
the repository; replace the path with your own configuration.
"""

import json
from pathlib import Path

from applied_motion import Gantry

from fluid_control import Pipettor

# Full instrument config at the repository root (defines the gantry + pipettor).
_CONFIG_PATH = Path(__file__).resolve().parents[2] / "test-fluid-configs.json"


def main() -> None:
    """Pick up tips, then eject them, printing each operation result."""
    with _CONFIG_PATH.open("r", encoding="utf-8") as fh:
        config = json.load(fh)

    components = config["component_config"]

    # The gantry provides the mount arm and the lateral axes to disable while
    # driving onto the tips. Here the pipettor's mount axis ("ZP") and the X/Y
    # axes it disables during pickup live on "gantry_2"; match these to your
    # instrument's `mount_axis` and `axes_disable_for_pickup` config.
    gantry = Gantry.from_config(components, name="gantry_2")

    pipettor = Pipettor(
        config=components,
        component_id="pipettor_1",
        mount_arm=gantry.axes["ZP"],
        disable_axes=(gantry.axes["X"], gantry.axes["Y"]),
    )

    pickup_result = pipettor.pickup_tips(duration=0.5)
    print(f"pickup: code={pickup_result.code}, message={pickup_result.message!r}")

    eject_result = pipettor.eject_tips()
    print(f"eject: code={eject_result.code}, message={eject_result.message!r}")


if __name__ == "__main__":
    main()
