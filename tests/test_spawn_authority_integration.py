"""S2-C — spawn_child Authority integration tests."""

from __future__ import annotations

import pytest

from core.security_exceptions import AuthorityViolationError
from core.wal import IntentStatus, WriteAheadLog
from governance.authority import Authority
from tools.spawn import spawn_child


def _add(a, b):
    return a + b


def test_spawn_child_requires_authority() -> None:
    with pytest.raises(TypeError):
        spawn_child("t1", fn=_add, args=(1, 2))  # type: ignore[call-arg]


def test_insufficient_authority_rejected() -> None:
    auth = Authority(subject="agent", scope=frozenset({"read"}))
    with pytest.raises(AuthorityViolationError):
        spawn_child(
            "add",
            authority=auth,
            required_capabilities=frozenset({"write"}),
            fn=_add,
            args=(1, 2),
        )


def test_sufficient_authority_accepted() -> None:
    auth = Authority(subject="agent", scope=frozenset({"compute", "read"}))
    result = spawn_child(
        "add",
        authority=auth,
        required_capabilities=frozenset({"compute"}),
        fn=_add,
        args=(2, 3),
    )
    assert result == 5


def test_authority_violation_logs_wal_critical(tmp_path) -> None:  # noqa: ANN001
    auth = Authority(subject="agent", scope=frozenset({"read"}))
    wal = WriteAheadLog(tmp_path / "auth.wal")
    with pytest.raises(AuthorityViolationError):
        spawn_child(
            "write_tool",
            authority=auth,
            required_capabilities=frozenset({"write"}),
            fn=_add,
            args=(1, 1),
            wal=wal,
        )
    entries = wal._read_all()
    assert any(
        e.status == IntentStatus.FAILED and "CRITICAL" in e.action_id for e in entries
    )
