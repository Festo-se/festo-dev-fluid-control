"""Unit tests for fluid-control configurator registrations and builders."""

from unittest.mock import MagicMock
from types import SimpleNamespace

import pytest
from configurator import (
    BuilderError,
    ComponentDependency,
    ComponentView,
    Configurator,
    Registration,
    Registry,
    RuntimeRegistry,
    SelectionError,
    ValidationError,
)

from fluid_control.aspirator import Aspirator
from fluid_control.configurator_adapter import (
    aspirator_registration,
    build_aspirator_from_view,
    build_dispenser_from_view,
    build_pipettor_from_view,
    dispenser_registration,
    fluid_control_registrations,
    pipettor_registration,
)
from fluid_control.dispenser import Dispenser
from fluid_control.pipettor import Pipettor


def _view(config: dict, component_id: str, component_type: str) -> ComponentView:
    """Create the selected view shape returned by configurator bootstrap."""
    component = config["components"][component_id]
    return ComponentView(
        component_id, component_type, component, config, f"components.{component_id}", config["components"]
    )


def _mock_controllers(mocker) -> None:
    """Patch hardware drivers with realistic no-hardware controller doubles."""
    pressure = MagicMock()
    pressure.get_output_pressure.side_effect = lambda: pressure.set_output_pressure.call_args.kwargs["pressure"]
    valve = MagicMock()
    valve.get_status.return_value = {"Readiness": 0}
    mocker.patch("fluid_control.fluid_control.PGVA", return_value=pressure)
    mocker.patch("fluid_control.fluid_control.VAEM", return_value=valve)
    mocker.patch("fluid_control.fluid_control.sleep")


def _managed_controller_doubles() -> tuple[MagicMock, MagicMock, MagicMock, MagicMock]:
    """Return realistic controller wrappers and their backend close mocks."""
    pressure = MagicMock()
    pressure_client = MagicMock()
    pressure._backend = SimpleNamespace(client=pressure_client)
    pressure.get_output_pressure.side_effect = lambda: pressure.set_output_pressure.call_args.kwargs["pressure"]
    valve = MagicMock()
    valve_backend = MagicMock()
    valve._backend = valve_backend
    valve.get_status.return_value = {"Readiness": 0}
    return pressure, valve, pressure_client, valve_backend.close_client


def test_registration_metadata_and_dispatch(dispenser_config, eight_channel_pipettor_config):
    """Registrations expose the expected logical names and builders."""
    registrations = fluid_control_registrations()
    registry = Registry.compose(*registrations)
    dispenser_view = _view(dispenser_config, "dispenser_1", "dispenser")
    pipettor_view = _view(eight_channel_pipettor_config, "pipettor_1", "pipettor")

    assert all(isinstance(registration, Registration) for registration in registrations)
    assert [(registration.name, registration.component_type) for registration in registrations] == [
        ("dispenser", "dispenser"),
        ("pipettor", "pipettor"),
        ("aspirator", "aspirator"),
    ]
    assert registrations[0].builder is build_dispenser_from_view
    assert registrations[1].builder is build_pipettor_from_view
    assert registrations[2].builder is build_aspirator_from_view
    assert registry.get(dispenser_view).builder is build_dispenser_from_view
    assert registry.get(pipettor_view).builder is build_pipettor_from_view
    assert all(callable(registration.cleanup) for registration in registrations)
    assert all(callable(registration.validator) for registration in registrations)
    assert all(registration.schema_versions == frozenset({"3.0"}) for registration in registrations)


def test_pipettor_builder_passes_explicit_runtime_axes(mocker, eight_channel_pipettor_config):
    mount_arm = MagicMock()
    disabled = (MagicMock(), MagicMock())
    pipettor = MagicMock(spec=Pipettor)
    builder = mocker.patch("fluid_control.configurator_adapter.Pipettor._from_component_data", return_value=pipettor)

    build_pipettor_from_view(
        _view(eight_channel_pipettor_config, "pipettor_1", "pipettor"),
        options={"mount_arm": mount_arm, "disable_axes": disabled},
    )

    assert builder.call_args.kwargs["mount_arm"] is mount_arm
    assert builder.call_args.kwargs["disable_axes"] == disabled


