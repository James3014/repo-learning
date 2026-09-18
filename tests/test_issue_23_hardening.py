from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from repolearn import (
    ActivationSource,
    AttemptIndependence,
    CONTRACT_CONTENT_SHA256,
    CONTRACT_REVISION,
    EvaluationSource,
    GuidedBranch,
    InteractionDefect,
    InteractionMode,
    InteractionObservationReceipt,
    LocalFileBackend,
    ResponseRelevance,
    TaskContext,
    TriggerDisposition,
    compute_skill_content_sha256,
    derive_fading_decision,
    hash_user_visible_trace,
    prepare_learning_decision,
)


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "repo-learning"


def event(
    event_id: str,
    observed_at: str = "2026-09-18T00:00:00Z",
    *,
    independence: str = "GUIDED",
    delay_hours: float | None = 0,
    cue_level: str = "NONE",
    transfer_distance: str = "NEAR_TRANSFER",
    classification: str = "TRANSFER_WITH_TRADEOFFS",
    legacy_fade_flag: bool = False,
):
    return {
        "schema": "repolearn.learning_event.v1",
        "event_id": event_id,
        "observed_at": observed_at,
        "profile_id": "james",
        "context": {"repository": "example/repo"},
        "capability": {"domain": "authority", "concept": "single owner"},
        "attempt": {
            "judgment": "bounded fixture",
            "cue_level": cue_level,
            "transfer_distance": transfer_distance,
            "evidence_timing": "PRE_EVIDENCE",
            "evidence_provenance": "USER_AUTHORED",
            "independence": independence,
            "delay_hours": delay_hours,
            "silent_cue_fading_eligible": legacy_fade_flag,
        },
        "assessment": {
            "classification": classification,
            "recommended_level": "L3",
            "rationale": "bounded fixture",
        },
    }


def receipt(**changes) -> InteractionObservationReceipt:
    values = {
        "task_id": "task-23",
        "activation_source": ActivationSource.EXPLICIT_INVOCATION,
        "trigger_selected": True,
        "selected_branch": GuidedBranch.JUDGMENT_PROMPT,
        "spontaneous_judgment_present": False,
        "branch_selection_valid": True,
        "prompt_generated": True,
        "prompt_answerable_without_repo_vocabulary": True,
        "terminology_clarification_required": False,
        "prompt_visible_in_final_response": True,
        "prompt_before_decisive_evidence": True,
        "answer_revealing_progress_before_prompt": False,
        "response_present": False,
        "response_relevance": ResponseRelevance.UNKNOWN,
        "engineering_blocked": False,
        "contract_revision": CONTRACT_REVISION,
        "contract_content_sha256": CONTRACT_CONTENT_SHA256,
        "trace_sha256": "b" * 64,
        "evaluation_source": EvaluationSource.HUMAN,
        "evaluator_id": "reviewer-1",
        "natural_task": True,
        "added_turns": 1,
        "added_time_ms_estimate": 500,
        "added_context_tokens_estimate": 80,
        "user_language": "zh-TW",
        "language_alignment_valid": True,
    }
    values.update(changes)
    return InteractionObservationReceipt(**values)


def test_contract_manifest_matches_python_revision_and_skill_fingerprint():
    manifest = json.loads((SKILL_ROOT / "references" / "contract-manifest.json").read_text())
    assert manifest["contract_revision"] == CONTRACT_REVISION
    assert manifest["content_sha256"] == CONTRACT_CONTENT_SHA256
    assert manifest["content_sha256"] == compute_skill_content_sha256(SKILL_ROOT)


def test_trace_hash_binds_exact_visible_interaction_without_persisting_text():
    first = hash_user_visible_trace(
        user_message="TOP-SECRET-USER-TEXT",
        progress_messages=("checking source",),
        final_response="TOP-SECRET-FINAL-TEXT",
    )
    second = hash_user_visible_trace(
        user_message="TOP-SECRET-USER-TEXT",
        progress_messages=("checking source",),
        final_response="DIFFERENT-FINAL-TEXT",
    )
    assert len(first) == 64
    assert first != second
    payload = receipt(trace_sha256=first).to_dict()
    serialized = json.dumps(payload)
    assert "TOP-SECRET-USER-TEXT" not in serialized
    assert "TOP-SECRET-FINAL-TEXT" not in serialized


