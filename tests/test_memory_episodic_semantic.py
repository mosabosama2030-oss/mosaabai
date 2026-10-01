"""Tests for episodic and semantic memory."""

from __future__ import annotations

import pytest

from memory.episodic import Episode, EpisodicMemory
from memory.semantic import SemanticMemory


# ---- Episodic ----

def _make_episode(id_: str, success: bool = True) -> Episode:
    return Episode(
        episode_id=id_,
        task_description=f"task {id_}",
        outcome="done" if success else "failed",
        success=success,
    )


def test_episodic_record_and_len() -> None:
    em = EpisodicMemory()
    em.record(_make_episode("1"))
    em.record(_make_episode("2"))
    assert len(em) == 2


def test_episodic_recent() -> None:
    em = EpisodicMemory()
    for i in range(5):
        em.record(_make_episode(str(i)))
    recent = em.recent(2)
    assert [e.episode_id for e in recent] == ["3", "4"]


def test_episodic_successful_and_failed() -> None:
    em = EpisodicMemory()
    em.record(_make_episode("ok", True))
    em.record(_make_episode("no", False))
    assert len(em.successful()) == 1
    assert len(em.failed()) == 1


def test_episodic_max_size() -> None:
    em = EpisodicMemory(max_size=3)
    for i in range(5):
        em.record(_make_episode(str(i)))
    assert len(em) == 3
    assert em.all()[0].episode_id == "2"


# ---- Semantic ----

def test_semantic_store_and_recall() -> None:
    sm = SemanticMemory()
    sm.store("capital_of_egypt", "Cairo", confidence=0.99, source="wikipedia")
    fact = sm.recall("capital_of_egypt")
    assert fact is not None
    assert fact.value == "Cairo"
    assert fact.confidence == 0.99
    assert fact.source == "wikipedia"


def test_semantic_forget() -> None:
    sm = SemanticMemory()
    sm.store("x", 1)
    sm.forget("x")
    assert sm.recall("x") is None


def test_semantic_confidence_validation() -> None:
    sm = SemanticMemory()
    with pytest.raises(ValueError):
        sm.store("bad", "value", confidence=1.5)


def test_semantic_high_confidence() -> None:
    sm = SemanticMemory()
    sm.store("a", 1, confidence=0.9)
    sm.store("b", 2, confidence=0.5)
    high = sm.high_confidence(threshold=0.8)
    assert len(high) == 1
    assert high[0].key == "a"


def test_semantic_contains() -> None:
    sm = SemanticMemory()
    sm.store("k", "v")
    assert "k" in sm
    assert "missing" not in sm
