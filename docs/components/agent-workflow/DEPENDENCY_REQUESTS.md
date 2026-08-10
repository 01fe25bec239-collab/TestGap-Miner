# Agent Workflow Dependency Requests

- Date: 2026-08-10
- Contract: `CONTRACT-WORKFLOW-001@1.0.0-draft.1` (`ACKNOWLEDGED_AND_MERGED`)
- Current task: `WORKFLOW-002-DB003-POSTMERGE-STATUS-RECONCILIATION-001`
  (`DOCUMENTATION_STATUS_RECONCILIATION_ONLY`)
- Original authorized implementation baseline: `f318d9b515a4324b0848e64059f179027d19bd1f`
- Reconciled current-main base: `6eb622cf429093f3806dbe0261c3fa86cad607b6`
- Historical starting-state evidence (superseded, retained as evidence): the
  original task began clean with no Agent Workflow directory; C1 and C2 began
  with exactly seven permitted untracked Markdown files and no other changed
  path.

## `AGW-DEP-001` / `DB-DEP-004` — A2-DATABASE contract acknowledgement

- Request ID: `AGW-DEP-001`
- Requesting Agent 2: `A2-AGENT-WORKFLOW`
- Owning Agent 2: `A2-DATABASE`
- Required change and reason: acknowledge the exact Workflow contract version
  and record how DB-002/DB-003 will preserve its projections, transitions,
  counters, review-required flag, event uniqueness, attribution, and fixtures.
- Contract affected: `CONTRACT-WORKFLOW-001`
- Exact blocking task: closure of `DB-DEP-004`; DB-002 run lifecycle and DB-003
  persistence planning.
- Backward-compatibility impact: high; enum rename/removal, transition changes,
  or idempotency changes require a versioned response and coordinated migration.
- Urgency: `HIGH`
- Proposed acceptance test: A2-DATABASE records all acknowledgement items,
  including two repair-entry sources, the repaired buggy-then-fixed sequence,
  one non-terminal repair continuation, five terminal repair exits,
  review-required/no-review completion, and side-effect-aware cancellation,
  while mapping DB-002 versus DB-003 without semantic conflict.
- Approval status: `ACCEPTED_WITH_NONBREAKING_CLARIFICATIONS`
- Producer status: `PRODUCER_COMPLETE`
- Consumer status: `CONSUMER_ACCEPTED`
- Merge status: `MERGED`
- Request status: `CLOSED`
- Consumer decision: `ACCEPTED_WITH_NONBREAKING_CLARIFICATIONS`
- Semantic commit: `a7c83f4`
- Contract version: `1.0.0-draft.1`
- Completion evidence: `DB-WORKFLOW-CONTRACT-ACK-001`, dated 2026-07-31,
  accepts `CONTRACT-WORKFLOW-001@1.0.0-draft.1` at semantic commit `a7c83f4`.
- Merge evidence: Workflow PR #8, merge commit
  `7da1132b9e30b51a212aa6574c23e2a832d9a6fd`, 2026-07-31; Database
  Workflow-reconciliation PR #10, merge commit
  `99c8022c9f44e6a54bed624aa0153be7e32f234b`, 2026-08-01.
- Downstream consumption: DB-002 merged via PR #12, merge commit
  `3701520e6d61e2bb80391e7af888d0d530bdb6c4`, 2026-08-02; DB-003 merged via PR #37 (`6eb622cf429093f3806dbe0261c3fa86cad607b6`), 2026-08-10. `DB-DEP-011` is
  `ACCEPTED` / `VERIFIED_COMPLETE` / `CLOSED`.
- Next action: none. This dependency is complete.

## `AGW-DEP-004` — Typed terminal actor relationship (open)

- Request ID: `AGW-DEP-004`
- Requesting Agent 2: `A2-AGENT-WORKFLOW`
- Owning Agent 2: `A2-AUTH` and `A2-AGENT-WORKFLOW` jointly
- Related issues: `AGW-ISSUE-011`, `DB-ISSUE-013`
- Required change and reason: define a typed actor relationship for terminal
  attribution so `terminal_actor_id` need not remain bounded opaque text.
- Contract affected: a future joint Auth/Workflow revision.
- Workflow decision recorded for DB-002:
  `ACCEPTED_FOR_DB002_DEFERRED_FOR_TYPED_CONTRACT`.
