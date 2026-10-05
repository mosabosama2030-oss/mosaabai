"""Security exception types for EO-005 G4 (CRIT-01..05)."""

from __future__ import annotations


class SecurityDowngradeError(Exception):
    """Hard security failure: missing tool_id, name-based fallback, etc."""


class ASTSecurityViolationError(Exception):
    """AST whitelist violation (CRIT-03)."""


class StatefulToolError(Exception):
    """Tool has freevars/cellvars or non-pure code object (CRIT-02)."""


class RegistryImmutableError(Exception):
    """TrustedToolRegistry mutation attempted (CRIT-05)."""


class ToolExecutionError(Exception):
    """Operational tool failure (may be mapped to Result.err)."""
