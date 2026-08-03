# Backend dependency requests — CONTRACT-API-001 consumer review

- Date: 2026-08-03
- Requesting/owning Agent 2: `A2-BACKEND`
- Task: `BACK-CONTRACT-API-001`
- Contract: `CONTRACT-API-001@0.1.0-draft.1`
- Contract status: `DRAFT_FOR_CONSUMER_REVIEW / NOT_IMPLEMENTATION_READY`
- Review rule: silence is not acceptance; no request authorizes implementation
  by Backend or another owner.

## Review status

| Request | Owning reviewer | Status |
|---|---|---|
| `BACK-API-REVIEW-UI-001` | `A2-UI` | `OPEN / PENDING_OWNER_REVIEW` |
| `BACK-API-REVIEW-AUTH-001` | `A2-AUTH` | `OPEN / PENDING_OWNER_REVIEW` |
| `BACK-API-REVIEW-DATABASE-001` | `A2-DATABASE` | `OPEN / PENDING_OWNER_REVIEW` |
| `BACK-API-REVIEW-WORKFLOW-001` | `A2-AGENT-WORKFLOW` | `OPEN / PENDING_OWNER_REVIEW` |
| `BACK-API-REVIEW-DEPLOYMENT-001` | `A2-DEPLOYMENT` | `OPEN / PENDING_OWNER_REVIEW` |
| `BACK-API-REVIEW-SECURITY-001` | `A2-SECURITY` | `OPEN / PENDING_OWNER_REVIEW` |
| `BACK-API-REVIEW-EVALUATION-001` | `A2-EVALUATION` | `OPEN / PENDING_OWNER_REVIEW` |
| `BACK-API-REVIEW-QUEUE-001` | `A2-QUEUE` | `OPEN / PENDING_OWNER_REVIEW` |
| `BACK-API-REVIEW-INTEGRATION-001` | `A2-INTEGRATION` | `OPEN / PENDING_OWNER_REVIEW` |

## `BACK-API-REVIEW-UI-001` — Dashboard consumer review

- Request ID: `BACK-API-REVIEW-UI-001`
- Requesting Agent 2: `A2-BACKEND`
- Owning Agent 2: `A2-UI`
- Required change and reason: Review the proposed route names, cursor response,
  run summary/detail base fields, polling-only status behavior, safe error
  envelope, bearer transport, and omitted unresolved projections against
  `UI-005` through `UI-009`. Identify the minimum endpoint-specific filters,
  sorts, and mock examples the Dashboard needs.
- Contract affected: `CONTRACT-API-001@0.1.0-draft.1`
- Exact blocking task: API contract acceptance and later `BACK-002` through
  `BACK-006`; UI consumer implementation remains separately authorized.
- Backward-compatibility impact: Route/model/query changes are cheap while
  draft; they become breaking for generated clients after acceptance.
- Urgency: `HIGH`
- Proposed acceptance test: A UI-owned consumer fixture can list runs, follow a
  `Location` status URL, render safe errors and request IDs, and tolerate
  omitted Evidence/Evaluation fields without guessing `null` semantics.
- Approval status: `OPEN / PENDING_OWNER_REVIEW`
- Completion evidence: None.

## `BACK-API-REVIEW-AUTH-001` — Auth and authorization boundary review

- Request ID: `BACK-API-REVIEW-AUTH-001`
- Requesting Agent 2: `A2-BACKEND`
- Owning Agent 2: `A2-AUTH`
- Required change and reason: Confirm bearer access-token transport, the
  internal authenticated-context handoff, deny-by-default action checks,
  `401` behavior, the safe `403`/`404` disclosure boundary, and raw-body
  webhook verifier handoff. Supply or explicitly defer exact principal,
  identity, issuer/subject, installation, and verifier-result formats. Review
  the draft response to `AUTH-DEP-006` without treating it as Auth runtime.
- Contract affected: `CONTRACT-API-001@0.1.0-draft.1` and
  `CONTRACT-AUTH-001@1.0.0-draft.2`
- Exact blocking task: API contract acceptance; later `AUTH-003`, `AUTH-005`,
  `AUTH-006`, `BACK-002`, `BACK-003`, and `BACK-007` coordination.
- Backward-compatibility impact: Freezing a public identity body or changing
  `401`/`403` meaning later would be breaking; the draft deliberately freezes
  neither identity format nor denial concealment policy.
- Urgency: `HIGH`
- Proposed acceptance test: Missing/invalid access credentials fail before a
  protected handler; denied exact-tuple access leaks no resource existence;
  raw webhook bytes reach verification unchanged; no token/header appears in
  an error.
