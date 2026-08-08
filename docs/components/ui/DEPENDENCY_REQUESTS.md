# UI Dependency Requests

- Date: 2026-08-08
- Agent 2: `A2-UI`
- Current task: `UI-AUTH002-CONSUMER-CONFLICT-RECONCILIATION-001-A3`
- Prompt type: `DOCUMENTATION_ONLY / CONFLICT_RESOLUTION / MERGED_FRONTEND_STATE_RECONCILIATION`
- Worktree: `/Users/omkar/Documents/TestGap-Miner-wt-ui-auth002-conflict-reconciliation`
- Branch: `agent2/ui-auth002-conflict-reconciliation`
- Current evidence baseline: `006cc885161ff49be582a9fa08f353a70c31c7b1`
- Historical API-reconciliation baseline: `ab60d4573d398fb610bc2ebb813f76d0c95b33d7`
- Historical bootstrap baseline: `9ac5a242bfbfad839dd41cd51171b4f81db1be85`
- `ASSUMED`: `NONE`

Every `UI-DEP-*` request below was opened by A2-UI. A2-UI records owning-manager
evidence without substituting its own acceptance: `UI-DEP-DEPLOY-001` is
partially satisfied by A2-DEPLOYMENT's merged decision, and
`UI-DEP-BACKEND-001` is partially satisfied by the published API draft. The
Auth and Security requests remain pending.

This file also carries the **UI-owned mirror** of `AUTH-DEP-012`, the inbound
A2-AUTH request that A2-UI owns as a consumer. The authoritative Auth-side
record lives in `docs/components/auth/DEPENDENCY_REQUESTS.md`, which is
Auth-owned and was not modified by this task.

No request below authorizes A3-UI to modify another component's files, and none
authorizes UI code, tests, manifests, lockfiles, or configuration.

## `UI-DEP-AUTH-001` — Callback and session semantics

- Request ID: `UI-DEP-AUTH-001`
- Requesting manager: `A2-UI`
- Owning manager: `A2-AUTH`
- Affected contract: `CONTRACT-AUTH-001` and a future UI contract
- Affected task: `UI-004`; secondarily `UI-005` and `UI-008`
- Exact need: Publish the callback and session semantics the UI must implement
  against — what the `/auth/callback` exchange means and which side performs
  it; how a session is established, represented, refreshed, and terminated;
  which component generates, stores, and verifies the OAuth `state` value and
  the PKCE code verifier, and where each is held; the access-token lifetime and
  the refresh trigger the UI must react to; the exact sign-out semantics; the
  error taxonomy for a failed or replayed callback so the UI can render a
  correct, non-leaking error UX; and confirmation of the UI-side custody rules
  recorded as `UI-DEC-013` through `UI-DEC-015`. Secret values are excluded.
- Urgency: `HIGH`
- Compatibility impact: None yet — nothing is implemented. Once `UI-004`
  exists, a change to session or state-custody semantics is breaking for the
  frontend.
- Proposed acceptance evidence: A published, versioned Auth statement naming,
  for each of session establishment, refresh, sign-out, `state`, and PKCE, the
  component that owns it and the storage location; plus an explicit
  confirmation that the UI must never receive or forward a refresh token.
- Current status: `PENDING / DRAFT_RESPONSE_UNDER_CONSUMER_REVIEW`.
  `CONTRACT-AUTH-001@1.1.0-draft.1` on Auth PR #29, at reviewed head
  `7abe17af8e212bd2127160338ea6ef409da02101`, is A2-AUTH's draft response to
  this request. It is `OPEN / DRAFT / NOT_MERGED` and A2-UI's consumer review
  returned `SPECIFICATION_CONFLICT` — see the `AUTH-DEP-012` mirror below. The
  request stays `PENDING` because the responding contract is neither corrected
  nor accepted.

## `UI-DEP-DEPLOY-001` — Provider, callback registration, domain, TLS, and Auth environment variables

- Request ID: `UI-DEP-DEPLOY-001`
- Requesting manager: `A2-UI`
- Owning manager: `A2-DEPLOYMENT`
- Affected contract: `CONTRACT-DEPLOY-001` and `CONTRACT-AUTH-001`
- Affected task: `UI-004`, `UI-010`; blocks `AUTH-002` frontend work
- Exact need: The frontend-facing half of the metadata boundary already
  requested as `AUTH-DEP-004` — the approved identity provider or approved
  equivalent; the owned dashboard domain; the exact-match callback URL
  allowlist including the deployed form of `/auth/callback`; which side
  terminates the callback in each environment; TLS termination; the
  **names** of the client-side Auth environment variables the frontend may
  read and their registration in the deployment variable registry; the
  secret-injection owner; the Vercel project and environment topology; and a
  non-production provider test configuration sufficient to run frontend Auth
  integration tests. **No secret value is requested.**
