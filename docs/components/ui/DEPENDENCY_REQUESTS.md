# UI Dependency Requests

- Date: 2026-08-02
- Agent 2: `A2-UI`
- Current task: `UI-DOC-BOOTSTRAP-001`
- Prompt type: `DOCUMENTATION_ONLY_BOOTSTRAP`
- Worktree: `/Users/omkar/Documents/TestGap-Miner-wt-ui-bootstrap`
- Branch: `agent2/ui-bootstrap-authdep010`
- Evidence baseline: `9ac5a242bfbfad839dd41cd51171b4f81db1be85`
- `ASSUMED`: `NONE`

Every request below is **opened by A2-UI** and awaits its owner's decision.
A2-UI does not set the status of a request owned by another manager, and no
status below is recorded as accepted, satisfied, or complete on A2-UI's behalf.
Only the owning manager may accept, in that owner's own records.

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
- Current status: `PENDING` — opened by A2-UI, awaiting A2-AUTH.

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
- Current status: `PENDING` — opened by A2-UI. The upstream `AUTH-DEP-004` is
  independently `PENDING` with `Completion evidence: None`
  (`docs/components/auth/DEPENDENCY_REQUESTS.md:128-150`). A2-UI does not and
  cannot change that status.

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
- Current status: `PENDING` — opened by A2-UI, awaiting A2-BACKEND.
  `apps/api/app/main.py` is three lines with no routes.

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
| `UI-DEP-API-002` | `A2-BACKEND` | `CONTRACT-API-001` | Transport for the Workflow, Evidence, and Evaluation surfaces above: list and detail endpoints, filtering, pagination at dashboard scale, and any streaming or polling contract for in-progress runs | `UI-006` – `UI-009` | `PENDING — NOT_YET_OPENED` |

## Summary

Four dependency requests are open: `UI-DEP-AUTH-001`, `UI-DEP-DEPLOY-001`,
`UI-DEP-BACKEND-001`, and `UI-DEP-SECURITY-001`. All four are `PENDING` with
their owning manager. Five further Workflow, Evidence, Evaluation, and API
dependencies are recorded as pending and not yet opened.

`AUTH-DEP-010` is the one dependency A2-UI **owns**, and A2-UI records it as
`ACCEPTED_WITH_CONSTRAINTS` — see `DECISION_LOG.md` `UI-DEC-016` and
`TASK_LEDGER.md` `AUTH-DEP-010-RESPONSE-001-R1`. The Auth-side copy of that
record still reads `PENDING` and is forbidden to this task; reconciliation is
tracked as `UI-ISSUE-012`.

`AUTH-DEP-004` is owned by A2-DEPLOYMENT and remains `PENDING`. A2-UI has not
marked it, or any other manager's request, accepted.
