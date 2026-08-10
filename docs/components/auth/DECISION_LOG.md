# Auth Decision Log

- Date: 2026-08-10
- Current task:
  `AUTH-006-FINALIZE-CONTRACT-AUTH-001-V1.2.0-DRAFT.1-001-A3-R3`
- Authorized manager task:
  `AUTH-006-FINALIZE-CONTRACT-AUTH-001-V1.2.0-DRAFT.1-001`
- Authorizing coordinator:
  `Agent 1`
- Baseline: `5ffa8994b286e85d9f676336dbe0169cfbc89d2c`
- Worktree: `/Users/omkar/Documents/TestGap-Miner-wt-auth-contract-1.2-finalization`
- Branch: `agent2/auth-contract-1.2-finalization`
- Target contract: `CONTRACT-AUTH-001@1.2.0-draft.1`
- Scope: `AUTH_DURABLE_RECORDS_AND_CONTRACT_ONLY`
- Auth identity persistence: `VERIFIED_COMPLETE` and merged
- Auth runtime status: `EXISTING_MERGED_CODE_IN_APPS_WEB_SRC_AUTH / AUTH_006_RUNTIME_MODIFICATION_AUTHORIZED=NONE / FENCE_CORRECTION_RUNTIME=NOT_YET_AUTHORIZED`
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

`AUTH-002-A2-UI-CONSUMER-CONFLICT-CORRECTION-001-A3` adds `AUTH-DEC-042` and
`AUTH-DEC-043`, reconciling the first consumer response this contract has ever
received. `AUTH-DEC-042` records that response — `A2-UI`,
`AUTH-002-CONSUMER-REVIEW-A2-UI-001`, reviewed head `7abe17a`, disposition
`SPECIFICATION_CONFLICT` — and its two owner-split corrections. `AUTH-DEC-043`
applies the Auth-owned half by freezing `/` as the default post-sign-in
destination and as the preserved-session rejected-callback safe recovery
destination. Neither decision accepts the contract, closes `AUTH-DEP-012`,
converts the A2-UI disposition, performs or completes the UI-owned correction,
or authorizes any implementation. The contract version identifier remains
`1.1.0-draft.1` and the classification remains `ADDITIVE_COMPATIBLE_MINOR`,
again because the draft is unaccepted and no accepted consumer implemented
against a prior default value.

`AUTH-002-CONSUMER-CORRECTION-UI-SECURITY-001-A3` supersedes that narrower task
and consolidates it with the `A2-SECURITY` response. `AUTH-DEC-042` and
`AUTH-DEC-043` are **preserved unchanged** and are not duplicated or rewritten.
The consolidated task adds `AUTH-DEC-044` through `AUTH-DEC-051`:
`AUTH-DEC-044` records the `A2-SECURITY` response — reviewed head `7abe17a`,
disposition `REJECTED_WITH_REASON`, seven required normative corrections — and
`AUTH-DEC-045` through `AUTH-DEC-051` apply those seven corrections in order:
the frozen provider-session cookie posture; the CSRF and credential-transport
boundary; `local` sign-out scope with the `<= 900`-second production
access-token bound; the public `SIGN_IN_FAILED` failure-oracle boundary; the
server-side ephemeral callback-correlation mechanism with its two frozen
lifetimes; the server-side intended-return state; and the live-provider proof
required before a pre-existing session counts as known-valid.

Every one of the eight restricts behavior or resolves a slot the draft left
explicitly open. None removes an error classification, none changes an existing
classification's retry, reauthentication or Backend-eligibility meaning, and
none weakens the prohibited-storage list — which is extended instead. The
contract version identifier remains `1.1.0-draft.1` and the classification
remains `ADDITIVE_COMPATIBLE_MINOR`, independently verified against the
contract's own versioning rules and consistent with `A2-SECURITY`'s own
classification of its corrections as pre-acceptance changes requiring no version
increase. No previously merged historical decision is rewritten. These decisions
authorize no Auth code, test, configuration, `UI-004`, Backend work, Deployment
work or provider provisioning.

`AUTH-002-CONSUMER-CORRECTION-UI-SECURITY-001-A3-PR30` adds `AUTH-DEC-052` and
rewrites no decision from `AUTH-DEC-001` through `AUTH-DEC-051`. It records
external merged evidence only: the UI-owned half of the `A2-UI` conflict is
`CORRECTED_AND_MERGED` as `UI-DEC-026` and `UI-DEC-027` via pull request #30 —
implementation commit `30deb92000a20d3837b2423b6bdee3ea3335a7f1`, merge commit
`63093f22c37a0fc6affe168f7d5230107b05cdf3`, the current `origin/main`. PR #30
changed six UI durable-record files and no `docs/components/auth/**` path, so no
rebase, merge, cherry-pick or other history reconciliation was performed on the
Auth branch. The historical `SPECIFICATION_CONFLICT` disposition against Auth
head `7abe17af` is unchanged and still stands against that head. `AUTH-DEP-012`
stays `OPEN` and `NOT_ACCEPTED`, `AUTH-ISSUE-027` stays `OPEN`, `A2-UI` and
`A2-SECURITY` rereviews of the corrected Auth head remain required, `UI-004`
remains `NOT_AUTHORIZED`, and no Backend or Deployment acceptance is created.
The contract version identifier remains `1.1.0-draft.1`, the classification
remains `ADDITIVE_COMPATIBLE_MINOR`, and this decision authorizes no code, test,
configuration, implementation or provisioning.

`AUTH-002-FINAL-READINESS-RECONCILIATION-001-A3` adds `AUTH-DEC-053`. It records
that all five affected owner reviews against corrected HEAD `84ad9e322d886f8963c34386f87074a444b3fa2b`
are complete (`A2-UI`, `A2-SECURITY`, `A2-BACKEND`, `A2-DEPLOYMENT`, `A2-INTEGRATION` all returned
`ACCEPTED_WITH_CONSTRAINTS`). No normative Auth correction remains. Shared registry correction is merged via PR #31
(`a80145e2` / `1057ba72`), reconciling `AUTH-DEP-003` to `COMPLETE / VERSION_AWARE_SHARED_REGISTRY_RECONCILED`
and `AUTH-ISSUE-002` to `CLOSED / VERSION_AWARE_REGISTRY_RECONCILED`. Historical responses at `7abe17af` are preserved as historical provenance. `CONTRACT-AUTH-001.md` content remains untouched (`8ed2154561785566b4b17baa16535e1fad8e662c`). Old non-normative consumer status provenance embedded in `CONTRACT-AUTH-001.md` is superseded for coordination purposes by the corrected-head reviews against `84ad9e322d886f8963c34386f87074a444b3fa2b`. Implementation remains unauthorized; PR #29 remains DRAFT pending final Agent 1 readiness decision.

