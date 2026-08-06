# Auth Dependency Requests

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
- Auth identity persistence: `VERIFIED_COMPLETE` and merged
- Auth runtime implementation: `NOT_STARTED`
- Auth runtime: `NOT_TESTED`
- `CONTRACT-AUTH-001@1.1.0-draft.1`: `DRAFT_FOR_CONSUMER_REVIEW /
  NOT_IMPLEMENTATION_READY`
- New requests opened by this task: `AUTH-DEP-011` through `AUTH-DEP-015`
- `ASSUMED`: `NONE`

## Database consumer review

- Consumer review: `DB-AUTH-CONTRACT-ACK-001`
- Initial A2-DATABASE result: `ACKNOWLEDGED_WITH_CHANGES`
- Requested changes: issuer comparison semantics; access-grant expiration
  timing.
- Auth response: Addressed in `CONTRACT-AUTH-001` version `1.0.0-draft.2`.
- Current approval status: `COMPLETE / ACKNOWLEDGED_AND_MERGED`
- Completion evidence: A2-DATABASE recorded
  `CONTRACT-AUTH-001@1.0.0-draft.2` as `ACKNOWLEDGED_AND_MERGED`
  (`docs/components/database/COMPONENT_STATUS.md:17-19`,
  `DECISION_LOG.md:20`, `TASK_LEDGER.md:10`) and implemented DB-002 against
  it. `DB-002` is `PASS / VERIFIED_COMPLETE / MERGED` via PR #12
  (implementation `5506ab5`, merge `3701520`), closed by PR #13 (`1511f47`).
  No rereview is outstanding.

## `DB-DEP-001` — Incoming Auth context request

- Request ID: `DB-DEP-001`
- Requesting Agent 2: `A2-DATABASE`
- Owning Agent 2: `A2-AUTH`
- Required change and reason: Define canonical identity, installation,
  repository, exact access-scope, actor, lifecycle, and secret-exclusion
  semantics so DB-002 does not invent Auth-owned semantics.
- Contract affected: `CONTRACT-AUTH-001`
- Exact blocking task: `DB-002`
- Backward-compatibility impact: Initial contract; incompatible changes may
  require migrations.
- Urgency: `HIGH`
- Proposed acceptance test: Use the original fixture with two users, two
  installations, two repositories, the five conceptual records, and the exact
  access tuple; verify exact case-sensitive issuer uniqueness, absence of
  issuer normalization, separate expiration and revocation timing, historical
  attribution, and absence of local credential fields.
- Approval status: `COMPLETE / ACCEPTED`
- Completion evidence: `CONTRACT-AUTH-001@1.0.0-draft.2` was acknowledged and
  merged by A2-DATABASE and implemented by DB-002. The proposed acceptance
  test is satisfied by 21 passing tests in
  `tests/database/test_auth_constraints.py`, executed 2026-08-02 under
  `AUTH-001`, covering the two-user / two-installation / two-repository
  fixture, exact case-sensitive issuer uniqueness, absence of issuer
  normalization, distinct expiration and revocation timing, historical
  attribution, and absence of local credential fields.

## `AUTH-DEP-001` — Database consumer acknowledgement

- Request ID: `AUTH-DEP-001`
- Requesting Agent 2: `A2-AUTH`
- Owning Agent 2: `A2-DATABASE`
- Required change and reason: Confirm the Auth contract fully defines the
  conceptual records and guarantees needed by DB-002 while Database retains
  ownership of physical persistence.
- Initial response: `ACKNOWLEDGED_WITH_CHANGES`
- Contract affected: `CONTRACT-AUTH-001` and future `CONTRACT-DB-001`
- Exact blocking task: Final closure of `AUTH-DB002-CONTRACT-001` and readiness
  of `DB-002`
- Backward-compatibility impact: Initial contract; incompatible changes may
  require migrations.
- Urgency: `HIGH`
- Proposed acceptance test: Database confirms the original five conceptual
  records and exact access-tuple fixture, exact case-sensitive issuer
  uniqueness, absence of issuer normalization, separate expiration and
  revocation timing, historical attribution, and absence of local credential
  fields.
- Approval status: `COMPLETE / ACCEPTED`
- Completion evidence: A2-DATABASE acknowledged `1.0.0-draft.2` and merged it;
  the five conceptual records are implemented as `users`, `auth_subjects`,
  `github_installations`, `repositories`, and `repository_access`
  (`apps/api/app/db/models/auth.py`). The initial
  `ACKNOWLEDGED_WITH_CHANGES` response is preserved as history. No Database
  action remains outstanding.

## `AUTH-DEP-002` — Workflow actor compatibility

- Request ID: `AUTH-DEP-002`
- Requesting Agent 2: `A2-AUTH`
- Owning Agent 2: `A2-AGENT-WORKFLOW`
- Required change and reason: Confirm workflow persistence can retain canonical
  actor attribution and a traceable authorized publication trigger without
  representing machine actors as humans.
- Contract affected: `CONTRACT-AUTH-001` and `CONTRACT-WORKFLOW-001`
- Exact blocking task: DB workflow persistence, actor attribution, and later
  Auth integration
- Backward-compatibility impact: Initial contracts; incompatible actor changes
  require coordination.
- Urgency: `HIGH`
- Proposed acceptance test: `HUMAN_USER`, `GITHUB_APP_INSTALLATION`,
  `SYSTEM_SERVICE`, and `UNAUTHENTICATED` round-trip without representing
  machine actors as humans; publication execution retains a traceable
  authorized trigger.
- Approval status: `PARTIALLY_SATISFIED`
- Completion evidence: `CONTRACT-WORKFLOW-001@1.0.0-draft.1` is accepted and
  merged, and `run_requests`/`runs` carry actor attribution
  (`apps/api/app/db/models/workflow.py`). The acceptance test is **not** met:
  `TERMINAL_ACTOR_TYPES = ("SYSTEM", "WORKFLOW", "WORKER", "HUMAN")` at line
  129 has no `GITHUB_APP_INSTALLATION` value, so publication execution has no
  machine actor. Remainder tracked as `AUTH-DEP-008`.

