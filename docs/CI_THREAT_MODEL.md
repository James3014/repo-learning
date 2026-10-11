# CI threat model

Scope: `.github/workflows/nexus-core-issue-completion.yml` (Nexus Core issue completion) and `.github/workflows/ci.yml` (CI).

## CI (`ci.yml`)

Runs on `push` and `pull_request`. For a fork PR, GitHub gives it a read-only token and no secrets. It runs untrusted code, but in an untrusted context. No extra controls.

## Nexus Core issue completion

### Why `pull_request_target`

The job must run the base branch's copy of the workflow, so a PR cannot weaken its own gate. Only `pull_request_target` does this. The cost is that the job runs in the target repository's context.

### What the job can read

- `GITHUB_TOKEN` with `contents: read`, `issues: read`, `pull-requests: read`. It is set as a job environment variable, so any code the job runs can read it.
- Any repository or organization secret the workflow names. Today it names none.
- The runner's environment, the Actions cache scope of the base branch, and the network.

### What the job runs

It checks out the PR head and runs `nexus-certify issue-check`, which runs the verifiers in `.nexus-core/config.toml` (`pytest` and `git diff --check`) on the PR head. So PR head code runs with the access above.

### Who can trigger it

`pull_request_target` fires for PRs from forks as well as from branches in this repository. A fork author has no write access, so running their code with the target's token would give them more than they have.

### Decision

The job is same-repository only.

- The first step, `same-repo-guard`, compares `github.event.pull_request.head.repo.full_name` with `github.repository` and fails with `NEXUS_CORE_FORK_PR_UNSUPPORTED` when they differ. It runs before checkout, so no fork code runs.
- The guard fails the job instead of skipping it. A skipped job can count as passing for a required check, which would let a fork PR bypass the gate.
- Anyone who can push a branch here already has write access, so running their branch with a read-only token adds nothing.
- A fork contribution needs a maintainer to push it to a branch in this repository first. That push is the review step.

`tests/test_workflow_security.py` fails if any workflow triggered by `pull_request_target` checks out `github.event.pull_request.head` without this guard as its first step.

### Changing this

Any change to the guard, the trigger, the permissions, or the secrets the job reads must update this file. The workflow file is a protected governance input, so a PR that changes it fails the Core gate on itself with `NEXUS_CORE_GOVERNANCE_INPUT_CHANGED` and needs an owner decision to merge.