def test_pipettor_builder_resolves_configured_motion_axes_from_gantry_dependency(
    mocker, eight_channel_pipettor_config
):
    from types import SimpleNamespace

    component = eight_channel_pipettor_config["components"]["pipettor_1"]
    component["mount_gantry"] = {"name": "gantry_2"}
    component["mount_axis"] = {"name": "ZP"}
    component["axes_disable_for_pickup"] = ["X", "Y"]
    axes = {name: MagicMock(name=name) for name in ("X", "Y", "ZP")}
    gantry = SimpleNamespace(axes=axes)
    pipettor = MagicMock(spec=Pipettor)
    builder = mocker.patch("fluid_control.configurator_adapter.Pipettor._from_component_data", return_value=pipettor)

    build_pipettor_from_view(
        _view(eight_channel_pipettor_config, "pipettor_1", "pipettor"),
        dependencies={"gantry_2": gantry},
    )

    assert builder.call_args.kwargs["mount_arm"] is axes["ZP"]
    assert builder.call_args.kwargs["disable_axes"] == (axes["X"], axes["Y"])


def test_pipettor_registration_declares_same_source_gantry_dependency(eight_channel_pipettor_config):
    component = eight_channel_pipettor_config["components"]["pipettor_1"]
    component["mount_gantry"] = {"name": "gantry_2"}
    eight_channel_pipettor_config["components"]["gantry_2"] = {"component_class": "gantry", "axes": {}}

    dependency_callback = pipettor_registration().component_dependencies
    assert dependency_callback is not None
    dependencies = dependency_callback(_view(eight_channel_pipettor_config, "pipettor_1", "pipettor"))

    assert dependencies == (ComponentDependency("gantry_2", "gantry", "components.pipettor_1.mount_gantry.name"),)


def test_missing_pipettor_gantry_reference_fails_before_builder(mocker, eight_channel_pipettor_config):
    eight_channel_pipettor_config["components"]["pipettor_1"]["mount_gantry"] = {"name": "missing_gantry"}
    built = []
    mocker.patch(
        "fluid_control.configurator_adapter.Pipettor._from_component_data",
        side_effect=lambda *args, **kwargs: built.append(args[0]),
    )

    with pytest.raises(SelectionError) as error:
        Configurator.bootstrap(
            eight_channel_pipettor_config,
            "pipettor_1",
            Registry([pipettor_registration()]),
        )

    assert error.value.code == "MISSING_RELATIONSHIP"
    assert error.value.path == "components.pipettor_1.mount_gantry.name"
    assert built == []


