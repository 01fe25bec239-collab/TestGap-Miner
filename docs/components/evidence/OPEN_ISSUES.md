# Evidence Component Open Issues

## Overview

- **Date**: 2026-08-10
- **Component**: `A2-EVIDENCE — Evidence, Artefact, and Provenance Component Manager`
- **Contract**: `CONTRACT-EVIDENCE-001@1.0.0-draft.3`
- **Task ID**: `EVIDENCE-005A-FINAL-REREVIEW-HISTORY-RECONCILIATION-001-A3`
- **Parent Manager Task**: `EVIDENCE-005A-FINAL-REREVIEW-HISTORY-RECONCILIATION-001`
- **Status**: `RECONCILIATION_OPEN_ISSUES_UPDATED`
- **Current Contract-Review Blockers**: `NONE`
- **Unresolved Normative Consumer Corrections**: `NONE`
- **`ASSUMED`**: `NONE`

This document records unresolved contract inputs, pending owner decisions, and implementation details for `CONTRACT-EVIDENCE-001@1.0.0-draft.3`. CURRENT EVIDENCE CONTRACT-REVIEW BLOCKERS: `NONE`. UNRESOLVED NORMATIVE CONSUMER CORRECTIONS: `NONE`. No unresolved issue has been arbitrarily answered or invented in this draft. Future implementation and release requirements (`INT-EVID-001`, `INT-EVID-002`) are recorded below as nonblocking obligations.

---

## Logged Open Issues

### `ISSUE-EVID-001` — Exact Confidence Numerical Scale and Calibration Methodology

- **Description**: The exact numerical scale (e.g. 0.0–1.0 float vs integer percentage vs categorical rating) and statistical calibration formulas for confidence assessment fields remain unresolved.
- **Classification**: `external owner confirmation` (`A2-EVALUATION` / `A2-SECURITY`).
- **Temporary Contract Strategy**: High-level semantic structure `confidence_reference` supported in Section 16 without hardcoding a specific numeric scale.

---

### `ISSUE-EVID-002` — Standardization of Uncertainty Categories and Taxonomy

- **Description**: The formal enumeration of uncertainty categories requires owner standardization. `MODEL_HALLUCINATION_RISK`, `TEST_FLAKINESS`, `PARTIAL_EXECUTION`, `UNRESOLVED_DEPENDENCY`, and `AMBIGUOUS_SPECIFICATION` are `NON_NORMATIVE_EXAMPLES` only.
- **Classification**: `external owner confirmation` (`A2-EVALUATION` / `A2-EXECUTION`).
- **Temporary Contract Strategy**: Opaque, versioned `uncertainty_category` supported in Section 16 pending owner taxonomy definition; no example is frozen as normative.

---

### `ISSUE-EVID-003` — Security-Approved Cryptographic Integrity Policy

- **Description**: Security must provide or approve the allowed digest, cryptographic canonicalization, signature/MAC, scope, and key-custody policy. No algorithm is selected by this draft.
- **Classification**: `external owner confirmation` (`A2-SECURITY`).
- **Temporary Contract Strategy**: Parameterized `digest_algorithm` string attribute supported in `ArtefactReference` and `EvidenceIntegrity` (Section 11).

---

### `ISSUE-EVID-004` — Exact Artefact Retention Duration Policy per Logical Category

- **Description**: Specific retention durations (e.g., 30 days vs 90 days vs permanent) for candidate patches, compile logs, test stdout/stderr, and execution traces are not yet specified.
- **Classification**: `external owner confirmation` (`A2-SECURITY` / `A2-DEPLOYMENT`).
- **Temporary Contract Strategy**: Provider-neutral completeness and retention semantic states (`EXPIRED`, `DELETED_OR_TOMBSTONED`) supported without hardcoded durations (Section 20).

---

### `ISSUE-EVID-005` — Physical Object Storage Locator Format Abstraction

- **Description**: Standardized format for `storage_locator` strings (e.g., `s3://...` vs `urn:artefact:...` vs internal URI) when passed across service boundaries.
- **Classification**: `implementation detail` (`A2-DEPLOYMENT` / `A2-DATABASE`).
- **Temporary Contract Strategy**: Abstract `storage_locator` string field provided in `ArtefactReference` (Section 10.4).

---

### `ISSUE-EVID-006` — Execution Producer-Result Schema Structure & Multiplicity

- **Description**: Detailed schema and serialization of facts submitted under an A2-EXECUTION-owned `producer_result_id`. In `CONTRACT-EVIDENCE-001@1.0.0-draft.3`, `producer_result_id` is conditional at CandidateVersion level and phase-specific in ExecutionEvidence/EvidenceBundle.
- **Classification**: `external owner confirmation` (`A2-EXECUTION`).
- **Temporary Contract Strategy**: Evidence treats `producer_result_id` as an opaque producer-result reference and maps structured outcomes in Section 8 without redefining creation, slot semantics, or runner internals.

---

### `ISSUE-EVID-007` — Database Physical Schema Mapping & Milestone Allocation

