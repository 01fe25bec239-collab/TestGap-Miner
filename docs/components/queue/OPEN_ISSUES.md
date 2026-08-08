# Queue Open Issues

- Contract: `CONTRACT-QUEUE-001@1.0.0-draft.2`
- State: `DRAFT / A2_QUEUE_REVIEW_PASSED / AFFECTED_OWNER_REREVIEW_PENDING`
- Historical review: `1.0.0-draft.1 / 10_OF_10_RESPONSES_RECEIVED / NOT_ACCEPTED`
- Provider: `UNSELECTED`

| Correction issue | State | Closure boundary |
|---|---|---|
| A2-QUEUE Workflow-sequence review | `ACCEPTED` | Exact `EXECUTING_BUGGY` then `EXECUTING_FIXED` invariant passed renewed review. |
| Constraint-register structure | `VALID / 39_ROWS / 11_COLUMNS` | All stable IDs and required fields remain present. |
| Auth/Integration/Evaluation source fidelity | `COMPLETE / ACCEPTED_BY_A2_QUEUE` | Exact mappings and full constraint/evidence obligations for 7 Auth, 5 Integration, and 5 Evaluation rows passed final source review. |
| 1. Workflow attempt identity | `CORRECTED_IN_DRAFT_2 / AFFECTED_OWNER_REREVIEW_PENDING` | Confirm run/step occurrence/kind/occurrence/zero-based attempt binding and Workflow-only creation/meaning. |
| 2. Checkpoint claim/fence scope | `CORRECTED_IN_DRAFT_2 / AFFECTED_OWNER_REREVIEW_PENDING` | Confirm conditional producing claim/fence and Workflow checkpoint authority. |
| 3. One-repair maximum | `CORRECTED_IN_DRAFT_2 / AFFECTED_OWNER_REREVIEW_PENDING` | Confirm Queue operations never alter/recreate the Workflow-owned `0..1` repair allowance. |
| 4. Workflow lifecycle versus Execution runtime | `CORRECTED_IN_DRAFT_2 / AFFECTED_OWNER_REREVIEW_PENDING` | Confirm Workflow semantic ownership, Execution runtime ownership, and Queue transport-only ownership. |
| 5. Physical persistence versus Evidence semantics | `CORRECTED_IN_DRAFT_2 / AFFECTED_OWNER_REREVIEW_PENDING` | Confirm Database-exclusive physical ownership, Evidence semantic ownership, commit-before-ack, and no DB-003. |
| 6. Producer-result identity and layered deduplication | `CORRECTED_IN_DRAFT_2 / AFFECTED_OWNER_REREVIEW_PENDING` | Confirm stable Workflow-authorized result-slot identity, per-submission validation, separate canonicalizations, and layered owners. |
| 7. Heartbeat and renewal authority | `CORRECTED_IN_DRAFT_2 / AFFECTED_OWNER_REREVIEW_PENDING` | Confirm Execution inputs, Queue renewal authority, Deployment transport/configuration, Security policy, and no signal-derived authority. |
| 8. Retry classification ownership | `CORRECTED_IN_DRAFT_2 / AFFECTED_OWNER_REREVIEW_PENDING` | Confirm Queue transport categories, Workflow semantic classification, and Deployment configuration-only boundary. |
| 9. Local/test adapter isolation | `CORRECTED_IN_DRAFT_2 / AFFECTED_OWNER_REREVIEW_PENDING` | Confirm clean-checkout/no-production-credential-or-state isolation and mandatory common conformance. |
| 10. Provider-adapter Security and operational mapping | `CORRECTED_IN_DRAFT_2 / AFFECTED_OWNER_REREVIEW_PENDING` | Confirm encryption/access/identity/secret/admin mapping and minimum operational signal capability. |

## Still unresolved after correction

| Issue | State / owner boundary |
|---|---|
| Affected-owner re-review | `PENDING / NOT_BEGUN`; required from A2-AGENT-WORKFLOW, A2-DATABASE, A2-EVIDENCE, A2-EXECUTION, A2-SECURITY, A2-AUTH, A2-DEPLOYMENT, A2-INTEGRATION, and A2-EVALUATION. A2-BACKEND is not reopened because no Backend/API-owned normative boundary changed. |
| Current-main freshness reconciliation | `COMPLETE / FRESHNESS_RECONCILED / NO_QUEUE_SEMANTIC_CONFLICT_FOUND`; reconciled with latest `origin/main` `9a28d72eb08303b6701bf7db6df622006991196a` under task `QUEUE-004-C4B-LATEST-MAIN-FRESHNESS-RECONCILIATION-001`. Queue contract SHA-256 remains unchanged (`106ef0e5c4a58a6010d55f890ac852f7869e041baca963298e4af436e5aa5327`). Auth PR #29 (`CONTRACT-AUTH-001@1.1.0-draft.1`) merged on main at `9a28d72eb08303b6701bf7db6df622006991196a`; verified no Queue semantic change. |
| A2-QUEUE final source review | `PASS`; `QUEUE-004-C3-C2-CONSTRAINT-REGISTER-SOURCE-FIDELITY-CORRECTION` is `COMPLETE / ACCEPTED_BY_A2_QUEUE`. |
| PR #24 ready/merge decision | `OPEN / DRAFT / NOT_READY / NOT_MERGED`. |
| Provider selection | `CONFIGURATION_VALUE_NOT_YET_SELECTED`. |
| DB-003 | `NOT_STARTED / UNAUTHORIZED`; no physical schema/design authorized. |
| Implementation evidence | `NOT_YET_AVAILABLE`; requires separately authorized runtime work. |
| Release gates | `INPUTS_MISSING`; configuration, compatibility, Security, and Evaluation measurements required. |

No issue authorizes runtime, provider selection, application code, tests,
dependencies, migrations, workers, sandboxes, infrastructure, PR readiness or
merge, or DB-003.
