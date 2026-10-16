"""Write-time validation of learning events at the append sink.

Events must conform to ``schemas/learning-event.v1.json`` (which forbids source
excerpts and other unknown fields) and must not claim a ``recommended_level``
above what the attempt fields allow, as derived by ``assess_judgment``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from .assessment import (
    CueLevel,
    EvidenceProvenance,
    EvidenceTiming,
    JudgmentEvidence,
    MasteryLevel,
    TransferDistance,
    assess_judgment,
)
from .state import StateUnavailableError

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "learning-event.v1.json"

_LEVEL_ORDER = {"UNASSESSED": -1, "L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4}
_TYPES = {
    "string": str,
    "boolean": bool,
    "object": Mapping,
    "array": list,
    "null": type(None),
}


class LearningEventValidationError(ValueError):
    """Raised when an event violates the learning-event contract."""


def _load_schema() -> Mapping[str, Any]:
    try:
        return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StateUnavailableError("learning-event schema is unavailable") from exc


def _type_ok(value: Any, expected: str) -> bool:
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, _TYPES[expected])


def _validate(value: Any, schema: Mapping[str, Any], path: str) -> None:
    """Validate the JSON Schema subset used by learning-event.v1 (no new dependency)."""

    if "const" in schema and value != schema["const"]:
        raise LearningEventValidationError(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        raise LearningEventValidationError(f"{path}: not an allowed value")
    declared = schema.get("type")
    if declared is not None:
        names = [declared] if isinstance(declared, str) else list(declared)
        if not any(_type_ok(value, name) for name in names):
            raise LearningEventValidationError(f"{path}: expected type {names}")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            raise LearningEventValidationError(f"{path}: too short")
        if schema.get("format") == "date-time":
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError as exc:
                raise LearningEventValidationError(f"{path}: not a date-time") from exc
    if isinstance(value, (int, float)) and not isinstance(value, bool) and "minimum" in schema:
        if value < schema["minimum"]:
            raise LearningEventValidationError(f"{path}: below minimum")
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            _validate(item, schema["items"], f"{path}[{index}]")
    if isinstance(value, Mapping):
        properties = schema.get("properties", {})
        for name in schema.get("required", ()):
            if name not in value:
                raise LearningEventValidationError(f"{path}: missing required {name!r}")
        if schema.get("additionalProperties") is False:
            for name in value:
                if name not in properties:
                    raise LearningEventValidationError(f"{path}: unexpected property {name!r}")
        for name, sub in properties.items():
            if name in value:
                _validate(value[name], sub, f"{path}.{name}")


def validate_event_schema(event: Mapping[str, Any]) -> None:
    _validate(event, _load_schema(), "event")


def _enum(enum_cls: Any, raw: Any, default: Any) -> Any:
    return default if raw is None else enum_cls(raw)


def event_level_ceiling(event: Mapping[str, Any], *, prior_level: str | None) -> str:
    """Highest level the event's attempt fields allow, via ``assess_judgment``.

    The bound is derived from the attempt fields only (user_attempted,
    ai_explanation_only, evidence_timing, evidence_provenance, cue_level,
    transfer_distance). Optional free-form ``evidence`` content is an unverified
    self-report, so the evidence-content gates are assumed satisfied; the result
    is an upper bound, never a grant.
    """

    attempt = event.get("attempt") or {}
    assessment = event.get("assessment") or {}
    evidence = JudgmentEvidence(
        goals=("-",),
        constraints=("-",),
        alternatives=("-",),
        trade_offs=("-",),
        evidence=("-",),
        falsifier="-",
        provenance=_enum(EvidenceProvenance, attempt.get("evidence_provenance"), EvidenceProvenance.USER_AUTHORED),
    )
    prior = MasteryLevel(prior_level) if prior_level else None
    result = assess_judgment(
        current_level=prior,
        user_attempted=attempt.get("user_attempted", True),
        ai_explanation_only=attempt.get("ai_explanation_only", False),
        evidence=evidence,
        cue_level=_enum(CueLevel, attempt.get("cue_level"), CueLevel.HEAVY),
        transfer_distance=_enum(TransferDistance, attempt.get("transfer_distance"), TransferDistance.SAME_STRUCTURE),
        delay=attempt.get("delay"),
        explicit_not_yet_encountered=assessment.get("classification") == "EXPLICIT_NOT_YET_ENCOUNTERED",
        evidence_timing=_enum(EvidenceTiming, attempt.get("evidence_timing"), EvidenceTiming.PRE_EVIDENCE),
    )
    return result.recommended_level.value


def validate_learning_event(
    event: Mapping[str, Any], *, prior_events: Sequence[Mapping[str, Any]] = ()
) -> None:
    """Reject non-conforming events and recommended_level above the evidence ceiling."""

    validate_event_schema(event)
    capability = event["capability"]
    prior_level: str | None = None
    for existing in prior_events:
        cap = existing.get("capability")
        if not isinstance(cap, Mapping):
            continue
        if cap.get("domain") != capability["domain"] or cap.get("concept") != capability["concept"]:
            continue
        level = (existing.get("assessment") or {}).get("recommended_level")
        if level in _LEVEL_ORDER and (
            prior_level is None or _LEVEL_ORDER[level] > _LEVEL_ORDER[prior_level]
        ):
            prior_level = level
    ceiling = event_level_ceiling(event, prior_level=prior_level)
    claimed = event["assessment"]["recommended_level"]
    if _LEVEL_ORDER[claimed] > _LEVEL_ORDER[ceiling]:
        raise LearningEventValidationError(
            f"recommended_level {claimed} exceeds the attempt evidence ceiling {ceiling}"
        )


def clamp_recommended_level(event: Mapping[str, Any], *, prior_level: str | None) -> str:
    """Level a projection may credit for an already-persisted event.

    Never exceeds the attempt-evidence ceiling, so a schema-valid event that
    over-claims (or a hand-edited ledger line) cannot raise mastery. An event
    whose attempt fields cannot be interpreted credits nothing (``UNASSESSED``).
    """

    assessment = event.get("assessment")
    claimed = assessment.get("recommended_level") if isinstance(assessment, Mapping) else None
    if claimed not in _LEVEL_ORDER:
        return "UNASSESSED"
    try:
        ceiling = event_level_ceiling(event, prior_level=prior_level)
    except (ValueError, TypeError, AttributeError):
        return "UNASSESSED"
    return claimed if _LEVEL_ORDER[claimed] <= _LEVEL_ORDER[ceiling] else ceiling
