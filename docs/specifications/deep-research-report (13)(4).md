# Database Schema and Design for the AI Platform

We design a **shared, multi-tenant relational database** (e.g. PostgreSQL) for the AI project. Tenant data (per organization) is isolated via a `tenant_id` (org_id) column on each relevant table, enforced by **Row-Level Security (RLS)**. RBAC is supported with global *Roles* and *Permissions*. The schema is normalized (3NF) with foreign-key constraints and indexes to ensure data integrity and performance.  

## Entity-Relationship Diagram (Text) 

- **Organizations** (tenants) 1–* *contain* many **Users** (through membership/user_roles) and many **Projects**.  
- **Users** *may belong to multiple* Organizations (many-to-many) via a membership table.  
- **Roles** and **Permissions** implement RBAC: a **RolePermissions** join table links roles to permissions, and a **UserRoles** (or OrganizationUsers) table links users to roles *scoped by tenant*.  
- **Projects/Workspaces** 1–* *have* many **UploadedDocuments**.  
- **UploadedDocuments** 1–* *have* multiple **DocumentVersions** (each version of a doc).  
- **DocumentVersions** 1–* *produce* **ExtractedContent** (text or data extracted).  
- **ExtractedContent** 1–* *have* **Embeddings** (vector representations) for each chunk or the full text.  
- **AgentRuns** (autonomous AI runs) 1–* *spawn* multiple **WorkflowRuns**.  
- **WorkflowRuns** 1–* *contain* multiple **WorkflowSteps**.  
- **WorkflowSteps** 1–* *may perform* **ToolCalls** and/or require **HumanApprovals**.  
- **AgentRuns** 1–* *produce* **GeneratedOutputs** (reports, answers).  
- **GeneratedOutputs** 1–* *have* many **Citations** (sources) and many **EvaluationResults**.  
- **UserFeedback** can apply to Outputs or Runs (1–* from Users to Outputs).  
- **APIKeys/Integrations** belong to Organizations or Users.  
- **UsageCost** records link usage (tokens, calls) to Org/User and track cost.  
- **AuditLogs** record user actions on any entity.  
- **Notifications** target Users about events (e.g. report ready).

Relationships use PK–FK constraints. For example, `Projects.org_id → Organizations.id`; `UploadedDocuments.project_id → Projects.id`; `UserRoles.user_id → Users.id` and `UserRoles.role_id → Roles.id`.

## Tenant Isolation and Security

**Multi-tenancy:** We use a shared database (pool model) with a `org_id` (tenant ID) on each data table. All access is filtered by the current tenant context. Data isolation is enforced using PostgreSQL Row-Level Security (RLS) policies. For example, on each table we `ENABLE ROW LEVEL SECURITY` and create a policy such as: 

```
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy 
  ON documents 
  USING (org_id = current_setting('app.current_tenant')::UUID);
```  

This ensures every query automatically applies `WHERE org_id = current_setting('app.current_tenant')`. In practice, the application sets the session parameter (`app.current_tenant`) after authenticating a user. This prevents any cross-tenant access.  

**Role-Based Access Control (RBAC):** We define global *Roles* and *Permissions* tables, and a join table to assign roles to users per tenant. For example, we implement a `user_roles` table `(user_id, org_id, role_id)` as shown in industry examples. Roles can be global (shared) or tenant-scoped; here we assume global roles with tenant-specific assignments. A `role_permissions` table maps which permissions each role has. Permission checks always include the tenant context.

**Sensitive Data Classification:** We label PII and sensitive fields appropriately. For example, **Users** contain PII (names, emails), classified as sensitive. Uploaded documents and content may contain user data or confidential information – we treat it as sensitive. Audit logs and API keys are also sensitive. Encryption (at rest/in transit) and access controls protect sensitive fields.

## Database Migration Plan

We will manage schema changes via version-controlled migrations (e.g. with Liquibase or Flyway). Best practices include: 

- **Pre-migration:** Review existing schema and data model.  
- **Backups:** Always backup the database before schema changes.  
- **Schema Migration Scripts:** Write incremental SQL changelogs for each alteration (DDL). Version-control these alongside application code.  
- **Data Transformation:** If needed, include data-migration steps to populate new columns or tables.  
- **Version Control:** Store migrations in source control and tag releases.  
- **Testing:** Apply migrations on staging with production-like data; run automated tests to validate integrity. Perform unit and integration testing of application with new schema.  
- **Rollback Plan:** Prepare a clear rollback procedure. For example, each changelog should be reversible or have a compensating script. Regularly test restores of backups to ensure rollback works. Liquibase and similar tools encourage defining rollback blocks and keeping migrations atomic.  
- **Deployment:** Use blue-green or canary deployment patterns to minimize downtime (apply schema changes off-peak). We also follow the advice to make smaller, frequent changes rather than large monolithic updates.  
- **Post-migration:** After deploying, monitor performance and check data consistency. Capture the new database state and continue drift detection. Document all changes. 

