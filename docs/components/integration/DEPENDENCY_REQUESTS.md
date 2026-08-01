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

## DB-DEP-011 closure evidence

- Backend scaffold: merged through PR #5.
- Deployment scaffold: merged through PR #4.
- Database scaffold: implementation commit `4daa4967e4cb4963ee82c7a1c9fdc7336fe7e6a7`, merged through PR #6 at `739a331c9942ed64a1ad8276d611889bbee53a27`.
- Auth Database reconciliation: PR #9, merge `6cf88f135215984424bec00994a05a1de1dd011e`.
- Workflow Database reconciliation: PR #10, merge and tested commit `99c8022c9f44e6a54bed624aa0153be7e32f234b`.
- Final Integration validation: `INT-DBDEP011-POSTGRES16-001` returned `PASS`.
- Dependency result: `DB-DEP-011` is `ACCEPTED / VERIFIED_COMPLETE / CLOSED`.

No DB-002 implementation request or authorization is created by this closure. A2-DATABASE owns the separate readiness assessment.
