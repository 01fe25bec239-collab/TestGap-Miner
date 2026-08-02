# CONTRACT-WORKFLOW-001 — Agent Workflow Lifecycle Contract

## Contract metadata

| Field | Value |
|---|---|
| Contract ID | `CONTRACT-WORKFLOW-001` |
| Version | `1.0.0-draft.1` |
| Status | `ACKNOWLEDGED_AND_MERGED` |
| Semantic commit | `a7c83f422bb51deefd233229c7573fda64b097b6` |
| Semantic integrity | `SEMANTIC_INTEGRITY_PRESERVED` / `NO_SEMANTIC_CHANGE_REQUIRED` |
| Owner | `A2-AGENT-WORKFLOW` |
| Required consumers | Backend, UI, Database, Evaluation, Integration |
| Database request | `DB-DEP-004` |
| Database task | `DB-WORKFLOW-CONTRACT-ACK-001` |
| Database decision | `ACCEPTED_WITH_NONBREAKING_CLARIFICATIONS` |
| Workflow merge evidence | PR #8, merge commit `7da1132b9e30b51a212aa6574c23e2a832d9a6fd`, 2026-07-31 |
| Database reconciliation merge evidence | PR #10, merge commit `99c8022c9f44e6a54bed624aa0153be7e32f234b`, 2026-08-01 |
| Consumed by | DB-002, merged via PR #12, merge commit `3701520e6d61e2bb80391e7af888d0d530bdb6c4`, 2026-08-02 |
| Scope | Run lifecycle, workflow steps, ordered events, bounded retry/repair, failure, abstention, cancellation, checkpoint/resume, and human review |
| Out of scope | Workflow-engine implementation, queue envelope, evidence schema, runtime tests, and DB-002/DB-003 implementation |

Normative terms `MUST`, `MUST NOT`, `SHOULD`, and `MAY` are used as in RFC 2119.

## Product and safety boundary

The MVP is Java/JUnit-only and Defects4J-first. A run may produce only a
test-only candidate patch backed by execution evidence. It permits one bounded
automated repair, explicit abstention, and human review. It MUST NOT edit
production code, auto-merge, approve, bypass branch protection, execute an
open-ended autonomous loop, or obtain arbitrary shell or network access.

Lifecycle records MUST contain only bounded, redacted metadata or opaque
evidence references. They MUST NOT contain raw secrets, prompts, repository
bytes, patch bytes, or execution logs.

## Canonical `RunState`

The normative enumeration, in declaration order, is:

`RECEIVED`, `VALIDATING`, `QUEUED`, `PLANNING`, `LOCALISING`, `GENERATING`, `EXECUTING_BUGGY`, `EXECUTING_FIXED`, `REPAIRING`, `SCORING`, `PUBLISHING`, `AWAITING_HUMAN_REVIEW`, `COMPLETED`, `ABSTAINED`, `FAILED_INPUT`, `FAILED_MODEL`, `FAILED_EXECUTION`, `FAILED_INFRASTRUCTURE`, `FAILED_SECURITY`, `CANCELLED`.

Consumers MUST persist the exact uppercase values. They MUST NOT infer state
order from declaration order.

### State definitions

| State | Meaning |
|---|---|
| `RECEIVED` | A durable run request and initial run projection exist. No input has been accepted yet. |
| `VALIDATING` | Input shape, source eligibility, access context, and safety constraints are being checked. |
| `QUEUED` | Validation passed and the run is eligible for asynchronous processing. Queue transport details remain owned by `CONTRACT-QUEUE-001`. |
| `PLANNING` | A bounded workflow plan is being produced. |
| `LOCALISING` | Candidate production and test locations are being selected without modifying repository content. |
| `GENERATING` | The initial test-only candidate patch is being generated. |
| `EXECUTING_BUGGY` | The initial or repaired candidate test is compiled and executed against the buggy baseline to establish failure evidence. |
| `EXECUTING_FIXED` | The same candidate test is compiled and executed against the fixed/reference condition. |
| `REPAIRING` | The single allowed automated repair of the test-only candidate is being generated. |
| `SCORING` | Execution-backed evidence and candidate quality are evaluated. |
| `PUBLISHING` | Bounded evidence metadata and an allowed draft/comment publication are being prepared or written. |
| `AWAITING_HUMAN_REVIEW` | Automation is finished and a human decision is required. |
| `COMPLETED` | The run ended after a recorded human disposition or an attributable no-review benchmark system completion. |
| `ABSTAINED` | The workflow safely declined to produce or publish a candidate for a stable abstention reason. |
| `FAILED_INPUT` | Input validation failed and cannot be retried without a corrected request. |
| `FAILED_MODEL` | A model/provider or model-output failure prevented safe continuation. |
| `FAILED_EXECUTION` | Candidate compilation/execution could not produce the required deterministic evidence. |
| `FAILED_INFRASTRUCTURE` | A bounded infrastructure failure exhausted the configured retry policy. |
| `FAILED_SECURITY` | A security or tool-policy violation stopped the run. |
| `CANCELLED` | A cancellation request won the terminal-state race and automation stopped cooperatively. |

