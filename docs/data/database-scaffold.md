# Database scaffold

DB-DEP011-DATABASE-SCAFFOLD-001-C1 provides the synchronous SQLAlchemy 2.x and
psycopg 3 infrastructure. DB-002 builds the domain schema on top of it; see
[`database-schema.md`](database-schema.md) for the models, constraints,
indexes, and migration.

## Layout and connection boundaries

- `app/db/config.py` validates `postgresql+psycopg` URLs.
- `app/db/engine.py` creates runtime engines lazily and provides `SELECT 1`.
- `app/db/session.py` creates synchronous sessions with `autoflush=False` and
  `expire_on_commit=False`.
- `app/db/dependencies.py` yields one request session, rolls back escaping
  exceptions, always closes, and never commits automatically.
- `app/db/metadata.py` holds the single Alembic `MetaData` and its constraint
  and index naming convention.
- `app/db/base.py` holds the one declarative base bound to that `MetaData`;
  `app/db/models/**` holds the DB-002 models.

Runtime engines read only `DATABASE_URL`. Migrations prefer
`MIGRATION_DATABASE_URL`; only when `TESTGAP_RUNTIME` is exactly `local` may
they fall back to `DATABASE_URL`. All other migration configurations fail
closed. URLs and credentials are never logged.

Database connectivity tests validate `TEST_DATABASE_URL` before connecting:
it must use `postgresql+psycopg`, name a database ending exactly in `_test`,
and differ from `DATABASE_URL`. Future migration tests using
`TEST_DATABASE_URL` must call `validate_test_database_url` before Alembic.
Host-registry validation remains pending Deployment/Integration ownership.

## Alembic

Run every command from the repository root with the explicit configuration:

```text
uv run --project apps/api alembic -c apps/api/alembic.ini heads
uv run --project apps/api alembic -c apps/api/alembic.ini history --verbose
uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
```

Since DB-002 there is exactly one head, `ad3f80907336`
(`create DB-002 core entities`). Alembic `target_metadata` is populated by
`alembic/env.py` importing `app.db.models`.
