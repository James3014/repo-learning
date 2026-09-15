import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from repolearn.assessment import AssessmentEvidence, MasteryLevel, assess_mastery_effect
from repolearn.triggers import InteractionMode, TriggerContext, decide_trigger

SCHEMAS = Path(__file__).parents[1] / "schemas"


def schema(name):
    return json.loads((SCHEMAS / name).read_text())


def test_learning_state_accepts_unassessed_and_bounded_frontiers():
    data = {"schema":"repolearn.learning_state.v1","profile_id":"user-1","revision":"r1","mastery":{"architecture":"UNASSESSED"},"priority_frontiers":["state identity"]}
    Draft202012Validator(schema("learning_state.v1.json")).validate(data)


def test_learning_state_rejects_more_than_three_frontiers():
    data = {"schema":"repolearn.learning_state.v1","profile_id":"u","revision":"r","mastery":{},"priority_frontiers":["a","b","c","d"]}
    with pytest.raises(ValidationError):
        Draft202012Validator(schema("learning_state.v1.json")).validate(data)


def test_repository_defaults_keep_source_excerpt_writeback_explicit():
    data = {"schema":"repolearn.repository.v1","repository":{"id":"acme/api"},"learning":{"enabled":True,"default_mode":"guided"},"authority":{"source":"AGENTS.md"},"privacy":{"allow_source_excerpt_writeback":False}}
    Draft202012Validator(schema("repository.v1.json")).validate(data)


def test_event_rejects_unknown_cue_level():
    data = {"schema":"repolearn.learning_event.v1","event_id":"e1","observed_at":"2026-09-15T00:00:00Z","profile_id":"u","context":{"repository_id":"acme/api"},"capability":{"domain":"architecture","concept":"ownership"},"attempt":{"cue_level":"MAGIC","transfer_distance":"NEAR_TRANSFER","delay":"7d"},"assessment":{"classification":"CORRECT","mastery_effect":"L2","rationale":"x"},"learning":{"reusable_principle":"p","applicability_boundary":"b"}}
    with pytest.raises(ValidationError):
        Draft202012Validator(schema("learning_event.v1.json")).validate(data)


def test_trigger_is_silent_for_exact_output_even_when_case_is_good():
    d = decide_trigger(TriggerContext(real_architecture_alternative=True,relevant_to_frontier=True,exact_output=True))
    assert not d.prompt and d.reason == "exact_output"


def test_trigger_allows_one_guided_point_for_high_value_case():
    d = decide_trigger(TriggerContext(real_architecture_alternative=True,relevant_to_frontier=True))
    assert d.prompt and d.max_primary_learning_points == 1


def test_observe_mode_never_prompts():
    d = decide_trigger(TriggerContext(mode=InteractionMode.OBSERVE,real_architecture_alternative=True,relevant_to_frontier=True))
    assert not d.prompt and d.max_primary_learning_points == 0


def test_missing_state_is_not_l0():
    level = assess_mastery_effect(AssessmentEvidence(demonstrated_by_user=True,state_available=False))
    assert level is MasteryLevel.UNASSESSED


def test_ai_explanation_is_not_user_mastery():
    level = assess_mastery_effect(AssessmentEvidence(demonstrated_by_user=False,ai_explanation_only=True))
    assert level is MasteryLevel.UNASSESSED


def test_l3_requires_independent_transfer_and_tradeoff():
    level = assess_mastery_effect(AssessmentEvidence(demonstrated_by_user=True,independent_judgment=True,materially_different_case=True,explained_tradeoff=True))
    assert level is MasteryLevel.L3


def test_l4_requires_proactive_falsifier_plus_independence():
    level = assess_mastery_effect(AssessmentEvidence(demonstrated_by_user=True,independent_judgment=True,proactive_falsifier=True))
    assert level is MasteryLevel.L4