- Urgency: `HIGH`
- Compatibility impact: Runtime configuration. A change to the callback URL,
  domain, or a public variable name breaks the deployed sign-in path.
- Proposed acceptance evidence: `AUTH-DEP-004` accepted; the deployed
  `/auth/callback` URL registered and exact-match allowlisted; the dashboard
  domain and TLS termination stated with an owner; every frontend-readable
  Auth variable name registered in
  `docs/components/deployment/ENVIRONMENT_VARIABLES.md` with no secret value;
  and a named non-production provider test configuration.
- Current status: `PARTIALLY_SATISFIED_FOR_CONTRACT_AND_DESIGN` —
  A2-DEPLOYMENT accepted `AUTH-DEP-004` with constraints through PR #20, and
  A2-AUTH reconciled it through PR #21.

Accepted for design:

- Provider: `SUPABASE_AUTH_WITH_GITHUB_OAUTH`
- Canonical issuer: `https://<SUPABASE_PROJECT_REF>.supabase.co/auth/v1`
- Audience: `authenticated`
- JWKS:
  `https://<SUPABASE_PROJECT_REF>.supabase.co/auth/v1/.well-known/jwks.json`
- Deployed Dashboard callback template: `${DASHBOARD_ORIGIN}/auth/callback`
- Local callback: `http://localhost:3000/auth/callback`
- OAuth termination: Supabase Auth
- Exact-match redirect allowlisting
- Exact, case-sensitive issuer comparison with no independent normalization
- FastAPI receives Supabase JWT access tokens only; refresh tokens are never
  forwarded to FastAPI.
- Registered variable names: `NEXT_PUBLIC_SUPABASE_URL`,
  `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_GITHUB_CLIENT_ID`,
  `SUPABASE_GITHUB_CLIENT_SECRET`, `AUTH_JWT_ISSUER`, `AUTH_JWT_AUDIENCE`,
  `AUTH_JWKS_URL`, and `DASHBOARD_ORIGIN`.

Still pending: actual provider provisioning; GitHub OAuth configuration; a
Vercel project and production Dashboard domain; verified TLS; production
callback registration; injected environment values and secrets; secret
injection evidence; and a non-production provider test configuration.

## `UI-DEP-BACKEND-001` — API route surface, error envelope, and CORS

- Request ID: `UI-DEP-BACKEND-001`
- Requesting manager: `A2-UI`
- Owning manager: `A2-BACKEND`
- Affected contract: `CONTRACT-API-001`
- Affected task: `UI-005`, `UI-006`, `UI-007`, `UI-008`, `UI-009`
- Exact need: Publish `CONTRACT-API-001` — the versioned REST route surface
  and OpenAPI document; request and response models; the pagination scheme;
  the stable error envelope with its `code`, safe `message`, `request_id`, and
  `details` semantics, including which statuses the UI must treat as
  re-authenticate versus forbidden versus retryable; the authenticated request
  context, confirming the `Authorization` bearer header as the accepted
  transport and confirming that no refresh token is ever accepted; the backend
  CORS policy naming the allowed frontend origin, allowed methods and headers,
  credentialed-request behavior, and preflight handling; and a fixture or mock
  surface the UI may build against before backend implementation completes.
- Urgency: `HIGH`
- Compatibility impact: Additive while the frontend is absent. After `UI-005`,
  route, model, or error-envelope changes are breaking for the UI.
- Proposed acceptance evidence: A published, versioned `CONTRACT-API-001` with
  a validating OpenAPI document; an error-envelope specification with a stable
  code list; a CORS policy naming the allowed origin and credential mode; and
  a documented statement that the error envelope leaks no secret and no
  internal detail.
- Current status: `PARTIALLY_SATISFIED_BY_CONTRACT_API_001_DRAFT`.

Satisfied documentary inputs from `CONTRACT-API-001@0.1.0-draft.1`:

- versioned draft contract publication and `/api/v1` convention;
- `Authorization: Bearer` access-token transport;
- refresh-token forwarding prohibition;
- safe `error.code/message/request_id/details` envelope;
- `X-Request-ID` and `X-Correlation-ID`;
- shared cursor-pagination conventions;
- polling through the response `Location` header.

Still pending:

- an accepted implementation-ready contract;
- a validating OpenAPI/client fixture;
- final authenticated-context shape from A2-AUTH;
- final `403` versus concealed `404` policy from Auth/Security;
- CORS, including Deployment/Security input and Backend configuration;
- complete endpoint-specific request/response models;
- complete Workflow, Evidence, Evaluation, Queue, and DB-003 projections;
- complete action semantics;
- API runtime implementation and API runtime tests.

API runtime remains `NOT_IMPLEMENTED / NOT_TESTED / NOT_AUTHORIZED`.

