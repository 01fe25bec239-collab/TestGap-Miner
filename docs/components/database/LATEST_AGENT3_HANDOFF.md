# Latest A3-DATABASE Handoff

## DB-002-PREREQUISITE-RECONCILIATION-001-C1 durable-record correction result

- Date: 2026-08-02
- Task: `DB-002-PREREQUISITE-RECONCILIATION-001-C1`
- Parent task: `DB-002-PREREQUISITE-RECONCILIATION-001-CLOSEOUT`
- Parent validation result: `CHANGE_REQUIRED`
- Prompt type: `DOCUMENTATION_CORRECTION_ONLY`
- Correction scope: Database durable records only; documentation only
- Result classification: `PASS`
- Branch: `agent2/database`
- Verified repository baseline:
  `1511f474ee301651b631c8adfe406aeb775327aa`
- `DB-002`: `PASS / VERIFIED_COMPLETE / MERGED`; `DB-002-C1`: `PASS`;
  `DB-002-C2`: `PASS`; `DB-002-MERGE-001`: `PASS`
- DB-002 implementation evidence: pull request #12; implementation commit
  `5506ab59211fbaba79f77d4fb5899a587c0e0236`; implementation merge commit
  `3701520e6d61e2bb80391e7af888d0d530bdb6c4`
- DB-002 durable-record reconciliation evidence: documentation pull request
  #13 (`docs(database): close merged DB-002`); head commit
  `861781b1c91cc5eed870653bc35b2d39fc9c1021`; reconciliation merge commit
  `1511f474ee301651b631c8adfe406aeb775327aa`
- Alembic head: `ad3f80907336`; exactly one head
- `CONTRACT-AUTH-001@1.0.0-draft.2`: `ACKNOWLEDGED_AND_MERGED`;
  `DB-DEP-001`: `ACCEPTED`
- `CONTRACT-WORKFLOW-001@1.0.0-draft.1`: `ACKNOWLEDGED_AND_MERGED`;
  `DB-DEP-004`: `ACCEPTED`
- `DB-DEP-011`: `ACCEPTED / VERIFIED_COMPLETE / CLOSED`
- `DB-003`: `NOT_STARTED` / `NOT_AUTHORIZED`; not begun and not assessed for
  readiness by this correction

### Six Database records corrected

1. `docs/components/database/COMPONENT_STATUS.md`
2. `docs/components/database/TASK_LEDGER.md`
3. `docs/components/database/DEPENDENCY_REQUESTS.md`
4. `docs/components/database/DECISION_LOG.md`
5. `docs/components/database/OPEN_ISSUES.md`
6. `docs/components/database/LATEST_AGENT3_HANDOFF.md` (this file)

The correction distinguishes PR #12 implementation evidence from PR #13
documentation-closeout evidence and records the verified repository baseline.
No code, ORM model, Alembic revision, migration, test, schema implementation,
manifest, lockfile, application-code, or upstream-owned file was changed.
DB-003 remains `NOT_STARTED` / `NOT_AUTHORIZED`.

### Recommended next action

A2-DATABASE performs a separate DB-003 readiness assessment. This correction
did not begin or authorize DB-003.

## Historical DB-002-MERGE-001 post-merge reconciliation result

- Date: 2026-08-02
- Task: `DB-002-MERGE-001`; parent task `DB-002`
- Prompt type: `POST_MERGE_TASK_RECONCILIATION`
- Scope: `DOCUMENTATION_ONLY`
- Result classification: `PASS`
- Branch: `agent2/database`; synchronized commit at that time
  `3701520e6d61e2bb80391e7af888d0d530bdb6c4`
- `DB-002`: `PASS / VERIFIED_COMPLETE / MERGED`
- `DB-002-C1`: `PASS`; `DB-002-C2`: `PASS`; `DB-002-MERGE-001`: `PASS`
- Pull request: #12 — `feat(database): implement DB-002 core persistence`
- Implementation commit: `5506ab59211fbaba79f77d4fb5899a587c0e0236`
- Implementation merge commit: `3701520e6d61e2bb80391e7af888d0d530bdb6c4`
- Alembic head: `ad3f80907336`; exactly one head
- A2-DATABASE final decision: `PASS`
- `DB-DEP-011`: `ACCEPTED / VERIFIED_COMPLETE / CLOSED`
- `DB-003`: `NOT_STARTED` / `NOT_AUTHORIZED`; not begun, not authorized, and not
  assessed for readiness by this task

