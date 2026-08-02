# UI Decision Log

- Date: 2026-08-02
- Agent 2: `A2-UI`
- Current task: `UI-DOC-BOOTSTRAP-001`
- Prompt type: `DOCUMENTATION_ONLY_BOOTSTRAP`
- Worktree: `/Users/omkar/Documents/TestGap-Miner-wt-ui-bootstrap`
- Branch: `agent2/ui-bootstrap-authdep010`
- Evidence baseline: `9ac5a242bfbfad839dd41cd51171b4f81db1be85`
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
