"""EO-005 G4b — 16 mandatory adversarial tests."""

from __future__ import annotations

import types

import pytest

from core.security import (
    ASTSecurityViolationError,
    RegistryImmutableError,
    SecurityDowngradeError,
    StatefulToolError,
    compute_spec_digest,
    frozen_builtins,
)
from tools.spawn import spawn_child
from tools.trusted_registry import TrustedToolRegistry


def _add(a, b):
    return a + b


def _mul(a, b):
    return a * b


def test_legacy_tool_registry_removed_or_unreachable() -> None:
    import tools.spawn as spawn_mod
    import tools.trusted_registry as tr

    with open(spawn_mod.__file__) as f1, open(tr.__file__) as f2:
        src = f1.read() + f2.read()
    assert "from tools.tool_registry" not in src
    assert hasattr(tr, "TrustedToolRegistry")
    with pytest.raises(ImportError):
        from tools.spawn import ToolRegistry  # type: ignore[attr-defined]  # noqa: F401


def test_no_name_only_tool_authorization() -> None:
    reg = TrustedToolRegistry()
    reg.register(name="add", version="1.0.0", description="add", parameters={}, fn=_add)
    with pytest.raises(SecurityDowngradeError):
        spawn_child("", registry=reg)
    with pytest.raises(SecurityDowngradeError):
        spawn_child(None, registry=reg)  # type: ignore[arg-type]


def test_spec_digest_is_deterministic() -> None:
    d1 = compute_spec_digest("add", "1.0.0", "add", {}, _add)
    d2 = compute_spec_digest("add", "1.0.0", "add", {}, _add)
    assert d1 == d2 and len(d1) == 64


def test_spec_digest_changes_when_code_changes() -> None:
    assert compute_spec_digest("op", "1.0.0", "op", {}, _add) != compute_spec_digest(
        "op", "1.0.0", "op", {}, _mul
    )


def test_same_name_different_bytecode_rejected() -> None:
    reg = TrustedToolRegistry()
    reg.register(name="op", version="1.0.0", description="op", parameters={}, fn=_add)
    with pytest.raises(SecurityDowngradeError):
        reg.register(name="op", version="1.0.0", description="op", parameters={}, fn=_mul)


def test_freevars_and_cellvars_rejected_at_registration() -> None:
    outer = 1

    def closure_fn(x):
        return x + outer

    reg = TrustedToolRegistry()
    with pytest.raises(StatefulToolError):
        reg.register(name="c", version="1.0.0", description="c", parameters={}, fn=closure_fn)


def test_registry_is_immutable_after_creation() -> None:
    reg = TrustedToolRegistry()
    reg.register(name="add", version="1.0.0", description="add", parameters={}, fn=_add)
    reg.freeze()
    assert isinstance(reg.mapping, types.MappingProxyType)
    with pytest.raises(RegistryImmutableError):
        reg.register(name="mul", version="1.0.0", description="mul", parameters={}, fn=_mul)


def test_registry_rejects_redefinition() -> None:
    reg = TrustedToolRegistry()
    reg.register(name="add", version="1.0.0", description="add", parameters={}, fn=_add)
    with pytest.raises(RegistryImmutableError):
        reg.register(name="add", version="1.0.0", description="add", parameters={}, fn=_add)


def test_registered_tool_mutation_cannot_change_trust() -> None:
    reg = TrustedToolRegistry()
    tid = reg.register(name="add", version="1.0.0", description="add", parameters={}, fn=_add)
    assert reg.is_trusted(tid)
    assert not reg.is_trusted("0" * 64)


def test_spawn_child_delegates_trusted_identity_not_name() -> None:
    reg = TrustedToolRegistry()
    tid = reg.register(name="add", version="1.0.0", description="add", parameters={}, fn=_add)
    assert spawn_child(tid, registry=reg, args=(2, 3)) == 5


def test_spawn_child_rejects_missing_tool_id() -> None:
    reg = TrustedToolRegistry()
    reg.register(name="add", version="1.0.0", description="add", parameters={}, fn=_add)
    with pytest.raises(SecurityDowngradeError):
        spawn_child("   ", registry=reg)


def test_ast_whitelist_blocks_attribute_access() -> None:
    reg = TrustedToolRegistry()

    def bad(x):
        return x.__class__

    with pytest.raises(ASTSecurityViolationError):
        reg.register(name="bad", version="1.0.0", description="bad", parameters={}, fn=bad)


def test_ast_whitelist_blocks_aliased_eval_call() -> None:
    reg = TrustedToolRegistry()

    def bad(x):
        return eval("1+1")  # noqa: S307

    with pytest.raises(ASTSecurityViolationError):
        reg.register(name="bad", version="1.0.0", description="bad", parameters={}, fn=bad)


def test_builtins_mutation_raises_type_error() -> None:
    fb = frozen_builtins()
    assert isinstance(fb, types.MappingProxyType)
    with pytest.raises(TypeError):
        fb["eval"] = eval  # type: ignore[index]


def test_unknown_digest_fails_closed() -> None:
    reg = TrustedToolRegistry()
    reg.register(name="add", version="1.0.0", description="add", parameters={}, fn=_add)
    with pytest.raises(SecurityDowngradeError):
        spawn_child("deadbeef" * 8, registry=reg)


def test_child_tool_set_remains_monotonic_by_identity() -> None:
    reg = TrustedToolRegistry()
    tid = reg.register(name="add", version="1.0.0", description="add", parameters={}, fn=_add)
    parent_ids = frozenset({tid})
    assert spawn_child(tid, registry=reg, parent_ids=parent_ids, args=(1, 1)) == 2
    with pytest.raises(SecurityDowngradeError):
        spawn_child("00" * 32, registry=reg, parent_ids=parent_ids)
