from pathlib import Path

SKILL = Path("skills/repo-learning/SKILL.md").read_text()
POLICY = Path("skills/repo-learning/references/policy.md").read_text()
STATE = Path("skills/repo-learning/references/state-contract.md").read_text()


def test_unspecified_mode_defaults_to_guided_for_manual_and_auto_selection():
    assert "Unless the user or host explicitly selects `observe` or `practice`, use `guided` mode." in SKILL
    assert "explicit RepoLearn invocation and automatic Skill selection" in SKILL
    assert "Default to `guided` when the user or host does not explicitly select a mode." in POLICY
    assert "automatic Skill selection" in POLICY


def test_explicit_invocation_is_positive_trigger_when_architecture_work_qualifies():
    assert "treat the user's request to use RepoLearn as acceptance of one low-cost learning interruption" in SKILL
    assert "classify the task as `LEARNING_OPPORTUNITY`" in SKILL
    assert "Do not choose `NO_TRIGGER` merely because low interruption is preferred" in SKILL
    assert "treat the user's request to use RepoLearn as acceptance of one low-cost interruption" in POLICY
    assert "Do not use the general low-interruption preference as a reason to choose `NO_TRIGGER`" in POLICY
    assert "This positive-control rule also applies when bounded state is `UNASSESSED`" in POLICY


def test_explicit_invocation_hard_suppressors_are_bounded():
    assert "Hard suppressors are:" in SKILL
    assert "Client-native chat memory alone is not such evidence" in SKILL
    assert "Hard suppressors for the explicit-invocation path are limited to" in POLICY
    assert "Chat memory by itself is not sufficient evidence for cue-fading suppression" in POLICY


def test_selected_guided_opportunity_requires_exactly_one_prompt_before_solution():
    assert "enforce this hard two-branch contract" in SKILL
    assert "MUST surface exactly one concise primary architecture judgment prompt" in SKILL
    assert "MUST NOT be converted into explanation-only output" in SKILL
    assert "before any substantive recommendation, conclusion, or decisive evidence" in POLICY
    assert "MUST emit exactly one concise primary judgment prompt" in POLICY


def test_no_trigger_remains_silent_and_nonblocking():
    assert "`NO_TRIGGER`: emit no learning prompt and continue normal engineering." in SKILL
    assert "`NO_TRIGGER`: emit no learning prompt and continue normal engineering." in POLICY
    assert "continue normal engineering without waiting" in SKILL


def test_missing_state_is_unassessed_not_mastery_or_backend_failure():
    assert "Treat a missing profile/state as `UNASSESSED`" in SKILL
    assert "not evidence of mastery" in POLICY
    assert "A missing profile/state from an otherwise available backend is `UNASSESSED`." in STATE
    assert "does not by itself suppress an otherwise qualifying guided interaction" in STATE
    assert "Do not claim silent cue-fading suppression from chat memory alone" in POLICY
