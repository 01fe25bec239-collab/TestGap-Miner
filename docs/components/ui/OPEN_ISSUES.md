# UI Open Issues

- Date: 2026-08-03
- Agent 2: `A2-UI`
- Current task: `UI-AUTH-DEPENDENCY-RECONCILIATION-001-A3-C1`
- Prompt type: `POST_MERGE_UI_DURABLE_STATE_RECONCILIATION`
- Worktree: `/Users/omkar/Documents/TestGap-Miner-wt-ui-auth-dependency-reconciliation`
- Branch: `agent2/ui-auth-dependency-reconciliation`
- Current evidence baseline: `ba4247af2195d4c8e60cb9990f616a95f2c54d54`
- Historical bootstrap baseline: `9ac5a242bfbfad839dd41cd51171b4f81db1be85`
- Frontend implementation: `NOT_STARTED`
- Frontend runtime: `NOT_IMPLEMENTED` / `NOT_TESTED`
- `ASSUMED`: `NONE`

Severity vocabulary is `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFORMATIONAL`.

An absent feature is recorded as an absence, not as a vulnerability. At this
commit the UI component has no runtime, so no issue below is an exploitable
finding. Each issue records what is unresolved and who owns resolving it.

## `UI-ISSUE-001` — `AUTH-DEP-004` runtime remainder

- Classification: `PARTIALLY_RESOLVED` / runtime dependency gap
- Severity: `HIGH`
- Owner: `A2-DEPLOYMENT`
- Historical bootstrap evidence: At baseline `9ac5a24`,
  `docs/components/auth/DEPENDENCY_REQUESTS.md` recorded `Approval status:
  PENDING` and `Completion evidence: None`.
- Current evidence: PR #20 merged A2-DEPLOYMENT's
  `ACCEPTED_WITH_CONSTRAINTS` response; PR #21 merged A2-AUTH's
  acknowledgement. `AUTH-DEP-004` is
  `SATISFIED_FOR_AUTH_CONTRACT_AND_DESIGN`.
- Disposition: Resolved for Auth contract/design. Runtime provisioning,
  production domain, TLS, callback registration, environment values, secret
  injection, and provider test configuration remain open.
- Blocks: Runtime verification for `UI-004` and `UI-010`, not Auth contract
  and design.

## `UI-ISSUE-002` — Provider runtime configuration remains unresolved

- Classification: `PARTIALLY_RESOLVED` / runtime decision gap
- Severity: `HIGH`
- Owner: `A2-DEPLOYMENT`, with `A2-AUTH`
- Historical bootstrap evidence: No provider was named in an accepted
  Deployment record, and the variable registry contained only database-scoped
  names.
- Current evidence: PR #20 selected `SUPABASE_AUTH_WITH_GITHUB_OAUTH` with
  architecture status `APPROVED_FOR_AUTH_CONTRACT_AND_DESIGN`.
- Disposition: Provider selection is resolved for design. Actual Supabase
  provisioning, GitHub OAuth configuration, deployed environment values, and
  runtime behavior remain open and untested.
- Blocks: Runtime implementation and verification for `UI-004`.

## `UI-ISSUE-003` — Runtime issuer, audience, and JWKS validation is unproven

- Classification: `PARTIALLY_RESOLVED` / runtime dependency gap
- Severity: `HIGH`
- Owner: `A2-DEPLOYMENT` (values), `A2-BACKEND` (validation), `A2-AUTH` (semantics)
- Historical bootstrap evidence: `AUTH-001_AUDIT.md` recorded wrong-issuer,
  wrong-audience, and JWKS-rotation handling as `NOT_STARTED`, then blocked on
  `AUTH-DEP-004`.
- Current evidence: PR #20 accepted the issuer template
  `https://<SUPABASE_PROJECT_REF>.supabase.co/auth/v1`, audience
  `authenticated`, and JWKS template
  `https://<SUPABASE_PROJECT_REF>.supabase.co/auth/v1/.well-known/jwks.json`
  for design. Issuer comparison is exact and case-sensitive; independent
  normalization is prohibited.
