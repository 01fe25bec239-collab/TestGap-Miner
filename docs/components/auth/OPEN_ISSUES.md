# Auth Open Issues

- Date: 2026-08-08
- Current task:
  `AUTH-002-CONSUMER-CORRECTION-UI-SECURITY-001-A3`
- Authorized manager task:
  `AUTH-002-CONSUMER-CORRECTION-UI-SECURITY-001`
- Supersedes the narrower task:
  `AUTH-002-A2-UI-CONSUMER-CONFLICT-CORRECTION-001`, whose uncommitted
  Auth-side corrections are preserved and reconciled into this package
- Consumer reviews reconciled:
  `AUTH-002-CONSUMER-REVIEW-A2-UI-001` — `A2-UI` — `SPECIFICATION_CONFLICT`;
  `AUTH-002-CONSUMER-REVIEW-A2-SECURITY-001` — `A2-SECURITY` —
  `REJECTED_WITH_REASON`, seven required normative corrections
- Reviewed head for both: `7abe17af8e212bd2127160338ea6ef409da02101`
- Pull request: #29 — `OPEN / DRAFT / NOT_MERGED`
- Prior correction tasks:
  `AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001-A3-C2`,
  `AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001-A3-C1`
- Originating task: `AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001-A3`
- Parent task: `AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001`
- Prompt type: `VERSIONED_AUTH_CONTRACT_AND_DESIGN / A3_DOCUMENTATION_EXECUTION_AND_VALIDATION`
- Scope: `AUTH_CONTRACT_AND_DESIGN_DOCUMENTATION_ONLY`
- Base commit: `006cc885161ff49be582a9fa08f353a70c31c7b1`
- Evidence: `docs/components/auth/AUTH-001_AUDIT.md`,
  `docs/components/auth/CONTRACT-AUTH-001.md`
- Auth identity persistence: `VERIFIED_COMPLETE` and merged
- Auth runtime: `NOT_STARTED` / `NOT_TESTED`
- `CONTRACT-AUTH-001@1.1.0-draft.1`: `DRAFT_FOR_CONSUMER_REVIEW /
  NOT_IMPLEMENTATION_READY`
- `ASSUMED`: `NONE`

Severity vocabulary is `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`,
`INFORMATIONAL`. An absent feature is recorded as absence, not as a
vulnerability. `AUTH-ISSUE-016` records
`UNSAFE_IF_DEPLOYED_IMPLEMENTED_BEHAVIOR`: the repository proves runnable
container behavior, but actual public or production exposure is `NOT_TESTED`.

## Closed and reconciled issues

### `AUTH-ISSUE-001` — Auth contract and records were absent

- Classification: `CLOSED`
- Evidence: The Auth contract and its records exist; A2-AUTH accepted
  `1.0.0-draft.2`.
- Resolution: Closed by A2-AUTH acceptance.

### `AUTH-ISSUE-003` — Auth/Database contract-first sequencing

- Classification: `CLOSED`
- Evidence: A2-DATABASE recorded `CONTRACT-AUTH-001@1.0.0-draft.2` as
  `ACKNOWLEDGED_AND_MERGED` (`docs/components/database/COMPONENT_STATUS.md`,
  `DECISION_LOG.md`) and implemented DB-002 against it. `DB-002` is
  `PASS / VERIFIED_COMPLETE / MERGED` via PR #12 (`3701520`), closed by PR #13
  (`1511f47`). `CONTRACT-WORKFLOW-001@1.0.0-draft.1` is likewise merged.
- Resolution: Both preconditions are satisfied. DB-002 is no longer blocked.

### `AUTH-ISSUE-008` — Issuer comparison semantics were insufficiently explicit

- Classification: `CLOSED`
- Evidence: `CONTRACT-AUTH-001@1.0.0-draft.2` defines exact case-sensitive
  issuer storage and comparison; the merged schema implements it
  (`apps/api/app/db/models/auth.py:70-84`, `sa.Text`, default collation, no
  `citext` and no functional index). Verified by passing tests
  `test_case_distinct_issuer_and_subject_are_separate_identities` and
  `test_issuer_and_subject_are_stored_without_normalization`.
- Resolution: Closed by Database acknowledgement and merged implementation.

### `AUTH-ISSUE-009` — Access-grant expiration timing was insufficiently explicit

- Classification: `CLOSED`
- Evidence: The merged schema keeps `expires_at`, `expired_at`, and
  `revoked_at` distinct via the `expiry_distinct_from_revocation`,
  `revoked_at_present`, and `active_not_terminated` check constraints. Verified
  by four passing tests including
  `test_expired_access_may_not_borrow_revoked_at`.
- Resolution: Closed by Database acknowledgement and merged implementation.

## Issues carried forward

### `AUTH-ISSUE-002` — Shared registry omits the Database consumer

- Classification: `OPEN`
- Severity: `INFORMATIONAL`
- Evidence: The shared registry omits A2-DATABASE as a blocking
  `CONTRACT-AUTH-001` consumer, although DB-002 consumed and merged it.
- Impact: Coordination record only; no Auth work is blocked.
- Owning component: A2-INTEGRATION or Agent 1.
- Blocking task: none.
- Resolution path: `AUTH-DEP-003`.

### `AUTH-ISSUE-004` — Identity-provider design metadata is not frozen

- Classification: `RESOLVED_FOR_CONTRACT_AND_DESIGN`
- Severity: `MEDIUM` at the original baseline; no longer blocking `AUTH-002`
  contract and design
- Original evidence (historical): at the `AUTH-001` baseline,
  `docs/components/deployment/ENVIRONMENT_VARIABLES.md` registered eleven
  variables, all database-scoped, and no approved IdP, issuer, audience,
  JWKS/key source, dashboard domain, callback allowlist, TLS fact, client
  variable name, or secret-injection owner existed anywhere in the repository.
- Resolution evidence: `AUTH-DEP-004` is `ACCEPTED_WITH_CONSTRAINTS /
  ACKNOWLEDGED_BY_A2_AUTH / MERGED_VIA_PR_20` (merge commit `fc549fa`).
  A2-DEPLOYMENT recorded the approved provider
  (`SUPABASE_AUTH_WITH_GITHUB_OAUTH`), canonical issuer, audience, JWKS
  source, callback set, redirect policy, TLS and secret-injection ownership,
  and the Auth-scoped variable names.