This approach aligns with general best practices (e.g. list of steps including backup, version control, testing, rollback).

## Backup and Recovery Strategy

We implement a robust backup strategy following the **3-2-1 rule**: keep 3 copies of data on 2 different media, with 1 offsite. In practice:

- **Onsite and Offsite:** Maintain backups on separate storage (e.g. cloud object storage plus on-premises storage) to guard against site failures.  
- **Backup Schedule:** Take full snapshots of the database weekly, with incremental (or differential) backups daily. For example, a full backup every Sunday and incremental nightly.  
- **Retention:** Keep full backups at least 8 weeks (2 months) as recommended for SMBs. Keep daily incrementals for at least one week. Store older archives offsite or in cold storage.  
- **Testing:** Regularly test backup restoration procedures to ensure recovery works.  
- **Point-in-Time Recovery (PITR):** If using PostgreSQL, enable WAL archiving to allow restoring to a specific time within retention.  
- **Encryption and Compliance:** Backups should be encrypted and access-controlled since they contain sensitive data (PII).  

With this strategy, we ensure data can be recovered after failures or disasters. Following the cited guidelines, full backups weekly with daily incrementals and multi-month retention provides safety.

## Tables and Schemas

Below is the detailed schema for each required table. We include the purpose, columns (with types), keys, indexes, constraints, retention policy, and sensitivity of each.

### Organizations  
- **Purpose:** Represents a tenant or customer.  
- **Columns:**  
  - `id` **UUID** (PK) – unique tenant identifier.  
  - `name` **text** – organization name.  
  - `created_at` **timestamp** – when created.  
  - `status` **text** – e.g. ‘active’, ‘suspended’.  
  - *Optional:* billing info fields (if needed separately).  
- **PK:** `id`.  
- **FKs:** None (top-level entity).  
- **Indexes:** Unique index on `id` (PK) and on `name` if name lookup needed.  
- **Unique:** `name` unique to prevent duplicates (if desired).  
- **Validation:** `name` non-null; `status` in allowed set.  
- **Retention:** Keep for life of tenant; when a tenant is deleted, archive or hard-delete based on policy (possibly after N months).  
- **Sensitive:** Organization metadata (likely not PII unless it contains contact info).  

### Users  
- **Purpose:** User accounts in the system.  
- **Columns:**  
  - `id` **UUID** (PK) – unique user ID.  
  - `org_id` **UUID** (FK → Organizations.id) – *primary/default organization or tenant of this user.* (If multi-org, could be null and use `UserRoles` table instead.)  
  - `email` **text** – user’s email (login).  
  - `password_hash` **text** – hashed password or auth info.  
  - `name` **text** – user’s name.  
  - `created_at` **timestamp** – account creation time.  
  - `last_login` **timestamp** – last login time.  
  - `is_active` **boolean** – active status.  
- **PK:** `id`.  
- **FKs:** `org_id → Organizations.id`. (If a user can join multiple orgs, model via a join table instead.)  
- **Indexes:** Unique index on (`org_id`, `email`) to enforce unique emails per org; or global unique on `email` if cross-org uniqueness required. Also index on `org_id` for tenancy.  
- **Unique:** `email` (with org scope) must be unique.  
- **Validation:** `email` must match email format; `password_hash` non-null (or support OAuth so could be null if external auth).  
- **Retention:** Retain user records for e.g. 2 years after deactivation for auditing.  
- **Sensitive:** Contains PII (email, name) and credentials – **Sensitive/PII**. Password hashes should be securely protected.  

### Roles  
- **Purpose:** Defines named roles for RBAC (e.g. Admin, Viewer).  
- **Columns:**  
  - `id` **serial/int or UUID** (PK) – role ID.  
  - `name` **text** – role name.  
  - `description` **text** – optional description.  
  - `created_at` **timestamp**.  
- **PK:** `id`.  
- **FKs:** None. (If tenant-specific roles were needed, add `org_id` FK; here we assume global roles.)  
- **Indexes:** Unique index on `name` (global).  
- **Unique:** `name` unique.  
- **Validation:** `name` non-null, matches allowed pattern (alphanumeric).  
- **Retention:** Roles are usually static; if deprecated, either keep for history or soft-delete.  
- **Sensitive:** No sensitive data.  

