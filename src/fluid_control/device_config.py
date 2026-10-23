# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""
Typed loader for fluid-control device configuration.

Parses a raw instrument-configuration mapping once and exposes the
component-scoped values consumed by
[`PressureOverLiquidControl`][fluid_control.fluid_control.PressureOverLiquidControl] as typed
attributes, keeping configuration-parsing concerns out of the engine.
"""

from configurator.device_config import InterfaceConfig, DeviceConfig
