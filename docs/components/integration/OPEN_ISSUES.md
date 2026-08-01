# Integration Open Issues

## INT-ISSUE-001 — Ownership conflicts resolved

- Classification: `CLOSED`
- Evidence: the Backend, Deployment, and Database acknowledgements are accepted; the approved primary-owner matrix is in `COMPONENT_STATUS.md`.

## INT-ISSUE-002 — Integration coordination commit remote accessibility

- Classification: `CLOSED`
- Evidence: the coordinated scaffold and reconciliations are merged in `origin/main` through tested commit `99c8022c9f44e6a54bed624aa0153be7e32f234b`.

## INT-ISSUE-003 — Scaffold implementation absent

- Classification: `CLOSED`
- Evidence: Backend, Deployment, and Database scaffold implementations are merged and passed final Integration validation.

## INT-ISSUE-004 — Owner-specific commits absent

- Classification: `CLOSED`
- Evidence: Backend PR #5, Deployment PR #4, and Database PR #6 are merged and contained in the tested commit.

## INT-ISSUE-005 — Auth and Workflow Database reconciliations

- Classification: `CLOSED`
- Evidence: Auth Database reconciliation PR #9 and Workflow Database reconciliation PR #10 are merged in the tested commit.
- Boundary: this closes the reconciliation issue but does not start or authorize DB-002.

## INT-ISSUE-006 — Clean-checkout combined-scaffold evidence absent

- Classification: `CLOSED`
- Evidence: `INT-DBDEP011-POSTGRES16-001` passed from a clean checkout; PostgreSQL 16, connectivity, Alembic, schemas, and 28 tests passed with zero skips.

## INT-ISSUE-007 — DB-002 readiness and authorization

- Classification: `OPEN / OUTSIDE_DB-DEP-011`
- Evidence: DB-DEP-011 is closed, but DB-002 was not implemented or assessed by Integration closeout.
- Resolution: A2-DATABASE performs a separate readiness assessment and obtains explicit authorization before DB-002 begins.
