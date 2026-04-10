"""Calculator tool -- safe arithmetic expression evaluator.

Used in Step 2 to demonstrate the agent loop with a concrete tool call.
The evaluator uses Python's AST module to parse and walk the expression
without calling eval(), preventing any code injection.
"""

from __future__ import annotations

import ast
import operator
from typing import Any

from .base import Tool

# Only allow these operators to ensure safety.
_BINARY_OPS: dict[type, Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS: dict[type, Any] = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(node: ast.expr) -> float | int:
    if isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float)):
            raise ValueError(f"Unsupported constant type: {type(node.value).__name__}")
        return node.value
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _BINARY_OPS:
            raise ValueError(f"Operator '{type(node.op).__name__}' is not allowed")
        return _BINARY_OPS[op_type](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _UNARY_OPS:
            raise ValueError(f"Unary operator '{type(node.op).__name__}' is not allowed")
        return _UNARY_OPS[op_type](_safe_eval(node.operand))
    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


class CalculatorTool(Tool):
    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return (
            "Evaluate a simple arithmetic expression and return the numeric result. "
            "Supports +, -, *, /, //, %, ** operators and parentheses. "
            "Examples: '42 * 17', '(10 + 5) / 3', '2 ** 10'."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Arithmetic expression to evaluate.",
                }
            },
            "required": ["expression"],
        }

    def execute(self, tool_input: dict[str, Any]) -> str:
        expr = str(tool_input.get("expression", "")).strip()
        if not expr:
            return "Error: 'expression' is required"
        try:
            tree = ast.parse(expr, mode="eval")
            result = _safe_eval(tree.body)
            # Return integer representation when the result is a whole number.
            if isinstance(result, float) and result.is_integer():
                return str(int(result))
            return str(result)
        except ZeroDivisionError:
            return "Error: division by zero"
        except (ValueError, SyntaxError) as exc:
            return f"Error: {exc}"
