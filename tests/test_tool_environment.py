"""Acceptance tests for the injectable ToolEnvironment (EO-003)."""

from __future__ import annotations

from typing import Any

import pytest

from tools.tool_environment import CapabilityViolationError, EmptyEnvironment, create_root
from tools.tool_interface import Tool, ToolResult


class _EchoTool(Tool):
    name = "echo"
    description = "echoes input"
    parameters = {"type": "object", "properties": {"text": {"type": "string"}}}

    async def execute(self, **kwargs: Any) -> ToolResult:
        return ToolResult.ok(kwargs.get("text", ""))


class _CalcTool(Tool):
    name = "calc"
    description = "basic arithmetic"
    parameters = {"type": "object", "properties": {"expr": {"type": "string"}}}

    async def execute(self, **kwargs: Any) -> ToolResult:
        return ToolResult.ok(42)


class _SecretTool(Tool):
    name = "secret"
    description = "should not escape"
    parameters = {}

    async def execute(self, **kwargs: Any) -> ToolResult:
        return ToolResult.failed("no secret here")


BASE_TOOLS = (
    _EchoTool(),
    _CalcTool(),
)

BASE_CAPABILITIES = {"read", "write"}


def test_tool_environment_creation() -> None:
    env = create_root("root", list(BASE_TOOLS), BASE_CAPABILITIES)
    assert env.environment_id == "root"
    assert env.parent_id is None
    assert len(env.tools) == 2
    assert env.capabilities == BASE_CAPABILITIES


def test_tool_environment_frozen() -> None:
    env = create_root("root", list(BASE_TOOLS), BASE_CAPABILITIES)
    with pytest.raises(AttributeError):
        env.tools = ()  # type: ignore[assignment]
    with pytest.raises(AttributeError):
        env.capabilities = frozenset()
    assert env.capabilities == BASE_CAPABILITIES


def test_tool_environment_has_tool() -> None:
    env = create_root("root", list(BASE_TOOLS), BASE_CAPABILITIES)
    assert env.has_tool("echo") is True
    assert env.has_tool("calc") is True
    assert env.has_tool("missing") is False


def test_tool_environment_get_tool() -> None:
    env = create_root("root", list(BASE_TOOLS), BASE_CAPABILITIES)
    assert env.get_tool("echo") is not None
    assert env.get_tool("echo").name == "echo"
    assert env.get_tool("missing") is None


def test_tool_environment_list_tools() -> None:
    env = create_root("root", list(BASE_TOOLS), BASE_CAPABILITIES)
    assert env.list_tools() == ["calc", "echo"]


def test_tool_environment_has_capability() -> None:
    env = create_root("root", list(BASE_TOOLS), BASE_CAPABILITIES)
    assert env.has_capability("read") is True
    assert env.has_capability("write") is True
    assert env.has_capability("tool") is False


def test_spawn_child_success() -> None:
    parent = create_root("parent", list(BASE_TOOLS), BASE_CAPABILITIES)
    child = parent.spawn_child(
        "child",
        (BASE_TOOLS[0],),
        frozenset({"read"}),
    )
    assert child.environment_id == "child"
    assert child.parent_id == "parent"
    assert child.has_tool("echo") is True
    assert child.has_capability("read") is True
    assert child.has_capability("write") is False


def test_spawn_child_rejects_escalation() -> None:
    parent = create_root("parent", list(BASE_TOOLS), BASE_CAPABILITIES)
    with pytest.raises(CapabilityViolationError) as excinfo:
        parent.spawn_child(
            "child",
            (BASE_TOOLS[0],),
            frozenset({"read", "tool"}),
        )
    assert excinfo.value.parent_id == "parent"
    assert excinfo.value.child_id == "child"
    assert "tool" in excinfo.value.violating_capabilities


def test_spawn_child_rejects_extra_tools() -> None:
    parent = create_root("parent", list(BASE_TOOLS), BASE_CAPABILITIES)
    with pytest.raises(CapabilityViolationError) as excinfo:
        parent.spawn_child(
            "child",
            BASE_TOOLS + (_SecretTool(),),
            frozenset(),
        )
    assert excinfo.value.parent_id == "parent"
    assert excinfo.value.child_id == "child"
    assert any(v.startswith("tool") for v in excinfo.value.violating_capabilities)


def test_spawn_child_preserves_parent_id() -> None:
    parent = create_root("parent", list(BASE_TOOLS), BASE_CAPABILITIES)
    child = parent.spawn_child("grandchild", (BASE_TOOLS[0],), frozenset({"read"}))
    assert child.parent_id == "parent"
    grandchild = child.spawn_child("grandchild2", (BASE_TOOLS[0],), frozenset({"read"}))
    assert grandchild.parent_id == "grandchild"


def test_capability_violation_error_serialization() -> None:
    parent = create_root("parent", list(BASE_TOOLS), BASE_CAPABILITIES)
    with pytest.raises(CapabilityViolationError) as excinfo:
        parent.spawn_child("child", (BASE_TOOLS[0],), frozenset({"write", "escalate"}))
    payload = excinfo.value.to_dict()
    assert json_safe(payload)
    assert payload["child_id"] == "child"
    assert payload["parent_id"] == "parent"
    assert payload["violating_capabilities"] == ["escalate"]


def test_no_global_state_between_environments() -> None:
    root_a = create_root("root-a", list(BASE_TOOLS), BASE_CAPABILITIES)
    root_b = create_root("root-b", list(BASE_TOOLS), BASE_CAPABILITIES)
    assert root_a is not root_b
    assert root_a.environment_id == "root-a"
    assert root_b.environment_id == "root-b"
    assert root_a.list_tools() == root_b.list_tools()
    child = root_a.spawn_child("child", (BASE_TOOLS[0],), frozenset({"read"}))
    assert child.parent_id == "root-a"
    assert child.has_tool("echo") is True
    assert root_b.list_tools() == ["calc", "echo"]


def test_empty_environment_sandbox() -> None:
    env = EmptyEnvironment()
    assert env.environment_id == "__empty__"
    assert env.tools == ()
    assert env.capabilities == frozenset()
    assert env.has_tool("anything") is False
    assert env.has_capability("anything") is False
    assert env.list_tools() == []


def json_safe(value: Any) -> bool:
    try:
        __import__("json").dumps(value, sort_keys=True)
        return True
    except (TypeError, ValueError):
        return False
