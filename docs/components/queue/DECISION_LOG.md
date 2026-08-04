# Queue Decision Log

## 2026-08-04 — Correct constraint-register source fidelity

- A2-QUEUE renewed review accepted the `EXECUTING_BUGGY` then
  `EXECUTING_FIXED` correction and confirmed the 39-row/11-column register was
  structurally valid.
- Finding: seven Auth, five Integration, and five Evaluation rows did not
  preserve exact source-review mappings and complete constraint/evidence
  content.
- Decision: correct only those 17 rows from the supplied source record;
  preserve all 39 stable IDs, six managers, eleven columns, Backend/Database/
  Security rows, dispositions, and merge/implementation/release effects.
- Contract boundary: `CONTRACT-QUEUE-001@1.0.0-draft.2` normative prose and
  matrix are byte-unchanged in this task.
- Status: `CORRECTION_PREPARED / A2_QUEUE_FINAL_SOURCE_REVIEW_PENDING`.
  Affected-owner re-review has not begun, current-main reconciliation has not
  occurred, and commit/push are not authorized.

## 2026-08-04 — Correct final Workflow sequence and constraint record defects

- A2-QUEUE independent review result:
  `CHANGES_REQUIRED — DRAFT_2_NOT_APPROVED_FOR_COMMIT`.
- Defect 1: the one-repair boundary named only a generic required Workflow
  sequence. Decision: state the authoritative repaired-candidate order exactly
  as `EXECUTING_BUGGY` then `EXECUTING_FIXED` in sections 8–9 and
  `QUEUE-REQ-010`, `QUEUE-REQ-015`, `QUEUE-REQ-019`, and `QUEUE-REQ-024`.
  Queue recovery cannot skip, reverse, complete, or shortcut either state and
  cannot authorize a second repair; Workflow remains authoritative under
  `CONTRACT-WORKFLOW-001`.
- Defect 2: the six constrained acceptances were summarized but their complete
  durable constraints were not individually recorded. Decision: add the
  39-entry accepted consumer-constraint register with stable IDs, manager,
  exact affected boundary, constraint, rationale, compatibility, evidence,
  closure, and contract/implementation/release effects.
- Status: `CONTRACT-QUEUE-001@1.0.0-draft.2` and all ten existing correction
  groups remain unchanged except for this focused completion. Final A2-QUEUE
  diff review is pending; affected-owner re-review has not begun; current-main
  reconciliation has not occurred; commit and push are not authorized.

## 2026-08-04 — Prepare draft.2 consolidated consumer-review correction

- Review total: `10_OF_10_RESPONSES_RECEIVED` for
  `CONTRACT-QUEUE-001@1.0.0-draft.1`: six
  `ACCEPTED_WITH_CONSTRAINTS`, two `SPECIFICATION_CONFLICT`, and two
  `REJECTED_WITH_REASON`. Draft.1 is historical review evidence, not an
  accepted contract.
- Version decision: create `CONTRACT-QUEUE-001@1.0.0-draft.2` because the first
  complete consumer review requires normative identity, ownership, retry,
  heartbeat, checkpoint, adapter, persistence, and result-boundary corrections.
  Keep the major/minor/patch version unchanged and keep the contract a draft.
- Correction 1: bind Workflow attempt identity to run, Workflow step
  occurrence, step kind, occurrence, and zero-based attempt index; Queue
  transport identities cannot create or redefine attempts.
- Correction 2: make checkpoint claim/fence binding conditional on production
  under Queue-managed claimed work; Workflow alone decides checkpoint
  commitment, eligibility, compatibility, and resume authority.
- Correction 3: preserve Workflow's `0..1` one-repair allowance across every
  Queue retry, recovery, replay, re-drive, and checkpoint-resume operation.
- Correction 4: separate Workflow semantic lifecycle/races/acceptance from
  Execution worker/runtime facts, cancellation observation, cleanup, and result
  production; Queue owns transport only.
- Correction 5: preserve A2-DATABASE as exclusive physical persistence owner;
  A2-EVIDENCE owns Evidence semantics, Workflow owns state effects, and Queue
  owns acknowledgement eligibility. No physical schema or DB-003 is authorized.
- Correction 6: make producer-result identity stable per Workflow-authorized
  attempt/result slot while preserving per-submission authority/provenance and
  layered Execution, Workflow, Evidence, Queue, Database, and Security
  deduplication ownership. Queue never defines canonical Evidence equality.
- Correction 7: Execution produces heartbeat/renewal inputs, Queue owns
  authoritative validation/renewal/lease/fence state, Deployment owns
  transport/clock/configuration, and Security owns field/trust policy. Signals
  alone extend no authority or semantic eligibility.
- Correction 8: Queue owns transport retry categories, Workflow owns semantic
  retry/failure/repair meaning, and Deployment owns operational configuration
  only; configuration cannot relabel semantic outcomes.
- Correction 9: require clean-checkout local/test isolation without production
  credentials, secrets, or shared production Queue/Database state; retain one
  common provider-neutral conformance suite.
