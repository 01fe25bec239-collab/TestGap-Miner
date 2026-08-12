# UI Component Status

- Date: 2026-08-11
- Agent 2: `A2-UI`
- Paired Agent 3: `A3-UI`
- Current task: `UI-004-FINAL-ACCEPTANCE-DURABLE-RECONCILIATION-001`
- Parent manager task: `UI-004-AUTH008-MERGED-INTERFACE-INTEGRATION-001`
- Prompt type: `DOCUMENTATION_STATUS_RECONCILIATION_ONLY`
- Scope: `DURABLE_UI_RECORD_STATUS_RECONCILIATION_ONLY`
- Repository: `01fe25bec239-collab/TestGap-Miner`
- Worktree: `/Users/omkar/Documents/TestGap-Miner-wt-ui-004-local-auth-integration`
- Branch: `agent2/ui-004-local-auth-integration`
- Current evidence baseline: `dfca07e69b2da77f864d2259541147b419be7c00`
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

## `UI-004` local Auth integration result — 2026-08-09

Task `UI-004-LOCAL-AUTH-INTEGRATION-001-A3`, branch
`agent2/ui-004-local-auth-integration`, baseline
`2a708afebec23e71ce1a0b6c5f6efd3df8c92496`. Changes are **unstaged and
uncommitted** and await independent A2-UI review.

- Disposition: `IMPLEMENTED / DETERMINISTICALLY_TESTED / UNSTAGED /
  PENDING_INDEPENDENT_A2_UI_REVIEW`.
- Scope implemented: UI-owned sign-in control, `SIGN_IN_PENDING` presentation,
  `/auth/callback` route surface with loading, success and failure
  presentation, authenticated/unauthenticated shell presentation, protected
  content mounting and unmounting, sign-out control, error-state presentation,
  and frontend interaction tests.
- Auth runtime is **consumed, not UI-owned**. `apps/web/src/auth/**` merged
  through PR #32 and has **zero changes** in this task. Every Auth operation
  goes through `AuthAdapter.beginSignIn`, `AuthAdapter.processCallback`,
  `AuthAdapter.getSessionSnapshot`, `AuthAdapter.subscribeToSessionChanges`,
  `AuthAdapter.refreshSession` and `AuthAdapter.signOut`.
- Architecture consequence recorded for review: the merged runtime issues an
  `httpOnly` correlation cookie scoped to `/auth/callback` and correlates
  attempts through a process-local store. Sign-in initiation and callback
  processing therefore run server-side (`/auth/sign-in` route handler and the
  `/auth/callback` server action), and session presentation runs from a browser
  Auth runtime. No correlation handle, access token or refresh token reaches
  browser state, storage or context.
- `TESTED` means deterministic frontend tests only: `npm test` 120 tests across
  11 files, `npm run lint`, `npm run typecheck` and `npm run build` all pass at
  this working tree.
- `E2E_BROWSER_OAUTH`: `NOT_TESTED`. No local Auth environment values are
  present in the worktree or runtime environment, so no real GitHub OAuth
  browser flow was executed. Deterministic test evidence is **not** evidence
  that provider sign-in works.
- `UI-004` created no provider configuration, no Backend authorization, no API
  client, and no deployment. `AUTH-003`, `UI-005` and production deployment
  remain out of scope and unimplemented.

This section supersedes the `UI-004`, `Frontend Auth behavior`,
`Frontend Auth tests`, `Reserved route /auth/callback` and `Auth runtime` rows
as they read before 2026-08-09. Every other historical disposition below is
preserved unchanged.

## `UI-004` AUTH-008 merged-interface continuation — 2026-08-11

Task `UI-004-AUTH008-MERGED-INTERFACE-INTEGRATION-001`, branch
`agent2/ui-004-local-auth-integration`, base
`dfca07e69b2da77f864d2259541147b419be7c00`. Changes remain **unstaged and
uncommitted** following completed A2-UI acceptance.

