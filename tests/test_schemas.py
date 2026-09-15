from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker, ValidationError


SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"


def load_schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text())


def validator(name: str) -> Draft202012Validator:
    schema = load_schema(name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def test_learning_state_schema_accepts_unassessed() -> None:
    instance = {
        "schema": "repolearn.learning_state.v1",
        "profile_id": "user-1",
        "updated_at": "2026-09-15T15:00:00Z",
        "domains": {"responsibility_boundary": {"level": "UNASSESSED", "evidence_count": 0, "last_event_id": None, "last_observed_at": None}},
        "review_queue": [],
        "source": {"backend": "example", "revision": None, "content_hash": None},
    }
    validator("learning-state.v1.json").validate(instance)


def test_learning_state_schema_rejects_unknown_mastery_level() -> None:
    instance = {
        "schema": "repolearn.learning_state.v1",
        "profile_id": "user-1",
        "updated_at": "2026-09-15T15:00:00Z",
        "domains": {"architecture": {"level": "BEGINNER", "evidence_count": 0}},
        "source": {"backend": "example"},
    }
    with pytest.raises(ValidationError):
        validator("learning-state.v1.json").validate(instance)


def test_learning_event_schema_carries_learning_evidence_not_authority() -> None:
    instance = {
        "schema": "repolearn.learning_event.v1",
        "event_id": "LE-1",
        "observed_at": "2026-09-15T15:00:00Z",
        "profile_id": "user-1",
        "context": {"repository": "example/repo", "revision": "abc", "task_ref": "1"},
        "capability": {"domain": "system_architecture", "concept": "state ownership"},
        "attempt": {"judgment": "Keep one canonical state owner.", "cue_level": "LIGHT", "transfer_distance": "NEAR_TRANSFER", "delay": "7d", "user_attempted": True, "ai_explanation_only": False},
        "evidence": {
            "goals": ["avoid split brain"],
            "constraints": ["multiple clients"],
            "alternatives": ["one backend", "client memory"],
            "trade_offs": ["availability versus consistency"],
            "inspected": ["state contract"],
            "falsifier": "A client must be canonical for an offline-only requirement."
        },
        "assessment": {"classification": "TRANSFER_WITH_TRADEOFFS", "recommended_level": "L3", "rationale": "Evidence-bounded transfer", "mastery_effect": "EVIDENCE_ONLY"}
    }
    validator("learning-event.v1.json").validate(instance)
    assert "merge_authority" not in instance
    assert "release_authority" not in instance


def test_learning_event_schema_rejects_invalid_cue_level() -> None:
    instance = {
        "schema": "repolearn.learning_event.v1",
        "event_id": "LE-1",
        "observed_at": "2026-09-15T15:00:00Z",
        "profile_id": "user-1",
        "context": {"repository": "example/repo"},
        "capability": {"domain": "architecture", "concept": "ownership"},
        "attempt": {"judgment": "", "cue_level": "MEDIUM", "transfer_distance": "SAME_STRUCTURE"},
        "assessment": {"classification": "UNASSESSED", "recommended_level": "UNASSESSED", "rationale": "none"}
    }
    with pytest.raises(ValidationError):
        validator("learning-event.v1.json").validate(instance)


def test_repository_schema_keeps_mastery_out_of_repo_config() -> None:
    valid = {
        "schema": "repolearn.repository.v1",
        "repository": {"id": "example/repo", "default_branch": "main"},
        "learning": {"enabled": True, "default_mode": "guided"},
        "authority": {"source": "AGENTS.md"},
        "privacy": {"allow_source_excerpt_writeback": False, "allow_private_repository_identifier_writeback": False}
    }
    schema_validator = validator("repository.v1.json")
    schema_validator.validate(valid)
    invalid = dict(valid)
    invalid["mastery"] = {"architecture": "L4"}
    with pytest.raises(ValidationError):
        schema_validator.validate(invalid)


def test_repository_schema_rejects_source_excerpt_opt_out_omission() -> None:
    invalid = {
        "schema": "repolearn.repository.v1",
        "repository": {"id": "example/repo"},
        "learning": {"enabled": True, "default_mode": "guided"},
        "authority": {"source": "AGENTS.md"},
        "privacy": {}
    }
    with pytest.raises(ValidationError):
        validator("repository.v1.json").validate(invalid)
