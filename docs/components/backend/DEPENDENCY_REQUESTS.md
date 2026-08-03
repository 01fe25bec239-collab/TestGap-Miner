# Backend Dependency Requests and Readiness Matrix

## Open Backend-owned contract response

### `BACK-DEP-001` — Versioned REST/OpenAPI contract

- Requesting/owning owner: `A2-BACKEND`
- Consumer requests: `UI-DEP-BACKEND-001`, `UI-DEP-API-002`, `DB-DEP-002`,
  and `AUTH-DEP-006`
- Contract: `CONTRACT-API-001`
- Status: `ABSENT / NOT_AUTHORIZED`
- Exact need: versioned routes and OpenAPI; request/response models;
  pagination/filter/sort; request IDs; stable safe error envelope; bearer
  Auth context; authorization failures; raw-body webhook boundary; CORS;
  health/readiness; and fixtures or mocks for consumers.
- Next action: a separately authorized contract-drafting and consumer-review
  task. `BACK-001` does not open it.

## Cross-owner dependencies

| ID / contract | Owner | Current state | Backend need |
|---|---|---|---|
| `CONTRACT-AUTH-001@1.0.0-draft.2` | A2-AUTH | Semantic contract merged; runtime absent | Principal semantics, deny-by-default actions, exact repository tuple, safe Auth failures. |
| `AUTH-002` / `AUTH-003` and `AUTH-DEP-004` | A2-AUTH / A2-DEPLOYMENT | Design metadata accepted; runtime not authorized/provisioned/tested | JWT issuer/audience/JWKS behavior and an authenticated request-context handoff before protected routes. |
| `AUTH-DEP-007` | A2-DATABASE | `PENDING` | Recoverable installation reference/equivalent before exact-tuple run authorization. |
| `AUTH-DEP-008` | A2-AGENT-WORKFLOW + A2-DATABASE | `PENDING` | Machine actor and authorized trigger before publication execution APIs. |
| `AUTH-DEP-009` | A2-DEPLOYMENT | `PENDING` | GitHub App/webhook variable names, public endpoint metadata, and least-privilege permissions before webhook runtime. |
| `CONTRACT-WORKFLOW-001@1.0.0-draft.1` | A2-AGENT-WORKFLOW | `ACKNOWLEDGED_AND_MERGED`; runtime absent | Run states, semantic request idempotency, cancellation, review, and failure behavior. |
| Workflow runtime/persistence integration handoff | Workflow/Database owners | `NOT_IMPLEMENTED / NOT_AUTHORIZED` | Required before API claims lifecycle mutation, cancellation application, or ordered event history. This audit recommends no DB task. |
| `QUEUE-003` / `CONTRACT-QUEUE-001` | A2-QUEUE | Ownership process pending / contract absent | Envelope, delivery identity, enqueue idempotency, redelivery, result, cancellation, and failure semantics before any producer. |
| Durable webhook delivery idempotency ownership | Future owner decision | `UNASSIGNED / ABSENT` | Duplicate-delivery rejection before end-to-end webhook processing. No DB or Queue implementation is recommended here. |
| `CONTRACT-EVIDENCE-001` | Evidence owner | `ABSENT / NOT_AUTHORIZED` | Evidence-card, artefact manifest/reference, access, expiry, checksum, and download behavior. |
| `CONTRACT-EVAL-001` | A2-EVALUATION | `ABSENT` | Benchmark identities, metrics, provenance, baselines, and release-gate representation. |
| `CONTRACT-SEC-001` | A2-SECURITY | `ABSENT` | Redaction, security errors/events, rate/abuse limits, retention, and artefact access policy. |
| `CONTRACT-DEPLOY-001` extensions | A2-DEPLOYMENT | Current approved contract covers Database runtime only | API liveness/readiness dependencies, object storage, runtime variables, and operational behavior. |
| Integration acceptance/handoff format | A2-INTEGRATION | DB scaffold accepted; final Backend contract not present | Final compatibility, release-readiness, and rollback acceptance. |

## Later Backend task dependency matrix

Exact task titles below are verified from the authoritative
`A2_BACKEND_MANAGER.md`.

| Task | Must be accepted/available before implementation |
|---|---|
| `BACK-002 — Control-plane foundation` | `BACK-001`; separately authorized `CONTRACT-API-001`; UI/Auth/Database consumer review; A2-DEPLOYMENT health/readiness and CORS/runtime inputs; A2-SECURITY error/redaction input where security details are exposed. |
| `BACK-003 — Run query and action API` | `BACK-002`; DB run/event/artefact/human-decision query interfaces; `CONTRACT-AUTH-001` and authenticated authorization handoff; `CONTRACT-WORKFLOW-001`; `CONTRACT-EVIDENCE-001`; stable API schemas and authorization-negative fixtures. |
| `BACK-004 — Benchmark and GitHub run creation` | `BACK-003`; benchmark/GitHub input contracts; DB-002 run-request idempotency; Auth repository scope including `AUTH-DEP-007`; request normalization and duplicate/conflict behavior in `CONTRACT-API-001`. |
| `BACK-005 — Queue and lifecycle integration` | `BACK-004`; A2-QUEUE `QUEUE-003` ownership result; accepted `CONTRACT-QUEUE-001`; `CONTRACT-WORKFLOW-001` lifecycle/cancellation behavior; Deployment-owned Queue adapter/runtime input. |
| `BACK-006 — Artefact and benchmark-summary API` | `BACK-005`; Database-owner artefact/evaluation query interface; `CONTRACT-EVIDENCE-001`; `CONTRACT-EVAL-001`; `CONTRACT-AUTH-001`; `CONTRACT-SEC-001`; Deployment-owned private storage and presigned-download adapter; UI consumer fields. |
| `BACK-007 — GitHub webhook and publication HTTP adapters` | `BACK-006`; Auth raw-body/signature verifier handoff; `AUTH-DEP-009`; durable delivery-idempotency owner decision; accepted `CONTRACT-QUEUE-001`; Workflow publication contract; `AUTH-DEP-008` machine publication actor; Deployment-owned GitHub runtime configuration. |
| `BACK-008 — Backend final acceptance` | All prior Backend tasks/contracts; Auth, Workflow, Queue, Evidence, Evaluation, Security, Deployment, UI, Database, and Integration consumer acknowledgements; full API/integration/security test evidence and rollback/handoff decision. |

No row authorizes another owner's implementation, DB-003, Queue runtime,
provider configuration, a manifest/lockfile change, or a public contract draft.
