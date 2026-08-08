# UI Open Issues

- Date: 2026-08-08
- Agent 2: `A2-UI`
- Current task: `UI-AUTH002-CONSUMER-CONFLICT-RECONCILIATION-001-A3`
- Prompt type: `DOCUMENTATION_ONLY / CONFLICT_RESOLUTION / MERGED_FRONTEND_STATE_RECONCILIATION`
- Worktree: `/Users/omkar/Documents/TestGap-Miner-wt-ui-auth002-conflict-reconciliation`
- Branch: `agent2/ui-auth002-conflict-reconciliation`
- Current evidence baseline: `006cc885161ff49be582a9fa08f353a70c31c7b1`
- Historical API-reconciliation baseline: `ab60d4573d398fb610bc2ebb813f76d0c95b33d7`
- Historical bootstrap baseline: `9ac5a242bfbfad839dd41cd51171b4f81db1be85`
- Frontend foundation: `IMPLEMENTED` / `MERGED` / `PRODUCTION_BUILDABLE`
- Frontend Auth behavior: `NOT_IMPLEMENTED` / `NOT_TESTED` / `NOT_AUTHORIZED`
- Auth runtime: `NOT_IMPLEMENTED` / `NOT_TESTED`
- Provider runtime: `NOT_PROVISIONED` / `NOT_TESTED`
- `ASSUMED`: `NONE`

Severity vocabulary is `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFORMATIONAL`.

An absent feature is recorded as an absence, not as a vulnerability. At this
commit the UI component has a merged, buildable frontend foundation but **no
Auth runtime and no session behavior of any kind**, so no issue below is an
exploitable finding. Each issue records what is unresolved and who owns
resolving it.

The merged frontend foundation resolves only those issues whose sole factual
basis was the absence of `apps/web`, Next.js, MUI or a frontend test harness.
It resolves no Auth, Security, Deployment, Backend, API, Workflow, Evidence,
Evaluation or runtime blocker.

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
  `localStorage`, no `sessionStorage`, no duplicate or shadow store, refresh
  token never forwarded, bearer `Authorization` transport — see `UI-DEC-026`
  for the current normative rule), but they do not substitute for the
  Auth-owned session semantics. The cookie posture itself remains
  A2-SECURITY-owned and unresolved under `AUTH-DEP-011`; see `UI-ISSUE-015`.
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

## `UI-ISSUE-008` — API draft is present but not implementation-ready

- Classification: `PARTIALLY_RESOLVED` / draft contract and runtime gap
- Severity: `HIGH`
- Owner: `A2-BACKEND`
- Historical evidence: At baseline `ba4247a`, no API contract was published;
  the UI therefore recorded the route, model, pagination, authenticated
  context, and error surface as absent.
- Current evidence: `CONTRACT-API-001@0.1.0-draft.1` is
  `PRESENT / DRAFT_FOR_CONSUMER_REVIEW / NOT_IMPLEMENTATION_READY`. It proposes
  `/api/v1`, `Authorization: Bearer` access-token transport, refresh-token
  exclusion, a safe `error.code/message/request_id/details` envelope,
  `X-Request-ID`, `X-Correlation-ID`, shared cursor pagination, and polling via
  `Location`.
- Remaining gap: final authenticated-context shape is
  `UNRESOLVED / AUTH_OWNED / RUNTIME_HANDOFF_NOT_FROZEN`; exact `403` versus
  concealed `404` is `UNRESOLVED_PENDING_AUTH_AND_SECURITY`; CORS is
  `UNRESOLVED / DEPLOYMENT_AND_SECURITY_INPUT_REQUIRED /
  BACKEND_CONFIGURATION_NOT_DEFINED`; validating OpenAPI/client fixtures are
  absent; endpoint-specific models and owner projections are partial; and API
  runtime is `NOT_IMPLEMENTED / NOT_TESTED / NOT_AUTHORIZED`.
- Impact: The UI has useful shared transport draft input, but every
  data-bearing implementation surface remains blocked. Safe error rendering
  must use only accepted fields and must never leak raw `details`.
- Blocks: `UI-005`, `UI-006`, `UI-007`, `UI-008`, `UI-009`.
- Resolution path: complete consumer/owner review, freeze the unresolved
  boundaries, provide validating OpenAPI/client fixtures and endpoint models,
  then separately authorize runtime and UI implementation.

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

## `UI-ISSUE-010` — Frontend foundation absence

- Classification: `RESOLVED_FOR_FOUNDATION` / previously absent feature
- Severity: `INFORMATIONAL` (absence, not vulnerability)
- Owner: `A2-UI`
- `HISTORICAL BOOTSTRAP EVIDENCE AT BASELINE 9ac5a24`: the repository contained
  80 tracked files, `apps/web` was `ABSENT`, and no frontend page, layout,
  route, component, test, manifest or lockfile existed.
- Current evidence: `apps/web` is `PRESENT` with eighteen tracked files.
  `UI-002` merged through PR #26 at `c5d4c8a462f6e76aa1dd4929e59012fb2823c999`,
  `UI-003` through PR #27 at `e7de96fc96e665fc32163dc9f26986e0e56e5510`, and
  the regression-test foundation through PR #28 at
  `006cc885161ff49be582a9fa08f353a70c31c7b1`. Every `validate` check passed.
  The foundation is `PRODUCTION_BUILDABLE` with merged automated tests.
