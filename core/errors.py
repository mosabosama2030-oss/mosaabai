"""Canonical error envelope for MosaabAI (EO-002 / Canonical Architecture A0.2).

Standard library only: no Pydantic, no external dependencies.
Deterministic, JSON-safe, and bounded serialization with no raw traceback exposure.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, TypeVar, cast

T = TypeVar("T")

MAX_MESSAGE_CHARS = 1000
MAX_CONTEXT_KEYS = 10
MAX_CONTEXT_VALUE_CHARS = 500


class ErrorCode(Enum):
    """The 11 architectural failure states of MosaabAI."""

    validation_failure = "validation_failure"
    authorization_failure = "authorization_failure"
    sandbox_failure = "sandbox_failure"
    tool_failure = "tool_failure"
    resource_exhaustion = "resource_exhaustion"
    policy_violation = "policy_violation"
    integrity_failure = "integrity_failure"
    provenance_failure = "provenance_failure"
    timeout = "timeout"
    external_dependency_failure = "external_dependency_failure"
    verification_failure = "verification_failure"


def _stringify_cause(cause: Exception) -> dict[str, str]:
    """Reduce an exception to a safe {type, message} pair — never the raw object."""
    return {"type": type(cause).__name__, "message": str(cause)}


@dataclass(frozen=True)
class MosaabError:
    """Bounded, JSON-safe error envelope (I-011 resource boundedness)."""

    code: ErrorCode
    message: str
    version: str = "1.0.0"
    fatal: bool = False
    retryable: bool = False
    context: dict[str, Any] | None = None
    trace_id: str | None = None
    cause: Exception | None = None

    def __post_init__(self) -> None:
        if len(self.message) > MAX_MESSAGE_CHARS:
            raise ValueError(f"message exceeds {MAX_MESSAGE_CHARS} characters")
        if self.context is not None:
            object.__setattr__(self, "context", self._bounded_context())

    def _bounded_context(self) -> dict[str, Any]:
        """Enforce context bounds: <=10 keys, values coerced to str of <=500 chars."""
        if not isinstance(self.context, dict):
            raise ValueError("context must be a dict or None")
        if len(self.context) > MAX_CONTEXT_KEYS:
            raise ValueError(f"context exceeds {MAX_CONTEXT_KEYS} keys")
        bounded: dict[str, Any] = {}
        for key, value in self.context.items():
            text = value if isinstance(value, str) else str(value)
            if len(text) > MAX_CONTEXT_VALUE_CHARS:
                raise ValueError(
                    f"context value for {key!r} exceeds {MAX_CONTEXT_VALUE_CHARS} characters"
                )
            bounded[key] = text
        return bounded

    def to_dict(self) -> dict[str, Any]:
        """Deterministic JSON-safe dict with sorted keys; cause reduced to strings."""
        payload: dict[str, Any] = {
            "code": self.code.value,
            "message": self.message,
            "version": self.version,
            "fatal": self.fatal,
            "retryable": self.retryable,
            "context": dict(self.context) if self.context is not None else None,
            "trace_id": self.trace_id,
            "cause": _stringify_cause(self.cause) if self.cause is not None else None,
        }
        return {key: payload[key] for key in sorted(payload)}


@dataclass(frozen=True)
class Result(Generic[T]):
    """Immutable success-or-error container (Result monad)."""

    _value: T | None = None
    _error: MosaabError | None = None
    _is_ok: bool = True

    def __post_init__(self) -> None:
        if self._is_ok and self._error is not None:
            raise ValueError("ok result cannot carry an error")
        if not self._is_ok and self._error is None:
            raise ValueError("err result must carry an error")

    def is_ok(self) -> bool:
        return self._is_ok

    def is_err(self) -> bool:
        return not self._is_ok

    def unwrap(self) -> T:
        if not self._is_ok:
            raise ValueError(f"called unwrap() on an err result: {self._error}")
        return cast(T, self._value)

    def unwrap_err(self) -> MosaabError:
        if self._is_ok:
            raise ValueError("called unwrap_err() on an ok result")
        if self._error is None:
            raise ValueError("err result is missing its MosaabError")
        return self._error


def ok(value: T) -> Result[T]:
    """Wrap a successful value in an ok Result."""
    return Result(_value=value, _error=None, _is_ok=True)


def err(code: ErrorCode, message: str, **kwargs: Any) -> Result[Any]:
    """Wrap a MosaabError built from code, message, and envelope kwargs."""
    error = MosaabError(code=code, message=message, **kwargs)
    return Result(_value=None, _error=error, _is_ok=False)
