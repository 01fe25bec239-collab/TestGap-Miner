# Database Open Issues

- Date: 2026-07-30
- Branch: `agent2/database`
- Current scaffold baseline: `11b8019f91921f9be5cc162ac3db48e9bd2d5364`
- DB-001/DB-001-C1: `PASS`, reviewed, and merged
- DB-001-C1: historical completed continuation
- Original DB-DEP011 scaffold attempt: historical `DEPENDENCY_BLOCKED`
- Database scaffold: `IMPLEMENTED`
- Migration chain: bootstrap exists with zero heads and no revisions
- Domain schema: `NOT_STARTED`; DB-002: `BLOCKED`
- `CONTRACT-AUTH-001` and `CONTRACT-WORKFLOW-001`: `PENDING`
- DB-DEP-011: `PENDING_INTEGRATION_VALIDATION`

## `DB-ISSUE-001` — Specification filename mismatch

- Classification: `BLOCKED`
- Evidence: `A2_DATABASE_MANAGER(1).md` names `(8)(7)`, `(12)(3)`, `(13)(3)`, and `(15)(1)` while the repository contains `(8)(8)`, `(12)(4)`, `(13)(4)`, and `(15)(2)`.
- Current handling: `SPECIFICATION_INDEX.md` designates the present files as working inputs.
- Needed resolution: Agent 1 confirms revision lineage. This does not block DB-001 but must be resolved before final acceptance.

## `DB-ISSUE-002` — Upstream contract registry is documentation-only

- Classification: `BLOCKED`
- Evidence: no versioned contract artefacts or completed handoffs exist for CONTRACT-AUTH-001, CONTRACT-API-001, CONTRACT-RAG-001, CONTRACT-WORKFLOW-001, CONTRACT-EVIDENCE-001, CONTRACT-QUEUE-001, CONTRACT-EVAL-001, CONTRACT-SEC-001, CONTRACT-DEPLOY-001, or CONTRACT-INTEGRATION-001.
- Impact: DB-002 directly awaits Auth and Workflow drafts. Later tasks retain their task-specific prerequisites, and no upstream-owned fields may be frozen.
- Tracking: eleven requests are prepared in `DEPENDENCY_REQUESTS.md`.

## `DB-ISSUE-003` — No implementation baseline

- Classification: `PARTIALLY_RESOLVED`
- Evidence: the shared Database infrastructure, Alembic bootstrap, tests, and
  documentation now exist. Alembic has zero heads and there is deliberately no
  ORM model, domain table, or revision.
- Impact: DB-002 remains unimplemented.
- Resolution path: A2-DATABASE/A2-INTEGRATION review the scaffold; DB-002 still
  requires draft CONTRACT-AUTH-001 and CONTRACT-WORKFLOW-001.

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

## Resolved specification contradictions

The following are not open because the manager explicitly resolves them:

- PostgreSQL replaces any generic SQLite shortcut.
- Alembic replaces Liquibase/Flyway for the Python stack.
- Organization tenancy, billing, enterprise RBAC, and generic document ingestion are out of MVP scope.
- Raw database-held secrets are rejected.
- pgvector is deferred, not mandatory.
