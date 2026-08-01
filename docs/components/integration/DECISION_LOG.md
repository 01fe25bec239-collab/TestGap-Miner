# Integration Decision Log

## INT-DEC-007 — Final coordinated ownership decision

- Status: `APPROVED` / `VERIFIED_COMPLETE`.
- A2-BACKEND, A2-DEPLOYMENT, and A2-DATABASE acknowledgements are accepted. Their exact primary ownership is frozen in `COMPONENT_STATUS.md`; A2-INTEGRATION owns the protected-file registry, Integration records, the DB-DEP-011 section of `CONTRACT-INTEGRATION-001`, coordination, validation, and future `tests/integration/**`.
- This is approved ownership, not implementation. No scaffold or contract implementation file is created or approved as implemented by this record. Deployment's contract contribution is recorded as Deployment-approved and remains Deployment-owned.

## INT-DEC-008 — Compatibility conventions

- Package manager: `uv`; Python: `>=3.11,<3.13`; manifest: `apps/api/pyproject.toml`; lockfile: `apps/api/uv.lock`.
- Package import: `app`; ASGI target: `app.main:app`; settings: `apps/api/app/settings.py`; shared pytest configuration: `apps/api/pyproject.toml`.
- Application sessions use synchronous SQLAlchemy `Session`; PostgreSQL driver is synchronous psycopg 3; Alembic execution is synchronous; `pytest-asyncio` is not initially required. A future async move requires a new coordinated decision.
- PostgreSQL major: 16; local image: `postgres:16.14-alpine3.24`; Compose service: `postgres`; runtime DB: `testgap`; test DB: `testgap_test`; test initializer: `docker/postgres/init/10-create-test-database.sh`; initial extensions: none; pgvector is deferred.

## INT-DEC-009 — Environment and role boundary

| Variable / role | Frozen contract |
|---|---|
| `DATABASE_URL` | Normal API/worker runtime only, using a least-privilege DML role. Loaded by ordinary Backend settings and never logged. |
| `MIGRATION_DATABASE_URL` | Migration execution only, using a DDL-capable role. Separately injected in production and not loaded by ordinary API/workers. |
| `TEST_DATABASE_URL` | Test settings only; differs from `DATABASE_URL`; targets a database ending in `_test`; rejects production targets; not loaded by production API/workers. |
| `TESTGAP_RUNTIME` | Deployment-only Compose/init control; not an ordinary API setting. |
| `POSTGRES_USER`, `POSTGRES_DB`, `POSTGRES_PASSWORD`, `POSTGRES_HOST_PORT` | Deployment/Compose-only. The application consumes `DATABASE_URL` instead. |
| Application role | Normal DML; no unrestricted DDL, database/role creation, or superuser. |
| Migration role | Sufficient DDL for owned-schema migration; never used by API/workers; not superuser unless separately approved. |
| Test role | Limited to `testgap_test`; no development or production access. |

Deployment implements exact grants and secret injection; Database approves privilege semantics and migration capability.

## INT-DEC-010 — Migration identity and test-database provisioning

Every Alembic command must explicitly pass `-c apps/api/alembic.ini`:

```text
uv run --project apps/api alembic -c apps/api/alembic.ini heads
uv run --project apps/api alembic -c apps/api/alembic.ini current
uv run --project apps/api alembic -c apps/api/alembic.ini history --verbose
uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
```

The final PostgreSQL 16 validation executed the applicable commands successfully: zero heads, zero revisions, and a no-op `upgrade head`. Connection precedence is: (1) `MIGRATION_DATABASE_URL` when present; (2) `DATABASE_URL` only for explicitly permitted local development; (3) `TEST_DATABASE_URL` only when deliberately mapped into `MIGRATION_DATABASE_URL` for migration testing. Zero heads are acceptable before DB-002. DB-DEP-011 creates no domain model or revision. Once DB-002 creates the first revision, exactly one head is required. Only A2-DATABASE authors revisions; Deployment executes but does not own migration contents.

Test database provisioning is owned by A2-DEPLOYMENT at `docker/postgres/init/10-create-test-database.sh`. It runs only in local or CI, creates `testgap_test` idempotently, never runs in production, and no Alembic revision creates the database. CI uses isolated project-scoped storage and project-scoped cleanup. Database retains schema-migration ownership inside `testgap_test`.

## INT-DEC-011 — Merge and rollback boundary

The final merge order and owner-specific rollback allocations are approved in `COMPONENT_STATUS.md`. Applied migrations and shared consumed contracts require coordinated rollback; environment-variable renames require coordinated compatibility and rollback planning.

## INT-DEC-012 — DB-DEP-011 final acceptance

- Status: `ACCEPTED / VERIFIED_COMPLETE / CLOSED`.
- Validation: `INT-DBDEP011-POSTGRES16-001` returned `PASS` against commit `99c8022c9f44e6a54bed624aa0153be7e32f234b`.
- Evidence: PostgreSQL `16.14` ran healthy from `postgres:16.14-alpine3.24`; runtime and isolated test connectivity passed; Alembic remained at zero heads/revisions; the no-op upgrade and all 28 tests passed with zero failures and zero skips.
- Scope: no domain model, domain table, DB-002 implementation, real secret, or ownership conflict was introduced.
- Local port: because 5432 was occupied, the approved loopback `POSTGRES_HOST_PORT=55478` override was used.
- Limitation: fresh-volume initialization was not repeated; retained-volume idempotent provisioning passed and is non-blocking.
- Auth and Workflow Database reconciliations are merged through PRs #9 and #10.
- Historical boundary: at tested commit
  `99c8022c9f44e6a54bed624aa0153be7e32f234b`, DB-002 was correctly
  `NOT_STARTED` pending separate A2-DATABASE readiness and authorization. This
  remains valid DB-DEP-011 closeout evidence.

## INT-DEC-013 — Reconcile current merged DB-002 state

- Date: 2026-08-02.
- Task: `INT-DB002-POSTMERGE-RECONCILE-001`.
- Status: `APPROVED / VERIFIED_COMPLETE`.
- Decision: at repository baseline
  `602fe45c623ac546a11149a54f16a4c84e9f734a`, DB-002 is
  `PASS / VERIFIED_COMPLETE / MERGED`.
- No historical decision is reversed. INT-DEC-012 accurately recorded the
  repository at `99c8022c9f44e6a54bed624aa0153be7e32f234b`; current status changed
  later through accepted A2-DATABASE implementation PR #12, Database closeout
  PR #13, and Database correction PR #14.
- Implementation evidence: PR #12, implementation commit
  `5506ab59211fbaba79f77d4fb5899a587c0e0236`, implementation merge commit
  `3701520e6d61e2bb80391e7af888d0d530bdb6c4`, and A2-DATABASE final decision
  `PASS`.
- Database reconciliation evidence: PR #13 head
  `861781b1c91cc5eed870653bc35b2d39fc9c1021`, merge
  `1511f474ee301651b631c8adfe406aeb775327aa`; PR #14 head
  `c914f8b7443b143241d8c52da0032ee83ecd614e`, merge
  `602fe45c623ac546a11149a54f16a4c84e9f734a`.
- Evidence ownership: A2-DATABASE performed and accepted DB-002 implementation
  and validation. Integration performed no new DB-002 runtime validation and
  only reconciled its durable records to accepted merged Database evidence.
- DB-DEP-011 remains `ACCEPTED / VERIFIED_COMPLETE / CLOSED`. DB-003 remains
  `NOT_STARTED / NOT_AUTHORIZED`; this decision authorizes no later persistence.