- Approval status: `OPEN / PENDING_OWNER_REVIEW`
- Completion evidence: None. Auth runtime and identity formats remain
  unresolved.

## `BACK-API-REVIEW-DATABASE-001` — Persistence/query consumer review

- Request ID: `BACK-API-REVIEW-DATABASE-001`
- Requesting Agent 2: `A2-BACKEND`
- Owning Agent 2: `A2-DATABASE`
- Required change and reason: Review the DB-002 field mapping, UUID/external-ID
  separation, cursor stability, proposed run-list filter/sort allowlist,
  durable `202` acceptance point, and duplicate/conflict alternatives. Identify
  query/index implications without adding a speculative index. Confirm that
  steps/events/actions/evidence remain unavailable until separately authorized
  DB-003 or later persistence work.
- Contract affected: `CONTRACT-API-001@0.1.0-draft.1`; response to `DB-DEP-002`
- Exact blocking task: API contract acceptance; later `BACK-003`, `BACK-004`,
  `DB-005`, and DB-007 index validation. DB-003 is not authorized.
- Backward-compatibility impact: Cursor key/order, identifier types, and
  duplicate behavior become externally visible once accepted.
- Urgency: `HIGH`
- Proposed acceptance test: Database fixtures round-trip internal UUIDs and
  distinct GitHub/benchmark IDs; deterministic cursor traversal has no
  duplicates or omissions; a persistence failure cannot return `202`.
- Approval status: `OPEN / PENDING_OWNER_REVIEW`
- Completion evidence: None. This request does not recommend or authorize
  DB-003, a migration, model, repository, or index.

## `BACK-API-REVIEW-WORKFLOW-001` — Lifecycle/action consumer review

- Request ID: `BACK-API-REVIEW-WORKFLOW-001`
- Requesting Agent 2: `A2-BACKEND`
- Owning Agent 2: `A2-AGENT-WORKFLOW`
- Required change and reason: Confirm the run summary/detail mapping to the
  canonical state contract, polling status boundary, action placeholder,
  cancellation race handling, regeneration/rerun distinction, and omission of
  steps/events/human decisions until their owner records exist. Identify which
  action request/response semantics may be exposed without re-owning Workflow.
- Contract affected: `CONTRACT-API-001@0.1.0-draft.1` and
  `CONTRACT-WORKFLOW-001@1.0.0-draft.1`
- Exact blocking task: API contract acceptance; later `BACK-003` through
  `BACK-005` and human-action integration.
- Backward-compatibility impact: Reinterpreting run states, cancellation,
  terminality, repair, or regeneration would be breaking.
- Urgency: `HIGH`
- Proposed acceptance test: Contract fixtures preserve exact states and
  terminal immutability; cancellation that loses a race is not represented as
  applied; regeneration creates a new run rather than mutating the old run.
- Approval status: `OPEN / PENDING_OWNER_REVIEW`
- Completion evidence: None. Workflow runtime, DB-003, Queue, and Evidence
  remain outside this request.

## `BACK-API-REVIEW-DEPLOYMENT-001` — Operational/runtime review

- Request ID: `BACK-API-REVIEW-DEPLOYMENT-001`
- Requesting Agent 2: `A2-BACKEND`
- Owning Agent 2: `A2-DEPLOYMENT`
- Required change and reason: Review `/healthz` liveness, `/readyz` response
  shape, the unresolved readiness dependency set, accepted/status polling and
  `Retry-After`, public webhook path metadata, CORS inputs, and runtime values.
  Supply Deployment-owned values only through Deployment records.
- Contract affected: `CONTRACT-API-001@0.1.0-draft.1` and future extension of
  `CONTRACT-DEPLOY-001`
- Exact blocking task: API contract acceptance; later `BACK-002`, `BACK-005`,
  `BACK-006`, and `BACK-007` operational wiring.
- Backward-compatibility impact: Probe paths/statuses and environment-variable
  names are operational contracts; renames or semantic changes require
  coordinated rollout and rollback.
- Urgency: `HIGH`
- Proposed acceptance test: Liveness remains `200` during dependency outage;
  readiness returns only safe `200/503`; probe bodies leak no dependency or
  configuration detail; deployed values are absent from this API draft.
- Approval status: `OPEN / PENDING_OWNER_REVIEW`
- Completion evidence: None. Exact runtime values, readiness dependencies,
  Queue/storage adapters, origins, URLs, and provider provisioning remain
  unresolved/not proven.