def test_self_reported_receipt_cannot_be_independent_g5_evidence():
    observed = receipt(
        evaluation_source=EvaluationSource.SELF_REPORTED,
        evaluator_id=None,
    )
    assert not observed.qualifies_for_independent_g5_evidence(
        expected_content_sha256=CONTRACT_CONTENT_SHA256
    )


def test_independent_receipt_requires_matching_loaded_contract():
    observed = receipt()
    assert observed.qualifies_for_independent_g5_evidence(
        expected_content_sha256="a" * 64
    )
    assert not observed.attestation_matches(
        expected_content_sha256="c" * 64
    )


def test_contract_content_hash_mismatch_or_missing_is_observable_defect():
    mismatched = receipt(contract_content_sha256="c" * 64)
    missing = receipt(contract_content_sha256=None)
    assert InteractionDefect.CONTRACT_ATTESTATION_DEFECT in mismatched.interaction_defects
    assert InteractionDefect.CONTRACT_ATTESTATION_DEFECT in missing.interaction_defects


def test_contract_revision_mismatch_is_observable_defect():
    observed = receipt(contract_revision="stale-contract")
    assert InteractionDefect.CONTRACT_ATTESTATION_DEFECT in observed.interaction_defects


def test_legacy_event_flag_cannot_self_authorize_fading(tmp_path):
    backend = LocalFileBackend(tmp_path)
    legacy = event(
        "ev-legacy",
        independence=AttemptIndependence.GUIDED.value,
        delay_hours=0,
        legacy_fade_flag=True,
    )
    assert not derive_fading_decision(legacy, previous_observed_at="2026-09-17T00:00:00Z").eligible
    backend.append_learning_event("james", legacy)
    state = backend.refresh_projection("james")
    concept = state["concepts"]["single owner"]
    assert concept["silent_cue_fading_eligible"] is False
    assert concept["fading_valid_until"] is None


def test_guided_same_session_success_cannot_suppress(tmp_path):
    backend = LocalFileBackend(tmp_path)
    guided = event(
        "ev-guided",
        independence=AttemptIndependence.GUIDED.value,
        delay_hours=0,
    )
    backend.append_learning_event("james", guided)
    state = backend.refresh_projection("james")
    assert state["concepts"]["single owner"]["fading_valid_until"] is None


def test_transfer_label_without_l3_or_l4_cannot_authorize_fading():
    weak = event(
        "ev-weak",
        independence=AttemptIndependence.INDEPENDENT.value,
        delay_hours=24,
    )
    weak["assessment"]["recommended_level"] = "L2"
    decision = derive_fading_decision(
        weak,
        previous_observed_at="2026-09-17T00:00:00Z",
    )
    assert not decision.eligible
    assert decision.reason == "insufficient_level"


def test_reassessment_or_ai_only_event_cannot_authorize_fading():
    reassessment = event(
        "ev-reassessment",
        independence=AttemptIndependence.INDEPENDENT.value,
        delay_hours=24,
    )
    reassessment["assessment"]["requires_reassessment"] = True
    assert (
        derive_fading_decision(
            reassessment,
            previous_observed_at="2026-09-17T00:00:00Z",
        ).reason
        == "reassessment_required"
    )

    resolver = event(
        "ev-resolver",
        independence=AttemptIndependence.INDEPENDENT.value,
        delay_hours=24,
    )
    resolver["assessment"]["reassessment_of_event_id"] = "ev-conflict"
    assert (
        derive_fading_decision(
            resolver,
            previous_observed_at="2026-09-17T00:00:00Z",
        ).reason
        == "reassessment_resolution_not_fresh_evidence"
    )

    ai_only = event(
        "ev-ai-only",
        independence=AttemptIndependence.INDEPENDENT.value,
        delay_hours=24,
    )
    ai_only["attempt"]["ai_explanation_only"] = True
    assert (
        derive_fading_decision(
            ai_only,
            previous_observed_at="2026-09-17T00:00:00Z",
        ).reason
        == "ai_explanation_only"
    )


