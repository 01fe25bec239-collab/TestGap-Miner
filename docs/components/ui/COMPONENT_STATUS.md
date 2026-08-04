# UI Component Status

- Date: 2026-08-04
- Agent 2: `A2-UI`
- Paired Agent 3: `A3-UI`
- Current task: `UI-API-DEPENDENCY-RECONCILIATION-001-A3`
- Parent manager task: `UI-API-DEPENDENCY-RECONCILIATION-001`
- Prompt type: `REBASE_THEN_FOCUSED_DOCUMENTATION_REPAIR_ONLY`
- Scope: `UNCOMMITTED_DOCUMENTATION_EDITS_ONLY`
- Repository: `01fe25bec239-collab/TestGap-Miner`
- Worktree: `/Users/omkar/Documents/TestGap-Miner-wt-ui-auth-dependency-reconciliation`
- Branch: `agent2/ui-auth-dependency-reconciliation`
- Current evidence baseline: `ab60d4573d398fb610bc2ebb813f76d0c95b33d7`
- Historical bootstrap baseline: `9ac5a242bfbfad839dd41cd51171b4f81db1be85`
- Specification snapshot: `docs/specifications/A2_UI_MANAGER.md` — preserved, not reconciled by this task
- `ASSUMED`: `NONE`

## Manager state

`A2-UI` is `INITIALIZED / DURABLE_RECORDS_MERGED`. The bootstrap package
merged through PR #19 at merge commit
`4c4b2e3aefb3529cb9acad2860f050247b47e6b2`. Initialization remains a
documentation event only; it authorizes no frontend or Auth runtime work.

## Current state

| Area | State | Evidence / next action |
|---|---|---|
| `UI-DOC-BOOTSTRAP-001` | `PASS / VERIFIED_COMPLETE / MERGED` | UI manager specification and six durable records merged through PR #19. |
| `AUTH-DEP-004` | `ACCEPTED_WITH_CONSTRAINTS / MERGED_VIA_PR_20 / SATISFIED_FOR_AUTH_CONTRACT_AND_DESIGN` | Deployment decision merged through PR #20; accepted values are design-only. |
| `AUTH-DEP-010` | `ACCEPTED_WITH_CONSTRAINTS / ACKNOWLEDGED_BY_A2_AUTH / UI_OWNERSHIP_ESTABLISHED_VIA_PR_19 / AUTH_RECONCILED_VIA_PR_21` | A2-AUTH reconciled the UI ownership boundary through PR #21. |
| `AUTH-002` contract/design | `READY_FOR_AUTH_002_CONTRACT_AND_DESIGN` | May begin only as a separate, newly authorized A2-AUTH task. |
| `AUTH-002` frontend implementation | `NOT_AUTHORIZED` | No frontend work is authorized by dependency acceptance. |
| `AUTH-002` runtime implementation | `NOT_AUTHORIZED` | No Auth runtime work is authorized by dependency acceptance. |
| `CONTRACT-API-001@0.1.0-draft.1` | `PRESENT / DRAFT_FOR_CONSUMER_REVIEW / NOT_IMPLEMENTATION_READY` | A2-UI completed manager-level consumer review. The draft is documentary input, not an accepted runtime contract. |
| `UI-DEP-BACKEND-001` | `PARTIALLY_SATISFIED_BY_CONTRACT_API_001_DRAFT / CONSUMER_REVIEW_AND_EXTERNAL_OWNER_INPUTS_PENDING / RUNTIME_NOT_IMPLEMENTED_OR_TESTED` | Shared transport conventions are documented; final Auth, Security, Deployment, owner projection, fixture, and runtime inputs remain unresolved. |
| API runtime | `NOT_IMPLEMENTED / NOT_TESTED / NOT_AUTHORIZED` | No API route, schema, middleware, OpenAPI snapshot, client fixture, or runtime behavior is proven or authorized. |
| Provider | `SUPABASE_AUTH_WITH_GITHUB_OAUTH` | Accepted for contract and design only. |
| Provider architecture | `APPROVED_FOR_AUTH_CONTRACT_AND_DESIGN` | Issuer, audience, JWKS, and callback templates are accepted design values. |
| Provider runtime | `NOT_PROVISIONED / NOT_TESTED` | No Supabase project, GitHub OAuth configuration, callback registration, deployed domain, TLS, environment value, or secret injection is proven. |
| `apps/web` | `ABSENT` | No frontend application exists. |
| Frontend implementation | `NOT_STARTED` | No page, layout, route, component, middleware, provider, Auth client, or API client exists. |
| Frontend runtime | `NOT_IMPLEMENTED / NOT_TESTED / NOT_AUTHORIZED` | Nothing to run; no frontend behavior has been tested or authorized. |
| Frontend Auth tests | `NOT_STARTED / NOT_TESTED` | No frontend Auth test exists or is authorized. |
| Reserved route `/auth/callback` | `RESERVED / NOT_IMPLEMENTED` | A2-UI owns the route and UX; A2-AUTH owns semantics; A2-DEPLOYMENT owns deployed registration. |
| UI durable records | `MERGED_AUTH_RECONCILIATION / CURRENT_API_REPAIR_UNSTAGED` | Six UI records are being reconciled for A2-UI review; no staging or commit is authorized. |

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
  is defense-in-depth only; FastAPI authorization remains authoritative.
- A3-AUTH may not modify UI-owned paths without A2-UI coordination; A3-UI may
  not modify Auth-owned paths.

## Remaining blockers

| Blocker | Owner | Blocks |
|---|---|---|
| Provider provisioning, production domain, TLS, callback registration, environment values, secret injection, and test-provider configuration | A2-DEPLOYMENT | `UI-004` verification and `UI-010` |
| Complete session/callback, PKCE, OAuth-state, refresh, and sign-out semantics | A2-AUTH | `UI-004` |
| Cookie, CSRF, and OAuth-state security acceptance | A2-SECURITY with A2-AUTH | `UI-004`, `UI-010` |
| Implementation-ready API contract, validating OpenAPI/client fixture, final Auth context, denial disclosure, CORS, endpoint models, and runtime | A2-BACKEND with A2-AUTH, A2-SECURITY, A2-DEPLOYMENT, and domain owners | `UI-005` through `UI-009` |
| Workflow, Evidence, and Evaluation UI projections | A2-AGENT-WORKFLOW and A2-EVALUATION | `UI-006` through `UI-009` |
| Separate authorization for `UI-001` and every implementation task | A2-UI / Agent 1 as applicable | All future UI work |

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
`docs/specifications/A2_UI_MANAGER.md` retains that bootstrap snapshot and was
not modified or reconciled by this task.

## Next action

A2-UI reviews the six unstaged, uncommitted API-dependency reconciliation
edits and returns its consumer-review decision to A2-BACKEND. Frontend, API,
Auth, Queue, and DB-003 implementation remain unauthorized.