### Merged DB-002 validation evidence

| Check | Result |
|---|---|
| DB-002 tables | Seven |
| Constraints | 55 |
| Indexes | 21 |
| Alembic heads | Exactly one — `ad3f80907336` |
| PostgreSQL 16.14 migration cycle | `PASS` |
| Database tests | 169 passed |
| Backend tests | 5 passed |
| Full suite | 174 passed |
| Failures / skips | Zero / zero |
| DB-003 implementation | Absent |

### Files modified by DB-002-MERGE-001

1. `docs/components/database/COMPONENT_STATUS.md`
2. `docs/components/database/TASK_LEDGER.md`
3. `docs/components/database/OPEN_ISSUES.md`
4. `docs/components/database/DECISION_LOG.md`
5. `docs/components/database/DEPENDENCY_REQUESTS.md`
6. `docs/components/database/LATEST_AGENT3_HANDOFF.md` (this file)

No ORM model, Alembic revision, migration, test, schema file, manifest,
lockfile, application-code file, or Auth-, Workflow-, Integration-, or
Deployment-owned file was changed. No commit, push, or pull request was made.

### Preserved records

- `DB-DEP-011`: `CLOSED`.
- `CONTRACT-AUTH-001@1.0.0-draft.2` and `CONTRACT-WORKFLOW-001@1.0.0-draft.1`
  acceptance is unchanged.
- The seven-table DB-002 boundary is unchanged.
- The runtime-enforcement limitations are unchanged: transition execution,
  expected-state-and-version compare/update, atomic projection/event mutation,
  append-only transition history, terminal-state update rejection after commit,
  regeneration decision-event persistence, and Workflow orchestration remain
  `NOT_IMPLEMENTED` / `NOT_TESTED`.
- `DB-ISSUE-013` and `DB-ISSUE-014` remain open, deferred, and nonblocking.
- All later-task blockers are unchanged: `DB-004` through `DB-008` remain
  `BLOCKED`, and `DB-DEP-002`, `DB-DEP-003`, and `DB-DEP-005` through
  `DB-DEP-010` remain `PENDING`.

### Recommended next action

A2-DATABASE reviews and merges this reconciliation, followed by a separate
DB-003 readiness assessment. DB-003 was not begun.

## Historical DB-002-C2 documentation correction result

- DB-002-C2: `PASS`
- DB-002 status at that time: `PASS_PENDING_A2_FINAL_REVIEW`; superseded by
  `PASS / VERIFIED_COMPLETE / MERGED` above
- Code/schema changes: none
- DB-DEP-011: `ACCEPTED / VERIFIED_COMPLETE / CLOSED`
- DB-003: `NOT_STARTED`

## Historical DB-002-C1 corrective result

1. Result classification: `PASS`.
2. Task: `DB-002-C1`; scope: `DB-002_CORRECTION_ONLY`.
3. DB-002 status at that time: `PASS_PENDING_A2_FINAL_REVIEW`; superseded by
   `PASS / VERIFIED_COMPLETE / MERGED` above.
4. Baseline: `8884b5d540351c735b6cddc01314a7dd9e25af05` on
   `agent2/database`.
5. No commit, push, pull request, second migration, or DB-003 work occurred.

### Failure-code constraint before and after

Before, each failed-state branch checked only a non-null value and
`left(failure_code, prefix_length) = 'FAMILY_'`, with `failure_code IS NULL` in
the `ELSE` branch.

```sql
CASE state
WHEN 'FAILED_INPUT' THEN failure_code IS NOT NULL AND left(failure_code, 6) = 'INPUT_'
WHEN 'FAILED_MODEL' THEN failure_code IS NOT NULL AND left(failure_code, 6) = 'MODEL_'
WHEN 'FAILED_EXECUTION' THEN failure_code IS NOT NULL AND left(failure_code, 10) = 'EXECUTION_'
WHEN 'FAILED_INFRASTRUCTURE' THEN failure_code IS NOT NULL AND left(failure_code, 15) = 'INFRASTRUCTURE_'
WHEN 'FAILED_SECURITY' THEN failure_code IS NOT NULL AND left(failure_code, 9) = 'SECURITY_'
ELSE failure_code IS NULL END
```

After, each branch uses the matching anchored PostgreSQL regular expression,
and the non-failure `ELSE` remains null-only.

