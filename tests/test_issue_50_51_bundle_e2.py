"""Issue #50 / #51 reproducers asserted at the enforcing sinks."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from repolearn import LocalFileBackend
from repolearn.deployment import DeploymentDefect, inspect_skill_directory, sync_skill_install
from repolearn.event_validation import LearningEventValidationError

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skills" / "repo-learning"


def _check(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(REPO / "scripts" / "install_skill.py"), "--root", str(root), "--check"],
        capture_output=True, text=True,
    )


@pytest.mark.parametrize("victim", ["SKILL.md", "references/policy.md", "references/state-contract.md"])
def test_issue_50_deleted_control_file_is_not_current_and_cli_check_fails(tmp_path, victim):
    root = tmp_path / "skills"
    assert sync_skill_install(SKILL, root).current is True
    assert _check(root).returncode == 0
    installed = root / "repo-learning"
    (installed / victim).unlink()
    att = inspect_skill_directory(installed)
    assert att.current is False
    assert att.defect is not DeploymentDefect.NONE
    assert _check(root).returncode != 0


def test_issue_50_unreadable_control_file_is_not_current(tmp_path):
    root = tmp_path / "skills"
    sync_skill_install(SKILL, root)
    target = root / "repo-learning" / "SKILL.md"
    target.unlink()
    target.mkdir()  # read_bytes raises OSError (IsADirectoryError)
    att = inspect_skill_directory(root / "repo-learning")
    assert att.current is False and att.defect is not DeploymentDefect.NONE


def test_issue_50_sync_refuses_source_missing_control_file(tmp_path):
    source = tmp_path / "src-skill"
    shutil.copytree(SKILL, source)
    (source / "references" / "state-contract.md").unlink()
    with pytest.raises(ValueError):
        sync_skill_install(source, tmp_path / "other-root")
    assert not (tmp_path / "other-root" / "repo-learning").exists()


def _event(event_id="e1", *, level="L4", **attempt):
    return {
        "schema": "repolearn.learning_event.v1", "event_id": event_id,
        "observed_at": "2026-10-01T00:00:00Z", "profile_id": "p1",
        "context": {"repository": "example/repo"},
        "capability": {"domain": "security", "concept": "authz"},
        "attempt": {"cue_level": "HEAVY", "transfer_distance": "SAME_STRUCTURE", "judgment": "",
                    "user_attempted": False, "ai_explanation_only": True,
                    "evidence_timing": "POST_EVIDENCE", "evidence_provenance": "AI_EXPLANATION",
                    **attempt},
        "assessment": {"classification": "EXPOSURE_ONLY", "recommended_level": level, "rationale": "x"},
    }


def test_issue_51_issue_reproducer_event_rejected_nothing_on_disk(tmp_path):
    ev = _event()
    ev["source_excerpt"] = "def secret_internal(): PRIVATE_KEY='...'"
    ev["context"] = {}
    backend = LocalFileBackend(tmp_path)
    with pytest.raises(LearningEventValidationError):
        backend.append_learning_event("p1", ev)
    ledger = tmp_path / "profiles" / "p1" / "events.jsonl"
    assert not ledger.exists() or ledger.read_text() == ""


def _write_ledger(tmp_path, events):
    ledger = tmp_path / "profiles" / "p1" / "events.jsonl"
    ledger.parent.mkdir(parents=True)
    ledger.write_text("".join(json.dumps(e) + "\n" for e in events))


def test_issue_51_persisted_overclaiming_event_projects_at_clamped_level(tmp_path):
    _write_ledger(tmp_path, [_event()])  # schema-valid, exposure-only, claims L4
    state = LocalFileBackend(tmp_path).refresh_projection("p1")
    assert state["concepts"]["authz"]["level"] == "UNASSESSED"
    assert state["domains"]["security"]["level"] == "UNASSESSED"


def test_issue_51_persisted_attempt_without_falsifier_claiming_l4_is_clamped_not_crashing(tmp_path):
    honest = _event("e1", level="L1", user_attempted=True, ai_explanation_only=False,
                    evidence_timing="PRE_EVIDENCE", evidence_provenance="USER_AUTHORED")
    over = _event("e2", level="L4", user_attempted=True, ai_explanation_only=False,
                  evidence_timing="PRE_EVIDENCE", evidence_provenance="USER_AUTHORED")
    over["observed_at"] = "2026-10-02T00:00:00Z"
    _write_ledger(tmp_path, [honest, over])
    state = LocalFileBackend(tmp_path).refresh_projection("p1")
    assert state["concepts"]["authz"]["level"] != "L4"


def test_issue_51_persisted_malformed_attempt_does_not_crash_projection(tmp_path):
    bad = _event(level="L3", cue_level="MEDIUM")
    _write_ledger(tmp_path, [bad])
    state = LocalFileBackend(tmp_path).refresh_projection("p1")
    assert state["concepts"]["authz"]["level"] == "UNASSESSED"
