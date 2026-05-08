"""Shared pytest fixtures for the festo-dev-fluid-control test suite.

Fixtures
--------
dispenser_config
    Minimal in-memory config dict for a 2-channel dispenser (water,
    dispense + aspirate).  No file I/O; no hardware required.

eight_channel_pipettor_config
    8-channel pipettor variant of the config dict.

dispenser
    A ``Dispenser`` instance whose PGVA and VAEM backends are replaced
    by ``MagicMock`` objects.  Exposes ``.mock_pgva`` and ``.mock_vaem``
    for per-test assertion.  ``sleep`` is also patched so valve-timing
    waits are instantaneous.

pipettor_instance
    Same pattern as ``dispenser`` but for ``Pipettor``.

hardware_dispenser
    A real ``Dispenser`` backed by live hardware.  Module-scoped; skipped
    when ``DISPENSER_PGVA_IP`` or ``DISPENSER_VAEM_IP`` env vars are not
    set.  Mark any test using this fixture with ``@pytest.mark.hardware``.
"""

import json
import socket
from os import getenv
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from fluid_control import Dispenser, Pipettor

# ---------------------------------------------------------------------------
# Path to bundled test fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Config-builder helpers
# ---------------------------------------------------------------------------


def _make_component(*, channels: int, active_channels: list[int]) -> dict:
    """Return an inner component config dict for a dispenser or pipettor.

    Calibration coefficients are derived from real test-config data so
    that timing calculations produce realistic (non-degenerate) values.
    """
    flow_d = {
        str(i): {"channel_index_coeff": 0.0, "flow_offset": 0.826181241 + i * 0.01}
        for i in active_channels
    }
    vol_d = {
        str(i): {"channel_index_coeff": 0.321305707, "volume_offset": -4.857648804 - i * 0.1}
        for i in active_channels
    }
    flow_a = {
        str(i): {"channel_index_coeff": 0.0, "flow_offset": 1.318858492 + i * 0.01}
        for i in active_channels
    }
    vol_a = {
        str(i): {"channel_index_coeff": 0.0, "volume_offset": -10.40199499 - i * 0.1}
        for i in active_channels
    }

    return {
        "uuid": "0000-000000000-000000-001",
        "type": "pressure-over-liquid",
        "fluid-channel-count": channels,
        "control_mode": "python",
        "control_modules": {
            "pressure": {
                "name": "pgva",
                "uuid": 1,
                "interface": {"type": "tcp/ip", "ip": "192.168.10.102", "port": 502},
            },
            "valve": {
                "name": "vaem",
                "valve_count": channels,
                "active_valve_terminals": active_channels,
                "valve_type": {
                    str(ch): {"type": {"error-handling": True}} for ch in active_channels
                },
                "uuid": 2,
                "interface": {"type": "tcp/ip", "ip": "192.168.10.27", "port": 502},
            },
        },
        "calibration": {
            "water": {
                "dispense": {
                    "flow_coefficients": flow_d,
                    "volume_offset_coefficients": vol_d,
                    "parameters": {"pressure": 70},
                },
                "aspirate": {
                    "flow_coefficients": flow_a,
                    "volume_offset_coefficients": vol_a,
                    "parameters": {"pressure": -100},
                },
            },
        },
    }


@pytest.fixture()
def dispenser_config() -> dict:
    """Minimal 2-channel dispenser config; no file I/O, no hardware."""
    component = _make_component(channels=2, active_channels=[1, 2])
    component["component_class"] = "dispenser"
    return {"components": {"dispenser_1": component}}


@pytest.fixture()
def eight_channel_pipettor_config() -> dict:
    """8-channel pipettor config; no file I/O, no hardware."""
    component = _make_component(channels=8, active_channels=list(range(1, 9)))
    component["component_class"] = "pipettor"
    return {"components": {"pipettor_1": component}}


# ---------------------------------------------------------------------------
# Mock-factory helpers
# ---------------------------------------------------------------------------


def _make_pressure_mock() -> tuple[MagicMock, dict]:
    """Return a (mock_pgva, state) pair.

    ``set_output_pressure`` and ``get_output_pressure`` are wired through a
    shared state dict so that ``_wait_output_pressure``'s polling loop
    terminates immediately rather than spinning forever.

    Note: ``set_output_pressure`` is always called with keyword argument
    ``pressure=``.  The side-effect lambda must accept that keyword.
    """
    state: dict[str, int] = {"pressure": 0}
    mock = MagicMock()

    def _set(pressure: int) -> None:
        state["pressure"] = pressure

    mock.set_output_pressure.side_effect = _set
    mock.get_output_pressure.side_effect = lambda: state["pressure"]
    mock.get_status_word.return_value = {"Status": "Idle"}

    return mock, state


