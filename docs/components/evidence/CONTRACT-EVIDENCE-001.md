# CONTRACT-EVIDENCE-001 — Evidence, Artefact, and Provenance Contract

## 1. Metadata and normative scope

| Field | Value |
|---|---|
| Contract ID | `CONTRACT-EVIDENCE-001` |
| Version | `1.0.0-draft.3` |
| Status | `DRAFT_FOR_FOCUSED_CONSUMER_REREVIEW / NOT_RUNTIME_IMPLEMENTED / NOT_PERSISTENCE_IMPLEMENTED` |
| Owner | `A2-EVIDENCE — Evidence, Artefact, and Provenance Component Manager` |
| Executor | `A3-EVIDENCE — Evidence Contract Documentation Executor` |
| Manager Task | `EVIDENCE-004-DEPLOYMENT-RESOURCE-OWNERSHIP-CORRECTION-001` |
| Execution Task | `EVIDENCE-004-DEPLOYMENT-RESOURCE-OWNERSHIP-CORRECTION-001-A3` |
| Baseline SHA | `b93c0aa782fbc5136ba4999d3c4fb556c51ca635` |
| Branch | `agent2/evidence-contract-001` |
| Worktree | `/Users/omkar/Documents/TestGap-Miner-wt-evidence-contract-001` |
| Consumes Contracts | `CONTRACT-WORKFLOW-001@1.0.0-draft.1` (merged), `CONTRACT-QUEUE-001@1.0.0-draft.2` (merged) |
| Physical Persistence | `A2-DATABASE exclusively owns physical persistence; DB-003 remains NOT_STARTED / NOT_AUTHORIZED` |
| Provider Selection | `UNSELECTED / CONFIGURATION_VALUE_NOT_YET_SELECTED` |
| Runtime Implementation | `NOT_IMPLEMENTED / NOT_TESTED / NOT_AUTHORIZED_BY_THIS_DRAFT` |

Normative terms **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are used in accordance with RFC 2119.

This contract defines logical, semantic, provider-neutral, implementation-neutral, and persistence-neutral Evidence requirements for TestGap-Miner.

It **MUST NOT** select:
- SQL tables, ORM classes, Database column names, indexes, migrations, physical constraints, or transaction mechanics;
- Queue transport provider or Queue delivery engine;
- Object-storage provider, cloud vendor, filesystem layout, or bucket architecture;
- Secret-redaction implementation, encryption key custody, or Security retention values;
- Runtime framework, container runtime, shell execution model, or sandbox implementation.

---

## 2. Authoritative ownership model

The contract explicitly defines and enforces component boundaries across TestGap-Miner.

### 2.1 A2-EVIDENCE ownership

`A2-EVIDENCE` exclusively owns the semantic definition, logical structure, integrity meaning, and provenance invariants of Evidence:

1. **Evidence-domain identifiers**: Logical identity semantics for EvidenceReferences, EvidenceBundles, EvidenceCards, ArtefactManifests, ArtefactReferences, ExecutionEvidence, CandidatePatches, CandidateVersions, EvidenceIntegrity, EvidenceFailureLinks, HumanDecision records, and HumanDecisionLinks.
2. **Candidate-patch Evidence semantics**: Representation and proof of candidate patches, including generation provenance, patch-content digests, changed-file manifests, test-only scope, and repair lineage.
3. **Candidate-version lineage**: Formal candidate-lineage metadata distinguishing initial candidates (`repair_level = 0`) from repaired candidates (`repair_level = 1`) and preserving parent-child relationships without overwriting prior candidate Evidence. This metadata does not enforce Workflow repair policy.
4. **Compile Evidence representation**: Evidence representation for compilation outcomes, build logs, compiler diagnostics, and build tool metadata supplied by `A2-EXECUTION`.
5. **Buggy-revision execution Evidence representation**: Evidence representation for test suite execution outcomes against the target buggy source revision.
6. **Fixed/reference-revision execution Evidence representation**: Evidence representation for test suite execution outcomes against the fixed or reference source revision.
7. **Execution-attempt ↔ Evidence linkage**: Semantic linkage connecting execution runner facts to formal Evidence objects.
8. **Failure Evidence**: Representation and attribution of compilation failures, execution test failures, timeouts, resource breaches, runner errors, flake indications, and integrity failures.
9. **EvidenceCard semantics**: Bounded, human-review-facing semantic projection of an EvidenceBundle.
10. **EvidenceBundle semantics**: Authoritative, aggregate semantic collection of all Evidence objects, execution facts, artefacts, and provenance metadata associated with a run or attempt.
11. **ArtefactManifest semantics**: Logical manifest grouping all associated output files, patches, logs, and execution traces.
12. **Immutable ArtefactReference semantics**: Immutable logical references to underlying stored artefacts, including digests, byte sizes, media types, and availability states.
13. **Evidence checksum/digest metadata semantics**: Logical digest fields and canonicalization scope definitions.
14. **Evidence integrity meaning**: Semantic classification of Evidence verification states (`VERIFIED`, `UNVERIFIABLE`, `CORRUPT`, `TAMPERED`, `MISSING`, `DELETED`).
15. **Evidence provenance**: Comprehensive end-to-end traceability linking Evidence objects back to originating runs, requests, Workflow attempts, Queue messages, execution runners, source repositories, models, prompt templates, and contract versions.
16. **Confidence and uncertainty Evidence fields**: Provider-neutral semantic structures representing confidence assessments, uncertainty flags, and uncertainty categories.
17. **Evidence availability**: Semantic representation of artefact and Evidence payload availability (`AVAILABLE`, `UNAVAILABLE`, `EXPIRED`, `REDACTED`, `DELETED_OR_TOMBSTONED`).
18. **Evidence completeness**: Normative seven-state completeness vocabulary (`COMPLETE`, `PARTIAL`, `UNAVAILABLE`, `INVALID`, `CONFLICTING`, `REDACTED`, `DELETED_OR_TOMBSTONED`).
19. **Evidence conflicts**: Classification rules when multiple Evidence submissions occur under the same identity scope.
20. **Evidence ↔ human-decision linkage**: Semantic record/linkage associating reviewed Evidence versions with Workflow-owned lifecycle dispositions (`APPROVED`, `REJECTED`, `DISMISSED`, `OUT_OF_SCOPE`, `REGENERATION_REQUESTED`) and Auth-owned human actor identities.
21. **Evidence contract compatibility/versioning**: Rules governing breaking vs non-breaking contract changes and version evolution.
22. **Canonical Evidence content**: Authoritative definition of canonical Evidence payload equality.
23. **Evidence duplicate/conflict classification**: Classification of incoming Evidence payloads into duplicate convergence vs conflicting submissions.
24. **Evidence semantic finalization**: State rules under which Evidence becomes immutable and finalized.
25. **Evidence deletion/tombstone semantic state**: Meaning and invariants governing deleted, expired, or tombstoned Evidence records.

### 2.2 Unowned boundaries (delegated to component owners)

`A2-EVIDENCE` **MUST NOT** make decisions on behalf of other component managers or answer unresolved external policy questions:

