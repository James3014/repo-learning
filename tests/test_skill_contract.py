from pathlib import Path

SKILL = Path("skills/repo-learning/SKILL.md").read_text()
POLICY = Path("skills/repo-learning/references/policy.md").read_text()
STATE = Path("skills/repo-learning/references/state-contract.md").read_text()


def test_repository_pointer_is_primary_activation_for_enrolled_repo():
    assert "a loaded repository instruction pointer that declares RepoLearn `ENABLED` is the primary activation path" in SKILL
    assert "automatic Skill selection is convenience/fallback only" in SKILL
    assert "a loaded repository instruction pointer is the primary RepoLearn activation signal" in POLICY
    assert "Automatic Skill discovery is convenience/fallback only" in POLICY


def test_unspecified_mode_defaults_to_guided_for_manual_repo_and_auto_selection():
    assert "Unless the user, host, or loaded repository activation pointer explicitly selects `observe` or `practice`, use `guided` mode." in SKILL
    assert "Default to `guided` when the user, host, or loaded repository activation pointer does not explicitly select a mode." in POLICY


def test_explicit_activation_is_positive_trigger_when_architecture_work_qualifies():
    assert "For an **explicit activation** (repository pointer or explicit user/host invocation)" in SKILL
    assert "classify the task as `LEARNING_OPPORTUNITY`" in SKILL
    assert "Do not choose `NO_TRIGGER` merely because low interruption is preferred" in SKILL
    assert "For an **explicit activation** (loaded repository pointer or explicit user/host invocation)" in POLICY
    assert "Do not use the general low-interruption preference as a reason to choose `NO_TRIGGER`" in POLICY
    assert "This positive-control rule also applies when bounded state is `UNASSESSED`" in POLICY


def test_explicit_activation_hard_suppressors_are_bounded():
    assert "Hard suppressors are:" in SKILL
    assert "Client-native chat memory alone is not such evidence" in SKILL
    assert "Hard suppressors for the explicit-activation path are limited to" in POLICY
    assert "Chat memory by itself is not sufficient evidence for cue-fading suppression" in POLICY


def test_selected_guided_opportunity_chooses_exactly_one_learning_branch():
    assert "`LEARNING_OPPORTUNITY`: choose exactly one of the following two branches" in SKILL
    assert "`JUDGMENT_PROMPT`" in SKILL
    assert "`SPONTANEOUS_JUDGMENT_CAPTURE`" in SKILL
    assert "choose exactly one interaction branch" in POLICY


def test_guided_prompt_branch_requires_role_first_comprehensibility():
    assert "Surface exactly one concise primary architecture judgment prompt" in SKILL
    assert "MUST be understandable from roles, decisions, and trade-offs in plain language" in SKILL
    assert "Use role-first, identifier-second framing" in SKILL
    assert "Apply an identifier-removal check before emitting the prompt" in SKILL
    assert "Do not turn source recall into an architecture test" in SKILL
    assert "Emit exactly one concise primary judgment prompt" in POLICY
    assert "Plain-language-first is mandatory" in POLICY
    assert "Use role-first, identifier-second framing" in POLICY
    assert "perform an identifier-removal check" in POLICY
    assert "Do not ask the user to name an internal contract/component" in POLICY


def test_prompt_comprehension_defect_is_not_user_regression_or_skip():
    assert "incomprehensible identifier-first prompt is an interaction defect" in SKILL
    assert "not `skip/no-response`" in SKILL
    assert "classify that interaction as a prompt-comprehension defect" in POLICY
    assert "rather than user failure, skip/no-response, or mastery regression" in POLICY


def test_guided_prompt_must_remain_visible_in_final_response():
    assert "counts as emitted only when that architecture question appears in the durable final user-visible assistant response" in SKILL
    assert "transient progress/status messages do not satisfy this requirement" in SKILL
    assert "include the single primary judgment question in the final response" in SKILL
    assert "counts as emitted only if the architecture question appears in the durable final user-visible assistant response" in POLICY
    assert "intermediate surface, include the single primary judgment question in the final response" in POLICY


