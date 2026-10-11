from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

from repolearn import (
    ActivationSource,
    CONTRACT_CONTENT_SHA256,
    CONTRACT_REVISION,
    GuidedBranch,
    InteractionDefect,
    InteractionMode,
    InteractionObservationReceipt,
    ResponseRelevance,
    SpontaneousCaptureObservation,
    TaskContext,
    TriggerDisposition,
    UserJudgmentSignal,
    prepare_learning_decision,
    select_guided_branch,
    select_learning_opportunity,
)

ROOT = Path(__file__).resolve().parents[1]
SKILL = (ROOT / "skills/repo-learning/SKILL.md").read_text()
POLICY = (ROOT / "skills/repo-learning/references/policy.md").read_text()
CASES = json.loads((ROOT / "tests/fixtures/guided_branch_cases.json").read_text())["cases"]
SCHEMA = json.loads((ROOT / "schemas/interaction-observation.v1.json").read_text())


class StaticBackend:
    def __init__(self, state):
        self.state = state

    def read_current_state(self, profile_id: str):
        return self.state


# --- labelled branch oracle -------------------------------------------------


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_labelled_branch_cases(case):
    signal = UserJudgmentSignal(**case["signal"])
    branch = select_guided_branch(
        signal,
        response_opportunity_available=case.get("response_opportunity_available", True),
    )
    assert branch.value == case["expected_branch"]


def test_issue_13_plain_language_questions_are_captured_not_requizzed():
    examples = [case for case in CASES if case["issue_13_example"]]
    assert len(examples) == 5
    for case in examples:
        assert case["signal"].get("question_only") is not True
        assert case["expected_branch"] == "SPONTANEOUS_JUDGMENT_CAPTURE"


def test_neutral_question_does_not_become_capture():
    assert select_guided_branch(UserJudgmentSignal(question_only=True)) is GuidedBranch.JUDGMENT_PROMPT


def test_decisive_evidence_without_prior_judgment_is_exposure_not_prompt():
    for signal in (
        UserJudgmentSignal(decisive_evidence_already_revealed=True),
        UserJudgmentSignal(explicit_position=True, decisive_evidence_already_revealed=True),
        UserJudgmentSignal(risk_pointing_question=True, pre_feedback=False),
    ):
        assert select_guided_branch(signal) is GuidedBranch.EXPOSURE_ONLY


# --- contract wording guards ------------------------------------------------


def _capture_branch_text(text: str) -> str:
    match = re.search(r"- `SPONTANEOUS_JUDGMENT_CAPTURE`: (.+)", text)
    assert match, "capture branch missing"
    return match.group(1)


def capture_contract_violations(text: str) -> list[str]:
    branch = _capture_branch_text(text)
    violations: list[str] = []
    tie_breaker = re.search(r"When uncertain whether a real judgment exists, use `(\w+)`", branch)
    if not tie_breaker or tie_breaker.group(1) != "JUDGMENT_PROMPT":
        violations.append("ambiguity must resolve to JUDGMENT_PROMPT")
    required = (
        "build that one question on the user's own point",
        "A risk-pointing question counts as an architecture-risk judgment",
        "A neutral information question",
        "Timing is relative to the user's statement",
        "agreement with or paraphrase of an answer already revealed is never spontaneous judgment",
        "Do not re-ask a qualifying judgment",
        "rather than mere agreement or praise",
        "extract one reusable principle in plain language",
        "state (not ask) one important applicability boundary or counterexample",
        "The capture contains no learning question",
        "before the bulk of the engineering output",
        "In the user's current language",
        "it is cued evidence, not spontaneous no-cue evidence",
        "in at most about five sentences",
        "never waits for or invites a user reply before engineering continues",
        "a why/how question that only asks how something works",
    )
    violations.extend(f"missing: {phrase}" for phrase in required if phrase not in branch)
    forbidden = (
        r"follow-up question",
        r"\bask the user\b",
        r"treat\w* the user's agreement",
        r"agreement[^.]*as (spontaneous|mastery|judgment) (judgment )?evidence",
        r"restate the principle",
        r"\bwait for (that|the user|their|a reply|an answer)",
        r"\binvit\w* the user to\b",
        r"\bparagraphs?\b",
        r"\btutorial\b",
        r"\b(any|every) question\b",
        r"\bstarts? with (why|how)\b",
        r"\blater agreement\b[^.]*\bcounts?\b",
        r"agreement[^.]*\bstill counts?\b",
    )
    violations.extend(
        f"forbidden: {pattern}" for pattern in forbidden if re.search(pattern, branch, re.IGNORECASE)
    )
    return violations


