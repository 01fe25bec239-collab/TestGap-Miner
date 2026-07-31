# Agent Workflow Decision Log

- Date: 2026-07-31
- Contract: `CONTRACT-WORKFLOW-001@1.0.0-draft.1`
- Current task: `AGW-DB002-CONTRACT-001-C3-C1` (`BUG_FIX`)

## `AGW-DEC-001` — Canonical lifecycle is closed and explicit

- Status: `IMPLEMENTED`
- Decision: preserve the manager's exact 20-state enumeration and allow only
  the listed lifecycle transitions, including the single bounded repair loop.
  The eight terminal states have no outgoing transitions.
- Evidence: canonical-state and transition sections in the contract.
- Next action: preserve the acknowledged enum and constraints in authorized
  downstream work.

## `AGW-DEC-002` — Repair is semantic and single-use

- Status: `IMPLEMENTED`
- Decision: entering `REPAIRING` atomically consumes the sole repair allowance;
  either execution state may enter repair, repaired output returns to buggy
  execution as the only non-terminal continuation and repeats buggy then fixed
  execution. Five terminal safety exits are permitted; none authorizes another
  repair.
- Evidence: lifecycle counter, transition, retry/repair, and fixture sections.
- Next action: DB-002/DB-003 later enforce counter/event constraints.

## `AGW-DEC-003` — DB-002 projection is separate from DB-003 history

- Status: `IMPLEMENTED`
- Decision: DB-002 owns immutable requests and current run projection; DB-003
  owns steps, attempts, append-only events, and ordering.
- Evidence: projection and ordered-event sections.
- Next action: A2-DATABASE maps physical schema without collapsing history
  into mutable DB-002 rows.

## `AGW-DEC-004` — External identifiers never become internal UUIDs

- Status: `IMPLEMENTED`
- Decision: GitHub IDs/GUIDs, SHAs, benchmark IDs, model/provider IDs, and
  future queue IDs remain separate from internal UUIDs. GitHub and benchmark
  semantic idempotency use the manager-required compositions.
- Evidence: identifier and idempotency sections.
- Next action: Database acknowledges uniqueness scope and canonical encoding.

## `AGW-DEC-005` — Regeneration creates a new run

- Status: `IMPLEMENTED`
- Decision: human-requested regeneration completes the reviewed run and creates
  a new idempotent run linked by internal `parent_run_id`; it never moves
  backward or resets the repair counter.
- Evidence: transition and human-review sections.
- Next action: future Evidence/DB-005 work defines the full human-decision
  record without changing this lifecycle rule.

## `AGW-DEC-006` — Lifecycle payloads are metadata-only

- Status: `IMPLEMENTED`
- Decision: events/checkpoints carry bounded, redacted metadata or opaque
  evidence references; raw secrets, prompts, repository bytes, patch bytes,
  and logs are forbidden.
- Evidence: safety, event, and checkpoint sections.
- Next action: Security/Evidence consumers preserve or strengthen this rule.

## `AGW-DEC-007` — Baseline source reconciliation

- Status: `ASSUMED`
- Non-breaking correction recorded: no standalone A2 draft file existed at the
  verified base, so the authoritative manager enumeration, `DB-DEP-004`, and
  issued task requirements were reconciled into the first versioned draft.
- Compatibility impact: none; this creates the initial contract.
- Next action: semantic corrections must be recorded and versioned.

## `AGW-DEC-008` — Review completion and late cancellation

- Status: `IMPLEMENTED`
- Decision: successful review-required runs reach human review before
  completion. Only an explicitly configured no-review benchmark may complete
  from scoring or publishing after durable evidence packaging and with system
  attribution. Human review accepts disposition-to-completion only; late
  cancellation is recorded as not applied.
- Evidence: corrected transition, cancellation, human-review, and fixture
  sections; C2 invariant output in the latest handoff preserves the C1 paths.
- Blocker: runtime enforcement is `NOT_TESTED`.
- Next action: preserve these acknowledged lifecycle constraints.

## `AGW-DEC-009` — Repair terminal exits and publication boundary

- Status: `IMPLEMENTED`
- Decision: repair may safely terminate as abstained, model failure,
  infrastructure failure, security failure, or cancellation. Publishing may
  cancel only before an external review artefact or publication side effect
  commits; a later request is recorded as not applied.
- Evidence: C2 transition, repair, cancellation, and fixture sections plus the
  latest invariant output.
- Starting-state evidence: original task clean/no directory; C1 and C2 exactly
  seven permitted untracked Markdown files and no other changed path.
- Blocker: runtime enforcement is `NOT_TESTED`.
- Next action: preserve the acknowledged lifecycle contract.

## `AGW-DEC-010` — Database acknowledgement accepted

- Status: `IMPLEMENTED` and documentation-`TESTED`
- Decision: record `DB-WORKFLOW-CONTRACT-ACK-001` as
  `ACCEPTED_WITH_NONBREAKING_CLARIFICATIONS` for the exact semantic commit
  `a7c83f4`. Database-owned text constraints, state/version compare-and-swap,
  versioned bounded request idempotency, and DB-002/DB-003 physical ownership
  preserve the Workflow contract.
- Evidence: the acknowledgement section in the contract and the C3 handoff.
- Compatibility impact: none; no Workflow-owned semantic changed.
- Documentation state: `VERIFIED_COMPLETE_PENDING_MERGE`.
- Semantic freeze: semantic commit `a7c83f4` is frozen; any semantic change
  invalidates the Database acknowledgement.
- Closure requirement: merge evidence is still required before downstream
  closure.
- Blocker: Auth, Queue, Evidence, and Security fields remain deferred to their
  owner contracts; runtime implementation is `NOT_TESTED`.
- Next action: A2-AGENT-WORKFLOW merges the verified seven-file documentation
  set and sends merge evidence to A2-DATABASE; keep DB-002/DB-003
  implementation outside this task.

## Explicit labels

- `IMPLEMENTED`: decisions encoded in the draft contract.
- `TESTED`: internal references and invariants documentation-validated.
- `NOT_TESTED`: runtime enforcement.
- `BLOCKED`: Auth/Queue dependencies and downstream implementation.
- `ASSUMED`: initial baseline reconciliation in `AGW-DEC-007`.
