from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import tomllib
import pytest


ROOT = Path(__file__).parents[1]
GIT = "/usr/bin/git"


def _repo(path: Path) -> None:
    subprocess.run([GIT, "init", "-q"], cwd=path, check=True)
    subprocess.run([GIT, "-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "--allow-empty", "-qm", "base"], cwd=path, check=True)


def _run(path: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    config = tomllib.loads((ROOT / ".nexus-core/config.toml").read_text())
    command = config["verifiers"][-1]["command"]
    if command[:1] == ["python3"]:
        verifier_dir = path / ".nexus-core"
        verifier_dir.mkdir(exist_ok=True)
        (verifier_dir / "trusted_git_diff.py").write_bytes((ROOT / command[1]).read_bytes())
    return subprocess.run(command, cwd=path, env=env, text=True, capture_output=True)


def _evidence(result: subprocess.CompletedProcess[str]) -> dict:
    return json.loads(result.stdout.splitlines()[0])["trusted_git"]


def test_trusted_environment_and_admin_config_paths_are_selected(monkeypatch):
    spec = importlib.util.spec_from_file_location("trusted_git_diff", ROOT / ".nexus-core/trusted_git_diff.py")
    helper = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(helper)
    default_path, _, _, _ = helper._select()

    monkeypatch.setenv("NEXUS_GIT_PATH", default_path)
    assert helper._select()[1] == "environment"
    monkeypatch.delenv("NEXUS_GIT_PATH")
    monkeypatch.setattr(helper, "_config_path", lambda: default_path)
    assert helper._select()[1] == "config"


def test_trusted_git_uses_supported_default_and_reports_evidence(tmp_path):
    _repo(tmp_path)
    env = dict(os.environ)
    env.pop("NEXUS_GIT_PATH", None)
    env.pop("GIT_NO_REPLACE_OBJECTS", None)

    result = _run(tmp_path, env)

    assert result.returncode == 0, result.stderr
    evidence = _evidence(result)
    assert evidence["source"] == "default"
    assert Path(evidence["path"]).is_absolute()
    assert evidence["replacement_refs_check"] == "passed"


def test_trusted_git_ignores_path_shim(tmp_path):
    _repo(tmp_path)
    shim_dir = tmp_path / "shim-bin"
    shim_dir.mkdir()
    shim = shim_dir / "git"
    shim.write_text("#!/bin/sh\necho 'git version shim'\nexit 0\n")
    shim.chmod(0o755)
    env = dict(os.environ, PATH=str(shim_dir) + os.pathsep + os.environ.get("PATH", ""))
    env.pop("NEXUS_GIT_PATH", None)
    env.pop("GIT_NO_REPLACE_OBJECTS", None)

    result = _run(tmp_path, env)

    assert result.returncode == 0, result.stderr
    evidence = _evidence(result)
    assert evidence["source"] == "default"
    assert evidence["path"] != str(shim)
    assert evidence["version"] != "git version shim"


def test_trusted_git_rejects_caller_writable_override_before_version(tmp_path):
    _repo(tmp_path)
    marker = tmp_path / "launched"
    override = tmp_path / "caller-git"
    override.write_text(f"#!/bin/sh\necho launched > '{marker}'\necho 'git version fake'\nexit 0\n")
    override.chmod(0o755)
    env = dict(os.environ, NEXUS_GIT_PATH=str(override))
    env.pop("GIT_NO_REPLACE_OBJECTS", None)

    result = _run(tmp_path, env)

    assert result.returncode == 127
    assert "NEXUS_GIT_PATH" in result.stderr
    assert not marker.exists()


def test_trusted_git_evidence_matches_launched_executable(tmp_path):
    _repo(tmp_path)
    env = dict(os.environ)
    env.pop("NEXUS_GIT_PATH", None)
    env.pop("GIT_NO_REPLACE_OBJECTS", None)

    result = _run(tmp_path, env)

    assert result.returncode == 0, result.stderr
    evidence = _evidence(result)
    executable = Path(evidence["path"])
    data = executable.read_bytes()
    info = executable.stat()
    actual_version = subprocess.run([str(executable), "--version"], text=True, capture_output=True, check=True).stdout.strip()
    assert evidence["sha256"] == hashlib.sha256(data).hexdigest()
    assert evidence["version"] == actual_version
    assert evidence["owner_uid"] == info.st_uid
    assert evidence["mode"] == oct(stat.S_IMODE(info.st_mode))
