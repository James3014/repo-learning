"""G6 rollout-readiness validation without performing repository installation."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping


EXPECTED_REPOSITORIES = (
    "James3014/Nexus-new",
    "James3014/devspace",
    "James3014/nexus-core",
    "James3014/nexus-learning",
    "James3014/nexus-open-swe-runtime",
    "James3014/repository-intelligence-engine",
    "James3014/nexus-runtime",
    "James3014/nexus-opencli-reviewer",
)

CANONICAL_SKILL_SOURCE = "James3014/repo-learning:skills/repo-learning/"
REPOSITORY_ACTIVATION_ADAPTER = "repo-instruction-pointer"

_FORBIDDEN_KEY_TOKENS = ("mastery", "state", "policy", "governance")
_ALLOWED_TOP_LEVEL = {"schema", "repositories"}
_ALLOWED_REPOSITORY_FIELDS = {
    "repository",
    "authority_reference",
    "mode",
    "clients",
    "privacy",
    "context_adapter",
    "activation_required",
    "activation_adapter",
    "canonical_skill_source",
}
_ALLOWED_PRIVACY_FIELDS = {
    "persist_source_excerpts",
    "persist_transcripts",
    "persist_personal_state_in_repository",
}


class RolloutManifestError(ValueError):
    """Raised when a rollout manifest exceeds the thin-context boundary."""


@dataclass(frozen=True)
class RolloutDryRunResult:
    ready: bool
    repository_count: int
    performs_installation: bool = False


def load_rollout_manifest(path: str | Path) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RolloutManifestError("rollout manifest is unreadable") from exc
    if not isinstance(payload, dict):
        raise RolloutManifestError("rollout manifest must be a JSON object")
    validate_rollout_manifest(payload)
    return payload


def _reject_forbidden_keys(value: Mapping[str, Any], *, location: str) -> None:
    for key in value:
        lowered = key.lower()
        for token in _FORBIDDEN_KEY_TOKENS:
            if token in lowered:
                raise RolloutManifestError(f"{location} must not contain {token} metadata")


def validate_rollout_manifest(manifest: Mapping[str, Any]) -> None:
    unknown_top = set(manifest) - _ALLOWED_TOP_LEVEL
    if unknown_top:
        raise RolloutManifestError(f"unapproved top-level metadata: {sorted(unknown_top)}")
    if manifest.get("schema") != "repolearn.rollout_manifest.v1":
        raise RolloutManifestError("unsupported rollout manifest schema")
    repositories = manifest.get("repositories")
    if not isinstance(repositories, list):
        raise RolloutManifestError("repositories must be a list")
    observed = tuple(entry.get("repository") if isinstance(entry, dict) else None for entry in repositories)
    if observed != EXPECTED_REPOSITORIES:
        raise RolloutManifestError("manifest must contain the exact repositories in the approved order")

    for index, entry in enumerate(repositories):
        if not isinstance(entry, dict):
            raise RolloutManifestError(f"repository entry {index} must be an object")
        _reject_forbidden_keys(entry, location=f"repository entry {index}")
        unknown = set(entry) - _ALLOWED_REPOSITORY_FIELDS
        if unknown:
            raise RolloutManifestError(f"unapproved repository metadata: {sorted(unknown)}")
        if entry.get("authority_reference") != "AGENTS.md":
            raise RolloutManifestError("authority_reference must remain a reference to AGENTS.md")
        if entry.get("mode") not in {"observe", "guided", "practice"}:
            raise RolloutManifestError("invalid learning mode")
        clients = entry.get("clients")
        if clients != ["codex", "claude"]:
            raise RolloutManifestError("client projection must remain the approved Codex/Claude pair")
        if entry.get("context_adapter") != "thin-reference-only":
            raise RolloutManifestError("context adapter must remain thin-reference-only")
        if entry.get("activation_required") is not True:
            raise RolloutManifestError("repository activation pointer must be required")
        if entry.get("activation_adapter") != REPOSITORY_ACTIVATION_ADAPTER:
            raise RolloutManifestError("activation adapter must remain repo-instruction-pointer")
        if entry.get("canonical_skill_source") != CANONICAL_SKILL_SOURCE:
            raise RolloutManifestError("canonical skill source must remain the repo-learning Skill source")
        privacy = entry.get("privacy")
        if not isinstance(privacy, dict):
            raise RolloutManifestError("privacy metadata must be an object")
        unknown_privacy = set(privacy) - _ALLOWED_PRIVACY_FIELDS
        if unknown_privacy:
            raise RolloutManifestError(f"unapproved privacy metadata: {sorted(unknown_privacy)}")
        if set(privacy) != _ALLOWED_PRIVACY_FIELDS or any(privacy.values()):
            raise RolloutManifestError("all persistence privacy defaults must be explicitly false")


def dry_run_rollout(manifest: Mapping[str, Any]) -> RolloutDryRunResult:
    """Validate G6 readiness only; never mutate or install into target repos."""

    validate_rollout_manifest(manifest)
    repositories = manifest["repositories"]
    return RolloutDryRunResult(ready=True, repository_count=len(repositories))
