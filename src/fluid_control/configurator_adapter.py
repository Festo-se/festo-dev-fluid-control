# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG
# SPDX-License-Identifier: MIT
"""Configurator registrations for fluid-control runtime components."""

import logging
from collections.abc import Mapping
from typing import Any, cast

from configurator import COMPAT, ComponentDependency, ComponentView, Registration, RuntimeRegistry, ValidationMode
from applied_motion import Axis

from fluid_control.aspirator import Aspirator
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
    close_resources = getattr(instance, "_close_runtime_resources", None)
    if not callable(close_resources):
        raise TypeError("Fluid-control builder result must expose runtime cleanup")
    close_resources()


def _bind_runtime(instance: Any, runtime: RuntimeRegistry | None) -> Any:
    """Attach the shared session to a provider-built fluid component."""
    if runtime is not None:
        instance.registry = runtime
        instance._runtime_registry = runtime
    return instance


def _pipettor_dependencies(view: ComponentView) -> tuple[ComponentDependency, ...]:
    """Resolve an optional mount gantry only when it belongs to this source."""
    mount_gantry = view.get("mount_gantry")
    name = mount_gantry.get("name") if isinstance(mount_gantry, Mapping) else None
    components = view.root.get("components")
    if isinstance(name, str) and name and isinstance(components, Mapping) and name in components:
        return (ComponentDependency(name, "gantry", f"{view.path}.mount_gantry.name"),)
    return ()


def _pipettor_axes(
    view: ComponentView,
    options: Mapping[str, Any],
    dependencies: Mapping[str, Any],
) -> tuple[Axis | None, tuple[Axis, ...]]:
    """Resolve configured motion axis names against an optional built gantry."""
    mount_arm = cast(Axis | None, options.get("mount_arm")) if "mount_arm" in options else None
    disabled = tuple(cast(tuple[Axis, ...], options["disable_axes"])) if "disable_axes" in options else None
    mount_gantry = view.get("mount_gantry")
    gantry_name = mount_gantry.get("name") if isinstance(mount_gantry, Mapping) else None
    gantry = dependencies.get(gantry_name) if isinstance(gantry_name, str) else None
    if gantry is None:
        return mount_arm, disabled or ()

    axes = gantry.axes
    if "mount_arm" not in options:
        mount_axis = view.get(
            "mount_axis"
        )  # TODO: Check whether this is right or should only be from "mount_arm". Or vice-versa

        axis_name = mount_axis.get("name") if isinstance(mount_axis, Mapping) else mount_axis
        if isinstance(axis_name, str):
            if axis_name not in axes:
                raise ValueError(f"Configured mount axis {axis_name!r} is not present on gantry {gantry_name!r}")
            mount_arm = axes[axis_name]

    if disabled is None:
        configured_names = view.get("axes_disable_for_pickup", ())
        if not isinstance(configured_names, (list, tuple)):
            raise ValueError("axes_disable_for_pickup must be a list of gantry axis names")
        missing = [axis_name for axis_name in configured_names if axis_name not in axes]
        if missing:
            raise ValueError(f"Configured disabled axes {missing!r} are not present on gantry {gantry_name!r}")
        disabled = tuple(axes[axis_name] for axis_name in configured_names)
    return mount_arm, disabled


