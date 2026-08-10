# Evidence Component Decision Log

## Overview

- **Date**: 2026-08-10
- **Component**: `A2-EVIDENCE — Evidence, Artefact, and Provenance Component Manager`
- **Executor**: `A3-EVIDENCE — Evidence Contract Documentation Executor`
- **Task ID**: `EVIDENCE-005A-FINAL-REREVIEW-HISTORY-RECONCILIATION-001-A3`
- **Parent Manager Task**: `EVIDENCE-005A-FINAL-REREVIEW-HISTORY-RECONCILIATION-001`
- **Active Contract Version**: `CONTRACT-EVIDENCE-001@1.0.0-draft.3`
- **Active Contract SHA-256**: `27b464a952baa136a6f0b97bee7df77cab2fa13832d39445229e16e0f0a58ca5`
- **Baseline SHA**: `b93c0aa782fbc5136ba4999d3c4fb556c51ca635`
- **Status**: `FINAL_RECONCILIATION_DECISIONS_RECORDED`
- **`ASSUMED`**: `NONE`

---

## Logged Decisions

### `DEC-EVID-001` — Semantic Evidence Ownership vs Physical Persistence Separation

- **Decision**: `A2-EVIDENCE` exclusively owns the semantic definition, logical structures, data requirements, integrity meaning, and provenance invariants of Evidence. `A2-DATABASE` exclusively owns physical persistence (tables, models, migrations, indexes, CAS, locking).
- **Context & Rationale**: Prevents joint ownership confusion. `A2-EVIDENCE` specifies domain data semantics without dictating physical SQL schemas.
- **Boundary Label**: `AUTHORITATIVE_DECISION`.

---

### `DEC-EVID-002` — Contract Identification and Initial Version Fixing

- **Decision**: Fixed Contract ID as `CONTRACT-EVIDENCE-001` and initial draft version as `1.0.0-draft.1`.
- **Context & Rationale**: Establishes a stable reference point for consumer review requests across component managers.
- **Boundary Label**: `AUTHORITATIVE_DECISION`.

---

### `DEC-EVID-003` — Provider Neutrality and Storage Abstraction

- **Decision**: `CONTRACT-EVIDENCE-001` MUST NOT select cloud vendors, object-storage providers (S3, GCS, Azure, POSIX), database engines, queue systems, or framework libraries. All provider choices remain `UNSELECTED / CONFIGURATION_VALUE_NOT_YET_SELECTED`.
- **Context & Rationale**: Ensures the contract remains completely decoupled from vendor implementation details.
- **Boundary Label**: `AUTHORITATIVE_DECISION`.

---

### `DEC-EVID-004` — Strict Domain Identity Separation

- **Decision**: Enforce strict separation among twenty operational and domain identities (`run_id`, `workflow_attempt_id`, `queue_message_id`, `queue_delivery_id`, `claim_or_lease_id`, `producer_result_id`, `evidence_reference_id`, `candidate_patch_id`, `candidate_version_id`, `execution_evidence_id`, `evidence_bundle_id`, `evidence_card_id`, `artefact_manifest_id`, `artefact_id`, `evidence_integrity_id`, `evidence_failure_link_id`, `human_decision_id`, `human_decision_link_id`, `publication_identity`, `correlation_id`).
- **Context & Rationale**: Queue IDs, delivery IDs, producer-result IDs, Evidence domain IDs, link IDs, and storage locators MUST remain distinct. `evidence_reference_id` is Evidence-owned and is the opaque Queue-facing reference, not an alias for any Evidence object identity.
- **Boundary Label**: `AUTHORITATIVE_DECISION`.

---

### `DEC-EVID-005` — Canonical Evidence Content Ownership

- **Decision**: `A2-EVIDENCE` exclusively owns the definition of canonical Evidence content and payload equality. Queue transport duplicate delivery receipts or provider ACKs MUST NOT define canonical Evidence equality.
- **Context & Rationale**: Protects Evidence integrity from transport-level deduplication semantics.
- **Boundary Label**: `AUTHORITATIVE_DECISION`.

---

### `DEC-EVID-006` — Immutability of Accepted Evidence & Conflict Classification

- **Decision**: Finalized accepted Evidence MUST NOT be overwritten, updated in place, or modified. Submissions sharing an identity scope with an existing record but containing a different canonical digest MUST be classified as `CONFLICTING` and preserved separately. Last-write-wins (LWW) is strictly prohibited.
- **Context & Rationale**: Guarantees tamper resistance and full provenance auditability.
- **Boundary Label**: `AUTHORITATIVE_DECISION`.