@pytest.mark.parametrize("text", [SKILL, POLICY], ids=["skill", "policy"])
def test_capture_branch_contract_has_no_violations(text):
    assert capture_contract_violations(text) == []


def test_review_counterexample_is_caught():
    mutated = SKILL.replace(
        "When uncertain whether a real judgment exists, use `JUDGMENT_PROMPT`",
        "When uncertain whether a real judgment exists, use `SPONTANEOUS_JUDGMENT_CAPTURE`",
    ).replace(
        "never waits for or invites a user reply before engineering continues.",
        "never waits for or invites a user reply before engineering continues. Before continuing, ask the user one follow-up "
        "question checking whether they can restate the principle, and treat the user's agreement "
        "with your explanation as spontaneous judgment evidence.",
    )
    assert mutated != SKILL
    violations = capture_contract_violations(mutated)
    assert "ambiguity must resolve to JUDGMENT_PROMPT" in violations
    assert any(item.startswith("forbidden:") for item in violations)


@pytest.mark.parametrize("text", [SKILL, POLICY], ids=["skill", "policy"])
def test_repetition_is_a_bounded_hard_suppressor(text):
    assert "already given for this concept earlier in the same task or session" in text
    assert "At most one learning interaction per task, across all concepts." in text


@pytest.mark.parametrize("text", [SKILL, POLICY], ids=["skill", "policy"])
def test_exposure_only_covers_answer_already_revealed(text):
    assert "decisive evidence for the selected point was already revealed before any user judgment on it" in text


def test_capture_defect_classes_are_named_in_contract():
    for phrase in ("re-quiz defect", "capture-quality defect", "cue-attribution defect", "repeated-interaction defect"):
        assert phrase in SKILL
        assert phrase in POLICY


# --- executable capture-quality observation ---------------------------------

GOOD_CAPTURE = {
    "capture_user_judgment_identified": True,
    "capture_reasoning_feedback_specific": True,
    "capture_principle_plain_language": True,
    "capture_boundary_stated": True,
    "capture_learning_question_asked": False,
    "capture_before_bulk_engineering_output": True,
}


def capture_receipt(**changes) -> InteractionObservationReceipt:
    values = {
        "task_id": "task-46",
        "activation_source": ActivationSource.REPOSITORY_POINTER,
        "trigger_selected": True,
        "selected_branch": GuidedBranch.SPONTANEOUS_JUDGMENT_CAPTURE,
        "spontaneous_judgment_present": True,
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
        "cue_level": "NONE",
        **GOOD_CAPTURE,
    }
    values.update(changes)
    return InteractionObservationReceipt(**values)


def test_complete_capture_has_no_defects():
    assert capture_receipt().interaction_defects == ()


def test_praise_only_capture_is_quality_defect():
    observed = capture_receipt(
        capture_reasoning_feedback_specific=False,
        capture_principle_plain_language=False,
        capture_boundary_stated=False,
    )
    assert observed.interaction_defects == (InteractionDefect.SPONTANEOUS_CAPTURE_QUALITY_DEFECT,)


def test_capture_after_bulk_engineering_output_is_quality_defect():
    observed = capture_receipt(capture_before_bulk_engineering_output=False)
    assert InteractionDefect.SPONTANEOUS_CAPTURE_QUALITY_DEFECT in observed.interaction_defects


def test_capture_that_asks_a_learning_question_is_requiz_defect():
    observed = capture_receipt(capture_learning_question_asked=True)
    assert observed.interaction_defects == (InteractionDefect.SPONTANEOUS_CAPTURE_REQUIZ_DEFECT,)


def test_unobserved_capture_shape_is_not_silently_green():
    observed = capture_receipt(**{key: None for key in GOOD_CAPTURE})
    assert InteractionDefect.SPONTANEOUS_CAPTURE_QUALITY_DEFECT in observed.interaction_defects
    assert InteractionDefect.SPONTANEOUS_CAPTURE_REQUIZ_DEFECT in observed.interaction_defects


def test_capture_observation_is_usable_standalone():
    observation = SpontaneousCaptureObservation(True, True, True, True, False, True)
    assert observation.defects == ()


