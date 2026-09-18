"""Client-neutral RepoLearn interaction preparation.

This module computes bounded state, trigger, guided branch, and response
classification. It never takes engineering control.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Mapping

from .interaction import (
    GuidedBranch,
    ResponseRelevance,
    UserJudgmentSignal,
    select_guided_branch,
)
from .state import StateBackend, StateUnavailableError
from .triggers import (
    ActivationSource,
    InteractionMode,
    TaskContext,
    TriggerDisposition,
    TriggerResult,
    select_learning_opportunity,
)


@dataclass(frozen=True)
class ClientLearningDecision:
    state_loaded: bool
    state: Mapping[str, Any] | None
    trigger: TriggerResult
    visible_learning_allowed: bool
    activation_source: ActivationSource
    guided_branch: GuidedBranch | None = None
    degraded_reason: str | None = None
    engineering_may_continue: bool = True


class LearningResponseDisposition(str, Enum):
    ANSWERED = "ANSWERED"
    SKIP_NO_RESPONSE = "SKIP_NO_RESPONSE"
    EXPLICIT_SKIP = "EXPLICIT_SKIP"
    UNRELATED_ENGINEERING_CONTINUATION = "UNRELATED_ENGINEERING_CONTINUATION"
    UNCLASSIFIED = "UNCLASSIFIED"


@dataclass(frozen=True)
class LearningResponseResult:
    disposition: LearningResponseDisposition
    relevance: ResponseRelevance
    should_assess: bool
    engineering_may_continue: bool = True


def classify_learning_response(
    response: str | None,
    *,
    relevance: ResponseRelevance = ResponseRelevance.UNKNOWN,
) -> LearningResponseResult:
    """Classify a later user turn without treating every non-empty turn as an answer.

    Semantic relevance is supplied explicitly by the client/host. UNKNOWN is
    intentionally non-assessable: uncertainty must not manufacture mastery.
    """

    if response is None or not response.strip():
        return LearningResponseResult(
            disposition=LearningResponseDisposition.SKIP_NO_RESPONSE,
            relevance=ResponseRelevance.UNKNOWN,
            should_assess=False,
        )
    if relevance is ResponseRelevance.PROMPT_ANSWER:
        return LearningResponseResult(
            disposition=LearningResponseDisposition.ANSWERED,
            relevance=relevance,
            should_assess=True,
        )
    if relevance is ResponseRelevance.EXPLICIT_SKIP:
        return LearningResponseResult(
            disposition=LearningResponseDisposition.EXPLICIT_SKIP,
            relevance=relevance,
            should_assess=False,
        )
    if relevance is ResponseRelevance.UNRELATED_ENGINEERING:
        return LearningResponseResult(
            disposition=LearningResponseDisposition.UNRELATED_ENGINEERING_CONTINUATION,
            relevance=relevance,
            should_assess=False,
        )
    return LearningResponseResult(
        disposition=LearningResponseDisposition.UNCLASSIFIED,
        relevance=ResponseRelevance.UNKNOWN,
        should_assess=False,
    )


def _silently_faded_concepts(state: Mapping[str, Any] | None) -> tuple[str, ...]:
    if not isinstance(state, Mapping):
        return ()
    concepts = state.get("concepts")
    if not isinstance(concepts, Mapping):
        return ()
    faded: list[str] = []
    for concept, value in concepts.items():
        if not isinstance(concept, str) or not isinstance(value, Mapping):
            continue
        if value.get("silent_cue_fading_eligible") is True:
            faded.append(concept)
    return tuple(faded)


def prepare_learning_decision(
    *,
    backend: StateBackend,
    profile_id: str,
    context: TaskContext,
    mode: InteractionMode,
    candidate_concepts: Iterable[str],
    judgment_signal: UserJudgmentSignal | None = None,
) -> ClientLearningDecision:
    """Load bounded state and choose a non-blocking learning interaction.

    Backend unavailability degrades to normal engineering and also disables
    learning-only research. A valid missing profile remains UNASSESSED and can
    still trigger.
    """

    try:
        state = backend.read_current_state(profile_id)
        state_loaded = state is not None
        degraded_reason = None
    except StateUnavailableError as exc:
        state = None
        state_loaded = False
        degraded_reason = str(exc)

    if degraded_reason is not None:
        trigger = TriggerResult(TriggerDisposition.NO_TRIGGER, reason="state_unavailable")
    else:
        trigger = select_learning_opportunity(
            context=context,
            mode=mode,
            candidate_concepts=candidate_concepts,
            silently_faded_concepts=_silently_faded_concepts(state),
        )

    visible_learning_allowed = (
        trigger.disposition is TriggerDisposition.LEARNING_OPPORTUNITY
        and degraded_reason is None
        and not context.exact_machine_output
    )

    guided_branch: GuidedBranch | None = None
    if visible_learning_allowed and mode is InteractionMode.GUIDED:
        guided_branch = select_guided_branch(judgment_signal or UserJudgmentSignal())

    return ClientLearningDecision(
        state_loaded=state_loaded,
        state=state,
        trigger=trigger,
        visible_learning_allowed=visible_learning_allowed,
        activation_source=context.activation_source,
        guided_branch=guided_branch,
        degraded_reason=degraded_reason,
    )