## Allowed transitions

Only the following transitions are valid. Absence from this table means the
transition MUST be rejected without changing the projection or appending a
transition event.

| From | Allowed next states |
|---|---|
| `RECEIVED` | `VALIDATING`, `CANCELLED` |
| `VALIDATING` | `QUEUED`, `FAILED_INPUT`, `FAILED_INFRASTRUCTURE`, `FAILED_SECURITY`, `CANCELLED` |
| `QUEUED` | `PLANNING`, `FAILED_INFRASTRUCTURE`, `FAILED_SECURITY`, `CANCELLED` |
| `PLANNING` | `LOCALISING`, `ABSTAINED`, `FAILED_MODEL`, `FAILED_INFRASTRUCTURE`, `FAILED_SECURITY`, `CANCELLED` |
| `LOCALISING` | `GENERATING`, `ABSTAINED`, `FAILED_MODEL`, `FAILED_INFRASTRUCTURE`, `FAILED_SECURITY`, `CANCELLED` |
| `GENERATING` | `EXECUTING_BUGGY`, `ABSTAINED`, `FAILED_MODEL`, `FAILED_INFRASTRUCTURE`, `FAILED_SECURITY`, `CANCELLED` |
| `EXECUTING_BUGGY` | `EXECUTING_FIXED`, `REPAIRING`, `ABSTAINED`, `FAILED_EXECUTION`, `FAILED_INFRASTRUCTURE`, `FAILED_SECURITY`, `CANCELLED` |
| `EXECUTING_FIXED` | `REPAIRING`, `SCORING`, `ABSTAINED`, `FAILED_EXECUTION`, `FAILED_INFRASTRUCTURE`, `FAILED_SECURITY`, `CANCELLED` |
| `REPAIRING` | `EXECUTING_BUGGY`, `ABSTAINED`, `FAILED_MODEL`, `FAILED_INFRASTRUCTURE`, `FAILED_SECURITY`, `CANCELLED` |
| `SCORING` | `PUBLISHING`, `AWAITING_HUMAN_REVIEW`, `COMPLETED`, `ABSTAINED`, `FAILED_INFRASTRUCTURE`, `FAILED_SECURITY`, `CANCELLED` |
| `PUBLISHING` | `AWAITING_HUMAN_REVIEW`, `COMPLETED`, `FAILED_INFRASTRUCTURE`, `FAILED_SECURITY`, `CANCELLED` |
| `AWAITING_HUMAN_REVIEW` | `COMPLETED` |

The `COMPLETED` transitions from `SCORING` and `PUBLISHING` are valid only for
an explicitly configured `BENCHMARK` run with `review_required == false` and
only after durable evidence packaging. Every other successful run MUST enter
`AWAITING_HUMAN_REVIEW` before `COMPLETED`.

The sole bounded lifecycle loop is a repair from either execution state to
`REPAIRING`, followed by `EXECUTING_BUGGY` and then `EXECUTING_FIXED`.
`EXECUTING_BUGGY` is the only non-terminal continuation from `REPAIRING`; its
other allowed targets are terminal safety exits and cannot authorize another
repair. A retry within one state is represented by a new step attempt, not a
self-transition. Regeneration creates a new run; it is not a transition back
to generation.

### Terminal-state immutability

