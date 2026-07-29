# Integration Component Status

- Date: 2026-07-30
- Agent 2: A2-INTEGRATION
- Paired Agent 3: A3-INTEGRATION
- Worktree: `/private/tmp/testgap-integration-dbdep011`
- Branch: `agent2/integration-dbdep011`
- Baseline commit: `e8dfd8d022324c5509dbb2db7c71544e7a06d36d`

## DB-DEP-011 state

| Item | State | Evidence / next action |
|---|---|---|
| INT-DBDEP011-002 owner acknowledgements | `VERIFIED_COMPLETE` | Backend, Deployment, and Database acknowledgements accepted. |
| INT-DBDEP011-003 final coordinated ownership decision | `VERIFIED_COMPLETE` | This record set freezes the approved ownership and compatibility decisions. |
| DB-DEP-011 | `PENDING` | Await owner-specific scaffold commits; no implementation is authorized by this decision. |
| Scaffold implementation | `NOT_STARTED` | No application, database, deployment, migration, or test scaffold exists. |
| DB-002 | `BLOCKED` | Auth and Workflow blockers remain independent of DB-DEP-011. |

## Approved primary ownership matrix

| Owner | Protected paths and responsibilities |
|---|---|
| A2-BACKEND | `apps/api/**` except Database-owned paths; `apps/api/app/main.py`; `apps/api/app/settings.py`; `apps/api/pyproject.toml`; `apps/api/uv.lock`; `tests/conftest.py`; `tests/api/**`; shared non-database pytest fixtures. Excludes `apps/api/app/db/**`, `apps/api/alembic/**`, and `apps/api/alembic.ini`. |
| A2-DATABASE | `apps/api/app/db/**`; `apps/api/app/db/models/**`; `apps/api/alembic/**`; `apps/api/alembic.ini`; `tests/database/**`; `docs/data/**`; `docs/components/database/**`; `CONTRACT-DB-001`; ORM/persistence semantics; Alembic configuration and revisions; migration ordering; database test/schema validation requirements. |
| A2-DEPLOYMENT | `.env.example`; `docs/components/deployment/ENVIRONMENT_VARIABLES.md`; `docs/components/deployment/CONTRACT-DEPLOY-001.md`; `compose.yml`; `Dockerfile`; `docker/**`; `.github/workflows/**`; `infra/**`; `scripts/deploy/**`; `ops/**`; PostgreSQL lifecycle; canonical environment registry; CI and deployed-migration execution wiring. |
| A2-INTEGRATION | Protected-file ownership registry; Integration component records; DB-DEP-011 section of `CONTRACT-INTEGRATION-001`; merge-order and rollback coordination; cross-component acceptance validation; `tests/integration/**` when created. |

Approved ownership is not implementation: no listed scaffold file exists or is changed by this task. Deployment's `CONTRACT-DEPLOY-001` contribution is Deployment-approved; Integration records the approval and does not own its content.

## Merge and rollback coordination

1. A2-BACKEND creates the minimal Python workspace, manifest, lockfile, importable FastAPI package, settings boundary, and shared pytest harness.
2. A2-DEPLOYMENT creates the canonical environment registry, `.env.example`, PostgreSQL 16 Compose service, test-database initializer, container/runtime files, and migration-execution wiring.
3. A2-DATABASE creates only the database scaffold: `app/db` package, Alembic bootstrap configuration, database fixtures, and database validation harness.
4. A2-INTEGRATION validates the combined scaffold from a clean checkout.

No domain model or Alembic revision may be created during DB-DEP-011. Deployment may merge before Database when its PostgreSQL service is required for Database validation, but Backend's manifest/package boundary must be available before Database dependency and test validation.

- Each owner may revert its own unmerged scaffold commit.
- Backend owns manifest/lockfile rollback; Deployment owns environment, Compose, CI, and migration-wiring rollback; Database owns Alembic bootstrap and DB-fixture rollback.
- Applied migrations and shared consumed contracts require coordinated rollback.
- A synchronous-to-asynchronous SQLAlchemy change, or any environment-variable rename, requires a new coordinated compatibility decision; renames also require rollback planning.
