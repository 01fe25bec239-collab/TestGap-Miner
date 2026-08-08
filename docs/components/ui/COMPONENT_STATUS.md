# UI Component Status

- Date: 2026-08-08
- Agent 2: `A2-UI`
- Paired Agent 3: `A3-UI`
- Current task: `UI-AUTH002-CONSUMER-CONFLICT-RECONCILIATION-001-A3`
- Parent manager task: `UI-AUTH002-CONSUMER-CONFLICT-RECONCILIATION-001`
- Prompt type: `DOCUMENTATION_ONLY / CONFLICT_RESOLUTION / MERGED_FRONTEND_STATE_RECONCILIATION`
- Scope: `UNCOMMITTED_DOCUMENTATION_EDITS_ONLY`
- Repository: `01fe25bec239-collab/TestGap-Miner`
- Worktree: `/Users/omkar/Documents/TestGap-Miner-wt-ui-auth002-conflict-reconciliation`
- Branch: `agent2/ui-auth002-conflict-reconciliation`
- Current evidence baseline: `006cc885161ff49be582a9fa08f353a70c31c7b1`
- Historical API-reconciliation baseline: `ab60d4573d398fb610bc2ebb813f76d0c95b33d7`
- Historical bootstrap baseline: `9ac5a242bfbfad839dd41cd51171b4f81db1be85`
- Specification snapshot: `docs/specifications/A2_UI_MANAGER.md` — preserved, not reconciled by this task
- `ASSUMED`: `NONE`

## Manager state

`A2-UI` is `INITIALIZED / DURABLE_RECORDS_MERGED`. The bootstrap package
merged through PR #19 at merge commit
`4c4b2e3aefb3529cb9acad2860f050247b47e6b2`. Initialization remains a
documentation event only; it authorizes no Auth runtime work.

A2-UI has since merged the frontend foundation through PR #26, PR #27 and PR
#28. That foundation is frontend evidence only. **It is not evidence that Auth,
the provider, the callback, or any session behavior works.**

## Current state

