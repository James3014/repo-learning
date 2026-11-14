from __future__ import annotations

import errno
import os
from pathlib import Path
import subprocess
import tomllib
import pytest

from repolearn import BackendConflictError, LocalFileBackend, StateUnavailableError


def event(event_id: str = "ev-1") -> dict:
    return {
        "schema": "repolearn.learning_event.v1",
        "event_id": event_id,
        "observed_at": "2026-09-15T12:00:00Z",
        "profile_id": "james",
        "context": {"repository": "example/repo"},
        "capability": {"domain": "authority-boundaries", "concept": "single owner"},
        "attempt": {"judgment": "one owner", "cue_level": "LIGHT", "transfer_distance": "NEAR_TRANSFER"},
        "assessment": {"classification": "EXPLAINED_WITH_EVIDENCE", "recommended_level": "L2", "rationale": "fixture"},
    }


def _install_verifier(root: Path) -> None:
    verifier_dir = root / ".nexus-core"
    verifier_dir.mkdir(exist_ok=True)
    source = Path(__file__).parents[1] / ".nexus-core/trusted_git_diff.py"
    (verifier_dir / source.name).write_bytes(source.read_bytes())


def test_issue_verifiers_reject_replacement_refs_and_disable_them(tmp_path):
    config = tomllib.loads((Path(__file__).parents[1] / ".nexus-core/config.toml").read_text())
    verifiers = {entry["id"]: entry for entry in config["verifiers"]}
    guarded_diff_check = list(verifiers["diff-check"]["command"])
    assert guarded_diff_check == ["/usr/bin/env", "python3", ".nexus-core/trusted_git_diff.py"]

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    _install_verifier(tmp_path)
    subprocess.run(["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "--allow-empty", "-qm", "base"], cwd=tmp_path, check=True)
    base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()
    (tmp_path / "bad.txt").write_text("trailing space \n")
    subprocess.run(["git", "add", "bad.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "-qm", "replacement"], cwd=tmp_path, check=True)
    replacement = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()
    subprocess.run(["git", "reset", "--hard", base], cwd=tmp_path, check=True)
    (tmp_path / "bad.txt").write_text("trailing space \n")
    subprocess.run(["git", "add", "bad.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "update-ref", "refs/replace/" + base, replacement], cwd=tmp_path, check=True)

    # Demonstrate the setting changes the actual diff result: with replacement
    # objects enabled, the staged file matches the replacement commit; disabled,
    # the staged trailing whitespace is compared to the empty base commit.
    ordinary_env = dict(os.environ)
    ordinary_env.pop("GIT_NO_REPLACE_OBJECTS", None)
    ordinary = subprocess.run(["git", "diff", "--cached", "--check", "HEAD"], cwd=tmp_path, env=ordinary_env, capture_output=True)
    disabled_env = dict(ordinary_env, GIT_NO_REPLACE_OBJECTS="1")
    disabled = subprocess.run(["git", "diff", "--cached", "--check", "HEAD"], cwd=tmp_path, env=disabled_env, capture_output=True)
    assert ordinary.returncode == 0
    assert disabled.returncode != 0

    shadow = tmp_path / "shadow-bin"
    shadow.mkdir()
    fake_git = shadow / "git"
    fake_git.write_text("#!/bin/sh\nif [ \"$1\" = --version ]; then echo 'git version fake'; fi\nexit 0\n")
    fake_git.chmod(0o755)
    verifier_env = dict(os.environ, PATH=str(shadow) + os.pathsep + os.environ["PATH"])
    verifier_env.pop("GIT_NO_REPLACE_OBJECTS", None)

    result = subprocess.run(guarded_diff_check, cwd=tmp_path, env=verifier_env, text=True, capture_output=True)
    assert result.returncode != 0
    assert "NEXUS_REPLACE_REFS_PRESENT" in result.stderr

    missing_git = dict(verifier_env, NEXUS_GIT_PATH=str(tmp_path / "missing-git"))
    missing = subprocess.run(guarded_diff_check, cwd=tmp_path, env=missing_git, text=True, capture_output=True)
    assert missing.returncode == 127
    assert "NEXUS_GIT_PATH" in missing.stderr


def test_read_state_cannot_follow_state_file_swapped_after_validation(tmp_path, monkeypatch):
    backend = LocalFileBackend(tmp_path)
    backend.append_learning_event("james", event())
    backend.refresh_projection("james")
    state_path = tmp_path / "profiles/james/state.json"
    outside = tmp_path / "outside.json"
    outside.write_text('{"outside_secret":"must not be read"}')
    original_is_symlink = Path.is_symlink
    original_open = os.open
    injected = False
    rejected_errno = []

    def swap(path: Path):
        nonlocal injected
        if not injected:
            injected = True
            state_path.unlink()
            state_path.symlink_to(outside)

    def swap_after_check(path: Path):
        if path == state_path:
            is_link = original_is_symlink(path)
            swap(path)
            return is_link
        return original_is_symlink(path)

    def swap_before_open(path, flags, *args, **kwargs):
        if path == "state.json" and kwargs.get("dir_fd") is not None:
            swap(state_path)
        try:
            return original_open(path, flags, *args, **kwargs)
        except OSError as exc:
            if path == "state.json" and kwargs.get("dir_fd") is not None:
                rejected_errno.append(exc.errno)
            raise

    monkeypatch.setattr(Path, "is_symlink", swap_after_check)
    monkeypatch.setattr("os.open", swap_before_open)
    with pytest.raises((OSError, ValueError, StateUnavailableError)):
        backend.read_current_state("james")
    assert injected
    assert rejected_errno == [errno.ELOOP]
    assert outside.read_text() == '{"outside_secret":"must not be read"}'


def test_local_backend_fails_closed_without_dir_fd_support(tmp_path, monkeypatch):
    import repolearn.backends as backends

    monkeypatch.setattr(backends, "_HAS_SAFE_DIR_FD", False, raising=False)
    operations = (
        lambda backend: backend.read_current_state("james"),
        lambda backend: backend.append_learning_event("james", event()),
        lambda backend: backend.refresh_projection("james"),
        lambda backend: backend.export_profile("james"),
        lambda backend: backend.delete_profile("james"),
    )
    for operation in operations:
        with pytest.raises(StateUnavailableError, match="platform lacks required"):
            operation(LocalFileBackend(tmp_path))


def test_dir_fd_capability_requires_listdir_fd_support(tmp_path, monkeypatch):
    import repolearn.backends as backends

    monkeypatch.setattr(os, "supports_fd", os.supports_fd - {os.listdir})
    supports_dir_fd = getattr(backends, "_has_safe_dir_fd_support", lambda: True)()
    monkeypatch.setattr(backends, "_HAS_SAFE_DIR_FD", supports_dir_fd, raising=False)
    with pytest.raises(StateUnavailableError, match="platform lacks required"):
        backends.LocalFileBackend(tmp_path).delete_profile("james")


def test_append_cannot_write_through_events_file_swapped_after_validation(tmp_path, monkeypatch):
    backend = LocalFileBackend(tmp_path)
    backend.append_learning_event("james", event())
    events_path = tmp_path / "profiles/james/events.jsonl"
    outside = tmp_path / "outside.jsonl"
    outside.write_text("")
    original_mkdir = Path.mkdir
    original_open = os.open
    injected = False

    def swap_after_mkdir(path: Path, *args, **kwargs):
        nonlocal injected
        result = original_mkdir(path, *args, **kwargs)
        if path == events_path.parent and not injected:
            injected = True
            events_path.unlink()
            events_path.symlink_to(outside)
        return result

    def swap_before_open(path, flags, *args, **kwargs):
        nonlocal injected
        if (
            path == "events.jsonl"
            and kwargs.get("dir_fd") is not None
            and flags & os.O_APPEND
            and not injected
        ):
            injected = True
            events_path.unlink()
            events_path.symlink_to(outside)
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", swap_after_mkdir)
    monkeypatch.setattr(os, "open", swap_before_open)
    try:
        backend.append_learning_event("james", event("ev-2"))
    except OSError:
        pass
    assert injected
    assert outside.read_text() == ""


def test_delete_cannot_unlink_files_after_profile_directory_swap(tmp_path, monkeypatch):
    backend = LocalFileBackend(tmp_path)
    backend.append_learning_event("james", event())
    profile = tmp_path / "profiles/james"
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "events.jsonl"
    secret.write_text("keep")
    original_iterdir = Path.iterdir
    original_listdir = os.listdir
    swapped = False

    def swap_then_iterdir(path: Path):
        nonlocal swapped
        if path == profile and not swapped:
            swapped = True
            profile.rename(tmp_path / "profiles/james.saved")
            profile.symlink_to(outside, target_is_directory=True)
        return original_iterdir(path)

    def swap_before_listdir(path):
        nonlocal swapped
        if isinstance(path, int) and not swapped:
            swapped = True
            profile.rename(tmp_path / "profiles/james.saved")
            profile.symlink_to(outside, target_is_directory=True)
        return original_listdir(path)

    monkeypatch.setattr(Path, "iterdir", swap_then_iterdir)
    monkeypatch.setattr(os, "listdir", swap_before_listdir)
    try:
        backend.delete_profile("james")
    except (OSError, BackendConflictError):
        pass
    assert swapped
    assert secret.read_text() == "keep"
    assert (tmp_path / "profiles/james.saved/events.jsonl").exists()


def test_delete_does_not_remove_replacement_profile_directory(tmp_path, monkeypatch):
    backend = LocalFileBackend(tmp_path)
    backend.append_learning_event("james", event())
    profile = tmp_path / "profiles/james"
    replacement = tmp_path / "profiles/james.replacement"
    replacement.mkdir()
    sentinel = replacement / "sentinel"
    sentinel.write_text("keep")
    original_stat = os.stat
    profile_stat_count = 0

    def swap_after_final_identity_check(path, *args, **kwargs):
        nonlocal profile_stat_count
        result = original_stat(path, *args, **kwargs)
        if path == "james" and kwargs.get("dir_fd") is not None:
            profile_stat_count += 1
            if profile_stat_count == 3:
                profile.rename(tmp_path / "profiles/james.saved")
                replacement.rename(profile)
        return result

    monkeypatch.setattr(os, "stat", swap_after_final_identity_check)
    with pytest.raises(BackendConflictError, match="changed during deletion"):
        backend.delete_profile("james")
    assert (profile / "sentinel").read_text() == "keep"
    assert profile.is_dir()
