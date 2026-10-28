"""Manual fluid-control hardware smoke test."""

import pprint
import time
from pathlib import Path
import logging

from applied_motion import Gantry
from configurator import Configurator, Registry
from fluid_control import Dispenser, PressureControl
from fluid_control.configurator_adapter import fluid_control_registrations


def main() -> None:
    """Run the manual hardware smoke test."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s.%(msecs)03d | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.FileHandler("fluid_control.log"), logging.StreamHandler()],
    )

    fixture_path = Path(__file__).parent / "src" / "fluid_control" / "data" / "test-fluid-configs.json"
    registry = Registry.compose(*fluid_control_registrations())
    with Configurator.bootstrap(fixture_path, "micro-dispenser", registry) as result:
        micro_view = result.views["micro-dispenser"]
        macro_view = micro_view.require_relationship("macro-dispenser")
        gantry = Gantry.from_config(micro_view.root)
        micro_dispenser = result.instance
        macro_dispenser = Dispenser(
            config={"components": {macro_view.name: macro_view.data}},
            component_id=macro_view.name,
            pressure_control=PressureControl(gantry),
            valve_control=micro_dispenser.valve_control,
        )

        pprint.pprint(micro_view.root)
        micro_dispenser.pressure_control.set_output_pressure(449)
        time.sleep(1.5)
        pprint.pprint(gantry._client.set_veab(150))
        time.sleep(3)
        pprint.pprint(gantry._client.get_veab())  # TODO: get_veab() is hanging
        macro_dispenser.close()


if __name__ == "__main__":
    main()
