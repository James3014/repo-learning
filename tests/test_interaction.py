from __future__ import annotations

import pytest

from repolearn import (
    ActivationSource,
    GuidedBranch,
    InteractionDefect,
    InteractionObservationReceipt,
    PromptDeliveryObservation,
    ResponseRelevance,
    UserJudgmentSignal,
    select_guided_branch,
)


@pytest.mark.parametrize(
    "signal",
    [
        UserJudgmentSignal(problem_framing_only=True),
        UserJudgmentSignal(option_enumeration_only=True),
        UserJudgmentSignal(question_only=True),
        UserJudgmentSignal(uncertainty_only=True),
        UserJudgmentSignal(),
    ],
)
def test_problem_framing_and_uncertainty_do_not_count_as_spontaneous_judgment(signal):
    assert select_guided_branch(signal) is GuidedBranch.JUDGMENT_PROMPT


@pytest.mark.parametrize(
    "signal",
    [
        UserJudgmentSignal(explicit_position=True),
        UserJudgmentSignal(explicit_prediction=True),
        UserJudgmentSignal(explicit_risk_judgment=True),
        UserJudgmentSignal(explicit_position=True, rationale_expressed=True),
    ],
)
def test_explicit_pre_feedback_directional_judgment_uses_spontaneous_capture(signal):
    assert select_guided_branch(signal) is GuidedBranch.SPONTANEOUS_JUDGMENT_CAPTURE


def test_post_evidence_position_does_not_count_as_spontaneous_judgment():
    signal = UserJudgmentSignal(
        explicit_position=True,
        decisive_evidence_already_revealed=True,
    )
    assert select_guided_branch(signal) is GuidedBranch.JUDGMENT_PROMPT


@pytest.mark.parametrize(
    ("observation", "expected"),
    [
        (
            PromptDeliveryObservation(False, None, None, None, None),
            InteractionDefect.PROMPT_VISIBILITY_DEFECT,
        ),
        (
            PromptDeliveryObservation(True, False, True, True, True),
            InteractionDefect.PROMPT_COMPREHENSION_DEFECT,
        ),
        (
            PromptDeliveryObservation(True, True, False, False, True),
            InteractionDefect.PROMPT_VISIBILITY_DEFECT,
        ),
        (
            PromptDeliveryObservation(True, True, False, True, False),
            InteractionDefect.PRE_EVIDENCE_ORDERING_DEFECT,
        ),
        (
            PromptDeliveryObservation(True, True, False, True, True, True),
            InteractionDefect.PRE_EVIDENCE_ORDERING_DEFECT,
        ),
        (
            PromptDeliveryObservation(True, True, False, True, True),
            InteractionDefect.NONE,
        ),
    ],
)
def test_prompt_delivery_defects_are_executable(observation, expected):
    assert observation.defect is expected


def receipt(**changes) -> InteractionObservationReceipt:
    values = {
        "task_id": "task-1",
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
        "cue_fading_suppressed": False,
        "cue_level": "LIGHT",
        "transfer_distance": "SAME_STRUCTURE",
    }
    values.update(changes)
    return InteractionObservationReceipt(**values)


def test_false_spontaneous_branch_is_detected():
    observed = receipt(
        selected_branch=GuidedBranch.SPONTANEOUS_JUDGMENT_CAPTURE,
        spontaneous_judgment_present=False,
    )
    assert observed.interaction_defect is InteractionDefect.GUIDED_BRANCH_SELECTION_DEFECT


def test_missing_spontaneous_capture_is_detected_when_judgment_exists():
    observed = receipt(
        selected_branch=GuidedBranch.JUDGMENT_PROMPT,
        spontaneous_judgment_present=True,
    )
    assert observed.interaction_defect is InteractionDefect.GUIDED_BRANCH_SELECTION_DEFECT


def test_unknown_nonempty_response_is_observable_defect_not_mastery():
    observed = receipt(
        response_present=True,
        response_relevance=ResponseRelevance.UNKNOWN,
    )
    assert observed.interaction_defect is InteractionDefect.RESPONSE_RELEVANCE_DEFECT


def test_receipt_is_schema_ready_and_contains_no_prompt_or_transcript_text():
    payload = receipt().to_dict()
    assert payload["schema"] == "repolearn.interaction_observation.v1"
    assert payload["interaction_defect"] == "NONE"
    assert "prompt_text" not in payload
    assert "transcript" not in payload
    assert "source_excerpt" not in payload
