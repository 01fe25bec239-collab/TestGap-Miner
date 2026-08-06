# Auth Decision Log

- Date: 2026-08-06
- Current task:
  `AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001-A3-C2`
- Prior correction task:
  `AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001-A3-C1`
- Originating task: `AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001-A3`
- Parent task: `AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001`
- Prompt type: `VERSIONED_AUTH_CONTRACT_AND_DESIGN / A3_DOCUMENTATION_EXECUTION_AND_VALIDATION`
- Scope: `AUTH_CONTRACT_AND_DESIGN_DOCUMENTATION_ONLY`
- Evidence baseline: `006cc885161ff49be582a9fa08f353a70c31c7b1`
- Prior evidence baseline: `fc549fa1a4c77f4835acefbb4f937c35ad6e8f76`
- Prior contract-task baseline: `739a331c9942ed64a1ad8276d611889bbee53a27`
- Auth identity persistence: `VERIFIED_COMPLETE` and merged
- Auth runtime implementation: `NOT_STARTED`
- Auth runtime: `NOT_TESTED`
- `ASSUMED`: `NONE`

`AUTH-DEC-001` through `AUTH-DEC-013` are contract decisions made under
`AUTH-DB002-CONTRACT-001`. They remain in force unchanged. `AUTH-001` adds
`AUTH-DEC-014` through `AUTH-DEC-020` as audit-level decisions only; none of
them alters `CONTRACT-AUTH-001` semantics.
`AUTH-DEPENDENCY-RECONCILIATION-001-A3` adds `AUTH-DEC-021` through
`AUTH-DEC-025`, which record merged dependency acceptances and readiness only.
None of them alters `CONTRACT-AUTH-001` semantics.

`AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001-A3` adds `AUTH-DEC-026`
through `AUTH-DEC-035`. These are the first decisions in this log that do
change `CONTRACT-AUTH-001`: they raise it to `1.1.0-draft.1` and add
browser-session semantics. Every earlier decision remains in force, and none of
the additions alters any identity, issuer, actor, access-grant, lifecycle,
attribution or secret-exclusion semantic. The statement in `AUTH-DEC-025` that
"no decision in this log authorizes Auth code, tests, or configuration" remains
true: the new decisions are documentation and design only.

`AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001-A3-C1` adds `AUTH-DEC-036`
through `AUTH-DEC-039`, applying four A2-AUTH manager corrections issued as
`CHANGES_REQUIRED_BEFORE_A2_AUTH_ACCEPTANCE`. Each correction **restricts** the
drafted behavior: it removes an ambiguity or an overclaim rather than adding a
capability. `AUTH-DEC-031` and `AUTH-DEC-032` are amended in place, below, and
`AUTH-DEC-034` is extended by `AUTH-DEC-039`. The contract version identifier
remains `1.1.0-draft.1` and the classification remains
`ADDITIVE_COMPATIBLE_MINOR`, because the draft was never accepted and no
consumer has implemented against it. These decisions likewise authorize no Auth
code, test, or configuration.

`AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001-A3-C2` adds `AUTH-DEC-040` and
`AUTH-DEC-041`, applying a second round of A2-AUTH manager corrections issued as
`CHANGES_REQUIRED_BEFORE_A2_AUTH_ACCEPTANCE`. `AUTH-DEC-040` replaces the
self-contradictory correlation-record lifetime in `AUTH-DEC-037` with a coherent
two-phase lifecycle; `AUTH-DEC-041` separates callback-attempt failure from
session-validity failure, which `AUTH-DEC-037` had conflated. `AUTH-DEC-037` is
amended in place, below. Neither correction relaxes correlation, replay
resistance, single-use authorization codes, or fail-closed behavior under
uncertainty. The contract version identifier remains `1.1.0-draft.1` and the
classification remains `ADDITIVE_COMPATIBLE_MINOR`, for the same reason: the
draft is still unaccepted. These decisions authorize no Auth code, test, or
configuration either.

## `AUTH-DEC-001` — Contract-first dependency bridge

Publish `CONTRACT-AUTH-001` before A2-DATABASE begins Auth-owned DB-002
persistence. A2-DATABASE acknowledgement and accepted
`CONTRACT-WORKFLOW-001` remain required.

## `AUTH-DEC-002` — UUID internal human identity

Canonical users and other Auth conceptual records use UUID internal IDs;
external identifiers remain separate.

## `AUTH-DEC-003` — Provider-neutral external identity

Opaque, case-sensitive `issuer + subject` is unique and maps to one canonical
user. Email and mutable login names are not authorization keys.

## `AUTH-DEC-004` — No local credential persistence

DB-002 requires no password hash or local credential field. Raw secrets and
provider tokens are excluded from ordinary domain tables.

