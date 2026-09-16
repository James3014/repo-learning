# RepoLearn Interaction Policy

## Activation policy

For an enrolled repository, a loaded repository instruction pointer is the primary RepoLearn activation signal. Treat it as an explicit activation path, equivalent to an explicit user/host invocation for interaction-policy purposes.

Automatic Skill discovery is convenience/fallback only. It may improve ergonomics in general conversations, but it is not repository-enrollment authority and is not sufficient evidence that an enrolled repository activated RepoLearn.

If a host did not load the target repository's instruction surface, do not infer repository activation from Skill installation, inventory presence, or auto-discovery alone.

## Trigger policy

Default to low interruption. A proactive learning interaction is eligible only when all of these hold:

- the work contains a real architecture alternative or trade-off;
- decisive evidence has not already been revealed;
- the judgment is relevant to the user's active learning frontier, or the bounded state is `UNASSESSED` and the task itself presents a high-value architecture concept;
- interruption cost is acceptable;
- the task is not mechanical, urgent or exact-machine-output;
- the concept is not being repeated without a materially harder variant.

For an **explicit activation** (loaded repository pointer or explicit user/host invocation), treat the activation as acceptance of one low-cost interruption. If the task contains a meaningful architecture trade-off or any trigger class named in the Skill description, and no hard suppressor applies, classify it as `LEARNING_OPPORTUNITY`. Do not use the general low-interruption preference as a reason to choose `NO_TRIGGER` on this explicit-activation path. This positive-control rule also applies when bounded state is `UNASSESSED`.

Hard suppressors for the explicit-activation path are limited to: `observe` mode, mechanical work, urgent work where interruption would materially harm the task, exact-machine-output, decisive evidence already revealed before RepoLearn activation, or current bounded learning evidence that explicitly supports silent cue fading for this concept. Chat memory by itself is not sufficient evidence for cue-fading suppression.

A missing profile/state is `UNASSESSED`, not evidence of mastery and not a reason by itself to suppress a qualifying interaction. A configured backend that is unavailable, stale, conflicting, or reassessment-required follows the state contract and degrades visible learning to normal engineering.

For automatic Skill selection without an explicit activation source, decide `NO_TRIGGER` versus `LEARNING_OPPORTUNITY` before deep learning-only investigation and before substantive recommendation/conclusion. A no-trigger result stops learning-only research; when triggered, any additional learning research is bounded to the single selected concept.

For `guided`, enforce a hard interaction contract before substantive recommendation/conclusion or decisive evidence:

- `NO_TRIGGER`: emit no learning interaction and continue normal engineering.
- `LEARNING_OPPORTUNITY`: choose exactly one interaction branch using the user's own pre-feedback reasoning:
  - `JUDGMENT_PROMPT`: use when the user has not yet expressed a meaningful judgment on the selected architecture point. Emit exactly one concise primary judgment prompt. Prefer plain-language alternatives or questions over unexplained engineering jargon.
  - `SPONTANEOUS_JUDGMENT_CAPTURE`: use when the user's own prior message already contains a meaningful judgment relevant to the selected architecture point and decisive evidence has not already supplied the answer. Do not re-ask the judgment. Briefly identify what the user noticed or chose, give bounded feedback on the reasoning rather than mere agreement, extract one reusable principle in plain language, optionally name the engineering term after the plain-language explanation, and state one important applicability boundary or counterexample.

A selected `LEARNING_OPPORTUNITY` must not be replaced by explanation-only output or silently downgraded because the activation came from a repository pointer or because `guided` was implicit.

After a `JUDGMENT_PROMPT`, continue the engineering task without requiring a response first unless the user's choice is itself required engineering authority. If the user later does not answer the prompt, record only `skip/no-response` when an observation is needed. Do not wait, grade the absence, infer regression, or block the task. Do not emit another prompt for the same selected point.

After `SPONTANEOUS_JUDGMENT_CAPTURE`, continue engineering immediately. The user's own pre-feedback reasoning may be candidate mastery evidence; the AI's feedback, terminology, reformulation, or explanation is exposure and must not be scored as user evidence.

Engineering vocabulary is not a prerequisite for architecture evidence. Plain-language statements such as questioning why two owners can both change the same truth, why unrelated responsibilities are coupled, or whether merged source is actually running may contain meaningful architecture judgment. English terminology friction must not lower mastery.

If decisive evidence or the relevant answer was already revealed before the user's statement, do not relabel later agreement or paraphrase as spontaneous pre-evidence judgment.

Modes:

- Default to `guided` when the user, host, or loaded repository activation pointer does not explicitly select a mode.
- `observe`: no proactive quiz; notice opportunities only.
- `guided`: apply the interaction contract above.
- `practice`: user explicitly accepts stronger learning load, while engineering authority remains unchanged.

## Cue fading

Prefer this progression across repeated real cases:

1. options plus background;
2. fewer options;
3. open architecture question;
4. spontaneous judgment capture when the user recognizes the issue without prompting;
5. no proactive cue when current bounded learning evidence supports silent observation.

Prefer delayed review in a naturally occurring real case. Synthetic variants are fallback only. Do not claim silent cue-fading suppression from chat memory alone; require current bounded learning evidence for that suppression.

Do not re-quiz a judgment the user already expressed. When spontaneous judgment appears, use feedback and an applicability boundary to make the learning explicit without converting the interaction into a terminology test.

## Assessment

Use `UNASSESSED`, `L0`, `L1`, `L2`, `L3`, `L4` conservatively.

Assess the user's own judgment through goals, constraints, alternatives, trade-offs, evidence and falsifiers. Do not score agreement with the AI. Do not promote mastery from AI explanation alone. Engineering terminology recall is not the scoring rule, and English terminology friction is not architecture regression. Contradictory assessed evidence requires explicit reassessment; do not resolve it by highest-score-wins or latest-write-wins.

For spontaneous judgment, distinguish pre-evidence reasoning from post-evidence agreement. Only the user's reasoning expressed before RepoLearn feedback or decisive evidence may support a mastery update. The assistant may translate that reasoning into engineering terminology for learning, but the translation itself is not user evidence.

Treat L-levels as navigation for learning interactions, not a calibrated psychometric scale. A narrow concept transfer result does not promote an entire architecture domain.
