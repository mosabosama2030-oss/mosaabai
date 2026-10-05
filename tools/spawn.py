"""spawn_child — Authority-gated tool execution (S2-C)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Callable

from core.security_exceptions import AuthorityViolationError
from governance.authority import Authority


def spawn_child(
    tool_id: str,
    *,
    authority: Authority,
    required_capabilities: frozenset[str] | None = None,
    fn: Callable[..., Any] | None = None,
    args: tuple[Any, ...] = (),
    kwargs: dict[str, Any] | None = None,
    wal: Any | None = None,
) -> Any:
    """Execute a tool under *authority* scope.

    required_capabilities must be ⊆ authority.scope.
    On violation: raise AuthorityViolationError and append WAL CRITICAL.
    """
    if authority is None:
        raise AuthorityViolationError("spawn_child requires authority: Authority")
    if not isinstance(authority, Authority):
        raise AuthorityViolationError("authority must be an Authority instance")

    needed = required_capabilities if required_capabilities is not None else frozenset()
    if not needed.issubset(authority.scope):
        _wal_critical(wal, tool_id, authority, needed)
        raise AuthorityViolationError(
            f"insufficient authority: need {sorted(needed)}, "
            f"have {sorted(authority.scope)}"
        )

    if fn is None:
        raise AuthorityViolationError("no callable provided for tool execution")

    return fn(*(args or ()), **(kwargs or {}))


def _wal_critical(
    wal: Any,
    tool_id: str,
    authority: Authority,
    needed: frozenset[str],
) -> None:
    if wal is None:
        return
    from core.wal import IntentStatus, WALEntry

    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    eid = str(uuid.uuid4())
    entry = WALEntry.create(
        entry_id=eid,
        action_id=f"CRITICAL:authority:{tool_id}",
        idempotency_key=eid,
        intent={
            "tool_id": tool_id,
            "needed": sorted(needed),
            "have": sorted(authority.scope),
            "subject": authority.subject,
        },
        status=IntentStatus.FAILED,
        created_at=now,
        updated_at=now,
        error="authority_violation",
    )
    wal.append(entry)