- Disposition: `IMPLEMENTED_LOCALLY / AUTH008_INTEGRATED / DETERMINISTIC_VALIDATION_PASS / A2_FINAL_ACCEPTED / UNSTAGED / UNCOMMITTED / UNPUSHED / NO_PR`.
- Final A2 disposition: `PASS — UI_004_AUTH008_MERGED_INTERFACE_INTEGRATION_ACCEPTED` (`A3_RESULT: PASS`, `A2_INDEPENDENT_REVIEW: PASS`).
- The browser now consumes Auth-owned `createAuthBrowserSessionFenceBridge`
  and `createBrowserAuthAdapter`; the obsolete browser `createAuthAdapter`
  construction and duplicate POST sign-in composition are absent.
- UI-owned `POST /auth/session-fence` applies the existing Auth-owned mutation
  validation and delegates only `PREPARE_SIGN_IN`, `PUBLISH_SIGN_OUT` and
  `RESOLVE_SESSION` to `AuthSessionFenceHostService` through
  `executeAuthSessionFenceHostRequest`.
- Callback `ok:true` is provisional. The callback view presents success and
  follows only the Auth-returned destination after a current
  `RESOLVE_SESSION == AUTHENTICATED`; `UNAUTHENTICATED` fails closed to the
  existing generic signed-out presentation.
- The local UI integration now uses a non-noop, process-local bounded
  `AuthSecurityEvent` sink. Deterministic tests prove `INVALID_CALLBACK`
  retention, Auth-owned field preservation, bounded eviction, secret-free
  payloads and observable sink failure.
- `ProtectedRegion` remains governed only by
  `snapshot.canRenderProtectedContent`; browser provider events remain
  provisional, and sign-out remains current-session-only through the
  Auth-owned browser/host composition.
- Validation: `npm test` passed 209 tests across 16 files; `npm run lint`,
  `npm run typecheck`, `npm run build`, and `git diff --check` passed. Auth-owned
  paths and package files have zero changes.
