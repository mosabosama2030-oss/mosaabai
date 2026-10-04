"""EO-004 Integration Suture Test.

Bridges P0.5.0 primitives: WAL + MosaabError + ToolEnvironment.
Reuses BASE_TOOLS/BASE_CAPABILITIES from the already-verified tool test.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from core.errors import ErrorCode, MosaabError
from core.wal import (
    IntentStatus,
    WALEntry,
    WriteAheadLog,
    idempotency_key_generator,
)
from tests.test_tool_environment import BASE_CAPABILITIES, BASE_TOOLS
from tools.tool_environment import CapabilityViolationError, create_root


def test_suture_capability_violation_to_wal() -> None:
    parent = create_root(
        "parent-env",
        list(BASE_TOOLS),
        set(BASE_CAPABILITIES),
    )
    child_env = "child-env"
    escalated = set(BASE_CAPABILITIES) | {"cap.unauthorized"}

    with pytest.raises(CapabilityViolationError):
        parent.spawn_child(child_env, BASE_TOOLS, escalated)

    err = MosaabError(
        code=ErrorCode.provenance_failure,
        message="child capability escalation blocked",
        trace_id="trace-eo-004",
        context={"parent_id": "parent-env", "child_id": child_env},
    )
    payload = err.to_dict()

    with tempfile.TemporaryDirectory() as tmp:
        wal = WriteAheadLog(Path(tmp) / "test.wal")
        entry = WALEntry(
            entry_id="entry-eo-004",
            action_id="action-eo-004",
            idempotency_key=idempotency_key_generator("action-eo-004", payload),
            intent=payload,
            status=IntentStatus.EXECUTING,
            created_at="2026-10-04T20:00:00Z",
            updated_at="2026-10-04T20:00:00Z",
        )
        wal.append(entry)

        recovered = wal.get("entry-eo-004")
        assert recovered is not None
        assert recovered.intent["trace_id"] == "trace-eo-004"
        assert recovered.intent["code"] == "provenance_failure"
        assert len(wal.pending()) == 1


def test_suture_error_with_cause_is_wal_safe() -> None:
    err = MosaabError(
        code=ErrorCode.tool_failure,
        message="Tool crashed",
        cause=ValueError("underlying issue"),
        trace_id="trace-cause",
    )
    serialized = json.dumps(err.to_dict(), sort_keys=True)
    assert "tool_failure" in serialized
    assert "trace-cause" in serialized
    assert "ValueError" in serialized