`AUTH-006-FINALIZE-CONTRACT-AUTH-001-V1.2.0-DRAFT.1-001-A3-R1` adds `AUTH-DEC-054` through `AUTH-DEC-066`. It finalizes `CONTRACT-AUTH-001@1.2.0-draft.1` incorporating accepted `AUTH-005` normative corrections across `A2-UI`, `A2-SECURITY`, `A2-DEPLOYMENT`, and `A2-INTEGRATION` (all `ACCEPTED_WITH_CONSTRAINTS`) along with R1 targeted corrections (`AUTH-DEC-062` through `AUTH-DEC-066`: callback generation supersession, sign-out tombstone ordering before publication, new-sign-in reconciliation, session-binding record exclusions, response fence non-mutation, and reconciled current runtime status). It formalizes `SIGN_OUT_WINS`, `ESTABLISHED_AUTH_SESSION` criteria, opaque context/binding handles, local sign-out tombstone, UI host boundary (`POST /auth/session-fence`), security constraints, sync authority requirements, security event follow-up (local non-noop sink required, enrichment follow-up), and 11 future integration test requirements. Contract version is raised to `1.2.0-draft.1`. Contract status is `FINALIZED_CONTRACT_DRAFT_FOR_A2_REVIEW`. Historical references to `1.1.0-draft.1` remain historical. Runtime modification under this task remains strictly `NOT_AUTHORIZED`.

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

**Superseded pending-state note — historical, not current.** The
`PENDING_A2_SECURITY_ACCEPTANCE` statement above records the state at the time
this decision was written. It is not the current state: `A2-SECURITY` has since
frozen the correlation mechanism, its required strength and both of its
lifetimes as policy in `AUTH-DEC-049`. The decision meaning above is unchanged;
only its then-pending Security residue is superseded.

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

**Superseded pending-state note — historical, not current.** The
`PENDING_A2_SECURITY_ACCEPTANCE` statement above records the state at the time
this decision was written. It is not the current state: `A2-SECURITY` has since
frozen the intended-return storage and integrity mechanism as policy in
`AUTH-DEC-050` — the return path is held only inside the server-side
`PENDING_ATTEMPT_CORRELATION` record and never in any browser persistence — and
the provider OAuth `state` prohibition stands unchanged. Only the physical
storage substrate and topology remain pending, and they are `A2-DEPLOYMENT`'s,
not `A2-SECURITY`'s. The decision meaning above is unchanged.

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

**Superseded pending-state note — historical, not current.** The
`PENDING_A2_SECURITY_ACCEPTANCE` statement above records the state at the time
this decision was written. It is not the current state: `A2-SECURITY` has since
frozen the mechanism, the representation and both lifetimes as policy in
`AUTH-DEC-049` — `PENDING_ATTEMPT_CORRELATION` at most 10 minutes from sign-in
initiation, `COMPLETED_CALLBACK_CORRELATION` exactly 120 seconds from successful
completion, an atomic transition, and fail-closed behavior on an unavailable
store or an unverifiable handle. Only the physical storage substrate and
topology remain pending, and they are `A2-DEPLOYMENT`'s, not `A2-SECURITY`'s.
The two-phase lifecycle meaning above is unchanged.

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

## `AUTH-DEC-042` — The A2-UI consumer response is `SPECIFICATION_CONFLICT`

Records the first consumer response ever returned against
`CONTRACT-AUTH-001@1.1.0-draft.1`.

| Field | Value |
|---|---|
| Consumer | `A2-UI` |
| Review task | `AUTH-002-CONSUMER-REVIEW-A2-UI-001` |
| Reviewed head | `7abe17af8e212bd2127160338ea6ef409da02101` |
| Pull request | #29 — `OPEN / DRAFT / NOT_MERGED` |
| Disposition | `SPECIFICATION_CONFLICT` |
| Agent 1 decision | `PASS / A2_UI_SPECIFICATION_CONFLICT_ACCEPTED / AUTH_OWNED_CORRECTIONS_AUTHORIZED` |

The disposition is authoritative for the head it was returned against. It is not
restated here, or anywhere else in the Auth records, as `ACCEPTED` or
`ACCEPTED_WITH_CONSTRAINTS`. Head `7abe17a` was rejected.

A2-UI reported the draft otherwise substantially consumable and accepted these
UI-facing contract areas: callback ownership; the nine-state session model; the
two `REFRESH_PENDING` modes; the `processCallback` abstraction with atomic
final-session observability; the `getAccessTokenForApiRequest` boundary; the
eleven Auth error classifications; indistinguishable presentation of the four
protected sign-in failures; relative-path-only redirects; fail-closed
protected-content handling; callback reload semantics; bounded callback
correlation; preserved-session callback-failure separation; UI route protection
as defense-in-depth; and no UI authorization authority.

Two blocking corrections were recognized, and ownership is split.

**Cookie conflict — UI-owned.** The merged `UI-DEC-013` prohibition on
non-`HttpOnly` cookies conflicts with the canonical browser-readable
`@supabase/ssr` session architecture this contract requires. `A2-UI` is
separately authorized by Agent 1 to supersede that conflicting current meaning
while preserving `UI-DEC-013`'s `localStorage` prohibition, its `sessionStorage`
prohibition and its duplicate-store prohibition. That work is not owned by Auth,
is not performed by this decision, and is not recorded as complete. No UI file
was modified. The browser-readable cookie posture itself remains
`PENDING_A2_SECURITY_ACCEPTANCE`; no A2-SECURITY acceptance is claimed.

**Frozen default and recovery route — Auth-owned.** Auth had not frozen the
concrete route A2-UI proposed. `AUTH-DEC-043` freezes it.

Every Auth custody requirement stands unchanged: the canonical Auth-owned
`@supabase/ssr` cookie-backed session; `createBrowserClient` as the approved
browser adapter; no access token and no refresh token in `localStorage`; no
access token and no refresh token in `sessionStorage`; no duplicate custom
token or session store; and no refresh token ever sent to FastAPI.

`AUTH-DEP-012` remains `OPEN` and `NOT_ACCEPTED`. Authorizing both owners to
correct is not closure. Closure requires the A2-UI correction to pass its own
manager review and merge, this Auth correction to pass A2-AUTH review and be
pushed, and `A2-UI` to rereview the corrected PR #29 head and return an
acceptable disposition. This decision authorizes no implementation, no `UI-004`,
and no runtime work.

> **Later state — recorded, not rewritten.** The text of `AUTH-DEC-042` above is
> the record as of the `A2-UI` response and is unchanged. Two of its statements
> have since been overtaken by external merged evidence and are read as
> historical: the UI-owned correction, described above as not performed and not
> complete, has since been merged by its owner as `UI-DEC-026`/`UI-DEC-027` via
> PR #30; and the browser-readable cookie posture, described above as
> `PENDING_A2_SECURITY_ACCEPTANCE`, was subsequently frozen as policy by
> `AUTH-DEC-045`. See `AUTH-DEC-052`. The `SPECIFICATION_CONFLICT` disposition
> against head `7abe17af` is **not** affected by either and still stands.

## `AUTH-DEC-043` — Default and preserved-session safe-recovery destination frozen to `/`

Freezes the concrete route left open by the earlier draft.

| Item | Value | Classification |
|---|---|---|
| Default post-sign-in destination | `/` | `A2_UI_PROPOSED / A2_AUTH_APPROVED` |
| Preserved-session rejected-callback safe recovery destination | `/` | `A2_UI_PROPOSED / A2_AUTH_APPROVED` |
| Rejected intended-return destination | `NEVER_USED` | unchanged prohibition, now explicit |

