# Deployment Open Issues

- Date: 2026-08-02
- Agent 2: `A2-DEPLOYMENT`
- Current task: `AUTH-DEP-004-FINALIZATION-001-A3`
- Scope: `DOCUMENTATION_AND_CONFIGURATION_REGISTRY_ONLY`
- Worktree: `/Users/omkar/Documents/TestGap-Miner-wt-deployment-authdep004`
- Branch: `agent2/deployment-authdep004-finalization`
- Starting commit: `4c4b2e3aefb3529cb9acad2860f050247b47e6b2`
- `ASSUMED`: `NONE`

The provider architecture itself is not unresolved. Supabase Auth with GitHub
OAuth is `APPROVED_FOR_AUTH_CONTRACT_AND_DESIGN`. The issues below are
unresolved provisioning, runtime, verification, and coordination work; none is
evidence of a configured or vulnerable production deployment.

## `DEPLOY-ISSUE-001` — Supabase project provisioning

- Status: `OPEN / NOT_STARTED / NOT_TESTED`
- Owner: `A2-DEPLOYMENT`
- Required work: Create the actual Supabase project and verify the Auth
  capability under a separate authorized task.
- Blocks: Provider runtime and runtime callback testing.

## `DEPLOY-ISSUE-002` — GitHub OAuth application and provider configuration

- Status: `OPEN / NOT_STARTED / NOT_TESTED`
- Owner: `A2-DEPLOYMENT`
- Required work: Create or select the actual GitHub OAuth application, register
  the Supabase callback, and configure the provider through a controlled
  Deployment-admin process without exposing its secret.
- Blocks: Human sign-in runtime.

## `DEPLOY-ISSUE-003` — Production Dashboard hostname

- Status: `OPEN / NOT_PROVEN / NOT_TESTED`
- Owner: `A2-DEPLOYMENT`
- Required work: Assign and verify the production Dashboard hostname, then
  assign `DASHBOARD_ORIGIN` outside tracked repository files.
- Blocks: Production Dashboard callback registration.

## `DEPLOY-ISSUE-004` — Vercel topology

- Status: `OPEN / NOT_STARTED / NOT_TESTED`
- Owner: `A2-DEPLOYMENT`
- Required work: Define and provision the Vercel project and deployment
  topology under separate authorization.
- Blocks: Deployed Dashboard verification.

## `DEPLOY-ISSUE-005` — TLS verification

- Status: `OPEN / NOT_PROVEN / NOT_TESTED`
- Owner: `A2-DEPLOYMENT`
- Required work: Establish and verify TLS termination for the production
  Dashboard deployment.
- Blocks: Production Auth acceptance.

## `DEPLOY-ISSUE-006` — Production callback and redirect registration

- Status: `OPEN / NOT_STARTED / NOT_TESTED`
- Owner: `A2-DEPLOYMENT`
- Required work: Register the exact GitHub-to-Supabase callback, the exact
  deployed Dashboard callback, and the approved exact-match redirect allowlist.
  Wildcard, arbitrary, and user-controlled destinations remain prohibited.
- Blocks: Production callback tests.

## `DEPLOY-ISSUE-007` — Secret injection verification

- Status: `OPEN / DESIGN_OWNER_ASSIGNED / RUNTIME_NOT_TESTED`
- Owner: `A2-DEPLOYMENT`
- Required work: Store the GitHub OAuth client secret in AWS Secrets Manager
  and inject it into Supabase Auth provider configuration through a controlled
  Deployment-admin process. Verify that it is absent from frontend code,
  browser JavaScript, `NEXT_PUBLIC` variables, FastAPI request handling,
  unapproved worker runtime, tracked files, CI logs, and Auth-owned Database
  records.
- Blocks: Provider runtime acceptance.

## `DEPLOY-ISSUE-008` — Runtime callback tests

- Status: `OPEN / NOT_IMPLEMENTED / NOT_TESTED`
- Owners: `A2-DEPLOYMENT`, `A2-AUTH`, and `A2-UI`, with `A2-SECURITY` review
- Required work: Test sign-in initiation, OAuth state and callback behavior,
  exact redirect enforcement, browser session handling, error paths, and the
  prohibition on forwarding refresh tokens to FastAPI.
- Blocks: Auth runtime acceptance.

## `DEPLOY-ISSUE-009` — JWT validation tests and coordination

- Status: `OPEN / NOT_IMPLEMENTED / NOT_TESTED`
- Owners: `A2-AUTH` and `A2-BACKEND`, coordinated with `A2-DEPLOYMENT`,
  `A2-UI`, and `A2-SECURITY`
- Required work: Implement and test exact case-sensitive issuer validation,
  expected-audience validation, JWKS retrieval/rotation, invalid and expired
  token rejection, and authenticated user-context behavior after the required
  sequential Auth work is authorized.
- Blocks: `AUTH-003` and final Auth runtime acceptance.

## Coordination summary

Deployment/Auth/UI/Security/Backend coordination remains required for runtime
implementation and acceptance. This documentation decision does not authorize
that work and does not classify the approved provider architecture as open.
