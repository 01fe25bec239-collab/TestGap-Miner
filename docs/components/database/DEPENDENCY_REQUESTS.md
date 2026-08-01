# Database Dependency Requests

- Date prepared: 2026-08-01
- Branch: `agent2/database`
- Baseline: `8884b5d540351c735b6cddc01314a7dd9e25af05`
- DB-001/DB-001-C1: `PASS`, reviewed, and merged
- DB-001-C1: historical completed continuation
- Original DB-DEP011 scaffold attempt: historical `DEPENDENCY_BLOCKED`
- Database scaffold: `IMPLEMENTED`; DB-DEP-011:
  `ACCEPTED / VERIFIED_COMPLETE / CLOSED`
- Migration chain: exactly one head, `ad3f80907336`
- Domain schema: `IMPLEMENTED` for DB-002; DB-002:
  `PASS_PENDING_A2_FINAL_REVIEW`; DB-002-C1: `PASS`
- `CONTRACT-AUTH-001@1.0.0-draft.2`: `ACKNOWLEDGED_AND_MERGED`
- `CONTRACT-WORKFLOW-001@1.0.0-draft.1`:
  `ACKNOWLEDGED_AND_MERGED`; `DB-DEP-004`: `ACCEPTED`

## `DB-DEP-001` — Auth context

- Request ID: `DB-DEP-001`
- Requesting Agent 2: `A2-DATABASE`
- Owning Agent 2: `A2-AUTH`
- Required change and reason: Publish the versioned authenticated-user, external-auth-subject, GitHub-installation context, repository-access semantics, actor types, lifecycle requirements, and whether any local credential field is required. Database must not invent AUTH-owned identity fields.
- Contract affected: `CONTRACT-AUTH-001`
- Historical blocking task: `DB-002`; actor semantics also govern `DB-005` and
  security-event attribution. The Auth dependency is accepted for DB-002.
- Backward-compatibility impact: Initial contract; future incompatible identifier or lifecycle changes would require a migration and consumer coordination.
- Urgency: `HIGH`
- Proposed acceptance test: Given two users, two installations, and two repositories, contract fixtures prove permitted access, denied cross-scope access, stable external-subject uniqueness, and no raw token/private-key storage.
- Approval status: `ACCEPTED`
- Completion evidence:
  - Contract: `CONTRACT-AUTH-001@1.0.0-draft.2`.
  - Path: `docs/components/auth/CONTRACT-AUTH-001.md`.
  - Auth producer: `PASS — A2_AUTH_ACCEPTED`.
  - Database consumer: A2-DATABASE `ACKNOWLEDGED`.
  - Pull request: #7.
  - Producer head commit: `20a6fa12398a29bfed3a28005aa71e2ffe0ba7d48`.
  - Merge commit: `f54f8755c0589db704bd0f94c891da11c42398a6`.
- Accepted semantic boundaries:
  - UUID internal identifiers and separate immutable external identifiers.
  - Exact case-sensitive issuer and opaque subject storage/comparison; unique
    exact issuer + subject; no independent Database normalization.
  - Unique GitHub installation numeric ID and unique GitHub repository numeric
    ID.
  - Exact user + installation + repository access tuple.
  - Distinct meanings for `expires_at`, `expired_at`, and `revoked_at`.
  - Historical attribution after suspension, revocation, expiration, deletion,
    or deprovisioning.
  - Distinct human and machine actors.
  - No local credentials, password hashes, raw tokens, private keys, or other
    secret persistence.
  - No generic organization tenancy, generic RBAC, or billing schema.

## `DB-DEP-002` — API query contract

- Request ID: `DB-DEP-002`
- Requesting Agent 2: `A2-DATABASE`
- Owning Agent 2: `A2-BACKEND`
- Required change and reason: Publish versioned create/read/query shapes for repositories, run requests, runs, publications, human decisions, filtering, sorting, and pagination. These determine safe constraints and critical indexes.
- Contract affected: `CONTRACT-API-001`
- Exact blocking task: `DB-005` and DB-007 index validation. DB-002 added no speculative index and no API-owned pagination, filter, sort, or repository display field; all remain deferred to CONTRACT-API-001 (see `DB-ISSUE-014`).
- Backward-compatibility impact: Initial contract; later filter/sort changes should be additive or explicitly versioned.
- Urgency: `HIGH`
- Proposed acceptance test: OpenAPI fixtures round-trip UUID internal IDs and separate GitHub IDs, reject cross-scope identifiers, and exercise documented run-list/run-detail pagination and filters.
- Approval status: `PENDING`
- Completion evidence: None; no versioned contract or handoff exists.

