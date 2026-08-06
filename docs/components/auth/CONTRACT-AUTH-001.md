# CONTRACT-AUTH-001 — Authentication Identity and Repository Authorization Boundary

## Metadata

| Field | Value |
|---|---|
| Contract ID | `CONTRACT-AUTH-001` |
| Version | `1.1.0-draft.1` |
| Previous version | `1.0.0-draft.2` |
| Change category | `ADDITIVE_COMPATIBLE_MINOR` |
| Status | `DRAFT_FOR_CONSUMER_REVIEW` |
| Implementation readiness | `NOT_IMPLEMENTATION_READY` |
| Runtime status | `NOT_IMPLEMENTED / NOT_TESTED` |
| Owner | `A2-AUTH` |
| Historical blocking consumer | `A2-DATABASE` (`DB-002`) — `ACKNOWLEDGED_AND_IMPLEMENTED` |
| Required consumers for the `1.1.0-draft.1` additions | `A2-UI`, `A2-SECURITY`, `A2-DEPLOYMENT`, `A2-BACKEND`, `A2-INTEGRATION` |
| Evidence baseline | `006cc885161ff49be582a9fa08f353a70c31c7b1` |
| Prior evidence baseline | `739a331c9942ed64a1ad8276d611889bbee53a27` |

This contract defines semantic identity, authorization, and browser-session
requirements only. It does not implement Auth, Database, Backend, or frontend
behavior. A2-DATABASE retains ownership of physical table names, ORM classes,
migrations, constraint names, indexes, PostgreSQL implementation, and migration
ordering. A2-UI retains ownership of frontend implementation, routes as user
surfaces, and UX. A2-DEPLOYMENT retains ownership of provider provisioning,
deployed origins, TLS, callback registration, and secret injection.

`A2-DATABASE` is recorded as a `HISTORICAL_BLOCKING_CONSUMER /
ACKNOWLEDGED_AND_IMPLEMENTED`. `DB-002` is merged (pull request #12,
implementation `5506ab5`, merge `3701520`) and no Database rereview of the
`1.0.0-draft.2` semantics is outstanding. Version `1.1.0-draft.1` adds
browser-session semantics that create no new Database obligation.

Version `1.1.0-draft.1` is a draft for consumer review. It is not accepted, not
implementation-ready, not implemented, and not tested. No statement in this
contract authorizes Auth runtime implementation, frontend implementation,
provider provisioning, or `UI-004`.

The `1.1.0-draft.1` text incorporates four A2-AUTH manager corrections applied
before acceptance, recorded as `AUTH-DEC-036` through `AUTH-DEC-039`: fail-closed
`REFRESH_PENDING` semantics, callback duplicate and replay correlation,
cross-tab and cross-request refresh limits, and intended-return state binding.
Each correction restricts behavior that the earlier draft text left permissive
or ambiguous.

A second A2-AUTH correction round then resolved two defects in that text,
recorded as `AUTH-DEC-040` and `AUTH-DEC-041`: the callback-correlation record
now has a coherent two-phase lifecycle whose completed phase survives successful
completion for a bounded, non-indefinite window, replacing text that required
post-success duplicate correlation while also removing the record at the
successful terminal outcome; and an `INVALID_CALLBACK` result now classifies the
callback attempt only, so it no longer asserts that an independently
established, known-valid session is invalid. Neither correction relaxes
correlation, replay resistance, single-use codes, or fail-closed behavior under
uncertainty.

The version identifier is unchanged because the draft was never accepted, and
the classification remains `ADDITIVE_COMPATIBLE_MINOR` over `1.0.0-draft.2`.

## Authentication domains and human-control boundary

Human authentication and GitHub App machine authentication are separate
domains. A human session must never be treated as a GitHub App installation
token, and a GitHub App installation token must never be treated as a human
identity.

No permission defined here authorizes auto-merge, approval bypass,
branch-protection bypass, or autonomous production-code editing. Publication
permission never grants merge permission.

## Canonical human user

A canonical human user has:

- internal UUID `user_id`;
- `status`: `ACTIVE`, `SUSPENDED`, or `DEPROVISIONED`;
- `created_at` and `updated_at`;
- nullable `suspended_at`; and
- nullable `deprovisioned_at`.

Only `ACTIVE` users receive new successful authorization. `SUSPENDED` and
`DEPROVISIONED` users are denied by default, while historical actor attribution
is retained. Email, username, login name, and display name are not identity
keys. MVP requires no password hash or local credential field.

## External authentication subject

An external authentication subject linked to a canonical user has:

- internal UUID `auth_subject_id`;
- `user_id`;
- `issuer`;
- opaque, case-sensitive `subject`;
- optional `provider_name`;
- optional immutable `provider_account_id`;
- `status`: `ACTIVE` or `REVOKED`;
- `linked_at`; and
- nullable `revoked_at`.

`issuer` is the canonical issuer string supplied by the configured identity
provider. The configured provider boundary stores that canonical issuer value
exactly as supplied. Issuer storage and comparison are exact and
case-sensitive. A2-DATABASE must not independently lowercase, uppercase,
rewrite, trim or append URL components, URL-normalize, remove trailing
characters, resolve aliases, or otherwise transform issuer values.

The pair `(issuer, subject)` is unique using the exact canonical stored issuer
and exact opaque subject values. `subject` remains opaque and case-sensitive.
One active issuer-subject maps to exactly one canonical user; duplicate linkage
to another user is rejected. A revoked subject cannot authenticate. Email and
mutable login names cannot authorize access. Provider tokens and refresh
tokens are never persisted.

Any future issuer-normalization or comparison-policy change is
contract-breaking and requires a new compatible contract decision, A2-AUTH
approval, A2-DATABASE migration and uniqueness assessment, consumer review,
and Integration coordination.

These provider-neutral semantics do not freeze a particular OAuth
implementation, identity provider, issuer value, audience value, callback URL,
or OAuth route for DB-002.

## GitHub App installation identity and lifecycle

A GitHub App installation has:

- internal UUID `installation_id`;
- unique GitHub numeric installation ID;
- immutable GitHub numeric account ID;
- `account_type`: `USER` or `ORGANIZATION`;
- `status`: `ACTIVE`, `SUSPENDED`, or `DELETED`;
- `installed_at`;
- nullable `suspended_at`;
- nullable `deleted_at`; and
- `last_synced_at`.

An inactive installation denies new repository operations. Installation tokens
and GitHub App private keys are never stored. Historical installation
attribution remains available.

## Repository identity and lifecycle

A repository has:

- internal UUID `repository_id`;
- unique GitHub numeric repository ID;
- `status`: `ACTIVE`, `ARCHIVED`, `INACCESSIBLE`, or `DELETED`;
- `created_at`;
- `updated_at`; and
- `last_synced_at`.

Owner/name strings are mutable display metadata only and must not authorize
access. `INACCESSIBLE` or `DELETED` repositories deny new actions. Historical
repository attribution remains available. Repository source bytes are outside
this contract.

## Exact repository-access grant

Repository authorization is scoped by the exact tuple:

`user + GitHub App installation + repository`

A repository-access grant has:

- internal UUID `repository_access_id`;
- `user_id`;
- `installation_id`;
- `repository_id`;
- `status`: `ACTIVE`, `REVOKED`, or `EXPIRED`;
- `authorization_source`: `GITHUB_VERIFIED`;
- `granted_at`;
- `last_verified_at`; and
- nullable `expires_at`;
- nullable `expired_at`; and
- nullable `revoked_at`.

At most one active grant exists for an exact
user-installation-repository tuple. A grant must not cross users,
installations, or repositories.

An `ACTIVE` grant may have a future `expires_at` or no scheduled expiration,
represented by a null `expires_at`. It must not have an `expired_at` indicating
that it has already been marked expired. At or after a non-null `expires_at`,
the grant denies new authorization even if asynchronous persistence
reconciliation has not yet changed its stored status to `EXPIRED`. Consumers
must not treat a past `expires_at` as authorized merely because the stored
status has not yet been updated.

An `EXPIRED` grant denies all new authorization. Its expiration time must be
represented by at least one of `expires_at`, `expired_at`, or an explicitly
documented Database-equivalent representation preserving the same Auth
meaning. `expires_at` is the scheduled validity boundary when one exists;
`expired_at` is when the grant was recorded or marked expired. When both exist,
they may differ because persistence reconciliation may occur after the
scheduled boundary. Historical grant attribution remains preserved.

A `REVOKED` grant denies all new authorization. Revocation uses `revoked_at`
and is an explicit withdrawal, not expiration. `revoked_at` must not substitute
for `expires_at` or `expired_at`, and expiration fields must not substitute for
`revoked_at`.

A2-AUTH owns these lifecycle meanings. A2-DATABASE owns physical column names,
SQL types, indexes, constraint names, and check-constraint implementation. It
may use an explicitly documented equivalent physical representation only when
that representation preserves the same Auth semantics. Database implementation
must not merge revocation and expiration into one indistinguishable lifecycle
event and must preserve historical attribution.

This is not enterprise RBAC. DB-002 requires no organization, role, permission,
user-role, or billing table. Sensitive actions may later require live GitHub
revalidation; exact authorization freshness is deferred to later Auth and
Security work.

## Initial authorization action vocabulary

The initial semantic actions, which do not require permission tables, are:

- `RUN_CREATE`
- `RUN_READ`
- `RUN_RERUN`
- `ARTEFACT_READ`
- `HUMAN_DECISION_WRITE`
- `PUBLICATION_REQUEST`
- `PUBLICATION_EXECUTE`

Authorization is deny-by-default. Human repository actions require an active
user, active external subject, active installation, accessible repository, and
active exact access grant. `HUMAN_DECISION_WRITE` and `PUBLICATION_REQUEST`
require a human actor.

`PUBLICATION_EXECUTE` uses the GitHub App installation actor and must be
traceable to an authorized request, event, or human decision. It does not grant
merge permission.

## Actor types and ownership

1. `HUMAN_USER`
   - requires `user_id`;
   - repository actions also identify `installation_id` and `repository_id`.
2. `GITHUB_APP_INSTALLATION`
   - requires `installation_id`;
   - repository actions also identify `repository_id`.
3. `SYSTEM_SERVICE`
   - requires a stable service identifier;
   - requires a request, run, or correlation identifier.
4. `UNAUTHENTICATED`
   - is used only for rejected requests or security attribution;
   - cannot authorize protected operations.

Auth owns actor identity meaning. Workflow owns workflow event shapes. Security
owns security-event shapes and redaction. Database owns persistence
implementation. Backend owns API route and error-envelope implementation.

## Lifecycle and historical attribution

Suspension, revocation, expiration, inaccessibility, deletion, and
deprovisioning deny new actions. Historical records retain actor, installation,
repository, and grant attribution. Destructive deletion must not break audit or
evidence history. Exact retention durations remain dependent on Security and
Deployment.

