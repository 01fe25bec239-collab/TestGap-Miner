# Deployment Component Status

- Date: 2026-08-02
- Agent 2: `A2-DEPLOYMENT`
- Paired Agent 3: `A3-DEPLOYMENT`
- Current task: `AUTH-DEP-004-FINALIZATION-001-A3`
- Parent task: `AUTH-DEP-004-FINALIZATION-001`
- Prompt type: `DOCUMENTATION_AND_CONFIGURATION_REGISTRY_RECONCILIATION`
- Scope: `DOCUMENTATION_AND_CONFIGURATION_REGISTRY_ONLY`
- Repository: `TestGap Miner`
- Primary repository path: `/Users/omkar/Documents/TestGap Miner_App`
- Worktree: `/Users/omkar/Documents/TestGap-Miner-wt-deployment-authdep004`
- Branch: `agent2/deployment-authdep004-finalization`
- Starting commit: `4c4b2e3aefb3529cb9acad2860f050247b47e6b2`
- `ASSUMED`: `NONE`

## Manager state

`A2-DEPLOYMENT` has reviewed and accepted the seven-file package. This branch
contains the accepted documentation package, and the `AUTH-DEP-004` decision
becomes repository-durable after merge. This is a documentation and
configuration-registry event, not provider provisioning or runtime
implementation evidence; provisioning remains `NOT_STARTED` and runtime
behavior remains `NOT_TESTED`.

## Current state

| Area | State | Evidence / next action |
|---|---|---|
| `AUTH-DEP-004-FINALIZATION-001-A3` | `PASS / VERIFIED_COMPLETE / A2_DEPLOYMENT_ACCEPTED / PENDING_MERGE` | A2-DEPLOYMENT accepted the seven-file package; the decision becomes repository-durable after merge. |
| `AUTH-DEP-004` | `ACCEPTED_WITH_CONSTRAINTS / A2_DEPLOYMENT_ACCEPTED` | Accepted decision recorded in `DECISION_LOG.md`; response recorded in `DEPENDENCY_REQUESTS.md`; this package is not yet merged. |
| Human identity provider | `SUPABASE_AUTH_WITH_GITHUB_OAUTH` | `APPROVED_FOR_AUTH_CONTRACT_AND_DESIGN`. |
| Provider provisioning | `NOT_STARTED / NOT_TESTED` | Create and configure the provider only under a separately authorized Deployment task. |
| Production callback registration | `NOT_STARTED / NOT_TESTED` | Exact callbacks and redirect policy are designed but not registered. |
| Production Dashboard domain | `NOT_PROVEN / NOT_TESTED` | A2-DEPLOYMENT must assign and verify it in future work. |
| TLS configuration | `NOT_PROVEN / NOT_TESTED` | A2-DEPLOYMENT owns TLS termination; no deployed TLS evidence exists. |
| Secret injection | `DESIGN_OWNER_ASSIGNED / RUNTIME_NOT_TESTED` | A2-DEPLOYMENT owns injection through AWS Secrets Manager and a controlled Deployment-admin process. |
| Environment-variable registry | `IMPLEMENTED / DOCUMENTATION_ONLY` | Eight names added to `ENVIRONMENT_VARIABLES.md`; no value was added. |
| `AUTH-002` contract/design | `READY_AFTER_A2_AUTH_RECONCILIATION` | Becomes ready only after this package merges and A2-AUTH reconciles its Auth-owned dependency and readiness records. |
| `AUTH-002` runtime implementation | `NOT_AUTHORIZED` | This task authorizes no frontend, callback, session, or provider runtime work. |
| `AUTH-003` | `NOT_AUTHORIZED` | Still requires sequential `AUTH-002` work and Backend JWT/runtime coordination. |
| Runtime completion | `NOT_IMPLEMENTED / NOT_TESTED` | No Supabase, GitHub OAuth, Vercel, domain, TLS, secret, callback, or JWT runtime was configured or tested. |

## Approved architecture boundary

The Dashboard begins sign-in through the Supabase Auth SDK boundary. Supabase
Auth terminates the GitHub OAuth callback and exchanges the authorization code.
FastAPI receives Supabase JWT access tokens only; it does not own the human
GitHub OAuth callback. Refresh tokens must never be forwarded to FastAPI, and
OAuth provider credentials or tokens must not be stored in Auth-owned Database
records.

## Deployment ownership

A2-DEPLOYMENT owns the Dashboard production-domain assignment, Vercel
deployment topology, TLS termination, callback and redirect-allowlist
registration, Deployment environment-variable registration, secret injection,
and production secret-store design. Ownership does not imply that any of these
runtime items is configured.

## Explicit labels

- `IMPLEMENTED`: Documentation and configuration-registry reconciliation only.
- `TESTED`: Repository, scope, and documentation validation only.
- `NOT_TESTED`: Supabase provisioning, GitHub OAuth configuration, Vercel,
  domains, TLS, secret injection, callback behavior, JWT validation, and Auth
  runtime.
- `BLOCKED`: Runtime implementation and provisioning remain unauthorized or
  incomplete.
- `ASSUMED`: `NONE`.

## Next action

Commit and push the accepted seven-file package. Open a pull request only after
A2-DEPLOYMENT verifies the pushed commit. Merge remains `NOT_AUTHORIZED` by
this task. After an eventual authorized merge, A2-AUTH reconciles its Auth-owned
records. No runtime or provisioning task begins through this decision record.
