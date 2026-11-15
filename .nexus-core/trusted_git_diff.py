#!/usr/bin/python3
"""Run the Issue diff verifier with a trusted, evidenced Git executable."""

from __future__ import annotations

import hashlib
import contextlib
import io
import json
import os
from pathlib import Path
import pwd
import stat
import subprocess
import sys


SETTING = "NEXUS_GIT_PATH"
ADMIN_CONFIGS = (
    Path("/etc/nexus-core/config.toml"),
    Path("/Library/Preferences/nexus-core.toml"),
)
DEFAULTS = {
    "Linux": ("/usr/bin/git", "/bin/git", "/usr/local/bin/git"),
    "Darwin": ("/usr/bin/git", "/opt/homebrew/bin/git", "/usr/local/bin/git", "/opt/local/bin/git"),
}
APPROVED_INSTALLERS = ("_apt", "_installer", "brew", "nixbld")
SAFE_CONFIG = (
    ("core.fsmonitor", "false"), ("core.hooksPath", "/dev/null"),
    ("core.sshCommand", ""), ("core.pager", "cat"), ("core.editor", ""),
    ("core.askPass", ""), ("diff.external", ""), ("include.path", "/dev/null"),
    ("includeIf.onbranch:main.path", "/dev/null"), ("protocol.ext.allow", "never"), ("credential.helper", ""),
)


def _fail(reason: str) -> "NoReturn":
    print(f"Trusted Git unavailable ({SETTING}): {reason}. PATH lookup is disabled.", file=sys.stderr)
    raise SystemExit(127)


def _config_path() -> str | None:
    for config in ADMIN_CONFIGS:
        if not config.exists():
            continue
        _trusted_file(config, executable=False)
        try:
            import tomllib
            value = tomllib.loads(config.read_text(encoding="utf-8")).get("trusted_executables", {}).get("git")
        except (OSError, ValueError, ImportError) as exc:
            _fail(f"administrator config {config} is unreadable or invalid: {exc}")
        if value is not None:
            if not isinstance(value, str):
                _fail(f"administrator config setting trusted_executables.git must be a path")
            return value
    return None


def _trusted_file(path: Path, *, executable: bool = True) -> tuple[os.stat_result, str]:
    try:
        resolved = path.resolve(strict=True)
        info = resolved.stat()
    except OSError as exc:
        _fail(f"{path} cannot be inspected: {exc}")
    if not stat.S_ISREG(info.st_mode):
        _fail(f"{resolved} is not a regular file")
    if executable and not os.access(resolved, os.X_OK):
        _fail(f"{resolved} is not executable")
    allowed_owners = {0}
    for name in APPROVED_INSTALLERS:
        try:
            allowed_owners.add(pwd.getpwnam(name).pw_uid)
        except KeyError:
            pass
    if info.st_uid not in allowed_owners:
        _fail(f"{resolved} is owned by unapproved uid {info.st_uid}")
    if os.access(resolved, os.W_OK, effective_ids=True):
        _fail(f"{resolved} is writable by the caller")
    parent = resolved.parent
    while True:
        try:
            if not parent.is_dir() or os.access(parent, os.W_OK, effective_ids=True):
                _fail(f"parent directory {parent} is writable by the caller or is not a directory")
        except OSError as exc:
            _fail(f"parent directory {parent} cannot be inspected: {exc}")
        if parent.parent == parent:
            break
        parent = parent.parent
    return info, str(resolved)


def _digest(path: str, expected: os.stat_result) -> str:
    try:
        with open(path, "rb") as handle:
            opened = os.fstat(handle.fileno())
            if (opened.st_dev, opened.st_ino) != (expected.st_dev, expected.st_ino):
                _fail(f"{path} changed during trust validation")
            digest = hashlib.sha256()
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
            return digest.hexdigest()
    except OSError as exc:
        _fail(f"{path} could not be hashed: {exc}")