The terminal states are `COMPLETED`, `ABSTAINED`, `FAILED_INPUT`,
`FAILED_MODEL`, `FAILED_EXECUTION`, `FAILED_INFRASTRUCTURE`,
`FAILED_SECURITY`, and `CANCELLED`. They have no outgoing transitions.

Once a terminal transition commits, state, terminal timestamp, terminal code,
and terminal attribution MUST NOT be changed. Later explanatory metadata MAY
be appended as a separate non-transition event, but MUST NOT rewrite history.

## DB-002 core projections

DB-002 owns durable run-request and current-run projections. Names below are
logical contract fields; Database may choose physical names while preserving
meaning and constraints.

### Run request projection

| Field | Requirement |
|---|---|
| `id` | Internal UUID primary identifier. |
| `request_kind` | `GITHUB` or `BENCHMARK`; additive kinds require a compatible contract revision. |
| `idempotency_key` | Required opaque digest/string derived from the applicable composition below; unique in the Database-defined request scope. |
| `github_delivery_guid` | Nullable external delivery GUID; separate from every UUID. |
| `github_repository_id` | Nullable GitHub numeric repository ID; separate from repository UUID. |
| `repository_sha` | Nullable immutable source commit SHA; never used as a UUID. |
| `benchmark_project_id` | Nullable external benchmark project ID. |
| `benchmark_bug_id` | Nullable external benchmark bug ID. |
| `configuration_version` | Required immutable workflow configuration version. |
| `model_id` | Required external/provider model identifier. |
| `prompt_template_version` | Required immutable prompt-template version. |
| `requested_by_subject` | Provisional Auth-owned identity reference; DB-002 MUST NOT freeze its final shape before `CONTRACT-AUTH-001`. |
| `correlation_id` | Bounded external correlation value; not an identity key. |
| `created_at` | Server-authored UTC timestamp. |

`GITHUB` requests require the three GitHub/source fields and prohibit benchmark
fields. `BENCHMARK` requests require both benchmark fields and prohibit the
GitHub delivery GUID. Repository scope for a benchmark remains an internal
repository relation, never an overloaded benchmark identifier.

### Run projection

| Field | Requirement |
|---|---|
| `id` | Internal UUID primary identifier. |
| `run_request_id` | Internal UUID foreign key to the immutable request. |
| `state` | Exact canonical `RunState`; initial value `RECEIVED`. |
| `contract_version` | Exact workflow contract version used to start/resume the run. |
| `review_required` | Required immutable boolean. `GITHUB` runs default to `true`; `BENCHMARK` runs default to `true` and MAY be explicitly configured `false`. |
| `repair_attempts_used` | Integer constrained to `0..1`; initial value `0`. |
| `retry_attempts_used` | Non-negative infrastructure/transport retry counter; initial value `0` and never greater than `retry_limit`. |
| `retry_limit` | Non-negative immutable limit snapshotted from run configuration. |
| `step_attempts_used` | Non-negative aggregate counter or derived projection; it does not authorize repair. |
| `version` | Non-negative optimistic-concurrency value incremented on projection mutation. |
| `created_at` | Server-authored UTC timestamp. |
| `updated_at` | Server-authored UTC timestamp, monotonic per committed mutation. |
| `terminal_at` | Required exactly when `state` is terminal. |
| `failure_code` | Required only for a `FAILED_*` terminal state and compatible with that state. |
| `abstention_code` | Required only for `ABSTAINED`. |
| `cancellation_code` | Required only for `CANCELLED`. |
| `terminal_actor_type` / `terminal_actor_id` | Required terminal attribution; Auth-owned human identity shape remains provisional. |
| `checkpoint_ref` | Nullable opaque reference to the latest committed checkpoint; no raw repository, patch, prompt, or log bytes. |
| `parent_run_id` | Nullable internal UUID identifying the prior completed run when a human requests regeneration. |

DB-002 stores the request and current projection. DB-003 owns normalized
workflow steps, attempts, events, and event ordering. The run projection MUST
be reconstructable from DB-003 transition events once those records exist.

### UUID and external-ID separation

