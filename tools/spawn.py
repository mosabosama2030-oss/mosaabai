"""Secure spawn_child — tool_id required, sandbox execution (EO-005 G4)."""

from __future__ import annotations

import types
from typing import Any

from core.errors import SecurityDowngradeError
from core.security import execute_in_sandbox, frozen_builtins
from tools.trusted_registry import TrustedToolRegistry


def spawn_child(
    tool_id: str,
    registry: TrustedToolRegistry,
    *,
    parent_ids: frozenset[str] | None = None,
    args: tuple[Any, ...] = (),
    kwargs: dict[str, Any] | None = None,
) -> Any:
    """Authorize by tool_id only and execute in frozen-builtins context.

    CRIT-01: missing/null/malformed tool_id → SecurityDowngradeError (no name fallback).
    I-005: child tool_id must be ⊆ parent_ids when parent_ids provided.
    """
    if tool_id is None or not isinstance(tool_id, str) or not tool_id.strip():
        raise SecurityDowngradeError("spawn_child requires non-empty tool_id: str")

    if parent_ids is not None and tool_id not in parent_ids:
        raise SecurityDowngradeError(
            f"child tool_id not in parent trusted set: {tool_id[:16]}…"
        )

    record = registry.get(tool_id)
    if record is None:
        raise SecurityDowngradeError(f"unknown tool_id (fail closed): {tool_id[:16]}…")

    fb = frozen_builtins()
    if not isinstance(fb, types.MappingProxyType):
        raise SecurityDowngradeError("__builtins__ freeze violated")

    return execute_in_sandbox(record.fn, *(args or ()), **(kwargs or {}))
