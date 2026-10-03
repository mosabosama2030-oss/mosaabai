"""Built-in calculator tool: safe arithmetic on string expressions."""

from __future__ import annotations

import ast
import math
import operator
from collections.abc import Callable
from typing import Any

from tools.tool_interface import Tool, ToolResult

_MAX_EXPRESSION_LENGTH = 1000
_MAX_EXPONENT = 10_000

_BIN_OPS: dict[type[ast.operator], Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPS: dict[type[ast.unaryop], Callable[[Any], Any]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "abs": abs,
    "ceil": math.ceil,
    "cos": math.cos,
    "exp": math.exp,
    "floor": math.floor,
    "log": math.log,
    "log10": math.log10,
    "max": max,
    "min": min,
    "round": round,
    "sin": math.sin,
    "sqrt": math.sqrt,
    "tan": math.tan,
}


def _evaluate(node: ast.AST) -> int | float:
    """Recursively evaluate an AST node. Raises ValueError on anything unsafe.

    Only numeric literals, arithmetic operators, and whitelisted math
    functions are allowed: no names, attributes, subscripts, imports, or
    arbitrary calls can ever be reached.
    """
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, int | float):
            raise ValueError(f"unsupported literal: {node.value!r}")
        return node.value
    if isinstance(node, ast.BinOp):
        operation = _BIN_OPS.get(type(node.op))
        if operation is None:
            raise ValueError(f"unsupported operator: {type(node.op).__name__}")
        left = _evaluate(node.left)
        right = _evaluate(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > _MAX_EXPONENT:
            raise ValueError(f"exponent out of range (max |exponent| <= {_MAX_EXPONENT})")
        return operation(left, right)
    if isinstance(node, ast.UnaryOp):
        operation = _UNARY_OPS.get(type(node.op))
        if operation is None:
            raise ValueError(f"unsupported unary operator: {type(node.op).__name__}")
        return operation(_evaluate(node.operand))
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("only direct calls to whitelisted functions are supported")
        function = _FUNCTIONS.get(node.func.id)
        if function is None:
            raise ValueError(f"unsupported function: {node.func.id}")
        if node.keywords:
            raise ValueError("keyword arguments are not supported")
        return function(*[_evaluate(arg) for arg in node.args])
    raise ValueError(f"unsupported syntax: {type(node).__name__}")


class Calculator(Tool):
    """Evaluate arithmetic expressions given as text."""

    name = "calculator"
    description = "Evaluate an arithmetic expression and return its numeric result."
    parameters = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Arithmetic expression, e.g. '2 + 2 * 3' or 'sqrt(16)'.",
            }
        },
        "required": ["expression"],
    }

    def compute(self, expression: str) -> int | float:
        """Evaluate an expression.

        Raises ValueError, SyntaxError, or ArithmeticError on invalid input.
        """
        if not isinstance(expression, str) or not expression.strip():
            raise ValueError("expression must be a non-empty string")
        if len(expression) > _MAX_EXPRESSION_LENGTH:
            raise ValueError(f"expression exceeds {_MAX_EXPRESSION_LENGTH} characters")
        return _evaluate(ast.parse(expression.strip(), mode="eval"))

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Run the calculator, reporting failures as ToolResults."""
        expression = kwargs.get("expression")
        if not isinstance(expression, str):
            return ToolResult.failed("parameter 'expression' must be a string")
        try:
            value = self.compute(expression)
        except (ValueError, SyntaxError, ArithmeticError, TypeError) as exc:
            return ToolResult.failed(f"cannot evaluate {expression!r}: {exc}")
        return ToolResult.ok(value, metadata={"expression": expression})
