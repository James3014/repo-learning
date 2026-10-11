from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from repolearn import (
    ActivationSource,
    CONTRACT_CONTENT_SHA256,
    CONTRACT_REVISION,
    GuidedBranch,
    InteractionDefect,
    InteractionMode,
    InteractionObservationReceipt,
    ResponseRelevance,
    TaskContext,
    TriggerDisposition,
    prepare_learning_decision,
    select_learning_opportunity,
)

from test_issue_46_spontaneous_capture import POLICY, SKILL, capture_contract_violations

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas/interaction-observation.v1.json").read_text())
CASES = json.loads((ROOT / "tests/fixtures/guided_branch_cases.json").read_text())["cases"]


class StaticBackend:
    def read_current_state(self, profile_id: str):
        return None


# --- contradiction and wording ----------------------------------------------


def test_boundary_no_longer_forbids_capturing_risk_pointing_questions():
    assert "Treating problem framing, questions," not in SKILL
    assert "neutral information questions, uncertainty, or option enumeration as spontaneous judgment" in SKILL
    assert "a risk-pointing question is a judgment; see step 8" in SKILL


@pytest.mark.parametrize("text", [SKILL, POLICY], ids=["skill", "policy"])
def test_per_task_cap_and_answered_prompt_feedback_are_defined(text):
    assert "At most one learning interaction per task, across all concepts." in text
    assert "Feedback on the user's answer to an emitted `JUDGMENT_PROMPT` is part of that same interaction, not a second one." in text
    assert "at most one short plain-language exposure note that asks nothing" in text


# Mutations from the independent review of #47: each changed meaning while all
# 248 tests stayed green after a fingerprint refresh.
REVIEW_MUTATIONS = {
    "capture-waits-for-user": (
        "The capture contains no learning question and never waits for or invites a user reply before engineering continues.",
        "The capture contains no learning question and never waits for or invites a user reply before engineering continues. "
        "Close the capture by inviting the user to explain in their own words how that boundary would apply here, and wait for that before continuing.",
    ),
    "every-why-question-is-risk": (
        "A neutral information question",
        "Any question that starts with why or how counts as a risk-pointing question. A neutral information question",
    ),
    "capture-becomes-lecture": (
        "in at most about five sentences",
        "in as many paragraphs as needed for a complete tutorial",
    ),
    "post-reveal-agreement-credited": (
        "agreement with or paraphrase of an answer already revealed is never spontaneous judgment",
        "agreement with or paraphrase of an answer already revealed is never spontaneous judgment, "
        "although a user's later agreement in their own words still counts toward mastery",
    ),
}


@pytest.mark.parametrize("text", [SKILL, POLICY], ids=["skill", "policy"])
@pytest.mark.parametrize("name", sorted(REVIEW_MUTATIONS))
def test_review_mutations_are_each_caught(text, name):
    old, new = REVIEW_MUTATIONS[name]
    assert old in text
    mutated = text.replace(old, new, 1)
    assert capture_contract_violations(mutated), name


# --- per-task cap ------------------------------------------------------------


def test_second_concept_in_same_task_is_not_selected():
    result = select_learning_opportunity(
        context=TaskContext(),
        mode=InteractionMode.GUIDED,
        candidate_concepts=["authority boundary", "runtime convergence"],
        already_handled_concepts=["authority boundary"],
        learning_interactions_in_task=1,
    )
    assert result.disposition is TriggerDisposition.NO_TRIGGER
    assert result.reason == "task_learning_interaction_used"


def test_negative_task_interaction_count_is_rejected():
    with pytest.raises(ValueError):
        select_learning_opportunity(
            context=TaskContext(),
            mode=InteractionMode.GUIDED,
            candidate_concepts=["authority boundary"],
            learning_interactions_in_task=-1,
        )


def test_already_handled_concept_matching_ignores_case():
    result = select_learning_opportunity(
        context=TaskContext(),
        mode=InteractionMode.GUIDED,
        candidate_concepts=["Authority Boundary"],
        already_handled_concepts=["authority boundary"],
    )
    assert result.disposition is TriggerDisposition.NO_TRIGGER
    assert result.reason == "already_handled_in_session"


def test_client_applies_per_task_cap_without_blocking_engineering():
    decision = prepare_learning_decision(
        backend=StaticBackend(),
        profile_id="james",
        context=TaskContext(),
        mode=InteractionMode.GUIDED,
        candidate_concepts=["runtime convergence"],
        learning_interactions_in_task=1,
    )
    assert decision.guided_branch is None
    assert decision.engineering_may_continue


def test_first_interaction_in_task_still_selected():
    result = select_learning_opportunity(
        context=TaskContext(),
        mode=InteractionMode.GUIDED,
        candidate_concepts=["authority boundary"],
    )
    assert result.disposition is TriggerDisposition.LEARNING_OPPORTUNITY


# --- receipts ----------------------------------------------------------------


def receipt(**changes) -> InteractionObservationReceipt:
    values = {
        "task_id": "task-48",
        "activation_source": ActivationSource.REPOSITORY_POINTER,
        "trigger_selected": True,
        "selected_branch": GuidedBranch.EXPOSURE_ONLY,
        "spontaneous_judgment_present": False,
        "branch_selection_valid": True,
        "prompt_generated": False,
        "prompt_answerable_without_repo_vocabulary": None,
        "terminology_clarification_required": None,
        "prompt_visible_in_final_response": None,
        "prompt_before_decisive_evidence": None,
        "answer_revealing_progress_before_prompt": False,
        "response_present": False,
        "response_relevance": ResponseRelevance.UNKNOWN,
        "engineering_blocked": False,
        "contract_revision": CONTRACT_REVISION,
        "contract_content_sha256": CONTRACT_CONTENT_SHA256,
    }
    values.update(changes)
    return InteractionObservationReceipt(**values)


def test_evidence_revealed_exposure_only_receipt_is_valid():
    observed = receipt(decisive_evidence_before_user_judgment=True)
    assert observed.branch_selection_valid is True
    assert observed.interaction_defects == ()


def test_prompt_after_evidence_revealed_is_branch_defect():
    observed = receipt(
        selected_branch=GuidedBranch.JUDGMENT_PROMPT,
        decisive_evidence_before_user_judgment=True,
        prompt_generated=True,
        prompt_answerable_without_repo_vocabulary=True,
        terminology_clarification_required=False,
        prompt_visible_in_final_response=True,
        prompt_before_decisive_evidence=True,
    )
    assert InteractionDefect.GUIDED_BRANCH_SELECTION_DEFECT in observed.interaction_defects


def test_second_interaction_in_task_is_repeated_defect():
    observed = receipt(decisive_evidence_before_user_judgment=True, prior_learning_interactions_in_task=1)
    assert InteractionDefect.REPEATED_LEARNING_INTERACTION_DEFECT in observed.interaction_defects


def test_negative_prior_interaction_count_is_rejected():
    with pytest.raises(ValueError):
        receipt(prior_learning_interactions_in_task=-1)


def test_new_receipt_fields_validate_against_schema():
    payload = receipt(
        decisive_evidence_before_user_judgment=True,
        prior_learning_interactions_in_task=2,
    ).to_dict()
    payload["trace_sha256"] = "b" * 64
    Draft202012Validator(SCHEMA, format_checker=FormatChecker()).validate(payload)


# --- fixture -----------------------------------------------------------------


def test_fixture_has_no_urgent_case_labelled_as_learning_branch():
    for case in CASES:
        message = case["user_message"].lower()
        assert "production is down" not in message
        assert "urgent" not in message