## `AUTH-DEC-005` — Exact repository authorization tuple

Repository access is deny-by-default and scoped by the exact
user-installation-repository tuple; grants never cross tuple members.

## `AUTH-DEC-006` — Provider-neutral Database boundary

The contract defines semantics only. A2-DATABASE owns physical schema,
constraints, indexes, ORM, PostgreSQL, migrations, and migration ordering.

## `AUTH-DEC-007` — Lifecycle denial and historical attribution

Inactive lifecycle states deny new actions without deleting historical actor,
installation, repository, or access attribution.

## `AUTH-DEC-008` — Canonical actor types

The actor vocabulary is `HUMAN_USER`, `GITHUB_APP_INSTALLATION`,
`SYSTEM_SERVICE`, and `UNAUTHENTICATED`, with human and machine identities kept
distinct.

## `AUTH-DEC-009` — No generic permission tables for DB-002

The initial action vocabulary is semantic. DB-002 adds no enterprise tenancy,
generic roles, permission tables, user-role tables, or billing.

## `AUTH-DEC-010` — Contract compatibility policy

Breaking semantic changes require a major version and coordinated Database and
Integration review. Additive clarifications may proceed through the compatible
draft contract process.

## `AUTH-DEC-011` — Exact issuer comparison

The canonical provider-supplied issuer value is stored and compared exactly
and case-sensitively. A2-DATABASE performs no independent transformation or
normalization. Any future normalization or comparison-policy change is
contract-breaking and requires a new compatible contract decision, A2-AUTH
approval, A2-DATABASE migration and uniqueness assessment, consumer review,
and Integration coordination.

## `AUTH-DEC-012` — Distinct access-grant expiration

`expires_at` is the scheduled validity boundary, `expired_at` records when a
grant was marked expired, and `revoked_at` records explicit withdrawal. At or
after a scheduled boundary, new authorization is denied even before
asynchronous status reconciliation. Expiration and revocation remain distinct.

## `AUTH-DEC-013` — Additive consumer-requested draft clarification

`CONTRACT-AUTH-001` version `1.0.0-draft.2` is an additive draft clarification
requested through `DB-AUTH-CONTRACT-ACK-001`; its status remains
`DRAFT_FOR_CONSUMER_REVIEW`.

## `AUTH-DEC-014` — First-party evidence excludes dependency-package source

Auth implementation evidence is drawn only from tracked first-party files.
Vendored and generated trees — `apps/api/.venv/**`, `.venv/**`,
`node_modules/**`, build, dist, and coverage outputs — are excluded from every
search and are never counted as TestGap Miner Auth implementation. A
third-party package that happens to contain OAuth, JWT, or session code proves
nothing about this system.

Applied in `AUTH-001_AUDIT.md` §2.1 and §3.1.

## `AUTH-DEC-015` — Documentation alone does not prove runtime implementation

A contract, a decision record, a status table, or a schema comment is never
accepted as evidence that a runtime behavior exists. `VERIFIED_COMPLETE`
requires both first-party implementation and executed supporting evidence.
An area whose only artefact is a contract is classified `NOT_STARTED`.

Corollary: Database constraint tests prove schema semantics only. They are
never cited as evidence of an Auth runtime decision. The audit adopts the
limitation that `tests/database/test_auth_constraints.py:1-7` states about
itself.

## `AUTH-DEC-016` — Absence is recorded as absence, not as a vulnerability

A missing Auth control is classified as an absent feature unless repository
evidence proves runnable unsafe behavior. The audit distinguishes five classes:
absent feature, incomplete control, contradictory contract, unsafe implemented
behavior, and untested behavior. Exactly one finding — `AUTH-ISSUE-016`, the
authenticate-by-exception API surface — is classified
`UNSAFE_IF_DEPLOYED_IMPLEMENTED_BEHAVIOR`, because `Dockerfile:17` ships a
runnable command and local `TestClient` evidence proves the unauthenticated
response. Actual public or production exposure is `NOT_TESTED`.

## `AUTH-DEC-017` — Current trust-boundary classification

Thirteen trust boundaries are authoritative for Auth planning:
B1 browser→frontend, B2 frontend→IdP, B3 IdP callback→frontend/backend,
B4 browser/frontend→FastAPI, B5 FastAPI→JWKS, B6 webhook sender→endpoint,
B7 service→GitHub App auth, B8 installation→repository,
B9 human→installation→grant, B10 service→PostgreSQL, B11 service→secret store,
B12 human approval→publication request, B13 publisher→GitHub destination.

At this baseline exactly two are implemented: B10 (`IMPLEMENTED` and `TESTED`)
and B11 (`PARTIAL`, database credentials only). B4 and B9 are `PARTIAL`. The
remaining nine are `NOT_STARTED`. Any Auth task that claims to close a
boundary must cite first-party implementation and an executed test.

