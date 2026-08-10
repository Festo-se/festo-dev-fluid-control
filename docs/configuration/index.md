# Configuration Reference

`festo-dev-fluid-control` uses a JSON configuration file to describe each instrument component, its hardware control modules, and its per-liquid-class calibration. This page explains the full schema and every field.

---

## Top-Level Structure

```json
{
    "_comment": "Human-readable description string — ignored by the library.",
    "spec_version": "3.0",
    "system_config": {
        "metadata": {}
    },
    "component_config": {
        "metadata": {},
        "components": {
            "<component_id>": { ... }
        }
    }
}
```

| Field                           | Type       | Description                                         |
| ------------------------------- | ---------- | --------------------------------------------------- |
| `spec_version`                | `string` | Config schema version. Current version is`"3.0"`. |
| `system_config`               | `object` | System-level metadata (reserved for future use).    |
| `component_config.components` | `object` | Map of`component_id` → component definition.     |

When you construct a `Dispenser`, the `component_id` argument selects the matching key from `component_config.components`.

---

## Component Fields

```json
"micro-dispenser": {
    "component_class": "dispenser",
    "uuid": "0000-000000000-000000-001",
    "type": "pressure-over-liquid",
    "fluid-channel-count": 2,
    "mounted": false,
    "control_modules": { ... },
    "calibration": { ... }
}
```

| Field                   | Type       | Description                                              |
| ----------------------- | ---------- | -------------------------------------------------------- |
| `component_class`     | `string` | Must be`"dispenser"` for `Dispenser` instances.      |
| `uuid`                | `string` | Unique identifier for this component. Used for auditing. |
| `type`                | `string` | Must be`"pressure-over-liquid"`.                       |
| `fluid-channel-count` | `int`    | Total number of fluid channels on the head.              |
| `mounted`             | `bool`   | `true` if the head is mounted on a motion axis.        |

### Mount Axis (Mounted Heads Only)

When `mounted` is `true`, the following fields describe the motion axis:

```json
"mount_axis": {
    "name": "Z",
    "index": 3,
    "uuid": "TODO"
},
"mount_axis_control": {
    "type": "CODESYS-PLC",
    "control_mode": "python",
    "control_package": "festo-applied-motion",
    ...
    "index": 3
}
```

For a static (non-mounted) `Dispenser`, these fields are still present in the schema but are not used by the library — pass `mount_arm=None` (the default) to the constructor.

---

## `control_modules`

Defines the hardware controllers: one pressure source and one valve controller.

```json
"control_modules": {
    "pressure": { ... },
    "valve": { ... }
}
```

### Pressure Controller (`"pressure"`)

Two pressure-source types are supported:

#### Standalone PGVA

Used for the micro-dispenser configuration. The library constructs a `PGVA` instance directly from this block.

```json
"pressure": {
    "type": "generator",
    "passed-by-init": false,
    "name": "pgva",
    "uuid": 1,
    "interface": {
        "type": "tcp/ip",
        "ip": "192.168.10.102",
        "port": 502
    }
}
```

| Field              | Type       | Description                                                           |
| ------------------ | ---------- | --------------------------------------------------------------------- |
| `passed-by-init` | `bool`   | `false` — the library initialises the PGVA from this config block. |
| `name`           | `string` | Must contain`"pgva"`. Used to select the PGVA driver.               |
| `uuid`           | `int`    | Modbus unit ID for the PGVA.                                          |
| `interface.ip`   | `string` | IP address of the PGVA on the instrument network.                     |
| `interface.port` | `int`    | TCP port (typically`502` for Modbus).                               |

#### External Pressure Regulator (e.g. VEAB via Gantry)

Used for the macro-dispenser configuration where pressure is controlled through an already-initialised motion controller. Pass the controller in via the `pressure_control` argument to the constructor.

```json
"pressure": {
    "type": "regulator",
    "passed-by-init": true,
    "name": "veab",
    "channel": 2,
    ...
}
```

| Field              | Type       | Description                                                                        |
| ------------------ | ---------- | ---------------------------------------------------------------------------------- |
| `passed-by-init` | `bool`   | `true` — the caller provides a `PressureControl` object at construction time. |
| `name`           | `string` | Informational; not used for driver selection when`passed-by-init` is `true`.   |

### Valve Controller (`"valve"`)

Describes the VAEM valve electronics module.

```json
"valve": {
    "type": "valve",
    "passed-by-init": false,
    "name": "vaem",
    "valve_count": 1,
    "active_valve_terminals": [1],
    "valve_type": {
        "1": {
            "typecode": "VYKA",
            "type": {
                "ports": 2,
                "switching-positions": 2,
                "closure": "NC",
                "operational-mechanism": "direct",
                "actuation-principle": "solenoid",
                "latching": false,
                "media-separated": false,
                "error-handling": true
            }
        }
    },
    "uuid": 2,
    "interface": {
        "type": "tcp/ip",
        "ip": "192.168.10.27",
        "port": 502
    }
}
```