- **A2-AGENT-WORKFLOW**: Exclusively owns run lifecycle states, state transitions, Workflow attempt authorization, repair allowance enforcement, retry versus repair semantics, cancellation meaning, terminality, accepted-result transitions, and human-review state effects.
- **A2-QUEUE**: Exclusively owns publication transport, delivery/redelivery mechanics, Queue message/delivery identity, claim/lease transport semantics, transport retry, acknowledgement eligibility, and dead-letter transport.
- **A2-EXECUTION**: Exclusively owns worker/runtime behavior, sandbox isolation, compile/test execution, shell command building, timeout enforcement, runtime enforcement of configured resource limits, observation of runtime behavior, production of resulting runtime/resource facts, resulting Execution-owned resource-limit facts/references, producer-result production, raw execution facts, and stdout/stderr generation.
- **A2-DATABASE**: Exclusively owns physical persistence, SQL tables, ORM models, database migrations, column names, physical data types, foreign keys, indexes, transactions, locking, compare-and-set (CAS), and physical fencing enforcement. `DB-003` remains `NOT_STARTED / NOT_AUTHORIZED`.
- **A2-DEPLOYMENT**: Exclusively owns operational runtime/resource configuration authority (including configured CPU limits, memory limits, disk/temporary workspace ceilings, process-count limits, filesystem/file-count quotas, output/log byte limits, runtime resource-policy/configuration values, deploy-time operational resource configuration, and other approved operational runtime ceilings), physical object-storage provisioning, cloud/provider selection (S3, GCS, Azure Blob, Supabase, local filesystem), storage bucket/container infrastructure, backup/recovery systems, and deployed storage paths.
- **A2-SECURITY**: Exclusively owns secret-redaction policy, sensitive-data classification, public-disclosure policy, retention-security policy, allowed digest, cryptographic canonicalization, signature/MAC and scope policy, encryption/key-custody policy, Security policy meaning, Security-policy denial meaning, Security classification, Security-owned policy interpretation, and Security-event policy/severity.
- **A2-UI**: Exclusively owns Evidence rendering, layout, styling, user interaction, and visual component presentation.
- **A2-EVALUATION**: Exclusively owns scoring formulas, benchmark metrics, quality gates, and release evaluation thresholds.
- **A2-BACKEND**: Exclusively owns API routes, HTTP status codes, transport serialization, endpoint authentication, and request handling.
- **A2-INTEGRATION**: Exclusively owns cross-contract release compatibility orchestration, deployment matrix verification, and system-wide integration testing.

`A2-EVIDENCE` owns ONLY the semantic representation of resulting runtime/resource facts, Evidence-side representation of opaque policy/config references, and Evidence-side provenance/integrity/completeness semantics for those facts. `A2-EVIDENCE` **MUST NOT** select resource limits, redefine resource limits, configure resource limits, own deploy-time operational configuration, become authoritative for runtime resource configuration, become authoritative for Execution enforcement, or reinterpret Security-policy denial as generic resource exhaustion.

---

## 3. Contract terminology and logical identities

This contract defines provider-neutral semantic structures and logical identity names.

### 3.1 Logical semantic structures

| Structure | Description | Logical Identifier |
|---|---|---|
| `EvidenceReference` | Evidence-owned opaque Queue-facing binding to an appropriate Evidence-owned object; Queue cannot infer the object's semantic type from the reference. | `evidence_reference_id` |
| `EvidenceBundle` | Authoritative aggregate/container for Evidence, phase-specific execution facts, artefacts, and provenance for a run/attempt; completeness is classified separately by `EvidenceCompleteness`. | `evidence_bundle_id` |
| `EvidenceCard` | Bounded, human-review-facing semantic projection of an `EvidenceBundle`. | `evidence_card_id` |
| `CandidatePatch` | Semantic representation of a generated test-only candidate code patch. | `candidate_patch_id` |
| `CandidateVersion` | Versioned instance of a candidate patch in the lineage tracking system. | `candidate_version_id` |
| `ExecutionEvidence` | Semantic representation of compilation and test execution facts. | `execution_evidence_id` |
| `ArtefactManifest` | Logical manifest of all files, logs, patches, and traces associated with Evidence. | `artefact_manifest_id` |
| `ArtefactReference` | Immutable logical reference to an individual stored artefact. | `artefact_id` |
| `EvidenceIntegrity` | Cryptographic digest and verification metadata for an Evidence object or artefact. | `evidence_integrity_id` |
| `EvidenceCompleteness` | Semantic completeness classification enum/structure. | N/A (State Enum) |
| `EvidenceFailureLink` | Attributable linkage connecting Evidence to specific failure categories. | `evidence_failure_link_id` |
| `HumanDecision` | Evidence-owned semantic record of a human review decision; Workflow owns disposition meaning and Auth owns actor identity. | `human_decision_id` |
| `HumanDecisionLink` | Semantic linkage connecting reviewed Evidence to human review actions. | `human_decision_link_id` |

### 3.2 Canonical logical identifier names

The following names are normative logical contract identifiers only:
- `evidence_reference_id`
- `evidence_bundle_id`
- `evidence_card_id`
- `candidate_patch_id`
- `candidate_version_id`
- `execution_evidence_id`
- `artefact_manifest_id`
- `artefact_id`
- `evidence_integrity_id`
- `evidence_failure_link_id`
- `human_decision_id`
- `human_decision_link_id`

`evidence_reference_id` is generated and owned by `A2-EVIDENCE` as the opaque Queue-facing reference. It is distinct from `evidence_bundle_id`, `evidence_card_id`, `artefact_manifest_id`, `artefact_id`, and `execution_evidence_id`; none of those domain identifiers may substitute for it in a Queue envelope.

These names **MUST NOT** be mapped to physical SQL columns, ORM attributes, or database types within this contract. `A2-DATABASE` exclusively owns all physical database mappings under separately authorized Database tasks. `CONTRACT-EVIDENCE-001` **MUST NOT** assign any Evidence structure, identifier, relationship, table, constraint, or persistence responsibility to `DB-003`, `DB-004`, `DB-005`, `DB-006`, or any other Database milestone. Database milestone allocation is entirely `A2-DATABASE`-owned and governed by the authoritative Database manager plan and Database durable records. If a future separately authorized Database task consumes an Evidence-owned logical identity/reference, `A2-DATABASE` determines its physical representation while preserving Evidence semantic identity, provenance, and immutability.

---

## 4. Identity separation

The Evidence contract enforces strict domain separation among distinct operational and domain identifiers across TestGap-Miner.

### 4.1 Separation matrix

