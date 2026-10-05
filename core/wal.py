"""Write-Ahead Log (WAL) for the cognitive loop — Phase P0.5.0-A0.1.

EO-005 G2: durability via os.fsync + directory fsync; payload bounds (I-011).
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

MAX_INTENT_BYTES = 65_536
MAX_RESULT_BYTES = 65_536
MAX_ERROR_BYTES = 4_096
PREVIEW_CHARS = 500
TRUNCATION_MARKER = "...[TRUNCATED]"


class IntentStatus(StrEnum):
    """Lifecycle status of a recorded intent in the WAL."""

    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


def _canonical_json_str(value: Any) -> str:
    """Serialise *value* to canonical JSON. Never raises for common types."""
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    except (TypeError, ValueError):
        return json.dumps({"_unserializable": type(value).__name__}, sort_keys=True)


def _bound_dict(value: dict[str, Any] | None, limit: int) -> tuple[dict[str, Any] | None, bool]:
    """Bound a dict payload by canonical JSON size. Silent truncation. Never raises."""
    if value is None:
        return None, False
    try:
        raw = _canonical_json_str(value)
        nbytes = len(raw.encode("utf-8"))
        if nbytes <= limit:
            return value, False
        preview = raw[:PREVIEW_CHARS]
        return (
            {
                "_truncated": True,
                "_original_bytes": nbytes,
                "_preview": preview,
            },
            True,
        )
    except BaseException:  # noqa: BLE001 — never-raise bounding
        return {"_truncated": True, "_original_bytes": -1, "_preview": ""}, True


def _bound_error(value: str | None) -> tuple[str | None, bool]:
    """Bound an error string by UTF-8 byte length. Silent truncation. Never raises."""
    if value is None:
        return None, False
    try:
        if not isinstance(value, str):
            value = str(value)
        encoded = value.encode("utf-8")
        if len(encoded) <= MAX_ERROR_BYTES:
            return value, False
        cut = encoded[: max(0, MAX_ERROR_BYTES - len(TRUNCATION_MARKER.encode("utf-8")))]
        preview = cut.decode("utf-8", errors="ignore") + TRUNCATION_MARKER
        return preview, True
    except BaseException:  # noqa: BLE001 — never-raise bounding
        return TRUNCATION_MARKER, True


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
    truncation_flags: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("intent", mode="before")
    @classmethod
    def _validate_intent(cls, v: Any) -> dict[str, Any]:
        if not isinstance(v, dict):
            try:
                v = dict(v)
            except BaseException:  # noqa: BLE001
                v = {"_malformed": str(type(v))}
        bounded, _ = _bound_dict(v, MAX_INTENT_BYTES)
        return bounded if bounded is not None else {}

    @field_validator("result", mode="before")
    @classmethod
    def _validate_result(cls, v: Any) -> dict[str, Any] | None:
        if v is None:
            return None
        if not isinstance(v, dict):
            try:
                v = dict(v)
            except BaseException:  # noqa: BLE001
                v = {"_malformed": str(type(v))}
        bounded, _ = _bound_dict(v, MAX_RESULT_BYTES)
        return bounded

    @field_validator("error", mode="before")
    @classmethod
    def _validate_error(cls, v: Any) -> str | None:
        if v is None:
            return None
        bounded, _ = _bound_error(v if isinstance(v, str) else str(v))
        return bounded

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
        """Construct a frozen entry with silent payload bounding."""
        flags: list[str] = []
        bound_intent, intent_trunc = _bound_dict(
            intent if isinstance(intent, dict) else {"_raw": str(intent)},
            MAX_INTENT_BYTES,
        )
        if intent_trunc:
            flags.append("intent")
        bound_result = result
        if result is not None:
            bound_result, result_trunc = _bound_dict(
                result if isinstance(result, dict) else {"_raw": str(result)},
                MAX_RESULT_BYTES,
            )
            if result_trunc:
                flags.append("result")
        bound_error, error_trunc = _bound_error(error)
        if error_trunc:
            flags.append("error")
        return cls(
            entry_id=entry_id,
            action_id=action_id,
            idempotency_key=idempotency_key,
            intent=bound_intent or {},
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            result=bound_result,
            error=bound_error,
            truncation_flags=tuple(flags),
        )


class WriteAheadLog:
    """Thread-safe, JSONL-persistent, log-structured write-ahead log.

    Design:
      - One JSON object per line (JSONL) so entries survive partial writes
        and can be recovered incrementally.
      - Append uses write + os.fsync + directory fsync so a crash mid-append
        cannot leave an unrecoverable truncated log as the durable file.
      - Updates are by entry_id; entry content is immutable, so an "update"
        rewrites the whole file (simple and crash-safe).
      - A single internal lock covers reads and writes.
    """

    _PENDING: ClassVar[set[IntentStatus]] = {IntentStatus.PENDING, IntentStatus.EXECUTING}

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._lock = threading.Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _now_iso(self) -> str:
        return datetime.now(UTC).isoformat().replace("+00:00", "Z")

    def _canonical_json(self, value: Any) -> str:
        return _canonical_json_str(value)

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
        except Exception:  # noqa: BLE001 — corrupt line skip
            return None

    def _read_all(self) -> list[WALEntry]:
        if not self._path.exists():
            return []
        with self._path.open("r", encoding="utf-8") as handle:
            return [entry for line in handle if (entry := self._parse_line(line))]

    def _fsync_file(self, handle: Any) -> None:
        """Force file data to durable storage. Never silent-skip."""
        try:
            os.fsync(handle.fileno())
        except OSError as exc:
            logger.warning("WAL file fsync failed for %s: %s", self._path, exc)
            raise

    def _fsync_directory(self, directory: Path) -> None:
        """Force directory entry (rename) durability. Warn if unsupported."""
        dir_fd: int | None = None
        try:
            dir_fd = os.open(str(directory), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            except OSError as exc:
                logger.warning(
                    "WAL directory fsync unsupported or failed for %s: %s",
                    directory,
                    exc,
                )
        except OSError as exc:
            logger.warning(
                "WAL directory fsync open failed for %s: %s",
                directory,
                exc,
            )
        finally:
            if dir_fd is not None:
                try:
                    os.close(dir_fd)
                except OSError:
                    pass

    def _write_all(self, entries: list[WALEntry]) -> None:
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(self._entry_to_line(entry))
            handle.flush()
            self._fsync_file(handle)
        os.replace(tmp, self._path)
        self._fsync_directory(self._path.parent)

    def append(self, entry: WALEntry) -> None:
        """Append *entry* as a single JSONL line and fsync the file + directory."""
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
                    now = self._now_iso()
                    flags = list(entry.truncation_flags)
                    payload: dict[str, Any] = {"status": status, "updated_at": now}
                    if result is not None:
                        bound_result, trunc = _bound_dict(result, MAX_RESULT_BYTES)
                        payload["result"] = bound_result
                        if trunc and "result" not in flags:
                            flags.append("result")
                    if error is not None:
                        bound_error, trunc = _bound_error(error)
                        payload["error"] = bound_error
                        if trunc and "error" not in flags:
                            flags.append("error")
                    payload["truncation_flags"] = tuple(flags)
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
            return [entry for entry in self._read_all() if entry.status in self._PENDING]

    def recover(self) -> list[WALEntry]:
        with self._lock:
            return [entry for entry in self._read_all() if entry.status in self._PENDING]

    def compact(self, max_entries: int = 1000) -> None:
        """Drop oldest finished entries so the log stays bounded."""
        with self._lock:
            entries = self._read_all()
            finished = [
                entry
                for entry in entries
                if entry.status
                in {
                    IntentStatus.COMPLETED,
                    IntentStatus.FAILED,
                    IntentStatus.ROLLED_BACK,
                }
            ]
            finished.sort(key=lambda e: e.updated_at)
            while len(finished) > max_entries:
                finished.pop(0)
            finished.reverse()
            self._write_all(finished)


def idempotency_key_generator(action_id: str, payload: dict[str, Any]) -> str:
    """Return a deterministic sha256 hex digest of *action_id* + *payload*."""
    canonical = f"{action_id}|{json.dumps(payload, sort_keys=True, separators=(',', ':'))}"
    return sha256(canonical.encode("utf-8")).hexdigest()