## `DB-DEP-003` — Repository context contract

- Request ID: `DB-DEP-003`
- Requesting Agent 2: `A2-DATABASE`
- Owning Agent 2: `A2-RAG`
- Required change and reason: Publish repository-manifest, ranked candidate, context-item, context-bundle, version/hash, ranking, and retention metadata. Database will persist provenance references, not generic documents or repository bytes.
- Contract affected: `CONTRACT-RAG-001`
- Exact blocking task: `DB-004`
- Backward-compatibility impact: Initial contract; identifiers and content hashes must remain stable or be versioned to preserve historical evidence.
- Urgency: `MEDIUM`
- Proposed acceptance test: A fixture records a ranked file selection for a repository SHA and reconstructs the exact context manifest without storing full file bytes in PostgreSQL.
- Approval status: `PENDING`
- Completion evidence: None; no versioned contract or handoff exists.

## `DB-DEP-004` — Workflow state contract

- Request ID: `DB-DEP-004`
- Requesting Agent 2: `A2-DATABASE`
- Owning Agent 2: `A2-AGENT-WORKFLOW`
- Required change and reason: Publish canonical run states, workflow-step kinds, ordered event shape, retry/repair counters, failure codes, terminal transitions, attribution, and abstention semantics.
- Contract affected: `CONTRACT-WORKFLOW-001`
- Historical blocking task: `DB-002` run lifecycle. The dependency is accepted
  for DB-002; DB-003 remains separately unstarted.
- Backward-compatibility impact: High; enum removal/rename or event-semantic changes require coordinated migrations. Prefer additive versioning.
- Urgency: `HIGH`
- Proposed acceptance test: Contract fixtures cover the successful path, one bounded repair, abstention, cancellation, invalid transitions, ordered append-only events, and rejection of more than one automated repair.
- Approval status: `ACCEPTED`
- Consumer decision: `ACCEPTED_WITH_NONBREAKING_CLARIFICATIONS`
- Completion evidence:
  - Contract: `CONTRACT-WORKFLOW-001@1.0.0-draft.1`.
  - Path: `docs/components/agent-workflow/CONTRACT-WORKFLOW-001.md`.
  - Semantic commit: `a7c83f422bb51deefd233229c7573fda64b097b6`.
  - Database acknowledgement commit:
    `5eb2e98d5a8189b5a4da3f3f5d0dc0013dca3dc0`.
  - Pull request: #8.
  - Merge commit: `7da1132b9e30b51a212aa6574c23e2a832d9a6fd`.
- Accepted semantic boundaries:
  - Exact canonical `RunState` values: `RECEIVED`, `VALIDATING`, `QUEUED`,
    `PLANNING`, `LOCALISING`, `GENERATING`, `EXECUTING_BUGGY`,
    `EXECUTING_FIXED`, `REPAIRING`, `SCORING`, `PUBLISHING`,
    `AWAITING_HUMAN_REVIEW`, `COMPLETED`, `ABSTAINED`, `FAILED_INPUT`,
    `FAILED_MODEL`, `FAILED_EXECUTION`, `FAILED_INFRASTRUCTURE`,
    `FAILED_SECURITY`, and `CANCELLED`.
  - The contract's allowed-transition table and terminal-state immutability.
  - `repair_attempts_used` constrained to `0..1`; retry and repair remain
    separate.
  - Repaired candidates repeat `EXECUTING_BUGGY` then `EXECUTING_FIXED`.
  - Cancellation loses after human review begins or a publication side effect
    commits.
  - Human review completes the existing run; regeneration creates a new
    request and run.
  - Internal UUIDs remain separate from external identifiers.
  - DB-002 owns `run_requests` and `runs` only; DB-003 owns steps, attempts,
    events, and ordering.
  - Event payloads contain bounded redacted metadata or opaque references only;
    no raw prompts, repository bytes, patch bytes, logs, or secrets.
  - DB-002 implements and tests stored projection shape only. Allowed-transition
    execution, compare/update concurrency, event/projection atomicity, terminal
    update rejection, transition history, regeneration decision events, and
    Workflow orchestration remain `NOT_IMPLEMENTED` / `NOT_TESTED`.

## `DB-DEP-005` — Evidence contract

