"""Privacy/readiness checks for a later Friend Alpha gate.

This module validates that the local product surface is safe enough to present to
an Alpha gate. It does not enroll a participant or prove Alpha usability.
"""

from __future__ import annotations

from dataclasses import dataclass


ALPHA_PREP_NOT_ALPHA = "G8-PREP readiness only; no Friend Alpha enrollment or usability claim is performed."


@dataclass(frozen=True)
class AlphaReadinessEvidence:
    private_state_isolated: bool
    export_available: bool
    delete_available: bool
    reset_available: bool
    privacy_disclosure_present: bool
    consent_flow_defined: bool
    failure_degrades_without_blocking: bool
    repository_stores_personal_mastery: bool = False
    persists_source_excerpts_by_default: bool = False
    persists_transcripts_by_default: bool = False
    persists_secrets: bool = False


@dataclass(frozen=True)
class AlphaReadinessResult:
    ready_for_friend_alpha_gate: bool
    performs_enrollment: bool
    claim_ceiling: str
    blockers: tuple[str, ...]


def check_alpha_readiness(evidence: AlphaReadinessEvidence) -> AlphaReadinessResult:
    blockers: list[str] = []
    for name, value in (
        ("private_state_isolated", evidence.private_state_isolated),
        ("export_available", evidence.export_available),
        ("delete_available", evidence.delete_available),
        ("reset_available", evidence.reset_available),
        ("privacy_disclosure_present", evidence.privacy_disclosure_present),
        ("consent_flow_defined", evidence.consent_flow_defined),
        ("failure_degrades_without_blocking", evidence.failure_degrades_without_blocking),
    ):
        if not value:
            blockers.append(name)
    for name, value in (
        ("repository_stores_personal_mastery", evidence.repository_stores_personal_mastery),
        ("persists_source_excerpts_by_default", evidence.persists_source_excerpts_by_default),
        ("persists_transcripts_by_default", evidence.persists_transcripts_by_default),
        ("persists_secrets", evidence.persists_secrets),
    ):
        if value:
            blockers.append(name)
    return AlphaReadinessResult(
        ready_for_friend_alpha_gate=not blockers,
        performs_enrollment=False,
        claim_ceiling=ALPHA_PREP_NOT_ALPHA,
        blockers=tuple(blockers),
    )