---

### `DEC-EVID-007` — CandidateVersion Lineage & Bounded Repair Tracking

- **Decision**: Repaired candidates (`repair_level = 1`) receive distinct candidate-version semantics and maintain explicit parent linkage (`parent_candidate_version_id`) to initial candidates (`repair_level = 0`). `repair_level` is candidate-lineage metadata only. Overwriting prior candidate Evidence is prohibited.
- **Context & Rationale**: Preserves candidate history without enforcing Workflow repair policy. Workflow exclusively owns `repair_attempts_used`, constrained to `0..1` and changed only by valid entry to `REPAIRING`; Evidence does not own or modify it.
- **Boundary Label**: `AUTHORITATIVE_DECISION`.

---

### `DEC-EVID-008` — Dual-Phase Buggy / Fixed Execution Representation

- **Decision**: Evidence uses phase-specific `ExecutionEvidence` records with exactly one phase-appropriate result (`compile_result`, `buggy_execution_result`, or `fixed_execution_result`) and groups them under `EvidenceBundle`, supporting explicit unavailable, partial, or conflicting outcomes.
- **Context & Rationale**: Establishes a trustworthy regression testing baseline without inferring success from mere object presence.
- **Boundary Label**: `AUTHORITATIVE_DECISION`.

---

### `DEC-EVID-009` — Queue Opaque Reference Boundary

- **Decision**: Consumed merged `CONTRACT-QUEUE-001@1.0.0-draft.2`. `evidence_reference_id` is the Evidence-owned opaque Queue-facing reference and is distinct from every Evidence domain ID. Queue MUST NOT infer the referenced object's semantic type, transport Evidence/artefact bytes, or expose Evidence domain IDs as the Queue Evidence field. Required digest/integrity transport uses Queue's existing `integrity_metadata` boundary.
- **Context & Rationale**: Evidence resolves the reference under `CONTRACT-EVIDENCE-001`; tombstones prevent a historical reference from resolving to replacement content.
- **Boundary Label**: `CONSUMED_AUTHORITATIVE_BOUNDARY`.

---

### `DEC-EVID-010` — Workflow Lifecycle Boundaries

- **Decision**: Consumed merged `CONTRACT-WORKFLOW-001@1.0.0-draft.1`. Evidence records execution facts but MUST NOT create Workflow states, transition runs, authorize attempts, consume repair allowance, or authorize second repairs.
- **Context & Rationale**: `A2-AGENT-WORKFLOW` exclusively owns lifecycle state transitions and repair allowances.
- **Boundary Label**: `CONSUMED_AUTHORITATIVE_BOUNDARY`.

---

### `DEC-EVID-011` — Database Physical Persistence Boundary

- **Decision**: `A2-DATABASE` exclusively owns physical persistence, SQL tables, ORM models, Alembic migrations, column types, constraints, and indexes. `DB-003` remains `NOT_STARTED / NOT_AUTHORIZED`.
- **Context & Rationale**: No physical database structures are created or selected in this contract draft task.
- **Boundary Label**: `CONSUMED_AUTHORITATIVE_BOUNDARY`.

---

### `DEC-EVID-012` — Security External Policy Boundary

- **Decision**: `A2-SECURITY` exclusively owns secret redaction policy, sensitive data classification, allowed digest, cryptographic canonicalization, signature/MAC and scope policy, retention security policy, and key custody. No algorithm is selected. Evidence objects record references to Security decisions without inventing policy.
- **Context & Rationale**: Keeps security policy centralized under `A2-SECURITY`.
- **Boundary Label**: `CONSUMED_AUTHORITATIVE_BOUNDARY`.

---

### `DEC-EVID-013` — Mandatory Consumer Review Prior to Acceptance

- **Decision**: Prepared formal consumer review requests for ten component managers in `DEPENDENCY_REQUESTS.md` with status `PREPARED / NOT_EXECUTED`. Silence from any component manager is explicitly NOT acceptance.
- **Context & Rationale**: Ensures rigorous cross-component review before freezing the contract.
- **Boundary Label**: `AUTHORITATIVE_DECISION`.

---

### `DEC-EVID-014` — Human Decision Boundary Alignment

- **Decision**: Workflow owns lifecycle disposition semantics (`APPROVED`, `REJECTED`, `DISMISSED`, `OUT_OF_SCOPE`, `REGENERATION_REQUESTED`); Auth owns human actor identity; Evidence owns the human-decision semantic record/linkage boundary; Database owns physical persistence.
- **Context & Rationale**: Consumes the merged Workflow boundary without assigning generic human-decision identity to Auth or Workflow.
- **Boundary Label**: `CONSUMED_AUTHORITATIVE_BOUNDARY`.