```sql
CASE state
WHEN 'FAILED_INPUT' THEN failure_code IS NOT NULL AND failure_code ~ '^INPUT_[A-Z0-9]+(_[A-Z0-9]+)*$'
WHEN 'FAILED_MODEL' THEN failure_code IS NOT NULL AND failure_code ~ '^MODEL_[A-Z0-9]+(_[A-Z0-9]+)*$'
WHEN 'FAILED_EXECUTION' THEN failure_code IS NOT NULL AND failure_code ~ '^EXECUTION_[A-Z0-9]+(_[A-Z0-9]+)*$'
WHEN 'FAILED_INFRASTRUCTURE' THEN failure_code IS NOT NULL AND failure_code ~ '^INFRASTRUCTURE_[A-Z0-9]+(_[A-Z0-9]+)*$'
WHEN 'FAILED_SECURITY' THEN failure_code IS NOT NULL AND failure_code ~ '^SECURITY_[A-Z0-9]+(_[A-Z0-9]+)*$'
ELSE failure_code IS NULL END
```

### Exact new PostgreSQL tests

- `test_unknown_uppercase_additive_failure_code_is_accepted` covers:
  `INPUT_NEW_REASON`, `MODEL_ADDITIONAL_FAILURE`,
  `EXECUTION_NEW_RUNNER_REASON`, `INFRASTRUCTURE_NEW_CAPACITY_REASON`, and
  `SECURITY_NEW_POLICY_REASON` in their matching failed states.
- `test_malformed_same_family_failure_code_is_rejected` covers: `INPUT_`,
  `INPUT_lowercase`, `INPUT_BAD-VALUE`, `INPUT BAD VALUE`, `INPUT__DOUBLE`,
  ` INPUT_BAD_VALUE`, and `INPUT_BAD_VALUE `.
- Preserved PostgreSQL tests cover every published contract code, a valid code
  in another failed family, and a failure code on a non-failure state.

All tests use the migrated PostgreSQL `session` fixture and execute real inserts
and constraint checks; no constant-only test is counted as enforcement evidence.

### Migration and PostgreSQL evidence

- Revision: `ad3f80907336` (`create DB-002 core entities`).
- Down revision: `None`.
- Head count: exactly one; `ad3f80907336 (head)`.
- Revision-file count: exactly one; no second revision was created.
- Isolated `testgap_test` cycle: `upgrade head` → `PASS`; `downgrade base` →
  `PASS`; second `upgrade head` → `PASS`; final current revision
  `ad3f80907336 (head)`.
- PostgreSQL exact version: `PostgreSQL 16.14 on
  aarch64-unknown-linux-musl, compiled by gcc (Alpine 15.2.0) 15.2.0, 64-bit`;
  server version `16.14`, major version 16.
- The migrated schema remains exactly the seven DB-002 tables plus
  `alembic_version`; DB-003/later tables remain absent.

### Validation results

| Check | Result |
|---|---|
| `uv sync --project apps/api --all-groups --locked` | `PASS`; no dependency file changed |
| Database suite | `169 passed`, 0 failed, 0 skipped |
| Backend suite | `5 passed`, 0 failed |
| Full suite | `174 passed`, 0 failed, 0 skipped |
| `git diff --check` | `PASS`; exit 0, no output |
| Alembic heads | `PASS`; one head and one revision |
| Secret-bearing field review | `PASS`; none added |
| Scope review | `PASS`; no forbidden path changed by DB-002-C1 |

### Durable-record corrections

- `COMPONENT_STATUS.md`: DB-002-C1 status and counts are current; the historical
  DB-001 schema map labels all seven DB-002 rows `IMPLEMENTED`; runtime storage
  enforcement is separated from unimplemented transition execution.
- `OPEN_ISSUES.md`: stale blocked/not-started statements are historical;
  DB-ISSUE-011 is `CLOSED / ACCEPTED_DATABASE_PHYSICAL_DECISION`; DB-ISSUE-012
  is `CLOSED / ACCEPTED_WITH_PATTERN_ENFORCEMENT`; DB-ISSUE-013 is
  `OPEN_NON_BLOCKING / DEFERRED_CONTRACT_SHAPE`; DB-ISSUE-014 remains open and
  nonblocking.
