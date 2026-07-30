# Auth Open Issues

- Parent task: `AUTH-DB002-CONTRACT-001`
- Continuation task: `AUTH-DB002-CONTRACT-001-C1`
- Scope: `DOCUMENTATION_ONLY_RECORD_REPAIR`
- Reviewed implementation commit: `8d8125b2c7d8f40681dee81c61b3cab44e4ca216`
- Auth implementation: `NOT_STARTED`
- Auth runtime: `NOT_TESTED`

## `AUTH-ISSUE-001` — Auth contract and records were absent

- Classification: `ADDRESSED_PENDING_FINAL_A2_REVIEW`
- Evidence: `CONTRACT-AUTH-001` semantic content passed A2-AUTH review. The
  task-ledger and dependency-request record defects identified by A2-AUTH were
  repaired in `AUTH-DB002-CONTRACT-001-C1`.
- Resolution: Final A2-AUTH review of the repaired management records remains
  required before A2-DATABASE handoff.

## `AUTH-ISSUE-002` — Shared registry omits the Database consumer

- Classification: `OPEN`
- Evidence: The shared registry omits A2-DATABASE although DB-002 is blocked by
  `DB-DEP-001`.
- Resolution: Agent 1 or A2-INTEGRATION records A2-DATABASE as a blocking
  `CONTRACT-AUTH-001` consumer. This task does not edit shared specifications.

## `AUTH-ISSUE-003` — Auth/Database contract-first sequencing

- Classification: `BLOCKED`
- Evidence: Database must not invent Auth-owned identity fields.
- Resolution: A2-DATABASE acknowledges `CONTRACT-AUTH-001` before DB-002 uses
  it. DB-002 also awaits accepted `CONTRACT-WORKFLOW-001`.

## `AUTH-ISSUE-004` — Identity-provider runtime metadata is not frozen

- Classification: `OPEN`
- Evidence: Issuer, audience, callback/domain, TLS, secret-injection variable
  names, and JWT runtime validation remain Deployment dependencies.
- Resolution: Obtain Deployment runtime metadata before `AUTH-002`,
  `AUTH-003`, and `AUTH-007`.

## `AUTH-ISSUE-005` — Workflow actor integration is pending

- Classification: `BLOCKED`
- Evidence: `CONTRACT-WORKFLOW-001` has not been accepted.
- Resolution: A2-AGENT-WORKFLOW confirms compatibility with the canonical actor
  types and traceable publication trigger.

## `AUTH-ISSUE-006` — Authorization freshness and retention are not frozen

- Classification: `OPEN`
- Evidence: Authorization freshness, retention, and redaction rules depend on
  Security guidance.
- Resolution: Obtain A2-SECURITY guidance before `AUTH-007` and `AUTH-008`.

## `AUTH-ISSUE-007` — Auth runtime is unimplemented

- Classification: `NOT_TESTED`
- Evidence: This task authorizes documentation only; no Auth implementation or
  runtime tests exist from it.
- Resolution: Schedule implementation only after contract acceptance.

A2-DATABASE consumer acknowledgement remains required. The expected untracked
`auth-contract-review.zip` review artifact is not a task change and must remain
unmodified and uncommitted.
