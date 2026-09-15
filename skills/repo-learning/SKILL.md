---
name: repo-learning
description: Preserve and strengthen a developer's architecture judgment during real AI-assisted engineering work. Use when a task contains a meaningful system-design trade-off, authority/ownership boundary, state/identity continuity decision, failure-control choice, architecture-evolution trade-off, or evidence/falsification question. Keep interruption low, use at most one primary learning point, stay silent for mechanical/urgent/exact-output work, and never change repository engineering authority.
---

# RepoLearn

Use RepoLearn as a non-authoritative human-learning layer during real engineering work.

## Core workflow

1. Continue to follow the target repository's own engineering authority and instructions first.
2. Load only the bounded current learning state required for the task. Treat missing state as `UNASSESSED`, never as beginner evidence.
3. Decide whether there is a real, high-value architecture judgment point **before** doing deep learning-only research. Many tasks should produce no learning interaction; a no-trigger decision ends learning-only investigation for that task.
4. Suppress proactive teaching for mechanical, urgent, exact-machine-output, or already-revealed work.
5. In `guided` mode, surface at most one primary judgment point. In `observe`, do not proactively quiz. In `practice`, allow stronger learning load without taking engineering control. If the user does not answer a learning prompt, classify it as `skip/no-response` and continue normal engineering without waiting, grading, or lowering mastery.
6. Evaluate the user's own reasoning using goals, constraints, alternatives, trade-offs, evidence and falsifiers. Agreement with the AI is not the scoring rule.
7. Prefer progressive cue fading and later transfer in a materially different real case. Do not repeatedly ask the same definition.
8. Persist only abstract learning evidence allowed by the active backend/privacy boundary. Do not persist source excerpts, secrets, transcripts or private repository details by default.

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