Every internal record uses its own UUID. GitHub IDs, delivery GUIDs, commit
SHAs, Defects4J project/bug IDs, model IDs, prompt versions, provider request
IDs, correlation IDs, and future queue message IDs MUST remain separately
typed/stored values. No external identifier may populate or masquerade as an
internal UUID.

### Idempotency composition

- GitHub-triggered request identity MUST include normalized
  `github_delivery_guid + github_repository_id + repository_sha`.
- Benchmark request identity MUST include normalized
  `benchmark_project_id + benchmark_bug_id + configuration_version + model_id
  + prompt_template_version`.
- Composition MUST be unambiguous (canonical encoding or length-prefixing),
  versioned, and hashed when stored as a bounded key.
- The same full normalized tuple in the same regeneration scope MUST resolve to
  the same run request. A conflicting payload under the same tuple MUST be
  rejected, not overwritten.
- A human-requested regeneration MUST extend the applicable base composition
  with `parent_run_id + human_decision_event_id`. This creates a distinct but
  itself idempotent request without weakening the required base composition.
- Queue delivery/message identity is not part of semantic run-request identity
  and remains provisional until `CONTRACT-QUEUE-001`.

## Lifecycle counters and constraints

- `repair_attempts_used` MUST be `0` or `1`.
- Entering `REPAIRING` atomically changes `repair_attempts_used` from `0` to
  `1`. Entry when it is already `1` MUST be rejected.
- The initial generated candidate is not a repair.
- A repairable candidate compile/test failure in either `EXECUTING_BUGGY` or
  `EXECUTING_FIXED` MAY enter `REPAIRING`.
- A repaired candidate MUST return only to `EXECUTING_BUGGY` and repeat the
  required `EXECUTING_BUGGY -> EXECUTING_FIXED` sequence. Prior evidence
  remains immutable; the repeated sequence establishes complete
  fail-on-buggy/pass-on-fixed evidence for the repaired candidate.
- A second repair is explicitly rejected. If the repaired candidate cannot
  complete the required execution sequence, it MUST terminate or abstain from
  the applicable execution state without returning to `REPAIRING`.
- `REPAIRING -> ABSTAINED` means bounded policy could not produce a trustworthy
  repaired candidate. `FAILED_MODEL`, `FAILED_INFRASTRUCTURE`, and
  `FAILED_SECURITY` record their corresponding exhausted or rejected repair
  outcome. `CANCELLED` remains valid because repair precedes publication and
  review. None of these terminal exits may authorize another repair.
- Infrastructure/transport retries do not change `repair_attempts_used`.
- Scheduling an infrastructure/transport retry atomically increments
  `retry_attempts_used`; scheduling is rejected when
  `retry_attempts_used == retry_limit`.
- Each retry/step attempt has a zero-based `attempt_index`, with uniqueness on
  `(run_id, step_kind, occurrence, attempt_index)`.
- Every retry class has an immutable per-run configured maximum. Exhaustion
  transitions to the matching failure/abstention state; no counter permits an
  open-ended loop.

## Workflow step kinds and attempts

The normative workflow-step kinds are:

`VALIDATE_INPUT`, `PLAN`, `LOCALISE`, `GENERATE_CANDIDATE`,
`EXECUTE_BUGGY`, `EXECUTE_FIXED`, `REPAIR_CANDIDATE`, `SCORE_EVIDENCE`,
`PUBLISH_DRAFT`, and `HUMAN_REVIEW`.

Queue wait/delivery is transport metadata, not a workflow-step kind until
`CONTRACT-QUEUE-001` says otherwise.

Each DB-003 step occurrence MUST have an internal UUID, run UUID, kind,
positive `occurrence`, created timestamp, and immutable input/version
references. Each attempt MUST have an internal UUID, step UUID, zero-based
`attempt_index`, start/end timestamps, outcome, actor attribution, and bounded
error/evidence references. An attempt is append-only after completion.

An infrastructure retry creates a new attempt under the same occurrence. A
semantic automated repair creates the single `REPAIR_CANDIDATE` occurrence,
then a new `EXECUTE_BUGGY` occurrence followed by a new `EXECUTE_FIXED`
occurrence. Retries MUST NOT create another run request or silently replace an
earlier attempt.

## Ordered append-only events

DB-003 events have this normative logical shape:

| Field | Requirement |
|---|---|
| `id` | Internal UUID. |
| `run_id` | Internal run UUID. |
| `sequence` | Positive integer, gap-tolerant and strictly increasing per run. |
| `event_type` | Stable versioned type such as `STATE_TRANSITIONED`, `STEP_ATTEMPT_STARTED`, `STEP_ATTEMPT_FINISHED`, `CHECKPOINT_COMMITTED`, `CANCELLATION_REQUESTED`, or `HUMAN_DECISION_RECORDED`. |
| `from_state` / `to_state` | Both required only for a transition event; the pair MUST be allowed above. |
| `step_id` / `step_kind` / `attempt_index` | Nullable step attribution; required when the event concerns an attempt. |
| `actor_type` / `actor_id` | Required attribution. Actor types are `SYSTEM`, `WORKFLOW`, `WORKER`, or `HUMAN`; identity details remain Auth-owned where applicable. |
| `occurred_at` | Producer-observed UTC timestamp. |
| `recorded_at` | Database-authored UTC timestamp. |
| `correlation_id` | Bounded trace correlation value. |
| `causation_event_id` | Nullable internal event UUID. |
| `producer_event_id` | Required stable producer-scoped idempotency value. |
| `contract_version` | Workflow contract version governing the event. |
| `payload` | Bounded, schema-versioned, redacted metadata or opaque references only. |

Events MUST be inserted, never updated or deleted. `(run_id, sequence)` and
`(run_id, producer_event_id)` MUST be unique. Sequence allocation and the
corresponding run projection update MUST commit atomically. Re-delivery of the
same producer event is an idempotent no-op only when its canonical content
matches; conflicting content MUST fail.

Timestamp order is not event order. Consumers order by `sequence`. Every
transition, cancellation request/outcome, checkpoint commit, step attempt
start/finish, terminal reason, and human decision MUST be attributable.

## Checkpoint and resume

- A checkpoint is committed only after its referenced events and projection
  update commit atomically.
- It contains bounded workflow state or an opaque object reference plus
  checksum; never raw secrets, prompts, repository bytes, patch bytes, or logs.
- Resume loads the latest committed projection/event sequence and verifies the
  checkpoint checksum, run version, contract compatibility, and terminal flag.
- A terminal run MUST NOT resume.
- Uncommitted work after the latest checkpoint is discarded or reconciled by
  producer-event idempotency. External side effects MUST use their own stable
  idempotency key before retry.
- Resume MUST continue the current step attempt or append a new bounded retry
  attempt; it MUST NOT decrement counters or erase events. The only contracted
  return to an earlier-declared state is
  `REPAIRING -> EXECUTING_BUGGY` after the repair allowance was consumed;
  resume MUST NOT skip that repaired-candidate buggy execution.
- Queue lease, visibility timeout, redelivery count, and envelope fields remain
  provisional under `CONTRACT-QUEUE-001`.

## Retry and repair semantics

Retries recover the same operation from a transient infrastructure/transport
failure. They are bounded by immutable run configuration, append a distinct
attempt, preserve prior evidence, and do not change lifecycle state unless the
retry budget is exhausted.

Repair is a semantic model action on the test-only candidate. It is permitted
from `EXECUTING_BUGGY` or `EXECUTING_FIXED`, only when
`repair_attempts_used == 0`, and only after a recorded repairable candidate
compile/test failure. Entering `REPAIRING` consumes the allowance even if
the repair step is retried. The repaired candidate returns to
`EXECUTING_BUGGY` and MUST repeat the buggy-then-fixed execution sequence. No
transition or resume path may grant a second repair. If repair generation
cannot continue, it MUST use the matching allowed terminal exit:
`ABSTAINED` for no trustworthy candidate within bounded policy,
`FAILED_MODEL` for exhausted model/provider or structured-output failure,
`FAILED_INFRASTRUCTURE` for exhausted infrastructure failure,
`FAILED_SECURITY` for security/tool-policy rejection, or `CANCELLED` for a
pre-publication cancellation.

## Failure-code taxonomy

Failure codes are stable uppercase values. A consumer MAY preserve an unknown
additive code but MUST use the terminal state as the compatibility boundary.

| Terminal state | Codes |
|---|---|
| `FAILED_INPUT` | `INPUT_MALFORMED`, `INPUT_SOURCE_UNSUPPORTED`, `INPUT_REFERENCE_INVALID`, `INPUT_SCOPE_VIOLATION` |
| `FAILED_MODEL` | `MODEL_PROVIDER_UNAVAILABLE`, `MODEL_OUTPUT_INVALID`, `MODEL_BUDGET_EXHAUSTED`, `MODEL_POLICY_REFUSAL` |
| `FAILED_EXECUTION` | `EXECUTION_COMPILE_ERROR`, `EXECUTION_TIMEOUT`, `EXECUTION_NONDETERMINISTIC`, `EXECUTION_RUNNER_ERROR` |
| `FAILED_INFRASTRUCTURE` | `INFRASTRUCTURE_DATABASE`, `INFRASTRUCTURE_OBJECT_STORE`, `INFRASTRUCTURE_QUEUE`, `INFRASTRUCTURE_CAPACITY`, `INFRASTRUCTURE_RETRY_EXHAUSTED` |
| `FAILED_SECURITY` | `SECURITY_AUTHORIZATION_DENIED`, `SECURITY_SECRET_DETECTED`, `SECURITY_TOOL_POLICY_VIOLATION`, `SECURITY_PRODUCTION_EDIT_ATTEMPT`, `SECURITY_NETWORK_POLICY_VIOLATION` |

Safe user-facing detail belongs in bounded metadata; secrets and raw provider,
tool, repository, patch, prompt, or log content are forbidden.

## Abstention-code taxonomy

`ABSTAINED` requires exactly one of:

- `UNSUPPORTED_LANGUAGE_OR_TEST_FRAMEWORK`
- `BUG_NOT_REPRODUCED`
- `INSUFFICIENT_LOCALISATION_CONFIDENCE`
- `INSUFFICIENT_CONTEXT`
- `NO_SAFE_TEST_ONLY_PATCH`
- `REPAIR_LIMIT_EXHAUSTED`
- `EVIDENCE_INCONCLUSIVE`
- `PUBLICATION_NOT_JUSTIFIED`

Abstention is a successful safety outcome, not a failure retry signal.
`REPAIR_LIMIT_EXHAUSTED` means the initial candidate and the one allowed repair
were insufficient; it MUST NOT authorize another repair.

## Cancellation

A cancellation request records requester attribution, safe reason code, and
time before attempting the terminal transition. Stable cancellation codes are
`USER_REQUESTED`, `SUPERSEDED`, `OPERATOR_REQUESTED`, and `SYSTEM_SHUTDOWN`.

Cancellation is accepted only from an allowed pre-review-boundary state.
Workers stop at the next safe boundary and MUST NOT publish after cancellation
commits. Once a run enters `AWAITING_HUMAN_REVIEW`, cancellation is not
allowed. A cancellation request that loses the race MUST be recorded as not
applied and MUST NOT change an awaiting-review or completed lifecycle. The
first committed terminal transition otherwise wins. Cancellation does not
delete requests, events, checkpoints, or evidence.

`PUBLISHING -> CANCELLED` is valid only while no external review artefact or
publication side effect has committed. After such a side effect commits, a
cancellation request MUST be recorded as not applied; the run MUST proceed to
`AWAITING_HUMAN_REVIEW` or its applicable no-review benchmark completion path,
and the publication MUST NOT be hidden, deleted, or rewritten.

## Human review and regeneration

Automation MUST NOT approve or merge its own output. `AWAITING_HUMAN_REVIEW`
requires an attributable human decision. Allowed dispositions are `APPROVED`,
`REJECTED`, `DISMISSED`, `OUT_OF_SCOPE`, and `REGENERATION_REQUESTED`; each
ends the current run as `COMPLETED`.

`APPROVED` means approved for the separately authorized human-controlled next
action, never automatic merge. `REJECTED` preserves all evidence.
`REGENERATION_REQUESTED` creates a new idempotent run request/run with a new
internal UUID and `parent_run_id` pointing to the completed run. It MUST NOT
transition the old run back to planning/generation, reuse its repair allowance,
or silently replace evidence.

