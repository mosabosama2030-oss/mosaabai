"""Core cognitive loop for MosaabAI v0.2.

Implements the sovereign cognitive cycle with real (simple) stage logic:
  Understand -> Model -> Plan -> Execute -> Observe -> Evaluate
  -> Replan -> Verify -> Learn -> Answer

Stages are injectable. The loop owns orchestration and state.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol

from cognition.strategies.selector import Strategy, StrategySelector
from memory.working import WorkingMemory


class LoopStage(StrEnum):
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
    description: str
    goal: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StageOutcome:
    stage: LoopStage
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    notes: str = ""


@dataclass
class TaskResult:
    task: Task
    success: bool
    answer: str | None = None
    stages: list[LoopStage] = field(default_factory=list)
    stage_outcomes: list[StageOutcome] = field(default_factory=list)
    error: str | None = None
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None


class StageHandler(Protocol):
    async def __call__(
        self,
        stage: LoopStage,
        task: Task,
        memory: WorkingMemory,
        result: TaskResult,
    ) -> StageOutcome: ...


class CognitiveLoop:
    """Sovereign cognitive loop with injectable stages and working memory."""

    def __init__(
        self,
        *,
        strategy_selector: StrategySelector | None = None,
        stage_handlers: dict[LoopStage, StageHandler] | None = None,
    ) -> None:
        self._stages = list(LoopStage)
        self._selector = strategy_selector or StrategySelector()
        self._handlers = stage_handlers or {}
        self._default = _DefaultStages(self._selector)

    async def run(self, task: str | Task) -> TaskResult:
        if isinstance(task, str):
            task = Task(description=task)

        result = TaskResult(task=task, success=False)
        memory = WorkingMemory()
        memory.set("task", task.description)
        if task.goal:
            memory.set("goal", task.goal)

        for stage in self._stages:
            result.stages.append(stage)
            handler = self._handlers.get(stage) or self._default.handler_for(stage)
            try:
                outcome = await handler(stage, task, memory, result)
                result.stage_outcomes.append(outcome)
                if not outcome.success and stage not in {
                    LoopStage.REPLAN,
                    LoopStage.EVALUATE,
                }:
                    if stage in {LoopStage.EXECUTE, LoopStage.VERIFY}:
                        result.error = outcome.notes or f"{stage.value} failed"
                        break
            except Exception as exc:  # noqa: BLE001
                result.error = f"{stage.value}: {exc}"
                result.stage_outcomes.append(
                    StageOutcome(stage=stage, success=False, notes=str(exc))
                )
                break

        if result.answer is None:
            result.answer = memory.get("answer")
        if result.answer and result.error is None:
            result.success = True

        result.finished_at = datetime.now(UTC)
        return result


class _DefaultStages:
    """Built-in simple stage implementations for Phase 0.2."""

    def __init__(self, selector: StrategySelector) -> None:
        self._selector = selector

    def handler_for(self, stage: LoopStage) -> StageHandler:
        mapping: dict[LoopStage, StageHandler] = {
            LoopStage.UNDERSTAND: self._understand,
            LoopStage.MODEL: self._model,
            LoopStage.PLAN: self._plan,
            LoopStage.EXECUTE: self._execute,
            LoopStage.OBSERVE: self._observe,
            LoopStage.EVALUATE: self._evaluate,
            LoopStage.REPLAN: self._replan,
            LoopStage.VERIFY: self._verify,
            LoopStage.LEARN: self._learn,
            LoopStage.ANSWER: self._answer,
        }
        return mapping[stage]

    async def _understand(
        self, stage: LoopStage, task: Task, memory: WorkingMemory, result: TaskResult
    ) -> StageOutcome:
        text = task.description.strip()
        tokens = text.split()
        memory.set("understood", {"raw": text, "token_count": len(tokens)})
        return StageOutcome(
            stage=stage,
            success=bool(text),
            data={"token_count": len(tokens)},
            notes="parsed task text" if text else "empty task",
        )

    async def _model(
        self, stage: LoopStage, task: Task, memory: WorkingMemory, result: TaskResult
    ) -> StageOutcome:
        goal = task.goal or task.description
        model = {"goal": goal, "constraints": [], "assumptions": []}
        memory.set("model", model)
        return StageOutcome(stage=stage, success=True, data=model, notes="goal captured")

    async def _plan(
        self, stage: LoopStage, task: Task, memory: WorkingMemory, result: TaskResult
    ) -> StageOutcome:
        strategies = self._selector.select(task.description)
        plan = {
            "strategies": [s.value for s in strategies],
            "steps": [
                {"id": 1, "action": "analyze", "strategy": strategies[0].value},
                {"id": 2, "action": "respond", "strategy": strategies[-1].value},
            ],
        }
        memory.set("plan", plan)
        memory.set("strategies", strategies)
        return StageOutcome(
            stage=stage,
            success=True,
            data={"strategies": plan["strategies"]},
            notes=f"selected {len(strategies)} strategies",
        )

    async def _execute(
        self, stage: LoopStage, task: Task, memory: WorkingMemory, result: TaskResult
    ) -> StageOutcome:
        strategies = memory.get("strategies") or []
        draft = (
            f"Processed: {task.description}\n"
            f"Strategies: {', '.join(s.value if hasattr(s, 'value') else str(s) for s in strategies)}"
        )
        memory.set("execution_output", draft)
        return StageOutcome(
            stage=stage,
            success=True,
            data={"output_len": len(draft)},
            notes="draft produced",
        )

    async def _observe(
        self, stage: LoopStage, task: Task, memory: WorkingMemory, result: TaskResult
    ) -> StageOutcome:
        output = memory.get("execution_output") or ""
        observation = {"has_output": bool(output), "length": len(str(output))}
        memory.set("observation", observation)
        return StageOutcome(stage=stage, success=True, data=observation)

    async def _evaluate(
        self, stage: LoopStage, task: Task, memory: WorkingMemory, result: TaskResult
    ) -> StageOutcome:
        obs = memory.get("observation") or {}
        ok_flag = bool(obs.get("has_output"))
        memory.set("evaluation", {"ok": ok_flag, "score": 1.0 if ok_flag else 0.0})
        return StageOutcome(stage=stage, success=ok_flag, data={"ok": ok_flag})

    async def _replan(
        self, stage: LoopStage, task: Task, memory: WorkingMemory, result: TaskResult
    ) -> StageOutcome:
        evaluation = memory.get("evaluation") or {}
        if evaluation.get("ok"):
            return StageOutcome(stage=stage, success=True, notes="no replan needed")
        memory.set("plan", {"strategies": [Strategy.EXPLORATORY.value], "steps": []})
        return StageOutcome(stage=stage, success=True, notes="fallback to exploratory")

    async def _verify(
        self, stage: LoopStage, task: Task, memory: WorkingMemory, result: TaskResult
    ) -> StageOutcome:
        output = memory.get("execution_output")
        valid = output is not None and len(str(output)) > 0
        memory.set("verified", valid)
        return StageOutcome(
            stage=stage,
            success=valid,
            notes="output present" if valid else "missing output",
        )

    async def _learn(
        self, stage: LoopStage, task: Task, memory: WorkingMemory, result: TaskResult
    ) -> StageOutcome:
        memory.set(
            "lesson",
            {
                "task": task.description[:200],
                "success": bool(memory.get("verified")),
            },
        )
        return StageOutcome(stage=stage, success=True, notes="lesson recorded")

    async def _answer(
        self, stage: LoopStage, task: Task, memory: WorkingMemory, result: TaskResult
    ) -> StageOutcome:
        output = memory.get("execution_output") or f"[no output] {task.description}"
        result.answer = str(output)
        memory.set("answer", result.answer)
        return StageOutcome(stage=stage, success=True, notes="answer set")