Rationale for `/`: it already exists; it is the implemented Overview
destination; it is same-origin; it depends on no Runs, Evidence, Benchmarks,
API-runtime or Auth-specific feature route; and it is therefore safe when
intended-return state is missing or rejected.

`/` is the fallback, not a replacement for intended-return validation. A valid
intended-return state may still select an allowed route under the existing
contract rules, which are unchanged: attempt binding, expiry, single use,
integrity, the disallowed-route rule, and the relative-path format rules all
continue to apply exactly as before. `/` is used when no usable intended-return
destination exists.

The second half of this decision governs one narrow condition: a callback
attempt is rejected, a session independently established before that callback
remains known-valid, the callback itself reports failure, and that session
remains `AUTHENTICATED`. In that condition:

- the safe recovery destination is `/`;
- callback success is **not** reported and "sign-in succeeded" is **not** shown;
- the rejected callback's intended-return destination is **never** used;
- the rejected intended-return state remains rejected and is removed under the
  existing contract semantics;
- the preserved session is **not** callback correlation and is **not** proof
  that this callback succeeded;
- Backend authorization remains authoritative;
- `A2-UI` may display a safe callback-error outcome or a safe route-recovery
  message; and
- final recovery navigation is `/`, controlled by no destination carried by the
  rejected attempt.

The safe recovery route is independent of the rejected return candidate by
construction, because it is a fixed Auth-owned destination rather than a
validated candidate.

Nothing here weakens callback replay resistance, callback-completion
correlation, the separation of callback outcome from session validity, or
fail-closed behavior where a pre-existing session's validity is unknown — that
case remains `TERMINAL_SESSION_ERROR` and this recovery does not apply to it.
Open-redirect protections, session-validity semantics and FastAPI authority are
unchanged. No Security mechanism is chosen here: `SameSite`, the CSRF
mechanism, callback-correlation storage and duration, intended-return storage
and integrity, sign-out scope and residual access-token lifetime all remain
pending their owning components.

## `AUTH-DEC-044` — The A2-SECURITY consumer response is `REJECTED_WITH_REASON`

Records the second consumer response returned against
`CONTRACT-AUTH-001@1.1.0-draft.1`.

| Field | Value |
|---|---|
| Consumer | `A2-SECURITY` |
| Review task | `AUTH-002-CONSUMER-REVIEW-A2-SECURITY-001` |
| Reviewed head | `7abe17af8e212bd2127160338ea6ef409da02101` |
| Pull request | #29 — `OPEN / DRAFT / NOT_MERGED` |
| Disposition | `REJECTED_WITH_REASON` |
| Required normative corrections | seven |
| Agent 1 decision | `PASS / A2_SECURITY_REJECTION_ACCEPTED / CONSOLIDATED_AUTH_CORRECTION_AUTHORIZED` |

The disposition is authoritative for the head it was returned against and is not
restated anywhere as acceptance. Head `7abe17a` was rejected.

In rejecting that head, `A2-SECURITY` explicitly **accepted the selected
architecture**: `SUPABASE_AUTH_WITH_GITHUB_OAUTH`; the `@supabase/ssr`
integration; `createBrowserClient` and `createServerClient`; one provider-owned
cookie-backed session as the sole canonical session source; a browser-readable
provider-session cookie; and required PKCE. The provider session is therefore
not redesigned as `HttpOnly`-only, and browser persistence is not reverted to a
`createClient` `localStorage` model. Every prohibited-storage rule stands and is
extended, never weakened: no access or refresh token in `localStorage` or
`sessionStorage`; no React, context, Redux, Zustand, IndexedDB, service-worker
or custom-cookie token store; no duplicate session store; and no refresh token
forwarded to FastAPI.

The seven required corrections are recorded as `AUTH-DEC-045` through
`AUTH-DEC-051`. All seven are applied. Applying a required correction is not the
requiring consumer's acceptance of it: `AUTH-DEP-011` remains `OPEN` and
`NOT_ACCEPTED`, and `A2-SECURITY` rereview of the corrected PR #29 head is
required. This decision authorizes no implementation, no `UI-004`, no
`AUTH-003`, no Backend work, no Deployment work and no provider provisioning.

## `AUTH-DEC-045` — Provider-session cookie posture frozen

Security correction 1. The cookie posture was previously an Auth proposal with
`SameSite` and the `HttpOnly` position left to Security. It is now frozen
policy.

| Attribute | Frozen value |
|---|---|
| Session | official `@supabase/ssr` provider session |
| Readability | `BROWSER_READABLE` |
| `SameSite` | `Lax` |
| `Secure` | `true` in every non-local environment |
| Host scope | host-only |
| `Domain` | absent |
| `Path` | `/` |
| `HttpOnly` | not `HttpOnly` under the selected browser-readable architecture |
| Lifetime and rotation | provider-managed |
| Duplicate copies | none |

The only permitted `Secure=false` case is `http://localhost:3000`. It does not
extend to preview environments, LAN hostnames, public tunnels, alternate HTTP
hosts, staging over HTTP or production over HTTP.

Ownership: `A2-SECURITY` holds `POLICY_ACCEPTANCE`; `A2-AUTH` holds
`AUTH_SEMANTICS`; `A2-DEPLOYMENT` holds
`RUNTIME_AND_CONFIGURATION_CONFIRMATION`, which has **not** been given. That
confirmation is `SECURITY_REQUIRED /
PENDING_AFFECTED_OWNER_COMPATIBILITY_REVIEW`. Nothing here claims the posture is
configured, deployed or verified.

## `AUTH-DEC-046` — CSRF and credential-transport boundary frozen

Security correction 2.

Protected FastAPI routes accept credentials only through
`Authorization: Bearer`. The provider-session cookie is never an API credential.
No application anti-CSRF token is required merely because a FastAPI request is
Bearer-authenticated. CORS uses the exact approved Dashboard origin, with no
wildcard and only the required headers and methods; CORS implementation remains
`A2-BACKEND`-owned.

Every same-origin Auth or session operation that mutates session state must use
a non-`GET` method, validate the exact `Origin`, apply Fetch Metadata checks
where available, and validate an Auth-owned anti-CSRF value bound either to the
current session or to the anonymous sign-in attempt. Sign-out is state-changing,
same-origin and CSRF-validated. `GET`, `HEAD` and `OPTIONS` Auth and session
endpoints remain side-effect-free.

The OAuth callback does **not** require the ordinary same-origin anti-CSRF token,
because it arrives as a top-level cross-site navigation. It must instead
validate provider OAuth `state`, PKCE, callback correlation, the exact callback
destination and intended-return binding before any protected effect. The
exemption narrows nothing else.

`A2-BACKEND` compatibility is unconfirmed: `SECURITY_REQUIRED /
PENDING_AFFECTED_OWNER_COMPATIBILITY_REVIEW`.

## `AUTH-DEC-047` — Sign-out scope `local` and production access-token lifetime `<= 900s`

Security corrections 3 and 3B.