### Permissions  
- **Purpose:** Defines fine-grained permissions (actions on resources).  
- **Columns:**  
  - `id` **serial/int or UUID** (PK).  
  - `action` **text** – e.g. ‘read’, ‘write’.  
  - `resource` **text** – e.g. ‘document’, ‘project’.  
  - `description` **text**.  
- **PK:** `id`.  
- **FKs:** None.  
- **Indexes:** Unique on `(action, resource)` to prevent duplicates (per example).  
- **Unique:** (`action`, `resource`) or a composite name unique index.  
- **Validation:** `action` and `resource` non-null.  
- **Retention:** Permissions rarely deleted; if new ones added, old ones kept.  
- **Sensitive:** No.  

### RolePermissions  
- **Purpose:** Join table linking roles to permissions (many-to-many).  
- **Columns:**  
  - `role_id` (FK → Roles.id).  
  - `permission_id` (FK → Permissions.id).  
- **PK:** Composite `(role_id, permission_id)`.  
- **FKs:** As above.  
- **Indexes:** Implicit via PK on `(role_id, permission_id)`; consider index on `permission_id` for reverse lookup.  
- **Unique:** PK ensures uniqueness.  
- **Validation:** N/A beyond FKs.  
- **Retention:** Tied to existing roles/permissions; cascade delete if a role or permission is removed.  
- **Sensitive:** No.  

### UserRoles (or OrganizationUsers)  
- **Purpose:** Assigns users to roles within an organization (tenant-scoped RBAC).  
- **Columns:**  
  - `user_id` (FK → Users.id).  
  - `org_id` (FK → Organizations.id).  
  - `role_id` (FK → Roles.id).  
- **PK:** Composite `(user_id, org_id, role_id)`.  
- **FKs:** As above.  
- **Indexes:** Index on `(org_id, user_id)` or `(user_id, org_id)` for lookups; PK index on all three.  
- **Unique:** The PK ensures a user can’t have the same role twice in one org.  
- **Validation:** All three columns non-null.  
- **Retention:** If a user leaves an org or loses a role, delete row. Keep history if auditing is needed.  
- **Sensitive:** No PII beyond linking to Users.  

### Projects (Workspaces)  
- **Purpose:** A workspace or project belonging to an organization, grouping documents and runs.  
- **Columns:**  
  - `id` **UUID** (PK).  
  - `org_id` **UUID** (FK → Organizations.id) – tenant ownership.  
  - `name` **text** – project name.  
  - `description` **text** – details.  
  - `created_by` **UUID** (FK → Users.id) – owner or creator.  
  - `created_at` **timestamp**.  
- **PK:** `id`.  
- **FKs:** `org_id → Organizations.id`; `created_by → Users.id`.  
- **Indexes:** Index on `(org_id, name)` for unique-per-org query; index on `org_id`.  
- **Unique:** `(org_id, name)` to ensure unique project names within an org.  
- **Validation:** `name` non-null; `org_id` non-null.  
- **Retention:** Delete or archive when project is deleted (cascade its documents). May keep metadata if needed for audit.  
- **Sensitive:** `description` may contain business logic – treat as non-public but not highly sensitive.  

### UploadedDocuments  
- **Purpose:** Tracks documents (files) uploaded by users.  
- **Columns:**  
  - `id` **UUID** (PK).  
  - `project_id` **UUID** (FK → Projects.id).  
  - `uploader_id` **UUID** (FK → Users.id).  
  - `file_name` **text**, `file_size` **int**, `content_type` **text** – file metadata.  
  - `storage_path` **text** or `file_url` – location in storage.  
  - `status` **text** – e.g. ‘uploaded’, ‘processing’, ‘error’.  
  - `created_at` **timestamp**.  
- **PK:** `id`.  
- **FKs:** `project_id → Projects.id`; `uploader_id → Users.id`.  
- **Indexes:** Index on `project_id`; possibly on `status` if querying by status.  
- **Unique:** None besides PK.  
- **Validation:** `file_name`, `storage_path`, `project_id` non-null.  
- **Retention:** Documents are retained as long as the project exists or as per data retention rules (e.g. purge after N years or on project deletion).  
- **Sensitive:** The content may be sensitive (user’s documents). Mark as sensitive.  

### DocumentVersions  
- **Purpose:** Maintains version history for uploaded documents.  
- **Columns:**  
  - `id` **UUID** (PK).  
  - `document_id` **UUID** (FK → UploadedDocuments.id).  
  - `version_number` **int** – version index (1,2,…).  
  - `content_hash` **text** – checksum for integrity.  
  - `file_size` **int** – size of this version.  
  - `created_at` **timestamp**.  