def test_independent_llm_evaluator_must_differ_from_generator():
    with pytest.raises(ValueError, match="must differ"):
        receipt(
            evaluation_source=EvaluationSource.INDEPENDENT_LLM,
            generator_id="model-a",
            evaluator_id="model-a",
        )


def test_delayed_independent_transfer_derives_temporary_fading(tmp_path):
    backend = LocalFileBackend(tmp_path)
    independent = event(
        "ev-independent",
        independence=AttemptIndependence.INDEPENDENT.value,
        delay_hours=24,
    )
    decision = derive_fading_decision(
        independent,
        previous_observed_at="2026-09-17T00:00:00Z",
    )
    assert decision.eligible
    assert decision.basis_event_id == "ev-independent"
    assert decision.valid_until == "2026-10-18T00:00:00Z"
    backend.append_learning_event(
        "james",
        event(
            "ev-prior",
            observed_at="2026-09-17T00:00:00Z",
            independence=AttemptIndependence.GUIDED.value,
            delay_hours=0,
            cue_level="LIGHT",
            transfer_distance="SAME_STRUCTURE",
            classification="EXPLAINED_WITH_EVIDENCE",
        ),
    )
    backend.append_learning_event("james", independent)
    state = backend.refresh_projection("james")
    concept = state["concepts"]["single owner"]
    assert concept["silent_cue_fading_eligible"] is True
    assert concept["fading_basis_event_id"] == "ev-independent"
    assert concept["fading_valid_until"] == "2026-10-18T00:00:00Z"


def test_reported_delay_cannot_fake_same_session_fading(tmp_path):
    backend = LocalFileBackend(tmp_path)
    backend.append_learning_event(
        "james",
        event(
            "ev-prior",
            observed_at="2026-09-18T00:00:00Z",
            independence=AttemptIndependence.GUIDED.value,
            cue_level="LIGHT",
            transfer_distance="SAME_STRUCTURE",
            classification="EXPLAINED_WITH_EVIDENCE",
        ),
    )
    fake_delay = event(
        "ev-fake-delay",
        observed_at="2026-09-18T01:00:00Z",
        independence=AttemptIndependence.INDEPENDENT.value,
        delay_hours=999,
    )
    backend.append_learning_event("james", fake_delay)
    state = backend.refresh_projection("james")
    assert state["concepts"]["single owner"]["fading_valid_until"] is None


def test_reassessment_resolution_revokes_existing_fading(tmp_path):
    backend = LocalFileBackend(tmp_path)
    backend.append_learning_event(
        "james",
        event(
            "ev-prior",
            observed_at="2026-09-16T00:00:00Z",
            independence=AttemptIndependence.GUIDED.value,
            cue_level="LIGHT",
            transfer_distance="SAME_STRUCTURE",
            classification="EXPLAINED_WITH_EVIDENCE",
        ),
    )
    backend.append_learning_event(
        "james",
        event(
            "ev-independent",
            observed_at="2026-09-18T00:00:00Z",
            independence=AttemptIndependence.INDEPENDENT.value,
            delay_hours=48,
        ),
    )
    faded = backend.refresh_projection("james")
    assert faded["concepts"]["single owner"]["fading_valid_until"] is not None

    conflict = event(
        "ev-conflict",
        observed_at="2026-09-19T00:00:00Z",
        independence=AttemptIndependence.GUIDED.value,
        cue_level="HEAVY",
        transfer_distance="SAME_STRUCTURE",
        classification="USER_ATTEMPT",
    )
    conflict["assessment"]["recommended_level"] = "L2"
    backend.append_learning_event("james", conflict)

    resolution = event(
        "ev-resolution",
        observed_at="2026-09-20T00:00:00Z",
        independence=AttemptIndependence.GUIDED.value,
        cue_level="HEAVY",
        transfer_distance="SAME_STRUCTURE",
        classification="REASSESSMENT_REQUIRED",
    )
    resolution["assessment"]["recommended_level"] = "L2"
    recovered = backend.resolve_reassessment(
        "james",
        conflict_event_id="ev-conflict",
        resolution_event=resolution,
    )
    concept = recovered["concepts"]["single owner"]
    assert concept["level"] == "L2"
    assert concept["silent_cue_fading_eligible"] is False
    assert concept["fading_valid_until"] is None
    assert concept["fading_basis_event_id"] is None


