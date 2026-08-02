# Auth Dependency Requests

- Date: 2026-08-02
- Current task: `AUTH-001-C2` — Auth task-graph reconciliation
- Parent task: `AUTH-001`
- Prompt type: `CONTINUATION`
- Scope: `DOCUMENTATION_ONLY_TASK_GRAPH_RECONCILIATION`
- Base commit: `1511f474ee301651b631c8adfe406aeb775327aa`
- Auth identity persistence: `VERIFIED_COMPLETE` and merged
- Auth runtime implementation: `NOT_STARTED`
- Auth runtime: `NOT_TESTED`

## Database consumer review

- Consumer review: `DB-AUTH-CONTRACT-ACK-001`
- Initial A2-DATABASE result: `ACKNOWLEDGED_WITH_CHANGES`
- Requested changes: issuer comparison semantics; access-grant expiration
  timing.
- Auth response: Addressed in `CONTRACT-AUTH-001` version `1.0.0-draft.2`.
- Current approval status: `COMPLETE / ACKNOWLEDGED_AND_MERGED`
- Completion evidence: A2-DATABASE recorded
  `CONTRACT-AUTH-001@1.0.0-draft.2` as `ACKNOWLEDGED_AND_MERGED`
  (`docs/components/database/COMPONENT_STATUS.md:17-19`,
  `DECISION_LOG.md:20`, `TASK_LEDGER.md:10`) and implemented DB-002 against
  it. `DB-002` is `PASS / VERIFIED_COMPLETE / MERGED` via PR #12
  (implementation `5506ab5`, merge `3701520`), closed by PR #13 (`1511f47`).
  No rereview is outstanding.

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
- Proposed acceptance test: Use the original fixture with two users, two
  installations, two repositories, the five conceptual records, and the exact
  access tuple; verify exact case-sensitive issuer uniqueness, absence of
  issuer normalization, separate expiration and revocation timing, historical
  attribution, and absence of local credential fields.
- Approval status: `COMPLETE / ACCEPTED`
- Completion evidence: `CONTRACT-AUTH-001@1.0.0-draft.2` was acknowledged and
  merged by A2-DATABASE and implemented by DB-002. The proposed acceptance
  test is satisfied by 21 passing tests in
  `tests/database/test_auth_constraints.py`, executed 2026-08-02 under
  `AUTH-001`, covering the two-user / two-installation / two-repository
  fixture, exact case-sensitive issuer uniqueness, absence of issuer
  normalization, distinct expiration and revocation timing, historical
  attribution, and absence of local credential fields.

## `AUTH-DEP-001` — Database consumer acknowledgement

- Request ID: `AUTH-DEP-001`
- Requesting Agent 2: `A2-AUTH`
- Owning Agent 2: `A2-DATABASE`
- Required change and reason: Confirm the Auth contract fully defines the
  conceptual records and guarantees needed by DB-002 while Database retains
  ownership of physical persistence.
- Initial response: `ACKNOWLEDGED_WITH_CHANGES`
- Contract affected: `CONTRACT-AUTH-001` and future `CONTRACT-DB-001`
- Exact blocking task: Final closure of `AUTH-DB002-CONTRACT-001` and readiness
  of `DB-002`
- Backward-compatibility impact: Initial contract; incompatible changes may
  require migrations.
- Urgency: `HIGH`
- Proposed acceptance test: Database confirms the original five conceptual
  records and exact access-tuple fixture, exact case-sensitive issuer
  uniqueness, absence of issuer normalization, separate expiration and
  revocation timing, historical attribution, and absence of local credential
  fields.
- Approval status: `COMPLETE / ACCEPTED`
- Completion evidence: A2-DATABASE acknowledged `1.0.0-draft.2` and merged it;
  the five conceptual records are implemented as `users`, `auth_subjects`,
  `github_installations`, `repositories`, and `repository_access`
  (`apps/api/app/db/models/auth.py`). The initial
  `ACKNOWLEDGED_WITH_CHANGES` response is preserved as history. No Database
  action remains outstanding.

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
- Approval status: `PARTIALLY_SATISFIED`
- Completion evidence: `CONTRACT-WORKFLOW-001@1.0.0-draft.1` is accepted and
  merged, and `run_requests`/`runs` carry actor attribution
  (`apps/api/app/db/models/workflow.py`). The acceptance test is **not** met:
  `TERMINAL_ACTOR_TYPES = ("SYSTEM", "WORKFLOW", "WORKER", "HUMAN")` at line
  129 has no `GITHUB_APP_INSTALLATION` value, so publication execution has no
  machine actor. Remainder tracked as `AUTH-DEP-008`.

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

