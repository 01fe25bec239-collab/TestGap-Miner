# Database Component Status

## Current state — DB-002

- Date: 2026-08-02
- Task: `DB-002 — Core identity, repository-context, run-request, and run
  persistence`
- Scope: `IMPLEMENTATION`
- Branch: `agent2/database`
- Baseline commit: `8884b5d540351c735b6cddc01314a7dd9e25af05`
- Result: `DB-002` `PASS / VERIFIED_COMPLETE / MERGED`; `DB-002-C1` `PASS`;
  `DB-002-C2` `PASS`; `DB-002-MERGE-001` `PASS`.
- Merge evidence: pull request #12; implementation commit
  `5506ab59211fbaba79f77d4fb5899a587c0e0236`; merge commit
  `3701520e6d61e2bb80391e7af888d0d530bdb6c4`. A2-DATABASE recorded the final
  decision `PASS`; no DB-002 review or merge action remains outstanding.
- Accepted contracts implemented against: `CONTRACT-AUTH-001@1.0.0-draft.2`
  (`ACKNOWLEDGED_AND_MERGED`) and `CONTRACT-WORKFLOW-001@1.0.0-draft.1`
  (`ACKNOWLEDGED_AND_MERGED`).
- `DB-DEP-001`: `ACCEPTED`. `DB-DEP-004`: `ACCEPTED`.
- `DB-DEP-011`: `ACCEPTED / VERIFIED_COMPLETE / CLOSED`.
- Database domain schema: `IMPLEMENTED` — seven DB-002 tables.
- Alembic state: exactly one head, `ad3f80907336`
  (`create DB-002 core entities`), down revision `None`.
- Auth runtime: `NOT_IMPLEMENTED` / `NOT_TESTED`.
- Workflow runtime: `NOT_IMPLEMENTED` / `NOT_TESTED`.
- `DB-003`: `NOT_STARTED` / `NOT_AUTHORIZED`; no step, attempt, event, ordering,
  or transition record was created, and no task authorizes one.

### Implemented DB-002 entities

| Table | Domain | Contract source |
|---|---|---|
| `users` | Canonical users | `CONTRACT-AUTH-001` |
| `auth_subjects` | External authentication subjects | `CONTRACT-AUTH-001` |
| `github_installations` | GitHub App installations | `CONTRACT-AUTH-001` |
| `repositories` | GitHub repositories | `CONTRACT-AUTH-001` |
| `repository_access` | Repository-access grants | `CONTRACT-AUTH-001` |
| `run_requests` | Run requests | `CONTRACT-WORKFLOW-001` |
| `runs` | Current run projection | `CONTRACT-WORKFLOW-001` |

Full field, constraint, index, and lifecycle documentation is in
`docs/data/database-schema.md`.

### DB-002 validation evidence

| Check | Result |
|---|---|
| `uv sync --project apps/api --all-groups --locked` | `PASS`; no manifest or lockfile change |
| Compose PostgreSQL 16 service | `PASS`; `postgres:16.14-alpine3.24`, server `16.14`, healthy |
| `alembic -c apps/api/alembic.ini heads` | `PASS`; exactly one head `ad3f80907336` |
| Upgrade from empty test database | `PASS`; seven DB-002 tables, 55 constraints, 21 indexes |
| Downgrade to base | `PASS`; zero DB-002 tables remain |
| Second upgrade to head | `PASS`; identical constraint and index counts restored |
| Database tests (`tests/database`) | `PASS`; 169 passed |
| Backend tests (`tests/api`) | `PASS`; 5 passed |
| Full suite (`tests`) | `PASS`; 174 passed |
| Forbidden DB-003/later tables | `ABSENT`; migrated schema is exactly the seven DB-002 tables plus `alembic_version` |
| Secret-bearing columns | `ABSENT`; asserted over both ORM metadata and reflected columns |
| `git diff --check` | `PASS` |

### Accepted-semantics preservation

