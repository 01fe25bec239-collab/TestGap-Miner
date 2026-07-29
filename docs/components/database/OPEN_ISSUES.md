# Database Open Issues

## DB-ISSUE-001 — Specification filename mismatch

The A2 manager references earlier research-document filenames than the uploaded files. The uploaded files are used as working inputs, but Agent 1 should confirm authoritative revision lineage.

## DB-ISSUE-002 — Upstream contracts unavailable

The following versioned contract drafts are not yet present:

- CONTRACT-AUTH-001
- CONTRACT-API-001
- CONTRACT-RAG-001
- CONTRACT-WORKFLOW-001
- CONTRACT-EVIDENCE-001
- CONTRACT-QUEUE-001
- CONTRACT-EVAL-001
- CONTRACT-SEC-001
- CONTRACT-DEPLOY-001
- CONTRACT-INTEGRATION-001

DB-001 may proceed without freezing these contracts. DB-002 and later tasks must respect their prerequisites.

## DB-ISSUE-003 — No implementation baseline

The repository was empty before bootstrap. Documentation must not be treated as implemented functionality.
