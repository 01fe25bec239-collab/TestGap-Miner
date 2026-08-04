# UI Decision Log

- Date: 2026-08-04
- Agent 2: `A2-UI`
- Current task: `UI-API-DEPENDENCY-RECONCILIATION-001-A3`
- Prompt type: `REBASE_THEN_FOCUSED_DOCUMENTATION_REPAIR_ONLY`
- Worktree: `/Users/omkar/Documents/TestGap-Miner-wt-ui-auth-dependency-reconciliation`
- Branch: `agent2/ui-auth-dependency-reconciliation`
- Current evidence baseline: `ab60d4573d398fb610bc2ebb813f76d0c95b33d7`
- Historical bootstrap baseline: `9ac5a242bfbfad839dd41cd51171b4f81db1be85`
- Frontend implementation: `NOT_STARTED`
- Frontend runtime: `NOT_IMPLEMENTED` / `NOT_TESTED`
- `ASSUMED`: `NONE`

`UI-DEC-001` through `UI-DEC-019` are the founding UI decisions recorded by
this bootstrap. Each is a decision about intent, ownership, or constraint.
**None of them is evidence that anything is implemented.** No decision below
alters another owner's contract.

## `UI-DEC-001` — `apps/web` is the frontend root

The first-party TestGap Miner dashboard lives at `apps/web`, as a sibling of
the existing `apps/api` FastAPI service.

State: `apps/web` is `ABSENT` at the evidence baseline — `ls apps/` returns
exactly `api`, and `find . -type d -name web` (excluding `.git`) returns
nothing. This decision reserves the path; it does not create it.
`UI-DOC-BOOTSTRAP-001` did not create `apps/web`.

## `UI-DEC-002` — A2-UI owns the frontend

A2-UI is the long-lived owner of `apps/web/**`, frontend manifests and
lockfiles scoped to `apps/web`, frontend tests, `docs/components/ui/**`, and
`docs/specifications/A2_UI_MANAGER.md`. A3-UI is a temporary, task-scoped agent
that acts only within an explicit prompt allowlist and never merges its own
work.

## `UI-DEC-003` — Non-UI owner boundaries

A2-UI does not own and must not redefine:

| Domain | Owner |
|---|---|
| Callback and session semantics, identity resolution, token custody rules, PKCE and OAuth-state semantics, `CONTRACT-AUTH-001` | `A2-AUTH` |
| Provider selection and provisioning, deployed callback registration, domains, TLS, secret injection, Auth environment-variable registration, `CONTRACT-DEPLOY-001` | `A2-DEPLOYMENT` |
| FastAPI JWT/JWKS validation, authenticated request context, backend authorization, API error envelope, backend CORS, `CONTRACT-API-001` | `A2-BACKEND` |
| Final cookie, CSRF, and OAuth-state security acceptance, `CONTRACT-SEC-001` | `A2-SECURITY` with `A2-AUTH` |
| Schema, migrations, persistence | `A2-DATABASE` |
| Run state, workflow steps, evidence, queue contracts | `A2-AGENT-WORKFLOW` |
| Benchmark cases, metrics, release gates | `A2-EVALUATION` |
| Release-readiness decision | `A2-INTEGRATION` |

Corollaries, both binding: **A3-AUTH may not modify UI-owned paths without
explicit A2-UI coordination**, and **A3-UI may not modify Auth-owned paths**
under any circumstance.

## `UI-DEC-004` — Next.js

The dashboard framework is Next.js. `NOT_IMPLEMENTED`.

## `UI-DEC-005` — App Router

Routing uses the Next.js App Router, not the Pages Router. `NOT_IMPLEMENTED`.

## `UI-DEC-006` — TypeScript

The frontend is written in TypeScript. `NOT_IMPLEMENTED`.

## `UI-DEC-007` — MUI

MUI is the component library and theming system. `NOT_IMPLEMENTED`. This does
not waive the accessibility gate: component-library defaults are not
accessibility evidence.

## `UI-DEC-008` — npm

`npm` is the frontend package manager, with `package.json` and
`package-lock.json` scoped to `apps/web`.

State: no `package.json`, `package-lock.json`, `tsconfig.json`, or
`next.config.*` exists anywhere in `git ls-files` at the evidence baseline, and
`UI-DOC-BOOTSTRAP-001` created none. The backend's `uv` tooling is unaffected.

## `UI-DEC-009` — Separate FastAPI backend

The frontend is a separate application that consumes the FastAPI service at
`apps/api` over HTTP. The UI does not embed backend logic, does not read the
database, and does not perform authorization.

State: `apps/api/app/main.py` is three lines and exposes no routes.

