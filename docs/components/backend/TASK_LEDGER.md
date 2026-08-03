# Backend Task Ledger

| Task | Status | Evidence / next action |
|---|---|---|
| `BACK-001` — API and repository audit | `PASS / VERIFIED_COMPLETE / A2_BACKEND_ACCEPTED` | Documentation-only inventory, gap assessment, dependency matrix, and command evidence. No runtime or contract created. |
| `BACK-001-C1` — authoritative task-ledger correction | `PASS / VERIFIED_COMPLETE / A2_BACKEND_ACCEPTED` | Exact `BACK-003` through `BACK-008` titles verified against the authoritative Backend manager specification and corrected in five Backend records. |
| Future `CONTRACT-API-001` draft/review task | `NOT_AUTHORIZED` | Recommended next A2-BACKEND task. Must be separately authorized and reviewed by UI, Auth, Database, Workflow, Evaluation, Deployment, Security, and Integration consumers as applicable. |
| `BACK-002` — Control-plane foundation | `NOT_STARTED / BLOCKED` | Requires a separately authorized, reviewed `CONTRACT-API-001` and operational owner inputs. |
| `BACK-003` — Run query and action API | `NOT_STARTED / BLOCKED` | Requires `BACK-002`, DB query interfaces, Auth context/authorization, Workflow/Evidence contracts, and stable API schemas. |
| `BACK-004` — Benchmark and GitHub run creation | `NOT_STARTED / BLOCKED` | Requires `BACK-003`, input contracts, DB idempotency, and Auth repository scope. |
| `BACK-005` — Queue and lifecycle integration | `NOT_STARTED / BLOCKED` | Requires `BACK-004`, A2-QUEUE `QUEUE-003`, accepted `CONTRACT-QUEUE-001`, Workflow lifecycle semantics, and a Deployment Queue adapter. |
| `BACK-006` — Artefact and benchmark-summary API | `NOT_STARTED / BLOCKED` | Requires `BACK-005`, Database artefact/evaluation query interfaces, Evidence/Evaluation/Security contracts, and the storage adapter. |
| `BACK-007` — GitHub webhook and publication HTTP adapters | `NOT_STARTED / BLOCKED` | Requires `BACK-006`, Auth verifier, Workflow publication contract, durable webhook idempotency, Queue contract, and GitHub runtime configuration. |
| `BACK-008` — Backend final acceptance | `NOT_STARTED / BLOCKED` | Requires all prior tasks and cross-owner acceptance evidence. |

## Boundary

No route, schema, service, test, contract, Queue/provider configuration,
Database model/migration, Auth/webhook runtime, deployment/CI/environment/UI,
manifest, or lockfile change is authorized by `BACK-001`.
