# Integration Dependency Requests

## INT-DBDEP011-BACKEND-001 — Backend scaffold ownership acknowledgement

- Request ID: `INT-DBDEP011-BACKEND-001`
- Requesting Agent 2: `A2-INTEGRATION`
- Owning Agent 2: `A2-BACKEND`
- Required change and reason: Acknowledge ownership of `apps/api/**` excluding `apps/api/app/db/**` and `apps/api/alembic/**`; specifically propose the API entrypoint, `apps/api/pyproject.toml`, `apps/api/uv.lock`, shared pytest configuration, `tests/conftest.py`, and `apps/api/app/settings.py`. Confirm that settings implements Deployment-owned names without owning `.env.example`.
- Contract affected: `CONTRACT-INTEGRATION-001`; consumes `CONTRACT-DEPLOY-001` names.
- Decisions required: accept or counter the Backend path boundary, dependency/lock tool, shared-test boundary, and typed-settings implementation boundary.
- Exact blocking task: `INT-DBDEP011-003` and DB-DEP-011 ownership closure.
- Backward-compatibility impact: Initial package layout, dependency resolver/lockfile, test invocation, and settings import paths become shared conventions; later changes require owner approval and migration guidance.
- Rollback boundary: Revert only the Backend-owned scaffold commit; do not alter Database-, Deployment-, or Integration-owned files.
- Urgency: `HIGH`
- Acceptance evidence: From a clean checkout after the owner’s future commit, its documented command creates the environment, imports the empty FastAPI package, validates non-secret settings, and collects the shared test configuration without database implementation.
- Required response format: `ACK`/`REJECT`/`COUNTERPROPOSAL`; exact owned paths; exact command; dependency/lock tool; settings boundary; required consumers; compatibility/rollback note; commit or handoff evidence.
- Approval status: `PENDING`
- Current status: `PENDING`
- Completion evidence: None.

## INT-DBDEP011-DEPLOYMENT-001 — Deployment boundary acknowledgement

- Request ID: `INT-DBDEP011-DEPLOYMENT-001`
- Requesting Agent 2: `A2-INTEGRATION`
- Owning Agent 2: `A2-DEPLOYMENT`
- Required change and reason: Acknowledge ownership of canonical environment names and root `.env.example`, `compose.yml`, `docker/**`, `.github/workflows/**`, `infra/**`, `Dockerfile*`, `scripts/deploy/**`, and `ops/**`. Specify the supported local PostgreSQL version/service, healthcheck, data-volume policy, runtime/migration execution boundary, and `CONTRACT-DEPLOY-001` contribution path.
- Contract affected: `CONTRACT-DEPLOY-001` and `CONTRACT-INTEGRATION-001`.
- Decisions required: accept or counter canonical variable names, local PostgreSQL service/version/healthcheck, data-volume policy, runtime/migration execution boundary, and the Deployment contract-contribution path.
- Exact blocking task: `INT-DBDEP011-003`, DB-DEP-011 ownership closure, and future DB-002 implementation bootstrap.
- Backward-compatibility impact: Environment names, Compose service names, connection semantics, and execution commands become shared conventions; breaking changes require Deployment ownership approval and documented transition/rollback.
- Rollback boundary: Revert only the Deployment-owned scaffold commit; Deployment owns reversal of environment, runtime, and migration wiring.
- Urgency: `HIGH`
- Acceptance evidence: From a clean checkout after the owner’s future commit, the documented local command starts or connects to the supported PostgreSQL service, passes its healthcheck, loads no secret from version control, and supports the Database-owned migration command without publishing a deployment contract prematurely.
- Required response format: `ACK`/`REJECT`/`COUNTERPROPOSAL`; exact owned paths; canonical variable names; local command; PostgreSQL version/healthcheck; migration execution command boundary; consumer list; rollback note; approval state for any deploy-contract contribution.
- Approval status: `PENDING`
- Current status: `PENDING`
- Completion evidence: None.

## INT-DBDEP011-DATABASE-001 — Database migration-boundary acknowledgement

- Request ID: `INT-DBDEP011-DATABASE-001`
- Requesting Agent 2: `A2-INTEGRATION`
- Owning Agent 2: `A2-DATABASE`
- Required change and reason: Acknowledge ownership of `apps/api/app/db/**`, `apps/api/alembic/**`, `apps/api/alembic.ini`, and `tests/database/**`; specify required PostgreSQL connectivity assumptions, Alembic command semantics/order, fixture/test-collection needs, and the point at which Backend/Deployment scaffold is sufficient without freezing Auth or Workflow fields.
- Contract affected: `CONTRACT-DB-001`; consumes `CONTRACT-INTEGRATION-001` and future `CONTRACT-DEPLOY-001`.
- Decisions required: accept or counter Database path boundaries, PostgreSQL assumptions, Alembic command semantics and revision ordering, and database-test collection needs.
- Exact blocking task: `INT-DBDEP011-003` and DB-DEP-011 ownership closure; DB-002 stays separately blocked by Auth/Workflow drafts.
- Backward-compatibility impact: Migration path, revision ordering, test paths, and upgrade/downgrade conventions become durable; changes need Database owner approval and an explicit rollback/compensating plan.
- Rollback boundary: Revert only the Database-owned scaffold commit; no cross-owner migration or deployment rollback is delegated to Integration.
- Urgency: `HIGH`
- Acceptance evidence: After future owner commits, a clean checkout can invoke the Database-owned Alembic command against the Deployment-owned local PostgreSQL service and collect `tests/database/**`; no migration is authored until Auth/Workflow draft contracts pass.
- Required response format: `ACK`/`REJECT`/`COUNTERPROPOSAL`; exact owned paths; required PostgreSQL assumptions; Alembic command/order; test command; consumer list; compatibility/rollback note; evidence.
- Approval status: `PENDING`
- Current status: `PENDING`
- Completion evidence: None.
