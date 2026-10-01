"""Tests for the core cognitive loop."""

from __future__ import annotations

import pytest

from core.cognitive_loop import CognitiveLoop, LoopStage, Task


@pytest.mark.asyncio
async def test_loop_runs_all_stages() -> None:
    loop = CognitiveLoop()
    result = await loop.run("test task")
    assert result.stages == list(LoopStage)
    assert result.success is True


@pytest.mark.asyncio
async def test_loop_produces_answer() -> None:
    loop = CognitiveLoop()
    result = await loop.run(Task(description="hello"))
    assert result.answer is not None
    assert "hello" in result.answer


@pytest.mark.asyncio
async def test_loop_accepts_string_or_task() -> None:
    loop = CognitiveLoop()
    r1 = await loop.run("task as string")
    r2 = await loop.run(Task(description="task as object"))
    assert r1.task.description == "task as string"
    assert r2.task.description == "task as object"
