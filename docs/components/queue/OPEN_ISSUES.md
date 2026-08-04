# Queue Open Issues

- Contract: `CONTRACT-QUEUE-001@1.0.0-draft.1`
- State: `DRAFT / PENDING_CONSUMER_REVIEW`
- Provider: `UNSELECTED`

| Issue | Classification | Owner / closure |
|---|---|---|
| Corrected canonical requirement matrix | `RESOLVED / A2_QUEUE_REVIEW_PASSED` | Count-only validation originally passed. A3 corrected the semantic ID/title mapping and seven drafting-status mismatches; the complete correction passed A2-QUEUE review. |
| Final semantic-boundary correction | `RESOLVED / A2_QUEUE_REVIEW_PASSED` | A2-QUEUE found and reviewed corrections for at-least-once disposition handling, Execution versus Workflow cleanup ownership, and outbox-plus-inbox capability requirements; all three passed. Consumer review has not begun. |
| Ten mandatory consumer reviews | `EXTERNAL_OWNER_POLICY_REQUIRED` | Each named reviewer returns an allowed written disposition; silence is not acceptance. |
| Security-approved envelope fields, redaction/disclosure, events, integrity algorithm/canonicalization, MAC/signature, and key custody | `EXTERNAL_OWNER_POLICY_REQUIRED` | A2-SECURITY records accepted policy and evidence requirements. |
| Actor/service identities, authorization-context format, current-authorization checks, and freshness | `EXTERNAL_OWNER_POLICY_REQUIRED` | A2-AUTH with A2-SECURITY records accepted references/policy. |
| Publication-intent/outbox/inbox equivalent, fencing, durable effect, deletion barrier, and uniqueness design | `IMPLEMENTATION_DETAIL_DEFERRED` | A2-DATABASE reviews the contract; later work requires explicit authorization. DB-003 remains unauthorized. |
| Workflow eligibility, attempt creation, cancellation, repair, result acceptance, and terminality | `EXTERNAL_OWNER_POLICY_REQUIRED` | A2-AGENT-WORKFLOW accepts or constrains the Queue boundary. |
| Evidence reference, accepted-result binding, deletion, proof, and retention | `EXTERNAL_OWNER_POLICY_REQUIRED` | A2-EVIDENCE supplies owner semantics; deleted Evidence cannot be recreated. |
| Worker protected effects, checkpoint compatibility, cleanup, and result production | `EXTERNAL_OWNER_POLICY_REQUIRED` | A2-EXECUTION supplies owner semantics. |
| Provider and configurable limits/timeouts/retries | `CONFIGURATION_VALUE_NOT_YET_SELECTED` | A2-DEPLOYMENT selects values after consumer constraints and measurements. |
| Concurrency, throughput, and provider capacity | `BLOCKED_BY_MISSING_MEASUREMENT_INPUT` | A2-EVALUATION and Deployment provide reproducible measurements. |
| Latency and other release thresholds | `RELEASE_GATE_INPUT_REQUIRED` | A2-EVALUATION/Integration define gates without changing transport semantics. |
| Provider receipt mapping and physical adapter details | `IMPLEMENTATION_DETAIL_DEFERRED` | Future authorized adapter implementation demonstrates conformance. |
| API duplicate response (`200`, `202`, or `409`) and `Retry-After` | `EXTERNAL_OWNER_POLICY_REQUIRED` | Backend/Database/Workflow/Integration/Deployment review; Queue does not select HTTP behavior. |
| Runtime conformance evidence | `IMPLEMENTATION_DETAIL_DEFERRED` | Future implementation supplies fencing, duplicate, crash, cancellation, redaction, integrity, replay, and dead-letter evidence. |

No issue authorizes Queue runtime, a provider, DB-003, application code, tests,
dependencies, migrations, workers, sandboxes, or infrastructure.