## Secret and credential boundary

DB-002 requires no local credential field. Ordinary domain tables must never
store:

- passwords or password hashes;
- OAuth authorization codes, access tokens, or refresh tokens;
- GitHub App private keys, JWTs, or installation access tokens;
- webhook secrets;
- JWT signing secrets;
- provider API keys;
- browser session tokens; or
- raw `Authorization` headers.

## DB-002 conceptual persistence obligations

This contract authorizes A2-DATABASE to implement physical representations for:

1. users;
2. external authentication subjects;
3. GitHub App installations;
4. repositories; and
5. repository-access grants.

The implementation must guarantee UUID internal IDs, separate immutable
external IDs, unique `issuer + subject`, unique GitHub installation ID, unique
GitHub repository ID, exact user-installation-repository access scoping,
lifecycle statuses and timestamps, no local credentials, no raw secrets, and
preserved historical attribution. It must not add enterprise tenancy, generic
RBAC, or billing.

---

# `AUTH-002` — Dashboard sign-in and session contract

Everything from here to the `Compatibility and versioning` section is added by
version `1.1.0-draft.1`. It is additive. It changes no identity semantic, no
issuer semantic, no actor type, no access-grant semantic, no lifecycle denial
rule, no historical-attribution rule, and no secret-exclusion rule defined
above.

## `AUTH-002` provider architecture and evidence status

The accepted architecture is `SUPABASE_AUTH_WITH_GITHUB_OAUTH`, recorded in
`AUTH-DEC-022` from Deployment-owned `DEPLOY-DEC-001` through `DEPLOY-DEC-008`.

| Element | Accepted design value |
|---|---|
| Canonical issuer | `https://<SUPABASE_PROJECT_REF>.supabase.co/auth/v1` |
| Audience | `authenticated` |
| JWKS | `https://<SUPABASE_PROJECT_REF>.supabase.co/auth/v1/.well-known/jwks.json` |
| Deployed Dashboard callback | `${DASHBOARD_ORIGIN}/auth/callback` |
| Local-development callback | `http://localhost:3000/auth/callback` |
| GitHub-registered Supabase callback | `https://<SUPABASE_PROJECT_REF>.supabase.co/auth/v1/callback` |
| OAuth termination | Supabase Auth |
| FastAPI boundary | Supabase JWT access tokens only |

Supabase Auth terminates the GitHub OAuth callback. The Dashboard
`/auth/callback` route is **not** the GitHub provider's direct OAuth callback;
GitHub redirects to the Supabase-hosted callback, and Supabase then redirects
the browser to the Dashboard callback. No repository evidence changes this
architecture, so no record in this contract may describe the Dashboard callback
as GitHub-registered.

`<SUPABASE_PROJECT_REF>` and `${DASHBOARD_ORIGIN}` are unresolved placeholders.
These are design values only. They are not evidence of a configured Supabase
project, an enabled GitHub OAuth provider, a production Dashboard domain, a
registered production callback, TLS configuration, injected secrets, or any
working callback, session, or JWT behavior. Provider runtime is
`NOT_PROVISIONED / NOT_TESTED`.

## `AUTH-002` sign-in initiation contract

Sign-in is initiated only by an explicit human action in the Dashboard. No
automatic, background, timer-driven, or navigation-triggered sign-in is
permitted. Initiating sign-in never proves that authentication succeeded.

A2-UI invokes the Auth-owned adapter operation defined in the
`Auth-owned UI adapter interface` section. A2-UI must not construct a provider
authorization URL, must not add provider query parameters of its own, must not
choose the OAuth flow type, and must not implement the code exchange. The
official Supabase integration constructs, signs, and validates the provider
authorization request; the accepted architecture requires that integration
rather than a hand-built URL.

Binding requirements:

1. GitHub OAuth is mediated through Supabase Auth. UI never contacts GitHub
   directly for authentication.
2. PKCE is `REQUIRED`. The flow type must be PKCE, and the PKCE code verifier
   is created and held by the provider integration on the initiating device.
   No Auth or UI code may read, copy, transmit, persist, or log the verifier.
3. OAuth `state` verification is `REQUIRED` and is performed by the provider
   integration. UI must not implement, weaken, or bypass it.
4. The callback destination requested at initiation must be selected by
   Auth-owned code from the approved callback set for the current environment
   and must never be taken from user input, referrer, query string, postMessage,
   or provider-returned data.
5. The approved callback set is exact-match only: `${DASHBOARD_ORIGIN}/auth/callback`
   deployed, `http://localhost:3000/auth/callback` local. No wildcard, no
   prefix match, no suffix match, no normalized comparison.
6. Provider OAuth `state` and the Dashboard intended-return state are two
   distinct mechanisms and must never be conflated. Provider OAuth `state` is
   provider-integration-owned under requirement 3 above. The Dashboard
   intended-return state is separately Auth-owned and is governed by the
   `Intended-return state binding` rules below.
7. An intended return path may be carried across sign-in only as an
   Auth-validated relative path, validated on the way in and again on the way
   out under the `Safe redirect contract`, and only while it remains bound to
   the originating sign-in attempt. It is never carried as an absolute URL and
   never becomes the provider redirect target.
8. Provider secrets, client secrets, and token values are never exposed to UI
   code, browser JavaScript, or a `NEXT_PUBLIC` variable.
   `SUPABASE_GITHUB_CLIENT_SECRET` is Deployment-owned and must never be
   frontend-readable.

### Intended-return state binding

Supabase/provider OAuth-state handling remains provider-integration-owned and
is not redefined here. The Dashboard intended-return state is a separate,
Auth-owned artefact with its own binding rules.

| Requirement | Rule |
|---|---|
| Creation | Created by Auth-owned code at sign-in initiation. UI never creates it. It is never derived from referrer, `postMessage`, provider-returned data, or any value the user supplies directly. |
| Attempt binding | Bound to exactly one sign-in attempt. A return state that cannot be correlated to the sign-in attempt actually being completed is unbound and must be discarded. |
| Expiry | Has a defined expiry. An expired return state is discarded. |
| Single use | Consumed exactly once. A second presentation of the same return state is a replay and is discarded. |
| Integrity | Integrity-protected, or held in Auth-controlled same-origin state that cannot be presented from another origin. The exact storage and integrity mechanism is `PENDING_A2_SECURITY_ACCEPTANCE` under `AUTH-DEP-011`; this draft does not invent it and does not record it as an accepted final Security decision. |
| Removal | Removed after callback success and after callback failure alike. No return state survives a completed or abandoned flow. |
| Syntax is not sufficiency | A syntactically safe relative path is never accepted merely because it is syntactically safe. Satisfying the `Safe redirect contract` format rules does not make an unbound, expired, replayed, tampered or missing return state usable. |
| Provider `state` reuse | The provider OAuth `state` parameter must not be reused as an application return-path container unless current official provider documentation explicitly supports that design **and** `A2-SECURITY` accepts it. No such documented support is recorded at this baseline, so the reuse is prohibited by this draft. |

Missing, expired, tampered, replayed or unbound return state falls back to the
default post-sign-in destination. The fallback is not a user-facing error and
never blocks an otherwise successful sign-in.

Behavior requirements:

| Condition | Required behavior |
|---|---|
| Repeated clicks on sign-in | The control is disabled or the request is coalesced while state is `SIGN_IN_PENDING`. At most one provider redirect may be initiated per user gesture sequence. |
| Concurrent sign-in in multiple tabs | Permitted, but each tab holds its own pending flow. A callback may only be completed by the device that initiated it, because the PKCE verifier is device-local. A callback arriving without a matching verifier fails as `PKCE_VALIDATION_FAILED`. |
| User cancels at GitHub or Supabase | The session returns to `UNAUTHENTICATED`. Classification `USER_CANCELLED`. No error banner implying system failure. |
| Provider denies the authorization | The session returns to `UNAUTHENTICATED`. Classification `PROVIDER_DENIED`. |
| Provider configuration unavailable or incomplete | Sign-in must not be attempted. Classification `CONFIGURATION_UNAVAILABLE`. The user-facing message must not name the missing variable, project reference, or host. |

## `AUTH-002` callback ownership contract

The ownership split for `/auth/callback` is frozen by this version.

| Owner | Owns |
|---|---|
| `A2-UI` | Route existence, loading UX, success UX, safe error UX, accessibility, visual presentation, and the final safe navigation using the destination Auth returns. |
| `A2-AUTH` | Callback semantic meaning, provider-result handling, PKCE verification semantics, OAuth-state verification semantics, callback-completion correlation, session-establishment semantics, replay and duplicate-callback behavior, intended-return state creation, binding, validation and removal, callback success and failure classification, and session validity after callback. |
| `A2-DEPLOYMENT` | Exact deployed callback registration, Dashboard origin assignment, TLS, environment registration, allowlist registration, and secret injection. |
| `A2-SECURITY` with `A2-AUTH` | Final acceptance of state protection, PKCE, CSRF posture, cookie posture, redirect safety, replay resistance, callback-completion correlation strength, and the intended-return state storage and integrity mechanism. |

A2-UI owning the route means owning the user-facing surface. It does not
authorize A2-UI to define what a callback means, to decide whether a session
exists, or to treat a rendered callback page as authentication.

Required callback behavior:

| Case | Required behavior | Classification |
|---|---|---|
| Valid first processing | Exchange the authorization code exactly once, establish the session, transition the attempt's correlation state to a completed callback-correlation record for that flow, clear callback parameters from the URL, then navigate to the validated destination. | success |
| Duplicate browser invocation, correlated | Permitted to resolve to the previously completed outcome **only** when correlation succeeds under the rules below and the completed record is still inside its bounded post-completion correlation window. No second session is created, no second exchange is performed, and no new success is reported. | success |
| Duplicate browser invocation, uncorrelated | Fails closed as a callback attempt. An existing valid session is not correlation and never justifies resolving the invocation; it is also not invalidated by the rejection. | `INVALID_CALLBACK`, resulting session state conditional |
| Page reload during processing | Treated as a duplicate invocation and subject to the same correlation requirement. The authorization code is single-use; a reload after a consumed code is never reported as a new sign-in. | success only when correlated, otherwise `INVALID_CALLBACK` |
| Page reload after successful callback processing | The established session may be used as the callback result only when the completed callback-correlation record for that exact flow is still available and still inside its bounded post-completion correlation window. Otherwise the callback attempt fails closed and callback parameters are cleared; the session's own validity is judged separately. | success only when correlated, otherwise `INVALID_CALLBACK` |
| Unrelated callback invocation | A callback invocation that belongs to no known sign-in attempt of this browsing context is rejected without a code exchange, whether or not a valid session exists, and without revoking a session that was independently established. | `INVALID_CALLBACK`, resulting session state conditional |
| Callback replay | Rejected. A consumed authorization code must never establish a second session and must never be re-exchanged. | `INVALID_CALLBACK` |
| Missing parameters | Rejected without a provider call. | `INVALID_CALLBACK` |
| Malformed parameters | Rejected without a provider call. No echo of the received value. | `INVALID_CALLBACK` |
| State mismatch | Rejected. Security-relevant. | `STATE_VALIDATION_FAILED` |
| PKCE failure, including a callback completed on a device that did not initiate the flow | Rejected. Security-relevant. | `PKCE_VALIDATION_FAILED` |
| Provider denial returned to the callback | Rejected as a normal outcome, not a system fault. | `PROVIDER_DENIED` |
| Expired callback | Rejected. The authorization code has a short provider-side validity, so a late exchange must fail closed rather than retry. | `INVALID_CALLBACK` |
| Session-exchange failure | Rejected. Session state becomes `TERMINAL_SESSION_ERROR` unless the failure is explicitly transient. | `SESSION_EXCHANGE_FAILED` or `TEMPORARY_PROVIDER_FAILURE` |
| Unsafe, unbound, expired, replayed or tampered return state | The session outcome is unaffected, but navigation falls back to the default post-sign-in destination. A tampered or replayed return state is additionally security-relevant. | success with fallback |
| Terminal failure | All partial session state **created by the rejected attempt** is cleared, callback parameters are removed from the URL, and the intended-return state associated with the rejected attempt is removed. Where no independently valid pre-existing session exists, the user is returned to an unauthenticated surface. A pre-existing session that was independently established and remains known-valid is preserved rather than cleared; a session whose validity is unknown fails closed. | terminal for the callback attempt |

### Callback-completion correlation

A prior successful callback result may be reused only when Auth can verify that
the invocation belongs to all three of:

1. the same sign-in attempt;
2. the same callback flow; and
3. the same previously completed callback outcome.

An existing valid session is **not** correlation. The presence of a session
proves that some sign-in once succeeded; it proves nothing about the invocation
being processed now. Resolving a callback because a session happens to exist is
prohibited.

An unrelated, malformed, consumed, expired, replayed or otherwise uncorrelated
callback invocation must:

- create no session;
- perform no new code exchange;
- perform no callback-directed navigation;
- return `INVALID_CALLBACK`;
- clear the callback parameters from the URL;
- remove the intended-return state associated with the rejected attempt; and
- produce the Security event required for `INVALID_CALLBACK`.

#### Correlation-record lifecycle

The correlation record is Auth-owned and scoped to one callback flow. It has two
successive states, named here as contract vocabulary rather than as an
implementation representation:

| Lifecycle state | Created | Meaning |
|---|---|---|
| `PENDING_ATTEMPT_CORRELATION` | When `beginSignIn` starts a sign-in attempt. | An attempt exists and has not yet reached a completed callback outcome. |
| `COMPLETED_CALLBACK_CORRELATION` | On successful first callback processing, by transition or replacement of the pending state. | That attempt's callback flow reached a completed outcome that may be reused by a correlated duplicate invocation. |

A completed record proves exactly four things and nothing more:

1. the originating sign-in attempt;
2. the callback flow;
3. the completed callback outcome; and
4. whether that outcome may be reused for a correlated duplicate invocation.

It is not a session, not a credential, and not authorization. It never carries an
authorization code, a token, or a PKCE verifier.

The completed record must remain available for a **bounded post-completion
correlation window**, so that an immediate duplicate invocation and a page reload
occurring after successful callback processing can both be correlated to that
completed outcome without performing another code exchange and without creating
another session. A successful callback therefore does **not** remove the
correlation evidence at the moment it completes; removing it immediately would
make the required post-success duplicate correlation impossible.

The record must not remain valid indefinitely. Once its bounded post-completion
window expires, or the record is otherwise removed, a later callback invocation
is no longer correlated: it returns `INVALID_CALLBACK`, performs no exchange, and
performs no callback-directed navigation.

Failed, abandoned, malformed, expired and terminally rejected flows must leave no
reusable successful-callback correlation evidence at all. Only a callback flow
that actually completed successfully may produce a `COMPLETED_CALLBACK_CORRELATION`
record, and a rejected attempt must never be able to manufacture one.

The exact storage mechanism, integrity mechanism, record representation,
retention duration and cleanup implementation are
`PENDING_A2_SECURITY_ACCEPTANCE` under `AUTH-DEP-011` and are not invented by
this draft. No concrete duration and no concrete Security mechanism is stated
here. Where correlation cannot be proven, the callback attempt fails closed; this
never weakens the single-use authorization-code rule or the replay-resistance
requirement, both of which continue to apply independently.

#### Callback-attempt failure versus session validity

A rejected callback attempt and an independently established session are two
separate facts, and this contract represents them separately. `INVALID_CALLBACK`
describes the outcome of the callback attempt. It is not, by itself, evidence
that the browser's existing session is invalid.

Every `INVALID_CALLBACK` outcome, without exception, creates no new session,
performs no code exchange, performs no callback-directed navigation, clears the
callback parameters, removes the intended-return state of the rejected attempt,
and emits the required Security event. The resulting **session** state is then
determined by the pre-existing session alone:

| Pre-existing session at the moment of rejection | Resulting session state | Required behavior |
|---|---|---|
| None, or none independently established before the rejected callback | `TERMINAL_SESSION_ERROR`, presenting as `UNAUTHENTICATED` | Reauthentication is required. |
| Independently established before the rejected callback and still known-valid | Preserved as `AUTHENTICATED` | The callback attempt fails, no callback success is reported, no callback-directed destination is used, and the UI presents a safe callback-error outcome or safe route recovery. FastAPI authorization remains authoritative for anything that session is used for. |
| Present but of unknown or unprovable validity | `TERMINAL_SESSION_ERROR` | Fail closed: protected content is removed and protected requests are prohibited, unless the session is later independently proven valid through an authorized session-restoration path. |

An existing session remains insufficient callback correlation in every one of
these rows. Preserving a known-valid session after a rejected callback is not the
same as resolving the callback with it: the callback must never use the existing
session as evidence that callback processing succeeded, and must never report
success, navigate to a callback-directed destination, or consume a return state
on the strength of it.

A malformed, unrelated or replayed callback must never revoke, sign out, or
otherwise invalidate a separately valid provider session merely because the
callback itself was invalid. Session invalidation requires an independent
session-validity failure, which is classified under its own error code.

Callback cleanup is mandatory. Authorization codes and tokens must never be
placed in durable UI state, must never remain in the URL, query string, or
fragment after callback processing, and must never appear in logs, error text,
analytics, or tracing metadata. Browser history must not retain a URL
containing an authorization code where the framework permits replacing it.

## `AUTH-002` session model

The session is provider-backed. This contract defines no second identity
system, no application session token, and no duplicate session store. Supabase
Auth is the canonical session source; FastAPI remains authoritative for
protected Backend authorization.

| State | Entry condition | Permitted UI | Prohibited UI | Backend requests | Recovery |
|---|---|---|---|---|---|
| `INITIALIZING` | Application start or hydration before the session is known. | Neutral loading affordance. | Rendering protected content; rendering a signed-in identity; asserting either authenticated or unauthenticated. | `NO` | Resolves to `AUTHENTICATED` or `UNAUTHENTICATED`. |
| `UNAUTHENTICATED` | No session, or session cleared. | Public surfaces, sign-in control. | Protected content; stale protected content; protected requests. | `NO` | User initiates sign-in. |
| `SIGN_IN_PENDING` | Sign-in initiated, provider redirect pending or in flight. | Pending affordance; cancel affordance. | Second concurrent initiation; protected content. | `NO` | Provider redirect, cancellation, or failure. |
| `CALLBACK_PROCESSING` | Callback route entered with provider result. | Loading UX; accessible progress announcement. | Treating this state as authenticated; rendering protected content; navigating on provider-supplied data. | `NO` | Success, or a classified failure. |
| `AUTHENTICATED` | A valid session is established and current. | Protected content; protected requests. | Treating UI belief as authorization; suppressing Backend denial. | `YES` | Refresh, sign-out, or expiry. |
| `REFRESH_PENDING` / mode `PROVEN_CREDENTIAL` | A refresh is in flight **while** the current access token and session remain known-valid, typically proactive refresh ahead of expiry. | Existing protected content may remain visible; user interaction permitted. | Sending a protected request with a token known to be expired; beginning any new privileged effect using an expired token; starting an unbounded retry loop. | `DEFERRED` — new protected requests wait for the refresh outcome. | `AUTHENTICATED` or `TERMINAL_SESSION_ERROR`. |
| `REFRESH_PENDING` / mode `UNPROVEN_CREDENTIAL` | A refresh is in flight because the access token is expired, Backend returned `401`, session validity is unknown, or the current credential cannot be proven usable. | Neutral pending affordance only. | Any protected content; any protected interaction; any protected request; any privileged effect. | `NO` — protected requests are prohibited, not merely deferred. | `AUTHENTICATED` or `TERMINAL_SESSION_ERROR`. |
| `SIGN_OUT_PENDING` | Sign-out requested. | Pending affordance. | New protected requests; new protected content. | `NO` | `UNAUTHENTICATED`. |
| `RECOVERABLE_ERROR` | A classified failure that a retry or a fresh attempt may resolve without reauthentication. | Safe error message; retry affordance. | Rendering protected content; automatic unbounded retry. | `NO` | User retry, or automatic bounded retry where the classification permits it. |
| `TERMINAL_SESSION_ERROR` | Session validity is lost or unknown and cannot be resolved without reauthentication. | Safe error message; sign-in affordance. | Any protected content; any protected request; any automatic retry. | `NO` | Reauthentication only. |

There remain nine session states. `REFRESH_PENDING` is one state carrying two
mutually exclusive, explicitly determined modes; it is never a single
undifferentiated condition, and a consumer must never treat the two modes as
interchangeable.

Binding session rules:

1. `INITIALIZING`, `SIGN_IN_PENDING`, `CALLBACK_PROCESSING`, and
   `REFRESH_PENDING` are loading states. A loading state is never
   authenticated, in either `REFRESH_PENDING` mode.
2. Stale UI state is never authorization. On entry to `UNAUTHENTICATED`,
   `SIGN_OUT_PENDING`, `TERMINAL_SESSION_ERROR`, or `REFRESH_PENDING` mode
   `UNPROVEN_CREDENTIAL`, previously rendered protected content must be removed
   from the view, not merely overlaid or disabled.
3. When session validity is uncertain, the session fails closed to
   `TERMINAL_SESSION_ERROR`. Uncertainty is never resolved in favor of access,
   and uncertainty must never preserve existing access.
4. A UI session state is a UX signal. It never substitutes for a FastAPI
   authorization decision, and a Backend denial always outranks it.
