# Auth Decision Log

- Date: 2026-08-02
- Current task: `AUTH-001-C2` — Auth task-graph reconciliation
- Parent task: `AUTH-001`
- Prompt type: `CONTINUATION`
- Scope: `DOCUMENTATION_ONLY_TASK_GRAPH_RECONCILIATION`
- Evidence baseline: `1511f474ee301651b631c8adfe406aeb775327aa`
- Prior contract-task baseline: `739a331c9942ed64a1ad8276d611889bbee53a27`
- Auth identity persistence: `VERIFIED_COMPLETE` and merged
- Auth runtime implementation: `NOT_STARTED`
- Auth runtime: `NOT_TESTED`

`AUTH-DEC-001` through `AUTH-DEC-013` are contract decisions made under
`AUTH-DB002-CONTRACT-001`. They remain in force unchanged. `AUTH-001` adds
`AUTH-DEC-014` through `AUTH-DEC-020` as audit-level decisions only; none of
them alters `CONTRACT-AUTH-001` semantics.

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

No decision in this log authorizes Auth code, tests, or configuration. The
shared registry's missing Database consumer remains an owner correction. The
stale `CONTRACT-AUTH-001` metadata recorded as `AUTH-ISSUE-011` is an A2-AUTH
correction; `AUTH-001` is forbidden to edit that file and did not.