Human-decision record details belong to the Evidence/Database DB-005 boundary;
the lifecycle disposition and attribution rules above are normative here.

An explicitly configured `BENCHMARK` run with `review_required == false` MAY
complete from `SCORING` or `PUBLISHING` after durable evidence packaging.
System completion MUST record attributable `terminal_actor_type` and
`terminal_actor_id`. Automated completion means only that benchmark processing
finished; it MUST NOT mean approval, merge, or permission to publish changes.

## Contract-version compatibility

- Every run, event, checkpoint, and fixture declares the governing contract
  version.
- Versions use semantic-version intent. A major change includes removing or
  renaming a state/code/required field, changing transition meaning, changing
  idempotency composition, or weakening terminal/repair guarantees.
- Minor revisions may add optional fields, event types, failure/abstention
  codes, or non-terminal transitions that older consumers can safely reject.
- Patch revisions clarify text without changing behavior.
- Consumers MUST reject unsupported major versions and MUST NOT resume a run
  under a different major version.
- A producer MUST finish an existing run under its pinned compatible version
  or perform an explicitly tested migration; silent reinterpretation is
  forbidden.
- While this draft awaits acknowledgement, changes remain versioned and
  recorded. `1.0.0-draft.1` is not final consumer approval.

## Required acceptance fixtures

Database and workflow implementations MUST later provide, at minimum:

1. `successful_human_review`: a `review_required == true` path through both
   executions, scoring, optional publication, `AWAITING_HUMAN_REVIEW`, human
   disposition, and completion.
2. `single_repair_success`: a repairable failure from each permitted execution
   source is covered; entry changes the counter `0 -> 1`, then the repaired
   candidate follows `REPAIRING -> EXECUTING_BUGGY -> EXECUTING_FIXED`.
3. `repair_terminal_exits`: each permitted terminal exit from `REPAIRING`
   records the matching bounded reason; none permits another repair.
4. `second_repair_rejected`: attempt to enter repair with counter `1` fails
   without event/projection mutation, followed by safe abstention.
5. `explicit_abstention`: a non-terminal state reaches `ABSTAINED` with a valid
   code and attribution.
6. `cooperative_cancellation`: cancellation before the review/publication
   boundary wins once, preserves history, and blocks publication. Cancellation
   during `PUBLISHING` succeeds only before any external side effect commits;
   later cancellation and cancellation from `AWAITING_HUMAN_REVIEW` are
   recorded as not applied without hiding or rewriting publication.
7. `invalid_and_terminal_transitions`: unlisted, self, second-repair, late
   cancellation, and every outgoing terminal transition are rejected.
8. `ordered_append_only_events`: sequences are ordered and unique; duplicate
   identical producer events are idempotent; conflicting duplicates fail.
9. `checkpoint_resume`: resume continues from the last committed sequence,
   preserves counters, and rejects terminal/incompatible resumes.
10. `idempotent_request_identity`: GitHub and benchmark compositions deduplicate
   exact requests and reject conflicting payloads.
11. `identifier_separation_and_redaction`: internal UUIDs remain distinct and
    event payloads contain no raw secret, prompt, repository, patch, or log
    bytes.
12. `benchmark_system_completion`: an explicitly configured
    `review_required == false` benchmark completes from `SCORING` or
    `PUBLISHING` after durable evidence packaging with system attribution and
    without approval or merge semantics.

These are acceptance requirements, not tests added by this documentation task.

## A2-DATABASE acknowledgement

- Record: `DB-WORKFLOW-CONTRACT-ACK-001`
- Date: 2026-07-31
- Exact contract: `CONTRACT-WORKFLOW-001@1.0.0-draft.1`
- Decision: `ACCEPTED_WITH_NONBREAKING_CLARIFICATIONS`

A2-DATABASE found no conflict with Workflow-owned semantics and accepted the
canonical states, terminal immutability, transition and repair rules,
publication cancellation boundary, review-required completion rules,
identifier separation, idempotency composition, and DB-002/DB-003 ownership
split.

The following non-normative, Database-owned physical mappings preserve, and
do not alter, this contract:

1. `RunState` is stored as text with a Database-owned check constraint.
2. Request kind is stored as text with a Database-owned check constraint.
3. Failure, abstention, and cancellation codes are versioned text values with
   state-shape constraints.
