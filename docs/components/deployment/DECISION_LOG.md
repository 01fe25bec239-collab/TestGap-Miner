# Deployment Decision Log

- Date: 2026-08-02
- Agent 2: `A2-DEPLOYMENT`
- Current task: `AUTH-DEP-004-FINALIZATION-001-A3`
- Starting commit: `4c4b2e3aefb3529cb9acad2860f050247b47e6b2`
- `ASSUMED`: `NONE`

## `DEPLOY-DEC-001` — `AUTH-DEP-004` acceptance

- Decision: `AUTH-DEP-004` is `ACCEPTED_WITH_CONSTRAINTS`.
- Human identity provider: `SUPABASE_AUTH_WITH_GITHUB_OAUTH`.
- Architecture status: `APPROVED_FOR_AUTH_CONTRACT_AND_DESIGN`.
- Runtime status: `NOT_PROVISIONED / NOT_IMPLEMENTED / NOT_TESTED`.

This decision satisfies the Deployment metadata needed for A2-AUTH to
reconcile and begin `AUTH-002` contract/design work. It does not authorize
`AUTH-002` runtime implementation. `AUTH-003` remains unauthorized and still
requires sequential `AUTH-002` work plus Backend JWT/runtime coordination.

## `DEPLOY-DEC-002` — OAuth termination boundary

1. The Dashboard begins sign-in through the Supabase Auth SDK boundary.
2. Supabase Auth terminates the GitHub OAuth callback.
3. Supabase Auth exchanges the OAuth authorization code.
4. FastAPI receives Supabase JWT access tokens only.
5. FastAPI does not own the human GitHub OAuth callback.
6. Refresh tokens must never be forwarded to FastAPI.
7. OAuth provider credentials and tokens must not be stored in Auth-owned
   Database records.

## `DEPLOY-DEC-003` — Canonical issuer, audience, and key source

- Canonical issuer:
  `https://<SUPABASE_PROJECT_REF>.supabase.co/auth/v1`
- Issuer comparison: exact and case-sensitive.
- Independent issuer normalization: prohibited.
- Expected audience: `authenticated`.
- JWKS source:
  `https://<SUPABASE_PROJECT_REF>.supabase.co/auth/v1/.well-known/jwks.json`

The placeholders above are design templates, not configured project values.

## `DEPLOY-DEC-004` — Authorization and token endpoints

- Supabase authorization entrypoint:
  `https://<SUPABASE_PROJECT_REF>.supabase.co/auth/v1/authorize?provider=github`
- Upstream GitHub authorization endpoint:
  `https://github.com/login/oauth/authorize`
- Upstream GitHub token endpoint:
  `https://github.com/login/oauth/access_token`

## `DEPLOY-DEC-005` — Callback and redirect policy

- GitHub OAuth callback registered with GitHub:
  `https://<SUPABASE_PROJECT_REF>.supabase.co/auth/v1/callback`
- Deployed Dashboard callback: `${DASHBOARD_ORIGIN}/auth/callback`.
- Local-development callback: `http://localhost:3000/auth/callback`.
- Redirect policy: exact-match allowlist only; no wildcard origins; no
  arbitrary origins; no user-controlled redirect destinations.

These callbacks are `APPROVED_FOR_AUTH_CONTRACT_AND_DESIGN` but
`NOT_REGISTERED / NOT_TESTED`.

## `DEPLOY-DEC-006` — Deployment and TLS ownership

A2-DEPLOYMENT owns Dashboard production-domain assignment, Vercel deployment
topology, TLS termination, callback registration, redirect-allowlist
registration, Deployment environment-variable registration, secret injection,
and production secret-store design.

- Provider provisioning: `NOT_STARTED / NOT_TESTED`.
- Production callback registration: `NOT_STARTED / NOT_TESTED`.
- Production Dashboard domain: `NOT_PROVEN / NOT_TESTED`.
- TLS configuration: `NOT_PROVEN / NOT_TESTED`.
- Secret injection: `DESIGN_OWNER_ASSIGNED / RUNTIME_NOT_TESTED`.

No Supabase project, GitHub OAuth application, Vercel project, production
domain, TLS configuration, callback, environment value, or secret is claimed
as configured.

## `DEPLOY-DEC-007` — Secret custody

- Secret owner: `A2-DEPLOYMENT`.
- Approved production secret store: `AWS Secrets Manager`.
- Injection design: The GitHub OAuth client secret is injected into Supabase
  Auth provider configuration through a controlled Deployment-admin process.

The secret must not be supplied to frontend code, browser JavaScript,
`NEXT_PUBLIC` variables, FastAPI request handling, worker runtime unless
separately required and approved, tracked repository files, CI logs, or
Auth-owned Database records.

## `DEPLOY-DEC-008` — Environment-variable names

The canonical registry contains these added names without values:

- Public frontend configuration, not secrets:
  `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`.
- Non-public Deployment-owned provider settings:
  `SUPABASE_GITHUB_CLIENT_ID`, `SUPABASE_GITHUB_CLIENT_SECRET`.
- Backend/Auth JWT validation configuration:
  `AUTH_JWT_ISSUER`, `AUTH_JWT_AUDIENCE`, `AUTH_JWKS_URL`.
- Shared deployed Dashboard origin:
  `DASHBOARD_ORIGIN`.

`SUPABASE_GITHUB_CLIENT_ID` must not use a `NEXT_PUBLIC` namespace.
`SUPABASE_GITHUB_CLIENT_SECRET` must never be frontend-readable, committed,
logged, or stored in Auth-owned Database records. `AUTH_JWT_ISSUER` retains
exact issuer semantics with no independent normalization. A2-DEPLOYMENT owns
and assigns `DASHBOARD_ORIGIN`.

## `DEPLOY-DEC-009` — Contract-version impact

This is an additive Deployment configuration decision. It does not modify or
replace `CONTRACT-DEPLOY-001.md`, which remains the existing Database
runtime-boundary contract, and it creates no contract-version change by itself.
A2-AUTH must reconcile the accepted values into Auth-owned contract/design
records after merge.

Any future identity-provider or canonical-issuer change requires A2-AUTH
review before adoption. If it changes Auth identity or token-validation
semantics, it requires a versioned Auth contract change and affected-consumer
coordination rather than independent Deployment normalization or substitution.