- Internal identifiers are UUIDs; every external identifier
  (GitHub numeric IDs, delivery GUIDs, commit SHAs, benchmark IDs, model IDs,
  prompt versions, correlation IDs) is separately typed and never populates a
  UUID.
- Issuer and subject storage and comparison are exact and case-sensitive on a
  plain `(issuer, subject)` unique constraint. No `citext`, no functional
  case-folding index, and no Database normalization of any kind.
- GitHub installation and repository numeric IDs are each unique.
- Repository access is scoped to the exact user + installation + repository
  tuple, with a partial unique index restricted to `ACTIVE` grants so historical
  revoked and expired grants remain stored and a later re-grant stays
  representable.
- `expires_at`, `expired_at`, and `revoked_at` retain distinct meanings, and an
  `ACTIVE` grant with a past `expires_at` remains storable pending delayed
  status reconciliation.
- All twenty canonical `RunState` values are persisted as exact uppercase text;
  no transition order is inferred from declaration order and no transition
  service exists.
- `repair_attempts_used` is constrained to `0..1`; retry counters are separate
  and bounded by the snapshotted `retry_limit`.
- Request idempotency uses a versioned composition with a persisted key version,
  a bounded digest, and a request fingerprint for conflict detection.
- No password, hash, token, private key, webhook secret, session token, raw
  Authorization header, raw prompt, repository byte, patch byte, or execution
  log is stored.

### Runtime-enforcement boundary

- `IMPLEMENTED` / `TESTED`: allowed stored `RunState` values; terminal and
  non-terminal row-shape consistency; counter bounds; failure, abstention, and
  cancellation code consistency; optimistic-concurrency version storage; and
  terminal-attribution storage.
- `NOT_IMPLEMENTED` / `NOT_TESTED`: allowed-transition execution; an
  expected-state-and-version compare/update operation; atomic projection/event
  mutation; append-only transition history; terminal-state update rejection
  after commit; regeneration decision-event persistence; and Workflow
  orchestration.
- DB-002 has no transition trigger or service. Terminal immutability remains a
  Workflow runtime and DB-003 event-history requirement, not a DB-002 database
  enforcement claim.

### Deliberate DB-002 exclusions

Workflow steps, attempts, append-only events, event ordering, producer-event
idempotency, transition history, context selections, candidate patches, patch
contents, execution evidence and attempts, artefact metadata, publications,
human decisions, benchmark cases, evaluation results, audit and security events,
model and cost telemetry, notifications, generic organizations, tenants, roles,
permissions, billing, API-key tables, embedding tables, pgvector, Auth runtime,
Workflow runtime, API routes, service orchestration, queue consumers, automatic
publication, and orchestration triggers were all deliberately not created.

## Historical DB-WORKFLOW-CONTRACT-MERGE-001

- Date: 2026-08-01
- Task: `DB-WORKFLOW-CONTRACT-MERGE-001`
- Scope: `DOCUMENTATION_ONLY`
- Result: `PASS`
- Synchronized commit: `6cf88f135215984424bec00994a05a1de1dd011e`
- `CONTRACT-AUTH-001@1.0.0-draft.2`: `ACKNOWLEDGED_AND_MERGED`.
- `CONTRACT-WORKFLOW-001@1.0.0-draft.1`: `ACKNOWLEDGED_AND_MERGED`.
- Workflow semantic commit: `a7c83f422bb51deefd233229c7573fda64b097b6`.
- Database acknowledgement commit:
  `5eb2e98d5a8189b5a4da3f3f5d0dc0013dca3dc0`.
- `DB-001`: `PASS`, reviewed, and merged in PR #1; PR head commit `ea5f1f0`;
  merged through merge commit `dd3330ba31ea3dcb350f818f17fa6a816e1c3a86`.