```
+-------------------------------------------------------------------------------+
|                           TESTGAP-MINER IDENTITIES                            |
+-----------------------------------+-------------------------------------------+
| Identifier                        | Owning Component Boundary                 |
+-----------------------------------+-------------------------------------------+
| run_id                            | A2-AGENT-WORKFLOW                         |
| workflow_attempt_id               | A2-AGENT-WORKFLOW                         |
| queue_message_id                  | A2-QUEUE                                  |
| queue_delivery_id                 | A2-QUEUE                                  |
| claim_or_lease_id                 | A2-QUEUE                                  |
| producer_result_id                | A2-EXECUTION                              |
| evidence_reference_id             | A2-EVIDENCE                               |
| candidate_patch_id                | A2-EVIDENCE                               |
| candidate_version_id              | A2-EVIDENCE                               |
| execution_evidence_id             | A2-EVIDENCE                               |
| evidence_bundle_id                | A2-EVIDENCE                               |
| evidence_card_id                  | A2-EVIDENCE                               |
| artefact_manifest_id              | A2-EVIDENCE                               |
| artefact_id                       | A2-EVIDENCE                               |
| evidence_integrity_id             | A2-EVIDENCE                               |
| evidence_failure_link_id          | A2-EVIDENCE                               |
| human_decision_id                 | A2-EVIDENCE; physical: A2-DATABASE         |
| human_decision_link_id            | A2-EVIDENCE                               |
| publication_identity              | A2-QUEUE                                  |
| correlation_id                    | Cross-component Tracing                   |
+-----------------------------------+-------------------------------------------+
```

### 4.2 Non-conflation rules

To prevent domain coupling and identity conflation errors, the following invariants are normative:

1. **Queue Message ID is not Evidence ID**: A Queue `queue_message_id` identifies a transport envelope; it **MUST NOT** be used as an `evidence_bundle_id` or `execution_evidence_id`.
2. **Delivery ID is not ExecutionEvidence ID**: A Queue `queue_delivery_id` represents a specific transport delivery attempt; it **MUST NOT** be used as an `execution_evidence_id`.
3. **Producer Result ID is not Evidence ID**: An A2-EXECUTION-owned `producer_result_id` identifies one Workflow-authorized semantic result slot/submission for one Workflow attempt and result phase. Evidence treats it as an opaque producer-result reference, **MUST NOT** substitute it for an Evidence identity, and **MUST NOT** redefine its creation or slot semantics.
4. **Correlation ID is not Evidence ID**: Tracing `correlation_id` values correlate logs across systems; they **MUST NOT** serve as primary Evidence keys.
5. **Artefact Storage Locator is not Artefact Identity**: Physical object storage locators (e.g. S3 URIs, file paths) identify physical bytes; they **MUST NOT** be equated with logical `artefact_id`.
6. **Signed/Download URL is not Artefact Identity**: Temporary pre-signed download URLs are transient access mechanisms; they **MUST NOT** represent `artefact_id`.
7. **Provider Receipt is not Evidence Identity**: Cloud provider receipts or Queue publication ACKs **MUST NOT** be used as Evidence identifiers.
8. **Queue Evidence Reference is distinct from Evidence domain identity**: `evidence_reference_id` is the only Evidence-specific Queue envelope reference. It **MUST NOT** be treated as `evidence_bundle_id`, `evidence_card_id`, `artefact_manifest_id`, `artefact_id`, or `execution_evidence_id`.

---

## 5. Queue contract compatibility

This contract consumes merged `CONTRACT-QUEUE-001@1.0.0-draft.2` and enforces its accepted boundaries.

### 5.1 Opaque Evidence reference boundary

In compliance with `CONTRACT-QUEUE-001`:
1. The only Evidence-specific field allowed in a Queue envelope is the optional, bounded `evidence_reference_id` generated and owned by `A2-EVIDENCE`.
2. Queue treats `evidence_reference_id` as opaque and **MUST NOT** infer whether it resolves to an `EvidenceBundle`, `EvidenceCard`, `ArtefactManifest`, `ArtefactReference`, `ExecutionEvidence`, or another Evidence-owned semantic object.
3. `A2-EVIDENCE` resolves and binds `evidence_reference_id` to the accepted-result/provenance context and appropriate current Evidence-owned object under this contract.
4. Content digest and integrity transport, where required, **MUST** use Queue's existing `integrity_metadata` boundary; this contract does not add a Queue field.
5. Queue payloads **MUST NOT** transport:
   - Evidence raw bytes;
   - Artefact content bytes;
   - Raw patch files;
   - Full stdout/stderr logs;
   - Raw source code repositories;
   - Model prompts or completions;
   - Authentication credentials or tokens.

Queue **MUST NOT** transport Evidence or artefact bytes, and Queue envelope fields **MUST NOT** directly expose `evidence_bundle_id`, `evidence_card_id`, `artefact_manifest_id`, `artefact_id`, or `execution_evidence_id` as the Evidence reference.

### 5.2 Producer-result and transport layering

The multi-component processing pipeline is layered as follows:
- **A2-EXECUTION**: Produces execution facts and owns `producer_result_id` for one Workflow-authorized semantic result slot/submission for one Workflow attempt and result phase.
- **A2-AGENT-WORKFLOW**: Evaluates semantic result acceptance for lifecycle progression.
- **A2-EVIDENCE**: Assigns Evidence identity, constructs canonical Evidence payloads, classifies duplicates/conflicts, and finalizes Evidence.
- **A2-QUEUE**: Handles duplicate transport convergence and message delivery redelivery.
- **A2-DATABASE**: Enforces physical uniqueness, locking, CAS, and relational transactions.
- **A2-SECURITY**: Defines the allowed digest, cryptographic canonicalization, signature/MAC and scope policy, and secret redaction.

Queue **MUST NOT** define canonical Evidence equality or evaluate Evidence content.

### 5.3 Commit-before-ack boundary

Where governing component contracts require durable Evidence retention before Queue processing completes:
- Semantic Evidence finalization and durable artefact reference records **MUST** be complete prior to Queue message acknowledgement eligibility (`commit-before-ack`).
- This contract defines semantic readiness only and **MUST NOT** define Database transaction mechanics or SQL lock syntax.

### 5.4 Deleted Evidence replay protection

If an Evidence object or artefact has been deleted or tombstoned under authoritative Security/Evidence policy:
- Subsequent Queue message replay, redelivery, or manual re-drive **MUST NOT** recreate the deleted Evidence payload or restore deleted content under the same historical identity.
- A historical `evidence_reference_id` **MUST NOT** resolve to replacement content or be rebound to another Evidence-owned object.
- Queue transport retry mechanics **MUST NOT** bypass Evidence tombstone invariants.

---

## 6. Candidate patch evidence and lineage

`A2-EVIDENCE` defines provider-neutral semantics for candidate patches generated during Workflow execution.

### 6.1 CandidatePatch and CandidateVersion semantics

