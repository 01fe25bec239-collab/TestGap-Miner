# Agent Workflow Open Issues

- Date: 2026-07-31
- Contract: `CONTRACT-WORKFLOW-001@1.0.0-draft.1`
- Current task: `AGW-DB002-CONTRACT-001-C2` (`BUG_FIX`)

## `AGW-ISSUE-001` — Database acknowledgement pending

- Classification: `BLOCKED`
- Evidence: the contract is marked
  `DRAFT_COMPLETE — PENDING_A2_DATABASE_ACKNOWLEDGEMENT`; no consumer
  acknowledgement exists in this worktree.
- Impact: the draft satisfies the Workflow side of `DB-DEP-004`, but DB-002
  and DB-003 cannot claim the contract is acknowledged.
- Next action: A2-DATABASE records the six acknowledgement items stated in the
  contract.

## `AGW-ISSUE-002` — Auth-owned identity shape pending

- Classification: `BLOCKED`
- Evidence: Database records identify `CONTRACT-AUTH-001` as an independent
  DB-002 prerequisite.
- Impact: human/requester actor identity fields are deliberately provisional.
- Next action: A2-AUTH publishes the versioned identity contract; Workflow and
  Database map it without overloading internal UUIDs.

## `AGW-ISSUE-003` — Queue transport contract pending

- Classification: `BLOCKED`
- Evidence: queue envelope, lease, redelivery, and message identity are
  explicitly outside this contract and owned by `CONTRACT-QUEUE-001`.
- Impact: the lifecycle contract defines semantic idempotency and retries but
  does not freeze transport fields.
- Next action: issue a separate owner-authorized Queue contract task before
  DB-003 freezes transport-related persistence.

## `AGW-ISSUE-004` — No runtime validation

- Classification: `NOT_TESTED`
- Evidence: this task created documentation only and forbade runtime tests,
  workflow-engine code, ORM models, migrations, routes, and workers.
- Impact: contract validation does not prove runtime behavior.
- Next action: authorized implementation tasks later add the required
  acceptance fixtures and execute them.

## `AGW-ISSUE-005` — Standalone manager draft absent

- Classification: `ASSUMED`
- Evidence: no pre-existing Agent Workflow directory or separate
  `CONTRACT-WORKFLOW-001` draft was found at the verified base.
- Impact: the substantive baseline was reconstructed from the authoritative
  manager, `DB-DEP-004`, and the issued task requirements.
- Next action: A2-AGENT-WORKFLOW confirms this is the intended complete draft
  during review; any semantic correction requires a recorded version change.

## Resolved by `AGW-DB002-CONTRACT-001-C1`

- Classification: `IMPLEMENTED` and documentation-`TESTED`
- Evidence: the transition table and invariant checks now permit repair from
  both execution states, require repair to restart buggy execution, require
  human review when configured, permit explicit no-review benchmark system
  completion, and reject late cancellation from human review.
- Blocker: runtime enforcement remains `NOT_TESTED`; A2-DATABASE
  acknowledgement remains `BLOCKED`.
- Next action: A2-DATABASE reviews the corrected draft semantics.

## Resolved by `AGW-DB002-CONTRACT-001-C2`

- Classification: `IMPLEMENTED` and documentation-`TESTED`
- Evidence: `REPAIRING` retains buggy execution as its sole non-terminal
  continuation and permits exactly five terminal safety exits; publication
  cancellation is qualified by external-side-effect commit.
- Starting-state evidence: the original task began clean with no Agent Workflow
  directory; C1 and C2 began with exactly seven permitted untracked Markdown
  files and no other changed path.
- Blocker: runtime enforcement remains `NOT_TESTED`; A2-DATABASE
  acknowledgement remains `BLOCKED`.
- Next action: A2-DATABASE reviews the final corrected draft.

## Explicit labels

- `IMPLEMENTED`: issue tracking record.
- `TESTED`: repository evidence references checked.
- `NOT_TESTED`: runtime and persistence behavior.
- `BLOCKED`: acknowledgement, Auth, and Queue consumer work.
- `ASSUMED`: baseline source described in `AGW-ISSUE-005`.
