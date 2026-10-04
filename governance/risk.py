"""Governance risk: assess how dangerous a proposed action is."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RiskLevel(StrEnum):
    """Severity of an assessed action."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskAssessment:
    """Outcome of assessing a single action."""

    level: RiskLevel
    reason: str
    requires_approval: bool


# (level, requires_approval, keywords, kind), evaluated in order; first match wins.
_RULES: tuple[tuple[RiskLevel, bool, tuple[str, ...], str], ...] = (
    (RiskLevel.CRITICAL, True, ("delete", "drop", "remove", "destroy"), "destructive"),
    (RiskLevel.MEDIUM, False, ("write", "create", "modify", "update"), "mutating"),
    (RiskLevel.LOW, False, ("read", "list", "show", "get", "fetch"), "read-only"),
    (RiskLevel.HIGH, True, ("execute", "run", "deploy", "install"), "execution"),
)


class RiskEngine:
    """Estimates action risk with keyword rules.

    Matching is case-insensitive; rules are evaluated in order and the
    first match wins. Unrecognized actions default to MEDIUM risk
    without approval.
    """

    def assess(self, action: str, context: dict | None = None) -> RiskAssessment:
        """Assess an action's risk. `context` is reserved for future rules."""
        if action:
            text = action.lower()
            for level, requires_approval, keywords, kind in _RULES:
                for keyword in keywords:
                    if keyword in text:
                        reason = f"{kind} keyword '{keyword}' in action"
                        return RiskAssessment(level, reason, requires_approval)
        return RiskAssessment(RiskLevel.MEDIUM, "unrecognized action", requires_approval=False)
