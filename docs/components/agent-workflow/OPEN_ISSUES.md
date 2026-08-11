# Agent Workflow Open Issues

- Date: 2026-08-11
- Contract: `CONTRACT-WORKFLOW-001@1.0.0-draft.1` (`ACKNOWLEDGED_AND_MERGED`)
- Current task: `WORKFLOW-003-POST-PR40-CURRENT-MAIN-VALIDATION-001`
- Authorized baseline: `2fe29e466b1c84799ef0d6d6d28fbcadb572c964`
- Reconciled base: `6b5485368367064e7f36b5837f49734425f284ee`

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

### `AGW-ISSUE-003` — Queue runtime/provider integration not implemented

- Status: `OPEN`
- Classification: `CONTRACT_EXISTS` / `RUNTIME_NOT_IMPLEMENTED_BY_WORKFLOW_002`
- Ownership: `CONTRACT-QUEUE-001` and Queue runtime/provider integration belong
  to A2-QUEUE. Workflow is a semantic consumer, not the Queue owner.
- Evidence: `CONTRACT-QUEUE-001` exists on the authorized baseline.
- Next action: any Queue runtime/provider work requires a separate
  owner-authorized integration task.

### `AGW-ISSUE-004` — Full Workflow runtime not implemented

- Status: `OPEN`
- Classification: `PURE_LIFECYCLE_FOUNDATION_IMPLEMENTED` /
  `DB003_PERSISTENCE_INTEGRATION_A2_ACCEPTED` /
  `EXTERNAL_RUNTIME_NOT_IMPLEMENTED`
- Evidence: WORKFLOW-002 pure lifecycle foundation is `PASS` / `MERGED` /
  `A2_ACCEPTED`; WORKFLOW-003 lifecycle-transition persistence is `IMPLEMENTED`
  / `TESTED` / `A2_ACCEPTED`; DB-003 is `PASS` / `MERGED`.
- Not implemented: Queue, Execution, Evidence, RAG/localisation,
  model/provider, publication, API routes, `WorkflowStep`,
  `WorkflowStepAttempt`, persistent retry scheduling, checkpoint storage, and
  regeneration child-run orchestration.
- Next action: open external integrations only under separately authorized
  owner tasks.

### `AGW-ISSUE-008` — Evidence runtime/persistence not implemented

- Status: `OPEN`
- Classification: `CONTRACT_EXISTS` / `RUNTIME_NOT_IMPLEMENTED_BY_WORKFLOW_002`
- Ownership: `CONTRACT-EVIDENCE-001` and Evidence semantics belong to
  A2-EVIDENCE. Workflow consumes the relevant semantic boundary.
- Evidence: `CONTRACT-EVIDENCE-001` exists on the authorized baseline.
- Next action: any Evidence runtime or persistence work requires a separate
  owner-authorized integration task.

### `AGW-ISSUE-009` — Security contract pending (historical)

- Status: `HISTORICAL` / `NOT_A_CURRENT_STATE_ASSERTION`
- Supersession note: the C1 correction did not infer or reconcile the current
  Security contract state, and C2 does not change that boundary. The earlier
  pending statement is retained only as historical coordination evidence.

### `AGW-ISSUE-010` — External acceptance fixtures not implemented

- Status: `OPEN`
- Classification: `PURE_SEMANTIC_FIXTURES_TESTED` /
  `EXTERNAL_OWNER_OR_FUTURE_INTEGRATION_REQUIRED`
- Evidence: pure semantics cover `successful_human_review`,
  `single_repair_success`, `repair_terminal_exits`, `second_repair_rejected`,
  `explicit_abstention`, `cooperative_cancellation`,
  `invalid_and_terminal_transitions`, `checkpoint_resume`, and
  `benchmark_system_completion`.
- Implemented by WORKFLOW-003: ordered durable transition insertion,
  producer-event idempotency consumption, redacted bounded Workflow metadata,
  event/projection atomicity, and projection CAS.
- Not implemented: external Queue, Execution, Evidence, publication, and API
  acceptance fixtures or Evidence byte handling.
- Next action: external owners add integration fixtures under separate tasks.

### `AGW-ISSUE-012` — DB-003 merged; Workflow integration implemented

- Status: `CLOSED` / `SUPERSEDED_BY_WORKFLOW_003`
- Classification: DB-003 `IMPLEMENTED` / `MERGED_BY_A2_DATABASE`; Workflow
  integration `IMPLEMENTED` / `TESTED` / `A2_ACCEPTED` /
  `READY_FOR_GIT_LIFECYCLE`
- Evidence: DB-003 workflow persistence was implemented and merged to main via PR #37 (`6eb622cf429093f3806dbe0261c3fa86cad607b6`). Active wording describing DB-003 as `NOT_STARTED` or `NOT_AUTHORIZED` is superseded.
- Distinction: WORKFLOW-002 remains the unchanged pure lifecycle foundation.
  WORKFLOW-003 adds only lifecycle transition persistence through DB-003;
  step/attempt orchestration and checkpoint persistence remain unimplemented.

## Closed baseline note

### `AGW-ISSUE-005` — Standalone manager draft absent

- Status: `CLOSED`
- Classification: `ASSUMED`
- Resolution: the authoritative manager, `DB-DEP-004`, and task requirements
  formed the recorded initial baseline.

## Explicit labels

- `IMPLEMENTED`: pure Workflow lifecycle foundation, WORKFLOW-003 DB-003
  transition persistence integration, and prior contract records.
- `TESTED`: pure semantics, real PostgreSQL persistence integration, Database
  regressions, and API regressions.
- `A2_ACCEPTED`: WORKFLOW-002 pure foundation, WORKFLOW-003, C1, and C2.
- `NOT_TESTED`: unauthorized external runtime integrations.
- `BLOCKED`: none in the authorized pure-core scope; remaining work is
  deferred or unauthorized.
- `ASSUMED`: none for the current task.
