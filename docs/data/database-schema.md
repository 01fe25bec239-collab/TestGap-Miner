# DB-002 schema — core identity, repository context, and workflow projections

- Task: `DB-002 — Core identity, repository-context, run-request, and run persistence`
- Owner: `A2-DATABASE`
- Accepted contracts: `CONTRACT-AUTH-001@1.0.0-draft.2`,
  `CONTRACT-WORKFLOW-001@1.0.0-draft.1`
- Alembic revision: `ad3f80907336` — `create DB-002 core entities`
- Down revision: `None` (first revision); heads: exactly one
- Target: PostgreSQL 16 (validated on `16.14`)

DB-002 implements exactly seven tables. No Auth runtime, Workflow runtime, API
route, service layer, queue consumer, or orchestration trigger exists. The
constraints below describe which rows are representable, not which transition
sequences are legal.

## Declarative boundary

- `app/db/metadata.py` holds the single `MetaData` instance and the naming
  convention that produces every constraint and index name.
- `app/db/base.py` defines the one `DeclarativeBase` bound to that `MetaData`,
  mapping `uuid.UUID` to `sa.Uuid` and `datetime` to
  `sa.DateTime(timezone=True)`.
- `app/db/models/auth.py` and `app/db/models/workflow.py` hold the models.
- `app/db/models/__init__.py` re-exports them; `alembic/env.py` imports the
  package so `target_metadata` contains every DB-002 table.
- SQLAlchemy is synchronous throughout, on psycopg 3, as in the DB-DEP-011
  scaffold. There is no second `MetaData`, and
  `tests/database/test_schema.py::test_models_share_one_metadata_instance`
  asserts that.

Naming convention:

| Kind | Pattern |
|---|---|
| Primary key | `pk_%(table_name)s` |
| Foreign key | `fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s` |
| Unique | `uq_%(table_name)s_%(column_0_N_name)s` |
| Check | `ck_%(table_name)s_%(constraint_name)s` |
| Index | `ix_%(table_name)s_%(column_0_N_name)s` |

Every primary key is a client-generated `uuid4` stored as PostgreSQL `UUID`; no
database extension is required. Every timestamp is `TIMESTAMP WITH TIME ZONE`.
Nullability is explicit on every column.

## Table purposes

| Table | Purpose | Contract source |
|---|---|---|
| `users` | Canonical human user | `CONTRACT-AUTH-001` §Canonical human user |
| `auth_subjects` | External authentication subject linked to one user | §External authentication subject |
| `github_installations` | GitHub App installation identity and lifecycle | §GitHub App installation identity and lifecycle |
| `repositories` | Repository identity and lifecycle | §Repository identity and lifecycle |
| `repository_access` | Exact user + installation + repository grant | §Exact repository-access grant |
| `run_requests` | Durable invocation record and idempotency boundary | `CONTRACT-WORKFLOW-001` §Run request projection |
| `runs` | Current run projection | §Run projection |

## Relationships

```text
users 1──* auth_subjects
users 1──* repository_access *──1 github_installations
                             *──1 repositories
repositories        1──* run_requests   (nullable repository scope)
auth_subjects       1──* run_requests   (nullable requesting subject)
run_requests        1──1 runs
runs                1──* runs           (parent_run_id regeneration lineage)
```

All foreign keys are explicit and use the default `NO ACTION` referential
action, so a parent row cannot be deleted while a historical child references
it. Every relationship is declared on the ORM side as well.

## Auth-contract field mapping

### `users`

| Column | Type | Null | Contract field |
|---|---|---|---|
| `id` | `UUID` | no | `user_id` |
| `status` | `TEXT` default `ACTIVE` | no | `status`: `ACTIVE` / `SUSPENDED` / `DEPROVISIONED` |
| `created_at` | `TIMESTAMPTZ` default `now()` | no | `created_at` |
| `updated_at` | `TIMESTAMPTZ` default `now()`, `onupdate` | no | `updated_at` |
| `suspended_at` | `TIMESTAMPTZ` | yes | nullable `suspended_at` |
| `deprovisioned_at` | `TIMESTAMPTZ` | yes | nullable `deprovisioned_at` |

