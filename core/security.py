"""EO-005 G4 — cryptographic identity, AST whitelist, frozen builtins."""

from __future__ import annotations

import ast
import hashlib
import inspect
import textwrap
import types
from collections.abc import Callable
from typing import Any

from core.security_exceptions import (  # noqa: F401
    ASTSecurityViolationError,
    RegistryImmutableError,
    SecurityDowngradeError,
    StatefulToolError,
    ToolExecutionError,
)

# Re-export for callers/tests
__all__ = [
    "ASTWhitelistVisitor",
    "analyze_function_ast",
    "assert_pure_code_object",
    "compute_spec_digest",
    "frozen_builtins",
    "make_sandbox_globals",
    "execute_in_sandbox",
    "ASTSecurityViolationError",
    "RegistryImmutableError",
    "SecurityDowngradeError",
    "StatefulToolError",
    "ToolExecutionError",
]

_SAFE_BUILTIN_NAMES: frozenset[str] = frozenset(
    {
        "abs", "all", "any", "bin", "bool", "dict", "float", "int", "len", "list",
        "max", "min", "pow", "range", "round", "set", "str", "sum", "tuple",
        "True", "False", "None",
    }
)

_FORBIDDEN_CALL_NAMES: frozenset[str] = frozenset(
    {
        "eval", "exec", "getattr", "setattr", "delattr", "open", "compile",
        "globals", "locals", "vars", "dir", "input", "__import__",
    }
)

_ALLOWED_AST_TYPES: frozenset[type] = frozenset(
    {
        ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Assign, ast.Name,
        ast.Load, ast.Store, ast.Constant, ast.BinOp, ast.UnaryOp, ast.Compare,
        ast.Return, ast.If, ast.Expr, ast.Pass, ast.Dict, ast.List, ast.Tuple,
        ast.Set, ast.Call, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv,
        ast.Mod, ast.Pow, ast.USub, ast.UAdd, ast.Eq, ast.NotEq, ast.Lt, ast.LtE,
        ast.Gt, ast.GtE, ast.And, ast.Or, ast.Not, ast.BoolOp,
    }
)

_FORBIDDEN_AST_TYPES: frozenset[type] = frozenset(
    {
        ast.Attribute, ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal,
        ast.ClassDef, ast.Lambda, ast.Yield, ast.YieldFrom, ast.Await,
        ast.AsyncFunctionDef, ast.Try, ast.With,
    }
)


class ASTWhitelistVisitor(ast.NodeVisitor):
    def generic_visit(self, node: ast.AST) -> None:
        t = type(node)
        if t in _FORBIDDEN_AST_TYPES:
            raise ASTSecurityViolationError(f"forbidden AST node: {t.__name__}")
        if t not in _ALLOWED_AST_TYPES and not isinstance(
            node, (ast.operator, ast.cmpop, ast.unaryop, ast.boolop, ast.expr_context)
        ):
            raise ASTSecurityViolationError(f"non-whitelisted AST node: {t.__name__}")
        super().generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if not isinstance(node.func, ast.Name):
            raise ASTSecurityViolationError("Call target must be ast.Name (no attributes)")
        name = node.func.id
        if name in _FORBIDDEN_CALL_NAMES:
            raise ASTSecurityViolationError(f"forbidden call: {name}")
        if name not in _SAFE_BUILTIN_NAMES:
            raise ASTSecurityViolationError(f"call not in pure-builtin whitelist: {name}")
        self.generic_visit(node)


def analyze_function_ast(fn: Callable[..., Any]) -> None:
    try:
        src = inspect.getsource(fn)
    except (OSError, TypeError) as exc:
        raise ASTSecurityViolationError(f"cannot obtain source for AST analysis: {exc}") from exc
    src = textwrap.dedent(src)
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        raise ASTSecurityViolationError(f"AST parse failed: {exc}") from exc
    ASTWhitelistVisitor().visit(tree)


def assert_pure_code_object(fn: Callable[..., Any]) -> None:
    code = getattr(fn, "__code__", None)
    if code is None:
        raise StatefulToolError("callable has no __code__")
    if code.co_freevars != ():
        raise StatefulToolError(f"co_freevars not empty: {code.co_freevars}")
    if code.co_cellvars != ():
        raise StatefulToolError(f"co_cellvars not empty: {code.co_cellvars}")


def compute_spec_digest(
    name: str,
    version: str,
    description: str,
    parameters: dict[str, Any],
    fn: Callable[..., Any],
) -> str:
    code = fn.__code__
    meta = f"{name}|{version}|{description}|{parameters!r}"
    bytecode = code.co_code
    try:
        src = textwrap.dedent(inspect.getsource(fn))
        tree = ast.parse(src)
        ast_fp = ast.dump(tree, annotate_fields=True)
    except Exception:  # noqa: BLE001
        ast_fp = ""
    blob = meta.encode("utf-8") + b"\0" + bytecode + b"\0" + ast_fp.encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def frozen_builtins() -> types.MappingProxyType[str, Any]:
    import builtins as _b

    safe: dict[str, Any] = {}
    for name in _SAFE_BUILTIN_NAMES:
        if hasattr(_b, name):
            safe[name] = getattr(_b, name)
    safe["True"] = True
    safe["False"] = False
    safe["None"] = None
    return types.MappingProxyType(safe)


def make_sandbox_globals() -> dict[str, Any]:
    return {"__builtins__": frozen_builtins()}


def execute_in_sandbox(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    g = make_sandbox_globals()
    if not isinstance(g["__builtins__"], types.MappingProxyType):
        raise SecurityDowngradeError("__builtins__ is not frozen")
    return fn(*args, **kwargs)