def test_config_backed_pipettor_builds_related_gantry_and_exposes_shared_runtime(
    monkeypatch, mocker, eight_channel_pipettor_config, dispenser_config
):
    from applied_motion.configurator_adapter import gantry_registration

    class EntryPoint:
        def __init__(self, name, provider):
            self.name = name
            self._provider = provider

        def load(self):
            return self._provider

    class EntryPoints(list):
        def select(self, *, group):
            assert group == RuntimeRegistry.entry_point_group
            return self

    component = eight_channel_pipettor_config["components"]["pipettor_1"]
    component["mount_gantry"] = {"name": "gantry_2"}
    component["mount_axis"] = {"name": "ZP"}
    component["axes_disable_for_pickup"] = ["X", "Y"]
    axes = {name: MagicMock(name=name) for name in ("X", "Y", "ZP")}
    gantry_component = {
        "component_class": "gantry",
        "component_spec_version": "3.0",
        "backend": "modbus",
        "axes": {name: {"name": name, "ip": f"192.168.0.{index}"} for index, name in enumerate(axes, 10)},
        "axis_order": ["X", "Y", "ZP"],
    }
    config = {
        "spec_version": "4.0",
        "components": {
            **eight_channel_pipettor_config["components"],
            **dispenser_config["components"],
            "gantry_2": gantry_component,
        }
    }
    providers = EntryPoints(
        [
            EntryPoint("pipettor", pipettor_registration),
            EntryPoint("dispenser", dispenser_registration),
            EntryPoint("gantry", gantry_registration),
        ]
    )
    monkeypatch.setattr("configurator.kernel.entry_points", lambda: providers)
    mocker.patch("fluid_control.fluid_control.PGVA", return_value=MagicMock())
    mocker.patch("fluid_control.fluid_control.VAEM", return_value=MagicMock(get_status=MagicMock(return_value={"Readiness": 0})))
    mocker.patch("fluid_control.fluid_control.sleep")
    mocker.patch("applied_motion.gantry_factory.EdconAxis", autospec=True, side_effect=list(axes.values()))

    pipettor = Pipettor(config=config, component_id="pipettor_1")

    assert isinstance(pipettor.registry, RuntimeRegistry)
    assert pipettor.registry.components == ("gantry_2", "pipettor_1")
    assert pipettor.mount_arm is axes["ZP"]
    assert pipettor.disable_axes == (axes["X"], axes["Y"])

    pressure_control = MagicMock()
    valve_control = MagicMock()
    dispenser = Dispenser(
        config=config,
        component_id="dispenser_1",
        registry=pipettor.registry,
        pressure_control=pressure_control,
        valve_control=valve_control,
    )

    assert dispenser.registry is pipettor.registry
    assert dispenser._runtime_registry is pipettor.registry
    assert dispenser.pressure_control is pressure_control
    assert dispenser.valve_control is valve_control
    assert pipettor.registry.components == ("gantry_2", "pipettor_1", "dispenser_1")
    with pytest.raises(ValueError, match="already initialized with a different pressure_control"):
        Dispenser(
            config=config,
            component_id="dispenser_1",
            registry=pipettor.registry,
            pressure_control=MagicMock(),
        )
    dispenser.close()
    assert pipettor.registry.closed is False
    pipettor.close()
    assert pipettor.registry.closed is True
    pressure_control.close.assert_not_called()
    valve_control.close.assert_not_called()


def test_fluid_registration_preflight_rejects_missing_calibration(mocker, dispenser_config):
    del dispenser_config["components"]["dispenser_1"]["calibration"]
    factory = mocker.patch("fluid_control.configurator_adapter.Dispenser")

    with pytest.raises(ValidationError):
        Configurator.bootstrap(
            dispenser_config,
            "dispenser_1",
            Registry.compose(*fluid_control_registrations()),
        )

    factory.assert_not_called()


def test_bootstrap_result_closes_builder_created_controller_connections(mocker, dispenser_config):
    """Bootstrap cleanup invokes the fluid instance lifecycle exactly once."""
    pressure, valve, pressure_client, valve_close = _managed_controller_doubles()
    mocker.patch("fluid_control.fluid_control.PGVA", return_value=pressure)
    mocker.patch("fluid_control.fluid_control.VAEM", return_value=valve)
    mocker.patch("fluid_control.fluid_control.sleep")

    result = Configurator.bootstrap(
        dispenser_config,
        "dispenser_1",
        Registry.compose(*fluid_control_registrations()),
    )
    result.close()
    result.close()

    pressure_client.close.assert_called_once_with()
    valve_close.assert_called_once_with()


@pytest.mark.parametrize(
    ("registration_factory", "builder"),
    [
        (dispenser_registration, build_dispenser_from_view),
        (pipettor_registration, build_pipettor_from_view),
        (aspirator_registration, build_aspirator_from_view),
    ],
)
def test_individual_registration_factories(registration_factory, builder):
    """Each factory binds exactly its corresponding builder."""
    assert registration_factory().builder is builder


