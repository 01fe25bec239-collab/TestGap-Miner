# CONTRACT-AUTH-001 — Authentication Identity and Repository Authorization Boundary

## Metadata

| Field | Value |
|---|---|
| Contract ID | `CONTRACT-AUTH-001` |
| Version | `1.2.0-draft.1` |
| Previous version | `1.1.0-draft.1` |
| Change category | `ADDITIVE_COMPATIBLE_MINOR` |
| Status | `FINALIZED_CONTRACT_DRAFT_FOR_A2_REVIEW` |
| Implementation readiness | `NOT_IMPLEMENTATION_READY` |
| Runtime status | `EXISTING_MERGED_CODE_IN_APPS_WEB_SRC_AUTH / AUTH_006_RUNTIME_MODIFICATION_AUTHORIZED=NONE / FENCE_CORRECTION_RUNTIME=NOT_YET_AUTHORIZED` |
| Owner | `A2-AUTH` |
| Historical blocking consumer | `A2-DATABASE` (`DB-002`) — `ACKNOWLEDGED_AND_IMPLEMENTED` |
| Required consumers for the `1.2.0-draft.1` additions | `A2-UI`, `A2-SECURITY`, `A2-DEPLOYMENT`, `A2-INTEGRATION` |
| Evidence baseline | `5ffa8994b286e85d9f676336dbe0169cfbc89d2c` |
| Prior evidence baseline | `84ad9e322d886f8963c34386f87074a444b3fa2b` |

This contract defines semantic identity, authorization, and browser-session
requirements only. It does not implement Auth, Database, Backend, or frontend
behavior. A2-DATABASE retains ownership of physical table names, ORM classes,
migrations, constraint names, indexes, PostgreSQL implementation, and migration
ordering. A2-UI retains ownership of frontend implementation, routes as user
surfaces, host/path/transport/wiring for `/auth/session-fence`, and UX. A2-DEPLOYMENT
retains ownership of provider provisioning, deployed origins, TLS, callback registration,
and secret injection.

`A2-DATABASE` is recorded as a `HISTORICAL_BLOCKING_CONSUMER /
ACKNOWLEDGED_AND_IMPLEMENTED`. `DB-002` is merged (pull request #12,
implementation `5506ab5`, merge `3701520`) and no Database rereview of the
`1.0.0-draft.2` semantics is outstanding. Version `1.1.0-draft.1` added
browser-session semantics, and version `1.2.0-draft.1` finalizes the contract by
incorporating the accepted `AUTH-005` normative corrections across `A2-UI`, `A2-SECURITY`,
`A2-DEPLOYMENT`, and `A2-INTEGRATION` (all `ACCEPTED_WITH_CONSTRAINTS`). Neither creates
a new Database obligation.

Version `1.2.0-draft.1` is `FINALIZED_CONTRACT_DRAFT_FOR_A2_REVIEW`. All required consumer reviews for `AUTH-005` additions are complete (`A2-UI`, `A2-SECURITY`, `A2-DEPLOYMENT`, `A2-INTEGRATION` all `ACCEPTED_WITH_CONSTRAINTS`). It is not implementation-ready. Merged Auth runtime code exists in baseline under `apps/web/src/auth/**` (including `AuthAdapter`, state machine, correlation, storage boundary, redirect, types, unit tests). This contract finalization task (`AUTH-006`) authorizes NO runtime modification. `AUTH-003` / `AUTH-005` fence correction runtime implementation is NOT YET AUTHORIZED / NOT YET IMPLEMENTED under this task. No statement in this contract authorizes Auth runtime implementation, frontend implementation, provider provisioning, or `UI-004`.

Version `1.2.0-draft.1` formalizes the `AUTH-005` session fence, Auth-context generation,
sign-out fence, callback generation binding, stale HTTP callback response fail-closed
semantics, session restoration rules, access-token fence/binding verification, multi-tab
fence semantics, production and local process synchronization authority requirements,
the UI host boundary (`POST /auth/session-fence`), security context/binding handles,
local sign-out tombstone, security event follow-up (local non-noop sink required, enrichment
as implementation follow-up), and integration future test requirements.

Historical references to `1.1.0-draft.1` remain historical in past records and past
decision logs and are not rewritten as though they originally referred to `1.2.0`.

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

`A2-UI` has since returned the first consumer response to this draft, under
review task `AUTH-002-CONSUMER-REVIEW-A2-UI-001` against reviewed head
`7abe17af8e212bd2127160338ea6ef409da02101`, with the disposition
`SPECIFICATION_CONFLICT`. That disposition stands for that head and is not
converted here. Two corrections follow from it, one owned by each side. The
UI-owned correction — superseding the conflicting current meaning of `UI-DEC-013`
so that the merged UI custody rule stops prohibiting the browser-readable
`@supabase/ssr` cookie this contract depends on, while its `localStorage`,
`sessionStorage` and duplicate-store prohibitions all remain — is `A2-UI`-owned
and is not performed by this contract. It has since been performed and merged by
its owner as `UI-DEC-026` and `UI-DEC-027` in pull request #30 (implementation
commit `30deb92000a20d3837b2423b6bdee3ea3335a7f1`, merge commit
`63093f22c37a0fc6affe168f7d5230107b05cdf3`), which changed UI durable records
only and no Auth path; the merged UI custody rule is now compatible with the
canonical Auth-owned `@supabase/ssr` session this contract requires, and the
merged text states that the browser-readable exception remains conditional on
A2-SECURITY acceptance of the final cookie posture and that browser Auth
implementation stays `NOT_AUTHORIZED`. The Auth-owned correction is applied in
this text and recorded as `AUTH-DEC-042` and `AUTH-DEC-043`: the concrete default
post-sign-in destination is frozen as `/`, and `/` is also frozen as the safe
recovery destination when a callback attempt is rejected while an independently
established pre-existing session remains known-valid. Neither correction changes
custody architecture, callback correlation, redirect validation, or any Security
posture that was, at that stage — before the subsequent `A2-SECURITY` consumer
response — still `PENDING_A2_SECURITY_ACCEPTANCE`. Those Security questions were
pending at the time of the `A2-UI` response and were subsequently resolved as
policy by `AUTH-DEC-045` through `AUTH-DEC-051`, recorded immediately below.
`AUTH-DEP-012` remains open — the merged UI-owned half does not accept this
draft — and `A2-UI` rereview of the corrected Auth head is required. The merged
UI correction is recorded as `AUTH-DEC-052`.

`A2-SECURITY` then returned the second consumer response, under review task
`AUTH-002-CONSUMER-REVIEW-A2-SECURITY-001` against the same reviewed head
`7abe17af8e212bd2127160338ea6ef409da02101`, with the disposition
`REJECTED_WITH_REASON` and **seven** required normative corrections. That
disposition also stands for that head and is not converted here. In rejecting
the head, `A2-SECURITY` explicitly **accepted the selected architecture**:
`SUPABASE_AUTH_WITH_GITHUB_OAUTH`, `@supabase/ssr`, `createBrowserClient` and
`createServerClient`, one provider-owned cookie-backed session as the only
canonical session source, a browser-readable provider-session cookie, and
required PKCE. The response itself is recorded as `AUTH-DEC-044`, and the seven
corrections are applied in this text and recorded as `AUTH-DEC-045` through
`AUTH-DEC-051`: the frozen provider-session cookie
posture; the CSRF and credential-transport boundary; `local` sign-out scope with
the production access-token lifetime bound; the public `SIGN_IN_FAILED`
failure-oracle boundary; the server-side ephemeral callback-correlation
mechanism with its two frozen lifetimes; the server-side intended-return state;
and the live-provider proof required before a pre-existing session may be
treated as known-valid. Both `AUTH-DEP-011` and `AUTH-DEP-012` remain open, and
both `A2-UI` and `A2-SECURITY` rereview of the corrected head are required.
`A2-BACKEND` and `A2-DEPLOYMENT` compatibility confirmations remain outstanding
and are not claimed anywhere in this text.

The version identifier is unchanged because the draft was never accepted, and
the classification remains `ADDITIVE_COMPATIBLE_MINOR` over `1.0.0-draft.2`.
`A2-SECURITY` classified its own corrections as pre-acceptance contract changes
that require no version increase, which this contract independently verified
against its own versioning rules below: no error classification is removed and
none has its retry, reauthentication or Backend-eligibility meaning changed; the
prohibited-storage list is only extended; and no other listed breaking item is
touched.

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
| Integrity | Held server-side inside the `PENDING_ATTEMPT_CORRELATION` record. It cannot be presented from another origin because it never leaves the server. Frozen by `A2-SECURITY`; see `Frozen intended-return mechanism` below. |
| Removal | Removed after callback success, callback failure, abandonment and expiry alike. No return state survives a completed or abandoned flow. |
| Syntax is not sufficiency | A syntactically safe relative path is never accepted merely because it is syntactically safe. Satisfying the `Safe redirect contract` format rules does not make an unbound, expired, replayed, tampered or missing return state usable. |
| Provider `state` reuse | The provider OAuth `state` parameter must not be reused as an application return-path container unless current official provider documentation explicitly supports that design **and** `A2-SECURITY` accepts it. No such documented support is recorded at this baseline, so the reuse is prohibited by this draft. |

