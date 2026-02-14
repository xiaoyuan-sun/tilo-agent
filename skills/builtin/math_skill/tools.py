from __future__ import annotations

import ast
from typing import Any

from tools.base import Tool


_ALLOWED_NODES = {
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.UAdd,
    ast.USub,
    ast.Constant,
    ast.Load,
    ast.Expr,
}


class _SafeEvaluator(ast.NodeVisitor):
    def visit(self, node: ast.AST) -> Any:
        if type(node) not in _ALLOWED_NODES:
            raise ValueError(f"Unsupported node {type(node).__name__}")
        return super().visit(node)

    def visit_Expression(self, node: ast.Expression) -> Any:
        return self.visit(node.body)

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        left = self.visit(node.left)
        right = self.visit(node.right)
        match node.op:
            case ast.Add():
                return left + right
            case ast.Sub():
                return left - right
            case ast.Mult():
                return left * right
            case ast.Div():
                return left / right
            case _:
                raise ValueError(f"Unsupported operator {type(node.op).__name__}")

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        operand = self.visit(node.operand)
        match node.op:
            case ast.UAdd():
                return +operand
            case ast.USub():
                return -operand
            case _:
                raise ValueError(f"Unsupported unary operator {type(node.op).__name__}")

    def visit_Constant(self, node: ast.Constant) -> Any:
        if not isinstance(node.value, (int, float)):
            raise ValueError("Only integer or float constants are allowed")
        return node.value


def _calculate(expression: str) -> dict[str, Any]:
    try:
        tree = ast.parse(expression, mode="eval")
        evaluator = _SafeEvaluator()
        result = evaluator.visit(tree)
        return {"result": result}
    except Exception as exc:
        return {"error": str(exc)}


math_tool = Tool(
    name="math.calc",
    description="Safely evaluate simple math expressions.",
    args_schema={"expression": "string"},
    func=_calculate,
)

TOOLS = [math_tool]