- **PK:** `(document_id, version_number)` composite, or surrogate `id`.  
- **FKs:** `document_id → UploadedDocuments.id`.  
- **Indexes:** PK index on `(document_id, version_number)`. Index on `document_id`.  
- **Unique:** Composite `(document_id, version_number)` ensures no duplicate versions.  
- **Validation:** `version_number` ≥ 1, incremented sequentially.  
- **Retention:** Retain all versions (for history); purge old versions if policy requires (older than X years).  
- **Sensitive:** Same as parent document – content may contain sensitive data.  

### ExtractedContent  
- **Purpose:** Stores text/data extracted from a document version (e.g. OCR text, JSON output).  
- **Columns:**  
  - `id` **UUID** (PK).  
  - `version_id` **UUID** (FK → DocumentVersions.id).  
  - `content` **text** – extracted text or data.  
  - `created_at` **timestamp**.  
- **PK:** `id`. (Or use `(version_id, id)` if multiple extracts per version.)  
- **FKs:** `version_id → DocumentVersions.id`.  
- **Indexes:** Index on `version_id`.  
- **Unique:** One-to-one or one-to-many per version as needed. If each version has exactly one content, could make `version_id` UNIQUE.  
- **Validation:** `content` non-null after extraction; may enforce max length or break into chunks.  
- **Retention:** Keep as long as DocumentVersion exists; optionally archive raw text for privacy reasons.  
- **Sensitive:** Content may contain any data from user’s document – **Highly Sensitive/PII** if documents include personal info.  

### Embeddings  
- **Purpose:** Stores vector embeddings computed from extracted content for similarity search or ML tasks.  
- **Columns:**  
  - `id` **UUID** (PK).  
  - `content_id` **UUID** (FK → ExtractedContent.id).  
  - `embedding` **vector** (e.g. using pgvector) or **float[]** – high-dimensional vector.  
  - `model` **text** – which embedding model was used.  
  - `created_at` **timestamp**.  
- **PK:** `id`.  
- **FKs:** `content_id → ExtractedContent.id`.  
- **Indexes:** A **vector index** on `embedding` (e.g. ivfflat, hnsw) for fast nearest-neighbor search (Postgres pgvector). Index on `content_id`.  
- **Unique:** One embedding per content chunk; if multiple chunks, each gets unique id. No enforced unique constraint on vector.  
- **Validation:** `embedding` non-null, match expected dimension (e.g. 1536 floats).  
- **Retention:** Follow content retention. May drop embeddings for old content after policy expires.  
- **Sensitive:** Vectors do not reveal raw text easily, but consider them as sensitive-derived data (cannot be reconstructed reliably, so lower sensitivity).  

### AgentRuns  
- **Purpose:** Represents an autonomous AI agent execution in response to a user request.  
- **Columns:**  
  - `id` **UUID** (PK).  
  - `org_id` **UUID** (FK → Organizations.id).  
  - `project_id` **UUID** (FK → Projects.id) – context.  
  - `initiated_by` **UUID** (FK → Users.id).  
  - `prompt` **text** – initial query or goal.  
  - `status` **text** – e.g. ‘running’, ‘completed’, ‘failed’.  
  - `started_at`, `ended_at` **timestamp**.  
- **PK:** `id`.  
- **FKs:** `org_id → Organizations.id`, `project_id → Projects.id`, `initiated_by → Users.id`.  
- **Indexes:** Index on `(org_id, status)` for querying runs by tenant and status; on `started_at`.  
- **Unique:** None.  
- **Validation:** `status` in allowed set; `prompt` length limit.  
- **Retention:** Keep run records for audit/training (e.g. 1–2 years). Purge old if needed.  
- **Sensitive:** Prompt and logs may contain sensitive user queries or data – **Sensitive**.  

### WorkflowRuns  
- **Purpose:** Tracks a higher-level workflow execution triggered by an AgentRun (if workflows span multiple steps).  
- **Columns:**  
  - `id` **UUID** (PK).  
  - `agent_run_id` **UUID** (FK → AgentRuns.id).  
  - `status` **text** (e.g. ‘pending’, ‘running’, ‘complete’, ‘failed’).  
  - `started_at`, `ended_at` **timestamp**.  
- **PK:** `id`.  
- **FKs:** `agent_run_id → AgentRuns.id`.  
- **Indexes:** Index on `(agent_run_id)`, on `status`.  
- **Unique:** One workflow per agent run (if one-to-one). If multiple workflows per run, no uniqueness.  
- **Validation:** `status` non-null.  
- **Retention:** Similar to AgentRuns.  
- **Sensitive:** Logs or input may contain sensitive info – **Sensitive** if linked to user data.  

