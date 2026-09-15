"""Client-neutral RepoLearn interaction preparation.

G2 separates four facts: Skill source exists, a client discovers it, learning
state loads, and a learning interaction actually occurs. This module only
computes the bounded state/trigger decision and never takes engineering control.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping, Any

from .state import StateBackend, StateUnavailableError
from .triggers import InteractionMode, TaskContext, TriggerDisposition, TriggerResult, select_learning_opportunity


@dataclass(frozen=True)
class ClientLearningDecision:
    state_loaded: bool
    state: Mapping[str, Any] | None
    trigger: TriggerResult
    visible_learning_allowed: bool
    degraded_reason: str | None = None
    engineering_may_continue: bool = True


class LearningResponseDisposition(str, Enum):
    ANSWERED = "ANSWERED"
    SKIP_NO_RESPONSE = "SKIP_NO_RESPONSE"


@dataclass(frozen=True)
class LearningResponseResult:
    disposition: LearningResponseDisposition
    should_assess: bool
    engineering_may_continue: bool = True


def classify_learning_response(response: str | None) -> LearningResponseResult:
    """Classify a visible learning prompt response without blocking engineering.

    No response (including blank text) is a skip, never negative mastery
    evidence and never a reason to wait. Engineering continues either way.
    """

    if response is None or not response.strip():
        return LearningResponseResult(
            disposition=LearningResponseDisposition.SKIP_NO_RESPONSE,
            should_assess=False,
        )
    return LearningResponseResult(
        disposition=LearningResponseDisposition.ANSWERED,
        should_assess=True,
    )


def prepare_learning_decision(
    *,
    backend: StateBackend,
    profile_id: str,
    context: TaskContext,
    mode: InteractionMode,
    candidate_concepts: Iterable[str],
) -> ClientLearningDecision:
    """Load bounded state and choose zero/one learning interaction.

    Backend unavailability degrades to normal engineering instead of blocking the
    task. Exact-machine-output work never permits visible learning output even if
    state awareness succeeds.
    """

    try:
        state = backend.read_current_state(profile_id)
        state_loaded = state is not None
        degraded_reason = None
    except StateUnavailableError as exc:
        state = None
        state_loaded = False
        degraded_reason = str(exc)

    trigger = select_learning_opportunity(
        context=context,
        mode=mode,
        candidate_concepts=candidate_concepts,
    )
    visible_learning_allowed = (
        trigger.disposition is TriggerDisposition.LEARNING_OPPORTUNITY
        and degraded_reason is None
        and not context.exact_machine_output
    )
    return ClientLearningDecision(
        state_loaded=state_loaded,
        state=state,
        trigger=trigger,
        visible_learning_allowed=visible_learning_allowed,
        degraded_reason=degraded_reason,
    )
