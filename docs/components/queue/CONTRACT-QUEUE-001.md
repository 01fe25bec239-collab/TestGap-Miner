# CONTRACT-QUEUE-001 — Provider-neutral Queue boundary

## 1. Metadata and normative scope

| Field | Value |
|---|---|
| Contract ID | `CONTRACT-QUEUE-001` |
| Version | `1.0.0-draft.2` |
| Status | `DRAFT / A2_QUEUE_REVIEW_PASSED / AFFECTED_OWNER_REREVIEW_PENDING` |
| Owner | `A2-QUEUE — Queue and Asynchronous Execution Component Manager` |
| Authorized baseline | `ab60d4573d398fb610bc2ebb813f76d0c95b33d7` |
| Historical consumer-review draft | `CONTRACT-QUEUE-001@1.0.0-draft.1` at `ed66cd39e5648c496552a3a160f0a7ef8ba7ba8a`; review completed, not accepted |
| Runtime | `NOT_IMPLEMENTED / NOT_TESTED / NOT_AUTHORIZED_BY_THIS_DRAFT` |
| Provider | `CONFIGURATION_VALUE_NOT_YET_SELECTED` |

The terms **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative as in
RFC 2119. This contract defines logical Queue behavior only. It does not select
a provider, physical Database types, persistence design, runtime adapter,
worker, infrastructure, test threshold, or release threshold.

### 1.1 External API dependency and PR #23 reconciliation

`CONTRACT-API-001@0.1.0-draft.1`, merged by PR #23 at the authorized baseline,
is an `EXTERNAL_BACKEND_API_DRAFT_DEPENDENCY`, a
`REQUIRED_QUEUE_CONSUMER_REVIEW`, and `NOT_QUEUE_RUNTIME_AUTHORIZATION`.
This contract does not redefine its HTTP routes, methods, status codes, error
envelope, authentication transport, pagination, Backend request handling, or
authenticated-context structure.

### 1.2 Semantic categories

| Category | Meaning |
|---|---|
| A. Normative contract requirements | Provider-neutral identity, validation, publication, delivery, claim, result, acknowledgement, retry, cancellation, dead-letter, integrity, and compatibility rules in this document. |
| B. Configurable provider values | Deploy-time values explicitly classified `CONFIGURATION_VALUE_NOT_YET_SELECTED`; configuration cannot weaken normative behavior. |
| C. External owner policies | Security, Auth, Database, Workflow, Evidence, Execution, Deployment, Integration, and Evaluation decisions classified `EXTERNAL_OWNER_POLICY_REQUIRED`. |
| D. Implementation acceptance evidence | Adapter conformance, persistence, race, fencing, replay, redaction, and fault-injection evidence; evidence demonstrates an implementation and does not define semantics. |
| E. Release and Evaluation gates | Measured capacity, latency, reliability, security, and compatibility thresholds classified `RELEASE_GATE_INPUT_REQUIRED` or `BLOCKED_BY_MISSING_MEASUREMENT_INPUT`; they are not transport semantics. |

## 2. Binding principles

1. Queue receipt is not authorization. Enqueue success does not create or
   extend authorization, and redelivery does not refresh authorization.
2. Provider receipt identity is not semantic identity. Semantic request,
   message, delivery, claim, Workflow attempt, result, and Evidence identities
   MUST remain separate. Requester, producer, worker, and publication
   identities MUST remain separate.
3. Worker authority does not imply publication authority. Transport redelivery
   MUST NOT automatically create a Workflow attempt.
4. Duplicate delivery MUST NOT create duplicate accepted semantic effects.
   Identical duplicate results require valid binding, required integrity checks,
   and canonical equality. Conflicting results MUST fail closed. Last-write-wins
   and automatic conflict merging are prohibited; accepted results and Evidence
   MUST NOT be overwritten by conflicts.
5. Required durable effects MUST commit before acknowledgement eligibility.
   Provider acknowledgement does not prove semantic completion, and a
   commit-before-ack failure MUST recover idempotently.
6. Confirmed lease loss prohibits further accepted protected effects. A stale
   or replaced worker cannot produce accepted effects, and a worker with
   confirmed lease loss cannot acknowledge success.
7. Cancellation, terminal state, deletion, and revocation MUST NOT be bypassed
   by replay, redelivery, or re-drive.
8. Corrupt, substituted, deleted, cancelled, superseded, or incompatible
   checkpoints MUST fail closed. Lease expiry alone is not a Workflow terminal
   outcome.
9. Poison work cannot retry indefinitely. Ordinary application failure is not
   automatically poison work. Dead-letter placement is not automatically a
   Workflow terminal state.
10. Dead-letter administrative actions MUST be attributable. Re-drive requires
    current authorization and current policy, creates a new delivery identity
    while preserving semantic identity and provenance, and cannot recreate
    deleted Evidence.
11. Queue payloads are allowlist-first. Credentials, tokens, cookies, keys, and
    authorization headers are prohibited. Raw repositories, archives, patches,
    prompts, model context, transcripts, full logs, Evidence bytes, artefact
    bytes, and arbitrary commands are prohibited. Encoding, hashing,
    compression, or encryption does not automatically make prohibited content
    acceptable.
12. Redaction MUST occur before serialization. Redaction failure MUST block
    publication. Consumers MUST validate defensively; unknown schema or
    canonicalization versions and required integrity mismatches MUST fail
    closed. An unkeyed checksum is content-consistency evidence only, not
    producer-authenticity proof.
13. Queue ordering is not Workflow event ordering. Queue acknowledgement is not
    Evidence proof. Provider extensions MUST NOT silently change semantic
    behavior.

## 3. API–Queue reconciliation

### 3.1 HTTP `202` versus Queue delivery

An API `202` retains exactly the API-owned meaning in
`CONTRACT-API-001@0.1.0-draft.1`: the durable run request and current-run
projection exist and the API-owned durable acceptance boundary succeeded. It
does not prove Queue publication, delivery, worker claim, execution start,
execution success, Evidence creation, or artefact creation.

Queue publication is tracked separately as `not_attempted`,
`rejected_before_acceptance`, `confirmed_failure`, `uncertain`,
`confirmed_success`, or `confirmed_duplicate_request`. These states MUST NOT
alter or reinterpret HTTP status semantics.

### 3.2 Durable request versus publication

Durable run-request creation, durable current-run projection, publication
eligibility, publication intent, publication attempt, confirmed publication,
uncertain publication, failed publication, delivery, claim/lease, and
acknowledgement are separate facts. Database persistence and provider
publication MUST NOT be assumed atomic.

Before a publication attempt, the producer MUST durably establish a stable
publication intent, or an A2-DATABASE-approved equivalent, bound to semantic
request and Queue message identity. Attempts and outcomes MUST be attributable
and idempotently reconcilable. A2-DATABASE owns the physical outbox/inbox or
equivalent design; DB-003 remains unauthorized.

### 3.3 Request and correlation identifiers

`X-Request-ID` and `X-Correlation-ID` remain API-owned tracing values. They are
not semantic request IDs, Queue message IDs, Queue delivery IDs, claim/lease
IDs, Workflow attempt IDs, result IDs, Evidence IDs, credentials,
authorization, or idempotency keys. A bounded `correlation_id` MAY be copied as
a tracing reference only; it MUST NOT grant authority or establish identity.

### 3.4 API versus Queue idempotency

API/client semantic request idempotency, Backend durable request idempotency,
Queue publication idempotency, Queue message identity, duplicate delivery
handling, Workflow attempt creation, and result-acceptance idempotency are
distinct. Provider receipts MUST NOT become semantic idempotency keys. This
contract does not select whether an API duplicate returns `200`, `202`, or
`409`.

### 3.5 Enqueue failure and uncertain publication

| Publication state | Required meaning and action |
|---|---|
| `publication_not_attempted` | No provider call occurred; preserve the durable intent and retry only under current eligibility and policy. |
| `publication_rejected_before_acceptance` | Provider definitively rejected before accepting work; record the attributable rejection and apply bounded retry classification. |
| `confirmed_publication_failure` | Provider definitively reports failure; retain identity and evidence, then retry or terminate publication handling under policy. |
| `publication_result_uncertain` | Acceptance may have occurred. Do not create a new semantic request blindly and do not assume non-publication; reconcile using stable message identity and idempotency, preserve attributable evidence, prevent duplicate accepted effects, and never report execution success. |
| `confirmed_publication_success` | Provider acceptance is confirmed; this still proves neither delivery nor execution. |
| `confirmed_duplicate_publication_request` | The stable publication identity was already accepted or recognized; reconcile to the existing semantic/message binding and do not create a new semantic effect. |

### 3.6 Cancellation

API cancellation-request acceptance, Workflow cancellation meaning, durable
cancellation intent, Queue cancellation/control delivery, worker observation,
protected-effect cutoff, cleanup, Workflow terminal transition, and Queue
acknowledgement are distinct. An accepted API cancellation request proves none
of worker observation, cleanup, or terminal cancellation. A worker MUST
revalidate cancellation before each protected effect and before success
acknowledgement; Queue transport does not choose the Workflow terminal state.

## 4. Logical identity model

Every identity is a separately typed logical value. This draft chooses no
physical Database type or unsupported length.