- Disposition: Design templates are accepted. Runtime values, key retrieval,
  validation, rejection behavior, and rotation handling remain unproven.
- Blocks: Runtime verification for `UI-004`; `CONTRACT-API-001` error handling
  for `UI-005`.

## `UI-ISSUE-004` — Production domain and callback registration remain unresolved

- Classification: `PARTIALLY_RESOLVED` / runtime dependency gap
- Severity: `HIGH`
- Owner: `A2-DEPLOYMENT`
- Historical bootstrap evidence: No accepted deployed callback template,
  production domain, exact-match allowlist, TLS statement, or callback
  registration existed.
- Current evidence: PR #20 accepted `${DASHBOARD_ORIGIN}/auth/callback` and
  `http://localhost:3000/auth/callback` as design templates and requires
  exact-match redirect allowlisting.
- Impact: `/auth/callback` remains a UI-owned, unimplemented route. The actual
  production origin, provider registration, deployed domain, and verified TLS
  remain absent.
- Blocks: `UI-004`, `UI-010`.
- Disposition: Callback design is resolved; production registration, domain,
  TLS, and runtime evidence remain open under `UI-DEP-DEPLOY-001`.

## `UI-ISSUE-005` — Cookie and session boundary is unresolved

- Classification: `OPEN` / contract gap
- Severity: `HIGH`
- Owner: `A2-AUTH` (semantics), `A2-SECURITY` (final acceptance)
- Evidence: `docs/components/auth/COMPONENT_STATUS.md:32` records
  "Auth implementation — CORS, CSRF, cookies, callback allowlist" as
  `NOT_STARTED`.
- Impact: Cookie names, `Secure` / `HttpOnly` / `SameSite` flags, cookie
  domain and path, session lifetime, refresh timing, and which side holds the
  session are all undefined. The UI-side custody rules are fixed (no token in
  `localStorage`, no duplicate custom token store, refresh token never
  forwarded, bearer `Authorization` transport), but they do not substitute for
  the Auth-owned session semantics.
- Blocks: `UI-004`, `UI-010`.
- Resolution path: A2-AUTH publishes session semantics; A2-SECURITY with
  A2-AUTH accepts the posture. Tracked as `UI-DEP-AUTH-001` and
  `UI-DEP-SECURITY-001`.

## `UI-ISSUE-006` — PKCE and OAuth-state handling are unresolved

- Classification: `OPEN` / contract gap
- Severity: `HIGH`
- Owner: `A2-AUTH`, accepted with `A2-SECURITY`
- Evidence: `docs/components/auth/AUTH-001_AUDIT.md:343` describes the intended
  dashboard-login path as "redirect to IdP with `state` + PKCE", and records it
  as `NOT_STARTED` with no implementation and no test.
- Impact: Which component generates, stores, and verifies the `state` value and
  the PKCE verifier — and where they are stored — is undefined. The UI must not
  invent this; an incorrect guess would be a real security defect once code
  exists.
- Blocks: `UI-004`.
- Resolution path: `UI-DEP-AUTH-001`, accepted by A2-SECURITY under
  `UI-DEP-SECURITY-001`.

## `UI-ISSUE-007` — CSRF and CORS posture are unresolved

- Classification: `OPEN` / contract gap
- Severity: `HIGH`
- Owner: `A2-BACKEND` (backend CORS), `A2-AUTH` with `A2-SECURITY` (CSRF)
- Evidence: `docs/components/auth/AUTH-001_AUDIT.md:319` records boundary `B4`
  as `PARTIAL` with "no auth of any kind"; there is no middleware in
  `apps/api/app/main.py`. FastAPI's default emits no CORS headers, which is the
  restrictive default.