- **Description**: PostgreSQL/SQLite table structures, JSONB column mappings, foreign key cascading rules, and indexing strategies for Evidence entities under future authorized Database milestones.
- **Classification**: `implementation detail` (`A2-DATABASE`).
- **Temporary Contract Strategy**: Kept strictly outside contract boundary; milestone allocation is exclusively owned by `A2-DATABASE`; `DB-003` remains `NOT_STARTED / NOT_AUTHORIZED` (Section 21).

---

### `ISSUE-EVID-008` — Backend OpenAPI Endpoint Schema Projections

- **Description**: REST API route definitions, query parameters, pagination, and JSON serialization schemas for fetching EvidenceBundles and EvidenceCards via HTTP.
- **Classification**: `implementation detail` (`A2-BACKEND`).
- **Temporary Contract Strategy**: Contract defines semantic content structures; HTTP route projections are owned by `A2-BACKEND`.

---

### `ISSUE-EVID-009` — UI EvidenceCard Component Visual Layout & Interactivity

- **Description**: Frontend component visual layout, tab navigation, diff rendering, and interactive controls for `EvidenceCard` presentation.
- **Classification**: `implementation detail` (`A2-UI`).
- **Temporary Contract Strategy**: Logical semantic projection defined in Section 15 without making UI layout assumptions.

---

### `ISSUE-EVID-010` — Quantitative Evaluation Gate Thresholds

- **Description**: Specific numerical thresholds for Evidence completeness pass rates and test coverage required to satisfy release quality gates.
- **Classification**: `release/Evaluation input` (`A2-EVALUATION`).
- **Temporary Contract Strategy**: Completeness states defined semantically (Section 12) without specifying quantitative release threshold numbers.

---

### `ISSUE-EVID-011` — Cross-Component Contract Compatibility Matrix & Rolling Upgrades

- **Description**: Protocol for handling minor version additions when microservices operate on different contract revisions during rolling system deployments.
- **Classification**: `external owner confirmation` (`A2-INTEGRATION`).
- **Temporary Contract Strategy**: Standard Major version fail-closed rule specified in Section 23.

---

### `ISSUE-EVID-012` — Evaluation Benchmark Dataset Manifest Versioning

- **Description**: Specific format and manifest distribution semantics for A2-EVALUATION benchmark dataset versioning referenced by `evaluation_benchmark_case_reference` and `evaluation_benchmark_manifest_version`.
- **Classification**: `external owner confirmation` (`A2-EVALUATION`).
- **Temporary Contract Strategy**: Evidence preserves `evaluation_benchmark_case_reference` and `evaluation_benchmark_manifest_version` as opaque provenance references without interpreting benchmark membership or dataset structure (Section 14.1).

---

### `ISSUE-EVID-013` — Auth Historical Actor Attribution Lifecycle Semantics

- **Description**: Specific A2-AUTH policies governing actor identity retention, pseudonymization, or historical attribution resolution after an actor is deprovisioned, suspended, or role-modified.
- **Classification**: `external owner confirmation` (`A2-AUTH`).
- **Temporary Contract Strategy**: Evidence preserves `human_actor_reference` as historical decision linkage only without treating it as current authentication, authorization, or permission (Section 18.2).

---

### `ISSUE-EVID-014` — Deployment Operational Resource Configuration Bounds & Validation Mechanics

- **Description**: Detailed schema format for passing deploy-time operational resource configuration (configured CPU limits, memory limits, disk/temp ceilings, process limits, filesystem quotas, log byte limits) from `A2-DEPLOYMENT` to `A2-EXECUTION` and representing them as opaque policy/config references in Evidence.
- **Classification**: `external owner confirmation` (`A2-DEPLOYMENT` / `A2-EXECUTION`).
- **Temporary Contract Strategy**: `A2-DEPLOYMENT` remains authoritative for operational runtime/resource configuration; `A2-EXECUTION` owns enforcement and fact production; `A2-SECURITY` owns Security policy meaning; `A2-EVIDENCE` preserves representation only without configuring or redefining limits (Sections 2.2, 8.1, 17.1).

---

### `ISSUE-EVID-015` / `INT-EVID-001` — Supported Version & Mixed-Version Compatibility Matrix

- **Description**: Requirement for a supported version and mixed-version compatibility matrix prior to multi-service system deployment and runtime implementation.
- **Classification**: `FUTURE IMPLEMENTATION / RELEASE OBLIGATION / NONBLOCKING FOR CURRENT CONTRACT ACCEPTANCE` (`A2-INTEGRATION`).
- **Temporary Contract Strategy**: Recorded per `INT-EVID-001` in `EVID-REREVIEW-INTEGRATION-002`. Does NOT block current Evidence contract acceptance or draft.3 freeze.

---

### `ISSUE-EVID-016` / `INT-EVID-002` — Rollout, Rollback & Historical Version Pinning Procedures

- **Description**: Requirement for rollout, rollback, and historical version pinning procedures prior to system release.
- **Classification**: `FUTURE IMPLEMENTATION / RELEASE OBLIGATION / NONBLOCKING FOR CURRENT CONTRACT ACCEPTANCE` (`A2-INTEGRATION`).
- **Temporary Contract Strategy**: Recorded per `INT-EVID-002` in `EVID-REREVIEW-INTEGRATION-002`. Does NOT block current Evidence contract acceptance or draft.3 freeze.
