# CONTRACT-DEPLOY-001 — Database runtime boundary

- Status: `APPROVED`
- Owner: A2-DEPLOYMENT
- Scope: DB-DEP-011 deployment scaffold

## Runtime roles and URLs

`postgres` is the local bootstrap-only superuser and must never be used by application, worker, test, or migration processes.

`DATABASE_URL` uses the non-superuser `testgap_app` role for DML against `testgap` only. `MIGRATION_DATABASE_URL` uses the non-superuser `testgap_migrator` role, which owns `testgap` and `testgap_test` and may execute DDL in both. API processes and workers must never use `MIGRATION_DATABASE_URL`.

`TEST_DATABASE_URL` uses the non-superuser `testgap_test` role for DML against `testgap_test` only. It is forbidden in production and cannot connect to `testgap`.

## Local lifecycle

`compose.yml` provides exactly one local PostgreSQL 16 service under the local project name `testgap-miner`. Only when `TESTGAP_RUNTIME` is `local` or `ci`, the initializer idempotently creates the three non-superuser roles and `testgap_test`, assigns both databases to the migration role, revokes public connectivity and schema creation, and installs future DML default privileges for the matching runtime role. None of these roles may create databases, roles, replication slots, or bypass row-level security.

Local reset requires `TESTGAP_RUNTIME=local` and an explicit `--yes`. It resolves the repository root and removes only the `testgap-miner` Compose project's volumes.

## Migration execution

`scripts/deploy/migrate.sh` requires `MIGRATION_DATABASE_URL` and executes the Database-owned Alembic configuration with an explicit `-c apps/api/alembic.ini`. DB-DEP-011 does not create Alembic configuration or revisions; the wrapper reports that absence until the Database owner supplies them.