Provider sign-out scope is `local`, meaning `CURRENT_SESSION_ONLY`. The broader
provider default scope is never inherited or used, and the scope is passed
explicitly rather than defaulted.

The production Supabase access-token lifetime is at most 900 seconds.
Classification: `PRODUCTION_SECURITY_REQUIREMENT /
PENDING_BACKEND_AND_DEPLOYMENT_CONSUMER_CONFIRMATION`.

Required semantics: local authenticated UI state clears immediately on sign-out;
an already-issued access token may remain accepted by FastAPI until its `exp`;
no baseline denial list, revocation list or token blocklist is required; and
neither Auth nor UI may claim immediate JWT revocation.

This is **not** recorded as already configured — no repository evidence proves
any JWT lifetime. Confirmation is required from `A2-BACKEND` and
`A2-DEPLOYMENT`. A future especially sensitive operation may require an explicit
live session-liveness check, but only where `A2-SECURITY` specifically
classifies that operation; none is classified at this version.

## `AUTH-DEC-048` — Public `SIGN_IN_FAILED` failure-oracle boundary

Security correction 4. Requiring four classifications to share a user-facing
message was insufficient, because the classification itself still crossed to the
browser and leaked the failed validation stage.

`INVALID_CALLBACK`, `STATE_VALIDATION_FAILED`, `PKCE_VALIDATION_FAILED` and
`SESSION_EXCHANGE_FAILED` must be indistinguishable through every untrusted
browser-observable channel. The browser and UI receive one public
classification, `SIGN_IN_FAILED`; one safe response shape; equivalent status
behavior; no internal validation-stage identifier; no provider detail; and no
field permitting inference of which stage failed. Response timing should be
normalized where practical and must never intentionally reveal the stage.

The four internal classifications remain valid, retained for server-side
Security events and restricted operational diagnostics, and keep their existing
retry, reauthentication, resulting-state and Backend-eligibility semantics
unchanged. No classification is removed and no classification's meaning is
altered, so this remains an additive, non-breaking change under the contract's
own versioning rules.

`A2-UI` is not required to distinguish the four through browser-visible
behavior, and must not attempt to. The Auth-owned UI adapter surfaces
`SIGN_IN_FAILED` for all four across the browser boundary. `USER_CANCELLED`,
`PROVIDER_DENIED`, `SESSION_EXPIRED`, `REFRESH_FAILED`, `SIGN_OUT_FAILED`,
`CONFIGURATION_UNAVAILABLE` and `TEMPORARY_PROVIDER_FAILURE` are unchanged and
remain individually observable.

## `AUTH-DEC-049` — Server-side ephemeral callback-correlation mechanism

Security correction 5. `AUTH-DEC-040` defined the correlation lifecycle but
deliberately left the mechanism and both durations open. Security has now
decided them, semantically and without selecting a technology.

Mechanism class: `AUTH_CONTROLLED / PROVIDER_NEUTRAL / SERVER_SIDE /
EPHEMERAL`. It must support atomic state transitions, atomic single-use
behavior, expiry, concurrent independent sign-in attempts, and shared
availability where multiple application runtime instances may process callbacks.

No database vendor, cache vendor, storage provider, cloud service or physical
implementation technology is selected. Physical storage technology and
deployment topology remain `PENDING_A2_DEPLOYMENT_CONFIRMATION`.

The browser carries only a cryptographically random opaque correlation handle,
in a separate Auth-owned cookie that in every non-local environment is
`HttpOnly`, `Secure`, `SameSite=Lax`, host-only and callback-path restricted.
That cookie carries no authorization code, access token, refresh token, PKCE
verifier, return path, provider payload or provider session.

The server-side record binds one sign-in attempt, one callback flow, the
lifecycle state, the creation time, the expiry, one completed-outcome reference
and the Security policy version.

| Lifecycle state | Frozen lifetime |
|---|---|
| `PENDING_ATTEMPT_CORRELATION` | at most 10 minutes from sign-in initiation |
| `COMPLETED_CALLBACK_CORRELATION` | exactly 120 seconds from successful completion |

The pending-to-completed transition is atomic. Failure, abandonment, a malformed
callback, an expired flow and a rejected flow must never create completed
correlation. An unavailable store or an unverifiable handle fails closed.
Concurrent tabs hold separate records and never overwrite one another.

## `AUTH-DEC-050` — Intended-return state is server-side only

Security correction 6. `AUTH-DEC-039` required the return state to be
attempt-bound, expiry-limited and single-use but left its storage open. It is
now frozen as server-side.

The intended return path exists only inside the server-side
`PENDING_ATTEMPT_CORRELATION` record. The browser carries only the opaque
correlation handle.

The return path must be validated before storage, bound to exactly one sign-in
attempt, expire within 10 minutes of initiation, be atomically single-use, and
be removed on success, on failure, on abandonment and on expiry.

It is never copied into provider OAuth `state`, never stored in the
browser-readable provider cookie, never stored in the correlation-handle cookie,
never placed in a URL, and never stored in `localStorage`, `sessionStorage`,
IndexedDB or any other custom browser persistence mechanism.

A missing server-side record, an integrity failure, a replay or a store failure
each falls back to `/`. These fallbacks relax no callback validation, and a
fallback destination is never callback success.

## `AUTH-DEC-051` — A preserved session requires live provider validation

Security correction 7. `AUTH-DEC-041` preserved an "independently established
and still known-valid" session without defining what proves validity, which
would have let cookie presence pass as proof.

A pre-existing session qualifies as
`INDEPENDENTLY_ESTABLISHED_AND_KNOWN_VALID_SESSION` only when all four hold:

1. its session identity existed before the rejected callback was processed;
2. callback processing performed no successful code exchange that created or
   replaced that session;
3. after callback rejection, authoritative server-side live provider validation
   succeeds; and
4. the validated session identity equals the pre-callback session identity.

Requirement 3 is normative as `LIVE_PROVIDER_SESSION_VALIDATION`. The contract
may reference `getUser()` as the currently supported provider example, but must
not permanently depend on one SDK method name where an equivalent authoritative
provider operation exists.

Insufficient alone: cookie presence; `getSession()`; a decoded JWT; local
signature or expiry validation; `getClaims()`; frontend state; a subscription
event; an existing access token.

Where live validation is unavailable, times out, fails, returns another session,
or cannot establish session-identity equality, validity is `UNPROVEN` and the
result is `FAIL_CLOSED`.

A rejected callback that preserves a session must emit an internal Security
event carrying at least `session_preserved=true`, `callback_success=false` and
`rejected_callback_destination_used=false`.

This tightens `AUTH-DEC-041` and `AUTH-DEC-043` without altering them: the
preserved-session recovery destination remains `/`, the rejected
intended-return destination remains `NEVER_USED`, no callback success is
reported, and a preserved session is still never callback correlation and never
proof that the callback succeeded.

## `AUTH-DEC-052` — The A2-UI owner-side `AUTH-002` conflict correction merged via PR #30