## `AUTH-DEC-018` — Auth secrets are named, never valued

Auth configuration is discussed by variable name only, in every Auth record.
No Auth record may contain a secret value, a private key, a token, or a
signature. A2-DEPLOYMENT freezes human IdP client-variable names and
secret-injection ownership through `AUTH-DEP-004`, and GitHub App/webhook
variable names through `AUTH-DEP-009`. Other future Auth-owned configuration
names remain indicative and non-binding in `AUTH-001_AUDIT.md` §7.2.

## `AUTH-DEC-019` — `AUTH-002` readiness decision

Status: `SUPERSEDED_BY_AUTH-DEC-024`. The reasoning below is preserved as the
historical `AUTH-001` record; its blocking conclusion no longer holds because
`AUTH-DEP-004` and `AUTH-DEP-010` are now accepted, acknowledged and merged.

`AUTH-002` is `NOT_READY / BLOCKED`. Its direct remaining prerequisite is
`AUTH-DEP-004`: A2-DEPLOYMENT-owned callback requirements and human IdP runtime
metadata, including the approved IdP/equivalent, canonical issuer, audience,
JWKS/key source, authorization/token endpoints, owned dashboard domain, OAuth
callback allowlist, TLS termination, client variable names, and
secret-injection ownership.

`AUTH-DEP-010` is an additional
`PROTECTED_FILE_AND_IMPLEMENTATION_OWNERSHIP_CONSTRAINT`. It must be resolved
before A3-AUTH or A3-UI modifies UI-owned paths or performs frontend Auth
integration tests, but it does not replace the direct prerequisite list.
`AUTH-002` contract/design work may begin after `AUTH-DEP-004` is accepted.

`AUTH-DEP-006` is a future Backend integration dependency for `AUTH-003`,
`AUTH-005`, and `AUTH-006`, not a direct `AUTH-002` prerequisite. `AUTH-DEP-009`
is the separate GitHub App/webhook runtime configuration dependency for
`AUTH-004` and `AUTH-005`, not a human sign-in prerequisite.

A2-AUTH deliberately does not authorize starting `AUTH-002` against assumed
identity-provider values. Freezing an issuer, audience, or callback URL
without the deployment owner would produce a contract that is wrong in a way
`CONTRACT-AUTH-001` §Compatibility and versioning classifies as breaking to
correct.

## `AUTH-DEC-020` — Auth prerequisites stop at task ownership boundaries

GitHub App machine-token authentication is independent from persistence of a
machine publication actor. `AUTH-004` is blocked by sequential `AUTH-003` and
`AUTH-DEP-009`; `AUTH-DEP-008` instead blocks `AUTH-006` and `AUTH-008` final
acceptance.

Webhook signature verification over the raw body and extraction of the
delivery GUID and repository identity are likewise independent from durable
delivery-idempotency persistence. `AUTH-005` is blocked by sequential
`AUTH-004`, `AUTH-DEP-006`, and `AUTH-DEP-009`. Durable duplicate-delivery
rejection is a downstream Backend/Workflow/Database integration gap that must
be resolved before end-to-end webhook processing and `AUTH-008` final
acceptance; `AUTH-001` selects no owner and authorizes no new Database model or
dependency contract.

Downstream integration requirements must not silently rewrite the
authoritative prerequisites or ownership of an Auth task.

## `AUTH-DEC-021` — A2-AUTH acknowledgement of `AUTH-DEP-004`

A2-DEPLOYMENT issued `ACCEPTED_WITH_CONSTRAINTS` for `AUTH-DEP-004`, and
A2-AUTH acknowledges that response. The decision is durably merged through
Deployment pull request #20, merge commit
`fc549fa1a4c77f4835acefbb4f937c35ad6e8f76`, evidenced by
`docs/components/deployment/DECISION_LOG.md` and
`docs/components/deployment/ENVIRONMENT_VARIABLES.md`.

The Auth-owned state of `AUTH-DEP-004` is therefore
`ACCEPTED_WITH_CONSTRAINTS / ACKNOWLEDGED_BY_A2_AUTH / MERGED_VIA_PR_20`.

## `AUTH-DEC-022` — Accepted human identity architecture

A2-AUTH records the Deployment-owned identity architecture accepted under
`AUTH-DEP-004`:

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
- Refresh tokens: never forwarded to FastAPI.
- Redirect policy: exact-match allowlist only.
- Issuer comparison: exact and case-sensitive, consistent with
  `AUTH-DEC-011`.
- Independent issuer normalization: prohibited.

These are accepted **design** values and are not proof of a configured
runtime. Consistent with `AUTH-DEC-015`, no record above is accepted as
evidence that any Supabase project, provider configuration, callback
registration, or key source exists or behaves as described.

