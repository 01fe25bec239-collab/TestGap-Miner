# Backend Decision Log

## `BACK-DEC-001` — Audit before contract or implementation

- Status: `APPROVED_FOR_ANALYSIS_ONLY`
- Decision: `BACK-001` records repository evidence and upstream dependencies
  only. It neither creates `CONTRACT-API-001` nor implements an API.
- Reason: the only HTTP surface is FastAPI's generated documentation surface;
  freezing routes now would guess unresolved Auth, Queue, Evidence,
  Evaluation, Security, Deployment, and consumer requirements.

## `BACK-DEC-002` — API contract requires separate authorization

- Status: `DEFERRED / NOT_AUTHORIZED`
- Decision: `CONTRACT-API-001` remains absent. A future task must explicitly
  authorize its draft, compatibility review, OpenAPI shape, error envelope,
  request correlation, versioning, pagination, CORS, health/readiness, and
  consumer fixtures.
- Compatibility: no public interface changes were made by this audit.

## `BACK-DEC-003` — Queue boundary remains external and pending

- Status: `PENDING_A2_QUEUE_QUEUE_003`
- Decision: Backend does not claim Queue ownership or implement a producer.
  Queue ownership and `CONTRACT-QUEUE-001` remain pending A2-QUEUE's
  `QUEUE-003` process.
- Supersession note: inspected older Workflow records name provisional or
  historical Workflow ownership. The current manager direction in `BACK-001`
  controls this Backend audit; those other-owner records were not modified.

## `BACK-DEC-004` — Existing persistence is not API/runtime evidence

- Status: `APPROVED`
- Decision: DB-002 run-request idempotency and Auth grant persistence are
  classified `PARTIAL` for Backend capabilities. They do not prove API
  request idempotency, webhook duplicate rejection, Auth context,
  authorization, Queue delivery, cancellation, or application routes.

## `BACK-DEC-005` — No DB-003 or Queue runtime recommendation

- Status: `APPROVED`
- Decision: this audit records missing persistence/runtime inputs without
  recommending DB-003 or Queue implementation. Any future work remains with
  its owner and requires separate authorization.
