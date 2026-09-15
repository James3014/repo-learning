from __future__ import annotations

from dataclasses import replace

import pytest

from repolearn.migration import MigrationEvidence, MigrationPreflightError, RollbackEvidence, dry_run_migration_preflight


HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64


def evidence() -> MigrationEvidence:
    return MigrationEvidence(
        source_backend="nexus-ledger-readthrough",
        source_revision="46f47bc",
        source_content_hash=HASH_A,
        source_readback_hash=HASH_A,
        destination_identity="local-file:james",
        destination_content_hash=HASH_B,
        destination_readback_hash=HASH_B,
        source_event_count=12,
        destination_event_count=12,
        source_projection_hash=HASH_C,
        destination_projection_hash=HASH_C,
        rollback=RollbackEvidence(source_content_hash=HASH_A, artifact_hash=HASH_B, restorable=True),
        current_writable_ssot="nexus-ledger-readthrough",
        destination_write_enabled=False,
        explicit_cutover=False,
    )


def test_complete_preflight_is_ready_but_does_not_cut_over_or_write() -> None:
    result = dry_run_migration_preflight(evidence())
    assert result.ready_for_explicit_cutover
    assert result.writable_ssot == "nexus-ledger-readthrough"
    assert not result.performed_migration
    assert not result.destination_write_enabled


@pytest.mark.parametrize(
    "changed,match",
    [
        ({"source_revision": ""}, "source_revision"),
        ({"source_readback_hash": HASH_B}, "stale source"),
        ({"destination_readback_hash": HASH_A}, "destination readback"),
        ({"destination_event_count": 11}, "event count"),
        ({"destination_projection_hash": HASH_A}, "projection"),
        ({"rollback": None}, "rollback"),
        ({"rollback": RollbackEvidence(source_content_hash=HASH_B, artifact_hash=HASH_B, restorable=True)}, "rollback source"),
        ({"rollback": RollbackEvidence(source_content_hash=HASH_A, artifact_hash=HASH_B, restorable=False)}, "restorable"),
        ({"destination_write_enabled": True}, "single writable SSOT"),
        ({"current_writable_ssot": "local-file:james"}, "source backend"),
        ({"conflicting_evidence": True}, "conflicting evidence"),
        ({"reassessment_required": True}, "conflicting evidence"),
        ({"explicit_cutover": True}, "cannot perform"),
    ],
)
def test_preflight_fails_closed_on_missing_stale_or_conflicting_evidence(changed: dict, match: str) -> None:
    with pytest.raises(MigrationPreflightError, match=match):
        dry_run_migration_preflight(replace(evidence(), **changed))