- `DB-001-C1`: historical completed continuation.
- `DB-DEP011-DATABASE-SCAFFOLD-001`: historical `DEPENDENCY_BLOCKED` attempt.
- C1/C2 result: `IMPLEMENTED`, reviewed, and merged through Database PR #6 and
  merge commit `739a331c9942ed64a1ad8276d611889bbee53a27`.
- Implemented: synchronous SQLAlchemy/psycopg 3 engine, session factory,
  request-session dependency, safe runtime/migration URL resolution,
  reusable test-database safety validation, connectivity helper, empty-metadata
  Alembic bootstrap, tests, and docs.

## Historical completed DB-001/DB-001-C1 reconciliation

- Date: 2026-07-29
- Agent 2: A2-DATABASE
- Paired Agent 3: A3-DATABASE
- Parent task: `DB-001 — Repository and schema reconciliation`
- Continuation task: `DB-001-C1`
- Prompt type: `CONTINUATION`
- Branch: `agent2/database`
- Starting commit: `0cfd7c0097707586b3bca1f6d2624a7852681ae5`
- Repository root: `/Users/omkar/Documents/TestGap Miner_App`
- Remote: `https://github.com/01fe25bec239-collab/TestGap-Miner.git`
- Starting status: clean; `## agent2/database...origin/agent2/database`
- Worktrees: one worktree at the repository root on `agent2/database`
- Initial A3 result: `PASS`
- A2 review of initial handoff: `PARTIAL`
- DB-001-C1 result: `PASS`, reviewed, and merged
- Result classification: `VERIFIED_COMPLETE` for corrected reconciliation documentation
- Overall historical task classification: `PASS`

DB-001-C1 corrected repository counts, DB-002 prerequisites, and the missing
shared-scaffold dependency.

## Historical snapshot at bootstrap commit 0cfd7c0

### Present

Directories:

- `.`
- `docs/`
- `docs/components/`
- `docs/components/database/`
- `docs/specifications/`

Files:

- `.gitignore`
- `README.md`
- `docs/components/database/COMPONENT_STATUS.md`
- `docs/components/database/DECISION_LOG.md`
- `docs/components/database/DEPENDENCY_REQUESTS.md`
- `docs/components/database/LATEST_AGENT3_HANDOFF.md`
- `docs/components/database/OPEN_ISSUES.md`
- `docs/components/database/TASK_LEDGER.md`
- `docs/specifications/00_AGENT1_DECOMPOSITION_AND_INDEX(1).md`
- `docs/specifications/A2_DATABASE_MANAGER(1).md`
- `docs/specifications/SPECIFICATION_INDEX.md`
- `docs/specifications/deep-research-report (8)(8).md`
- `docs/specifications/deep-research-report (12)(4).md`
- `docs/specifications/deep-research-report (13)(4).md`
- `docs/specifications/deep-research-report (15)(2).md`

Starting-commit totals:

- 15 tracked working-tree files.
- Seven files under `docs/specifications/`.
- Six files under `docs/components/database/`.

At that bootstrap commit, repository content was documentation and Git ignore
configuration only. This is historical inventory, not current repository state.

### Absent

| Area | Evidence | Classification |
|---|---|---|
| Package manifests | No `pyproject.toml`, requirements file, `package.json`, or equivalent | `NOT_STARTED` |
| Lockfiles | No Python, Node, container, or infrastructure lockfile | `NOT_STARTED` |
| Application code | No `apps/`, `src/`, Python, TypeScript, Java, or runtime entrypoint | `NOT_STARTED` |
| ORM/database dependencies | No declared PostgreSQL driver, SQLAlchemy, Alembic, or pgvector dependency | `NOT_STARTED` |
| Database configuration | No URL schema, settings module, `.env.example`, or database version pin | `NOT_STARTED` |
| Models and schemas | No ORM model, SQL schema, Pydantic contract, or generated schema | `NOT_STARTED` |
| Migrations | No `alembic.ini`, Alembic directory, SQL migration, or migration head | `NOT_STARTED` |
| Tests | No test directory, test file, fixture, or test runner configuration | `NOT_STARTED` |
| CI | No `.github/workflows/` or other CI configuration | `NOT_STARTED` |
| Containers | No Dockerfile, Compose file, or container configuration | `NOT_STARTED` |
| Shared contracts | No `packages/contracts/` or equivalent versioned contract artefact | `NOT_STARTED` |
| ADRs | No ADR directory or ADR file; `DECISION_LOG.md` is component management only | `NOT_STARTED` |
| Handoff reports | No prior completed handoff; only the initial placeholder existed | `NOT_STARTED` |
| Deployment infrastructure | No Terraform, cloud configuration, or service manifests | `NOT_STARTED` |

