# Database Open Issues

- Date: 2026-08-02
- Branch: `agent2/database`
- Baseline: `8884b5d540351c735b6cddc01314a7dd9e25af05`
- Synchronized commit: `1511f474ee301651b631c8adfe406aeb775327aa`
- DB-001/DB-001-C1: `PASS`, reviewed, and merged
- DB-001-C1: historical completed continuation
- Original DB-DEP011 scaffold attempt: historical `DEPENDENCY_BLOCKED`
- Database scaffold: `IMPLEMENTED`
- Migration chain: exactly one head, `ad3f80907336`
- Domain schema: `IMPLEMENTED` for DB-002; DB-002:
  `PASS / VERIFIED_COMPLETE / MERGED`; DB-002-C1: `PASS`; DB-002-C2: `PASS`;
  DB-002-MERGE-001: `PASS`
- DB-002 implementation evidence: pull request #12; implementation commit
  `5506ab59211fbaba79f77d4fb5899a587c0e0236`; implementation merge commit
  `3701520e6d61e2bb80391e7af888d0d530bdb6c4`
- DB-002 durable-record reconciliation evidence: documentation pull request
  #13 (`docs(database): close merged DB-002`); head commit
  `861781b1c91cc5eed870653bc35b2d39fc9c1021`; reconciliation merge commit
  `1511f474ee301651b631c8adfe406aeb775327aa`
- `CONTRACT-AUTH-001@1.0.0-draft.2`: `ACKNOWLEDGED_AND_MERGED`
- `DB-DEP-001`: `ACCEPTED`
- `CONTRACT-WORKFLOW-001@1.0.0-draft.1`: `ACKNOWLEDGED_AND_MERGED`
- `DB-DEP-004`: `ACCEPTED`
- DB-DEP-011: `ACCEPTED / VERIFIED_COMPLETE / CLOSED`
- DB-003: `NOT_STARTED` / `NOT_AUTHORIZED`

## `DB-ISSUE-001` — Specification filename mismatch

- Classification: `BLOCKED`
- Evidence: `A2_DATABASE_MANAGER(1).md` names `(8)(7)`, `(12)(3)`, `(13)(3)`, and `(15)(1)` while the repository contains `(8)(8)`, `(12)(4)`, `(13)(4)`, and `(15)(2)`.
- Current handling: `SPECIFICATION_INDEX.md` designates the present files as working inputs.
- Needed resolution: Agent 1 confirms revision lineage. This does not block DB-001 but must be resolved before final acceptance.

## `DB-ISSUE-002` — Upstream contract registry is incomplete

- Classification: `PARTIALLY_RESOLVED`
- Evidence: `CONTRACT-AUTH-001@1.0.0-draft.2` and
  `CONTRACT-WORKFLOW-001@1.0.0-draft.1` are acknowledged and merged, so the
  Auth and Workflow portions are closed. Other task-specific contracts remain
  pending as recorded in `DEPENDENCY_REQUESTS.md`.
- Impact: the direct Auth and Workflow prerequisites are satisfied and the
  DB-002 schema is implemented and merged. DB-002 is
  `PASS / VERIFIED_COMPLETE / MERGED`; DB-002-C1, DB-002-C2, and
  DB-002-MERGE-001 are each `PASS`. Later tasks retain their own prerequisites,
  and no other upstream-owned fields are frozen by this task.

## `DB-ISSUE-003` — No implementation baseline

- Classification: `CLOSED`
- Evidence: DB-002 implements seven tables through Alembic revision
  `ad3f80907336`, with 169 Database tests passing on PostgreSQL 16.14 after
  DB-002-C1, and is merged through implementation PR #12 at implementation
  merge commit
  `3701520e6d61e2bb80391e7af888d0d530bdb6c4`.
- Impact: the Database now has an implementation baseline. Later domains remain
  intentionally unimplemented under their own tasks and contracts.

## `DB-ISSUE-004` — Retention and deletion semantics are not frozen

- Classification: `PARTIAL`
- Evidence: specifications require retention, deletion, immutable evidence, redaction, backup, and recovery, but no per-domain duration or legal/security rule is approved.
- Blocking contracts/tasks: CONTRACT-SEC-001 and CONTRACT-DEPLOY-001; finalization belongs to DB-007.

## `DB-ISSUE-005` — Critical query and scale assumptions are unavailable

