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
    if command[-1:] == [".nexus-core/trusted_git_diff.py"]:
        verifier_dir = path / ".nexus-core"
        verifier_dir.mkdir(exist_ok=True)
        (verifier_dir / "trusted_git_diff.py").write_bytes((ROOT / command[-1]).read_bytes())
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


def _load_helper():
    spec = importlib.util.spec_from_file_location("trusted_git_diff_env", ROOT / ".nexus-core/trusted_git_diff.py")
    helper = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(helper)
    return helper


def test_diff_check_verifier_does_not_resolve_python_through_path():
    config = tomllib.loads((ROOT / ".nexus-core/config.toml").read_text())
    command = next(v["command"] for v in config["verifiers"] if v["id"] == "diff-check")
    assert Path(command[0]).is_absolute(), command


def test_git_subprocess_env_is_allowlisted(monkeypatch):
    helper = _load_helper()
    for key, value in {
        "GIT_INDEX_FILE": "/nonexistent-index",
        "GIT_DIR": "/nonexistent-dir",
        "GIT_CONFIG_COUNT": "1",
        "LD_PRELOAD": "/nonexistent.so",
        "DYLD_INSERT_LIBRARIES": "/nonexistent.dylib",
        "SECRET_TOKEN": "x",
    }.items():
        monkeypatch.setenv(key, value)
    seen = {}
    real_run = subprocess.run

    def spy(*args, **kwargs):
        seen.update(kwargs["env"])
        return real_run(*args, **kwargs)

    monkeypatch.setattr(helper.subprocess, "run", spy)
    path, _, info, digest = helper._select()
    helper._git(path, ["--version"], info, digest)
    for key in ("GIT_INDEX_FILE", "GIT_DIR", "LD_PRELOAD", "DYLD_INSERT_LIBRARIES", "SECRET_TOKEN"):
        assert key not in seen
    assert int(seen["GIT_CONFIG_COUNT"]) >= 10
    assert seen["GIT_NO_REPLACE_OBJECTS"] == "1"


def test_diff_invocation_disables_repo_git_execution_and_attributes(tmp_path, monkeypatch):
    _repo(tmp_path)
    helper = _load_helper()
    monkeypatch.chdir(tmp_path)
    captured = []
    real_run = subprocess.run

    def spy(args, **kwargs):
        captured.append((args, kwargs))
        return real_run(args, **kwargs)

    monkeypatch.setattr(helper.subprocess, "run", spy)
    path, _, info, digest = helper._select()
    helper._git(path, ["diff", "--cached", "--check", "HEAD"], info, digest)
    args, options = next(item for item in captured if item[0][1:2] == ["-c"] and "diff" in item[0])
    assert args[1:] == ["-c", "core.attributesFile=/dev/null", "diff", "--no-ext-diff", "--no-textconv", "--cached", "--check", "HEAD"]
    assert options["env"]["GIT_ATTR_NOSYSTEM"] == "1"


def test_diff_check_fails_closed_on_info_attributes(tmp_path, monkeypatch):
    _repo(tmp_path)
    helper = _load_helper()
    info_attributes = tmp_path / ".git/info/attributes"
    info_attributes.write_text("* textconv=unsafe\n")
    monkeypatch.chdir(tmp_path)
    path, _, info, digest = helper._select()
    with pytest.raises(SystemExit):
        helper._git(path, ["diff", "--cached", "--check", "HEAD"], info, digest)


def test_diff_check_interpreter_is_safe_fallback_command():
    config = tomllib.loads((ROOT / ".nexus-core/config.toml").read_text())
    command = next(v["command"] for v in config["verifiers"] if v["id"] == "diff-check")
    assert Path(command[0]).is_absolute()
    assert Path(command[0]).is_file(), f"absolute Python interpreter missing: {command[0]}"
    assert "/usr/bin/env" not in command
    assert (ROOT / ".nexus-core/trusted_git_diff.py").read_text().splitlines()[0] == "#!/usr/bin/python3"


