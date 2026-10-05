"""Authority model — monotonic delegation (I-005)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Optional

from core.security_exceptions import AuthorityViolationError


@dataclass(frozen=True)
class Authority:
    """Immutable authority credential.

    scope is a frozenset of capability names (str).
    Child scope must be ⊆ parent scope when parent is set.
    """

    subject: str
    scope: frozenset[str]
    parent: Optional[Authority] = None
    created_at: str = ""
    signature: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.created_at:
            object.__setattr__(
                self,
                "created_at",
                datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            )
        if not isinstance(self.scope, frozenset):
            object.__setattr__(self, "scope", frozenset(self.scope))
        if self.parent is not None and not self.scope.issubset(self.parent.scope):
            raise AuthorityViolationError(
                f"child scope {sorted(self.scope)} not ⊆ parent scope "
                f"{sorted(self.parent.scope)}"
            )
