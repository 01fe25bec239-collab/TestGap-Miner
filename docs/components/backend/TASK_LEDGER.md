# Backend Task Ledger

| Task | Status | Evidence / next action |
|---|---|---|
| `BACK-001` — API and repository audit | `PASS / VERIFIED_COMPLETE / A2_BACKEND_ACCEPTED / MERGED` | Documentation-only audit merged through PR #22 at baseline `7706f51`. |
| `BACK-001-C1` — authoritative task-ledger correction | `PASS / VERIFIED_COMPLETE / A2_BACKEND_ACCEPTED / MERGED` | Exact `BACK-003` through `BACK-008` titles reconciled to the Backend manager specification. |
| `BACK-CONTRACT-API-001` — draft `CONTRACT-API-001` and consumer-review package | `IMPLEMENTED_AS_DRAFT / PENDING_A2_BACKEND_AND_CONSUMER_REVIEW` | `CONTRACT-API-001@0.1.0-draft.1`; nine open owner-review requests; documentation only. Next: A2-BACKEND review and dispatch. |
| `BACK-002` — Control-plane foundation | `NOT_STARTED / BLOCKED` | Requires accepted applicable contract surfaces and UI/Auth/Database/Deployment/Security review. |
| `BACK-003` — Run query and action API | `NOT_STARTED / BLOCKED` | Requires `BACK-002`, DB query interfaces including DB-003 where needed, Auth handoff, Workflow/Evidence contracts, and accepted schemas. |
| `BACK-004` — Benchmark and GitHub run creation | `NOT_STARTED / BLOCKED` | Requires `BACK-003`, Evaluation/GitHub inputs, DB-002 idempotency, Auth exact tuple, and accepted duplicate behavior. |
| `BACK-005` — Queue and lifecycle integration | `NOT_STARTED / BLOCKED` | Requires `BACK-004`, A2-QUEUE ownership result, accepted `CONTRACT-QUEUE-001`, Workflow lifecycle semantics, and Deployment Queue adapter. |
| `BACK-006` — Artefact and benchmark-summary API | `NOT_STARTED / BLOCKED` | Requires `BACK-005`, Database query interfaces, Evidence/Evaluation/Security contracts, storage adapter, and UI fields. |
| `BACK-007` — GitHub webhook and publication HTTP adapters | `NOT_STARTED / BLOCKED` | Requires `BACK-006`, Auth verifier, durable replay owner decision, Queue/Workflow publication contracts, machine actor, and GitHub runtime configuration. |
| `BACK-008` — Backend final acceptance | `NOT_STARTED / BLOCKED` | Requires all prior tasks, nine consumer decisions, full API/OpenAPI/client/integration/security evidence, and release/rollback acceptance. |

## Boundary

`BACK-CONTRACT-API-001` authorizes Markdown under `docs/api/` and Backend
records only. It authorizes no route, runtime schema, service, test, Database
change, Queue/worker code, provider setting, manifest/lockfile, environment,
deployment, UI, CI, container, stage, commit, push, pull request, or merge.
