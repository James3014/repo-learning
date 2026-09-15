from __future__ import annotations

from repolearn.assessment import AssessmentClassification, CueLevel, JudgmentEvidence, LEARNING_ASSESSMENT_CHANGES_ENGINEERING_AUTHORITY, MASTERY_LEVEL_IS_CALIBRATED_PSYCHOMETRIC_SCALE, MasteryLevel, TransferDistance, assess_judgment


def complete_evidence(*, falsifier: str | None = None) -> JudgmentEvidence:
    return JudgmentEvidence(
        goals=("preserve one canonical truth",),
        constraints=("multiple clients",),
        alternatives=("central backend", "client memory"),
        trade_offs=("availability versus consistency",),
        evidence=("readback proves the backend revision",),
        falsifier=falsifier,
    )


def test_unassessed_is_distinct_from_l0() -> None:
    assert MasteryLevel.UNASSESSED is not MasteryLevel.L0
    result = assess_judgment(current_level=None, user_attempted=False, ai_explanation_only=False)
    assert result.prior_level is MasteryLevel.UNASSESSED
    assert result.recommended_level is MasteryLevel.UNASSESSED


def test_l0_requires_explicit_not_yet_encountered_evidence() -> None:
    result = assess_judgment(current_level=None, user_attempted=False, ai_explanation_only=False, explicit_not_yet_encountered=True)
    assert result.recommended_level is MasteryLevel.L0
    assert result.classification is AssessmentClassification.EXPLICIT_NOT_YET_ENCOUNTERED


def test_ai_explanation_or_exposure_does_not_promote_mastery() -> None:
    result = assess_judgment(
        current_level=MasteryLevel.L1,
        user_attempted=False,
        ai_explanation_only=True,
        evidence=complete_evidence(falsifier="anything"),
        cue_level=CueLevel.NONE,
        transfer_distance=TransferDistance.FAR_TRANSFER,
    )
    assert result.recommended_level is MasteryLevel.L1
    assert result.evidence_ceiling is MasteryLevel.UNASSESSED
    assert result.classification is AssessmentClassification.EXPOSURE_ONLY


def test_explanation_with_goals_constraints_and_evidence_supports_l2_ceiling() -> None:
    result = assess_judgment(
        current_level=MasteryLevel.L1,
        user_attempted=True,
        ai_explanation_only=False,
        evidence=JudgmentEvidence(goals=("avoid duplicate truth",), constraints=("offline client",), evidence=("state hash",)),
        cue_level=CueLevel.HEAVY,
        transfer_distance=TransferDistance.SAME_STRUCTURE,
    )
    assert result.evidence_ceiling is MasteryLevel.L2
    assert result.recommended_level is MasteryLevel.L2


def test_near_transfer_with_light_cue_and_tradeoffs_supports_l3_ceiling() -> None:
    result = assess_judgment(
        current_level=MasteryLevel.L2,
        user_attempted=True,
        ai_explanation_only=False,
        evidence=complete_evidence(),
        cue_level=CueLevel.LIGHT,
        transfer_distance=TransferDistance.NEAR_TRANSFER,
    )
    assert result.evidence_ceiling is MasteryLevel.L3
    assert result.classification is AssessmentClassification.TRANSFER_WITH_TRADEOFFS


def test_l4_ceiling_requires_uncued_far_transfer_and_falsifier() -> None:
    with_falsifier = assess_judgment(
        current_level=MasteryLevel.L3,
        user_attempted=True,
        ai_explanation_only=False,
        evidence=complete_evidence(falsifier="A verified offline-only requirement would justify a different owner."),
        cue_level=CueLevel.NONE,
        transfer_distance=TransferDistance.FAR_TRANSFER,
    )
    without_falsifier = assess_judgment(
        current_level=MasteryLevel.L3,
        user_attempted=True,
        ai_explanation_only=False,
        evidence=complete_evidence(),
        cue_level=CueLevel.NONE,
        transfer_distance=TransferDistance.FAR_TRANSFER,
    )
    assert with_falsifier.evidence_ceiling is MasteryLevel.L4
    assert without_falsifier.evidence_ceiling is MasteryLevel.L3


def test_delay_is_metadata_not_an_automatic_mastery_transition() -> None:
    immediate = assess_judgment(
        current_level=MasteryLevel.L1,
        user_attempted=True,
        ai_explanation_only=False,
        evidence=JudgmentEvidence(goals=("g",), constraints=("c",), evidence=("e",)),
        delay="same-session",
    )
    delayed = assess_judgment(
        current_level=MasteryLevel.L1,
        user_attempted=True,
        ai_explanation_only=False,
        evidence=JudgmentEvidence(goals=("g",), constraints=("c",), evidence=("e",)),
        delay="21d",
    )
    assert immediate.evidence_ceiling is delayed.evidence_ceiling is MasteryLevel.L2


def test_prior_mastery_is_not_regressed_by_one_weaker_event() -> None:
    result = assess_judgment(current_level=MasteryLevel.L3, user_attempted=True, ai_explanation_only=False, evidence=JudgmentEvidence())
    assert result.evidence_ceiling is MasteryLevel.L1
    assert result.recommended_level is MasteryLevel.L3


def test_assessment_is_navigation_not_authority_or_psychometrics() -> None:
    assert MASTERY_LEVEL_IS_CALIBRATED_PSYCHOMETRIC_SCALE is False
    assert LEARNING_ASSESSMENT_CHANGES_ENGINEERING_AUTHORITY is False
