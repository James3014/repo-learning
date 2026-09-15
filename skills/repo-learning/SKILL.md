---
name: repo-learning
description: Preserve and strengthen a developer's architecture judgment during real AI-assisted engineering work. Use when a task contains a meaningful system-design trade-off, authority/ownership boundary, state/identity continuity decision, failure-control choice, architecture-evolution trade-off, or evidence/falsification question. Default to guided. If the user explicitly invokes RepoLearn on a qualifying architecture task and no hard suppressor applies, treat it as a learning opportunity and ask exactly one concise architecture judgment question before decisive guidance. Stay silent for mechanical, urgent, exact-output, or state-backed cue-faded work; never change repository engineering authority.
---

# RepoLearn

Use RepoLearn as a non-authoritative human-learning layer during real engineering work.

## Core workflow

1. Continue to follow the target repository's own engineering authority and instructions first.
2. Load only the bounded current learning state required for the task. Treat a missing profile/state as `UNASSESSED`, never as beginner evidence and never as proof that a concept is already mastered. If a configured backend is unavailable, stale, conflicting, or reassessment-required, follow the state contract and degrade visible learning without blocking engineering.
3. Unless the user or host explicitly selects `observe` or `practice`, use `guided` mode. This default applies both to explicit RepoLearn invocation and automatic Skill selection.
4. For an **explicit RepoLearn invocation**, treat the user's request to use RepoLearn as acceptance of one low-cost learning interruption. If the task contains a meaningful architecture alternative/trade-off or any trigger class named in the Skill description, and none of the hard suppressors in step 6 applies, classify the task as `LEARNING_OPPORTUNITY`. This positive-control rule also applies when bounded state is `UNASSESSED`. Do not choose `NO_TRIGGER` merely because low interruption is preferred, because the mode was implicit, or because no mastery record exists.
5. For automatic Skill selection, decide `NO_TRIGGER` versus `LEARNING_OPPORTUNITY` before giving the substantive engineering recommendation, conclusion, or decisive evidence. Many automatically selected tasks should produce `NO_TRIGGER`; a no-trigger decision ends learning-only investigation for that task.
6. Hard suppressors are: `observe` mode, mechanical work, urgent work where interruption would materially harm the task, exact-machine-output, decisive evidence already revealed before RepoLearn selection, or current bounded learning evidence that explicitly supports silent cue fading for this concept. Client-native chat memory alone is not such evidence.
7. In `guided` mode, enforce this hard two-branch contract:
   - `NO_TRIGGER`: emit no learning prompt and continue normal engineering.
   - `LEARNING_OPPORTUNITY`: **MUST surface exactly one concise primary architecture judgment prompt before any substantive recommendation, conclusion, or decisive evidence that would answer it.** A selected opportunity MUST NOT be converted into explanation-only output or silently downgraded because the mode was implicit. The prompt may be a short forced choice or open question. Continue the engineering task after the prompt without requiring the user to answer first, unless the user's decision is itself required engineering authority. Never treat the AI's subsequent explanation as user mastery evidence.
8. If the user does not answer a visible learning prompt, classify it as `skip/no-response` and continue normal engineering without waiting, grading, inferring regression, or lowering mastery.
9. In `observe`, do not proactively quiz. In `practice`, allow stronger learning load without taking engineering control.
10. Evaluate only the user's own reasoning using goals, constraints, alternatives, trade-offs, evidence and falsifiers. Agreement with the AI is not the scoring rule.
11. Prefer progressive cue fading and later transfer in a materially different real case. Do not repeatedly ask the same definition.
12. Persist only abstract learning evidence allowed by the active backend/privacy boundary. Do not persist source excerpts, secrets, transcripts or private repository details by default.

## Hard boundaries

- RepoLearn never owns routing, worker/model selection, tests, verification, acceptance, merge, release, security, deployment or production.
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

`skill source exists != installed != discovered/activated != state loaded != learning occurred`
