#!/usr/bin/env python3
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
    env = {key: os.environ[key] for key in ("LANG", "LC_ALL", "LC_CTYPE", "TZ", "TMPDIR") if key in os.environ}
    env.update({
        "PATH": "/usr/bin:/bin",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
    })
    result = subprocess.run([path, *args], env=env, text=True, capture_output=True, check=False)
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
