# Database Open Issues

- Date: 2026-07-29
- Branch: `agent2/database`
- Starting commit: `0cfd7c0097707586b3bca1f6d2624a7852681ae5`
- Repository count baseline: 15 tracked files; seven specification files
- Initial DB-001 A3 result: `PASS`
- A2 review result: `PARTIAL`
- DB-001-C1 result: `PASS` pending A2 review

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

- Classification: `NOT_STARTED`
- Evidence: no manifests, dependencies, application code, database configuration, ORM models, Alembic files, migrations, tests, CI, containers, contracts, or infrastructure exist.
- Impact: no database version, ORM implementation, migration head, schema, or test result can be reported.
- Resolution path: DB-002 directly requires draft CONTRACT-AUTH-001 and CONTRACT-WORKFLOW-001 plus the owner-approved shared scaffold in DB-DEP-011. Other contracts remain scoped constraints.

## `DB-ISSUE-004` — Retention and deletion semantics are not frozen

- Classification: `PARTIAL`
- Evidence: specifications require retention, deletion, immutable evidence, redaction, backup, and recovery, but no per-domain duration or legal/security rule is approved.
- Blocking contracts/tasks: CONTRACT-SEC-001 and CONTRACT-DEPLOY-001; finalization belongs to DB-007.

## `DB-ISSUE-005` — Critical query and scale assumptions are unavailable

- Classification: `PARTIAL`
- Evidence: required critical lookup families are named, but API pagination/filter shapes, dataset scale, and performance targets are not contracted.
- Blocking contracts/tasks: CONTRACT-API-001, CONTRACT-EVAL-001, DB-007.

## `DB-ISSUE-006` — Shared Python/API/database scaffold is absent

- Classification: `BLOCKED`
- Evidence: no Python/API package scaffold, dependency manifest, lockfile, FastAPI package, test-runner configuration, environment schema/example, local PostgreSQL service, or approved owner map exists.
- Impact: DB-002 implementation cannot start without A3-DATABASE editing unowned protected files.
- Resolution path: A2-INTEGRATION coordinates A2-BACKEND, A2-DEPLOYMENT, and A2-DATABASE ownership and supplies an approved scaffold commit/handoff through DB-DEP-011.

## Resolved specification contradictions

The following are not open because the manager explicitly resolves them:

- PostgreSQL replaces any generic SQLite shortcut.
- Alembic replaces Liquibase/Flyway for the Python stack.
- Organization tenancy, billing, enterprise RBAC, and generic document ingestion are out of MVP scope.
- Raw database-held secrets are rejected.
- pgvector is deferred, not mandatory.
