"""Tests for working memory."""

from __future__ import annotations

import time

from memory.working import WorkingMemory


def test_set_and_get() -> None:
    wm = WorkingMemory()
    wm.set("task", "analyze csv")
    assert wm.get("task") == "analyze csv"


def test_get_missing_returns_default() -> None:
    wm = WorkingMemory()
    assert wm.get("nope") is None
    assert wm.get("nope", "fallback") == "fallback"


def test_delete() -> None:
    wm = WorkingMemory()
    wm.set("x", 1)
    wm.delete("x")
    assert wm.get("x") is None


def test_clear() -> None:
    wm = WorkingMemory()
    wm.set("a", 1)
    wm.set("b", 2)
    wm.clear()
    assert len(wm) == 0


def test_ttl_expiration() -> None:
    wm = WorkingMemory()
    wm.set("short", "value", ttl_seconds=1)
    assert wm.get("short") == "value"
    time.sleep(1.1)
    assert wm.get("short") is None


def test_keys_and_contains() -> None:
    wm = WorkingMemory()
    wm.set("k1", 1)
    wm.set("k2", 2)
    assert set(wm.keys()) == {"k1", "k2"}
    assert "k1" in wm
    assert "k3" not in wm
