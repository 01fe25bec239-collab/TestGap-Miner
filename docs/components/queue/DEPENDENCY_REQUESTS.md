# Queue Dependency Requests — CONTRACT-QUEUE-001 consumer review

- Date: `2026-08-04`
- Requester/owner: `A2-QUEUE`
- Contract: `CONTRACT-QUEUE-001@1.0.0-draft.1`
- Status: `DRAFT / PENDING_CONSUMER_REVIEW`
- API dependency: `CONTRACT-API-001@0.1.0-draft.1`
- Rule: silence is not acceptance; no request authorizes runtime or DB-003.

A2-QUEUE's final correction review passed. The Queue contract is ready for
consumer-review dispatch after the additive correction commit is pushed.
Consumer review has not begun, all ten written dispositions remain required,
and silence is not acceptance. Existing review requests remain open and
unchanged.

Every response MUST use `ACCEPTED`, `ACCEPTED_WITH_CONSTRAINTS`,
`REJECTED_WITH_REASON`, or `SPECIFICATION_CONFLICT`. A constraint records the
reviewer, exact section/requirement, rationale, compatibility impact, required
evidence, and closure condition here. Conflicts go to A2-QUEUE plus the owning
reviewer and then the coordinating manager if unresolved. Changes to an
accepted identity, authorization, publication, idempotency, delivery/lease,
result/acknowledgement, cancellation, integrity, dead-letter, retention,
lifecycle, compatibility, or release-gate boundary reopen affected review.

| Request | Reviewer | Exact inspection / owned boundary | Status |
|---|---|---|---|
| `QUEUE-REVIEW-BACKEND-001` | `A2-BACKEND` | Contract §§1.1, 3–6, 16–17: API `202`, durable request/handoff, producer behavior, request/correlation and API/Queue idempotency; API semantics stay Backend-owned. | `OPEN / PENDING_OWNER_REVIEW` |
| `QUEUE-REVIEW-WORKFLOW-001` | `A2-AGENT-WORKFLOW` | §§2, 3.6, 4, 6–9, 13, 15, 17: eligibility, attempts, lifecycle, cancellation, repair, results, terminality; Workflow semantics stay Workflow-owned. | `OPEN / PENDING_OWNER_REVIEW` |
| `QUEUE-REVIEW-DATABASE-001` | `A2-DATABASE` | §§3.2, 4, 6–7, 9–12, 15–17: durable intent/equivalent, fencing, uniqueness, commit, retention/deletion; physical design owned by Database and DB-003 unauthorized. | `OPEN / PENDING_OWNER_REVIEW` |
| `QUEUE-REVIEW-EVIDENCE-001` | `A2-EVIDENCE` | §§2, 4–5, 7, 9–12, 17: opaque references, result binding, deletion/recreation barrier, retention/proof; Evidence semantics stay Evidence-owned. | `OPEN / PENDING_OWNER_REVIEW` |
| `QUEUE-REVIEW-EXECUTION-001` | `A2-EXECUTION` | §§2, 4–9, 11–14, 17: worker identity, claims/renewal/loss, protected effects, checkpoints, result production, cleanup. | `OPEN / PENDING_OWNER_REVIEW` |
| `QUEUE-REVIEW-SECURITY-001` | `A2-SECURITY` | §§2, 4–5, 7–12, 14–17: allow/deny lists, redaction, integrity/canonicalization/keys, events, replay, dead-letter disclosure/retention. | `OPEN / PENDING_OWNER_REVIEW` |
| `QUEUE-REVIEW-AUTH-001` | `A2-AUTH` | §§2–5, 9–10, 12, 16–17: actor/service/authorization references, current authorization, cancellation/re-drive authority and freshness. | `OPEN / PENDING_OWNER_REVIEW` |
| `QUEUE-REVIEW-DEPLOYMENT-001` | `A2-DEPLOYMENT` | §§1–2, 5–6, 8, 10, 12, 14–17: provider adapter/configuration, capacity, timeouts/retries, identities, observability, rollout/rollback. | `OPEN / PENDING_OWNER_REVIEW` |
| `QUEUE-REVIEW-INTEGRATION-001` | `A2-INTEGRATION` | §§1–4, 6–15, 17: cross-contract consistency, provider-neutral conformance, mixed versions, conflict/rollout compatibility. | `OPEN / PENDING_OWNER_REVIEW` |
| `QUEUE-REVIEW-EVALUATION-001` | `A2-EVALUATION` | §§1.2, 7–8, 12–17: measurement provenance, implementation evidence, capacity/latency/reliability and release-gate separation. | `OPEN / PENDING_OWNER_REVIEW` |

## External policy/value requests

- A2-SECURITY/A2-AUTH: security-approved fields, redaction/disclosure,
  authorization freshness, integrity/canonicalization/MAC/signature/key custody,
  Security events, least privilege, and retention policy.
- A2-DATABASE: review a future physical durable-intent/outbox/inbox equivalent,
  fencing and commit model under separate authorization; do not begin DB-003.
- A2-DEPLOYMENT/A2-EVALUATION: measured inputs for provider capacity,
  concurrency, throughput, latency, retry/time values, and release gates.
- A2-EVIDENCE/A2-EXECUTION/A2-AGENT-WORKFLOW: reference, checkpoint, result,
  cancellation, cleanup, deletion, terminality, and accepted-effect semantics.

Implementation acceptance evidence remains required but unavailable because no
runtime is authorized. Release-gate inputs remain distinct and unavailable.
