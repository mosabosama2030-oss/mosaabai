"""Governance permissions: what agents are allowed to do."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Permission(StrEnum):
    """Capabilities an agent may be granted."""

    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    NETWORK = "network"
    FILESYSTEM = "filesystem"
    COMPUTE = "compute"
    MEMORY = "memory"
    AGENT_CREATE = "agent_create"


@dataclass(frozen=True)
class PermissionSet:
    """An immutable set of permissions."""

    permissions: frozenset[Permission] = frozenset()

    def __post_init__(self) -> None:
        # Enforce the frozenset invariant even when built from another iterable.
        object.__setattr__(self, "permissions", frozenset(self.permissions))

    def has(self, permission: Permission) -> bool:
        """Return whether the set contains a permission."""
        return permission in self.permissions

    def add(self, permission: Permission) -> PermissionSet:
        """Return a new set containing the permission; this set is unchanged."""
        return PermissionSet(self.permissions | {permission})

    def remove(self, permission: Permission) -> PermissionSet:
        """Return a new set without the permission; this set is unchanged."""
        return PermissionSet(self.permissions - {permission})

    def union(self, other: PermissionSet) -> PermissionSet:
        """Return a new set with the permissions of both sets."""
        return PermissionSet(self.permissions | other.permissions)


class PermissionEngine:
    """Deny-by-default permission registry for agents.

    Agents start with no permissions: unknown agents and known agents
    without a matching permission are always denied. `grant` installs
    the agent's full set (replacing any previous set); `revoke` removes
    the agent entirely.
    """

    def __init__(self) -> None:
        self._agents: dict[str, PermissionSet] = {}

    def grant(self, agent_id: str, permissions: PermissionSet) -> None:
        """Set an agent's permission set, replacing any previous set."""
        self._agents[agent_id] = permissions

    def check(self, agent_id: str, permission: Permission) -> bool:
        """Return whether an agent holds a permission. Unknown agents are denied."""
        permissions = self._agents.get(agent_id)
        return permissions is not None and permissions.has(permission)

    def revoke(self, agent_id: str) -> None:
        """Remove an agent and all of its permissions. No-op if unknown."""
        self._agents.pop(agent_id, None)

    def list_agents(self) -> list[str]:
        """Return the ids of all known agents."""
        return list(self._agents)