Missing, expired, tampered, replayed or unbound return state falls back to the
default post-sign-in destination. The fallback is not a user-facing error and
never blocks an otherwise successful sign-in.

#### Frozen intended-return mechanism

`A2-SECURITY` has decided this mechanism. The intended return path exists
**only** inside the server-side `PENDING_ATTEMPT_CORRELATION` record. The
browser carries only the `OPAQUE_CORRELATION_HANDLE` described under
`Frozen correlation mechanism`.

The return path must be:

- validated before storage;
- bound to exactly one sign-in attempt;
- expiry-limited to at most 10 minutes after initiation;
- atomically single-use; and
- removed on success, on failure, on abandonment and on expiry.

The return path is **never**: copied into provider OAuth `state`; stored in the
browser-readable provider cookie; stored in the correlation-handle cookie;
placed in a URL; stored in `localStorage`; stored in `sessionStorage`; stored in
IndexedDB; or stored in any other custom browser persistence mechanism.

| Condition | Behavior |
|---|---|
| Missing server-side record | Fall back to `/`. |
| Integrity failure | Fall back to `/`. |
| Replay | Fall back to `/`. |
| Store failure | Fall back to `/`. |

These fallbacks relax **no** callback validation. A fallback destination is not
callback success: the callback's own outcome is decided independently by OAuth
state, PKCE, correlation, the exact callback destination and attempt binding.

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
| Terminal failure | All partial session state **created by the rejected attempt** is cleared, callback parameters are removed from the URL, and the intended-return state associated with the rejected attempt is removed. Where no independently valid pre-existing session exists, the user is returned to an unauthenticated surface. A pre-existing session that was independently established and remains known-valid is preserved rather than cleared, and safe route recovery navigates to `/` under `Preserved-session safe route recovery`; a session whose validity is unknown fails closed. | terminal for the callback attempt |

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

#### Frozen correlation mechanism

`A2-SECURITY` has decided the mechanism. It is stated semantically; no vendor,
product or physical technology is selected.

| Property | Frozen value |
|---|---|
| Mechanism class | `AUTH_CONTROLLED / PROVIDER_NEUTRAL / SERVER_SIDE / EPHEMERAL` |
| Required capabilities | Atomic state transitions; atomic single-use behavior; expiry; concurrent independent sign-in attempts; shared availability where multiple application runtime instances may process callbacks. |
| Browser-carried material | A cryptographically random **opaque correlation handle** only, in a separate Auth-owned cookie. |
| `PENDING_ATTEMPT_CORRELATION` maximum lifetime | 10 minutes from sign-in initiation. |
| `COMPLETED_CALLBACK_CORRELATION` lifetime | Exactly 120 seconds from successful completion. |
| Pending → completed transition | `ATOMIC`. |
| Store unavailable, or handle unverifiable | `FAIL_CLOSED`. |
| Concurrent tabs | Separate records. One attempt never overwrites another. |

No database vendor, cache vendor, storage provider, cloud service or physical
implementation technology is selected here. Physical storage technology and
deployment topology remain `PENDING_A2_DEPLOYMENT_CONFIRMATION`, classified
`SECURITY_REQUIRED / PENDING_AFFECTED_OWNER_COMPATIBILITY_REVIEW`.

The correlation-handle cookie is a separate Auth-owned cookie, distinct from the
provider-session cookie, and in every non-local environment is:

- `HttpOnly`;
- `Secure`;
- `SameSite=Lax`;
- host-only; and
- restricted to the callback path.

The handle cookie contains no authorization code, no access token, no refresh
token, no PKCE verifier, no return path, no provider payload, and no provider
session. It is an opaque lookup handle and nothing else.

The server-side correlation record binds exactly: one sign-in attempt; one
callback flow; the lifecycle state; the creation time; the expiry; one
completed-outcome reference; and the Security policy version.

Failure, abandonment, a malformed callback, an expired flow and a rejected flow
must **never** create a `COMPLETED_CALLBACK_CORRELATION` record.

Where correlation cannot be proven — including where the store is unavailable or
the handle cannot be verified — the callback attempt fails closed. This never
weakens the single-use authorization-code rule or the replay-resistance
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
| Independently established before the rejected callback and still known-valid | Preserved as `AUTHENTICATED` | The callback attempt fails, no callback success is reported, no callback-directed destination is used, and the UI presents a safe callback-error outcome or safe route recovery whose final navigation is `/` under `Preserved-session safe route recovery`. The rejected attempt's intended-return destination is never used. FastAPI authorization remains authoritative for anything that session is used for. |
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

#### `INDEPENDENTLY_ESTABLISHED_AND_KNOWN_VALID_SESSION`

Frozen by `A2-SECURITY`. The earlier text used "independently established and
still known-valid" without defining what proves it, which let cookie presence
masquerade as proof. A pre-existing session qualifies only when **all four** are
true:

1. its session identity existed before the rejected callback was processed;
2. callback processing performed no successful code exchange that created or
   replaced that session;
3. after callback rejection, authoritative server-side **live provider
   validation** succeeds; and
4. the validated session identity equals the pre-callback session identity.

Requirement 3 is normative as `LIVE_PROVIDER_SESSION_VALIDATION`: an
authoritative server-side call to the provider that validates the session as it
stands now. `getUser()` may be referenced as the currently supported provider
example, but this contract does not permanently depend on one SDK method name;
any equivalent authoritative provider operation satisfies the requirement, and
the requirement is the authority, not the method name.

Each of the following is **insufficient on its own** to prove validity:

- cookie presence;
- `getSession()`;
- a decoded JWT;
- local signature or expiry validation;
- `getClaims()`;
- frontend state;
- a subscription event; or
- the existence of an access token.

If live validation is unavailable, times out, fails, returns a different
session, or cannot establish session-identity equality, then session validity is
`UNPROVEN` and the result is `FAIL_CLOSED`: `TERMINAL_SESSION_ERROR`, protected
content removed, protected requests prohibited.

A rejected callback that preserves a session must emit an internal Security
event carrying at least these semantic fields:

- `session_preserved=true`
- `callback_success=false`
- `rejected_callback_destination_used=false`

Callback cleanup is mandatory. Authorization codes and tokens must never be
placed in durable UI state, must never remain in the URL, query string, or
fragment after callback processing, and must never appear in logs, error text,
analytics, or tracing metadata. Browser history must not retain a URL
containing an authorization code where the framework permits replacing it.

## `AUTH-005` session fence, Auth context, and synchronization authority

This section incorporates the normative corrections authorized under `AUTH-005` and finalized by `AUTH-006`.

### `SIGN_OUT_WINS` principle

Physical arrival of stale provider cookie material (e.g. through delayed network response, browser caching, race conditions, or provider event delivery) MUST NEVER qualify as an established or usable Auth session after a newer Auth-context fence exists. `SIGN_OUT_WINS` is absolute across all runtime contexts.

### `ESTABLISHED_AUTH_SESSION` criteria

An `ESTABLISHED_AUTH_SESSION` exists if and only if ALL of the following six conditions are simultaneously satisfied:

1. **Valid provider session**: A valid, provider-backed session exists. The provider session remains the sole canonical provider credential/session.
2. **Current Auth context**: The Auth context matches the current generation.
3. **Valid session binding**: The session binding handle matches the active Auth context.
4. **No active local sign-out tombstone**: No active `LOCAL_SIGN_OUT_TOMBSTONE` exists for the context.
5. **Verified synchronization authority**: The synchronization authority confirms validity and generation currency.
6. **No newer sign-out generation**: No sign-out generation newer than the session binding has been published.

If any of these six conditions fails or is indeterminate, session establishment fails closed.

### OPAQUE_AUTH_CONTEXT_HANDLE, OPAQUE_AUTH_SESSION_BINDING_HANDLE, and LOCAL_SIGN_OUT_TOMBSTONE posture

| Handle / Artifact | Sensitivity & Exposure | Security Constraints |
|---|---|---|
| `OPAQUE_AUTH_CONTEXT_HANDLE` | Internal Auth context fence identifier. Never exposed to browser JS, analytics, logs, or tracing. | >=128-bit CSPRNG; opaque; `HttpOnly`; `Secure` outside exact `http://localhost:3000` exception; `SameSite=Lax`; host-only (no `Domain`); `Path=/`; browser-session scoped. |
| `OPAQUE_AUTH_SESSION_BINDING_HANDLE` | Binds a specific established session to an Auth context. Never exposed to browser JS, analytics, logs, or tracing. | >=128-bit CSPRNG; opaque; `HttpOnly`; `Secure` outside exact `http://localhost:3000` exception; `SameSite=Lax`; host-only (no `Domain`); `Path=/`; lifetime <= Auth context; new handle issued for each successful session establishment. |
| `LOCAL_SIGN_OUT_TOMBSTONE` | Deny-only local marker indicating an intentional sign-out. | Deny-only; browser-readable; **NOT** `HttpOnly`; `Secure` outside exact `http://localhost:3000` exception; `SameSite=Lax`; host-only (no `Domain`); `Path=/`; browser-session scoped; cannot grant authentication; absence alone proves nothing; stale callbacks cannot clear it; provider events cannot clear it; removal permitted ONLY through successful explicit Auth reconciliation or an authorized Auth-context reset. |

### Session-binding record structure and exclusions

A successful session-binding record binds at minimum:
- One Auth context;
- The attempt's Auth-context generation;
- One sign-in attempt;
- One callback flow;
- The successful session-establishment result.

The binding record MUST NOT contain:
- Access token;
- Refresh token;
- Provider-session bytes;
- Authorization code;
- PKCE verifier;
- Intended-return path;
- Identity claim;
- Authorization capability.

Callback-correlation records remain distinct from session-binding records.

Callback correlation records represent Auth-owned attempt/callback-flow correlation and the existing permitted pending intended-return binding.

Provider PKCE-verifier custody and provider OAuth-state generation/validation remain provider-integration-owned and are not transferred into Auth correlation records.

Session-binding records instead represent successful session establishment against an Auth context and Auth-context generation.

The two record types MUST NOT be merged.

### Callback response fence non-mutation rules

The callback response MUST NOT create, replace, rotate, clear, overwrite, or otherwise mutate:
- The authoritative browser Auth-context synchronization handle; or
- An already active newer `LOCAL_SIGN_OUT_TOMBSTONE`.

A stale callback may physically reintroduce stale provider-session cookie material or an old opaque session-binding handle, but those values MUST fail generation validation and remain unusable.

### New sign-in after sign-out reconciliation

A sign-out tombstone MUST NOT permanently prevent future authentication.

When the user deliberately initiates a NEW sign-in while `LOCAL_SIGN_OUT_TOMBSTONE` is active:
1. Auth MUST first perform `PREPARE_SIGN_IN` / Auth-context reconciliation with the authoritative synchronization authority;
2. Reconciliation MUST establish that pre-sign-out generations remain superseded;
3. Only AFTER successful reconciliation may the local tombstone be removed;
4. Only AFTER successful reconciliation may provider OAuth initiation proceed;
5. The new sign-in attempt binds to the then-current Auth-context generation.

If reconciliation is unavailable, fails, or is indeterminate:
- Provider sign-in MUST NOT proceed;
- The tombstone remains active;
- Auth remains fail closed.

### Synchronization Artefact Posture

Synchronization artefacts (handles, tombstones, fence records) are NOT:
- sessions;
- credentials;
- identities;
- permissions;
- authorization;
- token copies; or
- duplicate provider-session stores.

The provider session remains the sole canonical provider credential and session source. No duplicate session or token store is created or maintained.

### Sign-out fence, generation invalidation, and tombstone ordering

When `AuthAdapter.signOut()` is requested, Auth MUST establish the browser-local deny-only `LOCAL_SIGN_OUT_TOMBSTONE` BEFORE relying on any cross-runtime `PUBLISH_SIGN_OUT` operation or provider sign-out completion.

Required ordering:
1. User requests sign-out.
2. `LOCAL_SIGN_OUT_TOMBSTONE` becomes active locally.
3. Protected Auth eligibility fails closed immediately.
4. Publish / advance authoritative Auth generation (`PUBLISH_SIGN_OUT`).
5. Perform existing provider `CURRENT_SESSION_ONLY` sign-out.

If publication fails or synchronization authority is unavailable:
- `LOCAL_SIGN_OUT_TOMBSTONE` MUST remain active;
- Local Auth remains signed out;
- `AUTHENTICATED` MUST NOT be restored;
- Provider `SIGNED_IN`, `TOKEN_REFRESHED`, or equivalent events MUST NOT clear it;
- Stale callback or session material MUST NOT clear it;
- Protected UI remains prohibited;
- New protected API request preparation remains prohibited.

Do not redefine `SIGN_OUT_FAILED`.
Do not change `CURRENT_SESSION_ONLY`.
Do not claim immediate JWT revocation.

Publishing a sign-out fence increments the sign-out generation and creates a new Auth-context fence. Stale provider session material fails closed immediately. Physical cleanup of stale cookies and synchronization artefacts occurs at the first Auth-controlled cookie-mutating opportunity.

### Callback generation binding and stale HTTP callback response semantics

1. **Callback generation binding**: Every callback processing attempt is bound to the Auth-context generation active when `beginSignIn` / `PREPARE_SIGN_IN` was invoked.
2. **Stale HTTP callback responses**: A callback MUST fail closed as stale when the Auth-context generation to which its sign-in attempt is bound is no longer the authoritative current generation. A later sign-in attempt does NOT, merely by being later in time, invalidate an earlier independently correlated attempt when both remain bound to the same current Auth-context generation.
3. **Old callback after sign-out and new sign-in**: The required "old callback after new sign-in" case occurs when attempt A begins under generation G, sign-out advances the Auth context beyond G, explicit reconciliation occurs, and attempt B begins under the newer current generation. Any late callback or session response belonging to attempt A remains bound to generation G and MUST NOT establish or restore current Auth.
4. **Concurrent independent sign-in attempts**: Concurrent independent sign-in attempts MAY exist under the same current Auth-context generation and remain governed by existing attempt-specific callback correlation rules.

### Session restoration and access-token preparation

1. **Session restoration**: Restoring a session (in browser or server context) requires verifying the current fence, session binding, tombstone status, and synchronization authority. Provider-cookie arrival alone is insufficient. Provider events (e.g. `onAuthStateChange`) remain provisional until fence validation succeeds.
2. **Access-token preparation**: `getAccessTokenForApiRequest` requires current fence and session-binding verification before returning a token for FastAPI requests. If fence or binding verification fails, access-token retrieval fails closed.

### Multi-tab semantics

Multi-tab semantics are preserved. All tabs within the same browser context share the Auth-context fence, session binding, and tombstone state. A sign-out fence published in one tab immediately invalidates session validity across all tabs via shared fence validation.

### Production and local process synchronization authority

1. **Production synchronization authority**:
   - Environment-isolated;
   - Highly available;
   - Shared across every relevant Auth runtime;
   - Linearizable;
   - Restart-safe;
   - Failover-safe;
   - Fail-closed when unavailable or indeterminate.
   - Physical provider remains **UNSELECTED**. No concrete provider (such as Redis, Valkey, PostgreSQL, Supabase table, cloud cache) is named or selected.

2. **Local UI-004 process-local authority**:
   - Permitted ONLY when callback processing, session validation, and sign-out all run in exactly ONE local Next.js/Auth OS process and ONE memory space.
   - Must have no replicas, clustering, serverless isolates, load balancing, or independently restarted handlers.
   - On local authority process restart: authority state loss -> **FAIL CLOSED** -> reauthentication.
   - No production-safety claim may be made from local process memory.

### A2-UI host boundary (`/auth/session-fence`)

The host boundary for session fence operations is frozen as authorized by Agent 1:

- **HTTP method**: `POST`
- **Path**: `/auth/session-fence`
- **UI-owned implementation path**: `apps/web/src/app/auth/session-fence/route.ts`
- **Semantic operations behind the host**:
  - `PREPARE_SIGN_IN`
  - `PUBLISH_SIGN_OUT`
  - `RESOLVE_SESSION`
- **Ownership split**:
  - `A2-UI`: host/path/transport/wiring.
  - `A2-AUTH`: all Auth semantics behind the host endpoint. No Auth semantic ownership transfers to UI.
- **Request constraints**:
  - `POST` method only;
  - Exact approved Dashboard Origin;
  - Same-origin Fetch Metadata checks where supported;
  - Existing Auth-owned anti-CSRF boundary;
  - `Cache-Control: private, no-store`.
- **Presentation & navigation rule**:
  `processCallback()` success alone is NOT final proof of current authenticated presentation eligibility after AUTH-005. Final authenticated presentation/navigation requires current fence-resolved Auth eligibility. No new public UI Auth state is introduced.

### Sign-out contract amendment and AuthAdapter operation amendments