## `BACK-API-REVIEW-SECURITY-001` — Safe disclosure and abuse-control review

- Request ID: `BACK-API-REVIEW-SECURITY-001`
- Requesting Agent 2: `A2-BACKEND`
- Owning Agent 2: `A2-SECURITY`
- Required change and reason: Review the error envelope, allowed validation
  details, authorization non-disclosure, request/correlation header validation,
  cursor opacity, webhook body/header limits, redaction, rate/abuse responses,
  security-event boundary, retention, and CORS/CSRF implications. Publish the
  missing owner policy rather than embedding it in this API draft.
- Contract affected: `CONTRACT-API-001@0.1.0-draft.1` and absent
  `CONTRACT-SEC-001`
- Exact blocking task: API contract acceptance for security-sensitive fields;
  later `BACK-002`, `BACK-006`, `BACK-007`, and final acceptance.
- Backward-compatibility impact: Tightening limits can affect clients;
  weakening redaction or disclosure guarantees is breaking/security-sensitive.
- Urgency: `HIGH`
- Proposed acceptance test: Adversarial errors, invalid headers/cursors,
  unauthorized IDs, oversized webhooks, and dependency failures reveal no
  secret, raw input, resource existence, internal path, SQL, prompt, patch, or
  log content.
- Approval status: `OPEN / PENDING_OWNER_REVIEW`
- Completion evidence: None. No Security component record directory or
  `CONTRACT-SEC-001` exists at this baseline.

## `BACK-API-REVIEW-EVALUATION-001` — Benchmark/evaluation review

- Request ID: `BACK-API-REVIEW-EVALUATION-001`
- Requesting Agent 2: `A2-BACKEND`
- Owning Agent 2: `A2-EVALUATION`
- Required change and reason: Review the `BENCHMARK` run-request placeholder,
  benchmark identity boundary, run list/detail extensions, result provenance,
  aggregate/summary needs, and which evaluation values are safe and stable for
  API/UI exposure. Supply field semantics through `CONTRACT-EVAL-001`.
- Contract affected: `CONTRACT-API-001@0.1.0-draft.1` and absent
  `CONTRACT-EVAL-001`
- Exact blocking task: acceptance of benchmark API fields; later `BACK-004`,
  `BACK-006`, and UI benchmark dashboard integration.
- Backward-compatibility impact: Metric identity, value/unit, baseline, and
  release-gate meaning become breaking if silently reinterpreted.
- Urgency: `HIGH`
- Proposed acceptance test: An Evaluation-owned fixture round-trips benchmark
  identity and provenance without overloading internal UUIDs, and the API does
  not compute or reinterpret metrics in a request handler.
- Approval status: `OPEN / PENDING_OWNER_REVIEW`
- Completion evidence: None. No Evaluation component record directory or
  `CONTRACT-EVAL-001` exists at this baseline.

## `BACK-API-REVIEW-QUEUE-001` — Async/worker-delivery review

- Request ID: `BACK-API-REVIEW-QUEUE-001`
- Requesting Agent 2: `A2-BACKEND`
- Owning Agent 2: `A2-QUEUE`
- Required change and reason: Review what HTTP `202` may guarantee, the durable
  API-to-Queue handoff, delivery identity, enqueue idempotency, redelivery,
  result events, dead-letter outcomes, cancellation delivery, worker status,
  correlation propagation, and `Retry-After`. Publish an accepted
  `CONTRACT-QUEUE-001` before producer implementation.
- Contract affected: `CONTRACT-API-001@0.1.0-draft.1` and absent
  `CONTRACT-QUEUE-001`
- Exact blocking task: final async acceptance semantics; later `BACK-005`,
  webhook processing, worker integration, and final acceptance.
- Backward-compatibility impact: An HTTP acknowledgement must not overpromise a
  Queue/worker guarantee; changing delivery/idempotency meaning later is
  breaking for operations and retry behavior.
- Urgency: `HIGH`
- Proposed acceptance test: A duplicate or redelivered message has one semantic
  effect; an API `202` maps to the owner-approved durable boundary; a Queue
  outage cannot be reported as worker-started; cancellation outcome remains
  attributable.
- Approval status: `OPEN / PENDING_OWNER_REVIEW`
- Completion evidence: None. Queue ownership/process, worker delivery, runtime
  adapter, and contract semantics remain unresolved. No Queue code is
  authorized.

## `BACK-API-REVIEW-INTEGRATION-001` — Compatibility and release review

