# CONTRACT-QUEUE-001 — Provider-neutral Queue boundary

## 1. Metadata and normative scope

| Field | Value |
|---|---|
| Contract ID | `CONTRACT-QUEUE-001` |
| Version | `1.0.0-draft.1` |
| Status | `DRAFT / PENDING_CONSUMER_REVIEW` |
| Owner | `A2-QUEUE — Queue and Asynchronous Execution Component Manager` |
| Authorized baseline | `ab60d4573d398fb610bc2ebb813f76d0c95b33d7` |
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
| `workflow_attempt_id` | Workflow-owned semantic attempt | A2-AGENT-WORKFLOW | semantic request/run and Workflow transition | transport delivery or lease identity; redelivery alone cannot create it |
| `producer_result_id` | Stable producer result submission | Result-producing worker/service | attempt, message, claim/fence, canonical result | Evidence identity, provider receipt, or conflicting content |
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

## 7. Results, persistence, and acknowledgement

1. Result acceptance MUST bind semantic request, message, Workflow attempt,
   result, worker, claim/fence, applicable versions, and integrity metadata.
2. An identical duplicate result MAY be recognized only after valid binding,
   required integrity verification, and canonical equality. Recognition MUST
   return the existing accepted effect without rewriting it.
3. A conflicting duplicate MUST fail closed, emit attributable conflict and
   Security evidence, and preserve the accepted result/Evidence unchanged.
4. Current Workflow terminal/cancellation state, Evidence deletion state,
   authorization/policy, and fence MUST be checked before each accepted
   protected effect.
5. Required result, state, provenance, audit, and Evidence-reference effects
   MUST durably commit before acknowledgement becomes eligible. Physical
   persistence remains A2-DATABASE/A2-EVIDENCE-owned and DB-003 is unauthorized.
6. If commit succeeds and acknowledgement fails or is uncertain, redelivery
   MUST converge idempotently on the existing accepted effect. Acknowledgement
   MAY be retried without rerunning semantic work.
7. Negative acknowledgement MAY occur only with an attributable retry
   classification. It MUST NOT erase provenance, imply cancellation, or bypass
   bounded retry/poison rules.

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

## 9. Checkpoints, replay, cancellation, and stale work

A checkpoint MUST be an opaque reference bound to semantic request, Workflow
attempt, producing claim/fence, compatibility versions, integrity metadata,
and lifecycle state. Consumers MUST reject corrupt, substituted, deleted,
cancelled, superseded, or incompatible checkpoints. Checkpoint compatibility
rules require Workflow, Execution, Security, and Integration review.

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

## 13. Workflow lifecycle boundary

Queue states are transport/publication facts, not Workflow states. Queue
ordering is not Workflow event ordering; delivery, claim, expiry,
acknowledgement, negative acknowledgement, and dead-letter movement MUST NOT
invent or force Workflow transitions. A2-AGENT-WORKFLOW owns attempt creation,
execution lifecycle, repair, cancellation meaning, terminality, and result
acceptance transitions. Queue supplies attributable facts for Workflow to
consume under its contract.

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

## 17. Authoritative 26-row requirements matrix

Abbreviations: `Cfg` = configuration points; `Ext` = external dependencies;
`Impl` = implementation evidence; `Rel` = release evidence; `Compat` =
compatibility impact. `DB3` never authorizes DB-003.

