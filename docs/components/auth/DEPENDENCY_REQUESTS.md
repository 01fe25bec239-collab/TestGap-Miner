# Auth Dependency Requests

- Parent task: `AUTH-DB002-CONTRACT-001`
- Continuation task: `AUTH-DB002-CONTRACT-001-C1`
- Scope: `DOCUMENTATION_ONLY_RECORD_REPAIR`
- Auth implementation: `NOT_STARTED`
- Auth runtime: `NOT_TESTED`

## `DB-DEP-001` — Incoming Auth context request

- Request ID: `DB-DEP-001`
- Requesting Agent 2: `A2-DATABASE`
- Owning Agent 2: `A2-AUTH`
- Required change and reason: Define canonical identity, installation,
  repository, exact access-scope, actor, lifecycle, and secret-exclusion
  semantics so DB-002 does not invent Auth-owned semantics.
- Contract affected: `CONTRACT-AUTH-001`
- Exact blocking task: `DB-002`
- Backward-compatibility impact: Initial contract; incompatible changes may
  require migrations.
- Urgency: `HIGH`
- Proposed acceptance test: Use a fixture with two users, two installations,
  and two repositories to confirm exact user-installation-repository access,
  uniqueness and lifecycle behavior, historical attribution, and absence of
  local credential fields.
- Approval status: `ADDRESSED_PENDING_ACKNOWLEDGEMENT`
- Completion evidence: `CONTRACT-AUTH-001` version `1.0.0-draft.1`

## `AUTH-DEP-001` — Database consumer acknowledgement

- Request ID: `AUTH-DEP-001`
- Requesting Agent 2: `A2-AUTH`
- Owning Agent 2: `A2-DATABASE`
- Required change and reason: Confirm the Auth contract fully defines the
  conceptual records and guarantees needed by DB-002 while Database retains
  ownership of physical persistence.
- Contract affected: `CONTRACT-AUTH-001` and future `CONTRACT-DB-001`
- Exact blocking task: Final closure of `AUTH-DB002-CONTRACT-001` and readiness
  of `DB-002`
- Backward-compatibility impact: Initial contract; incompatible changes may
  require migrations.
- Urgency: `HIGH`
- Proposed acceptance test: Database confirms the five conceptual records,
  uniqueness rules, lifecycle rules, exact access tuple, historical
  attribution, and absence of local credential fields.
- Approval status: `PENDING`
- Completion evidence: None.

## `AUTH-DEP-002` — Workflow actor compatibility

- Request ID: `AUTH-DEP-002`
- Requesting Agent 2: `A2-AUTH`
- Owning Agent 2: `A2-AGENT-WORKFLOW`
- Required change and reason: Confirm workflow persistence can retain canonical
  actor attribution and a traceable authorized publication trigger without
  representing machine actors as humans.
- Contract affected: `CONTRACT-AUTH-001` and `CONTRACT-WORKFLOW-001`
- Exact blocking task: DB workflow persistence, actor attribution, and later
  Auth integration
- Backward-compatibility impact: Initial contracts; incompatible actor changes
  require coordination.
- Urgency: `HIGH`
- Proposed acceptance test: `HUMAN_USER`, `GITHUB_APP_INSTALLATION`,
  `SYSTEM_SERVICE`, and `UNAUTHENTICATED` round-trip without representing
  machine actors as humans; publication execution retains a traceable
  authorized trigger.
- Approval status: `PENDING`
- Completion evidence: None.

## `AUTH-DEP-003` — Shared registry consumer correction

- Request ID: `AUTH-DEP-003`
- Requesting Agent 2: `A2-AUTH`
- Owning Agent 2: `A2-INTEGRATION` or Agent 1
- Required change and reason: Correct the shared registry because it omits
  A2-DATABASE as a blocking consumer of the Auth contract.
- Contract affected: Shared-contract registry
- Exact blocking task: Authoritative coordination closure; not contract
  drafting
- Backward-compatibility impact: Additive documentation correction.
- Urgency: `MEDIUM`
- Proposed acceptance test: A2-DATABASE is listed or explicitly recorded as a
  blocking `CONTRACT-AUTH-001` consumer.
- Approval status: `PENDING`
- Completion evidence: None.

## `AUTH-DEP-004` — Identity-provider runtime metadata

- Request ID: `AUTH-DEP-004`
- Requesting Agent 2: `A2-AUTH`
- Owning Agent 2: `A2-DEPLOYMENT`
- Required change and reason: Document the owned runtime metadata needed for
  sign-in, JWT validation, and hardening without exposing secret values.
- Contract affected: `CONTRACT-AUTH-001` and `CONTRACT-DEPLOY-001`
- Exact blocking task: `AUTH-002`, `AUTH-003`, and `AUTH-007`
- Backward-compatibility impact: Runtime configuration unless identifier
  semantics change.
- Urgency: `MEDIUM`
- Proposed acceptance test: Issuer, audience, callback/domain, TLS, and
  secret-injection variable names are documented without secret values.
- Approval status: `PENDING`
- Completion evidence: None.

## `AUTH-DEP-005` — Security lifecycle and event guidance

- Request ID: `AUTH-DEP-005`
- Requesting Agent 2: `A2-AUTH`
- Owning Agent 2: `A2-SECURITY`
- Required change and reason: Define security-event, authorization freshness,
  retention, and redaction guidance needed for Auth hardening and final
  acceptance.
- Contract affected: `CONTRACT-AUTH-001` and `CONTRACT-SEC-001`
- Exact blocking task: `AUTH-007` and `AUTH-008`
- Backward-compatibility impact: May add lifecycle metadata; identity-breaking
  changes require coordination.
- Urgency: `MEDIUM`
- Proposed acceptance test: Auth security events contain no secrets or tokens
  and define approved authorization freshness, retention, and redaction rules.
- Approval status: `PENDING`
- Completion evidence: None.

DB-002 remains blocked pending A2-DATABASE acknowledgement and accepted
`CONTRACT-WORKFLOW-001`. No dependency request authorizes code, tests, or
Database implementation.
