# Queue Open Issues

- Contract: `CONTRACT-QUEUE-001@1.0.0-draft.2`
- State: `CORRECTION_PREPARED / A2_QUEUE_FINAL_SOURCE_REVIEW_PENDING`
- Historical review: `1.0.0-draft.1 / 10_OF_10_RESPONSES_RECEIVED / NOT_ACCEPTED`
- Provider: `UNSELECTED`

| Correction issue | State | Closure boundary |
|---|---|---|
| A2-QUEUE Workflow-sequence review | `ACCEPTED` | Exact `EXECUTING_BUGGY` then `EXECUTING_FIXED` invariant passed renewed review. |
| Constraint-register structure | `VALID / 39_ROWS / 11_COLUMNS` | All stable IDs and required fields remain present. |
| Auth/Integration/Evaluation source fidelity | `17_ROWS_CORRECTED / A2_QUEUE_FINAL_SOURCE_REVIEW_PENDING` | Confirm exact mappings and full constraint/evidence obligations for 7 Auth, 5 Integration, and 5 Evaluation rows. |
| 1. Workflow attempt identity | `CORRECTED_IN_DRAFT_2 / A2_QUEUE_REVIEW_PENDING` | Confirm run/step occurrence/kind/occurrence/zero-based attempt binding and Workflow-only creation/meaning. |
| 2. Checkpoint claim/fence scope | `CORRECTED_IN_DRAFT_2 / A2_QUEUE_REVIEW_PENDING` | Confirm conditional producing claim/fence and Workflow checkpoint authority. |
| 3. One-repair maximum | `CORRECTED_IN_DRAFT_2 / A2_QUEUE_REVIEW_PENDING` | Confirm Queue operations never alter/recreate the Workflow-owned `0..1` repair allowance. |
| 4. Workflow lifecycle versus Execution runtime | `CORRECTED_IN_DRAFT_2 / A2_QUEUE_REVIEW_PENDING` | Confirm Workflow semantic ownership, Execution runtime ownership, and Queue transport-only ownership. |
| 5. Physical persistence versus Evidence semantics | `CORRECTED_IN_DRAFT_2 / A2_QUEUE_REVIEW_PENDING` | Confirm Database-exclusive physical ownership, Evidence semantic ownership, commit-before-ack, and no DB-003. |
| 6. Producer-result identity and layered deduplication | `CORRECTED_IN_DRAFT_2 / A2_QUEUE_REVIEW_PENDING` | Confirm stable Workflow-authorized result-slot identity, per-submission validation, separate canonicalizations, and layered owners. |
| 7. Heartbeat and renewal authority | `CORRECTED_IN_DRAFT_2 / A2_QUEUE_REVIEW_PENDING` | Confirm Execution inputs, Queue renewal authority, Deployment transport/configuration, Security policy, and no signal-derived authority. |
| 8. Retry classification ownership | `CORRECTED_IN_DRAFT_2 / A2_QUEUE_REVIEW_PENDING` | Confirm Queue transport categories, Workflow semantic classification, and Deployment configuration-only boundary. |
| 9. Local/test adapter isolation | `CORRECTED_IN_DRAFT_2 / A2_QUEUE_REVIEW_PENDING` | Confirm clean-checkout/no-production-credential-or-state isolation and mandatory common conformance. |
| 10. Provider-adapter Security and operational mapping | `CORRECTED_IN_DRAFT_2 / A2_QUEUE_REVIEW_PENDING` | Confirm encryption/access/identity/secret/admin mapping and minimum operational signal capability. |

## Still unresolved after correction

| Issue | State / owner boundary |
|---|---|
| Affected-owner re-review | `NOT_BEGUN`; required at the new A2-QUEUE-reviewed head. |
| Current-main reconciliation | `PENDING`; deferred to the later reviewed commit/push task. |
| Commit/push authorization | `NOT_AUTHORIZED`; pending final A2-QUEUE source review. |
| PR #24 ready/merge decision | `OPEN / DRAFT / NOT_READY / NOT_MERGED`. |
| Provider selection | `CONFIGURATION_VALUE_NOT_YET_SELECTED`. |
| DB-003 | `NOT_STARTED / UNAUTHORIZED`; no physical schema/design authorized. |
| Implementation evidence | `NOT_YET_AVAILABLE`; requires separately authorized runtime work. |
| Release gates | `INPUTS_MISSING`; configuration, compatibility, Security, and Evaluation measurements required. |

No issue authorizes runtime, provider selection, application code, tests,
dependencies, migrations, workers, sandboxes, infrastructure, PR mutation, or
DB-003.
