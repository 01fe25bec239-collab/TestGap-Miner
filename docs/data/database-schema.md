# Database schema — DB-002 core and DB-003 workflow persistence

- Tasks: `DB-002 — Core identity, repository-context, run-request, and run
  persistence`; `DB-003-WORKFLOW-PERSISTENCE-IMPLEMENTATION-001`
- Owner: `A2-DATABASE`
- Accepted contracts: `CONTRACT-AUTH-001@1.0.0-draft.2`,
  `CONTRACT-WORKFLOW-001@1.0.0-draft.1`; provider-neutral identity boundaries
  consumed from `CONTRACT-QUEUE-001@1.0.0-draft.2`
- Alembic revisions: `ad3f80907336` — `create DB-002 core entities`;
  `e7b4c2d9a631` — `create DB-003 workflow persistence`
- DB-003 down revision: `ad3f80907336`; current head: `e7b4c2d9a631`;
  heads: exactly one
- Target: PostgreSQL 16 (validated on `16.14`)

DB-002 implements seven tables and DB-003 adds exactly three. No Auth runtime,
Workflow runtime, Queue runtime/provider/adapter, API route, service layer,
Evidence persistence, or transition chooser exists. The constraints below
describe representable rows and frozen transition-history pairs; they never
select when a transition, retry, or repair should happen.

## Declarative boundary

- `app/db/metadata.py` holds the single `MetaData` instance and the naming
  convention that produces every constraint and index name.
- `app/db/base.py` defines the one `DeclarativeBase` bound to that `MetaData`,
  mapping `uuid.UUID` to `sa.Uuid` and `datetime` to
  `sa.DateTime(timezone=True)`.
- `app/db/models/auth.py` and `app/db/models/workflow.py` hold the models.
- `app/db/models/__init__.py` re-exports them; `alembic/env.py` imports the
  package so `target_metadata` contains every current table.
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
| `workflow_steps` | Normalized semantic step occurrences | §Workflow step kinds and attempts |
| `workflow_step_attempts` | Zero-based attempts/retries under one occurrence | §Workflow step kinds and attempts |
| `run_events` | Ordered append-only attributable run timeline | §Ordered append-only events |

## Relationships

