# Backend Decision Log

## Historical audit decisions

### `BACK-DEC-001` — Audit before contract or implementation

- Status: `COMPLETE / SUPERSEDED_FOR_CONTRACT_AUTHORIZATION_ONLY`
- Decision: `BACK-001` remained analysis-only and created no contract or API.
  The later `BACK-CONTRACT-API-001` prompt separately authorizes this draft,
  but still authorizes no runtime route.

### `BACK-DEC-002` — API contract requires separate authorization

- Status: `SATISFIED_BY_BACK-CONTRACT-API-001`
- Decision: the separately authorized task creates
  `CONTRACT-API-001@0.1.0-draft.1` for consumer review. Acceptance and
  implementation remain separate decisions.

### `BACK-DEC-003` — Queue boundary remains external and pending

- Status: `PRESERVED / PENDING_A2_QUEUE`
- Decision: Backend does not claim Queue ownership, worker semantics, or a
  producer. `CONTRACT-QUEUE-001` remains absent and A2-QUEUE review is open.
  Older Workflow records naming provisional Queue ownership are not modified
  or silently treated as the current owner decision.

### `BACK-DEC-004` — Existing persistence is not API/runtime evidence

- Status: `PRESERVED`
- Decision: DB-002 is an accepted input but proves no HTTP, Auth, Queue,
  cancellation, webhook, or application behavior.

### `BACK-DEC-005` — No DB-003 or Queue runtime recommendation

- Status: `PRESERVED`
- Decision: this task neither recommends nor authorizes DB-003, Queue/worker
  runtime, a migration/model/index, or another owner's implementation.

## Contract-draft decisions

### `BACK-DEC-006` — Freeze transport mechanics, not owner semantics

- Status: `PROPOSED / PENDING_CONSUMER_REVIEW`
- Decision: the draft specifies Backend-owned URI, HTTP, header, error,
  pagination, probe, placeholder-path, and compatibility conventions. Auth
  identities, Workflow actions, DB-003, Queue/worker delivery, Evidence,
  Evaluation, Security policy, Deployment runtime values, and Integration
  release acceptance remain external.
- Reason: placeholders can be reviewed without fabricating upstream schemas.

### `BACK-DEC-007` — URI major version is `/api/v1`

- Status: `PROPOSED / PENDING_CONSUMER_REVIEW`
- Decision: all application resources use `/api/v1`; `/healthz` and `/readyz`
  remain unversioned operational probes. Breaking application changes require a
  new URI major.

### `BACK-DEC-008` — Cursor collections and strict requests

- Status: `PROPOSED / PENDING_UI_DATABASE_INTEGRATION_REVIEW`
- Decision: collections use opaque cursors, bounded limits, allowlisted
  filters/sorts, and deterministic UUID tie-breaking. Request objects reject
  unknown fields; consumers ignore additive response fields.
- Reason: this is the smallest stable generated-client and traversal boundary;
  it creates no speculative Database index.

### `BACK-DEC-009` — Safe errors and authorization non-disclosure

- Status: `PROPOSED / PENDING_AUTH_SECURITY_REVIEW`
- Decision: all application errors use the required safe envelope. Backend maps
  authentication failure to safe `401`; the exact `403` versus concealed `404`
  policy remains unresolved and must not be guessed.

### `BACK-DEC-010` — `202` is not worker evidence

- Status: `PROPOSED / PENDING_DATABASE_QUEUE_WORKFLOW_INTEGRATION_REVIEW`
- Decision: run-request `202` requires a durable DB-002 request/run and points
  to the run status resource. It does not claim Queue delivery, worker start,
  execution, or artefact creation. Duplicate response behavior and durable
  Queue handoff remain unresolved.

### `BACK-DEC-011` — Webhook route remains a raw-body placeholder

- Status: `PROPOSED / NOT_IMPLEMENTATION_READY`
- Decision: signature verification receives exact raw bytes before parse or
  side effect. Durable delivery replay ownership, limits, latency, Queue
  handoff, and Deployment values remain external blockers.

### `BACK-DEC-012` — Polling before streaming

- Status: `PROPOSED / PENDING_UI_REVIEW`
- Decision: accepted operations expose a `Location` polled with `GET`. No
  SSE/WebSocket contract is added until a consumer demonstrates the need.