---

### `DEC-EVID-015` — Availability and Integrity Orthogonality

- **Decision**: `AVAILABLE` means content is present and accessibly resolvable. It does not imply `VERIFIED`; `availability_state` and `integrity_state` are independent. After intentional byte deletion, availability is `DELETED_OR_TOMBSTONED` and current integrity is `DELETED`; any prior verification result is historical tombstone metadata only.
- **Context & Rationale**: Prevents content access from being mistaken for verification and keeps deletion semantics consistent across the artefact, integrity, and retention sections.
- **Boundary Label**: `AUTHORITATIVE_DECISION`.

---

### `DEC-EVID-016` — Producer-Result Semantic Fidelity

- **Decision**: `producer_result_id` is an A2-EXECUTION-owned opaque reference to one Workflow-authorized semantic result slot/submission for one Workflow attempt and result phase. Evidence does not redefine its creation, stability, or slot semantics.
- **Context & Rationale**: Preserves the merged Queue/Execution/Workflow meaning and prevents semantic drift in producer-result identity.
- **Boundary Label**: `CONSUMED_AUTHORITATIVE_BOUNDARY`.

---

### `DEC-EVID-017` — Provider-Neutral Manifest and Semantic Link Structures

- **Decision**: `ArtefactManifest`, `EvidenceFailureLink`, and `HumanDecisionLink` have explicit Evidence-owned identities and bounded semantic fields for membership, provenance, integrity, timestamps, and applicable candidate/execution/Workflow references. No provider, physical Database mapping, or transaction mechanic is selected.
- **Context & Rationale**: Makes the logical contract implementable by consumers while preserving Workflow disposition/lifecycle ownership, Auth actor-identity ownership, Evidence semantic record/link ownership, and Database physical-persistence ownership.
- **Boundary Label**: `AUTHORITATIVE_DECISION`.

---

### `DEC-EVID-018` — Uncertainty Taxonomy Remains Unfrozen

- **Decision**: `uncertainty_category` remains opaque and versioned pending A2-EVALUATION/A2-EXECUTION confirmation. Named categories in Section 16 are `NON_NORMATIVE_EXAMPLES` only.
- **Context & Rationale**: Prevents an unreviewed taxonomy from becoming normative by documentation accident.
- **Boundary Label**: `AUTHORITATIVE_DECISION`.

---

### `DEC-EVID-019` — Authoritative Contract Version Resolution to `CONTRACT-EVIDENCE-001@1.0.0-draft.2` (Superseding `1.1.0-draft.1`)

- **Decision**: Agent 1 authoritatively resolved the EVIDENCE-003 version escalation and selected `CONTRACT-EVIDENCE-001@1.0.0-draft.2` as the active corrected draft revision (superseding intermediate candidate `1.1.0-draft.1`). `A2-EVIDENCE` consumed, recorded, and applied this authoritative decision; `A2-EVIDENCE` did NOT independently choose the version. Historical reviewed draft `CONTRACT-EVIDENCE-001@1.0.0-draft.1` (SHA-256: `81c967531fb814f981380df98bdb06dd17c9ccee0f2c669faf6e94995dd87fc1`) MUST be retained as historical review provenance in durable records. Superseded intermediate candidate `CONTRACT-EVIDENCE-001@1.1.0-draft.1` (SHA-256: `e052e6fe4901bee8ff938c625e2a5f5d461f076f3467071da944d5935ff0b4c5`) is recorded as intermediate review provenance. New authoritative corrected contract SHA-256 is `793975666aa7935c5689143a3c9c68f4adb76106e0c2089debab606d2841801b`.
- **Context & Rationale**: Agent 1 authoritatively resolved the version escalation based on the rationale that: (1) source contract `1.0.0-draft.1` was not `FINAL_ACCEPTED`; (2) corrections occurred before acceptance of intended `1.0.0`; (3) BENCHMARK provenance is conditionally required and must not be described as merely a Minor additive OPTIONAL field; and (4) therefore the corrected candidate is the next draft iteration: `1.0.0-draft.2`.
- **Boundary Label**: `CONSUMED_AUTHORITATIVE_BOUNDARY`.

---

### `DEC-EVID-020` — EVID-EVAL-CORRECTION-001 Evaluation Benchmark Provenance Binding

