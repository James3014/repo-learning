"""G7 migration preflight primitives.

This module validates evidence for a later explicit single-SSOT cutover. It never
performs migration, enables destination writes, or changes canonical ownership.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
import re


_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


class MigrationPreflightError(ValueError):
    """Raised when migration evidence is incomplete, stale, or conflicting."""


@dataclass(frozen=True)
class RollbackEvidence:
    source_content_hash: str
    artifact_hash: str
    restorable: bool


@dataclass(frozen=True)
class MigrationEvidence:
    source_backend: str
    source_revision: str
    source_content_hash: str
    source_readback_hash: str
    destination_identity: str
    destination_content_hash: str
    destination_readback_hash: str
    source_event_count: int
    destination_event_count: int
    source_projection_hash: str
    destination_projection_hash: str
    rollback: RollbackEvidence | None
    current_writable_ssot: str
    destination_write_enabled: bool
    explicit_cutover: bool
    conflicting_evidence: bool = False
    reassessment_required: bool = False


@dataclass(frozen=True)
class MigrationPreflightResult:
    ready_for_explicit_cutover: bool
    writable_ssot: str
    destination_write_enabled: bool
    performed_migration: bool
    evidence_digest: str


def _require_hash(name: str, value: str) -> None:
    if not isinstance(value, str) or not _HASH_RE.fullmatch(value):
        raise MigrationPreflightError(f"{name} must be a lowercase sha256 hash")


def _evidence_digest(evidence: MigrationEvidence) -> str:
    payload = json.dumps(asdict(evidence), sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def dry_run_migration_preflight(evidence: MigrationEvidence) -> MigrationPreflightResult:
    """Fail closed unless all evidence supports a later explicit cutover.

    A successful result means only that the supplied evidence is internally
    consistent enough to present to an explicit cutover gate. This function never
    performs that cutover.
    """

    if not evidence.source_backend.strip():
        raise MigrationPreflightError("source_backend is required")
    if not evidence.source_revision.strip():
        raise MigrationPreflightError("source_revision is required")
    if not evidence.destination_identity.strip():
        raise MigrationPreflightError("destination_identity is required")

    for name, value in (
        ("source_content_hash", evidence.source_content_hash),
        ("source_readback_hash", evidence.source_readback_hash),
        ("destination_content_hash", evidence.destination_content_hash),
        ("destination_readback_hash", evidence.destination_readback_hash),
        ("source_projection_hash", evidence.source_projection_hash),
        ("destination_projection_hash", evidence.destination_projection_hash),
    ):
        _require_hash(name, value)

    if evidence.source_readback_hash != evidence.source_content_hash:
        raise MigrationPreflightError("stale source evidence: source readback hash differs")
    if evidence.destination_readback_hash != evidence.destination_content_hash:
        raise MigrationPreflightError("destination readback hash differs from prepared destination")
    if evidence.source_event_count < 0 or evidence.destination_event_count < 0:
        raise MigrationPreflightError("event count must be non-negative")
    if evidence.source_event_count != evidence.destination_event_count:
        raise MigrationPreflightError("event count mismatch between source and destination")
    if evidence.source_projection_hash != evidence.destination_projection_hash:
        raise MigrationPreflightError("projection equivalence is not proven")
    if evidence.conflicting_evidence or evidence.reassessment_required:
        raise MigrationPreflightError("conflicting evidence requires reassessment before migration")

    rollback = evidence.rollback
    if rollback is None:
        raise MigrationPreflightError("rollback evidence is required")
    _require_hash("rollback.source_content_hash", rollback.source_content_hash)
    _require_hash("rollback.artifact_hash", rollback.artifact_hash)
    if rollback.source_content_hash != evidence.source_content_hash:
        raise MigrationPreflightError("rollback source hash is not bound to the migration source")
    if rollback.artifact_hash != evidence.destination_content_hash:
        raise MigrationPreflightError("rollback artifact hash is not bound to the prepared destination")
    if not rollback.restorable:
        raise MigrationPreflightError("rollback evidence must be restorable")

    if evidence.current_writable_ssot != evidence.source_backend:
        raise MigrationPreflightError("current writable SSOT must remain the source backend during preflight")
    if evidence.destination_write_enabled:
        raise MigrationPreflightError("single writable SSOT invariant forbids destination writes before cutover")
    if evidence.explicit_cutover:
        raise MigrationPreflightError("dry-run preflight cannot perform or accept an explicit cutover")

    return MigrationPreflightResult(
        ready_for_explicit_cutover=True,
        writable_ssot=evidence.current_writable_ssot,
        destination_write_enabled=False,
        performed_migration=False,
        evidence_digest=_evidence_digest(evidence),
    )