### WorkflowSteps  
- **Purpose:** Individual steps or tasks within a WorkflowRun (e.g. “Generate outline”, “Fetch data”).  
- **Columns:**  
  - `id` **UUID** (PK).  
  - `workflow_run_id` **UUID** (FK → WorkflowRuns.id).  
  - `step_name` **text** – descriptive name.  
  - `status` **text** (‘pending’, ‘running’, ‘done’, ‘error’).  
  - `started_at`, `ended_at` **timestamp**.  
  - `input_data` **jsonb** – any input parameters.  
  - `output_data` **jsonb** – step output (if small).  
- **PK:** `id`.  
- **FKs:** `workflow_run_id → WorkflowRuns.id`.  
- **Indexes:** Index on `workflow_run_id`.  
- **Unique:** None needed.  
- **Validation:** `step_name`, `status` non-null.  
- **Retention:** Keep for history, possibly purge after workflows end.  
- **Sensitive:** Step inputs/outputs could include user data or API responses – **Sensitive**.  

### ToolCalls  
- **Purpose:** Logs each call to an external tool or service (e.g. OpenAI API) during a step.  
- **Columns:**  
  - `id` **UUID** (PK).  
  - `step_id` **UUID** (FK → WorkflowSteps.id).  
  - `tool_name` **text** – e.g. ‘OpenAI’, ‘BrowserTool’.  
  - `request` **jsonb** – parameters sent.  
  - `response` **jsonb** – raw response received.  
  - `started_at`, `ended_at` **timestamp**.  
  - `status` **text** (‘success’, ‘error’).  
- **PK:** `id`.  
- **FKs:** `step_id → WorkflowSteps.id`.  
- **Indexes:** Index on `(step_id)`, on `tool_name`.  
- **Unique:** None.  
- **Validation:** `tool_name`, `status` non-null.  
- **Retention:** Log for auditing (e.g. 6–12 months). Possibly purge old logs.  
- **Sensitive:** Request/response may include confidential data or API keys – **Highly Sensitive**.  

### HumanApprovals  
- **Purpose:** Captures human review steps (approve/reject) within workflows.  
- **Columns:**  
  - `id` **UUID** (PK).  
  - `step_id` **UUID** (FK → WorkflowSteps.id).  
  - `requested_by` **UUID** (FK → Users.id).  
  - `reviewer_id` **UUID** (FK → Users.id) – approver.  
  - `status` **text** (‘pending’, ‘approved’, ‘rejected’).  
  - `requested_at`, `responded_at` **timestamp**.  
  - `comment` **text** – reviewer’s comments.  
- **PK:** `id`.  
- **FKs:** `step_id → WorkflowSteps.id`, `requested_by → Users.id`, `reviewer_id → Users.id`.  
- **Indexes:** Index on `step_id`, on `status`.  
- **Unique:** One record per reviewer per step.  
- **Validation:** `status` allowed values; `responded_at` non-null if status is final.  
- **Retention:** Keep approvals for compliance (e.g. same as audit logs).  
- **Sensitive:** Comments or attachments may contain internal feedback – treat as sensitive.  

### GeneratedOutputs  
- **Purpose:** Final outputs generated by agents/workflows (reports, answers, etc.).  
- **Columns:**  
  - `id` **UUID** (PK).  
  - `agent_run_id` **UUID** (FK → AgentRuns.id).  
  - `content` **text or jsonb** – the output (report text, etc.).  
  - `format` **text** – e.g. ‘markdown’, ‘pdf’.  
  - `created_at` **timestamp**.  
- **PK:** `id`.  
- **FKs:** `agent_run_id → AgentRuns.id`.  
- **Indexes:** Index on `agent_run_id`.  
- **Unique:** None. (An agent run could produce multiple outputs.)  
- **Validation:** `content` non-null; enforce max length if needed or store large blobs elsewhere.  
- **Retention:** Keep outputs as long as needed (e.g. 1–2 years or archive).  
- **Sensitive:** Output may contain user data and analysis – **Sensitive**.  

### Citations  
- **Purpose:** Records sources cited in a GeneratedOutput (e.g. URLs, documents with quotes).  
- **Columns:**  
  - `id` **UUID** (PK).  
  - `output_id` **UUID** (FK → GeneratedOutputs.id).  
  - `source_url` **text** – link or citation reference.  
  - `extracted_text` **text** – snippet or quote from the source.  
  - `page_number` **int** – if applicable (for PDFs).  
  - `created_at` **timestamp**.  
