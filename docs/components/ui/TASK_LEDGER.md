# UI Task Ledger

- Date: 2026-08-03
- Agent 2: `A2-UI`
- Paired Agent 3: `A3-UI`
- Current task: `UI-AUTH-DEPENDENCY-RECONCILIATION-001-A3-C1`
- Parent manager task: `UI-AUTH-DEPENDENCY-RECONCILIATION-001`
- Prompt type: `POST_MERGE_UI_DURABLE_STATE_RECONCILIATION`
- Current evidence baseline: `ba4247af2195d4c8e60cb9990f616a95f2c54d54`
- A2-UI manager: `INITIALIZED / DURABLE_RECORDS_MERGED`
- `apps/web`: `ABSENT`
- Frontend runtime: `NOT_IMPLEMENTED / NOT_TESTED`
- Provider runtime: `NOT_PROVISIONED / NOT_TESTED`
- `ASSUMED`: `NONE`

## Documentation and dependency reconciliation

| Task | Status | Evidence / effect |
|---|---|---|
| `A1-UI-BOOTSTRAP-001` — Agent 1 UI component initialization | `PASS / BOOTSTRAP_INITIALIZED / EVIDENCE_RECONCILED` | Historical bootstrap evidence remains at baseline `9ac5a24`; no implementation was created. |
| `UI-DOC-BOOTSTRAP-001` — UI documentation bootstrap | `PASS / VERIFIED_COMPLETE / MERGED` | Manager specification and six UI durable records merged through PR #19, merge commit `4c4b2e3aefb3529cb9acad2860f050247b47e6b2`. |
| `AUTH-DEP-004` — Human sign-in and JWT/IdP deployment metadata | `ACCEPTED_WITH_CONSTRAINTS / MERGED_VIA_PR_20 / SATISFIED_FOR_AUTH_CONTRACT_AND_DESIGN` | Provider architecture and metadata templates are accepted for design only. Runtime provisioning remains absent and untested. |
| `AUTH-DEP-010-RESPONSE-001-R1` — Dashboard frontend ownership | `PASS / ACCEPTED_WITH_CONSTRAINTS / ACKNOWLEDGED_BY_A2_AUTH / UI_OWNERSHIP_ESTABLISHED_VIA_PR_19 / AUTH_RECONCILED_VIA_PR_21` | UI ownership established via PR #19 and reconciled by A2-AUTH via PR #21. Ownership resolution authorizes no implementation. |
| `AUTH-002` — Dashboard sign-in and session contract | `READY_FOR_AUTH_002_CONTRACT_AND_DESIGN / IMPLEMENTATION_NOT_AUTHORIZED` | Contract/design may begin only under a separate, newly authorized A2-AUTH task. Frontend and runtime implementation remain `NOT_AUTHORIZED`; provider runtime remains `NOT_PROVISIONED / NOT_TESTED`. |

## UI task graph

| Task | Status | Evidence / blocker |
|---|---|---|
| `UI-001` — Frontend and contract reconciliation | `NOT_STARTED / REQUIRES_SEPARATE_AUTHORIZATION` | Documentation bootstrap is merged, but no continuation or implementation authority is implied. This inspection-only task must be authorized separately. |
| `UI-002` — `apps/web` Next.js App Router + TypeScript scaffold, npm manifest and lockfile | `NOT_AUTHORIZED` | Requires explicit authorization to create `apps/web/**`, a frontend manifest, and lockfile. |
| `UI-003` — MUI theme, layout shell, navigation, accessibility baseline | `NOT_AUTHORIZED` | Requires `UI-002` and separate authorization. |
| `UI-004` — Authenticated session UX, `/auth/callback` route and callback UX, route protection as defense-in-depth | `BLOCKED / NOT_AUTHORIZED` | Provider design is accepted, so pending `AUTH-DEP-004` is no longer a blocker. Remaining blockers are separate authorization; `UI-002` and `UI-003`; complete A2-AUTH callback/session, PKCE, OAuth-state, refresh and sign-out semantics; A2-SECURITY with A2-AUTH cookie/CSRF/OAuth-state acceptance; and A2-DEPLOYMENT runtime provisioning, callback registration, domain, TLS, secret injection and test configuration. |
| `UI-005` — Typed API client, bearer transport, error-envelope handling, request correlation | `BLOCKED / NOT_AUTHORIZED` | Blocked by absent `CONTRACT-API-001`, authenticated request context, error envelope, and Backend CORS, plus `UI-002`. |
| `UI-006` — Run intake, run list, run detail, workflow-state presentation | `BLOCKED / NOT_AUTHORIZED` | Blocked by `UI-005` and absent UI-facing `CONTRACT-WORKFLOW-001` projection. |
| `UI-007` — Evidence-card UI and artefact presentation | `BLOCKED / NOT_AUTHORIZED` | Blocked by `UI-005`, `UI-006`, and absent UI-facing `CONTRACT-EVIDENCE-001` projection. |
| `UI-008` — Human review and decision controls | `BLOCKED / NOT_AUTHORIZED` | Blocked by `UI-004`, `UI-007`, authoritative Backend authorization, and Workflow/Auth human-decision semantics. Prohibited controls remain absent by construction. |
| `UI-009` — Benchmark dashboard | `BLOCKED / NOT_AUTHORIZED` | Blocked by `UI-005` and absent `CONTRACT-EVAL-001` benchmark surface. |
| `UI-010` — UI final acceptance | `BLOCKED / NOT_AUTHORIZED` | Blocked by all prior UI work, provider runtime evidence, accessibility, Security/Auth acceptance, Deployment callback/domain/TLS evidence, and A2-INTEGRATION readiness. |

## Summary

`UI-DOC-BOOTSTRAP-001` is merged. `AUTH-DEP-004` is satisfied for Auth
contract/design, and `AUTH-DEP-010` is acknowledged and reconciled through PR
#21. Neither dependency is pending.

**No UI implementation task is ready.** `UI-001` is `NOT_STARTED` and needs
separate authorization. `UI-002` and `UI-003` are `NOT_AUTHORIZED`.
`UI-004` through `UI-010` retain their actual remaining dependency and
authorization blockers. `apps/web` remains `ABSENT`; frontend implementation
is `NOT_STARTED`; frontend runtime and Auth tests remain untested.