def test_fading_expiry_reopens_natural_revalidation(tmp_path):
    backend = LocalFileBackend(tmp_path)
    backend.append_learning_event(
        "james",
        event(
            "ev-prior",
            observed_at="2026-09-16T00:00:00Z",
            independence=AttemptIndependence.GUIDED.value,
            delay_hours=0,
            cue_level="LIGHT",
            transfer_distance="SAME_STRUCTURE",
            classification="EXPLAINED_WITH_EVIDENCE",
        ),
    )
    backend.append_learning_event(
        "james",
        event(
            "ev-independent",
            independence=AttemptIndependence.INDEPENDENT.value,
            delay_hours=48,
        ),
    )
    backend.refresh_projection("james")
    before_expiry = prepare_learning_decision(
        backend=backend,
        profile_id="james",
        context=TaskContext(),
        mode=InteractionMode.GUIDED,
        candidate_concepts=["single owner"],
        now=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )
    after_expiry = prepare_learning_decision(
        backend=backend,
        profile_id="james",
        context=TaskContext(),
        mode=InteractionMode.GUIDED,
        candidate_concepts=["single owner"],
        now=datetime(2026, 10, 19, tzinfo=timezone.utc),
    )
    assert before_expiry.trigger.disposition is TriggerDisposition.NO_TRIGGER
    assert before_expiry.trigger.reason == "cue_faded"
    assert after_expiry.trigger.disposition is TriggerDisposition.LEARNING_OPPORTUNITY


def test_multiple_interaction_defects_are_preserved():
    observed = receipt(
        prompt_answerable_without_repo_vocabulary=False,
        prompt_visible_in_final_response=False,
        prompt_before_decisive_evidence=False,
        answer_revealing_progress_before_prompt=True,
        response_present=True,
        response_relevance=ResponseRelevance.UNKNOWN,
        engineering_blocked=True,
        language_alignment_valid=False,
    )
    defects = set(observed.interaction_defects)
    assert InteractionDefect.ENGINEERING_BLOCKING_DEFECT in defects
    assert InteractionDefect.PROMPT_VISIBILITY_DEFECT in defects
    assert InteractionDefect.PROMPT_COMPREHENSION_DEFECT in defects
    assert InteractionDefect.PRE_EVIDENCE_ORDERING_DEFECT in defects
    assert InteractionDefect.LANGUAGE_ALIGNMENT_DEFECT in defects
    assert InteractionDefect.RESPONSE_RELEVANCE_DEFECT in defects
    assert observed.interaction_defect in defects


def test_cost_and_language_fields_are_privacy_safe_and_schema_ready():
    payload = receipt().to_dict()
    assert payload["natural_task"] is True
    assert payload["added_turns"] == 1
    assert payload["added_time_ms_estimate"] == 500
    assert payload["added_context_tokens_estimate"] == 80
    assert payload["user_language"] == "zh-TW"
    assert payload["language_alignment_valid"] is True
    assert payload["interaction_defects"] == []


def test_negative_cost_estimates_are_rejected():
    with pytest.raises(ValueError, match="added_turns"):
        receipt(added_turns=-1)


def test_skill_contract_requires_current_user_language():
    skill = (SKILL_ROOT / "SKILL.md").read_text()
    assert "Use the user's current language for the plain-language question" in skill
    assert "preserve exact repository identifiers unchanged" in skill