## `UI-DEC-010` — Vercel deployment target

Vercel is the frontend deployment target. `NOT_PROVEN` / `NOT_TESTED`. No
deployment exists, and no deployed callback, domain, or TLS configuration is
accepted. Provisioning is owned by A2-DEPLOYMENT.

## `UI-DEC-011` — `/auth/callback` route ownership

`/auth/callback` is reserved as a UI-owned route.

- **A2-UI owns** the route's existence, page, layout, loading and error UX,
  redirect targets, user-facing copy, and accessibility.
- **A2-AUTH owns** the callback and session semantics — what the exchange
  means, how a session is established, how identity is resolved, and token
  lifetime and refresh behavior.
- **A2-DEPLOYMENT owns** the deployed callback registration, the exact URL
  allowlist, domains, TLS, secret injection, and Auth environment-variable
  registration.
- **A2-SECURITY with A2-AUTH** owns final cookie, CSRF, and OAuth-state
  security acceptance.

State: `RESERVED / NOT_IMPLEMENTED`. No route, page, or handler exists.

## `UI-DEC-012` — Supabase Auth integration is conditional

Supabase Auth integration for the dashboard is classified
**`CONDITIONAL / PENDING AUTH-DEP-004`**.

Until A2-DEPLOYMENT accepts `AUTH-DEP-004`, A2-UI must not represent any of the
following as an accepted Deployment decision: the final provider, the canonical
issuer, the audience, the JWKS URL or key source, authorization or token
endpoints, exact callback URLs, which side terminates the callback in a
deployed environment, cookie settings, Auth environment-variable names,
production domains, or TLS termination.

No provider-specific browser or server Auth client may be built under this
classification. Provider provisioning is `NOT_PROVEN` / `NOT_TESTED`.

## `UI-DEC-013` — No access or refresh token in `localStorage`

The UI stores no access token and no refresh token in `localStorage`. The same
prohibition covers `sessionStorage` and any non-`HttpOnly` cookie written by UI
code. Once implementation exists, this must be proven by an automated test, not
by inspection.

## `UI-DEC-014` — No duplicate custom token store

The UI does not build a parallel token cache, context, or singleton that
shadows the Auth-owned session source. One custody model exists, and A2-AUTH
owns it.

## `UI-DEC-015` — Token transport to FastAPI

- The accepted access-token transport to FastAPI is the **`Authorization`
  header**, carrying the access token as a bearer credential.
- **The refresh token is never forwarded to FastAPI.** It never appears in any
  request the UI originates.

These are UI-side transport and custody rules. They do not define token
issuance, lifetime, rotation, or validation, all of which are Auth-owned and
Backend-owned.

## `UI-DEC-016` — `AUTH-DEP-010` accepted with constraints

A2-UI, as the owning manager of `AUTH-DEP-010`, records
`ACCEPTED_WITH_CONSTRAINTS` via `AUTH-DEP-010-RESPONSE-001-R1`.

Accepted:

1. A first-party dashboard will exist, rooted at `apps/web`.
2. A2-UI owns the frontend and the protected UI paths.
3. A2-UI owns the `/auth/callback` route and its user-facing UX.
4. The browser-session custody model is stated: no token in `localStorage`, no
   duplicate custom token store, refresh token never forwarded to FastAPI,
   bearer `Authorization` transport, UI route protection as UX and
   defense-in-depth only, FastAPI authorization authoritative.

Constraints attached to the acceptance:

1. Callback and session semantics remain A2-AUTH-owned; A2-UI owns the route
   and UX, not the meaning.
2. Provider selection and provisioning, deployed callback registration,
   domains, TLS, secret injection, and Auth environment-variable registration
   remain A2-DEPLOYMENT-owned and unresolved via `AUTH-DEP-004`.
3. Final cookie, CSRF, and OAuth-state security acceptance remains A2-SECURITY
   with A2-AUTH.
4. A3-AUTH may not modify UI-owned paths without explicit A2-UI coordination.
5. A3-UI may not modify Auth-owned paths.
6. Acceptance authorizes **no** frontend implementation and **no** frontend
   Auth integration test. It resolves an ownership question only.

Record state: the A2-AUTH-side entry still reads `Approval status: PENDING`
(`docs/components/auth/DEPENDENCY_REQUESTS.md:300`). That file is Auth-owned
and forbidden to this task; reconciliation is tracked as `UI-ISSUE-012`.

## `UI-DEC-017` — UI route protection is defense-in-depth; backend authorization is authoritative

A UI redirect, route guard, or hidden control is a usability affordance and a
second layer of defence. It is never an authorization decision.