- `FULL_BROWSER_NETWORK_RESPONSE_ORDER_ACCEPTANCE`: `NOT_TESTED`; this remains
  a future A2-INTEGRATION evidence gate.

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
| `AUTH-002` contract/design history | `HISTORICAL_SPECIFICATION_CONFLICT / PRESERVED` | The reviewed PR #29 head and `UI-DEC-026` conflict record remain historical evidence; they are not rewritten by this continuation. Current implementation evidence comes from the subsequently merged Auth runtime and AUTH-008 interfaces on the current base. |
| `AUTH-002` frontend implementation | `NOT_AUTHORIZED` | No frontend work is authorized by dependency acceptance. |
| `AUTH-002` runtime implementation history | `SUPERSEDED_BY_MERGED_A2_AUTH_RUNTIME` | The earlier `NOT_AUTHORIZED` disposition is preserved in historical sections; current base `dfca07e6` contains the accepted AUTH-008 interfaces. |
| `AUTH-008` | `PASS / IMPLEMENTED / A2_AUTH_ACCEPTED / MERGED / DURABLE_ON_MAIN` | Browser bridge, browser adapter and session-fence host interfaces are present on the authoritative base and consumed without Auth-owned modifications. |
| Auth runtime | `IMPLEMENTED_BY_A2_AUTH / AUTH008_MERGED / CONSUMED_BY_UI_004 / NOT_UI_OWNED` | Base `dfca07e69b2da77f864d2259541147b419be7c00` provides the merged browser bridge, browser adapter and session-fence host interfaces. `UI-004` consumes them and changed no `apps/web/src/auth/**` path. Historical disposition before PR #32 was `NOT_IMPLEMENTED / NOT_TESTED`. Merged runtime code is not evidence that a real provider sign-in has been executed. |
| `CONTRACT-API-001@0.1.0-draft.1` | `PRESENT / DRAFT_FOR_CONSUMER_REVIEW / NOT_IMPLEMENTATION_READY` | A2-UI completed manager-level consumer review. The draft is documentary input, not an accepted runtime contract. |
| `UI-DEP-BACKEND-001` | `PARTIALLY_SATISFIED_BY_CONTRACT_API_001_DRAFT / CONSUMER_REVIEW_AND_EXTERNAL_OWNER_INPUTS_PENDING / UI_CONSUMER_CONTRACT_NOT_IMPLEMENTATION_READY` | Shared transport conventions are documented, but final Auth, Security, Deployment, owner projection, and validating client-fixture inputs remain unresolved. Backend runtime existence does not make the UI consumer contract implementation-ready. |
| API runtime | `BACKEND_RUNTIME_PRESENT_ON_CURRENT_MAIN / UI_TYPED_CLIENT_NOT_IMPLEMENTED / UI005_NOT_AUTHORIZED / UI_CONSUMER_CONTRACT_NOT_IMPLEMENTATION_READY` | Current main contains Backend runtime material, including the FastAPI application and middleware, plus later Workflow/runtime integration. A2-UI is neither classifying nor certifying Backend completeness; runtime existence is not `UI-005` readiness. |
| Provider | `SUPABASE_AUTH_WITH_GITHUB_OAUTH` | Accepted for contract and design only. |
| Provider architecture | `APPROVED_FOR_AUTH_CONTRACT_AND_DESIGN` | Issuer, audience, JWKS, and callback templates are accepted design values. |
| Provider runtime | `LOCAL_PROVIDER_PROVISIONING_COMPLETED_EXTERNALLY / NOT_REVERIFIED_BY_UI004 / REAL_BROWSER_OAUTH_NOT_TESTED / PRODUCTION_DEPLOYMENT_NOT_PROVEN` | External local provider provisioning is established project history but was not reverified by `UI-004`, which executed no real browser OAuth flow. Production provider/domain/TLS/callback/environment/secret deployment remains outside `UI-004` and is not proven here. |
| `apps/web` | `PRESENT` | Eighteen tracked files under `apps/web` at baseline `006cc88`, including `package.json`, `package-lock.json`, `tsconfig.json`, `next.config.ts`, `eslint.config.mjs` and `vitest.config.ts`. |
| Next.js App Router | `IMPLEMENTED` | `apps/web/src/app/layout.tsx`, `page.tsx`, `providers.tsx`, `globals.css`. |
| TypeScript | `IMPLEMENTED` | `apps/web/tsconfig.json` and TypeScript sources throughout `apps/web/src`. |
| MUI theme and application shell | `IMPLEMENTED` | `apps/web/src/theme.ts` and `apps/web/src/components/AppShell.tsx`. |
| Frontend automated regression tests | `IMPLEMENTED` | `apps/web/vitest.config.ts`, `src/test/setup.ts`, `src/test/renderWithTheme.tsx`, `src/app/page.test.tsx`, `src/components/AppShell.test.tsx`. |
| Frontend Auth behavior | `IMPLEMENTED_LOCALLY / AUTH008_INTEGRATED / DETERMINISTIC_VALIDATION_PASS / BROWSER_NETWORK_GATE_NOT_TESTED / UNSTAGED` | Includes `src/app/auth/session-fence/route.ts`, merged browser adapter/bridge consumption, callback `RESOLVE_SESSION` gating and `src/providers/securityEventSink.ts`, while preserving the existing shell and callback presentation. Historical disposition before 2026-08-09 was `NOT_IMPLEMENTED / NOT_TESTED / NOT_AUTHORIZED`. |
| Frontend Auth tests | `IMPLEMENTED / 209_TESTS_ACROSS_16_FILES_PASS / DETERMINISTIC_ONLY` | Tests cover browser composition, the three-operation session-fence route, same-origin/CSRF/cache policy, callback fail-closed gating, provider-event provisionality, protected-region removal, bounded security-event retention and failure observability. They are not full browser/network response-order evidence. Historical disposition before 2026-08-09 was `NOT_STARTED / NOT_TESTED`. |
| API client | `NOT_IMPLEMENTED / NOT_AUTHORIZED` | `UI-005` remains blocked; no typed client, transport, or error-envelope handling exists. |
| Route `/auth/callback` | `IMPLEMENTED / UI_OWNED_SURFACE / AUTH_OWNED_SEMANTICS / UNSTAGED` | `src/app/auth/callback/page.tsx`, `AuthCallbackView.tsx` and `actions.ts`. The route owns existence, loading, success, failure, accessibility and safe navigation only; it delegates every semantic to `AuthAdapter.processCallback`. A2-DEPLOYMENT still owns deployed registration. Historical disposition before 2026-08-09 was `RESERVED / NOT_IMPLEMENTED`. |
| `UI-004` | `IMPLEMENTED_LOCALLY / AUTH008_INTEGRATED / DETERMINISTIC_VALIDATION_PASS / A2_FINAL_ACCEPTED / UNSTAGED / UNCOMMITTED / UNPUSHED / NO_PR` | See the two `UI-004` result sections above. Final A2 disposition recorded: `PASS — UI_004_AUTH008_MERGED_INTERFACE_INTEGRATION_ACCEPTED`. Historical disposition before 2026-08-09 was `BLOCKED / NOT_AUTHORIZED`. Full browser/network response-order acceptance remains `NOT_TESTED`. |
| Auth PR #29 — `docs(auth): define dashboard sign-in and session contract` | `HISTORICAL_SNAPSHOT / PRESERVED` | Reviewed head `7abe17af8e212bd2127160338ea6ef409da02101`; branch `agent2/auth-002-session-contract`. This task does not rewrite that earlier review state. |
| A2-UI consumer review of `CONTRACT-AUTH-001@1.1.0-draft.1` | `HISTORICAL_SPECIFICATION_CONFLICT / PRESERVED` | Agent 1's earlier cookie-custody disposition remains recorded as history; AUTH-008 is the authoritative current interface baseline. |
| UI durable records | `MERGED_HISTORY_PRESERVED / CURRENT_UI004_AUTH008_RECONCILIATION_UNSTAGED` | These two UI records reflect the current local integration; no staging or commit is authorized. |

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

