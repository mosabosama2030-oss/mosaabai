"""Bounded, JSON-safe error envelope for MosaabAI."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar

T = TypeVar("T")
MAX_MESSAGE_CHARS = 1000
MAX_CONTEXT_KEYS = 10
MAX_CONTEXT_VALUE_CHARS = 500
TRUNCATION_MARKER = "...[TRUNCATED]"


class ErrorCode(Enum):
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


def _truncate_string(value, limit):
    if not isinstance(value, str):
        return value, False
    if len(value) <= limit:
        return value, False
    keep = max(0, limit - len(TRUNCATION_MARKER))
    return value[:keep] + TRUNCATION_MARKER, True


def _serialize_cause(cause):
    if cause is None:
        return None
    return {"type": type(cause).__name__, "message": str(cause)}


def _bounded_context(context):
    flags = []
    bounded = {}
    if len(context) > MAX_CONTEXT_KEYS:
        keys = sorted(context.keys())[:MAX_CONTEXT_KEYS]
        flags.append("context_keys")
    else:
        keys = sorted(context.keys())
    for key in keys:
        value = context[key]
        if isinstance(value, str):
            new_val, trunc = _truncate_string(value, MAX_CONTEXT_VALUE_CHARS)
            if trunc:
                if "context_value" not in flags:
                    flags.append("context_value")
                value = new_val
        bounded[key] = value
    return bounded, flags


@dataclass(frozen=True)
class MosaabError:
    code: ErrorCode
    message: str
    version: str = "1.0.0"
    fatal: bool = False
    retryable: bool = False
    context: dict = None
    trace_id: str = None
    cause: Exception = None
    _truncation_flags: tuple = field(default_factory=tuple, compare=False, repr=False)

    def __post_init__(self):
        flags = []
        new_msg, msg_trunc = _truncate_string(self.message, MAX_MESSAGE_CHARS)
        if msg_trunc:
            flags.append("message")
            object.__setattr__(self, "message", new_msg)
        if self.context is not None:
            bounded, ctx_flags = _bounded_context(self.context)
            object.__setattr__(self, "context", bounded)
            flags.extend(ctx_flags)
        if flags:
            object.__setattr__(self, "_truncation_flags", tuple(flags))

    def to_dict(self):
        return {
            "_truncated": list(self._truncation_flags),
            "cause": _serialize_cause(self.cause),
            "code": self.code.value,
            "context": dict(self.context) if self.context else None,
            "fatal": self.fatal,
            "message": self.message,
            "retryable": self.retryable,
            "trace_id": self.trace_id,
            "version": self.version,
        }


@dataclass(frozen=True)
class Result(Generic[T]):
    _value: Any = None
    _error: Any = None
    _is_ok: bool = True

    def is_ok(self):
        return self._is_ok

    def is_err(self):
        return not self._is_ok

    def unwrap(self):
        if not self._is_ok:
            msg = self._error.message if self._error else "unknown error"
            raise ValueError("unwrap() called on Err: " + msg)
        return self._value

    def unwrap_err(self):
        if self._is_ok:
            raise ValueError("unwrap_err() called on Ok")
        return self._error


def ok(value):
    return Result(_value=value, _is_ok=True)


def err(code, message, **kwargs):
    return Result(_error=MosaabError(code=code, message=message, **kwargs), _is_ok=False)
