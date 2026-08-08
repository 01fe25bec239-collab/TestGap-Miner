# Queue Open Issues

- Contract: `CONTRACT-QUEUE-001@1.0.0-draft.2`
- State: `DRAFT / REREVIEW_COMPLETE / READY_FOR_COORDINATING_MANAGER_DECISION`
- Contract SHA-256: `106ef0e5c4a58a6010d55f890ac852f7869e041baca963298e4af436e5aa5327` (unchanged)
- Reconciled current main: `9a28d72eb08303b6701bf7db6df622006991196a`
- Affected-owner re-review: `COMPLETE / 9_OF_9_RESPONSES_RECEIVED`
- Provider: `UNSELECTED`

| Correction / re-review issue | State | Closure boundary |
|---|---|---|
| A2-QUEUE Workflow-sequence review | `ACCEPTED` | Exact `EXECUTING_BUGGY` then `EXECUTING_FIXED` invariant passed renewed review. |
| Constraint-register structure | `VALID / 39_ROWS / 11_COLUMNS` | All stable IDs and required fields remain present. |
| Auth/Integration/Evaluation source fidelity | `COMPLETE / ACCEPTED_BY_A2_QUEUE` | Exact mappings and full constraint/evidence obligations for 7 Auth, 5 Integration, and 5 Evaluation rows passed final source review. |
| 1. Workflow attempt identity | `CORRECTED_IN_DRAFT_2 / REREVIEW_COMPLETE` | Confirmed run/step occurrence/kind/occurrence/zero-based attempt binding and Workflow-only creation/meaning. |
| 2. Checkpoint claim/fence scope | `CORRECTED_IN_DRAFT_2 / REREVIEW_COMPLETE` | Confirmed conditional producing claim/fence and Workflow checkpoint authority. |
| 3. One-repair maximum | `CORRECTED_IN_DRAFT_2 / REREVIEW_COMPLETE` | Confirmed Queue operations never alter/recreate the Workflow-owned `0..1` repair allowance. |
| 4. Workflow lifecycle versus Execution runtime | `CORRECTED_IN_DRAFT_2 / REREVIEW_COMPLETE` | Confirmed Workflow semantic ownership, Execution runtime ownership, and Queue transport-only ownership. |
| 5. Physical persistence versus Evidence semantics | `CORRECTED_IN_DRAFT_2 / REREVIEW_COMPLETE` | Confirmed Database-exclusive physical ownership, Evidence semantic ownership, commit-before-ack, and no DB-003. |
| 6. Producer-result identity and layered deduplication | `CORRECTED_IN_DRAFT_2 / REREVIEW_COMPLETE` | Confirmed stable Workflow-authorized result-slot identity, per-submission validation, separate canonicalizations, and layered owners. |
| 7. Heartbeat and renewal authority | `CORRECTED_IN_DRAFT_2 / REREVIEW_COMPLETE` | Confirmed Execution inputs, Queue renewal authority, Deployment transport/configuration, Security policy, and no signal-derived authority. |
| 8. Retry classification ownership | `CORRECTED_IN_DRAFT_2 / REREVIEW_COMPLETE` | Confirmed Queue transport categories, Workflow semantic classification, and Deployment configuration-only boundary. |
| 9. Local/test adapter isolation | `CORRECTED_IN_DRAFT_2 / REREVIEW_COMPLETE` | Confirmed clean-checkout/no-production-credential-or-state isolation and mandatory common conformance. |
| 10. Provider-adapter Security and operational mapping | `CORRECTED_IN_DRAFT_2 / REREVIEW_COMPLETE` | Confirmed encryption/access/identity/secret/admin mapping and minimum operational signal capability. |
| Affected-owner re-review | `RESOLVED / COMPLETE / 9_OF_9` | 9_OF_9 responses received: 1 ACCEPTED, 8 ACCEPTED_WITH_CONSTRAINTS, 0 REJECTED_WITH_REASON, 0 SPECIFICATION_CONFLICT. Normative Queue corrections required: NONE (NORMATIVE_CORRECTIONS_REQUIRED = NONE). |
| Stale current-main provenance wording | `RESOLVED / PROVENANCE_CORRECTED` | Current main consistently identified as `9a28d72eb08303b6701bf7db6df622006991196a` across all component status records. |

## Still unresolved after correction / downstream gates

| Issue | State / owner boundary |
|---|---|
| Coordinating-manager readiness decision | `PENDING / NEXT_GATE`; task `QUEUE-004-C7-COORDINATING-MANAGER-READINESS-DECISION-001`. |
| Final exact-head / current-main freshness | `PENDING_AT_READINESS_GATE`; required immediately before readiness/merge. |
| PR #24 ready/merge decision | `OPEN / DRAFT / NOT_READY / NOT_MERGED`. |
| Provider selection | `CONFIGURATION_VALUE_NOT_YET_SELECTED`. |
| DB-003 | `NOT_STARTED / UNAUTHORIZED`; no physical schema/design authorized. |
| Implementation evidence | `FUTURE_IMPLEMENTATION_EVIDENCE / NOT_YET_AVAILABLE`; requires separately authorized runtime work. |
| Release gates | `FUTURE_RELEASE_EVIDENCE / INPUTS_MISSING`; configuration, compatibility, Security, and Evaluation measurements required. |

No issue authorizes runtime, provider selection, application code, tests,
dependencies, migrations, workers, sandboxes, infrastructure, PR readiness or
merge, or DB-003.