- Impact: The allowed frontend origin, credentialed-request policy, preflight
  behavior, and CSRF defence are undefined. Backend CORS is not a UI-owned
  decision, and the UI must not assume an origin will be allowed.
- Blocks: `UI-005`, `UI-010`.
- Resolution path: `UI-DEP-BACKEND-001` and `UI-DEP-SECURITY-001`.

## `UI-ISSUE-008` — Backend authenticated-route and error contract is absent

- Classification: `OPEN` / contract gap
- Severity: `HIGH`
- Owner: `A2-BACKEND`
- Evidence: `apps/api/app/main.py` is three lines with no routes.
  `CONTRACT-API-001` is not published in `docs/`.
- Impact: The UI has no route surface, no request or response model, no
  pagination scheme, no authenticated request context, and no error envelope to
  bind to. Every data-bearing UI surface is blocked. The error envelope matters
  specifically because the UI must render a safe message, surface a
  `request_id` for support, and never leak `details` that could contain
  sensitive content.
- Blocks: `UI-005`, `UI-006`, `UI-007`, `UI-008`, `UI-009`.
- Resolution path: `UI-DEP-BACKEND-001`.

## `UI-ISSUE-009` — Provider test configuration is absent

- Classification: `OPEN` / dependency gap
- Severity: `MEDIUM`
- Owner: `A2-DEPLOYMENT`, with `A2-AUTH`
- Historical bootstrap evidence: No Auth environment-variable name or
  non-production provider configuration was registered.
- Current evidence: PR #20 registered the Auth variable names
  `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`,
  `SUPABASE_GITHUB_CLIENT_ID`, `SUPABASE_GITHUB_CLIENT_SECRET`,
  `AUTH_JWT_ISSUER`, `AUTH_JWT_AUDIENCE`, `AUTH_JWKS_URL`, and
  `DASHBOARD_ORIGIN`, without values.
- Impact: Variable-name registration is design evidence only. No provider
  tenant, test client, test callback registration, seeded identity, injected
  runtime value, or frontend Auth integration test exists. Fixture-only tests
  cannot demonstrate provider behavior.
- Blocks: `UI-004` verification, `UI-010`.
- Resolution path: `UI-DEP-DEPLOY-001`.

## `UI-ISSUE-010` — Runtime and end-to-end evidence is absent

- Classification: `OPEN` / absent feature
- Severity: `INFORMATIONAL` (absence, not vulnerability)
- Owner: `A2-UI`
- Current evidence: `apps/web` is `ABSENT`; no frontend page, layout, route,
  component, test, manifest, or lockfile exists. Frontend implementation is
  `NOT_STARTED`.
- `HISTORICAL BOOTSTRAP EVIDENCE AT BASELINE 9ac5a24`: the repository then
  contained 80 tracked files and no frontend artefact listed above.
- Impact: There is no build, no render, no accessibility audit, no end-to-end
  run, and no screenshot. Frontend runtime is `NOT_IMPLEMENTED` /
  `NOT_TESTED`, and frontend Auth tests are `NOT_STARTED` / `NOT_TESTED`. No
  UI claim of "working" is admissible until this is resolved.
- Blocks: `UI-010`.
- Resolution path: `UI-002` onward, after Agent 1 authorization.

## `UI-ISSUE-011` — `SPECIFICATION_INDEX.md` does not list `A2_UI_MANAGER.md`

- Classification: `OPEN` / documentation gap
- Severity: `LOW`
- Owner: `A2-UI` to raise; Agent 1 to authorize the edit
- Evidence: `docs/specifications/SPECIFICATION_INDEX.md` lists only
  `00_AGENT1_DECOMPOSITION_AND_INDEX(1).md` and `A2_DATABASE_MANAGER(1).md`
  under authoritative management documents.
- Impact: The new UI manager specification is not discoverable from the index.
- Disposition: `SPECIFICATION_INDEX.md` is explicitly forbidden to
  `UI-DOC-BOOTSTRAP-001` and was not modified. The index edit requires separate
  Agent 1 authorization. Nonblocking.