- Request ID: `DB-DEP-005`
- Requesting Agent 2: `A2-DATABASE`
- Owning Agent 2: `A2-AGENT-WORKFLOW`
- Required change and reason: Publish candidate-patch, execution-attempt, evidence-card, artefact-manifest, checksum, confidence/uncertainty, failure-evidence, and human-decision linkage fields, separating relational metadata from object bytes.
- Contract affected: `CONTRACT-EVIDENCE-001`
- Exact blocking task: `DB-004` and `DB-005`
- Backward-compatibility impact: High; published evidence must remain traceable, so removals require versioned readers and migration.
- Urgency: `HIGH`
- Proposed acceptance test: A fixture traces a test-only patch through buggy/fixed executions to a complete evidence card and a human rejection while every large log/object resolves by immutable metadata and checksum.
- Approval status: `PENDING`
- Completion evidence: None; no versioned contract or handoff exists.

## `DB-DEP-006` — Queue/idempotency contract

- Request ID: `DB-DEP-006`
- Requesting Agent 2: `A2-DATABASE`
- Owning Agent 2: `A2-AGENT-WORKFLOW`
- Required change and reason: Publish job envelope, source event identifiers, idempotency key, attempt/redelivery semantics, worker-result event, correlation ID, and poison/dead-letter handling so uniqueness constraints match at-least-once delivery.
- Contract affected: `CONTRACT-QUEUE-001`
- Exact blocking task: `DB-003`. DB-002 did not persist any Queue-owned envelope, lease, visibility-timeout, or redelivery field; all remain deferred to CONTRACT-QUEUE-001.
- Backward-compatibility impact: High; idempotency key changes can create duplicates. Version the envelope/key algorithm.
- Urgency: `HIGH`
- Proposed acceptance test: Replaying the same GitHub delivery GUID + repository ID + SHA and the same benchmark tuple links to one run request, while a legitimately different SHA/configuration creates a new request.
- Approval status: `PENDING`
- Completion evidence: None; no versioned contract or handoff exists.

## `DB-DEP-007` — Evaluation contract

- Request ID: `DB-DEP-007`
- Requesting Agent 2: `A2-DATABASE`
- Owning Agent 2: `A2-EVALUATION`
- Required change and reason: Publish benchmark-case/version, revision provenance, evaluation-run configuration, metric definitions/types/ranges, baselines, release gates, flake handling, and required reproducibility fields.
- Contract affected: `CONTRACT-EVAL-001`
- Exact blocking task: `DB-006`; dataset scale also blocks DB-007 query validation.
- Backward-compatibility impact: Initial metric versions must remain interpretable; formula changes require new metric versions rather than overwriting history.
- Urgency: `MEDIUM`
- Proposed acceptance test: Persist and reconstruct one complete Defects4J evaluation with model ID, prompt version, Java version, timezone, tool versions, metric values, and release-gate result; reject missing provenance and out-of-range values.
- Approval status: `PENDING`
- Completion evidence: None; no versioned contract or handoff exists.

## `DB-DEP-008` — Security/data classification contract

- Request ID: `DB-DEP-008`
- Requesting Agent 2: `A2-DATABASE`
- Owning Agent 2: `A2-SECURITY`
- Required change and reason: Publish domain data classifications, redaction-result fields, security-event taxonomy, audit immutability requirements, IP/user metadata policy, retention/deletion constraints, and prohibited relational payloads.
- Contract affected: `CONTRACT-SEC-001`
- Exact blocking task: security-sensitive portions of DB-003 through DB-007. DB-002 persisted no Security-owned redaction, classification, or event field, and stores no secret-bearing column; retention durations remain deferred to CONTRACT-SEC-001.
- Backward-compatibility impact: Security controls may tighten additively; relaxation or event removal requires escalation.
- Urgency: `HIGH`
- Proposed acceptance test: Fixtures prove raw secrets and unredacted prompts/logs cannot enter normal relational fields, security events remain searchable and attributable, and artefact deletion preserves required audit metadata.
- Approval status: `PENDING`
- Completion evidence: None; no versioned contract or handoff exists.

## `DB-DEP-009` — Database deployment/recovery contract

