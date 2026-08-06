# Auth Open Issues

- Date: 2026-08-06
- Current task:
  `AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001-A3-C2`
- Prior correction task:
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