## `AUTH-DEP-003` — Shared registry consumer correction

- Request ID: `AUTH-DEP-003`
- Requesting Agent 2: `A2-AUTH`
- Owning Agent 2: `A2-INTEGRATION` or Agent 1
- Required change and reason: Correct the shared registry because it omits
  A2-DATABASE as a blocking consumer of the Auth contract.
- Contract affected: Shared-contract registry
- Exact blocking task: Authoritative coordination closure; not contract
  drafting
- Backward-compatibility impact: Additive documentation correction.
- Urgency: `MEDIUM`
- Proposed acceptance test: A2-DATABASE is listed or explicitly recorded as a
  blocking `CONTRACT-AUTH-001` consumer.
- Approval status: `PENDING`
- Completion evidence: None.

## `AUTH-DEP-004` — Human sign-in and JWT/IdP deployment metadata

- Request ID: `AUTH-DEP-004`
- Requesting Agent 2: `A2-AUTH`
- Owning Agent 2: `A2-DEPLOYMENT`
- Required change and reason: Provide the approved identity provider or
  approved equivalent; canonical issuer; audience; JWKS URL or equivalent key
  source; authorization endpoint; token endpoint; owned dashboard domain;
  human OAuth callback URL/allowlist; TLS termination; client-ID and
  client-secret variable names; and secret-injection ownership. This is the
  authoritative deployment callback and human IdP metadata boundary. Secret
  values remain excluded.
- Contract affected: `CONTRACT-AUTH-001` and `CONTRACT-DEPLOY-001`
- Exact blocking task: `AUTH-002`, `AUTH-003`, and `AUTH-007`
- Backward-compatibility impact: Runtime configuration unless identifier
  semantics change.
- Urgency: `HIGH`
- Proposed acceptance test: Every listed human IdP/deployment field is
  documented with an explicit owner; callback URLs are exact-match allowlisted;
  TLS termination and secret injection ownership are stated; no secret value
  is present.
- Approval status: `ACCEPTED_WITH_CONSTRAINTS / ACKNOWLEDGED_BY_A2_AUTH /
  MERGED_VIA_PR_20`
- Completion evidence: A2-DEPLOYMENT issued `ACCEPTED_WITH_CONSTRAINTS`;
  A2-AUTH acknowledged it. Durably merged through Deployment pull request #20,
  merge commit `fc549fa1a4c77f4835acefbb4f937c35ad6e8f76`. Records:
  `docs/components/deployment/DECISION_LOG.md` and
  `docs/components/deployment/ENVIRONMENT_VARIABLES.md`, which registers the
  Auth-scoped variable **names** without secret values.
- The original request text above is preserved as historical context. The
  request itself is no longer `PENDING`.

### Accepted human identity architecture

The Deployment-owned design accepted under this request is:

- Provider: `SUPABASE_AUTH_WITH_GITHUB_OAUTH`
- Architecture status: `APPROVED_FOR_AUTH_CONTRACT_AND_DESIGN`
- Canonical issuer: `https://<SUPABASE_PROJECT_REF>.supabase.co/auth/v1`
- Audience: `authenticated`
- JWKS:
  `https://<SUPABASE_PROJECT_REF>.supabase.co/auth/v1/.well-known/jwks.json`
- Dashboard callback: `${DASHBOARD_ORIGIN}/auth/callback`
- Local callback: `http://localhost:3000/auth/callback`
- GitHub-registered Supabase callback:
  `https://<SUPABASE_PROJECT_REF>.supabase.co/auth/v1/callback`
- OAuth termination: Supabase Auth
- FastAPI boundary: FastAPI receives Supabase JWT access tokens only.
- Refresh tokens: must never be forwarded to FastAPI.
- Redirect policy: exact-match allowlist only.
- Issuer comparison: exact and case-sensitive.
- Independent issuer normalization: prohibited.

These are **accepted design values, not proof of configured runtime**. No
Supabase project, GitHub OAuth provider configuration, deployed callback
registration, or injected secret is proven by this repository.
`<SUPABASE_PROJECT_REF>` and `${DASHBOARD_ORIGIN}` remain unresolved
placeholders; no real project reference or hostname is recorded.

Dependency effect: `SATISFIED_FOR_CONTRACT_AND_DESIGN`. This satisfies
`AUTH-002` contract and design only. It authorizes no `AUTH-002` runtime
implementation, and it does not by itself unblock `AUTH-003` or `AUTH-007`,
which retain their sequential and runtime prerequisites.

## `AUTH-DEP-005` — Security lifecycle and event guidance

- Request ID: `AUTH-DEP-005`
- Requesting Agent 2: `A2-AUTH`
- Owning Agent 2: `A2-SECURITY`
- Required change and reason: Define security-event, authorization freshness,
  retention, and redaction guidance needed for Auth hardening and final
  acceptance.
- Contract affected: `CONTRACT-AUTH-001` and `CONTRACT-SEC-001`
- Exact blocking task: `AUTH-007` and `AUTH-008`
- Backward-compatibility impact: May add lifecycle metadata; identity-breaking
  changes require coordination.
- Urgency: `MEDIUM`
- Proposed acceptance test: Auth security events contain no secrets or tokens
  and define approved authorization freshness, retention, and redaction rules.
- Approval status: `PENDING`
- Completion evidence: None.

## `AUTH-DEP-006` — Backend request surface for authenticated Auth controls

