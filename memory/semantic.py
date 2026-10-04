"""Semantic memory: long-term storage of facts and concepts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class Fact:
    """A stored fact with provenance and confidence."""

    key: str
    value: Any
    confidence: float = 1.0
    source: str = "unknown"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class SemanticMemory:
    """Store of durable facts and concepts.

    Unlike working memory (task-scoped) or episodic memory (chronological),
    semantic memory holds knowledge that persists across tasks.
    """

    def __init__(self) -> None:
        self._facts: dict[str, Fact] = {}

    def store(
        self,
        key: str,
        value: Any,
        confidence: float = 1.0,
        source: str = "unknown",
    ) -> None:
        """Store or update a fact."""
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        self._facts[key] = Fact(
            key=key, value=value, confidence=confidence, source=source
        )

    def recall(self, key: str) -> Fact | None:
        """Retrieve a fact by key."""
        return self._facts.get(key)

    def forget(self, key: str) -> None:
        """Remove a fact."""
        self._facts.pop(key, None)

    def all_facts(self) -> list[Fact]:
        """Return all stored facts."""
        return list(self._facts.values())

    def high_confidence(self, threshold: float = 0.8) -> list[Fact]:
        """Return facts above a confidence threshold."""
        return [f for f in self._facts.values() if f.confidence >= threshold]

    def __len__(self) -> int:
        return len(self._facts)

    def __contains__(self, key: str) -> bool:
        return key in self._facts
