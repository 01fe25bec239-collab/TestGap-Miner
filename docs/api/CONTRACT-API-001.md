# CONTRACT-API-001 — Versioned REST/OpenAPI boundary

## Metadata

| Field | Value |
|---|---|
| Contract ID | `CONTRACT-API-001` |
| Version | `0.1.0-draft.1` |
| Status | `DRAFT_FOR_CONSUMER_REVIEW / NOT_IMPLEMENTATION_READY` |
| Owner | `A2-BACKEND` |
| Required reviewers | `A2-UI`, `A2-AUTH`, `A2-DATABASE`, `A2-AGENT-WORKFLOW`, `A2-DEPLOYMENT`, `A2-SECURITY`, `A2-EVALUATION`, `A2-QUEUE`, `A2-INTEGRATION` |
| Runtime implementation | `NOT_IMPLEMENTED / NOT_TESTED / NOT_AUTHORIZED_BY_THIS_DRAFT` |
| Evidence baseline | `7706f51eef07b7f89f322548eedd7bfba27a01e5` |

Normative terms `MUST`, `MUST NOT`, `SHOULD`, and `MAY` are used as in RFC
2119. This is a proposed transport contract, not an OpenAPI snapshot and not
authorization to add routes.

## Scope and ownership boundary

This draft owns the HTTP and OpenAPI conventions used by the FastAPI control
plane. It does not own the domain semantics transported through that boundary.

| Boundary | State / owner |
|---|---|
| API path, HTTP method/status, headers, safe error envelope, query syntax | Proposed here; owned by `A2-BACKEND` |
| Authenticated principal and identity formats | External: `CONTRACT-AUTH-001`; exact runtime handoff unresolved with `A2-AUTH` |
| Authorization policy and exact repository tuple | External: `A2-AUTH`; Security non-disclosure policy unresolved |
| Run lifecycle and action meaning | External: `CONTRACT-WORKFLOW-001@1.0.0-draft.1` |
| Run request/current-run persistence | External: DB-002, implemented by `A2-DATABASE` |
| Steps, attempts, ordered events, action audit history | External and unavailable: DB-003 is `NOT_STARTED / NOT_AUTHORIZED` |
| Queue envelope, enqueue, delivery, retry, worker result, cancellation delivery | External and unresolved with `A2-QUEUE`; `CONTRACT-QUEUE-001` is absent |
| Evidence, artefacts, human-decision record, publication record | External and unresolved; `CONTRACT-EVIDENCE-001` is absent |
| Benchmark/evaluation fields and release-gate meaning | External and unresolved with `A2-EVALUATION`; `CONTRACT-EVAL-001` is absent |
| Redaction, rate/abuse controls, security events, retention, disclosure policy | External and unresolved with `A2-SECURITY`; `CONTRACT-SEC-001` is absent |
| Probe dependencies, runtime values, CORS origin, public URLs, Queue/storage adapters | External and unresolved with `A2-DEPLOYMENT` |
| Compatibility acceptance and release handoff | External review by `A2-INTEGRATION` |

An omitted external field is unresolved, not implicitly nullable, empty, or
unsupported. No implementation may infer an owner contract from a placeholder
in this draft.

## REST and OpenAPI conventions

### Versioned application paths

- All application resources MUST be rooted at `/api/v1`.
- `v1` is the URI major version. Minor and patch revisions do not change the
  prefix.
- Operational probe paths are the deliberate exception described below.
- Canonical paths have no trailing slash. Implementations MUST NOT depend on an
  implicit redirect for non-`GET` requests.
- JSON request and response media type is `application/json` encoded as UTF-8.
- Public operation IDs and component-schema names MUST be stable and unique.
- The generated OpenAPI document MUST declare OpenAPI `3.1.x`,
  `info.version: 0.1.0-draft.1`, and `x-contract-id: CONTRACT-API-001` while
  implementing this exact draft.
- Request schemas MUST reject unknown properties. Response consumers MUST
  ignore unknown additive properties.
- Internal record identifiers use JSON strings with OpenAPI `format: uuid`.
  GitHub numeric IDs, delivery GUIDs, commit SHAs, correlation IDs, benchmark
  IDs, model IDs, and provider IDs MUST remain separately named and MUST NOT be
  represented as internal UUIDs.
- Server-authored timestamps use RFC 3339 `date-time` strings normalized to
  UTC. Clients MUST NOT infer ordering from timestamps when an owner contract
  defines an explicit sequence.

### Request and correlation IDs

Every HTTP response, including an error and an operational probe response,
MUST include:

- `X-Request-ID`: a server-controlled opaque identifier for one HTTP request;
- `X-Correlation-ID`: an opaque identifier for the related operation chain.

