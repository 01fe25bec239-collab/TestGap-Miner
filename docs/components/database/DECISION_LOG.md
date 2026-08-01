# Database Decision Log

- Date reconciled: 2026-07-31
- Branch: `agent2/database`
- Synchronized baseline: `f54f8755c0589db704bd0f94c891da11c42398a6`
- DB-001/DB-001-C1: `PASS`, reviewed, and merged
- DB-001-C1: historical completed continuation
- Original DB-DEP011 scaffold attempt: historical `DEPENDENCY_BLOCKED`
- Database scaffold: `IMPLEMENTED`; DB-DEP-011 final closure
  `PENDING_INTEGRATION_VALIDATION`
- Migration chain: bootstrap exists with zero heads and no revisions
- Domain schema: `NOT_STARTED`; DB-002: `BLOCKED`
- `CONTRACT-AUTH-001@1.0.0-draft.2`: `ACKNOWLEDGED_AND_MERGED`
- Workflow: separate verified Database post-merge reconciliation required

## `DB-DEC-001` — Persistence baseline

- Status: `VERIFIED_COMPLETE`; PostgreSQL/SQLAlchemy/Alembic scaffold
  implementation is `IMPLEMENTED`, while domain schema is `NOT_STARTED`.
- Decision: PostgreSQL, SQLAlchemy 2.x-style models, and Alembic migrations.
- Rejected alternatives for this baseline: SQLite persistence and Liquibase/Flyway.

## `DB-DEC-002` — MVP tenancy and authorization boundary

- Status: `VERIFIED_COMPLETE` as an approved documentation decision; implementation is `BLOCKED`.
- Decision: scope access by authenticated user, GitHub App installation, and repository.
- Rejected: organization-based enterprise tenancy, generic RLS tenancy, billing, and enterprise Roles/Permissions tables.

## `DB-DEC-003` — Identifier boundary

- Status: `VERIFIED_COMPLETE` as an approved documentation decision; implementation is `BLOCKED`.
- Decision: internal records use UUIDs. GitHub numeric identifiers, delivery GUIDs, provider request IDs, repository SHAs, and benchmark identifiers remain separate external values. GitHub run idempotency includes delivery GUID + repository ID + relevant SHA; benchmark idempotency includes project ID + bug ID + configuration version + model ID + prompt-template version.

## `DB-DEC-004` — Relational versus object storage

- Status: `VERIFIED_COMPLETE` as an approved documentation decision; implementation is `BLOCKED`.
- Decision: PostgreSQL holds metadata, relationships, constraints, hashes, lifecycle state, and auditable history. Private S3-compatible storage holds object bytes, generated patch bytes when large/sensitive, repository snapshots, and large execution logs.

## `DB-DEC-005` — Secret and identity handling

- Status: `VERIFIED_COMPLETE` as an approved documentation decision; implementation is `BLOCKED`.
- Decision: never store raw private keys, installation tokens, provider keys,
  API keys, password hashes, local credentials, or other secrets in ordinary
  tables. `CONTRACT-AUTH-001@1.0.0-draft.2` requires no local credential field.

## `DB-DEC-006` — Retrieval persistence

- Status: `VERIFIED_COMPLETE` as an approved documentation decision; implementation is `BLOCKED`.
- Decision: deterministic manifest, lexical, and structural retrieval is the baseline. Embeddings/pgvector are `DEFER` and remain feature-flagged until evaluation proves improvement.

## `DB-DEC-007` — Audit and human control

- Status: `VERIFIED_COMPLETE` as an approved documentation decision; implementation is `BLOCKED`.
- Decision: run/evidence/security history and human decisions are attributable and append-only or versioned. Generated changes are test-only, may be published only as draft PRs/comments, and are never auto-merged.

## `DB-DEC-008` — Generic schema disposition

- Status: `VERIFIED_COMPLETE`.
- Decision: adapt only domain-relevant run, workflow, evidence, evaluation, audit, and usage concepts. Reject generic Organizations/RBAC/document-ingestion/API-key tables. The complete matrix is in `COMPONENT_STATUS.md`.