- Request ID: `AUTH-DEP-006`
- Requesting Agent 2: `A2-AUTH`
- Owning Agent 2: `A2-BACKEND`
- Required change and reason: Publish the FastAPI route surface, the
  request-dependency mechanism that carries an authenticated principal, the
  error-envelope shape for unauthenticated and unauthorized responses, and a
  webhook route contract that exposes the **raw** request body before JSON
  parsing. Also confirm which component owns adding the JWT/JWKS verification
  dependency to `apps/api/pyproject.toml`. Evidence: `apps/api/app/main.py` is
  a three-line bare `FastAPI()` with no route, dependency, or middleware, and
  the manifest lists no JWT, JWKS, crypto, or outbound HTTP client.
- Contract affected: `CONTRACT-AUTH-001` and a future `CONTRACT-BACKEND-001`
- Exact blocking task: `AUTH-003`, `AUTH-005`, `AUTH-006`
- Backward-compatibility impact: Additive. No existing route exists to break.
- Urgency: `HIGH`
- Proposed acceptance test: A documented route declares a request dependency
  that rejects an absent or invalid credential before handler code runs; a
  documented webhook route exposes the exact raw body bytes; the error
  envelope for a rejected request contains no token, header, or secret value.
- Approval status: `PENDING`
- Completion evidence: None.

## `AUTH-DEP-007` — Installation reference for exact-tuple authorization

- Request ID: `AUTH-DEP-007`
- Requesting Agent 2: `A2-AUTH`
- Owning Agent 2: `A2-DATABASE`
- Required change and reason: `CONTRACT-AUTH-001` scopes repository
  authorization by the exact `user + installation + repository` tuple, but
  `run_requests` carries only `repository_id` and `requested_by_subject`
  (`apps/api/app/db/models/workflow.py:200-207`) and no installation
  reference. `AUTH-006` therefore cannot authorize a run request against the
  contract tuple from the request row alone. Add an installation reference, or
  document an equivalent representation that preserves the same Auth meaning.
  This is an absent field, not a defect in merged DB-002: DB-002 implemented
  exactly what the accepted contracts specified.
- Contract affected: `CONTRACT-AUTH-001` and `CONTRACT-WORKFLOW-001`
- Exact blocking task: `AUTH-006`
- Backward-compatibility impact: Additive nullable column plus a migration;
  no existing constraint changes. Making it non-nullable later would be
  breaking and requires coordination.
- Urgency: `MEDIUM`
- Proposed acceptance test: Given a persisted run request for a human actor,
  the exact `user + installation + repository` tuple is recoverable from
  persistence alone and matches an `ACTIVE` `repository_access` row, without
  guessing an installation.
- Approval status: `PENDING`
- Completion evidence: None.

## `AUTH-DEP-008` — Machine actor for publication execution

- Request ID: `AUTH-DEP-008`
- Requesting Agent 2: `A2-AUTH`
- Owning Agent 2: `A2-AGENT-WORKFLOW`, with `A2-DATABASE` for persistence
- Required change and reason: `CONTRACT-AUTH-001` requires
  `PUBLICATION_EXECUTE` to use the GitHub App installation actor with
  attribution traceable to an authorized request, event, or human decision.
  No such representation exists:
  `TERMINAL_ACTOR_TYPES = ("SYSTEM", "WORKFLOW", "WORKER", "HUMAN")`
  (`apps/api/app/db/models/workflow.py:129`) has no
  `GITHUB_APP_INSTALLATION` value, and no publication-actor record exists.
  Define how a publication side effect records its machine actor and its
  authorized trigger.
- Contract affected: `CONTRACT-AUTH-001` and `CONTRACT-WORKFLOW-001`
- Exact blocking task: `AUTH-006`, `AUTH-008`
- Integration impact: Also required for Workflow/Database publication
  integration. It does not block `AUTH-004` GitHub App JWT creation,
  installation-token exchange, caching, expiry handling, or permission
  introspection.
- Backward-compatibility impact: Additive if a new actor value or record is
  introduced; changing the meaning of an existing terminal actor value would
  be breaking.
- Urgency: `MEDIUM`
- Proposed acceptance test: A recorded publication side effect names a GitHub
  App installation as its actor, is never representable as a human actor, and
  resolves to an authorized request, event, or human decision. No merge or
  approval semantics are implied.
- Approval status: `PENDING`
- Completion evidence: None.

## `AUTH-DEP-009` — GitHub App and webhook runtime configuration

- Request ID: `AUTH-DEP-009`
- Requesting Agent 2: `A2-AUTH`
- Owning Agent 2: `A2-DEPLOYMENT`
- Required change and reason: Register the GitHub App ID variable name, GitHub
  App private-key variable name, webhook-secret variable name, webhook
  endpoint/public URL, GitHub App setup URL where applicable, installation
  callback/setup metadata where applicable, and the least-privilege GitHub App
  permission set. Explicitly exclude merge, branch-protection bypass, and
  production-code write scopes. This request excludes the human OAuth
  callback, dashboard domain, TLS, and IdP metadata owned by `AUTH-DEP-004`.
- Contract affected: `CONTRACT-AUTH-001` and `CONTRACT-DEPLOY-001`
- Exact blocking task: `AUTH-004`, `AUTH-005`
- Backward-compatibility impact: Additive configuration registry entries.
- Urgency: `HIGH`
- Proposed acceptance test: The App ID, private-key, and webhook-secret
  variable **names**; webhook endpoint/public URL; applicable setup and
  installation callback metadata; and GitHub App permission set are documented
  without secret values. The permission set excludes merge,
  branch-protection-bypass, and production-code-write scopes, and no human IdP
  callback/domain requirement is duplicated.
- Approval status: `PENDING`
- Completion evidence: None.

## `AUTH-DEP-010` — Dashboard frontend ownership

- Request ID: `AUTH-DEP-010`
- Requesting Agent 2: `A2-AUTH`
- Owning Agent 2: `A2-UI`
- Classification: `PROTECTED_FILE_AND_IMPLEMENTATION_OWNERSHIP_CONSTRAINT`
- Required change and reason: `apps/web` does not exist
  (`find . -type d -name web` returns nothing; `ls apps/` returns exactly
  `api`), so trust boundaries B1–B3 — browser to frontend, frontend to
  identity provider, and callback back to the application — have no
  implementing component. Confirm frontend ownership, whether a first-party
  dashboard will exist, protected UI paths, and which side terminates the
  OAuth callback. A3-AUTH and A3-UI must not modify UI-owned paths or perform
  frontend Auth integration tests until this is accepted. This constraint does
  not block `AUTH-002` contract/design work after `AUTH-DEP-004` is accepted.