- Resolution: The **design** metadata gap is closed. `AUTH-002` contract and
  design are no longer blocked by this issue.
- Residual — not resolved by this reconciliation: the accepted values are
  design values only. Actual Supabase project provisioning, GitHub OAuth
  provider configuration, Vercel project, production Dashboard hostname, TLS
  verification, production callback registration and secret injection remain
  `NOT_PROVISIONED / NOT_TESTED` and are owned by A2-DEPLOYMENT. The residual
  blocks Auth runtime, not Auth contract and design.

### `AUTH-ISSUE-005` — Workflow actor integration

- Classification: `PARTIALLY_RESOLVED`
- Severity: `MEDIUM`
- Evidence: `CONTRACT-WORKFLOW-001@1.0.0-draft.1` is accepted and merged, and
  `run_requests`/`runs` carry actor attribution. However
  `TERMINAL_ACTOR_TYPES = ("SYSTEM", "WORKFLOW", "WORKER", "HUMAN")`
  (`apps/api/app/db/models/workflow.py:129`) has no
  `GITHUB_APP_INSTALLATION` value.
- Impact: The contract's machine publication actor is not representable.
- Owning component: A2-AGENT-WORKFLOW, with A2-DATABASE for persistence.
- Blocking task: `AUTH-006` and `AUTH-008` final acceptance; not `AUTH-004`
  machine-token implementation.
- Resolution path: `AUTH-DEP-008`. Superseded in part by `AUTH-ISSUE-013`.

### `AUTH-ISSUE-006` — Authorization freshness and retention are not frozen

- Classification: `OPEN`
- Severity: `MEDIUM`
- Evidence: No Security guidance exists for revalidation freshness, retention,
  security-event shape, or redaction. `CONTRACT-AUTH-001` defers exact
  freshness.
- Impact: Blocks `AUTH-007` and `AUTH-008`.
- Owning component: A2-SECURITY.
- Blocking task: `AUTH-007`.
- Resolution path: `AUTH-DEP-005`.

### `AUTH-ISSUE-007` — Auth runtime is unimplemented

- Classification: `CONFIRMED_BY_AUDIT`
- Severity: `HIGH`
- Original evidence (historical): `AUTH-001` inventoried all 82 tracked files.
  The only first-party Auth artefacts were Database-owned persistence
  (`apps/api/app/db/models/auth.py`), Database-owned schema tests
  (`tests/database/test_auth_constraints.py`), and the Auth documentation
  records. `apps/api/app/main.py` is three lines. `apps/web` did not exist.
