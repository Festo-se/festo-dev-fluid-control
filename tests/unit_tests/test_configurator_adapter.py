"""Unit tests for fluid-control configurator registrations and builders."""

from unittest.mock import MagicMock
from types import SimpleNamespace

import pytest
from configurator import ComponentView, Configurator, Registration, Registry

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
from fluid_control.device_config import DeviceConfig
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


def test_bootstrap_selected_view_preserves_device_config_compatibility(mocker, dispenser_config):
    """A configurator-selected component preserves the legacy device view contract."""
    _mock_controllers(mocker)
    selected_component = dispenser_config["components"]["dispenser_1"]

    result = Configurator.bootstrap(
        dispenser_config,
        "dispenser_1",
        Registry.compose(*fluid_control_registrations()),
    )
    dispenser = result.instance

    assert dispenser.device_config.raw is selected_component
    assert dispenser.config is selected_component
    assert dispenser.device_config.active_channels == [1, 2]
    assert dispenser.device_config.active_valve_count == 2
    assert dispenser.device_config.pressure_interface.name == "pgva"
    assert dispenser.device_config.pressure_interface.ip == "192.168.10.102"
    assert dispenser.device_config.pressure_interface.port == 502
    assert dispenser.device_config.pressure_interface.unit_id == 1
    assert dispenser.device_config.valve_interface.name == "vaem"
    assert dispenser.device_config.valve_interface.ip == "192.168.10.27"
    assert dispenser.device_config.valve_interface.port == 502
    assert dispenser.device_config.valve_interface.unit_id == 1
    assert dispenser.device_config.valve_error_handling is True

    selected_component["calibration"]["water"]["dispense"]["parameters"]["pressure"] = 999
    assert dispenser.device_config.calibration["water"]["dispense"]["parameters"]["pressure"] == 999

    result.close()


def test_bootstrap_builder_uses_pre_resolved_device_config(mocker, dispenser_config):
    """The canonical builder does not re-resolve the selected component."""
    _mock_controllers(mocker)
    device_config = mocker.patch(
        "fluid_control.fluid_control.DeviceConfig",
        side_effect=AssertionError("constructor reparsed the selected component"),
    )

    result = Configurator.bootstrap(
        dispenser_config,
        "dispenser_1",
        Registry.compose(*fluid_control_registrations()),
    )

    assert result.instance.component_id == "dispenser_1"
    device_config.assert_not_called()
    result.close()


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
    assert isinstance(instance.device_config, DeviceConfig)
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

    assert result.instance.device_config.valve_error_handling is False
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
