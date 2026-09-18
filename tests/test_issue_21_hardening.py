from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from repolearn import (
    ActivationSource,
    AssessmentClassification,
    CueLevel,
    EvidenceProvenance,
    EvidenceTiming,
    GuidedBranch,
    InteractionMode,
    JudgmentEvidence,
    LearningResponseDisposition,
    LocalFileBackend,
    MasteryLevel,
    ProjectionConflictError,
    ResponseRelevance,
    StateBackend,
    StateUnavailableError,
    TaskContext,
    TransferDistance,
    TriggerDisposition,
    UserJudgmentSignal,
    assess_judgment,
    classify_learning_response,
    prepare_learning_decision,
    select_learning_opportunity,
)


class StaticBackend(StateBackend):
    def __init__(self, state):
        self.state = state

    def read_current_state(self, profile_id):
        return self.state

    def append_learning_event(self, profile_id, event):
        raise AssertionError("not used")

    def refresh_projection(self, profile_id):
        raise AssertionError("not used")

    def read_related_history(self, profile_id, *, concept=None, limit=20):
        return ()


class OfflineBackend(StaticBackend):
    def read_current_state(self, profile_id):
        raise StateUnavailableError("offline")


def test_auto_discovery_is_stricter_than_explicit_activation():
    auto = select_learning_opportunity(
        context=TaskContext(activation_source=ActivationSource.AUTO_DISCOVERY),
        mode=InteractionMode.GUIDED,
        candidate_concepts=["authority boundary"],
    )
    explicit = select_learning_opportunity(
        context=TaskContext(activation_source=ActivationSource.EXPLICIT_INVOCATION),
        mode=InteractionMode.GUIDED,
        candidate_concepts=["authority boundary"],
    )
    assert auto.disposition is TriggerDisposition.NO_TRIGGER
    assert auto.reason == "auto_discovery_not_eligible"
    assert explicit.disposition is TriggerDisposition.LEARNING_OPPORTUNITY


def test_auto_discovery_can_trigger_only_when_explicitly_marked_eligible():
    result = select_learning_opportunity(
        context=TaskContext(
            activation_source=ActivationSource.AUTO_DISCOVERY,
            automatic_discovery_trigger_eligible=True,
        ),
        mode=InteractionMode.GUIDED,
        candidate_concepts=["authority boundary"],
    )
    assert result.disposition is TriggerDisposition.LEARNING_OPPORTUNITY


def test_bounded_state_can_suppress_silent_cue_faded_concept():
    state = {
        "schema": "repolearn.learning_state.v1",
        "profile_id": "james",
        "updated_at": "2026-09-18T00:00:00Z",
        "domains": {},
        "concepts": {
            "authority boundary": {
                "level": "L3",
                "evidence_count": 3,
                "last_event_id": "ev-3",
                "last_observed_at": "2026-09-18T00:00:00Z",
                "last_cue_level": "NONE",
                "silent_cue_fading_eligible": True,
                "fading_valid_until": "2026-10-18T00:00:00Z",
                "fading_basis_event_id": "ev-3",
            }
        },
        "source": {"backend": "fixture"},
    }
    decision = prepare_learning_decision(
        backend=StaticBackend(state),
        profile_id="james",
        context=TaskContext(),
        mode=InteractionMode.GUIDED,
        candidate_concepts=["authority boundary"],
        now=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )
    assert decision.trigger.disposition is TriggerDisposition.NO_TRIGGER
    assert decision.trigger.reason == "cue_faded"
    assert not decision.visible_learning_allowed


def test_backend_failure_disables_learning_research_and_keeps_engineering_open():
    decision = prepare_learning_decision(
        backend=OfflineBackend(None),
        profile_id="james",
        context=TaskContext(),
        mode=InteractionMode.GUIDED,
        candidate_concepts=["state continuity"],
    )
    assert decision.trigger.disposition is TriggerDisposition.NO_TRIGGER
    assert decision.trigger.reason == "state_unavailable"
    assert not decision.trigger.learning_research_allowed
    assert decision.engineering_may_continue


def test_prepare_decision_selects_spontaneous_branch_only_for_real_user_judgment():
    framing = prepare_learning_decision(
        backend=StaticBackend(None),
        profile_id="james",
        context=TaskContext(),
        mode=InteractionMode.GUIDED,
        candidate_concepts=["authority boundary"],
        judgment_signal=UserJudgmentSignal(problem_framing_only=True),
    )
    judgment = prepare_learning_decision(
        backend=StaticBackend(None),
        profile_id="james",
        context=TaskContext(),
        mode=InteractionMode.GUIDED,
        candidate_concepts=["authority boundary"],
        judgment_signal=UserJudgmentSignal(
            explicit_position=True,
            rationale_expressed=True,
        ),
    )
    assert framing.guided_branch is GuidedBranch.JUDGMENT_PROMPT
    assert judgment.guided_branch is GuidedBranch.SPONTANEOUS_JUDGMENT_CAPTURE