## `AUTH-DEP-004` — Human sign-in and JWT/IdP deployment metadata

- Request ID: `AUTH-DEP-004`
- Requesting Agent 2: `A2-AUTH`
- Owning Agent 2: `A2-DEPLOYMENT`
- Required change and reason: Provide the approved identity provider or
  approved equivalent; canonical issuer; audience; JWKS URL or equivalent key
  source; authorization endpoint; token endpoint; owned dashboard domain;
  human OAuth callback URL/allowlist; TLS termination; client-ID and
  client-secret variable names; and secret-injection ownership. This is the
  authoritative deployment callback and human IdP metadata boundary. Secret
  values remain excluded.
- Contract affected: `CONTRACT-AUTH-001` and `CONTRACT-DEPLOY-001`
- Exact blocking task: `AUTH-002`, `AUTH-003`, and `AUTH-007`
- Backward-compatibility impact: Runtime configuration unless identifier
  semantics change.
- Urgency: `HIGH`
- Proposed acceptance test: Every listed human IdP/deployment field is
  documented with an explicit owner; callback URLs are exact-match allowlisted;
  TLS termination and secret injection ownership are stated; no secret value
  is present.
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

## `AUTH-DEP-006` — Backend request surface for authenticated Auth controls

- Request ID: `AUTH-DEP-006`
- Requesting Agent 2: `A2-AUTH`
- Owning Agent 2: `A2-BACKEND`
- Required change and reason: Publish the FastAPI route surface, the
  request-dependency mechanism that carries an authenticated principal, the
  error-envelope shape for unauthenticated and unauthorized responses, and a
  webhook route contract that exposes the **raw** request body before JSON
  parsing. Also confirm which component owns adding the JWT/JWKS verification
  dependency to `apps/api/pyproject.toml`. Evidence: `apps/api/app/main.py` is
  a three-line bare `FastAPI()` with no route, dependency, or middleware, and
  the manifest lists no JWT, JWKS, crypto, or outbound HTTP client.
- Contract affected: `CONTRACT-AUTH-001` and a future `CONTRACT-BACKEND-001`
- Exact blocking task: `AUTH-003`, `AUTH-005`, `AUTH-006`
- Backward-compatibility impact: Additive. No existing route exists to break.
- Urgency: `HIGH`
- Proposed acceptance test: A documented route declares a request dependency
  that rejects an absent or invalid credential before handler code runs; a
  documented webhook route exposes the exact raw body bytes; the error
  envelope for a rejected request contains no token, header, or secret value.
- Approval status: `PENDING`
- Completion evidence: None.

## `AUTH-DEP-007` — Installation reference for exact-tuple authorization

- Request ID: `AUTH-DEP-007`
- Requesting Agent 2: `A2-AUTH`
- Owning Agent 2: `A2-DATABASE`
- Required change and reason: `CONTRACT-AUTH-001` scopes repository
  authorization by the exact `user + installation + repository` tuple, but
  `run_requests` carries only `repository_id` and `requested_by_subject`
  (`apps/api/app/db/models/workflow.py:200-207`) and no installation
  reference. `AUTH-006` therefore cannot authorize a run request against the
  contract tuple from the request row alone. Add an installation reference, or
  document an equivalent representation that preserves the same Auth meaning.
  This is an absent field, not a defect in merged DB-002: DB-002 implemented
  exactly what the accepted contracts specified.
- Contract affected: `CONTRACT-AUTH-001` and `CONTRACT-WORKFLOW-001`
- Exact blocking task: `AUTH-006`
- Backward-compatibility impact: Additive nullable column plus a migration;
  no existing constraint changes. Making it non-nullable later would be
  breaking and requires coordination.
- Urgency: `MEDIUM`
- Proposed acceptance test: Given a persisted run request for a human actor,
  the exact `user + installation + repository` tuple is recoverable from
  persistence alone and matches an `ACTIVE` `repository_access` row, without
  guessing an installation.
- Approval status: `PENDING`
- Completion evidence: None.

## `AUTH-DEP-008` — Machine actor for publication execution

- Request ID: `AUTH-DEP-008`
- Requesting Agent 2: `A2-AUTH`
- Owning Agent 2: `A2-AGENT-WORKFLOW`, with `A2-DATABASE` for persistence
- Required change and reason: `CONTRACT-AUTH-001` requires
  `PUBLICATION_EXECUTE` to use the GitHub App installation actor with
  attribution traceable to an authorized request, event, or human decision.
  No such representation exists:
  `TERMINAL_ACTOR_TYPES = ("SYSTEM", "WORKFLOW", "WORKER", "HUMAN")`
  (`apps/api/app/db/models/workflow.py:129`) has no
  `GITHUB_APP_INSTALLATION` value, and no publication-actor record exists.
  Define how a publication side effect records its machine actor and its
  authorized trigger.
