from __future__ import annotations

import json
from pathlib import Path

import pytest

from repolearn import BackendConflictError, LocalFileBackend, ProjectionConflictError, StaleProjectionError


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


def test_contradictory_assessed_levels_require_reassessment(tmp_path):
    backend = LocalFileBackend(tmp_path)
    backend.append_learning_event("james", event("ev-1", level="L2"))
    backend.append_learning_event("james", event("ev-2", level="L3", observed_at="2026-09-16T12:00:00Z"))

    with pytest.raises(ProjectionConflictError, match="reassessment"):
        backend.refresh_projection("james")


def test_repeated_same_level_and_unassessed_evidence_do_not_create_false_conflict(tmp_path):
    backend = LocalFileBackend(tmp_path)
    backend.append_learning_event("james", event("ev-1", level="UNASSESSED"))
    backend.append_learning_event("james", event("ev-2", level="L2", observed_at="2026-09-16T12:00:00Z"))
    backend.append_learning_event("james", event("ev-3", level="L2", observed_at="2026-09-17T12:00:00Z"))

    state = backend.refresh_projection("james")
    assert state["domains"]["authority-boundaries"]["level"] == "L2"
    assert state["domains"]["authority-boundaries"]["evidence_count"] == 3


def test_profile_export_is_deterministic_and_bound_to_valid_projection(tmp_path):
    backend = LocalFileBackend(tmp_path)
    backend.append_learning_event("james", event())
    backend.refresh_projection("james")

    first = backend.export_profile("james")
    second = backend.export_profile("james")
    assert first == second
    payload = json.loads(first)
    assert payload["schema"] == "repolearn.profile_export.v1"
    assert payload["profile_id"] == "james"
    assert payload["events"] == [event()]
    assert payload["state"]["source"]["content_hash"]


def test_delete_and_reset_are_profile_scoped(tmp_path):
    backend = LocalFileBackend(tmp_path)
    backend.append_learning_event("james", event())
    backend.refresh_projection("james")
    backend.append_learning_event("other", {**event(), "event_id": "other-1", "profile_id": "other"})
    backend.refresh_projection("other")

    assert backend.delete_profile("james")
    assert not (tmp_path / "profiles" / "james").exists()
    assert (tmp_path / "profiles" / "other" / "events.jsonl").exists()

    reset = backend.reset_profile("james")
    assert reset["domains"] == {}
    assert backend.read_related_history("james") == ()


def test_data_controls_reject_symlinked_profile_path(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    (profiles / "james").symlink_to(outside, target_is_directory=True)
    backend = LocalFileBackend(tmp_path)

    with pytest.raises(ValueError, match="symlink"):
        backend.export_profile("james")
    with pytest.raises(ValueError, match="symlink"):
        backend.delete_profile("james")


def test_delete_refuses_unrecognized_profile_files(tmp_path):
    backend = LocalFileBackend(tmp_path)
    backend.append_learning_event("james", event())
    profile = tmp_path / "profiles" / "james"
    (profile / "keep.txt").write_text("do not delete")

    with pytest.raises(BackendConflictError, match="unrecognized"):
        backend.delete_profile("james")
    assert (profile / "keep.txt").exists()


def test_backend_rejects_symlinked_data_files(tmp_path):
    profile = tmp_path / "profiles" / "james"
    profile.mkdir(parents=True)
    outside = tmp_path / "outside-events"
    outside.write_text("")
    (profile / "events.jsonl").symlink_to(outside)
    backend = LocalFileBackend(tmp_path)

    with pytest.raises(ValueError, match="symlinks"):
        backend.read_related_history("james")
    with pytest.raises(ValueError, match="symlinks"):
        backend.append_learning_event("james", event())
