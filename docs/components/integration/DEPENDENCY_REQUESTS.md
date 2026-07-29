# Integration Dependency Requests

## Accepted acknowledgements

### INT-DBDEP011-BACKEND-001

- Requesting owner: A2-INTEGRATION; responding owner: A2-BACKEND.
- Approval status: `ACCEPTED` / `VERIFIED_COMPLETE`.
- Preserved response summary: accepts primary ownership of the minimal Python/FastAPI workspace, `apps/api/**` excluding the Database paths, `app.main`, `app.settings`, `pyproject.toml`, `uv.lock`, `tests/conftest.py`, `tests/api/**`, and shared non-database fixtures. Accepts `uv`, Python `>=3.11,<3.13`, import `app`, ASGI target `app.main:app`, and the shared pytest configuration boundary. Settings load the Deployment-owned ordinary-runtime names but do not own `.env.example`. Backend rollback is limited to its unmerged scaffold commit, including manifest/lockfile.

### INT-DBDEP011-DEPLOYMENT-001

- Requesting owner: A2-INTEGRATION; responding owner: A2-DEPLOYMENT.
- Approval status: `ACCEPTED` / `VERIFIED_COMPLETE`.
- Preserved response summary: accepts primary ownership of the canonical environment registry, `.env.example`, deployment records including `CONTRACT-DEPLOY-001`, PostgreSQL lifecycle, `compose.yml`, `Dockerfile`, `docker/**`, CI, infrastructure, deploy scripts, and operations files. Approves PostgreSQL 16 through `postgres:16.14-alpine3.24`, service `postgres`, `testgap`, idempotent local/CI-only `testgap_test` initialization, secret injection, grants, and migration-execution wiring. Deployment executes Database-owned migration contents and owns rollback of environment, Compose, CI, and migration wiring.

### INT-DBDEP011-DATABASE-001

- Requesting owner: A2-INTEGRATION; responding owner: A2-DATABASE.
- Approval status: `ACCEPTED` / `VERIFIED_COMPLETE`.
- Preserved response summary: accepts primary ownership of DB/ORM/Alembic paths, database tests, data and component records, `CONTRACT-DB-001`, synchronous SQLAlchemy/psycopg 3 semantics, migrations, ordering, and schema-validation requirements. Approves the explicit Alembic configuration path, the stated connection precedence, zero heads before DB-002, exactly one head after its first revision, and Database-only authorship of revisions. Database rollback is limited to its unmerged Alembic bootstrap and DB-fixture commit.

No implementation request is created by INT-DBDEP011-003. Owner-specific scaffold requests and commits are the prerequisite for INT-DBDEP011-004.
