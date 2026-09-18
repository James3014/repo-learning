# RepoLearn Repository Activation Contract v1

RepoLearn is a portable learning capability, but repository enrollment must not depend on probabilistic Skill auto-discovery.

This contract separates **repository activation** from **RepoLearn learning policy**.

## Authority split

- The **target repository** owns whether RepoLearn is enabled for work in that repository and exposes that decision through its normal instruction surface.
- **James3014/repo-learning** owns canonical RepoLearn trigger, interaction, assessment, cue-fading, privacy, state-adapter, and persistence contracts.
- The active learning-state backend owns the user's canonical personal-learning state under its own state contract.
- RepoLearn never acquires target-repository engineering authority.

A target repository must not copy RepoLearn's trigger, assessment, mastery, persistence, or cue-fading rules. Its local adapter is activation/context only.

## Activation sources

Use these as distinct evidence classes:

1. **Repository activation pointer** — primary path for an enrolled repository when the host actually loads that repository's instruction surface.
2. **Explicit user/host invocation** — deterministic manual control when RepoLearn is available.
3. **Automatic Skill discovery** — convenience/fallback only. It may improve ergonomics, but it is not repository-enrollment authority and must not be required for repository correctness claims.

If the host did not load the target repository's instruction surface, do not claim repository activation merely because the Skill is installed, appears in an inventory, or happened to auto-trigger.

## Thin pointer contract

An enrolled target repository should expose a short pointer through its authoritative instruction file or a client-specific projection of that file. The pointer may contain only:

- activation status (`ENABLED` / `DISABLED`);
- canonical RepoLearn source (`James3014/repo-learning`);
- canonical skill/capability name (`repo-learning`);
- selected interaction mode (`observe`, `guided`, or `practice`);
- fail-open behavior for learning unavailability;
- an explicit statement that target-repository engineering authority is unchanged.

Example:

```text
RepoLearn: ENABLED
Canonical source: James3014/repo-learning
Capability: repo-learning
Mode: guided
Failure behavior: continue normal engineering if RepoLearn is unavailable
Authority: this repository's existing engineering authority remains unchanged
```

Do not copy the canonical trigger rules, assessment rubric, mastery levels, persistence logic, or personal learning state into the target repository.

## Host/client behavior

When a host loads a repository instruction surface that declares RepoLearn `ENABLED`:

1. Treat the repository pointer as an explicit RepoLearn activation signal for that repository.
2. Load/use the canonical RepoLearn capability before substantive architecture guidance when the capability is available.
3. Apply the canonical RepoLearn Skill/policy; do not reinterpret the local pointer as a second policy source.
4. If the capability or learning backend is unavailable, continue normal engineering and preserve the repository's existing authority and verification rules.
5. Do not claim learning occurred unless the interaction/state evidence separately supports that claim.

A client that cannot load the repository instruction surface cannot provide deterministic repository activation through this mechanism. It may use explicit invocation or automatic discovery, but those are separate activation classes and should be reported as such.

## Evidence model

Keep these claims separate:

```text
repository_enrolled
!= repository_instruction_loaded
!= canonical_capability_loaded
!= learning_state_loaded
!= trigger_selected
!= visible_learning_interaction
!= learning_event_persisted
```

For dogfood/rollout diagnostics, prefer a bounded receipt. The executable `repolearn.interaction_observation.v1` receipt records classifications and booleans rather than prompt/transcript text, including:

```text
activation_source
trigger_selected
selected_branch
spontaneous_judgment_present
branch_selection_valid
prompt_generated
prompt_answerable_without_repo_vocabulary
terminology_clarification_required
prompt_visible_in_final_response
prompt_before_decisive_evidence
answer_revealing_progress_before_prompt
response_present
response_relevance
engineering_blocked
interaction_defect
cue_fading_suppressed
cue_level
transfer_distance
```

Repository/revision provenance may be carried separately by the host when privacy policy permits; it is intentionally not required inside the generic interaction receipt.

Do not include source excerpts, secrets, transcripts, private repository material, or full mastery history in public receipts.

## Reliability claim ceiling

A repository can claim **deterministic RepoLearn activation** only when its activation pointer is present and the tested host/client is proven to load that instruction surface.

Skill installation or automatic Skill discovery alone cannot support that claim.