- Corrected current evidence at baseline `006cc88`: the "`apps/web` does not
  exist" statement is `SUPERSEDED`. `apps/web` now exists through merged
  `UI-002` (PR #26), `UI-003` (PR #27) and the frontend regression foundation
  (PR #28). It contains no Auth surface: `apps/web/src/app` holds only
  `layout.tsx`, `page.tsx`, `providers.tsx`, `globals.css` and `page.test.tsx`;
  there is no `/auth/callback` route, no Auth adapter, no token-storage
  behavior and no provider integration; and `apps/web/package.json` declares no
  Supabase dependency. The finding itself is unchanged: Auth runtime remains
  absent.
- Impact: No human sign-in, session, JWT validation, GitHub App
  authentication, webhook verification, authorization enforcement, or
  publication control exists.
- Owning component: A2-AUTH.
- Blocking task: `AUTH-002` implementation onward.
- Resolution path: sequential `AUTH-002`…`AUTH-008` after their dependencies
  are accepted. `CONTRACT-AUTH-001@1.1.0-draft.1` defines `AUTH-002` semantics
  but implements nothing and authorizes no implementation.

## Issues opened by AUTH-001

### `AUTH-ISSUE-010` — No Auth-specific test suite and no Auth CI gate

- Classification: `UNTESTED_BEHAVIOR`
- Severity: `MEDIUM`
- Evidence: `ls -d tests/auth` → `No such file or directory`. CI
  (`.github/workflows/deployment.yml:24`) runs the full 174-test suite but has
  no Auth-specific step. The 21 passing tests in
  `tests/database/test_auth_constraints.py` state in their own header that they
  test no authorization decision.
- Impact: Any future Auth control would ship without dedicated coverage.
- Owning component: A2-AUTH.
- Blocking task: every `AUTH-002`…`AUTH-008` acceptance.
- Resolution path: each Auth implementation task creates `tests/auth/**`
  alongside its control. **AUTH-SPECIFIC TEST SUITE: `NOT_STARTED` /
  `NOT_TESTED`.**

### `AUTH-ISSUE-011` — `CONTRACT-AUTH-001` metadata contradicts merged state

- Classification: `RESOLVED_IN_DRAFT / PENDING_A2_AUTH_ACCEPTANCE_AND_MERGE`
- Severity: `MEDIUM` at the original baseline
- Original evidence (historical): `CONTRACT-AUTH-001.md` recorded
  `Blocking consumer: A2-DATABASE` and `Blocking consumer task: DB-002`, and
  its closing section stated DB-002 was still blocked, after A2-DATABASE had
  acknowledged and merged the contract and DB-002 was `MERGED`.
- Original impact: A reader of the contract alone would conclude DB-002 was
  still blocked and the contract still unaccepted.
- Owning component: A2-AUTH.
- Resolution evidence: `AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001-A3`
  revised the metadata under the compatible `1.1.0-draft.1` revision.
  A2-DATABASE is recorded as `HISTORICAL_BLOCKING_CONSUMER /
  ACKNOWLEDGED_AND_IMPLEMENTED`; the required consumers for the new additions
  are `A2-UI`, `A2-SECURITY`, `A2-DEPLOYMENT`, `A2-BACKEND` and
  `A2-INTEGRATION`; the evidence baseline is `006cc88`; and the closing
  limitations block records `DB-002` as merged, unblocked, and creating no new
  Database obligation.
- Residual: the correction is unstaged and uncommitted. It becomes durable only
  after A2-AUTH acceptance and merge. Until then this issue is resolved in
  draft only.

### `AUTH-ISSUE-012` — Run requests cannot reconstruct the exact authorization tuple

- Classification: `DEPENDENCY_GAP`
- Severity: `MEDIUM`
- Evidence: `apps/api/app/db/models/workflow.py:200-207` — `run_requests` has
  `repository_id` and `requested_by_subject` but no installation reference.
  `CONTRACT-AUTH-001` scopes repository authorization by the exact
  `user + installation + repository` tuple.
- Impact: `AUTH-006` cannot authorize a run request against the contract tuple
  from the request row alone.
- Owning component: A2-DATABASE, after an A2-AUTH ruling.
- Blocking task: `AUTH-006`.
- Resolution path: `AUTH-DEP-007`. This is an absent field, not a defect in
  merged DB-002 — DB-002 implemented exactly what the accepted contracts
  specified.

### `AUTH-ISSUE-013` — No machine actor for `PUBLICATION_EXECUTE`

- Classification: `DEPENDENCY_GAP`
- Severity: `MEDIUM`
- Evidence: `CONTRACT-AUTH-001` §Initial authorization action vocabulary
  requires `PUBLICATION_EXECUTE` to use the GitHub App installation actor with
  a traceable authorized trigger. No such actor value or record exists;
  `TERMINAL_ACTOR_TYPES` at `apps/api/app/db/models/workflow.py:129` omits it.
- Impact: Publication cannot be attributed to a machine actor as the contract
  requires. This blocks repository-scoped publication authorization in
  `AUTH-006` and `AUTH-008` final acceptance, not GitHub App JWT or
  installation-token implementation in `AUTH-004`.
- Owning component: A2-AGENT-WORKFLOW with A2-DATABASE.
- Blocking task: `AUTH-006`, `AUTH-008`.
- Resolution path: `AUTH-DEP-008`.

### `AUTH-ISSUE-014` — Human run-request attribution is subject-keyed, not user-keyed

- Classification: `CONTRACT_ALIGNMENT_NOTE`
- Severity: `LOW`
- Evidence: `run_requests.requested_by_subject → auth_subjects.id`
  (`apps/api/app/db/models/workflow.py:205-207`), while `CONTRACT-AUTH-001`
  §Actor types defines the `HUMAN_USER` actor as requiring `user_id`.
- Impact: None at rest — the canonical user is reachable by join through
  `auth_subjects.user_id`, and subject-keying preserves historical attribution
  when a subject is revoked. It does require an explicit ruling so `AUTH-006`
  resolves the actor consistently.
- Owning component: A2-AUTH.
- Blocking task: `AUTH-006`.
- Resolution path: A2-AUTH records the resolution rule in `AUTH-006`. No schema
  change is requested.

### `AUTH-ISSUE-015` — Auth environment variable registration

- Classification: `PARTIALLY_RESOLVED`
- Severity: `MEDIUM`
- Original evidence (historical): at the `AUTH-001` baseline, neither
  `.env.example`, `ENVIRONMENT_VARIABLES.md`, `compose.yml`, `Dockerfile`, nor
  `.github/workflows/deployment.yml` defined any Auth variable.
- Resolved part: `AUTH-DEP-004` (PR #20) registered the human IdP and callback
  variable **names** in `docs/components/deployment/ENVIRONMENT_VARIABLES.md`.
  Name registration is not provisioning: no value is injected and no deployed
  environment is proven.
- Remaining part: the GitHub App ID, GitHub App private-key and
  webhook-secret variable names remain absent, needed by `AUTH-004` and
  `AUTH-005`.
- Owning component: A2-DEPLOYMENT.
- Blocking task: `AUTH-004` and `AUTH-005` through `AUTH-DEP-009`. No longer
  blocks `AUTH-002` contract and design.
- Resolution path: `AUTH-DEP-009` registers the remaining GitHub App/webhook
  variable names and runtime metadata.

### `AUTH-ISSUE-016` — API is authenticate-by-exception rather than deny-by-default

- Classification: `UNSAFE_IF_DEPLOYED_IMPLEMENTED_BEHAVIOR`
- Severity: `LOW` at this baseline; `CRITICAL` once any protected route is
  added without `AUTH-003`
- Evidence: `apps/api/app/main.py:3` is a bare `FastAPI()` with no middleware
  and no dependency. `Dockerfile:17` ships
  `uvicorn app.main:app --host 0.0.0.0 --port 8000` as the container command.
  `tests/api/test_main.py:4-8` proves `/openapi.json` returns 200 with no
  credentials, and FastAPI additionally serves `/docs` and `/redoc` by default.
- Impact: In a running and network-reachable container, a caller can reach the
  default documentation/OpenAPI surface without credentials. The repository
  does not prove production deployment, public reachability, or an internet
  caller; those are `NOT_TESTED`. Severity is `LOW` at the empty-route baseline
  and potentially `CRITICAL` if a protected route is added without `AUTH-003`.
- Owning component: A2-AUTH with A2-BACKEND.
- Blocking task: `AUTH-003`; documentation-surface control belongs to
  `AUTH-007`.
- Resolution path: `AUTH-003` introduces a default-deny request dependency
  before any protected route exists; `AUTH-007` decides the docs-surface
  policy per environment.

### `AUTH-ISSUE-017` — Dashboard frontend ownership was unassigned

- Classification: `RESOLVED_FOR_OWNERSHIP_AND_COORDINATION`
- Severity: `MEDIUM` at the original baseline; ownership no longer unassigned
- Original evidence (historical): `find . -type d -name web` returned nothing;
  `ls apps/` returned exactly `api`; no frontend manifest or lockfile was
  tracked, and no component owned trust boundaries B1–B3.
- Resolution evidence: `AUTH-DEP-010` is `ACCEPTED_WITH_CONSTRAINTS /
  ACKNOWLEDGED_BY_A2_AUTH / UI_OWNERSHIP_ESTABLISHED_VIA_PR_19`. A2-UI owns the
  future Dashboard frontend, future `apps/web/**` after separate
  authorization, and the user-facing `/auth/callback` route and its UX;
  A2-AUTH retains callback, session, identity-resolution, token-custody, PKCE
  and OAuth-state semantics. Records: `docs/specifications/A2_UI_MANAGER.md`
  and `docs/components/ui/**`.
- Resolution: The ownership and coordination gap is closed. See
  `AUTH-DEP-010` in `DEPENDENCY_REQUESTS.md` for the full boundary.
- Residual — updated at baseline `006cc88`: the "no frontend exists" statement
  is `SUPERSEDED`. A frontend now exists at `apps/web`, but it has no Auth
  surface and no `/auth/callback` route. `AUTH-002` frontend implementation and
  frontend Auth integration tests remain `NOT_AUTHORIZED` and `NOT_TESTED`,
  and `UI-004` remains unauthorized. A3-AUTH may not modify UI-owned paths
  without A2-UI coordination; no UI-owned path was modified by this task.

### `AUTH-ISSUE-018` — CI workflow contains literal placeholder passwords

- Classification: `DEFERRED_NON_GOAL`
- Severity: `INFORMATIONAL`
- Evidence: `.github/workflows/deployment.yml:15-18` sets values such as
  `ci-app-placeholder`; the container is destroyed in the same job at lines
  30-31.
- Impact: None. These are placeholders for an ephemeral CI PostgreSQL, not
  credentials to any real system.
- Owning component: A2-DEPLOYMENT.
- Blocking task: none.
- Resolution path: accepted as-is; revisit only if CI ever reaches a
  non-ephemeral database.

### `AUTH-ISSUE-019` — Durable webhook delivery idempotency is absent

- Classification: `DOWNSTREAM_INTEGRATION_GAP`
- Severity: `HIGH`
- Evidence: No durable delivery-GUID or webhook idempotency record exists in
  the DB-002 schema.
- Impact: `AUTH-005` can implement and test raw-body signature verification,
  delivery-GUID extraction, repository-identity extraction, safe failure
  logging, and rejection without downstream calls. Durable duplicate-delivery
  rejection remains required before end-to-end webhook processing and
  `AUTH-008` final acceptance, but it is not a direct `AUTH-005` verifier
  prerequisite.
- Owning component: Not selected by `AUTH-001`; future
  Backend/Workflow/Database integration must assign ownership.
- Blocking task: end-to-end webhook processing and `AUTH-008` final
  acceptance; not `AUTH-005` verifier implementation.
- Resolution path: the future integration owner defines durable idempotency.
  This continuation authorizes no new Database model or dependency contract.

## Issues opened by `AUTH-002` contract and design

### `AUTH-ISSUE-020` — Browser session custody cannot be `HttpOnly`

- Classification: `OWNER_DECISION_REQUIRED`
- Severity: `MEDIUM`
- Evidence: current primary Supabase documentation states that `HttpOnly`
  cookies are "not necessary" for its session model and that "the browser-based
  side of your application needs access to the refresh token to properly
  maintain a browser session anyway". The official `@supabase/ssr` browser
  client reads and writes the session cookie from browser code, so an
  `HttpOnly` session cookie is incompatible with the accepted architecture.
- Impact: none on the accepted constraints, which prohibit `localStorage`,
  `sessionStorage` and duplicate stores but never required `HttpOnly`. The
  browser-readable refresh token is nevertheless a Security posture question
  that A2-SECURITY must decide explicitly rather than inherit by default.
- Owning component: A2-SECURITY with A2-AUTH.
- Blocking task: `AUTH-002` implementation, `UI-004`, `AUTH-007`.
- Resolution path: `AUTH-DEP-011`.

### `AUTH-ISSUE-021` — The default browser client factory violates the storage constraints

- Classification: `IMPLEMENTATION_HAZARD`
- Severity: `HIGH` if implemented incorrectly; `INFORMATIONAL` at this
  baseline because no Auth code exists
- Evidence: `createClient` from `@supabase/supabase-js` defaults to persisting
  the session to `localStorage` in a browser. The accepted constraints prohibit
  any access or refresh token in `localStorage`. `apps/web/package.json`
  currently declares neither package, so nothing is presently violated.
- Impact: a future implementer following a generic Supabase quickstart rather
  than the server-side rendering guide would silently violate a binding
  storage constraint.
- Owning component: A2-AUTH, enforced by A2-UI at implementation time.
- Blocking task: none now; a required check for `UI-004` and `AUTH-002`
  implementation acceptance.
- Resolution path: `CONTRACT-AUTH-001@1.1.0-draft.1` prohibits the defaulting
  factory in browser code and mandates `createBrowserClient` from
  `@supabase/ssr`. Acceptance requires an explicit implementation-time check.

### `AUTH-ISSUE-022` — Sign-out does not revoke issued Backend access tokens

- Classification: `ACCEPTED_LIMITATION / OWNER_DECISION_REQUIRED`
- Severity: `MEDIUM`
- Evidence: the accepted architecture gives FastAPI a Supabase JWT access
  token validated against JWKS. Nothing in the accepted provider or Backend
  design proves that a sign-out invalidates an already-issued access token
  before its expiry.
- Impact: after sign-out, a previously issued access token may remain
  acceptable to FastAPI until it expires. The contract therefore forbids any
  record from claiming that sign-out revokes issued Backend tokens.
- Owning component: A2-SECURITY with A2-BACKEND.
- Blocking task: `AUTH-003`, `AUTH-007`, `AUTH-008` final acceptance.
- Resolution path: `AUTH-DEP-011` and `AUTH-DEP-014` decide the acceptable
  residual window and any revocation or short-lifetime requirement.

### `AUTH-ISSUE-023` — UI durable records contradict merged frontend evidence

- Classification: `EXTERNAL_RECORD_INCONSISTENCY`
- Severity: `LOW`
- Evidence: `docs/components/ui/COMPONENT_STATUS.md` records `apps/web` as
  `ABSENT` and frontend implementation as `NOT_STARTED`;
  `docs/components/ui/TASK_LEDGER.md` records `UI-002` and `UI-003` as
  `NOT_AUTHORIZED`. Merged repository evidence contradicts all four: `apps/web`
  exists through PR #26, PR #27 and PR #28.
- Impact: coordination and review accuracy only. No Auth work is blocked, and
  the Auth contract relies on repository evidence rather than the stale
  statements.
- Owning component: A2-UI. These are UI-owned files; A3-AUTH must not modify
  them and did not.
- Blocking task: none.
- Resolution path: raised to A2-UI as a review question in `AUTH-DEP-012`.
- Status: `RESOLVED_BY_UI_OWNER_VIA_PR_30`. `UI-DEC-027`, merged in PR #30
  (merge commit `63093f22c37a0fc6affe168f7d5230107b05cdf3`), reconciles the UI
  durable records to the merged repository evidence: `apps/web` `PRESENT`,
  `UI-002` and `UI-003` `MERGED`, regression foundation `MERGED`. The same
  record keeps Auth frontend `NOT_IMPLEMENTED / NOT_TESTED / NOT_AUTHORIZED`,
  Auth runtime `NOT_IMPLEMENTED / NOT_TESTED`, provider runtime
  `NOT_PROVISIONED / NOT_TESTED`, `UI-004` `BLOCKED / NOT_AUTHORIZED` and
  `/auth/callback` `RESERVED / NOT_IMPLEMENTED`. A merged frontend foundation is
  not Auth evidence and is not recorded as any.

### `AUTH-ISSUE-024` — No A2-SECURITY component records exist

- Classification: `DEPENDENCY_GAP`
- Severity: `MEDIUM`
- Evidence: `docs/components/` contains `agent-workflow`, `auth`, `backend`,
  `database`, `deployment`, `integration` and `ui`. There is no
  `docs/components/security/` directory and no Security-owned durable record
  anywhere in the repository. Every Security requirement relevant to sessions,
  cookies, CSRF, PKCE, OAuth state, redirects, redaction and token handling
  currently exists only inside other components' records.
- Impact: `AUTH-DEP-005` and the new `AUTH-DEP-011` have a named owner but no
  durable record set to respond in, so the Security consumer review cannot be
  filed anywhere at present.
- Owning component: Agent 1, to establish A2-SECURITY records.
- Blocking task: `AUTH-002` acceptance, `AUTH-007`, `AUTH-008`.
- Resolution path: Agent 1 assigns or bootstraps the Security component
  records. `AUTH-002` cannot be merged on the basis of an absent Security
  reviewer.

## Issues opened by the A2-AUTH correction round

### `AUTH-ISSUE-025` — Return-state and callback-correlation mechanisms are undecided

- Classification: `OWNER_DECISION_REQUIRED`
- Severity: `MEDIUM`
- Evidence: `AUTH-DEC-037` requires a callback-completion correlation record
  proving that a duplicate invocation belongs to the same sign-in attempt,
  callback flow and completed outcome, because an existing session is not
  correlation. `AUTH-DEC-040` gives that record a two-phase lifecycle —
  `PENDING_ATTEMPT_CORRELATION` at sign-in, then
  `COMPLETED_CALLBACK_CORRELATION` on successful first callback processing —
  whose completed phase must survive successful completion for a bounded,
  non-indefinite post-completion window, and which a failed or rejected flow
  must never produce. `AUTH-DEC-039` requires an Auth-owned intended-return state
  that is attempt-bound, expiry-limited, single-use, integrity-protected or held
  in Auth-controlled same-origin state, and removed after success and failure
  alike. `CONTRACT-AUTH-001@1.1.0-draft.1` states the required properties and
  lifecycle of both and deliberately does **not** state a mechanism, a
  representation, or a duration.
- Impact: the contract is complete on semantics and intentionally incomplete on
  mechanism. An implementer must not select a storage or integrity scheme, must
  not choose the retention duration of the bounded post-completion correlation
  window, and must not reuse provider OAuth `state` as a return-path container,
  before A2-SECURITY decides. Nothing here is recorded as an accepted final
  Security decision. Until the window length is decided, both failure modes
  remain open: a window too short breaks the required post-success duplicate and
  reload correlation, and a window too long extends reusable completion evidence
  further than Security has accepted.
- Owning component: A2-SECURITY with A2-AUTH.
- Blocking task: `AUTH-002` acceptance and implementation, `UI-004`.
- Resolution path: `AUTH-DEP-011` questions 11, 12 and 15. Blocked in practice by
  `AUTH-ISSUE-024`, since no Security record set exists to answer in.
- **Update — mechanism decided, storage substrate still open.** `A2-SECURITY`
  has since decided both mechanisms. The correlation record is
  `AUTH_CONTROLLED / PROVIDER_NEUTRAL / SERVER_SIDE / EPHEMERAL`, with the
  browser carrying only an opaque handle in a separate `HttpOnly`, `Secure`,
  `SameSite=Lax`, host-only, callback-path-restricted Auth-owned cookie;
  `PENDING_ATTEMPT_CORRELATION` lives at most 10 minutes from initiation and
  `COMPLETED_CALLBACK_CORRELATION` exactly 120 seconds from successful
  completion, with an atomic transition and fail-closed behavior when the store
  is unavailable or the handle unverifiable (`AUTH-DEC-049`). The intended-return
  path lives only inside the server-side pending record, atomically single-use,
  never in any browser persistence, falling back to `/` on a missing record,
  integrity failure, replay or store failure (`AUTH-DEC-050`). The two failure
  modes this issue previously named — a window too short to permit post-success
  correlation, or too long to be acceptable — are resolved by the frozen
  120-second value. What remains open here is narrower and belongs to a
  different owner: the **physical storage technology and deployment topology**
  for the server-side ephemeral store, plus the key-custody requirements for
  handle integrity. Both are `SECURITY_REQUIRED /
  PENDING_AFFECTED_OWNER_COMPATIBILITY_REVIEW` by `A2-DEPLOYMENT` under
  `AUTH-DEP-013`. No vendor, product or physical technology is selected by Auth.
  This issue stays `OPEN` on that residue.

### `AUTH-ISSUE-026` — Cross-context refresh is not serialized and is untested

- Classification: `ACCEPTED_LIMITATION / UNTESTED_BEHAVIOR`
- Severity: `MEDIUM`
- Evidence: the accepted `@supabase/ssr` cookie-backed model shares session
  state between browsing contexts, but nothing in the accepted provider design
  serializes refresh across separate browser tabs, parallel server requests or
  separate runtime instances. `onAuthStateChange` and `BroadcastChannel`
  deliver notifications, not serialization guarantees. No test in this
  repository exercises concurrent cross-context refresh; the behavior is
  `NOT_TESTED`.
- Impact: concurrent cross-context refresh may produce a stale cookie, a
  temporarily null session, or one successful refresh paired with one rejected
  refresh. `AUTH-DEC-038` requires every such race to fail closed, tolerate
  provider cookie synchronization, avoid restoring stale authenticated state,
  use at most one bounded retry after a newer valid session is observed, and
  never create an automatic refresh loop. No Auth record may claim global
  single-flight refresh.
- Owning component: A2-AUTH, with A2-SECURITY and A2-INTEGRATION confirmation.
- Blocking task: `AUTH-002` acceptance; runtime verification blocked by absent
  Auth implementation and provider provisioning.
- Resolution path: `AUTH-DEP-011` question 13 and `AUTH-DEP-015` questions 10
  and 11; runtime verification once `AUTH-002` implementation and provider
  provisioning are separately authorized.

## Issues opened by the A2-UI consumer response

### `AUTH-ISSUE-027` — A2-UI returned `SPECIFICATION_CONFLICT` against head `7abe17a`

- Classification: `CONSUMER_SPECIFICATION_CONFLICT`
- Severity: `HIGH`
- Substate: `UI_SIDE_CORRECTED_AND_MERGED / AUTH_SIDE_CORRECTED_IN_WORKTREE /
  PENDING_A2_AUTH_ACCEPTANCE_AND_PUSH / A2_UI_REREVIEW_REQUIRED /
  CONTRACT_ACCEPTANCE_BLOCKED / IMPLEMENTATION_READINESS_BLOCKED`
- Current owner-side state:

  | Side | State | Evidence |
  |---|---|---|
  | UI | `CORRECTED_AND_MERGED` | PR #30 — implementation commit `30deb92000a20d3837b2423b6bdee3ea3335a7f1`, merge commit `63093f22c37a0fc6affe168f7d5230107b05cdf3`, current `origin/main`; `UI-DEC-026`, `UI-DEC-027` |
  | Auth | `CORRECTED_IN_WORKTREE / PENDING_A2_AUTH_ACCEPTANCE_AND_PUSH` | uncommitted seven-file Auth package on branch `agent2/auth-002-session-contract`, head `7abe17af8e212bd2127160338ea6ef409da02101` |
  | `A2-UI` rereview | `REQUIRED` | no rereview of any corrected Auth head exists |
  | Contract acceptance | `BLOCKED` | — |
  | Implementation readiness | `BLOCKED` | — |
- Evidence: consumer `A2-UI`, review task
  `AUTH-002-CONSUMER-REVIEW-A2-UI-001`, reviewed head
  `7abe17af8e212bd2127160338ea6ef409da02101` on pull request #29
  (`OPEN / DRAFT / NOT_MERGED`), disposition `SPECIFICATION_CONFLICT`. Agent 1
  accepted that response as authoritative consumer input and authorized
  corrections on both sides. Recorded as `AUTH-DEC-042` and `AUTH-DEC-043`.
- Conflict A — cookie custody, UI-owned: the merged `UI-DEC-013` non-`HttpOnly`
  cookie prohibition conflicts with the canonical browser-readable
  `@supabase/ssr` session architecture this contract requires. `A2-UI` is
  authorized to supersede that conflicting meaning while preserving its
  `localStorage`, `sessionStorage` and duplicate-store prohibitions. Auth
  neither performed nor authored that correction; no UI file was modified by
  A3-AUTH. Owner-side state: `CORRECTED_AND_MERGED` — `A2-UI` merged it as
  `UI-DEC-026` and `UI-DEC-027` in PR #30. The merged text preserves the
  `localStorage` prohibition, the `sessionStorage` prohibition and the
  no-duplicate/shadow-session-store rule, permits only the canonical Auth-owned
  `@supabase/ssr` session through the Auth-owned adapter and only conditionally
  on A2-SECURITY acceptance of the final cookie posture, proposes `/` as the UI
  default and safe recovery route, and keeps `UI-004` `NOT_AUTHORIZED`. It
  states in its own text that it does not make Auth PR #29 acceptable and that
  `A2-UI` rereview remains required. Recorded as `AUTH-DEC-052`.
- Conflict B — default and recovery route, Auth-owned: Auth had not frozen the
  concrete route A2-UI proposed. Corrected: default post-sign-in destination
  `/`; preserved-session rejected-callback safe recovery destination `/`;
  rejected intended-return destination `NEVER_USED`.
- Impact: `CONTRACT-AUTH-001@1.1.0-draft.1` is not consumable by `A2-UI` as
  reviewed at `7abe17af`. `AUTH-DEP-012` is `OPEN / RESPONSE_RECEIVED /
  SPECIFICATION_CONFLICT_AT_7ABE17AF / UI_OWNER_CORRECTION_MERGED_VIA_PR_30 /
  AUTH_OWNER_CORRECTION_IN_PROGRESS / CORRECTED_HEAD_REREVIEW_REQUIRED /
  NOT_ACCEPTED`. `UI-004` remains `NOT_AUTHORIZED`.
  The browser-readable cookie posture is **no longer pending Security**:
  `A2-SECURITY` has accepted the browser-readable `@supabase/ssr` architecture
  as policy, and the final provider-session cookie posture is frozen through
  `AUTH-DEC-045`. What remains outstanding on this issue is narrower still now
  that the UI-owned durable-record correction has merged: the Auth-owned
  correction is unstaged and uncommitted pending A2-AUTH acceptance and push;
  `A2-DEPLOYMENT` runtime and configuration confirmation is still outstanding;
  and `A2-UI` rereview of the corrected PR #29 head is still required. No
  `A2-UI` acceptance of any Auth head is claimed, and PR #30 is not such an
  acceptance.
- Owning components: `A2-UI` for conflict A; `A2-AUTH` for conflict B.
- Blocking task: `AUTH-002` acceptance; `UI-004`; merge of PR #29.
- Resolution path — four required, two met:
  1. the `A2-UI` correction passes its own manager review — `MET`, PR #30;
  2. that UI correction merges — `MET`, merge commit `63093f22`;
  3. this Auth correction passes A2-AUTH review and is pushed to the PR #29
     head — `NOT_MET`; and
  4. `A2-UI` rereviews the new head and returns an acceptable disposition —
     `NOT_MET`.
- Status: `OPEN`. It is not closed by the UI half having merged, and it is not
  closed by this Auth correction alone.

## Issues opened by the A2-SECURITY consumer response

### `AUTH-ISSUE-028` — A2-SECURITY returned `REJECTED_WITH_REASON` against head `7abe17a`

- Classification: `CONSUMER_REJECTION`
- Severity: `HIGH`
- Substate: `SEVEN_NORMATIVE_CORRECTIONS_REQUIRED / ALL_SEVEN_APPLIED /
  AUTH_CORRECTION_PENDING_A2_AUTH_REVIEW / A2_SECURITY_REREVIEW_REQUIRED`
- Evidence: consumer `A2-SECURITY`, review task
  `AUTH-002-CONSUMER-REVIEW-A2-SECURITY-001`, reviewed head
  `7abe17af8e212bd2127160338ea6ef409da02101` on pull request #29
  (`OPEN / DRAFT / NOT_MERGED`), disposition `REJECTED_WITH_REASON`, seven
  required normative corrections. Agent 1 accepted the rejection as
  authoritative and authorized the consolidated correction. Recorded as
  `AUTH-DEC-044`; the corrections as `AUTH-DEC-045` through `AUTH-DEC-051`.
- Architecture accepted, not disputed: `SUPABASE_AUTH_WITH_GITHUB_OAUTH`,
  `@supabase/ssr`, `createBrowserClient`, `createServerClient`, one
  provider-owned cookie-backed session, a browser-readable provider-session
  cookie, and required PKCE. The rejection was of the contract text, not of the
  architecture.
- Corrections and their residues:
  1. cookie posture frozen (`AUTH-DEC-045`) — residue: `A2-DEPLOYMENT` runtime
     and configuration confirmation;
  2. CSRF and credential-transport boundary frozen (`AUTH-DEC-046`) — residue:
     `A2-BACKEND` compatibility, including CORS implementation;
  3. `local` sign-out scope and `<= 900`-second production access-token bound
     (`AUTH-DEC-047`) — residue: `A2-BACKEND` and `A2-DEPLOYMENT` confirmation;
  4. public `SIGN_IN_FAILED` boundary (`AUTH-DEC-048`) — no owner residue;
  5. server-side ephemeral correlation with 10-minute and 120-second lifetimes
     (`AUTH-DEC-049`) — residue: `A2-DEPLOYMENT` storage capability and
     topology, tracked in `AUTH-ISSUE-025`;
  6. server-side intended-return state (`AUTH-DEC-050`) — residue: same as 5;
  7. live-provider proof for a preserved session (`AUTH-DEC-051`) — no owner
     residue.
- Impact: `CONTRACT-AUTH-001@1.1.0-draft.1` is not acceptable to `A2-SECURITY`
  as reviewed. `AUTH-DEP-011` is `OPEN / RESPONSE_RECEIVED /
  REJECTED_WITH_REASON / CORRECTION_IN_PROGRESS / NOT_ACCEPTED`. The
  cache-control, XSS/runtime, Security-event and key-custody requirements are
  recorded as implementation and release requirements and are **not** runtime
  evidence; nothing in this repository proves any of them is implemented.
- Owning component: `A2-SECURITY` for policy; `A2-AUTH` for the contract
  semantics applied here; `A2-DEPLOYMENT` and `A2-BACKEND` for the compatibility
  residues.
- Blocking task: `AUTH-002` acceptance; `UI-004`; merge of PR #29.
- Resolution path — none yet met: this Auth correction passes A2-AUTH review and
  is pushed to the PR #29 head; `A2-SECURITY` rereviews the new head and returns
  an acceptable disposition; and the `A2-DEPLOYMENT` and `A2-BACKEND`
  compatibility confirmations are obtained.
- Status: `OPEN`. Applying all seven required corrections does not close it.

### `AUTH-ISSUE-029` — Security implementation and release requirements are unmet

- Classification: `IMPLEMENTATION_REQUIREMENT / NOT_RUNTIME_EVIDENCE`
- Severity: `MEDIUM`
- Evidence: `A2-SECURITY` requires `Cache-Control: private, no-store` on every
  authentication, session-refresh, cookie-setting and callback response, with no
  shared-cache, ISR or CDN `Set-Cookie` serving; strict CSP with no
  `unsafe-eval` and no unrestricted `unsafe-inline`, nonce- or hash-based script
  policy, Trusted Types where supported, no unreviewed third-party scripts on
  authenticated surfaces, dependency and supply-chain scanning, no token
  exposure in the DOM, to analytics or to client logs, and callback and session
  route security testing; a bounded, secret-free, attributable Security-event
  field set with its prohibited-content list; and key-custody handling for
  opaque-handle integrity including `>= 256`-bit server key material where HMAC
  is selected, secret-manager custody, no `NEXT_PUBLIC`, source-control, log or
  browser exposure, and rotation accepting the previous verification key for at
  most 15 minutes while never minting with it.
- Impact: none of these is implemented, and none is claimed to be. There is no
  Auth runtime, no frontend Auth surface, no Security-event pipeline and no
  provisioned provider in this repository. Recording a requirement is not
  evidence of satisfying it.
- Owning component: `A2-AUTH` and `A2-UI` for application-side implementation,
  `A2-DEPLOYMENT` for cache, secret custody and rotation infrastructure, with
  `A2-SECURITY` acceptance.
- Blocking task: `AUTH-002` implementation once separately authorized;
  `AUTH-007`; `AUTH-008` final acceptance.
- Resolution path: implementation under a future authorized task, then
  `A2-SECURITY` verification against runtime evidence. No key was generated, no
  secret manager selected, no runtime configured and no infrastructure
  provisioned by this documentation task.
- Status: `OPEN`.

## Summary

`DB-002` is merged, `CONTRACT-AUTH-001@1.0.0-draft.2` is acknowledged and
merged, and no Database rereview is outstanding. `CONTRACT-AUTH-001` is now
drafted at `1.1.0-draft.1` and is `DRAFT_FOR_CONSUMER_REVIEW /
NOT_IMPLEMENTATION_READY`.

This reconciliation reclassified exactly the issues whose sole cause was
missing `AUTH-DEP-004` design metadata or missing A2-UI ownership:
`AUTH-ISSUE-004` is `RESOLVED_FOR_CONTRACT_AND_DESIGN`, `AUTH-ISSUE-017` is
`RESOLVED_FOR_OWNERSHIP_AND_COORDINATION`, and `AUTH-ISSUE-015` is
`PARTIALLY_RESOLVED` for its human-IdP half only. No runtime provisioning,
implementation, Security, Backend, Workflow or testing issue was resolved.

`AUTH-002` contract and design resolved `AUTH-ISSUE-011` in draft and corrected
the superseded "`apps/web` does not exist" evidence in `AUTH-ISSUE-007` and
`AUTH-ISSUE-017`. It opened `AUTH-ISSUE-020` through `AUTH-ISSUE-024`. It
resolved no runtime, provisioning, Security, Backend or testing issue, and it
closed nothing by acceptance.

The A2-AUTH correction round (`AUTH-DEC-036` through `AUTH-DEC-039`) closed no
issue. It tightened the drafted refresh, callback, cross-context and
return-state semantics and opened `AUTH-ISSUE-025` and `AUTH-ISSUE-026`, both
of which record decisions Auth deliberately did not make on A2-SECURITY's
behalf. `AUTH-ISSUE-024` remains the blocker that prevents either from being
answered, and it remains owned by Agent 1: no Security file was created by this
correction round.

The second A2-AUTH correction round (`AUTH-DEC-040` and `AUTH-DEC-041`) also
closed no issue and opened no new one. It fixed two defects internal to the
draft text rather than surfacing a new external dependency:

- `AUTH-DEC-040` replaced a self-contradictory correlation lifetime — the draft
  required post-success duplicate correlation while also removing the record at
  the successful terminal outcome — with a bounded two-phase lifecycle. This
  broadened `AUTH-ISSUE-025` rather than creating a sibling: the undecided
  mechanism now explicitly includes the record's representation, retention
  duration and cleanup, and the length of its bounded post-completion window.
- `AUTH-DEC-041` separated callback-attempt failure from session-validity
  failure. No new issue was opened for it, because it decides an Auth-owned
  semantic outright and defers nothing to another owner; the residual questions
  are consumer-review questions already carried by `AUTH-DEP-011` and
  `AUTH-DEP-012`, not undecided ownership.

Neither correction relaxed a fail-closed rule, and neither made an existing
session sufficient callback correlation.

The A2-UI consumer response opened `AUTH-ISSUE-027` and closed nothing.
`A2-UI` returned `SPECIFICATION_CONFLICT` against head `7abe17a`, and that
disposition stands for that head. Agent 1 authorized one correction per owner:
the UI-owned supersession of the conflicting `UI-DEC-013` cookie meaning, which
Auth did not perform or author, and the Auth-owned freezing of `/` as both the
default post-sign-in destination and the preserved-session rejected-callback
safe recovery destination, recorded as `AUTH-DEC-043`. `AUTH-DEC-042` records
the response itself.

The UI-owned half is now `CORRECTED_AND_MERGED`: `A2-UI` merged `UI-DEC-026` and
`UI-DEC-027` in PR #30 — implementation commit `30deb920`, merge commit
`63093f22`, current `origin/main` — recorded on the Auth side as
`AUTH-DEC-052`. That merge also resolves `AUTH-ISSUE-023`. The Auth-owned half
is `CORRECTED_IN_WORKTREE / PENDING_A2_AUTH_ACCEPTANCE_AND_PUSH`.
`AUTH-ISSUE-027` remains `OPEN` until this Auth correction is accepted and
pushed and `A2-UI` rereviews the new PR #29 head with an acceptable disposition.
Freezing a route resolved an open contract slot; merging the UI record
correction resolved the UI-owned half; neither is `A2-UI` acceptance of any Auth
head.

The A2-SECURITY consumer response opened `AUTH-ISSUE-028` and `AUTH-ISSUE-029`,
closed nothing, and narrowed `AUTH-ISSUE-025`. `A2-SECURITY` returned
`REJECTED_WITH_REASON` against the same head `7abe17a` with seven required
normative corrections, while explicitly accepting the selected architecture —
`SUPABASE_AUTH_WITH_GITHUB_OAUTH`, `@supabase/ssr`, `createBrowserClient`,
`createServerClient`, one provider-owned cookie-backed session, a
browser-readable provider-session cookie and required PKCE. All seven
corrections are applied and recorded as `AUTH-DEC-045` through `AUTH-DEC-051`,
with the response itself as `AUTH-DEC-044`. Applying every required correction
closes nothing: `AUTH-DEP-011` remains `OPEN` and `NOT_ACCEPTED`, and
`A2-SECURITY` rereview of the corrected PR #29 head is required.

The Security decision on the browser-readable cookie also settles the *policy*
question beneath the A2-UI conflict, which is why that posture is no longer
described anywhere as pending Security. It did not settle the UI-owned record
correction — PR #30 did, on its owner's side — and it does not remove the
`A2-DEPLOYMENT` runtime and configuration
confirmation, the `A2-BACKEND` compatibility confirmation, or any of the
implementation and release requirements now tracked as `AUTH-ISSUE-029`.
`AUTH-ISSUE-024` is likewise not closed: the Security response arrived through
the coordinator, not through a `docs/components/security/` record set, which
still does not exist and remains Agent 1's to create.

What remains open is Auth runtime absence, provider provisioning and every
untested runtime behavior — callback runtime, JWT validation, cookies, CSRF,
PKCE, OAuth state and frontend Auth integration — plus the remaining scoped
external dependencies, the unresolved cookie and Security posture decisions,
the absent A2-SECURITY record set, the absent Auth test suite, and downstream
durable webhook idempotency. No implementation defect is claimed in merged
code: every gap above is either absence, an unresolved dependency, an owner
decision, or a documentation inconsistency.

A drafted contract resolves nothing by itself. `CONTRACT-AUTH-001@1.1.0-draft.1`
is not accepted, is not implementation-ready, and authorizes no implementation.
