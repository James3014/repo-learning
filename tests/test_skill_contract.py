from pathlib import Path

SKILL = Path("skills/repo-learning/SKILL.md").read_text()
POLICY = Path("skills/repo-learning/references/policy.md").read_text()


def test_unspecified_mode_defaults_to_guided_for_manual_and_auto_selection():
    assert "Unless the user or host explicitly selects `observe` or `practice`, use `guided` mode." in SKILL
    assert "explicit RepoLearn invocation and automatic Skill selection" in SKILL
    assert "Default to `guided` when the user or host does not explicitly select a mode." in POLICY
    assert "automatic Skill selection" in POLICY


def test_default_guided_still_preserves_low_interruption_and_pre_evidence_prompting():
    assert "Guided is the default interaction policy, not a requirement to prompt on every task" in SKILL
    assert "surface the judgment point before revealing decisive evidence" in SKILL
    assert "Guided does not require a visible prompt on every task; apply the trigger policy first." in POLICY
