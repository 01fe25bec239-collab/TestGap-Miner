# Agent Workflow Decision Log

- Date: 2026-08-10
- Contract: `CONTRACT-WORKFLOW-001@1.0.0-draft.1` (`ACKNOWLEDGED_AND_MERGED`)
- Current task: `WORKFLOW-002-DB003-POSTMERGE-STATUS-RECONCILIATION-001`
  (`DOCUMENTATION_STATUS_RECONCILIATION_ONLY`)
- Original authorized implementation baseline: `f318d9b515a4324b0848e64059f179027d19bd1f`
- Reconciled current-main base: `6eb622cf429093f3806dbe0261c3fa86cad607b6`

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
- Runtime evidence: pure lifecycle enforcement is tested by
  `WORKFLOW-002-LIFECYCLE-RUNTIME-FOUNDATION-001`; external integration remains
  unimplemented.
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
- Runtime evidence: pure lifecycle enforcement is tested by
  `WORKFLOW-002-LIFECYCLE-RUNTIME-FOUNDATION-001`; external integration remains
  unimplemented.
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
- Deferred: Queue and Evidence fields remain owned by their respective
  contracts. Security fields remain owner-controlled; this correction makes no
  current Security-contract state claim. The pure lifecycle foundation is
  implemented by `AGW-DEC-016`; external runtime integration remains
  unimplemented.
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

## `AGW-DEC-015` — DB-002 boundary accepted; DB-003 status updated post-PR #37

- Status: `IMPLEMENTED`
- Decision: `DB002_BOUNDARY_ACCEPTED`. DB-002 owns only the durable run request
  and the current run projection, as merged. DB-003 owns workflow steps,
  attempts, ordered events, and transition history.