def test_prompt_visibility_defect_is_not_user_skip_or_regression():
    assert "prompt-visibility defect, not `skip/no-response`" in SKILL
    assert "Prompt visibility is also part of the interaction contract" in POLICY
    assert "Classify that interaction as a prompt-visibility defect" in POLICY
    assert "rather than user failure, skip/no-response, or mastery regression" in POLICY


def test_guided_prompt_must_precede_answer_revealing_content():
    assert "place the judgment question before the first substantive recommendation, conclusion, or decisive evidence" in SKILL
    assert "Perform a pre-evidence ordering check before sending" in SKILL
    assert "judgment question must appear before the first substantive recommendation, conclusion, or decisive evidence" in POLICY
    assert "perform a pre-evidence ordering check" in POLICY


def test_pre_evidence_ordering_defect_is_not_user_skip_or_regression():
    assert "pre-evidence-ordering defect, not `skip/no-response`" in SKILL
    assert "Pre-evidence ordering is part of the interaction contract as well" in POLICY
    assert "classify the interaction as a pre-evidence-ordering defect" in POLICY
    assert "post-evidence agreement and cannot be promoted to pre-evidence mastery evidence" in POLICY


def test_spontaneous_judgment_capture_does_not_requiz():
    assert "Do not re-ask the judgment" in SKILL
    assert "give bounded feedback on the reasoning rather than mere agreement" in SKILL
    assert "extract one reusable principle in plain language" in SKILL
    assert "state one important applicability boundary or counterexample" in SKILL
    assert "Do not re-ask the judgment" in POLICY
    assert "give bounded feedback on the reasoning rather than mere agreement" in POLICY


def test_plain_language_judgment_is_eligible_without_terminology():
    assert "Engineering vocabulary is not a prerequisite for either branch" in SKILL
    assert "Engineering terminology is not a prerequisite for architecture evidence" in SKILL
    assert "Engineering vocabulary is not a prerequisite for architecture evidence" in POLICY
    assert "English terminology friction must not lower mastery" in POLICY


def test_only_pre_feedback_user_reasoning_can_count_as_mastery_evidence():
    assert "only reasoning expressed before RepoLearn feedback or decisive evidence may count as candidate mastery evidence" in SKILL
    assert "the AI's reformulation, naming, or explanation is exposure, not user evidence" in SKILL
    assert "Only the user's reasoning expressed before RepoLearn feedback or decisive evidence may support a mastery update" in POLICY
    assert "the translation itself is not user evidence" in POLICY


def test_post_evidence_agreement_is_not_spontaneous_pre_evidence_judgment():
    assert "decisive evidence has not already supplied the answer" in SKILL
    assert "If decisive evidence or the relevant answer was already revealed before the user's statement" in POLICY
    assert "do not relabel later agreement or paraphrase as spontaneous pre-evidence judgment" in POLICY


def test_no_trigger_remains_silent_and_nonblocking():
    assert "`NO_TRIGGER`: emit no learning interaction and continue normal engineering." in SKILL
    assert "`NO_TRIGGER`: emit no learning interaction and continue normal engineering." in POLICY
    assert "continue normal engineering without waiting" in SKILL


def test_unanswered_prompt_remains_fail_open_without_second_prompt():
    assert "classify it as `skip/no-response` and continue normal engineering without waiting" in SKILL
    assert "Do not emit a second prompt for the same selected point" in SKILL
    assert "Do not emit another prompt for the same selected point" in POLICY


def test_auto_discovery_does_not_prove_repository_activation():
    assert "Auto-discovery alone must not be used as proof that a repository activated RepoLearn." in SKILL
    assert "do not infer repository activation from Skill installation, inventory presence, or auto-discovery alone" in POLICY


def test_missing_state_is_unassessed_not_mastery_or_backend_failure():
    assert "Treat a missing profile/state as `UNASSESSED`" in SKILL
    assert "not evidence of mastery" in POLICY
    assert "A missing profile/state from an otherwise available backend is `UNASSESSED`." in STATE
    assert "does not by itself suppress an otherwise qualifying guided interaction" in STATE
    assert "Do not claim silent cue-fading suppression from chat memory alone" in POLICY
