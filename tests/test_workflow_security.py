from __future__ import annotations

import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
GUARD_ID = "same-repo-guard"

_TRIGGER = re.compile(r"^\s*pull_request_target\s*:", re.MULTILINE)
_HEAD_CHECKOUT = re.compile(r"ref:\s*\$\{\{\s*github\.event\.pull_request\.head\.")
_STEP_START = re.compile(r"^(\s*)- (?:name|uses|id|run):", re.MULTILINE)


def _steps(text: str) -> list[str]:
    starts = list(_STEP_START.finditer(text))
    return [text[m.start() : (starts[i + 1].start() if i + 1 < len(starts) else len(text))] for i, m in enumerate(starts)]


def unsafe_head_checkout(text: str) -> str | None:
    """Return why a workflow runs PR head code in the target context without a same-repo guard, or None."""
    if not _TRIGGER.search(text) or not _HEAD_CHECKOUT.search(text):
        return None
    steps = _steps(text)
    if not steps:
        return "pull_request_target workflow checks out the PR head but has no steps"
    first = steps[0]
    if f"id: {GUARD_ID}" not in first:
        return f"first step must be the '{GUARD_ID}' step, before any checkout of the PR head"
    if "github.event.pull_request.head.repo.full_name" not in first or "github.repository" not in first:
        return f"'{GUARD_ID}' must compare the PR head repo with github.repository"
    if "exit 1" not in first or re.search(r"^\s*if:", first, re.MULTILINE):
        return f"'{GUARD_ID}' must fail the job for fork PRs, not skip"
    return None


@pytest.mark.parametrize("path", sorted(WORKFLOWS.glob("*.yml")), ids=lambda p: p.name)
def test_pull_request_target_head_checkout_is_same_repo_only(path: Path) -> None:
    assert unsafe_head_checkout(path.read_text(encoding="utf-8")) is None


def test_core_gate_workflow_links_threat_model() -> None:
    text = (WORKFLOWS / "nexus-core-issue-completion.yml").read_text(encoding="utf-8")
    assert "docs/CI_THREAT_MODEL.md" in text
    assert (ROOT / "docs" / "CI_THREAT_MODEL.md").is_file()


_GUARD = """\
      - name: Reject fork pull requests
        id: same-repo-guard
        env:
          HEAD_REPO: ${{ github.event.pull_request.head.repo.full_name }}
          BASE_REPO: ${{ github.repository }}
        run: |
          if [ "$HEAD_REPO" != "$BASE_REPO" ]; then exit 1; fi
"""
_CHECKOUT = """\
      - name: Checkout
        uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}
"""
_HEADER = "on:\n  pull_request_target:\njobs:\n  gate:\n    steps:\n"


def test_lint_rejects_head_checkout_without_guard() -> None:
    assert unsafe_head_checkout(_HEADER + _CHECKOUT) is not None


def test_lint_rejects_guard_after_checkout() -> None:
    assert unsafe_head_checkout(_HEADER + _CHECKOUT + _GUARD) is not None


def test_lint_rejects_guard_that_skips() -> None:
    skipping = _GUARD.replace("        id: same-repo-guard\n", "        id: same-repo-guard\n        if: false\n")
    assert unsafe_head_checkout(_HEADER + skipping + _CHECKOUT) is not None


def test_lint_accepts_guard_before_checkout() -> None:
    assert unsafe_head_checkout(_HEADER + _GUARD + _CHECKOUT) is None


def test_lint_ignores_pull_request_trigger() -> None:
    assert unsafe_head_checkout("on:\n  pull_request:\njobs:\n  t:\n    steps:\n" + _CHECKOUT) is None