Any future change of provider, canonical issuer, audience, JWKS source, or
callback set requires Auth contract review under `AUTH-DEC-010` before it is
adopted, because those values feed normative `CONTRACT-AUTH-001` identity
semantics.

## `AUTH-DEC-023` — A2-AUTH acknowledgement of `AUTH-DEP-010` and the accepted ownership boundary

A2-UI issued `ACCEPTED_WITH_CONSTRAINTS` for `AUTH-DEP-010`, and A2-AUTH
acknowledges that response. UI ownership was established through UI pull
request #19, evidenced by `docs/specifications/A2_UI_MANAGER.md` and the
UI-owned durable records under `docs/components/ui/`. The Auth-owned state of
`AUTH-DEP-010` is `ACCEPTED_WITH_CONSTRAINTS / ACKNOWLEDGED_BY_A2_AUTH /
UI_OWNERSHIP_ESTABLISHED_VIA_PR_19`.

Accepted boundary:

- A2-UI owns the future Dashboard frontend, future `apps/web/**` after
  separate authorization, the user-facing `/auth/callback` route, callback
  loading/error/redirect UX, UI accessibility, user-facing Auth states, and
  frontend consumption of Auth semantics.
- A2-AUTH owns callback semantics, session semantics, identity resolution,
  token lifetime and refresh semantics, token custody semantics, PKCE
  semantics, OAuth-state semantics, and Auth security acceptance.
- A2-DEPLOYMENT owns provider provisioning, deployed callback registration,
  domains, TLS, secret injection, and environment-variable registration.
- A2-SECURITY with A2-AUTH owns final cookie, CSRF and OAuth-state security
  acceptance.

Preserved constraints: no access or refresh token in `localStorage`; no access
or refresh token in `sessionStorage`; no duplicate custom token store; refresh
tokens are never forwarded to FastAPI; access tokens reach FastAPI through
`Authorization: Bearer`; UI route protection is defense-in-depth only; FastAPI
authorization remains authoritative; and A3-AUTH may not modify UI-owned paths
without A2-UI coordination.

Together with the accepted Deployment decisions in `AUTH-DEC-021` and
`AUTH-DEC-022`, this ownership decision satisfies the remaining UI ownership
and coordination prerequisite. `AUTH-DEC-024` is the authoritative decision
that supersedes the historical `AUTH-DEC-019` readiness conclusion.

## `AUTH-DEC-024` — `AUTH-002` contract and design readiness

`AUTH-002` contract/design state is
`READY_FOR_AUTH_002_CONTRACT_AND_DESIGN`. Direct dependency status:

- `AUTH-DEP-004`: `SATISFIED_FOR_CONTRACT_AND_DESIGN`
- `AUTH-DEP-010`: `SATISFIED_FOR_OWNERSHIP_AND_COORDINATION`

`AUTH-002` contract and design work may begin only as a separate, newly
authorized A2-AUTH task. This decision authorizes no work by itself.

## `AUTH-DEC-025` — Implementation remains unauthorized

Design acceptance is not implementation authorization:

- `AUTH-002` runtime implementation: `NOT_AUTHORIZED`
- `AUTH-002` frontend implementation: `NOT_AUTHORIZED`
- `AUTH-002` provider runtime: `NOT_PROVISIONED / NOT_TESTED`
- `AUTH-003`: `NOT_AUTHORIZED`, still requiring sequential `AUTH-002` design
  work and Backend JWT/runtime coordination through `AUTH-DEP-006`

Unresolved or untested and unchanged by the accepted design status: Supabase
project provisioning; GitHub OAuth provider configuration; the Vercel project;
the production Dashboard hostname; TLS verification; production callback
registration; secret injection; callback runtime behavior; JWT validation;
cookie, CSRF, PKCE and OAuth-state implementation; frontend Auth integration;
and Auth-specific tests.

No runtime task is marked ready merely because `AUTH-DEP-004` and
`AUTH-DEP-010` were accepted. `AUTH-004` remains blocked by sequential
`AUTH-003` and `AUTH-DEP-009`; `AUTH-005` by sequential `AUTH-004`,
`AUTH-DEP-006` and `AUTH-DEP-009`; `AUTH-006` by `AUTH-DEP-007` and
`AUTH-DEP-008`; and `AUTH-007` and `AUTH-008` by their existing Security,
Workflow and runtime prerequisites.

No decision in this log authorizes Auth code, tests, or configuration. The
shared registry's missing Database consumer remains an owner correction. The
stale `CONTRACT-AUTH-001` metadata recorded as `AUTH-ISSUE-011` is an A2-AUTH
correction; `AUTH-001` is forbidden to edit that file and did not. That
correction is made in draft by `AUTH-DEC-027` below.