- `TASK_LEDGER.md`: Workflow reconciliation is closed through PR #10 and merge
  commit `99c8022c9f44e6a54bed624aa0153be7e32f234b`; DB-002-C1 is `PASS`; DB-008
  now states that DB-002 exists while DB-003 through DB-007 remain incomplete.
- `DECISION_LOG.md`: DB-DEC-011/012 absence statements are historical;
  DB-DEC-014 records the regex-family design and the exact runtime boundary.
- `DEPENDENCY_REQUESTS.md`: accepted DB-002 dependencies are no longer described
  as current blockers, and transition/runtime enforcement remains deferred.
- `database-schema.md`: documents the five anchored patterns, accepted
  one-run-per-request decision, and storage-versus-runtime enforcement boundary.

### Accepted dispositions

- `DB-ISSUE-011`: `CLOSED / ACCEPTED_DATABASE_PHYSICAL_DECISION`.
  `runs.run_request_id UNIQUE` remains; changing cardinality later requires
  Workflow consumer and Database migration review.
- `DB-ISSUE-012`: `CLOSED / ACCEPTED_WITH_PATTERN_ENFORCEMENT`. Unknown additive
  uppercase family-compatible codes remain representable; terminal state is the
  compatibility boundary; malformed values are rejected.
- `DB-ISSUE-013`: `OPEN_NON_BLOCKING / DEFERRED_CONTRACT_SHAPE`. Bounded opaque
  `terminal_actor_id` and the actor-type constraint are accepted for DB-002; no
  foreign key is frozen; a future typed relation is additive.
- `DB-ISSUE-014`: remains open and nonblocking; no repository owner/name display
  fields were added.

### Runtime-enforcement truthfulness

- `IMPLEMENTED` / `TESTED`: allowed stored states; terminal/non-terminal row
  shape; counter bounds; failure/abstention/cancellation code consistency;
  version storage; terminal-attribution storage.
- `NOT_IMPLEMENTED` / `NOT_TESTED`: allowed-transition execution;
  expected-state-and-version compare/update; atomic projection/event mutation;
  append-only transition history; terminal-state update rejection after commit;
  regeneration decision-event persistence; Workflow orchestration.
- No orchestration trigger was added, and terminal immutability is not claimed as
  DB-002 database enforcement.

### Exact DB-002-C1 files modified

1. `apps/api/app/db/models/workflow.py`
2. `apps/api/alembic/versions/ad3f80907336_create_db_002_core_entities.py`
3. `tests/database/test_workflow_constraints.py`
4. `docs/data/database-schema.md`
5. `docs/components/database/COMPONENT_STATUS.md`
6. `docs/components/database/OPEN_ISSUES.md`
7. `docs/components/database/TASK_LEDGER.md`
8. `docs/components/database/DECISION_LOG.md`
9. `docs/components/database/DEPENDENCY_REQUESTS.md`
10. `docs/components/database/LATEST_AGENT3_HANDOFF.md`

### Historical DB-002-C1 disposition

`DB-002-C1`: `PASS`. `DB-002` at that time: `PASS_PENDING_A2_FINAL_REVIEW`, with
the recommended next action being A2-DATABASE final review. That review has since
completed with decision `PASS` and DB-002 merged in PR #12; the current DB-002
status is `PASS / VERIFIED_COMPLETE / MERGED`. DB-003 required separate
authorization and was not begun, and it remains `NOT_STARTED` /
`NOT_AUTHORIZED`.

## Retained original DB-002 implementation evidence

The remainder preserves the original seven-table DB-002 implementation handoff
as historical evidence. Its original pre-C1 test counts and initial-worktree
statements are not the current DB-002-C1 result above.

## Original result

- Result classification: `PASS`.
- Task: `DB-002 — Core identity, repository-context, run-request, and run
  persistence`.
- Prompt type: `IMPLEMENTATION`.
- Scope: `IMPLEMENTATION` of the seven DB-002 entities only.
- Agent 2: `A2-DATABASE`.
- Paired Agent 3: `A3-DATABASE — Database Coding Agent`.
- Date: 2026-08-01.
- DB-003 was not started.

## Repository evidence

- Root: `/Users/omkar/Documents/TestGap Miner_App`.
- Branch: `agent2/database`.
- Remote: `https://github.com/01fe25bec239-collab/TestGap-Miner.git`.
- Starting commit / `origin/main` / `origin/agent2/database`:
  `8884b5d540351c735b6cddc01314a7dd9e25af05` (all equal).
