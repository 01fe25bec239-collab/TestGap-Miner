# Deployment Dependency Requests

- Date: 2026-08-02
- Agent 2: `A2-DEPLOYMENT`
- Current task: `AUTH-DEP-004-FINALIZATION-001-A3`
- Scope: `DOCUMENTATION_AND_CONFIGURATION_REGISTRY_ONLY`
- Starting commit: `4c4b2e3aefb3529cb9acad2860f050247b47e6b2`
- `ASSUMED`: `NONE`

## `AUTH-DEP-004` — Response to A2-AUTH

- Request ID: `AUTH-DEP-004`.
- Requesting Agent 2: `A2-AUTH`.
- Owning Agent 2: `A2-DEPLOYMENT`.
- Result: `ACCEPTED_WITH_CONSTRAINTS`.
- Human identity provider: `SUPABASE_AUTH_WITH_GITHUB_OAUTH`.
- Architecture status: `APPROVED_FOR_AUTH_CONTRACT_AND_DESIGN`.
- Contract affected: `CONTRACT-AUTH-001`; additive Deployment configuration
  record. `CONTRACT-DEPLOY-001.md` remains unchanged.
- Exact blocking tasks named by the request: `AUTH-002`, `AUTH-003`, and
  `AUTH-007`.
- Completion evidence: `DECISION_LOG.md`, `COMPONENT_STATUS.md`, and the eight
  names added to `ENVIRONMENT_VARIABLES.md` by
  `AUTH-DEP-004-FINALIZATION-001-A3`.

## Satisfied for design

The response defines the approved provider architecture; canonical exact,
case-sensitive issuer; expected audience; JWKS source; authorization and token
endpoints; GitHub-to-Supabase callback; deployed and local Dashboard callbacks;
exact-match redirect policy; OAuth termination boundary; Dashboard domain,
Vercel, TLS, callback, environment, and secret ownership; variable names; and
AWS Secrets Manager production secret-store design. No secret value is present.

`AUTH-002` contract/design becomes
`READY_AFTER_A2_AUTH_RECONCILIATION`. A2-AUTH must update its Auth-owned
dependency and readiness records after this Deployment package merges. This
task does not modify `docs/components/auth/**`.

## Constraints and remaining work

- Provider provisioning: `NOT_STARTED / NOT_TESTED`.
- Production callback registration: `NOT_STARTED / NOT_TESTED`.
- Production Dashboard domain and TLS: `NOT_PROVEN / NOT_TESTED`.
- Secret injection: `DESIGN_OWNER_ASSIGNED / RUNTIME_NOT_TESTED`.
- Supabase project creation, GitHub OAuth application/provider configuration,
  Vercel topology, callback registration, secret registration, runtime callback
  behavior, and JWT validation remain future coordinated work.
- `AUTH-002` runtime implementation: `NOT_AUTHORIZED`.
- `AUTH-003`: `NOT_AUTHORIZED`; it still requires sequential `AUTH-002` work
  and Backend JWT/runtime coordination.

This acceptance is not provider provisioning, runtime validation, or
authorization to write frontend, Backend, Auth, infrastructure, secret, or
environment-value changes.