Email, username, login name, and display name are not identity keys, so they are
not stored. The contract states MVP requires no password hash or local
credential field, and none exists.

Constraints: `ck_users_status_allowed`, `ck_users_suspended_at_present`
(`SUSPENDED` implies `suspended_at`), `ck_users_deprovisioned_at_present`.
Neither timestamp check forbids a historical timestamp on a later-reactivated
`ACTIVE` user.

### `auth_subjects`

| Column | Type | Null | Contract field |
|---|---|---|---|
| `id` | `UUID` | no | `auth_subject_id` |
| `user_id` | `UUID` FK `users.id` | no | `user_id` |
| `issuer` | `TEXT` | no | `issuer`, stored exactly as supplied |
| `subject` | `TEXT` | no | opaque case-sensitive `subject` |
| `provider_name` | `TEXT` | yes | optional `provider_name` |
| `provider_account_id` | `TEXT` | yes | optional immutable `provider_account_id` |
| `status` | `TEXT` default `ACTIVE` | no | `status`: `ACTIVE` / `REVOKED` |
| `linked_at` | `TIMESTAMPTZ` default `now()` | no | `linked_at` |
| `revoked_at` | `TIMESTAMPTZ` | yes | nullable `revoked_at` |

`uq_auth_subjects_issuer_subject` is a plain unique constraint over
`(issuer, subject)` in the default collation. Comparison is therefore exact and
case-sensitive on the stored bytes. The Database performs no lowercasing,
uppercasing, trimming, URL normalization, trailing-character removal, or alias
resolution. **`citext` is not used and there is no functional
`lower()`/`upper()` index on either column** — both are prohibited by the
accepted contract and asserted by
`test_issuer_subject_uniqueness_is_exact_and_not_case_folded`.

`ck_auth_subjects_revoked_at_present` requires `revoked_at` for a `REVOKED`
subject. It deliberately does not force `revoked_at` to be null while `ACTIVE`:
because `(issuer, subject)` uniqueness is permanent for subjects, a later
re-link must reuse the same row and may retain its revocation history.

Uniqueness is on the pair only, so the same `issuer` may serve many subjects and
the same opaque `subject` string may legitimately appear under a different
issuer.

### `github_installations`

| Column | Type | Null | Contract field |
|---|---|---|---|
| `id` | `UUID` | no | `installation_id` |
| `github_installation_id` | `BIGINT` unique | no | unique GitHub numeric installation ID |
| `github_account_id` | `BIGINT` | no | immutable GitHub numeric account ID |
| `account_type` | `TEXT` | no | `USER` / `ORGANIZATION` |
| `status` | `TEXT` default `ACTIVE` | no | `ACTIVE` / `SUSPENDED` / `DELETED` |
| `installed_at` | `TIMESTAMPTZ` default `now()` | no | `installed_at` |
| `suspended_at` | `TIMESTAMPTZ` | yes | nullable `suspended_at` |
| `deleted_at` | `TIMESTAMPTZ` | yes | nullable `deleted_at` |
| `last_synced_at` | `TIMESTAMPTZ` default `now()` | no | `last_synced_at` |

Installation access tokens and GitHub App private keys are never stored.
Constraints: `ck_github_installations_status_allowed`,
`ck_github_installations_account_type_allowed`,
`ck_github_installations_github_ids_positive`,
`ck_github_installations_suspended_at_present`,
`ck_github_installations_deleted_at_present`.

### `repositories`

| Column | Type | Null | Contract field |
|---|---|---|---|
| `id` | `UUID` | no | `repository_id` |
| `github_repository_id` | `BIGINT` unique | no | unique GitHub numeric repository ID |
| `status` | `TEXT` default `ACTIVE` | no | `ACTIVE` / `ARCHIVED` / `INACCESSIBLE` / `DELETED` |
| `created_at` / `updated_at` / `last_synced_at` | `TIMESTAMPTZ` default `now()` | no | as named |

