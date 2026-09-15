"""Descriptive G9-prep observation aggregation.

These metrics describe interaction and transfer evidence. They do not establish
that RepoLearn caused a learning improvement.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable


DESCRIPTIVE_NOT_CAUSAL = (
    "Descriptive RepoLearn readiness evidence only; these metrics are not causal proof of learning effectiveness."
)


@dataclass(frozen=True)
class EvaluationObservation:
    task_id: str
    triggered: bool
    interrupted: bool
    skipped: bool
    added_turns: int
    added_time_seconds: float
    added_tokens: int
    added_context_tokens: int
    initial_cue_count: int
    final_cue_count: int
    learning_prompt_at: datetime | None
    transfer_observed_at: datetime | None
    materially_different_transfer: bool

    def __post_init__(self) -> None:
        if not self.task_id.strip():
            raise ValueError("task_id must be non-empty")
        if not self.triggered and (self.interrupted or self.skipped):
            raise ValueError("no-trigger observations cannot be interrupted or skipped")
        for name, value in (
            ("added_turns", self.added_turns),
            ("added_tokens", self.added_tokens),
            ("added_context_tokens", self.added_context_tokens),
            ("initial_cue_count", self.initial_cue_count),
            ("final_cue_count", self.final_cue_count),
        ):
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
        if self.added_time_seconds < 0:
            raise ValueError("added_time_seconds must be non-negative")
        if self.final_cue_count > self.initial_cue_count:
            raise ValueError("final cue demand cannot exceed the observation's initial cue demand")
        if self.materially_different_transfer:
            if self.learning_prompt_at is None or self.transfer_observed_at is None:
                raise ValueError("materially different transfer requires both prompt and transfer timestamps")
            if self.transfer_observed_at < self.learning_prompt_at:
                raise ValueError("transfer observation cannot precede its learning prompt")
        if (self.learning_prompt_at is None) != (self.transfer_observed_at is None):
            raise ValueError("prompt and transfer timestamps must be supplied together")
        for timestamp in (self.learning_prompt_at, self.transfer_observed_at):
            if timestamp is not None and timestamp.tzinfo is None:
                raise ValueError("evaluation timestamps must be timezone-aware")

    @property
    def cue_reduced(self) -> bool:
        return self.triggered and self.initial_cue_count > self.final_cue_count

    @property
    def delayed_material_transfer(self) -> bool:
        if not self.materially_different_transfer:
            return False
        assert self.learning_prompt_at is not None
        assert self.transfer_observed_at is not None
        return self.transfer_observed_at - self.learning_prompt_at >= timedelta(hours=24)


@dataclass(frozen=True)
class EvaluationReport:
    observation_count: int
    trigger_count: int
    no_trigger_count: int
    interruption_rate: float
    skip_rate: float
    total_added_turns: int
    total_added_time_seconds: float
    total_added_tokens: int
    total_added_context_tokens: int
    cue_reduction_count: int
    delayed_material_transfer_count: int
    evidence_statement: str = DESCRIPTIVE_NOT_CAUSAL


def aggregate_observations(observations: Iterable[EvaluationObservation]) -> EvaluationReport:
    items = tuple(observations)
    count = len(items)
    triggers = sum(item.triggered for item in items)
    interruptions = sum(item.interrupted for item in items)
    skips = sum(item.skipped for item in items)
    denominator = count or 1
    return EvaluationReport(
        observation_count=count,
        trigger_count=triggers,
        no_trigger_count=count - triggers,
        interruption_rate=interruptions / denominator if count else 0.0,
        skip_rate=skips / denominator if count else 0.0,
        total_added_turns=sum(item.added_turns for item in items),
        total_added_time_seconds=sum(item.added_time_seconds for item in items),
        total_added_tokens=sum(item.added_tokens for item in items),
        total_added_context_tokens=sum(item.added_context_tokens for item in items),
        cue_reduction_count=sum(item.cue_reduced for item in items),
        delayed_material_transfer_count=sum(item.delayed_material_transfer for item in items),
    )