Still unresolved for the UI consumer: final Auth-owned authenticated context;
exact denial disclosure; CORS; a validating OpenAPI/client fixture;
endpoint-specific Workflow, Evidence, Evaluation, Queue, and DB-003
projections/actions; implementation-ready consumer contracts; and frontend
runtime. Backend runtime material exists on current main; A2-UI does not
classify or certify its completeness.

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

These design records alone are not runtime evidence. External local provider
provisioning was subsequently completed, but `UI-004` did not reverify it or
execute a real browser OAuth flow. No production provider/domain/TLS/callback,
environment-value, or secret deployment is proven by this UI-owned record.

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

## Historical `AUTH-002` consumer-review snapshot — preserved

**HISTORICAL SNAPSHOT — 2026-08-08 / reviewed Auth PR #29 head
`7abe17af8e212bd2127160338ea6ef409da02101`.** The original dispositions below
are preserved as the state at that reviewed head; they are not current project
status.

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

For current implementation purposes, this snapshot was subsequently
superseded by corrected/merged Auth contract history, merged Auth runtime,
`AUTH-007`, and `AUTH-008`. The historical dispositions above remain unchanged.

## Remaining blockers

| Blocker | Owner | Blocks |
|---|---|---|
| Real browser OAuth execution evidence | A2-INTEGRATION | `UI-004` evidence limitation; currently `NOT_TESTED` |
| Full browser/network response-order acceptance | A2-INTEGRATION | Final `UI-004` browser evidence; currently `NOT_TESTED` |
| Production provider/domain/TLS/callback/environment/secret deployment evidence | A2-DEPLOYMENT | `UI-010`; outside `UI-004` and not proven by this record |
| Cookie, CSRF, and OAuth-state security acceptance | A2-SECURITY with A2-AUTH | `UI-004`, `UI-010` |
| Implementation-ready API contract, validating OpenAPI/client fixture, final Auth context, denial disclosure, CORS, endpoint models, and runtime | A2-BACKEND with A2-AUTH, A2-SECURITY, A2-DEPLOYMENT, and domain owners | `UI-005` through `UI-009` |
| Workflow, Evidence, and Evaluation UI projections | A2-AGENT-WORKFLOW and A2-EVALUATION | `UI-006` through `UI-009` |
| Separate authorization for `UI-001` and every remaining implementation task | A2-UI / Agent 1 as applicable | All future UI work after this explicitly authorized `UI-004` continuation. |

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

A2-UI has completed independent review and accepted the UI-004 integration (`PASS — UI_004_AUTH008_MERGED_INTERFACE_INTEGRATION_ACCEPTED`).
The complete `UI-004` diff remains unstaged and uncommitted on branch `agent2/ui-004-local-auth-integration`.
The full browser/network response-order gate remains `NOT_TESTED` for future A2-INTEGRATION evidence.
No staging, commit, push or PR action has occurred.