def test_builders_return_all_runtime_classes(mocker, dispenser_config, eight_channel_pipettor_config):
    """Selected views construct the three concrete runtime classes."""
    _mock_controllers(mocker)
    dispenser_view = _view(dispenser_config, "dispenser_1", "dispenser")
    pipettor_view = _view(eight_channel_pipettor_config, "pipettor_1", "pipettor")
    aspirator_component = dict(dispenser_config["components"]["dispenser_1"])
    aspirator_component["component_class"] = "aspirator"
    aspirator_config = {"components": {"aspirator_1": aspirator_component}}
    aspirator_view = _view(aspirator_config, "aspirator_1", "aspirator")

    assert isinstance(build_dispenser_from_view(dispenser_view), Dispenser)
    assert isinstance(build_pipettor_from_view(pipettor_view), Pipettor)
    assert isinstance(build_aspirator_from_view(aspirator_view), Aspirator)


def test_all_fluid_builders_use_injected_controller_options(mocker, dispenser_config, eight_channel_pipettor_config):
    _mock_controllers(mocker)
    dispenser_view = _view(dispenser_config, "dispenser_1", "dispenser")
    pipettor_view = _view(eight_channel_pipettor_config, "pipettor_1", "pipettor")
    aspirator_component = dict(dispenser_config["components"]["dispenser_1"])
    aspirator_component["component_class"] = "aspirator"
    aspirator_config = {"components": {"aspirator_1": aspirator_component}}
    aspirator_view = _view(aspirator_config, "aspirator_1", "aspirator")

    for builder, view in (
        (build_dispenser_from_view, dispenser_view),
        (build_pipettor_from_view, pipettor_view),
        (build_aspirator_from_view, aspirator_view),
    ):
        pressure_control = MagicMock()
        valve_control = MagicMock()
        instance = builder(
            view,
            options={"pressure_control": pressure_control, "valve_control": valve_control},
        )

        assert instance.pressure_control is pressure_control
        assert instance.valve_control is valve_control


def test_bootstrap_selected_view_preserves_component_mapping_behavior(mocker, dispenser_config):
    """A configurator-selected component is shared directly with the runtime instance."""
    _mock_controllers(mocker)
    selected_component = dispenser_config["components"]["dispenser_1"]

    result = Configurator.bootstrap(
        dispenser_config,
        "dispenser_1",
        Registry.compose(*fluid_control_registrations()),
    )
    dispenser = result.instance

    assert dispenser.config is selected_component
    assert dispenser.active_channels == [1, 2]
    assert dispenser.active_valve_count == 2
    assert dispenser.pressure_control_config.ip == "192.168.10.102"
    assert dispenser.pressure_control_config.port == 502
    assert dispenser.pressure_control_config.unit_id == 1
    assert dispenser.valve_control_config.ip == "192.168.10.27"
    assert dispenser.valve_control_config.port == 502
    assert dispenser.valve_control_config.unit_id == 1
    assert dispenser.valve_error_handling is True

    selected_component["calibration"]["water"]["dispense"]["parameters"]["pressure"] = 999
    assert dispenser.pressures["water"]["dispense"] == 70
    dispenser.set_pressures()
    assert dispenser.pressures["water"]["dispense"] == 999

    result.close()


def test_provider_initializes_selected_component_only_once(mocker, dispenser_config):
    """The provider initializes the selected mapping without recursive parsing."""
    _mock_controllers(mocker)
    initialize = mocker.spy(Dispenser, "_initialize_component_data")

    result = Configurator.bootstrap(
        dispenser_config,
        "dispenser_1",
        Registry.compose(*fluid_control_registrations()),
    )

    assert result.instance.component_id == "dispenser_1"
    assert result.instance.config is dispenser_config["components"]["dispenser_1"]
    initialize.assert_called_once()
    result.close()


def test_aspirator_retains_aspirate_capability(mocker, dispenser_config):
    """The aspirator builder keeps the aspiration operation on its runtime class."""
    _mock_controllers(mocker)
    component = dispenser_config["components"]["dispenser_1"]
    component["component_class"] = "aspirator"
    aspirator = build_aspirator_from_view(_view(dispenser_config, "dispenser_1", "aspirator"))
    handle_liquid = mocker.patch.object(aspirator, "_handle_liquid")
    command = {1: {"volume": 50.0, "liquid_class": "water"}}

    aspirator.aspirate(command)

    handle_liquid.assert_called_once_with(command, process="aspirate")
    aspirator.close()