- Provider sign-out scope remains `local` / `CURRENT_SESSION_ONLY`.
- Do NOT claim immediate Backend JWT revocation.
- Public `AuthAdapter` operation list remains unchanged (`beginSignIn`, `processCallback`, `getSessionSnapshot`, `subscribeToSessionChanges`, `getAccessTokenForApiRequest`, `refreshSession`, `signOut`).
- Operations are amended behind the public boundary to enforce fence validation, generation verification, and tombstone checks.

### Security event follow-up

- The current UI-004 no-op Security-event sink is **NOT acceptable**.
- A **LOCAL NON-NOOP sink** is **REQUIRED**.
- Local durable persistence is **NOT required**.
- The existing `AuthSecurityEvent` runtime payload/interface may require later Security-envelope enrichment.
- That enrichment is recorded as an **IMPLEMENTATION FOLLOW-UP** only, and is **NOT** implemented by AUTH-006.

### Integration future acceptance-test requirements

The following are recorded as **FUTURE acceptance-test requirements** (not claimed runtime evidence):

1. Deterministic server/browser response-order control;
2. Actual browser cookie jar;
3. Stale response order A;
4. Stale response order B;
5. Multi-tab shared browser context;
6. Faultable synchronization authority;
7. Deterministic callback response barriers;
8. Separate assertions for semantic denial versus physical cleanup;
9. No protected-content flash;
10. Access-token fail-closed;
11. Existing callback duplicate/replay regression suite remains green.

Vitest/jsdom-only proof is **INSUFFICIENT** for browser/network ordering acceptance. These tests are future implementation/integration evidence requirements, and are not claimed to have passed.

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
    the strength of an existing session. Where rule 9 preserves the session,
    safe route recovery navigates to `/` and never to the rejected attempt's
    intended-return destination. See `Preserved-session safe route recovery`.

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
| `HttpOnly` | **Not** `HttpOnly`, and not achievable as `HttpOnly` under the selected browser-readable architecture. `A2-SECURITY` has accepted the browser-readable provider session as policy. See `Frozen provider-session cookie posture` below. |
| `Secure` | `REQUIRED` in every non-local environment, with exactly one exception. See `Frozen provider-session cookie posture` below. |
| `SameSite` | `Lax`, frozen by `A2-SECURITY` policy acceptance. See `Frozen provider-session cookie posture` below. |
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

### Frozen provider-session cookie posture

`A2-SECURITY` reviewed this contract under
`AUTH-002-CONSUMER-REVIEW-A2-SECURITY-001`, returned `REJECTED_WITH_REASON`
against head `7abe17a`, and in doing so **accepted the selected Auth
architecture**: `SUPABASE_AUTH_WITH_GITHUB_OAUTH`, the `@supabase/ssr`
integration, `createBrowserClient` and `createServerClient`, one
provider-owned cookie-backed session as the only canonical session source, a
browser-readable provider-session cookie, and required PKCE. The posture below
is the accepted policy, not an Auth proposal.

| Attribute | Frozen value |
|---|---|
| Session | The official `@supabase/ssr` provider session. |
| Readability | `BROWSER_READABLE`. |
| `SameSite` | `Lax`. |
| `Secure` | `true` in every non-local environment. |
| Host scope | Host-only. |
| `Domain` attribute | Absent. No `Domain` attribute is set. |
| `Path` | `/`. |
| `HttpOnly` | Not `HttpOnly`, under the selected browser-readable architecture. |
| Lifetime and rotation | Provider-managed. |
| Duplicate copies | None. No custom token copy of any kind. |

The only permitted `Secure=false` case is `http://localhost:3000`. That
exception does **not** extend to preview environments, LAN hostnames, public
tunnels, alternate HTTP hosts, staging over HTTP, or production over HTTP. In
every one of those, `Secure=true` is required.

| Owner | Role in this posture |
|---|---|
| `A2-SECURITY` | `POLICY_ACCEPTANCE`. |
| `A2-AUTH` | `AUTH_SEMANTICS`. |
| `A2-DEPLOYMENT` | `RUNTIME_AND_CONFIGURATION_CONFIRMATION` — **not yet given**. |

`A2-DEPLOYMENT` has not confirmed that it can configure or guarantee this
posture. That confirmation is `SECURITY_REQUIRED /
PENDING_AFFECTED_OWNER_COMPATIBILITY_REVIEW`. Nothing here claims the posture is
implemented, deployed, or verified; Auth runtime and provider runtime remain
`NOT_IMPLEMENTED / NOT_TESTED` and `NOT_PROVISIONED / NOT_TESTED`.

The provider session is not redesigned as `HttpOnly`-only, and browser
persistence is not reverted to a `createClient` `localStorage` model. Every
prohibited-storage rule above stands unchanged.

### `AUTH-002` CSRF and credential-transport boundary

Frozen by `A2-SECURITY` policy acceptance.

| Boundary | Rule |
|---|---|
| Protected FastAPI credential | `Authorization: Bearer <access-token>` only. |
| Provider-session cookie as an API credential | `PROHIBITED`. FastAPI never accepts the provider-session cookie as a credential. |
| Application anti-CSRF token on Bearer-authenticated FastAPI requests | `NOT_REQUIRED`. A Bearer-authenticated API request does not require an application anti-CSRF token merely because it is a FastAPI request. |
| CORS origin | The exact approved Dashboard origin. No wildcard origin. |
| CORS headers and methods | Only those required. |
| CORS implementation ownership | `A2-BACKEND`. |

Every same-origin Auth or session operation that **mutates** session state must:

- use a non-`GET` method;
- validate the exact `Origin`;
- apply Fetch Metadata checks where the browser supports them; and
- validate an Auth-owned anti-CSRF value bound either to the current session or
  to the anonymous sign-in attempt.

Sign-out is a state-changing operation: it is same-origin, non-`GET`, and
CSRF-validated. `GET`, `HEAD` and `OPTIONS` Auth or session endpoints remain
`SIDE_EFFECT_FREE`.

The OAuth callback is the one deliberate exception. It arrives as a top-level
cross-site navigation and therefore does **not** carry the ordinary same-origin
anti-CSRF token. Before any protected effect, it must instead validate all of:
provider OAuth `state`; PKCE; callback correlation; the exact callback
destination against the exact-match approved set; and intended-return binding.
The exception narrows nothing else — replay resistance, single-use codes and
fail-closed behavior all continue to apply.

`A2-BACKEND` has not confirmed compatibility with Bearer-only transport, the
cookie-is-not-a-credential rule, or exact-origin CORS. Those confirmations are
`SECURITY_REQUIRED / PENDING_AFFECTED_OWNER_COMPATIBILITY_REVIEW`.

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
| Provider-session scope | `local`, meaning `CURRENT_SESSION_ONLY`. Frozen by `A2-SECURITY`. The official integration defaults to a broader global scope that signs the user out of every device; that default must **not** be inherited or used. The scope is passed explicitly. |
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
it. A previously issued access token may remain accepted by FastAPI until its
`exp`.

### Production access-token lifetime policy

`A2-SECURITY` bounds that residual window instead of leaving it unresolved.

| Item | Value |
|---|---|
| Production Supabase access-token lifetime | `<= 900 seconds` |
| Classification | `PRODUCTION_SECURITY_REQUIREMENT / PENDING_BACKEND_AND_DEPLOYMENT_CONSUMER_CONFIRMATION` |

Required semantics:

- the production access-token lifetime is at most 900 seconds;
- local authenticated UI state clears immediately on sign-out;
- an already-issued access token may remain accepted by FastAPI until its `exp`;
- no baseline denial list, revocation list or token blocklist is required; and
- neither Auth nor UI may claim immediate JWT revocation.

This is **not** recorded as already configured. No repository evidence proves
any JWT lifetime, and none is claimed. Confirmation is required from both
`A2-BACKEND` and `A2-DEPLOYMENT`, and remains `SECURITY_REQUIRED /
PENDING_AFFECTED_OWNER_COMPATIBILITY_REVIEW` under `AUTH-DEP-011`,
`AUTH-DEP-013` and `AUTH-DEP-014`.

A future especially sensitive operation may require an explicit live
session-liveness check, but only where `A2-SECURITY` specifically classifies
that operation. No such operation is classified at this version.

The UI fails closed after local sign-out state is established.

## `AUTH-002` safe redirect contract

| Item | Decision |
|---|---|
| Default post-sign-in destination | `/`. Frozen: `A2_UI_PROPOSED / A2_AUTH_APPROVED`. Resolved by Auth-owned code, never user-controlled, and never taken from a request, a referrer, or provider-returned data. |
| Default post-sign-in rationale | `/` already exists as the implemented Overview destination, is same-origin, depends on no Runs, Evidence, Benchmarks, API-runtime or Auth-specific feature route, and is therefore safe when intended-return state is missing or rejected. |
| Preserved-session rejected-callback safe recovery destination | `/`. Used only for the condition defined under `Preserved-session safe route recovery` below. It is independent of the rejected attempt's return candidate. |
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

