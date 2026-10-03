"""Tool interface: the contract every executable tool implements.

Tools are the agent's hands: the cognitive loop's Execute stage dispatches
a planned action to a registered tool and observes the returned
ToolResult, while the planner reads tool schemas to know what is callable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    """Outcome of a single tool execution.

    Tools report expected failures (bad input, domain errors) as
    unsuccessful results rather than raising, so the loop can observe the
    failure and replan instead of crashing.
    """

    success: bool
    output: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, output: Any = None, metadata: dict[str, Any] | None = None) -> ToolResult:
        """Build a successful result."""
        return cls(success=True, output=output, metadata=dict(metadata or {}))

    @classmethod
    def failed(cls, error: str, metadata: dict[str, Any] | None = None) -> ToolResult:
        """Build a failed result."""
        return cls(success=False, error=error, metadata=dict(metadata or {}))


class Tool(ABC):
    """Base class for all tools.

    Subclasses set `name`, `description`, and `parameters` (JSON-Schema
    style, matching LLM tool declarations) as class attributes and
    implement `execute`.
    """

    name: str = ""
    description: str = ""
    parameters: dict[str, Any] = {}

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Run the tool with the given arguments.

        `execute` may be called directly (bypassing the registry), so
        implementations should validate their own input and report
        expected failures as unsuccessful ToolResults.
        """
        raise NotImplementedError

    @property
    def required_parameters(self) -> list[str]:
        """Names of parameters the caller must provide."""
        return list(self.parameters.get("required", []))

    @property
    def parameter_names(self) -> list[str]:
        """Names of all declared parameters."""
        return list(self.parameters.get("properties", {}))

    def to_schema(self) -> dict[str, Any]:
        """Return the LLM-facing declaration of this tool."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }
