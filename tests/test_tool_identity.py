"""EO-005 G4b + Sprint 3 adversarial tests."""

from __future__ import annotations

import textwrap
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
    with pytest.raises(ImportError):
        from tools.spawn import ToolRegistry  # type: ignore[attr-defined]  # noqa: F401


def test_no_name_only_tool_authorization() -> None:
    reg = TrustedToolRegistry()
    reg.register(name="add", version="1.0.0", description="add", parameters={}, fn=_add)
    with pytest.raises(SecurityDowngradeError):
        spawn_child("", registry=reg)
    with pytest.raises(SecurityDowngradeError):
        spawn_child(None, registry=reg)  # type: ignore[arg-type]
    with pytest.raises(SecurityDowngradeError):
        spawn_child("add", registry=reg)


def test_spec_digest_is_deterministic() -> None:
    src = "def f(a, b):\n    return a + b\n"
    ns1: dict = {}
    ns2: dict = {}
    exec(src, ns1)  # noqa: S102
    exec(src, ns2)  # noqa: S102
    d1 = compute_spec_digest("f", "1.0.0", "f", {}, ns1["f"])
    d2 = compute_spec_digest("f", "1.0.0", "f", {}, ns2["f"])
    assert d1 == d2 and len(d1) == 64


def test_digest_stable_across_compilations() -> None:
    src = textwrap.dedent(
        """
        def outer(x):
            def inner(y):
                return x + y
            return inner(1)
        """
    )
    digests = []
    for _ in range(3):
        ns: dict = {}
        exec(src, ns)  # noqa: S102
        digests.append(compute_spec_digest("outer", "1", "o", {}, ns["outer"]))
    assert digests[0] == digests[1] == digests[2]


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
    def local_add(a, b):
        return a + b

    def evil(a, b):
        return 0

    reg = TrustedToolRegistry()
    tid = reg.register(
        name="local_add", version="1.0.0", description="add", parameters={}, fn=local_add
    )
    assert reg.is_trusted(tid) is True
    record = reg.get(tid)
    assert record is not None
    record.fn.__code__ = evil.__code__  # type: ignore[misc]
    assert reg.is_trusted(tid) is False


def test_spawn_child_delegates_trusted_identity_not_name() -> None:
    reg = TrustedToolRegistry()
    tid = reg.register(name="add", version="1.0.0", description="add", parameters={}, fn=_add)
    assert spawn_child(tid, registry=reg, args=(2, 3)) == 5


def test_spawn_child_rejects_missing_tool_id() -> None:
    reg = TrustedToolRegistry()
    reg.register(name="add", version="1.0.0", description="add", parameters={}, fn=_add)
    with pytest.raises(SecurityDowngradeError):
        spawn_child("   ", registry=reg)


def test_spawn_child_rejects_name_substitution() -> None:
    reg = TrustedToolRegistry()
    reg.register(name="add", version="1.0.0", description="add", parameters={}, fn=_add)
    with pytest.raises(SecurityDowngradeError):
        spawn_child("add", registry=reg, args=(1, 1))


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
    tid_add = reg.register(name="add", version="1.0.0", description="add", parameters={}, fn=_add)
    tid_mul = reg.register(name="mul", version="1.0.0", description="mul", parameters={}, fn=_mul)
    parent_ids = frozenset({tid_add})
    assert spawn_child(tid_add, registry=reg, parent_ids=parent_ids, args=(1, 1)) == 2
    with pytest.raises(SecurityDowngradeError):
        spawn_child(tid_mul, registry=reg, parent_ids=parent_ids, args=(2, 3))


def test_dict_order_does_not_change_digest() -> None:
    p1 = {"b": 1, "a": 2}
    p2 = {"a": 2, "b": 1}
    assert compute_spec_digest("op", "1.0.0", "d", p1, _add) == compute_spec_digest(
        "op", "1.0.0", "d", p2, _add
    )


def test_registered_function_code_mutation_blocked() -> None:
    def local_add(a, b):
        return a + b

    def evil(a, b):
        return 0

    reg = TrustedToolRegistry()
    tid = reg.register(
        name="local_add2", version="1.0.0", description="add", parameters={}, fn=local_add
    )
    record = reg.get(tid)
    assert record is not None
    record.fn.__code__ = evil.__code__  # type: ignore[misc]
    with pytest.raises(SecurityDowngradeError):
        spawn_child(tid, registry=reg, args=(1, 2))


def test_kwdefaults_mutation_post_registration_rejected() -> None:
    def greeter(msg="hello"):
        return msg

    reg = TrustedToolRegistry()
    tid = reg.register(
        name="greeter", version="1.0.0", description="g", parameters={}, fn=greeter
    )
    assert spawn_child(tid, registry=reg) == "hello"
    greeter.__defaults__ = ("pwned",)
    assert spawn_child(tid, registry=reg) == "hello"


def test_sandbox_actually_isolates_builtins() -> None:
    from core.security import execute_in_sandbox, make_sandbox_globals

    fb = frozen_builtins()
    assert "eval" not in fb and "open" not in fb
    g = make_sandbox_globals()
    assert isinstance(g["__builtins__"], types.MappingProxyType)

    def pure_add(a, b):
        return a + b

    assert execute_in_sandbox(pure_add, 2, 3) == 5


def test_memory_poisoning_via_builtin_dict() -> None:
    fb = frozen_builtins()
    with pytest.raises(TypeError):
        fb["__import__"] = __import__  # type: ignore[index]