### Preserved-session safe route recovery

This subsection governs exactly one condition, and no other:

- a callback attempt is rejected;
- a session that was independently established before that callback remains
  known-valid;
- the callback itself reports failure; and
- that independently established session remains `AUTHENTICATED` under the
  `Callback-attempt failure versus session validity` rules.

| Requirement | Rule |
|---|---|
| Safe recovery destination | `/`. |
| Callback outcome | The callback attempt remains failed. Callback success is **not** reported, and "sign-in succeeded" is **not** shown. |
| Rejected return candidate | `NEVER_USED`. The rejected callback's intended-return destination is never used, however safe it looks. It remains rejected and is removed under the existing intended-return state semantics. |
| Correlation | The preserved session is not callback correlation and is not proof that this callback succeeded. Recovery navigation is not a correlated resolution of the callback. |
| Authorization | Backend authorization remains authoritative for anything the preserved session is subsequently used for. |
| Presentation | `A2-UI` may show a safe callback-error outcome or a safe route-recovery message. The detail stays generic under the error vocabulary. |
| Final navigation | `/`. No destination derived from the rejected attempt controls the recovery. |

The safe recovery route is independent of the rejected return candidate by
construction: it is a fixed Auth-owned destination, not a validated candidate.
Nothing in this subsection weakens callback replay resistance,
callback-completion correlation, the separation of callback outcome from session
validity, or fail-closed behavior where a pre-existing session's validity is
unknown — in that case the session is `TERMINAL_SESSION_ERROR` and this
subsection does not apply.

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

Error-surface rule, frozen by `A2-SECURITY`: where an operation's error list
below names `INVALID_CALLBACK`, `STATE_VALIDATION_FAILED`,
`PKCE_VALIDATION_FAILED` or `SESSION_EXCHANGE_FAILED`, those are the
**internal** classifications. Across the browser boundary the adapter surfaces
the single public classification `SIGN_IN_FAILED`, with one safe response shape
and equivalent status behavior, carrying no internal validation-stage
identifier and no field from which the failed stage can be inferred. Browser
code never receives the four internal codes, and `A2-UI` must not attempt to
distinguish them. Every other classification is surfaced unchanged.

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
  the storage mechanism is frozen by `AUTH-DEC-050` — it is held only inside the
  server-side `PENDING_ATTEMPT_CORRELATION` record, never in any browser
  persistence — with only the physical storage substrate and topology pending
  `A2-DEPLOYMENT` confirmation. The provider OAuth `state` parameter is never
  used to carry it.
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
  preserved as `AUTHENTICATED`, only the callback attempt fails, and the
  destination returned for safe route recovery is `/` rather than the rejected
  attempt's intended-return destination; where its validity is unknown, the
  session fails closed to `TERMINAL_SESSION_ERROR`. Qualifying a pre-existing
  session as preserved requires the full
  `INDEPENDENTLY_ESTABLISHED_AND_KNOWN_VALID_SESSION` test, including
  authoritative server-side `LIVE_PROVIDER_SESSION_VALIDATION` and
  session-identity equality; anything short of that is `UNPROVEN` and fails
  closed.
- Errors, internal: `INVALID_CALLBACK`, `STATE_VALIDATION_FAILED`,
  `PKCE_VALIDATION_FAILED`, `SESSION_EXCHANGE_FAILED`, `PROVIDER_DENIED`,
  `USER_CANCELLED`, `TEMPORARY_PROVIDER_FAILURE`.
- Errors, browser-visible: the first four collapse to the single public
  classification `SIGN_IN_FAILED` under the `Public failure-oracle boundary`.
  `PROVIDER_DENIED`, `USER_CANCELLED` and `TEMPORARY_PROVIDER_FAILURE` are
  surfaced unchanged.
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
  because one exists. Where a known-valid session is preserved, the destination
  supplied for safe route recovery is `/`.
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
which validation step failed beyond the class itself.

### Public failure-oracle boundary

Frozen by `A2-SECURITY`. The earlier requirement that four classifications
merely "present the same user-facing message" was insufficient: identical copy
still leaks the stage through the classification itself.

These four internal classifications must be **indistinguishable through every
untrusted browser-observable channel**:

- `INVALID_CALLBACK`
- `STATE_VALIDATION_FAILED`
- `PKCE_VALIDATION_FAILED`
- `SESSION_EXCHANGE_FAILED`

| Boundary | Rule |
|---|---|
| Public browser/UI classification | `SIGN_IN_FAILED` — one code for all four. |
| Response shape | One safe shape, identical across all four. |
| Status behavior | Equivalent across all four. |
| Internal validation-stage identifier | Never crosses to the browser. |
| Provider detail | Never crosses to the browser. |
| Any inference-enabling field | Prohibited. No field may allow inference of which internal validation stage failed. |
| Response timing | `SHOULD` be normalized where practical, and `MUST NOT` intentionally reveal the failed validation stage. |

The four internal classifications remain valid and unchanged in meaning. They
are retained for server-side Security events and restricted operational
diagnostics only, and each keeps its existing retry, reauthentication,
resulting-state and Backend-eligibility semantics exactly as tabulated above.
Nothing is removed from the vocabulary.

`A2-UI` is **not** required to distinguish `INVALID_CALLBACK`,
`STATE_VALIDATION_FAILED`, `PKCE_VALIDATION_FAILED` or `SESSION_EXCHANGE_FAILED`
through browser-visible behavior, and must not attempt to. The Auth-owned UI
adapter surfaces `SIGN_IN_FAILED` for all four; `processCallback` and the other
adapter operations return the internal classification only across the
server-side boundary, never to browser code.

The remaining classifications — `USER_CANCELLED`, `PROVIDER_DENIED`,
`SESSION_EXPIRED`, `REFRESH_FAILED`, `SIGN_OUT_FAILED`,
`CONFIGURATION_UNAVAILABLE` and `TEMPORARY_PROVIDER_FAILURE` — are unchanged and
remain individually observable, because none of them discloses which internal
sign-in validation stage failed.

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
    Provider OAuth `state` is not reused as a return-path container. The
    mechanism is frozen by `AUTH-DEC-050` and stated in requirement 28 below;
    only the physical storage substrate and topology remain pending
    `A2-DEPLOYMENT` confirmation.
21. Callback-attempt and session-validity separation: an `INVALID_CALLBACK`
    result never itself invalidates, revokes or signs out a session that was
    independently established before the rejected callback and remains
    known-valid, and never permits that session to be read as proof that the
    callback succeeded. A pre-existing session of unknown validity fails closed.
22. Frozen provider-session cookie posture: browser-readable `@supabase/ssr`
    session, `SameSite=Lax`, `Secure=true` in every non-local environment with
    `http://localhost:3000` as the only exception, host-only, no `Domain`
    attribute, `Path=/`, not `HttpOnly`, provider-managed lifetime and rotation,
    and no custom token copy.
23. CSRF and credential transport: protected FastAPI routes accept credentials
    only through `Authorization: Bearer`; the provider-session cookie is never
    an API credential; no application anti-CSRF token is required merely because
    a FastAPI request is Bearer-authenticated; CORS uses the exact approved
    Dashboard origin with no wildcard and only required headers and methods.
    Every same-origin session-mutating Auth operation is non-`GET`, validates
    the exact `Origin`, applies Fetch Metadata checks where available, and
    validates an Auth-owned anti-CSRF value bound to the current session or to
    the anonymous sign-in attempt. Sign-out is state-changing and CSRF-validated.
    `GET`/`HEAD`/`OPTIONS` Auth endpoints remain side-effect-free. The OAuth
    callback is exempt from the ordinary same-origin anti-CSRF token and instead
    validates OAuth `state`, PKCE, correlation, the exact callback destination
    and intended-return binding before any protected effect.
24. Sign-out scope is `local` — current session only. The broader provider
    default scope is never inherited or used.
25. Production access-token lifetime is at most 900 seconds, and no record
    claims immediate JWT revocation after sign-out.
26. Public failure-oracle boundary: `INVALID_CALLBACK`,
    `STATE_VALIDATION_FAILED`, `PKCE_VALIDATION_FAILED` and
    `SESSION_EXCHANGE_FAILED` are indistinguishable through every untrusted
    browser-observable channel. The browser receives the single public
    classification `SIGN_IN_FAILED`, one safe response shape, equivalent status
    behavior, no internal validation-stage identifier and no field permitting
    inference of the failed stage. Timing should be normalized where practical
    and must never intentionally reveal the stage. The four internal
    classifications survive unchanged for server-side Security events and
    restricted operational diagnostics.