- Classification: `PARTIAL`
- Evidence: required critical lookup families are named, but API pagination/filter shapes, dataset scale, and performance targets are not contracted.
- Blocking contracts/tasks: CONTRACT-API-001, CONTRACT-EVAL-001, DB-007.

## `DB-ISSUE-006` — Shared scaffold final validation completed

- Classification: `CLOSED`
- Evidence: A2-INTEGRATION recorded `INT-DBDEP011-POSTGRES16-001` as `PASS` at
  commit `99c8022c9f44e6a54bed624aa0153be7e32f234b`, and DB-DEP-011 is
  `ACCEPTED / VERIFIED_COMPLETE / CLOSED`.
- Remaining action: none.

## `DB-ISSUE-007` — Docker CLI unavailable in A3 environment

- Classification: `CLOSED`
- DB-002 resolution: Docker `29.6.2` and Compose `5.3.1` were available for
  DB-002. The approved `testgap-miner` Compose PostgreSQL 16 service ran at
  server version `16.14`, and every DB-002 migration and test check ran against
  it. The retained volume was preserved and no destructive reset was performed.
- Historical classification: `ENVIRONMENT_LIMITATION`
- Evidence: `docker compose up -d --wait postgres` and
  `docker compose exec -T postgres pg_isready -U postgres -d testgap` were
  blocked because Docker was unavailable.
- Mitigation: the Deployment initializer and all authenticated connectivity,
  zero-head upgrade, Database, Backend, and full-suite checks passed against an
  isolated temporary PostgreSQL cluster; the cluster was stopped.
- Historical approved Compose PostgreSQL 16 validation: `NOT_TESTED` at that
  time; now `PASS` under both `INT-DBDEP011-POSTGRES16-001` and DB-002.

## `DB-ISSUE-008` — Production host registry is not contracted

- Classification: `PENDING`
- Implemented safety: `TEST_DATABASE_URL` requires the
  `postgresql+psycopg` scheme, an exact `_test` database-name suffix, and
  inequality with `DATABASE_URL`.
- Remaining action: Deployment/Integration owns any authoritative production
  host registry; no speculative hostnames are encoded.

## `DB-ISSUE-009` — Auth contract availability and semantic clarifications

- Classification: `CLOSED`
- Resolution: `CONTRACT-AUTH-001@1.0.0-draft.2` was accepted by A2-AUTH,
  acknowledged by A2-DATABASE, and merged in PR #7 at
  `f54f8755c0589db704bd0f94c891da11c42398a6`.
- Superseded Auth blockers: unavailable producer evidence, missing Database
  consumer acknowledgement, and the unmerged Auth contract.
- Accepted clarifications: issuer storage/comparison is exact and
  case-sensitive with no Database normalization; scheduled expiry
  (`expires_at`), recorded expiry (`expired_at`), and explicit revocation
  (`revoked_at`) have distinct meanings.
- Historical state at the time of the contract reconciliation: closure recorded
  contract evidence only; Auth runtime was `NOT_IMPLEMENTED` / `NOT_TESTED`, the
  Database domain schema was `NOT_STARTED`, and DB-002 was `BLOCKED`.
- Current state: Auth runtime remains `NOT_IMPLEMENTED` / `NOT_TESTED`; the
  seven-table DB-002 Database domain schema is implemented.

## `DB-ISSUE-010` — Workflow contract availability and lifecycle ambiguities

- Classification: `CLOSED`.
- Resolution: `CONTRACT-WORKFLOW-001@1.0.0-draft.1` was acknowledged by
  A2-DATABASE with decision `ACCEPTED_WITH_NONBREAKING_CLARIFICATIONS` and
  merged in PR #8 at
  `7da1132b9e30b51a212aa6574c23e2a832d9a6fd`.
- Superseded Workflow blockers: missing contract, missing consumer
  acknowledgement, missing merge evidence, unresolved canonical states,
  repair/retry ambiguity, cancellation and human-review lifecycle ambiguity,
  and DB-002/DB-003 ownership ambiguity.
- Accepted resolution: exact canonical states and transitions, immutable
  terminal projections, one repair with repaired buggy-then-fixed execution,
  separate bounded retries, late-cancellation rules, completion of the existing
  run after human review, new request/run on regeneration, and DB-002 ownership
  of `run_requests`/`runs` versus DB-003 ownership of steps, attempts, events,
  and ordering.
