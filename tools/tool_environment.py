"""ToolEnvironment — injectable capability-scoped container.

EO-003 / EO-005 G4: I-005 Monotonic Delegation enforced by tool_id
(not name). Same-name substitution is rejected at the identity boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tools.tool_interface import Tool

__all__ = [
    "ToolEnvironment",
    "CapabilityViolationError",
    "EmptyEnvironment",
    "create_root",
]


class CapabilityViolationError(Exception):
    """Raised when a child environment tries to escalate authority (I-005)."""

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


@dataclass(frozen=True)
class ToolEnvironment:
    """Immutable, capability-scoped tool registry (no global state)."""

    environment_id: str
    tools: tuple[Tool, ...]
    capabilities: frozenset[str]
    parent_id: str | None = None

    def trusted_ids(self) -> frozenset[str]:
        """Frozen set of canonical tool_ids in this environment."""
        return frozenset(tool.tool_id for tool in self.tools)

    def has_tool(self, name: str) -> bool:
        return any(tool.name == name for tool in self.tools)

    def get_tool(self, name: str) -> Tool | None:
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None

    def list_tools(self) -> list[str]:
        return sorted(tool.name for tool in self.tools)

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
          * same-name / different-id substitution is rejected
        """
        violating_capabilities = capabilities - self.capabilities
        parent_ids = self.trusted_ids()
        child_ids = {t.tool_id for t in tools}
        violating_ids = child_ids - parent_ids

        parent_name_to_id = {t.name: t.tool_id for t in self.tools}
        substitutions: set[str] = set()
        for t in tools:
            expected = parent_name_to_id.get(t.name)
            if expected is not None and expected != t.tool_id:
                substitutions.add(f"substitution:{t.name}")

        if violating_capabilities or violating_ids or substitutions:
            name_for_id = {t.tool_id: t.name for t in tools}
            violations = (
                set(violating_capabilities)
                | {f"tool_id:{tid}" for tid in violating_ids}
                | {f"tool:{name_for_id[tid]}" for tid in violating_ids if tid in name_for_id}
                | substitutions
            )
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
            "tool_ids": sorted(self.trusted_ids()),
            "capabilities": sorted(self.capabilities),
        }


def create_root(
    environment_id: str,
    tools: list[Tool],
    capabilities: set[str],
) -> ToolEnvironment:
    """Create a root ToolEnvironment (fresh instance every call).

    Each tool must expose a valid tool_id; missing identity is rejected.
    """
    validated: list[Tool] = []
    for tool in tools:
        tid = getattr(tool, "tool_id", None)
        if not tid or not isinstance(tid, str):
            raise ValueError(
                f"tool {getattr(tool, 'name', '?')!r} has no valid tool_id"
            )
        validated.append(tool)
    return ToolEnvironment(
        environment_id=environment_id,
        tools=tuple(validated),
        capabilities=frozenset(capabilities),
        parent_id=None,
    )


def _empty_environment() -> ToolEnvironment:
    return ToolEnvironment(
        environment_id="__empty__",
        tools=(),
        capabilities=frozenset(),
        parent_id=None,
    )


EmptyEnvironment = _empty_environment
