"""Low-interruption learning-trigger policy."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


MAX_PRIMARY_LEARNING_POINTS_PER_TASK = 1


class InteractionMode(str, Enum):
    OBSERVE = "observe"
    GUIDED = "guided"
    PRACTICE = "practice"


class TriggerDisposition(str, Enum):
    NO_TRIGGER = "NO_TRIGGER"
    LEARNING_OPPORTUNITY = "LEARNING_OPPORTUNITY"


@dataclass(frozen=True)
class TaskContext:
    meaningful: bool = True
    mechanical: bool = False
    urgent: bool = False
    exact_machine_output: bool = False
    decisive_evidence_already_revealed: bool = False
    deep_learning_research_would_be_required: bool = False


@dataclass(frozen=True)
class LearningOpportunity:
    concept: str

    def __post_init__(self) -> None:
        if not self.concept.strip():
            raise ValueError("learning concept must be non-empty")


@dataclass(frozen=True)
class TriggerResult:
    disposition: TriggerDisposition
    opportunities: tuple[LearningOpportunity, ...] = ()
    reason: str = ""

    def __post_init__(self) -> None:
        if len(self.opportunities) > MAX_PRIMARY_LEARNING_POINTS_PER_TASK:
            raise ValueError("at most one primary learning point is allowed per task")
        if self.disposition is TriggerDisposition.NO_TRIGGER and self.opportunities:
            raise ValueError("NO_TRIGGER cannot carry a learning opportunity")
        if self.disposition is TriggerDisposition.LEARNING_OPPORTUNITY and len(self.opportunities) != 1:
            raise ValueError("LEARNING_OPPORTUNITY must carry exactly one concept")

    @property
    def learning_research_allowed(self) -> bool:
        """Whether learning-only research may proceed after the trigger decision.

        Trigger selection is deliberately cheaper than any deep learning-only
        investigation. A no-trigger decision therefore forbids that extra work;
        a trigger permits research only for the single selected concept.
        """

        return self.disposition is TriggerDisposition.LEARNING_OPPORTUNITY

    @property
    def research_concepts(self) -> tuple[str, ...]:
        if not self.learning_research_allowed:
            return ()
        return tuple(opportunity.concept for opportunity in self.opportunities)


def select_learning_opportunity(*, context: TaskContext, mode: InteractionMode, candidate_concepts: Iterable[str]) -> TriggerResult:
    """Select zero or one learning point.

    RepoLearn is intentionally conservative: state awareness may be mandatory for
    a client integration, but teaching is conditional. Mechanical, urgent,
    exact-machine-output, already-revealed, or non-meaningful work stays silent.
    Observe mode is also silent by design.
    """

    if mode is InteractionMode.OBSERVE:
        return TriggerResult(TriggerDisposition.NO_TRIGGER, reason="observe_mode")

    suppression_reasons = (
        (not context.meaningful, "not_meaningful"),
        (context.mechanical, "mechanical"),
        (context.urgent, "urgent"),
        (context.exact_machine_output, "exact_machine_output"),
        (context.decisive_evidence_already_revealed, "decisive_evidence_already_revealed"),
    )
    for suppressed, reason in suppression_reasons:
        if suppressed:
            return TriggerResult(TriggerDisposition.NO_TRIGGER, reason=reason)

    for concept in candidate_concepts:
        normalized = concept.strip()
        if normalized:
            return TriggerResult(
                TriggerDisposition.LEARNING_OPPORTUNITY,
                opportunities=(LearningOpportunity(normalized),),
                reason="high_value_candidate",
            )

    return TriggerResult(TriggerDisposition.NO_TRIGGER, reason="no_candidate")
