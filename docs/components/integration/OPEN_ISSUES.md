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

- Classification: `CLOSED / HISTORICAL_CONTEXT_PRESERVED`
- Historical evidence: at the DB-DEP-011 closeout snapshot and tested commit
  `99c8022c9f44e6a54bed624aa0153be7e32f234b`, DB-002 was correctly
  `NOT_STARTED` and outside that task's authorization.
- Current resolution: A2-DATABASE later implemented and validated DB-002. PR
  #12 used implementation commit
  `5506ab59211fbaba79f77d4fb5899a587c0e0236` and merge
  `3701520e6d61e2bb80391e7af888d0d530bdb6c4`; A2-DATABASE's final decision was
  `PASS`. Database closeout PR #13 merged at
  `1511f474ee301651b631c8adfe406aeb775327aa`, and correction PR #14 merged at
  current baseline `602fe45c623ac546a11149a54f16a4c84e9f734a`.
- Current state: DB-002 is `PASS / VERIFIED_COMPLETE / MERGED`.
- Evidence boundary: Integration reconciled accepted merged Database evidence;
  it did not independently execute the DB-002 validation suite.
- Remaining boundary: DB-003 is `NOT_STARTED / NOT_AUTHORIZED`. Auth runtime
  and Workflow runtime remain `NOT_IMPLEMENTED / NOT_TESTED`; DB-002 provides
  no Workflow orchestration or transition history.