| Field | Value |
|---|---|
| Decision ID | `AUTH-DEC-052` |
| Owner of the corrected records | `A2-UI` |
| Recorded by | `A3-AUTH` — external merged evidence only |
| Consumer review | `AUTH-002-CONSUMER-REVIEW-A2-UI-001` |
| Reviewed Auth head | `7abe17af8e212bd2127160338ea6ef409da02101` |
| Historical disposition at that head | `SPECIFICATION_CONFLICT` — unchanged |
| Pull request | #30 — `docs(ui): reconcile Auth session custody and merged frontend state` |
| Implementation commit | `30deb92000a20d3837b2423b6bdee3ea3335a7f1` |
| Merge commit | `63093f22c37a0fc6affe168f7d5230107b05cdf3` — current `origin/main` |
| Merged UI decisions | `UI-DEC-026`, `UI-DEC-027` |
| Changed paths | six UI durable-record files; no `docs/components/auth/**` path |
| Auth-side state | contract correction remains uncommitted in this package |

**The historical disposition is not rewritten.** `A2-UI` returned
`SPECIFICATION_CONFLICT` against Auth head `7abe17af`, and that response remains
standing evidence against that head. This decision records only that the
UI-owned half of that conflict has been corrected and merged by its owner.

**What merged.** `UI-DEC-026` supersedes the conflicting non-`HttpOnly`-cookie
interpretation of the merged `UI-DEC-013` and nothing else. It preserves and
keeps binding: the `localStorage` prohibition; the `sessionStorage` prohibition;
the no-duplicate-and-no-shadow-session-store rule; `Authorization: Bearer`
transport with the absolute prohibition on forwarding a refresh token to
FastAPI; UI route protection as defense-in-depth only; and A2-SECURITY's joint
ownership of final cookie acceptance. The only browser-readable session store it
permits is the canonical Auth-owned cookie-backed session operated exclusively
through the approved `@supabase/ssr` Auth adapter, and it marks that permission
`CONDITIONAL` on A2-SECURITY acceptance of the final cookie posture. `UI-DEC-027`
reconciles the UI records to merged repository evidence — `apps/web` `PRESENT`,
`UI-002` and `UI-003` `MERGED` — while keeping Auth frontend
`NOT_IMPLEMENTED / NOT_TESTED / NOT_AUTHORIZED`, Auth runtime
`NOT_IMPLEMENTED / NOT_TESTED`, provider runtime `NOT_PROVISIONED / NOT_TESTED`,
`UI-004` `BLOCKED / NOT_AUTHORIZED` and `/auth/callback`
`RESERVED / NOT_IMPLEMENTED`.

**Compatibility consequence.** The merged UI custody rule no longer prohibits
the browser-readable provider cookie that the canonical Auth-owned
`@supabase/ssr` session depends on. The custody conflict between the merged UI
durable records and this contract's session architecture is therefore removed on
the UI side. Auth's architecture is unchanged by this decision: it neither
relaxes nor extends `AUTH-DEC-045`, and the merged UI text predates and does not
evaluate `AUTH-DEC-045` through `AUTH-DEC-051`.

**What this decision is not.**

- It is **not** `A2-UI` acceptance of the corrected Auth head. The merged UI text
  itself states that it does not make Auth PR #29 acceptable and that `A2-UI`
  rereview is still required.
- It does **not** convert `AUTH-DEP-012`, which stays `OPEN` and `NOT_ACCEPTED`.
- It does **not** close `AUTH-ISSUE-027`.
- It does **not** authorize `UI-004`, which remains `NOT_AUTHORIZED`.
- It does **not** discharge the `A2-SECURITY` corrected-head rereview, the
  `A2-BACKEND` or `A2-DEPLOYMENT` affected-boundary confirmations, or the final
  `A2-INTEGRATION` review.
- It is **not** implementation, provisioning or runtime evidence of any kind.

**Auth-side state.** The Auth-owned correction package remains unstaged and
uncommitted on branch `agent2/auth-002-session-contract` at head `7abe17af`,
pending A2-AUTH acceptance and push. No history reconciliation with `origin/main`
was performed or required: PR #30 touched no Auth path, so the branch and main
do not overlap.

## `AUTH-DEC-053` — `AUTH-002_FINAL_CONSUMER_AND_REGISTRY_COORDINATION_RECONCILED`

| Field | Value |
|---|---|
| Decision ID | `AUTH-DEC-053` |
| Task | `AUTH-002-FINAL-READINESS-RECONCILIATION-001-A3` |
| Authorizing coordinator | `Agent 1` |
| Supervising manager | `A2-AUTH` |
| Reviewed HEAD | `84ad9e322d886f8963c34386f87074a444b3fa2b` |
| Current `origin/main` | `1057ba727a4e825259c5f7772b6d428511a58a37` |
| Shared registry PR | PR #31 — merged (`a80145e2648596aef2254f4c3bd833c3a50be761` implementation, `1057ba727a4e825259c5f7772b6d428511a58a37` merge) |
| Contract | `CONTRACT-AUTH-001@1.1.0-draft.1` — unchanged (`8ed2154561785566b4b17baa16535e1fad8e662c`) |
| PR #29 status | `OPEN / DRAFT / NOT_MERGED / PENDING_FINAL_AGENT_1_READINESS_DECISION` |

**Final Consumer Coordination Matrix.**
All five current consumer domains have reviewed `CONTRACT-AUTH-001@1.1.0-draft.1` at HEAD `84ad9e322d886f8963c34386f87074a444b3fa2b` and returned `ACCEPTED_WITH_CONSTRAINTS`:
1. `A2-UI` — `AUTH-002-CONSUMER-REREVIEW-A2-UI-001` — `ACCEPTED_WITH_CONSTRAINTS` (required Auth corrections: NONE).
2. `A2-SECURITY` — `AUTH-002-CONSUMER-REREVIEW-A2-SECURITY-001` — `ACCEPTED_WITH_CONSTRAINTS` (seven original Security corrections ALL INCORPORATED, defective: NONE, required Auth corrections: NONE).
3. `A2-BACKEND` — `AUTH-002-CORRECTED-HEAD-AFFECTED-REVIEW-A2-BACKEND-001` — `ACCEPTED_WITH_CONSTRAINTS` (required Auth corrections: NONE).
4. `A2-DEPLOYMENT` — `AUTH-002-CORRECTED-HEAD-AFFECTED-REVIEW-A2-DEPLOYMENT-001` — `ACCEPTED_WITH_CONSTRAINTS` (required Auth corrections: NONE).
5. `A2-INTEGRATION` — `AUTH-002-FINAL-CORRECTED-HEAD-REVIEW-A2-INTEGRATION-001` — `ACCEPTED_WITH_CONSTRAINTS` (normative Auth corrections: NONE, cross-contract normative conflict: NONE).

**Historical Consumer Provenance Preserved.**
Historical responses against earlier HEAD `7abe17af8e212bd2127160338ea6ef409da02101` (`A2-UI` `SPECIFICATION_CONFLICT`, `A2-SECURITY` `REJECTED_WITH_REASON`, `A2-INTEGRATION` `ACCEPTED_WITH_CONSTRAINTS`) are preserved verbatim as immutable historical provenance (`HISTORICAL_STATE`). They are superseded for current coordination state by the final responses against `84ad9e322d886f8963c34386f87074a444b3fa2b` (`CURRENT_FINAL_COORDINATION_STATE`).