Every access decision is made and enforced server-side by FastAPI. The UI must
behave correctly — and must not leak data or misreport success — when the
backend denies a request the UI believed was permitted. Any future UI change
that would make a UI-side check load-bearing for security is a
`SPECIFICATION_CONFLICT` and must be escalated.

## `UI-DEC-018` — `AUTH-002` remains blocked

`AUTH-002` — Dashboard sign-in and session contract — remains
`NOT_READY / BLOCKED`. Its direct remaining blocker is `AUTH-DEP-004`
(`PENDING`, owner A2-DEPLOYMENT); `AUTH-DEP-010` is the additional frontend
implementation and ownership constraint.

`UI-DOC-BOOTSTRAP-001` did not begin `AUTH-002` and did not change its status.
A2-UI's acceptance of `AUTH-DEP-010` removes an ownership constraint; it does
not unblock `AUTH-002`.

## `UI-DEC-019` — Implementation remains unauthorized

No frontend implementation is authorized by this bootstrap. Specifically, the
following remain unauthorized until Agent 1 authorizes them explicitly:
creating `apps/web/**`; any application code, page, layout, route, component,
middleware, provider, browser or server Auth client, or API client; any test;
any `package.json`, `package-lock.json`, root manifest, or root lockfile; any
`.env*`, environment file, or environment schema; any CI workflow, container,
or infrastructure change.

`UI-001` is `PENDING_DOCUMENTATION_BOOTSTRAP`. `UI-002` and `UI-003` are
`NOT_AUTHORIZED`. `UI-004` through `UI-010` are `BLOCKED`.

Recording a working architecture in `UI-DEC-004` through `UI-DEC-010` is a
decision about intent. It is not authorization to build it.

## Post-merge supersession map

`UI-DEC-001` through `UI-DEC-019` above are preserved as the historical
bootstrap decisions made at baseline `9ac5a24`. Their original reasoning has
not been rewritten.

| Historical decision | Current treatment |
|---|---|
| `UI-DEC-012` | Its `CONDITIONAL / PENDING AUTH-DEP-004` conclusion is historical and superseded by `UI-DEC-021` for contract/design only. Its warning that design evidence is not runtime evidence remains binding. |
| `UI-DEC-016` | UI acceptance remains binding; its stale statement that the Auth-side record was pending is superseded by `UI-DEC-022`. |
| `UI-DEC-018` | Its `AUTH-002 NOT_READY / BLOCKED` conclusion is historical and superseded by `UI-DEC-023` for contract/design readiness only. Its statement that no implementation began remains true. |
| `UI-DEC-019` | Remains binding and is reaffirmed by `UI-DEC-024`; dependency acceptance does not authorize implementation. |

## `UI-DEC-020` — UI bootstrap is merged

`UI-DOC-BOOTSTRAP-001` is `PASS / VERIFIED_COMPLETE / MERGED`. The UI manager
specification and six UI durable records merged through PR #19, merge commit
`4c4b2e3aefb3529cb9acad2860f050247b47e6b2`. A2-UI is
`INITIALIZED / DURABLE_RECORDS_MERGED`.

The original uncommitted bootstrap state remains historical evidence. The
specification at `docs/specifications/A2_UI_MANAGER.md` retains that snapshot
and is not reconciled by this task.

## `UI-DEC-021` — `AUTH-DEP-004` accepted for contract and design

`AUTH-DEP-004` is `ACCEPTED_WITH_CONSTRAINTS / MERGED_VIA_PR_20 /
SATISFIED_FOR_AUTH_CONTRACT_AND_DESIGN`. This supersedes only the pending-state
portion of `UI-DEC-012`.

Accepted design values:

- Provider: `SUPABASE_AUTH_WITH_GITHUB_OAUTH`
- Architecture: `APPROVED_FOR_AUTH_CONTRACT_AND_DESIGN`
- Canonical issuer: `https://<SUPABASE_PROJECT_REF>.supabase.co/auth/v1`
- Audience: `authenticated`
- JWKS:
  `https://<SUPABASE_PROJECT_REF>.supabase.co/auth/v1/.well-known/jwks.json`
- Deployed Dashboard callback: `${DASHBOARD_ORIGIN}/auth/callback`
- Local callback: `http://localhost:3000/auth/callback`
- OAuth termination: Supabase Auth
- FastAPI receives Supabase JWT access tokens only.
- Refresh tokens are never forwarded to FastAPI.
- Redirects require exact-match allowlisting.
- Issuer comparison is exact and case-sensitive; independent issuer
  normalization is prohibited.