## `AUTH-DEC-026` — `CONTRACT-AUTH-001@1.1.0-draft.1` versioning classification

`CONTRACT-AUTH-001` moves from `1.0.0-draft.2` to `1.1.0-draft.1`. The change
category is `ADDITIVE_COMPATIBLE_MINOR`.

This classification was verified independently against the contract's own
`Compatibility and versioning` rules rather than assumed from the expected
version. None of the listed breaking items occurs: issuer-subject uniqueness is
unchanged; exact case-sensitive issuer comparison and the prohibition on
independent normalization are unchanged; no external ID becomes an internal ID;
no actor type is removed; the exact user-installation-repository access tuple is
unchanged; no local credential is permitted; no cross-installation or
cross-repository access is permitted; no lifecycle change re-enables denied
access; and no organization tenancy or generic RBAC is introduced.

Compatibility impact: existing `1.0.0-draft.2` consumers require no change, and
`DB-002` requires no migration, column or table.

Consumer-review consequence: the additions create new obligations for `A2-UI`,
`A2-SECURITY`, `A2-DEPLOYMENT`, `A2-BACKEND` and `A2-INTEGRATION`, so each must
review before the version may be treated as accepted.

Status after this task: `DRAFT_FOR_CONSUMER_REVIEW / NOT_IMPLEMENTATION_READY /
NOT_IMPLEMENTED / NOT_TESTED`.

## `AUTH-DEC-027` — Contract metadata reconciliation

`A2-DATABASE` and `DB-002` are no longer represented as an unresolved blocking
consumer. Database is recorded as `HISTORICAL_BLOCKING_CONSUMER /
ACKNOWLEDGED_AND_IMPLEMENTED`, evidenced by PR #12, implementation `5506ab5`
and merge `3701520`. The evidence baseline moves to `006cc88`. The contract's
closing limitations block records `DB-002` as merged and unblocked, and records
that `1.1.0-draft.1` creates no new Database obligation.

This resolves `AUTH-ISSUE-011` in draft. It becomes durable only after A2-AUTH
acceptance and merge.

## `AUTH-DEC-028` — Provider architecture is unchanged and Supabase terminates the provider callback

`SUPABASE_AUTH_WITH_GITHUB_OAUTH` is retained exactly as accepted in
`AUTH-DEC-022`. Supabase Auth terminates the GitHub OAuth callback. The
Dashboard `/auth/callback` route is not the GitHub provider's direct OAuth
callback, and no Auth record may describe it as GitHub-registered. Repository
evidence proves no architecture change, so none is documented.

All issuer, audience, JWKS and callback values remain unresolved placeholder
templates. Consistent with `AUTH-DEC-015` and `AUTH-DEC-018`, they are design
values only and are not evidence of any configured runtime.

## `AUTH-DEC-029` — Token custody uses the official cookie-backed SSR integration

Determined from current primary Supabase documentation rather than remembered
SDK behavior; the exact sources are listed in `LATEST_AGENT3_HANDOFF.md`.

The accepted storage constraints **can** be satisfied. The required integration
model is the official server-side rendering integration, `@supabase/ssr` with
`@supabase/supabase-js`, using `createBrowserClient` in browser code and
`createServerClient` in Server Components, Server Actions and Route Handlers.
The canonical session source is that integration's cookie-backed store, with
PKCE. There is no second store.

The session is browser-readable by design: the official guidance states that
`HttpOnly` is not necessary and that the browser side needs access to the
refresh token to maintain the session. `HttpOnly` is therefore not achievable
for this cookie and is not claimed. It was never one of the accepted
constraints, so no accepted constraint is weakened, and no
`TOKEN_CUSTODY_DESIGN_CONFLICT` arises. The final cookie posture is an
unresolved A2-SECURITY decision.

Binding prohibition: browser code must not initialize a Supabase client with
`createClient` from `@supabase/supabase-js`, because that client persists the
session to `localStorage` by default in a browser. The `localStorage`
prohibition is not waived because an SDK defaults to it; the defaulting factory
is prohibited instead. Recorded as `AUTH-ISSUE-021`.

No custom storage mechanism is invented, and every existing prohibition on
`localStorage`, `sessionStorage`, duplicate stores and refresh-token forwarding
to FastAPI is preserved.

## `AUTH-DEC-030` — Callback ownership split is frozen

A2-UI owns route existence, loading, success and error UX, accessibility,
presentation and the final navigation using the destination Auth returns.
A2-AUTH owns callback meaning, provider-result handling, PKCE and OAuth-state
verification semantics, session establishment, replay and duplicate behavior,
outcome classification, and post-callback session validity. A2-DEPLOYMENT owns
deployed registration, origin, TLS, environment registration, allowlist
registration and secret injection. A2-SECURITY with A2-AUTH owns final
acceptance of state protection, PKCE, CSRF posture, cookie posture, redirect
safety and replay resistance.