## `UI-DEP-SECURITY-001` — Cookie, CSRF, and OAuth-state acceptance

- Request ID: `UI-DEP-SECURITY-001`
- Requesting manager: `A2-UI`
- Owning manager: `A2-SECURITY`, jointly with `A2-AUTH`
- Affected contract: `CONTRACT-SEC-001` and `CONTRACT-AUTH-001`
- Affected task: `UI-004`, `UI-008`, `UI-010`
- Exact need: The security acceptance criteria the UI must satisfy — required
  cookie flags (`Secure`, `HttpOnly`, `SameSite`), cookie name, domain, path,
  and lifetime; the CSRF defence model for any state-changing request the UI
  originates, including the human accept, reject, regenerate, and dismiss
  decisions; the OAuth-state and PKCE verification requirements as a testable
  acceptance criterion; the XSS-safe rendering requirements for
  model-generated and repository-derived content shown in the evidence card;
  the redaction rules for anything the UI renders or logs; and the final
  acceptance procedure for the browser-session boundary `B1`.
- Urgency: `HIGH`
- Compatibility impact: May constrain the frontend session and rendering
  design. Earlier acceptance avoids rework.
- Proposed acceptance evidence: A published acceptance checklist for
  boundary `B1` with objectively testable criteria; a joint A2-SECURITY and
  A2-AUTH sign-off on the cookie, CSRF, and OAuth-state posture; and an
  explicit statement that no secret, raw token, private key, raw
  `Authorization` header, or unredacted prompt may be rendered or logged.
- Current status: `PENDING` — opened by A2-UI, awaiting A2-SECURITY with
  A2-AUTH.

## `AUTH-DEP-012` — A2-UI consumer review of the session contract (UI-owned mirror)

- Request ID: `AUTH-DEP-012`
- Requesting manager: `A2-AUTH`
- Owning manager: `A2-UI` — this record is A2-UI's own mirror of its consumer
  response. The authoritative Auth-side copy is Auth-owned and unmodified.
