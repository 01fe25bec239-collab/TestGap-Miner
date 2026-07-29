# Database Decision Log

- Date reconciled: 2026-07-29
- Branch: `agent2/database`
- Starting commit: `0cfd7c0097707586b3bca1f6d2624a7852681ae5`
- Repository count baseline: 15 tracked files; seven specification files
- Initial DB-001 A3 result: `PASS`
- A2 review result: `PARTIAL`
- DB-001-C1 result: `PASS` pending A2 review

## `DB-DEC-001` — Persistence baseline

- Status: `VERIFIED_COMPLETE` as an approved documentation decision; implementation is `NOT_STARTED`.
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
- Decision: never store raw private keys, installation tokens, provider keys, API keys, or other secrets in ordinary tables. Do not add local password hashes unless CONTRACT-AUTH-001 explicitly requires them.

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
- DB-002 boundary: its direct contract prerequisites are draft CONTRACT-AUTH-001 and CONTRACT-WORKFLOW-001. API, Queue, Security, Deployment, and Integration are scoped constraints where applicable, not universal prerequisites.

## `DB-DEC-010` — Shared scaffold ownership

- Status: `BLOCKED`.
- Decision: A3-DATABASE will not create unowned protected application-root, package, dependency, lock, environment, container, or test-harness files.
- Required resolution: A2-INTEGRATION coordinates owner-approved file ownership among A2-BACKEND, A2-DEPLOYMENT, and A2-DATABASE through DB-DEP-011 before DB-002 implementation bootstrap.