- Contract affected: `CONTRACT-AUTH-001` and a future UI contract
- Exact blocking task: `AUTH-002` frontend implementation and frontend Auth
  integration tests; not `AUTH-002` contract/design readiness
- Backward-compatibility impact: None yet; nothing is implemented.
- Urgency: `HIGH`
- Proposed acceptance test: A named component owns the browser session and the
  callback endpoint, and the cookie or token custody model is stated
  explicitly.
- Approval status: `ACCEPTED_WITH_CONSTRAINTS / ACKNOWLEDGED_BY_A2_AUTH /
  UI_OWNERSHIP_ESTABLISHED_VIA_PR_19`
- Completion evidence: A2-UI issued `ACCEPTED_WITH_CONSTRAINTS`; A2-AUTH
  acknowledged it. UI ownership was established through UI pull request #19.
  Records: `docs/specifications/A2_UI_MANAGER.md` and the UI-owned durable
  records under `docs/components/ui/`.
- The original request text above is preserved as historical context. The
  request itself is no longer `PENDING`.

### Accepted ownership boundary

A2-UI owns: future Dashboard frontend implementation; future `apps/web/**`
implementation after separate authorization; the user-facing `/auth/callback`
route; callback loading, error and redirect UX; UI accessibility; user-facing
Auth states; and frontend consumption of Auth semantics.

A2-AUTH owns: callback semantics; session semantics; identity resolution;
token lifetime and refresh semantics; token custody semantics; PKCE semantics;
OAuth-state semantics; and Auth security acceptance.

A2-DEPLOYMENT owns: provider provisioning; deployed callback registration;
domains; TLS; secret injection; and environment-variable registration.

A2-SECURITY with A2-AUTH owns final cookie, CSRF and OAuth-state security
acceptance.

Preserved custody and enforcement constraints:

- no access or refresh token in `localStorage`;
- no access or refresh token in `sessionStorage`;
- no duplicate custom token store;
- refresh tokens are never forwarded to FastAPI;
- access tokens are sent to FastAPI through `Authorization: Bearer`;
- UI route protection is defense-in-depth only;
- FastAPI authorization remains authoritative;
- A3-AUTH may not modify UI-owned paths without A2-UI coordination.

Dependency effect: `SATISFIED_FOR_OWNERSHIP_AND_COORDINATION`. Ownership and
coordination are resolved. `AUTH-002` frontend implementation remains
`NOT_AUTHORIZED`, and frontend Auth integration testing remains untested and
unauthorized.

## `AUTH-DEP-011` — Session, cookie and CSRF security acceptance

- Request ID: `AUTH-DEP-011`
- Requesting Agent 2: `A2-AUTH`
- Owning Agent 2: `A2-SECURITY`, jointly with `A2-AUTH`
- Contract affected: `CONTRACT-AUTH-001@1.1.0-draft.1` and a future
  `CONTRACT-SEC-001`
- Exact blocking task: `AUTH-002` acceptance and implementation, `UI-004`,
  `AUTH-007`
- Backward-compatibility impact: A different cookie or storage posture would be
  a breaking change under the `1.1.0-draft.1` versioning rules, because it
  would alter the prohibited-storage list.
- Urgency: `HIGH`
- Blocking-record note: no `docs/components/security/` record set exists, so
  this request has an owner but no place to be answered. See `AUTH-ISSUE-024`.

Exact conflict and evidence. Current primary Supabase documentation states that
`HttpOnly` cookies are "not necessary" for its session model and that "the
browser-based side of your application needs access to the refresh token to
properly maintain a browser session anyway". The official `@supabase/ssr`
browser client reads and writes the session cookie from browser code.
Consequently an `HttpOnly` session cookie is incompatible with the accepted
`SUPABASE_AUTH_WITH_GITHUB_OAUTH` architecture.

Affected requirement: browser custody of the refresh token. No accepted
constraint is violated — the binding constraints prohibit `localStorage`,
`sessionStorage`, duplicate stores and refresh-token forwarding to FastAPI, and
all four are satisfied — but the browser-readable refresh token is a posture
decision that must be made explicitly rather than inherited from a default.

Available options:

1. Accept the official cookie-backed browser-readable session with `Secure` and
   a decided `SameSite`. Security impact: refresh token is reachable by any
   successful XSS. Implementation impact: none beyond the contract as drafted.
2. Introduce a server-only custody layer that keeps the session behind
   `HttpOnly` cookies and proxies every provider interaction. Security impact:
   reduces XSS token theft. Implementation impact: departs from the official
   integration, adds an Auth-owned server surface, and requires re-deciding the
   accepted architecture with A2-DEPLOYMENT.
3. Reduce exposure without changing custody: shorter access-token lifetime,
   stricter `SameSite`, and monitoring. Security impact: partial.
   Implementation impact: Deployment configuration plus Backend expectations.

Additional exact conflicts raised by the A2-AUTH correction round
(`AUTH-DEC-036` through `AUTH-DEC-039`):

- **Callback-completion correlation.** The contract now requires a duplicate
  callback invocation to correlate to the same sign-in attempt, callback flow
  and completed outcome before a prior result may be reused. An existing
  session is explicitly not correlation. The record's storage, lifetime and
  required strength are undecided.