Owner and name strings are mutable display metadata that must never authorize
access, so DB-002 does not persist them; see the deferred-fields section.
Repository source bytes stay outside PostgreSQL.

### `repository_access`

| Column | Type | Null | Contract field |
|---|---|---|---|
| `id` | `UUID` | no | `repository_access_id` |
| `user_id` | `UUID` FK `users.id` | no | `user_id` |
| `installation_id` | `UUID` FK `github_installations.id` | no | `installation_id` |
| `repository_id` | `UUID` FK `repositories.id` | no | `repository_id` |
| `status` | `TEXT` default `ACTIVE` | no | `ACTIVE` / `REVOKED` / `EXPIRED` |
| `authorization_source` | `TEXT` default `GITHUB_VERIFIED` | no | `authorization_source` |
| `granted_at` | `TIMESTAMPTZ` default `now()` | no | `granted_at` |
| `last_verified_at` | `TIMESTAMPTZ` default `now()` | no | `last_verified_at` |
| `expires_at` | `TIMESTAMPTZ` | yes | scheduled validity boundary |
| `expired_at` | `TIMESTAMPTZ` | yes | when the grant was recorded expired |
| `revoked_at` | `TIMESTAMPTZ` | yes | explicit withdrawal |

Authorization scope is the exact `user + installation + repository` tuple. A
substituted user, installation, or repository is a different tuple and simply
has no active grant row; DB-002 provides no authorization service, so the
"denied" outcomes in the contract fixture are tested here as exact-tuple lookups
returning nothing.

#### Access-grant history design

`uq_repository_access_active` is a **partial unique index**:

```sql
CREATE UNIQUE INDEX uq_repository_access_active
  ON repository_access (user_id, installation_id, repository_id)
  WHERE status = 'ACTIVE';
```

This is the chosen mechanism for "at most one active grant per exact tuple"
without a permanent uniqueness rule. Consequences:

- Two `ACTIVE` rows for one tuple are rejected.
- `REVOKED` and `EXPIRED` rows are unconstrained by it, so historical grants stay
  stored and attributable, with their user, installation, and repository foreign
  keys intact.
- After a grant becomes inactive, a valid new `ACTIVE` grant for the same tuple
  inserts successfully, so a future re-grant is representable.

Lifecycle checks keep revocation and expiration distinguishable, as the contract
requires:

| Constraint | Rule |
|---|---|
| `ck_repository_access_active_not_terminated` | `ACTIVE` implies `expired_at IS NULL AND revoked_at IS NULL`. A future or null `expires_at` remains valid on an `ACTIVE` grant. |
| `ck_repository_access_revoked_at_present` | `REVOKED` requires `revoked_at`. |
| `ck_repository_access_expiry_distinct_from_revocation` | `EXPIRED` requires at least one of `expires_at` / `expired_at`, and forbids `revoked_at`. |
| `ck_repository_access_status_allowed`, `..._authorization_source_allowed` | Accepted value sets. |

An `ACTIVE` grant whose `expires_at` has already passed is intentionally still
storable: the contract states authorization expiry occurs at `expires_at` before
delayed status reconciliation, and consumers must not treat a past `expires_at`
as authorized. Enforcing that boundary is a read-time consumer obligation, not a
storage constraint.

## Workflow-contract field mapping

### `run_requests`