5. The `REFRESH_PENDING` mode is determined at entry, not inferred afterwards.
   Mode `PROVEN_CREDENTIAL` requires that both the current access token and the
   session are known-valid at the moment refresh begins. Every other entry
   condition — expired access token, Backend `401`, unknown session validity, or
   a credential that cannot be proven usable — is mode `UNPROVEN_CREDENTIAL`.
6. In mode `PROVEN_CREDENTIAL`, existing protected content may remain visible
   and new protected Backend requests wait for the refresh outcome. No new
   privileged effect may begin using an expired token.
7. In mode `UNPROVEN_CREDENTIAL`, protected content is removed or hidden,
   protected interactions are disabled, protected Backend requests are
   prohibited, and the session fails closed pending the refresh outcome.
8. A refresh that begins in mode `PROVEN_CREDENTIAL` and subsequently loses
   proof of validity — for example on an observed `401`, an observed session
   change, or an expiry crossed while in flight — transitions to mode
   `UNPROVEN_CREDENTIAL` immediately and applies rule 7 from that moment. The
   transition is one-way: mode never relaxes back to `PROVEN_CREDENTIAL` within
   the same refresh.
9. A failed callback attempt and a failed session are separate transitions. An
   `INVALID_CALLBACK` outcome always terminates the callback attempt, but it
   moves the session to `TERMINAL_SESSION_ERROR` only when no independently
   established, known-valid session existed before that callback. Where such a
   session did exist and remains known-valid, it is preserved and the session
   stays `AUTHENTICATED` while the callback attempt fails. Where its validity is
   unknown or unprovable, rule 3 applies and the session fails closed to
   `TERMINAL_SESSION_ERROR`.
10. Rule 9 never relaxes correlation. A preserved session is never treated as
    proof that the callback succeeded: no callback success is reported, no
    callback-directed destination is used, and no return state is consumed on
    the strength of an existing session.

## `AUTH-002` token-custody decision

This decision was determined from current primary Supabase documentation, not
from remembered SDK behavior. The sources inspected are recorded in
`docs/components/auth/LATEST_AGENT3_HANDOFF.md`.

Determination: the accepted storage constraints **can** be satisfied by the
current official Supabase integration model, provided the integration package
and client factories below are mandated rather than assumed.

| Item | Decision |
|---|---|
| Required integration model | The official server-side rendering integration: `@supabase/ssr` together with `@supabase/supabase-js`. |
| Browser client factory | `createBrowserClient` from `@supabase/ssr`. |
| Server client factory | `createServerClient` from `@supabase/ssr`. |
| Canonical session source | The provider integration's cookie-backed session store. There is no second store. |
| Session storage medium | Cookies, named by the provider integration as `sb-<project_ref>-auth-token` by default. |
| Flow type | PKCE. The `@supabase/ssr` clients are initiated to use the PKCE flow by default; the contract requires PKCE regardless of default. |
| Browser-readable versus server-only | Browser-readable. The official integration requires the browser side to read the session, including the refresh token, to maintain the browser session. |
| `HttpOnly` | **Not achievable** for the browser-readable session cookie under the accepted architecture, and **not required** by any accepted constraint. Supabase's official guidance states `HttpOnly` cookies are not necessary and that the browser side needs access to the refresh token. Final cookie posture is an unresolved `A2-SECURITY` decision recorded as `AUTH-DEP-011`. |
| `Secure` | `REQUIRED` on every non-local environment. Deployment-owned registration. |
| `SameSite` | `Lax` is the documented provider recommendation and the Auth-proposed default, because the callback is reached by a top-level cross-site redirect. Final value is an `A2-SECURITY` decision under `AUTH-DEP-011`. |
| Refresh-token custody | The provider integration's cookie store only. Never `localStorage`, never `sessionStorage`, never a custom store, never forwarded to FastAPI. |
| Access-token availability to the API transport layer | Available. The API transport layer obtains it through the Auth-owned adapter immediately before a request, and never caches a copy. |
| Page reload and session restoration | The cookie-backed session survives reload. Because Server Components cannot write cookies, refreshed tokens must be persisted by the framework proxy/middleware layer the official integration requires. |
| Cross-tab behavior | Provider-managed **notification** only. The integration emits session-change events consumed through the Auth-owned subscription operation. Those events are synchronization signals, not proof that refresh exchanges were serialized across tabs. Cross-tab custody is a shared cookie store that separate browsing contexts may read and write concurrently. |
| Cross-context refresh serialization | **Not guaranteed.** No claim is made that provider behavior serializes refresh across separate browser tabs, parallel server requests, or separate runtime instances. See the `AUTH-002` refresh contract. |
| Session expiry | Provider-managed refresh ahead of expiry; a refresh token is exchangeable once, within a short provider-side reuse interval. |
| Server/client boundary | Browser code uses the browser client. Server Components, Server Actions, and Route Handlers use the server client. Neither may construct a differently configured client. |
| Explicit SDK persistence configuration | `REQUIRED` to be explicit. The contract does not rely on a default. |

Prohibited storage mechanisms, restating and not weakening the existing
constraints:

- no access token in `localStorage`;
- no refresh token in `localStorage`;
- no access token in `sessionStorage`;
- no refresh token in `sessionStorage`;
- no duplicate custom token store, in-memory cache, React state, context value,
  IndexedDB record, service-worker cache, or Redux/Zustand slice holding a
  token copy;
- no refresh token forwarded to FastAPI;
- no token in a URL, query parameter, or fragment after callback processing;
- no token, `Authorization` header, or session secret in logs, errors,
  analytics, or tracing metadata.

Binding implementation prohibition: browser code must not initialize a Supabase
client with `createClient` from `@supabase/supabase-js`. In a browser that
client persists the session to `localStorage` by default, which violates the
first prohibited-storage rule above. The `localStorage` prohibition is not
waived because a provider SDK defaults to it; the defaulting factory is
prohibited instead.

No custom storage mechanism is invented by this contract. No accepted storage
constraint is weakened by it.

## `AUTH-002` refresh contract

| Item | Decision |
|---|---|
| Refresh initiation ownership | `A2-AUTH` semantics; the provider integration performs the exchange. |
| Refresh model | Provider-managed ahead-of-expiry refresh is primary. Application-triggered refresh is permitted only through the Auth-owned adapter operation and only in the bounded cases below. |
| Refresh mode determination | Every refresh begins in exactly one `REFRESH_PENDING` mode, determined at entry. Mode `PROVEN_CREDENTIAL` requires the current access token and session to be known-valid when refresh begins. Mode `UNPROVEN_CREDENTIAL` covers an expired access token, a Backend `401`, unknown session validity, and any credential that cannot be proven usable. |
| Behavior in mode `PROVEN_CREDENTIAL` | Existing protected content may remain visible. New protected Backend requests wait for the refresh outcome. No new privileged effect begins using an expired token. |
| Behavior in mode `UNPROVEN_CREDENTIAL` | Protected content is removed or hidden, protected interactions are disabled, and protected Backend requests are prohibited rather than queued. The session fails closed pending the outcome. |
| Mode degradation | A `PROVEN_CREDENTIAL` refresh that loses proof of validity while in flight degrades immediately and irreversibly to `UNPROVEN_CREDENTIAL`. Mode never relaxes back within the same refresh. |
| Synchronization scope | Single-flight **within one Auth adapter/client instance or one browsing context** only. Concurrent refresh requests inside that scope resolve to one in-flight exchange, and all callers observe its single outcome. |
| Cross-context serialization | **Not guaranteed and not claimed.** Nothing in the accepted provider design serializes refresh across separate browser tabs, parallel server requests, or separate runtime instances. No Auth record may state that provider behavior guarantees global single-flight refresh. |
| Concurrent refresh within one context | Never produces two independent exchanges from that context. A refresh token is exchangeable once within a short provider-side reuse interval, so uncoordinated concurrency risks invalidating the session. |
| Concurrent refresh across contexts | Possible, and must be tolerated. The observable outcomes include a stale cookie, a temporarily null session, and one successful refresh paired with one rejected refresh. Every such race fails closed, tolerates provider cookie synchronization, and never restores stale authenticated state. |
| Cross-context race recovery | At most **one** bounded retry, permitted only after a newer valid session is actually observed — for example through the Auth-owned subscription or a re-read of the cookie-backed session. A retry is never issued speculatively, and no automatic refresh loop may be created under any race. |
| Synchronization signals | `onAuthStateChange` events and any `BroadcastChannel` messages are synchronization signals only. They are not proof that all refresh exchanges were serialized, and must never be treated as such. |
| Stale requests during refresh | In mode `PROVEN_CREDENTIAL`, protected requests issued while `REFRESH_PENDING` wait for the outcome. In mode `UNPROVEN_CREDENTIAL` they are prohibited. In neither mode may a request be sent with a token already known to be expired. |
| Retry boundary | At most one refresh attempt per protected request failure. A refreshed token justifies at most one retry of that request. |
| Loop prevention | If a retried request fails again with `401`, no further refresh or retry is attempted for that request. The session moves to `TERMINAL_SESSION_ERROR`. |
| Backend `401` handling | A `401` means the credential was missing, invalid, or unusable at FastAPI. It does not by itself prove the session is refreshable. It always enters mode `UNPROVEN_CREDENTIAL`. Refresh is attempted at most once; if refresh fails or the retry fails, the session fails closed. |
| Simultaneous Backend `401` responses | Coalesced into the single in-flight refresh **within the same context**. Each request is retried at most once after that single outcome. Coalescing across contexts is not claimed. |
| Refresh failure | `REFRESH_FAILED`. Session becomes `TERMINAL_SESSION_ERROR`. Reauthentication required. |
| Expired session | `SESSION_EXPIRED`. Session becomes `TERMINAL_SESSION_ERROR`. Reauthentication required. |
| Uncertain outcome | Fail closed to `TERMINAL_SESSION_ERROR`. |
| Cross-tab session change | Observed through the Auth-owned subscription. A tab that learns the session ended must leave `AUTHENTICATED` and remove protected content. A tab that observes a session change it did not initiate must not assume its own in-flight exchange was serialized against it. |
| Refresh-token forwarding | `PROHIBITED`. A refresh token is never sent to FastAPI in any header, cookie, query parameter, or body. |

A Backend `401` must never create an unbounded refresh-and-retry cycle. UI
belief that a session exists never overrides Backend denial.

Uncertainty must never preserve access. Where the refresh outcome, the mode, or
the effect of a concurrent cross-context exchange cannot be determined, the
session fails closed rather than continuing to render or authorize protected
work.

## `AUTH-002` sign-out contract