@pytest.mark.parametrize(
    ("relevance", "expected", "should_assess"),
    [
        (
            ResponseRelevance.PROMPT_ANSWER,
            LearningResponseDisposition.ANSWERED,
            True,
        ),
        (
            ResponseRelevance.UNRELATED_ENGINEERING,
            LearningResponseDisposition.UNRELATED_ENGINEERING_CONTINUATION,
            False,
        ),
        (
            ResponseRelevance.EXPLICIT_SKIP,
            LearningResponseDisposition.EXPLICIT_SKIP,
            False,
        ),
        (
            ResponseRelevance.UNKNOWN,
            LearningResponseDisposition.UNCLASSIFIED,
            False,
        ),
    ],
)
def test_nonempty_later_turn_is_not_automatically_an_answer(relevance, expected, should_assess):
    result = classify_learning_response("continue with the engineering work", relevance=relevance)
    assert result.disposition is expected
    assert result.should_assess is should_assess


def test_post_evidence_agreement_cannot_promote_mastery():
    result = assess_judgment(
        current_level=MasteryLevel.L1,
        user_attempted=True,
        ai_explanation_only=False,
        evidence=JudgmentEvidence(
            goals=("single authority",),
            constraints=("multiple clients",),
            evidence=("verified trace",),
        ),
        evidence_timing=EvidenceTiming.POST_EVIDENCE,
    )
    assert result.classification is AssessmentClassification.POST_EVIDENCE_AGREEMENT
    assert result.evidence_ceiling is MasteryLevel.UNASSESSED
    assert result.recommended_level is MasteryLevel.L1


def test_ai_reformulation_cannot_inflate_user_evidence():
    result = assess_judgment(
        current_level=MasteryLevel.L1,
        user_attempted=True,
        ai_explanation_only=False,
        evidence=JudgmentEvidence(
            goals=("g",),
            constraints=("c",),
            alternatives=("a", "b"),
            trade_offs=("t",),
            evidence=("e",),
            falsifier="f",
            provenance=EvidenceProvenance.AI_REFORMULATED,
        ),
        cue_level=CueLevel.NONE,
        transfer_distance=TransferDistance.FAR_TRANSFER,
    )
    assert result.classification is AssessmentClassification.EXPOSURE_ONLY
    assert result.recommended_level is MasteryLevel.L1


def test_contradictory_weaker_evidence_requires_explicit_reassessment():
    result = assess_judgment(
        current_level=MasteryLevel.L3,
        user_attempted=True,
        ai_explanation_only=False,
        evidence=JudgmentEvidence(),
        contradicts_prior=True,
    )
    assert result.classification is AssessmentClassification.REASSESSMENT_REQUIRED
    assert result.requires_reassessment
    assert result.recommended_level is MasteryLevel.L3


def learning_event(event_id, level, observed_at, *, silent=False, concept="single owner"):
    return {
        "schema": "repolearn.learning_event.v1",
        "event_id": event_id,
        "observed_at": observed_at,
        "profile_id": "james",
        "context": {
            "repository": "example/repo",
            "activation_source": "explicit_invocation",
        },
        "capability": {
            "domain": "authority-boundaries",
            "concept": concept,
        },
        "attempt": {
            "judgment": "bounded fixture",
            "cue_level": "NONE" if silent else "LIGHT",
            "transfer_distance": "NEAR_TRANSFER",
            "evidence_timing": "PRE_EVIDENCE",
            "evidence_provenance": "USER_AUTHORED",
            "independence": "INDEPENDENT" if silent else "GUIDED",
            "delay_hours": 24 if silent else 0,
            "silent_cue_fading_eligible": silent,
        },
        "assessment": {
            "classification": "TRANSFER_WITH_TRADEOFFS" if silent else "EXPLAINED_WITH_EVIDENCE",
            "recommended_level": level,
            "rationale": "bounded fixture",
            "requires_reassessment": False,
        },
    }


