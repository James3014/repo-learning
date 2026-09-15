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

## G1 non-goals

G1 intentionally does **not** implement:

- a backend server, daemon, database service, cloud service, dashboard, vector database, or knowledge graph;
- a custom AI runtime, model gateway, or router;
- the G2 Agent Skill;
- `LocalFileBackend` or `NexusLedgerBackend` concrete storage;
- repository rollout, canonical-state migration, or external Alpha workflows.

## Development

Requires Python 3.11+.

```bash
python -m pip install -e '.[test]'
python -m pytest
git diff --check
```

## License

Apache-2.0.
