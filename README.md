# RepoLearn

RepoLearn is a portable human-learning layer for preserving and developing engineering judgment while working with AI-assisted development tools.

> **Product boundary:** RepoLearn can observe learning opportunities, guide practice, and maintain learning evidence. It never owns or changes a target repository's routing, workforce, tests, verification, acceptance, merge, release, security, deployment, or production authority.

## V1 direction

RepoLearn separates three concerns:

1. **Public core** — generic learning schemas, trigger rules, assessment contracts, adapters, and evaluation methods.
2. **Private user learning state** — mastery evidence, learning events, review queue, and preferences owned by the user through a state backend.
3. **Thin repository context** — repository identity, authority-source reference, learning mode, and privacy settings. Repository context never stores user mastery.

The first portable client direction is Agent Skills with client-specific installation projections. Skill installation, skill activation, state loading, and actual learning are separate facts.

## G1 generic contracts

This repository currently defines the minimum G1 contract surface:

- `repolearn.learning_state.v1`
- `repolearn.learning_event.v1`
- `repolearn.repository.v1`
- storage-neutral `StateBackend`
- low-interruption trigger policy with `observe`, `guided`, and `practice` modes
- conservative assessment primitives using `UNASSESSED`, `L0` through `L4`, cue level, transfer distance, delay metadata, and judgment evidence

Key invariants:

- `UNASSESSED != L0`.
- Missing state is not beginner evidence.
- AI explanation or exposure is not user mastery.
- Architecture judgment is evaluated through goals, constraints, alternatives, trade-offs, evidence, and falsifiers — not agreement with the AI.
- Teaching is conditional; zero learning triggers is a valid result.
- At most one primary learning point is selected for a meaningful task.
- Mechanical, urgent, exact-machine-output, or already-revealed work can remain silent.
- Client-native memory is not canonical mastery storage.
- Learning state never changes engineering authority.

## Portable runtime: G2 + G3 + G4

The portable-runtime layer adds:

- one canonical Agent Skills source at `skills/repo-learning/`;
- client-specific Codex and Claude Code installation projections without policy forks;
- a client-neutral state/trigger preparation contract that degrades to normal engineering when learning state is unavailable;
- `LocalFileBackend` for private local JSONL events plus deterministic JSON projection, with stable event idempotency, conflict detection, stale-projection detection and owner-only file permissions;
- `NexusLedgerBackend` as a hash/revision-bound **read-through** adapter for James's existing Nexus Owner-learning Ledger.

James's canonical personal-learning owner does not move in G4. The Nexus Ledger remains the writable SSOT until a later explicit migration transaction; RepoLearn does not create a second writable James mastery store.

The following remain later gates: real multi-day Nexus-new/devspace dogfood, 8-repository rollout, canonical-state migration, Friend Alpha and learning-effectiveness evaluation.

## Development

Requires Python 3.11+.

```bash
python -m pip install -e '.[test]'
python -m pytest
git diff --check
```

## License

Apache-2.0.