A `CandidatePatch` and its associated `CandidateVersion` **MUST** record and prove:
- `candidate_patch_id`: Logical candidate patch identity;
- `candidate_version_id`: Unique versioned candidate identity;
- `run_id`: Originating Workflow run reference;
- `workflow_attempt_id`: Originating Workflow attempt reference;
- `producer_result_id`: CONDITIONAL opaque reference to an applicable `A2-EXECUTION`-owned result identity for this Workflow attempt and result phase (where available); a `CandidateVersion` **MUST** be creatable and finalizable before execution using valid candidate identity, generation provenance, Workflow provenance, source provenance, configuration provenance, and model/prompt provenance without requiring `A2-EXECUTION` to mint a result identity before execution; `A2-EVIDENCE` **MUST NOT** synthesize, fabricate, or preallocate `producer_result_id`;
- `source_repository`: Source repository identifier;
- `source_revision`: Source commit SHA against which the patch was generated;
- `target_reference_revision`: Reference/fixed revision commit SHA (where applicable);
- `patch_digest`: Canonical cryptographic digest of the patch content;
- `digest_algorithm`: Identifier of the Security-approved digest algorithm; no algorithm is selected by this draft;
- `test_only_scope`: Boolean flag proving patch edits are strictly limited to test files;
- `changed_files_manifest`: List of modified file paths and change summaries;
- `generation_provenance`: Generator identifier, tool version, and timestamp;
- `model_identifier`: AI model identifier (when supplied by producer);
- `prompt_template_version`: Version of prompt template used (when supplied by producer);
- `configuration_version`: Configuration version active during generation;
- `parent_candidate_version_id`: Reference to parent candidate version (for repaired candidates);
- `repair_level`: Candidate-lineage metadata (`0` for initial candidate, `1` for repaired candidate); it is not the Workflow repair counter;
- `finalization_state`: Creation and finalization state semantics.

### 6.2 Lineage and repair distinction

To preserve accurate auditability across repair attempts:
1. **Initial Candidate**: Generated during initial workflow attempts, assigned `repair_level = 0` and `parent_candidate_version_id = NULL`.
2. **Repaired Candidate**: Generated following a repair step, assigned `repair_level = 1` and explicit `parent_candidate_version_id` referencing the initial candidate (`repair_level = 0`).
3. **Immutability of Prior Evidence**: Prior candidate Evidence **MUST NOT** be overwritten, updated in place, or silently deleted when a repair candidate is produced.
4. **Distinct Identity**: Repaired candidates receive distinct `candidate_patch_id` and `candidate_version_id` values while retaining lineage linkage to the original candidate.

`repair_level` records candidate lineage only. The authoritative Workflow counter is `repair_attempts_used`, constrained to `0..1` and changed only by valid entry to `REPAIRING`. `A2-EVIDENCE` **MUST NOT** own, enforce, consume, reset, or modify `repair_attempts_used`.

---

## 7. Workflow compatibility

This contract consumes merged `CONTRACT-WORKFLOW-001@1.0.0-draft.1` and enforces strict boundary non-interference.

### 7.1 Regression testing sequence

Evidence semantics support recording and proving outcomes for the normative Workflow execution sequence:
$$\text{EXECUTING\_BUGGY} \longrightarrow \text{EXECUTING\_FIXED}$$

For each candidate patch, Evidence records separate execution facts for execution against the target buggy revision and execution against the reference fixed revision.

### 7.2 Non-interference rules

`A2-EVIDENCE` provides representation for Workflow outcomes but **MUST NOT**:
1. Create, transition, or modify a `RunState`;
2. Transition a run state;
3. Authorize or instantiate a Workflow attempt;
4. Consume or modify Workflow repair allowance;
5. Reset repair allowance or authorize a second repair;
6. Classify Queue transport redelivery as a Workflow retry;
7. Treat the mere existence of an Evidence object as proof of Workflow success.

`A2-AGENT-WORKFLOW` exclusively owns all lifecycle meaning and transition authority.

---

## 8. Execution evidence representation

`A2-EVIDENCE` defines the semantic representation for raw execution facts supplied by `A2-EXECUTION`.

### 8.1 ExecutionEvidence structure

Each `ExecutionEvidence` object is phase-specific. An `EvidenceBundle` groups the separate records needed for compile, buggy-execution, and fixed-execution evidence, subject to explicit availability and completeness states. Every record **MUST** contain:
- `execution_evidence_id`: Logical execution evidence identity;
- `workflow_attempt_id`: Workflow attempt reference;
- `candidate_version_id`: CandidateVersion reference;
- `execution_phase`: Execution phase classification (`COMPILE`, `BUGGY_EXECUTION`, `FIXED_EXECUTION`);
- `command_reference`: Execution command identity or reference;
- `exit_classification`: Exit classification (`SUCCESS`, `TEST_FAILURE`, `COMPILE_FAILURE`, `TIMEOUT`, `RESOURCE_EXCEEDED`, `RUNNER_ERROR`);
- `exit_code`: Numeric exit code supplied by process execution (when available);
- `structured_outcome`: Structured test summary object;
- `execution_timing`: Start timestamp, end timestamp, and duration semantics;
- `stdout_artefact_id`: `ArtefactReference` to captured standard output log;
- `stderr_artefact_id`: `ArtefactReference` to captured standard error log;
- `output_artefact_references`: References to additional output artefacts (e.g., XML report files);
- `sandbox_metadata`: Runtime sandbox metadata supplied by Execution runner;
- `environment_metadata`: Java version, toolchain, and runtime environment versions (when supplied);
- `resource_limit_outcome`: Provider-neutral and extensible resource usage assessment capable of preserving applicable `A2-EXECUTION`-produced runtime facts for CPU, memory, disk/temporary workspace, process count, file-count/filesystem quota (when enforced), output/log byte limits, and other separately approved runtime resource ceilings. Where operational runtime/resource configuration applies (including configured CPU limits, memory limits, disk/temporary workspace ceilings, process-count limits, filesystem/file-count quotas, output/log byte limits, runtime resource-policy/configuration values, deploy-time operational resource configuration, or other approved operational runtime ceilings), `A2-DEPLOYMENT` remains authoritative for operational runtime/resource configuration. `A2-EXECUTION` owns enforcement of configured limits, observation of runtime behavior, production of resulting runtime/resource facts, and resulting Execution-owned resource-limit facts/references. `A2-SECURITY` owns Security policy meaning, Security-policy denial meaning, Security classification, and Security-owned policy interpretation. `A2-EVIDENCE` owns ONLY semantic representation of resulting runtime/resource facts, Evidence-side representation of opaque policy/config references, and Evidence-side provenance/integrity/completeness semantics for those facts. `A2-EVIDENCE` **MUST NOT** select resource limits, redefine resource limits, configure resource limits, own deploy-time operational configuration, become authoritative for runtime resource configuration, become authoritative for Execution enforcement, or reinterpret Security-policy denial as generic resource exhaustion. Where available, representation **MUST** be capable of preserving limit category, configured limit OR opaque policy/config reference, observed value, whether that limit terminated execution, and originating `A2-EXECUTION` fact/reference. Timeout remains independent through `timeout_classification`;
- `timeout_classification`: Timeout classification and limit threshold metadata;
- `flake_indication`: Non-determinism or test flake indicators (when supplied);
- `failure_classification`: Detailed failure classification reference;
- `producer_result_id`: Opaque reference to the applicable originating `A2-EXECUTION`-owned Workflow-authorized semantic result slot/submission for this specific Workflow attempt and result phase; each applicable phase-specific `ExecutionEvidence` record retains its relevant `producer_result_id` reference;
- `integrity_metadata`: Cryptographic digest metadata for execution facts.

Each record **MUST** contain exactly the result field appropriate to its `execution_phase` and **MUST NOT** require or carry the other phase result fields:

| `execution_phase` | Required phase result |
|---|---|
| `COMPILE` | `compile_result`: structured compile outcome (status, error count, warning count). |
| `BUGGY_EXECUTION` | `buggy_execution_result`: test outcome against the buggy revision (passed, failed, skipped, errored tests). |
| `FIXED_EXECUTION` | `fixed_execution_result`: test outcome against the fixed revision (passed, failed, skipped, errored tests). |

An aggregate `EvidenceBundle` preserves the applicable phase-specific producer-result references (`producer_result_id`) for all included execution phases (compile, buggy execution, fixed execution). A singular bundle-level `producer_result_id` is valid only if that particular `EvidenceBundle` is explicitly scoped to one Workflow-authorized semantic result slot.

### 8.2 Production boundary

`A2-EVIDENCE` owns the representation of execution facts. It **MUST NOT** define shell script implementation, sandbox container configuration, command building logic, OS process management, timeout timers, or runner execution frameworks. `A2-EXECUTION` exclusively owns execution production.

---

## 9. Buggy/Fixed regression trust relationship

To establish trust in candidate patches, Evidence **MUST** represent and prove execution against both buggy and fixed codebases.

### 9.1 Provenance requirements for regression testing

Evidence records **MUST** prove:
1. Candidate patch executed against the exact target buggy source revision;
2. Candidate patch executed against the exact reference fixed source revision (where available).

The semantic record **MUST** retain:
- Exact `candidate_version_id`;
- Exact target buggy source revision SHA;
- Exact reference fixed source revision SHA;
- Workflow attempt phase identification;
- Individual test case execution status lists for both runs;
- Associated log artefacts (`stdout_artefact_id`, `stderr_artefact_id`);
- Integrity digests for all execution facts.

### 9.2 Trust relationship states

The Evidence contract explicitly supports all valid regression testing outcomes:
- **Dual Execution Available**: Both buggy and fixed execution outcomes are fully recorded and verified.
- **Fixed Execution Explicitly Unavailable**: Buggy execution is recorded; fixed execution is recorded as explicitly unavailable (e.g. reference fix not provided).
- **Execution Partial**: Buggy or fixed execution completed partially (e.g. interrupted by timeout).
- **Execution Invalid**: Execution facts fail validation or formatting checks.
- **Execution Conflicting**: Inconsistent execution results reported for identical candidate versions.

Existence of Evidence **MUST NOT** be automatically interpreted as test success. Progression authorization remains strictly under `A2-AGENT-WORKFLOW` control.

---

## 10. Artefact manifest and references

`A2-EVIDENCE` defines provider-neutral `ArtefactManifest` and `ArtefactReference` abstractions.

### 10.1 ArtefactReference semantics

For every stored artefact associated with Evidence, an `ArtefactReference` **MUST** record:
- `artefact_id`: Immutable logical artefact identity;
- `artefact_type`: Logical category (`CANDIDATE_PATCH`, `COMPILE_LOG`, `TEST_STDOUT`, `TEST_STDERR`, `EXECUTION_LOG`, `CONTEXT_MANIFEST`, `PUBLICATION_PAYLOAD`, `CUSTOM_OUTPUT`);
- `content_digest`: Cryptographic digest of artefact bytes;
- `digest_algorithm`: Security-approved digest algorithm identifier; no algorithm is selected by this draft;
- `byte_size`: Size of artefact content in bytes;
- `media_type`: MIME/media type (e.g., `text/x-diff`, `text/plain`, `application/json`);
- `producer_id`: Identifier of creating producer component/runner;
- `candidate_version_id`: Reference to associated candidate patch version (where applicable);
- `execution_evidence_id`: Reference to associated execution evidence (where applicable);
- `creation_timestamp`: Creation timestamp semantics;
- `availability_state`: Availability state (`AVAILABLE`, `UNAVAILABLE`, `EXPIRED`, `REDACTED`, `DELETED_OR_TOMBSTONED`);
- `integrity_state`: Verification state (`VERIFIED`, `UNVERIFIABLE`, `CORRUPT`, `TAMPERED`, `MISSING`, `DELETED`);
- `redaction_state`: Redaction metadata reference;
- `storage_locator`: Abstract stable storage reference string;
- `contract_version`: Version of governing Evidence contract.

`availability_state` and `integrity_state` are independent dimensions. `AVAILABLE` means the content is present and accessibly resolvable; it does not imply `VERIFIED` or any other integrity state.

### 10.2 ArtefactManifest semantics

An `ArtefactManifest` **MUST** record:
- `artefact_manifest_id`: Logical manifest identity;
- `artefact_references`: Bounded collection of immutable `artefact_id` references;
- `candidate_version_id`: Associated candidate version where applicable;
- `execution_evidence_id` and execution linkage: Associated execution Evidence and Workflow attempt/phase references where applicable;
- `producer_provenance_reference`: Opaque producer/result/provenance reference appropriate to the manifest source;
- `manifest_digest` and `integrity_metadata`: Digest and verification metadata for the canonical manifest content, under Security-approved policy;
- `creation_timestamp`: Manifest creation timestamp semantics;
- `finalization_state` and `finalization_timestamp`: Explicit mutable-during-assembly versus immutable-finalized semantics;
- `contract_version` and `schema_version`: Governing semantic contract and manifest schema versions.

The collection bound is `CONFIGURATION_VALUE_NOT_YET_SELECTED`. A finalized manifest **MUST NOT** silently change its membership or bindings; a changed manifest receives a distinct identity. This semantic structure selects no storage provider, physical Database mapping, or transaction mechanic.

### 10.3 Logical artefact categories

```
+-------------------------------------------------------------------------------+
|                         LOGICAL ARTEFACT CATEGORIES                           |
+-------------------+-----------------------------------------------------------+
| Category          | Description                                               |
+-------------------+-----------------------------------------------------------+
| CANDIDATE_PATCH   | Unified diff patch file containing candidate edits.       |
| COMPILE_LOG       | Standard output/error captured during project build.      |
| TEST_STDOUT       | Standard output captured during test execution.           |
| TEST_STDERR       | Standard error captured during test execution.            |
| EXECUTION_LOG     | Environment, runner, and sandbox execution trace log.     |
| CONTEXT_MANIFEST  | Manifest of files selected for fault localization/prompt. |
| PUBLICATION_PAYLOAD| Opaque bundle prepared for external export/publication.   |
+-------------------+-----------------------------------------------------------+
```

### 10.4 Provider neutrality

This contract **MUST NOT** select vendor-specific storage technologies, cloud services, bucket naming conventions, filesystem directory layouts, or BLOB column schemas. `A2-DEPLOYMENT` exclusively owns physical object storage provisioning.

---

## 11. Integrity model

`A2-EVIDENCE` establishes an end-to-end cryptographic integrity model for Evidence content.

### 11.1 Digest scopes and canonicalization

The integrity model separates digests across operational boundaries:
1. **Artefact-Content Hashing**: Unkeyed cryptographic digest calculated directly over raw unredacted/redacted artefact byte streams.
2. **Execution-Result Canonicalization**: Canonical digest computed over structured execution fact representations.
3. **Evidence Canonicalization**: Canonical digest calculated over normalized `EvidenceBundle` JSON payloads.
4. **Queue-Envelope Canonicalization**: Queue transport envelope hashing (owned by `A2-QUEUE`).

