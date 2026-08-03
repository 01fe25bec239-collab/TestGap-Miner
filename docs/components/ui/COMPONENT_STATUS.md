# UI Component Status

- Date: 2026-08-03
- Agent 2: `A2-UI`
- Paired Agent 3: `A3-UI`
- Current task: `UI-AUTH-DEPENDENCY-RECONCILIATION-001-A3-C1`
- Parent manager task: `UI-AUTH-DEPENDENCY-RECONCILIATION-001`
- Prompt type: `POST_MERGE_UI_DURABLE_STATE_RECONCILIATION`
- Scope: `UNCOMMITTED_DOCUMENTATION_EDITS_ONLY`
- Repository: `01fe25bec239-collab/TestGap-Miner`
- Worktree: `/Users/omkar/Documents/TestGap-Miner-wt-ui-auth-dependency-reconciliation`
- Branch: `agent2/ui-auth-dependency-reconciliation`
- Current evidence baseline: `ba4247af2195d4c8e60cb9990f616a95f2c54d54`
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
| Provider | `SUPABASE_AUTH_WITH_GITHUB_OAUTH` | Accepted for contract and design only. |
| Provider architecture | `APPROVED_FOR_AUTH_CONTRACT_AND_DESIGN` | Issuer, audience, JWKS, and callback templates are accepted design values. |
| Provider runtime | `NOT_PROVISIONED / NOT_TESTED` | No Supabase project, GitHub OAuth configuration, callback registration, deployed domain, TLS, environment value, or secret injection is proven. |
| `apps/web` | `ABSENT` | No frontend application exists. |
| Frontend implementation | `NOT_STARTED` | No page, layout, route, component, middleware, provider, Auth client, or API client exists. |
| Frontend runtime | `NOT_IMPLEMENTED / NOT_TESTED` | Nothing to run; no frontend behavior has been tested. |
| Frontend Auth tests | `NOT_STARTED / NOT_TESTED` | No frontend Auth test exists or is authorized. |
| Reserved route `/auth/callback` | `RESERVED / NOT_IMPLEMENTED` | A2-UI owns the route and UX; A2-AUTH owns semantics; A2-DEPLOYMENT owns deployed registration. |
| UI durable records | `MERGED / CURRENT_RECONCILIATION_UNCOMMITTED` | Six UI records are being reconciled for A2-UI review; no staging or commit is authorized. |

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
| `CONTRACT-API-001`, authenticated request surface, error envelope, and CORS | A2-BACKEND | `UI-005` through `UI-009` |
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

A2-UI reviews the six unstaged, uncommitted reconciliation edits. Frontend and
Auth runtime implementation remain unauthorized.