| Identity | Purpose | Generation authority | Required binding | Prohibited reuse |
|---|---|---|---|---|
| `semantic_request_id` | One requested semantic operation across retries | Backend/Database owner | requester, operation, durable run request | message, delivery, claim, attempt, result, Evidence, receipt, tracing, or credential identity |
| `queue_message_id` | Stable logical publication identity | Queue producer under durable-intent rules | semantic request, operation, schema/contract version | provider receipt, delivery, claim, or a different semantic request |
| `queue_delivery_id` | One delivery/redelivery occurrence | Queue adapter or provider mapping | message, delivery metadata, provenance | message identity, Workflow attempt, or re-drive delivery |
| `claim_or_lease_id` | One fenced right to perform protected work | Claim/lease authority | delivery, worker, fence, lease state | replacement claim, worker identity, or authorization context |
| `workflow_attempt_id` | Workflow-owned semantic attempt | A2-AGENT-WORKFLOW | run identity, Workflow step-occurrence identity, step kind, occurrence, and zero-based `attempt_index` | transport delivery, claim/lease, provider receipt, or lifecycle transition as the universal attempt parent |
| `producer_result_id` | One Workflow-authorized semantic result slot or submission for one Workflow attempt and result phase | A2-EXECUTION under Workflow authorization | Workflow attempt and authorized result phase/slot | Evidence identity, provider receipt, delivery, claim, worker, or conflicting content |
| `evidence_reference_id` | Opaque reference to Evidence-owned material | A2-EVIDENCE | accepted result/provenance and current Evidence record | Evidence bytes, result identity, or recreation after deletion |
| `correlation_id` | Bounded cross-system trace reference | originating trusted boundary | trace chain only | semantic identity, authorization, credential, or idempotency |
| `causation_id` | Identifies the logical predecessor event/message | trusted producer | current message and predecessor identity/type | ordering proof, authorization, or current-message identity |
| `requester_actor_reference` | Actor attributable to the semantic request | Auth/Backend trusted boundary | semantic request and authorization reference | producer, worker, publication, or credential identity |
| `queue_producer_service_reference` | Service that formed the envelope | Deployment/Auth-approved service identity | message and publication intent | requester, worker, or publication actor identity |
| `worker_service_reference` | Service instance/principal processing delivery | Deployment/Auth-approved worker identity | claim, delivery, accepted effects | requester, producer, or publication authority |
| `publication_identity` | Stable identity of one logical publication intent and its retries | Queue producer under the durable-intent boundary | semantic request, Queue message, intent, producer, and publication actor | provider receipt, delivery identity, or a different message/semantic request |
| `publication_actor_reference` | Actor/service authorizing a publication action | Current Auth/policy boundary | publication intent/attempt | worker authority, requester identity, or provider receipt |
| `cancellation_actor_reference` | Actor attributable to cancellation intent | Current API/Auth/Workflow boundary | cancellation intent and target semantic request | worker, requester, or publication identity unless independently bound |
| `replay_or_redrive_actor_reference` | Administrator/service attributable to replay/re-drive | Authorized administrative boundary | administrative action, source provenance, current authorization | stale authorization or original delivery identity |
| `authorization_context_reference` | Opaque pointer to authorization decision context | A2-AUTH-approved authority | actor, action, resource boundary, policy version | token, credential, evergreen authorization, or semantic idempotency key |
| `policy_version` | Version of policy applied to a decision | Owning policy authority | validation/authorization decision and time | schema, contract, or identity value |
| `schema_version` | Envelope schema interpretation | A2-QUEUE contract process | serialized envelope and canonicalization input | contract or policy version |
| `contract_version` | Governing Queue semantic contract | A2-QUEUE contract process | message and consumer conformance | schema or Workflow contract version |

A Workflow event or lifecycle transition MAY reference an attempt when
applicable, but it is not the universal identity parent of an attempt. Queue
delivery, claim, lease, redelivery, and provider-receipt identities MUST NOT
create, replace, or redefine a Workflow attempt. A2-AGENT-WORKFLOW exclusively
owns attempt creation and attempt meaning.

For the same Workflow-authorized result slot, `producer_result_id` MUST remain
stable across Queue redelivery, acknowledgement retry, worker restart,
replacement-worker recovery, and same-attempt checkpoint recovery. Worker,
delivery, claim/fence, submission occurrence, and applicable version/integrity
metadata remain per-submission provenance and acceptance-authority facts.
Changing any of them MUST NOT by itself force a new `producer_result_id`. A new
identifier requires a new Workflow-authorized attempt or a separately defined
Workflow-authorized result phase/slot. Stable result identity never bypasses
current worker, claim, fence, authorization, or integrity validation.

## 5. Provider-neutral logical envelope

Fields not listed as allowed are prohibited. All strings, collections, and
metadata MUST be bounded; exact limits are
`CONFIGURATION_VALUE_NOT_YET_SELECTED`. Security approval for sensitive or
security-relevant field membership is `EXTERNAL_OWNER_POLICY_REQUIRED`.

| Logical field | Classification | Rule |
|---|---|---|
| `contract_version`, `schema_version` | REQUIRED | Known compatible values; unknown values fail closed. |
| `semantic_request_id`, `queue_message_id` | REQUIRED | Stable, separate, and bound as section 4 requires. |
| `queue_delivery_id` | CONDITIONALLY_REQUIRED | Required once a delivery exists; producer MUST NOT fabricate it before delivery. |
| `operation_kind` | REQUIRED | Allowlisted enum reviewed by Workflow and consumers. |
| `queue_producer_service_reference`, `publication_actor_reference` | REQUIRED | Attributable producer/publication identities. |
| `requester_actor_reference`, `authorization_context_reference`, `policy_version` | REQUIRED | Opaque references only; current authorization must still be revalidated when required. |
| `correlation_id`, `causation_id` | OPTIONAL | Bounded tracing/provenance references with no authority. |
| `workflow_attempt_id` | CONDITIONALLY_REQUIRED | Required only after Workflow validly creates an attempt. |
| `claim_or_lease_id`, `worker_service_reference`, `fence` | CONDITIONALLY_REQUIRED | Required on claimed/active/result/control messages as applicable. |
| `producer_result_id` | CONDITIONALLY_REQUIRED | Required for a result submission. |
| `evidence_reference_id` | OPTIONAL | Opaque Evidence reference; bytes are prohibited. |
| `input_reference`, `checkpoint_reference`, `result_reference` | OPTIONAL | Opaque, bounded, owner-approved references; never embedded content. |
| `publication_identity`, `publication_state` | CONDITIONALLY_REQUIRED | Required for publication reconciliation records/messages. |
| `delivery_attempt_metadata`, `retry_classification` | OPTIONAL | Bounded provider-neutral counters/categories; not Workflow ordering or attempts. |
| `cancellation_actor_reference`, `cancellation_intent_reference` | CONDITIONALLY_REQUIRED | Required for cancellation/control work. |
| `replay_or_redrive_actor_reference`, `original_provenance_reference` | CONDITIONALLY_REQUIRED | Required for replay/re-drive and dead-letter administrative work. |
| `integrity_metadata` | CONDITIONALLY_REQUIRED | Required where current Security/integrity policy requires it; section 11 applies. |
| `bounded_metadata` | OPTIONAL | Allowlisted scalar metadata only; no arbitrary extension bag. |
| credentials, tokens, cookies, keys, authorization headers | PROHIBITED | Redaction or encryption does not permit transport. |
| raw repositories, archives, patches, prompts, model context, transcripts | PROHIBITED | Use approved opaque references. |
| full logs, Evidence bytes, artefact bytes, arbitrary commands | PROHIBITED | Use approved opaque references; commands cannot be smuggled as data. |
| unknown fields or provider extensions with semantic meaning | PROHIBITED | Require a versioned contract/schema revision and consumer review. |

### 5.1 Validation and redaction

The producer MUST validate identity bindings, allowlisted operation/fields,
required versions, boundedness, current eligibility, and required integrity
metadata before publication. It MUST redact before serialization. A redaction
failure or prohibited field MUST block publication and create an attributable,
secret-free failure record and required Security event.

The consumer MUST defensively repeat schema, field, version, binding,
authorization/policy, cancellation/terminal/deletion, fencing, and integrity
validation. Producer validation is not consumer trust. Invalid work MUST fail
closed and be classified without leaking its prohibited content.

## 6. Publication, delivery, claim, and lease model

| State | Meaning |
|---|---|
| `available` | Durable semantic request exists and may be evaluated for publication; no publication claim. |
| `publication_pending` | Durable publication intent exists; attempt may be absent or in progress. |
| `publication_confirmed` | Provider acceptance confirmed; no delivery or execution claim. |
| `publication_uncertain` | Provider acceptance cannot be proven or disproven; stable-identity reconciliation required. |
| `delivered` | One delivery identity is available to a consumer; no claim or authorization implied. |
| `claimed` | A worker holds a new claim/lease and fence after current validation. |
| `active` | The valid claimant is processing; protected effects remain gated by fence and current state. |
| `renewal_requested` | Renewal requested; existing authority is not extended until confirmed. |
| `renewal_confirmed` | Lease authority is confirmed under the returned/current fence. |
| `renewal_uncertain` | Renewal outcome unknown; worker MUST stop new protected effects until reconciled. |
| `expired` | Lease time boundary passed; this alone is not Workflow terminality. |
| `revoked` | Authority explicitly withdrawn; protected effects prohibited. |
| `replaced` | A newer claim/fence supersedes the worker; old worker is stale. |
| `confirmed_lease_lost` | Loss is definitive; no protected effect or success acknowledgement is allowed. |
| `acknowledged` | Provider delivery acknowledged after all acknowledgement eligibility rules; not semantic-completion or Evidence proof. |
| `negatively_acknowledged` | Delivery explicitly released/rejected under retry classification; not a Workflow terminal transition. |
| `dead_lettered` | Delivery moved out of ordinary retry flow; not automatically a Workflow terminal state. |

