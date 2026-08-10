# Auth Component Status

- Date: 2026-08-10
- Agent 2: `A2-AUTH`
- Paired Agent 3: `A3-AUTH`
- Current task:
  `AUTH-006-FINALIZE-CONTRACT-AUTH-001-V1.2.0-DRAFT.1-001-A3-R2`
- Authorized manager task:
  `AUTH-006-FINALIZE-CONTRACT-AUTH-001-V1.2.0-DRAFT.1-001`
- Authorizing coordinator:
  `Agent 1`
- Task type:
  `DOCUMENTATION / CONTRACT FINALIZATION / NO_RUNTIME_IMPLEMENTATION`
- Required baseline:
  `5ffa8994b286e85d9f676336dbe0169cfbc89d2c`
- Worktree:
  `/Users/omkar/Documents/TestGap-Miner-wt-auth-contract-1.2-finalization`
- Branch:
  `agent2/auth-contract-1.2-finalization`
- Contract:
  `CONTRACT-AUTH-001@1.2.0-draft.1` — `FINALIZED_CONTRACT_DRAFT_FOR_A2_REVIEW / NOT_IMPLEMENTATION_READY`
- Runtime status:
  `EXISTING_MERGED_CODE_IN_APPS_WEB_SRC_AUTH / AUTH_006_RUNTIME_MODIFICATION_AUTHORIZED=NONE / FENCE_CORRECTION_RUNTIME=NOT_YET_AUTHORIZED`
- Consumer review status for AUTH-005 additions:
  `A2-UI` (`ACCEPTED_WITH_CONSTRAINTS`), `A2-SECURITY` (`ACCEPTED_WITH_CONSTRAINTS`),
  `A2-DEPLOYMENT` (`ACCEPTED_WITH_CONSTRAINTS`), `A2-INTEGRATION` (`ACCEPTED_WITH_CONSTRAINTS`)
- `ASSUMED`: `NONE`

## Current state

