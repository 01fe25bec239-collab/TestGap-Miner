# Auth Open Issues

- Date: 2026-08-03
- Current task: `AUTH-DEPENDENCY-RECONCILIATION-001-A3`
- Parent task: `AUTH-001`
- Prompt type: `POST_DEPENDENCY_MERGE_DURABLE_RECONCILIATION`
- Scope: `AUTH_DOCUMENTATION_RECONCILIATION_ONLY`
- Base commit: `fc549fa1a4c77f4835acefbb4f937c35ad6e8f76`
- Evidence: `docs/components/auth/AUTH-001_AUDIT.md`
- Auth identity persistence: `VERIFIED_COMPLETE` and merged
- Auth runtime: `NOT_STARTED` / `NOT_TESTED`

Severity vocabulary is `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`,
`INFORMATIONAL`. An absent feature is recorded as absence, not as a
vulnerability. `AUTH-ISSUE-016` records
`UNSAFE_IF_DEPLOYED_IMPLEMENTED_BEHAVIOR`: the repository proves runnable
container behavior, but actual public or production exposure is `NOT_TESTED`.

## Closed and reconciled issues

### `AUTH-ISSUE-001` — Auth contract and records were absent

- Classification: `CLOSED`
- Evidence: The Auth contract and its records exist; A2-AUTH accepted
  `1.0.0-draft.2`.
- Resolution: Closed by A2-AUTH acceptance.

### `AUTH-ISSUE-003` — Auth/Database contract-first sequencing

- Classification: `CLOSED`
- Evidence: A2-DATABASE recorded `CONTRACT-AUTH-001@1.0.0-draft.2` as
  `ACKNOWLEDGED_AND_MERGED` (`docs/components/database/COMPONENT_STATUS.md`,
  `DECISION_LOG.md`) and implemented DB-002 against it. `DB-002` is
  `PASS / VERIFIED_COMPLETE / MERGED` via PR #12 (`3701520`), closed by PR #13
  (`1511f47`). `CONTRACT-WORKFLOW-001@1.0.0-draft.1` is likewise merged.
- Resolution: Both preconditions are satisfied. DB-002 is no longer blocked.

### `AUTH-ISSUE-008` — Issuer comparison semantics were insufficiently explicit

- Classification: `CLOSED`
- Evidence: `CONTRACT-AUTH-001@1.0.0-draft.2` defines exact case-sensitive
  issuer storage and comparison; the merged schema implements it
  (`apps/api/app/db/models/auth.py:70-84`, `sa.Text`, default collation, no
  `citext` and no functional index). Verified by passing tests
  `test_case_distinct_issuer_and_subject_are_separate_identities` and
  `test_issuer_and_subject_are_stored_without_normalization`.
- Resolution: Closed by Database acknowledgement and merged implementation.

### `AUTH-ISSUE-009` — Access-grant expiration timing was insufficiently explicit

- Classification: `CLOSED`
- Evidence: The merged schema keeps `expires_at`, `expired_at`, and
  `revoked_at` distinct via the `expiry_distinct_from_revocation`,
  `revoked_at_present`, and `active_not_terminated` check constraints. Verified
  by four passing tests including
  `test_expired_access_may_not_borrow_revoked_at`.
- Resolution: Closed by Database acknowledgement and merged implementation.

## Issues carried forward

### `AUTH-ISSUE-002` — Shared registry omits the Database consumer

- Classification: `OPEN`
- Severity: `INFORMATIONAL`
- Evidence: The shared registry omits A2-DATABASE as a blocking
  `CONTRACT-AUTH-001` consumer, although DB-002 consumed and merged it.
- Impact: Coordination record only; no Auth work is blocked.
- Owning component: A2-INTEGRATION or Agent 1.
- Blocking task: none.
- Resolution path: `AUTH-DEP-003`.

### `AUTH-ISSUE-004` — Identity-provider design metadata is not frozen

- Classification: `RESOLVED_FOR_CONTRACT_AND_DESIGN`
- Severity: `MEDIUM` at the original baseline; no longer blocking `AUTH-002`
  contract and design
- Original evidence (historical): at the `AUTH-001` baseline,
  `docs/components/deployment/ENVIRONMENT_VARIABLES.md` registered eleven
  variables, all database-scoped, and no approved IdP, issuer, audience,
  JWKS/key source, dashboard domain, callback allowlist, TLS fact, client
  variable name, or secret-injection owner existed anywhere in the repository.
- Resolution evidence: `AUTH-DEP-004` is `ACCEPTED_WITH_CONSTRAINTS /
  ACKNOWLEDGED_BY_A2_AUTH / MERGED_VIA_PR_20` (merge commit `fc549fa`).
  A2-DEPLOYMENT recorded the approved provider
  (`SUPABASE_AUTH_WITH_GITHUB_OAUTH`), canonical issuer, audience, JWKS
  source, callback set, redirect policy, TLS and secret-injection ownership,
  and the Auth-scoped variable names.
