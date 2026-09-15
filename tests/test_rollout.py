from __future__ import annotations

import json
from pathlib import Path

import pytest

from repolearn.rollout import (
    CANONICAL_SKILL_SOURCE,
    EXPECTED_REPOSITORIES,
    REPOSITORY_ACTIVATION_ADAPTER,
    RolloutManifestError,
    dry_run_rollout,
    load_rollout_manifest,
    validate_rollout_manifest,
)


MANIFEST = Path(__file__).resolve().parents[1] / "manifests" / "g6-rollout.v1.json"


def test_rollout_manifest_contains_exact_eight_repositories_and_is_ready() -> None:
    manifest = load_rollout_manifest(MANIFEST)
    result = dry_run_rollout(manifest)
    assert tuple(entry["repository"] for entry in manifest["repositories"]) == EXPECTED_REPOSITORIES
    assert result.ready
    assert result.repository_count == 8
    assert not result.performs_installation


def test_rollout_manifest_requires_repo_activation_pointer_and_canonical_skill_source() -> None:
    manifest = load_rollout_manifest(MANIFEST)
    for entry in manifest["repositories"]:
        assert entry["activation_required"] is True
        assert entry["activation_adapter"] == REPOSITORY_ACTIVATION_ADAPTER
        assert entry["canonical_skill_source"] == CANONICAL_SKILL_SOURCE
        assert entry["context_adapter"] == "thin-reference-only"


@pytest.mark.parametrize("field,value,match", [
    ("activation_required", False, "activation pointer"),
    ("activation_adapter", "skill-auto-discovery", "activation adapter"),
    ("canonical_skill_source", "target-repo/copied-skill", "canonical skill source"),
])
def test_rollout_manifest_rejects_noncanonical_activation(field: str, value: object, match: str) -> None:
    manifest = load_rollout_manifest(MANIFEST)
    manifest["repositories"][0][field] = value
    with pytest.raises(RolloutManifestError, match=match):
        validate_rollout_manifest(manifest)


@pytest.mark.parametrize("forbidden", ["mastery", "state", "policy", "governance"])
def test_rollout_manifest_rejects_learning_state_or_cloned_authority(forbidden: str) -> None:
    manifest = load_rollout_manifest(MANIFEST)
    manifest["repositories"][0][forbidden] = {"copied": True}
    with pytest.raises(RolloutManifestError, match=forbidden):
        validate_rollout_manifest(manifest)


def test_rollout_manifest_rejects_missing_or_extra_repository() -> None:
    manifest = load_rollout_manifest(MANIFEST)
    manifest["repositories"].pop()
    with pytest.raises(RolloutManifestError, match="exact repositories"):
        validate_rollout_manifest(manifest)


def test_rollout_manifest_rejects_unapproved_metadata() -> None:
    manifest = load_rollout_manifest(MANIFEST)
    manifest["repositories"][0]["default_branch"] = "main"
    with pytest.raises(RolloutManifestError, match="metadata"):
        validate_rollout_manifest(manifest)
