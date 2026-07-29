# Database Decision Log

## APPROVED_EXISTING_DECISION — DB-DEC-001

- Persistence: PostgreSQL.
- Python ORM baseline: SQLAlchemy 2.x style.
- Migration baseline: Alembic.
- Internal identifiers: UUIDs.
- Object bytes and large logs: private S3-compatible storage; PostgreSQL stores metadata and references.

## REJECTED_GENERIC_RECOMMENDATION — DB-DEC-002

Do not copy the generic organization/RBAC/document-ingestion schema into the MVP. Enterprise tenancy, billing, generic uploaded-document processing, and local password storage are outside the MVP boundary.

## APPROVED_EXISTING_DECISION — DB-DEC-003

MVP access is scoped through authenticated user, GitHub App installation, and repository. Full organization-based RLS tenancy is post-MVP.

## APPROVED_EXISTING_DECISION — DB-DEC-004

Do not store raw secrets, installation tokens, provider keys, full repositories, large execution logs, or unredacted prompts in ordinary relational columns.