`A2-EVIDENCE` exclusively owns canonical Evidence content definition and equality evaluation.

### 11.2 Integrity states

An `EvidenceIntegrity` record evaluates and assigns one of the following verification states:
- `VERIFIED`: Content digest matches stored digest exactly;
- `UNVERIFIABLE`: Digest cannot be verified (e.g. algorithm unapproved or key unavailable);
- `CORRUPT`: Computed digest differs from registered manifest digest;
- `TAMPERED`: Structural inconsistency indicates unauthorized modification;
- `MISSING`: Referenced artefact bytes cannot be located at storage locator;
- `DELETED`: Content intentionally deleted under retention policy; metadata tombstoned.

`DELETED` is the current integrity state after intentional byte deletion: the bytes can no longer be verified. A bounded tombstone MAY retain the last pre-deletion verification result as historical metadata, but that historical value is not the current `integrity_state`.

### 11.3 Security policy boundary

`A2-SECURITY` exclusively owns the allowed digest, cryptographic canonicalization, signature/MAC, scope, key-custody, and security-incident policies. No algorithm is selected by this draft. Unkeyed content digests prove payload consistency but **MUST NOT** be used to claim producer authenticity without Security-approved authenticity protection.

---

## 12. Evidence completeness vocabulary

`A2-EVIDENCE` defines a normative, tightly controlled seven-state vocabulary for Evidence completeness.

### 12.1 Completeness states

```
+-------------------------------------------------------------------------------+
|                       EVIDENCE COMPLETENESS VOCABULARY                        |
+-----------------------+-------------------------------------------------------+
| State                 | Semantic Meaning                                      |
+-----------------------+-------------------------------------------------------+
| COMPLETE              | All required facts and referenced artefacts are       |
|                       | present, accessible, and verified.                    |
| PARTIAL               | Subset of expected facts/artefacts present; missing   |
|                       | items do not invalidate available data.               |
| UNAVAILABLE           | Required execution facts or artefacts are             |
|                       | structurally absent or unreachable.                   |
| INVALID               | Payload fails structural schema or semantic rules.    |
| CONFLICTING           | Mutually contradictory Evidence payloads submitted    |
|                       | for the same logical identity scope.                  |
| REDACTED              | Content sanitized or stripped per Security policy.    |
| DELETED_OR_TOMBSTONED | Content permanently purged per retention policy;      |
|                       | bounded audit tombstone remains.                      |
+-----------------------+-------------------------------------------------------+
```

### 12.2 State properties and guarantees

| Property / Guarantee | `COMPLETE` | `PARTIAL` | `UNAVAILABLE` | `INVALID` | `CONFLICTING` | `REDACTED` | `DELETED_OR_TOMBSTONED` |
|---|---|---|---|---|---|---|---|
| Referenced artefacts present? | Yes | Partial | No | No | No | Redacted | No (Tombstone) |
| Cryptographic integrity verifiable? | Yes | Partial | No | No | No | Sanitized | Tombstone only |
| Eligible for execution-backed claim? | Yes | No | No | No | No | Conditional | No |
| Compatible with human review card? | Yes | Yes | Yes | No | Yes | Yes | Tombstone card |

Completeness states describe data availability and integrity; they **MUST NOT** be used to define Workflow state transitions or claim automatic execution success.

---

## 13. Evidence conflict semantics

When incoming Evidence payloads share identity attributes with existing records, `A2-EVIDENCE` applies strict conflict semantics.

### 13.1 Convergence vs Conflict

1. **Canonical Equality (Duplicate Convergence)**:
   If an incoming Evidence submission shares `evidence_bundle_id` or `candidate_version_id` with an existing finalized record and its canonical Evidence digest matches identically, the submission converges to the existing record.
2. **Canonical Mismatch (Conflicting Submission)**:
   If an incoming Evidence submission shares identity attributes with an existing finalized record but contains a different canonical digest, it **MUST** be classified as `CONFLICTING`.

### 13.2 Immutability and conflict rules

- **Finalized Accepted Evidence Protection**: Finalized accepted Evidence **MUST NOT** be overwritten, updated in place, or replaced.
- **Last-Write-Wins Prohibition**: Last-write-wins (LWW) update strategies are explicitly **PROHIBITED**.
- **Preservation of Existing Records**: Conflicting submissions **MUST NOT** mutate existing accepted Evidence; conflict records are stored separately with full provenance attribution.
- **Queue Duplicate Independence**: Queue transport duplicate delivery receipts **MUST NOT** be used to define canonical Evidence equality.

Physical uniqueness enforcement belongs to `A2-DATABASE`. Security incident policy belongs to `A2-SECURITY`. Workflow outcome handling belongs to `A2-AGENT-WORKFLOW`.

---

## 14. Provenance model

The Evidence provenance model guarantees complete end-to-end auditability across the entire lifecycle of a candidate patch.

### 14.1 Traceability requirements

An `EvidenceBundle` **MUST** retain explicit semantic linkages to:
- `run_id`: Originating workflow run;
- `run_request_id`: Originating run request;
- `workflow_attempt_id`: Specific Workflow attempt;
- `workflow_step`: Workflow execution step;
- `queue_message_id` / `queue_delivery_id`: Originating Queue transport message and delivery references;
- `claim_or_lease_id`: Queue claim/lease provenance reference (where applicable);
- `producer_id` / `runner_id`: Execution runner instance and host metadata;
- `producer_result_id` / phase-specific producer result references: Aggregate `EvidenceBundle` preserves the applicable producer-result references for all included execution phases (compile, buggy execution, fixed execution). A singular bundle-level `producer_result_id` is valid only if that particular `EvidenceBundle` is explicitly scoped to one Workflow-authorized semantic result slot;
- `evaluation_benchmark_case_reference` / `evaluation_benchmark_manifest_version`: For BENCHMARK-originated Evidence, an immutable, versioned, `A2-EVALUATION`-owned benchmark provenance binding sufficient to identify (1) the exact Evaluation benchmark case and (2) the immutable benchmark manifest/dataset version governing that case. BENCHMARK Evidence **MUST** preserve this binding; non-BENCHMARK Evidence **MAY** mark it `NOT_APPLICABLE`. Evidence preserves this reference as provenance only and **MUST NOT** define benchmark membership policy, infer membership from result/model output, define population selection, reinterpret the Evaluation-owned reference, invent future `CONTRACT-EVAL-001` vocabulary, define scoring formulas, define metric denominators, or define release thresholds;
- `candidate_patch_id` / `candidate_version_id`: Candidate patch identity and version;
- `source_repository`: Source repository URL/name;
- `source_revision`: Target buggy commit SHA;
- `target_reference_revision`: Fixed/reference commit SHA;
- `selected_context_manifest`: File selection manifest used for localization/prompting;
- `configuration_version`: Active system configuration version;
- `model_identifier`: AI model name and version;
- `prompt_template_version`: Version of prompt template used;
- `evidence_contract_version`: `CONTRACT-EVIDENCE-001@1.0.0-draft.3`;
- `queue_contract_version`: `CONTRACT-QUEUE-001@1.0.0-draft.2`;
- `workflow_contract_version`: `CONTRACT-WORKFLOW-001@1.0.0-draft.1`;
- `producer_schema_version`: Execution output schema version;
- `causation_id` / `correlation_id`: Parent event causation and distributed tracing IDs;
- `human_decision_id`: Associated human review action (where applicable);
- `publication_identity`: Stable Queue publication-intent identity (where applicable).

