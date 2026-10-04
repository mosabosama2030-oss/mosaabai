"""Episodic memory: chronological record of past tasks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class Episode:
    """A single recorded episode (task run)."""

    episode_id: str
    task_description: str
    outcome: str
    success: bool
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class EpisodicMemory:
    """Chronological log of all task executions.

    Used by the cognitive loop to recall what was done before, detect
    recurring patterns, and inform future planning.
    """

    def __init__(self, max_size: int = 10000) -> None:
        self._episodes: list[Episode] = []
        self._max_size = max_size

    def record(self, episode: Episode) -> None:
        """Append an episode. Trims oldest if over capacity."""
        self._episodes.append(episode)
        if len(self._episodes) > self._max_size:
            self._episodes = self._episodes[-self._max_size :]

    def all(self) -> list[Episode]:
        """Return all episodes in chronological order."""
        return list(self._episodes)

    def recent(self, n: int = 10) -> list[Episode]:
        """Return the n most recent episodes."""
        return self._episodes[-n:]

    def successful(self) -> list[Episode]:
        """Return only successful episodes."""
        return [e for e in self._episodes if e.success]

    def failed(self) -> list[Episode]:
        """Return only failed episodes."""
        return [e for e in self._episodes if not e.success]

    def __len__(self) -> int:
        return len(self._episodes)