| ID / drafting status | Title | Normative decision | Owner | Consumers | Accepted constraints | Rejected alternatives | Cfg | Ext | Impl | Rel | Unresolved values | Compat | DB3 | Workflow | Security | Evaluation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `QUEUE-REQ-001` — `READY_FOR_DRAFT` | Identity separation | All section 4 identities MUST remain separately typed and bound. | A2-QUEUE | Backend, Workflow, Database, Evidence, Execution | Stable semantic/message identity; per-delivery/claim/result identity | Receipt-as-ID; tracing-as-ID | Formats deferred | Auth identity authorities | Round-trip/binding and collision checks | Cross-consumer compatibility | Physical types `IMPLEMENTATION_DETAIL_DEFERRED` | Identity collapse is breaking | Future records only; unauthorized | Attempts stay Workflow-owned | Identity mismatch fails closed | Preserve result provenance |
| `QUEUE-REQ-002` — `READY_FOR_DRAFT` | Envelope allowlist | Only section 5 allowed bounded fields/references MAY be serialized. | A2-QUEUE | All producers/consumers | Secret-free opaque references | Arbitrary payload/extension bags | Limits unselected | Security field policy | Producer/consumer rejection fixtures | Disclosure review | Security-approved fields `EXTERNAL_OWNER_POLICY_REQUIRED` | Required field/removal breaking | No schema authorized | Operation kinds reviewed | Redaction/denylist review | Evaluation bytes excluded |
| `QUEUE-REQ-003` — `READY_FOR_DRAFT` | Validation/redaction | Producer validates/redacts before serialization; consumers validate defensively. | A2-QUEUE | Backend, Workflow, Execution | Fail closed on redaction/version/integrity errors | Trust producer; redact after serialize | Limits unselected | Security policy | Adversarial invalid-envelope evidence | Security acceptance | Event schema external | Weakening is breaking | Future validation persistence only | Invalid work cannot transition | Events/disclosure owned | Fixtures must be secret-free |
| `QUEUE-REQ-004` — `READY_FOR_DRAFT` | Durable publication intent | Durable request, intent, attempt, outcome, delivery, and ack remain separate. | A2-QUEUE | Backend, Database, Workflow | Stable intent before provider attempt | Assume DB/provider atomicity | Publication timeout unselected | A2-DATABASE design | Crash-window reconciliation | Fault-injection gate | Physical outbox `IMPLEMENTATION_DETAIL_DEFERRED` | Atomicity change breaking | Owner-approved equivalent later; unauthorized | Eligibility remains Workflow-bound | Attribution required | Reliability evidence only |
| `QUEUE-REQ-005` — `READY_FOR_DRAFT` | HTTP/Queue boundary | API `202` proves only API durable acceptance. | A2-QUEUE + A2-BACKEND boundary | Backend, UI, Integration | Preserve API semantics | `202` means delivered/started/succeeded | None | API contract | Contract/API scenario check | Consumer acceptance | Retry-After external | Overpromise is breaking | No effect | Queue facts do not force state | No false disclosure | No success inference |
| `QUEUE-REQ-006` — `READY_FOR_DRAFT` | Publication outcomes | Six section 3.5 states MUST be attributable and reconcilable. | A2-QUEUE | Backend, Database, Deployment | Uncertain means may-have-published | Treat timeout as failure/success | Timeouts unselected | Provider adapter | Outcome/fault matrix | Operational recovery gate | Receipt behavior deferred | State meaning breaking | Possible future intent records only | No execution success claim | Preserve evidence | Measure uncertainty rate |
| `QUEUE-REQ-007` — `READY_FOR_DRAFT` | Publication idempotency | Stable message/publication identity prevents duplicate accepted publication effects. | A2-QUEUE | Backend, Database, Integration | Semantic/API/Queue idempotency separate | Provider receipt as semantic key | Adapter mapping deferred | Database uniqueness design | Duplicate publish scenarios | Interoperability gate | API duplicate response external | Key semantics breaking | Future constraint only | Does not create attempt | Abuse/replay checks | Duplicate-rate measurement |
| `QUEUE-REQ-008` — `READY_FOR_DRAFT / NUMERIC_VALUES_DEFERRED` | Payload boundedness | Every field/collection MUST be bounded; prohibited content remains prohibited under encoding. | A2-QUEUE | Producers, Deployment, Security | Allowlist-first references | Embedded repositories/logs/Evidence | Size/length/cardinality unselected | Security + provider constraints | Boundary-size/rejection checks | Capacity/disclosure gate | Numeric limits `CONFIGURATION_VALUE_NOT_YET_SELECTED` | Tightening needs rollout review | No effect | Oversize cannot transition | Limits/content policy | Dataset sizes inform selection |
| `QUEUE-REQ-009` — `READY_FOR_DRAFT / TIMING_VALUES_DEFERRED` | Claims/leases/fencing | Claims MUST fence stale workers; uncertain renewal pauses protected effects. | A2-QUEUE | Workflow, Execution, Database, Deployment | Monotonic fence or equivalent | Time alone/worker assertion as authority | Durations/timeouts/heartbeats unselected | Database/adapter design | Race and stale-worker fault tests | Reliability gate | Timing `CONFIGURATION_VALUE_NOT_YET_SELECTED` | Fence semantics breaking | Future fenced effects only | Lease expiry not terminal | Stale attempts are events | Measure renewal behavior |
| `QUEUE-REQ-010` — `READY_FOR_DRAFT / COUNTS_DEFERRED` | Bounded retry | All transport retries/re-drives MUST be bounded and classified. | A2-QUEUE | Workflow, Deployment, Evaluation | Categories in section 8 | Infinite retry; application failure as poison | Counts/backoff unselected | Workflow/Deployment policy | Retry exhaustion/fault checks | Operational gate | Counts `CONFIGURATION_VALUE_NOT_YET_SELECTED` | Count changes operationally sensitive | No effect | Semantic repair stays separate | Security rejection not ordinary retry | Reliability metrics |
| `QUEUE-REQ-011` — `READY_FOR_DRAFT / RETENTION_DEFERRED` | Dead-letter lifecycle | Dead-letter actions require provenance, attribution, least privilege, and no automatic re-drive. | A2-QUEUE | Security, Auth, Deployment, Integration | Current validation on re-drive | Auto re-drive; stale auth; mutable provenance | Re-drive limits unselected | Retention/authorization policy | Inspect/export/delete/re-drive tests | Administrative review | Retention `EXTERNAL_OWNER_POLICY_REQUIRED` | Record/action changes reviewed | Future admin records only | Not terminal automatically | Least privilege/disclosure | DLQ metrics not outcomes |
| `QUEUE-REQ-012` — `READY_FOR_QUEUE_OWNED_DRAFT` | Queue cancellation delivery | Cancellation transport is separate from API acceptance and Workflow outcome. | A2-QUEUE | Backend, Workflow, Execution | Durable intent; observation/effect cutoff distinct | Accepted request means cancelled worker | Delivery values unselected | Workflow cancellation semantics | Cancellation race/fence evidence | Cross-owner acceptance | Control mechanism deferred | Meaning changes breaking | No action persistence authorized | Owns terminal result | Current auth/policy/events | No cancelled run success |
| `QUEUE-REQ-013` — `READY_FOR_DRAFT / CAPACITY_DEFERRED` | Adapter capacity neutrality | Contract MUST remain provider-neutral; capacity is measured/configured externally. | A2-QUEUE | Deployment, Integration, Evaluation | Semantic conformance independent of provider | Provider-specific semantics in envelope | Capacity/concurrency deferred | Deployment measurements | Adapter conformance and load evidence | Capacity gate | Capacity `BLOCKED_BY_MISSING_MEASUREMENT_INPUT` | Provider swaps require conformance | No effect | No effect | Security controls cannot weaken | Owns measurement methodology |
| `QUEUE-REQ-014` — `READY_FOR_DRAFT` | Duplicate delivery/results | Duplicate delivery has one effect; identical results converge; conflicts fail closed. | A2-QUEUE | Workflow, Database, Evidence | Canonical equality + valid binding/integrity | Last-write-wins; auto merge | None | Canonicalization policy | Duplicate/conflict race tests | Integrity gate | Algorithm external | Conflict semantics breaking | Future unique/fence rules only | Owns acceptance transition | Conflict event required | Preserve evaluated result |
| `QUEUE-REQ-015` — `READY_FOR_DRAFT` | Commit before ack | Required durable effects commit before ack; ack failure recovers idempotently. | A2-QUEUE | Database, Evidence, Workflow, Deployment | Retry ack without rerunning effect | Ack before commit; ack as completion proof | Ack deadlines unselected | Persistence owners | Crash-before/after-commit tests | Recovery gate | Physical transaction deferred | Ordering change breaking | Future atomic scope only | Ack not lifecycle proof | Preserve audit/integrity | No completion inference |
| `QUEUE-REQ-016` — `READY_FOR_DRAFT / BYTE_LIMIT_DEFERRED` | Opaque references | Input/checkpoint/result/Evidence use bounded opaque references, never bytes. | A2-QUEUE | Evidence, Execution, Security | Reference binding/integrity | Inline artefacts/Evidence/prompts | Byte limits unselected | Owner reference formats | Reference validation/deletion tests | Disclosure/capacity gate | Limits `CONFIGURATION_VALUE_NOT_YET_SELECTED` | Format changes reviewed | No physical type selected | Checkpoint compatibility owned | Reference disclosure policy | Evaluation reads owner data |
| `QUEUE-REQ-017` — `READY_FOR_DRAFT` | Checkpoint compatibility | Corrupt/substituted/deleted/cancelled/superseded/incompatible checkpoints fail closed. | A2-QUEUE boundary | Workflow, Execution, Security, Integration | Bind attempt/fence/versions/integrity | Resume by opaque presence alone | None | Owner checkpoint contract | Tamper/stale/resume tests | Compatibility gate | Format deferred | Version rules breaking | Future reference only | Owns resume meaning | Integrity/deletion validation | No stale-result acceptance |
| `QUEUE-REQ-018` — `READY_FOR_DRAFT` | Current-policy replay protection | Replay/redelivery/re-drive MUST revalidate current state, policy, and authorization. | A2-QUEUE | Auth, Security, Workflow, Evidence | Stored auth is provenance only | Evergreen receipt/authorization | Freshness external | Auth/Security policies | Revocation/deletion replay tests | Security gate | Freshness `EXTERNAL_OWNER_POLICY_REQUIRED` | Weakening breaking | No effect | Terminal/cancel gates | Current validation owned | Exclude invalid replay |
| `QUEUE-REQ-019` — `READY_FOR_DRAFT` | Evidence deletion barrier | Queue activity MUST NOT recreate deleted Evidence. | A2-QUEUE + A2-EVIDENCE boundary | Evidence, Workflow, Database | Tombstone/equivalent validation | Recreate from DLQ/checkpoint/result | None | Evidence deletion semantics | Delete-then-replay tests | Evidence consumer acceptance | Mechanism deferred | Deletion bypass breaking | Future marker only | Terminal/deletion respected | Security event on bypass | Deleted data excluded |
| `QUEUE-REQ-020` — `READY_FOR_DRAFT` | Integrity metadata | Required integrity binds explicit scope/version and mismatch fails closed. | A2-QUEUE + A2-SECURITY boundary | All adapters/consumers | Unkeyed checksum only consistency | Checksum as authenticity; implicit scope | None | Security algorithms/keys | Tamper/canonicalization checks | Security gate | All algorithms `EXTERNAL_OWNER_POLICY_REQUIRED` | Canonicalization changes breaking | Future metadata only | Invalid result rejected | Owns algorithms/custody | Integrity provenance |
| `QUEUE-REQ-021` — `READY_FOR_DRAFT / DURATIONS_EXTERNAL` | Authorization freshness | Queue receipt never grants/refreshes authority; required current checks follow owner policy. | A2-AUTH/Security policy, Queue enforcement | Producers, workers, administrators | Revalidate at protected boundaries | Redelivery refreshes auth | None | Auth/Security freshness policy | Revocation-window scenarios | Authorization gate | Durations `EXTERNAL_OWNER_POLICY_REQUIRED` | Weakening breaking | No effect | Current auth gates effects | Owns policy/events | No unauthorized samples |
| `QUEUE-REQ-022` — `READY_FOR_DRAFT` | Security events/observability | Failures and admin actions MUST be attributable, bounded, and secret-free. | A2-QUEUE + A2-SECURITY boundary | Operations, Evaluation, Integration | Correlation for tracing only | Payload/log dump; observability as proof | Sampling external | Security event schema | Leak/redaction/attribution checks | Operational security gate | Event fields `EXTERNAL_OWNER_POLICY_REQUIRED` | Disclosure changes reviewed | Future event storage only | Logs do not order lifecycle | Owns disclosure/retention | Metrics need provenance |
| `QUEUE-REQ-023` — `READY_FOR_DRAFT` | Retention separation | Transport, audit, semantic, Evidence, and artefact retention remain separate. | Respective owners; Queue for transport category | Database, Evidence, Security, Deployment | Deletion/re-drive validation | One retention period governs all | Queue retention unselected | Owner retention policies | Expiry/deletion interaction tests | Compliance gate | Policies external | Retention weakening breaking | No records authorized | Terminality independent | Owns policy | Retention-aware datasets |
| `QUEUE-REQ-024` — `READY_FOR_DRAFT` | Workflow separation | Queue state/order/ack/expiry/DLQ MUST NOT define Workflow lifecycle or Evidence proof. | A2-QUEUE + A2-AGENT-WORKFLOW boundary | Backend, Workflow, Evidence, UI | Attributable Queue facts only | Queue ordering as event ordering | None | Workflow contract review | Cross-state scenario checks | Consumer acceptance | None | Boundary change breaking | No event model authorized | Owns transitions/attempts | Prevent false claims | No transport-derived success |
| `QUEUE-REQ-025` — `READY_FOR_DRAFT` | Version compatibility | Unknown schema/canonicalization fails closed; transitions are versioned/reviewed. | A2-QUEUE | All consumers, Integration, Deployment | Declared mixed-version compatibility | Guessing; silent provider semantics | Rollout values deferred | Integration/Deployment plans | Version matrix/rollback evidence | Compatibility gate | Rollout detail deferred | Major changes breaking | Migration unauthorized | Pinned governing versions | Integrity versions reviewed | Cross-version comparability |
| `QUEUE-REQ-026` — `READY_FOR_DRAFT` | Consumer review/conformance | Mandatory written dispositions and evidence precede acceptance/implementation. | A2-QUEUE | Ten reviewers in section 18 | Silence is not acceptance | Implicit approval; runtime authorization by draft | None | All review owners | Recorded dispositions + adapter evidence | All gates resolved | External values remain classified | Affected changes reopen review | DB-003 stays unauthorized | Workflow review required | Security review required | Evaluation gates separate |

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

This draft is complete for consumer review only. Acceptance requires all ten
written reviews, resolution of constraints/conflicts, a versioned revision if
semantics change, and separation of implementation evidence from release-gate
evidence. It authorizes no Queue runtime, provider, DB-003 work, application
change, test, dependency, migration, worker, sandbox, or infrastructure.