| Field                      | Type       | Description                                                                                                        |
| -------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------ |
| `passed-by-init`         | `bool`   | `false` — library constructs a VAEM; `true` — pass an existing VAEM in via `valve_control`.                |
| `name`                   | `string` | Must contain`"vaem"`.                                                                                            |
| `active_valve_terminals` | `int[]`  | List of VAEM terminal indices that are physically connected and active.                                            |
| `valve_type`             | `object` | Per-terminal valve spec. The`"error-handling"` field enables the VAEM hardware error-handling feature per valve. |
| `uuid`                   | `int`    | Modbus unit ID for the VAEM.                                                                                       |
| `interface.ip`           | `string` | IP address of the VAEM.                                                                                            |
| `interface.port`         | `int`    | TCP port (typically`502`).                                                                                       |

---

## `calibration`

The calibration block maps liquid classes to process-specific (dispense/aspirate) coefficients. These coefficients are fit from empirical data — see the [Direct Command example](../examples/examples.md#7-direct-command-raw-valve-timing) for how to gather calibration data.

```json
"calibration": {
    "<liquid_class>": {
        "<process>": {
            "flow_coefficients": {
                "<channel_id>": {
                    "channel_index_coeff": 0.0,
                    "flow_offset": 0.826181241
                }
            },
            "volume_offset_coefficients": {
                "<channel_id>": {
                    "channel_index_coeff": 0.321305707,
                    "volume_offset": -4.857648804
                }
            },
            "parameters": {
                "pressure": 70
            }
        }
    }
}
```

### Liquid Classes

Any string key is valid for `<liquid_class>`. Examples from the reference configurations:

| Liquid Class Key         | Description                                       |
| ------------------------ | ------------------------------------------------- |
| `"water"`              | Aqueous buffer, low viscosity baseline            |
| `"ethylene-glycol10%"` | 10 % ethylene glycol, slightly elevated viscosity |
| `"third-liquid-class"` | Placeholder for an additional fluid               |

!!! tip
    The liquid class string in the config must exactly match the `liquid_class` key you pass to `dispense()` at runtime.

### Processes

| Process Key    | Used By                     |
| -------------- | --------------------------- |
| `"dispense"` | `Dispenser`, `Pipettor` |
| `"aspirate"` | `Pipettor` only           |

`Dispenser` will raise `NotImplementedError` if `aspirate` is called.

### Calibration Coefficients

The library uses a two-term linear model to translate volume (µL) to valve opening time (ms):

$$
t_{open} = m(n) \cdot V + b(n)
$$

Where:

- $V$ is the target volume in µL
- $n$ is the number of simultaneously active channels
- $m(n)$ is the slope (ms/µL), interpolated from `channel_index_coeff` and `flow_offset`
- $b(n)$ is the intercept (ms), interpolated from `channel_index_coeff` and `volume_offset`

| Coefficient Field                                      | Description                                                    |
| ------------------------------------------------------ | -------------------------------------------------------------- |
| `flow_coefficients[ch].channel_index_coeff`          | Slope of slope vs. active-channel count                        |
| `flow_coefficients[ch].flow_offset`                  | Slope at single-channel (intercept of the slope line)          |
| `volume_offset_coefficients[ch].channel_index_coeff` | Slope of intercept vs. active-channel count                    |
| `volume_offset_coefficients[ch].volume_offset`       | Intercept at single-channel                                    |
| `parameters.pressure`                                | PGVA output pressure in mbar for this liquid class and process |

### Channel IDs in Calibration

The `channel_id` keys inside `flow_coefficients` and `volume_offset_coefficients` are **strings** that correspond to the VAEM terminal index — they must match the values listed in `active_valve_terminals`.

For example, if `active_valve_terminals` is `[1]`, the calibration channel key must be `"1"`.

---

## Complete Minimal Example

The following is a minimal working config for a single-channel micro-dispenser with one liquid class:

```json
{
    "spec_version": "3.0",
    "system_config": {"metadata": {}},
    "component_config": {
        "metadata": {},
        "components": {
            "my-dispenser": {
                "component_class": "dispenser",
                "uuid": "0000-000000000-000000-001",
                "type": "pressure-over-liquid",
                "fluid-channel-count": 1,
                "mounted": false,
                "control_modules": {
                    "pressure": {
                        "type": "generator",
                        "passed-by-init": false,
                        "name": "pgva",
                        "uuid": 1,
                        "interface": {
                            "type": "tcp/ip",
                            "ip": "192.168.1.10",
                            "port": 502
                        }
                    },
                    "valve": {
                        "type": "valve",
                        "passed-by-init": false,
                        "name": "vaem",
                        "valve_count": 1,
                        "active_valve_terminals": [1],
                        "valve_type": {
                            "1": {
                                "typecode": "VYKA",
                                "type": {
                                    "ports": 2,
                                    "switching-positions": 2,
                                    "closure": "NC",
                                    "operational-mechanism": "direct",
                                    "actuation-principle": "solenoid",
                                    "latching": false,
                                    "media-separated": false,
                                    "error-handling": true
                                }
                            }
                        },
                        "uuid": 2,
                        "interface": {
                            "type": "tcp/ip",
                            "ip": "192.168.1.11",
                            "port": 502
                        }
                    }
                },
                "calibration": {
                    "water": {
                        "dispense": {
                            "flow_coefficients": {
                                "1": {
                                    "channel_index_coeff": 0.0,
                                    "flow_offset": 0.826
                                }
                            },
                            "volume_offset_coefficients": {
                                "1": {
                                    "channel_index_coeff": 0.321,
                                    "volume_offset": -4.858
                                }
                            },
                            "parameters": {
                                "pressure": 70
                            }
                        }
                    }
                }
            }
        }
    }
}
```