- **Decision**: For BENCHMARK-originated Evidence, add an immutable, versioned, A2-EVALUATION-owned benchmark provenance binding (`evaluation_benchmark_case_reference` and `evaluation_benchmark_manifest_version`) sufficient to identify the exact Evaluation benchmark case and immutable benchmark manifest version. Non-BENCHMARK Evidence MAY mark it `NOT_APPLICABLE`.
- **Context & Rationale**: Preserves benchmark traceability as provenance only. A2-EVIDENCE MUST NOT define benchmark membership policy, infer membership from outputs, define population selection, reinterpret the reference, invent future CONTRACT-EVAL-001 vocabulary, define scoring formulas, metric denominators, or release thresholds.
- **Boundary Label**: `AUTHORITATIVE_DECISION`.

---

### `DEC-EVID-021` — EXEC-EVID-CORR-001 Producer-Result Placement & Multiplicity Correction

- **Decision**: `producer_result_id` is CONDITIONAL at `CandidatePatch` / `CandidateVersion` level. A CandidateVersion MUST be creatable/finalizable before execution without requiring A2-EXECUTION to mint a result identity prior to execution. In `EvidenceBundle`, phase-specific `ExecutionEvidence` records retain their phase `producer_result_id` references; aggregate EvidenceBundle preserves applicable producer_result_id references for all included execution phases.
- **Context & Rationale**: Prevents requiring result pre-allocation prior to execution while preserving phase-specific execution producer result traceability.
- **Boundary Label**: `AUTHORITATIVE_DECISION`.

---

### `DEC-EVID-022` — EXEC-EVID-CORR-002 Extensible Resource Limit Representation

- **Decision**: `resource_limit_outcome` is provider-neutral and extensible, capable of preserving applicable A2-EXECUTION runtime facts for CPU, memory, disk/temporary workspace, process count, file-count/filesystem quota, output/log byte limits, and other approved resource ceilings. `RESOURCE_LIMIT_EXCEEDED` definition updated accordingly. Policy denials (network, filesystem-access, tool, Security) MUST NOT be classified automatically as generic resource exhaustion.
- **Context & Rationale**: Ensures runtime resource limit tracking is extensible beyond CPU/memory without conflating operational or security access denials with resource exhaustion.
- **Boundary Label**: `AUTHORITATIVE_DECISION`.

---

### `DEC-EVID-023` — Database Milestone Allocation Boundary Correction

- **Decision**: Remove any wording allocating Evidence persistence exclusively to `DB-003`. Replace with explicit boundary stating `A2-DATABASE` exclusively owns physical database mappings under separately authorized Database tasks. CONTRACT-EVIDENCE-001 MUST NOT assign any Evidence structure, identifier, relationship, table, constraint, or persistence responsibility to `DB-003`, `DB-004`, `DB-005`, `DB-006`, or any other Database milestone.
- **Context & Rationale**: Database milestone allocation is entirely A2-DATABASE-owned. `DB-003` remains `NOT_STARTED / NOT_AUTHORIZED`.
- **Boundary Label**: `AUTHORITATIVE_DECISION`.

---

### `DEC-EVID-024` — AUTH-EVID-CORR-001 Human Actor Identity & Authorization Clarification

- **Decision**: Preserve `HumanDecisionLink` field shape. Clarify that `human_actor_reference` is an opaque reference to an A2-AUTH-owned HUMAN actor identity. Historical actor attribution DOES NOT equal current authentication, current authorization, or permission to repeat the action. A HumanDecisionLink MUST NOT independently authorize actions, workflow progression, or publication, nor restore expired/revoked authority. Storing credential or session secrets in Evidence is strictly PROHIBITED.
- **Context & Rationale**: Preserves clear separation between historical provenance attribution (Evidence) and active authentication/authorization enforcement (Auth).
- **Boundary Label**: `AUTHORITATIVE_DECISION`.

---

### `DEC-EVID-025` — Consumer Review Wave Recording & Focused Rereview Scope

- **Decision**: Record exact dispositions for all 11 component consumers. Historical rejected/conflict responses (`A2-EVALUATION`, `A2-EXECUTION`, `A2-DATABASE`) remain historical review evidence until rereviewed. Prepare 7 READ_ONLY focused rereview packets (`A2-EVALUATION`, `A2-EXECUTION`, `A2-DATABASE`, `A2-AUTH`, `A2-AGENT-WORKFLOW`, `A2-QUEUE`, `A2-INTEGRATION`). Preserve 4 unaffected consumers (`A2-DEPLOYMENT`, `A2-SECURITY`, `A2-BACKEND`, `A2-UI`). Silence is explicitly NOT acceptance.
- **Context & Rationale**: Governs the consumer rereview process cleanly and transparently without re-requesting reviews from unaffected owners.
- **Boundary Label**: `AUTHORITATIVE_DECISION`.

