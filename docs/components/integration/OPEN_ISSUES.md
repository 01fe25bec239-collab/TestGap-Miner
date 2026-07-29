# Integration Open Issues

## INT-ISSUE-001 — Ownership conflicts resolved

- Classification: `CLOSED`
- Evidence: the Backend, Deployment, and Database acknowledgements are accepted; the approved primary-owner matrix is in `COMPONENT_STATUS.md`.

## INT-ISSUE-002 — Integration coordination commit remote accessibility

- Classification: `OPEN`
- Evidence: the integration coordination commit is local to `agent2/integration-dbdep011`; remote accessibility is not evidenced by this validation-only task.
- Resolution: publish or otherwise provide remote commit evidence when authorized.

## INT-ISSUE-003 — Scaffold implementation absent

- Classification: `BLOCKED`
- Evidence: no workspace, environment, Compose, database/Alembic, or shared-test scaffold implementation exists.
- Resolution: await the owner-specific scaffold commits in the approved order.

## INT-ISSUE-004 — Owner-specific commits absent

- Classification: `BLOCKED`
- Evidence: no Backend, Deployment, or Database scaffold commit is available for cross-component validation.
- Resolution: owners deliver their bounded scaffold commits.

## INT-ISSUE-005 — Auth and Workflow remain DB-002 blockers

- Classification: `BLOCKED`
- Evidence: DB-002 still requires the Auth and Workflow prerequisite contracts.
- Resolution: do not begin DB-002 until those blockers are resolved by their owners.

## INT-ISSUE-006 — Clean-checkout combined-scaffold evidence absent

- Classification: `BLOCKED`
- Evidence: the committed owner scaffolds, runtime, and test harness do not exist.
- Resolution: INT-DBDEP011-004 validates the combined scaffold from a clean checkout after owner commits.