| Area | State | Evidence / next action |
|---|---|---|
| `UI-DOC-BOOTSTRAP-001` | `PASS / VERIFIED_COMPLETE / MERGED` | UI manager specification and six durable records merged through PR #19. |
| `UI-002` — `apps/web` Next.js App Router + TypeScript scaffold | `IMPLEMENTED / A2_UI_REVIEWED / COMMITTED / PUSHED / PR_CHECKS_PASSED / MERGED` | PR #26; implementation commit `55fabbf452ed4a7429c8d2d075b218708db611e3`; merge commit `c5d4c8a462f6e76aa1dd4929e59012fb2823c999`; `validate` check `SUCCESS`. |
| `UI-003` — MUI theme, application shell, navigation, accessibility baseline | `IMPLEMENTED / A2_UI_REVIEWED / ACCESSIBILITY_CORRECTION_APPLIED / COMMITTED / PUSHED / PR_CHECKS_PASSED / MERGED` | PR #27; implementation commit `cbd9e99287c7a7c11c65d8ac349e8356401fc2d3`; merge commit `e7de96fc96e665fc32163dc9f26986e0e56e5510`; `validate` check `SUCCESS`. |
| Frontend automated regression-test foundation | `IMPLEMENTED / A2_UI_REVIEWED / COMMITTED / PUSHED / PR_CHECKS_PASSED / MERGED` | PR #28; implementation commit `7ad4334a5b0f7d1a6546b7c8140c359b8a5d3e6c`; merge commit `006cc885161ff49be582a9fa08f353a70c31c7b1`; `validate` check `SUCCESS`. |
| Frontend foundation | `PRODUCTION_BUILDABLE` | Established by the merged `validate` checks on PR #26, PR #27 and PR #28. Buildability is not Auth, provider, or runtime session evidence. |
| `AUTH-DEP-004` | `ACCEPTED_WITH_CONSTRAINTS / MERGED_VIA_PR_20 / SATISFIED_FOR_AUTH_CONTRACT_AND_DESIGN` | Deployment decision merged through PR #20; accepted values are design-only. |
| `AUTH-DEP-010` | `ACCEPTED_WITH_CONSTRAINTS / ACKNOWLEDGED_BY_A2_AUTH / UI_OWNERSHIP_ESTABLISHED_VIA_PR_19 / AUTH_RECONCILED_VIA_PR_21` | A2-AUTH reconciled the UI ownership boundary through PR #21. |
| `AUTH-002` contract/design | `DRAFTED / DRAFT_FOR_CONSUMER_REVIEW / SPECIFICATION_CONFLICT / NOT_IMPLEMENTATION_READY` | `CONTRACT-AUTH-001@1.1.0-draft.1` has already been drafted by A2-AUTH under its own separate authorization. Auth PR #29 is `OPEN / DRAFT / NOT_MERGED`; reviewed Auth head `7abe17af8e212bd2127160338ea6ef409da02101`. A2-UI consumer review returned `SPECIFICATION_CONFLICT`. The UI-owned correction is applied by `UI-DEC-026`. The Auth-owned correction remains required, A2-SECURITY acceptance remains pending, and A2-UI rereview of the corrected head remains required. The contract is **not** accepted. `AUTH-002` frontend implementation remains `NOT_AUTHORIZED` and `AUTH-002` Auth runtime implementation remains `NOT_AUTHORIZED`. Supersedes the historical `READY_FOR_AUTH_002_CONTRACT_AND_DESIGN` readiness milestone recorded by `UI-DEC-023`. |
| `AUTH-002` frontend implementation | `NOT_AUTHORIZED` | No frontend work is authorized by dependency acceptance. |
| `AUTH-002` runtime implementation | `NOT_AUTHORIZED` | No Auth runtime work is authorized by dependency acceptance. |
| Auth runtime | `NOT_IMPLEMENTED / NOT_TESTED` | No callback exchange, session establishment, refresh, sign-out, PKCE, or OAuth-state behavior exists or has been executed anywhere in the repository. The merged frontend foundation does not change this. |
| `CONTRACT-API-001@0.1.0-draft.1` | `PRESENT / DRAFT_FOR_CONSUMER_REVIEW / NOT_IMPLEMENTATION_READY` | A2-UI completed manager-level consumer review. The draft is documentary input, not an accepted runtime contract. |
| `UI-DEP-BACKEND-001` | `PARTIALLY_SATISFIED_BY_CONTRACT_API_001_DRAFT / CONSUMER_REVIEW_AND_EXTERNAL_OWNER_INPUTS_PENDING / RUNTIME_NOT_IMPLEMENTED_OR_TESTED` | Shared transport conventions are documented; final Auth, Security, Deployment, owner projection, fixture, and runtime inputs remain unresolved. |
| API runtime | `NOT_IMPLEMENTED / NOT_TESTED / NOT_AUTHORIZED` | No API route, schema, middleware, OpenAPI snapshot, client fixture, or runtime behavior is proven or authorized. |
| Provider | `SUPABASE_AUTH_WITH_GITHUB_OAUTH` | Accepted for contract and design only. |
| Provider architecture | `APPROVED_FOR_AUTH_CONTRACT_AND_DESIGN` | Issuer, audience, JWKS, and callback templates are accepted design values. |
| Provider runtime | `NOT_PROVISIONED / NOT_TESTED` | No Supabase project, GitHub OAuth configuration, callback registration, deployed domain, TLS, environment value, or secret injection is proven. |
| `apps/web` | `PRESENT` | Eighteen tracked files under `apps/web` at baseline `006cc88`, including `package.json`, `package-lock.json`, `tsconfig.json`, `next.config.ts`, `eslint.config.mjs` and `vitest.config.ts`. |
| Next.js App Router | `IMPLEMENTED` | `apps/web/src/app/layout.tsx`, `page.tsx`, `providers.tsx`, `globals.css`. |
| TypeScript | `IMPLEMENTED` | `apps/web/tsconfig.json` and TypeScript sources throughout `apps/web/src`. |
| MUI theme and application shell | `IMPLEMENTED` | `apps/web/src/theme.ts` and `apps/web/src/components/AppShell.tsx`. |
| Frontend automated regression tests | `IMPLEMENTED` | `apps/web/vitest.config.ts`, `src/test/setup.ts`, `src/test/renderWithTheme.tsx`, `src/app/page.test.tsx`, `src/components/AppShell.test.tsx`. |
| Frontend Auth behavior | `NOT_IMPLEMENTED / NOT_TESTED / NOT_AUTHORIZED` | No browser or server Auth client, session code, provider client, protected route, or Auth-aware component exists. The merged foundation contains none. |
| Frontend Auth tests | `NOT_STARTED / NOT_TESTED` | No frontend Auth test exists or is authorized. The merged regression tests exercise the shell and page only. |
| API client | `NOT_IMPLEMENTED / NOT_AUTHORIZED` | `UI-005` remains blocked; no typed client, transport, or error-envelope handling exists. |
| Reserved route `/auth/callback` | `RESERVED / NOT_IMPLEMENTED` | A2-UI owns the route and UX; A2-AUTH owns semantics; A2-DEPLOYMENT owns deployed registration. No route, page, or handler exists in the merged `apps/web`. |
| `UI-004` | `BLOCKED / NOT_AUTHORIZED` | `UI-002` and `UI-003` no longer block it. Remaining blockers are separate Agent 1 authorization, complete A2-AUTH semantics, A2-SECURITY cookie/CSRF/OAuth-state acceptance under `AUTH-DEP-011`, and A2-DEPLOYMENT runtime provisioning. |
| Auth PR #29 — `docs(auth): define dashboard sign-in and session contract` | `OPEN / DRAFT / AUTH_CONTRACT_CONSUMER_REVIEW_IN_PROGRESS` | Reviewed head `7abe17af8e212bd2127160338ea6ef409da02101`; branch `agent2/auth-002-session-contract`. Not accepted, not merged, and not modified by this task. |
| A2-UI consumer review of `CONTRACT-AUTH-001@1.1.0-draft.1` | `SPECIFICATION_CONFLICT / CORRECTIONS_AUTHORIZED / REREVIEW_REQUIRED` | Agent 1 confirmed the cookie-custody conflict and authorized the UI-owned correction only. The Auth-owned correction and A2-UI rereview both remain outstanding. |
| UI durable records | `MERGED_THROUGH_PR_25 / CURRENT_AUTH002_RECONCILIATION_UNSTAGED` | Six UI records are being reconciled for A2-UI review; no staging or commit is authorized. |

