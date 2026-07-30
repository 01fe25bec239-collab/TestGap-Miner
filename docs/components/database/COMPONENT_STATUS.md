# Database Component Status

## Current state — DB-DEP011-DATABASE-SCAFFOLD-001-C2

- Date: 2026-07-30
- Task: `DB-DEP011-DATABASE-SCAFFOLD-001-C2`
- Parent: `DB-DEP011-DATABASE-SCAFFOLD-001-C1`
- Prompt type: `REPAIR`
- Starting and synchronized commit: `11b8019f91921f9be5cc162ac3db48e9bd2d5364`
- Branch: `agent2/database`
- `DB-001`: `PASS`, reviewed, and merged in PR #1 at `ea5f1f0`.
- `DB-001-C1`: historical completed continuation.
- `DB-DEP011-DATABASE-SCAFFOLD-001`: historical `DEPENDENCY_BLOCKED` attempt.
- C1/C2 result: `IMPLEMENTED` and tested at the Database boundary, pending
  A2-DATABASE review and A2-INTEGRATION PostgreSQL 16 validation.
- Implemented: synchronous SQLAlchemy/psycopg 3 engine, session factory,
  request-session dependency, safe runtime/migration URL resolution,
  reusable test-database safety validation, connectivity helper, empty-metadata
  Alembic bootstrap, tests, and docs.
- Alembic state: zero heads, no revision Python files, and zero domain tables.
- Test classification: Database unit/bootstrap tests `PASSED`; authenticated
  temporary PostgreSQL 17.10 checks `PASSED`; approved Compose PostgreSQL 16
  validation `NOT_TESTED`.
- Compose blocker: exact Docker Compose commands were `BLOCKED` because Docker
  was unavailable. A2-INTEGRATION must repeat clean-checkout validation using
  the approved PostgreSQL 16 Compose service.
- Scope: DB-002 has not begun. No model, domain table, Auth/Workflow field, or
  Alembic revision was created.
- Current blockers: domain schema `NOT_STARTED`; DB-002 `BLOCKED`;
  `CONTRACT-AUTH-001` and `CONTRACT-WORKFLOW-001` `PENDING`; DB-DEP-011 final
  acceptance `PENDING_INTEGRATION_VALIDATION`.

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

- Direct task prerequisites from the authoritative manager: completed DB-001, draft `CONTRACT-AUTH-001`, and draft `CONTRACT-WORKFLOW-001`.
- Shared scaffold status: implemented at the Database boundary; final
  DB-DEP-011 closure awaits A2 review and Integration PostgreSQL 16 validation.
- API, Queue, Security, Deployment, and Integration inputs remain scoped constraints where their owned fields or protected files are touched; they are not universal direct contract prerequisites for DB-002.
- No upstream-owned field is frozen.

## Current database state

