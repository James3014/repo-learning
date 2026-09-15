from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class InteractionMode(StrEnum):
    OBSERVE = "observe"
    GUIDED = "guided"
    PRACTICE = "practice"


@dataclass(frozen=True)
class TriggerContext:
    mode: InteractionMode = InteractionMode.GUIDED
    real_architecture_alternative: bool = False
    relevant_to_frontier: bool = False
    decisive_evidence_already_revealed: bool = False
    urgent: bool = False
    mechanical: bool = False
    exact_output: bool = False
    interruption_cost_acceptable: bool = True
    repeated_without_harder_variant: bool = False


@dataclass(frozen=True)
class TriggerDecision:
    prompt: bool
    reason: str
    max_primary_learning_points: int


def decide_trigger(context: TriggerContext) -> TriggerDecision:
    """Return a conservative learning-interruption decision.

    State loading is outside this function; exact-output callers still load state
    silently before preserving the requested machine-clean output.
    """
    if context.mode is InteractionMode.OBSERVE:
        return TriggerDecision(False, "observe_mode", 0)
    blockers = (
        (context.exact_output, "exact_output"),
        (context.urgent, "urgent_task"),
        (context.mechanical, "mechanical_task"),
        (context.decisive_evidence_already_revealed, "decisive_evidence_revealed"),
        (not context.interruption_cost_acceptable, "interruption_cost"),
        (context.repeated_without_harder_variant, "no_harder_variant"),
        (not context.real_architecture_alternative, "no_architecture_alternative"),
        (not context.relevant_to_frontier, "not_relevant_to_frontier"),
    )
    for blocked, reason in blockers:
        if blocked:
            return TriggerDecision(False, reason, 1)
    return TriggerDecision(True, "high_value_architecture_judgment", 1)
