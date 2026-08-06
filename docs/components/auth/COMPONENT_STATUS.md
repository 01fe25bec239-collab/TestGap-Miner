# Auth Component Status

- Date: 2026-08-06
- Agent 2: `A2-AUTH`
- Paired Agent 3: `A3-AUTH`
- Current task:
  `AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001-A3-C2`
- Prior correction task:
  `AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001-A3-C1`
- Originating task: `AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001-A3`
- Parent task: `AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001`
- A2-AUTH review of the originating draft:
  `CHANGES_REQUIRED_BEFORE_A2_AUTH_ACCEPTANCE`
- A2-AUTH review of the `A3-C1` corrected draft:
  `CHANGES_REQUIRED_BEFORE_A2_AUTH_ACCEPTANCE`
- Prompt type: `A2_AUTH_CORRECTION / A3_DOCUMENTATION_EXECUTION_AND_VALIDATION`
- Scope: `AUTH_CONTRACT_AND_DESIGN_DOCUMENTATION_ONLY`
- Base commit: `006cc885161ff49be582a9fa08f353a70c31c7b1`
- Worktree: `/Users/omkar/Documents/TestGap-Miner-wt-auth-002-session-contract`
- Branch: `agent2/auth-002-session-contract`
- Audit output: `docs/components/auth/AUTH-001_AUDIT.md`
- Contract: `CONTRACT-AUTH-001@1.1.0-draft.1` — `DRAFT_FOR_CONSUMER_REVIEW /
  NOT_IMPLEMENTATION_READY / NOT_IMPLEMENTED / NOT_TESTED`
- `ASSUMED`: `NONE`

## Current state

