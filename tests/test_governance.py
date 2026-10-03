"""Tests for the governance layer: permissions and risk."""

from __future__ import annotations

import pytest

from governance.permissions import Permission, PermissionEngine, PermissionSet
from governance.risk import RiskAssessment, RiskEngine, RiskLevel

# ---- PermissionSet ----


def test_permission_set_empty_default() -> None:
    ps = PermissionSet()
    assert isinstance(ps.permissions, frozenset)
    assert len(ps.permissions) == 0


def test_permission_set_has() -> None:
    ps = PermissionSet(frozenset({Permission.READ}))
    assert ps.has(Permission.READ)
    assert not ps.has(Permission.NETWORK)


def test_add_returns_new_set_original_unchanged() -> None:
    original = PermissionSet(frozenset({Permission.READ}))
    updated = original.add(Permission.WRITE)
    assert updated is not original
    assert updated.has(Permission.WRITE)
    assert original.has(Permission.READ)
    assert not original.has(Permission.WRITE)


def test_remove_returns_new_set_original_unchanged() -> None:
    original = PermissionSet(frozenset({Permission.READ, Permission.WRITE}))
    updated = original.remove(Permission.READ)
    assert updated is not original
    assert not updated.has(Permission.READ)
    assert original.has(Permission.READ)
    assert updated.has(Permission.WRITE)


def test_union_combines_sets_without_mutating_operands() -> None:
    a = PermissionSet(frozenset({Permission.READ}))
    b = PermissionSet(frozenset({Permission.WRITE, Permission.EXECUTE}))
    combined = a.union(b)
    assert combined.has(Permission.READ)
    assert combined.has(Permission.WRITE)
    assert combined.has(Permission.EXECUTE)
    assert not a.has(Permission.WRITE)
    assert not b.has(Permission.READ)


# ---- PermissionEngine ----


def test_grant_and_check() -> None:
    engine = PermissionEngine()
    engine.grant("agent-1", PermissionSet(frozenset({Permission.READ, Permission.WRITE})))
    assert engine.check("agent-1", Permission.READ) is True
    assert engine.check("agent-1", Permission.WRITE) is True
    assert engine.check("agent-1", Permission.NETWORK) is False


def test_known_agent_without_permission_is_denied() -> None:
    engine = PermissionEngine()
    engine.grant("agent-1", PermissionSet())
    assert engine.check("agent-1", Permission.READ) is False


def test_unknown_agent_returns_false() -> None:
    engine = PermissionEngine()
    assert engine.check("ghost", Permission.READ) is False
    assert engine.check("ghost", Permission.EXECUTE) is False


def test_default_deny_on_fresh_engine() -> None:
    engine = PermissionEngine()
    assert engine.list_agents() == []
    for permission in Permission:
        assert engine.check("anyone", permission) is False


def test_revoke_removes_agent() -> None:
    engine = PermissionEngine()
    engine.grant("agent-1", PermissionSet(frozenset({Permission.READ})))
    engine.revoke("agent-1")
    assert engine.check("agent-1", Permission.READ) is False
    assert engine.list_agents() == []
    engine.revoke("never-existed")  # no-op, must not raise


def test_list_agents() -> None:
    engine = PermissionEngine()
    engine.grant("b", PermissionSet())
    engine.grant("a", PermissionSet())
    assert sorted(engine.list_agents()) == ["a", "b"]


# ---- RiskEngine ----


@pytest.mark.parametrize(
    ("action", "level", "approval"),
    [
        ("delete the stale records", RiskLevel.CRITICAL, True),
        ("drop the temporary cache", RiskLevel.CRITICAL, True),
        ("remove old entries", RiskLevel.CRITICAL, True),
        ("destroy the sandbox", RiskLevel.CRITICAL, True),
        ("write the report", RiskLevel.MEDIUM, False),
        ("create a new workspace", RiskLevel.MEDIUM, False),
        ("modify the profile", RiskLevel.MEDIUM, False),
        ("update the config", RiskLevel.MEDIUM, False),
        ("list the users", RiskLevel.LOW, False),
        ("show the dashboard", RiskLevel.LOW, False),
        ("get the current status", RiskLevel.LOW, False),
        ("fetch remote data", RiskLevel.LOW, False),
        ("execute the plan", RiskLevel.HIGH, True),
        ("run the pipeline", RiskLevel.HIGH, True),
        ("deploy the service", RiskLevel.HIGH, True),
        ("install the package", RiskLevel.HIGH, True),
    ],
)
def test_risk_each_keyword_category(action: str, level: RiskLevel, approval: bool) -> None:
    result = RiskEngine().assess(action)
    assert result.level == level
    assert result.requires_approval is approval


def test_risk_case_insensitive() -> None:
    engine = RiskEngine()
    assert engine.assess("DELETE everything").level == RiskLevel.CRITICAL
    assert engine.assess("Please Deploy Now").requires_approval is True
    assert engine.assess("Write THE Report").level == RiskLevel.MEDIUM
    assert engine.assess("LIST items").level == RiskLevel.LOW


def test_risk_default_for_unknown_action() -> None:
    result = RiskEngine().assess("frobnicate the quux")
    assert result.level == RiskLevel.MEDIUM
    assert result.requires_approval is False


def test_risk_default_for_empty_action() -> None:
    result = RiskEngine().assess("")
    assert result.level == RiskLevel.MEDIUM
    assert result.requires_approval is False


def test_risk_assessment_fields() -> None:
    result = RiskEngine().assess("delete the record")
    assert isinstance(result, RiskAssessment)
    assert result.level == RiskLevel.CRITICAL
    assert result.requires_approval is True
    assert "delete" in result.reason
