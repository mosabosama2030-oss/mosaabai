"""Core cognitive loop for MosaabAI.

G5 / F-086: tool-call path via spawn_child; WAL append before execution;
operational errors → continue; security errors → hard re-raise.
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
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None


class CognitiveLoop:
    """Sovereign cognitive loop with optional TrustedToolRegistry + WAL."""

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
            except (
                SecurityDowngradeError,
                ASTSecurityViolationError,
                StatefulToolError,
                RegistryImmutableError,
            ):
                if self._wal is not None:
                    self._wal_critical(task, stage, "security_violation")
                raise
            except (ToolExecutionError, TimeoutError, OSError) as exc:
                result.error = f"{stage.value}: {exc}"
                result.success = False
                break
            except Exception as exc:  # noqa: BLE001
                result.error = f"{stage.value}: {exc}"
                result.success = False
                break

        result.finished_at = datetime.now(UTC)
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
            result.success = True

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
                intent={
                    "tool_id": task.tool_id,
                    "description": task.description,
                },
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
                    entry_id,
                    IntentStatus.COMPLETED,
                    result={"output": str(output)},
                )
        except (
            SecurityDowngradeError,
            ASTSecurityViolationError,
            StatefulToolError,
            RegistryImmutableError,
        ):
            if self._wal is not None:
                from core.wal import IntentStatus

                self._wal.update(entry_id, IntentStatus.FAILED, error="security_violation")
            raise
        except Exception as exc:
            if self._wal is not None:
                from core.wal import IntentStatus

                self._wal.update(entry_id, IntentStatus.FAILED, error=str(exc))
            if isinstance(exc, (ToolExecutionError, TimeoutError, OSError)):
                raise
            raise ToolExecutionError(str(exc)) from exc

    def _wal_critical(self, task: Task, stage: LoopStage, reason: str) -> None:
        try:
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
            self._wal.append(entry)
        except Exception:  # noqa: BLE001
            pass
