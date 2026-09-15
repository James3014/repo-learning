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

A missing profile/state is `UNASSESSED`, not evidence of mastery and not a reason by itself to suppress a qualifying prompt. A configured backend that is unavailable, stale, conflicting, or reassessment-required follows the state contract and degrades visible learning to normal engineering.

For automatic Skill selection without an explicit activation source, decide `NO_TRIGGER` versus `LEARNING_OPPORTUNITY` before deep learning-only investigation and before substantive recommendation/conclusion. A no-trigger result stops learning-only research; when triggered, any additional learning research is bounded to the single selected concept.

For `guided`, enforce a hard two-branch contract:

- `NO_TRIGGER`: emit no learning prompt and continue normal engineering.
- `LEARNING_OPPORTUNITY`: MUST emit exactly one concise primary judgment prompt before any substantive recommendation, conclusion, or decisive evidence that would answer it. Do not replace the prompt with an explanation, do not answer the judgment before surfacing it, and do not silently downgrade the selected opportunity because the activation came from a repository pointer or because `guided` was implicit.

After surfacing the prompt, continue the engineering task without requiring a response first unless the user's choice is itself required engineering authority. If the user later does not answer the prompt, record only `skip/no-response` when an observation is needed. Do not wait, grade the absence, infer regression, or block the task. The AI's own later explanation is exposure, not user mastery evidence.

Modes:

- Default to `guided` when the user, host, or loaded repository activation pointer does not explicitly select a mode.
- `observe`: no proactive quiz; notice opportunities only.
- `guided`: apply the hard two-branch contract above.
- `practice`: user explicitly accepts stronger learning load, while engineering authority remains unchanged.

## Cue fading

Prefer this progression across repeated real cases:

1. options plus background;
2. fewer options;
3. open architecture question;
4. no proactive cue, observe spontaneous recognition.

Prefer delayed review in a naturally occurring real case. Synthetic variants are fallback only. Do not claim silent cue-fading suppression from chat memory alone; require current bounded learning evidence for that suppression.

## Assessment

Use `UNASSESSED`, `L0`, `L1`, `L2`, `L3`, `L4` conservatively.

Assess the user's own judgment through goals, constraints, alternatives, trade-offs, evidence and falsifiers. Do not score agreement with the AI. Do not promote mastery from AI explanation alone. English terminology friction is not architecture regression. Contradictory assessed evidence requires explicit reassessment; do not resolve it by highest-score-wins or latest-write-wins.

Treat L-levels as navigation for learning interactions, not a calibrated psychometric scale. A narrow concept transfer result does not promote an entire architecture domain.