- Exact blocking task: none. This is deferred and nonblocking; DB-002 merged
  without it and no Auth foreign key is frozen.
- Backward-compatibility impact: low; a typed relationship is expected to be an
  additive migration.
- Urgency: `LOW`
- Proposed acceptance test: terminal attribution resolves to a typed actor
  without overloading internal UUIDs or storing secrets.
- Approval status: `OPEN` / `DEFERRED_NON_BLOCKING`
- Completion evidence: none.
- Next action: none required. Revisit only under a future jointly authorized
  Auth/Workflow task. Not authorized here.

## `AGW-DEP-002` — Auth identity contract

- Request ID: `AGW-DEP-002`
- Requesting Agent 2: `A2-AGENT-WORKFLOW`
- Owning Agent 2: `A2-AUTH`
- Required change and reason: publish authenticated requester/human actor
  identity and GitHub installation context so attribution fields cease to be
  provisional.
- Contract affected: `CONTRACT-AUTH-001`
- Exact blocking task: DB-002 identity fields and future human-review records.
- Backward-compatibility impact: high; internal UUID and external subject/
  installation identifiers must remain separate.
- Urgency: `HIGH`
- Proposed acceptance test: fixtures attribute a request, cancellation, and
  human decision without storing secrets or overloading UUIDs.
- Approval status: `SATISFIED_FOR_DB002`
- Completion evidence: `CONTRACT-AUTH-001` was published and accepted, and
  DB-002 was implemented and merged against it via PR #12, merge commit
  `3701520e6d61e2bb80391e7af888d0d530bdb6c4`, 2026-08-02. The Auth prerequisite
  no longer blocks DB-002.
- Remaining open scope: the typed terminal actor relationship only, tracked
  separately as `AGW-DEP-004` / `AGW-ISSUE-011`, deferred and nonblocking.
- Next action: none for DB-002. Future human-review records are covered by
  `AGW-DEP-004`.

## `AGW-DEP-003` — Queue transport contract

- Request ID: `AGW-DEP-003`
- Requesting Agent 2: `A2-AGENT-WORKFLOW`
- Owning Agent 2: `A2-QUEUE`
- Required change and reason: publish queue envelope, delivery identity,
  visibility/lease, redelivery, worker-result, and dead-letter semantics.
- Contract affected: `CONTRACT-QUEUE-001`
- Exact blocking task: transport-owned portion of DB-003 and worker integration.
- Backward-compatibility impact: high; transport uniqueness must not alter
  semantic run-request idempotency.
- Urgency: `MEDIUM`
- Proposed acceptance test: at-least-once duplicate delivery produces one
  semantic effect, bounded attempts, and attributable dead-letter outcome.
- Contract layer: `SATISFIED` / `CONTRACT_EXISTS`.
- Contract evidence: `CONTRACT-QUEUE-001` exists on the authorized baseline
  and remains owned by A2-QUEUE.
- Queue runtime/provider integration:
  `NOT_AUTHORIZED_BY_WORKFLOW_002` /
  `SEPARATE_OWNER_AUTHORIZATION_REQUIRED`.
- Next action: any runtime/provider integration requires a separate
  owner-authorized task.

## Ownership boundaries

- `CONTRACT-AUTH-001`: owned by `A2-AUTH`.
- `CONTRACT-QUEUE-001`: exists and is owned by `A2-QUEUE`; Workflow is a
  semantic consumer.
- `CONTRACT-EVIDENCE-001`: exists and is owned by `A2-EVIDENCE`; Workflow is a
  consumer of the relevant semantic boundary.
- `CONTRACT-SEC-001`: owned by `A2-SECURITY`.

WORKFLOW-002 implements neither Queue runtime/provider integration nor Evidence
runtime/persistence. This reconciliation changes no cross-owner contract.

## Explicit labels

- `IMPLEMENTED`: dependency request records reconciled to merged state.
- `TESTED`: ownership, merge evidence, and blocking-task references reconciled.
- `NOT_TESTED`: consumer/runtime behavior.
- `BLOCKED`: nothing. `AGW-DEP-001` is complete and closed; `AGW-DEP-002` is
  satisfied for DB-002; the `AGW-DEP-003` contract layer is satisfied while
  Queue runtime/provider integration requires separate owner authorization;
  `AGW-DEP-004` is deferred and nonblocking.
- `ASSUMED`: none for this current-state correction.