- DB-003 state: `IMPLEMENTED` / `MERGED_BY_A2_DATABASE` (merged via PR #37). WORKFLOW-002 DB-003 integration: `NOT_IMPLEMENTED_BY_WORKFLOW_002`.
- Runtime state: superseded in part by `AGW-DEC-016`; the pure lifecycle
  foundation is implemented, while the full integrated runtime remains
  unimplemented.
- Historical state recorded by this decision: `CONTRACT-QUEUE-001` and
  `CONTRACT-EVIDENCE-001` were not created at that time. `SUPERSEDED` for
  current-state use: both contracts exist on the authorized `f318d9b...`
  baseline; ownership remains with A2-QUEUE and A2-EVIDENCE respectively.
- Evidence: DB-002 merged via PR #12; DB-003 merged via PR #37 (`6eb622cf429093f3806dbe0261c3fa86cad607b6`).
- Next action: future WORKFLOW-002 DB-003 integration task.

## `AGW-DEC-016` — Pure lifecycle foundation is deterministic and isolated

- Status: `IMPLEMENTED` / `TESTED` / `A2_ACCEPTED` / `READY_FOR_GIT_LIFECYCLE`
- Decision: implement the exact acknowledged lifecycle topology as immutable
  stdlib-only domain values and pure transition, retry, and checkpoint/resume
  decisions under `app.workflow`.
- Boundary: no persistence, Queue transport, model/provider, RAG, Execution,
  Evidence, publication, API, Auth lookup, wall clock, randomness, network, or
  filesystem runtime behavior is part of this foundation.
- Compatibility: failure terminals validate uppercase family compatibility so
  additive same-family codes remain accepted; the terminal state is the
  compatibility boundary.
- Historical initial evidence: direct pure-core suite `403 passed`; API plus
  Workflow regression suite `445 passed`; source import-graph purity test
  passed. Superseded for current test counts by `AGW-DEC-017` and `AGW-DEC-018`.
- State: `A2_ACCEPTED` as part of `WORKFLOW-002-LIFECYCLE-RUNTIME-FOUNDATION-001`.

## `AGW-DEC-017` — C1 inputs fail closed at typed boundaries

- Status: `HISTORICAL_CORRECTION_COMPLETE` / `A2_ACCEPTED`
- Decision: require exact integer `repair_attempts_used` values `0` or `1` in
  snapshots and resume validation; require actual booleans for owner-produced
  semantic facts; reject malformed checkpoint attempt identities before
  constructing a resumed snapshot.
- Boundary: validation remains pure and stdlib-only; no transition topology,
  contract, dependency, persistence, or external integration changed.
- Evidence: direct Workflow suite `428 passed`; API plus Workflow suite
  `470 passed`; import and compile checks passed.
- State: historical completed correction evidence; C1 rereview passed and accepted by A2.

## `AGW-DEC-018` — C2 terminal meanings and repair history fail closed

- Status: `HISTORICAL_CORRECTION_COMPLETE` / `A2_ACCEPTED`
- Decision: `REPAIR_LIMIT_EXHAUSTED` requires a consumed repair allowance;
  `FAILED_INFRASTRUCTURE` requires `retry_attempts_used == retry_limit`; and
  lifecycle snapshots plus checkpoint resume share one state/repair-counter
  consistency predicate.
- Compatibility: canonical topology and additive same-family infrastructure
  failure codes remain unchanged. C1 strict typing and attribution behavior is
  preserved.
- Evidence: direct Workflow suite `487 passed`; API plus Workflow suite
  `529 passed`; import, compile, lock, scope, and diff checks passed.
- State: historical completed correction evidence; C2 rereview passed and accepted by A2.

## `AGW-DEC-019` — Final A2 acceptance and current-main reconciliation

- Status: `IMPLEMENTED` / `TESTED` / `A2_ACCEPTED` / `READY_FOR_GIT_LIFECYCLE`
- Task: `WORKFLOW-002-A2-FINAL-ACCEPTANCE-RECONCILIATION-001`
- Decision: Record final A2 review result `PASS — WORKFLOW_002_A2_FINAL_REVIEW_COMPLETE`. Reconcile original implementation baseline `f318d9b515a4324b0848e64059f179027d19bd1f` to reconciled current-main base `66182abccf9ed92d7e481e832cfec0bf11a805e8` following merge of PR #36 (`apps/worker/**`).
- Validation evidence: Workflow suite `487 passed`; API plus Workflow suite `529 passed`; `git diff --check` passed.
- Scope boundary preserved: pure lifecycle foundation `IMPLEMENTED / TESTED / A2_ACCEPTED`; full Workflow runtime `NOT_IMPLEMENTED`; DB-003 `IMPLEMENTED / MERGED_BY_A2_DATABASE`; WORKFLOW-002 DB-003 integration `NOT_IMPLEMENTED_BY_WORKFLOW_002`; Queue, Execution, Evidence, RAG, Model, and API integrations `NOT_IMPLEMENTED_BY_WORKFLOW_002`.

## `AGW-DEC-020` — Post-DB003 status reconciliation

- Status: `IMPLEMENTED`
- Task: `WORKFLOW-002-DB003-POSTMERGE-STATUS-RECONCILIATION-001`
- Decision: Reconcile current-main base to `6eb622cf429093f3806dbe0261c3fa86cad607b6` following the merge of PR #37 (`feat(database): implement DB-003 workflow persistence`). Update active DB-003 status in Workflow-owned records from `NOT_STARTED` / `NOT_AUTHORIZED` to `IMPLEMENTED` / `MERGED_BY_A2_DATABASE`.
- Preserved distinction: WORKFLOW-002 DB-003 integration remains `NOT_IMPLEMENTED_BY_WORKFLOW_002`. WORKFLOW-002 remains a pure in-process workflow lifecycle foundation. It does NOT yet: persist lifecycle mutations through DB-003, write Workflow events, create DB-003 step occurrences, create DB-003 attempts, perform event/projection atomic commits, integrate checkpoint persistence, or integrate producer-event idempotency.
- Validation evidence: Workflow suite `487 passed`; API plus Workflow suite `529 passed`; `git diff --check` passed.

## Explicit labels

- `IMPLEMENTED`: contract decisions, pure lifecycle foundation, and reconciliation records.
- `TESTED`: pure semantic enforcement plus existing API regression.
- `A2_ACCEPTED`: WORKFLOW-002 pure foundation, C1, and C2.
- `READY_FOR_GIT_LIFECYCLE`: WORKFLOW-002 pure foundation.
- `NOT_TESTED`: external runtime and persistence integration.
- `BLOCKED`: none in the authorized pure-core scope.
- `ASSUMED`: none for the current task; `AGW-DEC-007` remains historical.