## `DB-DEC-009` — Contract ownership

- Status: `VERIFIED_COMPLETE`.
- Decision: DB-001 may document provisional domains, but it does not freeze fields owned by AUTH, BACKEND, RAG, AGENT-WORKFLOW, EVALUATION, SECURITY, DEPLOYMENT, or INTEGRATION.
- DB-002 boundary: the Auth prerequisite is satisfied. Workflow requires its
  separate verified Database post-merge reconciliation. API, Queue, Security,
  Deployment, and Integration are scoped constraints where applicable, not
  universal prerequisites.

## `DB-DEC-010` — Shared scaffold ownership

- Status: `IMPLEMENTED`.
- Decision: A3-DATABASE will not create unowned protected application-root, package, dependency, lock, environment, container, or test-harness files.
- Resolution: A2-INTEGRATION coordinated ownership; Backend and Deployment
  scaffolds are merged and the Database-owned scaffold is implemented.

## `DB-DEC-011` — Minimal synchronous Database scaffold

- Date: 2026-07-30
- Status: `IMPLEMENTED` by
  `DB-DEP011-DATABASE-SCAFFOLD-001-C1/C2`, pending A2-DATABASE review and
  Integration PostgreSQL 16 validation.
- Decision: runtime engines are explicit synchronous SQLAlchemy factories using
  psycopg 3 and `pool_pre_ping=True`; sessions use `autoflush=False` and
  `expire_on_commit=False`; request dependencies roll back escaping exceptions,
  always close, and never auto-commit.
- Credential boundary: runtime resolution uses `DATABASE_URL` only. Migration
  resolution prefers `MIGRATION_DATABASE_URL`, permits `DATABASE_URL` fallback
  only when `TESTGAP_RUNTIME` exactly equals `local`, and otherwise fails closed.
- Test boundary: `TEST_DATABASE_URL` must use `postgresql+psycopg`, name a
  database ending exactly in `_test`, and differ from `DATABASE_URL`; errors
  never include credentials. Deployment/Integration host-registry validation
  remains pending.
- Migration boundary: empty `MetaData`, zero heads, no baseline revision,
  explicit `-c apps/api/alembic.ini`, synchronous online mode, and supported
  offline mode.
- Scope: no DB-002 model, table, enum, constraint, index, Auth/Workflow field,
  or revision exists.

## `DB-DEC-012` — Auth contract acceptance

- Date: 2026-07-31
- Status: `ACCEPTED`; `CONTRACT-AUTH-001@1.0.0-draft.2` is
  `ACKNOWLEDGED_AND_MERGED` through PR #7 and merge commit
  `f54f8755c0589db704bd0f94c891da11c42398a6`.
- Identity decision: internal identifiers are UUIDs; immutable external
  identifiers remain separate. Issuer and opaque subject storage/comparison is
  exact and case-sensitive, `(issuer, subject)` is unique on the exact stored
  values, and Database performs no independent lowercase, uppercase, trimming,
  URL normalization, alias resolution, or other issuer transformation.
- Scope decision: GitHub numeric installation ID and repository ID are each
  unique; repository access is scoped to the exact
  user-installation-repository tuple.
- Lifecycle decision: scheduled expiry (`expires_at`), recorded expiry
  (`expired_at`), and explicit revocation (`revoked_at`) retain distinct
  meanings. Suspension, revocation, expiration, deletion, and deprovisioning
  deny new actions without destroying historical attribution.
- Actor and credential decision: human and machine actors remain distinct.
  Database persists no local credentials, password hashes, raw tokens, private
  keys, or other secrets. Generic organization tenancy, generic RBAC, and
  billing schema remain out of scope.
- Ownership: A2-DATABASE owns physical names, SQL types, constraints, indexes,
  ORM mappings, migrations, and ordering, but must not change Auth semantics.
- Compatibility: any future incompatible change requires a versioned Auth
  contract update, Database consumer review, migration-impact analysis,
  affected-consumer acknowledgement, and Integration coordination.
- Runtime boundary: no Auth or Database implementation was performed; DB-002
  remains `BLOCKED`.
