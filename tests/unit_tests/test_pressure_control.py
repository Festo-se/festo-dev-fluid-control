# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG

"""
Unit tests for the generic ``PressureControl`` adapter.

The adapter wraps an arbitrary backend controller that exposes ``set_veab`` and
``get_veab``; all backend calls are mocked.
"""

from unittest.mock import MagicMock

import pytest

from fluid_control.pressure_control import PressureControl


class TestPressureControlSetOutputPressure:
    def test_delegates_to_controller_set_veab(self):
        controller = MagicMock()
        pc = PressureControl(controller)
        pc.set_output_pressure(70)
        controller.set_veab.assert_called_once_with(70)


class TestPressureControlGetOutputPressure:
    def test_returns_controller_get_veab_value(self):
        controller = MagicMock()
        controller.get_veab.return_value = 123
        pc = PressureControl(controller)
        assert pc.get_output_pressure() == 123

    def test_calls_controller_get_veab(self):
        controller = MagicMock()
        pc = PressureControl(controller)
        pc.get_output_pressure()
        controller.get_veab.assert_called_once_with()


class TestPressureControlGetStatus:
    def test_raises_not_implemented(self):
        pc = PressureControl(MagicMock())
        with pytest.raises(NotImplementedError):
            pc.get_status()