Claims MUST use monotonic fencing or an equivalent adapter mechanism that
lets every protected durable effect reject stale/replaced workers. Claim,
renewal, replacement, revocation, and loss transitions MUST be attributable.
No lease duration, visibility timeout, heartbeat interval, acknowledgement
deadline, or publication timeout is selected by this draft.

On uncertain renewal a worker MAY finish only non-protected local cleanup; it
MUST NOT initiate or commit protected effects, publish a result, or acknowledge
success until authority is reconciled. Confirmed loss is irreversible for that
claim identity.

A2-EXECUTION owns production of bounded worker heartbeat and renewal-request
inputs and observation of renewal responses. A2-QUEUE validates those inputs
and owns renewal acceptance/denial, authoritative lease visibility/state,
fence state, renewal uncertainty, and confirmed lease loss. A2-DEPLOYMENT owns
runtime transport, clock behavior, operational cadence/configuration, and
provider capability mapping. A2-SECURITY owns heartbeat field approval,
disclosure, and trust policy.

A heartbeat, liveness signal, or renewal request alone MUST NOT renew a lease,
extend authority, alter Workflow state, prove execution progress or success,
make result publication eligible, or make acknowledgement eligible. Only an
explicit renewal operation confirmed by the authoritative Queue/adapter lease
mechanism MAY extend authority. Exact cadence, jitter, retry counts, payload
bounds, and timing remain unresolved configuration or release-measurement
inputs.

## 7. Results, persistence, and acknowledgement

1. Result acceptance MUST bind semantic request, message, Workflow attempt,
   Workflow-authorized result phase/slot, stable producer result, current
   worker, delivery, claim/fence, submission occurrence, applicable versions,
   and integrity metadata.
2. A duplicate transport delivery or result submission MAY converge only after
   current binding, authorization, fence, integrity, and owner-canonicalization
   checks. Recognition MUST return the existing accepted effect without
   rewriting it.
3. A conflicting submission MUST fail closed, emit attributable conflict and
   required Security evidence, and preserve the accepted result/Evidence
   unchanged. Queue MUST NOT classify it as valid alternate Evidence.
4. Current Workflow terminal/cancellation state, Evidence deletion state,
   authorization/policy, and fence MUST be checked before each accepted
   protected effect.
5. Required result, Workflow state, provenance, audit, and Evidence-reference
   effects MUST durably commit before Queue acknowledgement becomes eligible,
   according to the respective owner contracts.
6. If commit succeeds and acknowledgement fails or is uncertain, redelivery
   MUST converge idempotently on the existing accepted effect. Acknowledgement
   MAY be retried without rerunning semantic work.
7. Negative acknowledgement MAY occur only with an attributable retry
   classification. It MUST NOT erase provenance, imply cancellation, or bypass
   bounded retry/poison rules.

A2-DATABASE exclusively owns physical persistence, physical transaction
design, constraints, indexes, locking, compare-and-set, fencing enforcement,
models, and migrations. A2-EVIDENCE owns Evidence identity, Evidence-reference
issuance, Evidence semantic finalization, completeness, provenance, Evidence
and artefact integrity meaning, compatibility, and deletion semantics.
A2-AGENT-WORKFLOW owns Workflow state and transition effects. A2-QUEUE owns
acknowledgement eligibility and transport semantics. This draft defines no
physical schema, makes A2-EVIDENCE no joint owner of physical Database
persistence, and does not authorize DB-003.

Layered result deduplication ownership remains separate: A2-EXECUTION owns
producer-result production, output, and contract-compatible serialization;
A2-AGENT-WORKFLOW owns semantic result acceptance, the accepted-result
transition, and result-slot/attempt meaning; A2-EVIDENCE owns Evidence
identity, canonical Evidence content, Evidence duplicate/conflict
classification, finalization, and preservation of accepted Evidence;
A2-QUEUE owns duplicate transport delivery, redelivery convergence, stable
transport binding, and prevention of duplicate accepted semantic effects from
transport duplication; A2-DATABASE owns physical uniqueness, locking,
transaction enforcement, and durable deduplication; A2-SECURITY owns
canonicalization algorithm approval, integrity algorithm policy, key policy,
and required Security-event handling.

## 8. Retry and poison-work model

| Category | Required separation |
|---|---|
| Queue transport redelivery | Same message, new delivery identity; no automatic Workflow attempt. |
| Queue retry | Provider/adapter reprocessing after classified delivery failure; bounded by configured policy. |
| Workflow infrastructure retry | Workflow-owned recovery decision; may create/continue an attempt only under Workflow rules. |
| Workflow semantic repair | Explicit semantic action with current authorization/provenance; not a transport retry. |
| Model/provider failure | Execution/provider classification external to Queue; not automatically poison work. |
| Deterministic application failure | Repeatable semantic/application failure; Workflow owns outcome and repair. |
| Security-policy rejection | Fail closed, no ordinary retry unless current Security policy explicitly permits re-evaluation. |
| Poison work | Repeatedly unprocessable transport/envelope work under a selected bounded poison policy. |
| Cancellation | Current cancellation intent/state gates work and effects; not a retry class. |
| Dead-letter movement | Administrative transport disposition after bounded handling; not Workflow terminality. |

All retries MUST be bounded. Retry counts, poison bounds, backoff schedules,
and re-drive limits are `CONFIGURATION_VALUE_NOT_YET_SELECTED`; this contract
does not invent them. Ordinary application failure MUST NOT be relabelled
poison merely to bypass Workflow handling.

A2-QUEUE owns provider-neutral transport retry categories, Queue retry-attempt
attribution, and publication/delivery retry boundaries. A2-AGENT-WORKFLOW owns
Workflow infrastructure-retry meaning, semantic failure and repair
classification, attempt creation, and repair allowance. A2-DEPLOYMENT owns
only configured retry counts, backoff, jitter, timeouts, capacity, and
provider-adapter behavior. Deployment configuration MUST NOT relabel Workflow
outcomes, semantic failures, Execution outcomes, Security rejections,
application failures, repairs, or cancellations.

Queue publication retry, delivery retry, redelivery, claim replacement,
lease-loss recovery, replay, re-drive, and checkpoint resume MUST NOT
increment, decrement, reset, or recreate `repair_attempts_used`, and MUST NOT
grant additional repair allowance. `repair_attempts_used` remains
A2-AGENT-WORKFLOW-owned, is constrained to `0..1`, and MAY change from `0` to
`1` only when Workflow validly enters `REPAIRING` under
`CONTRACT-WORKFLOW-001`. No Queue operation may authorize a second repair or
bypass the repaired candidate's required Workflow sequence.

A repaired candidate MUST complete the Workflow-owned sequence:

1. `EXECUTING_BUGGY`;
2. then `EXECUTING_FIXED`.

Queue publication retry, delivery retry, redelivery, claim replacement,
lease-loss recovery, replay, re-drive, and checkpoint resume MUST NOT skip
`EXECUTING_BUGGY`, skip `EXECUTING_FIXED`, reverse their required order, treat
transport recovery as completion of either state, authorize a second repair,
or produce a shortcut from `REPAIRING` directly to a later Workflow state.
Workflow remains authoritative under `CONTRACT-WORKFLOW-001`; Queue owns no
lifecycle transition.

## 9. Checkpoints, replay, cancellation, and stale work

A checkpoint transported through Queue MUST be a bounded opaque reference
bound to semantic request, Workflow attempt, applicable lifecycle state,
applicable contract/schema/version metadata, and required integrity metadata.
When checkpoint production occurred under Queue-managed claimed work, the
checkpoint MUST additionally bind to the producing claim and fence. No claim,
lease, or fence may be fabricated when Queue-managed claimed work did not
govern checkpoint production. Workflow remains the authority that decides
whether a checkpoint is committed, eligible, compatible, and resumable. Queue
reference presence or claim binding alone does not make it authoritative.
Consumers MUST reject corrupt, substituted, deleted, cancelled, superseded,
or incompatible checkpoints. Checkpoint compatibility rules require Workflow,
Execution, Security, and Integration review.

Checkpoint resume MUST NOT increment, decrement, reset, or recreate
`repair_attempts_used`, grant repair allowance, authorize a second repair, or
bypass the repaired candidate's required `EXECUTING_BUGGY` then
`EXECUTING_FIXED` sequence. It MUST NOT treat transport recovery as completion
of either state or shortcut from `REPAIRING` to a later Workflow state.

Replay/redelivery/re-drive MUST revalidate current schema, policy,
authorization, cancellation, terminality, deletion, supersession, checkpoint,
and fence state. Stored authorization context is provenance, not current
authority. A terminal, cancelled, revoked, deleted, or superseded operation
cannot be reopened by Queue activity.

## 10. Dead-letter administration

A dead-letter record MUST contain only bounded, secret-free metadata and
immutable original provenance. Inspection, export, deletion, and re-drive MUST
be separate least-privilege actions, each bound to an attributable
`replay_or_redrive_actor_reference` (or equivalent administrator reference),
current authorization, and current policy. Export MUST reapply current
redaction/disclosure policy.

There is no automatic re-drive. Re-drive MUST validate current schema,
Security policy, authorization, cancellation, terminal state, deletion, and
compatibility. It creates a new `queue_delivery_id` while preserving semantic
request/message identity and original provenance. It MUST NOT reuse stale
authorization, bypass retention/deletion, or recreate deleted Evidence.
Dead-letter retention is external/unselected and deletion actions MUST remain
attributable.

## 11. Integrity model

Logical integrity metadata contains:

