# CONTRACT-AUTH-001 — Authentication Identity and Repository Authorization Boundary

## Metadata

| Field | Value |
|---|---|
| Contract ID | `CONTRACT-AUTH-001` |
| Version | `1.0.0-draft.1` |
| Status | `DRAFT_FOR_CONSUMER_REVIEW` |
| Owner | `A2-AUTH` |
| Blocking consumer | `A2-DATABASE` |
| Blocking consumer task | `DB-002` |
| Additional consumers | `A2-BACKEND`, `A2-UI`, `A2-SECURITY`, `A2-INTEGRATION` |
| Evidence baseline | `739a331c9942ed64a1ad8276d611889bbee53a27` |

This contract defines semantic identity and authorization requirements only. It
does not implement Auth or Database behavior. A2-DATABASE retains ownership of
physical table names, ORM classes, migrations, constraint names, indexes,
PostgreSQL implementation, and migration ordering.

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

The pair `issuer + subject` is unique. One active issuer-subject maps to exactly
one canonical user; duplicate linkage to another user is rejected. A revoked
subject cannot authenticate. Email and mutable login names cannot authorize
access. Provider tokens and refresh tokens are never persisted.

These provider-neutral semantics do not freeze a particular OAuth
implementation for DB-002.

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
- nullable `revoked_at`.

At most one active grant exists for an exact
user-installation-repository tuple. A grant must not cross users,
installations, or repositories. `REVOKED` and `EXPIRED` grants deny new access.

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

## Compatibility and versioning

The following are breaking changes:

- changing issuer-subject uniqueness;
- reusing external IDs as internal IDs;
- removing actor types;
- changing the access tuple;
- permitting local credentials;
- permitting cross-installation or cross-repository access;
- lifecycle changes that re-enable denied access; or
- introducing organization tenancy or generic RBAC.

A breaking change requires a major contract version and coordinated
A2-DATABASE and A2-INTEGRATION review. Additive clarifications that preserve
these semantics may use a compatible draft/minor revision.

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

- Identity-provider issuer, audience, and callback values are not frozen.
- JWT runtime validation is not implemented or tested.
- GitHub access-verification freshness is not frozen.
- Exact retention periods are not frozen.
- Security-event payloads are not frozen.
- Workflow actor-event integration awaits `CONTRACT-WORKFLOW-001`.
- Deployment runtime metadata awaits owner input.
- Security lifecycle/event guidance remains an owner dependency.
- This contract is documentation, not Auth runtime implementation.
- A2-DATABASE must acknowledge this draft before treating it as accepted for
  DB-002; DB-002 also remains blocked on accepted `CONTRACT-WORKFLOW-001`.