- **Callback-correlation lifecycle** (second correction round, `AUTH-DEC-040`).
  The correlation record is now `PENDING_ATTEMPT_CORRELATION` from `beginSignIn`
  until the flow completes, then `COMPLETED_CALLBACK_CORRELATION` on successful
  first callback processing. The completed record must **survive** successful
  completion for a bounded post-completion correlation window, so that an
  immediate duplicate invocation and a post-success page reload can correlate
  without another code exchange and without another session; it must not remain
  valid indefinitely; and a failed, abandoned, malformed, expired or terminally
  rejected flow must never produce one. The window's length, and the record's
  representation, retention and cleanup, are undecided and are deliberately not
  invented by Auth.
- **Invalid callback versus existing session** (second correction round,
  `AUTH-DEC-041`). `INVALID_CALLBACK` now classifies the callback attempt only.
  It always creates no session, performs no exchange, performs no
  callback-directed navigation, clears callback parameters, removes the rejected
  attempt's return state and emits the Security event; but it moves the session
  to `TERMINAL_SESSION_ERROR` only where no independently established,
  known-valid session pre-existed the callback, or where a pre-existing
  session's validity is unknown. A known-valid pre-existing session is preserved
  as `AUTHENTICATED` while the callback attempt fails, and is still never
  accepted as correlation or as proof of callback success.
- **Intended-return state binding.** The Dashboard return state is now
  Auth-owned, attempt-bound, expiry-limited, single-use and removed on success
  and failure alike, and is never accepted on syntactic safety alone. Its
  storage and integrity mechanism is undecided, and reuse of provider OAuth
  `state` as a return-path container is prohibited absent explicit official
  provider support plus Security acceptance.
- **Cross-context refresh.** The contract no longer claims global single-flight
  refresh. Races across tabs, parallel server requests and runtime instances
  are possible and must fail closed with at most one bounded retry after a
  newer valid session is observed. The observable behavior is `NOT_TESTED`.
- **Fail-closed refresh modes.** `REFRESH_PENDING` now distinguishes a
  proven-credential refresh from an unproven-credential refresh, with protected
  content and protected requests prohibited in the latter.

Required owner decisions:

1. Approve or reject browser-readable cookie custody as drafted.
2. Fix the `SameSite` value. Auth proposes `Lax`, matching the documented
   provider recommendation, because the callback arrives by a top-level
   cross-site redirect. Confirm that `Strict` is not required.
3. Confirm `Secure` is mandatory on every non-local environment.
4. State the CSRF posture for the Dashboard, given that the API credential is a
   `Bearer` header rather than a cookie, and that cookies are used only for
   session custody.
5. Fix the provider sign-out scope. Auth proposes current-session scope;
   the official default signs the user out of every device.
6. Decide the acceptable residual window during which an already-issued access
   token remains valid at FastAPI after sign-out, and whether a shorter
   access-token lifetime or a revocation mechanism is required. See
   `AUTH-ISSUE-022`.
7. Approve or amend the twenty-one Security requirements in the contract.
8. Define the Security-event schema, severity, retention and redaction rules
   for the classifications the contract marks as requiring a Security log.
   This overlaps `AUTH-DEP-005`.
9. Confirm the cross-tab and session-fixation expectations, including that
   `onAuthStateChange` and `BroadcastChannel` events are treated as
   synchronization signals only and never as proof of serialization.
10. Confirm that the four sign-in failure classes must remain
    indistinguishable to the user, creating no failure oracle.
11. Decide the required strength, storage and lifetime of the
    callback-completion correlation record: what must Auth verify before a
    duplicate callback invocation may resolve to a previously completed
    outcome, given that an existing session is explicitly not sufficient? Also
    confirm that an uncorrelated invocation must return `INVALID_CALLBACK`,
    clear callback parameters and emit a Security event.
12. Decide the storage and integrity mechanism for the Auth-owned
    intended-return state, which must be attempt-bound, expiry-limited,
    single-use, integrity-protected or held in Auth-controlled same-origin
    state, and removed after success and failure alike. Auth has deliberately
    not invented this mechanism. Confirm also that provider OAuth `state` must
    not be reused as an application return-path container unless current
    official provider documentation explicitly supports it.
13. Accept or amend the cross-context refresh position: single-flight is
    guaranteed only within one adapter instance or browsing context; races
    across tabs, parallel server requests and runtime instances fail closed,
    permit at most one bounded retry after a newer valid session is observed,
    and never create an automatic refresh loop. State any monitoring or
    detection expectation for such races.
14. Accept or amend the fail-closed `REFRESH_PENDING` modes: whether a
    proven-credential refresh may keep existing protected content visible while
    deferring new protected requests, and confirmation that an
    unproven-credential refresh must remove protected content, disable
    protected interactions and prohibit protected requests outright.
15. Decide the bounded post-completion correlation window for a
    `COMPLETED_CALLBACK_CORRELATION` record: how long may a completed callback
    outcome remain reusable by a correlated duplicate invocation or a
    post-success reload, and by what cleanup does it stop being reusable? Auth
    requires only that the record survive successful completion long enough for
    that correlation to be possible and that it never remain valid
    indefinitely; it states no duration. Also confirm the record's required
    representation and integrity, that it carries no authorization code, token
    or PKCE verifier, and that no failed, abandoned, malformed, expired or
    terminally rejected flow may produce reusable successful-callback
    correlation evidence.
16. Accept or amend the separation of callback-attempt failure from
    session-validity failure: that `INVALID_CALLBACK` classifies the callback
    attempt only; that a session independently established before the rejected
    callback and still known-valid is preserved as `AUTHENTICATED` rather than
    invalidated; that a pre-existing session of unknown or unprovable validity
    fails closed to `TERMINAL_SESSION_ERROR`; that a malformed or replayed
    callback never revokes or signs out a separately valid provider session; and
    that a preserved session is still never correlation and never proof of
    callback success. State what Auth must treat as sufficient proof that a
    pre-existing session is "independently established and known-valid" at the
    moment a callback is rejected, and any Security-event or monitoring
    expectation for a rejected callback that leaves a session standing.

