"""Tests for the tool system: interface, registry, and built-in calculator."""

from __future__ import annotations

from typing import Any

import pytest

from tools.built_in.calculator import Calculator
from tools.tool_interface import Tool, ToolResult
from tools.tool_registry import ToolRegistry

# ---- Test doubles ----


class EchoTool(Tool):
    """Echoes its text argument back."""

    name = "echo"
    description = "Echo the given text."
    parameters = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    }

    async def execute(self, **kwargs: Any) -> ToolResult:
        return ToolResult.ok(kwargs["text"])


class BombTool(Tool):
    """Always raises."""

    name = "bomb"
    description = "Raises every time."
    parameters = {"type": "object", "properties": {}, "required": []}

    async def execute(self, **kwargs: Any) -> ToolResult:
        raise RuntimeError("boom")


class RudeTool(Tool):
    """Violates the contract by returning a bare value."""

    name = "rude"
    description = "Returns something that is not a ToolResult."
    parameters = {"type": "object", "properties": {}, "required": []}

    async def execute(self, **kwargs: Any) -> ToolResult:
        return 42  # type: ignore[return-value]


class NamelessTool(Tool):
    """Forgot to declare a name."""

    description = "No name."

    async def execute(self, **kwargs: Any) -> ToolResult:
        return ToolResult.ok()


# ---- Tool interface ----


def test_tool_is_abstract() -> None:
    with pytest.raises(TypeError):
        Tool()  # type: ignore[abstract]


def test_toolresult_ok() -> None:
    result = ToolResult.ok(7, metadata={"expr": "3 + 4"})
    assert result.success is True
    assert result.output == 7
    assert result.error is None
    assert result.metadata == {"expr": "3 + 4"}


def test_toolresult_failed() -> None:
    result = ToolResult.failed("bad input")
    assert result.success is False
    assert result.output is None
    assert result.error == "bad input"
    assert result.metadata == {}


def test_echo_tool_schema() -> None:
    tool = EchoTool()
    assert tool.required_parameters == ["text"]
    assert tool.parameter_names == ["text"]
    schema = tool.to_schema()
    assert schema["name"] == "echo"
    assert schema["description"] == "Echo the given text."
    assert schema["parameters"]["required"] == ["text"]


# ---- Calculator ----


def test_calculator_declaration() -> None:
    calc = Calculator()
    assert calc.name == "calculator"
    assert "expression" in calc.description or calc.description
    assert calc.required_parameters == ["expression"]
    assert calc.parameter_names == ["expression"]


def test_calculator_basic_arithmetic() -> None:
    calc = Calculator()
    assert calc.compute("2 + 2") == 4
    assert calc.compute("10 - 3") == 7
    assert calc.compute("6 * 7") == 42
    assert calc.compute("8 / 2") == 4.0
    assert calc.compute("7 // 2") == 3
    assert calc.compute("7 % 4") == 3
    assert calc.compute("2 ** 10") == 1024


def test_calculator_precedence_and_signs() -> None:
    calc = Calculator()
    assert calc.compute("2 + 2 * 3") == 8
    assert calc.compute("(2 + 2) * 3") == 12
    assert calc.compute("-5 + 3") == -2
    assert calc.compute("-(3 - 5)") == 2
    assert calc.compute("  1.5 * 2  ") == 3.0


def test_calculator_functions() -> None:
    calc = Calculator()
    assert calc.compute("sqrt(16)") == 4
    assert calc.compute("abs(-7)") == 7
    assert calc.compute("max(1, 9, 3)") == 9
    assert calc.compute("min(4, 2)") == 2
    assert calc.compute("round(3.14159, 2)") == 3.14
    assert calc.compute("floor(3.7) + ceil(3.2)") == 7


def test_calculator_invalid_syntax() -> None:
    calc = Calculator()
    with pytest.raises(SyntaxError):
        calc.compute("2 +")
    with pytest.raises(ValueError):
        calc.compute("")


def test_calculator_division_by_zero() -> None:
    with pytest.raises(ArithmeticError):
        Calculator().compute("1 / 0")


