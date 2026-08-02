# Agent Workflow Decision Log

- Date: 2026-08-02
- Contract: `CONTRACT-WORKFLOW-001@1.0.0-draft.1` (`ACKNOWLEDGED_AND_MERGED`)
- Current task: `WORKFLOW-DB002-OWNER-RECONCILIATION-001-C1`
  (`DOCUMENTATION_RECONCILIATION_ONLY`)
- Evidence baseline: `d13e28117ca6266c3ab3ffa7775f63185ab74b3e`

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
- Documentation state: `VERIFIED_COMPLETE` / `MERGED` via PR #8, merge commit
  `7da1132b9e30b51a212aa6574c23e2a832d9a6fd`, 2026-07-31. The historical
  pre-merge documentation state recorded at the time of this decision is
  superseded by that merge.
- Semantic freeze: semantic commit `a7c83f4` is frozen; any semantic change
  invalidates the Database acknowledgement.
- Closure requirement: satisfied. Merge evidence was delivered and the Database
  reconciliation merged via PR #10, merge commit
  `99c8022c9f44e6a54bed624aa0153be7e32f234b`, 2026-08-01.
- Deferred: Queue, Evidence, and Security fields remain owned by their
  contracts; runtime implementation remains `NOT_IMPLEMENTED` / `NOT_TESTED`.
- Next action: none. Superseded by `AGW-DEC-011` through `AGW-DEC-015`.

## `AGW-DEC-011` — Semantic integrity preserved after DB-002 merge

- Status: `IMPLEMENTED`
- Decision: `SEMANTIC_INTEGRITY_PRESERVED` / `NO_SEMANTIC_CHANGE_REQUIRED`. The
  merged DB-002 implementation introduced no conflict with the normative
  Workflow body.
- Evidence: the normative semantic-section SHA-256 is
  `6aefc5730cfb9c6138231811e63570854b469813011f47765f98af0bc3fdfe37`, verified
  identical before and after this reconciliation.
- Version impact: none. The contract remains `1.0.0-draft.1`. No semantic
  version change and no semantic-body change is required.
- Next action: preserve the frozen semantic body in authorized downstream work.

## `AGW-DEC-012` — One current run projection per durable request

- Status: `IMPLEMENTED`
- Database issue: `DB-ISSUE-011`
- Decision: `ACCEPTED_WITH_DOCUMENTATION_CLARIFICATION`. The Database
  `runs.run_request_id` `UNIQUE` constraint is accepted. Exactly one current run
  projection exists per durable request. Regeneration creates a new request and
  a new run. DB-003 event history is not represented by duplicate runs.
- Evidence: contract `RECEIVED` definition, regeneration rules, and the merged
  DB-002 schema.
- Compatibility impact: none; this is physical enforcement of an existing
  contract meaning.
- Next action: changing this cardinality later requires Workflow consumer review
  and Database migration review.

## `AGW-DEC-013` — Failure codes remain family-checked, not frozen

- Status: `IMPLEMENTED`
- Database issue: `DB-ISSUE-012`
- Decision: `ACCEPTED_AS_COMPATIBLE`. Anchored uppercase failure-family patterns
  preserve additive-compatible failure codes, and the terminal state remains the
  compatibility boundary.
- Constraint: this MUST NOT be replaced with a frozen failure-code enumeration.
  A frozen list would make a run in a valid terminal state unstorable after a
  minor additive contract revision.
- Evidence: the failure-code taxonomy section and the merged DB-002 check
  constraint.
- Compatibility impact: none.
- Next action: preserve family-pattern enforcement in authorized downstream work.

## `AGW-DEC-014` — Terminal actor identity deferred to a typed contract

- Status: `IMPLEMENTED` for DB-002; `DEFERRED_NON_BLOCKING` thereafter
- Database issue: `DB-ISSUE-013`
- Workflow issue: `AGW-ISSUE-011`
- Decision: `ACCEPTED_FOR_DB002_DEFERRED_FOR_TYPED_CONTRACT`. The DB-002 bounded
  opaque `terminal_actor_id` storage is accepted. No Auth foreign key is frozen.
- Ownership: the future typed actor relationship remains open, deferred,
  nonblocking, and jointly owned by `A2-AUTH` and `A2-AGENT-WORKFLOW`.
- Evidence: the contract marks the Auth-owned human identity shape provisional;
  merged DB-002 stores bounded opaque text with a checked actor-type vocabulary.
- Compatibility impact: none. A future typed relationship is an additive
  migration.
- Next action: none required. Revisit only under a future jointly authorized
  Auth/Workflow task.

## `AGW-DEC-015` — DB-002 boundary accepted; DB-003 remains unauthorized

- Status: `IMPLEMENTED`
- Decision: `DB002_BOUNDARY_ACCEPTED`. DB-002 owns only the durable run request
  and the current run projection, as merged. DB-003 owns workflow steps,
  attempts, ordered events, and transition history.
- DB-003 state: `NOT_STARTED` / `NOT_AUTHORIZED`. This decision does not start,
  approve readiness for, or authorize DB-003.
- Runtime state: Workflow runtime remains `NOT_IMPLEMENTED` / `NOT_TESTED`.
- Contracts not created: `CONTRACT-QUEUE-001` and `CONTRACT-EVIDENCE-001`.
- Evidence: DB-002 merged via PR #12, merge commit
  `3701520e6d61e2bb80391e7af888d0d530bdb6c4`, 2026-08-02.
- Next action: a separate owner-authorized DB-003 readiness assessment.

## Explicit labels

- `IMPLEMENTED`: decisions encoded in the draft contract, plus the post-merge
  owner decisions `AGW-DEC-011` through `AGW-DEC-015`.
- `TESTED`: internal references, invariants, and the frozen semantic-section
  hash documentation-validated.
- `NOT_TESTED`: runtime enforcement.
- `BLOCKED`: nothing. DB-003, runtime, Queue, and Evidence work are
  `NOT_AUTHORIZED`; `AGW-DEC-014` is deferred and nonblocking.
- `ASSUMED`: initial baseline reconciliation in `AGW-DEC-007`; merge evidence
  read from local `origin/main` history rather than from the GitHub API.
