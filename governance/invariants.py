"""Constitutional invariant enforcement points (I-001, I-005)."""

from __future__ import annotations

from core.security_exceptions import InvariantViolationError
from governance.authority import Authority


def assert_I001(actor_kind: str, action: str) -> None:
    """I-001: no model output creates authority."""
    if actor_kind == "model" and action == "create_authority":
        raise InvariantViolationError(
            "I-001 violated: model cannot create_authority"
        )


def assert_I005(parent: Authority, child: Authority) -> None:
    """I-005: E(child) ⊆ E(parent) — monotonic delegation."""
    if not child.scope.issubset(parent.scope):
        raise InvariantViolationError(
            f"I-005 violated: child scope {sorted(child.scope)} "
            f"not ⊆ parent {sorted(parent.scope)}"
        )
