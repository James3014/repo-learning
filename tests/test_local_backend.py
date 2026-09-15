from __future__ import annotations

import json

import pytest

from repolearn import BackendConflictError, LocalFileBackend, StaleProjectionError


def event(event_id: str = "ev-1", *, level: str = "L2", observed_at: str = "2026-09-15T12:00:00Z") -> dict:
    return {
        "schema": "repolearn.learning_event.v1",
        "event_id": event_id,
        "observed_at": observed_at,
        "profile_id": "james",
        "context": {"repository": "example/repo"},
        "capability": {"domain": "authority-boundaries", "concept": "single owner"},
        "attempt": {
            "judgment": "keep one canonical owner",
            "cue_level": "LIGHT",
            "transfer_distance": "NEAR_TRANSFER",
        },
        "assessment": {
            "classification": "EXPLAINED_WITH_EVIDENCE",
            "recommended_level": level,
            "rationale": "bounded fixture",
        },
    }


def test_local_backend_is_idempotent_and_projects_deterministically(tmp_path):
    backend = LocalFileBackend(tmp_path)
    payload = event()

    assert backend.append_learning_event("james", payload) == "ev-1"
    assert backend.append_learning_event("james", payload) == "ev-1"

    first = backend.refresh_projection("james")
    second = backend.refresh_projection("james")
    assert first == second
    assert first["domains"]["authority-boundaries"]["level"] == "L2"
    assert first["domains"]["authority-boundaries"]["evidence_count"] == 1
    assert backend.read_current_state("james") == first
    assert len(backend.read_related_history("james")) == 1


def test_event_identity_conflict_fails_closed(tmp_path):
    backend = LocalFileBackend(tmp_path)
    backend.append_learning_event("james", event())
    changed = event(level="L3")

    with pytest.raises(BackendConflictError):
        backend.append_learning_event("james", changed)


def test_stale_projection_is_detected(tmp_path):
    backend = LocalFileBackend(tmp_path)
    backend.append_learning_event("james", event())
    backend.refresh_projection("james")

    state_path = tmp_path / "profiles" / "james" / "state.json"
    state = json.loads(state_path.read_text())
    state["source"]["content_hash"] = "0" * 64
    state_path.write_text(json.dumps(state))

    with pytest.raises(StaleProjectionError):
        backend.read_current_state("james")


def test_private_files_are_owner_only(tmp_path):
    backend = LocalFileBackend(tmp_path)
    backend.append_learning_event("james", event())
    backend.refresh_projection("james")

    events_mode = (tmp_path / "profiles" / "james" / "events.jsonl").stat().st_mode & 0o777
    state_mode = (tmp_path / "profiles" / "james" / "state.json").stat().st_mode & 0o777
    assert events_mode == 0o600
    assert state_mode == 0o600


def test_profile_path_traversal_is_rejected(tmp_path):
    backend = LocalFileBackend(tmp_path)
    with pytest.raises(ValueError):
        backend.append_learning_event("../escape", event())
