# Agent Workflow Open Issues

- Date: 2026-07-31
- Contract: `CONTRACT-WORKFLOW-001@1.0.0-draft.1`
- Current task: `AGW-DB002-CONTRACT-001-C3-C1` (`BUG_FIX`)

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

## Open future issues

### `AGW-ISSUE-002` — Independent Auth prerequisite

- Status: `OPEN`
- Classification: `BLOCKED`
- Evidence: `CONTRACT-AUTH-001` remains an independent DB-002 prerequisite.
- Scope: this is not a defect in `CONTRACT-WORKFLOW-001`.
- Next action: A2-AUTH publishes its owned identity contract.

### `AGW-ISSUE-003` — Queue contract pending

- Status: `OPEN`
- Classification: `BLOCKED`
- Evidence: transport fields remain owned by `CONTRACT-QUEUE-001`.
- Next action: complete a separate owner-authorized Queue contract task.

### `AGW-ISSUE-004` — Workflow runtime not started

- Status: `OPEN`
- Classification: `NOT_TESTED`
- Evidence: no workflow engine or runtime behavior was implemented.
- Next action: begin only under a future authorized implementation task.

### `AGW-ISSUE-008` — Evidence contract pending

- Status: `OPEN`
- Classification: `BLOCKED`
- Evidence: Evidence payload fields remain owned by `CONTRACT-EVIDENCE-001`.
- Next action: the Evidence owner publishes its contract.

### `AGW-ISSUE-009` — Security contract pending

- Status: `OPEN`
- Classification: `BLOCKED`
- Evidence: Security payload fields remain owned by `CONTRACT-SEC-001`.
- Next action: the Security owner publishes its contract.

### `AGW-ISSUE-010` — Runtime acceptance fixtures not tested

- Status: `OPEN`
- Classification: `NOT_TESTED`
- Evidence: documentation defines fixtures but this task forbids runtime tests.
- Next action: authorized runtime implementation tasks add and run them.

## Closed baseline note

### `AGW-ISSUE-005` — Standalone manager draft absent

- Status: `CLOSED`
- Classification: `ASSUMED`
- Resolution: the authoritative manager, `DB-DEP-004`, and task requirements
  formed the recorded initial baseline.

## Explicit labels

- `IMPLEMENTED`: acknowledgement and ambiguity resolutions recorded.
- `TESTED`: documentation evidence and frozen semantic body validated.
- `NOT_TESTED`: workflow runtime and acceptance fixtures.
- `BLOCKED`: Auth, Queue, Evidence, and Security owner work.
- `ASSUMED`: closed initial baseline reconciliation.