def test_git_is_revalidated_after_execution(monkeypatch):
    helper = _load_helper()
    path, _, info, digest = helper._select()
    calls = []
    real_digest = helper._digest

    def digest_spy(p, expected):
        calls.append(p)
        return real_digest(p, expected) if len(calls) == 1 else "0" * 64

    monkeypatch.setattr(helper, "_digest", digest_spy)
    with pytest.raises(SystemExit):
        helper._git(path, ["--version"], info, digest)


@pytest.mark.parametrize("relative", [
    "objects/info/alternates", "refs/replace/unsafe", "info/attributes",
    "info/exclude", "shallow", "info/grafts", "packed-refs", "config.worktree",
])
def test_git_admin_metadata_rejects_links_and_execution_files(tmp_path, monkeypatch, relative):
    _repo(tmp_path)
    helper = _load_helper()
    target = tmp_path / ".git" / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        target.unlink()
    outside = tmp_path / "outside"
    outside.write_text("unsafe\n")
    target.symlink_to(outside)
    monkeypatch.chdir(tmp_path)
    path, _, info, digest = helper._select()
    with pytest.raises(SystemExit):
        helper._git(path, ["diff", "--cached", "--check", "HEAD"], info, digest)


@pytest.mark.parametrize("name", ["index", "index.lock"])
def test_git_rejects_symlinked_index_metadata(tmp_path, monkeypatch, name):
    _repo(tmp_path)
    helper = _load_helper()
    target = tmp_path / ".git" / name
    if target.exists():
        target.unlink()
    outside = tmp_path / "outside-index"
    outside.write_text("unsafe\n")
    target.symlink_to(outside)
    monkeypatch.chdir(tmp_path)
    path, _, info, digest = helper._select()
    with pytest.raises(SystemExit):
        helper._git(path, ["diff", "--cached", "--check", "HEAD"], info, digest)


def test_git_rejects_hardlinked_config(tmp_path, monkeypatch):
    _repo(tmp_path)
    helper = _load_helper()
    config = tmp_path / ".git/config"
    linked = tmp_path / "linked-config"
    os.link(config, linked)
    monkeypatch.chdir(tmp_path)
    path, _, info, digest = helper._select()
    with pytest.raises(SystemExit):
        helper._git(path, ["diff", "--cached", "--check", "HEAD"], info, digest)


def test_git_rejects_symlinked_metadata_directory(tmp_path, monkeypatch):
    _repo(tmp_path)
    helper = _load_helper()
    info = tmp_path / ".git/info"
    info.rename(tmp_path / ".git/info-real")
    info.symlink_to(tmp_path / ".git/info-real", target_is_directory=True)
    monkeypatch.chdir(tmp_path)
    path, _, git_info, digest = helper._select()
    with pytest.raises(SystemExit):
        helper._git(path, ["diff", "--cached", "--check", "HEAD"], git_info, digest)


@pytest.mark.parametrize("key,value", [
    ("filter.test.process", "unsafe"), ("filter.test.clean", "unsafe"),
    ("filter.test.smudge", "unsafe"), ("diff.test.command", "unsafe"),
    ("diff.test.textconv", "unsafe"), ("core.fsmonitor", "unsafe"),
    ("core.hooksPath", "unsafe"), ("include.path", "unsafe"),
    ("includeIf.onbranch:main.path", "unsafe"),
    ("extensions.worktreeConfig", "true"),
])
def test_git_rejects_execution_capable_config_at_any_scope(tmp_path, monkeypatch, key, value):
    _repo(tmp_path)
    helper = _load_helper()
    if key.startswith(("filter.", "diff.")):
        section, subsection, name = key.split(".", 2)
        line = f'[{section} "{subsection}"]\n\t{name} = {value}\n'
    elif key.startswith("includeIf."):
        subsection, name = key[len("includeIf."):].rsplit(".", 1)
        line = f'[includeIf "{subsection}"]\n\t{name} = {value}\n'
    else:
        section, name = key.split(".", 1)
        line = f"[{section}]\n\t{name} = {value}\n"
    with (tmp_path / ".git/config").open("a") as config:
        config.write("\n" + line)
    monkeypatch.chdir(tmp_path)
    path, _, info, digest = helper._select()
    with pytest.raises(SystemExit):
        helper._git(path, ["diff", "--cached", "--check", "HEAD"], info, digest)