**Version-Aware Shared Registry Reconciled.**
The shared registry in `docs/specifications/A2_DATABASE_MANAGER(1).md` was corrected and merged via PR #31 (`a80145e2` / `1057ba72`). Reconciles `AUTH-DEP-003` to `COMPLETE / VERSION_AWARE_SHARED_REGISTRY_RECONCILED` and `AUTH-ISSUE-002` to `CLOSED / VERSION_AWARE_REGISTRY_RECONCILED`. The established version-aware registry semantics are:
- `CONTRACT-AUTH-001@1.1.0-draft.1` current consumers: `A2-UI`, `A2-SECURITY`, `A2-DEPLOYMENT`, `A2-BACKEND`, `A2-INTEGRATION`.
- `A2-DATABASE`: `HISTORICAL_CONSUMER / ACKNOWLEDGED_AND_IMPLEMENTED_FOR_EARLIER_IDENTITY_CONTRACT_BOUNDARY` (`CONTRACT-AUTH-001@1.0.0-draft.2`).
- A2-DATABASE is not classified as a current blocking consumer of the 1.1 browser/session additions.

**Non-Normative Contract Status-Provenance Supersession.**
`docs/components/auth/CONTRACT-AUTH-001.md` blob SHA `8ed2154561785566b4b17baa16535e1fad8e662c` is byte-identical and untouched. Old non-normative consumer status provenance embedded in `CONTRACT-AUTH-001.md` (such as "consumer review pending" or "rereview required") is superseded for coordination purposes by this authoritative readiness reconciliation. The corrected-head reviews against `84ad9e322d886f8963c34386f87074a444b3fa2b` are the authoritative CURRENT coordination evidence. No normative contract rule is superseded or modified; contract version remains `1.1.0-draft.1`.

**Runtime Implementation Authorization Explicitly Prohibited.**
This non-normative readiness reconciliation does **NOT** authorize runtime implementation:
- Auth runtime: `NOT_IMPLEMENTED / NOT_TESTED / NOT_AUTHORIZED`
- Frontend Auth: `NOT_IMPLEMENTED / NOT_TESTED / NOT_AUTHORIZED`
- Backend JWT/JWKS: `NOT_IMPLEMENTED / NOT_TESTED / NOT_AUTHORIZED`
- Provider runtime: `NOT_PROVISIONED / NOT_TESTED`
- `UI-004`: `NOT_AUTHORIZED`
- `AUTH-003`: `NOT_AUTHORIZED`
- Release: `NOT_READY`

Pull request #29 remains `OPEN / DRAFT / NOT_MERGED` pending final Agent 1 readiness decision.

## `AUTH-DEC-054` — `CONTRACT-AUTH-001@1.2.0-draft.1` Finalization and Accepted `AUTH-005` Normative Corrections

| Field | Value |
|---|---|
| Decision ID | `AUTH-DEC-054` |
| Task | `AUTH-006-FINALIZE-CONTRACT-AUTH-001-V1.2.0-DRAFT.1-001-A3` |
| Authorizing coordinator | `Agent 1` |
| Target contract version | `CONTRACT-AUTH-001@1.2.0-draft.1` |
| Change category | `ADDITIVE_COMPATIBLE_MINOR` |
| Breaking | `NO` |

**Normative Corrections Incorporated.** Finalizes `CONTRACT-AUTH-001@1.2.0-draft.1` preserving accepted `AUTH-005` semantics:
1. `SIGN_OUT_WINS`: stale provider cookie material may physically arrive, but MUST NEVER qualify as an established or usable Auth session after a newer Auth-context fence exists.
2. `ESTABLISHED_AUTH_SESSION` criteria: requires valid provider session, current Auth context, valid session binding, no active local sign-out tombstone, verified synchronization authority, no newer sign-out generation.
3. Provider session remains the sole canonical provider credential/session.
4. Synchronization artefacts are NOT sessions, credentials, identities, permissions, authorization, token copies, or duplicate provider-session stores.

## `AUTH-DEC-055` — UI Host Boundary (`POST /auth/session-fence`)

| Field | Value |
|---|---|
| Decision ID | `AUTH-DEC-055` |
| Host HTTP Method | `POST` |
| Host Path | `/auth/session-fence` |
| UI-owned implementation path | `apps/web/src/app/auth/session-fence/route.ts` |
| Semantic Operations | `PREPARE_SIGN_IN`, `PUBLISH_SIGN_OUT`, `RESOLVE_SESSION` |
| Ownership split | A2-UI: host/path/transport/wiring; A2-AUTH: all Auth semantics behind host |

**UI Host Boundary Rules.**
- Host endpoint implementation path frozen as `apps/web/src/app/auth/session-fence/route.ts`.
- No Auth semantic ownership transfers to UI.
- `processCallback()` success alone is NOT final proof of current authenticated presentation eligibility after AUTH-005; final presentation/navigation requires fence-resolved Auth eligibility.
- No new public UI Auth state is introduced.

## `AUTH-DEC-056` — Security Constraints for Handles and Tombstone

| Field | Value |
|---|---|
| Decision ID | `AUTH-DEC-056` |
| Owner | `A2-SECURITY` |
| Handles & Tombstone | `OPAQUE_AUTH_CONTEXT_HANDLE`, `OPAQUE_AUTH_SESSION_BINDING_HANDLE`, `LOCAL_SIGN_OUT_TOMBSTONE` |

**Security Constraints.**
- `OPAQUE_AUTH_CONTEXT_HANDLE`: >=128-bit CSPRNG; opaque; `HttpOnly`; `Secure` outside exact `http://localhost:3000` exception; `SameSite=Lax`; host-only (no `Domain`); `Path=/`; browser-session scoped; never exposed to browser JS/analytics/logs/tracing.
- `OPAQUE_AUTH_SESSION_BINDING_HANDLE`: >=128-bit CSPRNG; opaque; `HttpOnly`; `Secure` outside exact `http://localhost:3000` exception; `SameSite=Lax`; host-only (no `Domain`); `Path=/`; lifetime <= Auth context; new handle issued for each successful session establishment.
- `LOCAL_SIGN_OUT_TOMBSTONE`: deny-only; browser-readable; **NOT** `HttpOnly`; `Secure` outside exact `http://localhost:3000` exception; `SameSite=Lax`; host-only (no `Domain`); `Path=/`; browser-session scoped; cannot grant authentication; absence alone proves nothing; stale callbacks/provider events cannot clear it; removal ONLY through successful explicit Auth reconciliation or authorized Auth-context reset.
- `/auth/session-fence` request constraints: `POST`, exact approved Dashboard Origin, same-origin Fetch Metadata where supported, existing Auth anti-CSRF, `Cache-Control: private, no-store`.

## `AUTH-DEC-057` — Security Event Sink Follow-up

| Field | Value |
|---|---|
| Decision ID | `AUTH-DEC-057` |
| Security event sink status | NOOP sink REJECTED; LOCAL NON-NOOP sink REQUIRED |
| Persistence requirement | Local durable persistence NOT required |
| Follow-up classification | `IMPLEMENTATION_FOLLOW_UP` |

