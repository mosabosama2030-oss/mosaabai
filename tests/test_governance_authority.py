"""S2-A — Authority model tests."""

from __future__ import annotations

import pytest

from core.security_exceptions import AuthorityViolationError
from governance.authority import Authority


def test_root_authority_has_no_parent() -> None:
    root = Authority(subject="human", scope=frozenset({"read", "write"}))
    assert root.parent is None
    assert "read" in root.scope


def test_child_authority_subset_of_parent() -> None:
    parent = Authority(subject="root", scope=frozenset({"a", "b", "c"}))
    child = Authority(subject="agent", scope=frozenset({"a", "b"}), parent=parent)
    assert child.scope.issubset(parent.scope)
    assert child.parent is parent


def test_child_exceeds_parent_rejected() -> None:
    parent = Authority(subject="root", scope=frozenset({"a"}))
    with pytest.raises(AuthorityViolationError):
        Authority(subject="agent", scope=frozenset({"a", "b"}), parent=parent)


def test_authority_immutable() -> None:
    auth = Authority(subject="human", scope=frozenset({"x"}))
    with pytest.raises(Exception):
        auth.subject = "other"  # type: ignore[misc]