| Element | Requirement |
|---|---|
| algorithm identifier | Identifies the approved digest/MAC/signature mechanism; exact choice is `EXTERNAL_OWNER_POLICY_REQUIRED`. |
| canonicalization version | Selects deterministic bytes; unknown versions fail closed; exact algorithm is `EXTERNAL_OWNER_POLICY_REQUIRED`. |
| digest scope | Explicitly lists the bound envelope fields/references and excludes mutable provider metadata. |
| digest value or opaque integrity reference | Bounded value/reference transported only when allowed by Security policy. |
| verifier responsibility | Producer computes/obtains it; adapter preserves it; consumer verifies it before protected effects where required. |
| mismatch behavior | Fail closed, do not acknowledge success, preserve secret-free attribution, and emit the required Security event. |

Exact algorithm, canonicalization, MAC/signature requirements, and key custody
are `EXTERNAL_OWNER_POLICY_REQUIRED`. An unkeyed checksum demonstrates content
consistency only and is not proof of producer authenticity.

Queue-envelope canonicalization, Execution-result canonicalization, and
Evidence/artefact canonicalization MUST remain separately defined. Queue MUST
NOT define canonical Evidence equality; A2-EVIDENCE owns that semantic
classification.

## 12. Authorization, Security, retention, and observability

- Current authorization and current policy MUST be revalidated at publication,
  claim/protected-effect, result acceptance, and administrative re-drive when
  the owning policies require it. Queue receipt and stored references never
  grant authority.
- Security events MUST be emitted through the Security-owned boundary for
  redaction failure, prohibited content, integrity mismatch, identity/binding
  mismatch, stale-worker effect attempts, conflicting results, replay-policy
  rejection, and unauthorized dead-letter action. Exact event schema,
  disclosure, severity, and retention are `EXTERNAL_OWNER_POLICY_REQUIRED`.
- Transport metadata, operational logs, publication/claim audit, dead-letter
  metadata, semantic request/result records, Evidence, and artefacts have
  separate retention categories. One category MUST NOT silently determine
  another. Exact retention is `EXTERNAL_OWNER_POLICY_REQUIRED` or the explicit
  unselected dead-letter configuration in section 16.
- Deletion tombstones or owner-approved equivalent state MUST prevent replay or
  re-drive from recreating deleted Evidence. Queue does not define Evidence
  deletion semantics.
- Observability MUST expose bounded, secret-free state transitions, latency
  measurements, retry/dead-letter classifications, and correlation references.
  It MUST NOT expose prohibited payloads or treat log/event presence as
  semantic completion, Workflow ordering, or Evidence proof.

Every future provider-adapter capability mapping MUST document encryption in
transit; encryption at rest or approved compensating controls; separate
least-privilege data-plane and control-plane service identities; credential
and secret-injection boundaries; and authorization and administrative-operation
boundaries. Its minimum operational signal capability MUST cover publication
failure, Queue depth, oldest-message age, delivery/redelivery, lease expiry,
renewal failure, heartbeat loss, dead-letter growth, stale-claim rejection,
acknowledgement latency, required-result-persistence latency, and worker or
consumer drain failure. Observability MUST NOT be treated as Workflow success,
Evidence proof, or semantic completion.

## 13. Workflow lifecycle boundary

Queue states are transport/publication facts, not Workflow states. Queue
ordering is not Workflow event ordering; delivery, claim, expiry,
acknowledgement, negative acknowledgement, and dead-letter movement MUST NOT
invent or force Workflow transitions. A2-AGENT-WORKFLOW owns attempt creation,
semantic execution-state lifecycle, repair, cancellation meaning, lifecycle
race outcome, terminality, and accepted-result transitions. A2-EXECUTION owns
worker/runtime execution behavior, execution-fact production, worker
cancellation observation, bounded cleanup, and producer-result production.
A2-QUEUE owns transport only and owns neither Workflow lifecycle nor worker
runtime behavior; it supplies attributable facts for Workflow to consume under
its contract.

## 14. Provider-neutral adapter conformance

An adapter MUST map provider operations to this logical model without
collapsing identities or weakening validation, fencing, idempotency,
commit-before-ack, bounded retry, redaction, authorization, integrity, or
dead-letter rules. Provider receipts and delivery tokens MAY be stored as
opaque operational metadata but MUST NOT become semantic identities.

Provider extensions are allowed only as bounded, non-semantic adapter metadata.
Any extension that changes retries, ordering, identity, authorization,
acknowledgement, lease loss, result acceptance, cancellation, or dead-letter
meaning requires a versioned contract change and affected consumer review.

The deterministic provider-neutral local/test adapter MUST run from a clean
checkout; require no production provider or production service credentials;
contain no committed secrets; use no shared production Queue or Database
state; isolate test messages, claims, dead-letter data, and artefact references;
and preserve the same validation, identity, redelivery, fencing, retry,
acknowledgement, failure, and dead-letter semantics as an authorized production
adapter. Provider-specific tests MAY be additive but MUST NOT replace the
common provider-neutral conformance suite. This correction authorizes no
runtime or test implementation.

Every future provider adapter MUST include the Security/access and minimum
operational-signal mapping required by section 12. Provider capability mapping
cannot weaken those requirements or turn operational observations into
semantic success.

## 15. Compatibility and transitions

1. Breaking semantic, identity, required-field, canonicalization, validation,
   authorization, fencing, acknowledgement, retry, or lifecycle changes require
   a new major contract/schema version and migration/replay policy review.
2. Additive optional allowlisted fields require a compatible minor version and
   affected consumer review. Consumers MUST safely reject unsupported required
   semantics; they MUST NOT guess.
3. Clarifications with no behavior change MAY use a patch version.
4. Every draft revision MUST record compatibility impact. Draft does not mean
   unversioned.
5. Producers MUST NOT publish an unsupported version. Consumers MUST fail
   closed on unknown schema/canonicalization versions and prohibited fields.
6. Mixed-version rollout requires declared producer/consumer compatibility,
   rollback behavior, and Integration/Deployment evidence. Existing work MUST
   remain pinned to its governing semantic versions.
7. Before acceptance, a consumer-review correction MAY advance only the draft
   suffix while retaining the proposed major/minor/patch version. Draft.1 to
   draft.2 does so here; draft.1 is not an accepted compatibility baseline.

## 16. Unresolved-value register

Each value is assigned exactly one classification; none is selected here.

| Unresolved value | Classification |
|---|---|
| provider choice | `CONFIGURATION_VALUE_NOT_YET_SELECTED` |
| provider receipt behavior | `IMPLEMENTATION_DETAIL_DEFERRED` |
| field lengths | `CONFIGURATION_VALUE_NOT_YET_SELECTED` |
| collection cardinalities | `CONFIGURATION_VALUE_NOT_YET_SELECTED` |
| payload-size limits | `CONFIGURATION_VALUE_NOT_YET_SELECTED` |
| authorization-freshness intervals | `EXTERNAL_OWNER_POLICY_REQUIRED` |
| lease durations | `CONFIGURATION_VALUE_NOT_YET_SELECTED` |
| visibility timeouts | `CONFIGURATION_VALUE_NOT_YET_SELECTED` |
| heartbeat intervals | `CONFIGURATION_VALUE_NOT_YET_SELECTED` |
| heartbeat/renewal cadence, jitter, retry counts, and payload bounds | `CONFIGURATION_VALUE_NOT_YET_SELECTED` |
| acknowledgement deadlines | `CONFIGURATION_VALUE_NOT_YET_SELECTED` |
| publication timeouts | `CONFIGURATION_VALUE_NOT_YET_SELECTED` |
| retry counts | `CONFIGURATION_VALUE_NOT_YET_SELECTED` |
| poison-work bounds | `CONFIGURATION_VALUE_NOT_YET_SELECTED` |
| backoff schedules | `CONFIGURATION_VALUE_NOT_YET_SELECTED` |
| dead-letter retention | `EXTERNAL_OWNER_POLICY_REQUIRED` |
| re-drive limits | `CONFIGURATION_VALUE_NOT_YET_SELECTED` |
| concurrency | `BLOCKED_BY_MISSING_MEASUREMENT_INPUT` |
| throughput | `BLOCKED_BY_MISSING_MEASUREMENT_INPUT` |
| latency | `RELEASE_GATE_INPUT_REQUIRED` |
| checksum algorithms | `EXTERNAL_OWNER_POLICY_REQUIRED` |
| canonicalization algorithms | `EXTERNAL_OWNER_POLICY_REQUIRED` |
| MAC/signature requirements | `EXTERNAL_OWNER_POLICY_REQUIRED` |
| key custody | `EXTERNAL_OWNER_POLICY_REQUIRED` |
| provider capacity | `BLOCKED_BY_MISSING_MEASUREMENT_INPUT` |
| operational thresholds, alert levels, sampling, and capacity | `RELEASE_GATE_INPUT_REQUIRED` |

Exact operational thresholds, alert levels, sampling, capacity, and release
pass/fail values remain Deployment configuration, Security policy, or
Evaluation measurement/release-gate input; none is selected by this draft.

## 17. Authoritative 26-row requirements matrix

Abbreviations: `Cfg` = configuration points; `Ext` = external dependencies;
`Impl` = implementation evidence; `Rel` = release evidence; `Compat` =
compatibility impact. `DB3` never authorizes DB-003.