Owning the route is owning the surface. It never confers authority to define
what a callback means or to treat a rendered page as authentication.

## `AUTH-DEC-031` — Loading is never authenticated and uncertainty fails closed

Amended by `AUTH-DEC-036`.

The session model defines nine UI-observable states. `INITIALIZING`,
`SIGN_IN_PENDING`, `CALLBACK_PROCESSING` and `REFRESH_PENDING` are loading
states and are never authenticated. Stale UI state is never authorization, and
protected content is removed rather than overlaid on entry to
`UNAUTHENTICATED`, `SIGN_OUT_PENDING` or `TERMINAL_SESSION_ERROR`. Whenever
session validity is uncertain, the session fails closed to
`TERMINAL_SESSION_ERROR`; uncertainty is never resolved in favor of access.

Amendment: `REFRESH_PENDING` carries two mutually exclusive modes determined at
entry, and protected content is additionally removed on entry to mode
`UNPROVEN_CREDENTIAL`. Uncertainty must never preserve existing access, not
merely never grant new access. See `AUTH-DEC-036`.

## `AUTH-DEC-032` — Bounded refresh and no unbounded retry

Amended by `AUTH-DEC-036` and `AUTH-DEC-038`.

Refresh is provider-managed ahead of expiry, with application-triggered refresh
permitted only through the Auth-owned adapter and only in bounded cases.
Concurrent refresh is single-flight **within one Auth adapter/client instance or
one browsing context**; the original unqualified "single-flight: one exchange,
one shared outcome" is corrected, because nothing in the accepted provider
design serializes refresh across separate browser tabs, parallel server
requests, or separate runtime instances. A protected request that receives `401`
justifies at most one refresh and at most one retry; a second failure ends the
attempt and the session fails closed. A Backend `401` never creates an unbounded
refresh-and-retry cycle, and UI belief that a session exists never overrides
Backend denial. Refresh tokens are never forwarded to FastAPI.

Amendment: the refresh entry condition now determines a fail-closed mode
(`AUTH-DEC-036`), and cross-context refresh races are explicitly not serialized
(`AUTH-DEC-038`).

## `AUTH-DEC-033` — Sign-out is local-first and claims no Backend token revocation

Local authenticated state is cleared whether or not the remote sign-out
succeeds, and `SIGN_OUT_FAILED` still leaves the user signed out in this
browser. Sign-out wins over a concurrent refresh and over a late callback
success. The provider sign-out scope must be passed explicitly rather than
defaulted, because the official integration defaults to signing the user out of
every device; the Auth-proposed default is current-session scope and the final
value is an A2-SECURITY decision.

No Auth record may claim that sign-out revokes already-issued Backend access
tokens. The accepted provider and Backend design proves no such revocation.
Recorded as `AUTH-ISSUE-022`.

## `AUTH-DEC-034` — Redirects are Auth-validated relative paths only

Extended by `AUTH-DEC-039`: format validation is necessary but never
sufficient. A return path must also be bound to the sign-in attempt being
completed.

Only a single relative path beginning with exactly one `/` may become a
post-authentication destination. Protocol-relative forms, any scheme prefix,
absolute URLs, user-info `@` forms, backslashes, control characters, encoded
and nested bypass forms, malformed paths and disallowed internal routes are all
rejected, and every rejection falls back to the default destination.
Provider-returned data never directly controls final navigation. Callback
destinations remain exact-match allowlisted with no wildcard, prefix, suffix or
normalized comparison. This design prevents open redirects.

## `AUTH-DEC-035` — Stable error vocabulary with no failure oracle

The Auth-owned error vocabulary for this version is exactly eleven
classifications: `USER_CANCELLED`, `PROVIDER_DENIED`, `INVALID_CALLBACK`,
`STATE_VALIDATION_FAILED`, `PKCE_VALIDATION_FAILED`, `SESSION_EXCHANGE_FAILED`,
`SESSION_EXPIRED`, `REFRESH_FAILED`, `SIGN_OUT_FAILED`,
`CONFIGURATION_UNAVAILABLE` and `TEMPORARY_PROVIDER_FAILURE`. A consumer must
not invent an Auth error class and must not map an unrecognized failure onto a
more permissive one.

`STATE_VALIDATION_FAILED`, `PKCE_VALIDATION_FAILED`, `INVALID_CALLBACK` and
`SESSION_EXCHANGE_FAILED` must present the same generic user-facing sign-in
failure, so the UI creates no oracle distinguishing which validation step
failed. Authorization codes, PKCE verifiers, tokens, raw provider payloads, raw
headers, cookie values, the project reference, hostnames, secrets, stack traces
and unapproved internal identifiers are redacted from every classification.