The contract **MUST NOT** alter or redefine semantics of identifiers owned by external components.

---

## 15. EvidenceCard presentation boundary

`EvidenceCard` provides a bounded, human-review-facing semantic projection of an `EvidenceBundle`.

### 15.1 Semantic contents

An `EvidenceCard` **MUST** include:
- Invocation and source context metadata;
- Candidate patch identity and version (`candidate_version_id`);
- Selected files manifest summary;
- Compilation outcome summary;
- Buggy revision execution outcome summary;
- Fixed/reference revision execution outcome summary (or explicit unavailable reason);
- Bounded explanation or rationale reference;
- Confidence assessment reference;
- Uncertainty indication and category;
- Evidence completeness state;
- Integrity verification state;
- Immutable references to logs and patch artefacts;
- AI-generated indicator (boolean flag);
- Human-review-required indicator (boolean flag);
- `governing_contract_version`: `CONTRACT-EVIDENCE-001@1.0.0-draft.3`.

### 15.2 Presentation rules

- **UI Layout Ownership**: `A2-UI` exclusively owns presentation layout, styling, and visual rendering. `EvidenceCard` defines data content only.
- **Truthful Representation**: An `EvidenceCard` **MUST NOT** present unexecuted claims or unverified patches as execution-backed facts.

---

## 16. Confidence and uncertainty model

`A2-EVIDENCE` provides provider-neutral semantic structures for confidence and uncertainty metadata.

### 16.1 Semantic structure

Confidence and uncertainty records support:
- `confidence_reference`: Opaque confidence assessment reference or score payload;
- `uncertainty_flag`: Boolean flag indicating presence of significant uncertainty;
- `uncertainty_category`: Opaque, versioned category pending A2-EVALUATION/A2-EXECUTION confirmation. `MODEL_HALLUCINATION_RISK`, `TEST_FLAKINESS`, `PARTIAL_EXECUTION`, `UNRESOLVED_DEPENDENCY`, and `AMBIGUOUS_SPECIFICATION` are `NON_NORMATIVE_EXAMPLES`, not a frozen taxonomy;
- `assessment_producer`: Component or model originating the assessment;
- `calibration_metadata`: Calibration model version or assessment methodology metadata.

### 16.2 Constraints and non-overriding rules

If no numeric scale has been authoritatively approved by `A2-EVALUATION`, this contract **MUST NOT** invent a numeric scale.

Confidence metadata **MUST NOT**:
1. Override missing or corrupt Evidence;
2. Convert `PARTIAL` or `UNAVAILABLE` completeness into `COMPLETE`;
3. Convert `CONFLICTING` Evidence into valid Evidence;
4. Turn an unexecuted candidate claim into a verified fact;
5. Authorize Workflow progression or state transitions.

---

## 17. Failure evidence representation

`A2-EVIDENCE` defines `EvidenceFailureLink` to record attributable failure data across execution phases.

### 17.1 Failure attribution

An `EvidenceFailureLink` **MUST** contain:
- `evidence_failure_link_id`: Evidence-owned semantic link identity;
- `source_evidence_bundle_id`: Exact source `EvidenceBundle` reference;
- `source_evidence_reference`: Exact source Evidence object reference where applicable;
- `candidate_version_id`, `workflow_attempt_id`, and `execution_evidence_id`: Candidate/execution linkage where applicable;
- `failure_classification` and `failure_reference`: Failure category and attributable source fact/reference;
- `supporting_artefact_ids` and `supporting_failure_evidence_references`: Bounded supporting artefact/failure-Evidence references where applicable;
- `attribution_provenance`: Producer, actor/service, result, and causation provenance references applicable to the failure;
- `observed_timestamp` and `recorded_timestamp`: Failure occurrence and Evidence-recording timestamp semantics.

Supported failure classifications include:
- `COMPILE_FAILURE`: Project compilation or build failure;
- `BUGGY_EXECUTION_FAILURE`: Test suite failures on buggy revision;
- `FIXED_EXECUTION_FAILURE`: Unexpected test failures on fixed reference revision;
- `TIMEOUT_EXCEEDED`: Execution time limit exceeded;
- `RESOURCE_LIMIT_EXCEEDED`: Runtime resource ceiling breached (preserving applicable A2-EXECUTION-produced runtime facts for CPU, memory, disk/temporary workspace, process count, file-count/filesystem quota when enforced, output/log byte limits, or other separately approved runtime resource ceilings). A2-DEPLOYMENT remains authoritative for operational runtime/resource configuration; A2-EXECUTION owns enforcement and runtime fact production; A2-SECURITY owns Security policy meaning; A2-EVIDENCE owns representation only. Network-policy denials, filesystem-access-policy denials, tool-policy denials, and Security rejections **MUST NOT** be classified automatically as generic resource exhaustion;
- `RUNNER_INFRASTRUCTURE_FAILURE`: Execution runner or container failure;
- `FLAKE_NONDETERMINISM`: Non-deterministic test outcome detected;
- `INTEGRITY_FAILURE`: Digest mismatch or corrupted artefact payload;
- `MISSING_ARTEFACT`: Referenced log or patch file missing from storage;
- `CONFLICTING_EVIDENCE`: Contradictory Evidence submitted under same identity;
- `SECURITY_REJECTION`: Payload rejected by Security redaction policy;
- `FIXED_REVISION_UNAVAILABLE`: Reference fixed revision unavailable for regression testing.

### 17.2 Failure boundaries

`EvidenceFailureLink` represents failure facts. It **MUST NOT** invent Workflow terminal state mappings (owned by `A2-AGENT-WORKFLOW`), define Security event severity (owned by `A2-SECURITY`), or equate Queue dead-letter state automatically with execution failure (owned by `A2-QUEUE`).

---

## 18. Human decision linkage

`A2-EVIDENCE` defines `HumanDecisionLink` to link human review actions to exact Evidence versions.

### 18.1 HumanDecisionLink semantics