A caller MAY send either header. An accepted inbound value MUST be 1–128 ASCII
characters from `A-Z`, `a-z`, `0-9`, `.`, `_`, `:`, and `-`. The server MUST
replace a missing or invalid value with a generated opaque value and MUST NOT
reflect an invalid value. The generated format is not a client contract.

If `X-Correlation-ID` is absent, its initial value is the effective request ID.
Request IDs MUST be unique per HTTP attempt; a retry MAY retain the correlation
ID but MUST receive a new request ID. Neither value is an identity,
authorization credential, idempotency key, or secret.

The error envelope repeats the effective request ID. Propagation beyond the
HTTP process, including Queue and worker delivery, remains unresolved until
`CONTRACT-QUEUE-001` is accepted.

## Safe error contract

Every JSON API error MUST use exactly this top-level shape:

```json
{
  "error": {
    "code": "STABLE_ERROR_CODE",
    "message": "Safe user-facing message",
    "request_id": "opaque-request-id",
    "details": {}
  }
}
```

- `code` is a stable uppercase machine-readable value.
- `message` is safe for direct display but MUST NOT reveal credentials,
  headers, tokens, secrets, provider payloads, SQL, stack traces, internal
  paths, repository contents, prompts, patches, logs, or authorization tuples.
- `request_id` MUST equal the response `X-Request-ID`.
- `details` MUST be a JSON object and defaults to `{}`. Field-level validation
  detail is allowed only after Security review and MUST never echo raw input.
- Framework-native error bodies and HTML error pages MUST be mapped to this
  envelope for `/api/v1` and webhook paths.

Initial transport codes are:

| HTTP | Code | Boundary |
|---:|---|---|
| 400 | `INVALID_REQUEST` | Malformed syntax or unsupported request shape outside field validation |
| 401 | `AUTHENTICATION_REQUIRED` | Missing, invalid, or unusable access credential; include `WWW-Authenticate: Bearer` |
| 403 | `AUTHORIZATION_DENIED` | Authenticated principal denied an action; no policy or tuple detail |
| 404 | `RESOURCE_NOT_FOUND` | Resource not found after the applicable disclosure policy |
| 409 | `CONFLICT` | Current resource/request state conflicts with the operation |
| 422 | `VALIDATION_FAILED` | Structurally valid JSON with invalid typed fields, query, cursor, filter, or sort |
| 429 | `RATE_LIMITED` | Security/operational policy rejected excess traffic; policy remains Security-owned |
| 500 | `INTERNAL_ERROR` | Unexpected server error; `details` MUST be `{}` |
| 503 | `DEPENDENCY_UNAVAILABLE` | Required dependency unavailable; dependency identity MUST NOT be exposed |

Domain-specific codes require the owning contract and a compatible API
revision. Whether a denied resource is returned as `403` or concealed as `404`
is unresolved pending joint Auth and Security review; implementations MUST NOT
guess that disclosure rule.

## Authenticated-context and authorization-response boundary

- Protected routes accept an access token only through
  `Authorization: Bearer <access-token>`.
- Refresh tokens MUST NOT be forwarded to or accepted by FastAPI. Cookies,
  query parameters, and request bodies are not alternate API credentials in
  this draft.
- Authentication MUST complete before a protected handler consumes a request
  body or performs a domain lookup.
- The runtime authenticated context is an internal Auth-to-Backend handoff,
  never a client-supplied JSON model. Its field names, identity formats, token
  claims, issuer values, and subject representation remain Auth-owned and are
  deliberately not frozen here.
- Authorization is deny-by-default and consumes the Auth-owned action and
  exact user + installation + repository boundary where applicable. API route
  possession never grants permission.
- An allow/deny decision is made by an Auth-owned dependency. Backend maps an
  unauthenticated outcome to safe `401` and an authenticated denial to the
  jointly approved safe `403`/`404` disclosure response.
- An authorization failure MUST NOT reveal whether another user's run,
  repository, installation, artefact, or decision exists.

`CONTRACT-AUTH-001@1.0.0-draft.2` supplies semantic actions and identity
meaning but no JWT/JWKS runtime or final authenticated-context format.
`AUTH-DEP-007` and `AUTH-DEP-008` remain unresolved and this draft does not
invent replacements.

## Pagination, filter, and sort conventions

Collection routes use cursor pagination.

### Query syntax

- `limit`: integer, default `50`, minimum `1`, maximum `100`.
- `cursor`: opaque URL-safe token returned by the preceding response. Clients
  MUST NOT parse or construct it.
- `sort`: comma-separated allowlisted field names. A leading `-` means
  descending; no prefix means ascending.
- Filters use endpoint-allowlisted query parameter names. Repeating one filter
  means OR within that field; different filter names combine with AND.
- UTC time windows use paired `*_after` (inclusive) and `*_before` (exclusive)
  RFC 3339 values.
