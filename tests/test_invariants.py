"""S2-D — I-001 and I-005 enforcement tests."""

from __future__ import annotations

import pytest

from core.security_exceptions import InvariantViolationError
from governance.authority import Authority
from governance.invariants import assert_I001, assert_I005


def test_i001_model_cannot_create_authority() -> None:
    with pytest.raises(InvariantViolationError):
        assert_I001("model", "create_authority")


def test_i001_human_can_create_authority() -> None:
    assert_I001("human", "create_authority")


def test_i005_child_exceeds_rejected() -> None:
    parent = Authority(subject="root", scope=frozenset({"a"}))
    wider = Authority(subject="agent2", scope=frozenset({"a", "b"}))
    with pytest.raises(InvariantViolationError):
        assert_I005(parent, wider)


def test_i005_child_subset_accepted() -> None:
    parent = Authority(subject="root", scope=frozenset({"a", "b", "c"}))
    child = Authority(subject="agent", scope=frozenset({"a", "b"}), parent=parent)
    assert_I005(parent, child)


def test_i005_transitive_delegation() -> None:
    root = Authority(subject="root", scope=frozenset({"a", "b", "c", "d"}))
    mid = Authority(subject="mid", scope=frozenset({"a", "b", "c"}), parent=root)
    leaf = Authority(subject="leaf", scope=frozenset({"a"}), parent=mid)
    assert_I005(root, mid)
    assert_I005(mid, leaf)
    assert_I005(root, leaf)