27. Callback-correlation mechanism: Auth-controlled, provider-neutral,
    server-side and ephemeral, supporting atomic transitions, atomic single use,
    expiry, concurrent independent attempts and shared availability across
    runtime instances. The browser carries only a cryptographically random
    opaque handle in a separate Auth-owned cookie that is `HttpOnly`, `Secure`,
    `SameSite=Lax`, host-only and callback-path restricted in every non-local
    environment, and that carries no code, token, verifier, return path,
    provider payload or session. `PENDING_ATTEMPT_CORRELATION` lives at most 10
    minutes from initiation; `COMPLETED_CALLBACK_CORRELATION` lives exactly 120
    seconds from successful completion; the transition is atomic; an unavailable
    store or unverifiable handle fails closed; concurrent tabs get separate
    records that never overwrite one another.
28. Intended-return state is held only in the server-side
    `PENDING_ATTEMPT_CORRELATION` record: validated before storage, bound to one
    attempt, expiring within 10 minutes of initiation, atomically single-use,
    removed on success, failure, abandonment and expiry, and never placed in
    provider OAuth `state`, the provider cookie, the handle cookie, a URL,
    `localStorage`, `sessionStorage`, IndexedDB or any other browser
    persistence. A missing record, integrity failure, replay or store failure
    falls back to `/` without relaxing callback validation.
29. A preserved pre-existing session qualifies as
    `INDEPENDENTLY_ESTABLISHED_AND_KNOWN_VALID_SESSION` only on all four
    conditions, including authoritative server-side
    `LIVE_PROVIDER_SESSION_VALIDATION` and session-identity equality. Cookie
    presence, `getSession()`, a decoded JWT, local signature or expiry checks,
    `getClaims()`, frontend state, a subscription event and the existence of an
    access token are each insufficient alone. Unproven validity fails closed.
30. Auth response cache boundary, XSS and runtime hardening, the Security-event
    boundary and key-custody handling as specified in the four subsections
    below.

### Auth response cache boundary

Classification: `IMPLEMENTATION_REQUIREMENT / NOT_RUNTIME_EVIDENCE`.

Any response that handles authentication, refreshes a session, sets a session
cookie, or processes a callback must be served with:

`Cache-Control: private, no-store`

Authenticated and session-refresh routes must not be served through shared
caches, through ISR-generated shared session responses, or through a shared CDN
cache that contains `Set-Cookie`.

None of this is claimed to be implemented. No repository evidence proves any
cache header, and no runtime is asserted.

### XSS and runtime security requirements

Classification: `IMPLEMENTATION_AND_RELEASE_REQUIREMENTS /
NOT_CURRENT_RUNTIME_EVIDENCE`.

- a strict Content Security Policy;
- no `unsafe-eval`;
- no unrestricted `unsafe-inline`;
- a nonce- or hash-based script policy;
- Trusted Types where the browser supports them;
- no unreviewed third-party scripts on authenticated surfaces;
- dependency and supply-chain scanning;
- no token exposure in the DOM;
- no token exposure to analytics;
- no token exposure to client logs; and
- callback and session route security testing.

These are release requirements, not current runtime evidence. They do **not**
alter the accepted browser-readable provider-session architecture.

### Security-event boundary

Security-required event metadata is `BOUNDED / SECRET_FREE / ATTRIBUTABLE`.

Required semantic fields: `event_id`; `event_version`; `event_name`;
`occurred_at`; `severity`; `environment_class`; `source_component`; `outcome`;
`blocking_effect`; `actor_type`; an approved opaque `actor_reference` or
`UNAUTHENTICATED`; an opaque `sign_in_attempt_reference`; an opaque
`callback_flow_reference`; an opaque `request_reference`; an opaque
`correlation_reference`; `policy_version`; `session_preserved`; a bounded reason
code; and `redaction_status`.

An event must **never** include: an access token; a refresh token; an
authorization code; a PKCE verifier; a cookie; a raw header; a provider payload;
the project reference; a hostname; a full URL; a stack trace; a raw exception;
an email address; a mutable display name; a secret; or a signing key.

Event names, severities and retention classes are recorded where the
authoritative `A2-SECURITY` response supplies them; nothing beyond that is
invented here. The Security-event pipeline is **not** represented as
implemented: no repository runtime evidence proves it, and none is claimed.

### Key-custody implementation requirements

Classification: `IMPLEMENTATION_REQUIREMENT / NOT_RUNTIME_EVIDENCE`.

Opaque-handle integrity requires:

- an approved cryptographic handle-integrity mechanism;
- a server-controlled signing and verification key;
- a randomly generated server key of at least 256 bits where an HMAC-based
  implementation is selected;
- secret-manager custody;
- no `NEXT_PUBLIC` exposure;
- no source-control exposure;
- no logging;
- no browser exposure;
- key rotation supporting both the current and the previous verification key;
- the previous verification key accepted for at most 15 minutes; and
- the previous key never minting new handles.

No key is generated or created here, no secret manager is selected, no runtime
is configured, and no infrastructure is provisioned.

Resolved by `A2-SECURITY` and no longer open: the provider-session cookie
policy including `SameSite` and the `HttpOnly` position, the CSRF policy, the
sign-out scope, the production access-token lifetime bound, the public
failure-oracle boundary, the callback-correlation mechanism and both of its
lifetimes, the intended-return storage and integrity mechanism, and the proof
required for a preserved pre-existing session.

Still **not** decided here: retention periods beyond those stated, event
severities and retention classes not supplied by the authoritative Security
response, the disclosure policy, and production monitoring thresholds. These
remain `A2-SECURITY`-owned review items under `AUTH-DEP-011`. Separately, the
physical storage technology and deployment topology for the correlation store,
the runtime configuration of the cookie posture and the JWT lifetime, the CORS
implementation and the Backend denial behavior are **owner-compatibility**
questions for `A2-DEPLOYMENT` and `A2-BACKEND`, classified
`SECURITY_REQUIRED / PENDING_AFFECTED_OWNER_COMPATIBILITY_REVIEW`. None of them
is recorded as confirmed.

## `AUTH-002` conceptual acceptance fixtures

These are conceptual contract fixtures. They are not runtime tests, and no
runtime test is created by this version. Every fixture below prohibits
disclosure of tokens, authorization codes, PKCE verifiers, and secrets, and
every failing fixture requires fail-closed behavior; both are restated only
where the fixture adds a specific obligation.