- Resolution: The **design** metadata gap is closed. `AUTH-002` contract and
  design are no longer blocked by this issue.
- Residual — not resolved by this reconciliation: the accepted values are
  design values only. Actual Supabase project provisioning, GitHub OAuth
  provider configuration, Vercel project, production Dashboard hostname, TLS
  verification, production callback registration and secret injection remain
  `NOT_PROVISIONED / NOT_TESTED` and are owned by A2-DEPLOYMENT. The residual
  blocks Auth runtime, not Auth contract and design.

### `AUTH-ISSUE-005` — Workflow actor integration

- Classification: `PARTIALLY_RESOLVED`
- Severity: `MEDIUM`
- Evidence: `CONTRACT-WORKFLOW-001@1.0.0-draft.1` is accepted and merged, and
  `run_requests`/`runs` carry actor attribution. However
  `TERMINAL_ACTOR_TYPES = ("SYSTEM", "WORKFLOW", "WORKER", "HUMAN")`
  (`apps/api/app/db/models/workflow.py:129`) has no
  `GITHUB_APP_INSTALLATION` value.
- Impact: The contract's machine publication actor is not representable.
- Owning component: A2-AGENT-WORKFLOW, with A2-DATABASE for persistence.
- Blocking task: `AUTH-006` and `AUTH-008` final acceptance; not `AUTH-004`
  machine-token implementation.
- Resolution path: `AUTH-DEP-008`. Superseded in part by `AUTH-ISSUE-013`.

### `AUTH-ISSUE-006` — Authorization freshness and retention are not frozen

- Classification: `OPEN`
- Severity: `MEDIUM`
- Evidence: No Security guidance exists for revalidation freshness, retention,
  security-event shape, or redaction. `CONTRACT-AUTH-001` defers exact
  freshness.
- Impact: Blocks `AUTH-007` and `AUTH-008`.
- Owning component: A2-SECURITY.
- Blocking task: `AUTH-007`.
- Resolution path: `AUTH-DEP-005`.

### `AUTH-ISSUE-007` — Auth runtime is unimplemented

- Classification: `CONFIRMED_BY_AUDIT`
- Severity: `HIGH`
- Evidence: `AUTH-001` inventoried all 82 tracked files. The only first-party
  Auth artefacts are Database-owned persistence
  (`apps/api/app/db/models/auth.py`), Database-owned schema tests
  (`tests/database/test_auth_constraints.py`), and the Auth documentation
  records. `apps/api/app/main.py` is three lines. `apps/web` does not exist.
- Impact: No human sign-in, session, JWT validation, GitHub App
  authentication, webhook verification, authorization enforcement, or
  publication control exists.
- Owning component: A2-AUTH.
- Blocking task: `AUTH-002` onward.
- Resolution path: sequential `AUTH-002`…`AUTH-008` after their dependencies
  are accepted.

## Issues opened by AUTH-001

### `AUTH-ISSUE-010` — No Auth-specific test suite and no Auth CI gate

- Classification: `UNTESTED_BEHAVIOR`
- Severity: `MEDIUM`
- Evidence: `ls -d tests/auth` → `No such file or directory`. CI
  (`.github/workflows/deployment.yml:24`) runs the full 174-test suite but has
  no Auth-specific step. The 21 passing tests in
  `tests/database/test_auth_constraints.py` state in their own header that they
  test no authorization decision.
- Impact: Any future Auth control would ship without dedicated coverage.
- Owning component: A2-AUTH.
- Blocking task: every `AUTH-002`…`AUTH-008` acceptance.
- Resolution path: each Auth implementation task creates `tests/auth/**`
  alongside its control. **AUTH-SPECIFIC TEST SUITE: `NOT_STARTED` /
  `NOT_TESTED`.**

### `AUTH-ISSUE-011` — `CONTRACT-AUTH-001` metadata contradicts merged state

- Classification: `CONTRADICTORY_CONTRACT`
- Severity: `MEDIUM`
- Evidence: `docs/components/auth/CONTRACT-AUTH-001.md:9-12` records
  `Status: DRAFT_FOR_CONSUMER_REVIEW`, `Blocking consumer: A2-DATABASE`,
  `Blocking consumer task: DB-002`; lines 310-311 state DB-002 is still
  blocked. A2-DATABASE has acknowledged and merged the contract and DB-002 is
  `MERGED`.
- Impact: A reader of the contract alone would conclude DB-002 is still
  blocked and the contract still unaccepted.
- Owning component: A2-AUTH.
- Blocking task: none technically; a correctness defect in the authoritative
  record.
- Resolution path: A2-AUTH revises the contract metadata under a compatible
  revision. `CONTRACT-AUTH-001.md` is forbidden to `AUTH-001` and was not
  modified.

