---
name: repo-learning
description: Preserve and strengthen a developer's architecture judgment during real AI-assisted engineering work. Use when a task contains a meaningful system-design trade-off, authority/ownership boundary, state/identity continuity decision, failure-control choice, architecture-evolution trade-off, or evidence/falsification question. Keep interruption low, use at most one primary learning point, stay silent for mechanical/urgent/exact-output work, and never change repository engineering authority.
---

# RepoLearn

Use RepoLearn as a non-authoritative human-learning layer during real engineering work.

## Core workflow

1. Continue to follow the target repository's own engineering authority and instructions first.
2. Load only the bounded current learning state required for the task. Treat a missing profile/state as `UNASSESSED`, never as beginner evidence and never as proof that a concept is already mastered. If a configured backend is unavailable, stale, conflicting, or reassessment-required, follow the state contract and degrade visible learning without blocking engineering.
3. Unless the user or host explicitly selects `observe` or `practice`, use `guided` mode. This default applies both to explicit RepoLearn invocation and automatic Skill selection.
4. Decide `NO_TRIGGER` versus `LEARNING_OPPORTUNITY` before giving the substantive engineering recommendation, conclusion, or decisive evidence. Many tasks should produce `NO_TRIGGER`; a no-trigger decision ends learning-only investigation for that task.
5. Suppress proactive teaching for mechanical, urgent, exact-machine-output, already-revealed work, or a concept that current bounded learning evidence shows should be silent under cue fading.
6. In `guided` mode, enforce this hard two-branch contract:
   - `NO_TRIGGER`: emit no learning prompt and continue normal engineering.
   - `LEARNING_OPPORTUNITY`: **MUST surface exactly one concise primary architecture judgment prompt before any substantive recommendation, conclusion, or decisive evidence that would answer it.** A selected opportunity MUST NOT be converted into explanation-only output or silently downgraded because the mode was implicit. The prompt may be a short forced choice or open question. Continue the engineering task after the prompt without requiring the user to answer first, unless the user's decision is itself required engineering authority. Never treat the AI's subsequent explanation as user mastery evidence.
7. If the user does not answer a visible learning prompt, classify it as `skip/no-response` and continue normal engineering without waiting, grading, inferring regression, or lowering mastery.
8. In `observe`, do not proactively quiz. In `practice`, allow stronger learning load without taking engineering control.
9. Evaluate only the user's own reasoning using goals, constraints, alternatives, trade-offs, evidence and falsifiers. Agreement with the AI is not the scoring rule.
10. Prefer progressive cue fading and later transfer in a materially different real case. Do not repeatedly ask the same definition.
11. Persist only abstract learning evidence allowed by the active backend/privacy boundary. Do not persist source excerpts, secrets, transcripts or private repository details by default.

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