| # | Fixture | Initial state | Actor | Operation | Expected transitions | Permitted UI | Prohibited UI | Backend eligible | Classification | Attribution | Owner dependencies |
|---:|---|---|---|---|---|---|---|:-:|---|---|---|
| 1 | Successful sign-in | `UNAUTHENTICATED` | `HUMAN_USER` | `beginSignIn` then `processCallback` | `SIGN_IN_PENDING` → `CALLBACK_PROCESSING` → `AUTHENTICATED` | protected content after success; navigation to the bound, unexpired, single-use return destination, else the default | protected content before success; navigating on a return state that is unbound, expired or already consumed; retaining the return state after completion | yes, after `AUTHENTICATED` | success | canonical user | Deployment provisioning; intended-return state mechanism frozen by `AUTH-DEC-050`, with only the physical storage substrate pending `A2-DEPLOYMENT` |
| 2 | User cancellation | `SIGN_IN_PENDING` | `HUMAN_USER` | abandon at provider | → `UNAUTHENTICATED` | neutral message | error implying system fault | no | `USER_CANCELLED` | `UNAUTHENTICATED` | none |
| 3 | Provider denial | `SIGN_IN_PENDING` | Provider | denial returned | → `UNAUTHENTICATED` | denial without cause | naming the provider reason | no | `PROVIDER_DENIED` | `UNAUTHENTICATED` | Security event shape |
| 4 | Valid callback | `CALLBACK_PROCESSING` | `A2-AUTH` | `processCallback` | → `AUTHENTICATED`; the attempt's `PENDING_ATTEMPT_CORRELATION` state becomes a `COMPLETED_CALLBACK_CORRELATION` record for this exact flow, which remains available for its bounded post-completion window; the return state is consumed and removed | success UX, then validated navigation | leaving the code in the URL; treating a session as proof of completion; retaining a consumed return state; discarding the completed correlation record at the instant of success | yes | success | canonical user | correlation-record mechanism, representation and lifetimes frozen by `AUTH-DEC-049`; physical storage substrate and topology pending `A2-DEPLOYMENT` |
| 4a | Duplicate callback invocation, correlated, inside the post-completion window | `AUTHENTICATED` after fixture 4, same flow re-entered | `HUMAN_USER` | `processCallback` | no state change; the completed correlation record is matched and the previously completed outcome is reused | the already-established session | a second code exchange; a second session; reporting a new sign-in; requiring a re-exchange because the record was removed at completion | yes | success | canonical user | correlation-record mechanism, representation and lifetimes frozen by `AUTH-DEC-049`; physical storage substrate and topology pending `A2-DEPLOYMENT` |
| 4b | Duplicate or unrelated callback invocation, uncorrelated, with an independently established, known-valid session present | `AUTHENTICATED` | Attacker or unrelated navigation | `processCallback` | callback attempt fails; no session created; no exchange; callback parameters cleared; rejected attempt's return state removed; the pre-existing known-valid session is preserved and remains `AUTHENTICATED`; safe route recovery navigates to `/` | safe callback-error outcome or safe route recovery to `/` | resolving the invocation because a session exists; navigating to the rejected attempt's intended-return destination; any code exchange; any callback-directed navigation; reporting callback success; revoking or signing out the pre-existing session because the callback was invalid | unchanged for the preserved session, with FastAPI authoritative | `INVALID_CALLBACK` | canonical user of the preserved session | Security event shape |
| 4b-i | Uncorrelated callback with no independently valid pre-existing session, or one whose validity cannot be proven | `UNAUTHENTICATED`, or a session of unknown validity | Attacker or unrelated navigation | `processCallback` | callback attempt fails; no session created; no exchange; callback parameters cleared; → `TERMINAL_SESSION_ERROR` | generic sign-in failure | any protected content; treating unknown validity as valid | no | `INVALID_CALLBACK` | `UNAUTHENTICATED` | Security event shape |
| 4c | Reload after successful callback processing | `AUTHENTICATED`, callback URL reloaded | `HUMAN_USER` | `processCallback` | resolves to the established session while the `COMPLETED_CALLBACK_CORRELATION` record for that exact flow is still inside its bounded post-completion window; once that window has expired or the record is gone, the callback attempt fails with no exchange and no callback-directed navigation, and the session outcome follows fixtures 4b and 4b-i | protected content only on matched correlation | assuming completion from session existence alone; re-exchanging the consumed code; treating the expired window as authorization to retry | conditional | success while correlated, otherwise `INVALID_CALLBACK` | canonical user, or `UNAUTHENTICATED` where no valid session is preserved | correlation-record mechanism, representation and lifetimes frozen by `AUTH-DEC-049`; physical storage substrate and topology pending `A2-DEPLOYMENT` |
| 5 | Invalid state | `CALLBACK_PROCESSING` | Attacker or corruption | `processCallback` | → `TERMINAL_SESSION_ERROR` | generic sign-in failure | distinguishing this from fixture 6 | no | `STATE_VALIDATION_FAILED` | `UNAUTHENTICATED` | Security event shape |
| 6 | Invalid or missing PKCE proof | `CALLBACK_PROCESSING` | Attacker, or a different device | `processCallback` | → `TERMINAL_SESSION_ERROR` | generic sign-in failure | distinguishing this from fixture 5 | no | `PKCE_VALIDATION_FAILED` | `UNAUTHENTICATED` | Security event shape |
| 7 | Callback replay | `AUTHENTICATED` or `UNAUTHENTICATED` | Attacker | replay a consumed code | no new session; no new code exchange; no callback-directed navigation; callback parameters cleared; Security event produced; an independently established, known-valid session is preserved as `AUTHENTICATED` with safe route recovery to `/`, while an absent or unprovable one resolves to `TERMINAL_SESSION_ERROR` | generic sign-in failure, or safe route recovery to `/` where a session is preserved | reporting a new sign-in; navigating to the replayed attempt's intended-return destination; resolving successfully because a valid session already exists; re-exchanging the consumed code; revoking or signing out a separately valid session because the replay was rejected | no while `TERMINAL_SESSION_ERROR`; unchanged for a preserved session | `INVALID_CALLBACK` | `UNAUTHENTICATED`, or the canonical user of a preserved session | Security event shape |
| 8 | Expired callback | `CALLBACK_PROCESSING`, entered from a sign-in that began at `UNAUTHENTICATED` or `RECOVERABLE_ERROR`, so no independently established session pre-exists | `HUMAN_USER` | late `processCallback` | → `TERMINAL_SESSION_ERROR`, by the no-pre-existing-session row of the conditional rule rather than by an unconditional one | generic sign-in failure with a sign-in affordance | automatic retry of the exchange | no | `INVALID_CALLBACK` | `UNAUTHENTICATED` | none |
| 9 | Session restoration after reload | `AUTHENTICATED`, page reloaded on a non-callback route | `HUMAN_USER` | application start | `INITIALIZING` → `AUTHENTICATED` | protected content after resolution | protected content while `INITIALIZING`; treating the restored session as proof that any callback completed | yes, after resolution | success | canonical user | framework proxy/middleware layer |
| 10 | Proactive refresh while the credential remains provable | `AUTHENTICATED`, token near expiry but still valid | system | protected request | → `REFRESH_PENDING` mode `PROVEN_CREDENTIAL` | existing protected content may remain visible | sending a token known to be expired; beginning a new privileged effect on an expired token | deferred — new protected requests wait for the outcome | none if refresh succeeds | canonical user | none |
| 10a | Refresh after expiry, `401`, or unprovable credential | `AUTHENTICATED` in UI belief; token expired, Backend returned `401`, or session validity unknown | system | protected request | → `REFRESH_PENDING` mode `UNPROVEN_CREDENTIAL` | neutral pending affordance only | any protected content; any protected interaction; any protected request; treating this identically to fixture 10 | no — prohibited, not deferred | none if refresh succeeds, otherwise `REFRESH_FAILED` or `SESSION_EXPIRED` | canonical user | none |
| 11 | Successful refresh | `REFRESH_PENDING`, either mode | `A2-AUTH` | `refreshSession` | → `AUTHENTICATED` | resume, retry the request once; restore protected content only after the successful outcome | more than one retry; restoring protected content while the outcome is unknown | yes | success | canonical user | none |
| 12 | Refresh failure | `REFRESH_PENDING`, either mode | `A2-AUTH` | `refreshSession` | → `TERMINAL_SESSION_ERROR` | "sign in again" | any protected request; any retry; leaving mode-`PROVEN_CREDENTIAL` content on screen after the failure | no | `REFRESH_FAILED` | canonical user | Security event shape |
| 13 | Concurrent refresh requests within one context | `AUTHENTICATED`, several protected requests in flight in one browsing context | system | several `getAccessTokenForApiRequest` | one refresh, one shared outcome within that context | one pending affordance | two independent exchanges from the same context | deferred then yes or no | shared outcome | canonical user | none |
| 13a | Concurrent refresh across contexts | `AUTHENTICATED` in two tabs, or a tab plus a parallel server request | system | refresh in each context | not serialized; outcomes may include a stale cookie, a temporarily null session, or one success plus one rejection | one pending affordance per context; at most one bounded retry after a newer valid session is observed | claiming global single-flight; restoring stale authenticated state; speculative retry; any automatic refresh loop | no while unresolved | shared outcome where observable, otherwise fail closed | canonical user | provider cookie synchronization behavior; `A2-SECURITY` and `A2-INTEGRATION` confirmation |
| 14 | Sign-out | `AUTHENTICATED` | `HUMAN_USER` | `signOut` | → `SIGN_OUT_PENDING` → `UNAUTHENTICATED` | public surfaces | any stale protected content | no | success | canonical user | sign-out scope frozen as `local` by `AUTH-DEC-047`; `A2-BACKEND` and `A2-DEPLOYMENT` confirmation outstanding |
| 15 | Sign-out failure | `SIGN_OUT_PENDING` | provider or network | remote failure | → `UNAUTHENTICATED` regardless | "signed out on this device" | claiming the session persists; claiming issued tokens were revoked | no | `SIGN_OUT_FAILED` | canonical user | Security event shape |
| 16 | Unsafe return URL | `CALLBACK_PROCESSING` with a hostile return path | Attacker | `processCallback` | → `AUTHENTICATED` | navigation to the default destination | navigation to the supplied path | yes | success with fallback | canonical user | Security event shape |
| 16a | Unbound, expired or replayed return state that is syntactically safe | `CALLBACK_PROCESSING` with a well-formed relative path that is not bound to this attempt, has expired, or was already consumed | Attacker or stale state | `processCallback` | → `AUTHENTICATED`; the return state is discarded and removed | navigation to the default post-sign-in destination | accepting the path because it is syntactically safe; reusing a consumed return state; retaining it after completion | yes | success with fallback | canonical user | intended-return state mechanism frozen by `AUTH-DEC-050`, with only the physical storage substrate pending `A2-DEPLOYMENT` |
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

