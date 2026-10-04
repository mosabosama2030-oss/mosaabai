"""Tool interface: the contract every executable tool implements.

Improvements over v0.1:
  - Canonical tool identity (tool_id) independent of display name
  - Identity is derived from name + version + schema fingerprint
  - Prevents same-name substitution attacks (I-005 / F-002)
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    success: bool
    output: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, output: Any = None, metadata: dict[str, Any] | None = None) -> ToolResult:
        return cls(success=True, output=output, metadata=dict(metadata or {}))

    @classmethod
    def failed(cls, error: str, metadata: dict[str, Any] | None = None) -> ToolResult:
        return cls(success=False, error=error, metadata=dict(metadata or {}))


def compute_tool_id(name: str, version: str, parameters: dict[str, Any]) -> str:
    schema = json.dumps(parameters, sort_keys=True, separators=(",", ":"), default=str)
    raw = f"{name.strip().lower()}|{version.strip()}|{schema}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


class Tool(ABC):
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    parameters: dict[str, Any] = {}

    @property
    def tool_id(self) -> str:
        return compute_tool_id(self.name, self.version, self.parameters)

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        raise NotImplementedError

    @property
    def required_parameters(self) -> list[str]:
        return list(self.parameters.get("required", []))

    @property
    def parameter_names(self) -> list[str]:
        return list(self.parameters.get("properties", {}))

    def to_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "tool_id": self.tool_id,
            "description": self.description,
            "parameters": self.parameters,
        }

    def identity_tuple(self) -> tuple[str, str, str]:
        return (self.tool_id, self.name, self.version)