| ID / drafting status | Title | Normative decision | Owner | Consumers | Accepted constraints | Rejected alternatives | Cfg | Ext | Impl | Rel | Unresolved values | Compat | DB3 | Workflow | Security | Evaluation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `QUEUE-REQ-001` — `READY_FOR_DRAFT` | Provider-neutral Queue ownership and boundary | A2-QUEUE owns transport publication, delivery, acknowledgement eligibility, retry, and dead-letter semantics only; Workflow owns semantic lifecycle and Execution owns worker/runtime behavior. All other owners retain their semantics. | A2-QUEUE | All producers, consumers, and ten section 18 reviewers | Queue facts cross owner boundaries only through versioned, attributable contracts | Provider choice or Queue receipt silently defining API, Workflow, Execution, Evidence, authorization, or release meaning | Provider unselected | All owner contracts and written reviews | Boundary/conformance scenarios across every consumer | All affected owners re-review draft.2; silence is not acceptance | External policies and provider values remain classified | Boundary collapse or provider-specific semantics is breaking | No physical design or DB-003 authorization | Owns attempts, semantic lifecycle/races, repair, cancellation meaning, terminality, and accepted-result transitions | Controls cannot weaken across adapters; authority is never inferred from receipt | Implementation evidence and release gates remain separate |
| `QUEUE-REQ-002` — `READY_FOR_DRAFT` | Queue, semantic, delivery, attempt, result and Evidence identifier separation | All identities remain separately typed; `workflow_attempt_id` binds run, Workflow step occurrence, step kind, occurrence, and zero-based `attempt_index`. Queue delivery/claim/lease/redelivery/receipt identities cannot create, replace, or redefine it. | A2-QUEUE boundary; A2-AGENT-WORKFLOW attempt authority | Backend, Workflow, Database, Evidence, Execution, Integration | Stable semantic/message/publication identities; new delivery/claim identities; owner-generated attempt/result/Evidence identities | Receipt-as-ID, tracing-as-ID, delivery/transition-as-universal-attempt-parent, result-as-Evidence, or credential-as-identity | Formats deferred | Auth and owner identity authorities | Round-trip, binding, collision, and cross-type rejection checks | Cross-consumer compatibility | Physical types `IMPLEMENTATION_DETAIL_DEFERRED` | Identity collapse or changed authority is breaking | Future records only; DB-003 unauthorized | Owns attempt creation/meaning; a lifecycle transition may reference an attempt but is not its universal parent | Identity/binding mismatch fails closed and is attributable | Preserve attempt, result, and Evidence provenance |
| `QUEUE-REQ-003` — `READY_FOR_DRAFT` | Enqueue and semantic-request idempotency | API/client semantic-request, Backend durable-request, enqueue/publication, Queue-message, delivery, Workflow-attempt, and result-acceptance idempotency MUST remain separate; stable semantic/message/publication identities reconcile duplicate or uncertain enqueue without a second semantic effect. | A2-QUEUE + A2-BACKEND boundary | Backend, Database, Workflow, Integration | Reuse the original semantic/message binding for a confirmed duplicate publication request | Provider receipt as semantic key; blind new request after timeout; enqueue success as execution success | Publication timeout unselected | API idempotency policy, Database uniqueness design, provider mapping | Duplicate, timeout, retry, and uncertain-publication scenarios | Backend and Integration acceptance | API duplicate response external; receipt behavior deferred | Key or duplicate meaning changes are breaking | Future uniqueness/intent records only; unauthorized | Duplicate enqueue does not create an attempt or force state | Current eligibility and authorization still apply; abuse/replay checks required | Measure duplicate and uncertainty rates without redefining success |
| `QUEUE-REQ-004` — `READY_FOR_DRAFT` | Producer-result identity, duplicate comparison and deduplication | `producer_result_id` identifies one Workflow-authorized result slot/submission for one attempt and phase and remains stable across redelivery, ack retry, worker restart/replacement, and same-attempt checkpoint recovery; per-submission worker/delivery/claim/fence/occurrence/version/integrity facts remain validated. | Layered Execution/Workflow/Evidence/Queue/Database/Security ownership | Workflow, Database, Evidence, Execution, Security | New result ID only for a new Workflow-authorized attempt or separately defined phase/slot; owner canonicalizations remain separate | Worker/delivery/claim change forcing a result ID; result ID as Evidence ID; last-write-wins; Queue-defined Evidence equality or valid-alternate conflict | None | Workflow result-slot policy, Execution serialization, Security algorithms, Evidence classification, Database enforcement | Duplicate/conflict, replacement-worker, checkpoint, tamper, stale-fence, and owner-canonicalization race tests | Integrity and Evidence consumer gates | Algorithms `EXTERNAL_OWNER_POLICY_REQUIRED` | Result identity, equality, or conflict semantics changes are breaking | Physical uniqueness/locking/deduplication only; DB-003 unauthorized | Owns result-slot/attempt meaning, semantic acceptance, and accepted-result transition | Approves algorithms/policy; conflicts and integrity/binding failures emit required events | Owns Evidence identity/content/duplicate-conflict classification/finalization and preserves accepted Evidence |
| `QUEUE-REQ-005` — `READY_FOR_DRAFT` | Provider-neutral at-least-once delivery guarantee | A confirmed publication MUST NOT be silently lost. It MUST remain eligible for delivery or redelivery until either:<br><br>- acknowledgement becomes valid after the required durable effects commit; or<br>- an explicit, attributable transport disposition blocks ordinary delivery under current policy, cancellation, terminal-state, deletion, Security, or bounded poison/dead-letter rules.<br><br>A transport disposition does not itself create a Workflow terminal state. Consumers MUST tolerate one or more deliveries without claiming provider-level exactly-once execution. | A2-QUEUE | Workflow, Execution, Deployment, Integration | At-least-once transport, idempotent consumer convergence, bounded retry, cancellation protection, current-policy revalidation, and no silent loss | At-most-once loss; exactly-once provider claims; unbounded retry; acknowledgement or dead-letter disposition as semantic completion or Workflow terminality | Acknowledgement and visibility timing unselected | Provider adapter and Deployment policy | Lost-delivery, duplicate-delivery, ack-loss, restart, and recovery tests | Reliability and interoperability gates | Timing `CONFIGURATION_VALUE_NOT_YET_SELECTED` | Weaker delivery or stronger semantic claims are breaking | Future delivery/effect records only; unauthorized | Delivery count and dead-letter disposition do not define attempts, outcomes, or terminality | Repeated delivery never refreshes authority or bypasses current checks | Measure loss, duplicate delivery, recovery, and convergence |
| `QUEUE-REQ-006` — `READY_FOR_DRAFT` | Redelivery semantics and attributable delivery records | Every delivery/redelivery occurrence MUST have a distinct attributable delivery record bound to the stable Queue message and provenance; redelivery revalidates current schema, policy, authorization, cancellation, terminal, deletion, checkpoint, and fence state. | A2-QUEUE | Workflow, Execution, Auth, Security, Database, Evaluation | Same semantic/message identity, new delivery identity, preserved original provenance | Reusing a delivery ID; treating redelivery as new semantic work, refreshed authorization, or a new Workflow attempt | Delivery-attempt limits unselected | Adapter delivery mapping and Auth/Security policy | Redelivery, revocation, deletion, cancellation, stale-checkpoint, and provenance checks | Security and recovery gates | Retry/timing values `CONFIGURATION_VALUE_NOT_YET_SELECTED`; freshness external | Delivery-record or replay-validation weakening is breaking | Possible future delivery records only; DB-003 unauthorized | Redelivery alone creates no attempt and cannot reopen terminal work | Stored authorization is provenance only; invalid replay fails closed | Metrics use attributable delivery records, not semantic outcomes |
| `QUEUE-REQ-007` — `READY_FOR_DRAFT` | Required durable persistence before acknowledgement | Required durable effects commit under their owner contracts before Queue acknowledgement eligibility. Database exclusively owns all physical persistence/transactions/constraints/indexes/locking/CAS/fencing/models/migrations; Evidence owns Evidence semantics; Workflow owns state/transition effects; Queue owns ack eligibility/transport. | Respective semantic owners; A2-DATABASE exclusive physical owner; A2-QUEUE acknowledgement boundary | Database, Evidence, Workflow, Deployment | Commit before ack; retry ack idempotently after commit; no joint Evidence ownership of physical Database persistence | Ack before commit; ack as completion/Evidence proof; Queue-defined physical schema; rerun after ack uncertainty | Ack deadlines unselected | Database, Evidence, and Workflow owner contracts | Crash-before-commit, crash-after-commit, ack-loss, and redelivery tests | Recovery and durability gate | Physical transaction `IMPLEMENTATION_DETAIL_DEFERRED` | Commit/ack ordering or owner-boundary changes are breaking | No physical schema; DB-003 unauthorized | Owns Workflow state and transition effects; ack does not define lifecycle | Owns algorithm/key/event policy; Evidence alone owns Evidence/artefact integrity meaning | Evidence identity/reference issuance/finalization/completeness/provenance/integrity meaning/compatibility/deletion remain A2-EVIDENCE-owned |
| `QUEUE-REQ-008` — `READY_FOR_DRAFT / NUMERIC_VALUES_DEFERRED` | Claims and leases | A claim/lease grants one currently valid, attributable, fenced right to perform protected work for a delivery; it MUST NOT create, replace, redefine, or become the parent of the Workflow attempt bound to run/step occurrence/kind/occurrence/attempt index. | A2-QUEUE claim boundary; A2-AGENT-WORKFLOW attempt authority | Workflow, Execution, Database, Deployment, Auth | Distinct claim identity, worker binding, current validation, and monotonic fence or equivalent | Unfenced claims; time-only or worker assertion as authority; receipt/claim as attempt | Lease duration and visibility timeout unselected | Database/adapter claim design and Auth policy | Claim, replacement, revocation, stale-worker, attempt-binding, and authorization tests | Reliability and authorization gates | Timing `CONFIGURATION_VALUE_NOT_YET_SELECTED` | Claim authority or attempt/fence semantics changes are breaking | Future claim/fence records only; DB-003 unauthorized | Owns attempt creation/meaning; claim does not create an attempt and lease expiry is not terminal | Claim and protected effects require current authorization; stale effect attempts are events | Measure claim contention and validity without defining semantics |
| `QUEUE-REQ-009` — `READY_FOR_DRAFT / TIMING_VALUES_DEFERRED` | Lease renewal, uncertainty, loss and abandoned-worker recovery | Execution produces bounded heartbeat/renewal inputs and observes responses; Queue validates and authoritatively accepts/denies renewal and owns lease visibility/fence/uncertainty/loss. Inputs alone extend no authority or semantic eligibility; only explicitly confirmed renewal does. | A2-QUEUE authority; A2-EXECUTION input/observation; A2-DEPLOYMENT transport/clock/config; A2-SECURITY field/trust policy | Workflow, Execution, Database, Deployment, Security | Attributable renewal request/response/confirmation/loss and replacement fencing; signals prove no progress/success | Optimistic or signal-implied renewal/progress/success; protected effects during uncertainty; reviving a lost claim | Lease, heartbeat, cadence, jitter, retry, payload, renewal, and visibility values unselected | Database/adapter design, Deployment mapping, Security policy | Renewal-timeout, partition, heartbeat-loss, abandoned-worker, replacement, and stale-effect fault tests | Reliability and recovery gate | Timing/bounds `CONFIGURATION_VALUE_NOT_YET_SELECTED` | Loss/renewal authority changes are breaking | Future lease-transition records only; DB-003 unauthorized | Signals do not alter state; expiry/loss alone is not terminal | Owns heartbeat fields/disclosure/trust; confirmed-lost workers cannot publish effects | Measure renewal uncertainty, abandonment, recovery, and stale rejection |
| `QUEUE-REQ-010` — `READY_FOR_DRAFT / COUNTS_DEFERRED` | Transport retry classification and retry-attempt handling | Queue owns attributable bounded provider-neutral publication/delivery retry categories and boundaries; Workflow owns infrastructure-retry/semantic-failure/repair meaning, attempt creation, and the `0..1` repair allowance; Deployment configures counts/backoff/jitter/timeouts/capacity/adapter behavior only. | A2-QUEUE transport classification boundary | Workflow, Deployment, Integration, Evaluation | Queue retries/recovery/replay/resume never alter/reset/recreate `repair_attempts_used`; only valid Workflow entry to `REPAIRING` changes `0` to `1`; repaired candidates complete `EXECUTING_BUGGY` then `EXECUTING_FIXED` | Infinite retry; retry counter as Workflow attempt; Deployment relabelling outcomes/failures/repairs/cancellation; Queue skipping/reversing/completing either required execution state or authorizing a second repair | Counts, backoff, jitter, and timeouts unselected | Workflow semantic classification and Deployment operational configuration | Retry exhaustion/classification, one-repair and required-sequence invariance, backoff, and fault-injection checks | Operational reliability gate | Counts/backoff `CONFIGURATION_VALUE_NOT_YET_SELECTED` | Category/repair/sequence meaning is breaking; count changes are operationally sensitive | No effect; DB-003 unauthorized | Owns attempts, infrastructure retry, semantic failure/repair classification, repair allowance, and `EXECUTING_BUGGY` then `EXECUTING_FIXED` lifecycle transitions | Security rejection is not ordinary retry unless current policy permits re-evaluation | Reliability metrics retain category and attempt provenance |
| `QUEUE-REQ-011` — `READY_FOR_DRAFT / RETENTION_DEFERRED` | Poison-work and dead-letter handling | Poison work is bounded unprocessable transport/envelope work; dead-letter movement follows bounded handling and all inspect/export/delete/re-drive actions preserve immutable provenance, require least privilege/current policy, and are attributable. | A2-QUEUE | Security, Auth, Workflow, Deployment, Integration | No automatic re-drive; new delivery identity on authorized re-drive; current validation and redaction | Infinite poison retry; ordinary application failure as poison; auto re-drive; stale auth; mutable provenance | Poison bounds, re-drive limits, and retry counts unselected | Retention, authorization, Workflow classification, and provider policy | Exhaustion plus inspect/export/delete/re-drive, revocation, and deletion tests | Administrative, Security, and operational review | Dead-letter retention external; counts `CONFIGURATION_VALUE_NOT_YET_SELECTED` | Poison/DLQ meaning or action model changes are breaking | Future admin records only; DB-003 unauthorized | Dead-letter is not terminal and cannot bypass cancellation/deletion | Least privilege, current authorization, disclosure, and Security events required | DLQ metrics are transport evidence, not Workflow outcomes |
| `QUEUE-REQ-012` — `READY_FOR_QUEUE_OWNED_DRAFT` | Queue ordering versus authoritative Workflow event ordering | Queue ordering/delivery/retry/acknowledgement/expiry/dead-letter position MUST NOT define Workflow event ordering or attempt identity; events/transitions may reference attempts but are not universal attempt parents. | A2-QUEUE + A2-AGENT-WORKFLOW boundary | Backend, Workflow, Evidence, UI, Integration | Attributable Queue facts may be consumed under Workflow ordering and attempt rules | Queue FIFO/sequence/provider timestamp/transition as Workflow event order, attempt parent, or Evidence proof | None | Workflow event-ordering and attempt contract | Out-of-order, duplicate, delayed, redelivered, and attempt-binding cross-state scenarios | Workflow and consumer acceptance | None | Ordering/attempt-boundary collapse is breaking | No event model or DB-003 authorization | Owns authoritative events, transitions, attempt creation/meaning, and terminality | Prevent false ordering/completion claims and preserve attribution | No transport-derived success or event sequence |
| `QUEUE-REQ-013` — `READY_FOR_DRAFT / CAPACITY_DEFERRED` | Claim concurrency, locking and prevention of competing authoritative effects | Claim acquisition and every protected durable effect MUST use monotonic fencing, locking, uniqueness, compare-and-set, or an owner-approved equivalent so concurrent, replaced, or stale workers cannot commit competing authoritative effects. | A2-QUEUE + A2-DATABASE/A2-AGENT-WORKFLOW boundary | Workflow, Execution, Database, Evidence, Deployment | One accepted authority/effect under races; later fence rejects earlier workers | Process-local lock, time alone, last-write-wins, or worker assertion as authority | Concurrency and timing unselected | Database atomicity/locking design and Workflow effect rules | Concurrent-claim, replacement, stale-commit, result, cancellation, and ack race tests | Integrity, reliability, and capacity gates | Concurrency `BLOCKED_BY_MISSING_MEASUREMENT_INPUT` | Fence/locking/accepted-effect changes are breaking | Future constraints/transactions only; DB-003 unauthorized | Owns authoritative transition/effect acceptance | Stale/competing effect attempts fail closed and emit Security evidence | Measure contention and capacity without weakening correctness |
| `QUEUE-REQ-014` — `READY_FOR_DRAFT` | Cancellation propagation and atomic race handling | Queue owns cancellation/control transport only; Workflow owns attempt creation, semantic lifecycle, repair, cancellation meaning, lifecycle-race outcome, terminality, and accepted-result transitions; Execution owns runtime behavior/facts, worker observation, bounded cleanup, and producer-result production. | A2-QUEUE boundary with A2-AGENT-WORKFLOW and A2-EXECUTION | Backend, Workflow, Execution, Database, Auth, Security | Durable attributable cancellation intent; current authorization; one race-safe effect cutoff | Accepted request means worker observation/cleanup; acknowledgement means cancellation completed; Queue chooses terminal state/runtime behavior; check-then-act race | Delivery/timing values unselected | Workflow cancellation/lifecycle semantics; Execution runtime behavior; Database atomicity; Auth/Security policy | Cancellation-versus-claim/result/commit/ack/replay race and fence tests | Cross-owner cancellation and reliability gates | Control mechanism `IMPLEMENTATION_DETAIL_DEFERRED` | Cancellation/lifecycle/runtime ownership or cutoff changes are breaking | Future intent/effect boundary only; DB-003 unauthorized | Owns cancellation/lifecycle/race/terminal outcome and accepted transition | Current auth/policy and attributable events; replay cannot bypass cancellation | Cancelled work cannot produce measured success |
| `QUEUE-REQ-015` — `READY_FOR_DRAFT` | Checkpoint references, compatibility and resume boundary | Queue transports only bounded opaque checkpoint references bound to semantic request, Workflow attempt, applicable lifecycle, versions, and integrity; producing claim/fence is additionally required only when Queue-managed claimed work governed production and MUST NOT otherwise be fabricated. | A2-QUEUE transport boundary with Workflow/Execution | Workflow, Execution, Evidence, Security, Integration | Workflow alone decides committed/eligible/compatible/resumable; resume never alters the `0..1` repair allowance or skips/reverses/completes `EXECUTING_BUGGY` then `EXECUTING_FIXED` | Embedded bytes; unconditional claim/fence; resume by reference/claim presence; stale/cross-attempt substitution; resume authorizing repair or shortcutting the required sequence | Reference limits unselected | Owner checkpoint format, Workflow resume/repair rules, Security integrity policy | Claimed/unclaimed production, tamper, deletion, cancellation, supersession, mixed-version, resume, repair, and sequence-invariance tests | Compatibility and Security gates | Format and algorithms external/deferred | Resume/binding/version/repair-sequence rules are breaking | Future reference only; no physical type or DB-003 authorization | Owns checkpoint commitment/eligibility/compatibility/resume and attempt/lifecycle/repair sequence meaning | Integrity/deletion mismatch fails closed and is attributable | No stale/incompatible resumed result acceptance |
| `QUEUE-REQ-016` — `READY_FOR_DRAFT / BYTE_LIMIT_DEFERRED` | Bounded payload envelope, metadata and opaque references | Only the section 5 allowlist of bounded, versioned, secret-free metadata and opaque input/checkpoint/result/Evidence references MAY be serialized; checkpoint claim/fence binding is conditional on Queue-managed claimed production; producers validate/redact and consumers validate defensively. | A2-QUEUE | All producers/consumers, Evidence, Execution, Security, Deployment | Allowlist-first fields, explicit integrity scope/version, owner-approved opaque references; never fabricate inapplicable claim/lease/fence | Arbitrary extension bags; embedded repositories/logs/Evidence/artefacts/prompts; credentials; redact-after-serialize; implicit checksum authenticity | Size, length, and cardinality unselected | Security field/redaction/integrity policy and owner reference formats | Boundary-size, prohibited-content, claimed/unclaimed reference, redaction, version, tamper, and canonicalization tests | Disclosure, compatibility, and capacity gates | Limits `CONFIGURATION_VALUE_NOT_YET_SELECTED`; algorithms/fields external | Required-field removal, validation weakening, or canonicalization change is breaking | Future validation metadata only; no schema/type or DB-003 authorization | Invalid/oversize work cannot transition; checkpoint authority/compatibility remains Workflow-owned | Owns field policy, disclosure, events, algorithms, and key custody | Fixtures remain secret-free; Evaluation reads owner data by reference |
| `QUEUE-REQ-017` — `READY_FOR_DRAFT` | Transaction-versus-publication atomicity and durable publication intent | Database transactions and provider publication MUST NOT be assumed atomic; before any provider attempt a stable durable publication intent or A2-DATABASE-approved equivalent MUST bind semantic request, Queue message, producer, actor, and attributable attempt/outcome. | A2-QUEUE + A2-DATABASE boundary | Backend, Database, Workflow, Deployment | Separate intent, attempt, outcome, delivery, and ack facts; uncertain means may-have-published and reconciles stable identity | Direct publish after uncommitted state; treating timeout as success/failure; blind new intent | Publication timeout unselected | Database atomicity design and provider adapter | Crash-window, timeout, rejection, confirmed/uncertain/duplicate outcome matrix | Fault-injection and operational recovery gate | Physical intent `IMPLEMENTATION_DETAIL_DEFERRED`; timeout unselected | Atomicity, intent, or publication-state meaning changes are breaking | Future intent records only; DB-003 unauthorized | Publication facts neither create attempts nor claim execution success | Attribution/integrity required; uncertainty preserves secret-free evidence | Measure outcome uncertainty and recovery only |
| `QUEUE-REQ-018` — `READY_FOR_DRAFT` | Transactional outbox, inbox or provider-neutral equivalent | The physical implementation MUST provide both:<br><br>1. a transactional outbox, durable publication-intent mechanism, or A2-DATABASE-approved equivalent that closes producer commit/publication crash windows; and<br><br>2. an inbox, processed-delivery ledger, or A2-DATABASE-approved equivalent that provides durable consumer deduplication across retries and restarts.<br><br>One combined mechanism MAY satisfy both capabilities only when it demonstrably preserves durable publication intent, reconciliation, fencing, duplicate protection, and the logical boundaries in this contract. | A2-DATABASE physical owner; A2-QUEUE semantic owner | Backend, Database, Workflow, Deployment, Integration | Both producer crash-window protection and durable consumer duplicate protection are required; one combined mechanism may satisfy both only with demonstrated equivalent guarantees | Outbox-only behavior with no durable consumer duplicate protection; inbox-only behavior with no producer crash-window protection; in-memory-only deduplication; compare-and-set alone where it does not provide both required capabilities; provider receipt used as Database truth; mandating a provider product | None selected | Separately authorized Database design and adapter implementation | Commit/publish crash, relay restart, inbox duplicate, ordering, and recovery evidence | Database, Integration, and reliability acceptance | Mechanism `IMPLEMENTATION_DETAIL_DEFERRED` | Replacing the mechanism is compatible only if semantics/evidence remain unchanged | Required future design; this draft does not start or authorize DB-003 | Inbox/equivalent cannot invent Workflow attempts or transitions | Least-privilege records, integrity, and secret-free failure evidence | Compare implementation reliability without selecting semantics |
| `QUEUE-REQ-019` — `READY_FOR_DRAFT` | Duplicate-consumer protection and one accepted semantic effect | Duplicate/concurrent/replayed/redelivered/re-driven consumption converges on at most one accepted effect after current binding, fence, authorization, cancellation, terminal, deletion, checkpoint, and integrity validation; Queue duplication creates/redefines no attempt, and stable result-slot/conditional checkpoint binding cannot alter repair allowance, skip/reverse/complete `EXECUTING_BUGGY` then `EXECUTING_FIXED`, or bypass Evidence rules. | Layered Queue/Workflow/Execution/Evidence/Database/Security ownership | Workflow, Database, Evidence, Execution, Security | Reuse the existing accepted effect; preserve per-submission provenance, Evidence deletion barriers, `repair_attempts_used`, and the required Workflow sequence | Last-write-wins; duplicate effect/attempt; Queue-defined canonical Evidence/alternate conflict; replay reopening/shortcutting repair; recreating deleted Evidence | None | Workflow acceptance/repair, Execution result, Database uniqueness/fencing, Evidence classification/deletion, Auth/Security policies | Duplicate/concurrent/replay/checkpoint/repair-sequence/delete/revoke/cancel and replacement-worker races | Integrity, Evidence, and Security gates | Physical mechanism deferred; freshness external | Accepted-effect, attempt/result-slot, repair-sequence, or replay-validation weakening is breaking | Owns physical uniqueness/locking/transactions/durable deduplication; DB-003 unauthorized | Owns result-slot/attempt meaning, accepted transition, terminal/cancellation gates, repair allowance, and `EXECUTING_BUGGY` then `EXECUTING_FIXED` order | Algorithms/policy and invalid-duplicate/conflict events remain Security-owned | Owns canonical Evidence content, duplicate/conflict classification/finalization, and preservation of accepted Evidence |
| `QUEUE-REQ-020` — `READY_FOR_DRAFT` | Durable observability, correlation, audit and Security-event requirements | Durable bounded secret-free facts/events are required, and every provider mapping documents encryption/access/identity/injection/admin boundaries plus publication, depth/age, delivery/redelivery, lease/renewal/heartbeat, DLQ, stale-claim, ack/persistence latency, and drain-failure signals. | A2-QUEUE + A2-SECURITY boundary | Operations, Database, Security, Evaluation, Integration, Deployment | Correlation traces only; operational signals never prove Workflow success, Evidence, or completion | Payload/log dumps; trace/signal as semantic identity/authority/success/proof | Thresholds, alerts, sampling, capacity, and pass/fail values external | Security access/event/disclosure policy, Deployment mapping, Database audit, Evaluation gates | Capability, leak, redaction, attribution, tamper, missing-event/signal, and false-inference checks | Operational Security and audit/release gates | Values remain Deployment configuration, Security policy, or Evaluation input | Removing capability/attribution or increasing disclosure requires review and may be breaking | Future audit storage only; DB-003 unauthorized | Logs/signals do not define lifecycle, ordering, or success | Owns access/event/disclosure/algorithm/key policy and least privilege | Owns measurement/release inputs; metrics cannot infer semantic success |
| `QUEUE-REQ-021` — `READY_FOR_DRAFT / DURATIONS_EXTERNAL` | Queue, audit, semantic, Evidence and artefact retention separation | Queue transport/dead-letter records, publication/claim audit, operational logs, semantic request/result records, Evidence, and artefacts MUST retain and delete independently under their respective owner policies. | Respective owners; A2-QUEUE for transport category | Database, Evidence, Security, Deployment, Workflow, Evaluation | Current deletion/tombstone validation on replay/re-drive; attributable administrative deletion | One retention period for all categories; expiry implying terminality; Queue activity recreating deleted Evidence | Queue/dead-letter retention unselected/external | Owner retention, legal, deletion, and disclosure policies | Expiry, deletion, tombstone, replay, re-drive, and cross-category tests | Compliance, Evidence, and Security gate | Retention policies `EXTERNAL_OWNER_POLICY_REQUIRED` | Retention weakening or deletion bypass is breaking | Future records/tombstones only; DB-003 unauthorized | Retention/expiry does not define Workflow terminality | Owns disclosure and required deletion-bypass events | Retention-aware datasets exclude deleted or unauthorized material |
| `QUEUE-REQ-022` — `READY_FOR_DRAFT` | Deterministic provider-neutral local/test adapter | The deterministic adapter runs from a clean checkout without production credentials/secrets/shared production Queue or Database state; isolates messages/claims/DLQ/artefact references; and preserves production validation, identity, redelivery, fencing, retry, ack, failure, and DLQ semantics. | A2-QUEUE | Developers, Workflow, Execution, Integration, Evaluation | Common provider-neutral conformance suite is mandatory; provider-specific tests are additive only | Shared production state/credentials; committed secrets; provider tests replacing common conformance; weakened happy path | Test timing/capacity not semantic defaults | Contract fixtures and future separately authorized adapter design | Clean-checkout isolation plus repeatable publication/delivery/claim/ack/failure/restart conformance | Adapter parity and Integration gate | Implementation `IMPLEMENTATION_DETAIL_DEFERRED` | Divergence/isolation weakening is incompatible | No persistence implementation or DB-003 authorization by this draft | Simulated transport cannot invent Workflow attempts/events/outcomes | Same redaction, integrity, authorization, secret-free, and credential-isolation rules | Owns reproducibility and comparability of adapter evidence |
| `QUEUE-REQ-023` — `READY_FOR_DRAFT` | Queue transport records versus Workflow semantic events | Publication intents/outcomes, deliveries, claims/leases, retries, acknowledgements, expiries, and dead-letter records are Queue transport facts and MUST NOT be stored, named, or interpreted as authoritative Workflow semantic events. | A2-QUEUE + A2-AGENT-WORKFLOW boundary | Backend, Workflow, Database, Evidence, UI, Integration | Explicitly typed attributable Queue records consumed through the Workflow contract | Queue state row as Workflow event; ack/expiry/DLQ as lifecycle transition; transport log as Evidence proof | None | Workflow event model and Database record design | Type-separation, projection, cross-state, and false-inference tests | Workflow, Database, and consumer acceptance | Physical records `IMPLEMENTATION_DETAIL_DEFERRED` | Collapsing record/event types is breaking | Future record schema only; no event model or DB-003 authorization | Owns semantic events, projections, attempts, transitions, and terminality | Prevent misleading lifecycle/Evidence claims and preserve provenance | Transport facts cannot be scored as semantic outcomes |
| `QUEUE-REQ-024` — `READY_FOR_DRAFT` | Execution-attempt and producer-result persistence boundary | Workflow owns run/step-occurrence/kind/occurrence/attempt-index identity, lifecycle/repair/acceptance, result slots, checkpoint authority, and repaired-candidate order `EXECUTING_BUGGY` then `EXECUTING_FIXED`; Execution owns runtime facts/result production; Queue transports stable result identity and conditional checkpoint claim binding without changing attempts/repair or shortcutting either required state; durable owner effects precede ack eligibility. | A2-QUEUE boundary with Workflow/Database/Evidence/Execution/Security | Workflow, Database, Evidence, Execution, Security | Stable result ID across transport/worker recovery; per-submission authority/provenance; separate canonicalizations; Database-exclusive physical persistence; Evidence-semantic ownership; `0..1` repair and required-sequence invariance | Delivery/transition/claim as attempt parent; worker/claim change forces result ID; Queue canonical Evidence/alternate conflict; fabricated checkpoint fence; Queue-owned lifecycle/runtime/repair or direct `REPAIRING` shortcut; joint Evidence physical persistence | None | Workflow attempt/result/checkpoint/repair contract, Execution result/runtime contract, Database physical persistence, Evidence semantics, Security policy | Attempt/result/checkpoint/repair-sequence binding, worker recovery, stale-fence, physical commit, duplicate/conflict, and ack-loss tests | Workflow, durability, Evidence, and integrity gates | Physical persistence `IMPLEMENTATION_DETAIL_DEFERRED` | Attempt/result/checkpoint/repair-sequence/owner boundary changes are breaking | Owns physical schema/transactions/constraints/locking/CAS/fencing/models/migrations; DB-003 unauthorized | Owns attempts, result slots/acceptance, checkpoint authority, lifecycle, repair allowance, and `EXECUTING_BUGGY` then `EXECUTING_FIXED` transitions | Owns algorithm/integrity/key/event policy; invalid/conflicting/stale effects fail closed | Owns Evidence identity/reference/finalization/completeness/provenance/integrity meaning/compatibility/deletion; no transport-derived completion |
| `QUEUE-REQ-025` — `READY_FOR_DRAFT` | Backend durable request and Queue publication transaction boundary | Backend durable request/current-run acceptance and Queue publication are separate boundaries: API `202` proves only Backend durable acceptance, while an A2-DATABASE-approved transaction/equivalent must establish publication eligibility and stable intent before asynchronous publication. | A2-BACKEND/A2-DATABASE owners with A2-QUEUE boundary | Backend, Database, Workflow, UI, Integration, Deployment | Preserve API semantics; reconcile durable request, eligibility, intent, attempt, and outcome without dual-write assumptions | `202` means queued/delivered/started/succeeded; provider call inside an assumed atomic DB transaction; publication failure rewrites HTTP meaning | Publication timeout unselected | `CONTRACT-API-001`, Backend transaction design, Database equivalent, provider adapter | API/transaction crash-window, commit/rollback, publication outcome, duplicate, and reconciliation scenarios | Backend, Database, Integration, and recovery acceptance | Retry-After/API duplicate response external; physical transaction deferred | Overpromising API or changing transaction/publication meaning is breaking | Future request/intent boundary only; DB-003 unauthorized | Publication facts do not force attempts, transitions, or success | Attribution, current eligibility, and secret-free failure evidence required | No execution-success inference; measure handoff recovery |
| `QUEUE-REQ-026` — `READY_FOR_DRAFT` | Deployment/provider-adapter capability and conformance boundary | Every future adapter preserves the full logical contract, clean-checkout isolated common conformance, and documented encryption/access/identity/secret/admin plus minimum operational-signal mappings; provider-specific tests are additive and observability is not semantic proof. | A2-QUEUE with A2-DEPLOYMENT/A2-INTEGRATION | All consumers and ten section 18 reviewers | Provider-neutral semantics; isolated local/test parity; bounded extensions; declared compatibility/rollback; Security mapping; measured operations | Production/shared credentials or state in tests; provider tests replacing common suite; silent extensions; weak access/signals; implicit approval; draft as runtime authorization | Provider, capacity, concurrency, thresholds, alerts, sampling, rollout, and operational values unselected | Deployment/Integration plans, all affected re-reviews, Security/Auth policies, Evaluation inputs | Clean-checkout adapter conformance, isolation, access/signal capability, version, rollback, load, fault, and Security evidence | All owner gates plus measured capacity/reliability/compatibility | Capacity/thresholds `BLOCKED_BY_MISSING_MEASUREMENT_INPUT` or `RELEASE_GATE_INPUT_REQUIRED`; external values remain classified | Provider swap or semantic/version change reopens affected review and may be breaking | DB-003 remains unauthorized; migration and implementation require separate authorization | Workflow review required; adapter cannot alter lifecycle/attempt/repair semantics | Security review required for encryption/access/identities/secrets/events; controls cannot weaken | Owns measurement methodology/release inputs; signals cannot prove semantic success |

