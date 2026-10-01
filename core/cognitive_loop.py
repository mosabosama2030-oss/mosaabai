"""Core cognitive loop for MosaabAI.

Implements the sovereign cognitive cycle:
Understand -> Model -> Plan -> Execute -> Observe -> Evaluate -> Replan -> Verify -> Learn -> Answer
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class LoopStage(str, Enum):
    """Stages of the cognitive loop."""

    UNDERSTAND = "understand"
    MODEL = "model"
    PLAN = "plan"
    EXECUTE = "execute"
    OBSERVE = "observe"
    EVALUATE = "evaluate"
    REPLAN = "replan"
    VERIFY = "verify"
    LEARN = "learn"
    ANSWER = "answer"


@dataclass
class Task:
    """A unit of work."""

    description: str
    goal: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    """Outcome of running a task through the cognitive loop."""

    task: Task
    success: bool
    answer: str | None = None
    stages: list[LoopStage] = field(default_factory=list)
    error: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None


class CognitiveLoop:
    """Sovereign cognitive loop.

    Entry point for all task execution. Every stage is replaceable; the
    loop owns orchestration and state, not the individual reasoning engines.
    """

    def __init__(self) -> None:
        self._stages = list(LoopStage)

    async def run(self, task: str | Task) -> TaskResult:
        """Run a task through the full cognitive loop."""
        if isinstance(task, str):
            task = Task(description=task)

        result = TaskResult(task=task, success=False)

        for stage in self._stages:
            result.stages.append(stage)
            try:
                await self._run_stage(stage, task, result)
            except Exception as exc:  # noqa: BLE001
                result.error = f"{stage.value}: {exc}"
                result.success = False
                break

        result.finished_at = datetime.now(timezone.utc)
        return result

    async def _run_stage(self, stage: LoopStage, task: Task, result: TaskResult) -> None:
        """Execute a single stage. Placeholder; each stage is implemented in later phases."""
        if stage is LoopStage.ANSWER:
            result.answer = f"[stub] task received: {task.description}"
            result.success = True