| Column | Type | Null | Contract field |
|---|---|---|---|
| `id` | `UUID` | no | `id` |
| `request_kind` | `TEXT` | no | `request_kind`: `GITHUB` / `BENCHMARK` |
| `idempotency_key` | `VARCHAR(128)` | no | `idempotency_key`, bounded digest |
| `idempotency_key_version` | `INTEGER` default `1` | no | persisted idempotency-key version (Database-owned physical mapping accepted in `DB-DEC-013`) |
| `request_fingerprint` | `VARCHAR(128)` | no | request fingerprint for conflict detection (same accepted mapping) |
| `github_delivery_guid` | `TEXT` | yes | `github_delivery_guid` |
| `github_repository_id` | `BIGINT` | yes | `github_repository_id` |
| `repository_sha` | `VARCHAR(64)` | yes | `repository_sha` |
| `benchmark_project_id` | `TEXT` | yes | `benchmark_project_id` |
| `benchmark_bug_id` | `TEXT` | yes | `benchmark_bug_id` |
| `configuration_version` | `TEXT` | no | `configuration_version` |
| `model_id` | `TEXT` | no | `model_id` |
| `prompt_template_version` | `TEXT` | no | `prompt_template_version` |
| `repository_id` | `UUID` FK `repositories.id` | yes | internal repository relation carrying repository scope, including for benchmark requests |
| `requested_by_subject` | `UUID` FK `auth_subjects.id` | yes | `requested_by_subject`, resolved against the now-accepted Auth shape |
| `correlation_id` | `VARCHAR(255)` | yes | bounded `correlation_id`, not an identity key |
| `created_at` | `TIMESTAMPTZ` default `now()` | no | `created_at` |

Idempotency uniqueness is `uq_run_requests_idempotency_key_version_idempotency_key`
over `(idempotency_key_version, idempotency_key)`. The version participates so a
future composition version cannot collide with an already-stored key. A replay of
the same normalized tuple resolves to the stored request; a conflicting payload
reusing the same key violates the unique constraint and is rejected rather than
overwritten, and `request_fingerprint` lets the caller tell an identical replay
apart from a conflicting one.

`ck_run_requests_kind_field_shape` encodes the contract's kind rules: a `GITHUB`
request requires delivery GUID, GitHub repository ID, and repository SHA and
prohibits both benchmark fields; a `BENCHMARK` request requires both benchmark
fields and prohibits the delivery GUID. Repository scope for a benchmark uses
`repository_id`, never an overloaded benchmark identifier.

Every external identifier is separately typed: `BIGINT` for GitHub numeric IDs,
bounded text for delivery GUIDs, SHAs, benchmark IDs, model IDs, prompt versions,
and correlation IDs. None populates or masquerades as an internal `UUID`.

### `runs`

| Column | Type | Null | Contract field |
|---|---|---|---|
| `id` | `UUID` | no | `id` |
| `run_request_id` | `UUID` FK `run_requests.id`, unique | no | `run_request_id` |
| `state` | `TEXT` default `RECEIVED` | no | exact canonical `RunState` |
| `contract_version` | `VARCHAR(64)` | no | `contract_version` |
| `review_required` | `BOOLEAN` default `true` | no | `review_required` |
| `repair_attempts_used` | `INTEGER` default `0` | no | `repair_attempts_used`, `0..1` |
| `retry_attempts_used` | `INTEGER` default `0` | no | `retry_attempts_used` |
| `retry_limit` | `INTEGER` | no | `retry_limit` |
| `step_attempts_used` | `INTEGER` default `0` | no | `step_attempts_used` |
| `version` | `INTEGER` default `0` | no | optimistic-concurrency `version` |
| `created_at` / `updated_at` | `TIMESTAMPTZ` default `now()` | no | as named |
| `terminal_at` | `TIMESTAMPTZ` | yes | required exactly when `state` is terminal |
| `failure_code` | `TEXT` | yes | required only for `FAILED_*` |
| `abstention_code` | `TEXT` | yes | required only for `ABSTAINED` |
| `cancellation_code` | `TEXT` | yes | required only for `CANCELLED` |
| `terminal_actor_type` | `TEXT` | yes | terminal attribution type |
| `terminal_actor_id` | `VARCHAR(255)` | yes | terminal attribution identity, bounded and opaque |
| `checkpoint_ref` | `VARCHAR(512)` | yes | opaque checkpoint reference |
| `parent_run_id` | `UUID` FK `runs.id` | yes | regeneration lineage |