A `HumanDecisionLink` **MUST** record:
- `human_decision_link_id`: Evidence-owned identity of this semantic link;
- `human_decision_id`: Distinct Evidence-owned human-decision record identity;
- `reviewed_evidence_bundle_id`: Exact `EvidenceBundle` version reviewed;
- `reviewed_evidence_card_id`: Exact `EvidenceCard` version displayed to reviewer;
- `human_actor_reference`: Opaque reference to an `A2-AUTH`-owned HUMAN actor identity. `A2-EVIDENCE` does NOT mint, redefine, authenticate, authorize, revoke, suspend, or expire this identity, nor own provider-subject meaning, nor convert machine/service/install identities into human actors. `HumanDecisionLink` represents historical decision and provenance linkage only;
- `decision_timestamp`: Decision timestamp semantics;
- `disposition`: Workflow-owned lifecycle disposition (`APPROVED`, `REJECTED`, `DISMISSED`, `OUT_OF_SCOPE`, `REGENERATION_REQUESTED`);
- `rationale_reference`: Optional bounded rationale or rationale reference;
- `workflow_event_or_result_reference`: Workflow-owned event/result reference;
- `regeneration_child_run_reference`: Distinct child-run reference where regeneration applies.

### 18.2 Invariants

1. **Rejection Immutability**: Rejection of a candidate **MUST NOT** delete or purge historical Evidence records.
2. **Regeneration Traceability**: Regeneration requests spawn new runs with distinct identities; prior Evidence records remain immutable and fully attributable.
3. **Domain Ownership**: `A2-AGENT-WORKFLOW` owns lifecycle disposition semantics and effects; `A2-AUTH` owns human actor identity; `A2-EVIDENCE` owns the human-decision semantic record/linkage boundary; `A2-DATABASE` owns its physical persistence.
4. **Auth Identity & Authorization Distinction**: `human_actor_reference` is an opaque identity/provenance reference only; historical actor attribution DOES NOT equal current authentication, current authorization, or permission to repeat the action. Historical `human_actor_reference` **MAY** remain when Auth semantics permit historical attribution after later actor lifecycle changes. A `HumanDecisionLink` **MUST NOT** independently authorize another `HUMAN_DECISION_WRITE`, authorize Workflow progression, authorize publication, restore expired/revoked/suspended/deprovisioned authority, act as a permission/capability/grant/role, or replace current `A2-AUTH` authorization. Every NEW protected operation **MUST** independently satisfy current `A2-AUTH` authentication and authorization. Evidence **MUST NOT** store, derive, copy, or reinterpret as `human_actor_reference` any passwords, password hashes, OAuth codes, access tokens, refresh tokens, session cookies, session tokens, GitHub App private keys/JWTs, installation tokens, provider API keys, raw Authorization headers, or other credential/session secrets.

---

## 19. Security boundary

This contract explicitly leaves external to `A2-EVIDENCE` all Security policy definitions:
- Secret redaction rules and pattern matching;
- Data sensitivity classification levels;
- Public disclosure policies;
- Retention security durations;
- Cryptographic key custody and access management;
- Encryption algorithms and key rotation;
- Allowed digest, cryptographic canonicalization, signature/MAC, and scope policy;
- Security event classification and severity assignment.

Evidence objects record references to Security decisions (e.g. `redaction_state`, `security_classification_id`, `integrity_policy_version`), but `A2-EVIDENCE` **MUST NOT** invent Security policy. `A2-SECURITY` exclusively owns Security policy.

---

## 20. Retention and deletion semantics

`A2-EVIDENCE` defines provider-neutral semantic states for Evidence retention and deletion.

### 20.1 Semantic lifecycle states

- `AVAILABLE`: Content is present and accessibly resolvable; this state makes no integrity claim.
- `UNAVAILABLE`: Content temporarily or structurally unreachable.
- `EXPIRED`: Retention period elapsed; content marked for deletion.
- `REDACTED`: Content sanitized per Security policy.
- `DELETED_OR_TOMBSTONED`: Byte content permanently deleted; immutable audit tombstone preserved.

These are availability/lifecycle states only. Unexpected absence is represented by integrity state `MISSING`; verification failure is represented by `CORRUPT` or `TAMPERED`. They are not additional availability states.

### 20.2 Invariants

1. **No Re-resolution**: Once Evidence content is deleted under policy, historical `evidence_reference_id`, `evidence_bundle_id`, or `artefact_id` references **MUST NOT** resolve to new replacement content; an `evidence_reference_id` **MUST NOT** be rebound to another object.
2. **Replay Protection**: Queue replay, redelivery, or manual re-drive **MUST NOT** recreate deleted content under historical identities.
3. **Audit Tombstone**: Bounded audit metadata (identity, deletion timestamp, digest, deletion rationale reference) MAY remain in tombstone state per Security policy.

`A2-SECURITY` determines policy; `A2-DEPLOYMENT` executes byte deletion; `A2-DATABASE` manages physical metadata tombstones.

Availability and integrity are orthogonal: an `AVAILABLE` record may have any applicable current `integrity_state`, and `VERIFIED` must be established independently. When byte deletion completes, `availability_state` becomes `DELETED_OR_TOMBSTONED` and current `integrity_state` becomes `DELETED`; any last pre-deletion verification result is retained only as historical tombstone metadata.

---

## 21. Database boundary

The Evidence contract explicitly states:

$$\mathbf{A2\text{-}DATABASE\ exclusively\ owns\ physical\ persistence.}$$

This contract **MUST NOT** create, define, or select:
- Database task `DB-003`;
- Physical SQL table names;
- ORM classes or SQLalchemy models;
- Database migration scripts (Alembic);
- SQL column types, constraints, or lengths;
- Database index configurations;
- Physical transaction isolation levels or CAS mechanics.

Evidence defines logical semantic requirements only. `DB-003` remains:
$$\mathbf{NOT\_STARTED\ /\ NOT\_AUTHORIZED}$$

---

## 22. Provider neutrality

`CONTRACT-EVIDENCE-001` remains strictly provider-neutral.

The following selections are classified `UNSELECTED / CONFIGURATION_VALUE_NOT_YET_SELECTED`:
- Queue provider (RabbitMQ, SQS, NATS, Kafka);
- Object storage provider (AWS S3, Google Cloud Storage, Azure Blob, Supabase Storage, MinIO, POSIX filesystem);
- Cloud vendor or serverless infrastructure;
- Framework-specific persistence libraries;
- Cryptographic hash library (pending `A2-SECURITY` algorithm approval);
- Pre-signed URL generation provider or CDN;
- Encryption key management provider.

Providers must later demonstrate conformance to this contract during implementation testing.

---

## 23. Contract compatibility and versioning rules

The Evidence contract follows strict semantic versioning (`MAJOR.MINOR.PATCH-draft.N`).

### 23.1 Breaking vs Non-breaking changes

The following changes are **BREAKING** and require a Major version increment:
1. Altering logical identity semantics or identifier separation rules;
2. Removing required fields from `EvidenceBundle`, `EvidenceCard`, or `ExecutionEvidence`;
3. Changing the semantic meaning of any `EvidenceCompleteness` state;
4. Weakening immutable conflict rules or allowing last-write-wins;
5. Weakening deletion invariants or permitting historical ID re-use;
6. Modifying `CandidateVersion` lineage rules or repair distinctions;
7. Altering buggy/fixed regression testing trust semantics.

Additive, optional fields MAY be introduced in Minor versions following consumer review.

### 23.2 Version enforcement

- Systems encountering unsupported Major versions **MUST** fail closed.
- Existing finalized Evidence remains bound to the exact contract version under which it was finalized.
- Migration implementation details are not defined within this contract.