At commit `0cfd7c0`, the database version, ORM code, and migration chain were
absent.

## DB-002 prerequisite boundary

- Direct task prerequisites from the authoritative manager: completed DB-001,
  accepted Auth and Workflow contracts. Auth is satisfied by
  `CONTRACT-AUTH-001@1.0.0-draft.2`; Workflow is satisfied by
  `CONTRACT-WORKFLOW-001@1.0.0-draft.1` and accepted `DB-DEP-004`.
- Shared scaffold status: `DB-DEP-011` is `ACCEPTED / VERIFIED_COMPLETE /
  CLOSED` after A2-INTEGRATION clean-checkout PostgreSQL 16 validation.
- API, Queue, Security, Deployment, and Integration inputs remain scoped constraints where their owned fields or protected files are touched; they are not universal direct contract prerequisites for DB-002.
- No upstream-owned field is frozen.

## Current database state

| Area | Classification | Actual state and evidence |
|---|---|---|
| PostgreSQL/SQLAlchemy scaffold | `IMPLEMENTED` | Synchronous psycopg 3 engine/session/configuration exists |
| Alembic setup | `IMPLEMENTED` | Configuration plus `target_metadata` containing every DB-002 model |
| Migration chain | `IMPLEMENTED` | Exactly one head `ad3f80907336`; upgrade/downgrade/upgrade validated on PostgreSQL 16.14 |
| Domain schema | `IMPLEMENTED` for DB-002 | Seven DB-002 tables; DB-003 and later domains remain absent |
| Users/auth-subject persistence | `IMPLEMENTED` | `users` and `auth_subjects` with exact case-sensitive `(issuer, subject)` uniqueness |
| GitHub installation persistence | `IMPLEMENTED` | `github_installations` with a unique GitHub numeric installation ID and no token or key storage |
| Repository access | `IMPLEMENTED` | `repository_access` scoped to the exact tuple with an `ACTIVE`-only partial unique index |
| Repositories | `IMPLEMENTED` | `repositories` with a unique GitHub numeric repository ID; API/Integration-owned display and query fields remain deferred |
| Run requests | `IMPLEMENTED` | `run_requests` with versioned idempotency uniqueness and kind-shape constraints; Queue/Security-owned fields remain deferred |
| Runs | `IMPLEMENTED` | `runs` current projection with canonical state, counter, terminal, and attribution constraints |
| Workflow steps/events | `NOT_STARTED` | Deliberately absent; DB-003 owns these records and still has scoped Queue dependencies |
| Context selections | `BLOCKED` | Missing; awaits CONTRACT-RAG-001 |
| Candidate patches | `BLOCKED` | Missing; awaits CONTRACT-EVIDENCE-001 |
| Execution attempts | `BLOCKED` | Missing; accepted Workflow semantics apply; awaits Evidence contract |
| Artefact metadata | `BLOCKED` | Missing; awaits Evidence, Security, and Deployment contracts |
| Publications | `BLOCKED` | Missing; awaits API, Evidence, and Integration contracts |
| Human decisions | `BLOCKED` | Accepted Auth semantics apply; awaits API and Evidence contracts |
| Benchmark cases | `BLOCKED` | Missing; awaits CONTRACT-EVAL-001 |
| Evaluation results | `BLOCKED` | Missing; awaits CONTRACT-EVAL-001 |
| Audit/security events | `BLOCKED` | Missing; awaits CONTRACT-SEC-001 |
| Model and cost telemetry | `BLOCKED` | Missing; accepted Workflow semantics apply; awaits Evaluation and Security contracts; billing is out of scope |
| Database unit/bootstrap tests | `PASS` | 169 Database tests pass, covering scaffold safety plus DB-002 schema, migration cycle, Auth constraints, and Workflow projection constraints |
| Authenticated PostgreSQL checks | `PASS` | Temporary PostgreSQL 17.10 checks passed |
| Approved Compose PostgreSQL 16 validation | `PASS` | DB-002 validated against the Compose `postgres:16.14-alpine3.24` service, server `16.14` |
| Index documentation | `IMPLEMENTED` for DB-002 | Every DB-002 index is documented in `docs/data/database-schema.md` with its query, selectivity, uniqueness, and lifecycle implication; DB-007 still owns whole-schema index validation |
| Retention documentation | `PARTIAL` | Principles exist, but durations and deletion semantics await Security/Deployment contracts |
| Organization tenancy and enterprise RBAC | `OUT_OF_SCOPE` | Explicit MVP non-goal |
| Billing schema | `OUT_OF_SCOPE` | Explicit MVP non-goal |
| Generic document ingestion | `OUT_OF_SCOPE` | Explicit MVP non-goal |
| Mandatory pgvector baseline | `DEPRECATED` | Superseded by deterministic retrieval first; optional feature flag only |

