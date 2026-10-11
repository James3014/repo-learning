from __future__ import annotations

from pathlib import Path

from repolearn import (
    CURRENT_CONTRACT,
    ContractIdentity,
    DeploymentDefect,
    DeploymentStage,
    attest_loaded_contract,
    inspect_skill_directory,
    sync_skill_install,
)


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "repo-learning"


def test_loaded_contract_attestation_detects_stale_runtime_skill():
    stale = attest_loaded_contract(
        loaded_revision="g5-runtime-evidence-v1",
        loaded_content_sha256="57c2dd82c3f04125fb487d31df8bfc1f2ed9f3e73b5599f726a4608e0a529202",
    )
    assert stale.stage is DeploymentStage.LOADED
    assert stale.current is False
    assert stale.defect is DeploymentDefect.CONTRACT_IDENTITY_MISMATCH


def test_loaded_contract_attestation_accepts_exact_current_identity():
    current = attest_loaded_contract(
        loaded_revision=CURRENT_CONTRACT.revision,
        loaded_content_sha256=CURRENT_CONTRACT.content_sha256,
    )
    assert current.current is True
    assert current.defect is DeploymentDefect.NONE


def test_loaded_contract_attestation_missing_or_invalid_identity_fails_closed():
    missing = attest_loaded_contract(
        loaded_revision=None,
        loaded_content_sha256=None,
    )
    invalid = attest_loaded_contract(
        loaded_revision="something",
        loaded_content_sha256="not-a-sha",
    )
    assert missing.current is False
    assert missing.defect is DeploymentDefect.MISSING
    assert invalid.current is False
    assert invalid.defect is DeploymentDefect.MISSING


def test_filesystem_sync_check_detects_missing_current_and_content_drift(tmp_path):
    install_root = tmp_path / "skills"

    before = sync_skill_install(SKILL_ROOT, install_root, check_only=True)
    assert before.current is False
    assert before.defect is DeploymentDefect.MISSING

    installed = sync_skill_install(SKILL_ROOT, install_root)
    assert installed.current is True

    checked = sync_skill_install(SKILL_ROOT, install_root, check_only=True)
    assert checked.current is True

    target_skill = install_root / "repo-learning" / "SKILL.md"
    target_skill.write_text(target_skill.read_text() + "\n# local drift\n")

    drifted = inspect_skill_directory(install_root / "repo-learning")
    assert drifted.current is False
    assert drifted.defect is DeploymentDefect.CONTENT_FINGERPRINT_MISMATCH


def test_contract_identity_rejects_malformed_fingerprint():
    try:
        ContractIdentity("revision", "bad")
    except ValueError as exc:
        assert "content_sha256" in str(exc)
    else:
        raise AssertionError("malformed fingerprint must fail")


def test_missing_control_file_is_not_current_issue_50(tmp_path):
    import shutil
    import pytest

    root = tmp_path / "skills"
    assert sync_skill_install(SKILL_ROOT, root).current is True
    installed = root / "repo-learning"
    (installed / "SKILL.md").unlink()
    (installed / "references" / "policy.md").unlink()
    attestation = inspect_skill_directory(installed)
    assert attestation.current is False
    assert attestation.defect is DeploymentDefect.CONTENT_FINGERPRINT_MISMATCH
    assert sync_skill_install(SKILL_ROOT, root, check_only=True).current is False

    source = tmp_path / "src-skill"
    shutil.copytree(SKILL_ROOT, source)
    (source / "references" / "state-contract.md").unlink()
    with pytest.raises(ValueError, match="CONTENT_FINGERPRINT_MISMATCH"):
        sync_skill_install(source, tmp_path / "other-root")


def test_unfingerprinted_non_loaded_attestation_is_not_current_issue_50():
    from repolearn import ContractAttestation

    for stage in (DeploymentStage.SOURCE, DeploymentStage.PACKAGE, DeploymentStage.INSTALLED):
        a = ContractAttestation(stage=stage, expected=CURRENT_CONTRACT, observed=CURRENT_CONTRACT)
        assert a.current is False
        assert a.defect is DeploymentDefect.CONTENT_FINGERPRINT_MISMATCH