- Divergence from `origin/main`: `0 0`.
- Starting worktree: clean, no untracked files, empty stash.
- Final commit: none. No commit, push, or pull request was made, as instructed.

## Contracts applied

- `CONTRACT-AUTH-001@1.0.0-draft.2` — `ACKNOWLEDGED_AND_MERGED`; `DB-DEP-001`
  `ACCEPTED`.
- `CONTRACT-WORKFLOW-001@1.0.0-draft.1` — `ACKNOWLEDGED_AND_MERGED`;
  `DB-DEP-004` `ACCEPTED`.
- `DB-DEP-011` — `ACCEPTED / VERIFIED_COMPLETE / CLOSED`.

Neither contract was altered, normalized, extended, or reinterpreted.

## Files created

1. `apps/api/app/db/base.py`
2. `apps/api/app/db/models/__init__.py`
3. `apps/api/app/db/models/auth.py`
4. `apps/api/app/db/models/workflow.py`
5. `apps/api/alembic/versions/ad3f80907336_create_db_002_core_entities.py`
6. `tests/database/conftest.py`
7. `tests/database/support.py`
8. `tests/database/test_schema.py`
9. `tests/database/test_migration_cycle.py`
10. `tests/database/test_auth_constraints.py`
11. `tests/database/test_workflow_constraints.py`
12. `docs/data/database-schema.md`

## Files modified

1. `apps/api/app/db/metadata.py` — added the constraint and index naming
   convention to the single existing `MetaData`.
2. `apps/api/alembic/env.py` — imports `app.db.models` so `target_metadata`
   contains every DB-002 table.
3. `tests/database/test_alembic.py` — asserts one head, one revision, the
   correct message, no forbidden table or seed data, and complete downgrade
   coverage.
4. `tests/database/test_scaffold.py` — the pre-existing
   `test_import_does_not_create_an_engine` probe left a mocked
   `app.db.engine` in `sys.modules`; it now reimports the real module in a
   `finally` block. Without this, any later real connection in the same session
   failed with `'Mock' object does not support the context manager protocol`.
5. `docs/data/database-scaffold.md` — points at the DB-002 schema document and
   corrects the stale "zero heads, empty metadata" statements.
6. `docs/components/database/COMPONENT_STATUS.md`
7. `docs/components/database/TASK_LEDGER.md`
8. `docs/components/database/OPEN_ISSUES.md`
9. `docs/components/database/DECISION_LOG.md`
10. `docs/components/database/DEPENDENCY_REQUESTS.md`
11. `docs/components/database/LATEST_AGENT3_HANDOFF.md` (this file)

No file was deleted. A local gitignored `.env` was created to run the approved
Compose service; it is untracked, excluded by `.gitignore`, and is not a
repository change.

## Models and tables

| Model | Table | Domain |
|---|---|---|
| `User` | `users` | Canonical users |
| `AuthSubject` | `auth_subjects` | External authentication subjects |
| `GitHubInstallation` | `github_installations` | GitHub App installations |
| `Repository` | `repositories` | GitHub repositories |
| `RepositoryAccess` | `repository_access` | Repository-access grants |
| `RunRequest` | `run_requests` | Run requests |
| `Run` | `runs` | Current run projection |

One `MetaData`, one `DeclarativeBase`, synchronous SQLAlchemy 2.x on psycopg 3,
UUID primary keys, timezone-aware timestamps, explicit nullability, explicit
foreign keys, and explicit relationships throughout.

## Constraints and indexes

55 constraints and 21 indexes. Complete list and rationale in
`docs/data/database-schema.md`.