def _validate_component_view(view: ComponentView, expected_type: str) -> Mapping[str, Any]:
    """Validate the minimum view contract required by a fluid builder.

    Args:
        view: Selected configurator component view.
        expected_type: Runtime component type required by the builder.

    Returns:
        The selected component mapping, shared with the runtime instance.

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
    return view.data


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
    component = _validate_component_view(view, view.component_type)
    if view.root.get("spec_version") != "4.0":
        raise ValueError("Fluid-control configs require root spec_version '4.0'")
    control_modules = component["control_modules"]
    pressure_module = control_modules["pressure_generator"]
    valve_module = control_modules["valve"]
    active_channels = valve_module["active_valve_terminals"]
    pressure_interface = pressure_module["interface"]
    valve_interface = valve_module["interface"]
    _ = {
        "active_channel_count": len(active_channels),
        "channel_count": component["fluid-channel-count"],
        "pressure_module_name": pressure_module["name"],
        "pressure_module_uuid": pressure_module["uuid"],
        "pressure_interface_type": pressure_interface["type"],
        "pressure_interface_ip": pressure_interface["ip"],
        "pressure_interface_port": pressure_interface["port"],
        "valve_module_name": valve_module["name"],
        "valve_interface_type": valve_interface["type"],
        "valve_interface_ip": valve_interface["ip"],
        "valve_interface_port": valve_interface["port"],
    }
    for valve_info in valve_module["valve_type"].values():
        _ = valve_info["type"]["error-handling"]

    calibration = component["calibration"]
    for processes in calibration.values():
        for entry in processes.values():
            _ = entry["parameters"]["pressure"]
            _ = entry["flow_coefficients"]
            _ = entry["volume_offset_coefficients"]


def build_dispenser_from_view(
    view: ComponentView,
    *,
    mode: ValidationMode = COMPAT,
    options: Mapping[str, Any] | None = None,
    resolver: Any = None,
    runtime: RuntimeRegistry | None = None,
) -> Dispenser:
    """Build a dispenser from a selected configurator component view.

    Args:
        view: Selected and validated ``dispenser`` component view.
        mode: Configurator validation mode accepted by the builder protocol.
        options: Configurator build options accepted by the builder protocol.
        resolver: Configurator resolver accepted by the builder protocol.
        runtime: Shared runtime registry used to bind the built component.

    Returns:
        A dispenser initialized from the selected component mapping.

    Raises:
        TypeError: If the view does not satisfy the component-view contract.
        ValueError: If the view is not a dispenser component.
    """
    component = _validate_component_view(view, "dispenser")
    logger.debug("Building dispenser %r from selected configurator view", view.name)
    runtime_options = dict(options or {})
    instance = Dispenser._from_component_data(
        view.name,
        cast(dict, component),
        pressure_control=runtime_options.get("pressure_control"),
        valve_control=runtime_options.get("valve_control"),
    )
    return _bind_runtime(instance, runtime)


def build_pipettor_from_view(
    view: ComponentView,
    *,
    mode: ValidationMode = COMPAT,
    options: Mapping[str, Any] | None = None,
    resolver: Any = None,
    runtime: RuntimeRegistry | None = None,
    dependencies: Mapping[str, Any] | None = None,
) -> Pipettor:
    """Build a pipettor from a selected configurator component view.

    Args:
        view: Selected and validated ``pipettor`` component view.
        mode: Configurator validation mode accepted by the builder protocol.
        options: Configurator build options accepted by the builder protocol.
        resolver: Configurator resolver accepted by the builder protocol.
        runtime: Shared runtime registry used to bind the built component.
        dependencies: Already-built components required by this pipettor.

    Returns:
        A pipettor constructed through its existing compatibility signature.

    Raises:
        TypeError: If the view does not satisfy the component-view contract.
        ValueError: If the view is not a pipettor component.
    """
    component = _validate_component_view(view, "pipettor")
    logger.debug("Building pipettor %r from selected configurator view", view.name)
    runtime_options = dict(options or {})
    mount_arm, disable_axes = _pipettor_axes(view, runtime_options, dependencies or {})
    instance = Pipettor._from_component_data(
        view.name,
        cast(dict, component),
        mount_arm=mount_arm,
        disable_axes=disable_axes,
        pressure_control=runtime_options.get("pressure_control"),
        valve_control=runtime_options.get("valve_control"),
    )
    return _bind_runtime(instance, runtime)


def build_aspirator_from_view(
    view: ComponentView,
    *,
    mode: ValidationMode = COMPAT,
    options: Mapping[str, Any] | None = None,
    resolver: Any = None,
    runtime: RuntimeRegistry | None = None,
) -> Aspirator:
    """Build an aspirator from a selected configurator component view.

    Args:
        view: Selected and validated ``aspirator`` component view.
        mode: Configurator validation mode accepted by the builder protocol.
        options: Configurator build options accepted by the builder protocol.
        resolver: Configurator resolver accepted by the builder protocol.
        runtime: Shared runtime registry used to bind the built component.

    Returns:
        An aspirator constructed through its existing compatibility signature.

    Raises:
        TypeError: If the view does not satisfy the component-view contract.
        ValueError: If the view is not an aspirator component.
    """
    component = _validate_component_view(view, "aspirator")
    logger.debug("Building aspirator %r from selected configurator view", view.name)
    runtime_options = dict(options or {})
    instance = Aspirator._from_component_data(
        view.name,
        cast(dict, component),
        pressure_control=runtime_options.get("pressure_control"),
        valve_control=runtime_options.get("valve_control"),
    )
    return _bind_runtime(instance, runtime)


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
        schema_versions=frozenset({"3.0"}),
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
        component_dependencies=_pipettor_dependencies,
        schema_versions=frozenset({"3.0"}),
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
        schema_versions=frozenset({"3.0"}),
    )


def fluid_control_registrations() -> tuple[Registration, Registration, Registration]:
    """Return all fluid-control registrations in stable component order.

    Returns:
        Registrations for dispenser, pipettor, and aspirator components.
    """
    return dispenser_registration(), pipettor_registration(), aspirator_registration()
