"""Manual fluid-control hardware smoke test."""

import pprint
import json
import time
from pathlib import Path
import logging

from applied_motion import Gantry
from fluid_control import Dispenser, PressureControl


def main() -> None:
    """Run the manual hardware smoke test."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s.%(msecs)03d | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.FileHandler("fluid_control.log"), logging.StreamHandler()],
    )

    fixture_path = Path(__file__).parent / "src" / "fluid_control" / "data" / "test-fluid-configs.json"
    config = json.loads(fixture_path.read_text(encoding="utf-8"))
    normalized = config.get("component_config", config)
    with Dispenser(config=config, component_id="micro-dispenser") as micro_dispenser:
        gantry = Gantry(config=config, registry=micro_dispenser.registry)
        macro_dispenser = Dispenser(
            config={"components": {"macro-dispenser": normalized["components"]["macro-dispenser"]}},
            component_id="macro-dispenser",
            pressure_control=PressureControl(gantry),
            valve_control=micro_dispenser.valve_control,
        )

        pprint.pprint(normalized)
        micro_dispenser.pressure_control.set_output_pressure(449)
        time.sleep(1.5)
        pprint.pprint(gantry._client.set_veab(150))
        time.sleep(3)
        pprint.pprint(gantry._client.get_veab())  # TODO: get_veab() is hanging
        macro_dispenser.close()


if __name__ == "__main__":
    main()
