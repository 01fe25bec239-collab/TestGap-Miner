# Queue Decision Log

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
