# RepoLearn Agent Guidelines

RepoLearn is a human-learning layer. This repository owns RepoLearn's generic learning contracts, policy logic, schemas, adapters, tests, and release artifacts.

## Authority

- Canonical RepoLearn source authority lives in this repository.
- A target repository owns only whether RepoLearn is enabled for work in that repository and the thin context needed to locate the canonical capability. It must not clone RepoLearn trigger, assessment, mastery, persistence, or cue-fading policy.
- Automatic Skill discovery is a convenience mechanism, not repository activation authority and not evidence that an enrolled repository actually activated RepoLearn.
- RepoLearn never owns or changes a target repository's routing, workforce, tests, verification, acceptance, merge, release, security, deployment, or production authority.
- User learning state and mastery evidence are personal data. Public core code must not embed or publish a user's private learning history.
- Repository adapters provide repository context and activation only; they never define user mastery or engineering authority.
- Client-native memory is not canonical mastery storage.

## Repository activation

- The canonical repository-activation contract is `docs/REPOSITORY_ACTIVATION_V1.md`.
- For an enrolled target repository, a loaded repo-local instruction pointer is the primary activation signal. Explicit user/host invocation is a valid manual control; automatic Skill discovery is fallback/convenience only.
- A repo-local activation pointer may name the canonical RepoLearn source, skill name, mode, and fail-open behavior. It must remain a pointer, not a policy fork.
- If a host does not load the target repository's instruction surface, repository activation is not proven. Do not infer it from Skill installation or auto-discovery alone.
- RepoLearn unavailability must fail open to normal engineering work; it never weakens the target repository's own authority or verification gates.

## Mutation boundaries

- Prefer the smallest change that preserves public contracts and privacy boundaries.
- Do not add servers, daemons, cloud services, database services, dashboards, vector databases, knowledge graphs, model gateways, or custom AI runtimes without explicit product authority and evidence of need.
- Do not copy Nexus-specific governance machinery into RepoLearn. Reuse generalizable structure, not another repository's authority semantics.

## Verification

- Source changes require focused tests for affected contracts and `git diff --check`.
- Schema changes require positive and negative validation tests.
- Implementation evidence is not approval, merge, release, deployment, or production evidence.

## Privacy

- Source excerpts, private repository data, transcripts, secrets, and personal learning evidence must not be persisted by default.
- Cross-repository learning may transfer abstract principles, not private source-specific evidence across workspace or organization boundaries.

## Nexus Core issue-bound completion evidence

- This repository is enrolled in the standalone `nexus-certify` Golden Path through `.nexus-core/config.toml`.
- For mutation work tracked by a repository-local GitHub Issue, run `nexus-certify issue-init --issue <N>` before relying on Issue-bound completion evidence, and run `nexus-certify issue-check --issue <N>` before claiming engineering completion.
- This binding is Evidence Trust + Completion only. It does not select learning triggers, assessment, mastery, persistence, cue fading, learning state, execution lane, route, worker/model, Candidate acceptance, merge, release, deployment, or production authority.
- RepoLearn remains fully functional without Nexus Core; Core adds optional verification assurance and is not a runtime dependency of RepoLearn.
- DIRECT work remains transport-neutral. A Core mutation session is not required solely because repository files are being changed.

## Handoff

`HANDOFF.md` at the repository root is the shared progress log for every agent (Claude, Codex, others) and every device. It records state only; it grants no authority and never overrides this file, Issues, or Task Cards.

- **Read first.** At session start read `HANDOFF.md`. If its recorded HEAD is behind, run `git log <recorded-HEAD>..HEAD` and correct stale entries before acting on them.
- **Update at milestones.** Update it when a meaningful step finishes or before the session ends — not every turn. Overwrite stale state; do not append history.
- **Format.** The header line holds date, author agent, and current short HEAD. `▶ 下一步` has exactly one item. Every todo carries an Issue number (`#N`); items without one go under `待確認`. Record why, blockers, and next — not changed-file lists (git already has those).
- **Size cap: 150 lines.** Move finished or expired content to `docs/archive/HANDOFF-YYYY-MM.md`.
- **Read back.** After writing, re-read `HANDOFF.md` to confirm the change actually landed.
- **No secrets.** Never put tokens, passwords, credentials, or internal hostnames in it.