4. Run projection mutations use state/version compare-and-swap optimistic
   concurrency.
5. Request idempotency uses versioned canonical composition, a persisted
   idempotency-key version, a bounded digest, and a request fingerprint for
   conflict detection.
6. DB-002 implements only `run_requests` and `runs`.
7. DB-003 owns workflow steps, attempts, run events, ordering,
   producer-event idempotency, and transition history.
8. Auth-owned identity fields remain provisional until `CONTRACT-AUTH-001`.
9. Queue transport fields remain deferred to `CONTRACT-QUEUE-001`.
10. Evidence and Security payload fields remain deferred to
    `CONTRACT-EVIDENCE-001` and `CONTRACT-SEC-001`.

The Database consumer acknowledgement is complete and merged. `CONTRACT-AUTH-001`
and the merge/state synchronization that previously gated DB-002 are both
satisfied; DB-002 is `PASS` / `VERIFIED_COMPLETE` / `MERGED`. No runtime
readiness is claimed by this contract.

## Post-merge owner reconciliation (non-normative)

This section is non-normative acknowledgement and reconciliation material. It
records owner decisions made after the merge of this contract. It does not
change, qualify, or reinterpret the normative semantic body above.

- Task: `WORKFLOW-DB002-OWNER-RECONCILIATION-001-C1`
- Prompt type: `DOCUMENTATION_RECONCILIATION_ONLY`
- Date: 2026-08-02
- Baseline: `d13e28117ca6266c3ab3ffa7775f63185ab74b3e`
- Normative semantic-section SHA-256, unchanged before and after:
  `6aefc5730cfb9c6138231811e63570854b469813011f47765f98af0bc3fdfe37`

### Merge state

| Item | State |
|---|---|
| `CONTRACT-WORKFLOW-001@1.0.0-draft.1` | `ACKNOWLEDGED_AND_MERGED` |
| Workflow PR #8 | Merged, `7da1132b9e30b51a212aa6574c23e2a832d9a6fd`, 2026-07-31 |
| Database Workflow-reconciliation PR #10 | Merged, `99c8022c9f44e6a54bed624aa0153be7e32f234b`, 2026-08-01 |
| `DB-DEP-011` | `ACCEPTED` / `VERIFIED_COMPLETE` / `CLOSED` |
| DB-002 | `PASS` / `VERIFIED_COMPLETE` / `MERGED` |
| DB-003 | `NOT_STARTED` / `NOT_AUTHORIZED` |
| Workflow runtime | `NOT_IMPLEMENTED` / `NOT_TESTED` |

### Final owner decisions

1. **Semantic integrity** — `SEMANTIC_INTEGRITY_PRESERVED` /
   `NO_SEMANTIC_CHANGE_REQUIRED`. The merged DB-002 implementation introduced
   no conflict with the normative Workflow body. Version remains
   `1.0.0-draft.1`.

2. **`DB-ISSUE-011`** — `ACCEPTED_WITH_DOCUMENTATION_CLARIFICATION`. The
   Database `runs.run_request_id` `UNIQUE` constraint is accepted. One current
   run projection exists per durable request. Regeneration creates a new
   request and a new run. DB-003 event history is not represented by duplicate
   runs.

3. **`DB-ISSUE-012`** — `ACCEPTED_AS_COMPATIBLE`. Anchored uppercase
   failure-family patterns preserve additive-compatible failure codes. The
   terminal state remains the compatibility boundary. This MUST NOT be replaced
   with a frozen failure-code enumeration.

4. **`DB-ISSUE-013`** — `ACCEPTED_FOR_DB002_DEFERRED_FOR_TYPED_CONTRACT`. The
   DB-002 bounded opaque `terminal_actor_id` storage is accepted. No Auth
   foreign key is frozen. The future typed actor relationship remains open,
   deferred, nonblocking, and jointly owned by Auth and Workflow.

5. **DB-002 versus DB-003 boundary** — `DB002_BOUNDARY_ACCEPTED`. DB-002 owns
   the durable request and current run projection only. DB-003 remains
   `NOT_STARTED` / `NOT_AUTHORIZED`.