Removing a classification, or changing an existing one's retry,
reauthentication or Backend-eligibility meaning, is a breaking change under the
contract's versioning rules.

## `AUTH-DEC-036` — `REFRESH_PENDING` carries two fail-closed-aware modes

Corrects the drafted `REFRESH_PENDING` state, which combined proactive refresh
of a still-valid credential with refresh after expiry, after a Backend `401`,
or under unknown session validity. Those cases must not be interpretable
identically.

`REFRESH_PENDING` remains one of the nine session states and is not split into
a tenth. It carries two mutually exclusive modes, determined at entry rather
than inferred afterwards:

- Mode `PROVEN_CREDENTIAL` — refresh begins while the current access token and
  the session are known-valid. Existing protected content may remain visible,
  new protected Backend requests wait for the refresh outcome, and no new
  privileged effect may begin using an expired token.
- Mode `UNPROVEN_CREDENTIAL` — refresh begins because the access token is
  expired, because Backend returned `401`, because session validity is unknown,
  or because the current credential cannot be proven usable. Protected content
  is removed or hidden, protected interactions are disabled, protected Backend
  requests are prohibited rather than queued, and the session fails closed
  pending the outcome.

A `PROVEN_CREDENTIAL` refresh that loses proof of validity while in flight
degrades immediately and irreversibly to `UNPROVEN_CREDENTIAL`.

A loading state remains never authenticated in either mode, and uncertainty
must never preserve access. The two modes must never be satisfiable by the same
implementation behavior; an ambiguous single state is prohibited.

## `AUTH-DEC-037` — A duplicate callback resolves only on proven correlation

Corrects the drafted duplicate-callback rule, which allowed a second invocation
to resolve successfully merely because a valid session already existed. That is
too permissive: an existing session proves only that some sign-in once
succeeded, never anything about the invocation being processed now.

A prior successful callback result is reusable only when Auth verifies that the
invocation belongs to the same sign-in attempt, the same callback flow, and the
same previously completed callback outcome. An existing session alone is not
correlation.

An unrelated, malformed, consumed, expired, replayed or uncorrelated callback
must create no session, perform no new code exchange, perform no
callback-directed navigation, return `INVALID_CALLBACK`, clear the callback
parameters, and produce the required Security event.

A page reload after successful callback processing may resolve to the
established session only when callback completion for that exact flow is proven
by the correlation record; otherwise it fails closed. The single-use
authorization-code rule and the replay-resistance requirement are preserved
unchanged and apply independently of correlation.

The correlation record is Auth-owned and created when the sign-in attempt
begins. Its exact storage, lifetime and required strength are
`PENDING_A2_SECURITY_ACCEPTANCE` under `AUTH-DEP-011` and are not invented
here. Recorded as `AUTH-ISSUE-025`.

**Amended by the second A2-AUTH correction round.** As first drafted, this
decision also stated that the correlation record is removed once the callback
flow reaches a terminal outcome. A successful callback is a terminal callback
outcome, so that statement contradicted the post-success duplicate-correlation
requirement in the same decision. The record's lifecycle is now defined by
`AUTH-DEC-040` and supersedes any immediate-removal reading here. This decision
also implied that an uncorrelated callback invalidates the browser session;
`AUTH-DEC-041` supersedes that, and the requirement that an existing session is
never correlation is unchanged by both amendments.

## `AUTH-DEC-038` — Single-flight refresh is scoped, not global

Corrects any reading of the draft under which provider behavior guarantees
global single-flight refresh. It does not, and no Auth record may claim it.

Single-flight refresh is guaranteed only within one Auth adapter/client
instance or one browsing context. Serialization is **not** promised across
separate browser tabs, parallel server requests, or separate runtime instances.

Concurrent cross-context refresh may produce a stale cookie, a temporarily null
session, or one successful refresh paired with one rejected refresh. Every such
race must fail closed, tolerate provider cookie synchronization, avoid
restoring stale authenticated state, use at most one bounded retry and only
after a newer valid session has actually been observed, and never create an
automatic refresh loop.

`onAuthStateChange` events and `BroadcastChannel` messages are synchronization
signals only. They are never proof that all refresh exchanges were serialized.

The observable behavior of concurrent cross-context refresh under the official
`@supabase/ssr` cookie model is `NOT_TESTED` in this repository. Recorded as
`AUTH-ISSUE-026`, with review questions in `AUTH-DEP-011` and `AUTH-DEP-015`.

## `AUTH-DEC-039` — Intended-return state is Auth-owned and attempt-bound

Separates provider OAuth state from the Dashboard's intended-return state.
Supabase/provider OAuth-state handling remains provider-integration-owned. The
Dashboard intended-return state is separately Auth-owned.

