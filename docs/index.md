# Festo Fluid Control

`festo-dev-fluid-control` is a Python library for programmatic control of Festo's modular pressure-over-liquid dispensing and pipetting instruments. It provides high-level abstractions over the Festo [PGVA](https://www.festo.com/catalogue/en_GB/Details.htm?id=PGVA) pressure generator and [VAEM](https://www.festo.com/catalogue/en_GB/Details.htm?id=VAEM) valve electronics module, translating volume-based commands into calibrated valve-timing pulses.

---

## How It Works

A **pressure-over-liquid** instrument pressurises a liquid reservoir with the PGVA and opens a solenoid valve via the VAEM for a precisely calibrated duration. The duration is determined by a per-channel, per-liquid-class calibration curve that maps target volume (µL) to valve opening time (ms).

```
┌─────────────────────────────────────────────────┐
│              festo-dev-fluid-control             │
│                                                  │
│   Dispenser / Pipettor                           │
│       │                                          │
│       ├── PressureOverLiquidControl              │
│       │       ├── PGVA  (pressure generator)     │
│       │       └── VAEM  (valve controller)       │
│       │                                          │
│       └── Calibration curves per liquid class    │
└─────────────────────────────────────────────────┘
```

The `Dispenser` class is the primary entry point for fixed-volume, non-aspirating applications (e.g. reagent dispensing). The `Pipettor` class extends this with aspirate, mix, and tip-handling operations.

---

## Quick Start

```python
import json
from fluid_control import Dispenser

# Load your instrument configuration
with open("micro-dispenser-config.json") as fh:
    config = json.load(fh)

# Instantiate the dispenser — hardware connection is established here
dispenser = Dispenser(config=config, component_id="micro-dispenser")

# Dispense 25 µL of water on channel 1
dispenser.dispense({
    1: {"volume": 25.0, "liquid_class": "water"}
})
```

See the [Examples](examples/examples.md) section for detailed walkthroughs.

---

## Installation

### With uv (Recommended)

[uv](https://docs.astral.sh/uv/) is the recommended package manager for this project.

```bash
# Add to an existing project
uv add festo-dev-fluid-control

# Or install directly into the active environment
uv pip install festo-dev-fluid-control
```

### With pip

```bash
pip install festo-dev-fluid-control
```

### From Source (Editable Install)

```bash
git clone https://github.com/Festo-se/festo-dev-fluid-control.git
cd festo-dev-fluid-control
pip install -e .
```

### Within a Virtual Environment

```bash
# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux / macOS

# Then install
pip install festo-dev-fluid-control
```

---

## Dependencies

| Package | Role |
|---|---|
| `festo-pgva` | Driver for the PGVA pressure generator (TCP/Modbus) |
| `festo-vaem` | Driver for the VAEM valve electronics module (TCP/Modbus) |
| `festo-dev-applied-motion` | Optional motion-axis support for mounted pipettors |

The PGVA and VAEM communicate over TCP/IP using Modbus. Network addresses are specified in the [configuration file](configuration/index.md).