def _git_env(*, audit: bool = False) -> dict[str, str]:
    env = {key: os.environ[key] for key in ("LANG", "LC_ALL", "LC_CTYPE", "TZ", "TMPDIR") if key in os.environ}
    env.update({"PATH": "/usr/bin:/bin", "GIT_NO_REPLACE_OBJECTS": "1", "GIT_ATTR_NOSYSTEM": "1"})
    if audit:
        # git config only reads values; expose system/global/worktree scopes for the policy scan.
        for key in ("GIT_CONFIG_NOSYSTEM", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM"):
            if key in os.environ:
                env[key] = os.environ[key]
        env.pop("GIT_CONFIG_NOSYSTEM", None)
    else:
        env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull})
    env["GIT_CONFIG_COUNT"] = str(len(SAFE_CONFIG))
    for index, (key, value) in enumerate(SAFE_CONFIG):
        env[f"GIT_CONFIG_KEY_{index}"] = key
        env[f"GIT_CONFIG_VALUE_{index}"] = value
    return env


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _lstat_chain(path: Path, *, recursive: bool = False) -> list[tuple[str, os.stat_result]]:
    """Reject links in the path and its tree; return a stable inode snapshot."""
    try:
        absolute = path.absolute()
        chain = list(reversed((absolute, *absolute.parents)))
        snapshot = []
        for item in chain:
            info = item.lstat()
            if stat.S_ISLNK(info.st_mode):
                _fail(f"Git metadata path contains symlink: {item}")
            snapshot.append((str(item), info))
        if recursive and absolute.is_dir():
            for base, dirs, files in os.walk(absolute, followlinks=False):
                for name in dirs + files:
                    child = Path(base, name)
                    info = child.lstat()
                    if stat.S_ISLNK(info.st_mode):
                        _fail(f"Git metadata contains symlink: {child}")
                    snapshot.append((str(child), info))
        return snapshot
    except OSError as exc:
        _fail(f"Git metadata path {path} cannot be inspected: {exc}")