### `AUTH-ISSUE-012` — Run requests cannot reconstruct the exact authorization tuple

- Classification: `DEPENDENCY_GAP`
- Severity: `MEDIUM`
- Evidence: `apps/api/app/db/models/workflow.py:200-207` — `run_requests` has
  `repository_id` and `requested_by_subject` but no installation reference.
  `CONTRACT-AUTH-001` scopes repository authorization by the exact
  `user + installation + repository` tuple.
- Impact: `AUTH-006` cannot authorize a run request against the contract tuple
  from the request row alone.
- Owning component: A2-DATABASE, after an A2-AUTH ruling.
- Blocking task: `AUTH-006`.
- Resolution path: `AUTH-DEP-007`. This is an absent field, not a defect in
  merged DB-002 — DB-002 implemented exactly what the accepted contracts
  specified.

### `AUTH-ISSUE-013` — No machine actor for `PUBLICATION_EXECUTE`

- Classification: `DEPENDENCY_GAP`
- Severity: `MEDIUM`
- Evidence: `CONTRACT-AUTH-001` §Initial authorization action vocabulary
  requires `PUBLICATION_EXECUTE` to use the GitHub App installation actor with
  a traceable authorized trigger. No such actor value or record exists;
  `TERMINAL_ACTOR_TYPES` at `apps/api/app/db/models/workflow.py:129` omits it.
- Impact: Publication cannot be attributed to a machine actor as the contract
  requires. This blocks repository-scoped publication authorization in
  `AUTH-006` and `AUTH-008` final acceptance, not GitHub App JWT or
  installation-token implementation in `AUTH-004`.
- Owning component: A2-AGENT-WORKFLOW with A2-DATABASE.
- Blocking task: `AUTH-006`, `AUTH-008`.
- Resolution path: `AUTH-DEP-008`.

### `AUTH-ISSUE-014` — Human run-request attribution is subject-keyed, not user-keyed

- Classification: `CONTRACT_ALIGNMENT_NOTE`
- Severity: `LOW`
- Evidence: `run_requests.requested_by_subject → auth_subjects.id`
  (`apps/api/app/db/models/workflow.py:205-207`), while `CONTRACT-AUTH-001`
  §Actor types defines the `HUMAN_USER` actor as requiring `user_id`.
- Impact: None at rest — the canonical user is reachable by join through
  `auth_subjects.user_id`, and subject-keying preserves historical attribution
  when a subject is revoked. It does require an explicit ruling so `AUTH-006`
  resolves the actor consistently.
- Owning component: A2-AUTH.
- Blocking task: `AUTH-006`.
- Resolution path: A2-AUTH records the resolution rule in `AUTH-006`. No schema
  change is requested.

### `AUTH-ISSUE-015` — Auth environment variable registration

- Classification: `PARTIALLY_RESOLVED`
- Severity: `MEDIUM`
- Original evidence (historical): at the `AUTH-001` baseline, neither
  `.env.example`, `ENVIRONMENT_VARIABLES.md`, `compose.yml`, `Dockerfile`, nor
  `.github/workflows/deployment.yml` defined any Auth variable.
