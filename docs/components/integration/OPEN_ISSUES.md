# Integration Open Issues

## INT-ISSUE-001 — DB-DEP-011 has no owner acknowledgements

- Classification: `BLOCKED`
- Evidence: no Backend, Deployment, or Database acknowledgement/approved scaffold commit exists.
- Impact: `CONTRACT-INTEGRATION-001` scaffold section cannot be finalized; DB-DEP-011 remains pending.
- Resolution: receive the three structured responses requested in `DEPENDENCY_REQUESTS.md`.

## INT-ISSUE-002 — Deployment contract is protected

- Classification: `BLOCKED`
- Evidence: `CONTRACT-DEPLOY-001` is owned by A2-DEPLOYMENT and no approved contribution exists.
- Rule: this task documents requirements only; it must not publish or approve deployment content.

## INT-ISSUE-003 — Auth and Workflow are separate DB-002 blockers

- Classification: `BLOCKED`
- Evidence: Database ledger requires draft `CONTRACT-AUTH-001` and `CONTRACT-WORKFLOW-001` before DB-002.
- Rule: DB-DEP-011 clearance alone does not make DB-002 ready.

## INT-ISSUE-004 — Manager-document revision mismatch

- Classification: `PARTIAL`
- Evidence: manager prompts reference earlier research filename suffixes; `SPECIFICATION_INDEX.md` designates the present files as working inputs.
- Resolution: Agent 1 confirms revision lineage before final acceptance.

## INT-ISSUE-005 — No versioned Integration contract

- Classification: `BLOCKED`
- Evidence: `CONTRACT-INTEGRATION-001` has coordination records only; no versioned contract file exists.
- Resolution: wait for the coordinated owner decision after all acknowledgements.

## INT-ISSUE-006 — No scaffold implementation

- Classification: `BLOCKED`
- Evidence: no application, environment, deployment, database, migration, or test scaffold commit exists.
- Resolution: await owner-specific scaffold commits; DB-002 must not begin.

## INT-ISSUE-007 — Database historical starting-commit wording

- Classification: `PARTIAL`
- Evidence: Database-owned records retain temporary historical starting-commit wording.
- Rule: Integration must not edit Database-owned files; reconcile that wording only through the Database owner.
