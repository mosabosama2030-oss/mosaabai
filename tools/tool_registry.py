"""TrustedToolRegistry — canonical tool identity registry (EO-005 G4).

Also retains a thin ToolRegistry for backward-compatible dispatch used by
existing tests (name-based catalog). New identity enforcement uses
TrustedToolRegistry only.
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


class TrustedToolRegistry:
    """Maps tool_id -> Tool. Source of truth for known-good tool identities.

    Immutable mapping: once a tool_id is registered, it cannot be reassigned
    to a different implementation.
    """

    def __init__(self) -> None:
        self._by_id: dict[str, Tool] = {}
        self._by_name: dict[str, str] = {}  # name -> tool_id

    def register(self, tool: Tool) -> str:
        """Register *tool* and return its tool_id.

        Rejects missing identity, forged ids that do not match compute,
        and reassignment of an existing tool_id to a different tool object.
        """
        if tool is None:
            raise ValueError("tool is required")
        try:
            tid = tool.tool_id
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"tool has no valid tool_id: {exc}") from exc
        if not tid or not isinstance(tid, str):
            raise ValueError("tool must define a non-empty tool_id")
        expected = tool.tool_id
        if tid != expected:
            raise ValueError(f"forged tool_id: got {tid!r}, expected {expected!r}")

        existing = self._by_id.get(tid)
        if existing is not None and existing is not tool:
            if existing.identity_tuple() != tool.identity_tuple():
                raise ValueError(
                    f"tool_id {tid[:12]}… already registered to a different implementation"
                )
            return tid

        prior_id = self._by_name.get(tool.name)
        if prior_id is not None and prior_id != tid:
            raise ValueError(
                f"tool name {tool.name!r} already registered with different tool_id "
                f"(possible substitution)"
            )

        self._by_id[tid] = tool
        self._by_name[tool.name] = tid
        return tid

    def get_by_id(self, tool_id: str) -> Tool | None:
        return self._by_id.get(tool_id)

    def get_by_name(self, name: str) -> Tool | None:
        tid = self._by_name.get(name)
        if tid is None:
            return None
        return self._by_id.get(tid)

    def is_trusted(self, tool: Tool) -> bool:
        registered = self._by_id.get(tool.tool_id)
        return registered is not None and registered.tool_id == tool.tool_id

    def list_all(self) -> list[Tool]:
        return list(self._by_id.values())


class ToolRegistry:
    """Central catalog of tools by name (legacy dispatch helper)."""

    def __init__(self, tools: Iterable[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools or ():
            self.register(tool)

    def register(self, tool: Tool) -> None:
        if not tool.name or not tool.name.strip():
            raise ValueError("tool must define a non-empty name")
        if tool.name in self._tools:
            raise ValueError(f"tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> Tool:
        return self._tools.pop(name)

    def get(self, name: str) -> Tool:
        return self._tools[name]

    def has(self, name: str) -> bool:
        return name in self._tools

    def names(self) -> list[str]:
        return list(self._tools)

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.to_schema() for tool in self._tools.values()]

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: object) -> bool:
        return name in self._tools

    async def call(self, name: str, **arguments: Any) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult.failed(f"unknown tool: {name}", metadata={"tool": name})

        error = self._validate(tool, arguments)
        if error is not None:
            return ToolResult.failed(error, metadata={"tool": name})

        try:
            result = await tool.execute(**arguments)
        except Exception as exc:  # noqa: BLE001
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
