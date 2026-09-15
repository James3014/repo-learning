from __future__ import annotations

from datetime import datetime, timezone

import pytest

from repolearn.evaluation import DESCRIPTIVE_NOT_CAUSAL, EvaluationObservation, aggregate_observations


def observation(**changes) -> EvaluationObservation:
    values = {
        "task_id": "task-1",
        "triggered": True,
        "interrupted": True,
        "skipped": False,
        "added_turns": 1,
        "added_time_seconds": 30.0,
        "added_tokens": 100,
        "added_context_tokens": 40,
        "initial_cue_count": 2,
        "final_cue_count": 1,
        "learning_prompt_at": datetime(2026, 9, 14, tzinfo=timezone.utc),
        "transfer_observed_at": datetime(2026, 9, 16, tzinfo=timezone.utc),
        "materially_different_transfer": True,
    }
    values.update(changes)
    return EvaluationObservation(**values)


def test_aggregation_covers_trigger_cost_skip_cues_and_delayed_transfer() -> None:
    report = aggregate_observations(
        [
            observation(),
            observation(
                task_id="task-2",
                triggered=False,
                interrupted=False,
                skipped=False,
                added_turns=0,
                added_time_seconds=0,
                added_tokens=0,
                added_context_tokens=0,
                initial_cue_count=0,
                final_cue_count=0,
                learning_prompt_at=None,
                transfer_observed_at=None,
                materially_different_transfer=False,
            ),
            observation(task_id="task-3", skipped=True, interrupted=False, added_turns=0),
        ]
    )
    assert report.observation_count == 3
    assert report.trigger_count == 2
    assert report.no_trigger_count == 1
    assert report.interruption_rate == pytest.approx(1 / 3)
    assert report.skip_rate == pytest.approx(1 / 3)
    assert report.total_added_turns == 1
    assert report.total_added_time_seconds == 60.0
    assert report.total_added_tokens == 200
    assert report.total_added_context_tokens == 80
    assert report.cue_reduction_count == 2
    assert report.delayed_material_transfer_count == 2
    assert report.evidence_statement == DESCRIPTIVE_NOT_CAUSAL


def test_transfer_before_24_hours_is_not_delayed_evidence() -> None:
    report = aggregate_observations(
        [observation(transfer_observed_at=datetime(2026, 9, 14, 23, tzinfo=timezone.utc))]
    )
    assert report.delayed_material_transfer_count == 0


@pytest.mark.parametrize(
    "changes",
    [
        {"triggered": False, "interrupted": True},
        {"triggered": False, "skipped": True},
        {"added_turns": -1},
        {"added_time_seconds": -1},
        {"final_cue_count": 3},
        {"materially_different_transfer": True, "transfer_observed_at": None},
    ],
)
def test_invalid_observation_is_rejected(changes: dict) -> None:
    with pytest.raises(ValueError):
        observation(**changes)
