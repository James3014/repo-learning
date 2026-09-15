---
name: repo-learning
description: Preserve and strengthen a developer's architecture judgment during real AI-assisted engineering work. Use when a task contains a meaningful system-design trade-off, authority/ownership boundary, state/identity continuity decision, failure-control choice, architecture-evolution trade-off, or evidence/falsification question. When loaded repository instructions explicitly enable RepoLearn, treat that pointer as the primary repository activation signal; automatic Skill discovery is convenience only, not repository-activation evidence. Default to guided, keep interruption bounded, and never change repository engineering authority.
---

# RepoLearn

Use RepoLearn as a non-authoritative human-learning layer during real engineering work.

## Core workflow

1. Continue to follow the target repository's own engineering authority and instructions first.
2. Load only the bounded current learning state required for the task. Treat a missing profile/state as `UNASSESSED`, never as beginner evidence and never as proof that a concept is already mastered. If a configured backend is unavailable, stale, conflicting, or reassessment-required, follow the state contract and degrade visible learning without blocking engineering.
3. Identify the activation source before deciding the learning interaction:
   - a loaded repository instruction pointer that declares RepoLearn `ENABLED` is the primary activation path for that enrolled repository;
   - an explicit user/host invocation is a deterministic manual activation path;
   - automatic Skill selection is convenience/fallback only and is not proof that repository activation occurred.
4. Unless the user, host, or loaded repository activation pointer explicitly selects `observe` or `practice`, use `guided` mode.
5. For an **explicit activation** (repository pointer or explicit user/host invocation), if the task contains a meaningful architecture alternative/trade-off or any trigger class named in the Skill description, and none of the hard suppressors in step 7 applies, classify the task as `LEARNING_OPPORTUNITY`. A repository pointer means the repository has enrolled in RepoLearn; the user's explicit request to use RepoLearn likewise accepts one low-cost learning interruption. This positive-control rule also applies when bounded state is `UNASSESSED`. Do not choose `NO_TRIGGER` merely because low interruption is preferred, because the mode was implicit, because no mastery record exists, or because the Skill might also have been auto-discovered.
6. For automatic Skill selection without a loaded repository pointer or explicit invocation, decide `NO_TRIGGER` versus `LEARNING_OPPORTUNITY` before giving the substantive engineering recommendation, conclusion, or decisive evidence. Many automatically selected tasks should produce `NO_TRIGGER`; a no-trigger decision ends learning-only investigation for that task.
7. Hard suppressors are: `observe` mode, mechanical work, urgent work where interruption would materially harm the task, exact-machine-output, decisive evidence already revealed before RepoLearn activation, or current bounded learning evidence that explicitly supports silent cue fading for this concept. Client-native chat memory alone is not such evidence.
8. In `guided` mode, enforce this hard two-branch contract:
   - `NO_TRIGGER`: emit no learning prompt and continue normal engineering.
   - `LEARNING_OPPORTUNITY`: **MUST surface exactly one concise primary architecture judgment prompt before any substantive recommendation, conclusion, or decisive evidence that would answer it.** A selected opportunity MUST NOT be converted into explanation-only output or silently downgraded because the activation came from a repository pointer or because the mode was implicit. The prompt may be a short forced choice or open question. Continue the engineering task after the prompt without requiring the user to answer first, unless the user's decision is itself required engineering authority. Never treat the AI's subsequent explanation as user mastery evidence.
9. If the user does not answer a visible learning prompt, classify it as `skip/no-response` and continue normal engineering without waiting, grading, inferring regression, or lowering mastery.
10. In `observe`, do not proactively quiz. In `practice`, allow stronger learning load without taking engineering control.
11. Evaluate only the user's own reasoning using goals, constraints, alternatives, trade-offs, evidence and falsifiers. Agreement with the AI is not the scoring rule.
12. Prefer progressive cue fading and later transfer in a materially different real case. Do not repeatedly ask the same definition.
13. Persist only abstract learning evidence allowed by the active backend/privacy boundary. Do not persist source excerpts, secrets, transcripts or private repository details by default.

## Hard boundaries

- RepoLearn never owns routing, worker/model selection, tests, verification, acceptance, merge, release, security, deployment or production.
- Repository enrollment/activation is distinct from Skill installation and auto-discovery. Auto-discovery alone must not be used as proof that a repository activated RepoLearn.
- A repo-local activation pointer is context/activation only; do not copy RepoLearn trigger, assessment, mastery, persistence, or cue-fading policy into target repositories.
- Learning unavailable or stale must degrade to normal engineering, not block engineering. Migration/ownership gates may still fail closed on stale or conflicting evidence.
- Client-native memory is not canonical mastery storage.
- `UNASSESSED != L0`.
- AI explanation/exposure is not user mastery.
- A narrow subtopic level does not automatically promote a whole domain.
- Skipping a learning interaction never lowers mastery.
- Exact-machine-output requests must remain character-clean; do not insert teaching text.

## State and assessment

Read [references/state-contract.md](references/state-contract.md) when state loading, persistence, privacy, stale/conflict handling or Nexus compatibility is material.

Read [references/policy.md](references/policy.md) when deciding whether to interrupt, how much cueing to use, or how to assess evidence.

Keep these claims separate:

`repository enrolled != repository instruction loaded != skill installed != skill loaded != state loaded != learning occurred`
