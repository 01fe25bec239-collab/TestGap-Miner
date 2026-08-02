# Deployment Task Ledger

- Date: 2026-08-02
- Agent 2: `A2-DEPLOYMENT`
- Paired Agent 3: `A3-DEPLOYMENT`
- Current task: `AUTH-DEP-004-FINALIZATION-001-A3`
- Parent task: `AUTH-DEP-004-FINALIZATION-001`
- Scope: `DOCUMENTATION_AND_CONFIGURATION_REGISTRY_ONLY`
- Worktree: `/Users/omkar/Documents/TestGap-Miner-wt-deployment-authdep004`
- Branch: `agent2/deployment-authdep004-finalization`
- Starting commit: `4c4b2e3aefb3529cb9acad2860f050247b47e6b2`
- `ASSUMED`: `NONE`

## Current and future tasks

| Task | Status | Evidence / blocker |
|---|---|---|
| `AUTH-DEP-004-FINALIZATION-001-A3` — Deployment durable-record and environment-variable registry reconciliation | `PASS / VERIFIED_COMPLETE / A2_DEPLOYMENT_ACCEPTED / PENDING_MERGE` | Six Deployment manager records created and eight variable names added to the existing registry. No value, credential, runtime, or infrastructure change. |
| `AUTH-DEP-004` — Human sign-in and JWT/IdP deployment metadata | `ACCEPTED_WITH_CONSTRAINTS` | `SUPABASE_AUTH_WITH_GITHUB_OAUTH` is `APPROVED_FOR_AUTH_CONTRACT_AND_DESIGN`; exact metadata and ownership are in `DECISION_LOG.md`. |
| A2-AUTH reconciliation after merge | `PENDING / REQUIRED` | A2-AUTH must update its Auth-owned `AUTH-DEP-004` response and `AUTH-002` readiness records. This task must not modify `docs/components/auth/**`. |
| `AUTH-002` contract/design | `READY_AFTER_A2_AUTH_RECONCILIATION` | The Deployment design dependency is satisfied when the accepted record is merged and reconciled by A2-AUTH. |
| `AUTH-002` runtime implementation | `NOT_AUTHORIZED` | No Dashboard sign-in, session, callback, SDK, or provider runtime work is authorized. |
| `AUTH-003` — Backend JWT validation and user context | `NOT_AUTHORIZED / SEQUENTIALLY_BLOCKED` | Requires sequential `AUTH-002` work and A2-BACKEND coordination for JWT validation and runtime integration. |
| Supabase and GitHub OAuth provisioning | `FUTURE_TASK / NOT_STARTED / NOT_TESTED` | Separate authorization must create the Supabase project and configure the GitHub OAuth application/provider. |
| Dashboard domain, Vercel topology, callback registration, and TLS | `FUTURE_TASK / NOT_PROVEN / NOT_TESTED` | A2-DEPLOYMENT must assign the production hostname, establish deployment topology, register exact callbacks/redirects, and verify TLS. |
| Production secret registration and injection | `FUTURE_TASK / DESIGN_OWNER_ASSIGNED / RUNTIME_NOT_TESTED` | A2-DEPLOYMENT must register and inject the provider secret through AWS Secrets Manager and a controlled Deployment-admin process. |
| Runtime callback and JWT validation | `FUTURE_TASK / NOT_IMPLEMENTED / NOT_TESTED` | Requires coordinated Deployment, Auth, UI, Security, and Backend implementation and tests. |

## Scope boundary

This task changes documentation and the environment-variable name registry
only. It performs no provider provisioning, callback registration, domain or
TLS work, Vercel setup, secret creation or injection, frontend/backend coding,
Auth implementation, or runtime testing.
