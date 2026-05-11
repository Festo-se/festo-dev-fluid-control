# Dispenser Examples

These examples walk through common dispensing workflows using the `Dispenser` class. Each example builds on the previous one. All examples assume a config file is available — see the [Configuration Guide](../configuration/index.md) for the full schema.

---

## 1. Loading a Configuration File

Configuration is stored as JSON and passed to `Dispenser` as a plain Python `dict`. Load it with the standard `json` module:

```python
import json
from fluid_control import Dispenser

with open("micro-dispenser-config.json") as fh:
    config = json.load(fh)
```

The `component_id` argument selects which component entry inside `config["component_config"]["components"]` to use. It must match a key in that dict exactly.

---

## 2. Basic Single-Channel Dispense

Instantiate a `Dispenser`, then call `dispense()` with a dict mapping channel IDs to operation parameters.

```python
import json
from fluid_control import Dispenser

with open("micro-dispenser-config.json") as fh:
    config = json.load(fh)

dispenser = Dispenser(config=config, component_id="micro-dispenser")

# Dispense 25 µL of water on channel 1
dispenser.dispense({
    1: {"volume": 25.0, "liquid_class": "water"}
})
```

`liquid_class` must match a key in the `calibration` section of the config (e.g. `"water"`, `"ethylene-glycol10%"`). The `Dispenser` automatically:

1. Looks up the calibration coefficients for the channel and liquid class.
2. Calculates the required valve opening time in milliseconds.
3. Commands the PGVA to the calibrated dispense pressure.
4. Opens the VAEM valve for the calculated duration.

---

## 3. Multi-Channel Dispense

To dispense across multiple channels simultaneously, add additional channel entries to the dict. All channels are armed before the VAEM is triggered, so they fire in parallel.

```python
dispenser.dispense({
    1: {"volume": 10.0, "liquid_class": "water"},
    2: {"volume": 15.0, "liquid_class": "water"},
})
```

!!! note
    All channels in a single `dispense()` call share one pressure setpoint. When mixing liquid classes with different calibrated pressures, the pressure of the **last** channel processed is applied. In practice, split calls by liquid class if their pressures differ.

---

## 4. Dispensing Multiple Liquid Classes

The `Dispenser` resolves calibration per channel from `liquid_class` in each command. Dispensing different liquid classes requires separate calls if their pressures differ:

```python
# First dispense: water at its calibrated pressure
dispenser.dispense({
    1: {"volume": 20.0, "liquid_class": "water"}
})

# Second dispense: ethylene glycol at its calibrated pressure
dispenser.dispense({
    1: {"volume": 20.0, "liquid_class": "ethylene-glycol10%"}
})
```

To see which liquid classes are configured for the current dispenser:

```python
print(list(dispenser.get_liquid_classes()))
# ['water', 'ethylene-glycol10%', 'third-liquid-class']
```

---

## 5. Using the Context Manager

`Dispenser` supports Python's context manager protocol. This is the recommended pattern when integrating with application code — the context manager ensures the instrument is properly cleaned up on exit, even if an exception is raised.

```python
import json
from fluid_control import Dispenser

with open("micro-dispenser-config.json") as fh:
    config = json.load(fh)

with Dispenser(config=config, component_id="micro-dispenser") as dispenser:
    dispenser.dispense({
        1: {"volume": 30.0, "liquid_class": "water"}
    })
# Pressure is released and valves are closed on __exit__
```

---

## 6. Checking Instrument Status

`get_status()` returns a snapshot of the pressure controller, valve controller, and internal fluid-control state:

```python
status = dispenser.get_status()
print(status)
# {
#   'pressure': {...},          # PGVA status dict
#   'vaem': {...},              # VAEM status dict
#   'fluid_control_status': 0  # 0 = clear, 1 = error, 2 = busy
# }
```

---

## 7. Direct Command (Raw Valve Timing)

`direct_command()` bypasses volume calibration entirely and sends raw pressure and valve-timing values. This is intended for **building calibration data**, not for production dispensing.

```python
# Open channel 1 for 120 ms at 70 mbar
result = dispenser.direct_command(
    channel_times={1: 120},
    pressure=70,
)
print(result)  # [0, 'Direct command executed successfully']
```

Combine this with a gravimetric balance to measure dispensed volumes at known opening times, then fit the slope/intercept coefficients for your config file.

---

## 8. Macro Dispenser with External Pressure Control

The macro-dispenser configuration uses an external pressure regulator (e.g. a VEAB channel on a motion controller) instead of a standalone PGVA. Pass pre-initialised `pressure_control` and `valve_control` objects to skip internal hardware initialisation:

```python
import json
from fluid_control import Dispenser, PressureControl
from applied_motion import Gantry

with open("test-fluid-configs.json") as fh:
    config = json.load(fh)

components = config["component_config"]

# Initialise the gantry (provides the VEAB pressure regulator)
gantry = Gantry.from_config(components)

# Initialise the micro-dispenser first (owns the VAEM connection)
micro_dispenser = Dispenser(config=components, component_id="micro-dispenser")

# Initialise the macro-dispenser, re-using the VAEM from the micro-dispenser
macro_dispenser = Dispenser(
    config=components,
    component_id="macro-dispenser",
    pressure_control=PressureControl(gantry),
    valve_control=micro_dispenser.valve_control,
)

macro_dispenser.dispense({
    2: {"volume": 50.0, "liquid_class": "water"}
})
```

---

## 9. Updating Calibration at Runtime

Calibration can be replaced without re-instantiating the `Dispenser`. `set_new_calibration()` accepts a calibration dict in the same format as the config file's `"calibration"` key:

```python
new_calibration = {
    "water": {
        "dispense": {
            "flow_coefficients": {
                "1": {"channel_index_coeff": 0.0, "flow_offset": 0.84}
            },
            "volume_offset_coefficients": {
                "1": {"channel_index_coeff": 0.31, "volume_offset": -4.9}
            },
            "parameters": {"pressure": 70}
        }
    }
}

dispenser.set_new_calibration(new_calibration)
```

All internal timing functions are rebuilt immediately from the new coefficients.

---

## 10. Iterating Over Channels

`Dispenser` implements `__iter__` and `__contains__`, so you can iterate over active channels or check membership:

```python
# Print all active channels
for channel in dispenser:
    print(f"Channel {channel} is active")

# Check whether a channel is configured
if 1 in dispenser:
    dispenser.dispense({1: {"volume": 10.0, "liquid_class": "water"}})
```

The total number of fluid channels is available via `len()`:

```python
print(len(dispenser))  # e.g. 2
```