- **PK:** `id`.  
- **FKs:** `output_id → GeneratedOutputs.id`.  
- **Indexes:** Index on `output_id`.  
- **Unique:** Allow multiple citations per output. No unique constraint.  
- **Validation:** `source_url` should be a valid URL if provided.  
- **Retention:** Keep for audit (same as outputs). Possibly expire if output is deleted.  
- **Sensitive:** Usually public sources, but `extracted_text` may contain copyrighted material – treat as non-PII, but respect IP.  

### EvaluationResults  
- **Purpose:** Stores evaluation metrics or scores for outputs (e.g. automated or human evaluation).  
- **Columns:**  
  - `id` **UUID** (PK).  
  - `output_id` **UUID** (FK → GeneratedOutputs.id).  
  - `metric` **text** – e.g. ‘accuracy’, ‘relevance’.  
  - `value` **float** – numeric result.  
  - `evaluated_at` **timestamp**.  
  - `evaluator_id` **UUID** (FK → Users.id, nullable) – if a human did it.  
- **PK:** `id`.  
- **FKs:** `output_id → GeneratedOutputs.id`; `evaluator_id → Users.id`.  
- **Indexes:** Index on `(output_id, metric)`.  
- **Unique:** Could enforce one metric per output or allow updates (not strictly needed).  
- **Validation:** `value` within expected range.  
- **Retention:** Keep for analysis (e.g. years).  
- **Sensitive:** Results themselves are not sensitive, but may correlate with output content (sensitive indirectly).  

### UserFeedback  
- **Purpose:** User ratings or comments on outputs or agent runs.  
- **Columns:**  
  - `id` **UUID** (PK).  
  - `user_id` **UUID** (FK → Users.id).  
  - `target_type` **text** – e.g. ‘output’, ‘agent_run’.  
  - `target_id` **UUID** – ID of the output or run.  
  - `rating` **int** – e.g. 1–5 stars or -1/0/1.  
  - `comment` **text**.  
  - `created_at` **timestamp**.  
- **PK:** `id`.  
- **FKs:** `user_id → Users.id`. Targets are polymorphic (could reference `GeneratedOutputs.id` or `AgentRuns.id`).  
- **Indexes:** Index on `(target_type, target_id)` for lookup.  
- **Unique:** One feedback per user per target (optional).  
- **Validation:** `rating` within allowed range.  
- **Retention:** Keep per feedback policy (usually a few years).  
- **Sensitive:** Comments may contain user opinions; consider moderate privacy but not highly sensitive.  

### AuditLogs  
- **Purpose:** Immutable log of actions for security/audit (user actions, data changes).  
- **Columns:**  
  - `id` **bigserial** (PK).  
  - `timestamp` **timestamp** – when action occurred.  
  - `user_id` **UUID** (nullable, FK → Users.id) – who did it (could be system or null).  
  - `action` **text** – e.g. ‘login’, ‘create_document’.  
  - `entity` **text** – table or object type affected.  
  - `entity_id` **UUID or text** – ID of affected record (nullable).  
  - `details` **jsonb** – additional info (before/after values).  
  - `ip_address` **inet** – source IP (optional).  
- **PK:** `id`.  
- **FKs:** `user_id → Users.id`.  
- **Indexes:** Index on `timestamp`; on `user_id`.  
- **Unique:** None. (Logs should never conflict.)  
- **Validation:** All fields non-null except optional (entity_id, user_id).  
- **Retention:** High-retention (e.g. 1+ year) for compliance; purge only as allowed.  
- **Sensitive:** Logs may record sensitive actions (e.g. file access) – treat as **Sensitive** (but mostly metadata, not user data).  

### Notifications  
- **Purpose:** In-app or email notifications for users (e.g. “Report ready”).  
- **Columns:**  
  - `id` **UUID** (PK).  
  - `user_id` **UUID** (FK → Users.id).  
  - `type` **text** – e.g. ‘report_ready’, ‘approval_needed’.  
  - `message` **text** – notification text.  
  - `created_at` **timestamp**.  
  - `read_at` **timestamp** (nullable) – when marked read.  
- **PK:** `id`.  
- **FKs:** `user_id → Users.id`.  
- **Indexes:** Index on `user_id`; on `(user_id, read_at)` to find unread.  
- **Unique:** None (multiple notifications per user).  
- **Validation:** `type` non-null; `message` non-null.  
- **Retention:** Delete or archive after user reads (optional, e.g. keep 30 days).  
- **Sensitive:** Messages may contain details but not PII typically.  

### APIKeys (Integrations)  
- **Purpose:** Stores API keys or integration credentials for external services.  
- **Columns:**  
  - `id` **UUID** (PK).  
  - `org_id` **UUID** (FK → Organizations.id) or `user_id` – owner of key.  
  - `service` **text** – e.g. ‘OpenAI’, ‘Dropbox’.  
  - `key` **text** – the API key or token (encrypted/hashed).  
  - `secret` **text** (nullable) – optional secret.  
  - `scope` **text** – permitted scopes/permissions.  
  - `created_at`, `revoked_at` **timestamp**.  
