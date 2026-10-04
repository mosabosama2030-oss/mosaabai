"""ToolEnvironment — injectable capability-scoped container for tool registries.

EO-003 / Canonical Architecture A0.3. Establishes I-005 (Monotonic Delegation).

Standard library only: no Pydantic, no external dependencies.

Thread safety: all public methods are read-only or pure functions over
immutable frozen dataclass fields, so no locking is required. Instances are
immutable by construction (dataclass(frozen=True)), which is the thread-safe
guarantee: a child never shares mutable state with its parent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tools.tool_interface import Tool

__all__ = [
    "ToolEnvironment",
    "CapabilityViolationError",
    "EmptyEnvironment",
]


class CapabilityViolationError(Exception):
    """Raised when a child environment tries to escalate authority.

    I-005 (Monotonic Delegation): authority can only flow down, never up or
    outward, and a child can never hold more capability than its parent.
    """

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
        """Deterministic JSON-safe representation with sorted keys."""
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
          * new.capabilities must be a subset of self.capabilities
          * new.tools must be a subset of self.tools (by spec.name)
        """
        violating_capabilities = capabilities - self.capabilities
        violating_tool_names = {tool.name for tool in tools} - {tool.name for tool in self.tools}
        if violating_capabilities or violating_tool_names:
            violations = set(violating_capabilities) | {
                f"tool:{name}" for name in violating_tool_names
            }
            # Graceful enforcement: no raise during instantiation of the
            # child object itself — the violation is reported structurally.
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
        """Deterministic, sorted-key description for logging and audit."""
        return {
            "environment_id": self.environment_id,
            "parent_id": self.parent_id,
            "tool_count": len(self.tools),
            "capability_count": len(self.capabilities),
            "tools": self.list_tools(),
            "capabilities": sorted(self.capabilities),
        }


def tool_environment_factory() -> tuple[ToolEnvironment, ToolEnvironment]:
    """Factory for root environments — no global state, no singleton.

    Every call returns a brand-new independent instance.
    """

    def create_root(
        environment_id: str,
        tools: list[Tool],
        capabilities: set[str],
    ) -> ToolEnvironment:
        return ToolEnvironment(
            environment_id=environment_id,
            tools=tuple(tools),
            capabilities=frozenset(capabilities),
            parent_id=None,
        )

    def _empty_sandbox() -> ToolEnvironment:
        """Sandbox root: no tools, no capabilities."""
        return ToolEnvironment(
            environment_id="__empty__",
            tools=(),
            capabilities=frozenset(),
            parent_id=None,
        )

    return create_root, _empty_sandbox


# Convenience singletons (module-level factories only — no shared state).
_create_root, _empty_sandbox = tool_environment_factory()


def create_root(
    environment_id: str,
    tools: list[Tool],
    capabilities: set[str],
) -> ToolEnvironment:
    """Create a root ToolEnvironment (fresh instance every call)."""
    return _create_root(environment_id, tools, capabilities)


def _empty_sandbox() -> ToolEnvironment:
    """Sandbox root environment with no tools and no capabilities."""
    return ToolEnvironment(
        environment_id="__empty__",
        tools=(),
        capabilities=frozenset(),
        parent_id=None,
    )


def _empty_environment() -> ToolEnvironment:
    """Sandbox root environment with no tools and no capabilities."""
    return _empty_sandbox()


# Spec-compatible public API alias (lowercase def keeps project ruff N802 clean).
EmptyEnvironment = _empty_environment
