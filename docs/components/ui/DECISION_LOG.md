# UI Decision Log

- Date: 2026-08-08
- Agent 2: `A2-UI`
- Current task: `UI-AUTH002-CONSUMER-CONFLICT-RECONCILIATION-001-A3`
- Prompt type: `DOCUMENTATION_ONLY / CONFLICT_RESOLUTION / MERGED_FRONTEND_STATE_RECONCILIATION`
- Worktree: `/Users/omkar/Documents/TestGap-Miner-wt-ui-auth002-conflict-reconciliation`
- Branch: `agent2/ui-auth002-conflict-reconciliation`
- Current evidence baseline: `006cc885161ff49be582a9fa08f353a70c31c7b1`
- Historical API-reconciliation baseline: `ab60d4573d398fb610bc2ebb813f76d0c95b33d7`
- Historical bootstrap baseline: `9ac5a242bfbfad839dd41cd51171b4f81db1be85`
- Frontend foundation: `IMPLEMENTED` / `MERGED` / `PRODUCTION_BUILDABLE`
- Frontend Auth behavior: `NOT_IMPLEMENTED` / `NOT_TESTED` / `NOT_AUTHORIZED`
- Auth runtime: `NOT_IMPLEMENTED` / `NOT_TESTED`
- Provider runtime: `NOT_PROVISIONED` / `NOT_TESTED`
- `ASSUMED`: `NONE`

`UI-DEC-001` through `UI-DEC-019` are the founding UI decisions recorded by
the bootstrap at baseline `9ac5a24`. Each is a decision about intent,
ownership, or constraint. **None of them is evidence that anything is
implemented.** No decision below alters another owner's contract.

The current normative reading of any historical decision is whatever the
**Post-merge supersession map** and the later `UI-DEC-020` onward decisions
say it is. Where the two differ, the later decision governs.

## `UI-DEC-001` — `apps/web` is the frontend root

The first-party TestGap Miner dashboard lives at `apps/web`, as a sibling of
the existing `apps/api` FastAPI service.

Historical state at the bootstrap baseline `9ac5a24`, **superseded by
`UI-DEC-027`**: `apps/web` was `ABSENT` — `ls apps/` returned exactly `api`, and
`find . -type d -name web` (excluding `.git`) returned nothing. That decision
reserved the path; it did not create it, and `UI-DOC-BOOTSTRAP-001` did not
create `apps/web`.

Current state: `apps/web` is `PRESENT`, created by the separately authorized
`UI-002` and merged through PR #26.

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

The dashboard framework is Next.js. Recorded as `NOT_IMPLEMENTED` at the
bootstrap baseline; **now `IMPLEMENTED` per `UI-DEC-027`**.

## `UI-DEC-005` — App Router

Routing uses the Next.js App Router, not the Pages Router. Recorded as
`NOT_IMPLEMENTED` at the bootstrap baseline; **now `IMPLEMENTED` per
`UI-DEC-027`**.

## `UI-DEC-006` — TypeScript

The frontend is written in TypeScript. Recorded as `NOT_IMPLEMENTED` at the
bootstrap baseline; **now `IMPLEMENTED` per `UI-DEC-027`**.

## `UI-DEC-007` — MUI

MUI is the component library and theming system. Recorded as `NOT_IMPLEMENTED`
at the bootstrap baseline; **now `IMPLEMENTED` per `UI-DEC-027`**. This does
not waive the accessibility gate: component-library defaults are not
accessibility evidence, and `UI-010` accessibility acceptance remains
outstanding.

## `UI-DEC-008` — npm

`npm` is the frontend package manager, with `package.json` and
`package-lock.json` scoped to `apps/web`.

Historical state at the bootstrap baseline `9ac5a24`, **superseded by
`UI-DEC-027`**: no `package.json`, `package-lock.json`, `tsconfig.json`, or
`next.config.*` existed anywhere in `git ls-files`, and `UI-DOC-BOOTSTRAP-001`
created none.