- Request ID: `DB-DEP-009`
- Requesting Agent 2: `A2-DATABASE`
- Owning Agent 2: `A2-DEPLOYMENT`
- Required change and reason: Publish supported PostgreSQL version, connection/runtime variables, migration execution owner and ordering, pooling assumptions, object-storage metadata contract, backup/PITR targets, restore procedure, retention enforcement boundary, and observability requirements.
- Contract affected: `CONTRACT-DEPLOY-001`
- Exact blocking task: `DB-007` and `DB-008`. The version question is resolved in practice: `CONTRACT-DEPLOY-001` and `compose.yml` pin PostgreSQL 16, and the DB-002 migration and tests are validated against server `16.14`. Backup, PITR, restore, retention enforcement, and observability requirements remain outstanding.
- Backward-compatibility impact: Runtime variable and migration-command changes affect deployment and rollback; version them and retain a transition path.
- Urgency: `HIGH`
- Proposed acceptance test: A clean supported PostgreSQL instance applies all migrations, a representative snapshot restores, the application health check verifies connectivity, and object references resolve without public bucket access.
- Approval status: `PENDING`
- Completion evidence: None; no versioned contract or handoff exists.

## `DB-DEP-010` — Integration/handoff contract

- Request ID: `DB-DEP-010`
- Requesting Agent 2: `A2-DATABASE`
- Owning Agent 2: `A2-INTEGRATION`
- Required change and reason: Publish versioned component-handoff, dependency-resolution, contract-compatibility, schema/migration evidence, and release-readiness formats, including consumer acknowledgement requirements.
- Contract affected: `CONTRACT-INTEGRATION-001`
- Exact blocking task: `DB-005` integration coordination and final acceptance `DB-008`. Integration-owned fields touched during DB-002 remain provisional; CONTRACT-INTEGRATION-001 is not a universal DB-002 contract prerequisite. DB-DEP-011 is closed. DB-DEP-010 remains relevant to DB-005 integration coordination and DB-008 final acceptance, but it is not a DB-002 blocker.
- Backward-compatibility impact: Initial contract; later required evidence should be additive where possible.
- Urgency: `MEDIUM`
- Proposed acceptance test: A database handoff fixture identifies migration head, schema version, exact tests, consumers, unresolved requests, rollback procedure, and produces a deterministic release-readiness decision.
- Approval status: `PENDING`
- Completion evidence: None; no versioned contract or handoff exists.

## `DB-DEP-011` — Shared Python/API/database scaffold

- Request ID: `DB-DEP-011`
- Requesting Agent 2: `A2-DATABASE`
- Owning Agent 2: `A2-INTEGRATION`
- Required change and reason: Coordinate and record owner-approved creation of the shared Python/FastAPI workspace scaffold, dependency manifest and lockfile, test harness, environment schema, and local PostgreSQL development boundary required before A3-DATABASE can implement DB-002 without editing unowned protected files. Identify which files belong to A2-BACKEND, A2-DEPLOYMENT, and A2-DATABASE.
- Contract affected: `CONTRACT-INTEGRATION-001` and `CONTRACT-DEPLOY-001`
- Historical blocking task: `DB-002 implementation bootstrap`; resolved and
  closed before DB-002 implementation.
- Backward-compatibility impact: Initial scaffold. Package layout, dependency management, environment names, and migration execution command become shared conventions and must be versioned or changed through owner approval.
- Urgency: `HIGH`
- Proposed acceptance test: From a clean checkout, the approved repository-native commands create the Python environment, import the empty FastAPI package, load validated non-secret database settings, start or connect to the supported local PostgreSQL service, and collect the database test suite without A3-DATABASE modifying unowned protected files.
- Approval status: `ACCEPTED / VERIFIED_COMPLETE / CLOSED`
- Completion evidence: A2-BACKEND dependency PR #5 merged at `11b8019`.
  `DB-DEP011-DATABASE-SCAFFOLD-001-C1/C2` implements only Database-owned paths.
  A2-INTEGRATION recorded `INT-DBDEP011-POSTGRES16-001` as `PASS` at commit
  `99c8022c9f44e6a54bed624aa0153be7e32f234b`, and closed DB-DEP-011 through
  `INT-DBDEP011-CLOSEOUT-002` merged at
  `8884b5d540351c735b6cddc01314a7dd9e25af05`.
- DB-002 consumption: the scaffold supported DB-002 unchanged. No manifest,
  lockfile, environment, Compose, container, CI, or Deployment file was
  modified, and no new dependency or environment variable was required. The
  DB-002 migration tests reuse the existing `MIGRATION_DATABASE_URL` role
  against the existing `TEST_DATABASE_URL` database, exactly as
  `CONTRACT-DEPLOY-001` defines those roles.
