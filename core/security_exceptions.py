"""Security and governance exception types."""

from __future__ import annotations


class SecurityDowngradeError(Exception):
    """Hard security failure / privilege downgrade attempt."""


class AuthorityViolationError(SecurityDowngradeError):
    """Authority scope or monotonic-delegation violation (I-005)."""


class InvariantViolationError(SecurityDowngradeError):
    """Constitutional invariant breach (I-001, I-005, …)."""
