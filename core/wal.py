"""Write-Ahead Log (WAL) for the cognitive loop.

Invariants:
  I-008  Provenance (immutable entries once written)
  I-011  Resource boundedness (payload size limits + automatic compact)
"""

from __future__ import annotations

import json
import os
import threading
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

MAX_INTENT_BYTES = 64_000
MAX_RESULT_BYTES = 64_000
MAX_ERROR_CHARS = 2_000
MAX_ENTRIES_DEFAULT = 1_000
TRUNCATION_MARKER = "...[TRUNCATED]"


class IntentStatus(StrEnum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


def _bound_dict(value: dict[str, Any] | None, limit: int) -> dict[str, Any] | None:
    if value is None:
        return None
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    if len(raw.encode("utf-8")) <= limit:
        return value
    keep = max(0, limit - 80)
    truncated = raw[:keep] + TRUNCATION_MARKER
    return {"_truncated": True, "_raw": truncated}


def _bound_error(value: str | None) -> str | None:
    if value is None:
        return None
    if len(value) <= MAX_ERROR_CHARS:
        return value
    keep = max(0, MAX_ERROR_CHARS - len(TRUNCATION_MARKER))
    return value[:keep] + TRUNCATION_MARKER


class WALEntry(BaseModel):
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

    @field_validator("intent")
    @classmethod
    def _bound_intent(cls, v: dict[str, Any]) -> dict[str, Any]:
        bounded = _bound_dict(v, MAX_INTENT_BYTES)
        return bounded if bounded is not None else {}

    @field_validator("result")
    @classmethod
    def _bound_result(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        return _bound_dict(v, MAX_RESULT_BYTES)

    @field_validator("error")
    @classmethod
    def _bound_err(cls, v: str | None) -> str | None:
        return _bound_error(v)

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
    _PENDING = {IntentStatus.PENDING, IntentStatus.EXECUTING}
    _FINISHED = {
        IntentStatus.COMPLETED,
        IntentStatus.FAILED,
        IntentStatus.ROLLED_BACK,
    }

    def __init__(
        self,
        path: str | Path,
        *,
        max_entries: int = MAX_ENTRIES_DEFAULT,
        auto_compact: bool = True,
    ) -> None:
        self._path = Path(path)
        self._lock = threading.Lock()
        self._max_entries = max(1, max_entries)
        self._auto_compact = auto_compact
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _now_iso(self) -> str:
        return datetime.now(UTC).isoformat().replace("+00:00", "Z")

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
            try:
                os.fsync(handle.fileno())
            except (OSError, AttributeError):
                pass
        tmp.replace(self._path)
        try:
            dir_fd = os.open(str(self._path.parent), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except (OSError, AttributeError):
            pass

    def append(self, entry: WALEntry) -> None:
        with self._lock:
            entries = self._read_all()
            entries.append(entry)
            if self._auto_compact and len(entries) > self._max_entries * 2:
                entries = self._compact_list(entries)
            self._write_all(entries)

    def update(
        self,
        entry_id: str,
        status: IntentStatus,
        *,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        with self._lock:
            entries = self._read_all()
            for index, entry in enumerate(entries):
                if entry.entry_id == entry_id:
                    now = self._now_iso()
                    payload: dict[str, Any] = {"status": status, "updated_at": now}
                    if result is not None:
                        payload["result"] = _bound_dict(result, MAX_RESULT_BYTES)
                    if error is not None:
                        payload["error"] = _bound_error(error)
                    entries[index] = entry.model_copy(update=payload)
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
        with self._lock:
            return [e for e in self._read_all() if e.status in self._PENDING]

    def recover(self) -> list[WALEntry]:
        return self.pending()

    def _compact_list(self, entries: list[WALEntry]) -> list[WALEntry]:
        pending = [e for e in entries if e.status in self._PENDING]
        finished = [e for e in entries if e.status in self._FINISHED]
        finished.sort(key=lambda e: e.updated_at)
        keep = max(0, self._max_entries - len(pending))
        finished = finished[-keep:] if keep else []
        finished.reverse()
        return pending + finished

    def compact(self, max_entries: int | None = None) -> None:
        limit = max_entries if max_entries is not None else self._max_entries
        with self._lock:
            old = self._max_entries
            self._max_entries = max(1, limit)
            try:
                entries = self._compact_list(self._read_all())
                self._write_all(entries)
            finally:
                self._max_entries = old


def idempotency_key_generator(action_id: str, payload: dict[str, Any]) -> str:
    canonical = (
        f"{action_id}|{json.dumps(payload, sort_keys=True, separators=(',', ':'), default=str)}"
    )
    return sha256(canonical.encode("utf-8")).hexdigest()
