# Environment variable registry

This is the canonical registry for Deployment-owned database environment variables. Keep real values in the deployment secret store or an untracked `.env` file; `.env.example` contains placeholders only.

| Variable | Consumers | Required use |
| --- | --- | --- |
| `DATABASE_URL` | API and workers | DML runtime URL for `testgap_app`, for example `postgresql+psycopg://testgap_app:<app-password>@127.0.0.1:5432/testgap`. |
| `MIGRATION_DATABASE_URL` | Migration job via `scripts/deploy/migrate.sh` | DDL-capable migration URL, for example `postgresql+psycopg://testgap_migrator:<migration-password>@127.0.0.1:5432/testgap`. API and workers must not use it. |
| `TEST_DATABASE_URL` | Tests only | Test-only URL targeting `testgap_test`, for example `postgresql+psycopg://testgap_test:<test-password>@127.0.0.1:5432/testgap_test`. It is forbidden in production. |
| `TESTGAP_RUNTIME` | PostgreSQL initializer and local reset | Deployment initialization guard. Its only valid values are `local` and `ci`. It is not an application setting. |
| `POSTGRES_USER` | Local Compose PostgreSQL | Fixed to `postgres`, the local bootstrap-only superuser. Applications must not use it. |
| `POSTGRES_DB` | Local Compose PostgreSQL | Fixed to the runtime database `testgap`. |
| `POSTGRES_PASSWORD` | Local Compose PostgreSQL | Required bootstrap-only `postgres` password. |
| `POSTGRES_APP_PASSWORD` | Local initializer | Required password for the non-superuser `testgap_app` DML role. |
| `POSTGRES_MIGRATION_PASSWORD` | Local initializer | Required password for the non-superuser `testgap_migrator` DDL role. |
| `POSTGRES_TEST_PASSWORD` | Local initializer | Required password for the non-superuser `testgap_test` DML role. |
| `POSTGRES_HOST_PORT` | Local Compose PostgreSQL | Loopback host port; defaults to `5432`. |

All password values are secret inputs and must never be committed. Compose fixes `POSTGRES_USER=postgres` and `POSTGRES_DB=testgap`; neither is application configuration.