The twenty canonical `RunState` values are persisted as exact uppercase text and
enforced by `ck_runs_state_allowed`. Declaration order carries no transition
meaning and no ordering is stored.

Counter and lifecycle constraints:

| Constraint | Rule |
|---|---|
| `ck_runs_repair_attempts_used_range` | `BETWEEN 0 AND 1` — one automated repair maximum |
| `ck_runs_retry_limit_non_negative`, `ck_runs_retry_attempts_used_range` | retries are non-negative and never exceed the snapshotted limit; they are independent of `repair_attempts_used`, so retry and repair remain different concepts |
| `ck_runs_step_attempts_used_non_negative`, `ck_runs_version_non_negative` | non-negative counters, including the optimistic-concurrency version |
| `ck_runs_terminal_at_matches_state` | `terminal_at` is present exactly for the eight terminal states |
| `ck_runs_terminal_actor_matches_state` | terminal rows carry both actor type and actor ID; non-terminal rows carry neither |
| `ck_runs_terminal_actor_type_allowed` | `SYSTEM` / `WORKFLOW` / `WORKER` / `HUMAN` |
| `ck_runs_abstention_code_matches_state` | closed contract list, required only for `ABSTAINED` |
| `ck_runs_cancellation_code_matches_state` | closed contract list, required only for `CANCELLED` |
| `ck_runs_failure_code_matches_state` | required only for `FAILED_*`, and constrained to that state's anchored uppercase code-family pattern |
| `ck_runs_parent_run_id_not_self` | a run cannot be its own parent |

Failure codes use anchored PostgreSQL regular expressions by family:
`^INPUT_[A-Z0-9]+(_[A-Z0-9]+)*$`,
`^MODEL_[A-Z0-9]+(_[A-Z0-9]+)*$`,
`^EXECUTION_[A-Z0-9]+(_[A-Z0-9]+)*$`,
`^INFRASTRUCTURE_[A-Z0-9]+(_[A-Z0-9]+)*$`, and
`^SECURITY_[A-Z0-9]+(_[A-Z0-9]+)*$`. This preserves unknown additive uppercase
codes while keeping terminal state as the compatibility boundary. Published
codes and valid additive codes are accepted; bare prefixes, lowercase,
whitespace, hyphens, double underscores, and cross-family codes are rejected.
Abstention and cancellation codes remain closed lists.

`terminal_actor_id` is a bounded opaque value rather than a foreign key, because
the contract still marks the Auth-owned human identity shape as provisional for
terminal attribution.

`run_request_id` is unique: the contract pairs one durable request with one
initial run projection, and a human regeneration creates a new request and a new
run rather than a second run under the same request. This is the accepted
Database physical decision recorded by closed `DB-ISSUE-011`; changing the
cardinality later requires Workflow consumer and migration review.

## Indexes

