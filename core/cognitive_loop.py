"""Core cognitive loop for MosaabAI.

F-086: explicit exception classification; operational → continue; security → hard raise;
WAL CRITICAL must not silently fail.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from core.security_exceptions import (
    ASTSecurityViolationError,
    RegistryImmutableError,
    SecurityDowngradeError,
    StatefulToolError,
    ToolExecutionError,
)

_SECURITY_ERRORS = (
    SecurityDowngradeError,
    ASTSecurityViolationError,
    StatefulToolError,
    RegistryImmutableError,
)
_OPERATIONAL_ERRORS = (ToolExecutionError, TimeoutError, OSError)


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
    tool_id: str | None = None
    tool_args: tuple[Any, ...] = ()
    tool_kwargs: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    task: Task
    success: bool
    answer: str | None = None
    stages: list[LoopStage] = field(default_factory=list)
    error: str | None = None
    tool_output: Any = None
    operational_errors: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None


class CognitiveLoop:
    def __init__(
        self,
        *,
        registry: Any | None = None,
        wal: Any | None = None,
        wal_path: str | Path | None = None,
    ) -> None:
        self._stages = list(LoopStage)
        self._registry = registry
        self._wal = wal
        if self._wal is None and wal_path is not None:
            from core.wal import WriteAheadLog

            self._wal = WriteAheadLog(wal_path)

    async def run(self, task: str | Task) -> TaskResult:
        if isinstance(task, str):
            task = Task(description=task)

        result = TaskResult(task=task, success=False)

        for stage in self._stages:
            result.stages.append(stage)
            try:
                await self._run_stage(stage, task, result)
            except _SECURITY_ERRORS:
                self._wal_critical(task, stage, "security_violation")
                raise
            except _OPERATIONAL_ERRORS as exc:
                msg = f"{stage.value}: {exc}"
                result.operational_errors.append(msg)
                result.error = msg
                continue
            except Exception as exc:
                if isinstance(exc, _SECURITY_ERRORS):
                    self._wal_critical(task, stage, "security_violation")
                    raise
                msg = f"{stage.value}: {exc}"
                result.operational_errors.append(msg)
                result.error = msg
                continue

        result.finished_at = datetime.now(UTC)
        if result.answer is not None and (
            not result.operational_errors or result.tool_output is not None
        ):
            result.success = True
        return result

    async def _run_stage(self, stage: LoopStage, task: Task, result: TaskResult) -> None:
        if stage is LoopStage.EXECUTE and task.tool_id and self._registry is not None:
            await self._execute_tool(task, result)
            return
        if stage is LoopStage.ANSWER:
            if result.tool_output is not None:
                result.answer = str(result.tool_output)
            else:
                result.answer = f"[stub] task received: {task.description}"

    async def _execute_tool(self, task: Task, result: TaskResult) -> None:
        from tools.spawn import spawn_child

        entry_id = str(uuid.uuid4())
        if self._wal is not None:
            from core.wal import IntentStatus, WALEntry

            now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
            entry = WALEntry.create(
                entry_id=entry_id,
                action_id=f"tool:{task.tool_id}",
                idempotency_key=entry_id,
                intent={"tool_id": task.tool_id, "description": task.description},
                status=IntentStatus.PENDING,
                created_at=now,
                updated_at=now,
            )
            self._wal.append(entry)
            self._wal.update(entry_id, IntentStatus.EXECUTING)

        try:
            output = spawn_child(
                task.tool_id,  # type: ignore[arg-type]
                registry=self._registry,
                args=task.tool_args,
                kwargs=task.tool_kwargs or {},
            )
            result.tool_output = output
            if self._wal is not None:
                from core.wal import IntentStatus

                self._wal.update(
                    entry_id, IntentStatus.COMPLETED, result={"output": str(output)}
                )
        except _SECURITY_ERRORS:
            if self._wal is not None:
                from core.wal import IntentStatus

                self._wal.update(entry_id, IntentStatus.FAILED, error="security_violation")
            raise
        except Exception as exc:
            if self._wal is not None:
                from core.wal import IntentStatus

                self._wal.update(entry_id, IntentStatus.FAILED, error=str(exc))
            if isinstance(exc, _OPERATIONAL_ERRORS):
                raise
            raise ToolExecutionError(str(exc)) from exc

    def _wal_critical(self, task: Task, stage: LoopStage, reason: str) -> None:
        if self._wal is None:
            return
        from core.wal import IntentStatus, WALEntry

        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        eid = str(uuid.uuid4())
        entry = WALEntry.create(
            entry_id=eid,
            action_id=f"CRITICAL:{stage.value}",
            idempotency_key=eid,
            intent={"reason": reason, "task": task.description},
            status=IntentStatus.FAILED,
            created_at=now,
            updated_at=now,
            error=reason,
        )
        try:
            self._wal.append(entry)
        except Exception as wal_exc:
            raise RuntimeError(
                f"WAL CRITICAL append failed during security halt: {wal_exc}"
            ) from wal_exc
