from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MasteryLevel(StrEnum):
    UNASSESSED = "UNASSESSED"
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"


@dataclass(frozen=True)
class AssessmentEvidence:
    demonstrated_by_user: bool
    independent_judgment: bool = False
    materially_different_case: bool = False
    explained_tradeoff: bool = False
    proactive_falsifier: bool = False
    ai_explanation_only: bool = False
    state_available: bool = True


def assess_mastery_effect(evidence: AssessmentEvidence) -> MasteryLevel:
    """Return the strongest level directly supported by one bounded event.

    A caller still decides whether and how this event changes a broader domain
    projection. Narrow evidence must never auto-promote a whole domain.
    """
    if not evidence.state_available:
        return MasteryLevel.UNASSESSED
    if evidence.ai_explanation_only or not evidence.demonstrated_by_user:
        return MasteryLevel.UNASSESSED
    if evidence.proactive_falsifier and evidence.independent_judgment:
        return MasteryLevel.L4
    if (evidence.independent_judgment and evidence.materially_different_case and evidence.explained_tradeoff):
        return MasteryLevel.L3
    if evidence.explained_tradeoff:
        return MasteryLevel.L2
    return MasteryLevel.L1
