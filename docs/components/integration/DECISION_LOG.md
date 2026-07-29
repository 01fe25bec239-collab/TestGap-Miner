# Integration Decision Log

## INT-DEC-001 — Early coordination scope

- Status: `VERIFIED_COMPLETE`
- A2-INTEGRATION’s general final-integration scope is narrowed by the phase-specific DB-DEP-011 manager prompt, which authorizes documentation-only early coordination. No scaffold implementation is authorized.

## INT-DEC-002 — Ownership baseline

- Status: `PROPOSED`, pending owner acknowledgement.
- Backend owns the API workspace, entrypoint, manifest/lockfile, shared pytest configuration, and typed settings implementation.
- Database owns DB/ORM/Alembic paths and migration semantics.
- Deployment owns canonical environment names, `.env.example`, local PostgreSQL/Compose, runtime execution, CI, and deployment files.
- Integration owns the ownership ledger, dependency coordination, merge-order validation, and `CONTRACT-INTEGRATION-001` coordination record.

## INT-DEC-003 — Contract boundary

- Status: `VERIFIED_COMPLETE`.
- A2-INTEGRATION owns `CONTRACT-INTEGRATION-001`; A2-DEPLOYMENT exclusively owns `CONTRACT-DEPLOY-001`. This task cannot approve, publish, or alter the latter.

## INT-DEC-004 — Technical baseline and gate

- Status: `VERIFIED_COMPLETE`.
- PostgreSQL + SQLAlchemy 2.x + Alembic is preserved as the persistence baseline.
- DB-002 remains blocked by Auth and Workflow drafts even after the scaffold is eventually accepted.

## INT-DEC-005 — Rollback and merge boundary

- Status: `PROPOSED`.
- Owner commits merge in the documented order and remain independently revertible. No cross-owner migration, environment, or deployment rollback is delegated to Integration.

## INT-DEC-006 — Approval and implementation state

- Status: `VERIFIED_COMPLETE`.
- Proposed ownership is not approved ownership: every protected-path assignment remains `PROPOSED` pending the three owner acknowledgements.
- Implemented files: only these six Integration management records. No application scaffold, contract, environment, deployment, database, migration, or test implementation exists.