def test_git_uses_config_overrides_and_config_inspection(monkeypatch):
    helper = _load_helper()
    path, _, info, digest = helper._select()
    seen = []
    real_run = subprocess.run

    def spy(args, **kwargs):
        seen.append((args, kwargs.get("env", {})))
        return real_run(args, **kwargs)

    monkeypatch.setattr(helper.subprocess, "run", spy)
    helper._git(path, ["--version"], info, digest)
    git_env = next(env for args, env in seen if "--version" in args)
    assert git_env["GIT_CONFIG_COUNT"]
    pairs = [(git_env[f"GIT_CONFIG_KEY_{i}"], git_env[f"GIT_CONFIG_VALUE_{i}"]) for i in range(int(git_env["GIT_CONFIG_COUNT"]))]
    assert dict(pairs)["core.fsmonitor"] == "false"
    assert dict(pairs)["core.hooksPath"] == "/dev/null"
    assert dict(pairs)["protocol.ext.allow"] == "never"
    assert dict(pairs)["include.path"] == "/dev/null"
    assert dict(pairs)["includeIf.onbranch:main.path"] == "/dev/null"
    assert dict(pairs)["core.sshCommand"] == ""
    assert dict(pairs)["core.pager"] == "cat"
    assert dict(pairs)["core.editor"] == ""
    assert dict(pairs)["core.askPass"] == ""
    assert dict(pairs)["diff.external"] == ""
    assert dict(pairs)["credential.helper"] == ""
    assert any("--show-origin" in args and "--list" in args for args, _ in seen)


@pytest.mark.parametrize("scope_env", ["GIT_CONFIG_SYSTEM", "GIT_CONFIG_GLOBAL"])
def test_git_rejects_execution_config_from_system_and_global_scopes(tmp_path, monkeypatch, scope_env):
    _repo(tmp_path)
    helper = _load_helper()
    config = tmp_path / f"{scope_env.lower()}.config"
    config.write_text('[filter "outside"]\n\tprocess = unsafe\n')
    monkeypatch.setenv(scope_env, str(config))
    monkeypatch.chdir(tmp_path)
    path, _, info, digest = helper._select()
    with pytest.raises(SystemExit):
        helper._git(path, ["diff", "--cached", "--check", "HEAD"], info, digest)


def test_git_rejects_execution_config_loaded_through_include(tmp_path, monkeypatch):
    _repo(tmp_path)
    helper = _load_helper()
    included = tmp_path / "included.config"
    included.write_text('[diff "unsafe"]\n\ttextconv = unsafe\n')
    with (tmp_path / ".git/config").open("a") as config:
        config.write(f"\n[include]\n\tpath = {included}\n")
    monkeypatch.chdir(tmp_path)
    path, _, info, digest = helper._select()
    with pytest.raises(SystemExit):
        helper._git(path, ["diff", "--cached", "--check", "HEAD"], info, digest)


def test_configured_interpreter_path_is_present_or_fails_clearly():
    config = tomllib.loads((ROOT / ".nexus-core/config.toml").read_text())
    command = next(v["command"] for v in config["verifiers"] if v["id"] == "diff-check")
    assert Path(command[0]).is_file(), f"absolute Python interpreter missing: {command[0]}"


@pytest.mark.parametrize("config_text", ["[core]\n\tfsmonitor\n", '[filter "x"]\n\tclean\n', '[diff "x"]\n\ttextconv\n'])
def test_git_rejects_valueless_execution_capable_config(tmp_path, monkeypatch, config_text):
    _repo(tmp_path)
    helper = _load_helper()
    with (tmp_path / ".git/config").open("a") as config:
        config.write("\n" + config_text)
    monkeypatch.chdir(tmp_path)
    path, _, info, digest = helper._select()
    with pytest.raises(SystemExit):
        helper._git(path, ["diff", "--cached", "--check", "HEAD"], info, digest)
