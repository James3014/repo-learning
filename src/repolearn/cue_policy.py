"""Small evidence-derived cue-fading policy.

This is intentionally not a psychometric forgetting model. Evidence events record
facts; this module alone decides whether those facts justify temporary silent cue
fading.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any


MIN_FADING_DELAY_HOURS = 24.0
FADING_VALIDITY_DAYS = 30


class AttemptIndependence(str, Enum):
    GUIDED = "GUIDED"
    SPONTANEOUS = "SPONTANEOUS"
    INDEPENDENT = "INDEPENDENT"


@dataclass(frozen=True)
class FadingDecision:
    eligible: bool
    valid_until: str | None = None
    basis_event_id: str | None = None
    reason: str = ""


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _format_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def derive_fading_decision(
    event: Mapping[str, Any],
    *,
    previous_observed_at: str | None = None,
) -> FadingDecision:
    """Derive temporary cue suppression from evidence facts.

    Legacy silent_cue_fading_eligible and reported delay_hours fields are
    deliberately not authority. Delay is verified from durable event timestamps.
    """

    attempt = event.get("attempt", {})
    assessment = event.get("assessment", {})
    if not isinstance(attempt, Mapping) or not isinstance(assessment, Mapping):
        return FadingDecision(False, reason="missing_attempt_or_assessment")

    observed_at = _parse_datetime(event.get("observed_at"))
    previous = _parse_datetime(previous_observed_at)
    if observed_at is None:
        return FadingDecision(False, reason="invalid_observed_at")
    if previous is None:
        return FadingDecision(False, reason="no_prior_exposure")
    verified_delay_hours = (observed_at - previous).total_seconds() / 3600.0

    checks = (
        (attempt.get("user_attempted", True) is not False, "no_user_attempt"),
        (attempt.get("ai_explanation_only", False) is not True, "ai_explanation_only"),
        (attempt.get("evidence_provenance") == "USER_AUTHORED", "not_user_authored"),
        (attempt.get("evidence_timing") == "PRE_EVIDENCE", "not_pre_evidence"),
        (attempt.get("independence") == AttemptIndependence.INDEPENDENT.value, "not_independent"),
        (attempt.get("cue_level") == "NONE", "cue_present"),
        (attempt.get("transfer_distance") in {"NEAR_TRANSFER", "FAR_TRANSFER"}, "not_transfer"),
        (verified_delay_hours >= MIN_FADING_DELAY_HOURS, "insufficient_delay"),
        (
            assessment.get("classification")
            in {"TRANSFER_WITH_TRADEOFFS", "INDEPENDENT_FALSIFIER"},
            "insufficient_assessment",
        ),
        (assessment.get("recommended_level") in {"L3", "L4"}, "insufficient_level"),
        (assessment.get("requires_reassessment", False) is not True, "reassessment_required"),
        (
            not isinstance(assessment.get("reassessment_of_event_id"), str),
            "reassessment_resolution_not_fresh_evidence",
        ),
    )
    for passed, reason in checks:
        if not passed:
            return FadingDecision(False, reason=reason)

    event_id = event.get("event_id")
    if not isinstance(event_id, str) or not event_id.strip():
        return FadingDecision(False, reason="missing_event_id")

    valid_until = observed_at + timedelta(days=FADING_VALIDITY_DAYS)
    return FadingDecision(
        True,
        valid_until=_format_datetime(valid_until),
        basis_event_id=event_id,
        reason="delayed_independent_transfer",
    )


def fading_is_current(concept_state: Mapping[str, Any], *, now: datetime | None = None) -> bool:
    valid_until = _parse_datetime(concept_state.get("fading_valid_until"))
    if valid_until is None:
        return False
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc) <= valid_until