| Area | Classification | Actual state and evidence |
|---|---|---|
| PostgreSQL/SQLAlchemy scaffold | `IMPLEMENTED` | Synchronous psycopg 3 engine/session/configuration exists |
| Alembic setup | `IMPLEMENTED` | Bootstrap configuration and empty metadata exist |
| Migration chain | `IMPLEMENTED` bootstrap | Zero heads and no revisions |
| Domain schema | `NOT_STARTED` | Zero domain tables; DB-002 was not run |
| Users/auth-subject persistence | `BLOCKED` | Missing; awaits CONTRACT-AUTH-001 |
| GitHub installation persistence | `BLOCKED` | Missing; direct DB-002 contract prerequisite is CONTRACT-AUTH-001; Integration details remain provisional |
| Repository access | `BLOCKED` | Missing; awaits CONTRACT-AUTH-001 |
| Repositories | `BLOCKED` | Missing; awaits direct Auth draft; API/Integration-owned query fields remain provisional |
| Run requests | `BLOCKED` | Missing; awaits direct Workflow draft; API/Queue/Security-owned fields remain provisional |
| Runs | `BLOCKED` | Missing; awaits CONTRACT-WORKFLOW-001 |
| Workflow steps/events | `BLOCKED` | Missing; awaits CONTRACT-WORKFLOW-001 and CONTRACT-QUEUE-001 |
| Context selections | `BLOCKED` | Missing; awaits CONTRACT-RAG-001 |
| Candidate patches | `BLOCKED` | Missing; awaits CONTRACT-EVIDENCE-001 |
| Execution attempts | `BLOCKED` | Missing; awaits Workflow and Evidence contracts |
| Artefact metadata | `BLOCKED` | Missing; awaits Evidence, Security, and Deployment contracts |
| Publications | `BLOCKED` | Missing; awaits API, Evidence, and Integration contracts |
| Human decisions | `BLOCKED` | Missing; awaits Auth, API, and Evidence contracts |
| Benchmark cases | `BLOCKED` | Missing; awaits CONTRACT-EVAL-001 |
| Evaluation results | `BLOCKED` | Missing; awaits CONTRACT-EVAL-001 |
| Audit/security events | `BLOCKED` | Missing; awaits CONTRACT-SEC-001 |
| Model and cost telemetry | `BLOCKED` | Missing; awaits Workflow, Evaluation, and Security contracts; billing is out of scope |
| Database unit/bootstrap tests | `PASS` | Safety, configuration, engine, session, dependency, connectivity-helper, and zero-head checks pass |
| Authenticated PostgreSQL checks | `PASS` | Temporary PostgreSQL 17.10 checks passed |
| Approved Compose PostgreSQL 16 validation | `NOT_TESTED` | Docker unavailable; A2-INTEGRATION must run clean-checkout validation |
| Index documentation | `PARTIAL` | Requirements mention critical lookups, but no schema-specific index plan exists |
| Retention documentation | `PARTIAL` | Principles exist, but durations and deletion semantics await Security/Deployment contracts |
| Organization tenancy and enterprise RBAC | `OUT_OF_SCOPE` | Explicit MVP non-goal |
| Billing schema | `OUT_OF_SCOPE` | Explicit MVP non-goal |
| Generic document ingestion | `OUT_OF_SCOPE` | Explicit MVP non-goal |
| Mandatory pgvector baseline | `DEPRECATED` | Superseded by deterministic retrieval first; optional feature flag only |

Infrastructure is implemented; domain persistence remains intentionally absent.
DB-002 remains blocked by pending Auth/Workflow contracts and final scaffold
review/Integration validation.

## Generic schema keep/adapt/reject matrix

No generic entity has an `ALREADY_IMPLEMENTED_EQUIVALENT`, because there is no application schema.

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

## Provisional TestGap Miner schema map

This is a domain map, not a frozen field list. Internal identifiers are UUIDs. GitHub numeric identifiers and delivery GUIDs remain separate external values. Object bytes and large logs remain in private object storage.

| Domain | Purpose and ownership | Likely ID / important uniqueness | Data handling | Required contract | DB-002 readiness |
|---|---|---|---|---|---|
| users | Minimal local principal; DB persistence, AUTH semantics | UUID; AUTH-defined subject linkage | `CONFIDENTIAL` PII; relational | AUTH | `BLOCKED` |
| auth_subjects | Map external provider subjects to users; AUTH owns provider semantics | UUID; unique provider + external subject | `CONFIDENTIAL`; relational; no password hash unless AUTH requires it | AUTH | `BLOCKED` |
| github_installations | Persist GitHub App installation identity, never tokens | UUID; unique GitHub numeric installation ID | `INTERNAL`; relational; secrets external | AUTH; Integration is a scoped constraint | `BLOCKED` |
| repository_access | Scope user/install/repository access | UUID or composite; unique user + installation + repository | `INTERNAL`; relational | AUTH | `BLOCKED` |
| repositories | Repository identity and relevant SHA metadata | UUID; unique GitHub numeric repository ID, external IDs separate | `INTERNAL`; relational metadata; source bytes external/ephemeral | AUTH direct; API/Integration scoped | `BLOCKED` |
| run_requests | Durable invocation and idempotency boundary | UUID; unique contract-defined idempotency key | `CONFIDENTIAL`; relational metadata; large input external/redacted | WORKFLOW direct; API/Queue/Security scoped | `BLOCKED` |
| runs | Current lifecycle/provenance for one execution | UUID; request/attempt uniqueness defined by WORKFLOW | `INTERNAL`; relational | WORKFLOW, EVIDENCE | `BLOCKED` |
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
- The generic database report includes database-held API keys and password hashes. Raw secrets are prohibited; local password hashes require an explicit AUTH contract.
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