The intended-return state must be created by Auth, bound to exactly one sign-in
attempt, given a defined expiry, single-use, integrity-protected or stored in
Auth-controlled same-origin state, and removed after callback success and
failure alike. It must never be accepted merely because it contains a
syntactically safe path: format validation and binding validation are two
independent gates, and passing format alone authorizes nothing.

Missing, expired, tampered, replayed or unbound return state falls back to the
default post-sign-in destination without affecting the session outcome.

The exact storage and integrity mechanism remains `PENDING_A2_SECURITY_ACCEPTANCE`
and must not be recorded as an accepted final Security decision. The provider
OAuth `state` parameter must not be reused as an application return-path
container unless current official provider documentation explicitly supports
that design and A2-SECURITY accepts it; no such documented support is recorded
at this baseline, so the reuse is prohibited. Recorded as `AUTH-ISSUE-025`.

## `AUTH-DEC-040` — The callback-correlation record has a two-phase bounded lifecycle

Resolves the internal contradiction in `AUTH-DEC-037` as first drafted: it
required a duplicate invocation and a post-success reload to correlate to the
same completed callback outcome, while also removing the correlation record once
the flow reached a terminal outcome. A successful callback **is** a terminal
callback outcome, so immediate removal made the required post-success
correlation impossible.

The correlation record now has two successive Auth-owned states, scoped to one
callback flow:

1. `PENDING_ATTEMPT_CORRELATION` — created when `beginSignIn` starts a sign-in
   attempt, and held until the callback flow completes.
2. `COMPLETED_CALLBACK_CORRELATION` — created on successful first callback
   processing, by transition or replacement of the pending state.

A completed record proves exactly four things: the originating sign-in attempt,
the callback flow, the completed callback outcome, and whether that outcome may
be reused for a correlated duplicate invocation. It proves nothing else. It is
not a session, not a credential and not authorization, and it never carries an
authorization code, a token or a PKCE verifier.

The completed record remains available for a **bounded post-completion
correlation window**, so that an immediate duplicate invocation and a page
reload after successful callback processing can both correlate to that outcome
without a second code exchange and without a second session. A successful
callback therefore does not discard its correlation evidence at the instant it
completes.

The record is never valid indefinitely. Once its bounded window expires, or the
record is otherwise removed, a later callback invocation is not correlated: it
returns `INVALID_CALLBACK`, performs no exchange, and performs no
callback-directed navigation.

Failed, abandoned, malformed, expired and terminally rejected flows leave no
reusable successful-callback correlation evidence. Only a flow that actually
completed successfully may produce a `COMPLETED_CALLBACK_CORRELATION` record.

The exact storage mechanism, integrity mechanism, record representation,
retention duration and cleanup implementation — including the length of the
bounded post-completion window — remain `PENDING_A2_SECURITY_ACCEPTANCE` under
`AUTH-DEP-011`. No duration and no Security mechanism is invented here.
Recorded as `AUTH-ISSUE-025`.

## `AUTH-DEC-041` — An invalid callback does not invalidate an independent session

Corrects the drafted treatment of `INVALID_CALLBACK` as proof that the entire
existing browser session is invalid. A rejected callback attempt and an
independently established session are separate facts, and the contract now
represents them separately.

Every unrelated, malformed, consumed, expired, replayed or uncorrelated callback
still creates no new session, performs no code exchange, performs no
callback-directed navigation, returns `INVALID_CALLBACK`, clears the callback
parameters, removes the intended-return state associated with the rejected
attempt, and emits the required Security event. An existing session remains
insufficient callback correlation in every case.

The resulting **session** state is conditional on the pre-existing session
alone:

- no independently valid pre-existing session — `TERMINAL_SESSION_ERROR`,
  presenting as `UNAUTHENTICATED`, and reauthentication is required;
- a session independently established before the rejected callback and still
  known-valid — preserved and still `AUTHENTICATED`, while the callback attempt
  fails, no callback success is reported, no callback-directed destination is
  used, the UI presents a safe callback-error outcome or safe route recovery,
  and FastAPI authorization remains authoritative;
- a pre-existing session whose validity is unknown or unprovable — fail closed:
  protected content removed, protected requests prohibited, and
  `TERMINAL_SESSION_ERROR` unless later independently proven valid through an
  authorized session-restoration path.

Preserving a known-valid session is not resolving the callback with it. The
callback must never use the existing session as evidence that callback
processing succeeded. Conversely, a malformed callback must never revoke or sign
out a separately valid provider session merely because the callback itself was
invalid; session invalidation requires an independent session-validity failure,
classified under its own error code.

The `INVALID_CALLBACK` error vocabulary now expresses this conditional resulting
session state instead of always forcing `TERMINAL_SESSION_ERROR`. This narrows
no fail-closed rule: uncertainty still resolves against access.