Current state: `apps/web/package.json`, `apps/web/package-lock.json`,
`apps/web/tsconfig.json` and `apps/web/next.config.ts` are tracked, created by
`UI-002` and merged through PR #26. The backend's `uv` tooling is unaffected,
and no root manifest or root lockfile was introduced.

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

**Historical text, partially superseded. See `UI-DEC-026` for the current
normative custody rule.** The clause reading "any non-`HttpOnly` cookie written
by UI code" below is **superseded and is not current**. Everything else in this
decision remains binding.

The UI stores no access token and no refresh token in `localStorage`. The same
prohibition covers `sessionStorage` and any non-`HttpOnly` cookie written by UI
code. Once implementation exists, this must be proven by an automated test, not
by inspection.

The `localStorage` and `sessionStorage` prohibitions are **not** weakened by
that supersession. They remain fully current and binding under `UI-DEC-026`, as
does the requirement that they be proven by an automated test rather than by
inspection.

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

No frontend implementation was authorized by the bootstrap itself. The
prohibition list below is the bootstrap-era text; **the `apps/web`, manifest,
lockfile and test entries in it are superseded by `UI-DEC-027`** because Agent 1
separately authorized `UI-002`, `UI-003` and the test foundation, which are now
merged. Every other entry remains unauthorized until Agent 1 authorizes it
explicitly.

Bootstrap-era list: creating `apps/web/**`; any application code, page, layout,
route, component, middleware, provider, browser or server Auth client, or API
client; any test; any `package.json`, `package-lock.json`, root manifest, or
root lockfile; any `.env*`, environment file, or environment schema; any CI
workflow, container, or infrastructure change.

Still unauthorized today: any `/auth/callback` route or handler; any browser or
server Auth client; any session, PKCE or OAuth-state code; any provider client;
any API client; any `.env*`, environment file, or environment schema; any root
manifest or root lockfile; and any CI workflow, container, or infrastructure
change.

Historical classification at the bootstrap baseline `9ac5a24`, **partially
superseded by `UI-DEC-027`**: `UI-001` was `PENDING_DOCUMENTATION_BOOTSTRAP`;
`UI-002` and `UI-003` were `NOT_AUTHORIZED`; `UI-004` through `UI-010` were
`BLOCKED`.

Current classification: `UI-002` and `UI-003` were subsequently authorized by
Agent 1, implemented, and merged through PR #26, PR #27 and PR #28, so their
`NOT_AUTHORIZED` classification and the corresponding `apps/web`, manifest,
lockfile and test prohibitions above are superseded. `UI-001` remains
`NOT_STARTED` and requires separate authorization. `UI-004` through `UI-010`
remain `BLOCKED / NOT_AUTHORIZED`, and every other prohibition in this decision
— `/auth/callback`, Auth clients, session code, API clients, `.env*`, CI,
containers and infrastructure — remains binding.

Recording a working architecture in `UI-DEC-004` through `UI-DEC-010` was a
decision about intent, not authorization to build it. The frontend foundation
was built only after Agent 1 separately authorized it.

## Post-merge supersession map

`UI-DEC-001` through `UI-DEC-019` above are preserved as the historical
bootstrap decisions made at baseline `9ac5a24`. Their original reasoning has
not been rewritten.

