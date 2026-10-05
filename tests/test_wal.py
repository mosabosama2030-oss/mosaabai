"""Tests for the Write-Ahead Log (WAL) — Phase P0.5.0-A0.1 + EO-005 G2."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from core.wal import (
    MAX_ERROR_BYTES,
    MAX_INTENT_BYTES,
    MAX_RESULT_BYTES,
    IntentStatus,
    WriteAheadLog,
    _bound_dict,
    _bound_error,
    idempotency_key_generator,
)
from core.wal import WALEntry as Entry

NOW = datetime.now(UTC).isoformat().replace("+00:00", "Z")
EYE, A_ID = "e1", "a1"


def _entry(status: str = "pending", **overrides) -> Entry:
    base = {
        "entry_id": EYE,
        "action_id": A_ID,
        "idempotency_key": "key-1",
        "intent": {"task": "do something"},
        "status": IntentStatus.PENDING,
        "created_at": NOW,
        "updated_at": NOW,
    }
    base["status"] = status
    base.update(overrides)
    if "status" in base:
        base["status"] = IntentStatus(base["status"])
    return Entry.create(**base)


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
        _ = json.loads(line)


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


def test_wal_uses_os_fsync(tmp_path: Path) -> None:
    wal = WriteAheadLog(tmp_path / "wal.jsonl")
    with patch("core.wal.os.fsync") as mock_fsync:
        wal.append(_entry())
        assert mock_fsync.called
        assert mock_fsync.call_count >= 1


def test_wal_fsyncs_parent_directory(tmp_path: Path) -> None:
    wal = WriteAheadLog(tmp_path / "wal.jsonl")
    calls: list[int] = []

    real_fsync = __import__("os").fsync

    def tracking_fsync(fd: int) -> None:
        calls.append(fd)
        try:
            real_fsync(fd)
        except OSError:
            pass

    with patch("core.wal.os.fsync", side_effect=tracking_fsync):
        wal.append(_entry())

    assert len(calls) >= 2  # file + directory


def test_wal_survives_torn_write(tmp_path: Path) -> None:
    """Simulate crash after partial tmp write: durable file remains previous state."""
    path = tmp_path / "wal.jsonl"
    wal = WriteAheadLog(path)
    wal.append(_entry(entry_id="durable-1"))
    assert len(wal.all()) == 1

    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("{broken", encoding="utf-8")
    recovered = WriteAheadLog(path)
    assert [e.entry_id for e in recovered.all()] == ["durable-1"]


def test_wal_directory_fsync_supported_on_termux(tmp_path: Path) -> None:
    """Preflight: directory fsync either succeeds or logs explicit warning (not silent)."""
    wal = WriteAheadLog(tmp_path / "wal.jsonl")
    call_count = {"n": 0}

    def selective_fsync(fd: int) -> None:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return  # file ok
        raise OSError("dir fsync unsupported")

    with (
        patch("core.wal.os.fsync", side_effect=selective_fsync),
        patch("core.wal.logger.warning") as mock_warn,
    ):
        wal.append(_entry(entry_id="termux-1"))
    assert mock_warn.called
    assert WriteAheadLog(tmp_path / "wal.jsonl").get("termux-1") is not None


def test_wal_fsync_failure_is_not_silent(tmp_path: Path) -> None:
    wal = WriteAheadLog(tmp_path / "wal.jsonl")

    def fail_fsync(fd: int) -> None:
        raise OSError("fsync failed")

    with (
        patch("core.wal.os.fsync", side_effect=fail_fsync),
        pytest.raises(OSError, match="fsync failed"),
    ):
        wal.append(_entry())


def test_wal_intent_truncated_silently() -> None:
    huge = {"blob": "X" * (MAX_INTENT_BYTES + 10_000)}
    entry = Entry.create(
        entry_id="big-intent",
        action_id="a",
        idempotency_key="k",
        intent=huge,
        status=IntentStatus.PENDING,
        created_at=NOW,
        updated_at=NOW,
    )
    assert entry.intent.get("_truncated") is True
    assert entry.intent.get("_original_bytes", 0) > MAX_INTENT_BYTES
    assert "intent" in entry.truncation_flags
    raw = json.dumps(entry.intent)
    assert len(raw.encode("utf-8")) < MAX_INTENT_BYTES


def test_wal_result_truncated_silently() -> None:
    huge = {"blob": "Y" * (MAX_RESULT_BYTES + 10_000)}
    entry = Entry.create(
        entry_id="big-result",
        action_id="a",
        idempotency_key="k",
        intent={"ok": True},
        status=IntentStatus.COMPLETED,
        created_at=NOW,
        updated_at=NOW,
        result=huge,
    )
    assert entry.result is not None
    assert entry.result.get("_truncated") is True
    assert "result" in entry.truncation_flags


def test_wal_error_truncated_silently() -> None:
    huge_err = "E" * (MAX_ERROR_BYTES + 5000)
    entry = Entry.create(
        entry_id="big-err",
        action_id="a",
        idempotency_key="k",
        intent={"ok": True},
        status=IntentStatus.FAILED,
        created_at=NOW,
        updated_at=NOW,
        error=huge_err,
    )
    assert entry.error is not None
    assert len(entry.error.encode("utf-8")) <= MAX_ERROR_BYTES
    assert "error" in entry.truncation_flags


def test_wal_truncation_flags_recorded() -> None:
    entry = Entry.create(
        entry_id="flags",
        action_id="a",
        idempotency_key="k",
        intent={"blob": "I" * (MAX_INTENT_BYTES + 1000)},
        status=IntentStatus.FAILED,
        created_at=NOW,
        updated_at=NOW,
        result={"blob": "R" * (MAX_RESULT_BYTES + 1000)},
        error="E" * (MAX_ERROR_BYTES + 1000),
    )
    assert set(entry.truncation_flags) >= {"intent", "result", "error"}


def test_wal_never_raises_during_bounding() -> None:
    adversarial = [
        None,
        "string",
        123,
        object(),
        {"ok": "v"},
        {"nested": {"x": list(range(100))}},
    ]
    for item in adversarial:
        try:
            _bound_dict(item if isinstance(item, dict) else {"_v": str(item)}, 100)
            _bound_error(str(item) if item is not None else None)
        except BaseException as exc:
            raise AssertionError(f"bounding raised on {type(item)}: {exc}") from exc


def test_wal_existing_tests_still_pass() -> None:
    """Semantic smoke: small payloads round-trip unchanged."""
    entry = Entry.create(
        entry_id="smoke",
        action_id="a",
        idempotency_key="k",
        intent={"task": "small"},
        status=IntentStatus.PENDING,
        created_at=NOW,
        updated_at=NOW,
    )
    assert entry.intent == {"task": "small"}
    assert entry.truncation_flags == ()


def test_wal_compact_still_works(tmp_path: Path) -> None:
    wal = WriteAheadLog(tmp_path / "wal.jsonl")
    for i in range(5):
        wal.append(_entry(entry_id=f"c{i}", status="completed", result={"i": i}))
    wal.compact(max_entries=2)
    assert len(wal.all()) == 2