def test_calculator_rejects_unsafe_expressions() -> None:
    calc = Calculator()
    with pytest.raises(ValueError):
        calc.compute("2 + x")  # unknown name
    with pytest.raises(ValueError):
        calc.compute("__import__('os')")  # dangerous call
    with pytest.raises(ValueError):
        calc.compute("'abc' + 'def'")  # string literal
    with pytest.raises(ValueError):
        calc.compute("(1).real")  # attribute access


def test_calculator_rejects_oversized_expression() -> None:
    with pytest.raises(ValueError):
        Calculator().compute("1 + " * 500 + "1")


async def test_calculator_execute_success() -> None:
    result = await Calculator().execute(expression="2 + 2")
    assert result.success is True
    assert result.output == 4
    assert result.metadata["expression"] == "2 + 2"


async def test_calculator_execute_reports_domain_error() -> None:
    result = await Calculator().execute(expression="1 / 0")
    assert result.success is False
    assert result.error is not None
    assert "1 / 0" in result.error


async def test_calculator_execute_requires_string_expression() -> None:
    assert (await Calculator().execute()).success is False
    assert (await Calculator().execute(expression=42)).success is False


# ---- Tool registry ----


def test_registry_register_and_lookup() -> None:
    registry = ToolRegistry()
    calc = Calculator()
    registry.register(calc)
    assert registry.has("calculator")
    assert "calculator" in registry
    assert len(registry) == 1
    assert registry.names() == ["calculator"]
    assert registry.get("calculator") is calc


def test_registry_constructor_registers_tools() -> None:
    registry = ToolRegistry([Calculator(), EchoTool()])
    assert set(registry.names()) == {"calculator", "echo"}


def test_registry_duplicate_register_raises() -> None:
    registry = ToolRegistry([Calculator()])
    with pytest.raises(ValueError):
        registry.register(Calculator())


def test_registry_rejects_nameless_tool() -> None:
    registry = ToolRegistry()
    with pytest.raises(ValueError):
        registry.register(NamelessTool())


def test_registry_unregister_and_missing() -> None:
    registry = ToolRegistry([Calculator()])
    removed = registry.unregister("calculator")
    assert removed.name == "calculator"
    assert len(registry) == 0
    with pytest.raises(KeyError):
        registry.get("calculator")


def test_registry_schemas() -> None:
    registry = ToolRegistry([Calculator(), EchoTool()])
    schemas = registry.schemas()
    assert [s["name"] for s in schemas] == ["calculator", "echo"]
    assert schemas[0]["parameters"]["required"] == ["expression"]
    assert schemas[1]["parameters"]["properties"]["text"]["type"] == "string"


async def test_registry_call_dispatches() -> None:
    registry = ToolRegistry([Calculator(), EchoTool()])
    calc_result = await registry.call("calculator", expression="2 + 2 * 3")
    assert calc_result.success is True
    assert calc_result.output == 8
    echo_result = await registry.call("echo", text="hi")
    assert isinstance(echo_result, ToolResult)
    assert echo_result.output == "hi"


async def test_registry_call_unknown_tool() -> None:
    registry = ToolRegistry()
    result = await registry.call("nope")
    assert result.success is False
    assert result.error is not None
    assert "unknown tool" in result.error
    assert result.metadata["tool"] == "nope"


async def test_registry_call_missing_required_parameter() -> None:
    registry = ToolRegistry([Calculator()])
    result = await registry.call("calculator")
    assert result.success is False
    assert result.error is not None
    assert "expression" in result.error


async def test_registry_call_unexpected_parameter() -> None:
    registry = ToolRegistry([Calculator()])
    result = await registry.call("calculator", expression="1 + 1", extra=1)
    assert result.success is False
    assert result.error is not None
    assert "extra" in result.error


async def test_registry_call_type_mismatch() -> None:
    registry = ToolRegistry([Calculator()])
    result = await registry.call("calculator", expression=42)
    assert result.success is False
    assert result.error is not None
    assert "string" in result.error


async def test_registry_call_captures_tool_exception() -> None:
    registry = ToolRegistry([BombTool()])
    result = await registry.call("bomb")
    assert result.success is False
    assert result.error is not None
    assert "boom" in result.error
    assert result.metadata["tool"] == "bomb"


async def test_registry_call_rejects_contract_violation() -> None:
    registry = ToolRegistry([RudeTool()])
    result = await registry.call("rude")
    assert result.success is False
    assert result.error is not None
    assert "ToolResult" in result.error
