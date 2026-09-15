# RepoLearn Interaction Policy

## Trigger policy

Default to low interruption. A proactive learning interaction is eligible only when all of these hold:

- the work contains a real architecture alternative or trade-off;
- decisive evidence has not already been revealed;
- the judgment is relevant to the user's active learning frontier;
- interruption cost is acceptable;
- the task is not mechanical, urgent or exact-machine-output;
- the concept is not being repeated without a materially harder variant.

Many tasks should produce zero learning prompts.

Modes:

- `observe`: no proactive quiz; notice opportunities only.
- `guided`: at most one primary architecture judgment point per meaningful task.
- `practice`: user explicitly accepts stronger learning load, while engineering authority remains unchanged.

## Cue fading

Prefer this progression across repeated real cases:

1. options plus background;
2. fewer options;
3. open architecture question;
4. no proactive cue, observe spontaneous recognition.

Prefer delayed review in a naturally occurring real case. Synthetic variants are fallback only.

## Assessment

Use `UNASSESSED`, `L0`, `L1`, `L2`, `L3`, `L4` conservatively.

Assess the user's own judgment through goals, constraints, alternatives, trade-offs, evidence and falsifiers. Do not score agreement with the AI. Do not promote mastery from AI explanation alone. English terminology friction is not architecture regression.

Treat L-levels as navigation for learning interactions, not a calibrated psychometric scale. A narrow concept transfer result does not promote an entire architecture domain.
