# Auth Component Status

- Date: 2026-08-03
- Agent 2: `A2-AUTH`
- Paired Agent 3: `A3-AUTH`
- Current task: `AUTH-DEPENDENCY-RECONCILIATION-001-C1`
- Parent task: `AUTH-DEPENDENCY-RECONCILIATION-001-A3`
- Prompt type: `A2_AUTH_ACCEPTANCE_CORRECTION_COMMIT_AND_PUSH`
- Scope: `AUTH_DOCUMENTATION_CORRECTION_FINALIZATION_COMMIT_AND_PUSH`
- Base commit: `fc549fa1a4c77f4835acefbb4f937c35ad6e8f76`
- Worktree: `/Users/omkar/Documents/TestGap-Miner-wt-auth-dependency-reconciliation`
- Branch: `agent2/auth-dependency-reconciliation`
- Audit output: `docs/components/auth/AUTH-001_AUDIT.md`

## Current state

| Area | State | Evidence / next action |
|---|---|---|
| `AUTH-DEPENDENCY-RECONCILIATION-001-A3` | `PASS / VERIFIED_COMPLETE / A2_AUTH_ACCEPTED / PENDING_MERGE` | A2-AUTH completed content review and accepted the six-file reconciliation package. The decision becomes repository-durable after merge. Commit and push the accepted package; open a PR only after A2-AUTH verifies the pushed commit. Merge is `NOT_AUTHORIZED` by this task. |
| `AUTH-001` | `PASS / VERIFIED_COMPLETE / MERGED` | `AUTH-001-C1`: `PASS`. `AUTH-001-C2`: `PASS`. A2-AUTH accepted the complete audit package and it merged through pull request #17; no additional audit repair is required. |
| `AUTH-DEP-004` | `ACCEPTED_WITH_CONSTRAINTS / ACKNOWLEDGED / MERGED` | A2-DEPLOYMENT accepted with constraints; A2-AUTH acknowledged. Durably merged through pull request #20, merge commit `fc549fa1a4c77f4835acefbb4f937c35ad6e8f76`. Evidence: `docs/components/deployment/DECISION_LOG.md`, `docs/components/deployment/ENVIRONMENT_VARIABLES.md`. |
| `AUTH-DEP-010` | `ACCEPTED_WITH_CONSTRAINTS / ACKNOWLEDGED` | A2-UI accepted with constraints; A2-AUTH acknowledged. UI ownership established through pull request #19. Evidence: `docs/specifications/A2_UI_MANAGER.md` and the UI-owned durable records under `docs/components/ui/`. |
| Accepted human identity architecture | `APPROVED_FOR_AUTH_CONTRACT_AND_DESIGN` | Deployment-owned design: `SUPABASE_AUTH_WITH_GITHUB_OAUTH`; canonical issuer `https://<SUPABASE_PROJECT_REF>.supabase.co/auth/v1`; audience `authenticated`; JWKS `https://<SUPABASE_PROJECT_REF>.supabase.co/auth/v1/.well-known/jwks.json`. Accepted design values only; not proof of configured runtime. |
| `AUTH-002` contract/design | `READY_FOR_AUTH_002_CONTRACT_AND_DESIGN` | `AUTH-DEP-004`: `SATISFIED_FOR_CONTRACT_AND_DESIGN`. `AUTH-DEP-010`: `SATISFIED_FOR_OWNERSHIP_AND_COORDINATION`. Contract/design may begin only as a separate, newly authorized A2-AUTH task. |
| `AUTH-002` implementation | `NOT_AUTHORIZED` | Runtime implementation `NOT_AUTHORIZED`; frontend implementation `NOT_AUTHORIZED`; provider runtime `NOT_PROVISIONED / NOT_TESTED`. Accepted design status does not authorize implementation. |
| Provider provisioning | `NOT_STARTED / NOT_TESTED` | No Supabase project provisioning, GitHub OAuth provider configuration, Vercel project, production Dashboard hostname, TLS verification, production callback registration, or secret injection is proven by this repository. |
| `CONTRACT-AUTH-001@1.0.0-draft.2` | `ACKNOWLEDGED_AND_MERGED` | A2-DATABASE recorded acknowledgement in `docs/components/database/COMPONENT_STATUS.md` and `DECISION_LOG.md`; merged into `origin/main`. |
| `DB-002` | `PASS / VERIFIED_COMPLETE / MERGED` | Pull request #12, implementation commit `5506ab5`, merge commit `3701520`; closed by PR #13 (`1511f47`). Seven domain tables, five of them Auth-owned. |
| Contract task (`AUTH-DB002-CONTRACT-001`) | `PASS / COMPLETE` | Producer package accepted; consumer acknowledgement received and merged. No review action remains. |
| Auth identity persistence | `VERIFIED_COMPLETE` | `apps/api/app/db/models/auth.py`: `users`, `auth_subjects`, `github_installations`, `repositories`, `repository_access`. 21 Auth constraint tests executed 2026-08-02, all passing. |
| Auth implementation — human sign-in, session, OAuth callback | `NOT_STARTED` | No `apps/web`; no login, session, or callback code anywhere in the repository. |
| Auth implementation — JWT validation and user context | `NOT_STARTED` | `apps/api/app/main.py` is three lines; no JWT/JWKS dependency in `apps/api/pyproject.toml`. |
| Auth implementation — GitHub App machine auth, installation tokens, App manifest | `NOT_STARTED` | No first-party app-ID, private-key, or token-exchange code; no GitHub App manifest exists. |
| Auth implementation — webhook authenticity | `NOT_STARTED` | No webhook route, raw-body handling, or `X-Hub-Signature-256` verifier. Durable delivery-GUID persistence is separately absent as a downstream integration gap. |
| Auth implementation — repository-scoped authorization | `PARTIAL` | Exact-tuple grant model persisted and tested; no runtime reads a grant to allow or deny anything. |
| Auth implementation — human approval and publication boundaries | `PARTIAL` | Semantics defined in `CONTRACT-AUTH-001` and `CONTRACT-WORKFLOW-001`; no enforcement code and no machine publication-actor record. |
| Auth implementation — CORS, CSRF, cookies, callback allowlist | `NOT_STARTED` | No middleware in `apps/api/app/main.py`. FastAPI's default emits no CORS headers, which is the restrictive default. |
| Auth implementation — logs, audit events, redaction | `NOT_STARTED` | No logging configuration in `apps/api/app/**`. Only the `DATABASE_URL` redaction exists. Blocked on `AUTH-DEP-005`. |
| Auth deployment configuration | `NAMES_REGISTERED / NOT_PROVISIONED / NOT_TESTED` | `docs/components/deployment/ENVIRONMENT_VARIABLES.md` now registers Auth-scoped variable **names** through `AUTH-DEP-004` (PR #20). Registration of names is not provisioning: no injected value, deployed environment, or runtime read is proven. |
| Auth tests and CI validation | `NOT_STARTED` | `tests/auth/` does not exist. CI runs the full 174-test suite but has no Auth-specific gate. |
| Auth runtime | `NOT_STARTED / NOT_TESTED` | No test in this repository exercises an authentication or authorization decision. Database constraint tests prove schema semantics only. |
| Inbound FastAPI boundary (`B4`) | `UNSAFE_IF_DEPLOYED_IMPLEMENTED_BEHAVIOR` | A running container binds Uvicorn to `0.0.0.0`; local `TestClient` evidence proves the default OpenAPI surface is unauthenticated. Severity is `LOW` at the empty-route baseline and potentially `CRITICAL` if a protected route is added without `AUTH-003`. Actual public or production exposure is `NOT_TESTED`. |
| Secret handling | `PARTIAL` | `SecretStr` redaction proven by `tests/api/test_settings.py`; `.gitignore` excludes `.env*`, `*.pem`, `*.key`, `secrets/`; no Auth secret is defined or handled. |

## Test evidence recorded by AUTH-001

| Command | Result |
|---|---|
| `uv sync --project apps/api --all-groups --locked` | `PASS`; no manifest or lockfile change |
| `uv run --project apps/api pytest tests/api -q` | `PASS`; 5 passed |
| `uv run --project apps/api pytest tests/database/test_auth_constraints.py -q` | `PASS`; 21 passed against an isolated disposable PostgreSQL 16 |
| `uv run --project apps/api pytest -q` | `PASS`; 174 passed |
| `tests/auth` | `ABSENT`; AUTH-SPECIFIC TEST SUITE `NOT_STARTED` / `NOT_TESTED` |

## Readiness

`AUTH-002` contract/design is `READY_FOR_AUTH_002_CONTRACT_AND_DESIGN`. Both
direct prerequisites are satisfied: `AUTH-DEP-004` is
`SATISFIED_FOR_CONTRACT_AND_DESIGN` and `AUTH-DEP-010` is
`SATISFIED_FOR_OWNERSHIP_AND_COORDINATION`. `AUTH-DEP-006` is a future Backend
integration dependency, and `AUTH-DEP-009` is a GitHub App/webhook
configuration dependency; neither is a direct `AUTH-002` prerequisite. See
`AUTH-001_AUDIT.md` §13.

`AUTH-002` runtime implementation is `NOT_AUTHORIZED`, `AUTH-002` frontend
implementation is `NOT_AUTHORIZED`, and the `AUTH-002` provider runtime is
`NOT_PROVISIONED / NOT_TESTED`. Contract/design work may begin only as a
separate, newly authorized A2-AUTH task.

Acceptance of `AUTH-DEP-004` and `AUTH-DEP-010` authorizes no runtime task. The
following remain unresolved or untested and are not reversed by the accepted
design status: actual Supabase project provisioning; actual GitHub OAuth
provider configuration; actual Vercel project; production Dashboard hostname;
TLS verification; production callback registration; secret injection; callback
runtime behavior; JWT validation; cookie implementation; CSRF implementation;
PKCE implementation; OAuth-state implementation; frontend Auth integration; and
Auth-specific tests.

`AUTH-003` remains `NOT_AUTHORIZED`. It still requires sequential `AUTH-002`
design work and Backend JWT/runtime coordination through `AUTH-DEP-006`.

`AUTH-004` remains `BLOCKED` by sequential predecessor `AUTH-003` and pending
`AUTH-DEP-009`, not `AUTH-DEP-008`. The required GitHub installation Database
records already exist.

`AUTH-005` remains `BLOCKED` by sequential predecessor `AUTH-004`,
`AUTH-DEP-006`, and `AUTH-DEP-009`. Delivery-GUID persistence is a downstream
integration gap, not a direct `AUTH-005` verifier prerequisite; it must be
resolved before end-to-end webhook processing and `AUTH-008` final acceptance.

`CONTRACT-AUTH-001.md` metadata still describes DB-002 as a blocking, pending
consumer review. That file is forbidden to `AUTH-001` and was not modified;
the discrepancy is recorded as `AUTH-ISSUE-011` for A2-AUTH.

No Auth implementation, test, or configuration was created by this task.
Auth runtime remains `NOT_STARTED / NOT_TESTED`. `AUTH-002` contract/design is
ready; `AUTH-002` implementation remains `NOT_AUTHORIZED`.

Next action: commit and push the accepted six-file package. Open a pull request
only after A2-AUTH verifies the pushed commit. Merge remains `NOT_AUTHORIZED`
by this task.
