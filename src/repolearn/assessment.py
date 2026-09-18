"""Evidence-bounded assessment primitives.

The L0-L4 ladder is navigation for learning interactions, not a calibrated
psychometric scale. Assessment returns an evidence ceiling; it does not grant or
change engineering authority and it does not directly persist mastery.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MasteryLevel(str, Enum):
    UNASSESSED = "UNASSESSED"
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"


class CueLevel(str, Enum):
    NONE = "NONE"
    LIGHT = "LIGHT"
    HEAVY = "HEAVY"


class TransferDistance(str, Enum):
    SAME_STRUCTURE = "SAME_STRUCTURE"
    NEAR_TRANSFER = "NEAR_TRANSFER"
    FAR_TRANSFER = "FAR_TRANSFER"


class EvidenceTiming(str, Enum):
    PRE_EVIDENCE = "PRE_EVIDENCE"
    POST_EVIDENCE = "POST_EVIDENCE"


class EvidenceProvenance(str, Enum):
    USER_AUTHORED = "USER_AUTHORED"
    AI_REFORMULATED = "AI_REFORMULATED"
    AI_EXPLANATION = "AI_EXPLANATION"


class AssessmentClassification(str, Enum):
    UNASSESSED = "UNASSESSED"
    EXPLICIT_NOT_YET_ENCOUNTERED = "EXPLICIT_NOT_YET_ENCOUNTERED"
    EXPOSURE_ONLY = "EXPOSURE_ONLY"
    POST_EVIDENCE_AGREEMENT = "POST_EVIDENCE_AGREEMENT"
    USER_ATTEMPT = "USER_ATTEMPT"
    EXPLAINED_WITH_EVIDENCE = "EXPLAINED_WITH_EVIDENCE"
    TRANSFER_WITH_TRADEOFFS = "TRANSFER_WITH_TRADEOFFS"
    INDEPENDENT_FALSIFIER = "INDEPENDENT_FALSIFIER"
    REASSESSMENT_REQUIRED = "REASSESSMENT_REQUIRED"


MASTERY_LEVEL_IS_CALIBRATED_PSYCHOMETRIC_SCALE = False
LEARNING_ASSESSMENT_CHANGES_ENGINEERING_AUTHORITY = False

_LEVEL_ORDER = {
    MasteryLevel.UNASSESSED: -1,
    MasteryLevel.L0: 0,
    MasteryLevel.L1: 1,
    MasteryLevel.L2: 2,
    MasteryLevel.L3: 3,
    MasteryLevel.L4: 4,
}


@dataclass(frozen=True)
class JudgmentEvidence:
    goals: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    alternatives: tuple[str, ...] = ()
    trade_offs: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    falsifier: str | None = None
    provenance: EvidenceProvenance = EvidenceProvenance.USER_AUTHORED

    @property
    def supports_explanation(self) -> bool:
        return bool(self.goals and self.constraints and self.evidence)

    @property
    def supports_transfer(self) -> bool:
        return bool(self.goals and self.constraints and self.alternatives and self.trade_offs and self.evidence)

    @property
    def has_falsifier(self) -> bool:
        return bool(self.falsifier and self.falsifier.strip())


@dataclass(frozen=True)
class AssessmentResult:
    prior_level: MasteryLevel
    evidence_ceiling: MasteryLevel
    recommended_level: MasteryLevel
    classification: AssessmentClassification
    cue_level: CueLevel
    transfer_distance: TransferDistance
    delay: str | None
    rationale: str
    requires_reassessment: bool = False


def _higher(left: MasteryLevel, right: MasteryLevel) -> MasteryLevel:
    return left if _LEVEL_ORDER[left] >= _LEVEL_ORDER[right] else right


def assess_judgment(
    *,
    current_level: MasteryLevel | None,
    user_attempted: bool,
    ai_explanation_only: bool,
    evidence: JudgmentEvidence | None = None,
    cue_level: CueLevel = CueLevel.HEAVY,
    transfer_distance: TransferDistance = TransferDistance.SAME_STRUCTURE,
    delay: str | None = None,
    explicit_not_yet_encountered: bool = False,
    evidence_timing: EvidenceTiming = EvidenceTiming.PRE_EVIDENCE,
    contradicts_prior: bool = False,
) -> AssessmentResult:
    """Return a conservative evidence recommendation.

    Only user-authored, pre-evidence reasoning can promote mastery. AI
    reformulation and post-evidence agreement remain exposure. A weaker attempt
    does not regress prior mastery, while explicitly contradictory weaker
    evidence is surfaced as REASSESSMENT_REQUIRED rather than silently resolved.
    """

    prior = current_level or MasteryLevel.UNASSESSED
    evidence = evidence or JudgmentEvidence()

    if explicit_not_yet_encountered and prior is MasteryLevel.UNASSESSED and not user_attempted:
        return AssessmentResult(
            prior_level=prior,
            evidence_ceiling=MasteryLevel.L0,
            recommended_level=MasteryLevel.L0,
            classification=AssessmentClassification.EXPLICIT_NOT_YET_ENCOUNTERED,
            cue_level=cue_level,
            transfer_distance=transfer_distance,
            delay=delay,
            rationale="Explicit evidence says the concept has not yet been encountered.",
        )

    if not user_attempted:
        return AssessmentResult(
            prior_level=prior,
            evidence_ceiling=MasteryLevel.UNASSESSED,
            recommended_level=prior,
            classification=(
                AssessmentClassification.EXPOSURE_ONLY
                if ai_explanation_only
                else AssessmentClassification.UNASSESSED
            ),
            cue_level=cue_level,
            transfer_distance=transfer_distance,
            delay=delay,
            rationale="No assessable user attempt was provided.",
        )

    if (
        ai_explanation_only
        or evidence.provenance is not EvidenceProvenance.USER_AUTHORED
    ):
        return AssessmentResult(
            prior_level=prior,
            evidence_ceiling=MasteryLevel.UNASSESSED,
            recommended_level=prior,
            classification=AssessmentClassification.EXPOSURE_ONLY,
            cue_level=cue_level,
            transfer_distance=transfer_distance,
            delay=delay,
            rationale="AI explanation or reformulation is exposure, not user mastery evidence.",
        )

    if evidence_timing is EvidenceTiming.POST_EVIDENCE:
        return AssessmentResult(
            prior_level=prior,
            evidence_ceiling=MasteryLevel.UNASSESSED,
            recommended_level=prior,
            classification=AssessmentClassification.POST_EVIDENCE_AGREEMENT,
            cue_level=cue_level,
            transfer_distance=transfer_distance,
            delay=delay,
            rationale="The user response followed decisive answer-revealing evidence.",
        )

    ceiling = MasteryLevel.L1
    classification = AssessmentClassification.USER_ATTEMPT
    rationale = "A real user attempt establishes encounter evidence only."

    if evidence.supports_explanation:
        ceiling = MasteryLevel.L2
        classification = AssessmentClassification.EXPLAINED_WITH_EVIDENCE
        rationale = "The attempt identifies goals, constraints and supporting evidence."

    if (
        evidence.supports_transfer
        and transfer_distance is not TransferDistance.SAME_STRUCTURE
        and cue_level is not CueLevel.HEAVY
    ):
        ceiling = MasteryLevel.L3
        classification = AssessmentClassification.TRANSFER_WITH_TRADEOFFS
        rationale = "The attempt transfers with alternatives, trade-offs and evidence under limited cueing."

    if (
        ceiling is MasteryLevel.L3
        and evidence.has_falsifier
        and transfer_distance is TransferDistance.FAR_TRANSFER
        and cue_level is CueLevel.NONE
    ):
        ceiling = MasteryLevel.L4
        classification = AssessmentClassification.INDEPENDENT_FALSIFIER
        rationale = "The attempt independently transfers and names evidence that would change the judgment."

    if (
        contradicts_prior
        and prior is not MasteryLevel.UNASSESSED
        and _LEVEL_ORDER[ceiling] < _LEVEL_ORDER[prior]
    ):
        return AssessmentResult(
            prior_level=prior,
            evidence_ceiling=ceiling,
            recommended_level=prior,
            classification=AssessmentClassification.REASSESSMENT_REQUIRED,
            cue_level=cue_level,
            transfer_distance=transfer_distance,
            delay=delay,
            rationale="Contradictory weaker evidence requires explicit reassessment.",
            requires_reassessment=True,
        )

    return AssessmentResult(
        prior_level=prior,
        evidence_ceiling=ceiling,
        recommended_level=_higher(prior, ceiling),
        classification=classification,
        cue_level=cue_level,
        transfer_distance=transfer_distance,
        delay=delay,
        rationale=rationale,
    )