## API draft consumer-review state

Documented by `CONTRACT-API-001@0.1.0-draft.1`:

- `/api/v1` application-path conventions;
- `Authorization: Bearer` access-token transport;
- refresh-token forwarding prohibition;
- safe error-envelope proposal;
- `X-Request-ID` and `X-Correlation-ID`;
- shared cursor-pagination conventions;
- polling through the response `Location` header.

Exact classifications:

- Authorization bearer transport:
  `PROPOSED_AND_DOCUMENTED_IN_API_DRAFT`.
- Refresh-token forwarding: `PROHIBITED`.
- Final authenticated context:
  `UNRESOLVED / AUTH_OWNED / RUNTIME_HANDOFF_NOT_FROZEN`.
- Safe error envelope: `PROPOSED_AND_DOCUMENTED_IN_API_DRAFT`.
- Exact `403` versus concealed `404` policy:
  `UNRESOLVED_PENDING_AUTH_AND_SECURITY`.
- Request and correlation IDs:
  `PROPOSED_AND_DOCUMENTED_IN_API_DRAFT`.
- Shared cursor pagination: `PROPOSED_AND_DOCUMENTED_IN_API_DRAFT`.
- Endpoint-specific projections and actions: `PARTIAL / OWNER_DEPENDENT`.
- CORS: `UNRESOLVED / DEPLOYMENT_AND_SECURITY_INPUT_REQUIRED /
  BACKEND_CONFIGURATION_NOT_DEFINED`.