- Affected contract: `CONTRACT-AUTH-001@1.1.0-draft.1` and a future UI contract
- Affected task: `AUTH-002` acceptance; `UI-004`
- Reviewed Auth PR: #29 — `docs(auth): define dashboard sign-in and session
  contract`, branch `agent2/auth-002-session-contract`, reviewed head
  `7abe17af8e212bd2127160338ea6ef409da02101`, state `OPEN / DRAFT / NOT_MERGED`
- **Current disposition: `SPECIFICATION_CONFLICT`**
- Agent 1 decision on that disposition:
  `PASS / UI_AUTH_COOKIE_CONFLICT_CONFIRMED / UI_OWNED_CORRECTION_AUTHORIZED`

### Confirmed conflict

The merged `UI-DEC-013` prohibits "any non-`HttpOnly` cookie written by UI
code". The reviewed Auth contract candidate adopts the canonical
browser-readable `@supabase/ssr` cookie-backed session and states that
`HttpOnly` is not achievable for that session under the accepted architecture.

### UI-owned correction, applied by this task

`UI-DEC-026` supersedes **only** the conflicting non-`HttpOnly`-cookie clause of
`UI-DEC-013`. It preserves the `localStorage` prohibition, the `sessionStorage`
prohibition, `UI-DEC-014`'s no-duplicate-store rule, and `UI-DEC-015`'s Bearer
transport and refresh-token boundary. The only potentially permitted
browser-readable session store is the canonical Auth-owned cookie-backed
session, operated exclusively through the approved `@supabase/ssr` adapter, and
that exception is `CONDITIONAL` on A2-SECURITY accepting the final cookie
posture.

### Routes A2-UI accepts

| Item | A2-UI position |
|---|---|
| Default post-sign-in destination candidate | `/` |
| Safe callback-error recovery route, used when a callback attempt is rejected while a session established independently before that callback remains known-valid | `/` |

Both are proposals from the consumer side. A2-UI records, and requires, that:

- A2-AUTH must record both routes in its own contract package; A2-UI does not
  define them unilaterally and Auth remains the owner of the semantics;
- a rejected callback's intended-return destination must **never** be used as
  the recovery destination;
- a preserved, independently valid session must never be presented as
  "sign-in succeeded"; the callback reports no success and no callback-directed
  destination is used;
- the intended return path A2-UI supplies to `beginSignIn` is a **candidate
  only** — Auth creates, binds, expires and consumes the return state, and the
  UI must accept a silent fallback to the default destination whenever the
  return state is missing, expired, tampered, replayed or unbound;
- A2-SECURITY acceptance of the cookie, CSRF and OAuth-state posture remains
  **pending** under `AUTH-DEP-011`;
- **A2-UI rereview remains required** after the Auth-owned correction is pushed.

### Not yet granted

`AUTH-DEP-012` is **not** `ACCEPTED`. A2-UI's consumer review has **not**
passed. The UI-owned correction does not by itself make Auth PR #29 acceptable,
and this record is not A2-SECURITY acceptance of a browser-readable cookie.

## Future dependencies — not yet opened

These are recorded as **pending** future needs. They are not yet formal
requests: A2-UI will open them with concrete field-level requirements once
`UI-001` establishes what each Dashboard surface actually consumes. Opening
them prematurely would freeze another owner's contract against guessed needs.

| Prospective ID | Owning manager | Affected contract | Need | Affected task | Status |
|---|---|---|---|---|---|
| `UI-DEP-WORKFLOW-001` | `A2-AGENT-WORKFLOW` | `CONTRACT-WORKFLOW-001` | UI-facing projection of run state: which of the canonical states are user-visible, their display semantics and ordering, terminal versus non-terminal distinction, failure-code taxonomy, retry and abstention transitions, and the bounded single-repair-attempt representation | `UI-006` | `PENDING — NOT_YET_OPENED` |
| `UI-DEP-EVIDENCE-001` | `A2-AGENT-WORKFLOW` | `CONTRACT-EVIDENCE-001` | Evidence-card field set and rendering contract: candidate patch reference, execution attempts on buggy and fixed revisions, artefact manifest, artefact reference and short-lived download-URL issuance and expiry, and what the UI must show to make a claim reviewable rather than asserted | `UI-007` | `PENDING — NOT_YET_OPENED` |
| `UI-DEP-WORKFLOW-002` | `A2-AGENT-WORKFLOW`, with `A2-AUTH` | `CONTRACT-WORKFLOW-001`, `CONTRACT-AUTH-001` | Human decision contract: how accept, reject, regenerate, and dismiss are submitted, how the immutable audit event is rendered, how current decision state is derived, and confirmation that no prohibited action — auto-merge, approval bypass, branch-protection bypass, production-code edit — is exposed | `UI-008` | `PENDING — NOT_YET_OPENED` |
| `UI-DEP-EVAL-001` | `A2-EVALUATION` | `CONTRACT-EVAL-001` | Benchmark dashboard surface: benchmark case identity, metric result set and value ranges, baseline references, release-gate result representation, and the required provenance fields to display | `UI-009` | `PENDING — NOT_YET_OPENED` |
| `UI-DEP-API-002` | `A2-BACKEND` | `CONTRACT-API-001` | Shared cursor pagination and polling through `Location` are proposed. Workflow, Evidence, and Evaluation projections remain pending; endpoint-specific filters, fields, and actions remain owner-dependent. | `UI-006` – `UI-009` | `PARTIAL_DRAFT_INPUT_AVAILABLE / NOT_YET_OPENED` |

## Summary

Four formal UI requests remain open. `UI-DEP-AUTH-001` remains `PENDING`; its
draft response, `CONTRACT-AUTH-001@1.1.0-draft.1` on Auth PR #29, is under
consumer review and A2-UI returned `SPECIFICATION_CONFLICT` on it.
`UI-DEP-DEPLOY-001` is
`PARTIALLY_SATISFIED_FOR_CONTRACT_AND_DESIGN`; its runtime and test-provider
remainders stay pending. `UI-DEP-BACKEND-001` is
`PARTIALLY_SATISFIED_BY_CONTRACT_API_001_DRAFT`; acceptance, owner inputs,
fixtures, endpoint models, CORS, and runtime remain pending.
`UI-DEP-SECURITY-001` remains `PENDING`. Four future Workflow, Evidence, and
Evaluation dependencies remain pending and not yet opened;
`UI-DEP-API-002` has partial shared-transport draft input but is not yet
formally opened.

The inbound `AUTH-DEP-012` mirror is `SPECIFICATION_CONFLICT`. It is not
`ACCEPTED`, A2-UI's consumer review has not passed, and A2-UI rereview of the
corrected Auth PR #29 head remains required. A2-UI accepts `/` as both the
default post-sign-in destination candidate and the safe callback-error recovery
route, subject to A2-AUTH recording them in its own contract package and to
pending A2-SECURITY acceptance under `AUTH-DEP-011`.

`AUTH-DEP-004` is `ACCEPTED_WITH_CONSTRAINTS / MERGED_VIA_PR_20 /
SATISFIED_FOR_AUTH_CONTRACT_AND_DESIGN`. `AUTH-DEP-010` is
`ACCEPTED_WITH_CONSTRAINTS / ACKNOWLEDGED_BY_A2_AUTH /
UI_OWNERSHIP_ESTABLISHED_VIA_PR_19 / AUTH_RECONCILED_VIA_PR_21`. Neither is
pending, and neither authorizes implementation.