def _make_valve_mock() -> MagicMock:
    """Return a VAEM MagicMock with sane defaults for unit testing.

    ``Readiness == 0`` causes the dispense retry loop inside
    ``_handle_liquid`` to exit on the first iteration.
    """
    mock = MagicMock()
    mock.get_status.return_value = {
        "Status": 1,
        "Error": 0,
        "Readiness": 0,  # 0 = done  →  dispense while-repeat loop exits
        "OperatingMode": 1,
        **{f"Valve{i}": 0 for i in range(1, 9)},
    }
    return mock


# ---------------------------------------------------------------------------
# Simulated tip-rack position sequence for _pickup_action stall detection
#
# FestoAxis uses mm as its single unit.  ``mount_arm.get_current_axis_position()``
# returns mm.  ``_pickup_action`` exits when movement per iteration falls
# at or below ``delta = 0.5`` mm on two consecutive jog iterations.
#
# The sequence below models a 0.5 s-per-jog descent with free-air travel
# of 5 mm/jog and stall once tip contact is made (0.3 mm then 0.2 mm —
# both below the 0.5 mm threshold):
#
#   Index  Position (mm)  Movement vs prev  Stall (≤0.5 mm)?  count
#   -----  -------------  ----------------  ----------------  -----
#     0        0.0               —          pre-loop read       —
#     1        5.0             5.0 mm            no              0
#     2       10.0             5.0 mm            no              0
#     3       10.3             0.3 mm            yes             1
#     4       10.5             0.2 mm            yes        2 → exit
# ---------------------------------------------------------------------------
TIP_RACK_POSITIONS: list[float] = [0.0, 5.0, 10.0, 10.3, 10.5]


# ---------------------------------------------------------------------------
# Core unit-test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def dispenser(mocker, dispenser_config):
    """Dispenser with fully mocked PGVA + VAEM + sleep."""
    mock_pgva, _state = _make_pressure_mock()
    mock_vaem = _make_valve_mock()

    mocker.patch("fluid_control.fluid_control.PGVA", return_value=mock_pgva)
    mocker.patch("fluid_control.fluid_control.VAEM", return_value=mock_vaem)
    mocker.patch("fluid_control.fluid_control.sleep")

    instance = Dispenser(config=dispenser_config)
    instance.mock_pgva = mock_pgva
    instance.mock_vaem = mock_vaem
    return instance


@pytest.fixture()
def pipettor_instance(mocker, eight_channel_pipettor_config):
    """Pipettor with fully mocked PGVA + VAEM + sleep."""
    mock_pgva, _state = _make_pressure_mock()
    mock_vaem = _make_valve_mock()

    mocker.patch("fluid_control.fluid_control.PGVA", return_value=mock_pgva)
    mocker.patch("fluid_control.fluid_control.VAEM", return_value=mock_vaem)
    mocker.patch("fluid_control.fluid_control.sleep")

    instance = Pipettor(config=eight_channel_pipettor_config)
    instance.mock_pgva = mock_pgva
    instance.mock_vaem = mock_vaem
    return instance


@pytest.fixture()
def pipettor_with_arm(mocker, eight_channel_pipettor_config):
    """Non-static Pipettor with a mocked mount_arm and realistic tip-rack positions.

    ``mount_arm.current_position()`` is pre-loaded with ``TIP_RACK_POSITIONS``
    so that ``_pickup_action`` runs its full stall-detection loop and exits
    cleanly without real hardware.

    Exposes ``.mock_pgva``, ``.mock_vaem``, and ``.mock_arm`` for assertions.
    """
    mock_pgva, _state = _make_pressure_mock()
    mock_vaem = _make_valve_mock()

    mocker.patch("fluid_control.fluid_control.PGVA", return_value=mock_pgva)
    mocker.patch("fluid_control.fluid_control.VAEM", return_value=mock_vaem)
    mocker.patch("fluid_control.fluid_control.sleep")

    mock_arm = MagicMock()
    mock_arm.current_position.side_effect = list(TIP_RACK_POSITIONS)

    instance = Pipettor(config=eight_channel_pipettor_config, mount_arm=mock_arm)
    instance.mock_pgva = mock_pgva
    instance.mock_vaem = mock_vaem
    instance.mock_arm = mock_arm
    return instance


# ---------------------------------------------------------------------------
# Hardware fixture — requires live devices
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def hardware_dispenser():
    """Real Dispenser connected to live hardware.

    Requires ``DISPENSER_PGVA_IP`` and ``DISPENSER_VAEM_IP`` environment
    variables.  Run hardware tests with::

        DISPENSER_PGVA_IP=192.168.10.102 DISPENSER_VAEM_IP=192.168.10.27 \\
            uv run pytest -m hardware
    """
    pgva_ip = getenv("DISPENSER_PGVA_IP")
    vaem_ip = getenv("DISPENSER_VAEM_IP")
    if not pgva_ip or not vaem_ip:
        pytest.skip(
            "DISPENSER_PGVA_IP and DISPENSER_VAEM_IP not set — skipping hardware tests"
        )

    component = _make_component(channels=2, active_channels=[1, 2])
    component["control_modules"]["pressure"]["interface"]["ip"] = pgva_ip
    component["control_modules"]["valve"]["interface"]["ip"] = vaem_ip
    component["component_class"] = "dispenser"
    config = {"components": {"dispenser_1": component}}
    return Dispenser(config=config)


