"""Tool interface: the contract every executable tool implements.

EO-005 G4: canonical tool identity (tool_id) for I-005 enforcement.
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


def compute_tool_id(spec_dict: dict[str, Any]) -> str:
    """Return sha256 hex of canonical JSON(spec_dict). Deterministic."""
    canonical = json.dumps(spec_dict, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class ToolResult:
    """Outcome of a single tool execution."""

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


class Tool(ABC):
    """Base class for all tools.

    Subclasses set `name`, `description`, and `parameters` as class attributes
    and implement `execute`. `tool_id` is computed from the canonical spec
    unless a subclass overrides it intentionally.
    """

    name: str = ""
    description: str = ""
    parameters: dict[str, Any] = {}
    version: str = "1.0.0"

    def to_schema(self) -> dict[str, Any]:
        """Return the LLM-facing declaration of this tool."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "version": self.version,
        }

    @property
    def tool_id(self) -> str:
        """Canonical identity: sha256 of sorted name|version|schema."""
        return compute_tool_id(self.to_schema())

    def identity_tuple(self) -> tuple[str, str, str]:
        """Return (tool_id, name, version)."""
        return (self.tool_id, self.name, self.version)

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        raise NotImplementedError

    @property
    def required_parameters(self) -> list[str]:
        return list(self.parameters.get("required", []))

    @property
    def parameter_names(self) -> list[str]:
        return list(self.parameters.get("properties", {}))
