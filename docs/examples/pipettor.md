# Pipettor Examples

These examples walk through common pipetting workflows using the `Pipettor` class.
The `Pipettor` extends the `Dispenser` capabilities with **aspirate**, **mix**, and
**tip-handling** operations. If you are new to the library, read the
[Dispenser Examples](examples.md) first — configuration loading, multi-channel
commands, context managers, and status inspection work identically here.

All examples assume a config file is available — see the
[Configuration Guide](../configuration/index.md) for the full schema. Runnable
versions of these snippets live in the repository under `examples/pipettor/`.

---

## 1. Loading a Configuration

As with the `Dispenser`, configuration is a plain Python `dict`. You can load your
own JSON file, or use the bundled example configuration (which ships inside the
installed package and defines a `pipettor` component):

```python
from fluid_control import Pipettor
from fluid_control.reference_config import load_example_config

config = load_example_config()

pipettor = Pipettor(config=config, component_id="pipettor")
```

To load your own file instead:

```python
import json
from fluid_control import Pipettor

with open("pipettor-config.json") as fh:
    config = json.load(fh)

pipettor = Pipettor(config=config, component_id="pipettor")
```

The `component_id` must match a key in `config["component_config"]["components"]`
whose `component_class` is `"pipettor"`.

---

## 2. Aspirate and Dispense (Basic Transfer)

A transfer aspirates a volume, then dispenses it. Both operations take the same
channel-command mapping (`{channel: {"volume": µL, "liquid_class": str}}`) but use
different calibration processes (`aspirate` / `dispense`), each with its own
calibrated pressure.

```python
pipettor.aspirate({1: {"volume": 50.0, "liquid_class": "water"}})
pipettor.dispense({1: {"volume": 50.0, "liquid_class": "water"}})
```

!!! note
    `aspirate` requires an `"aspirate"` calibration block for the liquid class,
    and `dispense` requires a `"dispense"` block. A `Dispenser` supports only
    `dispense`; calling `aspirate` on one raises `NotImplementedError`.

---

## 3. Multi-Channel Aspirate

Add more channel entries to operate on several channels in parallel. All channels
are armed before the valve controller is triggered, so they fire together.

```python
pipettor.aspirate({
    1: {"volume": 40.0, "liquid_class": "water"},
    2: {"volume": 40.0, "liquid_class": "water"},
})
```

The valve-opening time is computed per channel from the calibration, and the
active-channel count feeds the calibration model — so per-channel timing accounts
for how many channels fire simultaneously.

---

## 4. Mixing

`mix()` repeatedly aspirates and dispenses the same volume to homogenise the
liquid in the channel. The number of aspirate/dispense cycles is given by
`cycles`:

```python
# Mix 20 µL up and down for 3 cycles on channel 1
pipettor.mix({1: {"volume": 20.0, "liquid_class": "water"}}, cycles=3)
```

---

## 5. Tip Handling (Pickup and Eject)

Tip handling requires a **mounted** (non-static) pipettor. The mount arm (a motion
axis) drives down onto the tips until engagement stalls its motion, and pneumatic
actuation ejects them. The mount arm and the lateral axes to disable during
engagement come from a connected `Gantry` — `gantry.axes` maps axis names to
`Axis` instances. Match the axis names to the component's `mount_axis` and
`axes_disable_for_pickup` config fields:

```python
import json
from applied_motion import Gantry
from fluid_control import Pipettor

with open("test-fluid-configs.json") as fh:
    config = json.load(fh)

components = config["component_config"]

# The pipettor's mount axis ("ZP") and disabled X/Y axes live on "gantry_2".
gantry = Gantry.from_config(components, name="gantry_2")

pipettor = Pipettor(
    config=components,
    component_id="pipettor_1",
    mount_arm=gantry.axes["ZP"],
    disable_axes=(gantry.axes["X"], gantry.axes["Y"]),
)

pickup = pipettor.pickup_tips(duration=0.5)
print(pickup.code, pickup.message)   # 0 'Tips picked up successfully'

eject = pipettor.eject_tips()
print(eject.code, eject.message)     # 0 'Tips ejected successfully'
```

!!! warning
    Calling `pickup_tips()` or `eject_tips()` on a **static** pipettor (one
    constructed without a `mount_arm`) raises `NotImplementedError`. Tip handling
    currently assumes a co-mounted, dynamic tip-ejection mechanism.

Both methods return an
[`OperationResult`](../configuration/index.md), a `(code, message)` named tuple.
`code` is `0` on success, `1` on error, `2` on busy. The fields are available both
by name (`result.code`, `result.message`) and by position (`result[0]`,
`result[1]`).

---

## 6. Using the Context Manager

Like the `Dispenser`, `Pipettor` supports the context-manager protocol. This is
the recommended pattern for application code — pressure is released and valves are
closed on exit, even if an exception is raised.

```python
from fluid_control import Pipettor
from fluid_control.reference_config import load_example_config

config = load_example_config()

with Pipettor(config=config, component_id="pipettor") as pipettor:
    pipettor.aspirate({1: {"volume": 50.0, "liquid_class": "water"}})
    pipettor.dispense({1: {"volume": 50.0, "liquid_class": "water"}})
# Pressure released and valves closed on __exit__
```

---

## 7. Checking Liquid Classes and Status

The introspection helpers behave exactly as they do for the `Dispenser`:

```python
# Which liquid classes are configured?
print(list(pipettor.get_liquid_classes()))
# ['water']

# Snapshot of pressure controller, valve controller, and internal state
status = pipettor.get_status()
print(status["fluid_control_status"])   # 0 = clear, 1 = error, 2 = busy
```

---

## See Also

- [Dispenser Examples](examples.md) — fixed-volume dispensing, multi-channel
  commands, direct calibration commands, and runtime calibration updates.
- [Configuration Reference](../configuration/index.md) — the full config schema,
  including the `aspirate` calibration process used by the `Pipettor`.
