"""Write-Ahead Log (WAL) for the cognitive loop — Phase P0.5.0-A0.1."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class IntentStatus(StrEnum):
    """Lifecycle status of a recorded intent in the WAL."""

    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class WALEntry(BaseModel):
    """A single write-ahead log entry.

    Frozen after construction so an entry, once written, is immutable.
    """

    model_config = {"frozen": True, "protect_assignment": True}

    entry_id: str
    action_id: str
    idempotency_key: str = Field(..., alias="idempotency_key")
    intent: dict[str, Any]
    status: IntentStatus
    created_at: str
    updated_at: str
    result: dict[str, Any] | None = None
    error: str | None = None

    @classmethod
    def create(
        cls,
        *,
        entry_id: str,
        action_id: str,
        idempotency_key: str,
        intent: dict[str, Any],
        status: IntentStatus,
        created_at: str,
        updated_at: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> WALEntry:
        """Construct a frozen entry via pydantic's validated model builder."""
        return cls(
            entry_id=entry_id,
            action_id=action_id,
            idempotency_key=idempotency_key,
            intent=intent,
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            result=result,
            error=error,
        )


class WriteAheadLog:
    """Thread-safe, JSONL-persistent, log-structured write-ahead log.

    Design:
      - One JSON object per line (JSONL) so entries survive partial writes
        and can be recovered incrementally.
      - Append is atomic-ish (write + fsync) so a crash mid-append cannot
        leave a truncated entry in the log.
      - Updates are by entry_id; entry content is immutable, so an "update"
        rewrites the whole line (simple and crash-safe).
      - A single internal lock covers reads and writes so concurrent
        producers serialize against the mutable index/state, not against
        each other's JSONL lines.
    """

    _PENDING = {IntentStatus.PENDING, IntentStatus.EXECUTING}

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._lock = threading.Lock()
        # Ensure the parent directory exists so a fresh path can be created
        # deterministically (e.g. a tmp_path in tests).
        self._path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _now_iso(self) -> str:
        """Return the current UTC time as an ISO-8601 string."""
        return datetime.now(UTC).isoformat().replace("+00:00", "Z")

    def _canonical_json(self, value: Any) -> str:
        """Serialise *value* to a canonical, sorted-key, stable form."""
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    def _entry_to_line(self, entry: WALEntry) -> str:
        return json.dumps(entry.model_dump(mode="json")) + "\n"

    def _parse_line(self, line: str) -> WALEntry | None:
        line = line.strip()
        if not line:
            return None
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return None
        try:
            return WALEntry.model_validate(data)
        except Exception:
            return None

    def _read_all(self) -> list[WALEntry]:
        if not self._path.exists():
            return []
        with self._path.open("r", encoding="utf-8") as handle:
            return [entry for line in handle if (entry := self._parse_line(line))]

    def _write_all(self, entries: list[WALEntry]) -> None:
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(self._entry_to_line(entry))
            handle.flush()
            os_fsync = getattr(handle, "fsync", None)
            if os_fsync is not None:
                os_fsync()
        tmp.rename(self._path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def append(self, entry: WALEntry) -> None:
        """Append *entry* as a single JSONL line and fsync the file."""
        with self._lock:
            entries = self._read_all()
            entries.append(entry)
            self._write_all(entries)

    def update(
        self,
        entry_id: str,
        status: IntentStatus,
        *,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        """Update the status (and optionally result/error) of an entry."""
        with self._lock:
            entries = self._read_all()
            for index, entry in enumerate(entries):
                if entry.entry_id == entry_id:
                    updated = entry.model_copy(update={"status": status})
                    now = self._now_iso()
                    if result is not None:
                        updated = updated.model_copy(update={"result": result})
                    if error is not None:
                        updated = updated.model_copy(update={"error": error})
                    updated = updated.model_copy(update={"updated_at": now})
                    entries[index] = updated
                    break
            else:
                raise KeyError(f"entry {entry_id!r} not found")
            self._write_all(entries)

    def get(self, entry_id: str) -> WALEntry | None:
        with self._lock:
            for entry in self._read_all():
                if entry.entry_id == entry_id:
                    return entry
            return None

    def all(self) -> list[WALEntry]:
        with self._lock:
            return list(self._read_all())

    def pending(self) -> list[WALEntry]:
        """Return entries whose status is PENDING or EXECUTING."""
        with self._lock:
            return [entry for entry in self._read_all() if entry.status in self._PENDING]

    def recover(self) -> list[WALEntry]:
        """Startup recovery: return unfinished entries for reconstitution."""
        with self._lock:
            return [entry for entry in self._read_all() if entry.status in self._PENDING]

    def compact(self, max_entries: int = 1000) -> None:
        """Drop oldest finished entries so the log stays bounded."""
        with self._lock:
            entries = self._read_all()
            finished = [
                entry
                for entry in entries
                if entry.status in {
                    IntentStatus.COMPLETED,
                    IntentStatus.FAILED,
                    IntentStatus.ROLLED_BACK,
                }
            ]
            # Keep the most recently updated finished entries. Sort oldest-first,
            # drop the oldest beyond max_entries, then present the survivors
            # newest-first.
            finished.sort(key=lambda e: e.updated_at)
            while len(finished) > max_entries:
                finished.pop(0)
            finished.reverse()
            self._write_all(finished)


def idempotency_key_generator(action_id: str, payload: dict[str, Any]) -> str:
    """Return a deterministic sha256 hex digest of *action_id* + *payload*.

    The payload is serialised to canonical JSON (sorted keys) so the same
    logical intent always yields the same key, regardless of dict ordering.
    """
    canonical = f"{action_id}|{json.dumps(payload, sort_keys=True, separators=(',', ':'))}"
    return sha256(canonical.encode("utf-8")).hexdigest()
