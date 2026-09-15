from __future__ import annotations

import hashlib

import pytest

from repolearn import NexusLedgerBackend, ReadOnlyCanonicalBackendError, StaleProjectionError


LEDGER = """---
artifact_authority: owner_learning_record
---

# Owner Ledger

## Current Learning State — bounded bootstrap projection

**目前狀態修訂：** `2026-09-15 / LA-20260915-001`

### Domain-level mastery view

| Architecture domain | 目前等級 | 證據邊界 | 下一個有用的真實案例 |
|---|---|---|---|
| 問題與目標界定 | UNASSESSED | x | y |
| 責任、介面與權責劃分 | L1 | x | y |
| 資料、狀態與身分設計 | UNASSESSED | x | y |
| 整體運作與失敗控制 | UNASSESSED | x | y |
| 成本、組織與系統演進取捨 | UNASSESSED | x | y |
| 假設、證據與反證 | UNASSESSED | x | y |

## 熟練度等級
"""


def test_nexus_ledger_projects_current_state_without_becoming_owner():
    digest = hashlib.sha256(LEDGER.encode()).hexdigest()
    backend = NexusLedgerBackend(LEDGER, source_revision="84bd08a", expected_content_hash=digest)
    state = backend.read_current_state("james")

    assert state["schema"] == "repolearn.learning_state.v1"
    assert state["domains"]["責任、介面與權責劃分"]["level"] == "L1"
    assert state["source"]["backend"] == "nexus-ledger-readthrough"
    assert "LA-20260915-001" in state["source"]["revision"]

    with pytest.raises(ReadOnlyCanonicalBackendError):
        backend.append_learning_event("james", {"event_id": "must-not-write"})


def test_nexus_ledger_hash_mismatch_fails_closed():
    with pytest.raises(StaleProjectionError):
        NexusLedgerBackend(LEDGER, source_revision="84bd08a", expected_content_hash="0" * 64)
