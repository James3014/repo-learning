from __future__ import annotations

from repolearn import (
    InteractionMode,
    StateBackend,
    StateUnavailableError,
    TaskContext,
    TriggerDisposition,
    prepare_learning_decision,
)


class UnavailableBackend(StateBackend):
    def read_current_state(self, profile_id):
        raise StateUnavailableError("offline")

    def append_learning_event(self, profile_id, event):
        raise AssertionError("not used")

    def refresh_projection(self, profile_id):
        raise AssertionError("not used")

    def read_related_history(self, profile_id, *, concept=None, limit=20):
        raise AssertionError("not used")


def test_backend_unavailable_degrades_without_blocking_engineering():
    decision = prepare_learning_decision(
        backend=UnavailableBackend(),
        profile_id="james",
        context=TaskContext(mechanical=True),
        mode=InteractionMode.GUIDED,
        candidate_concepts=["authority boundary"],
    )
    assert not decision.state_loaded
    assert decision.trigger.disposition is TriggerDisposition.NO_TRIGGER
    assert decision.degraded_reason == "offline"


def test_exact_machine_output_never_allows_visible_learning():
    decision = prepare_learning_decision(
        backend=UnavailableBackend(),
        profile_id="james",
        context=TaskContext(exact_machine_output=True),
        mode=InteractionMode.PRACTICE,
        candidate_concepts=["state continuity"],
    )
    assert decision.trigger.disposition is TriggerDisposition.NO_TRIGGER
    assert not decision.visible_learning_allowed
