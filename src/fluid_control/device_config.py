# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""
Typed loader for fluid-control device configuration.

Parses a raw instrument-configuration mapping once and exposes the
component-scoped values consumed by
[`PressureOverLiquidControl`][fluid_control.fluid_control.PressureOverLiquidControl] as typed
attributes, keeping configuration-parsing concerns out of the engine.
"""

from collections.abc import KeysView
from dataclasses import dataclass


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
    """
    Component-scoped view over a fluid-control instrument configuration.

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

    def __init__(self, config: dict, component_id: str) -> None:
        """
        Parse a component configuration from a full instrument config.

        Args:
            config (dict): Full instrument-configuration mapping. A
                ``"component_config"`` wrapper is unwrapped when present.
            component_id (str): Key identifying the component inside
                ``config["components"]``.

        """
        parsed_config = config.get("component_config", config)
        self.component_id = component_id
        self.raw: dict = parsed_config["components"][component_id]

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
        """Return the liquid-class keys present in the current calibration mapping."""
        return self.calibration.keys()

    def build_pressures(self) -> dict:
        """
        Compute the per-liquid-class, per-process pressure mapping.

        Returns:
            dict: ``{liquid_class: {process: pressure}}`` built from the live
            calibration mapping.

        """
        pressures: dict = {}
        for liquid_class, processes in self.calibration.items():
            pressures[liquid_class] = {process: entry["parameters"]["pressure"] for process, entry in processes.items()}
        return pressures

    def flow_coefficients(self, liquid_class: str, process: str) -> dict:
        """Return the flow-coefficient mapping for a liquid class and process."""
        return self.calibration[liquid_class][process]["flow_coefficients"]

    def volume_offset_coefficients(self, liquid_class: str, process: str) -> dict:
        """Return the volume-offset-coefficient mapping for a liquid class and process."""
        return self.calibration[liquid_class][process]["volume_offset_coefficients"]
