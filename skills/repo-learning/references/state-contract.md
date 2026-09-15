# RepoLearn State Contract

RepoLearn has exactly one canonical personal-learning truth per user at a time.

## Generic local users

Use `LocalFileBackend` for private local state. It stores profile-scoped `events.jsonl` plus a deterministic `state.json` projection with owner-only file permissions. Event identity is idempotent: replaying the same event is a no-op, while reusing an event ID for different content fails closed. Projection reads fail if the stored source hash no longer matches the event ledger. Distinct assessed levels for the same domain are conflicting learning evidence and require explicit reassessment; projection must not resolve them by highest-score-wins or latest-write-wins.

Local data controls support deterministic profile export plus profile-scoped delete/reset. They reject path traversal, symlinked profile data, and destructive deletion when unrecognized files are present.

Do not persist source excerpts, full transcripts, secrets, private URLs or company-private architecture material by default. Cross-repository transfer should preserve abstract principles and capability evidence, not source-private payloads.

## James before migration

James's canonical personal-learning state remains the existing Nexus Owner-learning Ledger until an explicit later migration transaction.

Use `NexusLedgerBackend` only as a read-through compatibility adapter during G4/G5. Bind it to an exact Nexus source revision and Ledger content hash. It must not write the Nexus Ledger or create a second writable `~/.repolearn` mastery truth for James.

A later migration requires explicit transaction evidence: source revision/hash, destination hash, event count, projection equivalence, readback, rollback/restorability, and no-lost-event proof. Migration preflight remains a dry run: destination writes stay disabled and the current source remains the sole writable SSOT until a separately authorized explicit cutover. Missing, stale, conflicting, or reassessment-required evidence fails the migration gate closed. Only after a verified cutover may the old Ledger become historical/pointer-only.

## Client behavior

State loading is bounded and best-effort. Backend unavailability or a stale projection must degrade to normal engineering. This fail-open interaction behavior does not weaken migration safety: ownership/cutover preflight still fails closed on stale or conflicting evidence. Learning state must never lower mastery, alter target-repository authority, or block repository work.