Check constraints: `ck_users_status_allowed`,
`ck_users_suspended_at_present`, `ck_users_deprovisioned_at_present`,
`ck_auth_subjects_status_allowed`, `ck_auth_subjects_revoked_at_present`,
`ck_github_installations_status_allowed`,
`ck_github_installations_account_type_allowed`,
`ck_github_installations_github_ids_positive`,
`ck_github_installations_suspended_at_present`,
`ck_github_installations_deleted_at_present`,
`ck_repositories_status_allowed`, `ck_repositories_github_id_positive`,
`ck_repository_access_status_allowed`,
`ck_repository_access_authorization_source_allowed`,
`ck_repository_access_active_not_terminated`,
`ck_repository_access_revoked_at_present`,
`ck_repository_access_expiry_distinct_from_revocation`,
`ck_run_requests_request_kind_allowed`,
`ck_run_requests_kind_field_shape`,
`ck_run_requests_idempotency_key_version_positive`,
`ck_run_requests_github_repository_id_positive`,
`ck_runs_state_allowed`, `ck_runs_repair_attempts_used_range`,
`ck_runs_retry_limit_non_negative`, `ck_runs_retry_attempts_used_range`,
`ck_runs_step_attempts_used_non_negative`, `ck_runs_version_non_negative`,
`ck_runs_terminal_at_matches_state`, `ck_runs_failure_code_matches_state`,
`ck_runs_abstention_code_matches_state`,
`ck_runs_cancellation_code_matches_state`,
`ck_runs_terminal_actor_matches_state`,
`ck_runs_terminal_actor_type_allowed`, `ck_runs_parent_run_id_not_self`.

Unique: `uq_auth_subjects_issuer_subject`,
`uq_github_installations_github_installation_id`,
`uq_repositories_github_repository_id`,
`uq_run_requests_idempotency_key_version_idempotency_key`,
`uq_runs_run_request_id`, plus the partial unique index
`uq_repository_access_active` over
`(user_id, installation_id, repository_id) WHERE status = 'ACTIVE'`.

Foreign keys: `fk_auth_subjects_user_id_users`,
`fk_repository_access_user_id_users`,
`fk_repository_access_installation_id_github_installations`,
`fk_repository_access_repository_id_repositories`,
`fk_run_requests_repository_id_repositories`,
`fk_run_requests_requested_by_subject_auth_subjects`,
`fk_runs_run_request_id_run_requests`, `fk_runs_parent_run_id_runs`.

Non-unique indexes: `ix_auth_subjects_user_id`,
`ix_repository_access_user_id`, `ix_repository_access_installation_id`,
`ix_repository_access_repository_id`, `ix_run_requests_repository_id`,
`ix_run_requests_requested_by_subject`, `ix_runs_parent_run_id`. Each is a
foreign-key reverse-lookup path PostgreSQL does not index automatically. No
speculative index for a later task was added.

## Auth-contract mapping

Every `users`, `auth_subjects`, `github_installations`, `repositories`, and
`repository_access` column maps to a named `CONTRACT-AUTH-001@1.0.0-draft.2`
field; the per-column table is in `docs/data/database-schema.md`.

Preserved exactly: UUID internal identifiers separate from immutable external
identifiers; case-sensitive exact issuer and subject storage with unique
`(issuer, subject)` and no Database normalization, no `citext`, and no
case-folding functional index; unique GitHub installation and repository numeric
IDs; the exact user + installation + repository access tuple; all lifecycle
statuses and timestamps; distinct `expires_at`, `expired_at`, and `revoked_at`
meanings with expiry able to occur before delayed status reconciliation;
historical attribution after suspension, revocation, expiration, deletion, and
deprovisioning; and distinct human and machine actor meanings.

Not stored: passwords, password hashes, OAuth codes, access tokens, refresh
tokens, GitHub private keys, installation tokens, webhook secrets, API secrets,
browser session tokens, and raw Authorization headers.

## Workflow-contract mapping

Every `run_requests` and `runs` column maps to a named
`CONTRACT-WORKFLOW-001@1.0.0-draft.1` projection field.

Preserved exactly: the twenty canonical `RunState` values as uppercase text with
no order inferred from declaration order; internal UUIDs separate from external
identifiers; versioned idempotency composition with a persisted key version, a
bounded digest, and a request fingerprint for conflict detection;
`repair_attempts_used` constrained to `0..1`; a non-negative optimistic
concurrency `version`; terminal-state meaning with required terminal timestamp
and attribution; the cancellation and human-review code boundaries; one
automated repair maximum; and retry and repair as separate concepts.

Not stored: raw prompts, repository bytes, patch bytes, execution logs, and
secrets. No Queue-, Evidence-, Security-, Evaluation-, or API-owned field was
added.

Three Database-owned decisions are recorded for owner confirmation:
`DB-ISSUE-011` (unique `runs.run_request_id`), `DB-ISSUE-012` (failure codes
checked by contract family prefix so an additive code stays storable), and
`DB-ISSUE-013` (terminal actor identity as bounded opaque text while the Auth
shape is provisional).

## Alembic