- Correction 10: require every future adapter mapping to document encryption,
  least-privilege data/control identities, secret/admin boundaries, and the
  minimum operational signals while keeping thresholds and gates external.
- Overlap disposition: Deployment and Execution heartbeat findings resolve
  through the same four-owner boundary in correction 7. Workflow, Evidence,
  and Execution result-boundary findings resolve through corrections 4–6;
  their authorities remain layered rather than shared or collapsed.
- Authorization: no runtime, adapter, worker, test, dependency, provider,
  infrastructure, model, migration, or DB-003 implementation is authorized.
- Reconciliation: `origin/main` at
  `c5d4c8a462f6e76aa1dd4929e59012fb2823c999` was observed; reconciliation is
  deferred until after independent A2-QUEUE diff review in the later reviewed
  commit/push task. No merge or rebase is performed here.

The entries below are historical decisions for draft.1 and are superseded only
where this draft.2 correction expressly changes their current status or
normative boundary.

## 2026-08-04 — Correct the canonical requirement matrix

- Finding: The original section 17 count-only validation passed with 26 unique
  sequential IDs, but semantic mapping validation failed because several IDs
  named the wrong subjects.
- Decision: Replace the matrix with the canonical 26-ID title mapping and move
  each requirement's constraints, evidence, dependencies, and owner effects to
  its correct semantic row without changing `1.0.0-draft.1`.
- Review: After the semantic ID/title correction, A2-QUEUE found seven
  drafting-status mapping mismatches; those statuses are corrected pending
  final A2-QUEUE review. No runtime, provider, or DB-003 work is authorized.
- Final semantic-boundary review: A2-QUEUE found defects in at-least-once
  disposition handling, Execution versus Workflow cleanup ownership, and the
  outbox-plus-inbox capability requirements. All three are corrected pending
  one final A2-QUEUE diff review; PR #24 is not ready and consumer review has
  not begun.

## 2026-08-04 — Initialize A2-QUEUE durable records

- Decision: A2-QUEUE is initialized as Queue and asynchronous-execution
  component owner. `QUEUE-003` and all owner responses are complete.
- Constraint: Owner-confirmation work is not repeated.
- Evidence: Authorized task and this Queue-owned record set.

## 2026-08-04 — Reauthorize Queue contract drafting

- Decision: `QUEUE-004` is reauthorized against
  `ab60d4573d398fb610bc2ebb813f76d0c95b33d7`.
- Result: `CONTRACT-QUEUE-001@1.0.0-draft.1` is
  `DRAFT / PENDING_CONSUMER_REVIEW`.
- Compatibility: First authoritative provider-neutral Queue draft; no runtime
  or accepted prior Queue contract is changed.

## 2026-08-04 — Reconcile PR #23 and the API boundary

- Decision: Treat `CONTRACT-API-001@0.1.0-draft.1` as
  `EXTERNAL_BACKEND_API_DRAFT_DEPENDENCY`,
  `REQUIRED_QUEUE_CONSUMER_REVIEW`, and
  `NOT_QUEUE_RUNTIME_AUTHORIZATION`.
- Accepted: API `202` proves only the API durable acceptance boundary;
  durable request/publication, request/correlation/Queue identities,
  API/Queue idempotency, uncertain publication, and cancellation are separate.
- Rejected: Redefining routes, methods/statuses, error/auth/pagination,
  authenticated context, Backend handling, or API duplicate response behavior.

## 2026-08-04 — Keep semantic identities and authorities separate

- Decision: Semantic request, message, delivery, claim, Workflow attempt,
  result, and Evidence identities are separate; requester, producer, worker,
  publication, cancellation, and re-drive actors are separately attributable.
- Rejected: Provider receipts, trace IDs, credentials, delivery tokens, or
  stored authorization as semantic identity/current authority.

## 2026-08-04 — Require durable intent and fail-closed recovery

- Decision: A durable publication intent or A2-DATABASE-approved equivalent
  precedes provider attempts. Uncertain publication reconciles stable identity;
  accepted effects commit before acknowledgement; stale claims and conflicts
  fail closed.
- Deferred: Physical outbox/inbox, transaction, fence storage, and adapter.
  DB-003 remains unauthorized.

## 2026-08-04 — Keep payloads reference-only and allowlist-first

- Decision: Bounded metadata and opaque references only; prohibited content
  remains prohibited when encoded, compressed, hashed, or encrypted. Redaction
  occurs before serialization and failure blocks publication.
- External: Security field/event/integrity policy and exact configured limits.

## 2026-08-04 — Separate transport semantics from evidence and gates

- Decision: Runtime conformance evidence and release/Evaluation gates do not
  define transport semantics. Queue ordering/acknowledgement/DLQ/lease expiry
  do not define Workflow ordering/completion/terminality or Evidence proof.
- Status: Provider unselected; runtime not implemented; consumer review pending.

## 2026-08-04 — Approve the complete correction for additive commit

- Independent review: A2-QUEUE reviewed the complete unstaged correction.
- Result: The canonical mapping and final semantic-boundary correction passed.
- Decision: Approve the correction for one additive documentation commit.
- Authorization boundary: No runtime, provider, DB-003, or implementation work
  is authorized.