- Proposed acceptance test: every decision above is recorded with an explicit
  owner and value; no accepted storage prohibition is weakened; no fail-closed
  rule is relaxed; no cross-context serialization is asserted without evidence;
  no correlation evidence is made permanent or made unusable at the moment of
  successful completion; no rejected callback is permitted to invalidate an
  independently valid session, and no existing session is permitted to prove
  callback success; no secret, token or project reference appears in the
  response.
- Approval status: `PENDING`
- Completion evidence: None.

## `AUTH-DEP-012` — A2-UI consumer review of the session contract

- Request ID: `AUTH-DEP-012`
- Requesting Agent 2: `A2-AUTH`
- Owning Agent 2: `A2-UI`
- Required change and reason: `CONTRACT-AUTH-001@1.1.0-draft.1` freezes the
  callback ownership split, the nine-state session model, the Auth-owned UI
  adapter interface and the eleven-code error vocabulary that a future,
  separately authorized `UI-004` will consume. A2-UI must confirm these are
  implementable and complete, so that `UI-004` never invents Auth semantics.
- Contract affected: `CONTRACT-AUTH-001@1.1.0-draft.1` and a future UI contract
- Exact blocking task: `AUTH-002` acceptance; `UI-004`
- Backward-compatibility impact: Additive for UI. Nothing is implemented, so
  nothing breaks.
- Urgency: `HIGH`

Review questions:

1. Is the `/auth/callback` ownership split correct and sufficient, with A2-UI
   owning route existence, loading, success and error UX, accessibility,
   presentation and final navigation, and A2-AUTH owning every semantic?
2. Is the nine-state session model sufficient to render every UI surface, and
   are the permitted and prohibited behaviors per state implementable?
3. Is the `processCallback` result shape sufficient — a session snapshot plus
   an already-validated navigation destination — without UI seeing raw
   provider parameters?
4. Is `getAccessTokenForApiRequest` an acceptable API transport boundary, given
   that the token must not be cached and is used for exactly one request?
5. Is the eleven-code error vocabulary sufficient for UX, and is the
   requirement that four sign-in failures present identically acceptable?
6. Is the relative-path-only return-path rule workable for the intended
   navigation flows, and what concrete default post-sign-in destination does
   A2-UI propose?
7. Are the loading and failure state requirements — never authenticated,
   protected content removed rather than overlaid — implementable in the
   current Next.js App Router shell?
8. Which accessibility responsibilities does A2-UI accept for callback
   progress announcement and error presentation?
9. Does A2-UI confirm that UI route protection is defense-in-depth only and
   carries no frontend authorization authority?
10. Does A2-UI confirm the prohibited-storage list, including the prohibition
    on `createClient` from `@supabase/supabase-js` in browser code and the
    requirement to use `createBrowserClient` from `@supabase/ssr`?
11. Separate record correction: `docs/components/ui/COMPONENT_STATUS.md` and
    `docs/components/ui/TASK_LEDGER.md` still record `apps/web` as `ABSENT`
    and `UI-002`/`UI-003` as `NOT_AUTHORIZED`, which merged PR #26, PR #27 and
    PR #28 contradict. These are UI-owned files; A3-AUTH did not modify them.
    See `AUTH-ISSUE-023`.
12. Does A2-UI accept that the intended return path it supplies to
    `beginSignIn` is a **candidate only**? Auth creates, binds, expires and
    consumes the return state; UI never creates or persists one, never reads
    provider OAuth `state`, and must accept a silent fallback to the default
    post-sign-in destination whenever the return state is missing, expired,
    tampered, replayed or unbound — including when the path itself looks
    perfectly safe.
13. Can A2-UI render the two `REFRESH_PENDING` modes distinctly? Mode
    `PROVEN_CREDENTIAL` may keep existing protected content visible while new
    protected requests wait; mode `UNPROVEN_CREDENTIAL` must remove or hide
    protected content, disable protected interactions, and show a neutral
    pending affordance only. The two must never render identically.
14. Does A2-UI accept that a reload of the callback route is not a new sign-in,
    that a rendered callback page plus an existing session is never proof that
    a callback completed, and that an uncorrelated callback invocation presents
    the same generic sign-in failure as the other three indistinguishable
    classes?
15. Does A2-UI accept that a post-success reload of the callback route
    correlates to the completed outcome only while the completed correlation
    record is inside its bounded post-completion window, and that after that
    window the same reload presents the generic sign-in failure instead — with
    no re-exchange, no new session, and no callback-directed navigation? The
    window's length is an A2-SECURITY decision under `AUTH-DEP-011`, so the UI
    must not assume a duration or render a countdown.
16. Can A2-UI present a **safe callback-error outcome or safe route recovery**
    for the case where a callback attempt is rejected while a session
    independently established before that callback remains known-valid? In that
    case the session stays `AUTHENTICATED` and is not signed out, but the
    callback reports no success and no callback-directed destination is used.
    What does A2-UI propose the user sees, given that the failure detail must
    stay generic and that a preserved session must never be presented as
    "sign-in succeeded"? Which safe destination does route recovery use, given
    that it must not be the rejected callback's intended-return destination?

- Proposed acceptance test: A2-UI confirms it can implement `UI-004` against
  this contract without defining any Auth semantic of its own, or names the
  exact gaps.
- Approval status: `PENDING`
- Completion evidence: None.

## `AUTH-DEP-013` — A2-DEPLOYMENT confirmation of callback and runtime configuration

- Request ID: `AUTH-DEP-013`
- Requesting Agent 2: `A2-AUTH`
- Owning Agent 2: `A2-DEPLOYMENT`
- Required change and reason: `CONTRACT-AUTH-001@1.1.0-draft.1` depends on the
  callback templates, origin ownership, exact-match allowlists and variable
  names accepted under `AUTH-DEP-004`. The new session design adds
  client/server runtime and cookie-domain implications that A2-DEPLOYMENT must
  confirm.