- Resolved part: `AUTH-DEP-004` (PR #20) registered the human IdP and callback
  variable **names** in `docs/components/deployment/ENVIRONMENT_VARIABLES.md`.
  Name registration is not provisioning: no value is injected and no deployed
  environment is proven.
- Remaining part: the GitHub App ID, GitHub App private-key and
  webhook-secret variable names remain absent, needed by `AUTH-004` and
  `AUTH-005`.
- Owning component: A2-DEPLOYMENT.
- Blocking task: `AUTH-004` and `AUTH-005` through `AUTH-DEP-009`. No longer
  blocks `AUTH-002` contract and design.
- Resolution path: `AUTH-DEP-009` registers the remaining GitHub App/webhook
  variable names and runtime metadata.

### `AUTH-ISSUE-016` — API is authenticate-by-exception rather than deny-by-default

- Classification: `UNSAFE_IF_DEPLOYED_IMPLEMENTED_BEHAVIOR`
- Severity: `LOW` at this baseline; `CRITICAL` once any protected route is
  added without `AUTH-003`
- Evidence: `apps/api/app/main.py:3` is a bare `FastAPI()` with no middleware
  and no dependency. `Dockerfile:17` ships
  `uvicorn app.main:app --host 0.0.0.0 --port 8000` as the container command.
  `tests/api/test_main.py:4-8` proves `/openapi.json` returns 200 with no
  credentials, and FastAPI additionally serves `/docs` and `/redoc` by default.
- Impact: In a running and network-reachable container, a caller can reach the
  default documentation/OpenAPI surface without credentials. The repository
  does not prove production deployment, public reachability, or an internet
  caller; those are `NOT_TESTED`. Severity is `LOW` at the empty-route baseline
  and potentially `CRITICAL` if a protected route is added without `AUTH-003`.
- Owning component: A2-AUTH with A2-BACKEND.
- Blocking task: `AUTH-003`; documentation-surface control belongs to
  `AUTH-007`.
- Resolution path: `AUTH-003` introduces a default-deny request dependency
  before any protected route exists; `AUTH-007` decides the docs-surface
  policy per environment.

### `AUTH-ISSUE-017` — Dashboard frontend ownership was unassigned

- Classification: `RESOLVED_FOR_OWNERSHIP_AND_COORDINATION`
- Severity: `MEDIUM` at the original baseline; ownership no longer unassigned
- Original evidence (historical): `find . -type d -name web` returned nothing;
  `ls apps/` returned exactly `api`; no frontend manifest or lockfile was
  tracked, and no component owned trust boundaries B1–B3.
- Resolution evidence: `AUTH-DEP-010` is `ACCEPTED_WITH_CONSTRAINTS /
  ACKNOWLEDGED_BY_A2_AUTH / UI_OWNERSHIP_ESTABLISHED_VIA_PR_19`. A2-UI owns the
  future Dashboard frontend, future `apps/web/**` after separate
  authorization, and the user-facing `/auth/callback` route and its UX;
  A2-AUTH retains callback, session, identity-resolution, token-custody, PKCE
  and OAuth-state semantics. Records: `docs/specifications/A2_UI_MANAGER.md`
  and `docs/components/ui/**`.
- Resolution: The ownership and coordination gap is closed. See
  `AUTH-DEP-010` in `DEPENDENCY_REQUESTS.md` for the full boundary.
- Residual — not resolved by this reconciliation: no frontend exists, and
  `AUTH-002` frontend implementation and frontend Auth integration tests
  remain `NOT_AUTHORIZED` and `NOT_TESTED`. A3-AUTH may not modify UI-owned
  paths without A2-UI coordination.

### `AUTH-ISSUE-018` — CI workflow contains literal placeholder passwords

- Classification: `DEFERRED_NON_GOAL`
- Severity: `INFORMATIONAL`
- Evidence: `.github/workflows/deployment.yml:15-18` sets values such as
  `ci-app-placeholder`; the container is destroyed in the same job at lines
  30-31.
- Impact: None. These are placeholders for an ephemeral CI PostgreSQL, not
  credentials to any real system.
- Owning component: A2-DEPLOYMENT.
- Blocking task: none.
- Resolution path: accepted as-is; revisit only if CI ever reaches a
  non-ephemeral database.

### `AUTH-ISSUE-019` — Durable webhook delivery idempotency is absent

- Classification: `DOWNSTREAM_INTEGRATION_GAP`
- Severity: `HIGH`
- Evidence: No durable delivery-GUID or webhook idempotency record exists in
  the DB-002 schema.
- Impact: `AUTH-005` can implement and test raw-body signature verification,
  delivery-GUID extraction, repository-identity extraction, safe failure
  logging, and rejection without downstream calls. Durable duplicate-delivery
  rejection remains required before end-to-end webhook processing and
  `AUTH-008` final acceptance, but it is not a direct `AUTH-005` verifier
  prerequisite.
- Owning component: Not selected by `AUTH-001`; future
  Backend/Workflow/Database integration must assign ownership.
- Blocking task: end-to-end webhook processing and `AUTH-008` final
  acceptance; not `AUTH-005` verifier implementation.
- Resolution path: the future integration owner defines durable idempotency.
  This continuation authorizes no new Database model or dependency contract.

## Summary

`DB-002` is merged, `CONTRACT-AUTH-001@1.0.0-draft.2` is acknowledged and
merged, and no Database rereview is outstanding.

This reconciliation reclassified exactly the issues whose sole cause was
missing `AUTH-DEP-004` design metadata or missing A2-UI ownership:
`AUTH-ISSUE-004` is `RESOLVED_FOR_CONTRACT_AND_DESIGN`, `AUTH-ISSUE-017` is
`RESOLVED_FOR_OWNERSHIP_AND_COORDINATION`, and `AUTH-ISSUE-015` is
`PARTIALLY_RESOLVED` for its human-IdP half only. No runtime provisioning,
implementation, Security, Backend, Workflow or testing issue was resolved.

What remains open is Auth runtime absence, provider provisioning and every
untested runtime behavior — callback runtime, JWT validation, cookies, CSRF,
PKCE, OAuth state and frontend Auth integration — plus the remaining scoped
external dependencies, one contradictory contract metadata block, the absent
Auth test suite, and downstream durable webhook idempotency. No implementation
defect is claimed in merged code: every gap above is either absence, an
unresolved dependency, or a documentation contradiction.
