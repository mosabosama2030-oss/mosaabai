"""G5 + F-086/F-087 integration tests."""

from __future__ import annotations

import asyncio

import pytest

from core.cognitive_loop import CognitiveLoop, LoopStage, Task
from core.security import SecurityDowngradeError
from tools.spawn import spawn_child
from tools.trusted_registry import TrustedToolRegistry


def _add(a, b):
    return a + b


def test_loop_still_runs_stages() -> None:
    loop = CognitiveLoop()
    result = asyncio.run(loop.run("hello"))
    assert LoopStage.ANSWER in result.stages
    assert result.success is True


def test_security_violation_bypasses_generic_handler() -> None:
    reg = TrustedToolRegistry()
    with pytest.raises(SecurityDowngradeError):
        spawn_child(None, registry=reg)  # type: ignore[arg-type]


def test_operational_tool_success_via_spawn() -> None:
    reg = TrustedToolRegistry()
    tid = reg.register(name="add", version="1.0.0", description="add", parameters={}, fn=_add)
    assert spawn_child(tid, registry=reg, args=(2, 2)) == 4


def test_loop_does_not_swallow_security_errors() -> None:
    loop = CognitiveLoop()

    async def boom(stage, task, result):  # noqa: ANN001
        raise SecurityDowngradeError("injected")

    loop._run_stage = boom  # type: ignore[method-assign]
    with pytest.raises(SecurityDowngradeError):
        asyncio.run(loop.run("x"))


def test_full_10_stage_loop_with_tool_execution(tmp_path) -> None:  # noqa: ANN001
    from core.wal import IntentStatus, WriteAheadLog

    reg = TrustedToolRegistry()
    tid = reg.register(name="add", version="1.0.0", description="add", parameters={}, fn=_add)
    wal = WriteAheadLog(tmp_path / "loop.wal")
    loop = CognitiveLoop(registry=reg, wal=wal)
    task = Task(description="sum", tool_id=tid, tool_args=(2, 5))
    result = asyncio.run(loop.run(task))
    assert result.success is True
    assert result.tool_output == 7
    assert result.answer == "7"
    assert len(result.stages) == 10
    entries = [e for e in wal._read_all() if e.status == IntentStatus.COMPLETED]
    assert len(entries) >= 1


def test_wal_critical_entry_present_on_security_failure(tmp_path) -> None:  # noqa: ANN001
    """F-086: security failure writes WAL CRITICAL entry then re-raises."""
    from core.wal import IntentStatus, WriteAheadLog

    reg = TrustedToolRegistry()
    wal = WriteAheadLog(tmp_path / "crit.wal")
    loop = CognitiveLoop(registry=reg, wal=wal)
    task = Task(description="x", tool_id="00" * 32, tool_args=())
    with pytest.raises(SecurityDowngradeError):
        asyncio.run(loop.run(task))
    entries = wal._read_all()
    assert any(
        e.status == IntentStatus.FAILED and "CRITICAL" in e.action_id for e in entries
    ) or any(e.error == "security_violation" for e in entries)
