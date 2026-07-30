# Database scaffold

DB-DEP011-DATABASE-SCAFFOLD-001-C1 provides synchronous SQLAlchemy 2.x and
psycopg 3 infrastructure only. DB-002 has not begun: metadata is empty, Alembic
has zero heads, and no domain model, table, or revision exists.

## Layout and connection boundaries

- `app/db/config.py` validates `postgresql+psycopg` URLs.
- `app/db/engine.py` creates runtime engines lazily and provides `SELECT 1`.
- `app/db/session.py` creates synchronous sessions with `autoflush=False` and
  `expire_on_commit=False`.
- `app/db/dependencies.py` yields one request session, rolls back escaping
  exceptions, always closes, and never commits automatically.
- `app/db/metadata.py` contains the deliberately empty Alembic metadata.

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

Before DB-002, `heads` and `history` produce no revisions and `upgrade head` is
a no-op. Do not create a baseline revision.