- Revision ID: `ad3f80907336`.
- Message: `create DB-002 core entities`.
- Down revision: `None`.
- Heads: exactly one — `ad3f80907336 (head)`.
- Revision files: one.
- Contents: DB-002 tables, constraints, and indexes only; no seed data, no
  secret, no DB-003 or later table; complete `downgrade()`.
- Every command used `-c apps/api/alembic.ini`.

## Migration cycle on the isolated test database

| Step | Result |
|---|---|
| Baseline `testgap_test` | Empty; only `alembic_version` |
| `upgrade head` | Seven DB-002 tables, 55 constraints, 21 indexes; `current` = `ad3f80907336 (head)` |
| Schema inspection | Every expected constraint and index present, including the partial `uq_repository_access_active` with predicate `WHERE (status = 'ACTIVE'::text)` |
| `downgrade base` | Zero DB-002 tables; only `alembic_version` remains; `current` empty |
| `upgrade head` again | Seven tables, 55 constraints, 21 indexes restored identically |

The runtime `testgap` database was never migrated by this task and still holds
only an empty `alembic_version`. The test database was left at base.

## PostgreSQL

- Image `postgres:16.14-alpine3.24`, service `postgres`, healthy.
- `show server_version;` → `16.14`. Major version 16 as required.
- `pg_isready -U postgres -d testgap` → accepting connections.
- Docker `29.6.2`, Docker Compose `5.3.1`.
- Port 5432 was occupied locally, so the tracked `POSTGRES_HOST_PORT` override
  used loopback port 55432.
- The retained `testgap-miner_postgres-data` volume predated this task, so the
  Deployment-owned initializer was re-run in place — it is idempotent — to
  reconcile role passwords. No destructive reset was performed and the volume
  was preserved.

## Test results

| Suite | Command | Result |
|---|---|---|
| Database | `pytest -c apps/api/pyproject.toml tests/database -q` | 157 passed, 0 failed, 0 skipped |
| Backend | `pytest -c apps/api/pyproject.toml tests/api -q` | 5 passed |
| Full | `pytest -c apps/api/pyproject.toml tests -q` | 162 passed, 0 failed, 0 skipped |

Coverage includes: one Alembic head; upgrade from an empty PostgreSQL 16
database; downgrade to the zero-revision state; second upgrade; expected DB-002
tables present; forbidden DB-003 and later tables absent; the accepted
two-user / two-installation / two-repository fixture; permitted access through
the exact tuple; cross-repository, cross-installation, and cross-user
substitution finding no grant; duplicate exact issuer + subject rejection;
case-distinct issuer and subject remaining separate identities; byte-exact
storage with no normalization; duplicate GitHub installation and repository ID
rejection; revoked distinguishable from expired; historical inactive grants
still attributable; active-grant uniqueness; re-grant after both revocation and
expiry; no secret column; all twenty canonical `RunState` values accepted;
unknown and lowercase states rejected; `repair_attempts_used` limited to 0 or 1;
negative versions and retry counters rejected; duplicate conflicting request
idempotency rejected; internal UUID and external identity separation; and the
existence of `run_requests` and `runs` with DB-003 steps, attempts, and events
absent.

No test claims that transition orchestration is exercised, because DB-002
implements no transition service.

## Schema-inspection evidence

Tables in `testgap_test` at head: `alembic_version`, `auth_subjects`,
`github_installations`, `repositories`, `repository_access`, `run_requests`,
`runs`, `users`.

`uq_repository_access_active` reflects as:

```sql
CREATE UNIQUE INDEX uq_repository_access_active
  ON public.repository_access
  USING btree (user_id, installation_id, repository_id)
  WHERE (status = 'ACTIVE'::text)
```

## Forbidden-table absence evidence

`test_no_db_003_or_later_table_exists` asserts the migrated schema minus
`alembic_version` equals exactly the seven DB-002 tables, and that it intersects
an explicit 37-name forbidden list — steps, attempts, events, ordering,
checkpoints, context selections, candidate patches, patch contents, execution
evidence and attempts, artefacts, publications, human decisions, benchmark
cases, evaluation results, audit and security events, model usage,
notifications, organizations, tenants, roles, permissions, role permissions,
user roles, API keys, embeddings, and billing — in the empty set.
`test_the_revision_creates_no_forbidden_table_and_seeds_no_data` asserts the same
against the revision source, together with the absence of `op.bulk_insert` and
`op.execute`.

## Secret-storage review

