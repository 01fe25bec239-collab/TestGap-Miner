# Agent Workflow Open Issues

- Date: 2026-08-02
- Contract: `CONTRACT-WORKFLOW-001@1.0.0-draft.1` (`ACKNOWLEDGED_AND_MERGED`)
- Current task: `WORKFLOW-DB002-OWNER-RECONCILIATION-001-C1`
  (`DOCUMENTATION_RECONCILIATION_ONLY`)
- Evidence baseline: `d13e28117ca6266c3ab3ffa7775f63185ab74b3e`

## Current blockers

None. The Workflow contract is merged, `DB-DEP-011` is closed, and DB-002 is
merged. Remaining items are either deferred and nonblocking, or unauthorized
future owner work; both are listed separately below.

## Closed Database consumer issues — Workflow owner decisions

These three Database-raised issues are dispositioned here by the Workflow
owner. The Database-side records remain owned by A2-DATABASE and were not
modified by this task.

### `DB-ISSUE-011` — One run per run request

- Status: `CLOSED`
- Workflow decision: `ACCEPTED_WITH_DOCUMENTATION_CLARIFICATION`
- Clarification: the `runs.run_request_id` `UNIQUE` constraint is accepted. One
  current run projection exists per durable request. Regeneration creates a new
  request and a new run. DB-003 event history is not represented by duplicate
  runs.
- Compatibility impact: none; this is the physical enforcement of an existing
  contract meaning. No semantic change is required.

### `DB-ISSUE-012` — Failure codes checked by family

- Status: `CLOSED`
- Workflow decision: `ACCEPTED_AS_COMPATIBLE`
- Clarification: anchored uppercase failure-family patterns preserve
  additive-compatible failure codes, and the terminal state remains the
  compatibility boundary. This MUST NOT be replaced with a frozen failure-code
  enumeration.
- Compatibility impact: none; a frozen enumeration would break the contract's
  additive-code allowance.

## Closed acknowledgement issues

### `AGW-ISSUE-001` — A2-DATABASE acknowledgement

- Status: `CLOSED`
- Resolution: `DB-WORKFLOW-CONTRACT-ACK-001` accepted semantic commit
  `a7c83f4` with decision
  `ACCEPTED_WITH_NONBREAKING_CLARIFICATIONS`.
- Evidence: contract acknowledgement and Database physical-mapping note.

### `AGW-ISSUE-006` — DB-002 versus DB-003 ownership ambiguity

- Status: `CLOSED`
- Resolution: DB-002 owns only `run_requests` and `runs`; DB-003 owns workflow
  steps, attempts, run events, ordering, producer-event idempotency, and
  transition history.
- Evidence: accepted contract acknowledgement.

### `AGW-ISSUE-007` — Database physical enum-storage ambiguity

- Status: `CLOSED`
- Resolution: `RunState` and request kind use text with Database-owned check
  constraints; terminal codes use versioned text with state-shape constraints.
- Evidence: accepted non-normative Database physical mappings.

### `AGW-ISSUE-002` — Independent Auth prerequisite for DB-002

- Status: `CLOSED`
- Resolution: `CONTRACT-AUTH-001` was published and accepted, and DB-002 was
  implemented and merged against it. The Auth prerequisite and the merge/state
  synchronization that previously gated DB-002 are both satisfied.
- Evidence: DB-002 merged via PR #12, merge commit
  `3701520e6d61e2bb80391e7af888d0d530bdb6c4`, 2026-08-02.
- Note: the separate typed actor identity shape remains open as
  `AGW-ISSUE-011`; it is deferred and nonblocking.

## Open deferred, nonblocking issues

These do not block any merged or authorized work.

### `AGW-ISSUE-011` — Typed terminal actor relationship (`DB-ISSUE-013`)

- Status: `OPEN`
- Classification: `DEFERRED_NON_BLOCKING`
- Owners: `A2-AGENT-WORKFLOW` and `A2-AUTH` jointly
- Workflow decision: `ACCEPTED_FOR_DB002_DEFERRED_FOR_TYPED_CONTRACT`
- Evidence: DB-002 stores `terminal_actor_id` as bounded opaque text with no
  Auth foreign key, and checks `terminal_actor_type` against the Workflow actor
  vocabulary `SYSTEM` / `WORKFLOW` / `WORKER` / `HUMAN`.
- Disposition: the DB-002 representation is accepted. No Auth foreign key is
  frozen. A future joint Auth/Workflow contract may introduce a typed actor
  relationship through an additive migration.
- Next action: none required. Revisit only under a future jointly authorized
  Auth/Workflow task.

## Unauthorized future owner work

These are not blockers and not open defects. None is authorized by this task.

### `AGW-ISSUE-003` — Queue contract not authorized

- Status: `OPEN`
- Classification: `NOT_AUTHORIZED`
- Evidence: transport fields remain owned by `CONTRACT-QUEUE-001`, which was
  not created here.
- Next action: complete a separate owner-authorized Queue contract task.

### `AGW-ISSUE-004` — Workflow runtime not implemented

- Status: `OPEN`
- Classification: `NOT_IMPLEMENTED` / `NOT_TESTED` / `NOT_AUTHORIZED`
- Evidence: no workflow engine or runtime behavior exists.
- Next action: begin only under a future authorized implementation task.

### `AGW-ISSUE-008` — Evidence contract not authorized

- Status: `OPEN`
- Classification: `NOT_AUTHORIZED`
- Evidence: Evidence payload fields remain owned by `CONTRACT-EVIDENCE-001`,
  which was not created here.
- Next action: the Evidence owner publishes its contract.

### `AGW-ISSUE-009` — Security contract pending

- Status: `OPEN`
- Classification: `NOT_AUTHORIZED`
- Evidence: Security payload fields remain owned by `CONTRACT-SEC-001`.
- Next action: the Security owner publishes its contract.

### `AGW-ISSUE-010` — Runtime acceptance fixtures not tested

- Status: `OPEN`
- Classification: `NOT_TESTED` / `NOT_AUTHORIZED`
- Evidence: documentation defines fixtures but this task forbids runtime tests.
- Next action: authorized runtime implementation tasks add and run them.

### `AGW-ISSUE-012` — DB-003 not started and not authorized

- Status: `OPEN`
- Classification: `NOT_STARTED` / `NOT_AUTHORIZED`
- Evidence: DB-003 owns workflow steps, attempts, ordered events, and
  transition history. The DB-002 versus DB-003 boundary is recorded as
  `DB002_BOUNDARY_ACCEPTED`.
- Next action: a separate owner-authorized DB-003 readiness assessment. This
  task neither starts nor authorizes DB-003.

## Closed baseline note

### `AGW-ISSUE-005` — Standalone manager draft absent

- Status: `CLOSED`
- Classification: `ASSUMED`
- Resolution: the authoritative manager, `DB-DEP-004`, and task requirements
  formed the recorded initial baseline.

## Explicit labels

- `IMPLEMENTED`: acknowledgement, ambiguity resolutions, and post-merge owner
  decisions recorded.
- `TESTED`: documentation evidence and frozen semantic body validated.
- `NOT_TESTED`: workflow runtime and acceptance fixtures.
- `BLOCKED`: nothing. Queue, Evidence, Security, DB-003, and runtime work are
  `NOT_AUTHORIZED` rather than blocked; `AGW-ISSUE-011` is deferred and
  nonblocking.
- `ASSUMED`: closed initial baseline reconciliation; merge evidence read from
  local `origin/main` history rather than from the GitHub API.
