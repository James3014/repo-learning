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
8. In `guided` mode, enforce this hard interaction contract before any substantive recommendation, conclusion, or decisive evidence that would answer the selected architecture judgment:
   - `NO_TRIGGER`: emit no learning interaction and continue normal engineering.
   - `LEARNING_OPPORTUNITY`: choose exactly one of the following two branches based on the user's own pre-feedback reasoning:
     - `JUDGMENT_PROMPT`: use when the user has not yet expressed a meaningful judgment on the selected architecture point. Surface exactly one concise primary architecture judgment prompt. The prompt MUST be understandable from roles, decisions, and trade-offs in plain language before any optional repository-specific identifiers are introduced. Use role-first, identifier-second framing: exact component, API, schema, state, or contract names may be appended for traceability only after the plain-language meaning is clear. Apply an identifier-removal check before emitting the prompt: if removing repository-specific names makes the architecture choice unclear, rewrite the prompt. Do not turn source recall into an architecture test by asking the user to name an internal contract/component unless source recall is explicitly the learning target. The prompt counts as emitted only when that architecture question appears in the durable final user-visible assistant response. Hidden reasoning, chain-of-thought/thinking UI, tool calls, internal scratchpads, and transient progress/status messages do not satisfy this requirement. Do not spend the learning interaction only in an intermediate surface: even if the question was formulated internally or mentioned during progress, include the single primary judgment question in the final response. "Exactly one" means one unique learning decision/question for the task; repeating the same question in the final response after an intermediate mention is canonical delivery, not a second learning point. Within that final response, place the judgment question before the first substantive recommendation, conclusion, or decisive evidence that would reveal the answer to the selected architecture point. User-visible progress/status output must also avoid revealing that answer before the canonical final-response question. Perform a pre-evidence ordering check before sending: if answer-revealing content appears before the question in any user-visible surface, move or withhold that content until after the question. Continue the engineering task immediately after the prompt without requiring the user to answer first, unless the user's decision is itself required engineering authority.
     - `SPONTANEOUS_JUDGMENT_CAPTURE`: use only when the user's own prior message contains an explicit pre-feedback position, choice, prediction, or architecture-risk judgment relevant to the selected point and decisive evidence has not already supplied the answer. Problem framing, terminology mentions, listing alternatives, asking a question, or expressing uncertainty without a directional judgment are not sufficient. When uncertain whether a real judgment exists, use `JUDGMENT_PROMPT`. Do not re-ask a qualifying judgment. Briefly identify what the user noticed or chose, give bounded feedback on the reasoning rather than mere agreement, extract one reusable principle in plain language, optionally name the engineering term after the plain-language explanation, state one important applicability boundary or counterexample, then continue the engineering task.
   A selected `LEARNING_OPPORTUNITY` MUST NOT be converted into explanation-only output or silently downgraded because the activation came from a repository pointer or because the mode was implicit. Engineering vocabulary is not a prerequisite for either branch.
9. After a visible `JUDGMENT_PROMPT`, classify a later turn as `ANSWERED` only when it actually contains prompt-relevant user reasoning. A blank/no response, explicit skip, unrelated engineering instruction, or semantically unclassified turn is not assessable learning evidence; continue normal engineering without waiting, grading, inferring regression, or lowering mastery. Do not emit a second unique prompt for the same selected point.
10. In `observe`, do not proactively quiz. In `practice`, allow stronger learning load without taking engineering control.
11. Evaluate only the user's own reasoning using goals, constraints, alternatives, trade-offs, evidence and falsifiers. Agreement with the AI is not the scoring rule. Only user-authored reasoning expressed before RepoLearn feedback or decisive evidence may promote mastery. Post-evidence agreement is exposure, and goals/alternatives/trade-offs/evidence/falsifiers added by AI reformulation or explanation must not be credited to the user.
12. Prefer progressive cue fading and later transfer in a materially different real case. Do not repeatedly ask the same definition or re-quiz a judgment the user already expressed. Suppress a proactive prompt for a concept only when the current bounded state explicitly marks that concept eligible for silent cue fading; chat memory alone is insufficient. Plain-language recognition of a system risk may be stronger evidence than terminology recall.
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
- Engineering terminology is not a prerequisite for architecture evidence; terminology friction must not lower mastery.
- A valid architecture trigger with an incomprehensible identifier-first prompt is an interaction defect, not negative user evidence, not `skip/no-response`, and not mastery regression.
- A guided prompt that exists only in hidden reasoning or intermediate/transient output is a prompt-visibility defect, not `skip/no-response`, not negative user evidence, and not mastery regression.
- A guided prompt that appears only after answer-revealing recommendation, conclusion, or decisive evidence in the final response or earlier user-visible progress is a pre-evidence-ordering defect, not `skip/no-response`, not negative user evidence, and not mastery regression.
- Treating problem framing, questions, uncertainty, or option enumeration as spontaneous judgment is a guided-branch-selection defect; when branch evidence is ambiguous, prompt rather than invent user mastery.
- Treating an unrelated engineering continuation as an answered learning prompt is a response-relevance defect; unknown relevance is non-assessable.
- Exact-machine-output requests must remain character-clean; do not insert teaching text.

## State and assessment

Read [references/state-contract.md](references/state-contract.md) when state loading, persistence, privacy, stale/conflict handling or Nexus compatibility is material.

Read [references/policy.md](references/policy.md) when deciding whether to interrupt, how much cueing to use, or how to assess evidence.

Keep these claims separate:

`repository enrolled != repository instruction loaded != skill installed != skill loaded != state loaded != learning occurred`
