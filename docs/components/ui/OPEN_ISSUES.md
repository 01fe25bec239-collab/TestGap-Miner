# UI Open Issues

- Date: 2026-08-02
- Agent 2: `A2-UI`
- Current task: `UI-DOC-BOOTSTRAP-001`
- Prompt type: `DOCUMENTATION_ONLY_BOOTSTRAP`
- Worktree: `/Users/omkar/Documents/TestGap-Miner-wt-ui-bootstrap`
- Branch: `agent2/ui-bootstrap-authdep010`
- Starting commit: `9ac5a242bfbfad839dd41cd51171b4f81db1be85`
- Frontend implementation: `NOT_STARTED`
- Frontend runtime: `NOT_IMPLEMENTED` / `NOT_TESTED`
- `ASSUMED`: `NONE`

Severity vocabulary is `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFORMATIONAL`.

An absent feature is recorded as an absence, not as a vulnerability. At this
commit the UI component has no runtime, so no issue below is an exploitable
finding. Each issue records what is unresolved and who owns resolving it.

## `UI-ISSUE-001` — `AUTH-DEP-004` is pending

- Classification: `OPEN` / dependency gap
- Severity: `HIGH`
- Owner: `A2-DEPLOYMENT`
- Evidence: `docs/components/auth/DEPENDENCY_REQUESTS.md:128-150` —
  `Approval status: PENDING`, `Completion evidence: None`.
- Impact: `AUTH-DEP-004` is the authoritative deployment callback and human
  IdP metadata boundary. Until it is accepted by its owner, the UI has no
  approved provider, no issuer, no audience, no key source, no endpoints, no
  owned dashboard domain, no callback allowlist, no TLS statement, no client
  variable names, and no secret-injection owner.
- Blocks: `UI-004`; `AUTH-002` frontend work.
- Resolution path: A2-DEPLOYMENT accepts `AUTH-DEP-004`. Tracked from the UI
  side as `UI-DEP-DEPLOY-001`.
- Disposition: This task changes nothing about `AUTH-DEP-004`. It remains
  `PENDING`.

## `UI-ISSUE-002` — Final identity provider is unresolved

- Classification: `OPEN` / decision gap
- Severity: `HIGH`
- Owner: `A2-DEPLOYMENT`, with `A2-AUTH`
- Evidence: No provider is named in any accepted Deployment record.
  `docs/components/deployment/ENVIRONMENT_VARIABLES.md` registers eleven
  variables, all database-scoped; zero Auth variables exist.
- Impact: Supabase Auth is recorded as `CONDITIONAL / PENDING AUTH-DEP-004`,
  never as an accepted Deployment decision. A2-UI must not build a
  provider-specific browser or server Auth client, and must not represent
  Supabase or any other provider as selected.
- Blocks: `UI-004`.
- Resolution path: `AUTH-DEP-004` acceptance names the provider or approved
  equivalent.

## `UI-ISSUE-003` — Exact issuer, audience, and JWKS source are unresolved

- Classification: `OPEN` / dependency gap
- Severity: `HIGH`
- Owner: `A2-DEPLOYMENT` (values), `A2-BACKEND` (validation), `A2-AUTH` (semantics)
- Evidence: `docs/components/auth/AUTH-001_AUDIT.md:348-350` records wrong-issuer,
  wrong-audience, and JWKS-rotation handling as `NOT_STARTED`, each blocked on
  `AUTH-DEP-004`.
- Impact: The UI cannot assert that any token it forwards will be accepted,
  and cannot design a correct expired-or-rejected-session experience without
  knowing what the backend will reject and how it will report the rejection.
- Blocks: `UI-004`, `UI-005`.
- Resolution path: `AUTH-DEP-004` for values; `CONTRACT-API-001` for the error
  surface.

## `UI-ISSUE-004` — Domain and callback registration are unresolved

- Classification: `OPEN` / dependency gap
- Severity: `HIGH`
- Owner: `A2-DEPLOYMENT`
- Evidence: No owned dashboard domain, exact-match callback allowlist, TLS
  termination statement, or deployed callback registration exists in any
  accepted record.
- Impact: `/auth/callback` is reserved as a UI-owned route, but the deployed
  URL, its registration with the provider, the domain, and TLS termination are
  all unknown. A2-UI owns the route and its user-facing UX; A2-UI does not own
  the deployed registration.
- Blocks: `UI-004`, `UI-010`.
- Resolution path: `AUTH-DEP-004` and `UI-DEP-DEPLOY-001`.

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
- Evidence: No non-production provider tenant, test client, test callback
  registration, or seeded test identity exists in any record. No Auth
  environment variable is registered anywhere
  (`docs/components/auth/AUTH-001_AUDIT.md:573`).
- Impact: Even after `AUTH-DEP-004` is accepted, frontend Auth integration
  tests cannot run without a test configuration. Provider provisioning is
  `NOT_PROVEN` / `NOT_TESTED`. Fixture-only tests can never demonstrate real
  provider behavior and must be labeled as fixture evidence.
- Blocks: `UI-004` verification, `UI-010`.
- Resolution path: `UI-DEP-DEPLOY-001`.

## `UI-ISSUE-010` — Runtime and end-to-end evidence is absent

- Classification: `OPEN` / absent feature
- Severity: `INFORMATIONAL` (absence, not vulnerability)
- Owner: `A2-UI`
- Evidence: `apps/web` is `ABSENT`; `ls apps/` returns exactly `api`;
  `find . -type d -name web` returns nothing; 80 tracked files contain no
  frontend page, route, component, test, manifest, or lockfile.
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

## `UI-ISSUE-012` — `AUTH-DEP-010` still reads `PENDING` in the Auth records

- Classification: `OPEN` / record-synchronization gap
- Severity: `LOW`
- Owner: `A2-AUTH` (record), coordinated with `A2-UI`
- Evidence: `docs/components/auth/DEPENDENCY_REQUESTS.md:300` —
  `Approval status: PENDING`. The Auth summary at lines 309-311 also lists
  `AUTH-DEP-010` among the still-pending requests.
- Impact: A2-UI records `AUTH-DEP-010` as `ACCEPTED_WITH_CONSTRAINTS` via
  `AUTH-DEP-010-RESPONSE-001-R1`; the Auth-side record has not yet been
  updated. Until reconciled, the two records disagree.
- Disposition: `docs/components/auth/**` is Auth-owned and forbidden to this
  task; it was not modified. A2-UI must coordinate the update with A2-AUTH
  rather than editing it. Nonblocking for the documentation bootstrap.

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

Fourteen issues are open. None is an exploitable finding, because the UI
component has no runtime: `apps/web` is `ABSENT` and frontend runtime is
`NOT_IMPLEMENTED` / `NOT_TESTED`.

The controlling blockers are `UI-ISSUE-001` (`AUTH-DEP-004` pending) for every
Auth-touching surface and `UI-ISSUE-008` (no `CONTRACT-API-001`) for every
data-bearing surface. `AUTH-DEP-004` remains `PENDING` and `AUTH-002` remains
`NOT_READY / BLOCKED`; this task changed neither.
