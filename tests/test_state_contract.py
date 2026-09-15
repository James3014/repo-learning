from __future__ import annotations

import inspect

from repolearn.state import CLIENT_NATIVE_MEMORY_IS_CANONICAL, LEARNING_STATE_AFFECTS_ENGINEERING_AUTHORITY, StateBackend


def test_state_backend_exposes_only_storage_contract_methods() -> None:
    abstract_methods = set(StateBackend.__abstractmethods__)
    assert abstract_methods == {"read_current_state", "append_learning_event", "refresh_projection", "read_related_history"}
    assert inspect.isabstract(StateBackend)


def test_client_native_memory_is_not_canonical() -> None:
    assert CLIENT_NATIVE_MEMORY_IS_CANONICAL is False


def test_learning_state_never_changes_engineering_authority() -> None:
    assert LEARNING_STATE_AFFECTS_ENGINEERING_AUTHORITY is False