| Area | State | Evidence / next action |
|---|---|---|
| `AUTH-006-FINALIZE-CONTRACT-AUTH-001-V1.2.0-DRAFT.1-001-A3-R2` | `IMPLEMENTED / UNSTAGED / UNCOMMITTED / PENDING_A2_AUTH_REVIEW` | Finalizes `CONTRACT-AUTH-001@1.2.0-draft.1` incorporating accepted `AUTH-005` normative corrections across `A2-UI`, `A2-SECURITY`, `A2-DEPLOYMENT`, and `A2-INTEGRATION` (all `ACCEPTED_WITH_CONSTRAINTS`) along with R1/R2 targeted corrections: PKCE provider custody & OAuth state ownership preservation, callback correlation record separation, Auth runtime unit test reconciliation (`PRESENT_IN_BASELINE`), Auth CSRF/cookie foundation reconciliation (`PRESENT_IN_BASELINE`), OPEN_ISSUES impact wording fix, callback generation supersession, tombstone ordering before publication, new-sign-in reconciliation, session-binding record exclusions, response fence non-mutation, and reconciled current runtime status. Existing merged Auth runtime code exists under `apps/web/src/auth/**`. THIS TASK AUTHORIZES NO RUNTIME MODIFICATION. `AUTH-003` / `AUTH-005` fence correction runtime implementation is `NOT_YET_AUTHORIZED / NOT_YET_IMPLEMENTED` under this task. |
| `AUTH-002-FINAL-READINESS-RECONCILIATION-001-A3` | `HISTORICAL_STATE / SUPERSEDED_BY_AUTH-006_FINALIZATION` | Prior non-normative readiness reconciliation across five consumer domains against HEAD `84ad9e322d886f8963c34386f87074a444b3fa2b`. Added decision `AUTH-DEC-053`. Superseded by `AUTH-006` contract finalization. |
| `A2-UI` consumer response | `ACCEPTED_WITH_CONSTRAINTS` | `AUTH-005` review complete. Host boundary frozen as `POST /auth/session-fence` (`apps/web/src/app/auth/session-fence/route.ts`). Operations: `PREPARE_SIGN_IN`, `PUBLISH_SIGN_OUT`, `RESOLVE_SESSION`. Host/path/transport/wiring owned by A2-UI; Auth semantics owned by A2-AUTH. `processCallback()` alone is not final presentation proof. No new public UI Auth state introduced. |
| `A2-SECURITY` consumer response | `ACCEPTED_WITH_CONSTRAINTS` | `AUTH-005` review complete. Security constraints frozen for handles (`OPAQUE_AUTH_CONTEXT_HANDLE`, `OPAQUE_AUTH_SESSION_BINDING_HANDLE`) and tombstone (`LOCAL_SIGN_OUT_TOMBSTONE`). NOOP event sink rejected; LOCAL NON-NOOP sink required; local durable persistence not required; event-envelope enrichment recorded as implementation follow-up only. |
| `A2-DEPLOYMENT` consumer response | `ACCEPTED_WITH_CONSTRAINTS` | `AUTH-005` review complete. Production synchronization authority must be environment-isolated, HA, shared, linearizable, restart-safe, failover-safe, fail-closed when unavailable/indeterminate. Physical provider remains **UNSELECTED** (no Redis, Valkey, PostgreSQL, Supabase table, cloud cache). Local UI-004 process-local authority permitted ONLY when callback processing, session validation, sign-out run in 1 OS process and 1 memory space; authority loss on restart fails closed to reauthentication. |
| `A2-INTEGRATION` consumer response | `ACCEPTED_WITH_CONSTRAINTS` | `AUTH-005` review complete. 11 future acceptance-test requirements recorded (deterministic response order control, actual browser cookie jar, stale response orders A/B, multi-tab shared context, faultable sync authority, response barriers, denial vs physical cleanup, no protected-content flash, access-token fail-closed, green existing callback duplicate/replay suite). Vitest/jsdom-only proof is INSUFFICIENT for browser/network ordering acceptance; recorded as future evidence requirements. |
| `AUTH-DEP-003` — Shared registry correction | `COMPLETE / VERSION_AWARE_SHARED_REGISTRY_RECONCILED` | Reconciled via merged PR #31 (`a80145e2` / `1057ba72`) in `docs/specifications/A2_DATABASE_MANAGER(1).md`. Registry is version-aware. |
| `AUTH-ISSUE-002` — Shared registry omits Database consumer | `CLOSED / VERSION_AWARE_REGISTRY_RECONCILED` | Closed via merged PR #31 (`a80145e2` / `1057ba72`). |
| Provider-session cookie posture | `FROZEN / POLICY_AND_COORDINATION_ACCEPTED` | Browser-readable `@supabase/ssr` session; `SameSite=Lax`; `Secure=true` in every non-local environment with `http://localhost:3000` the only exception; host-only; no `Domain`; `Path=/`; not `HttpOnly`; provider-managed lifetime and rotation; no custom token copy. Accepted by `A2-SECURITY` (policy), `A2-AUTH` (semantics), `A2-DEPLOYMENT` (coordination). `AUTH-DEC-045`. |
| CSRF and credential transport | `FROZEN / POLICY_AND_COORDINATION_ACCEPTED` | Bearer-only for protected FastAPI routes; provider cookie never an API credential; no anti-CSRF token required for Bearer API requests; exact-origin CORS. Same-origin Auth session mutations validate `Origin`, Fetch Metadata, Auth anti-CSRF. Callback exempt from same-origin token, gated on OAuth `state`, PKCE, correlation, exact destination and return binding. `AUTH-DEC-046`. |
| Sign-out scope and access-token lifetime | `FROZEN / POLICY_AND_COORDINATION_ACCEPTED` | Sign-out scope `local` (`CURRENT_SESSION_ONLY`). Production access-token lifetime `<= 900 seconds`. Local UI state clears immediately. `AUTH-DEC-047`. |
| Public failure-oracle boundary | `FROZEN` | Public classification `SIGN_IN_FAILED` for `INVALID_CALLBACK`, `STATE_VALIDATION_FAILED`, `PKCE_VALIDATION_FAILED`, `SESSION_EXCHANGE_FAILED`. Internal classifications preserved for logging. `AUTH-DEC-048`. |
| Callback-correlation mechanism | `FROZEN / POLICY_AND_COORDINATION_ACCEPTED` | Server-side ephemeral correlation store; opaque handle cookie in browser; `PENDING_ATTEMPT_CORRELATION` `<= 10` minutes; `COMPLETED_CALLBACK_CORRELATION` exactly `120` seconds; atomic transition; fail-closed. `AUTH-DEC-049`. |
| Intended-return state | `FROZEN / SERVER_SIDE_ONLY` | Held only inside server-side `PENDING_ATTEMPT_CORRELATION` record. Never in browser persistence. Missing/failed state falls back to `/`. `AUTH-DEC-050`. |
| Preserved-session proof | `FROZEN` | Four conditions required including server-side `LIVE_PROVIDER_SESSION_VALIDATION` and session-identity equality. Unproven validity fails closed. `AUTH-DEC-051`. |
| `AUTH-006` implementation status | `NOT_AUTHORIZED` | Runtime modification under `AUTH-006`: `NONE / NOT_AUTHORIZED`; existing merged Auth runtime code exists under `apps/web/src/auth/**`; `AUTH-003`/`AUTH-005` fence correction runtime `NOT_YET_AUTHORIZED / NOT_YET_IMPLEMENTED`; frontend `/auth/callback` route `NOT_IMPLEMENTED / NOT_AUTHORIZED`; provider runtime `NOT_PROVISIONED / NOT_TESTED`. |
| Provider provisioning | `NOT_STARTED / NOT_TESTED` | No Supabase project provisioning, GitHub OAuth provider configuration, Vercel project, production Dashboard hostname, TLS verification, production callback registration, or secret injection is proven by this repository. |
| `CONTRACT-AUTH-001@1.1.0-draft.1` | `HISTORICAL / SUPERSEDED_BY_1.2.0-draft.1` | Superseded as current candidate contract version by `CONTRACT-AUTH-001@1.2.0-draft.1`. Historical references preserved. |
| `CONTRACT-AUTH-001@1.0.0-draft.2` | `HISTORICAL / ACKNOWLEDGED_AND_MERGED` | A2-DATABASE recorded acknowledgement in `docs/components/database/COMPONENT_STATUS.md` and `DECISION_LOG.md`; merged into `origin/main`. |
| `DB-002` | `PASS / VERIFIED_COMPLETE / MERGED` | Pull request #12, implementation commit `5506ab5`, merge commit `3701520`; closed by PR #13 (`1511f47`). Seven domain tables, five of them Auth-owned. |
| Auth identity persistence | `VERIFIED_COMPLETE` | `apps/api/app/db/models/auth.py`: `users`, `auth_subjects`, `github_installations`, `repositories`, `repository_access`. 21 Auth constraint tests executed 2026-08-02, all passing. |
| Existing merged Auth runtime code | `PRESENT_IN_BASELINE / NOT_YET_FENCE_CORRECTED` | Existing merged Auth runtime code is present in baseline under `apps/web/src/auth/**` (including `AuthAdapter`, state machine, correlation, storage boundary, redirect, types, unit tests). No `/auth/callback` route exists. `AUTH-006` authorizes NO runtime modification. `AUTH-003` / `AUTH-005` fence correction runtime implementation is `NOT_YET_AUTHORIZED / NOT_YET_IMPLEMENTED` under this task. |
| `/auth/callback` route | `NOT_IMPLEMENTED` | Reserved. A2-UI owns route existence and UX; A2-AUTH owns semantics; A2-DEPLOYMENT owns deployed registration. |
| Auth implementation — JWT validation and user context | `NOT_STARTED / NOT_AUTHORIZED` | `apps/api/app/main.py` is three lines; no JWT/JWKS dependency in `apps/api/pyproject.toml`. |
| Auth implementation — GitHub App machine auth | `NOT_STARTED / NOT_AUTHORIZED` | No first-party app-ID, private-key, or token-exchange code; no GitHub App manifest exists. |
| Auth implementation — webhook authenticity | `NOT_STARTED / NOT_AUTHORIZED` | No webhook route, raw-body handling, or `X-Hub-Signature-256` verifier. |
| Auth implementation — repository-scoped authorization | `PARTIAL` | Exact-tuple grant model persisted and tested; no runtime reads a grant to allow or deny anything. |
| Auth implementation — CORS, CSRF, cookies | `RECONCILED` | AUTH-OWNED CSRF / COOKIE FOUNDATION: PRESENT_IN_BASELINE under `apps/web/src/auth/**` (`csrf.ts`). BACKEND CORS IMPLEMENTATION: SEPARATELY A2-BACKEND-OWNED / DO NOT CLAIM IMPLEMENTED UNLESS PROVEN. AUTH-005 SESSION-FENCE RUNTIME CORRECTION: NOT_YET_AUTHORIZED / NOT_YET_IMPLEMENTED. |
| Auth tests and CI validation | `RECONCILED` | Auth runtime unit tests: PRESENT_IN_BASELINE under `apps/web/src/auth/**` (`adapter.test.ts`, `correlation.test.ts`, `state-machine.test.ts`, `storage-boundary.test.ts`, `supabase.test.ts`, `supabase-cookie-journal.test.ts`). `tests/auth/`: ABSENT. AUTH-005 cross-runtime/browser-network acceptance: NOT_YET_TESTED / FUTURE_INTEGRATION_REQUIREMENT (Vitest/jsdom-only proof is INSUFFICIENT for stale HTTP response/browser-cookie ordering acceptance). |
| Auth runtime status | `EXISTING_MERGED_CODE_PRESENT / AUTH_006_RUNTIME_MODIFICATION_AUTHORIZED=NONE / FENCE_CORRECTION_RUNTIME=NOT_YET_AUTHORIZED` | Merged Auth runtime code exists in baseline under `apps/web/src/auth/**`. `AUTH-006` authorizes no runtime edits under this task. `AUTH-003`/`AUTH-005` fence corrections not yet authorized/implemented. |