Still unresolved: final Auth-owned authenticated context; exact denial
disclosure; CORS; a validating OpenAPI/client fixture; endpoint-specific
Workflow, Evidence, Evaluation, Queue, and DB-003 projections/actions; API
runtime; and frontend runtime.

## Accepted provider design values

- Canonical issuer: `https://<SUPABASE_PROJECT_REF>.supabase.co/auth/v1`
- Audience: `authenticated`
- JWKS: `https://<SUPABASE_PROJECT_REF>.supabase.co/auth/v1/.well-known/jwks.json`
- Deployed Dashboard callback template: `${DASHBOARD_ORIGIN}/auth/callback`
- Local callback: `http://localhost:3000/auth/callback`
- OAuth termination: Supabase Auth
- FastAPI receives Supabase JWT access tokens only.
- Refresh tokens are never forwarded to FastAPI.
- Redirects require exact-match allowlisting.
- Issuer comparison is exact and case-sensitive; independent issuer
  normalization is prohibited.

These are accepted design values only. They are not proof of a provisioned
provider, configured GitHub OAuth, deployed Vercel project, production
hostname, TLS, callback registration, injected environment values or secrets,
or working callback/session behavior.

## Ownership and binding constraints

- A2-UI owns UI durable records, future authorized `apps/web` implementation,
  the user-facing `/auth/callback` route and UX, frontend session-state
  presentation, frontend Auth integration and tests after authorization, and
  accessibility.
- A2-AUTH owns callback and session semantics, identity resolution, token
  custody, token lifetime and refresh semantics, PKCE, and OAuth-state
  semantics.
- A2-DEPLOYMENT owns provider provisioning, deployed domains, callback
  registration, TLS, environment-variable registration, and secret injection.
- A2-SECURITY with A2-AUTH owns final cookie, CSRF, and OAuth-state security
  acceptance.
- No access or refresh token may enter `localStorage` or `sessionStorage`; no
  duplicate custom token store may exist; refresh tokens are never forwarded
  to FastAPI; access tokens use `Authorization: Bearer`; UI route protection
  is defense-in-depth only; FastAPI authorization remains authoritative. The
  current normative custody rule is `UI-DEC-026`, which supersedes only the
  blanket non-`HttpOnly`-cookie clause of `UI-DEC-013` and weakens none of the
  storage prohibitions above.
- A3-AUTH may not modify UI-owned paths without A2-UI coordination; A3-UI may
  not modify Auth-owned paths.

## `AUTH-002` consumer-review state

A2-UI's consumer review of `CONTRACT-AUTH-001@1.1.0-draft.1`, at reviewed Auth
PR #29 head `7abe17af8e212bd2127160338ea6ef409da02101`, returned
`SPECIFICATION_CONFLICT`. Agent 1 accepted that disposition and returned
`PASS / UI_AUTH_COOKIE_CONFLICT_CONFIRMED / UI_OWNED_CORRECTION_AUTHORIZED`.

| Item | State |
|---|---|
| Confirmed conflict | The merged `UI-DEC-013` prohibits a non-`HttpOnly` cookie written by UI code; the Auth candidate contract states `HttpOnly` is not achievable for the browser-readable `@supabase/ssr` cookie-backed session. |
| UI-owned correction | `AUTHORIZED / APPLIED_AS_UI-DEC-026` — this task, documentation only. |
| Auth-owned correction | `REQUIRED / NOT_YET_PUSHED` — owned by A2-AUTH on PR #29. |
| Final cookie posture — `HttpOnly`, `SameSite`, lifetime, domain, CSRF | `UNRESOLVED / A2-SECURITY_OWNED` under `AUTH-DEP-011`. Not decided by A2-UI or A3-UI. |
| A2-UI rereview of the corrected Auth PR head | `REQUIRED / NOT_PERFORMED` |
| `AUTH-DEP-012` | `SPECIFICATION_CONFLICT` — not `ACCEPTED`. |

The UI-owned correction does not by itself make Auth PR #29 acceptable, and it
is not A2-SECURITY acceptance of a browser-readable cookie.

