"""Working memory: short-lived state for the current task."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class WorkingMemoryEntry:
    """A single entry in working memory."""

    key: str
    value: Any
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ttl_seconds: int | None = None


class WorkingMemory:
    """In-memory store for the current task's active state.

    Working memory is scoped to a single task. It is discarded when the
    task completes. It holds the intermediate values that the cognitive
    loop needs across stages: context, hypotheses, plans, observations.
    """

    def __init__(self) -> None:
        self._store: dict[str, WorkingMemoryEntry] = {}

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """Store a value under a key."""
        self._store[key] = WorkingMemoryEntry(
            key=key, value=value, ttl_seconds=ttl_seconds
        )

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value. Returns default if key is missing or expired."""
        entry = self._store.get(key)
        if entry is None:
            return default
        if self._is_expired(entry):
            del self._store[key]
            return default
        return entry.value

    def delete(self, key: str) -> None:
        """Remove a key from memory."""
        self._store.pop(key, None)

    def clear(self) -> None:
        """Remove all entries (end of task)."""
        self._store.clear()

    def keys(self) -> list[str]:
        """Return the list of active keys."""
        return [k for k, e in self._store.items() if not self._is_expired(e)]

    def __len__(self) -> int:
        return len(self.keys())

    def __contains__(self, key: str) -> bool:
        return key in self.keys()

    @staticmethod
    def _is_expired(entry: WorkingMemoryEntry) -> bool:
        if entry.ttl_seconds is None:
            return False
        elapsed = (datetime.now(timezone.utc) - entry.created_at).total_seconds()
        return elapsed > entry.ttl_seconds
