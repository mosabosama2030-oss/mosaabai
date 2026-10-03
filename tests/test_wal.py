"""Tests for the Write-Ahead Log (WAL) — Phase P0.5.0-A0.1."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.wal import (
    IntentStatus,
    WriteAheadLog,
    idempotency_key_generator,
)
from core.wal import WALEntry as Entry

NOW = datetime.now(UTC).isoformat().replace("+00:00", "Z")
EYE, A_ID = "e1", "a1"


def _entry(status: str = "pending", **overrides) -> Entry:
    """Build a WALEntry with a default base and allow overrides.

    The explicit 'status' parameter is applied on top of the default
    base, then any caller-provided overrides, then the status is
    normalised to the IntentStatus enum before construction.
    """
    base = {
        "entry_id": EYE,
        "action_id": A_ID,
        "idempotency_key": "key-1",
        "intent": {"task": "do something"},
        "status": IntentStatus.PENDING,
        "created_at": NOW,
        "updated_at": NOW,
    }
    # Apply the explicit 'status' parameter (binds to the parameter,
    # not **overrides, so it is not automatically applied).
    base["status"] = status
    # Apply any caller-provided overrides.
    base.update(overrides)
    # Normalise the status field through the enum so the model validates.
    if "status" in base:
        base["status"] = IntentStatus(base["status"])
    return Entry.create(**base)


# ---------------------------------------------------------------------------
# 1. append / read
# ---------------------------------------------------------------------------
def test_append_and_read_single(tmp_path: Path) -> None:
    wal = WriteAheadLog(tmp_path / "wal.jsonl")
    entry = _entry()
    wal.append(entry)

    assert wal.get(EYE) == entry
    assert wal.all() == [entry]
    assert wal.pending() == [entry]


def test_append_multiple(tmp_path: Path) -> None:
    wal = WriteAheadLog(tmp_path / "wal.jsonl")
    e1 = _entry(entry_id="e1")
    e2 = _entry(entry_id="e2")
    e3 = _entry(entry_id="e3")
    wal.append(e1)
    wal.append(e2)
    wal.append(e3)

    assert wal.all() == [e1, e2, e3]
    assert wal.get("e2") == e2
    assert wal.pending() == [e1, e2, e3]


def test_update_status(tmp_path: Path) -> None:
    wal = WriteAheadLog(tmp_path / "wal.jsonl")
    entry = _entry()
    wal.append(entry)

    wal.update(EYE, IntentStatus.EXECUTING)
    read_back = wal.get(EYE)
    assert read_back is not None
    assert read_back.status == IntentStatus.EXECUTING
    assert read_back.result is None
    assert read_back.error is None
    assert "updated_at" in read_back.model_dump()


def test_update_with_error(tmp_path: Path) -> None:
    wal = WriteAheadLog(tmp_path / "wal.jsonl")
    entry = _entry()
    wal.append(entry)

    wal.update(EYE, IntentStatus.FAILED, error="boom")
    read_back = wal.get(EYE)

    assert read_back is not None
    assert read_back.status == IntentStatus.FAILED
    assert read_back.error == "boom"
    assert read_back.result is None


def test_pending_returns_only_unfinished(tmp_path: Path) -> None:
    wal = WriteAheadLog(tmp_path / "wal.jsonl")
    wal.append(_entry(entry_id="1", status="pending"))
    wal.append(_entry(entry_id="2", status="executing"))
    wal.append(_entry(entry_id="3", status="completed"))
    wal.append(_entry(entry_id="4", status="failed"))
    wal.append(_entry(entry_id="5", status="rolled_back"))

    assert [e.entry_id for e in wal.pending()] == ["1", "2"]


def test_recover_returns_unfinished(tmp_path: Path) -> None:
    wal = WriteAheadLog(tmp_path / "wal.jsonl")
    wal.append(_entry(entry_id="1", status="pending"))
    wal.append(_entry(entry_id="2", status="executing"))
    wal.append(_entry(entry_id="3", status="completed"))

    assert [e.entry_id for e in wal.recover()] == ["1", "2"]


def test_persistence_across_instances(tmp_path: Path) -> None:
    path = tmp_path / "shared.jsonl"
    first = WriteAheadLog(path)
    first.append(_entry(entry_id="shared-1"))
    first.append(_entry(entry_id="shared-2"))

    second = WriteAheadLog(path)
    assert second.all() == first.all()
    assert second.get("shared-1") is not None
    assert second.get("shared-2") is not None
    assert second.pending() == first.pending()


def test_idempotency_key_determinism() -> None:
    payload_a = {"answer": 42, "verbose": {"nested": True}, "x": 1}
    payload_b = {"x": 1, "answer": 42, "verbose": {"nested": True}}

    assert idempotency_key_generator("echo", payload_a) == idempotency_key_generator(
        "echo", payload_b
    )
    assert idempotency_key_generator("echo", payload_a) == idempotency_key_generator(
        "echo", payload_a
    )


def _canonical_json(value: Any) -> str:
    """Serialise *value* to a canonical, sorted-key, stable form."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def test_idempotency_key_is_sha256() -> None:
    payload = {"forced": "structure"}
    key = idempotency_key_generator("render", payload)

    assert len(key) == 64
    assert all(c in "0123456789abcdef" for c in key)
    assert key == __import__("hashlib").sha256(
        f"render|{_canonical_json(payload)}".encode()
    ).hexdigest()


def test_compact(tmp_path: Path) -> None:
    wal = WriteAheadLog(tmp_path / "wal.jsonl")
    for i in range(5):
        wal.append(
            _entry(
                entry_id=f"e{i}",
                status="completed",
                result={"index": i},
            )
        )

    wal.compact(max_entries=2)

    after = wal.all()
    assert len(after) == 2
    # Compact keeps the most recent (largest updated_at) finished entries.
    assert [e.entry_id for e in after] == ["e4", "e3"]


def test_file_format_is_jsonl(tmp_path: Path) -> None:
    wal = WriteAheadLog(tmp_path / "wal.jsonl")
    wal.append(_entry())
    wal.append(_entry(entry_id="e2", intent={"x": 1}))

    lines = tmp_path.joinpath("wal.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    for line in lines:
        assert line.startswith("{")
        assert line.endswith("}")
        _ = __import__("json").loads(line)  # must be valid, single-line JSON


def test_concurrent_append(tmp_path: Path) -> None:
    wal = WriteAheadLog(tmp_path / "wal.jsonl")
    num_threads = 8
    results: list[str] = []
    lock = threading.Lock()

    def worker() -> None:
        entry = _entry(
            entry_id=f"th-{threading.get_ident()}",
            status="pending",
        )
        wal.append(entry)
        with lock:
            results.append(entry.entry_id)

    threads = [threading.Thread(target=worker) for _ in range(num_threads)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(results) == num_threads
    assert len(wal.all()) == num_threads