## Remaining blockers

| Blocker | Owner | Blocks |
|---|---|---|
| Provider provisioning, production domain, TLS, callback registration, environment values, secret injection, and test-provider configuration | A2-DEPLOYMENT | `UI-004` verification and `UI-010` |
| Complete session/callback, PKCE, OAuth-state, refresh, and sign-out semantics | A2-AUTH | `UI-004` |
| Cookie, CSRF, and OAuth-state security acceptance | A2-SECURITY with A2-AUTH | `UI-004`, `UI-010` |
| Implementation-ready API contract, validating OpenAPI/client fixture, final Auth context, denial disclosure, CORS, endpoint models, and runtime | A2-BACKEND with A2-AUTH, A2-SECURITY, A2-DEPLOYMENT, and domain owners | `UI-005` through `UI-009` |
| Workflow, Evidence, and Evaluation UI projections | A2-AGENT-WORKFLOW and A2-EVALUATION | `UI-006` through `UI-009` |
| Separate authorization for `UI-001` and every remaining implementation task | A2-UI / Agent 1 as applicable | All future UI work. `UI-002` and `UI-003` were separately authorized and are merged; that authorization does not extend to `UI-004` or later. |
| `AUTH-002` cookie-custody conflict: Auth-owned correction, then A2-UI rereview of the corrected PR #29 head | A2-AUTH, then A2-UI | `AUTH-DEP-012` acceptance; `UI-004` |

## Historical bootstrap state — preserved

At bootstrap on 2026-08-02, evidence baseline
`9ac5a242bfbfad839dd41cd51171b4f81db1be85`, worktree
`/Users/omkar/Documents/TestGap-Miner-wt-ui-bootstrap`, and branch
`agent2/ui-bootstrap-authdep010`, A2-UI was recorded as `INITIALIZED`; the
manager specification and six UI durable records were new, untracked, and
awaiting A2-UI review. `AUTH-DEP-004` was then `PENDING`, `AUTH-DEP-010` had
only the UI-side acceptance, and `AUTH-002` was `NOT_READY / BLOCKED`.
`apps/web` was `ABSENT`; frontend implementation was `NOT_STARTED`; frontend
runtime was `NOT_IMPLEMENTED / NOT_TESTED`; provider provisioning was
`NOT_PROVEN / NOT_TESTED`. The bootstrap validation passed for its seven-file
untracked documentation package, and no implementation or Git publication
action was performed by A3-UI.

Those statements are historical evidence, not the current dependency state.
The bootstrap-era `apps/web` `ABSENT`, frontend `NOT_STARTED`, and
`UI-002`/`UI-003` `NOT_AUTHORIZED` conclusions in this section are **superseded**
by the merged PR #26, PR #27 and PR #28 evidence recorded in the current-state
table above and by `UI-DEC-027`. They must not be read as current state.
`docs/specifications/A2_UI_MANAGER.md` retains that bootstrap snapshot and was
not modified or reconciled by this task.

## Historical API-reconciliation state — preserved

At baseline `ab60d4573d398fb610bc2ebb813f76d0c95b33d7`, on branch
`agent2/ui-auth-dependency-reconciliation`, A2-UI completed manager-level
consumer review of `CONTRACT-API-001@0.1.0-draft.1` and recorded
`UI-DEP-BACKEND-001` as `PARTIALLY_SATISFIED_BY_CONTRACT_API_001_DRAFT`. At that
baseline `apps/web` was still `ABSENT` and `UI-002`/`UI-003` were still
`NOT_AUTHORIZED`. Those two frontend statements are historical and superseded;
the API consumer-review conclusions remain current and are unchanged by this
task.

## Next action

A2-UI independently reviews the six unstaged, uncommitted `AUTH-002`
consumer-conflict and merged-frontend-state reconciliation edits. After A2-UI
acceptance and merge of this UI-owned correction, and after A2-AUTH pushes the
Auth-owned correction, A2-UI rereviews the corrected Auth PR #29 head. `UI-004`,
API, Auth, Queue, and DB-003 implementation remain unauthorized.
