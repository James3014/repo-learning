from __future__ import annotations

import pytest

from repolearn.triggers import InteractionMode, LearningOpportunity, MAX_PRIMARY_LEARNING_POINTS_PER_TASK, TaskContext, TriggerDisposition, TriggerResult, select_learning_opportunity


@pytest.mark.parametrize(
    ("context", "reason"),
    [
        (TaskContext(meaningful=False), "not_meaningful"),
        (TaskContext(mechanical=True), "mechanical"),
        (TaskContext(urgent=True), "urgent"),
        (TaskContext(exact_machine_output=True), "exact_machine_output"),
        (TaskContext(decisive_evidence_already_revealed=True), "decisive_evidence_already_revealed"),
    ],
)
def test_suppressed_contexts_are_silent(context: TaskContext, reason: str) -> None:
    result = select_learning_opportunity(context=context, mode=InteractionMode.GUIDED, candidate_concepts=["canonical state"])
    assert result.disposition is TriggerDisposition.NO_TRIGGER
    assert result.opportunities == ()
    assert result.reason == reason


def test_observe_mode_never_interrupts() -> None:
    result = select_learning_opportunity(context=TaskContext(), mode=InteractionMode.OBSERVE, candidate_concepts=["ownership boundary"])
    assert result.disposition is TriggerDisposition.NO_TRIGGER
    assert result.reason == "observe_mode"


def test_guided_selects_at_most_one_primary_learning_point() -> None:
    result = select_learning_opportunity(context=TaskContext(), mode=InteractionMode.GUIDED, candidate_concepts=["ownership boundary", "retry semantics"])
    assert result.disposition is TriggerDisposition.LEARNING_OPPORTUNITY
    assert len(result.opportunities) == MAX_PRIMARY_LEARNING_POINTS_PER_TASK == 1
    assert result.opportunities[0].concept == "ownership boundary"


def test_practice_still_allows_zero_trigger_when_no_candidate() -> None:
    result = select_learning_opportunity(context=TaskContext(), mode=InteractionMode.PRACTICE, candidate_concepts=[])
    assert result.disposition is TriggerDisposition.NO_TRIGGER
    assert result.reason == "no_candidate"


def test_result_constructor_enforces_one_point_ceiling() -> None:
    with pytest.raises(ValueError, match="at most one"):
        TriggerResult(
            TriggerDisposition.LEARNING_OPPORTUNITY,
            opportunities=(LearningOpportunity("a"), LearningOpportunity("b")),
        )