## Test evidence recorded by AUTH-001

| Command | Result |
|---|---|
| `uv sync --project apps/api --all-groups --locked` | `PASS`; no manifest or lockfile change |
| `uv run --project apps/api pytest tests/api -q` | `PASS`; 5 passed |
| `uv run --project apps/api pytest tests/database/test_auth_constraints.py -q` | `PASS`; 21 passed against an isolated disposable PostgreSQL 16 |
| `uv run --project apps/api pytest -q` | `PASS`; 174 passed |
| `tests/auth` | `ABSENT`; Auth runtime unit tests PRESENT_IN_BASELINE under `apps/web/src/auth/**`; AUTH-005 cross-runtime acceptance NOT_YET_TESTED / FUTURE_INTEGRATION_REQUIREMENT |

## Contract Finalization Summary

`AUTH-006` contract finalization is `COMPLETE / PENDING_A2_AUTH_REVIEW`.

Target Version: `CONTRACT-AUTH-001@1.2.0-draft.1`

### Authoritative Final Owner Matrix

| Consumer | Task | Reviewed Head | Disposition | Required Auth Corrections |
|---|---|---|---|---|
| `A2-UI` | `AUTH-005-CONSUMER-REVIEW-A2-UI-001` | Baseline `5ffa899` | `ACCEPTED_WITH_CONSTRAINTS` | `NONE` |
| `A2-SECURITY` | `AUTH-005-CONSUMER-REVIEW-A2-SECURITY-001` | Baseline `5ffa899` | `ACCEPTED_WITH_CONSTRAINTS` | `NONE` |
| `A2-DEPLOYMENT` | `AUTH-005-CONSUMER-REVIEW-A2-DEPLOYMENT-001` | Baseline `5ffa899` | `ACCEPTED_WITH_CONSTRAINTS` | `NONE` |
| `A2-INTEGRATION` | `AUTH-005-CONSUMER-REVIEW-A2-INTEGRATION-001` | Baseline `5ffa899` | `ACCEPTED_WITH_CONSTRAINTS` | `NONE` |

### Implementation Authorization Explicit Prohibition

`CONTRACT-AUTH-001@1.2.0-draft.1` finalization does **NOT** authorize runtime implementation:
- Existing merged Auth runtime state: Present in baseline under `apps/web/src/auth/**` (including `AuthAdapter`, state machine, correlation, storage boundary, redirect, types, and tests).
- `AUTH-006` runtime modification authorization: `NONE` / `NO_RUNTIME_MODIFICATION_AUTHORIZED`.
- `AUTH-003` / `AUTH-005` fence correction runtime implementation: `NOT_YET_AUTHORIZED` / `NOT_YET_IMPLEMENTED`.
- Frontend Auth `/auth/callback`: `NOT_IMPLEMENTED / NOT_AUTHORIZED`.
- Backend JWT/JWKS: `NOT_IMPLEMENTED / NOT_AUTHORIZED`.
- Provider runtime: `NOT_PROVISIONED / NOT_TESTED`.
- `UI-004`: `NOT_AUTHORIZED`.
- `AUTH-003`: `NOT_AUTHORIZED`.
- Release: `NOT_READY`.

Next action: A2-AUTH independent review of this contract finalization package across all modified files.