**Security Event Sink Rules.**
- Current UI-004 no-op Security-event sink is NOT acceptable.
- A local non-noop sink is REQUIRED; local durable persistence is NOT required.
- Existing `AuthSecurityEvent` runtime payload/interface may require later Security-envelope enrichment.
- That enrichment is recorded as an `IMPLEMENTATION_FOLLOW_UP` only and is NOT implemented by AUTH-006.

## `AUTH-DEC-058` — Production Synchronization Authority Constraints

| Field | Value |
|---|---|
| Decision ID | `AUTH-DEC-058` |
| Production Sync Authority | Environment-isolated, HA, shared, linearizable, restart-safe, failover-safe, fail-closed |
| Physical Provider | `UNSELECTED` |

**Production Sync Authority Rules.**
- Production synchronization authority MUST be environment-isolated, highly available, shared across every relevant Auth runtime, linearizable, restart-safe, failover-safe, and fail-closed when unavailable or indeterminate.
- Production physical provider remains **UNSELECTED** (no Redis, Valkey, PostgreSQL, Supabase table, cloud cache, etc. selected).

## `AUTH-DEC-059` — Local UI-004 Process-Local Authority Constraints

| Field | Value |
|---|---|
| Decision ID | `AUTH-DEC-059` |
| Local UI-004 Authority Scope | Permitted ONLY when callback processing, session validation, and sign-out run in 1 OS process and 1 memory space |
| Restart Behavior | Authority state loss -> `FAIL_CLOSED` -> reauthentication |

**Local Process Authority Rules.**
- For local UI-004 only, process-local authority is permitted ONLY when callback processing, session validation, and sign-out all run in exactly ONE local Next.js/Auth OS process and ONE memory space.
- Must have no replicas, clustering, serverless isolates, load balancing, or independently restarted handlers.
- On local authority process restart: authority state loss -> FAIL CLOSED -> reauthentication.
- No production-safety claim may be made from local process memory.

## `AUTH-DEC-060` — Integration Future Acceptance-Test Requirements

| Field | Value |
|---|---|
| Decision ID | `AUTH-DEC-060` |
| Status | `FUTURE_ACCEPTANCE_TEST_REQUIREMENTS` |
| Vitest/jsdom proof status | `INSUFFICIENT_FOR_BROWSER_NETWORK_ORDERING` |

**Integration Test Requirements.**
- Records 11 future acceptance-test requirements: (1) deterministic server/browser response-order control, (2) actual browser cookie jar, (3) stale response order A, (4) stale response order B, (5) multi-tab shared browser context, (6) faultable sync authority, (7) deterministic callback response barriers, (8) separate assertions for semantic denial vs physical cleanup, (9) no protected-content flash, (10) access-token fail-closed, (11) green existing callback duplicate/replay suite.
- Vitest/jsdom-only proof is INSUFFICIENT for browser/network ordering acceptance.
- Recorded as future implementation/integration evidence requirements, NOT claimed passed tests.

## `AUTH-DEC-061` — Preserved Operations and Scope Constraints

| Field | Value |
|---|---|
| Decision ID | `AUTH-DEC-061` |
| Public `AuthAdapter` operations | `PRESERVED_UNCHANGED` |
| Provider sign-out scope | `local` / `CURRENT_SESSION_ONLY` |
| Backend JWT revocation claim | `NONE` |
| Duplicate token/session store | `PROHIBITED` |

**Preserved Boundaries.**
- Existing public `AuthAdapter` operation list remains unchanged (`beginSignIn`, `processCallback`, `getSessionSnapshot`, `subscribeToSessionChanges`, `getAccessTokenForApiRequest`, `refreshSession`, `signOut`).
- Provider sign-out scope remains `local` / `CURRENT_SESSION_ONLY`.
- Do not claim immediate Backend JWT revocation.
- Create no duplicate session/token store.

## `AUTH-DEC-062` — Callback Generation Supersession & Same-Generation Concurrent Sign-In Semantics

| Field | Value |
|---|---|
| Decision ID | `AUTH-DEC-062` |
| Task | `AUTH-006-FINALIZE-CONTRACT-AUTH-001-V1.2.0-DRAFT.1-001-A3-R1` |
| Callback supersession | Generation-bound fail-closed as stale |
| Same-generation concurrent sign-in | Preserved |

**Callback Generation Supersession Semantics.**
- A callback MUST fail closed as stale when the Auth-context generation to which its sign-in attempt is bound is no longer the authoritative current generation.
- A later sign-in attempt does NOT, merely by being later in time, invalidate an earlier independently correlated attempt when both remain bound to the same current Auth-context generation.
- The required "old callback after new sign-in" case occurs when attempt A begins under generation G → sign-out advances Auth context beyond G → explicit reconciliation occurs → attempt B begins under newer current generation → late callback belonging to attempt A remains bound to generation G → attempt A MUST NOT establish or restore current Auth.
- Concurrent independent sign-in attempts MAY exist under the same current Auth-context generation and remain governed by existing attempt-specific callback correlation rules.

## `AUTH-DEC-063` — Explicit Sign-Out Tombstone Ordering & Publication Failure Semantics

| Field | Value |
|---|---|
| Decision ID | `AUTH-DEC-063` |
| Task | `AUTH-006-FINALIZE-CONTRACT-AUTH-001-V1.2.0-DRAFT.1-001-A3-R1` |
| Tombstone establishment ordering | MUST precede `PUBLISH_SIGN_OUT` and provider sign-out |
| Publication failure behavior | Tombstone remains active; local Auth remains signed out |

**Sign-Out Tombstone Ordering Rules.**
- When `AuthAdapter.signOut()` is requested, Auth MUST establish the browser-local deny-only `LOCAL_SIGN_OUT_TOMBSTONE` BEFORE relying on any cross-runtime `PUBLISH_SIGN_OUT` operation or provider sign-out completion.
- Required ordering: (1) user requests sign-out → (2) `LOCAL_SIGN_OUT_TOMBSTONE` becomes active locally → (3) protected Auth eligibility fails closed → (4) publish/advance authoritative Auth generation (`PUBLISH_SIGN_OUT`) → (5) perform existing provider `CURRENT_SESSION_ONLY` sign-out.
- If publication fails or synchronization authority is unavailable: `LOCAL_SIGN_OUT_TOMBSTONE` MUST remain active; local Auth remains signed out; `AUTHENTICATED` state MUST NOT be restored; provider `SIGNED_IN` / `TOKEN_REFRESHED` / equivalent events MUST NOT clear it; stale callback/session material MUST NOT clear it; protected UI remains prohibited; new protected API request preparation remains prohibited.
- `SIGN_OUT_FAILED` is NOT redefined; `CURRENT_SESSION_ONLY` scope is unchanged; immediate JWT revocation is NOT claimed.

## `AUTH-DEC-064` — Explicit New Sign-In After Sign-Out Reconciliation Rules