These values do not prove a provisioned Supabase project, configured GitHub
OAuth, deployed Vercel project, production hostname, TLS, registered callbacks,
injected environment values or secrets, or working callback/session behavior.

## `UI-DEC-022` — `AUTH-DEP-010` acknowledged and reconciled

`AUTH-DEP-010` is `ACCEPTED_WITH_CONSTRAINTS / ACKNOWLEDGED_BY_A2_AUTH /
UI_OWNERSHIP_ESTABLISHED_VIA_PR_19 / AUTH_RECONCILED_VIA_PR_21`. PR #21
supersedes the stale synchronization conclusion in `UI-DEC-016`.

The accepted ownership boundary remains:

- A2-UI owns UI durable records, future authorized `apps/web` implementation,
  the user-facing `/auth/callback` route and UX, frontend session-state
  presentation, frontend Auth integration and tests after authorization, and
  accessibility.
- A2-AUTH owns callback/session semantics, identity resolution, token custody,
  token lifetime and refresh semantics, PKCE, and OAuth-state semantics.
- A2-DEPLOYMENT owns provisioning, deployed domains, callback registration,
  TLS, environment-variable registration, and secret injection.
- A2-SECURITY with A2-AUTH owns final cookie, CSRF, and OAuth-state security
  acceptance.

All custody and enforcement constraints in `UI-DEC-013` through
`UI-DEC-017` remain binding, including the cross-agent path boundaries.

## `UI-DEC-023` — `AUTH-002` contract/design is ready

`AUTH-002` is `READY_FOR_AUTH_002_CONTRACT_AND_DESIGN` because
`AUTH-DEP-004` is satisfied for contract/design and `AUTH-DEP-010` is
satisfied for ownership/coordination. This supersedes `UI-DEC-018` only for
the contract/design readiness conclusion.

Contract/design may begin only as a separate, newly authorized A2-AUTH task.
This decision does not begin the work and authorizes no implementation.

## `UI-DEC-024` — Implementation and provider runtime remain unauthorized

- `AUTH-002` frontend implementation: `NOT_AUTHORIZED`
- `AUTH-002` runtime implementation: `NOT_AUTHORIZED`
- Provider runtime: `NOT_PROVISIONED / NOT_TESTED`
- `apps/web`: `ABSENT`
- Frontend implementation: `NOT_STARTED`
- Frontend runtime: `NOT_IMPLEMENTED / NOT_TESTED`
- Frontend Auth tests: `NOT_STARTED / NOT_TESTED`

No decision in this log authorizes code, routes, components, tests, manifests,
lockfiles, configuration, provisioning, staging, or publication.

## `UI-DEC-025` — API draft consumer review partially satisfies the UI dependency

`CONTRACT-API-001@0.1.0-draft.1` is
`PRESENT / DRAFT_FOR_CONSUMER_REVIEW / NOT_IMPLEMENTATION_READY`. A2-UI has
completed manager-level consumer review. `UI-DEP-BACKEND-001` is
`PARTIALLY_SATISFIED_BY_CONTRACT_API_001_DRAFT`; it is not fully satisfied.

The draft documents these proposed shared transport conventions:

- `/api/v1` application paths;
- `Authorization: Bearer` access-token transport;
- refresh-token forwarding is `PROHIBITED`;
- a safe `error.code/message/request_id/details` envelope;
- `X-Request-ID` and `X-Correlation-ID`;
- shared opaque cursor pagination;
- polling of accepted operations through the `Location` header.

The following remain unresolved and are not frozen by this UI decision:

- final authenticated context:
  `UNRESOLVED / AUTH_OWNED / RUNTIME_HANDOFF_NOT_FROZEN`;
- exact `403` versus concealed `404` disclosure:
  `UNRESOLVED_PENDING_AUTH_AND_SECURITY`;
- CORS: `UNRESOLVED / DEPLOYMENT_AND_SECURITY_INPUT_REQUIRED /
  BACKEND_CONFIGURATION_NOT_DEFINED`;
- endpoint-specific projections and actions: `PARTIAL / OWNER_DEPENDENT`,
  including incomplete Workflow projections, absent Evidence/Evaluation
  projections, unresolved Queue delivery, and unauthorized DB-003 inputs;
- validating OpenAPI/client fixtures and complete endpoint models.

API runtime is `NOT_IMPLEMENTED / NOT_TESTED / NOT_AUTHORIZED`. Frontend
runtime is `NOT_IMPLEMENTED / NOT_TESTED / NOT_AUTHORIZED`. This consumer
review creates no API, frontend, Auth, Queue, Database, Evidence, Evaluation,
Security, Deployment, or other implementation authorization.