- **PK:** `id`.  
- **FKs:** `org_id → Organizations.id` (if org-scoped), `user_id → Users.id` (if user-scoped).  
- **Indexes:** Index on `org_id` or `user_id`; on `service`.  
- **Unique:** Possibly unique index on `(org_id, service)` if only one key per service.  
- **Validation:** `key` non-null; store encrypted.  
- **Retention:** Keep active keys; delete or archive revoked keys after grace period.  
- **Sensitive:** Keys and secrets – **Highly Sensitive**.  

### UsageCostRecords  
- **Purpose:** Tracks usage of resources and associated costs (for billing).  
- **Columns:**  
  - `id` **UUID** (PK).  
  - `org_id` **UUID** (FK → Organizations.id).  
  - `user_id` **UUID** (FK → Users.id, nullable) – who used it.  
  - `date` **date** – day of usage.  
  - `resource` **text** – e.g. ‘tokens’, ‘api_calls’, ‘storage’.  
  - `quantity` **numeric** – amount used (e.g. number of tokens).  
  - `cost` **numeric** – cost in currency.  
  - `recorded_at` **timestamp**.  
- **PK:** `id`. (Could also use composite `(org_id, date, resource)` as key.)  
- **FKs:** `org_id → Organizations.id`, `user_id → Users.id`.  
- **Indexes:** Index on `(org_id, date)` for aggregation; on `date`.  
- **Unique:** Possibly unique per `(org_id, date, resource)` if aggregated daily; otherwise multiple entries allowed.  
- **Validation:** `quantity >= 0`; `cost >= 0`.  
- **Retention:** Keep at least a billing cycle (e.g. 1 year); older can be aggregated or purged.  
- **Sensitive:** Usage patterns could indirectly reveal data usage but not PII – treat as low sensitivity.  

## Row-Level Security Rules 

To implement tenant isolation, we enable RLS on each table that contains `org_id` (tenant_id). For example: 

```sql
ALTER TABLE <table> ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy 
  ON <table> 
  FOR ALL 
  USING (org_id = current_setting('app.current_tenant')::UUID);
```

This policy automatically scopes all reads and writes to the current tenant. As one source explains, RLS “allows controlling access to rows in a table based on context (for example, `tenant_id`)” and is available in Postgres. We repeat this for all tenant-scoped tables (Projects, Documents, AgentRuns, etc.). Tables like **Roles** and **Permissions** (global) need no `org_id` and can be open to all, or optionally also locked by a global-admin-only RLS rule.

## Database Migration Plan

Schema changes will follow a migration-based approach under version control. For each release: write SQL changelogs (or use an ORM/DDL tool) that add/alter tables and columns. Review and test migrations in staging. Apply migrations during off-peak hours. Keep a rollback script for each change. We will also **document** the schema state and monitor for drift. Automation tools (Liquibase/Flyway) will track which migrations have been applied, helping audits and enabling one-click deployments.

## Backup Strategy

We follow the 3-2-1 backup rule. In practice:
- **3 copies:** Production database + 2 backups.
- **2 media:** e.g. primary DB and backups in cloud storage + on-premises storage.
- **1 offsite:** At least one backup stored offsite or in a different region.  

We take weekly full backups with daily incremental backups. Full backups are retained for 8+ weeks (≈2 months) as recommended; incrementals for 1–2 weeks. We encrypt backups and periodically restore test snapshots to verify integrity. This aligns with backup best practices.

## Sample Records

**Organizations:**  
- (id=`org-1`, name=“Acme Corp”, created_at=`2026-01-01`)  

**Users:**  
- (id=`user-1`, org_id=`org-1`, email=`alice@acme.com`, name=`Alice`, created_at=`2026-01-02`, is_active=TRUE)  
- (id=`user-2`, org_id=`org-1`, email=`bob@acme.com`, name=`Bob`, created_at=`2026-01-05`, is_active=TRUE)  

**Roles:**  
- (id=1, name=`admin`)  
- (id=2, name=`viewer`)  

**Permissions:**  
- (id=1, action=`read`, resource=`document`)  
- (id=2, action=`write`, resource=`document`)  

**RolePermissions:**  
- (role_id=1, permission_id=1)  *(admin → read-document)*  
- (role_id=1, permission_id=2)  *(admin → write-document)*  
- (role_id=2, permission_id=1)  *(viewer → read-document)*  

