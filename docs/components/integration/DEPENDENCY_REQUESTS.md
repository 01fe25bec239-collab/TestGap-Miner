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

The historical closure created no DB-002 implementation request or
authorization. At tested commit
`99c8022c9f44e6a54bed624aa0153be7e32f234b`, DB-002 was correctly
`NOT_STARTED`; that completed dependency history remains unchanged.

## Current DB-002 dependency disposition

- Reconciliation task: `INT-DB002-POSTMERGE-RECONCILE-001`.
- Current baseline: `602fe45c623ac546a11149a54f16a4c84e9f734a`.
- DB-002: `PASS / VERIFIED_COMPLETE / MERGED`; no Integration dependency
  request for DB-002 readiness or implementation remains pending.
- A2-DATABASE evidence: PR #12; implementation commit
  `5506ab59211fbaba79f77d4fb5899a587c0e0236`; implementation merge commit
  `3701520e6d61e2bb80391e7af888d0d530bdb6c4`; final decision `PASS`; Alembic
  head `ad3f80907336`; 169 Database tests, 5 Backend tests, and 174 full-suite
  tests passed with zero failures and zero skips.
- Database record evidence: PR #13 head
  `861781b1c91cc5eed870653bc35b2d39fc9c1021`, merge
  `1511f474ee301651b631c8adfe406aeb775327aa`; PR #14 head
  `c914f8b7443b143241d8c52da0032ee83ecd614e`, merge
  `602fe45c623ac546a11149a54f16a4c84e9f734a`.
- Integration accepts that merged Database evidence without claiming a new
  Integration execution of the DB-002 validation suite.
- DB-003 remains `NOT_STARTED / NOT_AUTHORIZED`; no dependency request here
  authorizes its readiness assessment or implementation.
