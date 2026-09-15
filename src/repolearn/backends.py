from __future__ import annotations

from typing import Any, Mapping, Protocol, Sequence


class StateBackend(Protocol):
    """Storage boundary for one canonical personal-learning state owner."""

    def read_current_state(self) -> Mapping[str, Any]: ...

    def append_learning_event(self, event: Mapping[str, Any]) -> str: ...

    def refresh_projection(self) -> Mapping[str, Any]: ...

    def read_related_history(self, *, concepts: Sequence[str], limit: int = 20) -> Sequence[Mapping[str, Any]]: ...
