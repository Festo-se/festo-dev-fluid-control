"""Hello."""

import json  # TODO: FestoConfiguration class with built in validators, etc
from fluid_control import Dispenser, PressureControl
from applied_motion import Gantry

import json
from os import getenv
from pathlib import Path
import logging
from pgva import PGVA, PGVATCPConfig

from applied_motion import Gantry

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s.%(msecs)03d | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.FileHandler("applied_motion.log"), logging.StreamHandler()],
)

_DEFAULT_FPOSBAPI_IP = "192.168.10.25"
_DEFAULT_FPOSBAPI_PORT = 1234


ip = getenv("FPOSBAPI_IP", _DEFAULT_FPOSBAPI_IP)
port = int(getenv("FPOSBAPI_PORT", str(_DEFAULT_FPOSBAPI_PORT)))
fixture_path = Path(__file__).parent / "test-fluid-configs.json"
with fixture_path.open() as fh:
    cfg = json.load(fh)
    # TODO: Validate TCP connction with cfg["interface"]["type"] = "tcp/ip"
    components = cfg["component_config"]
import pprint

# Init gantry
gantry = Gantry.from_config(components)

# Init micro dispenser
micro_dispenser = Dispenser(config=components, component_id="micro-dispenser")

pprint.pprint(components)
# Init macro dispenser
macro_dispenser = Dispenser(
    config=components,
    component_id="macro-dispenser",
    pressure_control=PressureControl(gantry),
    valve_control=micro_dispenser.valve_control,
)
