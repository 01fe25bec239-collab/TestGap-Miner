# Backend Open Issues

## `BACK-ISSUE-001` — Consumer acceptance is pending

- Classification: `OPEN / BLOCKED_FOR_IMPLEMENTATION`
- Evidence: `CONTRACT-API-001@0.1.0-draft.1` is
  `DRAFT_FOR_CONSUMER_REVIEW`; all nine requests are open.
- Resolution: record explicit UI, Auth, Database, Workflow, Deployment,
  Security, Evaluation, Queue, and Integration decisions. Silence is not
  acceptance.

## `BACK-ISSUE-002` — Application API behavior remains absent

- Classification: `NOT_STARTED / NOT_TESTED`
- Evidence: this documentation task adds no route, schema, middleware, probe,
  handler, service, test, manifest, setting, or OpenAPI snapshot.
- Resolution: none under this task; implementation requires later
  authorization and accepted dependencies.

## `BACK-ISSUE-003` — Auth context and denial disclosure are unresolved

- Classification: `DEPENDENCY_PENDING`
- Owners: `A2-AUTH`, with `A2-SECURITY` for disclosure policy.
- Needed: exact internal authenticated-context/identity handoff, JWT/JWKS
  runtime boundary, Auth decision result, and safe `403` versus concealed `404`
  rule. `AUTH-DEP-007` and `AUTH-DEP-008` remain open.

## `BACK-ISSUE-004` — Query/cursor and duplicate behavior need Database review

- Classification: `DEPENDENCY_PENDING`
- Owner: `A2-DATABASE`, coordinated with Workflow and Integration.
- Needed: DB-002 field mapping, cursor stability/index implications, and
  duplicate semantic request mapping to `200`, `202`, or `409`.
- Boundary: no index, migration, model, or repository change is authorized.

## `BACK-ISSUE-005` — DB-003 and action audit persistence are unavailable

- Classification: `EXTERNAL / NOT_STARTED / NOT_AUTHORIZED`
- Owner: `A2-DATABASE` under separate authorization, with Workflow semantics.
- Impact: steps, attempts, ordered events, action audit, cancellation outcome,
  Evidence, publication, and human-decision persistence cannot be promised by
  run detail or action routes.
- Resolution: do not recommend or start DB-003 through this contract task.

## `BACK-ISSUE-006` — Workflow action API semantics are unresolved

- Classification: `DEPENDENCY_PENDING`
- Owner: `A2-AGENT-WORKFLOW`, with Auth/Evidence where applicable.
- Needed: cancellation request/outcome mapping, regeneration/rerun request
  body, human disposition, publication request, action response, and owner
  record mapping. Canonical states remain consumed unchanged.

## `BACK-ISSUE-007` — Queue and worker delivery contract is absent

- Classification: `DEPENDENCY_BLOCKED / NOT_IMPLEMENTED / NOT_TESTED`
- Owner: pending `A2-QUEUE` review.
- Needed: accepted `CONTRACT-QUEUE-001`, durable handoff, delivery identity,
  enqueue idempotency, redelivery, result/dead-letter events, cancellation,
  correlation propagation, worker status, and `Retry-After`.
- Resolution: no producer, adapter, setting, provider, Queue code, or worker
  code is authorized.

## `BACK-ISSUE-008` — Durable webhook replay ownership is unresolved

- Classification: `DEPENDENCY_PENDING / NOT_TESTED`
- Owners: requires Auth, Database/Workflow, Queue, Deployment, Security, and
  Integration coordination; durable owner not selected.
- Needed: delivery-GUID replay store, webhook-to-run idempotency, body/header
  limits, event allowlist, latency target, public URL/configuration, and
  downstream acceptance point.
- Boundary: raw-body verification is only a proposed HTTP boundary.

## `BACK-ISSUE-009` — Evidence contract is absent

- Classification: `DEPENDENCY_BLOCKED`
- Owner: external Evidence owner; current registry history does not authorize
  this Backend task to assign or implement it.
- Needed: candidate patch, execution attempt, evidence card, artefact manifest,
  access/expiry/checksum/download, publication, and human-decision record
  schemas. `CONTRACT-EVIDENCE-001` does not exist.

## `BACK-ISSUE-010` — Evaluation contract is absent

- Classification: `DEPENDENCY_BLOCKED`
- Owner: `A2-EVALUATION`.
- Needed: benchmark request identity, metric values/units, provenance,
  baselines, release gates, aggregates, and summary fields.
  `CONTRACT-EVAL-001` does not exist.

## `BACK-ISSUE-011` — Security policy contract is absent

- Classification: `DEPENDENCY_BLOCKED`
- Owner: `A2-SECURITY`.
- Needed: redaction, allowed validation details, authorization disclosure,
  rate/abuse behavior, security events, retention, header/cursor/body limits,
  CORS/CSRF input, and artefact policy. No Security component records or
  `CONTRACT-SEC-001` exist at this baseline.

## `BACK-ISSUE-012` — Deployment operational inputs are incomplete

- Classification: `DEPENDENCY_PENDING / VALUES_NOT_PROVEN`
- Owner: `A2-DEPLOYMENT`.
- Needed: readiness dependency set, startup behavior, runtime values, public
  URLs, Dashboard origin/CORS inputs, webhook configuration, Queue/storage
  adapters, polling guidance, and `Retry-After` behavior.
- Evidence: current `CONTRACT-DEPLOY-001` covers the Database runtime boundary;
  Auth design values are not deployed-runtime proof.

## `BACK-ISSUE-013` — UI query and polling needs are not accepted

- Classification: `DEPENDENCY_PENDING`
- Owner: `A2-UI`.
- Needed: endpoint-specific run filters/sorts, polling cadence, safe error UX,
  fixtures/mocks, and behavior while Evidence/Evaluation properties are
  omitted.

## `BACK-ISSUE-014` — Integration compatibility/release decision is pending

- Classification: `DEPENDENCY_PENDING`
- Owner: `A2-INTEGRATION`.
- Needed: generated-client compatibility evidence, cursor/deprecation rules,
  cross-owner acceptance, release gate, overlap window, and rollback.

## Explicit non-recommendations

This draft does not recommend or authorize API routes, DB-003, migrations,
models, indexes, Queue/worker runtime, provider configuration, Evidence or
Evaluation implementation, Security policy invention, deployment runtime
values, tests, manifests, lockfiles, environments, CI, or containers.
