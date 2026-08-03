# Backend Component Status

- Date: 2026-08-03
- Agent 2: `A2-BACKEND`
- Agent 3: `A3-BACKEND`
- Current task: `BACK-001 — API and repository audit`
- Prompt type: `VALIDATION_ONLY`
- Branch: `agent2/backend-api-contract`
- Base/HEAD at audit start: `ba4247af2195d4c8e60cb9990f616a95f2c54d54`

## Audited API surface

`apps/api/app/main.py` exports only `app = FastAPI()`. FastAPI therefore exposes
its framework-generated documentation routes (`/openapi.json`, `/docs`,
`/docs/oauth2-redirect`, and `/redoc`) and no application operation. The
generated document reports OpenAPI `3.1.0`.

| Area | State | Evidence / dependency |
|---|---|---|
| FastAPI application | `IMPLEMENTED / TESTED` | Importable empty app; `/openapi.json` is the only tested HTTP path. |
| Versioned application routes | `NOT_STARTED / NOT_TESTED` | No router or path operation exists; `CONTRACT-API-001` is absent. |
| Request IDs / correlation middleware | `NOT_STARTED / NOT_TESTED` | No middleware or response header behavior exists. DB-002 only stores a bounded request correlation value. |
| Stable error envelope | `NOT_STARTED / NOT_TESTED` | No exception handler exists. The required `error.code/message/request_id/details` shape is documentary only. |
| Health / readiness | `NOT_STARTED / NOT_TESTED` | No probe route exists. `CONTRACT-DEPLOY-001` currently defines only the Database runtime boundary, not API probe semantics. |
| Authenticated request context | `NOT_STARTED / NOT_TESTED` | No dependency or JWT/JWKS library exists. `CONTRACT-AUTH-001@1.0.0-draft.2` supplies identity semantics only. |
| Repository authorization | `PARTIAL / RUNTIME_NOT_TESTED` | DB-002 persists exact user + installation + repository grants; no API/runtime consumes them and `AUTH-DEP-007` remains pending. |
| Webhook boundary | `NOT_STARTED / NOT_TESTED` | No raw-body route, signature verification, delivery-GUID handling, or webhook tests exist. |
| Idempotency | `PARTIAL / RUNTIME_NOT_TESTED` | DB-002 persists versioned run-request idempotency composition; no API conflict behavior, durable webhook duplicate handling, or Queue delivery behavior exists. |
| Queue producer | `NOT_STARTED / NOT_TESTED / BLOCKED` | No Queue library, setting, provider configuration, producer, or contract. Ownership and `CONTRACT-QUEUE-001` remain pending A2-QUEUE `QUEUE-003`. |
| Cancellation API | `CONTRACT_ONLY / NOT_TESTED` | `CONTRACT-WORKFLOW-001@1.0.0-draft.1` defines cooperative and late-cancellation semantics; no route, service, Queue cancellation, or persistence integration exists. |
| Artefact API | `NOT_STARTED / NOT_TESTED / BLOCKED` | No routes or persistence; `CONTRACT-EVIDENCE-001`, Security rules, and object-reference/download semantics are absent. |
| Benchmark API | `NOT_STARTED / NOT_TESTED / BLOCKED` | No routes or persistence; `CONTRACT-EVAL-001` is absent. |
| Runtime settings | `IMPLEMENTED / TESTED` | Only redacted, required `DATABASE_URL` using `postgresql+psycopg`; no Auth, webhook, Queue, object-storage, or API settings. |

## API test inventory

`tests/api/test_main.py` contains one test for unauthenticated OpenAPI
availability. `tests/api/test_settings.py` contains four tests covering a valid
Database URL, two redacted failure cases, and the exact one-field settings
surface. `tests/conftest.py` provides one `TestClient` fixture. No application
route, Auth, authorization, webhook, idempotency, Queue, cancellation,
artefact, benchmark, health, readiness, request-ID, or error-envelope test
exists.

## Contract state

- `CONTRACT-API-001`: `ABSENT / NOT_AUTHORIZED`; it requires a separately
  authorized future drafting task.
- `CONTRACT-AUTH-001@1.0.0-draft.2`: semantic contract present and merged;
  Auth runtime remains absent and its own metadata-status conflict remains
  Auth-owned.
- `CONTRACT-WORKFLOW-001@1.0.0-draft.1`: acknowledged and merged; runtime,
  Evidence, and Queue are explicitly out of scope.
- `CONTRACT-DEPLOY-001`: approved for the Database runtime boundary only; it
  does not yet freeze Backend health/readiness, Auth/webhook, Queue, or object
  storage runtime behavior.
- `CONTRACT-QUEUE-001`: absent; ownership is pending A2-QUEUE `QUEUE-003`.
- `CONTRACT-EVIDENCE-001`, `CONTRACT-EVAL-001`, and `CONTRACT-SEC-001`: absent.

## Readiness and next action

`BACK-001` is complete as a documentation-only audit. The next A2-BACKEND task
should be a separately authorized `CONTRACT-API-001` draft and consumer-review
task. No `BACK-002` implementation, DB-003, Queue runtime, provider
configuration, or later API task is ready through this audit.

## Explicit labels

- `IMPLEMENTED`: minimal FastAPI/settings/test scaffold; DB-002 persistence by
  A2-DATABASE; this Backend audit record set.
- `TESTED`: five API/settings tests and OpenAPI import/probe described in the
  latest handoff.
- `NOT_TESTED`: every application API and runtime behavior listed above.
- `BLOCKED`: contract-dependent later Backend work, as mapped in
  `DEPENDENCY_REQUESTS.md`.
- `ASSUMED`: `NONE`; exact task titles were verified from the authoritative
  `A2_BACKEND_MANAGER.md`. No runtime behavior or deployed environment is
  inferred from documentation.
