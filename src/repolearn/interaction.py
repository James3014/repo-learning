"""Executable human-learning interaction contracts.

These primitives make RepoLearn's guided branch, response relevance, and
privacy-safe dogfood observations explicit without taking engineering authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .triggers import ActivationSource


class GuidedBranch(str, Enum):
    JUDGMENT_PROMPT = "JUDGMENT_PROMPT"
    SPONTANEOUS_JUDGMENT_CAPTURE = "SPONTANEOUS_JUDGMENT_CAPTURE"


@dataclass(frozen=True)
class UserJudgmentSignal:
    """Bounded pre-feedback signal used to choose the guided branch.

    Callers should set explicit_position / explicit_prediction /
    explicit_risk_judgment only for an actual directional user judgment.
    Problem framing, option enumeration, questions, and uncertainty alone do not
    satisfy this contract.
    """

    explicit_position: bool = False
    explicit_prediction: bool = False
    explicit_risk_judgment: bool = False
    rationale_expressed: bool = False
    problem_framing_only: bool = False
    option_enumeration_only: bool = False
    question_only: bool = False
    uncertainty_only: bool = False
    pre_feedback: bool = True
    decisive_evidence_already_revealed: bool = False

    @property
    def meaningful_pre_evidence_judgment(self) -> bool:
        if not self.pre_feedback or self.decisive_evidence_already_revealed:
            return False
        return self.explicit_position or self.explicit_prediction or self.explicit_risk_judgment


def select_guided_branch(signal: UserJudgmentSignal) -> GuidedBranch:
    """Choose the safe guided branch.

    Uncertainty resolves to JUDGMENT_PROMPT rather than inventing user mastery.
    """

    if signal.meaningful_pre_evidence_judgment:
        return GuidedBranch.SPONTANEOUS_JUDGMENT_CAPTURE
    return GuidedBranch.JUDGMENT_PROMPT


class ResponseRelevance(str, Enum):
    PROMPT_ANSWER = "PROMPT_ANSWER"
    UNRELATED_ENGINEERING = "UNRELATED_ENGINEERING"
    EXPLICIT_SKIP = "EXPLICIT_SKIP"
    UNKNOWN = "UNKNOWN"


class InteractionDefect(str, Enum):
    NONE = "NONE"
    GUIDED_BRANCH_SELECTION_DEFECT = "GUIDED_BRANCH_SELECTION_DEFECT"
    PROMPT_COMPREHENSION_DEFECT = "PROMPT_COMPREHENSION_DEFECT"
    PROMPT_VISIBILITY_DEFECT = "PROMPT_VISIBILITY_DEFECT"
    PRE_EVIDENCE_ORDERING_DEFECT = "PRE_EVIDENCE_ORDERING_DEFECT"
    RESPONSE_RELEVANCE_DEFECT = "RESPONSE_RELEVANCE_DEFECT"
    ENGINEERING_BLOCKING_DEFECT = "ENGINEERING_BLOCKING_DEFECT"


@dataclass(frozen=True)
class PromptDeliveryObservation:
    prompt_generated: bool
    prompt_answerable_without_repo_vocabulary: bool | None
    terminology_clarification_required: bool | None
    prompt_visible_in_final_response: bool | None
    prompt_before_decisive_evidence: bool | None
    answer_revealing_progress_before_prompt: bool = False

    @property
    def defect(self) -> InteractionDefect:
        if not self.prompt_generated or self.prompt_visible_in_final_response is not True:
            return InteractionDefect.PROMPT_VISIBILITY_DEFECT
        if self.prompt_answerable_without_repo_vocabulary is not True:
            return InteractionDefect.PROMPT_COMPREHENSION_DEFECT
        if self.prompt_before_decisive_evidence is not True or self.answer_revealing_progress_before_prompt:
            return InteractionDefect.PRE_EVIDENCE_ORDERING_DEFECT
        return InteractionDefect.NONE


@dataclass(frozen=True)
class InteractionObservationReceipt:
    """Privacy-safe G5/G6 interaction receipt.

    Intentionally stores classifications and booleans, not prompt text,
    transcripts, source excerpts, secrets, or private repository payloads.
    """

    task_id: str
    activation_source: ActivationSource
    trigger_selected: bool
    selected_branch: GuidedBranch | None
    spontaneous_judgment_present: bool
    branch_selection_valid: bool
    prompt_generated: bool
    prompt_answerable_without_repo_vocabulary: bool | None
    terminology_clarification_required: bool | None
    prompt_visible_in_final_response: bool | None
    prompt_before_decisive_evidence: bool | None
    answer_revealing_progress_before_prompt: bool
    response_present: bool
    response_relevance: ResponseRelevance
    engineering_blocked: bool
    cue_fading_suppressed: bool = False
    cue_level: str | None = None
    transfer_distance: str | None = None

    def __post_init__(self) -> None:
        if not self.task_id.strip():
            raise ValueError("task_id must be non-empty")
        if not self.trigger_selected and self.selected_branch is not None:
            raise ValueError("no-trigger receipt cannot select a guided branch")
        if self.trigger_selected and self.selected_branch is not None:
            expected_branch = (
                GuidedBranch.SPONTANEOUS_JUDGMENT_CAPTURE
                if self.spontaneous_judgment_present
                else GuidedBranch.JUDGMENT_PROMPT
            )
            if self.selected_branch is not expected_branch:
                object.__setattr__(self, "branch_selection_valid", False)

    @property
    def interaction_defect(self) -> InteractionDefect:
        if self.engineering_blocked:
            return InteractionDefect.ENGINEERING_BLOCKING_DEFECT
        if not self.branch_selection_valid:
            return InteractionDefect.GUIDED_BRANCH_SELECTION_DEFECT
        if self.selected_branch is GuidedBranch.JUDGMENT_PROMPT:
            prompt_defect = PromptDeliveryObservation(
                prompt_generated=self.prompt_generated,
                prompt_answerable_without_repo_vocabulary=self.prompt_answerable_without_repo_vocabulary,
                terminology_clarification_required=self.terminology_clarification_required,
                prompt_visible_in_final_response=self.prompt_visible_in_final_response,
                prompt_before_decisive_evidence=self.prompt_before_decisive_evidence,
                answer_revealing_progress_before_prompt=self.answer_revealing_progress_before_prompt,
            ).defect
            if prompt_defect is not InteractionDefect.NONE:
                return prompt_defect
            if self.response_present and self.response_relevance is ResponseRelevance.UNKNOWN:
                return InteractionDefect.RESPONSE_RELEVANCE_DEFECT
        return InteractionDefect.NONE

    def to_dict(self) -> dict[str, object]:
        """Return a bounded schema-ready receipt without user/repository text."""

        return {
            "schema": "repolearn.interaction_observation.v1",
            "task_id": self.task_id,
            "activation_source": self.activation_source.value,
            "trigger_selected": self.trigger_selected,
            "selected_branch": self.selected_branch.value if self.selected_branch else None,
            "spontaneous_judgment_present": self.spontaneous_judgment_present,
            "branch_selection_valid": self.branch_selection_valid,
            "prompt_generated": self.prompt_generated,
            "prompt_answerable_without_repo_vocabulary": self.prompt_answerable_without_repo_vocabulary,
            "terminology_clarification_required": self.terminology_clarification_required,
            "prompt_visible_in_final_response": self.prompt_visible_in_final_response,
            "prompt_before_decisive_evidence": self.prompt_before_decisive_evidence,
            "answer_revealing_progress_before_prompt": self.answer_revealing_progress_before_prompt,
            "response_present": self.response_present,
            "response_relevance": self.response_relevance.value,
            "engineering_blocked": self.engineering_blocked,
            "interaction_defect": self.interaction_defect.value,
            "cue_fading_suppressed": self.cue_fading_suppressed,
            "cue_level": self.cue_level,
            "transfer_distance": self.transfer_distance,
        }