- Contract affected: `CONTRACT-AUTH-001@1.1.0-draft.1` and `CONTRACT-DEPLOY-001`
- Exact blocking task: `AUTH-002` implementation, `UI-004` verification,
  `AUTH-007`
- Backward-compatibility impact: Configuration only, unless a callback or
  origin changes, which would require Auth contract review.
- Urgency: `HIGH`

Review questions:

1. Are `${DASHBOARD_ORIGIN}/auth/callback` and
   `http://localhost:3000/auth/callback` still the complete approved callback
   set, and will both be registered exact-match with no wildcard?
2. Does A2-DEPLOYMENT confirm sole ownership and assignment of
   `DASHBOARD_ORIGIN`, and that Auth and UI never derive it from a request?
3. Does A2-DEPLOYMENT confirm TLS ownership, and that `Secure` cookies are
   guaranteed in every non-local environment?
4. Are the registered variable names sufficient for the official
   `@supabase/ssr` integration, specifically
   `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` for
   browser configuration, with `SUPABASE_GITHUB_CLIENT_ID` and
   `SUPABASE_GITHUB_CLIENT_SECRET` remaining non-public?
5. Does the deployment topology support both a browser runtime and a server
   runtime for the same application, as the official integration requires,
   including a proxy or middleware layer able to write refreshed session
   cookies?
6. What is the cookie domain and path posture for the Dashboard origin, and are
   there subdomain implications for the session cookie?
7. Does A2-DEPLOYMENT confirm the provider-configuration boundary — that
   A2-AUTH and A2-UI never configure the Supabase project or the GitHub OAuth
   application?
8. Does A2-DEPLOYMENT confirm secret-injection ownership, and that no secret
   ever reaches frontend code, a `NEXT_PUBLIC` variable, or a tracked file?
9. What differs between production and local configuration that Auth or UI must
   branch on, and who owns that branch?
10. Does A2-DEPLOYMENT confirm that the Dashboard callback is not the
    GitHub-registered OAuth callback, and that
    `https://<SUPABASE_PROJECT_REF>.supabase.co/auth/v1/callback` remains the
    GitHub-registered one?

- Proposed acceptance test: every question is answered with an explicit owner;
  the callback set remains exact-match; no secret value, real project
  reference, or real hostname appears in the response.
- Approval status: `PENDING`
- Completion evidence: None.

## `AUTH-DEP-014` — A2-BACKEND confirmation of the bearer and denial boundary

- Request ID: `AUTH-DEP-014`
- Requesting Agent 2: `A2-AUTH`
- Owning Agent 2: `A2-BACKEND`, with `A2-SECURITY` for disclosure
- Required change and reason: the session contract's refresh and failure
  behavior depends on what a FastAPI `401` means and on the error envelope the
  frontend must interpret. `CONTRACT-API-001@0.1.0-draft.1` proposes the
  transport but leaves the authenticated context, the `403`-versus-concealed-`404`
  policy and CORS unresolved. This request does not duplicate `AUTH-DEP-006`,
  which covers the route surface and raw-body webhook contract; it covers the
  frontend-facing consequences only.
- Contract affected: `CONTRACT-AUTH-001@1.1.0-draft.1` and
  `CONTRACT-API-001`
- Exact blocking task: `AUTH-002` implementation, `AUTH-003`, `UI-005`
- Backward-compatibility impact: Additive. No protected route exists yet.
- Urgency: `HIGH`

Review questions:

1. Does A2-BACKEND confirm that a protected route accepts an access token only
   through `Authorization: Bearer`, and that cookies, query parameters and
   bodies are never alternate credentials?
2. Does A2-BACKEND confirm that a refresh token is never accepted, and that
   receiving one is itself a rejectable condition?
3. Under exactly which conditions is `401` returned, and does a `401` ever
   distinguish an expired token from an otherwise invalid one? The frontend
   refresh policy depends on this, and the contract currently assumes it does
   not.
4. Is the `CONTRACT-API-001` error envelope stable enough for the frontend to
   classify failures without parsing free text?
5. What token-expiry behavior should the frontend expect — clock skew
   tolerance, and whether the Backend ever accepts a slightly expired token?
6. Does A2-BACKEND accept the frontend retry constraint of at most one refresh
   and one retry per failed protected request, with no unbounded loop?
7. What is the resolution of the `403` versus concealed-`404` policy, and what
   must the frontend render for each?
8. How should the frontend behave for a suspended or deprovisioned canonical
   user, or a revoked external subject, where the provider session is still
   valid but FastAPI denies? Fixtures 18 and 19 assume terminal failure without
   an automatic reauthentication loop.
9. Does A2-BACKEND confirm that the authenticated context is an internal
   Auth-to-Backend handoff and never a client-supplied model?
10. What CORS posture will the API expose to the Dashboard origin, and who
    owns it?

- Proposed acceptance test: the frontend can classify every protected-request
  failure into the contract's states from the documented status and envelope
  alone, without guessing a disclosure rule.
- Approval status: `PENDING`
- Completion evidence: None.

## `AUTH-DEP-015` — A2-INTEGRATION cross-contract consistency review

- Request ID: `AUTH-DEP-015`
- Requesting Agent 2: `A2-AUTH`
- Owning Agent 2: `A2-INTEGRATION`
- Required change and reason: `CONTRACT-AUTH-001@1.1.0-draft.1` now touches UI,
  Security, Deployment and Backend boundaries simultaneously. A2-INTEGRATION
  must confirm cross-contract consistency and gate implementation readiness.
- Contract affected: `CONTRACT-AUTH-001@1.1.0-draft.1`, `CONTRACT-API-001`,
  `CONTRACT-DEPLOY-001`, a future UI contract and a future `CONTRACT-SEC-001`
- Exact blocking task: `AUTH-002` implementation readiness
- Backward-compatibility impact: Additive minor; no consumer breaks.
- Urgency: `MEDIUM`

Review questions:

1. Is `CONTRACT-AUTH-001@1.1.0-draft.1` consistent with
   `CONTRACT-API-001@0.1.0-draft.1` on bearer transport, refresh-token
   exclusion and the error envelope?
2. Is it consistent with the merged Deployment decisions `DEPLOY-DEC-001`
   through `DEPLOY-DEC-009`?
3. Is the required `@supabase/ssr` integration compatible with every other
   accepted contract, and does any other contract assume a different session
   model?
4. Does A2-INTEGRATION agree that implementation readiness is gated on all four
   consumer reviews plus an Agent 1 cross-component semantic decision, and that
   CI passing is not a merge criterion for a contract PR?
5. Are there unresolved consumer conflicts between the Auth session model and
   the UI records that still describe `apps/web` as absent?
6. Is the `1.0.0-draft.2` to `1.1.0-draft.1` classification correct as an
   additive compatible minor?
7. What are the rollback and mixed-version implications if a consumer
   implements against `1.1.0-draft.1` and it later changes?
8. Is the ownership boundary complete, or does any surface in the session
   design lack a named owner?
9. Does the shared registry need updating to list the five required consumers
   for this version? This overlaps the still-pending `AUTH-DEP-003`.
10. Does any other accepted or drafted contract assume that session refresh is
    serialized across browser tabs, parallel server requests, or separate
    runtime instances? `CONTRACT-AUTH-001@1.1.0-draft.1` guarantees
    single-flight refresh only within one Auth adapter instance or browsing
    context, and explicitly declines to promise more.
11. For a deployment that runs both a browser runtime and a server runtime
    against the same cookie-backed session, does A2-INTEGRATION accept the
    documented cross-context race outcomes — stale cookie, temporarily null
    session, or one success plus one rejection — with fail-closed handling, at
    most one bounded retry after a newer valid session is observed, and no
    automatic refresh loop? Name any component that would break under those
    outcomes.
12. Is any cross-component behavior dependent on the Auth-owned intended-return
    state or the callback-completion correlation record, both of whose exact
    mechanisms remain `PENDING_A2_SECURITY_ACCEPTANCE`?

- Proposed acceptance test: A2-INTEGRATION records a cross-contract consistency
  result and an explicit implementation-readiness gate, naming every unresolved
  conflict.
- Approval status: `PENDING`
- Completion evidence: None.

## Summary

`DB-DEP-001` and `AUTH-DEP-001` are `COMPLETE / ACCEPTED`: DB-002 is merged and
`CONTRACT-AUTH-001@1.0.0-draft.2` is `ACKNOWLEDGED_AND_MERGED`. No Database
rereview is outstanding.

`AUTH-DEP-004` is `ACCEPTED_WITH_CONSTRAINTS / ACKNOWLEDGED_BY_A2_AUTH /
MERGED_VIA_PR_20` and `AUTH-DEP-010` is `ACCEPTED_WITH_CONSTRAINTS /
ACKNOWLEDGED_BY_A2_AUTH / UI_OWNERSHIP_ESTABLISHED_VIA_PR_19`. Together they
satisfy `AUTH-002` contract and design only.

Still `PENDING`: `AUTH-DEP-003` (registry correction), `AUTH-DEP-005`
(Security guidance), `AUTH-DEP-006` (Backend request surface), `AUTH-DEP-007`
(installation reference), `AUTH-DEP-008` (machine publication actor), and
`AUTH-DEP-009` (GitHub App/webhook runtime configuration). `AUTH-DEP-002` is
`PARTIALLY_SATISFIED`, with its remainder tracked as `AUTH-DEP-008`.

Opened by `AUTH-002` contract and design, all `PENDING`: `AUTH-DEP-011`
(Security session, cookie and CSRF acceptance), `AUTH-DEP-012` (A2-UI consumer
review), `AUTH-DEP-013` (A2-DEPLOYMENT callback and runtime confirmation),
`AUTH-DEP-014` (A2-BACKEND bearer and denial boundary), and `AUTH-DEP-015`
(A2-INTEGRATION cross-contract consistency).

No consumer has responded to any of the five. **Silence is not acceptance.**
`CONTRACT-AUTH-001@1.1.0-draft.1` remains `DRAFT_FOR_CONSUMER_REVIEW /
NOT_IMPLEMENTATION_READY` until each named owner returns an explicit decision
and material conflicts are reconciled.

The A2-AUTH correction round `AUTH-DEC-036` through `AUTH-DEC-039` widened three
of the five packets rather than resolving anything: `AUTH-DEP-011` carried
fourteen required Security decisions, `AUTH-DEP-012` fourteen A2-UI review
questions, and `AUTH-DEP-015` twelve A2-INTEGRATION questions. The
intended-return state mechanism and the callback-completion correlation
mechanism are recorded as `PENDING_A2_SECURITY_ACCEPTANCE` and are deliberately
not invented by Auth. `AUTH-DEP-013` and `AUTH-DEP-014` are unchanged.

The second correction round `AUTH-DEC-040` and `AUTH-DEC-041` widened two of the
packets and resolved nothing: `AUTH-DEP-011` now carries sixteen required
Security decisions, adding the bounded post-completion correlation window with
its representation, retention and cleanup, and the acceptance of
callback-attempt/session-validity separation; `AUTH-DEP-012` now carries sixteen
A2-UI review questions, adding the post-window reload presentation and the safe
callback-error or route-recovery surface for a rejected callback that leaves a
known-valid session standing. No duration and no Security mechanism is invented
by Auth in either. `AUTH-DEP-013`, `AUTH-DEP-014` and `AUTH-DEP-015` are
unchanged by this round.

`AUTH-DEP-011` has an owner but no durable record set to be answered in,
because no `docs/components/security/` directory exists. See `AUTH-ISSUE-024`.
Creating that record set is Agent 1's task; A3-AUTH created no Security file and
must not.

No dependency request authorizes A3-AUTH to modify another component's files,
and none authorizes Auth code, tests, or configuration.