Infrastructure and the DB-002 domain persistence are implemented against the
merged Auth and Workflow contracts. Every later domain remains intentionally
absent and awaits its own contract and task authorization.

## Generic schema keep/adapt/reject matrix

This is the historical DB-001 generic-schema disposition. At that time no
application schema existed; DB-002 has since implemented its seven-table slice.

| Generic entity | Decision | TestGap Miner treatment |
|---|---|---|
| Organizations | `REJECT` | No organization-based enterprise tenancy in MVP |
| Users | `ADAPT` | Minimal user record plus external auth subjects; AUTH owns identity fields |
| Roles | `REJECT` | No enterprise RBAC schema in MVP |
| Permissions | `REJECT` | No enterprise RBAC schema in MVP |
| RolePermissions | `REJECT` | No enterprise RBAC schema in MVP |
| UserRoles | `REJECT` | Access scopes by user, GitHub installation, and repository |
| Projects | `ADAPT` | Replace generic workspaces with repositories and versioned benchmark cases |
| UploadedDocuments | `REJECT` | No generic document-ingestion schema |
| DocumentVersions | `REJECT` | Repository SHAs, patches, manifests, and artefact versions are domain-specific |
| ExtractedContent | `REJECT` | No OCR/general document extraction |
| Embeddings | `DEFER` | Optional only after deterministic retrieval evidence; no mandatory pgvector |
| AgentRuns | `ADAPT` | Split into run requests, runs, events, and model usage |
| WorkflowRuns | `ADAPT` | Use TestGap Miner runs governed by the canonical workflow state contract |
| WorkflowSteps | `ADAPT` | Ordered, attributable workflow steps and append-only events |
| ToolCalls | `ADAPT` | Redacted execution/model telemetry; never store raw secrets or unrestricted payloads |
| HumanApprovals | `ADAPT` | Append-only human decisions with actor and evidence linkage |
| GeneratedOutputs | `ADAPT` | Candidate patches, artefact metadata, and publication records |
| Citations | `ADAPT` | Context selections and evidence references tied to repository files and executions |
| EvaluationResults | `ADAPT` | Evaluation runs and metric results with reproducibility metadata |
| UserFeedback | `ADAPT` | Auditable accept/reject/regenerate/dismiss decisions |
| AuditLogs | `ADAPT` | Separate run-event and security-event histories with redaction |
| Notifications | `DEFER` | Backend/UI concern; add persistence only if a contract proves it is needed |
| APIKeys | `REJECT` | Raw secrets belong in managed secret storage, not database tables |
| UsageCostRecords | `ADAPT` | Model/tool usage and cost telemetry only; no billing ledger |