- Historical state at the time of the contract reconciliation: closure recorded
  contract evidence only; Workflow runtime was `NOT_IMPLEMENTED` / `NOT_TESTED`,
  the Database domain schema was `NOT_STARTED`, and DB-002 was
  `BLOCKED_PENDING_FINAL_READINESS_ASSESSMENT`.
- Current state: Workflow runtime remains `NOT_IMPLEMENTED` / `NOT_TESTED`; the
  seven-table DB-002 Database domain schema is implemented.

## `DB-ISSUE-011` — One run per run request is a Database-owned strengthening

- Classification: `CLOSED / ACCEPTED_DATABASE_PHYSICAL_DECISION`
- Owner: `A2-AGENT-WORKFLOW`
- Evidence: `CONTRACT-WORKFLOW-001` states that `RECEIVED` means "a durable run
  request and initial run projection exist", and that a human regeneration
  creates a new request and a new run. It does not state the cardinality
  explicitly.
- Database decision: `runs.run_request_id` is `UNIQUE`, so exactly one current
  projection exists per durable request. Without it, request idempotency would
  not actually deduplicate runs.
- Accepted disposition: this is the Database physical enforcement for one
  current projection per durable request. Regeneration creates a new request and
  run; DB-003 owns historical events rather than duplicate current projections.
- Compatibility: changing this cardinality later requires Workflow consumer
  review and Database migration review.

## `DB-ISSUE-012` — Failure codes are checked by family, not by frozen list

- Classification: `CLOSED / ACCEPTED_WITH_PATTERN_ENFORCEMENT`
- Owner: `A2-AGENT-WORKFLOW`
- Evidence: the contract publishes an exact failure-code table but also states a
  consumer MAY preserve an unknown additive code while MUST using the terminal
  state as the compatibility boundary. A frozen `IN` list would make a run in a
  valid terminal state unstorable after a minor additive contract revision.
- Database decision: `ck_runs_failure_code_matches_state` requires a failure code
  exactly for `FAILED_*` states and applies the matching anchored family pattern.
  Unknown additive codes remain representable, but codes must remain uppercase
  and family-compatible; the terminal state remains the compatibility boundary.
  Bare prefixes, lowercase values, whitespace, invalid punctuation, and
  cross-family codes are rejected. Abstention and cancellation codes remain
  frozen lists because their contract vocabularies are closed.

## `DB-ISSUE-013` — Terminal actor identity shape remains provisional

- Classification: `OPEN_NON_BLOCKING / DEFERRED_CONTRACT_SHAPE`
- Owners: `A2-AGENT-WORKFLOW` and `A2-AUTH`
- Evidence: `CONTRACT-WORKFLOW-001` marks the Auth-owned human identity shape for
  terminal attribution as provisional.
- Database handling: `runs.terminal_actor_id` is bounded opaque text with no
  foreign key, and `runs.terminal_actor_type` is checked against the Workflow
  actor vocabulary `SYSTEM` / `WORKFLOW` / `WORKER` / `HUMAN`.
- DB-002 disposition: the current representation is accepted and did not block
  DB-002 acceptance or merge. No foreign key is frozen. A future Auth/Workflow
  contract may add a typed relationship through an additive migration. This item
  remains open, deferred, and nonblocking after the DB-002 merge.

## `DB-ISSUE-014` — Repository display metadata is deferred

- Classification: `OPEN_NON_BLOCKING / DEFERRED_READ_MODEL`
- Owners: `A2-AUTH`, `A2-BACKEND`
- Evidence: `CONTRACT-AUTH-001` states owner/name strings are mutable display
  metadata that must not authorize access, and no accepted contract requires
  storing them.
- Database handling: `repositories` stores identity and lifecycle only. Adding
  display columns later is an additive migration.
- Needed resolution: `CONTRACT-API-001` (`DB-DEP-002`) defining the read model.
- DB-002 disposition: this item did not block DB-002 acceptance or merge and
  remains open, deferred, and nonblocking afterwards.

## Resolved specification contradictions

The following are not open because the manager explicitly resolves them:

- PostgreSQL replaces any generic SQLite shortcut.
- Alembic replaces Liquibase/Flyway for the Python stack.
- Organization tenancy, billing, enterprise RBAC, and generic document ingestion are out of MVP scope.
- Raw database-held secrets are rejected.
- pgvector is deferred, not mandatory.