**UserRoles:**  
- (user_id=`user-1`, org_id=`org-1`, role_id=1)  *(Alice is admin)*  
- (user_id=`user-2`, org_id=`org-1`, role_id=2)  *(Bob is viewer)*  

**Projects:**  
- (id=`proj-1`, org_id=`org-1`, name=`Project Alpha`, created_by=`user-1`, created_at=`2026-01-10`)  

**UploadedDocuments:**  
- (id=`doc-1`, project_id=`proj-1`, uploader_id=`user-1`, file_name=`report.pdf`, file_size=204800, content_type=`application/pdf`, storage_path=`/files/org-1/proj-1/report.pdf`, status=`uploaded`, created_at=`2026-01-10`)  

**DocumentVersions:**  
- (document_id=`doc-1`, version_number=1, content_hash=`abc123`, file_size=204800, created_at=`2026-01-10`)  

**ExtractedContent:**  
- (id=`cont-1`, version_id=`doc-1#1`, content=`"This is the report text..."`, created_at=`2026-01-10`)  

**Embeddings:**  
- (id=`emb-1`, content_id=`cont-1`, embedding=`[0.12, 0.03, …]`, model=`text-embedding-xyz`, created_at=`2026-01-10`)  

**AgentRuns:**  
- (id=`run-1`, org_id=`org-1`, project_id=`proj-1`, initiated_by=`user-1`, prompt=`"Summarize document"`, status=`completed`, started_at=`2026-01-10 10:00`, ended_at=`2026-01-10 10:05`)  

**WorkflowRuns:**  
- (id=`wf-1`, agent_run_id=`run-1`, status=`completed`, started_at=`2026-01-10 10:01`, ended_at=`2026-01-10 10:05`)  

**WorkflowSteps:**  
- (id=`step-1`, workflow_run_id=`wf-1`, step_name=`Generate Summary`, status=`completed`, started_at=`2026-01-10 10:01`, ended_at=`2026-01-10 10:03`)  

**ToolCalls:**  
- (id=`call-1`, step_id=`step-1`, tool_name=`OpenAI`, status=`success`, request=`{"prompt":"Summarize ..."}`, response=`{"text":"..."}`, started_at=`2026-01-10 10:01`, ended_at=`2026-01-10 10:02`)  

**HumanApprovals:**  
- (id=`app-1`, step_id=`step-1`, requested_by=`user-1`, reviewer_id=`user-2`, status=`approved`, requested_at=`2026-01-10 10:02`, responded_at=`2026-01-10 10:04`, comment=`"Looks good"`)  

**GeneratedOutputs:**  
- (id=`out-1`, agent_run_id=`run-1`, content=`"Summary: ..."`, format=`markdown`, created_at=`2026-01-10 10:05`)  

**Citations:**  
- (id=`cite-1`, output_id=`out-1`, source_url=`"https://example.com"`, extracted_text=`"Relevant excerpt ..."`, created_at=`2026-01-10 10:05`)  

**EvaluationResults:**  
- (id=`eval-1`, output_id=`out-1`, metric=`accuracy`, value=0.85, evaluated_at=`2026-01-10 11:00`)  

**UserFeedback:**  
- (id=`fb-1`, user_id=`user-2`, target_type=`output`, target_id=`out-1`, rating=5, comment=`"Excellent summary"`, created_at=`2026-01-10 11:05`)  

**AuditLogs:**  
- (id=1, timestamp=`2026-01-10 10:00`, user_id=`user-1`, action=`upload_document`, entity=`UploadedDocuments`, entity_id=`doc-1`, details=`{"file_name":"report.pdf"}`, ip_address=`192.168.1.10`)  

**Notifications:**  
- (id=`noti-1`, user_id=`user-1`, type=`report_ready`, message=`"Your report is ready."`, created_at=`2026-01-10 10:05`, read_at=`2026-01-10 10:06`)  

**APIKeys:**  
- (id=`key-1`, org_id=`org-1`, service=`OpenAI`, key=`"<encrypted-key>"`, scope=`"create:embedding,create:completion"`, created_at=`2026-01-01`)  

**UsageCostRecords:**  
- (id=`u-1`, org_id=`org-1`, user_id=`user-1`, date=`2026-01-10`, resource=`tokens`, quantity=1500, cost=0.045, recorded_at=`2026-01-10 23:59`)  

These examples illustrate how entities link via foreign keys and how multi-tenant data is scoped by `org_id`. All queries for a given tenant would automatically filter by that `org_id`, as enforced by RLS.

**Sources:** Best practices and patterns are informed by industry guidelines for multi-tenant RBAC and data isolation, as well as backup and migration strategies. These inform our design choices above.