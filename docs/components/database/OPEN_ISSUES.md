# Database Open Issues

- Date: 2026-07-31
- Branch: `agent2/database`
- Synchronized baseline: `f54f8755c0589db704bd0f94c891da11c42398a6`
- DB-001/DB-001-C1: `PASS`, reviewed, and merged
- DB-001-C1: historical completed continuation
- Original DB-DEP011 scaffold attempt: historical `DEPENDENCY_BLOCKED`
- Database scaffold: `IMPLEMENTED`
- Migration chain: bootstrap exists with zero heads and no revisions
- Domain schema: `NOT_STARTED`; DB-002: `BLOCKED`
- `CONTRACT-AUTH-001@1.0.0-draft.2`: `ACKNOWLEDGED_AND_MERGED`
- `DB-DEP-001`: `ACCEPTED`
- Workflow: separate verified Database post-merge reconciliation required
- DB-DEP-011: `PENDING_INTEGRATION_VALIDATION`

## `DB-ISSUE-001` — Specification filename mismatch

- Classification: `BLOCKED`
- Evidence: `A2_DATABASE_MANAGER(1).md` names `(8)(7)`, `(12)(3)`, `(13)(3)`, and `(15)(1)` while the repository contains `(8)(8)`, `(12)(4)`, `(13)(4)`, and `(15)(2)`.
- Current handling: `SPECIFICATION_INDEX.md` designates the present files as working inputs.
- Needed resolution: Agent 1 confirms revision lineage. This does not block DB-001 but must be resolved before final acceptance.

## `DB-ISSUE-002` — Upstream contract registry is incomplete

- Classification: `PARTIALLY_RESOLVED`
- Evidence: `CONTRACT-AUTH-001@1.0.0-draft.2` is acknowledged and merged, so
  the Auth portion is closed. Workflow documentation is merged but requires a
  separate verified Database post-merge reconciliation. Other task-specific
  contracts remain pending as recorded in `DEPENDENCY_REQUESTS.md`.
- Impact: DB-002 no longer awaits Auth. It remains blocked on Workflow
  reconciliation and final Database scaffold/readiness verification. Later
  tasks retain their own prerequisites, and no other upstream-owned fields are
  frozen by this task.

## `DB-ISSUE-003` — No implementation baseline

- Classification: `PARTIALLY_RESOLVED`
- Evidence: the shared Database infrastructure, Alembic bootstrap, tests, and
  documentation now exist. Alembic has zero heads and there is deliberately no
  ORM model, domain table, or revision.
- Impact: DB-002 remains unimplemented.
- Resolution path: complete final Database scaffold/readiness verification and
  the separate Workflow post-merge reconciliation before assessing DB-002
  readiness.

## `DB-ISSUE-004` — Retention and deletion semantics are not frozen

- Classification: `PARTIAL`
- Evidence: specifications require retention, deletion, immutable evidence, redaction, backup, and recovery, but no per-domain duration or legal/security rule is approved.
- Blocking contracts/tasks: CONTRACT-SEC-001 and CONTRACT-DEPLOY-001; finalization belongs to DB-007.

## `DB-ISSUE-005` — Critical query and scale assumptions are unavailable

- Classification: `PARTIAL`
- Evidence: required critical lookup families are named, but API pagination/filter shapes, dataset scale, and performance targets are not contracted.
- Blocking contracts/tasks: CONTRACT-API-001, CONTRACT-EVAL-001, DB-007.

## `DB-ISSUE-006` — Shared scaffold final validation is pending

- Classification: `PENDING_INTEGRATION_VALIDATION`
- Evidence: Backend and Deployment scaffolds are merged at `11b8019`; the
  Database-owned continuation implements the remaining persistence scaffold
  without modifying any unowned file. Database unit/bootstrap tests and
  authenticated temporary PostgreSQL 17.10 checks passed.
- Remaining action: A2-DATABASE review and A2-INTEGRATION clean-checkout
  validation with the approved Compose PostgreSQL 16 service.

## `DB-ISSUE-007` — Docker CLI unavailable in A3 environment

- Classification: `ENVIRONMENT_LIMITATION`
- Evidence: `docker compose up -d --wait postgres` and
  `docker compose exec -T postgres pg_isready -U postgres -d testgap` were
  blocked because Docker was unavailable.
- Mitigation: the Deployment initializer and all authenticated connectivity,
  zero-head upgrade, Database, Backend, and full-suite checks passed against an
  isolated temporary PostgreSQL cluster; the cluster was stopped.
- Approved Compose PostgreSQL 16 validation: `NOT_TESTED`.
- Resolution: A2-INTEGRATION reruns both commands and the full Database
  validation in a Docker-enabled clean checkout.

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
- Scope: closure records contract evidence only. Auth runtime remains
  `NOT_IMPLEMENTED` / `NOT_TESTED`; Database domain schema remains
  `NOT_STARTED`; DB-002 remains `BLOCKED`.

## Resolved specification contradictions

The following are not open because the manager explicitly resolves them:

- PostgreSQL replaces any generic SQLite shortcut.
- Alembic replaces Liquibase/Flyway for the Python stack.
- Organization tenancy, billing, enterprise RBAC, and generic document ingestion are out of MVP scope.
- Raw database-held secrets are rejected.
- pgvector is deferred, not mandatory.
