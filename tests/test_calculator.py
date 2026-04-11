"""Tests for the calculator tool."""

from __future__ import annotations

import pytest

from claw_code_python.tools.calculator import CalculatorTool


@pytest.fixture()
def calc():
    return CalculatorTool()


def test_addition(calc):
    assert calc.execute({"expression": "1 + 2"}) == "3"


def test_multiplication(calc):
    assert calc.execute({"expression": "42 * 17"}) == "714"


def test_parentheses(calc):
    assert calc.execute({"expression": "(10 + 5) / 3"}) == "5"


def test_integer_result_for_whole_float(calc):
    # 9 / 3 = 3.0 → should return "3" not "3.0"
    assert calc.execute({"expression": "9 / 3"}) == "3"


def test_float_result(calc):
    assert calc.execute({"expression": "1 / 3"}) == str(1 / 3)


def test_power(calc):
    assert calc.execute({"expression": "2 ** 10"}) == "1024"


def test_floor_div(calc):
    assert calc.execute({"expression": "7 // 2"}) == "3"


def test_modulo(calc):
    assert calc.execute({"expression": "10 % 3"}) == "1"


def test_unary_negation(calc):
    assert calc.execute({"expression": "-5 + 10"}) == "5"


def test_division_by_zero(calc):
    result = calc.execute({"expression": "1 / 0"})
    assert result.startswith("Error")


def test_invalid_expression(calc):
    result = calc.execute({"expression": "not valid"})
    assert result.startswith("Error")


def test_blocked_builtin(calc):
    # Should not allow function calls
    result = calc.execute({"expression": "__import__('os').system('id')"})
    assert result.startswith("Error")


def test_empty_expression(calc):
    result = calc.execute({"expression": ""})
    assert result.startswith("Error")
