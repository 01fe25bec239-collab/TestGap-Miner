# Auth Open Issues

- Parent task: `AUTH-DB002-CONTRACT-001`
- Current task: `AUTH-DB002-CONTRACT-001-C2`
- Consumer review: `DB-AUTH-CONTRACT-ACK-001`
- Scope: `DOCUMENTATION_ONLY_CONTRACT_REPAIR`
- Auth implementation: `NOT_STARTED`
- Auth runtime: `NOT_TESTED`

## `AUTH-ISSUE-001` — Auth contract and records were absent

- Classification: `CLOSED`
- Evidence: The Auth contract and six records exist; management-record repairs
  passed; A2-AUTH final review is complete.
- Resolution: Closed by A2-AUTH acceptance.

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

## `AUTH-ISSUE-008` — Issuer comparison semantics were insufficiently explicit

- Classification: `ADDRESSED_PENDING_DATABASE_REREVIEW`
- Evidence: `CONTRACT-AUTH-001` version `1.0.0-draft.2` defines exact,
  case-sensitive issuer storage and comparison and prohibits
  Database-independent normalization.
- Resolution: A2-DATABASE rereviews the A2-AUTH-accepted repair.

## `AUTH-ISSUE-009` — Access-grant expiration timing was insufficiently explicit

- Classification: `ADDRESSED_PENDING_DATABASE_REREVIEW`
- Evidence: `CONTRACT-AUTH-001` version `1.0.0-draft.2` distinguishes
  `expires_at`, `expired_at`, and `revoked_at` and denies authorization at or
  after a scheduled expiration boundary.
- Resolution: A2-DATABASE rereviews the A2-AUTH-accepted repair.

A2-DATABASE final acknowledgement remains required. Shared-registry consumer
correction, accepted `CONTRACT-WORKFLOW-001`, IdP runtime metadata,
authorization freshness beyond the defined expiration boundary, retention and
redaction guidance, and Auth runtime `NOT_TESTED` remain open. The expected
untracked `auth-contract-review.zip`, `auth-contract-repair-review.zip`, and
`auth-contract-c2-review.zip` artifacts are not task changes and must remain
unmodified and uncommitted.