def test_ai_cued_judgment_cannot_be_recorded_as_no_cue():
    cued = capture_receipt(risk_first_raised_by_ai=True, cue_level="NONE")
    assert InteractionDefect.CUE_ATTRIBUTION_DEFECT in cued.interaction_defects
    assert capture_receipt(risk_first_raised_by_ai=True, cue_level="LIGHT").interaction_defects == ()


def test_repeated_concept_interaction_is_defect():
    observed = capture_receipt(repeated_concept_in_session=True)
    assert InteractionDefect.REPEATED_LEARNING_INTERACTION_DEFECT in observed.interaction_defects


def test_capture_quality_fields_do_not_affect_prompt_branch():
    observed = capture_receipt(
        selected_branch=GuidedBranch.JUDGMENT_PROMPT,
        spontaneous_judgment_present=False,
        prompt_generated=True,
        prompt_answerable_without_repo_vocabulary=True,
        terminology_clarification_required=False,
        prompt_visible_in_final_response=True,
        prompt_before_decisive_evidence=True,
        **{key: None for key in GOOD_CAPTURE},
    )
    assert observed.interaction_defects == ()


# --- trigger / client wiring ------------------------------------------------


def test_concept_already_handled_in_session_is_not_selected_again():
    result = select_learning_opportunity(
        context=TaskContext(),
        mode=InteractionMode.GUIDED,
        candidate_concepts=["authority boundary"],
        already_handled_concepts=["authority boundary"],
    )
    assert result.disposition is TriggerDisposition.NO_TRIGGER
    assert result.reason == "already_handled_in_session"


def test_client_passes_response_opportunity_to_branch_selection():
    decision = prepare_learning_decision(
        backend=StaticBackend(None),
        profile_id="james",
        context=TaskContext(),
        mode=InteractionMode.GUIDED,
        candidate_concepts=["runtime convergence"],
        response_opportunity_available=False,
    )
    assert decision.guided_branch is GuidedBranch.EXPOSURE_ONLY
    assert decision.engineering_may_continue


def test_client_skips_concept_already_handled_in_session():
    decision = prepare_learning_decision(
        backend=StaticBackend(None),
        profile_id="james",
        context=TaskContext(),
        mode=InteractionMode.GUIDED,
        candidate_concepts=["runtime convergence"],
        already_handled_concepts=["runtime convergence"],
    )
    assert decision.trigger.disposition is TriggerDisposition.NO_TRIGGER
    assert decision.guided_branch is None
    assert decision.engineering_may_continue


# --- schema -----------------------------------------------------------------


def _validator() -> Draft202012Validator:
    Draft202012Validator.check_schema(SCHEMA)
    return Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def _with_trace(receipt: InteractionObservationReceipt) -> dict[str, object]:
    payload = receipt.to_dict()
    payload["trace_sha256"] = "b" * 64
    return payload


@pytest.mark.parametrize(
    "receipt",
    [
        capture_receipt(),
        capture_receipt(capture_learning_question_asked=True, repeated_concept_in_session=True),
        capture_receipt(
            selected_branch=GuidedBranch.EXPOSURE_ONLY,
            spontaneous_judgment_present=False,
            response_opportunity_before_reveal=False,
        ),
        capture_receipt(
            selected_branch=GuidedBranch.JUDGMENT_PROMPT,
            spontaneous_judgment_present=False,
            prompt_generated=True,
            prompt_answerable_without_repo_vocabulary=True,
            terminology_clarification_required=False,
            prompt_visible_in_final_response=True,
            prompt_before_decisive_evidence=True,
            answer_revealed_in_same_assistant_turn=True,
        ),
    ],
    ids=["capture", "capture-defects", "exposure-only", "prompt-no-response-opportunity"],
)
def test_receipt_to_dict_validates_against_schema(receipt):
    _validator().validate(_with_trace(receipt))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("selected_branch", "QUIZ_AGAIN"),
        ("interaction_defect", "MADE_UP_DEFECT"),
        ("interaction_defects", ["MADE_UP_DEFECT"]),
        ("capture_learning_question_asked", "no"),
        ("repeated_concept_in_session", None),
        ("capture_transcript", "raw text"),
    ],
)
def test_schema_rejects_invalid_capture_receipts(field, value):
    payload = _with_trace(capture_receipt())
    payload[field] = value
    with pytest.raises(ValidationError):
        _validator().validate(payload)
