"""ToolEnvironment — injectable capability-scoped container with canonical identity.

Fixes F-002 / strengthens I-005:
  - Child tools must be a subset by *tool_id*, not by name.
  - Same-name substitution of a different implementation is rejected.
  - TrustedToolRegistry tracks known good identities.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tools.tool_interface import Tool

__all__ = [
    "ToolEnvironment",
    "CapabilityViolationError",
    "IdentityViolationError",
    "TrustedToolRegistry",
    "EmptyEnvironment",
    "create_root",
]


class CapabilityViolationError(Exception):
    """Raised when a child tries to escalate authority (I-005)."""

    def __init__(
        self,
        parent_id: str | None,
        child_id: str,
        violating_capabilities: set[str],
    ) -> None:
        self.parent_id = parent_id
        self.child_id = child_id
        self.violating_capabilities = violating_capabilities
        message = (
            f"capability escalation in child '{child_id}': "
            f"{sorted(violating_capabilities)} not in parent '{parent_id}'"
        )
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "child_id": self.child_id,
            "parent_id": self.parent_id,
            "violating_capabilities": sorted(self.violating_capabilities),
            "message": str(self),
        }


class IdentityViolationError(Exception):
    """Raised when a tool identity does not match a trusted / parent identity."""

    def __init__(self, message: str, *, tool_name: str, expected_id: str, actual_id: str) -> None:
        self.tool_name = tool_name
        self.expected_id = expected_id
        self.actual_id = actual_id
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "expected_id": self.expected_id,
            "actual_id": self.actual_id,
            "message": str(self),
        }


class TrustedToolRegistry:
    """Maps tool_id -> (name, version). Source of truth for known-good tools."""

    def __init__(self) -> None:
        self._by_id: dict[str, tuple[str, str]] = {}
        self._by_name: dict[str, str] = {}

    def register(self, tool: Tool) -> None:
        tid = tool.tool_id
        self._by_id[tid] = (tool.name, tool.version)
        self._by_name[tool.name] = tid

    def is_trusted(self, tool: Tool) -> bool:
        return tool.tool_id in self._by_id

    def expected_id(self, name: str) -> str | None:
        return self._by_name.get(name)

    def verify(self, tool: Tool) -> None:
        expected = self._by_name.get(tool.name)
        if expected is None:
            raise IdentityViolationError(
                f"tool '{tool.name}' is not in the trusted registry",
                tool_name=tool.name,
                expected_id="",
                actual_id=tool.tool_id,
            )
        if tool.tool_id != expected:
            raise IdentityViolationError(
                f"tool '{tool.name}' identity mismatch (possible substitution)",
                tool_name=tool.name,
                expected_id=expected,
                actual_id=tool.tool_id,
            )


@dataclass(frozen=True)
class ToolEnvironment:
    """Immutable, capability-scoped tool registry (no global state)."""

    environment_id: str
    tools: tuple[Tool, ...]
    capabilities: frozenset[str]
    parent_id: str | None = None

    def _id_set(self) -> frozenset[str]:
        return frozenset(t.tool_id for t in self.tools)

    def _name_to_id(self) -> dict[str, str]:
        return {t.name: t.tool_id for t in self.tools}

    def has_tool(self, name: str) -> bool:
        return any(tool.name == name for tool in self.tools)

    def get_tool(self, name: str) -> Tool | None:
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None

    def get_tool_by_id(self, tool_id: str) -> Tool | None:
        for tool in self.tools:
            if tool.tool_id == tool_id:
                return tool
        return None

    def list_tools(self) -> list[str]:
        return sorted(tool.name for tool in self.tools)

    def list_tool_ids(self) -> list[str]:
        return sorted(tool.tool_id for tool in self.tools)

    def has_capability(self, cap: str) -> bool:
        return cap in self.capabilities

    def spawn_child(
        self,
        environment_id: str,
        tools: tuple[Tool, ...],
        capabilities: frozenset[str],
    ) -> ToolEnvironment:
        """Create a child environment; enforce monotonic delegation (I-005).

        Rules:
          * new.capabilities ⊆ self.capabilities
          * every child tool.tool_id must exist in parent (identity, not name)
        """
        violating_capabilities = capabilities - self.capabilities
        parent_ids = self._id_set()
        violating_ids = {t.tool_id for t in tools} - parent_ids

        parent_name_map = self._name_to_id()
        substitutions: set[str] = set()
        for t in tools:
            expected = parent_name_map.get(t.name)
            if expected is not None and expected != t.tool_id:
                substitutions.add(f"substitution:{t.name}")

        if violating_capabilities or violating_ids or substitutions:
            violations = set(violating_capabilities) | {
                f"tool_id:{tid}" for tid in violating_ids
            } | substitutions
            raise CapabilityViolationError(
                parent_id=self.environment_id,
                child_id=environment_id,
                violating_capabilities=violations,
            )
        return ToolEnvironment(
            environment_id=environment_id,
            tools=tools,
            capabilities=capabilities,
            parent_id=self.environment_id,
        )

    def describe(self) -> dict[str, Any]:
        return {
            "environment_id": self.environment_id,
            "parent_id": self.parent_id,
            "tool_count": len(self.tools),
            "capability_count": len(self.capabilities),
            "tools": self.list_tools(),
            "tool_ids": self.list_tool_ids(),
            "capabilities": sorted(self.capabilities),
        }


def create_root(
    environment_id: str,
    tools: list[Tool],
    capabilities: set[str],
) -> ToolEnvironment:
    """Create a root ToolEnvironment (fresh instance every call)."""
    return ToolEnvironment(
        environment_id=environment_id,
        tools=tuple(tools),
        capabilities=frozenset(capabilities),
        parent_id=None,
    )


def EmptyEnvironment() -> ToolEnvironment:
    """Sandbox root: no tools, no capabilities."""
    return ToolEnvironment(
        environment_id="__empty__",
        tools=(),
        capabilities=frozenset(),
        parent_id=None,
    )