| Index | Table | Supports | Selectivity | Uniqueness | Lifecycle implication |
|---|---|---|---|---|---|
| `uq_repository_access_active` | `repository_access` | The exact-tuple active-authorization lookup and the "one active grant per tuple" rule | Very high — at most one row per tuple | Unique, partial (`status = 'ACTIVE'`) | Only `ACTIVE` rows participate, so revoked/expired history is retained and a re-grant stays possible |
| `ix_repository_access_user_id` | `repository_access` | Historical attribution for a user, and revocation sweeps on suspension/deprovisioning | Medium — few grants per user | Non-unique | Covers inactive rows the partial unique index excludes; required because PostgreSQL does not index foreign keys automatically |
| `ix_repository_access_installation_id` | `repository_access` | Cascade of installation suspension/deletion to affected grants | Medium | Non-unique | Same |
| `ix_repository_access_repository_id` | `repository_access` | Cascade of repository archival/inaccessibility to affected grants | Medium | Non-unique | Same |
| `ix_auth_subjects_user_id` | `auth_subjects` | Resolving all external subjects for a canonical user | High — few subjects per user | Non-unique | Includes revoked subjects |
| `ix_run_requests_repository_id` | `run_requests` | Request history for a repository | Medium | Non-unique | Supports the FK integrity check on repository rows |
| `ix_run_requests_requested_by_subject` | `run_requests` | Request attribution for a subject | Medium | Non-unique | Retains attribution after the subject is revoked |
| `ix_runs_parent_run_id` | `runs` | Finding regenerated children of a completed run | Very high — usually zero or one | Non-unique | Lineage survives after the parent run is terminal |
| `uq_auth_subjects_issuer_subject` | `auth_subjects` | Exact `(issuer, subject)` identity resolution | Unique | Unique | Permanent; a re-link reuses the row |
| `uq_github_installations_github_installation_id` | `github_installations` | External installation identity resolution | Unique | Unique | Survives suspension and deletion |
| `uq_repositories_github_repository_id` | `repositories` | External repository identity resolution | Unique | Unique | Survives archival and deletion |
| `uq_run_requests_idempotency_key_version_idempotency_key` | `run_requests` | Versioned request-idempotency resolution and conflict rejection | Unique | Unique | Permanent; requests are immutable |
| `uq_runs_run_request_id` | `runs` | One current projection per request | Unique | Unique | Regeneration produces a new request, not a second run |

Primary-key indexes are implied and not listed. No speculative index for DB-003
or later work was added: there is no state worklist index, no `created_at`
ordering index, and no partial index over non-terminal runs, because no query
owner has contracted those paths.

## Lifecycle, deletion, and historical attribution

- Suspension, revocation, expiration, inaccessibility, deletion, and
  deprovisioning are all status plus timestamp changes. No row is deleted.
- Foreign keys use the default restrictive action, so a user, installation, or
  repository referenced by history cannot be removed by a cascade.
- A `DEPROVISIONED` user, a `SUSPENDED` installation, and an `INACCESSIBLE`
  repository all remain fully joinable from their historical grants.
- Terminal run projections store their state, `terminal_at`, terminal code, and
  terminal attribution. This is storage, not terminal-update rejection. DB-002
  stores no transition history; runtime enforcement and the append-only event
  record that makes terminal immutability auditable are later work.
- Retention durations remain unfrozen pending `CONTRACT-SEC-001` and
  `CONTRACT-DEPLOY-001` (`DB-ISSUE-004`).

## Prohibited secret storage

No table stores a password, password hash, OAuth authorization code, OAuth
access or refresh token, GitHub App private key or JWT, installation access
token, webhook secret, JWT signing secret, provider API key, browser session
token, or raw `Authorization` header. No table stores a raw prompt, repository
bytes, patch bytes, or an execution log.

`tests/database/test_schema.py` asserts this twice — once over the ORM metadata
and once over the reflected PostgreSQL columns — using a name pattern covering
`password`, `secret`, `token`, `private_key`, `api_key`, `credential`,
`authorization_header`, `session_key`, `signing_key`, and `jwt`.

## DB-002 versus DB-003 boundary

DB-002 owns: `users`, `auth_subjects`, `github_installations`, `repositories`,
`repository_access`, `run_requests`, `runs`.

DB-003 and later own, and DB-002 deliberately does not create: workflow steps,
step attempts, append-only run events, event ordering and sequence allocation,
producer-event idempotency, transition history, checkpoints as records, context
selections, candidate patches, patch contents, execution evidence and attempts,
artefact metadata, publications, human decisions, benchmark cases, evaluation
results, audit and security events, model or cost telemetry, and notifications.

Also permanently out of scope for the MVP: generic organizations, tenants, roles,
permissions, billing tables, API-key tables, embedding tables, and pgvector.