## Historical DB-001 provisional schema map with current DB-002 disposition

This is a domain map, not a frozen field list. Internal identifiers are UUIDs. GitHub numeric identifiers and delivery GUIDs remain separate external values. Object bytes and large logs remain in private object storage.

| Domain | Purpose and ownership | Likely ID / important uniqueness | Data handling | Required contract | DB-002 readiness |
|---|---|---|---|---|---|
| users | Minimal local principal; DB persistence, AUTH semantics | UUID; AUTH-defined subject linkage | `CONFIDENTIAL` PII; relational | AUTH | `IMPLEMENTED` in DB-002 |
| auth_subjects | Map external provider subjects to users; AUTH owns provider semantics | UUID; unique provider + external subject | `CONFIDENTIAL`; relational; no password hash unless AUTH requires it | AUTH | `IMPLEMENTED` in DB-002 |
| github_installations | Persist GitHub App installation identity, never tokens | UUID; unique GitHub numeric installation ID | `INTERNAL`; relational; secrets external | AUTH; Integration is a scoped constraint | `IMPLEMENTED` in DB-002 |
| repository_access | Scope user/install/repository access | UUID or composite; unique user + installation + repository | `INTERNAL`; relational | AUTH | `IMPLEMENTED` in DB-002 |
| repositories | Repository identity and relevant SHA metadata | UUID; unique GitHub numeric repository ID, external IDs separate | `INTERNAL`; relational metadata; source bytes external/ephemeral | AUTH direct; API/Integration scoped | `IMPLEMENTED` in DB-002 |
| run_requests | Durable invocation and idempotency boundary | UUID; unique contract-defined idempotency key | `CONFIDENTIAL`; relational metadata; large input external/redacted | WORKFLOW direct; API/Queue/Security scoped | `IMPLEMENTED` in DB-002 |
| runs | Current lifecycle/provenance for one execution | UUID; request/attempt uniqueness defined by WORKFLOW | `INTERNAL`; relational | WORKFLOW, EVIDENCE | `IMPLEMENTED` in DB-002 |
| workflow_steps | Ordered step attempts and outcomes | UUID; unique run + contract-defined sequence/attempt | `INTERNAL`; relational; large inputs/outputs external | WORKFLOW | `OUT_OF_SCOPE` for DB-002; DB-003 |
| run_events | Append-only attributable timeline | UUID; unique run + monotonic contract event position/idempotency token | `INTERNAL`; relational; redacted payloads | WORKFLOW, QUEUE, SEC | `OUT_OF_SCOPE` for DB-002; DB-003 |
| context_selections | Record ranked repository context used by a run | UUID; unique run + context item/version/rank rule | `CONFIDENTIAL`; relational references; file bytes external | RAG, SEC | `OUT_OF_SCOPE` for DB-002; DB-004 |
| candidate_patches | Versioned test-only candidate identity and hash | UUID; unique run + generation/repair attempt | `CONFIDENTIAL`; relational metadata; patch bytes in private object storage | EVIDENCE, WORKFLOW, SEC | `OUT_OF_SCOPE` for DB-002; DB-004 |
| execution_attempts | Compile/test outcomes for buggy/fixed revisions | UUID; unique candidate + revision kind + attempt | `INTERNAL`; relational results; large logs in object storage | EVIDENCE, WORKFLOW | `OUT_OF_SCOPE` for DB-002; DB-004 |
| artifacts | Immutable/versioned metadata and checksums | UUID; unique storage key and/or content hash within contract scope | Classification follows payload; metadata relational, bytes object storage | EVIDENCE, SEC, DEPLOY | `OUT_OF_SCOPE` for DB-002; DB-004 |
| publications | GitHub comment/draft-PR/SARIF attempts and fallbacks | UUID; contract idempotency across destination and candidate/version | `INTERNAL`; relational metadata; publication payload external/object storage as needed | API, EVIDENCE, INTEGRATION | `OUT_OF_SCOPE` for DB-002; DB-005 |
| human_decisions | Append-only accept/reject/regenerate/dismiss history | UUID; contract event/idempotency rule; never overwrite history | `CONFIDENTIAL` actor metadata; relational | AUTH, API, EVIDENCE | `OUT_OF_SCOPE` for DB-002; DB-005 |
| benchmark_cases | Versioned Defects4J case identity and revisions | UUID; unique project + bug ID + case/config version | `PUBLIC` or `INTERNAL`; relational metadata; corpus bytes external | EVAL | `OUT_OF_SCOPE` for DB-002; DB-006 |
| evaluation_runs | Reproducible benchmark execution identity | UUID; unique benchmark idempotency tuple from CONTRACT-DB-001 | `INTERNAL`; relational | EVAL, WORKFLOW | `OUT_OF_SCOPE` for DB-002; DB-006 |
| metric_results | Typed metric values and release-gate results | UUID; unique evaluation run + metric + scope/version | `INTERNAL`; relational | EVAL | `OUT_OF_SCOPE` for DB-002; DB-006 |
| model_usage | Versioned model/prompt/tool/token/cost metadata, not billing | UUID; provider request ID kept separate; uniqueness contract-defined | `CONFIDENTIAL`; relational redacted metadata; prompts/responses not stored raw | WORKFLOW, EVAL, SEC | `OUT_OF_SCOPE` for DB-002; DB-006 |
| security_events | Searchable auth/signature/permission/sandbox violations | UUID; source event/fingerprint uniqueness contract-defined | `RESTRICTED`; relational redacted metadata; large forensic logs external | SEC, AUTH | `OUT_OF_SCOPE` for DB-002; DB-006/DB-007 |

