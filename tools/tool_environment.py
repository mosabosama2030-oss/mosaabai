"""ToolEnvironment — injectable capability-scoped container.

EO-003 / EO-005 G4 remediation (F-016): I-005 enforced by *recomputed*
canonical digests, never by self-reported tool.tool_id alone.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tools.tool_interface import Tool, compute_tool_id

__all__ = [
    "ToolEnvironment",
    "CapabilityViolationError",
    "EmptyEnvironment",
    "create_root",
    "canonical_tool_id",
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


def canonical_tool_id(tool: Tool) -> str:
    """Independently recompute identity from the tool's public spec.

    Never trust tool.tool_id alone (F-016). The digest is derived only from
    to_schema() fields — an overridden tool_id property cannot forge this.
    """
    return compute_tool_id(tool.to_schema())


def _assert_identity_bound(tool: Tool, environment_id: str | None = None) -> str:
    """Return canonical id; raise CapabilityViolationError on self-attested mismatch."""
    canonical = canonical_tool_id(tool)
    claimed = getattr(tool, "tool_id", None)
    if claimed is not None and claimed != canonical:
        raise CapabilityViolationError(
            parent_id=environment_id,
            child_id=getattr(tool, "name", "?"),
            violating_capabilities={f"forged_tool_id:{getattr(tool, 'name', '?')}"},
        )
    return canonical


@dataclass(frozen=True)
class ToolEnvironment:
    """Immutable, capability-scoped tool registry (no global state)."""

    environment_id: str
    tools: tuple[Tool, ...]
    capabilities: frozenset[str]
    parent_id: str | None = None

    def trusted_ids(self) -> frozenset[str]:
        """Frozen set of *recomputed* canonical tool_ids (not self-reported)."""
        return frozenset(canonical_tool_id(tool) for tool in self.tools)

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
          * every child tool's *recomputed* canonical id ⊆ parent trusted_ids
          * self-reported tool_id must match recomputed digest (F-016)
          * same-name / different-id substitution is rejected
        """
        violating_capabilities = capabilities - self.capabilities
        parent_ids = self.trusted_ids()

        forged: set[str] = set()
        child_canonical: dict[str, str] = {}
        for t in tools:
            try:
                cid = _assert_identity_bound(t, environment_id=self.environment_id)
            except CapabilityViolationError as exc:
                forged |= set(exc.violating_capabilities)
                cid = canonical_tool_id(t)
            child_canonical[t.name] = cid

        child_ids = set(child_canonical.values())
        violating_ids = child_ids - parent_ids

        parent_name_to_id = {t.name: canonical_tool_id(t) for t in self.tools}
        substitutions: set[str] = set()
        for t in tools:
            expected = parent_name_to_id.get(t.name)
            actual = child_canonical.get(t.name)
            if expected is not None and actual is not None and expected != actual:
                substitutions.add(f"substitution:{t.name}")

        if violating_capabilities or violating_ids or substitutions or forged:
            name_for_id = {cid: name for name, cid in child_canonical.items()}
            violations = (
                set(violating_capabilities)
                | {f"tool_id:{tid}" for tid in violating_ids}
                | {f"tool:{name_for_id[tid]}" for tid in violating_ids if tid in name_for_id}
                | substitutions
                | forged
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

    Each tool's self-reported tool_id must match the recomputed digest (F-016).
    """
    validated: list[Tool] = []
    for tool in tools:
        try:
            _assert_identity_bound(tool, environment_id=None)
        except CapabilityViolationError as exc:
            raise ValueError(
                f"tool {getattr(tool, 'name', '?')!r} has forged tool_id: "
                f"{sorted(exc.violating_capabilities)}"
            ) from exc
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