Two `A2-SECURITY` corrections apply across every fixture above and are not
restated per row. First, wherever a fixture records a "generic sign-in failure"
arising from `INVALID_CALLBACK`, `STATE_VALIDATION_FAILED`,
`PKCE_VALIDATION_FAILED` or `SESSION_EXCHANGE_FAILED`, the browser-observable
outcome is the single public classification `SIGN_IN_FAILED` with one safe
response shape and equivalent status behavior; the internal classification named
in the fixture is the server-side one. A fixture is not satisfied if any
browser-observable difference distinguishes those four. Second, wherever a
fixture preserves a pre-existing session — 4b and 7 in particular — preservation
is satisfied only when the full
`INDEPENDENTLY_ESTABLISHED_AND_KNOWN_VALID_SESSION` test passes, including
authoritative server-side `LIVE_PROVIDER_SESSION_VALIDATION` and
session-identity equality. Cookie presence or a decoded token satisfies neither
fixture, and an unproven session resolves to 4b-i instead.

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

### Version `1.2.0-draft.1` classification

| Field | Value |
|---|---|
| Old version | `1.1.0-draft.1` |
| New version | `1.2.0-draft.1` |
| Change category | `ADDITIVE_COMPATIBLE_MINOR` |
| Breaking | `NO` |

Verified against this section's own rules. The `AUTH-005` normative corrections finalized in `1.2.0-draft.1` change none of the listed breaking items: issuer-subject uniqueness is untouched; issuer normalization and exact case-sensitive comparison are untouched; no external ID becomes an internal ID; no actor type is removed; the exact user-installation-repository access tuple is unchanged; no local credential is permitted; no cross-installation or cross-repository access is permitted; no lifecycle change re-enables denied access; and no organization tenancy or generic RBAC is introduced. The additions formalize session fence validation, sign-out fence semantics (`SIGN_OUT_WINS`), context/binding handles, local sign-out tombstone, synchronization authority requirements, UI host boundary (`POST /auth/session-fence`), security event follow-up, and future integration test requirements.

Historical references to `1.1.0-draft.1` remain historical in past records and past decision logs and are not rewritten as though they originally referred to `1.2.0`.

Compatibility impact: existing consumers of `1.1.0-draft.1` and `1.0.0-draft.2` require no database migration, no new column, and no new table. `DB-002` remains `ACKNOWLEDGED_AND_IMPLEMENTED`.

Consumer-review consequence: all required consumer reviews for `AUTH-005` / `1.2.0-draft.1` are complete: `A2-UI` (`ACCEPTED_WITH_CONSTRAINTS`), `A2-SECURITY` (`ACCEPTED_WITH_CONSTRAINTS`), `A2-DEPLOYMENT` (`ACCEPTED_WITH_CONSTRAINTS`), and `A2-INTEGRATION` (`ACCEPTED_WITH_CONSTRAINTS`). No consumer requested a further normative Auth-contract correction.

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
13. Stale provider cookie material arriving after a sign-out fence MUST NOT qualify as an established or usable session (`SIGN_OUT_WINS`).
14. An old callback response bound to a superseded Auth-context generation (e.g. attempt A under generation G where sign-out and reconciliation advanced context to a newer generation before attempt B) MUST fail closed without establishing a session or clearing a local tombstone. A later sign-in attempt under the same current generation does NOT invalidate an earlier independently correlated attempt.
15. `getAccessTokenForApiRequest` MUST fail closed when invoked with a stale fence or active tombstone.
16. Local process-local authority state loss on restart MUST cause session verification to fail closed, requiring reauthentication.
17. Multi-tab fence invalidation MUST cause all open tabs in a browser context to lose session establishment immediately upon sign-out fence publication.

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
- The concrete default post-sign-in destination is frozen as `/`
  (`A2_UI_PROPOSED / A2_AUTH_APPROVED`), and `/` is likewise frozen as the
  preserved-session rejected-callback safe recovery destination. See
  `AUTH-DEC-043`. Freezing these two destinations does not accept the contract
  and does not close `AUTH-DEP-012`.

Open:

- Provider runtime is `NOT_PROVISIONED / NOT_TESTED`: no Supabase project,
  GitHub OAuth provider configuration, Vercel project, production Dashboard
  hostname, TLS verification, production callback registration, or injected
  secret is proven by this repository.
- JWT runtime validation is not implemented or tested.
- Retention periods beyond those frozen, event severities and retention classes
  not supplied by the authoritative Security response, the disclosure policy and
  production monitoring thresholds remain unresolved `A2-SECURITY` decisions.
  See `AUTH-DEP-011`. The cookie policy, `SameSite` value, `HttpOnly` position,
  CSRF policy, sign-out scope, production access-token lifetime bound, public
  failure-oracle boundary, callback-correlation mechanism and lifetimes,
  intended-return mechanism and preserved-session proof are **no longer** open:
  `A2-SECURITY` decided them, and they are recorded above as frozen policy.
- The physical storage technology and the deployment topology for the
  server-side ephemeral correlation store are `SECURITY_REQUIRED /
  PENDING_AFFECTED_OWNER_COMPATIBILITY_REVIEW` by `A2-DEPLOYMENT`. The mechanism
  class, capabilities and lifetimes are frozen; no vendor, product or physical
  technology is selected by this contract. See `AUTH-DEP-011`, `AUTH-DEP-013`
  and `AUTH-ISSUE-025`.
- The cache-control boundary, the XSS and runtime hardening requirements, the
  Security-event boundary and the key-custody requirements are recorded as
  implementation and release requirements, **not** as runtime evidence. Nothing
  in this repository proves any of them is implemented, and none is claimed.
- Refresh serialization across browser tabs, parallel server requests and
  separate runtime instances is **not** guaranteed by the accepted provider
  design and is not claimed anywhere in this contract. The observable behavior
  of concurrent cross-context refresh under `@supabase/ssr` cookie
  synchronization is `NOT_TESTED`. See `AUTH-DEP-011`, `AUTH-DEP-015` and
  `AUTH-ISSUE-026`.
- The Backend authenticated-context handoff, the exact `403` versus
  concealed-`404` policy, CORS, and the Backend token-verification retry policy
  are unresolved. See `AUTH-DEP-006` and `AUTH-DEP-014`.
- The provider sign-out scope is frozen as `local` and the production
  access-token lifetime bound is frozen at `<= 900 seconds`. Both require
  `A2-BACKEND` and `A2-DEPLOYMENT` compatibility confirmation, which has **not**
  been given: `SECURITY_REQUIRED / PENDING_AFFECTED_OWNER_COMPATIBILITY_REVIEW`.
  Neither is claimed to be configured.
- GitHub access-verification freshness is not frozen.
- `A2-UI` has responded to this draft with `SPECIFICATION_CONFLICT` under
  `AUTH-002-CONSUMER-REVIEW-A2-UI-001` against head `7abe17a`. The response is
  received, not accepted: `AUTH-DEP-012` remains `OPEN`. Two corrections were
  authorized, one per owner. The Auth-owned correction — the frozen `/` default
  and the frozen `/` preserved-session safe recovery — is applied in this text.
  The UI-owned correction to the merged `UI-DEC-013` custody meaning is
  `A2-UI`-owned and is not performed here. Closure requires `A2-UI` rereview of
  the corrected head and an acceptable disposition.
- `A2-SECURITY` has responded to this draft with `REJECTED_WITH_REASON` under
  `AUTH-002-CONSUMER-REVIEW-A2-SECURITY-001` against head `7abe17a`, requiring
  seven normative corrections. All seven are applied above. The response is
  received, not accepted: `AUTH-DEP-011` remains `OPEN`, and `A2-SECURITY`
  rereview of the corrected head is required. Applying a required correction is
  not the correcting party's acceptance of it.
- `A2-BACKEND` compatibility is unconfirmed for Bearer-only credential
  transport, the provider cookie not being an API credential, exact-origin CORS,
  the `<= 900`-second production access-token lifetime, post-sign-out residual
  JWT validity, the one-refresh-plus-one-retry boundary and Backend denial
  behavior. `A2-DEPLOYMENT` compatibility is unconfirmed for `Secure` provider
  cookies, host-only configuration, `Path=/`, the exact `localhost` `Secure`
  exception, the production JWT lifetime, callback infrastructure, the
  server-side ephemeral correlation-store capability, secret injection, key
  rotation, cache safety and deployment topology. All are
  `SECURITY_REQUIRED / PENDING_AFFECTED_OWNER_COMPATIBILITY_REVIEW`.
- This contract is documentation, not Auth runtime implementation. Auth
  runtime, frontend Auth behavior, provider runtime, and Backend JWT behavior
  are `NOT_IMPLEMENTED / NOT_TESTED`.
- Version `1.1.0-draft.1` requires `A2-UI`, `A2-SECURITY`, `A2-DEPLOYMENT`,
  `A2-BACKEND`, and `A2-INTEGRATION` consumer review before it may be treated
  as accepted. It is `NOT_IMPLEMENTATION_READY`, and it authorizes no
  implementation, no `UI-004`, and no `AUTH-003`.
