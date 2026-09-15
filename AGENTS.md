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
