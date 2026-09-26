"""RepoLearn contract deployment attestation and filesystem skill sync."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import os
from pathlib import Path
import re
import shutil
import uuid

from .host_eval import compute_skill_content_sha256
from .version import CONTRACT_CONTENT_SHA256, CONTRACT_REVISION


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class DeploymentStage(str, Enum):
    SOURCE = "SOURCE"
    PACKAGE = "PACKAGE"
    INSTALLED = "INSTALLED"
    LOADED = "LOADED"


class DeploymentDefect(str, Enum):
    NONE = "NONE"
    MISSING = "MISSING"
    INVALID_IDENTITY = "INVALID_IDENTITY"
    CONTRACT_IDENTITY_MISMATCH = "CONTRACT_IDENTITY_MISMATCH"
    CONTENT_FINGERPRINT_MISMATCH = "CONTENT_FINGERPRINT_MISMATCH"


@dataclass(frozen=True)
class ContractIdentity:
    revision: str
    content_sha256: str

    def __post_init__(self) -> None:
        if not self.revision.strip():
            raise ValueError("revision must be non-empty")
        if not _SHA256_RE.fullmatch(self.content_sha256):
            raise ValueError("content_sha256 must be a lowercase SHA-256 hex digest")


CURRENT_CONTRACT = ContractIdentity(CONTRACT_REVISION, CONTRACT_CONTENT_SHA256)


@dataclass(frozen=True)
class ContractAttestation:
    stage: DeploymentStage
    expected: ContractIdentity
    observed: ContractIdentity | None
    computed_content_sha256: str | None = None

    @property
    def current(self) -> bool:
        if self.observed != self.expected:
            return False
        if self.computed_content_sha256 is not None:
            return self.computed_content_sha256 == self.expected.content_sha256
        return True

    @property
    def defect(self) -> DeploymentDefect:
        if self.observed is None:
            return DeploymentDefect.MISSING
        if self.observed != self.expected:
            return DeploymentDefect.CONTRACT_IDENTITY_MISMATCH
        if (
            self.computed_content_sha256 is not None
            and self.computed_content_sha256 != self.expected.content_sha256
        ):
            return DeploymentDefect.CONTENT_FINGERPRINT_MISMATCH
        return DeploymentDefect.NONE


def attest_loaded_contract(
    *,
    loaded_revision: str | None,
    loaded_content_sha256: str | None,
    expected: ContractIdentity = CURRENT_CONTRACT,
) -> ContractAttestation:
    """Compare the actually loaded Skill identity with the expected canonical identity."""

    observed: ContractIdentity | None = None
    if loaded_revision and loaded_content_sha256:
        try:
            observed = ContractIdentity(loaded_revision, loaded_content_sha256)
        except ValueError:
            observed = None
    return ContractAttestation(
        stage=DeploymentStage.LOADED,
        expected=expected,
        observed=observed,
    )


def _read_manifest_identity(skill_dir: Path) -> ContractIdentity | None:
    manifest_path = skill_dir / "references" / "contract-manifest.json"
    if not manifest_path.is_file():
        return None
    try:
        data = json.loads(manifest_path.read_text())
        return ContractIdentity(
            revision=str(data["contract_revision"]),
            content_sha256=str(data["content_sha256"]),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def inspect_skill_directory(
    skill_dir: str | Path,
    *,
    stage: DeploymentStage = DeploymentStage.INSTALLED,
    expected: ContractIdentity = CURRENT_CONTRACT,
) -> ContractAttestation:
    """Attest one filesystem Skill tree against the expected contract."""

    path = Path(skill_dir)
    if not path.is_dir():
        return ContractAttestation(stage=stage, expected=expected, observed=None)

    identity = _read_manifest_identity(path)
    if identity is None:
        return ContractAttestation(stage=stage, expected=expected, observed=None)

    try:
        computed = compute_skill_content_sha256(path)
    except OSError:
        computed = None

    return ContractAttestation(
        stage=stage,
        expected=expected,
        observed=identity,
        computed_content_sha256=computed,
    )


def sync_skill_install(
    source_dir: str | Path,
    install_root: str | Path,
    *,
    check_only: bool = False,
    expected: ContractIdentity = CURRENT_CONTRACT,
) -> ContractAttestation:
    """Check or atomically replace <install_root>/repo-learning from canonical source."""

    source = Path(source_dir)
    source_attestation = inspect_skill_directory(
        source,
        stage=DeploymentStage.SOURCE,
        expected=expected,
    )
    if not source_attestation.current:
        raise ValueError(
            f"source skill contract is not current: {source_attestation.defect.value}"
        )

    root = Path(install_root).expanduser()
    target = root / "repo-learning"
    if check_only:
        return inspect_skill_directory(
            target,
            stage=DeploymentStage.INSTALLED,
            expected=expected,
        )

    root.mkdir(parents=True, exist_ok=True)
    staged = root / f".repo-learning.stage-{uuid.uuid4().hex}"
    backup = root / f".repo-learning.backup-{uuid.uuid4().hex}"
    shutil.copytree(source, staged)

    staged_attestation = inspect_skill_directory(
        staged,
        stage=DeploymentStage.PACKAGE,
        expected=expected,
    )
    if not staged_attestation.current:
        shutil.rmtree(staged, ignore_errors=True)
        raise ValueError(
            f"staged skill contract is not current: {staged_attestation.defect.value}"
        )

    moved_old = False
    try:
        if target.exists():
            os.replace(target, backup)
            moved_old = True
        os.replace(staged, target)
    except Exception:
        if staged.exists():
            shutil.rmtree(staged, ignore_errors=True)
        if moved_old and backup.exists() and not target.exists():
            os.replace(backup, target)
        raise
    else:
        if backup.exists():
            shutil.rmtree(backup)

    return inspect_skill_directory(
        target,
        stage=DeploymentStage.INSTALLED,
        expected=expected,
    )
