from __future__ import annotations

from repolearn import (
    InteractionMode,
    LearningResponseDisposition,
    ProjectionConflictError,
    StateBackend,
    StateUnavailableError,
    StaleProjectionError,
    TaskContext,
    TriggerDisposition,
    classify_learning_response,
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


class StaleBackend(UnavailableBackend):
    def read_current_state(self, profile_id):
        raise StaleProjectionError("stale")


class ConflictingBackend(UnavailableBackend):
    def read_current_state(self, profile_id):
        raise ProjectionConflictError("reassessment required")


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


def test_stale_projection_also_degrades_to_normal_engineering():
    decision = prepare_learning_decision(
        backend=StaleBackend(),
        profile_id="james",
        context=TaskContext(),
        mode=InteractionMode.GUIDED,
        candidate_concepts=["state continuity"],
    )
    assert not decision.state_loaded
    assert decision.engineering_may_continue
    assert not decision.visible_learning_allowed
    assert decision.degraded_reason == "stale"


def test_conflicting_projection_also_fails_open_for_engineering_interaction():
    decision = prepare_learning_decision(
        backend=ConflictingBackend(),
        profile_id="james",
        context=TaskContext(),
        mode=InteractionMode.GUIDED,
        candidate_concepts=["authority boundary"],
    )
    assert not decision.state_loaded
    assert decision.engineering_may_continue
    assert not decision.visible_learning_allowed
    assert decision.degraded_reason == "reassessment required"


def test_learning_no_response_is_skip_not_assessment_or_blocker():
    result = classify_learning_response(None)
    assert result.disposition is LearningResponseDisposition.SKIP_NO_RESPONSE
    assert not result.should_assess
    assert result.engineering_may_continue


def test_valid_unassessed_state_is_not_backend_failure_and_can_still_trigger():
    class UnassessedBackend(UnavailableBackend):
        def read_current_state(self, profile_id):
            return None

    decision = prepare_learning_decision(
        backend=UnassessedBackend(),
        profile_id="new-user",
        context=TaskContext(),
        mode=InteractionMode.GUIDED,
        candidate_concepts=["state continuity"],
    )
    assert not decision.state_loaded
    assert decision.degraded_reason is None
    assert decision.visible_learning_allowed
    assert decision.engineering_may_continue
