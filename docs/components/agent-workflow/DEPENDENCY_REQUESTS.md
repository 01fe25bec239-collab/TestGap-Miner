# Agent Workflow Dependency Requests

- Date: 2026-07-31
- Contract: `CONTRACT-WORKFLOW-001@1.0.0-draft.1`
- Current task: `AGW-DB002-CONTRACT-001-C2` (`BUG_FIX`)
- Starting-state evidence: the original task began clean with no Agent Workflow
  directory; C1 and C2 began with exactly seven permitted untracked Markdown
  files and no other changed path.

## `AGW-DEP-001` — A2-DATABASE contract acknowledgement

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
- Approval status: `PENDING`
- Completion evidence: none.
- Next action: A2-DATABASE review and acknowledgement.

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
- Approval status: `PENDING`
- Completion evidence: none.
- Next action: A2-AUTH publishes the versioned contract.

## `AGW-DEP-003` — Queue transport contract

- Request ID: `AGW-DEP-003`
- Requesting Agent 2: `A2-AGENT-WORKFLOW`
- Owning Agent 2: `A2-AGENT-WORKFLOW` under a separate authorized task
- Required change and reason: publish queue envelope, delivery identity,
  visibility/lease, redelivery, worker-result, and dead-letter semantics.
- Contract affected: `CONTRACT-QUEUE-001`
- Exact blocking task: transport-owned portion of DB-003 and worker integration.
- Backward-compatibility impact: high; transport uniqueness must not alter
  semantic run-request idempotency.
- Urgency: `MEDIUM`
- Proposed acceptance test: at-least-once duplicate delivery produces one
  semantic effect, bounded attempts, and attributable dead-letter outcome.
- Approval status: `PENDING`
- Completion evidence: none; intentionally not implemented in this task.
- Next action: issue a separate scoped contract prompt.

## Explicit labels

- `IMPLEMENTED`: dependency request record.
- `TESTED`: ownership and blocking-task references reconciled.
- `NOT_TESTED`: consumer/runtime behavior.
- `BLOCKED`: all three requests remain pending.
- `ASSUMED`: A2-AGENT-WORKFLOW retains Queue ownership per the shared registry,
  but a separate task is required.