# ---------------------------------------------------------------------------
# test-config.json fixtures
#
# The JSON file is stored under tests/fixtures/ so the test suite remains
# self-contained after the top-level config files are removed from the repo.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def test_config() -> dict:
    """Load the bundled test-config.json from tests/fixtures/.

    Session-scoped: the file is read once per test session.
    """
    config_path = FIXTURES_DIR / "test-config.json"
    with config_path.open() as fh:
        return json.load(fh)


@pytest.fixture()
def test_dispenser(mocker, test_config):
    """Dispenser built from the real test-config.json, PGVA + VAEM mocked.

    Exposes ``.mock_pgva`` and ``.mock_vaem`` for per-test assertion.
    The test dispenser component has:
      - 2 channels (terminals 1 and 2)
      - liquid classes: ``water``, ``ethylene-glycol10%``, ``third-liquid-class``
      - only ``dispense`` processes (no aspirate calibration for this component)
    """
    mock_pgva, _state = _make_pressure_mock()
    mock_vaem = _make_valve_mock()

    mocker.patch("fluid_control.fluid_control.PGVA", return_value=mock_pgva)
    mocker.patch("fluid_control.fluid_control.VAEM", return_value=mock_vaem)
    mocker.patch("fluid_control.fluid_control.sleep")

    instance = Dispenser(config=test_config["component_config"])
    instance.mock_pgva = mock_pgva
    instance.mock_vaem = mock_vaem
    return instance


@pytest.fixture()
def test_pipettor(mocker, test_config):
    """Pipettor built from the real test-config.json, PGVA + VAEM mocked.

    Exposes ``.mock_pgva`` and ``.mock_vaem`` for per-test assertion.
    The test pipettor component has:
      - 8 channels (terminals 1–8, calibration keys ``"1"``–``"8"``)
      - liquid classes: ``water``, ``ethylene-glycol10%``
      - both ``aspirate`` and ``dispense`` processes
    """
    mock_pgva, _state = _make_pressure_mock()
    mock_vaem = _make_valve_mock()

    mocker.patch("fluid_control.fluid_control.PGVA", return_value=mock_pgva)
    mocker.patch("fluid_control.fluid_control.VAEM", return_value=mock_vaem)
    mocker.patch("fluid_control.fluid_control.sleep")

    instance = Pipettor(config=test_config["component_config"])
    instance.mock_pgva = mock_pgva
    instance.mock_vaem = mock_vaem
    return instance


# ---------------------------------------------------------------------------
# test hardware fixtures — real devices, IPs taken from test-config.json
#
# Run with:
#     uv run pytest -m hardware -v
# ---------------------------------------------------------------------------


def _is_reachable(host: str, port: int, timeout: float = 1.0) -> bool:
    """Return True if a TCP connection to host:port succeeds within timeout seconds."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _require_reachable(hosts: list[tuple[str, int]]) -> None:
    """Skip the current test if any (host, port) pair is unreachable."""
    unreachable = [f"{h}:{p}" for h, p in hosts if not _is_reachable(h, p)]
    if unreachable:
        pytest.skip(f"Hardware unreachable: {', '.join(unreachable)}")


@pytest.fixture(scope="module")
def test_hardware_dispenser(test_config):
    """Real Dispenser connected to the test hardware (PGVA 192.168.10.102, VAEM 192.168.10.27).

    Module-scoped so the TCP connections are opened once per test module.
    Skipped automatically if either device is unreachable.
    Run with::

        uv run pytest -m hardware -v
    """
    modules = test_config["component_config"]["components"]["dispenser_1"]["control_modules"]
    _require_reachable([
        (modules["pressure"]["interface"]["ip"], modules["pressure"]["interface"]["port"]),
        (modules["valve"]["interface"]["ip"], modules["valve"]["interface"]["port"]),
    ])
    return Dispenser(config=test_config["component_config"])


@pytest.fixture(scope="module")
def test_hardware_pipettor(test_config):
    """Real Pipettor connected to the test hardware (PGVA 192.168.0.29, VAEM 192.168.0.1).

    Module-scoped so the TCP connections are opened once per test module.
    Skipped automatically if either device is unreachable.
    Run with::

        uv run pytest -m hardware -v
    """
    modules = test_config["component_config"]["components"]["pipettor_1"]["control_modules"]
    _require_reachable([
        (modules["pressure"]["interface"]["ip"], modules["pressure"]["interface"]["port"]),
        (modules["valve"]["interface"]["ip"], modules["valve"]["interface"]["port"]),
    ])
    return Pipettor(config=test_config["component_config"])