- Unknown filters, unsupported sort fields, malformed cursors, and cursors used
  with different filters/sorts return `422 VALIDATION_FAILED`.
- Offset/page-number pagination is not part of v1.

Every sort is made deterministic by appending internal `id` as a tie-breaker
in the same direction as the final requested sort field unless `id` is already
present. The proposed run-list default is `-created_at,-id`. The cursor MUST be
bound to the effective filter and sort set and MUST not expose raw database
keys or sensitive values.

### Collection response

```json
{
  "items": [],
  "page": {
    "limit": 50,
    "has_more": false,
    "next_cursor": null
  }
}
```

`next_cursor` is non-null only when `has_more` is true. Total counts are omitted
because they may require a separate query and are not needed for traversal.
Endpoint-specific filters and sort allowlists remain subject to UI and Database
review; no speculative Database index is authorized by this draft.

## Health and readiness boundary

Operational probes are intentionally outside `/api/v1` so infrastructure does
not depend on the application major version.

| Method/path | Meaning | Response |
|---|---|---|
| `GET /healthz` | Process liveness only; MUST NOT query Database, Queue, Auth provider, object storage, GitHub, or workers | `200 {"status":"ok"}` |
| `GET /readyz` | Whether this API instance may receive traffic | `200 {"status":"ready"}` or `503 {"status":"not_ready"}` |

Probe bodies MUST NOT enumerate dependencies, configuration, credentials,
hostnames, versions, exception text, or stack traces. The exact readiness
dependency set, startup grace behavior, and deployment values remain owned by
`A2-DEPLOYMENT` and are unresolved. In particular, this draft does not decide
whether Queue availability gates API readiness.

## Proposed run API placeholders

These paths reserve a review surface; they are not implementation-ready until
their referenced owner decisions are accepted.

| Operation ID | Method/path | Auth boundary | Proposed success |
|---|---|---|---|
| `createRunRequest` | `POST /api/v1/run-requests` | Auth-owned `RUN_CREATE` | `202 Accepted` plus `Location` of run detail |
| `listRuns` | `GET /api/v1/runs` | Auth-owned `RUN_READ` per returned resource | `200` cursor collection |
| `getRun` | `GET /api/v1/runs/{run_id}` | Auth-owned `RUN_READ` | `200` run detail |
| `requestRunAction` | `POST /api/v1/runs/{run_id}/actions` | Action-specific Auth decision | `202 Accepted` plus run status `Location` |

### Run request placeholder

`RunRequestCreate` will be a strict discriminated union using the DB-002
`request_kind` values `GITHUB` and `BENCHMARK`. Exact GitHub issue/PR/comment,
benchmark, configuration, model, prompt-template, installation, repository,
and idempotency input fields are not frozen here. They require Auth, Database,
Workflow, Evaluation, and Integration review.

The API MUST keep internal UUIDs distinct from GitHub IDs, delivery GUIDs,
commit SHAs, and benchmark IDs. Request idempotency composition remains the
accepted Workflow/DB-002 semantic boundary. Client header behavior and
duplicate/conflict response behavior are unresolved and MUST NOT be invented.

### Run list placeholder

`listRuns` uses the common cursor contract. Proposed allowlisted fields are
limited to DB-002 projection fields: repeated `state`, repeated
`request_kind`, `created_after`, and `created_before`; proposed sort fields are
`created_at` and `updated_at`. Repository display/search fields, event fields,
evidence fields, evaluation fields, and total counts remain unresolved.

### Run summary/detail base projection

The proposed base response maps only accepted DB-002 and Workflow fields:

- `id` and `run_request_id`: internal UUIDs;
- `state`: exact `RunState` from `CONTRACT-WORKFLOW-001`;
- `contract_version`: governing Workflow contract version;
- `review_required`;
- `created_at`, `updated_at`, and nullable `terminal_at`;
- a safe terminal code only when allowed by the Workflow and Security
  contracts.

Run detail does not yet freeze `steps`, `events`, `evidence`, `artefacts`,
`evaluation`, `publication`, or `human_decision`. Those properties MUST be
omitted until DB-003 and the Evidence/Evaluation/Security owner contracts are
accepted; omission does not mean an empty result.

### Run action placeholder

The request body will be a strict discriminated union with an `action`
discriminator. Cancellation, rerun/regeneration, human disposition, and
publication-request semantics remain owned by Workflow, Auth, Evidence, and
DB-003. This draft does not freeze action values or bodies, does not create an
audit record, and does not permit auto-merge, approval bypass,
branch-protection bypass, production-code editing, or synchronous workflow
execution in a handler.

## Asynchronous accepted and status behavior

- A run-creation `202` means a durable DB-002 run request and current-run
  projection exist and the request was accepted for asynchronous handoff.