---

### `DEC-EVID-026` — Deployment Operational Runtime / Resource Configuration Ownership Clarification (`EXEC-EVID-CORR-002-C1`)

- **Decision**: `A2-DEPLOYMENT` remains authoritative for operational runtime/resource configuration (configured CPU limits, memory limits, disk/temporary workspace ceilings, process-count limits, filesystem/file-count quotas, output/log byte limits, runtime resource-policy values, deploy-time operational resource configuration, and approved operational runtime ceilings). `A2-EXECUTION` owns runtime enforcement, observation, production of resulting runtime/resource facts, and Execution-owned resource-limit facts/references. `A2-SECURITY` owns Security policy meaning, Security-policy denial meaning, Security classification, and Security-owned policy interpretation. `A2-EVIDENCE` owns ONLY semantic representation of resulting runtime/resource facts, Evidence-side representation of opaque policy/config references, and Evidence-side provenance/integrity/completeness semantics. `A2-EVIDENCE` MUST NOT select, redefine, or configure resource limits, own deploy-time operational configuration, become authoritative for runtime resource configuration or Execution enforcement, or reinterpret Security-policy denial as generic resource exhaustion.
- **Context & Rationale**: Resolves blocker `EXEC-EVID-CORR-002-C1` raised by `A2-INTEGRATION` in `EVID-REREVIEW-INTEGRATION-001` during draft.2 focused rereview.
- **Boundary Label**: `AUTHORITATIVE_DECISION`.

---

### `DEC-EVID-027` — Version Advance to `CONTRACT-EVIDENCE-001@1.0.0-draft.3`

- **Decision**: Advance active corrected candidate version from `CONTRACT-EVIDENCE-001@1.0.0-draft.2` (SHA-256: `793975666aa7935c5689143a3c9c68f4adb76106e0c2089debab606d2841801b`) to `CONTRACT-EVIDENCE-001@1.0.0-draft.3` (SHA-256: `27b464a952baa136a6f0b97bee7df77cab2fa13832d39445229e16e0f0a58ca5`). Historical references to `1.0.0-draft.1` and `1.0.0-draft.2` remain historically accurate.
- **Context & Rationale**: Pre-final-acceptance correction cycle version advance for task `EVIDENCE-004-DEPLOYMENT-RESOURCE-OWNERSHIP-CORRECTION-001`.
- **Boundary Label**: `AUTHORITATIVE_DECISION`.

---

### `DEC-EVID-028` — Draft 3 Consumer Review Gate Completion & Contract Acceptance

- **Decision**: Consumer review gate for `CONTRACT-EVIDENCE-001@1.0.0-draft.3` (SHA-256: `27b464a952baa136a6f0b97bee7df77cab2fa13832d39445229e16e0f0a58ca5`) is `COMPLETE`. All three draft.3 focused rereview packets are completed (`EVID-REREVIEW-DEPLOYMENT-002`: `ACCEPTED`, `EVID-REREVIEW-EXECUTION-002`: `ACCEPTED`, `EVID-REREVIEW-INTEGRATION-002`: `ACCEPTED_WITH_CONSTRAINTS`). All normative correction blockers (including `EXEC-EVID-CORR-002-C1`) are `RESOLVED`. UNRESOLVED NORMATIVE CORRECTIONS: `NONE`. UNRESOLVED CONSUMER-REVIEW BLOCKERS: `NONE`. Contract final state is `ACCEPTED_CONTRACT_DRAFT` / `READY_FOR_USER_MANAGED_GIT_LIFECYCLE` / `NOT_RUNTIME_IMPLEMENTED` / `NOT_PERSISTENCE_IMPLEMENTED`. Integration constraints `INT-EVID-001` (supported version and mixed-version compatibility matrix) and `INT-EVID-002` (rollout, rollback, and historical version pinning) are recorded as nonblocking future implementation/release obligations and are NOT current contract blockers. This decision does NOT authorize runtime implementation, persistence implementation, DB-003, or release.
- **Context & Rationale**: Completes task `EVIDENCE-005A-FINAL-REREVIEW-HISTORY-RECONCILIATION-001` by recording final consumer review acceptance and clearing all active review blockers while preserving full historical review provenance.
- **Boundary Label**: `AUTHORITATIVE_DECISION`.
