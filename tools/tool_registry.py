"""DEPRECATED: This module is superseded by tools/tool_environment.py.

Reason: Global singleton violates I-005 (Monotonic Delegation).
See EO-003 and Canonical Architecture Section 7.2.

This module is retained for backward compatibility and will be
removed in P0.5.4.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from tools.tool_interface import Tool, ToolResult

_JSON_TYPES: dict[str, type | tuple[type, ...]] = {
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
    "object": dict,
    "array": list,
}


class ToolRegistry:
    """Central catalog of tools available to the cognitive loop.

    The planner reads `schemas()` to learn what is callable; the Execute
    stage dispatches through `call()`. The registry validates arguments
    against each tool's parameter schema and converts execution errors
    into failed ToolResults so a bad call never crashes the loop.
    """

    def __init__(self, tools: Iterable[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools or ():
            self.register(tool)

    def register(self, tool: Tool) -> None:
        """Add a tool. Raises ValueError on empty or duplicate names."""
        if not tool.name or not tool.name.strip():
            raise ValueError("tool must define a non-empty name")
        if tool.name in self._tools:
            raise ValueError(f"tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> Tool:
        """Remove a tool and return it. Raises KeyError if absent."""
        return self._tools.pop(name)

    def get(self, name: str) -> Tool:
        """Look up a tool by name. Raises KeyError if absent."""
        return self._tools[name]

    def has(self, name: str) -> bool:
        """Return whether a tool is registered."""
        return name in self._tools

    def names(self) -> list[str]:
        """Return registered tool names in registration order."""
        return list(self._tools)

    def schemas(self) -> list[dict[str, Any]]:
        """Return LLM-facing declarations for every registered tool."""
        return [tool.to_schema() for tool in self._tools.values()]

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: object) -> bool:
        return name in self._tools

    async def call(self, name: str, **arguments: Any) -> ToolResult:
        """Dispatch a call to a registered tool.

        Unknown tools, invalid arguments, and execution errors are
        reported as failed ToolResults (with `metadata["tool"]` set)
        rather than raised.
        """
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult.failed(f"unknown tool: {name}", metadata={"tool": name})

        error = self._validate(tool, arguments)
        if error is not None:
            return ToolResult.failed(error, metadata={"tool": name})

        try:
            result = await tool.execute(**arguments)
        except Exception as exc:  # noqa: BLE001 - a broken tool must not crash the loop
            message = f"tool '{name}' raised {type(exc).__name__}: {exc}"
            return ToolResult.failed(message, metadata={"tool": name})

        if not isinstance(result, ToolResult):
            got = type(result).__name__
            return ToolResult.failed(
                f"tool '{name}' returned {got}, expected a ToolResult",
                metadata={"tool": name},
            )
        return result

    @staticmethod
    def _validate(tool: Tool, arguments: dict[str, Any]) -> str | None:
        """Check arguments against the tool's schema.

        Returns a human-readable error message, or None if valid.
        """
        properties = tool.parameters.get("properties", {})
        required = tool.parameters.get("required", [])

        missing = [p for p in required if p not in arguments]
        if missing:
            return f"missing required parameter(s): {', '.join(missing)}"

        unexpected = [key for key in arguments if key not in properties]
        if unexpected:
            return f"unexpected parameter(s): {', '.join(unexpected)}"

        for key, value in arguments.items():
            schema = properties.get(key, {})
            expected = schema.get("type") if isinstance(schema, dict) else None
            if not isinstance(expected, str):
                continue
            if expected in ("integer", "number") and isinstance(value, bool):
                return f"parameter '{key}' must be of type {expected}"
            allowed = _JSON_TYPES.get(expected)
            if allowed is not None and not isinstance(value, allowed):
                return f"parameter '{key}' must be of type {expected}"
        return None