## 18. Mandatory consumer-review duties

Every reviewer MUST inspect the named sections and its owned boundary and
return exactly one disposition: `ACCEPTED`, `ACCEPTED_WITH_CONSTRAINTS`,
`REJECTED_WITH_REASON`, or `SPECIFICATION_CONFLICT`. Silence is not acceptance.
Constraints MUST be recorded in `DEPENDENCY_REQUESTS.md` with reviewer, exact
section/requirement, rationale, compatibility impact, required evidence, and
closure condition. A conflict is escalated to A2-QUEUE and the conflicting
owner; unresolved cross-owner conflicts go to the coordinating manager and
block acceptance. Any change to an accepted identity, authorization,
publication, idempotency, delivery/lease, result/acknowledgement, cancellation,
integrity, dead-letter, retention, lifecycle, compatibility, or release-gate
boundary requires another review cycle for affected consumers.

| Reviewer | Sections to inspect | Owned boundary |
|---|---|---|
| `A2-BACKEND` | 1.1, 3, 4, 5, 6, 16, 17 | API `202`, durable request/publication handoff, producer behavior, API/Queue idempotency, request/correlation propagation |
| `A2-AGENT-WORKFLOW` | 2, 3.6, 4, 6–9, 13, 15, 17 | Eligibility, attempts, lifecycle/cancellation/terminal meaning, semantic repair, result acceptance |
| `A2-DATABASE` | 3.2, 4, 6–7, 9–12, 15–17 | Physical intent/outbox/inbox equivalent, uniqueness/fencing/commit boundaries, retention/deletion; no DB-003 authorization |
| `A2-EVIDENCE` | 2, 4–5, 7, 9–12, 17 | Evidence references, accepted-result binding, deletion/recreation barrier, Evidence retention/proof boundary |
| `A2-EXECUTION` | 2, 4–9, 11–14, 17 | Worker identity, protected effects, claims/renewal/loss, checkpoints, result production, cleanup |
| `A2-SECURITY` | 2, 4–5, 7–12, 14–17 | Allow/deny lists, redaction, integrity/canonicalization/keys, events, policy, dead-letter administration, disclosure/retention |
| `A2-AUTH` | 2–5, 9–10, 12, 16–17 | Actor/service/authorization references, current authorization, cancellation/re-drive authority, freshness |
| `A2-DEPLOYMENT` | 1–2, 5–6, 8, 10, 12, 14–17 | Provider adapter/runtime configuration, capacity, timeouts/retries, identities, observability, rollout/rollback |
| `A2-INTEGRATION` | 1–4, 6–15, 17 | Cross-contract consistency, provider-neutral conformance, mixed-version compatibility, conflict resolution |
| `A2-EVALUATION` | 1.2, 7–8, 12–17 | Measurement provenance, implementation evidence, capacity/latency/reliability and release-gate separation |

## 19. Acceptance state

All ten reviews of `CONTRACT-QUEUE-001@1.0.0-draft.1` were received. Draft.1
remains historical review evidence and was not accepted: two
`SPECIFICATION_CONFLICT` and two `REJECTED_WITH_REASON` dispositions blocked
merge. This `1.0.0-draft.2` correction changes normative identity, ownership,
retry, heartbeat, checkpoint, adapter, and result-boundary wording without
changing the major/minor/patch version. A2-QUEUE's final source review passed.
The branch was reconciled with `origin/main` at
`e7de96fc96e665fc32163dc9f26986e0e56e5510` with no Queue semantic conflict.
Focused draft.2 re-review by the nine affected owners is pending and has not
begun. PR #24 remains `OPEN / DRAFT / NOT_READY / NOT_MERGED`. Draft.2 remains
unaccepted and is not implementation-ready.

This draft authorizes no Queue runtime, provider selection, DB-003 work,
application change, test, dependency, migration, worker, sandbox, or
infrastructure.