def test_local_projection_carries_concept_cue_fading_state(tmp_path):
    backend = LocalFileBackend(tmp_path)
    backend.append_learning_event(
        "james",
        learning_event("ev-0", "L2", "2026-09-17T00:00:00Z", silent=False),
    )
    backend.append_learning_event(
        "james",
        learning_event("ev-1", "L3", "2026-09-18T00:00:00Z", silent=True),
    )
    state = backend.refresh_projection("james")
    concept = state["concepts"]["single owner"]
    assert concept["level"] == "L3"
    assert concept["last_cue_level"] == "NONE"
    assert concept["silent_cue_fading_eligible"] is True


def test_reassessment_resolution_recovers_previously_conflicted_projection(tmp_path):
    backend = LocalFileBackend(tmp_path)
    backend.append_learning_event(
        "james",
        learning_event("ev-1", "L3", "2026-09-15T00:00:00Z"),
    )
    backend.refresh_projection("james")
    backend.append_learning_event(
        "james",
        learning_event("ev-2", "L2", "2026-09-16T00:00:00Z"),
    )

    with pytest.raises(ProjectionConflictError):
        backend.refresh_projection("james")

    recovered = backend.resolve_reassessment(
        "james",
        conflict_event_id="ev-2",
        resolution_event=learning_event(
            "ev-3",
            "L2",
            "2026-09-17T00:00:00Z",
        ),
    )
    assert recovered["domains"]["authority-boundaries"]["level"] == "L2"
    assert backend.read_current_state("james") == recovered


def test_reassessment_resolution_cannot_cross_concept_boundary(tmp_path):
    backend = LocalFileBackend(tmp_path)
    backend.append_learning_event(
        "james",
        learning_event("ev-1", "L3", "2026-09-15T00:00:00Z"),
    )
    backend.refresh_projection("james")
    backend.append_learning_event(
        "james",
        learning_event("ev-2", "L2", "2026-09-16T00:00:00Z"),
    )

    before = backend.read_related_history("james")
    with pytest.raises(ProjectionConflictError, match="domain/concept"):
        backend.resolve_reassessment(
            "james",
            conflict_event_id="ev-2",
            resolution_event=learning_event(
                "ev-3",
                "L2",
                "2026-09-17T00:00:00Z",
                concept="different concept",
            ),
        )
    assert backend.read_related_history("james") == before


def test_invalid_reassessment_is_rejected_before_ledger_append(tmp_path):
    backend = LocalFileBackend(tmp_path)
    backend.append_learning_event(
        "james",
        learning_event("ev-1", "L3", "2026-09-15T00:00:00Z"),
    )
    backend.refresh_projection("james")
    backend.append_learning_event(
        "james",
        learning_event("ev-2", "L2", "2026-09-16T00:00:00Z"),
    )
    before = backend.read_related_history("james")
    invalid = learning_event("ev-3", "L2", "2026-09-17T00:00:00Z")
    invalid["assessment"]["recommended_level"] = "BROKEN"

    with pytest.raises(ValueError, match="valid recommended_level"):
        backend.resolve_reassessment(
            "james",
            conflict_event_id="ev-2",
            resolution_event=invalid,
        )
    assert backend.read_related_history("james") == before


def test_interaction_observation_schema_accepts_bounded_receipt():
    schema = json.loads(
        (Path(__file__).resolve().parents[1] / "schemas" / "interaction-observation.v1.json").read_text()
    )
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    validator.validate(
        {
            "schema": "repolearn.interaction_observation.v1",
            "task_id": "task-1",
            "activation_source": "explicit_invocation",
            "trigger_selected": True,
            "selected_branch": "JUDGMENT_PROMPT",
            "spontaneous_judgment_present": False,
            "branch_selection_valid": True,
            "prompt_generated": True,
            "prompt_answerable_without_repo_vocabulary": True,
            "terminology_clarification_required": False,
            "prompt_visible_in_final_response": True,
            "prompt_before_decisive_evidence": True,
            "answer_revealing_progress_before_prompt": False,
            "response_present": False,
            "response_relevance": "UNKNOWN",
            "engineering_blocked": False,
            "interaction_defect": "NONE",
            "interaction_defects": [],
            "cue_fading_suppressed": False,
            "contract_revision": "g5-runtime-evidence-v1",
            "contract_content_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "trace_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "evaluation_source": "SELF_REPORTED",
            "evaluator_id": None,
            "natural_task": True,
            "added_turns": 0,
            "added_time_ms_estimate": None,
            "added_context_tokens_estimate": None,
            "user_language": "en",
            "language_alignment_valid": True,
            "cue_level": "LIGHT",
            "transfer_distance": "SAME_STRUCTURE",
        }
    )
