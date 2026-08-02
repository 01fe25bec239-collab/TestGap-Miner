# Database Decision Log

- Date reconciled: 2026-08-02
- Branch: `agent2/database`
- DB-002 implementation baseline:
  `8884b5d540351c735b6cddc01314a7dd9e25af05`
- Current `DB-002-WORKFLOW-OWNER-ACK-001` reconciliation baseline:
  `c0c3c1d5d25c671553058fec786cf7bbd99baf43`
- Historical DB-002 reconciliation merge commit:
  `1511f474ee301651b631c8adfe406aeb775327aa` (PR #13)
- DB-001/DB-001-C1: `PASS`, reviewed, and merged
- DB-001-C1: historical completed continuation
- Original DB-DEP011 scaffold attempt: historical `DEPENDENCY_BLOCKED`
- Database scaffold: `IMPLEMENTED`; DB-DEP-011:
  `ACCEPTED / VERIFIED_COMPLETE / CLOSED`
- Migration chain: exactly one head, `ad3f80907336`
- Domain schema: `IMPLEMENTED` for DB-002; DB-002:
  `PASS / VERIFIED_COMPLETE / MERGED`; DB-002-C1: `PASS`; DB-002-C2: `PASS`;
  DB-002-MERGE-001: `PASS`
- DB-002 implementation evidence: pull request #12; implementation commit
  `5506ab59211fbaba79f77d4fb5899a587c0e0236`; implementation merge commit
  `3701520e6d61e2bb80391e7af888d0d530bdb6c4`
- DB-002 durable-record reconciliation evidence: documentation pull request
  #13 (`docs(database): close merged DB-002`); head commit
  `861781b1c91cc5eed870653bc35b2d39fc9c1021`; reconciliation merge commit
  `1511f474ee301651b631c8adfe406aeb775327aa`
- DB-003: `NOT_STARTED` / `NOT_AUTHORIZED`
- `CONTRACT-AUTH-001@1.0.0-draft.2`: `ACKNOWLEDGED_AND_MERGED`
- `DB-DEP-001`: `ACCEPTED`
- `CONTRACT-WORKFLOW-001@1.0.0-draft.1`:
  `ACKNOWLEDGED_AND_MERGED`; `DB-DEP-004`: `ACCEPTED`

## `DB-DEC-015` — Workflow-owner DB-002 reconciliation closure

- Status: `WORKFLOW-DB002-OWNER-RECONCILIATION-001` is
  `SATISFIED / VERIFIED_COMPLETE / CLOSED`; execution task
  `WORKFLOW-DB002-OWNER-RECONCILIATION-001-C1` is
  `PASS / VERIFIED_COMPLETE / MERGED`.
- Evidence: Workflow PR #16, documentation commit
  `4db0911d5600f852f43edc9e132a48bd817577b3`, and merge commit
  `110a90ca53058372677d53868977f74520bd3f80`. PR #17
  (`docs(auth): complete AUTH-001 trust-boundary audit`) is separately the Auth
  trust-boundary audit and current baseline
  `c0c3c1d5d25c671553058fec786cf7bbd99baf43`; it is not Auth runtime and does
  not resolve the typed machine/publication actor relationship.
- Contract decision: `CONTRACT-WORKFLOW-001@1.0.0-draft.1` remains
  authoritative and `ACKNOWLEDGED_AND_MERGED`; its semantic body is
  `SEMANTIC_INTEGRITY_PRESERVED / NO_SEMANTIC_CHANGE_REQUIRED`.
- Owner dispositions: DB-ISSUE-011 is
  `ACCEPTED_WITH_DOCUMENTATION_CLARIFICATION`; DB-ISSUE-012 is
  `ACCEPTED_AS_COMPATIBLE`; DB-ISSUE-013 is
  `ACCEPTED_FOR_DB002_DEFERRED_FOR_TYPED_CONTRACT` and remains
  `OPEN_NON_BLOCKING / DEFERRED_TYPED_CONTRACT`.
- Physical decisions preserved: `runs.run_request_id UNIQUE` represents one
  current run projection per durable request; regeneration creates a new
  request and run, while DB-003 history is not duplicate current-run rows.
  Failure codes retain anchored uppercase additive family patterns rather than
  a frozen enumeration. `terminal_actor_id` remains bounded opaque storage with
  no Auth foreign key; Auth and Workflow jointly own a future typed relationship
  that may be added by a future contract and migration.
- Correction decision: model correction `NONE`; migration correction `NONE`;
  constraint correction `NONE`; test correction `NONE`.
- Boundary: DB-002 remains `PASS / VERIFIED_COMPLETE / MERGED`; DB-DEP-011
  remains `ACCEPTED / VERIFIED_COMPLETE / CLOSED`; DB-003 remains
  `NOT_STARTED / NOT_AUTHORIZED`. This decision does not begin or authorize
  DB-003, create steps, attempts, run events, ordering, transition history,
  Queue persistence, Evidence persistence, or runtime behavior, or authorize an
  A3-DATABASE DB-003 implementation prompt. Auth runtime is
  `NOT_STARTED / NOT_TESTED`; Workflow runtime is
  `NOT_IMPLEMENTED / NOT_TESTED`; `CONTRACT-QUEUE-001`: `NOT_CREATED`;
  `CONTRACT-EVIDENCE-001`: `NOT_CREATED`.
- Dependency result: `WORKFLOW_OWNER_RESPONSE_ACKNOWLEDGED` /
  `WORKFLOW_DB002_RECONCILIATION_DEPENDENCY_SATISFIED`.

## `DB-DEC-001` — Persistence baseline

- Historical status at DB-DEC-001: `VERIFIED_COMPLETE`; the
  PostgreSQL/SQLAlchemy/Alembic scaffold was `IMPLEMENTED`, while domain schema
  was `NOT_STARTED`. Current DB-002 domain schema status is `IMPLEMENTED`.
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
- DB-002 boundary: the Auth and Workflow direct contract prerequisites are
  satisfied and merged. API, Queue, Security, Deployment, and Integration
  remain scoped constraints where applicable, not universal DB-002
  prerequisites.

## `DB-DEC-010` — Shared scaffold ownership

- Status: `IMPLEMENTED`.
- Decision: A3-DATABASE will not create unowned protected application-root, package, dependency, lock, environment, container, or test-harness files.
- Resolution: A2-INTEGRATION coordinated ownership; Backend and Deployment
  scaffolds are merged and the Database-owned scaffold is implemented.

## `DB-DEC-011` — Minimal synchronous Database scaffold

- Date: 2026-07-30
- Status: `IMPLEMENTED`, reviewed, and merged through Database PR #6 and merge
  commit `739a331c9942ed64a1ad8276d611889bbee53a27`. DB-DEP-011 completed final
  A2-INTEGRATION clean-checkout PostgreSQL 16 validation and is
  `ACCEPTED / VERIFIED_COMPLETE / CLOSED` through Integration closeout merge
  commit `8884b5d540351c735b6cddc01314a7dd9e25af05`.
- Decision: runtime engines are explicit synchronous SQLAlchemy factories using
  psycopg 3 and `pool_pre_ping=True`; sessions use `autoflush=False` and
  `expire_on_commit=False`; request dependencies roll back escaping exceptions,
  always close, and never auto-commit.
- Credential boundary: runtime resolution uses `DATABASE_URL` only. Migration
  resolution prefers `MIGRATION_DATABASE_URL`, permits `DATABASE_URL` fallback
  only when `TESTGAP_RUNTIME` exactly equals `local`, and otherwise fails closed.
- Test boundary: `TEST_DATABASE_URL` must use `postgresql+psycopg`, name a
  database ending exactly in `_test`, and differ from `DATABASE_URL`; errors
  never include credentials. The authoritative production host registry remains
  separately pending under `DB-ISSUE-008`.
- Migration boundary: empty `MetaData`, zero heads, no baseline revision,
  explicit `-c apps/api/alembic.ini`, synchronous online mode, and supported
  offline mode.
- Historical scope at the time of DB-DEC-011: no DB-002 model, table, enum,
  constraint, index, Auth/Workflow field, or revision existed. DB-002 has since
  implemented its seven-table slice through `DB-DEC-014`.

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
- Historical runtime boundary at the time of DB-DEC-012: no Auth or Database
  implementation had been performed and DB-002 was `BLOCKED`. The DB-002 schema
  has since been implemented; Auth runtime is `NOT_STARTED / NOT_TESTED`.

## `DB-DEC-013` — Workflow contract acceptance

- Date: 2026-08-01
- Status: `ACCEPTED`; `CONTRACT-WORKFLOW-001@1.0.0-draft.1` is
  `ACKNOWLEDGED_AND_MERGED` through PR #8 and merge commit
  `7da1132b9e30b51a212aa6574c23e2a832d9a6fd`.
- State contract decision: persist the exact canonical `RunState` text and
  validate allowed stored values. The Workflow runtime is responsible for the
  allowed-transition table, expected-state-and-version compare/update, and
  terminal-state update rejection after commit; DB-002 does not implement those
  operations.
- Counter decision: `repair_attempts_used` is constrained to `0..1`; repair
  and retry remain separate, and a repaired candidate repeats buggy then fixed
  execution.
- Identity decision: internal UUIDs remain separate from external identifiers.
  Request identity uses versioned canonical idempotency-key composition, a
  persisted key version, bounded digest, and request fingerprint for conflict
  detection.
- Ownership decision: DB-002 owns only `run_requests` and current `runs`
  projections. DB-003 owns steps, attempts, append-only events, event ordering,
  producer-event idempotency, and transition history.
- Payload decision: lifecycle payloads contain bounded redacted metadata or
  opaque references only; raw prompts, repository bytes, patch bytes, logs,
  and secrets are prohibited. Queue, Evidence, and Security payload fields are
  deferred to their versioned owner contracts.
- Compatibility: any future incompatible Workflow change requires a versioned
  Workflow contract, Database consumer review, migration-impact analysis,
  affected-consumer acknowledgement, and Integration coordination.
- Historical runtime boundary at the time of acceptance: no Workflow or Database
  implementation had been performed. DB-002 has since implemented only the
  durable request/current-projection storage subset; see `DB-DEC-014`. Workflow
  runtime and DB-003 event history remain unimplemented.

## `DB-DEC-014` — DB-002 physical schema

- Date: 2026-08-01
- Status: `IMPLEMENTED` and `MERGED` through implementation pull request #12,
  implementation commit `5506ab59211fbaba79f77d4fb5899a587c0e0236` and implementation merge commit
  `3701520e6d61e2bb80391e7af888d0d530bdb6c4`. Alembic revision `ad3f80907336`
  (`create DB-002 core entities`) is the single head. Full documentation is in
  `docs/data/database-schema.md`.
- Declarative boundary: one `MetaData` in `app/db/metadata.py` carrying the
  constraint and index naming convention, one `DeclarativeBase` in
  `app/db/base.py`, models in `app/db/models/**`, and `alembic/env.py`
  importing that package so `target_metadata` contains every DB-002 table.
  SQLAlchemy remains synchronous on psycopg 3.
- Identifier decision: UUID primary keys generated client-side as `uuid4`, so no
  PostgreSQL extension is required. External identifiers use their own types —
  `BIGINT` for GitHub numeric IDs, bounded text for delivery GUIDs, SHAs,
  benchmark IDs, model IDs, prompt versions, and correlation IDs.
- Enumeration decision: statuses, request kinds, states, terminal actor types,
  abstention codes, and cancellation codes are stored as exact uppercase text
  with Database-owned check constraints. Failure codes use matching anchored
  PostgreSQL family patterns — `^INPUT_[A-Z0-9]+(_[A-Z0-9]+)*$`,
  `^MODEL_[A-Z0-9]+(_[A-Z0-9]+)*$`,
  `^EXECUTION_[A-Z0-9]+(_[A-Z0-9]+)*$`,
  `^INFRASTRUCTURE_[A-Z0-9]+(_[A-Z0-9]+)*$`, and
  `^SECURITY_[A-Z0-9]+(_[A-Z0-9]+)*$` — so unknown additive uppercase codes
  remain representable while malformed or cross-family values are rejected. No
  PostgreSQL `ENUM` type is created.
- Issuer/subject decision: a plain `UNIQUE (issuer, subject)` constraint in the
  default collation. `citext` and case-folding functional indexes are prohibited
  and absent.
- Access-history decision: a partial unique index
  `uq_repository_access_active` over
  `(user_id, installation_id, repository_id) WHERE status = 'ACTIVE'`. This
  enforces at most one active grant per exact tuple while leaving revoked and
  expired grants stored and attributable, and while keeping a later re-grant
  representable. A permanent unique constraint was explicitly rejected because it
  would block a valid future re-grant.
- Expiry/revocation decision: `expires_at`, `expired_at`, and `revoked_at` are
  separate columns with check constraints that keep expiration and revocation
  distinguishable and prevent either from substituting for the other. An
  `ACTIVE` grant with a past `expires_at` stays storable, because the contract
  places that authorization boundary at read time, before delayed status
  reconciliation.
- Run-projection decision: `runs.run_request_id` remains unique under closed
  `DB-ISSUE-011` (`ACCEPTED_WITH_DOCUMENTATION_CLARIFICATION`); changing that
  cardinality requires Workflow consumer and migration review. Failure codes use
  the anchored uppercase family patterns under closed `DB-ISSUE-012`
  (`ACCEPTED_AS_COMPATIBLE`); unknown additive codes remain storable
  and terminal state stays the compatibility boundary. Terminal attribution is
  bounded opaque text with no foreign key under `DB-ISSUE-013`
  (`OPEN_NON_BLOCKING / DEFERRED_TYPED_CONTRACT`;
  `ACCEPTED_FOR_DB002_DEFERRED_FOR_TYPED_CONTRACT`).
- Index decision: only justified DB-002 lookup paths are indexed — the partial
  active-access index, the foreign-key reverse-lookup indexes PostgreSQL does not
  create automatically, and the contract-required unique indexes. No state
  worklist, timestamp ordering, or other speculative index for a later task was
  added.
- Secret decision: no domain table has a password, hash, token, private key,
  webhook secret, session token, raw Authorization header, raw prompt, repository
  byte, patch byte, or execution log column. This is asserted over both the ORM
  metadata and the reflected PostgreSQL columns.
- Migration decision: a single revision with a complete downgrade, no seed data,
  and no DB-003 or later table. Multiple revisions were not required.
- Scope decision: DB-002 created no DB-003 or later table, no Auth or Workflow
  runtime, no API route, no service orchestration, and no trigger.
- Enforcement boundary: DB-002 implements and tests stored state vocabulary,
  terminal/non-terminal row shape, counter bounds, code consistency, version
  storage, and terminal attribution. It does not implement or test transition
  execution, expected-state-and-version compare/update, atomic projection/event
  mutation, transition history, terminal update rejection, regeneration
  decision-event persistence, or Workflow orchestration.
