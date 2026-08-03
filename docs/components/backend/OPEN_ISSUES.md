# Backend Open Issues

## `BACK-ISSUE-001` — `CONTRACT-API-001` is absent

- Classification: `BLOCKED_FOR_IMPLEMENTATION / NOT_AUTHORIZED`
- Evidence: no matching contract file exists; `app.main` has no application
  operation. UI, Auth, and Database records all request the contract.
- Resolution: separately authorize A2-BACKEND to draft and obtain consumer
  review. Do not create it under `BACK-001`.

## `BACK-ISSUE-002` — Application API behavior is absent

- Classification: `NOT_STARTED / NOT_TESTED`
- Scope: versioned routes, request IDs, error envelope, health/readiness,
  Auth context, authorization, webhook processing, cancellation, artefacts,
  and benchmarks.
- Evidence: bare `FastAPI()` plus framework documentation routes only; five
  tests cover OpenAPI availability and settings.

## `BACK-ISSUE-003` — Queue ownership and contract are pending

- Classification: `DEPENDENCY_BLOCKED`
- Evidence: no Queue dependency, setting, producer, test, or
  `CONTRACT-QUEUE-001` exists.
- Resolution: wait for A2-QUEUE `QUEUE-003` to assign durable ownership and
  publish an accepted contract. Backend does not implement or configure Queue.

## `BACK-ISSUE-004` — Auth semantics exist without Auth runtime

- Classification: `DEPENDENCY_PENDING`
- Evidence: `CONTRACT-AUTH-001` and DB-002 Auth persistence exist; JWT/JWKS,
  authenticated context, grant reads, authorization decisions, and Auth tests
  do not. `AUTH-DEP-007` prevents reconstructing the exact authorization tuple
  from a run request alone.
- Resolution: consume separately authorized Auth/Deployment/Database owner
  handoffs before protected application routes.

## `BACK-ISSUE-005` — Webhook verification and durable duplicate handling are absent

- Classification: `DEPENDENCY_PENDING / NOT_TESTED`
- Evidence: no raw-body route, signature verifier, delivery-GUID runtime, or
  duplicate-delivery record. `AUTH-DEP-009` is pending and durable idempotency
  ownership is unassigned.
- Resolution: freeze the API raw-body/error boundary, consume the Auth verifier
  and Deployment configuration handoffs, and obtain an owner decision for
  durable idempotency. No persistence or Queue implementation is recommended.

## `BACK-ISSUE-006` — Evidence, Evaluation, and Security contracts are absent

- Classification: `DEPENDENCY_BLOCKED`
- Impact: artefact/evidence, human-decision/publication, benchmark, safe error,
  retention, and access behavior cannot be frozen.
- Resolution: consume separately authorized owner contracts when published.

## `BACK-ISSUE-007` — Deployment contract does not define API operational probes

- Classification: `DEPENDENCY_PENDING`
- Evidence: the approved `CONTRACT-DEPLOY-001` is explicitly a Database
  runtime boundary and contains no API liveness/readiness or object-storage
  semantics.
- Resolution: obtain A2-DEPLOYMENT input before freezing probe dependencies or
  private artefact delivery behavior.

## `BACK-ISSUE-008` — Later Backend task titles reconciled

- Classification: `CLOSED / VERIFIED`
- Evidence: `BACK-001-C1` read the authoritative
  `/Users/omkar/Documents/TestGap Miner/A2_BACKEND_MANAGER.md` and corrected
  the Backend task ledger and dependency matrix to its exact titles.
- Resolution: no title ambiguity remains.

## Explicit non-recommendations

This audit does not recommend DB-003, Queue runtime, provider configuration,
or any application implementation. Those require their owners and separate
authorization.
