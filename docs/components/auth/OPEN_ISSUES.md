# Auth Open Issues

- Current task: `AUTH-DB002-CONTRACT-001`
- Scope: `DOCUMENTATION_ONLY`
- Evidence baseline: `739a331c9942ed64a1ad8276d611889bbee53a27`
- Auth implementation: `NOT_STARTED`
- Auth runtime: `NOT_TESTED`

## `AUTH-ISSUE-001` — Auth contract and records were absent

- Classification: `ADDRESSED_PENDING_REVIEW`
- Evidence: the baseline contained no `docs/components/auth/` record set.
- Resolution: this task authors the contract and six records; A2-AUTH review
  and A2-DATABASE acknowledgement remain required.

## `AUTH-ISSUE-002` — Shared registry omits the Database consumer

- Classification: `OPEN`
- Evidence: the shared registry lists Backend, UI, Security, and Integration as
  Auth-contract consumers but omits A2-DATABASE, although DB-002 is blocked by
  `DB-DEP-001`.
- Resolution: Agent 1 or A2-INTEGRATION corrects its owned registry. This task
  does not edit shared specifications.

## `AUTH-ISSUE-003` — Auth/Database contract-first sequencing

- Classification: `BLOCKED`
- Evidence: Database must not invent Auth-owned identity fields.
- Resolution: A2-DATABASE acknowledges `CONTRACT-AUTH-001` before DB-002 uses
  it. DB-002 also awaits `CONTRACT-WORKFLOW-001`.

## `AUTH-ISSUE-004` — Identity-provider runtime metadata is not frozen

- Classification: `OPEN`
- Evidence: issuer, audience, callback values, and JWT runtime validation are
  outside this contract.
- Resolution: obtain Deployment and Auth runtime decisions before
  implementation.

## `AUTH-ISSUE-005` — Workflow actor integration is pending

- Classification: `BLOCKED`
- Evidence: `CONTRACT-WORKFLOW-001` is pending.
- Resolution: A2-AGENT-WORKFLOW confirms compatibility with the canonical actor
  types and traceable publication trigger.

## `AUTH-ISSUE-006` — Authorization freshness and retention are not frozen

- Classification: `OPEN`
- Evidence: live GitHub revalidation cadence and exact retention durations
  depend on Security and Deployment guidance.
- Resolution: obtain owner decisions before final Auth acceptance.

## `AUTH-ISSUE-007` — Auth runtime is unimplemented

- Classification: `NOT_TESTED`
- Evidence: this task authorizes documentation only; no Auth implementation or
  tests exist from it.
- Resolution: schedule implementation only after contract acceptance.

No code or tests are authorized here. A2-DATABASE consumer acknowledgement is
required before the Auth dependency is accepted.