- Request ID: `BACK-API-REVIEW-INTEGRATION-001`
- Requesting Agent 2: `A2-BACKEND`
- Owning Agent 2: `A2-INTEGRATION`
- Required change and reason: Review contract versioning, operation IDs,
  strict-request/additive-response policy, cursor invalidation, deprecation,
  generated-client compatibility, unresolved-owner gates, and the eventual
  OpenAPI acceptance/rollback evidence. Confirm that a draft does not claim
  release readiness.
- Contract affected: `CONTRACT-API-001@0.1.0-draft.1` and future
  `CONTRACT-INTEGRATION-001` handoff
- Exact blocking task: contract acceptance and `BACK-008` final acceptance.
- Backward-compatibility impact: Integration owns the cross-component decision
  when an apparently additive change breaks a consumer or deployment.
- Urgency: `HIGH`
- Proposed acceptance test: Generated consumer fixtures detect removed/renamed
  operations or fields; unsupported majors fail clearly; an accepted rollback
  plan exists before a deployed route is removed.
- Approval status: `OPEN / PENDING_OWNER_REVIEW`
- Completion evidence: None.

## Unresolved cross-owner decision register

1. Auth authenticated-context and identity formats; JWT/JWKS runtime handoff.
2. Auth/Security `403` versus concealed `404` disclosure policy.
3. `AUTH-DEP-007` exact installation reference and `AUTH-DEP-008` machine actor.
4. DB-002 API mapping, cursor/index implications, and duplicate/conflict HTTP
   behavior.
5. DB-003 steps, attempts, ordered events, action audit, and human-decision
   persistence; DB-003 remains `NOT_STARTED / NOT_AUTHORIZED`.
6. Workflow action body/response semantics, cancellation race representation,
   and regeneration API mapping.
7. Queue ownership outcome, `CONTRACT-QUEUE-001`, durable handoff, enqueue,
   delivery, redelivery, worker result, dead letter, cancellation, correlation,
   and status semantics.
8. Durable GitHub delivery-GUID replay ownership and webhook-to-run
   idempotency.
9. Evidence/artefact/human-decision/publication schemas and access/download
   behavior; `CONTRACT-EVIDENCE-001` is absent.
10. Evaluation benchmark request, metric, provenance, baseline, release-gate,
    aggregate, and summary fields; `CONTRACT-EVAL-001` is absent.
11. Security redaction, validation detail, disclosure, rate/abuse limits,
    security events, retention, cursor/header/body limits, and artefact policy;
    `CONTRACT-SEC-001` is absent.
12. Deployment readiness dependency set, runtime values, public URLs, CORS
    origin, `Retry-After`, Queue/storage adapters, and webhook configuration.
13. UI endpoint-specific filters/sorts, polling cadence, and mock/fixture needs.
14. Integration consumer compatibility, OpenAPI/client validation,
    deprecation window, release acceptance, and rollback.

## Later Backend task dependency matrix

| Task | Must be accepted/available before implementation |
|---|---|
| `BACK-002 — Control-plane foundation` | Accepted applicable parts of `CONTRACT-API-001`; UI/Auth/Database review; Deployment probe/CORS/runtime input; Security error/redaction input. |
| `BACK-003 — Run query and action API` | `BACK-002`; DB query interfaces including separately authorized DB-003 where required; Auth handoff; Workflow and Evidence owner contracts; accepted run/action schemas. |
| `BACK-004 — Benchmark and GitHub run creation` | `BACK-003`; Evaluation/GitHub input contracts; DB-002 idempotency; Auth exact tuple; accepted normalization and duplicate behavior. |
| `BACK-005 — Queue and lifecycle integration` | `BACK-004`; A2-QUEUE ownership result; accepted `CONTRACT-QUEUE-001`; Workflow semantics; Deployment Queue adapter. |
| `BACK-006 — Artefact and benchmark-summary API` | `BACK-005`; Database query interfaces; Evidence/Evaluation/Security contracts; private storage adapter; UI fields. |
| `BACK-007 — GitHub webhook and publication HTTP adapters` | `BACK-006`; Auth verifier; durable replay decision; Queue and Workflow publication contracts; machine actor; Deployment GitHub runtime values. |
| `BACK-008 — Backend final acceptance` | All prior tasks and all required consumer acknowledgements, tests, OpenAPI/client evidence, security validation, release and rollback decision. |

No row authorizes another owner's implementation, DB-003, Queue or worker
runtime, provider configuration, a migration/model/index, route code, test,
manifest/lockfile change, environment value, or deployment change.