| Field | Value |
|---|---|
| Decision ID | `AUTH-DEC-064` |
| Task | `AUTH-006-FINALIZE-CONTRACT-AUTH-001-V1.2.0-DRAFT.1-001-A3-R1` |
| Tombstone permanence | Non-permanent; clearable via explicit reconciliation |
| Pre-sign-in reconciliation requirement | Mandatory before tombstone removal and provider OAuth initiation |

**New Sign-In After Sign-Out Reconciliation.**
- A sign-out tombstone MUST NOT permanently prevent future authentication.
- When the user deliberately initiates a NEW sign-in while `LOCAL_SIGN_OUT_TOMBSTONE` is active:
  1. Auth MUST first perform `PREPARE_SIGN_IN` / Auth-context reconciliation with the authoritative synchronization authority;
  2. Reconciliation MUST establish that pre-sign-out generations remain superseded;
  3. Only AFTER successful reconciliation may the local tombstone be removed;
  4. Only AFTER successful reconciliation may provider OAuth initiation proceed;
  5. The new sign-in attempt binds to the then-current Auth-context generation.
- If reconciliation is unavailable, fails, or is indeterminate: provider sign-in MUST NOT proceed; the tombstone remains active; Auth remains fail closed.

## `AUTH-DEC-065` — Session-Binding Record Exclusions & Callback Response Fence Non-Mutation Rules

| Field | Value |
|---|---|
| Decision ID | `AUTH-DEC-065` |
| Task | `AUTH-006-FINALIZE-CONTRACT-AUTH-001-V1.2.0-DRAFT.1-001-A3-R1` |
| Session-binding record structure | Binds context, generation, attempt, callback flow, establishment result |
| Binding record exclusions | Prohibits tokens, credentials, PKCE verifier, code, path, identity, capabilities |
| Callback response fence non-mutation | Prohibits mutating context handle or active newer tombstone |

**Session-Binding Record and Callback Response Fence Rules.**
- A successful session-binding record binds at minimum: one Auth context, attempt's Auth-context generation, one sign-in attempt, one callback flow, successful session-establishment result.
- The binding record MUST NOT contain: access token, refresh token, provider-session bytes, authorization code, PKCE verifier, intended-return path, identity claim, authorization capability.
- Callback-correlation records remain distinct from session-binding records and MUST NOT be merged.
- The callback response MUST NOT create, replace, rotate, clear, overwrite, or otherwise mutate the authoritative browser Auth-context synchronization handle or an already active newer `LOCAL_SIGN_OUT_TOMBSTONE`.
- A stale callback may physically reintroduce stale provider-session cookie material or an old opaque session-binding handle, but those values MUST fail generation validation and remain unusable.

## `AUTH-DEC-066` — Reconciled Current Runtime Status and Contract Status Wording

| Field | Value |
|---|---|
| Decision ID | `AUTH-DEC-066` |
| Task | `AUTH-006-FINALIZE-CONTRACT-AUTH-001-V1.2.0-DRAFT.1-001-A3-R1` |
| Contract status wording | `FINALIZED_CONTRACT_DRAFT_FOR_A2_REVIEW` |
| Runtime status reconciliation | Distinguishes existing merged runtime code, zero task authorization, and un-authorized fence corrections |

**Runtime Status & Contract Status Reconciliation.**
- Contract status wording updated to `FINALIZED_CONTRACT_DRAFT_FOR_A2_REVIEW`.
- Reconciles current-state wording in durable records to explicitly distinguish:
  A. Existing merged Auth runtime state: present in baseline under `apps/web/src/auth/**` (including `AuthAdapter`, state machine, correlation, storage boundary, redirect, types, unit tests).
  B. `AUTH-006` implementation authorization: `NONE / NO_RUNTIME_MODIFICATION_AUTHORIZED` under this task.
  C. `AUTH-003` / `AUTH-005` fence correction runtime implementation: `NOT_YET_AUTHORIZED / NOT_YET_IMPLEMENTED` under this task.

## `AUTH-DEC-067` — R2 Final Targeted Review Corrections

| Field | Value |
|---|---|
| Decision ID | `AUTH-DEC-067` |
| Task | `AUTH-006-FINALIZE-CONTRACT-AUTH-001-V1.2.0-DRAFT.1-001-A3-R2` |
| PKCE & OAuth State Ownership | PKCE verifier custody and provider OAuth state generation/validation remain provider-integration-owned; not transferred into Auth correlation records |
| Callback Correlation Record Separation | Callback correlation records remain distinct from session-binding records; records Auth-owned attempt/callback flow correlation & pending intended-return binding |
| Auth Test Status Reconciliation | Auth runtime unit tests: `PRESENT_IN_BASELINE` under `apps/web/src/auth/**`; `tests/auth/`: `ABSENT`; `AUTH-005 cross-runtime acceptance`: `NOT_YET_TESTED / FUTURE_INTEGRATION_REQUIREMENT` |
| CSRF & Cookie Status Reconciliation | Auth-owned CSRF/cookie foundation: `PRESENT_IN_BASELINE`; Backend CORS: separately `A2-BACKEND-OWNED`; Session fence runtime: `NOT_YET_AUTHORIZED / NOT_YET_IMPLEMENTED` |
| Open Issues Impact Wording | Reconciled impact wording to distinguish existing merged runtime foundation from missing hosted/UI integration and Backend authorization runtime |

**R2 Final Targeted Review Corrections.**
- **PKCE Provider Custody & OAuth State Ownership**: PKCE remains required; the PKCE verifier is created and held by the provider integration on the initiating device. Auth code, UI code, and correlation records MUST NOT read, copy, transmit, persist, or log the PKCE verifier. Provider OAuth state generation and validation remain provider-integration-owned and MUST NOT become an Auth application return-path or correlation payload.
- **Callback Correlation Record Separation**: Callback-correlation records represent Auth-owned attempt/callback-flow correlation and existing permitted pending intended-return binding. Session-binding records represent successful session establishment against an Auth context and generation. The two record types MUST NOT be merged.
- **Auth Test Status Reconciliation**: Durable records updated to reflect that Auth runtime unit tests are `PRESENT_IN_BASELINE` under `apps/web/src/auth/**` (including `adapter.test.ts`), while `tests/auth/` is `ABSENT` and AUTH-005 cross-runtime acceptance is `NOT_YET_TESTED / FUTURE_INTEGRATION_REQUIREMENT`. Vitest/jsdom-only proof is INSUFFICIENT for stale HTTP response/browser-cookie ordering acceptance.
- **CSRF & Cookie Status Reconciliation**: Reconciled status to distinguish `AUTH-OWNED CSRF / COOKIE FOUNDATION: PRESENT_IN_BASELINE` under `apps/web/src/auth/csrf.ts` and `apps/web/src/auth/**` from `BACKEND CORS IMPLEMENTATION: SEPARATELY A2-BACKEND-OWNED` and `AUTH-005 SESSION-FENCE RUNTIME CORRECTION: NOT_YET_AUTHORIZED / NOT_YET_IMPLEMENTED`.
- **Open Issues Impact Wording**: Reconciled `AUTH-ISSUE-001` impact statement to acknowledge existing merged browser runtime foundations in `apps/web/src/auth/**` while accurately representing missing hosted UI integration (`/auth/callback`) and separate incomplete Backend runtime boundaries.
