from __future__ import annotations

import copy

import pytest

from repolearn import LocalFileBackend
from repolearn.event_validation import LearningEventValidationError


def event(event_id="e1", *, level="L4", **attempt):
    return {
        "schema": "repolearn.learning_event.v1",
        "event_id": event_id,
        "observed_at": "2026-10-01T00:00:00Z",
        "profile_id": "p1",
        "context": {"repository": "example/repo"},
        "capability": {"domain": "security", "concept": "authz"},
        "attempt": {
            "cue_level": "NONE",
            "transfer_distance": "FAR_TRANSFER",
            "judgment": "",
            "user_attempted": True,
            "ai_explanation_only": False,
            "evidence_timing": "PRE_EVIDENCE",
            "evidence_provenance": "USER_AUTHORED",
            **attempt,
        },
        "assessment": {"classification": "INDEPENDENT_FALSIFIER", "recommended_level": level, "rationale": "x"},
    }


def _ledger(tmp_path):
    return tmp_path / "profiles" / "p1" / "events.jsonl"


def test_honest_user_authored_pre_evidence_event_is_accepted(tmp_path):
    backend = LocalFileBackend(tmp_path)
    assert backend.append_learning_event("p1", event()) == "e1"
    assert backend.refresh_projection("p1")["concepts"]["authz"]["level"] == "L4"


@pytest.mark.parametrize(
    "attempt",
    [
        {"user_attempted": False, "ai_explanation_only": True,
         "evidence_timing": "POST_EVIDENCE", "evidence_provenance": "AI_EXPLANATION"},
        {"ai_explanation_only": True},
        {"evidence_timing": "POST_EVIDENCE"},
        {"evidence_provenance": "AI_REFORMULATED"},
        {"user_attempted": False},
        {"cue_level": "HEAVY"},
        {"transfer_distance": "SAME_STRUCTURE"},
    ],
)
def test_recommended_level_above_attempt_ceiling_is_rejected_and_not_persisted(tmp_path, attempt):
    backend = LocalFileBackend(tmp_path)
    with pytest.raises(LearningEventValidationError, match="exceeds"):
        backend.append_learning_event("p1", event(**attempt))
    assert not _ledger(tmp_path).exists() or _ledger(tmp_path).read_text() == ""
    assert not backend.read_related_history("p1")


def test_schema_forbidden_source_excerpt_is_rejected_and_not_persisted(tmp_path):
    backend = LocalFileBackend(tmp_path)
    bad = event(level="L1", cue_level="HEAVY", transfer_distance="SAME_STRUCTURE")
    bad["source_excerpt"] = "def secret_internal(): PRIVATE_KEY='...'"
    with pytest.raises(LearningEventValidationError, match="source_excerpt"):
        backend.append_learning_event("p1", bad)
    assert not _ledger(tmp_path).exists() or "PRIVATE_KEY" not in _ledger(tmp_path).read_text()


@pytest.mark.parametrize(
    "mutate",
    [
        lambda e: e["context"].clear(),
        lambda e: e["attempt"].update(cue_level="MEDIUM"),
        lambda e: e["assessment"].update(recommended_level="L9"),
        lambda e: e.pop("assessment"),
        lambda e: e.update(schema="other"),
    ],
)
def test_schema_violations_are_rejected(tmp_path, mutate):
    backend = LocalFileBackend(tmp_path)
    bad = copy.deepcopy(event())
    mutate(bad)
    with pytest.raises(LearningEventValidationError):
        backend.append_learning_event("p1", bad)
