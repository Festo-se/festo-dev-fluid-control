"""Regression tests for import-safe canonical entry points."""

import ast
import importlib.util
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).parents[2]


def _import_file(path: Path, module_name: str) -> None:
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


def test_main_import_has_no_hardware_or_file_side_effects(tmp_path, monkeypatch):
    """Importing the legacy smoke-test module must not execute its test."""
    monkeypatch.chdir(tmp_path)

    _import_file(REPOSITORY_ROOT / "main.py", "fluid_control_main_import_test")

    assert not (tmp_path / "fluid_control.log").exists()


def test_all_examples_are_import_safe():
    """Every example can be inspected/imported without connecting to hardware."""
    for index, path in enumerate(sorted((REPOSITORY_ROOT / "examples").rglob("*.py"))):
        _import_file(path, f"fluid_control_example_import_test_{index}")


def test_config_driven_examples_use_component_constructors():
    """Examples use config-backed component constructors without catalogs."""
    paths = (
        REPOSITORY_ROOT / "examples" / "composable_cli.py",
        REPOSITORY_ROOT / "examples" / "dispenser" / "basic_dispense.py",
        REPOSITORY_ROOT / "examples" / "dispenser" / "context_manager.py",
        REPOSITORY_ROOT / "examples" / "dispenser" / "direct_command_calibration.py",
        REPOSITORY_ROOT / "examples" / "dispenser" / "macro_dispenser_external_pressure.py",
        REPOSITORY_ROOT / "examples" / "dispenser" / "multi_channel_dispense.py",
        REPOSITORY_ROOT / "examples" / "pipettor" / "aspirate_dispense.py",
        REPOSITORY_ROOT / "examples" / "pipettor" / "mix.py",
        REPOSITORY_ROOT / "examples" / "pipettor" / "tip_handling.py",
    )
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        source = ast.unparse(tree)
        assert "Configurator.bootstrap" not in source
        assert "Registry.compose" not in source