def _repo_snapshot(git: str) -> tuple[list[tuple[str, os.stat_result]], Path]:
    env = _git_env()
    result = subprocess.run(
        [git, "rev-parse", "--git-dir", "--git-common-dir", "--absolute-git-dir"],
        cwd=Path.cwd(), env=env, text=True, capture_output=True, check=False,
    )
    if result.returncode:
        _fail(f"cannot resolve repository Git directories: {result.stderr.strip()}")
    values = result.stdout.splitlines()
    if len(values) != 3:
        _fail("Git returned incomplete repository directory paths")
    cwd = Path.cwd().resolve(strict=True)
    paths = [Path(v) if Path(v).is_absolute() else cwd / v for v in values]
    for p in paths:
        _lstat_chain(p)
    gitdir, common, absolute = (p.resolve(strict=True) for p in paths)
    if absolute != gitdir:
        _fail("Git directory resolution is inconsistent")
    worktree_admin = _inside(gitdir, common / "worktrees")
    gitfile = cwd / ".git"
    is_gitfile = False
    try:
        st = gitfile.lstat()
        is_gitfile = stat.S_ISREG(st.st_mode)
    except OSError:
        pass
    if not _inside(gitdir, cwd) and not (worktree_admin and is_gitfile):
        _fail(f"Git directory {gitdir} is outside target repository {cwd}")
    if not _inside(common, cwd) and not (worktree_admin and is_gitfile):
        _fail(f"Git common directory {common} is outside target repository {cwd}")

    roots = list(dict.fromkeys((gitdir, common)))
    snapshot: list[tuple[str, os.stat_result]] = []
    for root in roots:
        snapshot.extend(_lstat_chain(root))
        try:
            for base, dirs, files in os.walk(root, followlinks=False, onerror=lambda exc: _fail(f"Git metadata tree cannot be inspected: {exc}")):
                for name in (*dirs, *files):
                    item = Path(base, name)
                    info = item.lstat()
                    if stat.S_ISLNK(info.st_mode):
                        _fail(f"Git metadata contains symlink: {item}")
                    resolved_item = item.resolve(strict=True)
                    if not (_inside(resolved_item, cwd) or any(_inside(resolved_item, allowed) for allowed in roots)):
                        _fail(f"Git metadata escapes target repository: {item}")
                    if item.name in ("config", "config.worktree") and stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
                        _fail(f"Git config is hardlinked: {item}")
                    snapshot.append((str(item), info))
        except OSError as exc:
            _fail(f"Git metadata tree {root} cannot be inspected: {exc}")
    for required in (common / "objects", common / "refs", common / "HEAD", common / "config"):
        if not required.exists():
            _fail(f"required Git metadata is missing: {required}")
    for name in ("info/attributes",):
        for root in dict.fromkeys(roots):
            item = root / name
            if item.exists() or item.is_symlink():
                if item.stat().st_size:
                    _fail(f"repository-local attributes file {item} is not empty")
    for root in dict.fromkeys(roots):
        for forbidden in (root / "objects/info/alternates", root / "refs/replace", root / "info/grafts"):
            if forbidden.exists() or forbidden.is_symlink():
                marker = " NEXUS_REPLACE_REFS_PRESENT" if forbidden.name == "replace" else ""
                _fail(f"forbidden Git metadata exists: {forbidden}{marker}")
    gitfile = cwd / ".git"
    if not _inside(common, cwd):
        try:
            snapshot.extend(_lstat_chain(gitfile))
            target_line = gitfile.read_text(encoding="utf-8").strip()
            if not target_line.startswith("gitdir:") or (gitfile.parent / target_line[7:].strip()).resolve(strict=True) != gitdir:
                _fail("worktree .git pointer does not resolve to its Git admin directory")
            common_pointer = (gitdir / "commondir").read_text(encoding="utf-8").strip()
            if (gitdir / common_pointer).resolve(strict=True) != common:
                _fail("worktree commondir pointer does not resolve to the common Git directory")
            gitdir_pointer = (gitdir / "gitdir").read_text(encoding="utf-8").strip()
            if (gitdir / gitdir_pointer).resolve(strict=True) != gitfile.resolve(strict=True):
                _fail("worktree gitdir pointer does not resolve to the target repository")
        except OSError as exc:
            _fail(f"worktree Git pointers cannot be inspected: {exc}")
    return snapshot, gitdir


# Standard git-lfs filter values; accepted only from system/global scope (attributes are disabled for the diff, so no filter runs).
LFS_FILTER_VALUES = {
    "filter.lfs.clean": "git-lfs clean -- %f",
    "filter.lfs.smudge": "git-lfs smudge -- %f",
    "filter.lfs.process": "git-lfs filter-process",
    "filter.lfs.required": "true",
}


def _check_config(git: str) -> None:
    env = _git_env(audit=True)
    count = len(SAFE_CONFIG)
    for i in range(count):
        env.pop(f"GIT_CONFIG_KEY_{i}", None)
        env.pop(f"GIT_CONFIG_VALUE_{i}", None)
    env.pop("GIT_CONFIG_COUNT", None)
    result = subprocess.run([git, "config", "--null", "--show-scope", "--show-origin", "--list"], cwd=Path.cwd(), env=env, capture_output=True, check=False)
    if result.returncode:
        _fail("cannot inspect Git config from all scopes")
    # --null --show-scope --show-origin emits "scope\0origin\0key\nvalue\0" per entry; a valueless key has no newline.
    tokens = result.stdout.decode("utf-8", "replace").split("\0")
    if tokens and tokens[-1] == "":
        tokens.pop()
    if len(tokens) % 3:
        _fail("cannot parse Git config from all scopes")
    for i in range(0, len(tokens), 3):
        scope, record = tokens[i], tokens[i + 2]
        name, has_value, value = record.partition("\n")
        key = name.lower()
        if scope in {"system", "global"} and has_value and LFS_FILTER_VALUES.get(key) == value:
            continue
        if key.startswith("filter.") or (key.startswith("diff.") and key.endswith((".command", ".textconv"))) or key in {
            "core.fsmonitor", "core.hookspath", "include.path", "extensions.worktreeconfig",
        } or key.startswith("includeif."):
            _fail(f"execution-capable Git config is present: {key}")