@pytest.mark.parametrize(
    ("runtime_class", "config_fixture", "component_id"),
    [
        (Dispenser, "dispenser_config", "dispenser_1"),
        (Pipettor, "eight_channel_pipettor_config", "pipettor_1"),
        (Aspirator, "dispenser_config", "dispenser_1"),
    ],
)
def test_direct_constructors_preserve_injected_controllers(runtime_class, config_fixture, component_id, request):
    """All concrete classes retain caller-owned pressure and valve injection."""
    config = request.getfixturevalue(config_fixture)
    component = config["components"][component_id]
    if runtime_class is Aspirator:
        component["component_class"] = "aspirator"
    pressure = MagicMock()
    valve = MagicMock()

    instance = runtime_class(
        config=config,
        component_id=component_id,
        pressure_control=pressure,
        valve_control=valve,
    )

    assert instance.pressure_control is pressure
    assert instance.valve_control is valve
    assert instance.config == component
    assert not hasattr(instance, "device_config")
    instance.close()
    pressure.close.assert_not_called()
    valve.close.assert_not_called()


def test_bootstrap_selected_view_aggregates_valve_error_handling(mocker, dispenser_config):
    """The selected view preserves false aggregation when one valve disables handling."""
    _mock_controllers(mocker)
    valve_types = dispenser_config["components"]["dispenser_1"]["control_modules"]["valve"]["valve_type"]
    valve_types["2"]["type"]["error-handling"] = False

    result = Configurator.bootstrap(
        dispenser_config,
        "dispenser_1",
        Registry.compose(*fluid_control_registrations()),
    )

    assert result.instance.valve_error_handling is False
    result.close()


@pytest.mark.parametrize(
    ("builder", "component_type"),
    [
        (build_dispenser_from_view, "pipettor"),
        (build_pipettor_from_view, "dispenser"),
        (build_aspirator_from_view, "dispenser"),
    ],
)
def test_builder_rejects_wrong_component_type(builder, component_type, dispenser_config):
    """Builders reject selected views for a different runtime type."""
    view = _view(dispenser_config, "dispenser_1", component_type)

    with pytest.raises(ValueError, match="Expected a"):
        builder(view)


@pytest.mark.parametrize(
    ("builder", "view"),
    [
        (build_dispenser_from_view, object()),
        (build_pipettor_from_view, object()),
        (build_aspirator_from_view, object()),
        (
            build_dispenser_from_view,
            ComponentView("", "dispenser", {}, {}, "components", {}),
        ),
        (
            build_dispenser_from_view,
            ComponentView("dispenser_1", "dispenser", None, {}, "components.dispenser_1", {}),
        ),
    ],
)
def test_builder_rejects_malformed_view(builder, view):
    """Builders reject non-view input before attempting construction."""
    with pytest.raises(TypeError):
        builder(view)


def test_builders_do_not_load_select_or_bootstrap(mocker, dispenser_config):
    """Builders use only the already-selected view and never own bootstrap."""
    _mock_controllers(mocker)
    guarded_components = MagicMock()
    guarded_components.get.side_effect = AssertionError("builder traversed relationships")
    view = ComponentView(
        "dispenser_1",
        "dispenser",
        dispenser_config["components"]["dispenser_1"],
        dispenser_config,
        "components.dispenser_1",
        guarded_components,
    )
    open_mock = mocker.patch("builtins.open", side_effect=AssertionError("builder loaded a file"))

    result = build_dispenser_from_view(view)

    assert isinstance(result, Dispenser)
    assert open_mock.call_count == 0
    assert "Configurator" not in vars(__import__("fluid_control.configurator_adapter", fromlist=["Configurator"]))
