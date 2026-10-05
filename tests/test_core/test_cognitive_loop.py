"""Tests for the core cognitive loop v0.2."""

from __future__ import annotations

import asyncio

from core.cognitive_loop import CognitiveLoop, LoopStage, Task


def test_loop_runs_all_stages() -> None:
    loop = CognitiveLoop()
    result = asyncio.run(loop.run("test task"))
    assert result.stages == list(LoopStage)
    assert result.success is True
    assert result.answer is not None


def test_loop_produces_answer() -> None:
    loop = CognitiveLoop()
    result = asyncio.run(loop.run(Task(description="hello world")))
    assert result.answer is not None


def test_loop_accepts_string_or_task() -> None:
    loop = CognitiveLoop()
    r1 = asyncio.run(loop.run("task as string"))
    r2 = asyncio.run(loop.run(Task(description="task as object")))
    assert r1.task.description == "task as string"
    assert r2.task.description == "task as object"


def test_loop_records_stage_outcomes() -> None:
    loop = CognitiveLoop()
    result = asyncio.run(loop.run("plan a trip"))
    assert len(result.stage_outcomes) == len(list(LoopStage))
    assert result.trace_id
    assert result.finished_at is not None


def test_empty_task_still_completes() -> None:
    loop = CognitiveLoop()
    result = asyncio.run(loop.run(""))
    assert result.stages == list(LoopStage)