## `UI-ISSUE-012` — `AUTH-DEP-010` Auth-record reconciliation

- Classification: `RESOLVED` / record synchronization
- Severity: `LOW`
- Owner: `A2-AUTH` (record), coordinated with `A2-UI`
- Historical bootstrap evidence: The Auth-side record at baseline `9ac5a24`
  still read `Approval status: PENDING`, while UI recorded
  `ACCEPTED_WITH_CONSTRAINTS`.
- Current evidence: A2-AUTH acknowledged `AUTH-DEP-010`, recorded
  `SATISFIED_FOR_OWNERSHIP_AND_COORDINATION`, and merged its reconciliation
  through PR #21.
- Disposition: Resolved by PR #21. Auth-owned records were inspected but not
  modified by this UI task.

## `UI-ISSUE-013` — Manager title variance

- Classification: `OPEN` / naming
- Severity: `INFORMATIONAL`
- Owner: Agent 1
- Evidence: `docs/specifications/00_AGENT1_DECOMPOSITION_AND_INDEX(1).md:30`
  names A2-UI "Frontend and UI Component Manager". The `UI-DOC-BOOTSTRAP-001`
  prompt titled it "Dashboard and Frontend Component Manager".
- Disposition: `A2_UI_MANAGER.md` retains the Agent 1 index title as canonical
  and records the variance. Not resolved by assumption. Nonblocking.

## `UI-ISSUE-014` — Future Workflow, Evidence, and API contracts are needed for full Dashboard function

- Classification: `OPEN` / future contract need
- Severity: `MEDIUM`
- Owners: `A2-AGENT-WORKFLOW`, `A2-BACKEND`, `A2-EVALUATION`
- Evidence: No UI-facing projection exists for `CONTRACT-WORKFLOW-001`
  (run states, workflow steps, failure codes, retry and abstention
  transitions), `CONTRACT-EVIDENCE-001` (candidate patch, execution attempt,
  evidence card, artefact manifest), `CONTRACT-EVAL-001` (benchmark case,
  metric result, baseline, release-gate result), or `CONTRACT-API-001` (the
  transport that carries all of them).
- Impact: The two PRD-named UI surfaces — the evidence card and the benchmark
  dashboard — cannot be specified, built, or tested without these. Specific
  unknowns include: which run states are user-visible and how terminal
  failures are distinguished; how an evidence card proves execution on buggy
  and fixed revisions; how artefacts are referenced and how short-lived
  download URLs are issued and expire; how a human accept, reject, regenerate,
  or dismiss decision is submitted and rendered as an immutable audit event;
  and which benchmark metrics and baselines are displayed.
- Blocks: `UI-006`, `UI-007`, `UI-008`, `UI-009`.
- Resolution path: A2-UI opens the future Workflow, Evidence, and Evaluation
  dependency requests once `UI-001` establishes the concrete UI data needs.
  Recorded as pending in `DEPENDENCY_REQUESTS.md`.

## Summary

Thirteen issues remain open or partially resolved; `UI-ISSUE-012` is resolved
by PR #21. None is an exploitable UI finding because `apps/web` remains
`ABSENT` and frontend runtime is `NOT_IMPLEMENTED / NOT_TESTED`.

`AUTH-DEP-004` and `AUTH-DEP-010` are no longer pending. The controlling Auth
blockers are the runtime remainders in `UI-ISSUE-001` through
`UI-ISSUE-007` and `UI-ISSUE-009`: provisioning, runtime values, deployed
domain/TLS/callback registration, complete Auth semantics, Security
acceptance, and provider test configuration. `UI-ISSUE-008` remains the
controlling blocker for every data-bearing surface. Runtime, implementation,
session, Security, Backend, Workflow, Evidence, and Evaluation issues remain
open without additional evidence.
