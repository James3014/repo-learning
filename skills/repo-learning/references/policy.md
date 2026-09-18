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
  - `JUDGMENT_PROMPT`: use when the user has not yet expressed a meaningful judgment on the selected architecture point. Emit exactly one concise primary judgment prompt. Plain-language-first is mandatory: use the user's current language unless the user asks otherwise, preserve exact repository identifiers unchanged, and state the roles, decision, and trade-off so the question is understandable before optional repository-specific identifiers appear. Use role-first, identifier-second framing; exact component/API/schema/state/contract names may be added afterward only for traceability. Before emitting, perform an identifier-removal check: removing repository-specific names must still leave the architecture choice understandable. Do not ask the user to name an internal contract/component unless source recall itself is the explicit learning target. The judgment prompt counts as emitted only if the architecture question appears in the durable final user-visible assistant response. Hidden reasoning, chain-of-thought/thinking UI, tool calls, internal scratchpads, and transient progress/status messages do not satisfy this requirement. If the question was formulated internally or appeared only in an intermediate surface, include the single primary judgment question in the final response rather than treating the interaction as already delivered. One unique judgment question may therefore be rendered again in the canonical final response without becoming a second learning point. Within the final response, the judgment question must appear before the first substantive recommendation, conclusion, or decisive evidence that would reveal the answer to the selected architecture point. User-visible progress/status output must not reveal that answer first either. Before sending, perform a pre-evidence ordering check across all user-visible surfaces and move or withhold answer-revealing content until after the question.
  - `SPONTANEOUS_JUDGMENT_CAPTURE`: use only when the user's own prior message contains an explicit pre-feedback position, choice, prediction, or architecture-risk judgment relevant to the selected point and decisive evidence has not already supplied the answer. Problem framing, naming terms, listing options, asking a question, or expressing uncertainty without a directional judgment is not enough. When branch evidence is ambiguous, choose `JUDGMENT_PROMPT`. Do not re-ask a qualifying judgment. Briefly identify what the user noticed or chose, give bounded feedback on the reasoning rather than mere agreement, extract one reusable principle in plain language, optionally name the engineering term after the plain-language explanation, and state one important applicability boundary or counterexample.

A selected `LEARNING_OPPORTUNITY` must not be replaced by explanation-only output or silently downgraded because the activation came from a repository pointer or because `guided` was implicit.

After a `JUDGMENT_PROMPT`, continue the engineering task without requiring a response first unless the user's choice is itself required engineering authority. Classify a later turn as an answer only when it contains prompt-relevant user reasoning. Blank/no response, explicit skip, unrelated engineering continuation, and semantically unclassified replies are non-assessable and must not be promoted to mastery evidence. Do not wait, grade the absence, infer regression, or block the task. Do not emit another unique prompt for the same selected point.

After `SPONTANEOUS_JUDGMENT_CAPTURE`, continue engineering immediately. The user's own pre-feedback reasoning may be candidate mastery evidence; the AI's feedback, terminology, reformulation, or explanation is exposure and must not be scored as user evidence. Structured evidence fields used for assessment must contain only user-authored content; AI-added goals, alternatives, trade-offs, evidence, or falsifiers cannot raise the evidence ceiling.

Engineering vocabulary is not a prerequisite for architecture evidence. Plain-language statements such as questioning why two owners can both change the same truth, why unrelated responsibilities are coupled, or whether merged source is actually running may contain meaningful architecture judgment. English terminology friction must not lower mastery.

Prompt comprehensibility is part of the interaction contract. A selected architecture concept can be valid while the emitted prompt is defective. If the user cannot understand the architecture choice without first decoding repository-specific identifiers, classify that interaction as a prompt-comprehension defect rather than user failure, skip/no-response, or mastery regression.

Prompt visibility is also part of the interaction contract. A prompt generated only in hidden reasoning or intermediate/transient output has not been delivered to the user. Classify that interaction as a prompt-visibility defect rather than user failure, skip/no-response, or mastery regression. The final response must preserve the one primary architecture question while still completing the engineering work without waiting for an answer.

Pre-evidence ordering is part of the interaction contract as well. If the final response or earlier user-visible progress gives the recommendation, conclusion, or decisive evidence that reveals the answer before the judgment question, classify the interaction as a pre-evidence-ordering defect rather than user failure, skip/no-response, or mastery regression. Engineering may continue immediately after the question; ordering must not become a blocking approval gate. Any user answer given only after decisive evidence has already revealed the answer remains post-evidence agreement and cannot be promoted to pre-evidence mastery evidence.

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

Prefer delayed review in a naturally occurring real case. Synthetic variants are fallback only. Evidence events record facts rather than granting themselves suppression authority. Silent cue fading requires a derived, still-current window backed by user-authored, pre-evidence, independent, cue-free (`NONE`), near/far transfer evidence delayed by at least 24 hours and assessed at transfer-with-tradeoffs or stronger. Legacy event flags named `silent_cue_fading_eligible` are compatibility data only and must not drive policy. Use a simple bounded validity window rather than a psychometric forgetting claim; after expiry, allow natural revalidation. Do not claim silent cue-fading suppression from chat memory alone.

Do not re-quiz a judgment the user already expressed. When spontaneous judgment appears, use feedback and an applicability boundary to make the learning explicit without converting the interaction into a terminology test.

## Assessment

Use `UNASSESSED`, `L0`, `L1`, `L2`, `L3`, `L4` conservatively.

Assess the user's own judgment through goals, constraints, alternatives, trade-offs, evidence and falsifiers. Do not score agreement with the AI. Do not promote mastery from AI explanation alone. Engineering terminology recall is not the scoring rule, and English terminology friction is not architecture regression. Contradictory assessed evidence requires explicit reassessment; do not resolve it by highest-score-wins or latest-write-wins.

For spontaneous judgment, distinguish pre-evidence reasoning from post-evidence agreement. Only user-authored reasoning expressed before RepoLearn feedback or decisive evidence may support a mastery update. Post-evidence agreement and AI-reformulated evidence are exposure only. The assistant may translate user reasoning into engineering terminology for learning, but the translation and any additional rationale it invents are not user evidence.

Treat L-levels as navigation for learning interactions, not a calibrated psychometric scale. A narrow concept transfer result does not promote an entire architecture domain.

## Dogfood evidence integrity

A dogfood receipt must attest the loaded RepoLearn contract revision/fingerprint and bind semantic evaluation to a privacy-safe hash of the exact user-visible interaction trace. Self-reported labels are useful for debugging but do not by themselves count as independent interaction-quality evidence. Record evaluator provenance (`DETERMINISTIC`, `INDEPENDENT_LLM`, or `HUMAN`) when making an independent G5 claim. Preserve all applicable interaction defects rather than only a single precedence winner. Also retain bounded interruption-cost estimates (added turns, time and context tokens) because low interruption is part of the product contract, not merely a convenience.
