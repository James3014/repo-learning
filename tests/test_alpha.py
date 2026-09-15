from __future__ import annotations

from dataclasses import replace

import pytest

from repolearn.alpha import ALPHA_PREP_NOT_ALPHA, AlphaReadinessEvidence, check_alpha_readiness


def evidence() -> AlphaReadinessEvidence:
    return AlphaReadinessEvidence(
        private_state_isolated=True,
        export_available=True,
        delete_available=True,
        reset_available=True,
        privacy_disclosure_present=True,
        consent_flow_defined=True,
        failure_degrades_without_blocking=True,
    )


def test_alpha_readiness_is_prep_only_and_never_enrolls() -> None:
    result = check_alpha_readiness(evidence())
    assert result.ready_for_friend_alpha_gate
    assert not result.performs_enrollment
    assert result.claim_ceiling == ALPHA_PREP_NOT_ALPHA
    assert result.blockers == ()


@pytest.mark.parametrize(
    "changed,blocker",
    [
        ({"private_state_isolated": False}, "private_state_isolated"),
        ({"export_available": False}, "export_available"),
        ({"delete_available": False}, "delete_available"),
        ({"reset_available": False}, "reset_available"),
        ({"privacy_disclosure_present": False}, "privacy_disclosure_present"),
        ({"consent_flow_defined": False}, "consent_flow_defined"),
        ({"failure_degrades_without_blocking": False}, "failure_degrades_without_blocking"),
        ({"repository_stores_personal_mastery": True}, "repository_stores_personal_mastery"),
        ({"persists_source_excerpts_by_default": True}, "persists_source_excerpts_by_default"),
        ({"persists_transcripts_by_default": True}, "persists_transcripts_by_default"),
        ({"persists_secrets": True}, "persists_secrets"),
    ],
)
def test_alpha_readiness_fails_closed_on_privacy_or_control_gap(changed: dict, blocker: str) -> None:
    result = check_alpha_readiness(replace(evidence(), **changed))
    assert not result.ready_for_friend_alpha_gate
    assert blocker in result.blockers