- Contract affected: `CONTRACT-AUTH-001` and `CONTRACT-WORKFLOW-001`
- Exact blocking task: `AUTH-006`, `AUTH-008`
- Integration impact: Also required for Workflow/Database publication
  integration. It does not block `AUTH-004` GitHub App JWT creation,
  installation-token exchange, caching, expiry handling, or permission
  introspection.
- Backward-compatibility impact: Additive if a new actor value or record is
  introduced; changing the meaning of an existing terminal actor value would
  be breaking.
- Urgency: `MEDIUM`
- Proposed acceptance test: A recorded publication side effect names a GitHub
  App installation as its actor, is never representable as a human actor, and
  resolves to an authorized request, event, or human decision. No merge or
  approval semantics are implied.
- Approval status: `PENDING`
- Completion evidence: None.

## `AUTH-DEP-009` — GitHub App and webhook runtime configuration

- Request ID: `AUTH-DEP-009`
- Requesting Agent 2: `A2-AUTH`
- Owning Agent 2: `A2-DEPLOYMENT`
- Required change and reason: Register the GitHub App ID variable name, GitHub
  App private-key variable name, webhook-secret variable name, webhook
  endpoint/public URL, GitHub App setup URL where applicable, installation
  callback/setup metadata where applicable, and the least-privilege GitHub App
  permission set. Explicitly exclude merge, branch-protection bypass, and
  production-code write scopes. This request excludes the human OAuth
  callback, dashboard domain, TLS, and IdP metadata owned by `AUTH-DEP-004`.
- Contract affected: `CONTRACT-AUTH-001` and `CONTRACT-DEPLOY-001`
- Exact blocking task: `AUTH-004`, `AUTH-005`
- Backward-compatibility impact: Additive configuration registry entries.
- Urgency: `HIGH`
- Proposed acceptance test: The App ID, private-key, and webhook-secret
  variable **names**; webhook endpoint/public URL; applicable setup and
  installation callback metadata; and GitHub App permission set are documented
  without secret values. The permission set excludes merge,
  branch-protection-bypass, and production-code-write scopes, and no human IdP
  callback/domain requirement is duplicated.
- Approval status: `PENDING`
- Completion evidence: None.

## `AUTH-DEP-010` — Dashboard frontend ownership

- Request ID: `AUTH-DEP-010`
- Requesting Agent 2: `A2-AUTH`
- Owning Agent 2: `A2-UI`
- Classification: `PROTECTED_FILE_AND_IMPLEMENTATION_OWNERSHIP_CONSTRAINT`
- Required change and reason: `apps/web` does not exist
  (`find . -type d -name web` returns nothing; `ls apps/` returns exactly
  `api`), so trust boundaries B1–B3 — browser to frontend, frontend to
  identity provider, and callback back to the application — have no
  implementing component. Confirm frontend ownership, whether a first-party
  dashboard will exist, protected UI paths, and which side terminates the
  OAuth callback. A3-AUTH and A3-UI must not modify UI-owned paths or perform
  frontend Auth integration tests until this is accepted. This constraint does
  not block `AUTH-002` contract/design work after `AUTH-DEP-004` is accepted.
- Contract affected: `CONTRACT-AUTH-001` and a future UI contract
- Exact blocking task: `AUTH-002` frontend implementation and frontend Auth
  integration tests; not `AUTH-002` contract/design readiness
- Backward-compatibility impact: None yet; nothing is implemented.
- Urgency: `HIGH`
- Proposed acceptance test: A named component owns the browser session and the
  callback endpoint, and the cookie or token custody model is stated
  explicitly.
- Approval status: `PENDING`
- Completion evidence: None.

## Summary

`DB-DEP-001` and `AUTH-DEP-001` are `COMPLETE / ACCEPTED`: DB-002 is merged and
`CONTRACT-AUTH-001@1.0.0-draft.2` is `ACKNOWLEDGED_AND_MERGED`. No Database
rereview is outstanding.

Still `PENDING`: `AUTH-DEP-003` (registry correction), `AUTH-DEP-004` (IdP
metadata), `AUTH-DEP-005` (Security guidance), and the five requests opened by
`AUTH-001` — `AUTH-DEP-006` through `AUTH-DEP-010`. `AUTH-DEP-002` is
`PARTIALLY_SATISFIED`, with its remainder tracked as `AUTH-DEP-008`.

No dependency request authorizes A3-AUTH to modify another component's files,
and none authorizes Auth code, tests, or configuration.
