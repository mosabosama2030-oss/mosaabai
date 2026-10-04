"""Bounded, JSON-safe error envelope for MosaabAI (EO-005 G3 v3)."""

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


def _safe_str(value: Any) -> str:
    """Never raises. Returns a string representation or safe marker."""
    try:
        return str(value)
    except BaseException:
        try:
            return f"<unrepresentable:{type(value).__name__}>"
        except BaseException:
            return "<unrepresentable>"


def _truncate_string(value: Any, limit: int) -> tuple[str, bool]:
    """Never raises. Coerces to str, then truncates silently."""
    if not isinstance(value, str):
        value = _safe_str(value)
    if len(value) <= limit:
        return value, False
    keep = max(0, limit - len(TRUNCATION_MARKER))
    return value[:keep] + TRUNCATION_MARKER, True


def _serialize_cause(cause: Any) -> dict[str, str] | None:
    """Never raises."""
    if cause is None:
        return None
    try:
        return {"type": type(cause).__name__, "message": _safe_str(cause)}
    except BaseException:
        return {"type": "unknown", "message": "<unrepresentable>"}


def _bounded_context(context: Any) -> tuple[dict[str, str], list[str]]:
    """Silent, deterministic, JSON-safe. NEVER raises under any input."""
    flags: list[str] = []

    mapping: Any = context
    if not isinstance(mapping, dict):
        try:
            mapping = dict(mapping)
        except BaseException:
            short = _safe_str(context)[:MAX_CONTEXT_VALUE_CHARS]
            return {"_malformed": short}, ["context_malformed"]

    try:
        all_keys = list(mapping.keys())
    except BaseException:
        return {"_malformed": "<keys-unavailable>"}, ["context_malformed"]

    try:
        sorted_keys = sorted(all_keys)
    except BaseException:
        try:
            sorted_keys = sorted(all_keys, key=_safe_str)
        except BaseException:
            sorted_keys = all_keys

    if len(sorted_keys) > MAX_CONTEXT_KEYS:
        sorted_keys = sorted_keys[:MAX_CONTEXT_KEYS]
        flags.append("context_keys")

    bounded: dict[str, str] = {}
    for key in sorted_keys:
        try:
            value = mapping[key]
        except BaseException:
            continue

        if not isinstance(value, str):
            value = _safe_str(value)

        new_val, trunc = _truncate_string(value, MAX_CONTEXT_VALUE_CHARS)
        if trunc:
            if "context_value" not in flags:
                flags.append("context_value")
            value = new_val

        try:
            safe_key = _safe_str(key)
        except BaseException:
            continue

        bounded[safe_key] = value

    return bounded, flags


@dataclass(frozen=True)
class MosaabError:
    code: ErrorCode
    message: str
    version: str = "1.0.0"
    fatal: bool = False
    retryable: bool = False
    context: dict[str, Any] | None = None
    trace_id: str | None = None
    cause: Exception | None = None
    _truncation_flags: tuple[str, ...] = field(
        default_factory=tuple, compare=False, repr=False
    )

    def __post_init__(self) -> None:
        flags: list[str] = []

        if not isinstance(self.message, str):
            object.__setattr__(self, "message", _safe_str(self.message))
            flags.append("message_coerced")

        new_msg, msg_trunc = _truncate_string(self.message, MAX_MESSAGE_CHARS)
        if msg_trunc:
            flags.append("message")
            object.__setattr__(self, "message", new_msg)

        if self.context is not None:
            bounded, ctx_flags = _bounded_context(self.context)
            object.__setattr__(self, "context", bounded)
            for f in ctx_flags:
                if f not in flags:
                    flags.append(f)

        if flags:
            object.__setattr__(self, "_truncation_flags", tuple(flags))

    def to_dict(self) -> dict[str, Any]:
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

    def __post_init__(self) -> None:
        if self._is_ok and self._error is not None:
            raise ValueError("Ok result cannot carry an error")
        if not self._is_ok and self._error is None:
            raise ValueError("Err result must carry an error")

    def is_ok(self) -> bool:
        return self._is_ok

    def is_err(self) -> bool:
        return not self._is_ok

    def unwrap(self) -> T:
        if not self._is_ok:
            msg = self._error.message if self._error else "unknown error"
            raise ValueError("unwrap() called on Err: " + msg)
        return self._value  # type: ignore[no-any-return]

    def unwrap_err(self) -> MosaabError:
        if self._is_ok:
            raise ValueError("unwrap_err() called on Ok")
        return self._error  # type: ignore[no-any-return]


def ok(value: T) -> Result[T]:
    return Result(_value=value, _is_ok=True)


def err(code: ErrorCode, message: str, **kwargs: Any) -> Result[Any]:
    return Result(_error=MosaabError(code=code, message=message, **kwargs), _is_ok=False)
