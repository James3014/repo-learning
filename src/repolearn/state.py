"""State-backend contracts for RepoLearn.

G1 defines the boundary only. Concrete storage backends belong to later gates.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import Any


CLIENT_NATIVE_MEMORY_IS_CANONICAL = False
"""Client-native memory must never become the canonical mastery store."""

LEARNING_STATE_AFFECTS_ENGINEERING_AUTHORITY = False
"""Learning state cannot change target-repository engineering authority."""


class StateUnavailableError(RuntimeError):
    """Raised when a configured canonical learning-state backend is unavailable."""


class StateBackend(ABC):
    """Storage-neutral contract for canonical personal learning state.

    Backends own persistence semantics only. They do not own repository routing,
    verification, acceptance, merge, release, security, or production authority.
    """

    @abstractmethod
    def read_current_state(self, profile_id: str) -> Mapping[str, Any] | None:
        """Return the bounded current projection, or ``None`` when unassessed."""

    @abstractmethod
    def append_learning_event(self, profile_id: str, event: Mapping[str, Any]) -> str:
        """Append one durable learning event and return its stable event identity."""

    @abstractmethod
    def refresh_projection(self, profile_id: str) -> Mapping[str, Any]:
        """Recompute and return the bounded current-state projection."""

    @abstractmethod
    def read_related_history(
        self,
        profile_id: str,
        *,
        concept: str | None = None,
        limit: int = 20,
    ) -> Sequence[Mapping[str, Any]]:
        """Read bounded related history on demand, not the whole ledger by default."""