def _select() -> tuple[str, str, os.stat_result, str]:
    if SETTING in os.environ:
        raw, source = os.environ[SETTING], "environment"
    else:
        configured = _config_path()
        if configured is not None:
            raw, source = configured, "config"
        else:
            for candidate in DEFAULTS.get(sys.platform.split("-")[0].capitalize(), ()):
                try:
                    with contextlib.redirect_stderr(io.StringIO()):
                        info, path = _trusted_file(Path(candidate))
                except SystemExit:
                    continue
                return path, "default", info, _digest(path, info)
            _fail("no trusted Git found in supported system locations")
    candidate = Path(raw)
    if not candidate.is_absolute():
        _fail(f"{SETTING} and trusted_executables.git must be absolute paths")
    info, path = _trusted_file(candidate)
    return path, source, info, _digest(path, info)


def _git(path: str, args: list[str], expected: os.stat_result, expected_digest: str) -> subprocess.CompletedProcess[str]:
    current, resolved = _trusted_file(Path(path))
    if resolved != path or (current.st_dev, current.st_ino) != (expected.st_dev, expected.st_ino):
        _fail(f"{path} changed during trust validation")
    if _digest(path, current) != expected_digest:
        _fail(f"{path} changed after its SHA-256 was recorded")
    before, _ = _repo_snapshot(path)
    _check_config(path)
    env = _git_env()
    command = [path]
    if args[:1] == ["diff"]:
        command.extend(["-c", "core.attributesFile=/dev/null"])
        args = [*args[:1], "--no-ext-diff", "--no-textconv", *args[1:]]
    result = subprocess.run([*command, *args], env=env, text=True, capture_output=True, check=False)
    after_repo, _ = _repo_snapshot(path)
    if [(p, (s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns)) for p, s in before] != [(p, (s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns)) for p, s in after_repo]:
        _fail("Git repository metadata changed while Git was running")
    after, after_resolved = _trusted_file(Path(path))
    if (
        after_resolved != path
        or (after.st_dev, after.st_ino, after.st_mtime_ns, after.st_size)
        != (current.st_dev, current.st_ino, current.st_mtime_ns, current.st_size)
        or _digest(path, after) != expected_digest
    ):
        _fail(f"{path} changed while Git was running")
    return result


def main() -> int:
    path, source, info, digest = _select()
    version = _git(path, ["--version"], info, digest)
    if version.returncode:
        _fail(f"trusted executable {path} failed --version")
    ref_check = _git(path, ["for-each-ref", "--format=%(refname)", "refs/replace"], info, digest)
    if ref_check.returncode:
        _fail(f"trusted executable {path} failed the replacement-ref check")
    refs_present = bool(ref_check.stdout.strip())
    evidence = {
        "trusted_git": {
            "path": path,
            "source": source,
            "owner_uid": info.st_uid,
            "mode": oct(stat.S_IMODE(info.st_mode)),
            "sha256": digest,
            "version": version.stdout.strip(),
            "replacement_refs_check": "failed" if refs_present else "passed",
        }
    }
    print(json.dumps(evidence, sort_keys=True))
    if refs_present:
        print(f"NEXUS_REPLACE_REFS_PRESENT: {ref_check.stdout.strip()}", file=sys.stderr)
        return 1
    diff = _git(path, ["diff", "--cached", "--check", "HEAD"], info, digest)
    sys.stdout.write(diff.stdout)
    sys.stderr.write(diff.stderr)
    return diff.returncode


if __name__ == "__main__":
    raise SystemExit(main())
