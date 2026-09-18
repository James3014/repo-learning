"""Executable human-learning interaction contracts.

These primitives make RepoLearn guided behavior and privacy-safe dogfood
observations explicit without taking engineering authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re

from .triggers import ActivationSource
from .version import CONTRACT_REVISION


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class GuidedBranch(str, Enum):
    JUDGMENT_PROMPT = "JUDGMENT_PROMPT"
    SPONTANEOUS_JUDGMENT_CAPTURE = "SPONTANEOUS_JUDGMENT_CAPTURE"


@dataclass(frozen=True)
class UserJudgmentSignal:
    """Bounded pre-feedback signal used to choose the guided branch."""

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
    """Choose the safe guided branch; ambiguity resolves to a prompt."""

    if signal.meaningful_pre_evidence_judgment:
        return GuidedBranch.SPONTANEOUS_JUDGMENT_CAPTURE
    return GuidedBranch.JUDGMENT_PROMPT


class ResponseRelevance(str, Enum):
    PROMPT_ANSWER = "PROMPT_ANSWER"
    UNRELATED_ENGINEERING = "UNRELATED_ENGINEERING"
    EXPLICIT_SKIP = "EXPLICIT_SKIP"
    UNKNOWN = "UNKNOWN"


class EvaluationSource(str, Enum):
    SELF_REPORTED = "SELF_REPORTED"
    DETERMINISTIC = "DETERMINISTIC"
    INDEPENDENT_LLM = "INDEPENDENT_LLM"
    HUMAN = "HUMAN"


class InteractionDefect(str, Enum):
    NONE = "NONE"
    CONTRACT_ATTESTATION_DEFECT = "CONTRACT_ATTESTATION_DEFECT"
    GUIDED_BRANCH_SELECTION_DEFECT = "GUIDED_BRANCH_SELECTION_DEFECT"
    PROMPT_COMPREHENSION_DEFECT = "PROMPT_COMPREHENSION_DEFECT"
    PROMPT_VISIBILITY_DEFECT = "PROMPT_VISIBILITY_DEFECT"
    PRE_EVIDENCE_ORDERING_DEFECT = "PRE_EVIDENCE_ORDERING_DEFECT"
    LANGUAGE_ALIGNMENT_DEFECT = "LANGUAGE_ALIGNMENT_DEFECT"
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
    language_alignment_valid: bool | None = None

    @property
    def defects(self) -> tuple[InteractionDefect, ...]:
        defects: list[InteractionDefect] = []
        if not self.prompt_generated or self.prompt_visible_in_final_response is not True:
            defects.append(InteractionDefect.PROMPT_VISIBILITY_DEFECT)
        if self.prompt_answerable_without_repo_vocabulary is not True:
            defects.append(InteractionDefect.PROMPT_COMPREHENSION_DEFECT)
        if self.prompt_before_decisive_evidence is not True or self.answer_revealing_progress_before_prompt:
            defects.append(InteractionDefect.PRE_EVIDENCE_ORDERING_DEFECT)
        if self.language_alignment_valid is False:
            defects.append(InteractionDefect.LANGUAGE_ALIGNMENT_DEFECT)
        return tuple(defects)

    @property
    def defect(self) -> InteractionDefect:
        return self.defects[0] if self.defects else InteractionDefect.NONE


@dataclass(frozen=True)
class InteractionObservationReceipt:
    """Privacy-safe interaction receipt with provenance and contract attestation."""

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
    contract_revision: str | None = None
    contract_content_sha256: str | None = None
    trace_sha256: str | None = None
    evaluation_source: EvaluationSource = EvaluationSource.SELF_REPORTED
    generator_id: str | None = None
    evaluator_id: str | None = None
    natural_task: bool = False
    added_turns: int = 0
    added_time_ms_estimate: int | None = None
    added_context_tokens_estimate: int | None = None
    user_language: str | None = None
    language_alignment_valid: bool | None = None

    def __post_init__(self) -> None:
        if not self.task_id.strip():
            raise ValueError("task_id must be non-empty")
        if not self.trigger_selected and self.selected_branch is not None:
            raise ValueError("no-trigger receipt cannot select a guided branch")
        if self.added_turns < 0:
            raise ValueError("added_turns must be >= 0")
        if self.added_time_ms_estimate is not None and self.added_time_ms_estimate < 0:
            raise ValueError("added_time_ms_estimate must be >= 0")
        if self.added_context_tokens_estimate is not None and self.added_context_tokens_estimate < 0:
            raise ValueError("added_context_tokens_estimate must be >= 0")
        for name, value in (
            ("contract_content_sha256", self.contract_content_sha256),
            ("trace_sha256", self.trace_sha256),
        ):
            if value is not None and not _SHA256_RE.fullmatch(value):
                raise ValueError(f"{name} must be a lowercase SHA-256 hex digest")
        if self.evaluation_source is not EvaluationSource.SELF_REPORTED:
            if not self.evaluator_id or not self.evaluator_id.strip():
                raise ValueError("independent/deterministic evaluation requires evaluator_id")
        if (
            self.evaluation_source is EvaluationSource.INDEPENDENT_LLM
            and self.generator_id is not None
            and self.evaluator_id == self.generator_id
        ):
            raise ValueError("independent LLM evaluator must differ from generator_id")
        if self.trigger_selected and self.selected_branch is not None:
            expected_branch = (
                GuidedBranch.SPONTANEOUS_JUDGMENT_CAPTURE
                if self.spontaneous_judgment_present
                else GuidedBranch.JUDGMENT_PROMPT
            )
            if self.selected_branch is not expected_branch:
                object.__setattr__(self, "branch_selection_valid", False)

    @property
    def interaction_defects(self) -> tuple[InteractionDefect, ...]:
        defects: list[InteractionDefect] = []
        if self.contract_revision is not None and self.contract_revision != CONTRACT_REVISION:
            defects.append(InteractionDefect.CONTRACT_ATTESTATION_DEFECT)
        if self.engineering_blocked:
            defects.append(InteractionDefect.ENGINEERING_BLOCKING_DEFECT)
        if not self.branch_selection_valid:
            defects.append(InteractionDefect.GUIDED_BRANCH_SELECTION_DEFECT)
        if self.selected_branch is GuidedBranch.JUDGMENT_PROMPT:
            prompt = PromptDeliveryObservation(
                prompt_generated=self.prompt_generated,
                prompt_answerable_without_repo_vocabulary=self.prompt_answerable_without_repo_vocabulary,
                terminology_clarification_required=self.terminology_clarification_required,
                prompt_visible_in_final_response=self.prompt_visible_in_final_response,
                prompt_before_decisive_evidence=self.prompt_before_decisive_evidence,
                answer_revealing_progress_before_prompt=self.answer_revealing_progress_before_prompt,
                language_alignment_valid=self.language_alignment_valid,
            )
            defects.extend(prompt.defects)
            if self.response_present and self.response_relevance is ResponseRelevance.UNKNOWN:
                defects.append(InteractionDefect.RESPONSE_RELEVANCE_DEFECT)
        return tuple(dict.fromkeys(defects))

    @property
    def interaction_defect(self) -> InteractionDefect:
        return self.interaction_defects[0] if self.interaction_defects else InteractionDefect.NONE

    def attestation_matches(
        self,
        *,
        expected_revision: str = CONTRACT_REVISION,
        expected_content_sha256: str | None = None,
    ) -> bool:
        if self.contract_revision != expected_revision:
            return False
        if expected_content_sha256 is not None:
            return self.contract_content_sha256 == expected_content_sha256
        return self.contract_content_sha256 is not None

    def qualifies_for_independent_g5_evidence(
        self,
        *,
        expected_content_sha256: str,
    ) -> bool:
        return bool(
            self.natural_task
            and self.trace_sha256
            and self.attestation_matches(expected_content_sha256=expected_content_sha256)
            and self.evaluation_source
            in {EvaluationSource.DETERMINISTIC, EvaluationSource.INDEPENDENT_LLM, EvaluationSource.HUMAN}
            and self.evaluator_id
            and (
                self.evaluation_source is not EvaluationSource.INDEPENDENT_LLM
                or self.generator_id is None
                or self.evaluator_id != self.generator_id
            )
        )

    def to_dict(self) -> dict[str, object]:
        """Return a schema-ready receipt without user/repository text."""

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
            "interaction_defects": [defect.value for defect in self.interaction_defects],
            "cue_fading_suppressed": self.cue_fading_suppressed,
            "cue_level": self.cue_level,
            "transfer_distance": self.transfer_distance,
            "contract_revision": self.contract_revision,
            "contract_content_sha256": self.contract_content_sha256,
            "trace_sha256": self.trace_sha256,
            "evaluation_source": self.evaluation_source.value,
            "generator_id": self.generator_id,
            "evaluator_id": self.evaluator_id,
            "natural_task": self.natural_task,
            "added_turns": self.added_turns,
            "added_time_ms_estimate": self.added_time_ms_estimate,
            "added_context_tokens_estimate": self.added_context_tokens_estimate,
            "user_language": self.user_language,
            "language_alignment_valid": self.language_alignment_valid,
        }