| Historical decision | Current treatment |
|---|---|
| `UI-DEC-012` | Its `CONDITIONAL / PENDING AUTH-DEP-004` conclusion is historical and superseded by `UI-DEC-021` for contract/design only. Its warning that design evidence is not runtime evidence remains binding. |
| `UI-DEC-013` | **Partially superseded by `UI-DEC-026`.** Only the clause prohibiting "any non-`HttpOnly` cookie written by UI code" is superseded. The `localStorage` prohibition, the `sessionStorage` prohibition, and the automated-test proof requirement remain fully current and binding. |
| `UI-DEC-016` | UI acceptance remains binding; its stale statement that the Auth-side record was pending is superseded by `UI-DEC-022`. |
| `UI-DEC-018` | Its `AUTH-002 NOT_READY / BLOCKED` conclusion is historical and superseded by `UI-DEC-023` for contract/design readiness only. Its statement that no implementation began remains true. |
| `UI-DEC-019` | Remains binding **except** for its `UI-002` and `UI-003` `NOT_AUTHORIZED` classification and its `apps/web` / manifest / lockfile / test prohibitions, which Agent 1 separately authorized and which PR #26, PR #27 and PR #28 have merged — see `UI-DEC-027`. Every other prohibition in it, including `/auth/callback`, Auth clients, session code, API clients, `.env*`, CI and infrastructure, remains binding and is reaffirmed by `UI-DEC-024`. |
| `UI-DEC-023` | **`HISTORICAL READINESS MILESTONE`.** Its `READY_FOR_AUTH_002_CONTRACT_AND_DESIGN` conclusion, and its "contract/design may begin only as a separate, newly authorized A2-AUTH task" clause, are historical and `SATISFIED`: that readiness was consumed by the `AUTH-002` contract drafting work, in which A2-AUTH performed the separately authorized contract/design task and produced `CONTRACT-AUTH-001@1.1.0-draft.1` on Auth PR #29. The current contract state is governed by the PR #29 consumer-review evidence and `UI-DEC-026` — `OPEN / DRAFT / SPECIFICATION_CONFLICT / NOT_IMPLEMENTATION_READY`, not `READY_TO_BEGIN`. Its no-implementation-authorization rule remains fully binding, as do `UI-004` `BLOCKED / NOT_AUTHORIZED` and provider runtime `NOT_PROVISIONED / NOT_TESTED`. |

`UI-DEC-023` is listed in this map as a later historical readiness milestone.
It is not a bootstrap decision and its inclusion does not change the
preservation statement above for `UI-DEC-001` through `UI-DEC-019`.

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
`UI-DEC-017` remain binding, including the cross-agent path boundaries — with
the single exception of the non-`HttpOnly`-cookie clause of `UI-DEC-013`, which
is superseded by `UI-DEC-026`. No storage prohibition is weakened by that
exception.

## `UI-DEC-023` — `AUTH-002` contract/design readiness (HISTORICAL READINESS MILESTONE — READINESS CONSUMED)

**This decision is a `HISTORICAL READINESS MILESTONE`. Its readiness
conclusion has been consumed/satisfied and is no longer a current-state
record. It is preserved, not deleted.**

Historical fact, preserved as recorded: at the time `UI-DEC-023` was made,
`AUTH-002` was `READY_FOR_AUTH_002_CONTRACT_AND_DESIGN` because `AUTH-DEP-004`
was satisfied for contract/design and `AUTH-DEP-010` was satisfied for
ownership/coordination. That readiness superseded `UI-DEC-018` only for the
contract/design readiness conclusion.

Historical text, `SATISFIED` and no longer readable as current state:
"Contract/design may begin only as a separate, newly authorized A2-AUTH task."
That separate authorization was subsequently granted, A2-AUTH began and
performed the authorized contract/design task, and drafted
`CONTRACT-AUTH-001@1.1.0-draft.1` on Auth PR #29. The readiness recorded here
was consumed by that drafting work.

Current `AUTH-002` contract state is therefore
`OPEN / DRAFT / SPECIFICATION_CONFLICT / NOT_IMPLEMENTATION_READY`, **not**
`READY_TO_BEGIN`. The current state is governed by the PR #29 consumer-review
evidence and by `UI-DEC-026`, not by this decision.

What remains binding from this decision:

- It began no work and authorizes no implementation of any kind.
- `AUTH-002` frontend implementation and Auth runtime implementation remain
  `NOT_AUTHORIZED`.
- `UI-004` remains `BLOCKED / NOT_AUTHORIZED`; nothing here authorizes it.
- Provider runtime remains `NOT_PROVISIONED / NOT_TESTED`.

## `UI-DEC-024` — Implementation and provider runtime remain unauthorized

**The frontend-state bullets in this decision are superseded by `UI-DEC-027`.**
The Auth and provider bullets remain fully current and binding.

Current and binding:

- `AUTH-002` frontend implementation: `NOT_AUTHORIZED`
- `AUTH-002` runtime implementation: `NOT_AUTHORIZED`
- Auth runtime: `NOT_IMPLEMENTED / NOT_TESTED`
- Provider runtime: `NOT_PROVISIONED / NOT_TESTED`
- Frontend Auth behavior: `NOT_IMPLEMENTED / NOT_TESTED / NOT_AUTHORIZED`
- Frontend Auth tests: `NOT_STARTED / NOT_TESTED`

Recorded at the `ab60d45` API-reconciliation baseline and **superseded** by
`UI-DEC-027` — these were true then and are not current:

- `apps/web`: `ABSENT` — now `PRESENT`
- Frontend implementation: `NOT_STARTED` — the foundation is now merged
- Frontend runtime: `NOT_IMPLEMENTED / NOT_TESTED` — the foundation is now
  `PRODUCTION_BUILDABLE` with merged automated regression tests

No decision in this log authorizes Auth code, `/auth/callback`, session logic,
a provider client, an API client, provisioning, staging, or publication. The
separately authorized and merged `UI-002`, `UI-003` and test-foundation work is
the only implementation authorization that has ever been granted, and it
extends to nothing further.

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

API runtime is `NOT_IMPLEMENTED / NOT_TESTED / NOT_AUTHORIZED`. Frontend Auth
behavior is `NOT_IMPLEMENTED / NOT_TESTED / NOT_AUTHORIZED`. This consumer
review creates no API, frontend, Auth, Queue, Database, Evidence, Evaluation,
Security, Deployment, or other implementation authorization.

## `UI-DEC-026` — `AUTH-002` cookie-custody conflict resolved on the UI side

A2-UI's consumer review of `CONTRACT-AUTH-001@1.1.0-draft.1`, at reviewed Auth
PR #29 head `7abe17af8e212bd2127160338ea6ef409da02101`, returned
`SPECIFICATION_CONFLICT`.

The conflict: the merged `UI-DEC-013` prohibits "any non-`HttpOnly` cookie
written by UI code", while the Auth candidate contract adopts the canonical
browser-readable `@supabase/ssr` cookie-backed session and states that
`HttpOnly` is not achievable for that session under the accepted architecture.

Agent 1 returned
`PASS / UI_AUTH_COOKIE_CONFLICT_CONFIRMED / UI_OWNED_CORRECTION_AUTHORIZED`,
accepting the `SPECIFICATION_CONFLICT` disposition and directing that the
UI-owned side of the conflict be reconciled. This decision performs that
UI-owned reconciliation and nothing else.

### Scope of supersession

This decision supersedes **only** the conflicting non-`HttpOnly`-cookie
interpretation of `UI-DEC-013`. It supersedes nothing else, and it weakens no
prohibition. Specifically preserved and still binding:

- `UI-DEC-013`'s `localStorage` prohibition;
- `UI-DEC-013`'s `sessionStorage` prohibition;
- `UI-DEC-014`'s no-duplicate-custom-token-store rule;
- `UI-DEC-015`'s `Authorization: Bearer` transport rule and its absolute
  prohibition on forwarding a refresh token to FastAPI;
- `UI-DEC-017`'s rule that UI route protection is defense-in-depth only;
- A2-SECURITY's ownership, jointly with A2-AUTH, of final cookie acceptance.

### Current normative custody rule

A2-UI must not directly persist an access token or refresh token in:

- `localStorage`;
- `sessionStorage`;
- React component state;
- React context;
- Redux;
- Zustand;
- IndexedDB;
- service-worker storage;
- an in-memory custom token cache;
- a custom cookie;
- any duplicate or shadow session store.

The only potentially permitted browser-readable session store is the canonical
Auth-owned cookie-backed session, operated exclusively through the approved
`@supabase/ssr` Auth adapter.

That exception is **`CONDITIONAL`** on A2-SECURITY accepting the final cookie
posture. Until A2-SECURITY acceptance:

- the storage design remains a contract candidate;
- browser Auth implementation is `NOT_AUTHORIZED`.

A2-UI must never:

- create the canonical session store itself;
- copy the canonical session into another store;
- manage a duplicate cookie;
- shadow the provider session;
- read or persist refresh tokens outside the Auth-owned adapter;
- initialize an independent provider client;
- weaken the `localStorage` prohibition;
- weaken the `sessionStorage` prohibition.

Refresh tokens remain prohibited from FastAPI. Access-token use remains
immediate, single-request `Authorization: Bearer` transport through the future
Auth/API boundary, with no cached copy.

### What this decision is not

This correction is **not** final Security approval for browser-readable
cookies. `HttpOnly`, `SameSite`, cookie lifetime, cookie domain, `Secure`
exceptions, CSRF, callback-correlation storage/integrity/duration, and
intended-return-state storage and integrity are **A2-SECURITY-owned and
unresolved** under `AUTH-DEP-011`. A2-UI and A3-UI decide none of them.

This correction also does **not** by itself make Auth PR #29 acceptable. It
resolves the UI-owned half only. The Auth-owned correction package remains
outstanding, and **A2-UI rereview is still required** after both the UI-owned
and the Auth-owned correction packages have been completed. Until that
rereview, `AUTH-DEP-012` stays `SPECIFICATION_CONFLICT` and is not `ACCEPTED`.

Any statement elsewhere in the UI records that all of the historical
`UI-DEC-013` remains currently binding is qualified to exclude the superseded
non-`HttpOnly`-cookie clause.

## `UI-DEC-027` — Merged frontend implementation baseline reconciled

The UI durable records are reconciled to the actual repository state at
baseline `006cc885161ff49be582a9fa08f353a70c31c7b1`.

| Item | Evidence |
|---|---|
| PR #26 — `feat(ui): add Next.js application scaffold` | Implementation commit `55fabbf452ed4a7429c8d2d075b218708db611e3`; merge commit `c5d4c8a462f6e76aa1dd4929e59012fb2823c999`; `validate` check `SUCCESS`. |
| PR #27 — `feat(ui): add MUI application shell` | Implementation commit `cbd9e99287c7a7c11c65d8ac349e8356401fc2d3`; merge commit `e7de96fc96e665fc32163dc9f26986e0e56e5510`; `validate` check `SUCCESS`. |
| PR #28 — `test(ui): add frontend regression foundation` | Implementation commit `7ad4334a5b0f7d1a6546b7c8140c359b8a5d3e6c`; merge commit `006cc885161ff49be582a9fa08f353a70c31c7b1`; `validate` check `SUCCESS`. |

Reconciled current state:

- `apps/web`: `PRESENT`
- `UI-002`: `MERGED`
- `UI-003`: `MERGED`
- Frontend regression-test foundation: `MERGED`
- Frontend foundation: `PRODUCTION_BUILDABLE`
- Next.js App Router: `IMPLEMENTED`
- TypeScript: `IMPLEMENTED`
- MUI theme and shell: `IMPLEMENTED`
- Frontend automated regression tests: `IMPLEMENTED`

Unchanged and still binding:

- Auth frontend: `NOT_IMPLEMENTED / NOT_TESTED / NOT_AUTHORIZED`
- Auth runtime: `NOT_IMPLEMENTED / NOT_TESTED`
- Provider runtime: `NOT_PROVISIONED / NOT_TESTED`
- `UI-004`: `BLOCKED / NOT_AUTHORIZED`
- `/auth/callback`: `RESERVED / NOT_IMPLEMENTED`

`UI-DEC-001`'s reservation of `apps/web` as the frontend root is now satisfied
rather than merely reserved; `UI-DEC-004` through `UI-DEC-008` — Next.js, App
Router, TypeScript, MUI and npm — are now `IMPLEMENTED` rather than
`NOT_IMPLEMENTED`. `UI-DEC-009`'s separation from the FastAPI backend, and
`UI-DEC-010`'s `NOT_PROVEN / NOT_TESTED` Vercel deployment status, are
unchanged.

**A merged, buildable, tested frontend foundation is never evidence that Auth
works.** No Auth client, session code, provider client, protected route, or
`/auth/callback` handler exists in the merged `apps/web`, and none is
authorized.
