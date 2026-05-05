"""Unit tests for the ``Status`` state machine.

``Status`` is a simple three-state object (clear=0, error=1, busy=2).
These tests are self-contained — no fixtures, no mocks, no hardware.
"""

from fluid_control.fluid_control import Status


class TestStatusInitialState:
    def test_initial_code_is_zero(self):
        s = Status()
        assert s.code == 0

    def test_get_status_returns_zero_on_construction(self):
        s = Status()
        assert s.get_status() == 0


class TestStatusTransitions:
    def test_set_busy_sets_code_to_two(self):
        s = Status()
        s.set_busy()
        assert s.code == 2

    def test_get_status_returns_two_when_busy(self):
        s = Status()
        s.set_busy()
        assert s.get_status() == 2

    def test_set_error_sets_code_to_one(self):
        s = Status()
        s.set_error()
        assert s.code == 1

    def test_get_status_returns_one_when_error(self):
        s = Status()
        s.set_error()
        assert s.get_status() == 1

    def test_set_clear_sets_code_to_zero(self):
        s = Status()
        s.set_busy()
        s.set_clear()
        assert s.code == 0

    def test_get_status_returns_zero_after_clear(self):
        s = Status()
        s.set_error()
        s.set_clear()
        assert s.get_status() == 0

    def test_busy_then_clear(self):
        s = Status()
        s.set_busy()
        assert s.get_status() == 2
        s.set_clear()
        assert s.get_status() == 0

    def test_busy_then_error(self):
        s = Status()
        s.set_busy()
        assert s.get_status() == 2
        s.set_error()
        assert s.get_status() == 1

    def test_error_then_clear(self):
        s = Status()
        s.set_error()
        s.set_clear()
        assert s.get_status() == 0

    def test_multiple_clear_calls_idempotent(self):
        s = Status()
        s.set_clear()
        s.set_clear()
        assert s.get_status() == 0

    def test_multiple_error_calls_idempotent(self):
        s = Status()
        s.set_error()
        s.set_error()
        assert s.get_status() == 1


class TestStatusIndependence:
    def test_two_instances_are_independent(self):
        s1 = Status()
        s2 = Status()
        s1.set_error()
        assert s2.get_status() == 0


class TestStatusRepr:
    def test_repr_contains_code(self):
        s = Status()
        assert "code=0" in repr(s)

    def test_repr_contains_message(self):
        s = Status()
        assert "message=" in repr(s)

    def test_repr_format(self):
        s = Status()
        s.message = "test"
        assert repr(s) == "Status(code=0, message='test')"

    def test_repr_reflects_error_code(self):
        s = Status()
        s.set_error()
        assert "code=1" in repr(s)


class TestStatusStr:
    def test_str_clear_is_clear(self):
        s = Status()
        assert str(s) == "clear"

    def test_str_error_is_error(self):
        s = Status()
        s.set_error()
        assert str(s) == "error"

    def test_str_busy_is_busy(self):
        s = Status()
        s.set_busy()
        assert str(s) == "busy"

    def test_str_unknown_code(self):
        s = Status()
        s.code = 99
        assert "unknown" in str(s)


class TestStatusBool:
    def test_bool_true_when_clear(self):
        s = Status()
        assert bool(s) is True

    def test_bool_false_when_error(self):
        s = Status()
        s.set_error()
        assert bool(s) is False

    def test_bool_false_when_busy(self):
        s = Status()
        s.set_busy()
        assert bool(s) is False

    def test_bool_usable_in_if_expression(self):
        s = Status()
        assert s  # truthy when clear
        s.set_error()
        assert not s  # falsy when error


class TestStatusEquality:
    def test_equal_to_same_code_status(self):
        s1 = Status()
        s2 = Status()
        assert s1 == s2

    def test_not_equal_after_diverging_state(self):
        s1 = Status()
        s2 = Status()
        s1.set_error()
        assert s1 != s2

    def test_equal_to_int_zero_when_clear(self):
        s = Status()
        assert s == 0

    def test_equal_to_int_one_when_error(self):
        s = Status()
        s.set_error()
        assert s == 1

    def test_equal_to_int_two_when_busy(self):
        s = Status()
        s.set_busy()
        assert s == 2

    def test_not_equal_to_wrong_int(self):
        s = Status()
        assert s != 5

    def test_returns_not_implemented_for_non_status_non_int(self):
        s = Status()
        result = s.__eq__("clear")
        assert result is NotImplemented


class TestStatusHash:
    def test_hash_returns_int(self):
        s = Status()
        assert isinstance(hash(s), int)

    def test_equal_statuses_have_same_hash(self):
        s1 = Status()
        s2 = Status()
        assert hash(s1) == hash(s2)

    def test_different_statuses_have_different_hashes(self):
        s_clear = Status()
        s_error = Status()
        s_error.set_error()
        assert hash(s_clear) != hash(s_error)

    def test_usable_as_dict_key(self):
        s = Status()
        d = {s: "value"}
        assert d[s] == "value"
