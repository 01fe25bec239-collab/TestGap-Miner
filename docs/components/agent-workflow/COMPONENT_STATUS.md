# Agent Workflow Component Status

- Date: 2026-08-11
- Branch: `agent2/workflow-003-persistence-integration`
- Task: `WORKFLOW-003-POST-PR40-CURRENT-MAIN-VALIDATION-001`
- Baseline: `2fe29e466b1c84799ef0d6d6d28fbcadb572c964`
- Reconciled Base: `6b5485368367064e7f36b5837f49734425f284ee`
- Contract: `CONTRACT-WORKFLOW-001@1.0.0-draft.1`

## Current result

- Result: `PASS — WORKFLOW_003_POST_PR40_RECONCILED_AND_POSTGRESQL_VALIDATED_READY_FOR_GIT_LIFECYCLE`
- WORKFLOW-003: `IMPLEMENTED` / `TESTED` / `A2_ACCEPTED` /
  `READY_FOR_GIT_LIFECYCLE`
- WORKFLOW-003 C1: `HISTORICAL_CORRECTION_COMPLETE` / `A2_ACCEPTED`
- WORKFLOW-003 C2: `HISTORICAL_CORRECTION_COMPLETE` / `A2_ACCEPTED`
- WORKFLOW-002 pure lifecycle foundation: `PASS` / `MERGED` / `A2_ACCEPTED`
- DB-003: `PASS` / `MERGED` / consumed without modification
- Workflow PostgreSQL integration: `PASS` / real isolated PostgreSQL 17.10 /
  no Workflow PostgreSQL skips
- Workflow tests: `556 passed`
- DB-003 persistence and constraint regressions: `157 passed`
- API plus Workflow regressions: `598 passed`
- Full Python suite: `826 passed`, `0 skipped` (or `825 passed`, `1 skipped` when runtime `DATABASE_URL` is omitted)
- Compile: `PASS`
- `git diff --check`: `PASS`
- Reconciled base: PR #40 merged `apps/worker/**` (Java/JUnit/Defects4J adapters); no Workflow path or semantic conflict
- Full Workflow runtime: `NOT_IMPLEMENTED`
- Queue integration: `NOT_IMPLEMENTED`
- Execution integration: `NOT_IMPLEMENTED`
- Evidence integration: `NOT_IMPLEMENTED`
- API integration: `NOT_IMPLEMENTED`

## Implemented boundary

`app.workflow.persistence` now provides the Workflow-owned adapter between the
frozen WORKFLOW-002 decision engine and DB-003's `append_run_event` and
`compare_and_swap_run` primitives. It explicitly maps the durable contract
version, reconstructs and validates `LifecycleSnapshot`, requires event actor
attribution, evaluates new work through the pure engine, and atomically flushes
one `STATE_TRANSITIONED` event plus the allowlisted Run CAS projection update
inside a savepoint in the caller-owned transaction.

The result distinguishes `APPLIED`, `IDEMPOTENT_REPLAY`, `REJECTED`,
`CONFLICT`, `INVALID_DURABLE_STATE`, and `RUN_NOT_FOUND`. Conflict reasons are
`STALE_PROJECTION`, `PRODUCER_EVENT_CONFLICT`, and
`PERSISTENCE_INCONSISTENCY`.

The A2-accepted C1 correction validates the locked current durable Run before
classifying new work, stale requests, or replays. A stale request first performs
a read-only producer-event existence query; a missing event cannot insert a new
event and returns `STALE_PROJECTION`, while an existing event is still delegated
to DB-003 as the producer-fingerprint authority. Invalid durable state precedes
stale/replay classification, PostgreSQL tests prove caller-owned outer rollback,
and the task-ledger history is preserved.

The C2 correction validates durable terminal semantics after snapshot field
validation: `FAILED_INFRASTRUCTURE` requires an exhausted retry budget, and
`REPAIR_LIMIT_EXHAUSTED` requires the one repair allowance to be consumed.
These invariants fail closed before stale/replay classification, so malformed
terminal projections cannot become `IDEMPOTENT_REPLAY`; valid terminal replay
remains `IDEMPOTENT_REPLAY`.

## Preserved boundaries

- Queue integration, Execution integration, Evidence integration,
  RAG/localisation, model/provider orchestration, publication orchestration,
  API routes, `WorkflowStep` orchestration, `WorkflowStepAttempt` orchestration,
  persistent retry scheduling, checkpoint storage, and regeneration child-run
  creation remain `NOT_IMPLEMENTED`.
- No fingerprint algorithm, sequence allocator, alternate CAS, or alternate
  event store was added.
- No Database-owned file, migration, Database test, dependency, lockfile, or
  Workflow contract file changed.
- WORKFLOW-002 `engine.py`, `types.py`, and `checkpoint.py` remain unchanged and
  free of persistence/runtime imports.

## Review state

- A3 implementation and test evidence: complete.
- A2 final result: `PASS — WORKFLOW_003_A2_FINAL_REVIEW_COMPLETE`.
- A2 acceptance: WORKFLOW-003, C1, and C2 accepted.
- Next action: Git lifecycle.
- Staged: no.
- Committed: no.
- Pushed: no.
- PR: none.
- Assumed: none.