Fields owned by AUTH, BACKEND, RAG, AGENT-WORKFLOW, EVALUATION, SECURITY, DEPLOYMENT, and INTEGRATION remain provisional.

## Contradictions and resolutions

- The manager names research files with earlier suffixes than those present. `SPECIFICATION_INDEX.md` authorizes the present files as working inputs pending Agent 1 confirmation. This remains open.
- The generic architecture suggests SQLite as a possible MVP shortcut; the manager sets PostgreSQL as authoritative. PostgreSQL wins.
- The generic architecture treats pgvector as an MVP default; the manager requires deterministic retrieval first and optional pgvector behind a feature flag. The manager wins.
- The generic architecture/database report proposes organization tenancy, RLS, enterprise RBAC, and generic document ingestion. These are rejected for MVP by the PRD and manager.
- The generic database report proposes Liquibase/Flyway. The Python baseline requires Alembic.
- The generic database report includes database-held API keys and password hashes. `CONTRACT-AUTH-001@1.0.0-draft.2` prohibits raw secrets, password hashes, and local credentials for DB-002.
- The generic threat report assumes broad multi-tenancy and generic file ingestion. Its security controls are retained, but those product features remain out of scope.

## DB-001 acceptance evidence

- Repository state and all working-tree files were inspected.
- All present and absent implementation categories are explicit.
- All required database areas are classified.
- The complete 24-entity generic schema matrix is recorded.
- The provisional 20-domain TestGap Miner schema map is recorded.
- Contradictions and all eleven dependency requests are recorded.
- DB-002 direct contract prerequisites are limited to Auth and Workflow drafts; the owner-approved shared scaffold separately blocks implementation bootstrap.
- No application implementation or protected specification file was changed.
- DB-001/DB-001-C1 were reviewed and merged in PR #1.
