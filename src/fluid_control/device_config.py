# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG
# SPDX-License-Identifier: MIT
# Provenance-ID: FLUID@8da843a2bf8f846e340913e72e5c03e696455e3b

"""
Typed loader for fluid-control device configuration.

Parses a raw instrument-configuration mapping once and exposes the
component-scoped values consumed by
[`PressureOverLiquidControl`][fluid_control.fluid_control.PressureOverLiquidControl] as typed
attributes, keeping configuration-parsing concerns out of the engine.
"""

from collections.abc import KeysView, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from configurator import load_source, normalize_root


@dataclass(frozen=True)
class InterfaceConfig:
    """
    Connection parameters for a hardware control module.

    Attributes:
        name (str): Control-module name (e.g. ``"pgva"`` or ``"vaem"``).
        interface_type (str): Transport identifier (e.g. ``"tcp/ip"``).
        ip (str): Host address of the controller.
        port (int): TCP port of the controller.
        unit_id (int): Modbus unit / slave id of the controller.
    """

    name: str
    interface_type: str
    ip: str
    port: int
    unit_id: int


class DeviceConfig:
    """Component-scoped view over a fluid-control instrument configuration.

    Resolves a single component from a full instrument-configuration mapping
    and exposes the derived values required to initialise the engine.

    Attributes:
        component_id (str): Key identifying the component within the config.
        raw (dict): The unmodified component-configuration mapping. Shared by
            reference with the engine so in-place calibration edits stay visible.
        active_channels (list[int]): Active valve-terminal indices.
        active_valve_count (int): Number of active valve terminals.
        channel_count (int): Declared fluid-channel count for the component.
        pressure_interface (InterfaceConfig): Pressure-controller connection.
        valve_interface (InterfaceConfig): Valve-controller connection.
        valve_error_handling (bool): Whether every valve enables error handling.
    """

    @staticmethod
    def _validate_component_data(component: Mapping[str, Any]) -> None:
        """Validate fields consumed by fluid-control initialization.

        Args:
            component: Selected component mapping from a normalized configuration.

        Raises:
            KeyError: If a required component or calibration field is missing.
            TypeError: If a required mapping does not support the expected access pattern.
        """
        control_modules = component["control_modules"]
        pressure_module = control_modules["pressure"]
        valve_module = control_modules["valve"]

        active_channels = valve_module["active_valve_terminals"]
        _ = len(active_channels)
        _ = component["fluid-channel-count"]

        pressure_interface = pressure_module["interface"]
        _ = (
            pressure_module["name"],
            pressure_interface["type"],
            pressure_interface["ip"],
            pressure_interface["port"],
            pressure_module["uuid"],
        )
        valve_interface = valve_module["interface"]
        _ = (
            valve_module["name"],
            valve_interface["type"],
            valve_interface["ip"],
            valve_interface["port"],
        )
        for valve_info in valve_module["valve_type"].values():
            _ = valve_info["type"]["error-handling"]

        calibration = component["calibration"]
        for processes in calibration.values():
            for entry in processes.values():
                _ = entry["parameters"]["pressure"]
                _ = entry["flow_coefficients"]
                _ = entry["volume_offset_coefficients"]

    def __init__(self, config: Mapping[str, Any] | str | Path, component_id: str) -> None:
        """Parse a component config from a full instrument config.

        Args:
            config: Mapping, JSON string, or path to a full instrument config.
                An optional ``component_config`` wrapper is normalized.
            component_id: Key identifying the component inside ``components``.
        """
        raw_config, _ = load_source(config)
        parsed_config = normalize_root(raw_config)
        self.component_id = component_id
        self.raw: dict = parsed_config["components"][component_id]
        self._validate_component_data(self.raw)

        control_modules = self.raw["control_modules"]
        pressure_module = control_modules["pressure"]
        valve_module = control_modules["valve"]

        self.active_channels: list[int] = valve_module["active_valve_terminals"]
        self.active_valve_count: int = len(self.active_channels)
        self.channel_count: int = self.raw["fluid-channel-count"]

        self.pressure_interface = InterfaceConfig(
            name=pressure_module["name"],
            interface_type=pressure_module["interface"]["type"],
            ip=pressure_module["interface"]["ip"],
            port=pressure_module["interface"]["port"],
            unit_id=pressure_module["uuid"],
        )
        # The VAEM controller is always addressed on Modbus unit id 1 regardless of
        # the ``uuid`` recorded in the configuration file.
        self.valve_interface = InterfaceConfig(
            name=valve_module["name"],
            interface_type=valve_module["interface"]["type"],
            ip=valve_module["interface"]["ip"],
            port=valve_module["interface"]["port"],
            unit_id=1,
        )
        self.valve_error_handling: bool = all(
            valve_info["type"]["error-handling"] for valve_info in valve_module["valve_type"].values()
        )

    @property
    def calibration(self) -> dict:
        """Return the live calibration mapping (liquid class -> process -> data)."""
        return self.raw["calibration"]

    def liquid_classes(self) -> KeysView[str]:
        """Return liquid-class keys in the current calibration mapping."""
        return self.calibration.keys()

    def build_pressures(self) -> dict:
        """Compute the per-liquid-class, per-process pressure mapping.

        Returns:
            Mapping shaped as ``{liquid_class: {process: pressure}}``.
        """
        pressures: dict = {}
        for liquid_class, processes in self.calibration.items():
            pressures[liquid_class] = {process: entry["parameters"]["pressure"] for process, entry in processes.items()}
        return pressures

    def flow_coefficients(self, liquid_class: str, process: str) -> dict:
        """Return flow coefficients for a liquid class and process."""
        return self.calibration[liquid_class][process]["flow_coefficients"]

    def volume_offset_coefficients(self, liquid_class: str, process: str) -> dict:
        """Return volume-offset coefficients for a liquid class and process."""
        return self.calibration[liquid_class][process]["volume_offset_coefficients"]