- Disposition: The foundation-absence basis for this issue is resolved. It is
  closed **only** for that basis.
- Still open under this issue: no accessibility audit has been accepted for
  `UI-010`; no end-to-end run exists, because there is no API runtime and no
  Auth runtime to run against; no Auth or session behavior has been rendered
  or tested. Frontend Auth behavior remains `NOT_IMPLEMENTED / NOT_TESTED /
  NOT_AUTHORIZED` and frontend Auth tests remain `NOT_STARTED / NOT_TESTED`.
- Blocks: `UI-010`.
- Resolution path: `UI-004` onward after separate authorization, plus API and
  Auth runtimes and A2-INTEGRATION acceptance.

## `UI-ISSUE-015` — `AUTH-002` cookie-custody specification conflict

- Classification: `CONFIRMED / UI_SIDE_CORRECTION_AUTHORIZED /
  AUTH_SIDE_CORRECTION_REQUIRED / A2_UI_REREVIEW_REQUIRED`
- Severity: `HIGH`
- Owners: `A2-UI` (UI-owned correction — applied), `A2-AUTH` (Auth-owned
  correction — outstanding), `A2-SECURITY` with `A2-AUTH` (final cookie
  acceptance under `AUTH-DEP-011`)
- Evidence: A2-UI's consumer review of `CONTRACT-AUTH-001@1.1.0-draft.1`, at
  reviewed Auth PR #29 head `7abe17af8e212bd2127160338ea6ef409da02101`,
  returned `SPECIFICATION_CONFLICT`. The merged `UI-DEC-013` prohibits "any
  non-`HttpOnly` cookie written by UI code"; the Auth candidate contract adopts
  the canonical browser-readable `@supabase/ssr` cookie-backed session and
  states that `HttpOnly` is not achievable for it under the accepted
  architecture. Agent 1 returned `PASS / UI_AUTH_COOKIE_CONFLICT_CONFIRMED /
  UI_OWNED_CORRECTION_AUTHORIZED`.
- UI-owned correction: applied by this task as `UI-DEC-026`, superseding only
  the conflicting non-`HttpOnly`-cookie clause of `UI-DEC-013` and weakening no
  storage prohibition.
- Impact: `AUTH-DEP-012` cannot be `ACCEPTED` and `AUTH-002` cannot be accepted
  while the conflict stands. `UI-004` remains `BLOCKED / NOT_AUTHORIZED`.
- Blocks: `AUTH-DEP-012` acceptance; `AUTH-002` acceptance; `UI-004`.
- **The conflict is not resolved.** It may be classified as resolved only after
  all of the following have occurred:
  1. this UI-owned correction package passes independent A2-UI review;
  2. this UI-owned correction is merged;
  3. the Auth-owned correction is pushed by A2-AUTH;
  4. A2-UI rereviews the corrected Auth PR #29 head.
- Out of scope for A2-UI and A3-UI: `HttpOnly` architecture policy, `SameSite`,
  cookie lifetime, cookie domain, `Secure` exceptions, CSRF,
  callback-correlation storage/integrity/duration, and intended-return-state
  storage and integrity. All are A2-SECURITY-owned and unresolved under
  `AUTH-DEP-011`.

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

## `UI-ISSUE-014` — Owner projections and action semantics are incomplete for full Dashboard function

- Classification: `OPEN` / future contract need
- Severity: `MEDIUM`
- Owners: `A2-AGENT-WORKFLOW`, `A2-BACKEND`, `A2-EVALUATION`
- Historical evidence: At baseline `ba4247a`, no UI-facing API contract was
  published.
- Current evidence: `CONTRACT-API-001@0.1.0-draft.1` now proposes shared
  transport, cursor pagination, polling, and placeholder run surfaces. The
  endpoint-specific projections and actions remain `PARTIAL /
  OWNER_DEPENDENT`. Workflow projections remain incomplete; Evidence and
  Evaluation projections remain absent; Queue delivery semantics remain
  unresolved; and DB-003 inputs remain `NOT_STARTED / NOT_AUTHORIZED`.
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

Fifteen issues are recorded. `UI-ISSUE-012` is resolved by PR #21.
`UI-ISSUE-010` is resolved for its frontend-foundation basis only, by PR #26,
PR #27 and PR #28, and remains open for accessibility acceptance and
end-to-end evidence. `UI-ISSUE-015` is `CONFIRMED` and is **not** resolved.
The remaining twelve stay open or partially resolved.

None is an exploitable UI finding. The merged frontend foundation contains no
Auth client, no session code, no provider client, no protected route and no
`/auth/callback` handler; Auth runtime is `NOT_IMPLEMENTED / NOT_TESTED` and
provider runtime is `NOT_PROVISIONED / NOT_TESTED`, so there is no session,
token or credential in play anywhere in the repository.

`AUTH-DEP-004` and `AUTH-DEP-010` are no longer pending. The controlling Auth
blockers are the runtime remainders in `UI-ISSUE-001` through
`UI-ISSUE-007` and `UI-ISSUE-009`: provisioning, runtime values, deployed
domain/TLS/callback registration, complete Auth semantics, Security
acceptance, and provider test configuration. `UI-ISSUE-008` is partially
resolved by the API draft but remains the controlling contract/runtime blocker
for every data-bearing surface. Runtime, implementation, Auth context,
`403`/`404` disclosure, CORS, validating fixtures, Queue, DB-003, Workflow,
Evidence, and Evaluation issues remain open without additional evidence.