```text
users 1──* auth_subjects
users 1──* repository_access *──1 github_installations
                             *──1 repositories
repositories        1──* run_requests   (nullable repository scope)
auth_subjects       1──* run_requests   (nullable requesting subject)
run_requests        1──1 runs
runs                1──* runs           (parent_run_id regeneration lineage)
runs                1──* workflow_steps 1──* workflow_step_attempts
runs                1──* run_events
workflow_steps      1──* run_events      (optional step attribution)
workflow_step_attempts 1──* run_events   (optional attempt attribution)
run_events          1──* run_events      (optional causation link)
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

## DB-003 workflow persistence

### `workflow_steps`

| Column | Type | Null | Physical meaning |
|---|---|---|---|
| `id` | `UUID` | no | Internal step-occurrence identity |
| `run_id` | `UUID` FK `runs.id` | no | Owning run, indexed |
| `kind` | `VARCHAR(64)` | no | Exact Workflow step-kind vocabulary |
| `occurrence` | `INTEGER` | no | Positive semantic occurrence number |
| `created_at` | `TIMESTAMPTZ` default `now()` | no | Database-authored creation time |
| `input_reference` | `VARCHAR(512)` | no | Bounded opaque input reference only |
| `input_version` | `VARCHAR(128)` | no | Bounded immutable input version/reference |

`uq_workflow_steps_run_id_kind_occurrence` enforces one logical occurrence per
run and kind. `ck_workflow_steps_kind_allowed` contains exactly
`VALIDATE_INPUT`, `PLAN`, `LOCALISE`, `GENERATE_CANDIDATE`, `EXECUTE_BUGGY`,
`EXECUTE_FIXED`, `REPAIR_CANDIDATE`, `SCORE_EVIDENCE`, `PUBLISH_DRAFT`, and
`HUMAN_REVIEW`; `ck_workflow_steps_occurrence_positive` requires
`occurrence > 0`. `trg_db003_workflow_steps_immutable` rejects updates so the
input binding and occurrence identity cannot be rewritten. The supporting
`UNIQUE (run_id, id, kind)` key lets event attribution prove that an optional
step belongs to the same run and carries the stored kind.

### `workflow_step_attempts`

| Column | Type | Null | Physical meaning |
|---|---|---|---|
| `id` | `UUID` | no | Internal Workflow-attempt identity, never a Queue identity |
| `step_id` | `UUID` FK `workflow_steps.id` | no | Owning step occurrence, indexed |
| `attempt_index` | `INTEGER` | no | Zero-based retry/attempt position |
| `started_at` / `ended_at` | `TIMESTAMPTZ` | start no / end yes | Attempt interval; end remains null while active |
| `outcome` | `VARCHAR(128)` | yes | Bounded caller-owned outcome; no Execution taxonomy is invented |
| `actor_type` / `actor_id` | `VARCHAR(32)` / `VARCHAR(255)` | no | Exact actor type plus bounded opaque attribution |
| `error_reference` / `evidence_reference` | `VARCHAR(512)` | yes | Opaque references only; no error/log/Evidence bytes |

`UNIQUE (step_id, attempt_index)` plus the step occurrence key proves logical
uniqueness across `(run_id, kind, occurrence, attempt_index)`. Checks require a
non-negative index, an end at or after start, exact actor type, and either an
active shape (`ended_at` and `outcome` both null) or completed shape (both
present). Before completion,
`trg_db003_workflow_attempts_immutable` permits only end/outcome/reference
completion fields to change. Once `ended_at` is present, every update and
delete is rejected. A retry inserts another index under the same occurrence;
it never replaces attempt zero, creates another run request, or changes the
separate `repair_attempts_used` allowance.

### `run_events`

| Column | Type | Null | Physical meaning |
|---|---|---|---|
| `id` | `UUID` | no | Internal event identity |
| `run_id` / `sequence` | `UUID` / `INTEGER` | no | Owning run and positive authoritative per-run order |
| `event_type` | `VARCHAR(128)` | no | Bounded versioned event type; vocabulary remains additive |
| `from_state` / `to_state` | `VARCHAR(64)` | yes | Exact states, both required for `STATE_TRANSITIONED` |
| `step_id` / `step_kind` / `attempt_index` | UUID / bounded text / integer | yes | Consistent optional step and actual-attempt attribution |
| `actor_type` / `actor_id` | bounded text | no | Exact actor vocabulary and opaque attribution |
| `occurred_at` / `recorded_at` | `TIMESTAMPTZ` | no | Producer-observed and Database-authored times |
| `correlation_id` | `VARCHAR(255)` | yes | Trace-only value, never semantic identity |
| `causation_event_id` | `UUID` FK `run_events.id` | yes | Optional predecessor event |
| `producer_event_id` | `VARCHAR(255)` | no | Producer-scoped idempotency identity |
| `contract_version` / `payload_schema_version` | `VARCHAR(64)` | no | Governing Workflow and payload schema versions |
| `payload` | `JSONB` default `{}` | no | Object-shaped, redacted metadata/opaque references, max 65,536 serialized bytes |
| `producer_event_fingerprint` / `_version` | `VARCHAR(128)` / positive integer | no | Caller-supplied canonical-content fingerprint and its version |
| `failure_code` / `abstention_code` / `cancellation_code` | bounded text | yes | Explicit transition-target-compatible terminal reason |

`UNIQUE (run_id, sequence)` and `UNIQUE (run_id, producer_event_id)` enforce
ordering and producer idempotency. Composite foreign keys prove that a supplied
step belongs to the event run, `step_kind` matches it, and a supplied
`attempt_index` exists under that step. Sequence, not either timestamp, is the
timeline order.

For `STATE_TRANSITIONED`, both states are required and the stored pair must be
one of the exact frozen `CONTRACT-WORKFLOW-001@1.0.0-draft.1` transitions.
Unknown/lowercase states and self/unlisted pairs are rejected. This is
historical-row integrity only, not a Database state machine. Failure targets
use the same anchored uppercase additive family patterns as `runs`; abstention
and cancellation targets use their exact closed vocabularies. All terminal
reason columns must be null for other targets and non-transition events.

`trg_db003_run_events_append_only` rejects every update and delete, including
direct SQL and ORM mutation. Payload checks require a JSON object and cap its
serialized text at 65,536 bytes. Fixtures use empty/redacted metadata only; raw
prompts, repository/patch/log/artefact/Evidence bytes, tokens, and secrets have
no physical column.

### Database persistence primitives

`app/db/workflow_persistence.py::append_run_event` receives an existing
`Session` and a transient `RunEvent`. It locks the target `runs` row, resolves
`(run_id, producer_event_id)`, returns the existing row only when fingerprint
version and fingerprint match, raises `ProducerEventConflictError` on a
conflict, allocates `max(sequence) + 1` while holding the per-run lock, then
adds and flushes. It never commits.

`compare_and_swap_run` updates only an explicit current-projection allowlist
when both expected state and version match. A success sets `updated_at` and
increments `runs.version` exactly once; a miss raises
`RunProjectionConflictError`. It never validates semantic transition intent
and never commits. A caller can therefore perform CAS plus event append in one
SQLAlchemy transaction; an invalid event rollback restores both projection and
event state.

`trg_db003_runs_terminal_immutable` protects only the frozen terminal facts on
an already-terminal run: state, terminal timestamp, all three terminal reason
columns, terminal actor type, and terminal actor ID. It does not select a
transition or protect unrelated future-domain fields.

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
| `ix_workflow_steps_run_id` | `workflow_steps` | Step timeline/scoping for one run | Medium | Non-unique | Includes every semantic occurrence |
| `uq_workflow_steps_run_id_kind_occurrence` | `workflow_steps` | Logical occurrence identity | Unique | Unique | Retries reuse the occurrence |
| `uq_workflow_steps_run_id_id_kind` | `workflow_steps` | Composite event-attribution FK target | Unique | Unique | Proves run/step/kind consistency |
| `ix_workflow_step_attempts_step_id` | `workflow_step_attempts` | Ordered attempt history under a step | Medium | Non-unique | Includes active and completed attempts |
| `uq_workflow_step_attempts_step_id_attempt_index` | `workflow_step_attempts` | Retry/attempt identity | Unique | Unique | Prior attempts remain stored |
| `ix_run_events_run_id` | `run_events` | Complete per-run timeline scan | Medium | Non-unique | Sequence remains authoritative order |
| `uq_run_events_run_id_sequence` | `run_events` | Per-run authoritative ordering | Unique | Unique | Append-only history |
| `uq_run_events_run_id_producer_event_id` | `run_events` | Producer-event idempotency | Unique | Unique | Conflicting reuse fails closed |

Primary-key indexes are implied and not listed. No speculative index for DB-003
or later work was added: there is no state worklist index, timestamp-ordering
index, or partial index over non-terminal runs, because no query owner has
contracted those paths.

## Lifecycle, deletion, and historical attribution

- Suspension, revocation, expiration, inaccessibility, deletion, and
  deprovisioning are all status plus timestamp changes. No row is deleted.
- Foreign keys use the default restrictive action, so a user, installation, or
  repository referenced by history cannot be removed by a cascade.
- A `DEPROVISIONED` user, a `SUSPENDED` installation, and an `INACCESSIBLE`
  repository all remain fully joinable from their historical grants.
- Terminal run projections store their state, `terminal_at`, terminal code, and
  terminal attribution. DB-003 rejects rewrites of those facts after the run is
  terminal and stores immutable attributable transition history.
- Retention durations remain unfrozen pending `CONTRACT-SEC-001` and
  `CONTRACT-DEPLOY-001` (`DB-ISSUE-004`).

## Prohibited secret storage

No table stores a password, password hash, OAuth authorization code, OAuth
access or refresh token, GitHub App private key or JWT, installation access
token, webhook secret, JWT signing secret, provider API key, browser session
token, or raw `Authorization` header. No table stores a raw prompt, repository
bytes, patch bytes, execution log, Evidence bytes, or artefact bytes.

`tests/database/test_schema.py` asserts this twice — once over the ORM metadata
and once over the reflected PostgreSQL columns — using a name pattern covering
`password`, `secret`, `token`, `private_key`, `api_key`, `credential`,
`authorization_header`, `session_key`, `signing_key`, and `jwt`.

## DB-002, DB-003, and later-task boundary

DB-002 owns: `users`, `auth_subjects`, `github_installations`, `repositories`,
`repository_access`, `run_requests`, `runs`.

DB-003 owns and now implements only `workflow_steps`,
`workflow_step_attempts`, and `run_events`, including event ordering,
producer-event idempotency, transition-history integrity, append-only
enforcement, attempt immutability, terminal-fact protection, and run CAS.

DB-004 and later remain absent: checkpoint records, context selections,
candidate patches and versions, patch contents, execution evidence, artefact
metadata, publications, human decisions, benchmark/evaluation results, audit
and security events, model/cost telemetry, and notifications.

Also permanently out of scope for the MVP: generic organizations, tenants, roles,
permissions, billing tables, API-key tables, embedding tables, and pgvector.

DB-003 implements the physical expected-state/version compare/update and atomic
projection/event transaction boundary without choosing transitions. It does
not implement Workflow scheduling/orchestration, retry or repair decisions,
Queue transport, regeneration decisions, Evidence semantics, or any DB-004+
domain. `test_no_db_004_or_queue_table_exists` asserts the migrated database
contains exactly the ten current tables plus `alembic_version`.

## Deferred owner-controlled fields

| Deferred item | Owner | Why it is absent |
|---|---|---|
| Repository owner/name display strings | Auth / API | Mutable display metadata that must not authorize access; no contracted query needs them yet |
| User email, username, display name | Auth | Explicitly not identity keys; no contract requires storage |
| Queue message/delivery/claim/lease/ack/provider fields | Queue | Provider-neutral `CONTRACT-QUEUE-001@1.0.0-draft.2` is consumed only for identity separation; Queue runtime/storage is not DB-003 |
| Evidence, artefact, and checksum fields | Evidence | Provisional until `CONTRACT-EVIDENCE-001` (`DB-DEP-005`) |
| Security-event and redaction fields | Security | Provisional until `CONTRACT-SEC-001` (`DB-DEP-008`) |
| Evaluation and metric fields | Evaluation | Provisional until `CONTRACT-EVAL-001` (`DB-DEP-007`) |
| API pagination, filter, and sort projections | Backend | Provisional until `CONTRACT-API-001` (`DB-DEP-002`); no speculative index added |
| Concrete terminal-actor identity shape | Auth / Workflow | Contract still marks terminal human attribution provisional; stored as bounded opaque text |

## Migration

Revision `ad3f80907336`, message `create DB-002 core entities`, down revision
`None`. It creates only DB-002 tables, constraints, and indexes; it contains no
seed data, no secret, and no DB-003 table.

Revision `e7b4c2d9a631`, message `create DB-003 workflow persistence`, has down
revision `ad3f80907336` and is the sole head. It creates only the three DB-003
tables plus their authorized indexes, constraints, functions, and triggers.
Downgrading to `ad3f80907336` removes every DB-003 object while preserving all
seven DB-002 tables and their rows. Re-upgrade recreates DB-003. Downgrading
from DB-002 to base continues to remove DB-002 through its unchanged historical
revision.

Run every command from the repository root with the explicit configuration:

```text
uv run --project apps/api alembic -c apps/api/alembic.ini heads
uv run --project apps/api alembic -c apps/api/alembic.ini history --verbose
uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
uv run --project apps/api alembic -c apps/api/alembic.ini downgrade ad3f80907336
uv run --project apps/api alembic -c apps/api/alembic.ini downgrade base
```

`alembic/env.py` resolves its URL from `MIGRATION_DATABASE_URL`, falling back to
`DATABASE_URL` only when `TESTGAP_RUNTIME` is exactly `local`. There is exactly
one head and two revisions in one linear chain.

## Tests

| File | Covers |
|---|---|
| `tests/database/test_alembic.py` | Exactly one head, the two-revision linear chain, unchanged DB-002 base, DB-003-only second revision, complete downgrade coverage |
| `tests/database/test_migration_cycle.py` | Fresh upgrade, populated DB-002 to DB-003 upgrade, DB-003 to DB-002 downgrade with rows preserved, re-upgrade, and full base round trip |
| `tests/database/test_schema.py` | DB-002 subset plus exact DB-003 additions, DB-004+/Queue absence, UUID keys, timezone-aware timestamps, foreign keys, named checks, and secret-column absence |
| `tests/database/test_auth_constraints.py` | The accepted two-user / two-installation / two-repository fixture, exact-tuple scoping, duplicate subject rejection, case-distinct identities, byte-exact storage, duplicate external ID rejection, revoked-versus-expired distinction, historical attribution, active-grant uniqueness, re-grant after revocation and after expiry |
| `tests/database/test_workflow_constraints.py` | All twenty canonical states accepted, unknown and lowercase states rejected, repair bounds, non-negative version and retry counters, idempotency uniqueness and versioning, kind field shape, UUID versus external identity separation, terminal timestamp/attribution rules, failure/abstention/cancellation code rules, regeneration lineage |
| `tests/database/test_workflow_persistence.py` | Step/attempt constraints and immutability, retries, event ordering/idempotency/attribution/transition and failure history, append-only triggers, CAS, atomic commit/rollback, terminal immutability, payload bound, Queue separation, and DB-004 exclusion |

Schema tests use `TEST_DATABASE_URL` for DML and the migration role pointed at
the same isolated test database for DDL, matching `CONTRACT-DEPLOY-001`. They
skip when those variables are absent. Stored transition-history integrity and
physical transaction behavior are tested; transition selection and Workflow
orchestration are not implemented.
