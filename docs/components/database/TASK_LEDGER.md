# Database Task Ledger

| Task | Status | Evidence | Next action |
|---|---|---|---|
| DB-001 — Repository and schema reconciliation | READY | Repository was empty before bootstrap; specifications and management records are now present | Run A3-DATABASE validation-only inspection on `agent2/database` |
| DB-002 — Canonical identifiers and core entities | BLOCKED | Requires DB-001 and draft Auth/Workflow identity contracts | Wait |
| DB-003 — Workflow persistence and event history | BLOCKED | Requires CONTRACT-WORKFLOW-001 | Wait |
| DB-004 — Context, patch, execution, and artefact metadata | BLOCKED | Requires RAG and Evidence contracts | Wait |
| DB-005 — GitHub publication and human decisions | BLOCKED | Requires Auth and Backend contracts | Wait |
| DB-006 — Evaluation, provenance, and usage metadata | BLOCKED | Requires CONTRACT-EVAL-001 | Wait |
| DB-007 — Indexes, retention, migrations, and recovery | BLOCKED | Requires DB-002 through DB-006 | Wait |
| DB-008 — Database final acceptance | BLOCKED | Requires every prior DB task and consumer feedback | Wait |
