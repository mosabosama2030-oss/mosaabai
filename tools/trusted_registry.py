"""TrustedToolRegistry — immutable, identity-bound registry (EO-005 G4).

F-085: at execution time, recompute digest from live __code__ and reject
if it no longer matches the registered tool_id (TOCTOU-safe re-check).
"""

from __future__ import annotations

import types
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from core.security import (
    analyze_function_ast,
    assert_pure_code_object,
    compute_spec_digest,
)
from core.security_exceptions import (
    RegistryImmutableError,
    SecurityDowngradeError,
)


@dataclass(frozen=True)
class TrustedTool:
    tool_id: str
    name: str
    version: str
    description: str
    parameters: dict[str, Any]
    fn: Callable[..., Any]

    def verify_code_integrity(self) -> None:
        """Recompute digest from current __code__; raise if mutated (F-085)."""
        current = compute_spec_digest(
            self.name, self.version, self.description, self.parameters, self.fn
        )
        if current != self.tool_id:
            raise SecurityDowngradeError(
                f"registered function code mutated (digest mismatch): {self.name}"
            )


class TrustedToolRegistry:
    def __init__(self) -> None:
        self._mutable: dict[str, TrustedTool] = {}
        self._by_name: dict[str, str] = {}
        self._frozen = False
        self._view: types.MappingProxyType[str, TrustedTool] | None = None

    def register(
        self,
        *,
        name: str,
        version: str,
        description: str,
        parameters: dict[str, Any],
        fn: Callable[..., Any],
    ) -> str:
        if self._frozen:
            raise RegistryImmutableError("registry is frozen; re-registration forbidden")
        if not name or not isinstance(name, str):
            raise SecurityDowngradeError("tool name required")
        assert_pure_code_object(fn)
        analyze_function_ast(fn)
        tool_id = compute_spec_digest(name, version, description, parameters, fn)
        if tool_id in self._mutable:
            raise RegistryImmutableError(f"tool_id already registered: {tool_id[:16]}…")
        prior = self._by_name.get(name)
        if prior is not None and prior != tool_id:
            raise SecurityDowngradeError(f"same name different bytecode rejected: {name}")
        record = TrustedTool(
            tool_id=tool_id,
            name=name,
            version=version,
            description=description,
            parameters=dict(parameters),
            fn=fn,
        )
        self._mutable[tool_id] = record
        self._by_name[name] = tool_id
        return tool_id

    def freeze(self) -> None:
        self._frozen = True
        self._view = types.MappingProxyType(dict(self._mutable))

    @property
    def mapping(self) -> types.MappingProxyType[str, TrustedTool]:
        if self._view is None:
            return types.MappingProxyType(self._mutable)
        return self._view

    def get(self, tool_id: str) -> TrustedTool | None:
        if not tool_id or not isinstance(tool_id, str):
            raise SecurityDowngradeError("tool_id required")
        return self._mutable.get(tool_id)

    def known_ids(self) -> frozenset[str]:
        return frozenset(self._mutable.keys())

    def is_trusted(self, tool_id: str) -> bool:
        return tool_id in self._mutable
