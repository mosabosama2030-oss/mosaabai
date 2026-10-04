"""Acceptance tests for the canonical error envelope (EO-002)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from core.errors import ErrorCode, MosaabError, Result, err, ok

SECRET_TEST_VALUE = "sk-live-DO-NOT-LEAK-9f3a"

EXPECTED_CODES = {
    "validation_failure",
    "authorization_failure",
    "sandbox_failure",
    "tool_failure",
    "resource_exhaustion",
    "policy_violation",
    "integrity_failure",
    "provenance_failure",
    "timeout",
    "external_dependency_failure",
    "verification_failure",
}


def test_error_code_exhaustiveness() -> None:
    assert len(ErrorCode) == 11
    assert {member.name for member in ErrorCode} == EXPECTED_CODES
    assert {member.value for member in ErrorCode} == EXPECTED_CODES


def test_mosaab_error_required_fields() -> None:
    error = MosaabError(ErrorCode.validation_failure, "invalid payload")
    assert error.code is ErrorCode.validation_failure
    assert error.message == "invalid payload"
    assert error.version == "1.0.0"
    assert error.fatal is False
    assert error.retryable is False
    assert error.context is None
    assert error.trace_id is None
    assert error.cause is None


def test_mosaab_error_to_dict_json_safe() -> None:
    error = MosaabError(
        ErrorCode.policy_violation,
        "blocked by policy",
        context={"rule": "no_secrets", "depth": 2},
        trace_id="trace-1",
        cause=ValueError("bad input"),
    )
    payload = error.to_dict()
    text = json.dumps(payload, sort_keys=True)
    assert json.loads(text) == payload
    assert payload["code"] == "policy_violation"
    assert payload["cause"] == {"type": "ValueError", "message": "bad input"}


def test_mosaab_error_to_dict_deterministic() -> None:
    def build() -> dict[str, Any]:
        return MosaabError(
            ErrorCode.tool_failure,
            "tool failed",
            context={"b": "2", "a": "1", "c": "3"},
            trace_id="t-9",
        ).to_dict()

    first, second = build(), build()
    assert first == second
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert list(first) == sorted(first)


def test_mosaab_error_stringifies_cause() -> None:
    inner = RuntimeError("inner boom")
    outer = ValueError("outer boom")
    outer.__cause__ = inner
    error = MosaabError(ErrorCode.sandbox_failure, "sandbox crashed", cause=outer)
    payload = error.to_dict()
    assert payload["cause"] == {"type": "ValueError", "message": "outer boom"}
    text = json.dumps(payload, sort_keys=True)
    assert "RuntimeError" not in text
    assert "inner boom" not in text


def test_mosaab_error_preserves_trace_id() -> None:
    error = MosaabError(ErrorCode.timeout, "deadline exceeded", trace_id="trace-abc-123")
    assert error.to_dict()["trace_id"] == "trace-abc-123"
    wrapped = err(ErrorCode.timeout, "deadline exceeded", trace_id="trace-abc-123")
    assert wrapped.is_err()
    assert wrapped.unwrap_err().trace_id == "trace-abc-123"


def test_mosaab_error_preserves_retryable() -> None:
    failure = err(
        ErrorCode.external_dependency_failure, "upstream 503", retryable=True
    ).unwrap_err()
    assert failure.retryable is True
    assert failure.to_dict()["retryable"] is True
    assert MosaabError(ErrorCode.tool_failure, "boom").retryable is False




def test_mosaab_error_no_raw_exception_leak() -> None:
    class LeakyError(Exception):
        def __repr__(self) -> str:
            return f"LeakyError({SECRET_TEST_VALUE})"

    cause = LeakyError("handled failure")
    assert SECRET_TEST_VALUE in repr(cause)
    error = MosaabError(ErrorCode.provenance_failure, "provenance check failed", cause=cause)
    payload = error.to_dict()
    assert set(payload["cause"]) == {"type", "message"}
    text = json.dumps(payload, sort_keys=True)
    assert SECRET_TEST_VALUE not in text
    assert repr(cause) not in text


def test_result_ok_unwraps_correctly() -> None:
    result = ok(42)
    assert isinstance(result, Result)
    assert result.is_ok() is True
    assert result.is_err() is False
    assert result.unwrap() == 42
    empty = ok(None)
    assert empty.is_ok() is True
    assert empty.is_err() is False
    assert empty.unwrap() is None


def test_result_err_unwraps_err_correctly() -> None:
    result: Result[Any] = err(ErrorCode.tool_failure, "tool exploded", fatal=True)
    assert result.is_err() is True
    assert result.is_ok() is False
    failure = result.unwrap_err()
    assert isinstance(failure, MosaabError)
    assert failure.code is ErrorCode.tool_failure
    assert failure.message == "tool exploded"
    assert failure.fatal is True


def test_result_ok_unwrap_err_raises_value_error() -> None:
    result = ok("value")
    with pytest.raises(ValueError):
        result.unwrap_err()


def test_result_err_unwrap_raises_value_error() -> None:
    result = err(ErrorCode.authorization_failure, "denied")
    with pytest.raises(ValueError, match="denied"):
        result.unwrap()


def test_message_truncated_silently() -> None:
    error = MosaabError(code=ErrorCode.tool_failure, message="A" * 1500)
    assert len(error.message) == 1000
    assert error.message.endswith("...[TRUNCATED]")


def test_context_keys_truncated_silently() -> None:
    ctx = {f"k{i:02d}": i for i in range(15)}
    error = MosaabError(code=ErrorCode.validation_failure, message="ok", context=ctx)
    assert error.context is not None
    assert len(error.context) == 10
    assert list(error.context.keys()) == sorted(ctx.keys())[:10]


def test_context_value_truncated_silently() -> None:
    error = MosaabError(code=ErrorCode.tool_failure, message="ok", context={"k": "B" * 800})
    assert error.context is not None
    assert len(error.context["k"]) == 500
    assert error.context["k"].endswith("...[TRUNCATED]")


def test_truncation_flags_recorded() -> None:
    ctx = {f"k{i:02d}": "C" * 800 for i in range(15)}
    error = MosaabError(code=ErrorCode.tool_failure, message="D" * 1500, context=ctx)
    flags = error._truncation_flags
    assert "message" in flags
    assert "context_keys" in flags
    assert "context_value" in flags
    assert error.to_dict()["_truncated"] == list(flags)


def test_no_valueerror_during_bounding() -> None:
    try:
        ctx = {f"k{i}": "Y" * 2000 for i in range(50)}
        MosaabError(
            code=ErrorCode.tool_failure,
            message="X" * 10000,
            context=ctx,
        )
    except ValueError as exc:
        raise AssertionError("ValueError during bounding: " + str(exc)) from exc


def test_truncation_deterministic() -> None:
    ctx = {f"k{i:02d}": "Z" * 800 for i in range(15)}
    e1 = MosaabError(code=ErrorCode.tool_failure, message="A" * 1500, context=ctx)
    e2 = MosaabError(code=ErrorCode.tool_failure, message="A" * 1500, context=ctx)
    assert e1.message == e2.message
    assert e1.context == e2.context
    assert e1._truncation_flags == e2._truncation_flags