| Item | Decision |
|---|---|
| Request | A2-UI presents the control and calls the Auth-owned sign-out operation. |
| Local invalidation | Mandatory and first-class. Local authenticated state is cleared whether or not the remote call succeeds. |
| Provider-session scope | Auth-proposed default is current-session scope, not all devices. The official integration defaults to a global scope that signs the user out of every device, so the scope must be passed explicitly rather than defaulted. Final scope is an `A2-SECURITY` decision under `AUTH-DEP-011`. |
| Outstanding requests | In-flight protected requests are abandoned. Their responses must not restore protected content or authenticated state. |
| Route transition | Navigate to the default post-sign-out destination under the `Safe redirect contract`. |
| Cross-tab synchronization | Other tabs observe the session change through the Auth-owned subscription and leave `AUTHENTICATED`. Delivery is a synchronization signal, not a serialization guarantee: a tab that has a refresh in flight when sign-out occurs elsewhere must fail closed rather than let that refresh restore authenticated state. |
| Remote failure | `SIGN_OUT_FAILED`. Local authenticated UI state is still cleared and the user is still treated as signed out in this browser. |
| Stale content | Protected content is removed on entry to `SIGN_OUT_PENDING` and must not reappear. |
| During refresh | Sign-out wins. The refresh outcome must not restore `AUTHENTICATED`. |
| During callback processing | Sign-out wins. A late callback success must not establish a session after sign-out was requested. |
| Repeated sign-out | Idempotent. A second request from `UNAUTHENTICATED` is a no-op success. |
| Completion classification | Sign-out is complete for UI purposes once local authenticated state is cleared, independently of the remote result. |

Sign-out does not revoke already-issued Backend access tokens. The accepted
provider and Backend design proves no such revocation, so no record may claim
it. A previously issued access token may remain accepted by FastAPI until it
expires. Reducing that window is an unresolved joint `A2-SECURITY` and
`A2-BACKEND` decision recorded as `AUTH-DEP-011` and `AUTH-DEP-014`.

The UI fails closed after local sign-out state is established.

## `AUTH-002` safe redirect contract

| Item | Decision |
|---|---|
| Default post-sign-in destination | An Auth-approved default application path, resolved by Auth-owned code. The concrete path is `A2-UI`-proposed and Auth-approved; it is not user-controlled. |
| Default post-sign-out destination | The public application root. |
| Allowed return-path format | A single relative path beginning with exactly one `/`, optionally followed by a query string and fragment. |
| Same-origin requirement | Mandatory. The final navigation target is always same-origin by construction, because only a relative path is ever accepted. |
| Allowlist behavior | Callback destinations use an exact-match allowlist. Return paths use the format rules here, the disallowed-route rule below, **and** the intended-return state binding rules in the sign-in initiation section. |
| Format versus binding | Two independent gates. Format validation decides whether a path is shaped safely; binding validation decides whether this flow is entitled to use it at all. A candidate must pass both. Passing format alone never authorizes navigation. |
| Provider OAuth `state` | Not a return-path container. It is provider-integration-owned and is never read by Auth as an application destination. |

A candidate return path is rejected when it:

- begins with `//` or `/\`, which are protocol-relative forms;
- contains a scheme, including `http:`, `https:`, `javascript:`, `data:`,
  `file:`, or any `scheme:` prefix;
- is an absolute URL, whether same-origin or external;
- contains `@`, which enables user-info host confusion;
- contains a backslash, a control character, a newline, or a null byte;
- contains a percent-encoded or repeatedly encoded form that decodes into any
  of the above; validation is applied after a single decode, and any candidate
  still containing an encoded delimiter after that decode is rejected rather
  than decoded again;
- contains a nested redirect parameter whose value is itself a URL;
- is malformed under the platform URL parser;
- names an internal route that is not permitted as a post-sign-in destination,
  including `/auth/callback` itself.

| Return-state condition | Behavior |
|---|---|
| Absent | Use the default post-sign-in destination. |
| Expired | Use the default post-sign-in destination. |
| Tampered | Reject and use the default post-sign-in destination. Security-relevant. |
| Replayed — already consumed by an earlier callback | Reject and use the default post-sign-in destination. Security-relevant. |
| Unbound — not correlated to the sign-in attempt being completed | Reject and use the default post-sign-in destination. Security-relevant. |
| Syntactically safe but unbound, expired, replayed or tampered | Rejected. A safe-looking relative path is never accepted on syntax alone. |
| Disallowed internal route | Reject and use the default post-sign-in destination. |
| Any rejection | Fallback is always the default destination. A rejected return path never becomes navigation. |

Provider-returned data never directly controls final navigation. Every
destination passes Auth-owned validation first. This design prevents open
redirects.

The intended-return state is removed after callback success and after callback
failure alike, so a return path can never outlive the single sign-in attempt it
was created for.

## `AUTH-002` Auth-owned UI adapter interface

This is the minimum semantic interface a future, separately authorized `UI-004`
may consume. The names below are Auth-owned semantic names chosen after
checking the supported official integration; they are deliberately not provider
method names, so that the adapter can wrap the official integration without
leaking provider specifics into UI code. Defining this interface authorizes no
implementation.

Rules applying to every operation: no operation returns a refresh token to UI;
no operation accepts or returns a provider secret; no operation logs a token,
an `Authorization` header, an authorization code, or a PKCE verifier; and no
caller may cache a returned access token beyond the single request it is
attached to.

### `beginSignIn`

- Purpose: start the provider-mediated GitHub sign-in.
- Owner: `A2-AUTH`.
- Input: an optional intended return path, as a candidate only.
- Output: none on success; the browser is redirected. A classified error
  otherwise.
- Preconditions: `UNAUTHENTICATED` or `RECOVERABLE_ERROR`.
- Effects: `SIGN_IN_PENDING`. Auth creates the sign-in attempt's correlation
  state, initially `PENDING_ATTEMPT_CORRELATION`, and, when a candidate return
  path is supplied and passes format validation, an Auth-owned intended-return
  state bound to that one attempt, with a defined expiry and single-use
  semantics.
- Errors: `CONFIGURATION_UNAVAILABLE`, `TEMPORARY_PROVIDER_FAILURE`.
- Cancellation: the user may abandon the flow at the provider. An abandoned
  attempt's return state expires or is removed; it is never reusable by a later
  attempt.
- Concurrency: at most one in-flight initiation per browsing context.
- Retry: safe after a returned error; never automatic. A retry is a new sign-in
  attempt with a new correlation record and a new return state.
- Return-state handling: the caller's candidate path is never stored verbatim
  as an authorization to navigate. It is bound, expiry-limited and single-use;
  the storage and integrity mechanism is `PENDING_A2_SECURITY_ACCEPTANCE`. The
  provider OAuth `state` parameter is never used to carry it.
- Prohibited caller behavior: constructing a provider URL, supplying a callback
  destination, supplying an absolute return URL, supplying or reading the
  provider OAuth `state`, creating or persisting its own return state, calling
  from `CALLBACK_PROCESSING`.

### `processCallback`

- Purpose: interpret the provider result and establish the session.
- Owner: `A2-AUTH`.
- Input: the callback request context.
- Output: a session snapshot and a validated navigation destination, or a
  classified error.
- Preconditions: `CALLBACK_PROCESSING`.
- Effects: on success, `AUTHENTICATED`, and the attempt's
  `PENDING_ATTEMPT_CORRELATION` state becomes a `COMPLETED_CALLBACK_CORRELATION`
  record that remains available for its bounded post-completion correlation
  window. On failure, the callback attempt terminates: callback parameters are
  cleared and the intended-return state of the rejected attempt is removed. The
  resulting session state is `RECOVERABLE_ERROR` or `TERMINAL_SESSION_ERROR`
  where no independently established, known-valid session pre-existed the
  callback; where such a session did pre-exist and remains known-valid, it is
  preserved as `AUTHENTICATED` and only the callback attempt fails; where its
  validity is unknown, the session fails closed to `TERMINAL_SESSION_ERROR`.
- Errors: `INVALID_CALLBACK`, `STATE_VALIDATION_FAILED`,
  `PKCE_VALIDATION_FAILED`, `SESSION_EXCHANGE_FAILED`, `PROVIDER_DENIED`,
  `USER_CANCELLED`, `TEMPORARY_PROVIDER_FAILURE`.
- Cancellation: not cancellable once the code exchange is in flight.
- Concurrency: single-flight per callback flow. A duplicate invocation resolves
  to the existing outcome **only** when correlation to the same sign-in
  attempt, the same callback flow, and the same completed outcome is verified
  against a `COMPLETED_CALLBACK_CORRELATION` record still inside its bounded
  post-completion window; it never performs a second exchange. An uncorrelated
  invocation fails closed with `INVALID_CALLBACK`.
- Correlation: required, and independent of session existence. An existing
  valid session is not correlation and never justifies resolving an invocation.
  After a successful callback, a page reload may resolve to the established
  session only through the completed correlation record for that exact flow,
  while that record remains inside its bounded post-completion window;
  afterwards, and in every uncorrelated case, the invocation fails closed.
- Session separation: an `INVALID_CALLBACK` result reports the failure of the
  callback attempt, never the invalidation of an independently established
  session. `processCallback` must not revoke or sign out a separately valid
  provider session because the callback was invalid, and must not report success
  because one exists.
- Return-state handling: an intended-return state is honored only when bound to
  this sign-in attempt, unexpired, unconsumed, integrity-intact and
  format-valid. Any other return state falls back to the default post-sign-in
  destination without affecting the session outcome. The return state is
  removed on success and on failure alike.
- Retry: `PROHIBITED` on the same authorization code. The code is single-use.
- Prohibited caller behavior: reading raw provider parameters, navigating to a
  provider-supplied destination, treating an existing session as proof that a
  callback completed, rendering protected content before success, retrying the
  exchange.

### `getSessionSnapshot`

- Purpose: read the current session state for rendering.
- Owner: `A2-AUTH`.
- Input: none.
- Output: a snapshot carrying the session state, a stable non-secret user
  reference, and nothing else. No access token, no refresh token, no raw
  provider payload, no JWT claims not explicitly approved for disclosure.
- Preconditions: none.
- Effects: none. This operation is read-only and must not trigger a refresh.
- Errors: none; an unknown session resolves to `INITIALIZING` or
  `UNAUTHENTICATED`.
- Concurrency: safe.
- Prohibited caller behavior: treating a snapshot as authorization, persisting
  a snapshot as a credential, using a snapshot to suppress a Backend denial.

### `subscribeToSessionChanges`

- Purpose: observe session transitions, including cross-tab changes.
- Owner: `A2-AUTH`.
- Input: a callback receiving a session snapshot.
- Output: an unsubscribe handle.
- Preconditions: none.
- Effects: none directly; consumers react to state changes.
- Errors: none.
- Concurrency: multiple subscribers permitted; each receives the same
  snapshots.
- Prohibited caller behavior: failing to unsubscribe on unmount, performing
  privileged work inside the callback, assuming an event ordering guarantee
  beyond the delivered snapshots.

### `getAccessTokenForApiRequest`

- Purpose: supply an access token for exactly one protected FastAPI request.
- Owner: `A2-AUTH`.
- Input: none.
- Output: an access token valid for immediate single use, or a classified
  error.
- Preconditions: `AUTHENTICATED`, or `REFRESH_PENDING` in mode
  `PROVEN_CREDENTIAL`. Calling in mode `UNPROVEN_CREDENTIAL` is prohibited,
  because protected requests are prohibited in that mode.
- Effects: may enter `REFRESH_PENDING` if the token is near expiry, in mode
  `PROVEN_CREDENTIAL`; enters mode `UNPROVEN_CREDENTIAL` if the token is
  already expired or session validity cannot be proven. Joins the single
  in-flight refresh in this context rather than starting a second.
- Errors: `SESSION_EXPIRED`, `REFRESH_FAILED`, `TEMPORARY_PROVIDER_FAILURE`.
- Cancellation: the caller may abandon the request; the session outcome stands.
- Concurrency: coalesced through single-flight refresh **within this adapter
  instance or browsing context only**. Coalescing across tabs, parallel server
  requests or separate runtime instances is not provided and must not be
  assumed.
- Retry: at most one retry per request after one successful refresh.
- Token exposure: the returned value is used only as
  `Authorization: Bearer <access-token>` for one request. It is never stored,
  never placed in a URL, never logged, and never rendered.
- Prohibited caller behavior: caching the token, reusing it after a `401`
  without the bounded refresh path, sending it to any origin other than the
  approved FastAPI origin, sending a refresh token.

### `refreshSession`

- Purpose: request a bounded, explicit refresh.
- Owner: `A2-AUTH`.
- Input: none.
- Output: a session snapshot or a classified error.
- Preconditions: `AUTHENTICATED` or `REFRESH_PENDING`, in either mode.
- Effects: `AUTHENTICATED` on success; `TERMINAL_SESSION_ERROR` on failure. The
  entry condition determines the `REFRESH_PENDING` mode, and mode
  `UNPROVEN_CREDENTIAL` removes protected content for the duration.
- Errors: `REFRESH_FAILED`, `SESSION_EXPIRED`, `TEMPORARY_PROVIDER_FAILURE`.
- Concurrency: single-flight within one adapter instance or browsing context;
  concurrent callers in that scope share one outcome. Cross-tab, cross-request
  and cross-instance serialization is not guaranteed; a losing cross-context
  exchange fails closed and may be retried at most once, and only after a newer
  valid session has actually been observed.
- Retry: bounded. No automatic loop, including under a cross-context race.
- Prohibited caller behavior: calling on a timer, calling in a render path,
  calling to "check" whether the user is signed in, retrying after
  `REFRESH_FAILED`.

### `signOut`

- Purpose: end the session in this browser.
- Owner: `A2-AUTH`.
- Input: none.
- Output: a completion result and the default post-sign-out destination.
- Preconditions: any state.
- Effects: `SIGN_OUT_PENDING`, then `UNAUTHENTICATED`.
- Errors: `SIGN_OUT_FAILED`, which still clears local authenticated state.
- Concurrency: idempotent; repeated calls coalesce.
- Retry: safe.
- Prohibited caller behavior: rendering protected content after the call,
  treating `SIGN_OUT_FAILED` as still-signed-in, claiming that issued Backend
  access tokens were revoked.

## `AUTH-002` error and UX vocabulary

`R` marks whether retry is safe. `Re-auth` marks whether reauthentication is
required. `Detail` marks whether the user may see failure detail beyond the
safe category. `Sec log` marks whether a Security event is required. `Backend`
marks whether protected Backend requests remain prohibited.

| Code | Meaning | Owning boundary | R | Re-auth | Detail | Safe message category | Sec log | Resulting state | Backend | Recoverable |
|---|---|---|:-:|:-:|:-:|---|:-:|---|:-:|---|
| `USER_CANCELLED` | The user abandoned sign-in at the provider. | User | yes | no | yes | neutral, "sign-in was not completed" | no | `UNAUTHENTICATED` | prohibited | recoverable |
| `PROVIDER_DENIED` | The provider refused the authorization. | Provider | yes | yes | no | denial without cause | yes | `UNAUTHENTICATED` | prohibited | recoverable |
| `INVALID_CALLBACK` | Missing, malformed, expired, consumed, replayed, unrelated, or otherwise uncorrelated callback, including a duplicate invocation that cannot be correlated to the same sign-in attempt, callback flow and completed outcome, or whose completed correlation record is outside its bounded post-completion window. Classifies the callback attempt only. | `A2-AUTH` | no, restart sign-in instead for this attempt | only where no known-valid session is preserved | no | generic sign-in failure | yes | conditional: `TERMINAL_SESSION_ERROR` when no independently established, known-valid session pre-existed the callback, or when a pre-existing session's validity is unknown; otherwise the pre-existing known-valid session is preserved as `AUTHENTICATED` and only the callback attempt fails | prohibited while `TERMINAL_SESSION_ERROR`; unchanged for a preserved `AUTHENTICATED` session, which FastAPI remains authoritative over | terminal for the callback attempt |
| `STATE_VALIDATION_FAILED` | OAuth state did not verify. | `A2-AUTH` with `A2-SECURITY` | no | yes | no | generic sign-in failure | yes | `TERMINAL_SESSION_ERROR` | prohibited | terminal |
| `PKCE_VALIDATION_FAILED` | PKCE proof missing or invalid, including a cross-device callback. | `A2-AUTH` with `A2-SECURITY` | no | yes | no | generic sign-in failure | yes | `TERMINAL_SESSION_ERROR` | prohibited | terminal |
| `SESSION_EXCHANGE_FAILED` | The code exchange failed for a non-transient reason. | `A2-AUTH` | no | yes | no | generic sign-in failure | yes | `TERMINAL_SESSION_ERROR` | prohibited | terminal |
| `SESSION_EXPIRED` | The session is no longer valid. | `A2-AUTH` | no | yes | yes | "your session ended, sign in again" | no | `TERMINAL_SESSION_ERROR` | prohibited | terminal |
| `REFRESH_FAILED` | Refresh did not produce a usable session. | `A2-AUTH` | no | yes | no | "your session ended, sign in again" | yes | `TERMINAL_SESSION_ERROR` | prohibited | terminal |
| `SIGN_OUT_FAILED` | Remote sign-out did not confirm. | `A2-AUTH` | yes | no | yes | "signed out on this device" | yes | `UNAUTHENTICATED` | prohibited | recoverable |
| `CONFIGURATION_UNAVAILABLE` | Required provider configuration is absent or unusable. | `A2-DEPLOYMENT` | no | no | no | "sign-in is unavailable" | yes | `RECOVERABLE_ERROR` | prohibited | recoverable |
| `TEMPORARY_PROVIDER_FAILURE` | A transient provider or network failure. | Provider | yes, bounded | no | no | "try again" | no | `RECOVERABLE_ERROR` | prohibited | recoverable |

These eleven classifications are the complete Auth-owned vocabulary for this
version. A consumer must not invent an Auth error class, and must not map an
unrecognized failure onto a more permissive class.

Every classification must redact: authorization codes, PKCE verifiers, access
tokens, refresh tokens, raw provider payloads, raw headers, cookie values, the
Supabase project reference, hostnames, secrets, stack traces, internal
identifiers not approved for disclosure, and any detail that distinguishes
which validation step failed beyond the class itself. `STATE_VALIDATION_FAILED`,
`PKCE_VALIDATION_FAILED`, `INVALID_CALLBACK`, and `SESSION_EXCHANGE_FAILED`
must present the same user-facing generic sign-in failure, so that the UI
creates no oracle distinguishing them.

## `AUTH-002` Backend boundary

Preserved and restated:

1. FastAPI authorization is authoritative.
2. UI route guards are UX and defense-in-depth only. They never grant access.
3. Protected FastAPI requests carry an access token only through
   `Authorization: Bearer <access-token>`.
4. Refresh tokens never reach FastAPI, in any header, cookie, query parameter,
   or body.
5. An absent or invalid credential produces unauthenticated behavior, never a
   partially trusted state.
6. The UI must handle Backend denial correctly even when it believed a session
   existed.
7. A Backend `401` does not by itself prove that refresh is safe or that the
   session is recoverable.
8. A Backend authorization decision is never replaced, cached, or pre-empted by
   frontend session state.

Not defined here, and left to `A2-BACKEND` with `A2-SECURITY`: the request
dependency implementation, the JWT library choice, the authenticated-principal
Python model, route middleware, the exact `403` versus concealed-`404` policy,
CORS implementation, API route behavior, the JWKS cache implementation, and the
Backend token-verification retry policy. These are recorded as consumer inputs
in `DEPENDENCY_REQUESTS.md` and remain unresolved.

## `AUTH-002` Security requirements

The following are required by this draft:

1. PKCE on every sign-in flow.
2. OAuth-state verification on every callback.
3. Exact-match callback registration and exact-match callback selection.
4. No open redirect; all navigation destinations pass Auth-owned validation.
5. No token in a URL fragment or query parameter after callback processing.
6. Callback replay resistance; a consumed authorization code never establishes
   a second session.
7. Single-use authorization-code semantics, honored rather than retried.
8. Callback-completion correlation: a prior successful callback outcome is
   reusable only when the invocation is verified to belong to the same sign-in
   attempt, the same callback flow, and the same completed outcome, evidenced by
   a `COMPLETED_CALLBACK_CORRELATION` record still inside its bounded
   post-completion correlation window. An existing session is never accepted as
   correlation. The record survives successful completion for that bounded
   window so that a duplicate invocation or a post-success reload can correlate,
   is never valid indefinitely, and is never producible by a failed, abandoned,
   malformed, expired or terminally rejected flow.
9. No authorization-code or token logging.
10. No raw `Authorization`-header logging.
11. No secret, project reference, or hostname in any user-facing error.
12. Fail-closed behavior whenever session validity is uncertain. Uncertainty
    never preserves existing access.
13. Session-fixation resistance: a session established by callback processing
    must be the session created by that exchange, and any pre-existing
    unauthenticated client state associated with the flow is discarded on
    completion.
14. Removal of stale authenticated state after sign-out or terminal failure.
15. Enforcement of the prohibited-storage list, including the prohibition on
    the `localStorage`-defaulting browser client factory.
16. Safe callback cleanup, including URL parameter removal and intended-return
    state removal on success and failure alike.
17. Actor-attributable Security failures for the classifications marked
    `Sec log` above, attributed under the existing actor vocabulary and using
    `UNAUTHENTICATED` where no canonical user is resolved.
18. Fail-closed refresh: a refresh entered because the token is expired, because
    Backend returned `401`, because session validity is unknown, or because the
    credential cannot be proven usable removes protected content, disables
    protected interactions and prohibits protected Backend requests for its
    duration.
19. No cross-context refresh overclaim: no record asserts that provider
    behavior guarantees global single-flight refresh across tabs, parallel
    server requests or runtime instances. Cross-context races fail closed, use
    at most one bounded retry after a newer valid session is observed, and never
    create an automatic refresh loop.
20. Intended-return state binding: the Dashboard return state is Auth-created,
    bound to one sign-in attempt, expiry-limited, single-use,
    integrity-protected or held in Auth-controlled same-origin state, removed
    after success and failure, and never accepted on syntactic safety alone.
    Provider OAuth `state` is not reused as a return-path container. The exact
    mechanism remains `PENDING_A2_SECURITY_ACCEPTANCE`.
21. Callback-attempt and session-validity separation: an `INVALID_CALLBACK`
    result never itself invalidates, revokes or signs out a session that was
    independently established before the rejected callback and remains
    known-valid, and never permits that session to be read as proof that the
    callback succeeded. A pre-existing session of unknown validity fails closed.

Deliberately **not** decided here, because they belong to `A2-SECURITY`: the
final cookie policy including `SameSite` and any `HttpOnly` position, the final
CSRF policy, retention periods, the Security-event schema, event severity, the
disclosure policy, key custody, production monitoring thresholds, the exact
storage and integrity mechanism for the intended-return state, and the required
strength, representation, retention duration and cleanup of the
callback-completion correlation record, including the length of its bounded
post-completion correlation window. Each is raised as an
explicit review question in `DEPENDENCY_REQUESTS.md` under `AUTH-DEP-011`. None
of them is recorded here as an accepted final Security decision.

## `AUTH-002` conceptual acceptance fixtures

These are conceptual contract fixtures. They are not runtime tests, and no
runtime test is created by this version. Every fixture below prohibits
disclosure of tokens, authorization codes, PKCE verifiers, and secrets, and
every failing fixture requires fail-closed behavior; both are restated only
where the fixture adds a specific obligation.

| # | Fixture | Initial state | Actor | Operation | Expected transitions | Permitted UI | Prohibited UI | Backend eligible | Classification | Attribution | Owner dependencies |
|---:|---|---|---|---|---|---|---|:-:|---|---|---|
| 1 | Successful sign-in | `UNAUTHENTICATED` | `HUMAN_USER` | `beginSignIn` then `processCallback` | `SIGN_IN_PENDING` → `CALLBACK_PROCESSING` → `AUTHENTICATED` | protected content after success; navigation to the bound, unexpired, single-use return destination, else the default | protected content before success; navigating on a return state that is unbound, expired or already consumed; retaining the return state after completion | yes, after `AUTHENTICATED` | success | canonical user | Deployment provisioning; intended-return state mechanism pending `A2-SECURITY` |
| 2 | User cancellation | `SIGN_IN_PENDING` | `HUMAN_USER` | abandon at provider | → `UNAUTHENTICATED` | neutral message | error implying system fault | no | `USER_CANCELLED` | `UNAUTHENTICATED` | none |
| 3 | Provider denial | `SIGN_IN_PENDING` | Provider | denial returned | → `UNAUTHENTICATED` | denial without cause | naming the provider reason | no | `PROVIDER_DENIED` | `UNAUTHENTICATED` | Security event shape |
| 4 | Valid callback | `CALLBACK_PROCESSING` | `A2-AUTH` | `processCallback` | → `AUTHENTICATED`; the attempt's `PENDING_ATTEMPT_CORRELATION` state becomes a `COMPLETED_CALLBACK_CORRELATION` record for this exact flow, which remains available for its bounded post-completion window; the return state is consumed and removed | success UX, then validated navigation | leaving the code in the URL; treating a session as proof of completion; retaining a consumed return state; discarding the completed correlation record at the instant of success | yes | success | canonical user | correlation-record mechanism, representation and window length pending `A2-SECURITY` |
| 4a | Duplicate callback invocation, correlated, inside the post-completion window | `AUTHENTICATED` after fixture 4, same flow re-entered | `HUMAN_USER` | `processCallback` | no state change; the completed correlation record is matched and the previously completed outcome is reused | the already-established session | a second code exchange; a second session; reporting a new sign-in; requiring a re-exchange because the record was removed at completion | yes | success | canonical user | correlation-record mechanism, representation and window length pending `A2-SECURITY` |
| 4b | Duplicate or unrelated callback invocation, uncorrelated, with an independently established, known-valid session present | `AUTHENTICATED` | Attacker or unrelated navigation | `processCallback` | callback attempt fails; no session created; no exchange; callback parameters cleared; rejected attempt's return state removed; the pre-existing known-valid session is preserved and remains `AUTHENTICATED` | safe callback-error outcome or safe route recovery | resolving the invocation because a session exists; any code exchange; any callback-directed navigation; reporting callback success; revoking or signing out the pre-existing session because the callback was invalid | unchanged for the preserved session, with FastAPI authoritative | `INVALID_CALLBACK` | canonical user of the preserved session | Security event shape |
| 4b-i | Uncorrelated callback with no independently valid pre-existing session, or one whose validity cannot be proven | `UNAUTHENTICATED`, or a session of unknown validity | Attacker or unrelated navigation | `processCallback` | callback attempt fails; no session created; no exchange; callback parameters cleared; → `TERMINAL_SESSION_ERROR` | generic sign-in failure | any protected content; treating unknown validity as valid | no | `INVALID_CALLBACK` | `UNAUTHENTICATED` | Security event shape |
| 4c | Reload after successful callback processing | `AUTHENTICATED`, callback URL reloaded | `HUMAN_USER` | `processCallback` | resolves to the established session while the `COMPLETED_CALLBACK_CORRELATION` record for that exact flow is still inside its bounded post-completion window; once that window has expired or the record is gone, the callback attempt fails with no exchange and no callback-directed navigation, and the session outcome follows fixtures 4b and 4b-i | protected content only on matched correlation | assuming completion from session existence alone; re-exchanging the consumed code; treating the expired window as authorization to retry | conditional | success while correlated, otherwise `INVALID_CALLBACK` | canonical user, or `UNAUTHENTICATED` where no valid session is preserved | correlation-record mechanism, representation and window length pending `A2-SECURITY` |
| 5 | Invalid state | `CALLBACK_PROCESSING` | Attacker or corruption | `processCallback` | → `TERMINAL_SESSION_ERROR` | generic sign-in failure | distinguishing this from fixture 6 | no | `STATE_VALIDATION_FAILED` | `UNAUTHENTICATED` | Security event shape |
| 6 | Invalid or missing PKCE proof | `CALLBACK_PROCESSING` | Attacker, or a different device | `processCallback` | → `TERMINAL_SESSION_ERROR` | generic sign-in failure | distinguishing this from fixture 5 | no | `PKCE_VALIDATION_FAILED` | `UNAUTHENTICATED` | Security event shape |
| 7 | Callback replay | `AUTHENTICATED` or `UNAUTHENTICATED` | Attacker | replay a consumed code | no new session; no new code exchange; no callback-directed navigation; callback parameters cleared; Security event produced; an independently established, known-valid session is preserved as `AUTHENTICATED`, while an absent or unprovable one resolves to `TERMINAL_SESSION_ERROR` | generic sign-in failure, or safe route recovery where a session is preserved | reporting a new sign-in; resolving successfully because a valid session already exists; re-exchanging the consumed code; revoking or signing out a separately valid session because the replay was rejected | no while `TERMINAL_SESSION_ERROR`; unchanged for a preserved session | `INVALID_CALLBACK` | `UNAUTHENTICATED`, or the canonical user of a preserved session | Security event shape |
| 8 | Expired callback | `CALLBACK_PROCESSING`, entered from a sign-in that began at `UNAUTHENTICATED` or `RECOVERABLE_ERROR`, so no independently established session pre-exists | `HUMAN_USER` | late `processCallback` | → `TERMINAL_SESSION_ERROR`, by the no-pre-existing-session row of the conditional rule rather than by an unconditional one | generic sign-in failure with a sign-in affordance | automatic retry of the exchange | no | `INVALID_CALLBACK` | `UNAUTHENTICATED` | none |
| 9 | Session restoration after reload | `AUTHENTICATED`, page reloaded on a non-callback route | `HUMAN_USER` | application start | `INITIALIZING` → `AUTHENTICATED` | protected content after resolution | protected content while `INITIALIZING`; treating the restored session as proof that any callback completed | yes, after resolution | success | canonical user | framework proxy/middleware layer |
| 10 | Proactive refresh while the credential remains provable | `AUTHENTICATED`, token near expiry but still valid | system | protected request | → `REFRESH_PENDING` mode `PROVEN_CREDENTIAL` | existing protected content may remain visible | sending a token known to be expired; beginning a new privileged effect on an expired token | deferred — new protected requests wait for the outcome | none if refresh succeeds | canonical user | none |
| 10a | Refresh after expiry, `401`, or unprovable credential | `AUTHENTICATED` in UI belief; token expired, Backend returned `401`, or session validity unknown | system | protected request | → `REFRESH_PENDING` mode `UNPROVEN_CREDENTIAL` | neutral pending affordance only | any protected content; any protected interaction; any protected request; treating this identically to fixture 10 | no — prohibited, not deferred | none if refresh succeeds, otherwise `REFRESH_FAILED` or `SESSION_EXPIRED` | canonical user | none |
| 11 | Successful refresh | `REFRESH_PENDING`, either mode | `A2-AUTH` | `refreshSession` | → `AUTHENTICATED` | resume, retry the request once; restore protected content only after the successful outcome | more than one retry; restoring protected content while the outcome is unknown | yes | success | canonical user | none |
| 12 | Refresh failure | `REFRESH_PENDING`, either mode | `A2-AUTH` | `refreshSession` | → `TERMINAL_SESSION_ERROR` | "sign in again" | any protected request; any retry; leaving mode-`PROVEN_CREDENTIAL` content on screen after the failure | no | `REFRESH_FAILED` | canonical user | Security event shape |
| 13 | Concurrent refresh requests within one context | `AUTHENTICATED`, several protected requests in flight in one browsing context | system | several `getAccessTokenForApiRequest` | one refresh, one shared outcome within that context | one pending affordance | two independent exchanges from the same context | deferred then yes or no | shared outcome | canonical user | none |
| 13a | Concurrent refresh across contexts | `AUTHENTICATED` in two tabs, or a tab plus a parallel server request | system | refresh in each context | not serialized; outcomes may include a stale cookie, a temporarily null session, or one success plus one rejection | one pending affordance per context; at most one bounded retry after a newer valid session is observed | claiming global single-flight; restoring stale authenticated state; speculative retry; any automatic refresh loop | no while unresolved | shared outcome where observable, otherwise fail closed | canonical user | provider cookie synchronization behavior; `A2-SECURITY` and `A2-INTEGRATION` confirmation |
| 14 | Sign-out | `AUTHENTICATED` | `HUMAN_USER` | `signOut` | → `SIGN_OUT_PENDING` → `UNAUTHENTICATED` | public surfaces | any stale protected content | no | success | canonical user | Security scope decision |
| 15 | Sign-out failure | `SIGN_OUT_PENDING` | provider or network | remote failure | → `UNAUTHENTICATED` regardless | "signed out on this device" | claiming the session persists; claiming issued tokens were revoked | no | `SIGN_OUT_FAILED` | canonical user | Security event shape |
| 16 | Unsafe return URL | `CALLBACK_PROCESSING` with a hostile return path | Attacker | `processCallback` | → `AUTHENTICATED` | navigation to the default destination | navigation to the supplied path | yes | success with fallback | canonical user | Security event shape |
| 16a | Unbound, expired or replayed return state that is syntactically safe | `CALLBACK_PROCESSING` with a well-formed relative path that is not bound to this attempt, has expired, or was already consumed | Attacker or stale state | `processCallback` | → `AUTHENTICATED`; the return state is discarded and removed | navigation to the default post-sign-in destination | accepting the path because it is syntactically safe; reusing a consumed return state; retaining it after completion | yes | success with fallback | canonical user | intended-return state mechanism pending `A2-SECURITY` |
| 17 | Backend `401` while UI believed it was authenticated | `AUTHENTICATED` | FastAPI | protected request denied | → `REFRESH_PENDING` mode `UNPROVEN_CREDENTIAL`, then `AUTHENTICATED` or `TERMINAL_SESSION_ERROR` | one bounded refresh and one retry; protected content removed for the duration | unbounded refresh-and-retry; ignoring the denial; keeping protected content visible while the credential is unproven | at most one retry, and none until the refresh resolves | none, or `REFRESH_FAILED` | canonical user | Backend `401` semantics |
| 18 | Suspended or deprovisioned canonical user | `AUTHENTICATED` at the provider | FastAPI | protected request | → `TERMINAL_SESSION_ERROR` on denial | denial without cause | treating a valid provider session as authorization | denied | Backend denial, not an Auth error class | canonical user retained for attribution | Backend denial policy; `403`/`404` disclosure |
| 19 | Revoked external subject | `AUTHENTICATED` at the provider | FastAPI | protected request | → `TERMINAL_SESSION_ERROR` on denial | denial without cause | reauthenticating into access | denied | Backend denial | subject retained for attribution | Backend denial policy |
| 20 | Secret and token redaction | any | any | any failure | unchanged by this fixture | safe category text only | any token, code, verifier, header, cookie, project reference, hostname, or stack trace in UI, logs, analytics, or tracing | unchanged | unchanged | as applicable | Security redaction guidance |

Fixtures 18 and 19 restate an existing `1.0.0-draft.2` guarantee in session
terms: a valid provider session is never authorization. `SUSPENDED` and
`DEPROVISIONED` users and `REVOKED` subjects are denied by FastAPI while
historical attribution is retained, exactly as the identity sections above
require.

The twenty numbered fixtures are unchanged in number and meaning. Fixtures
`4a`, `4b`, `4b-i`, `4c`, `10a`, `13a` and `16a` are lettered additions that make
the corrected callback-correlation lifecycle, the separation of callback-attempt
failure from session validity, refresh fail-closed, cross-context refresh and
return-state-binding semantics separately checkable; lettering keeps the
required numbering stable. Fixtures 10 and 10a must never be satisfiable by the
same behavior, and neither must fixtures 4a and 4b. Fixtures 4b and 4b-i must
never be satisfiable by the same behavior either: the callback fails identically
in both, and only the pre-existing session's independently established validity
distinguishes the resulting session state.

## Compatibility and versioning

The following are breaking changes:

- changing issuer-subject uniqueness;
- changing issuer normalization or comparison policy;
- reusing external IDs as internal IDs;
- removing actor types;
- changing the access tuple;
- permitting local credentials;
- permitting cross-installation or cross-repository access;
- lifecycle changes that re-enable denied access; or
- introducing organization tenancy or generic RBAC.

Version `1.1.0-draft.1` additionally classifies these as breaking:

- weakening the prohibited-storage list;
- permitting a refresh token to reach FastAPI;
- permitting a credential transport other than `Authorization: Bearer` for
  protected FastAPI requests;
- removing the PKCE or OAuth-state requirement;
- replacing the exact-match callback policy with a pattern match;
- permitting provider-returned data to control navigation without Auth-owned
  validation;
- treating a loading state as authenticated;
- allowing frontend session state to override a Backend authorization decision;
- removing an error classification, or changing an existing classification's
  retry, reauthentication, or Backend-eligibility meaning.

A breaking change requires a major contract version and coordinated
A2-DATABASE and A2-INTEGRATION review. Additive clarifications that preserve
these semantics may use a compatible draft/minor revision.

### Version `1.1.0-draft.1` classification

| Field | Value |
|---|---|
| Old version | `1.0.0-draft.2` |
| New version | `1.1.0-draft.1` |
| Change category | `ADDITIVE_COMPATIBLE_MINOR` |
| Breaking | `NO` |

Verified against this section's own rules. The `AUTH-002` additions change none
of the listed breaking items: issuer-subject uniqueness is untouched; issuer
normalization and exact case-sensitive comparison are untouched; no external ID
becomes an internal ID; no actor type is removed; the exact
user-installation-repository access tuple is unchanged; no local credential is
permitted; no cross-installation or cross-repository access is permitted; no
lifecycle change re-enables denied access; and no organization tenancy or
generic RBAC is introduced. The additions are confined to browser-session,
callback, custody, refresh, sign-out, redirect, adapter, error, and Security
semantics that did not previously exist in this contract.

Compatibility impact: existing consumers of `1.0.0-draft.2` require no change.
`DB-002` requires no migration, no new column, and no new table.

Consumer-review consequence: the additions introduce new obligations for
`A2-UI`, `A2-SECURITY`, `A2-DEPLOYMENT`, `A2-BACKEND`, and `A2-INTEGRATION`, so
each must review this version before it can be treated as accepted. Silence is
not acceptance.

## Conceptual acceptance fixture

Fixture:

- User A with active Subject A;
- User B with active Subject B;
- Installation A and Installation B;
- Repository A and Repository B;
- active grant User A + Installation A + Repository A; and
- active grant User B + Installation B + Repository B.

Required outcomes:

1. User A may access Repository A through Installation A.
2. User A may not access Repository B.
3. User A may not use Installation B for Repository A.
4. User B may not access Repository A.
5. Duplicate Subject A linkage to User B is rejected.
6. Revoking User A's grant denies later access.
7. Suspending Installation A denies later access.
8. Deprovisioning User A denies later access.
9. No token, private key, password hash, or webhook secret is stored.
10. A GitHub App actor is not recorded as a human actor.
11. An unauthenticated actor cannot authorize a protected action.
12. Publication execution has machine attribution and a traceable authorized
    trigger.

## Current limitations and cross-contract dependencies

Resolved since `1.0.0-draft.2`:

- Identity-provider issuer, audience, and callback **design values** are frozen
  as templates by `AUTH-DEP-004` and recorded above. Their runtime remains
  unprovisioned.
- Workflow actor-event integration no longer awaits `CONTRACT-WORKFLOW-001`,
  which is accepted and merged. The separate machine publication-actor gap
  remains open as `AUTH-DEP-008`.
- `HISTORICAL / COMPLETED`: A2-DATABASE has acknowledged this contract and
  implemented `DB-002` against it. `DB-002` is `MERGED` and is no longer
  blocked on `CONTRACT-WORKFLOW-001`. No Database rereview is outstanding, and
  version `1.1.0-draft.1` creates no new Database obligation.

Open:

- Provider runtime is `NOT_PROVISIONED / NOT_TESTED`: no Supabase project,
  GitHub OAuth provider configuration, Vercel project, production Dashboard
  hostname, TLS verification, production callback registration, or injected
  secret is proven by this repository.
- JWT runtime validation is not implemented or tested.
- The final cookie policy, `SameSite` value, any `HttpOnly` position, the CSRF
  policy, the Security-event schema and severity, retention periods, the
  disclosure policy, key custody, and monitoring thresholds are unresolved
  `A2-SECURITY` decisions. See `AUTH-DEP-011`.
- The exact storage and integrity mechanism for the Auth-owned intended-return
  state is unresolved and `PENDING_A2_SECURITY_ACCEPTANCE`. This contract states
  the binding properties it must have; it does not invent the mechanism and
  records no accepted Security decision for it. See `AUTH-DEP-011` and
  `AUTH-ISSUE-025`.
- The exact storage mechanism, integrity mechanism, record representation,
  required strength, retention duration and cleanup of the callback-completion
  correlation record — including the length of the bounded post-completion
  correlation window during which a `COMPLETED_CALLBACK_CORRELATION` record
  stays reusable — are unresolved and `PENDING_A2_SECURITY_ACCEPTANCE`. This
  contract states the lifecycle and the properties the record must have, and
  deliberately states no duration and no mechanism. See `AUTH-DEP-011` and
  `AUTH-ISSUE-025`.
- Refresh serialization across browser tabs, parallel server requests and
  separate runtime instances is **not** guaranteed by the accepted provider
  design and is not claimed anywhere in this contract. The observable behavior
  of concurrent cross-context refresh under `@supabase/ssr` cookie
  synchronization is `NOT_TESTED`. See `AUTH-DEP-011`, `AUTH-DEP-015` and
  `AUTH-ISSUE-026`.
- The Backend authenticated-context handoff, the exact `403` versus
  concealed-`404` policy, CORS, and the Backend token-verification retry policy
  are unresolved. See `AUTH-DEP-006` and `AUTH-DEP-014`.
- The provider sign-out scope and the residual validity window of an
  already-issued access token after sign-out are unresolved joint
  `A2-SECURITY` and `A2-BACKEND` decisions.
- GitHub access-verification freshness is not frozen.
- The concrete default post-sign-in destination path is `A2-UI`-proposed and
  Auth-approved, and is not yet fixed.
- This contract is documentation, not Auth runtime implementation. Auth
  runtime, frontend Auth behavior, provider runtime, and Backend JWT behavior
  are `NOT_IMPLEMENTED / NOT_TESTED`.
- Version `1.1.0-draft.1` requires `A2-UI`, `A2-SECURITY`, `A2-DEPLOYMENT`,
  `A2-BACKEND`, and `A2-INTEGRATION` consumer review before it may be treated
  as accepted. It is `NOT_IMPLEMENTATION_READY`, and it authorizes no
  implementation, no `UI-004`, and no `AUTH-003`.
