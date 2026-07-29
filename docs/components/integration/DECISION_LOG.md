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

All commands are `PROPOSED_COMMAND — NOT_YET_EXECUTABLE`. Connection precedence is: (1) `MIGRATION_DATABASE_URL` when present; (2) `DATABASE_URL` only for explicitly permitted local development; (3) `TEST_DATABASE_URL` only when deliberately mapped into `MIGRATION_DATABASE_URL` for migration testing. Zero heads are acceptable before DB-002. DB-DEP-011 creates no domain model or revision. Once DB-002 creates the first revision, exactly one head is required. Only A2-DATABASE authors revisions; Deployment executes but does not own migration contents.

Test database provisioning is owned by A2-DEPLOYMENT at `docker/postgres/init/10-create-test-database.sh`. It runs only in local or CI, creates `testgap_test` idempotently, never runs in production, and no Alembic revision creates the database. CI uses isolated project-scoped storage and project-scoped cleanup. Database retains schema-migration ownership inside `testgap_test`.

## INT-DEC-011 — Merge and rollback boundary

The final merge order and owner-specific rollback allocations are approved in `COMPONENT_STATUS.md`. Applied migrations and shared consumed contracts require coordinated rollback; environment-variable renames require coordinated compatibility and rollback planning.