No domain column matches `password`, `passwd`, `secret`, `token`,
`private_key`, `api_key`, `credential`, `authorization_header`, `session_key`,
`signing_key`, or `jwt`, asserted over both the ORM metadata and the reflected
PostgreSQL columns. A scan of every changed and new file for GitHub tokens, PEM
blocks, Slack tokens, AWS keys, provider keys, and the local Compose passwords
returned no match. `repository_access.authorization_source` is a provenance
label with a single allowed value, `GITHUB_VERIFIED`, not a credential.

## Validation commands

| Command | Result |
|---|---|
| `uv sync --project apps/api --all-groups --locked` | Succeeded; no manifest or lockfile change |
| `docker compose --project-name testgap-miner up -d --wait postgres` | Container healthy |
| `docker compose ... exec -T postgres pg_isready -U postgres -d testgap` | Accepting connections |
| `docker compose ... exec -T postgres psql ... -Atc "show server_version;"` | `16.14` |
| `alembic -c apps/api/alembic.ini heads` | `ad3f80907336 (head)` |
| `alembic -c apps/api/alembic.ini history --verbose` | One revision, parent `<base>` |
| `alembic -c apps/api/alembic.ini upgrade head` / `downgrade base` / `upgrade head` | All succeeded |
| `git diff --check` | Exit 0, no output |
| `docker compose --project-name testgap-miner down` | Stopped; retained volume preserved |

### `git diff --stat`

```text
 apps/api/alembic/env.py                         |   1 +
 apps/api/app/db/metadata.py                     |  11 +-
 docs/components/database/COMPONENT_STATUS.md    | 169 ++++++++++++++++--------
 docs/components/database/DECISION_LOG.md        |  70 +++++++++-
 docs/components/database/DEPENDENCY_REQUESTS.md |  36 ++---
 docs/components/database/OPEN_ISSUES.md         |  99 +++++++++++---
 docs/components/database/TASK_LEDGER.md         |  18 +--
 docs/data/database-scaffold.md                  |  17 ++-
 tests/database/test_alembic.py                  |  37 +++++-
 tests/database/test_scaffold.py                 |  11 +-
 10 files changed, 349 insertions(+), 120 deletions(-)
```

`git diff --stat` covers tracked modifications only; the twelve new files listed
above are untracked and therefore not represented in it.

### Scope check

Every changed and new path lies under `apps/api/app/db/**`,
`apps/api/alembic/**`, `tests/database/**`, `docs/data/**`, or
`docs/components/database/**`. `apps/api/pyproject.toml`, `apps/api/uv.lock`,
`apps/api/app/main.py`, `apps/api/app/settings.py`, `tests/conftest.py`,
`tests/api/**`, `tests/integration/**`, `.env.example`, `compose.yml`,
`Dockerfile`, `docker/**`, `.github/**`, `infra/**`, `scripts/**`, `ops/**`, and
the Auth, Agent-Workflow, Backend, Deployment, and Integration documentation
trees are all unchanged. No dependency was added or changed.

## Remaining non-DB-002 items (still current after merge)

- `DB-ISSUE-011` and `DB-ISSUE-012` are closed by DB-002-C1.
- `DB-ISSUE-013` is explicitly open, deferred, and nonblocking.
- `DB-ISSUE-014` defers repository display metadata to `CONTRACT-API-001`.
- `DB-ISSUE-001` (specification filename lineage), `DB-ISSUE-004` (retention and
  deletion durations), `DB-ISSUE-005` (query and scale assumptions), and
  `DB-ISSUE-008` (production host registry) remain open as before.
- `DB-DEP-002`, `DB-DEP-003`, `DB-DEP-005` through `DB-DEP-010` remain
  `PENDING` and block their own later Database tasks.

## Historical DB-002-C1 recommended next action

A2-DATABASE performing the final DB-002-C1 review was the recommended next
action at that time; it is complete, with decision `PASS` and DB-002 merged in
implementation PR #12 at implementation merge commit
`3701520e6d61e2bb80391e7af888d0d530bdb6c4`. The current recommended
next action is recorded in the DB-002-MERGE-001 section above. DB-003 required
separate explicit authorization, was not begun, and remains `NOT_STARTED` /
`NOT_AUTHORIZED`.

No commit, push, pull request, DB-003 work, or rollback action was performed by
DB-002-C1 or by DB-002-MERGE-001.