- `202` MUST NOT claim that a Queue message was delivered, a worker started,
  execution succeeded, or an artefact exists.
- The response MUST include `Location: /api/v1/runs/{run_id}` and a body with
  only `run_id`, `status_url`, `request_id`, and `correlation_id` until a richer
  response is reviewed.
- The status URL is polled with `GET`; no streaming/SSE/WebSocket contract is
  proposed in this draft.
- A persistence failure returns a safe error, not `202`.
- Queue enqueue atomicity, an outbox boundary, worker delivery, retry,
  redelivery, result events, dead letters, cancellation delivery, and
  Queue-specific status are unresolved external decisions.
- Duplicate semantic request behavior (`200` existing, `202` existing, or
  `409`) remains unresolved pending Database, Workflow, and Integration review.
- `Retry-After` behavior for accepted requests and unavailable dependencies is
  unresolved with Deployment and Queue.

An action `202` means only that an attributable action request was durably
accepted. DB-003 and owner action records do not exist, so action routes remain
placeholders and MUST NOT be implemented from this sentence alone.

## GitHub webhook raw-body boundary

Proposed path: `POST /api/v1/webhooks/github`.

- The exact request bytes MUST be retained unchanged for signature
  verification before JSON parsing, normalization, persistence, Queue use, or
  business logic.
- The boundary consumes `X-Hub-Signature-256`, `X-GitHub-Delivery`, and
  `X-GitHub-Event`. Header value formats and verifier output remain Auth-owned.
- Invalid or missing signature input MUST produce a safe error with no body
  echo and no downstream side effect.
- A successful `202` means only that a verified delivery crossed the approved
  durable acceptance boundary. It does not mean worker delivery or run
  completion.
- Payload-size limits, event allowlists, durable delivery-GUID replay
  protection, delivery-to-run idempotency, Queue handoff, response latency
  target, and public endpoint/runtime values are unresolved with Security,
  Auth, Database/Workflow, Queue, and Deployment.
- The webhook secret and raw body MUST never appear in logs, errors, events, or
  response models.

Because durable replay ownership is unresolved, this route is
`PLACEHOLDER / NOT_IMPLEMENTATION_READY`.

## Adjacent unresolved HTTP policy

CORS is not frozen by this draft. The current FastAPI default emits no CORS
headers. Any future browser API policy requires the Deployment-owned Dashboard
origin, UI method/header needs, and Auth/Security credential and CSRF review.
No wildcard credentialed origin is implied or authorized.

## Compatibility and versioning rules

1. Breaking HTTP changes require a new URI major version such as `/api/v2`.
   Breaking changes include removing or renaming a route, method, required
   request/response field, header, error field/code meaning, sort/filter
   meaning, identifier type, or authorization requirement.
2. Additive optional response fields, new routes, and new error codes may use a
   compatible minor contract revision after affected consumer review.
3. Text-only clarifications with no behavioral change use a patch revision.
4. Draft revisions may change before acceptance, but every change MUST bump the
   draft version, record compatibility impact, and notify all affected
   consumers. `draft` never means unversioned.
5. Existing runs retain their pinned Workflow contract version. An API release
   MUST NOT silently reinterpret an existing run under a new external-contract
   major version.
6. Clients MUST ignore unknown response properties. Servers MUST reject unknown
   request properties. New enum members are compatible only where the owning
   contract explicitly defines them as additive and consumers can preserve or
   safely reject unknown values.
7. Cursor format is server-private. A compatible deployment SHOULD honor
   unexpired cursors; an incompatible query revision may reject them with
   `422 VALIDATION_FAILED` but MUST NOT mispage silently.
8. Deprecation requires consumer notice, replacement documentation, an overlap
   window approved by Integration, and `Deprecation`/`Sunset` response headers
   when a deployed route is scheduled for removal.
9. No route is accepted or frozen until all blocking consumer-review requests
   in the Backend dependency package are resolved for the relevant surface.

## Review gates and current classification

This draft is ready for consumer review, not implementation. Acceptance
requires written responses from all nine named reviewers. A response may
accept, request a compatible clarification, or identify a specification
conflict. Silence is not acceptance.

- `IMPLEMENTED`: this Markdown draft and Backend-owned review requests only.
- `TESTED`: documentation scope and whitespace checks only after final
  validation.
- `NOT_TESTED`: OpenAPI generation, clients, routes, middleware, probes, Auth,
  authorization, Queue/worker behavior, webhook behavior, persistence use, and
  every runtime status described here.
- `BLOCKED`: implementation readiness on the nine consumer reviews and the
  unresolved external contracts/owner decisions listed above.
- `ASSUMED`: no missing owner semantics. Existing Auth, Workflow, DB-002, and
  Deployment records are treated as documentary inputs, not runtime evidence.
