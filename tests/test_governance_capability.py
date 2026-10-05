"""S2-B — Capability model tests."""

from __future__ import annotations

import pytest

from governance.capability import Capability, CapabilitySet


def test_capability_immutable() -> None:
    c = Capability(name="read", constraints={"path": "/tmp"})
    with pytest.raises(TypeError):
        c.constraints["path"] = "/etc"  # type: ignore[index]


def test_capability_hashable() -> None:
    c1 = Capability(name="read", constraints={"a": 1})
    c2 = Capability(name="read", constraints={"a": 1})
    s = {c1, c2}
    assert len(s) == 1


def test_capability_subset() -> None:
    a = Capability(name="a", constraints={})
    b = Capability(name="b", constraints={})
    s1 = CapabilitySet([a])
    s2 = CapabilitySet([a, b])
    assert s1.issubset(s2)
    assert s2.issuperset(s1)
    assert a in s2


def test_capability_deterministic_serial() -> None:
    c = Capability(name="x", constraints={"b": 2, "a": 1})
    d = c.to_dict()
    assert list(d["constraints"].keys()) == ["a", "b"]
    assert d["name"] == "x"