| Area | State | Evidence / next action |
|---|---|---|
| `AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001-A3-C2` | `CORRECTED / UNSTAGED / PENDING_A2_AUTH_REVIEW` | A2-AUTH returned a second `CHANGES_REQUIRED_BEFORE_A2_AUTH_ACCEPTANCE` on the `A3-C1` text. Two corrections applied in the same seven files at the same baseline `006cc88`: (1) the callback-correlation record given a coherent two-phase lifecycle — `PENDING_ATTEMPT_CORRELATION` then `COMPLETED_CALLBACK_CORRELATION` — whose completed phase survives successful completion for a bounded, non-indefinite post-completion window, replacing text that required post-success duplicate correlation while also removing the record at the successful terminal outcome; (2) `INVALID_CALLBACK` narrowed to classify the callback attempt only, so an independently established, known-valid session is preserved rather than invalidated, while a session of unknown validity still fails closed. Recorded as `AUTH-DEC-040` and `AUTH-DEC-041`; no new issue opened, `AUTH-ISSUE-025` broadened. Contract version and classification unchanged. Documentation only. A2-AUTH acceptance is not claimed and remains outstanding. |
| `AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001-A3-C1` | `SUPERSEDED_BY_A3-C2 / CORRECTED / UNSTAGED / PENDING_A2_AUTH_REVIEW` | A2-AUTH returned `CHANGES_REQUIRED_BEFORE_A2_AUTH_ACCEPTANCE` on the original draft. Four corrections applied in the same seven files at baseline `006cc88`: fail-closed `REFRESH_PENDING` modes, callback duplicate/replay correlation, scoped cross-context refresh limits, and Auth-owned intended-return state binding. Recorded as `AUTH-DEC-036` through `AUTH-DEC-039`; opened `AUTH-ISSUE-025` and `AUTH-ISSUE-026`. Contract version and classification unchanged. Documentation only. Its callback-correlation lifetime and its `INVALID_CALLBACK` session outcome are superseded by the `A3-C2` corrections; the rest stands. |
| `AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001-A3` | `SUPERSEDED_BY_A3-C1 / DRAFTED / UNSTAGED` | Seven Auth-owned files drafted at baseline `006cc88`. `CONTRACT-AUTH-001` raised to `1.1.0-draft.1` with the `AUTH-002` sign-in, callback, session, custody, refresh, sign-out, redirect, adapter, error, Backend-boundary and Security sections plus 20 conceptual fixtures. Documentation only. Its `REFRESH_PENDING`, duplicate-callback, single-flight and return-path text is superseded by the `A3-C1` and `A3-C2` corrections. |
| `AUTH-DEPENDENCY-RECONCILIATION-001-A3` | `HISTORICAL / PASS / VERIFIED_COMPLETE / A2_AUTH_ACCEPTED / MERGED` | `COMPLETED`. The six-file reconciliation package merged through pull request #21, implementation commit `fb89d72`, merge commit `ba4247a`. Its commit, push and PR actions are finished; no action remains. The old reconciliation branch `agent2/auth-dependency-reconciliation` and worktree `/Users/omkar/Documents/TestGap-Miner-wt-auth-dependency-reconciliation` are `SUPERSEDED` and are not used by the current task. |
| `AUTH-001` | `PASS / VERIFIED_COMPLETE / MERGED` | `AUTH-001-C1`: `PASS`. `AUTH-001-C2`: `PASS`. A2-AUTH accepted the complete audit package and it merged through pull request #17; no additional audit repair is required. |
| `AUTH-DEP-004` | `ACCEPTED_WITH_CONSTRAINTS / ACKNOWLEDGED / MERGED` | A2-DEPLOYMENT accepted with constraints; A2-AUTH acknowledged. Durably merged through pull request #20, merge commit `fc549fa1a4c77f4835acefbb4f937c35ad6e8f76`. Evidence: `docs/components/deployment/DECISION_LOG.md`, `docs/components/deployment/ENVIRONMENT_VARIABLES.md`. |
| `AUTH-DEP-010` | `ACCEPTED_WITH_CONSTRAINTS / ACKNOWLEDGED` | A2-UI accepted with constraints; A2-AUTH acknowledged. UI ownership established through pull request #19. Evidence: `docs/specifications/A2_UI_MANAGER.md` and the UI-owned durable records under `docs/components/ui/`. |
| Accepted human identity architecture | `APPROVED_FOR_AUTH_CONTRACT_AND_DESIGN` | Deployment-owned design: `SUPABASE_AUTH_WITH_GITHUB_OAUTH`; canonical issuer `https://<SUPABASE_PROJECT_REF>.supabase.co/auth/v1`; audience `authenticated`; JWKS `https://<SUPABASE_PROJECT_REF>.supabase.co/auth/v1/.well-known/jwks.json`. Accepted design values only; not proof of configured runtime. |
| `AUTH-002` contract/design | `DRAFTED / PENDING_A2_AUTH_REVIEW / PENDING_CONSUMER_REVIEW` | Superseded `READY_FOR_AUTH_002_CONTRACT_AND_DESIGN`: the authorized contract/design task is executed and drafted. `CONTRACT-AUTH-001@1.1.0-draft.1` carries the full sign-in, callback, session, custody, refresh, sign-out, redirect, adapter, error, Backend-boundary, Security and fixture content. Not accepted, not implementation-ready. |
| `CONTRACT-AUTH-001@1.1.0-draft.1` | `DRAFT_FOR_CONSUMER_REVIEW / NOT_IMPLEMENTATION_READY / NOT_IMPLEMENTED / NOT_TESTED` | Additive compatible minor over `1.0.0-draft.2`; no breaking change. Now carries the four A2-AUTH corrections (`AUTH-DEC-036`–`AUTH-DEC-039`) plus the second-round corrections (`AUTH-DEC-040`, `AUTH-DEC-041`), which restrict, or repair an internal contradiction in, the drafted behavior rather than extending it; the version identifier is unchanged because the draft was never accepted and no consumer implemented against it. Required consumers: `A2-UI`, `A2-SECURITY`, `A2-DEPLOYMENT`, `A2-BACKEND`, `A2-INTEGRATION`. No consumer has responded. Silence is not acceptance. |
| Session refresh semantics | `CORRECTED_IN_DRAFT / SECURITY_REVIEW_PENDING` | `REFRESH_PENDING` carries two modes: `PROVEN_CREDENTIAL` may keep existing content visible while deferring new protected requests; `UNPROVEN_CREDENTIAL` — expired token, Backend `401`, unknown validity — removes protected content and prohibits protected requests. Single-flight refresh is scoped to one adapter instance or browsing context; cross-tab, cross-request and cross-instance serialization is explicitly not claimed. `NOT_TESTED`. See `AUTH-ISSUE-026`. |
| Callback correlation and intended-return state | `SEMANTICS_DEFINED / MECHANISM_PENDING_A2_SECURITY` | A duplicate callback resolves only on proven correlation to the same sign-in attempt, flow and completed outcome; an existing session is not correlation. The intended-return state is Auth-owned, attempt-bound, expiry-limited, single-use and removed on success and failure alike, and is never accepted on syntactic safety alone. Storage and integrity mechanisms are deliberately not invented: `PENDING_A2_SECURITY_ACCEPTANCE` under `AUTH-DEP-011`. See `AUTH-ISSUE-025`. |
| Callback-correlation lifecycle | `SEMANTICS_DEFINED / WINDOW_PENDING_A2_SECURITY` | The correlation record is `PENDING_ATTEMPT_CORRELATION` from `beginSignIn` until the flow completes, then `COMPLETED_CALLBACK_CORRELATION` on successful first callback processing. The completed record survives successful completion for a bounded post-completion correlation window so that an immediate duplicate invocation and a post-success reload can correlate without another exchange and without another session; it is never valid indefinitely; and no failed, abandoned, malformed, expired or terminally rejected flow may produce one. After the window expires or the record is removed, a later invocation returns `INVALID_CALLBACK` with no exchange and no callback-directed navigation. Window length, representation, retention and cleanup are `PENDING_A2_SECURITY_ACCEPTANCE` under `AUTH-DEP-011`. See `AUTH-DEC-040` and `AUTH-ISSUE-025`. |
| Invalid callback versus existing session | `SEMANTICS_DEFINED / CONSUMER_REVIEW_PENDING` | `INVALID_CALLBACK` classifies the callback attempt only. Every rejection creates no session, performs no exchange, performs no callback-directed navigation, clears callback parameters, removes the rejected attempt's return state and emits the Security event. The resulting session state is conditional: `TERMINAL_SESSION_ERROR` where no independently established, known-valid session pre-existed the callback or where a pre-existing session's validity is unknown; otherwise the known-valid session is preserved as `AUTHENTICATED` while the callback fails. A preserved session is still never correlation and never proof of callback success, and an invalid callback never revokes a separately valid provider session. See `AUTH-DEC-041`; A2-UI question 16 and A2-SECURITY question 16. |
| `AUTH-002` implementation | `NOT_AUTHORIZED` | Runtime implementation `NOT_AUTHORIZED`; frontend implementation `NOT_AUTHORIZED`; provider runtime `NOT_PROVISIONED / NOT_TESTED`. Neither accepted design status nor a drafted contract authorizes implementation. |
| Token custody decision | `DECIDED_IN_DRAFT / SECURITY_REVIEW_PENDING` | The accepted storage constraints are satisfiable by the official `@supabase/ssr` integration with `createBrowserClient`/`createServerClient` cookie-backed PKCE sessions. `HttpOnly` is not achievable for the browser-readable session and is not an accepted constraint. Final cookie, `SameSite`, CSRF and sign-out-scope posture is an unresolved `A2-SECURITY` decision: `AUTH-DEP-011`. `NOT_TESTED`. |
| Provider provisioning | `NOT_STARTED / NOT_TESTED` | No Supabase project provisioning, GitHub OAuth provider configuration, Vercel project, production Dashboard hostname, TLS verification, production callback registration, or secret injection is proven by this repository. |
| `CONTRACT-AUTH-001@1.0.0-draft.2` | `HISTORICAL / ACKNOWLEDGED_AND_MERGED / SUPERSEDED_BY_1.1.0-draft.1` | A2-DATABASE recorded acknowledgement in `docs/components/database/COMPONENT_STATUS.md` and `DECISION_LOG.md`; merged into `origin/main`. Superseded as the current version by `1.1.0-draft.1`, which preserves all of its semantics. |
| `DB-002` | `PASS / VERIFIED_COMPLETE / MERGED` | Pull request #12, implementation commit `5506ab5`, merge commit `3701520`; closed by PR #13 (`1511f47`). Seven domain tables, five of them Auth-owned. |
| Contract task (`AUTH-DB002-CONTRACT-001`) | `PASS / COMPLETE` | Producer package accepted; consumer acknowledgement received and merged. No review action remains. |
| Auth identity persistence | `VERIFIED_COMPLETE` | `apps/api/app/db/models/auth.py`: `users`, `auth_subjects`, `github_installations`, `repositories`, `repository_access`. 21 Auth constraint tests executed 2026-08-02, all passing. |
| Auth implementation — human sign-in, session, OAuth callback | `NOT_STARTED` | Corrected at baseline `006cc88`: the earlier "no `apps/web`" evidence is `SUPERSEDED`. `apps/web` now exists, but it contains no Auth code. Verified: `apps/web/src/app` holds only `layout.tsx`, `page.tsx`, `providers.tsx`, `globals.css` and `page.test.tsx`; there is no `/auth/callback` route, no Auth adapter, no token-storage behavior, and no provider integration. `apps/web/package.json` lists no `@supabase/ssr` or `@supabase/supabase-js` dependency. |
| `apps/web` | `PRESENT / NO_AUTH_SURFACE` | Merged: `UI-002` Next.js scaffold (PR #26, `c5d4c8a`), `UI-003` MUI shell (PR #27, `e7de96f`), frontend regression foundation (PR #28, `006cc88`). Next.js 16 App Router with React 19 and MUI. UI-owned; not modified by this task. |
| `/auth/callback` route | `NOT_IMPLEMENTED` | Reserved. A2-UI owns route existence and UX; A2-AUTH owns semantics, frozen by `CONTRACT-AUTH-001@1.1.0-draft.1`; A2-DEPLOYMENT owns deployed registration. |
| Auth implementation — JWT validation and user context | `NOT_STARTED` | `apps/api/app/main.py` is three lines; no JWT/JWKS dependency in `apps/api/pyproject.toml`. |
| Auth implementation — GitHub App machine auth, installation tokens, App manifest | `NOT_STARTED` | No first-party app-ID, private-key, or token-exchange code; no GitHub App manifest exists. |
| Auth implementation — webhook authenticity | `NOT_STARTED` | No webhook route, raw-body handling, or `X-Hub-Signature-256` verifier. Durable delivery-GUID persistence is separately absent as a downstream integration gap. |
| Auth implementation — repository-scoped authorization | `PARTIAL` | Exact-tuple grant model persisted and tested; no runtime reads a grant to allow or deny anything. |
| Auth implementation — human approval and publication boundaries | `PARTIAL` | Semantics defined in `CONTRACT-AUTH-001` and `CONTRACT-WORKFLOW-001`; no enforcement code and no machine publication-actor record. |
| Auth implementation — CORS, CSRF, cookies, callback allowlist | `NOT_STARTED` | No middleware in `apps/api/app/main.py`. FastAPI's default emits no CORS headers, which is the restrictive default. |
| Auth implementation — logs, audit events, redaction | `NOT_STARTED` | No logging configuration in `apps/api/app/**`. Only the `DATABASE_URL` redaction exists. Blocked on `AUTH-DEP-005`. |
| Auth deployment configuration | `NAMES_REGISTERED / NOT_PROVISIONED / NOT_TESTED` | `docs/components/deployment/ENVIRONMENT_VARIABLES.md` now registers Auth-scoped variable **names** through `AUTH-DEP-004` (PR #20). Registration of names is not provisioning: no injected value, deployed environment, or runtime read is proven. |
| Auth tests and CI validation | `NOT_STARTED` | `tests/auth/` does not exist. CI runs the full 174-test suite but has no Auth-specific gate. |
| Auth runtime | `NOT_STARTED / NOT_TESTED` | No test in this repository exercises an authentication or authorization decision. Database constraint tests prove schema semantics only. |
| Inbound FastAPI boundary (`B4`) | `UNSAFE_IF_DEPLOYED_IMPLEMENTED_BEHAVIOR` | A running container binds Uvicorn to `0.0.0.0`; local `TestClient` evidence proves the default OpenAPI surface is unauthenticated. Severity is `LOW` at the empty-route baseline and potentially `CRITICAL` if a protected route is added without `AUTH-003`. Actual public or production exposure is `NOT_TESTED`. |
| Secret handling | `PARTIAL` | `SecretStr` redaction proven by `tests/api/test_settings.py`; `.gitignore` excludes `.env*`, `*.pem`, `*.key`, `secrets/`; no Auth secret is defined or handled. |

## Test evidence recorded by AUTH-001

| Command | Result |
|---|---|
| `uv sync --project apps/api --all-groups --locked` | `PASS`; no manifest or lockfile change |
| `uv run --project apps/api pytest tests/api -q` | `PASS`; 5 passed |
| `uv run --project apps/api pytest tests/database/test_auth_constraints.py -q` | `PASS`; 21 passed against an isolated disposable PostgreSQL 16 |
| `uv run --project apps/api pytest -q` | `PASS`; 174 passed |
| `tests/auth` | `ABSENT`; AUTH-SPECIFIC TEST SUITE `NOT_STARTED` / `NOT_TESTED` |

## Readiness

`AUTH-002` contract/design is `DRAFTED / PENDING_A2_AUTH_REVIEW /
PENDING_CONSUMER_REVIEW`. The prior `READY_FOR_AUTH_002_CONTRACT_AND_DESIGN`
state is `SUPERSEDED` because the authorized contract/design task has now been
executed. Both direct prerequisites remain satisfied: `AUTH-DEP-004` is
`SATISFIED_FOR_CONTRACT_AND_DESIGN` and `AUTH-DEP-010` is
`SATISFIED_FOR_OWNERSHIP_AND_COORDINATION`. `AUTH-DEP-006` is a future Backend
integration dependency, and `AUTH-DEP-009` is a GitHub App/webhook
configuration dependency; neither is a direct `AUTH-002` prerequisite. See
`AUTH-001_AUDIT.md` §13.

The drafted contract is not accepted. A2-AUTH manager review has not been
performed, and no consumer review has been received from `A2-UI`,
`A2-SECURITY`, `A2-DEPLOYMENT`, `A2-BACKEND`, or `A2-INTEGRATION`. Silence is
not acceptance.

`AUTH-002` runtime implementation is `NOT_AUTHORIZED`, `AUTH-002` frontend
implementation is `NOT_AUTHORIZED`, and the `AUTH-002` provider runtime is
`NOT_PROVISIONED / NOT_TESTED`. Contract/design work may begin only as a
separate, newly authorized A2-AUTH task.

Acceptance of `AUTH-DEP-004` and `AUTH-DEP-010` authorizes no runtime task. The
following remain unresolved or untested and are not reversed by the accepted
design status: actual Supabase project provisioning; actual GitHub OAuth
provider configuration; actual Vercel project; production Dashboard hostname;
TLS verification; production callback registration; secret injection; callback
runtime behavior; JWT validation; cookie implementation; CSRF implementation;
PKCE implementation; OAuth-state implementation; frontend Auth integration; and
Auth-specific tests.

`AUTH-003` remains `NOT_AUTHORIZED`. It still requires sequential `AUTH-002`
design work and Backend JWT/runtime coordination through `AUTH-DEP-006`.

`AUTH-004` remains `BLOCKED` by sequential predecessor `AUTH-003` and pending
`AUTH-DEP-009`, not `AUTH-DEP-008`. The required GitHub installation Database
records already exist.

`AUTH-005` remains `BLOCKED` by sequential predecessor `AUTH-004`,
`AUTH-DEP-006`, and `AUTH-DEP-009`. Delivery-GUID persistence is a downstream
integration gap, not a direct `AUTH-005` verifier prerequisite; it must be
resolved before end-to-end webhook processing and `AUTH-008` final acceptance.

`AUTH-ISSUE-011` is `RESOLVED_IN_DRAFT`. The `CONTRACT-AUTH-001` metadata no
longer describes DB-002 as a blocking, pending consumer. A2-DATABASE is now
recorded as `HISTORICAL_BLOCKING_CONSUMER / ACKNOWLEDGED_AND_IMPLEMENTED`, the
evidence baseline is updated to `006cc88`, and the closing limitations block
records `DB-002` as merged and unblocked. The resolution becomes durable only
after A2-AUTH acceptance and merge.

No Auth implementation, test, or configuration was created by this task. Auth
runtime remains `NOT_STARTED / NOT_TESTED`; frontend Auth behavior, provider
runtime and Backend JWT behavior remain `NOT_IMPLEMENTED / NOT_TESTED`.
`AUTH-002` implementation remains `NOT_AUTHORIZED`, and `UI-004` and
`AUTH-003` remain unauthorized.

The A2-AUTH correction round applied four required changes before acceptance
and closed no issue. It opened `AUTH-ISSUE-025` (undecided intended-return
state and callback-correlation mechanisms) and `AUTH-ISSUE-026` (cross-context
refresh is neither serialized nor tested). Both are `PENDING_A2_SECURITY` and
are unanswerable while `AUTH-ISSUE-024` stands, since no Security record set
exists; that remains Agent 1's to resolve and no Security file was created
here.

The second A2-AUTH correction round applied two further required changes before
acceptance, closed no issue and opened none. `AUTH-DEC-040` replaced a
contradiction internal to the `A3-C1` text — post-success duplicate correlation
was required while the correlation record was also removed at the successful
terminal outcome — with a two-phase lifecycle whose completed phase persists for
a bounded, non-indefinite post-completion window. `AUTH-DEC-041` separated
callback-attempt failure from session-validity failure, so `INVALID_CALLBACK` no
longer asserts that an independently established, known-valid session is
invalid. `AUTH-ISSUE-025` was broadened to carry the undecided window length,
representation, retention and cleanup; no sibling issue was opened for
`AUTH-DEC-041`, because it defers nothing to another owner. Every preserved
constraint from the first round still stands: two fail-closed `REFRESH_PENDING`
modes with one-way degradation, scoped single-flight refresh with no global
cross-tab claim, attempt-bound intended-return state, callback replay
resistance, an existing session never being correlation, the prohibited-storage
list, `Bearer`-only transport, and every `NOT_PROVISIONED`, `NOT_IMPLEMENTED`,
`NOT_TESTED` and `NOT_AUTHORIZED` status above.

Next action: A2-AUTH independent review of the corrected seven-file unstaged
draft, including SHA-256 verification of every changed file. On a pass, A2-AUTH and
the user manage staging, one documentation commit, a normal push, and one
draft pull request. Merge remains blocked until the `A2-UI`, `A2-SECURITY`,
`A2-DEPLOYMENT` and `A2-BACKEND` consumer reviews are received, material
conflicts are reconciled, and Agent 1 records the final cross-component
semantic decision.