DB-002 implements and tests allowed stored states, terminal/non-terminal row
shape, counter bounds, failure/abstention/cancellation code consistency,
optimistic-concurrency version storage, and terminal-attribution storage. It
does not implement or test allowed-transition execution, an expected-state and
version compare/update operation, atomic projection/event mutation, append-only
transition history, terminal-state update rejection after commit, regeneration
decision-event persistence, or Workflow orchestration. No orchestration trigger
exists.

`tests/database/test_schema.py::test_no_db_003_or_later_table_exists` asserts the
migrated database contains exactly the seven DB-002 tables plus
`alembic_version`.

## Deferred owner-controlled fields

| Deferred item | Owner | Why it is absent |
|---|---|---|
| Repository owner/name display strings | Auth / API | Mutable display metadata that must not authorize access; no contracted query needs them yet |
| User email, username, display name | Auth | Explicitly not identity keys; no contract requires storage |
| Queue lease, visibility timeout, redelivery count, envelope fields | Queue | Provisional until `CONTRACT-QUEUE-001` (`DB-DEP-006`) |
| Evidence, artefact, and checksum fields | Evidence | Provisional until `CONTRACT-EVIDENCE-001` (`DB-DEP-005`) |
| Security-event and redaction fields | Security | Provisional until `CONTRACT-SEC-001` (`DB-DEP-008`) |
| Evaluation and metric fields | Evaluation | Provisional until `CONTRACT-EVAL-001` (`DB-DEP-007`) |
| API pagination, filter, and sort projections | Backend | Provisional until `CONTRACT-API-001` (`DB-DEP-002`); no speculative index added |
| Concrete terminal-actor identity shape | Auth / Workflow | Contract still marks terminal human attribution provisional; stored as bounded opaque text |

## Migration

Revision `ad3f80907336`, message `create DB-002 core entities`, down revision
`None`. It creates only DB-002 tables, constraints, and indexes; it contains no
seed data, no secret, and no DB-003 table. `downgrade()` drops every object it
creates, returning the database to the zero-revision state while the migration
remains unconsumed.

Run every command from the repository root with the explicit configuration:

```text
uv run --project apps/api alembic -c apps/api/alembic.ini heads
uv run --project apps/api alembic -c apps/api/alembic.ini history --verbose
uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
uv run --project apps/api alembic -c apps/api/alembic.ini downgrade base
```

`alembic/env.py` resolves its URL from `MIGRATION_DATABASE_URL`, falling back to
`DATABASE_URL` only when `TESTGAP_RUNTIME` is exactly `local`. There is exactly
one head.

## Tests

| File | Covers |
|---|---|
| `tests/database/test_alembic.py` | Exactly one head, one revision, correct message, no forbidden table or seed data in the revision, complete downgrade coverage |
| `tests/database/test_migration_cycle.py` | Upgrade from empty, downgrade to the zero-revision state, second upgrade, restored constraints and partial unique index |
| `tests/database/test_schema.py` | Table set, forbidden-table absence, UUID primary keys, timezone-aware timestamps, exact issuer/subject uniqueness with no case folding, unique external IDs, partial active-access uniqueness, explicit foreign keys, named check constraints, secret-column absence |
| `tests/database/test_auth_constraints.py` | The accepted two-user / two-installation / two-repository fixture, exact-tuple scoping, duplicate subject rejection, case-distinct identities, byte-exact storage, duplicate external ID rejection, revoked-versus-expired distinction, historical attribution, active-grant uniqueness, re-grant after revocation and after expiry |
| `tests/database/test_workflow_constraints.py` | All twenty canonical states accepted, unknown and lowercase states rejected, repair bounds, non-negative version and retry counters, idempotency uniqueness and versioning, kind field shape, UUID versus external identity separation, terminal timestamp/attribution rules, failure/abstention/cancellation code rules, regeneration lineage |

Schema tests use `TEST_DATABASE_URL` for DML and the migration role pointed at
the same isolated test database for DDL, matching `CONTRACT-DEPLOY-001`. They
skip when those variables are absent. No transition orchestration is tested,
because DB-002 implements no transition service.
