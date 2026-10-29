# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG
# SPDX-License-Identifier: MIT
"""Configurator registrations for fluid-control runtime components."""

import logging
from collections.abc import Mapping
from typing import Any, cast

from configurator import COMPAT, ComponentView, Registration, ValidationMode
from applied_motion import Axis

from fluid_control.aspirator import Aspirator
from fluid_control.device_config import DeviceConfig
from fluid_control.dispenser import Dispenser
from fluid_control.pipettor import Pipettor

logger = logging.getLogger(__name__)


def _cleanup_fluid_control(instance: Any) -> None:
    """Close a configurator-built fluid-control instance.

    Args:
        instance: Fluid-control runtime object returned by a builder.

    Raises:
        TypeError: If the builder result does not expose a callable ``close`` method.
    """
    close = getattr(instance, "close", None)
    if not callable(close):
        raise TypeError("Fluid-control builder result must expose close()")
    close()


def _validate_component_view(view: ComponentView, expected_type: str) -> DeviceConfig:
    """Validate the minimum view contract required by a fluid builder.

    Args:
        view: Selected configurator component view.
        expected_type: Runtime component type required by the builder.

    Returns:
        A pre-resolved device configuration retaining the selected component mapping.

    Raises:
        TypeError: If ``view`` is not a configurator component view or its
            root/data/name fields are malformed.
        ValueError: If the view identifies a different component type.
    """
    if not isinstance(view, ComponentView):
        raise TypeError(f"Expected a ComponentView, got {type(view).__name__}")
    if view.component_type != expected_type:
        raise ValueError(f"Expected a {expected_type} component, got {view.component_type!r}")
    if not isinstance(view.name, str) or not view.name:
        raise TypeError("ComponentView name must be a non-empty string")
    if not isinstance(view.data, Mapping):
        raise TypeError("ComponentView data must be a mapping")
    if not isinstance(view.root, Mapping):
        raise TypeError("ComponentView root must be a mapping")
    # DeviceConfig is created from the already-selected component only. The
    # compatibility constructor receives this view and therefore does not
    # select or parse the component a second time.
    return DeviceConfig({"components": {view.name: cast(dict[str, Any], view.data)}}, view.name)


def validate_fluid_view(view: ComponentView, **_: Any) -> None:
    """Validate a selected fluid component without opening controllers.

    Args:
        view: Selected configurator component view.

    Raises:
        TypeError: If the selected view is malformed.
        ValueError: If the selected component type is unsupported.
        KeyError: If required fluid configuration fields are absent.
    """
    if view.component_type not in {"dispenser", "pipettor", "aspirator"}:
        raise ValueError(f"Unsupported fluid component type: {view.component_type!r}")
    device_config = _validate_component_view(view, view.component_type)
    device_config.build_pressures()
    for liquid_class, processes in device_config.calibration.items():
        for process in processes:
            device_config.flow_coefficients(liquid_class, process)
            device_config.volume_offset_coefficients(liquid_class, process)


def build_dispenser_from_view(
    view: ComponentView,
    *,
    mode: ValidationMode = COMPAT,
    options: Mapping[str, Any] | None = None,
    resolver: Any = None,
) -> Dispenser:
    """Build a dispenser from a selected configurator component view.

    Args:
        view: Selected and validated ``dispenser`` component view.
        mode: Configurator validation mode accepted by the builder protocol.
        options: Configurator build options accepted by the builder protocol.
        resolver: Configurator resolver accepted by the builder protocol.

    Returns:
        A dispenser constructed through its existing compatibility signature.

    Raises:
        TypeError: If the view does not satisfy the component-view contract.
        ValueError: If the view is not a dispenser component.
    """
    del mode, options, resolver
    device_config = _validate_component_view(view, "dispenser")
    logger.debug("Building dispenser %r from selected configurator view", view.name)
    return Dispenser(config={"components": {view.name: view.data}}, component_id=view.name, device_config=device_config)


def build_pipettor_from_view(
    view: ComponentView,
    *,
    mode: ValidationMode = COMPAT,
    options: Mapping[str, Any] | None = None,
    resolver: Any = None,
) -> Pipettor:
    """Build a pipettor from a selected configurator component view.

    Args:
        view: Selected and validated ``pipettor`` component view.
        mode: Configurator validation mode accepted by the builder protocol.
        options: Configurator build options accepted by the builder protocol.
        resolver: Configurator resolver accepted by the builder protocol.

    Returns:
        A pipettor constructed through its existing compatibility signature.

    Raises:
        TypeError: If the view does not satisfy the component-view contract.
        ValueError: If the view is not a pipettor component.
    """
    del mode, resolver
    device_config = _validate_component_view(view, "pipettor")
    logger.debug("Building pipettor %r from selected configurator view", view.name)
    runtime_options = dict(options or {})
    mount_arm: Axis | None = None
    disable_axes: tuple[Axis, ...] = ()
    if "mount_arm" in runtime_options:
        mount_arm = cast(Axis | None, runtime_options["mount_arm"])
    if "disable_axes" in runtime_options:
        disable_axes = cast(tuple[Axis, ...], tuple(runtime_options["disable_axes"]))
    return Pipettor(
        config={"components": {view.name: view.data}},
        component_id=view.name,
        device_config=device_config,
        mount_arm=mount_arm,
        disable_axes=disable_axes,
    )


def build_aspirator_from_view(
    view: ComponentView,
    *,
    mode: ValidationMode = COMPAT,
    options: Mapping[str, Any] | None = None,
    resolver: Any = None,
) -> Aspirator:
    """Build an aspirator from a selected configurator component view.

    Args:
        view: Selected and validated ``aspirator`` component view.
        mode: Configurator validation mode accepted by the builder protocol.
        options: Configurator build options accepted by the builder protocol.
        resolver: Configurator resolver accepted by the builder protocol.

    Returns:
        An aspirator constructed through its existing compatibility signature.

    Raises:
        TypeError: If the view does not satisfy the component-view contract.
        ValueError: If the view is not an aspirator component.
    """
    del mode, options, resolver
    device_config = _validate_component_view(view, "aspirator")
    logger.debug("Building aspirator %r from selected configurator view", view.name)
    return Aspirator(config={"components": {view.name: view.data}}, component_id=view.name, device_config=device_config)


def dispenser_registration() -> Registration:
    """Return the registration for dispenser components.

    Returns:
        Registration binding ``dispenser`` views to the dispenser builder.
    """
    return Registration(
        name="dispenser",
        component_type="dispenser",
        builder=build_dispenser_from_view,
        validator=validate_fluid_view,
        cleanup=_cleanup_fluid_control,
    )


def pipettor_registration() -> Registration:
    """Return the registration for pipettor components.

    Returns:
        Registration binding ``pipettor`` views to the pipettor builder.
    """
    return Registration(
        name="pipettor",
        component_type="pipettor",
        builder=build_pipettor_from_view,
        validator=validate_fluid_view,
        cleanup=_cleanup_fluid_control,
    )


def aspirator_registration() -> Registration:
    """Return the registration for aspirator components.

    Returns:
        Registration binding ``aspirator`` views to the aspirator builder.
    """
    return Registration(
        name="aspirator",
        component_type="aspirator",
        builder=build_aspirator_from_view,
        validator=validate_fluid_view,
        cleanup=_cleanup_fluid_control,
    )


def fluid_control_registrations() -> tuple[Registration, Registration, Registration]:
    """Return all fluid-control registrations in stable component order.

    Returns:
        Registrations for dispenser, pipettor, and aspirator components.
    """
    return dispenser_registration(), pipettor_registration(), aspirator_registration()
