# RepoLearn Agent Guidelines

RepoLearn is a human-learning layer. This repository owns RepoLearn's generic learning contracts, policy logic, schemas, adapters, tests, and release artifacts.

## Authority

- Canonical RepoLearn source authority lives in this repository.
- RepoLearn never owns or changes a target repository's routing, workforce, tests, verification, acceptance, merge, release, security, deployment, or production authority.
- User learning state and mastery evidence are personal data. Public core code must not embed or publish a user's private learning history.
- Repository adapters provide repository context only; they never define user mastery or engineering authority.
- Client-native memory is not canonical mastery storage.

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
