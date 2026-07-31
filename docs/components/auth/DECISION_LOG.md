# Auth Decision Log

- Current task: `AUTH-DB002-CONTRACT-001-C2`
- Scope: `DOCUMENTATION_ONLY_CONTRACT_REPAIR`
- Evidence baseline: `739a331c9942ed64a1ad8276d611889bbee53a27`
- Auth implementation: `NOT_STARTED`
- Auth runtime: `NOT_TESTED`

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

No decision in this log authorizes Auth code, tests, or DB-002 implementation.
The shared registry's missing Database consumer remains an owner correction.
