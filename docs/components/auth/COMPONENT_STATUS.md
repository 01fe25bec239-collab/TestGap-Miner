# Auth Component Status

- Date: 2026-08-08
- Agent 2: `A2-AUTH`
- Paired Agent 3: `A3-AUTH`
- Current task:
  `AUTH-002-CONSUMER-CORRECTION-UI-SECURITY-001-A3-PR30`
- Continuation of:
  `AUTH-002-CONSUMER-CORRECTION-UI-SECURITY-001-A3`
- Authorized manager task:
  `AUTH-002-CONSUMER-CORRECTION-UI-SECURITY-001`
- Supersedes the narrower task:
  `AUTH-002-A2-UI-CONSUMER-CONFLICT-CORRECTION-001`, whose uncommitted
  Auth-side corrections are preserved and reconciled into this package
- Consumer reviews reconciled:
  `AUTH-002-CONSUMER-REVIEW-A2-UI-001` — `A2-UI` — `SPECIFICATION_CONFLICT`;
  `AUTH-002-CONSUMER-REVIEW-A2-SECURITY-001` — `A2-SECURITY` —
  `REJECTED_WITH_REASON`, seven required normative corrections
- Reviewed head for both: `7abe17af8e212bd2127160338ea6ef409da02101`
- Pull request: #29 — `OPEN / DRAFT / NOT_MERGED`
- Prior correction tasks:
  `AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001-A3-C2`,
  `AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001-A3-C1`
- Originating task: `AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001-A3`
- Parent task: `AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001`
- A2-AUTH review of the originating draft:
  `CHANGES_REQUIRED_BEFORE_A2_AUTH_ACCEPTANCE`
- A2-AUTH review of the `A3-C1` corrected draft:
  `CHANGES_REQUIRED_BEFORE_A2_AUTH_ACCEPTANCE`
- Prompt type: `A2_AUTH_CORRECTION / A3_DOCUMENTATION_EXECUTION_AND_VALIDATION`
- Scope: `AUTH_CONTRACT_AND_DESIGN_DOCUMENTATION_ONLY`
- Base commit: `006cc885161ff49be582a9fa08f353a70c31c7b1`
- Current `origin/main`: `63093f22c37a0fc6affe168f7d5230107b05cdf3`
- Main divergence: `UI_DOCUMENTATION_ONLY / NO_AUTH_PATH_OVERLAP /
  NO_REBASE_OR_BRANCH_MERGE_REQUIRED`
- Merged external evidence: PR #30 — `docs(ui): reconcile Auth session custody
  and merged frontend state`; implementation commit
  `30deb92000a20d3837b2423b6bdee3ea3335a7f1`; merge commit
  `63093f22c37a0fc6affe168f7d5230107b05cdf3`; `UI-DEC-026`, `UI-DEC-027`
- Worktree: `/Users/omkar/Documents/TestGap-Miner-wt-auth-002-session-contract`
- Branch: `agent2/auth-002-session-contract`
- Branch HEAD: `7abe17af8e212bd2127160338ea6ef409da02101`
- Audit output: `docs/components/auth/AUTH-001_AUDIT.md`
- Contract: `CONTRACT-AUTH-001@1.1.0-draft.1` — `DRAFT_FOR_CONSUMER_REVIEW /
  NOT_IMPLEMENTATION_READY / NOT_IMPLEMENTED / NOT_TESTED`
- `ASSUMED`: `NONE`

## Current state

| Area | State | Evidence / next action |
|---|---|---|
| `AUTH-002-CONSUMER-CORRECTION-UI-SECURITY-001-A3-PR30` | `RECONCILED / UNSTAGED / UNCOMMITTED / PENDING_A2_AUTH_REVIEW` | Merged-state reconciliation of the existing uncommitted Auth package against the new `origin/main` `63093f22c37a0fc6affe168f7d5230107b05cdf3`. Records that the UI-owned half of the `A2-UI` conflict is `CORRECTED_AND_MERGED` via PR #30 (implementation commit `30deb920`, merge commit `63093f22`, `UI-DEC-026`/`UI-DEC-027`), and removes stale current-state wording that described that correction as outstanding or unmerged. Adds `AUTH-DEC-052`. No history reconciliation was performed and none is required: PR #30 changed six UI durable-record files and no `docs/components/auth/**` path, so branch head `7abe17af` is unaffected. `AUTH-DEC-042`–`AUTH-DEC-051` are unchanged, and the historical `SPECIFICATION_CONFLICT` at `7abe17af` is not rewritten. No consumer acceptance is created: `AUTH-DEP-011`, `AUTH-DEP-012`, `AUTH-ISSUE-027` and `AUTH-ISSUE-028` all stay open, `A2-UI` and `A2-SECURITY` corrected-head rereviews stay required, and `A2-BACKEND`/`A2-DEPLOYMENT` confirmations stay outstanding. Contract version and classification unchanged. Same seven Auth files; no eighth path; no UI file modified — PR #30 is external merged evidence only. Documentation only. A2-AUTH acceptance is not claimed. |
| `AUTH-002-CONSUMER-CORRECTION-UI-SECURITY-001-A3` | `CORRECTED / UNSTAGED / UNCOMMITTED / PENDING_A2_AUTH_REVIEW` | Consolidated reconciliation of both consumer responses against the existing PR #29 draft, which stays `OPEN / DRAFT / NOT_MERGED`. Supersedes the narrower `AUTH-002-A2-UI-CONSUMER-CONFLICT-CORRECTION-001`; that task's uncommitted Auth-side corrections were preserved and reconciled rather than recreated, and `AUTH-DEC-042`/`AUTH-DEC-043` stand unchanged. Adds the `A2-SECURITY` response (`AUTH-DEC-044`) and its seven required normative corrections (`AUTH-DEC-045`–`AUTH-DEC-051`): frozen provider-session cookie posture; CSRF and credential-transport boundary; `local` sign-out scope with the `<= 900`-second production access-token bound; public `SIGN_IN_FAILED` failure-oracle boundary; server-side ephemeral callback correlation with 10-minute pending and exactly 120-second completed lifetimes; server-side intended-return state; and live-provider proof for a preserved session. Cache-control, XSS/runtime, Security-event and key-custody requirements are recorded as implementation and release requirements, not runtime evidence. Opened `AUTH-ISSUE-028` and `AUTH-ISSUE-029`; narrowed `AUTH-ISSUE-025`. Contract version and classification unchanged. Same seven files; no UI or Security file touched; no Security file created. Documentation only. A2-AUTH acceptance is not claimed. |
| `A2-SECURITY` consumer response | `REJECTED_WITH_REASON_AT_7ABE17AF / SEVEN_CORRECTIONS_APPLIED / REREVIEW_REQUIRED / NOT_ACCEPTED` | `AUTH-002-CONSUMER-REVIEW-A2-SECURITY-001` against head `7abe17a`, seven required normative corrections. Received and rejected, never converted to acceptance. Architecture explicitly accepted: `SUPABASE_AUTH_WITH_GITHUB_OAUTH`, `@supabase/ssr`, `createBrowserClient`, `createServerClient`, one provider-owned cookie-backed session, browser-readable provider-session cookie, required PKCE. All seven corrections applied. `AUTH-DEP-011` remains `OPEN / NOT_ACCEPTED`. See `AUTH-ISSUE-028`. |
| Provider-session cookie posture | `FROZEN / PENDING_A2_DEPLOYMENT_CONFIRMATION` | Browser-readable `@supabase/ssr` session; `SameSite=Lax`; `Secure=true` in every non-local environment with `http://localhost:3000` the only exception — not preview, LAN, tunnels, alternate HTTP hosts, staging HTTP or production HTTP; host-only; no `Domain`; `Path=/`; not `HttpOnly`; provider-managed lifetime and rotation; no custom token copy. `A2-SECURITY` holds policy acceptance, `A2-AUTH` the semantics, `A2-DEPLOYMENT` the runtime and configuration confirmation, which has **not** been given. See `AUTH-DEC-045`. |
| CSRF and credential transport | `FROZEN / PENDING_A2_BACKEND_CONFIRMATION` | Bearer-only for protected FastAPI routes; provider cookie never an API credential; no anti-CSRF token required merely because a request is Bearer-authenticated; exact-origin CORS with no wildcard, `A2-BACKEND`-implemented. Session-mutating same-origin Auth operations are non-`GET` and validate exact `Origin`, Fetch Metadata where available, and an Auth-owned anti-CSRF value bound to the session or the anonymous attempt; sign-out is CSRF-validated; `GET`/`HEAD`/`OPTIONS` stay side-effect-free. The OAuth callback is exempt from the same-origin token and instead gates on OAuth `state`, PKCE, correlation, exact destination and return binding. See `AUTH-DEC-046`. |
| Sign-out scope and access-token lifetime | `FROZEN / PENDING_A2_BACKEND_AND_A2_DEPLOYMENT_CONFIRMATION` | Sign-out scope `local` — current session only; the broader provider default is never inherited. Production access-token lifetime `<= 900 seconds`, classified `PRODUCTION_SECURITY_REQUIREMENT / PENDING_BACKEND_AND_DEPLOYMENT_CONSUMER_CONFIRMATION`. Local UI state clears immediately; an issued token may remain accepted by FastAPI until `exp`; no denial list required; no immediate-revocation claim. **Not** configured, and not claimed to be. See `AUTH-DEC-047`. |
| Public failure-oracle boundary | `FROZEN` | `INVALID_CALLBACK`, `STATE_VALIDATION_FAILED`, `PKCE_VALIDATION_FAILED` and `SESSION_EXCHANGE_FAILED` are indistinguishable through every untrusted browser-observable channel. The browser receives the single public classification `SIGN_IN_FAILED`, one safe response shape, equivalent status behavior, no validation-stage identifier and no inference-enabling field; timing should be normalized and must never intentionally reveal the stage. The four internal classifications survive unchanged for server-side Security events and restricted diagnostics. `A2-UI` is no longer required to distinguish them. See `AUTH-DEC-048`. |
| Callback-correlation mechanism | `FROZEN / STORAGE_SUBSTRATE_PENDING_A2_DEPLOYMENT` | `AUTH_CONTROLLED / PROVIDER_NEUTRAL / SERVER_SIDE / EPHEMERAL`, supporting atomic transitions, atomic single use, expiry, concurrent attempts and shared availability across runtime instances. Browser carries only a cryptographically random opaque handle in a separate Auth-owned cookie that is `HttpOnly`, `Secure`, `SameSite=Lax`, host-only and callback-path restricted in non-local environments, containing no code, token, verifier, return path, payload or session. `PENDING_ATTEMPT_CORRELATION` at most 10 minutes from initiation; `COMPLETED_CALLBACK_CORRELATION` exactly 120 seconds from successful completion; atomic transition; fail-closed on unavailable store or unverifiable handle; concurrent tabs get separate non-overwriting records. No vendor or technology selected. See `AUTH-DEC-049` and `AUTH-ISSUE-025`. |
| Intended-return state | `FROZEN / SERVER_SIDE_ONLY` | Held only inside the server-side `PENDING_ATTEMPT_CORRELATION` record: validated before storage, bound to one attempt, expiring within 10 minutes of initiation, atomically single-use, removed on success, failure, abandonment and expiry. Never in provider OAuth `state`, the provider cookie, the handle cookie, a URL, `localStorage`, `sessionStorage`, IndexedDB or any other browser persistence. Missing record, integrity failure, replay or store failure each falls back to `/` without relaxing callback validation. See `AUTH-DEC-050`. |
| Preserved-session proof | `FROZEN` | `INDEPENDENTLY_ESTABLISHED_AND_KNOWN_VALID_SESSION` requires all four: identity pre-existed the rejected callback; no successful exchange created or replaced it; authoritative server-side `LIVE_PROVIDER_SESSION_VALIDATION` succeeds after rejection; and the validated identity equals the pre-callback identity. Cookie presence, `getSession()`, a decoded JWT, local signature/expiry checks, `getClaims()`, frontend state, a subscription event and an existing access token are each insufficient alone. Unavailable, timed-out, failed, mismatched or unprovable validation is `UNPROVEN` and fails closed. A preserving rejection emits an internal Security event with `session_preserved=true`, `callback_success=false`, `rejected_callback_destination_used=false`. See `AUTH-DEC-051`. |
| Security implementation and release requirements | `RECORDED / NOT_IMPLEMENTED / NOT_TESTED` | `Cache-Control: private, no-store` on auth, refresh, cookie-setting and callback responses with no shared-cache, ISR or CDN `Set-Cookie` serving; strict CSP, no `unsafe-eval`, no unrestricted `unsafe-inline`, nonce/hash script policy, Trusted Types where supported, no unreviewed third-party scripts on authenticated surfaces, supply-chain scanning, no token in DOM, analytics or client logs, callback and session route security testing; bounded secret-free attributable Security-event fields with their prohibited-content list; key custody with `>= 256`-bit server key where HMAC is selected, secret-manager custody, no `NEXT_PUBLIC`/source-control/log/browser exposure, rotation accepting the previous verification key for at most 15 minutes and never minting with it. None implemented, none claimed. No key generated, no secret manager selected, no runtime configured, no infrastructure provisioned. See `AUTH-ISSUE-029`. |
| `A2-DEPLOYMENT` consumer response | `CONSUMER_RESPONSE_OR_AFFECTED_BOUNDARY_CONFIRMATION_STILL_REQUIRED` | No `A2-DEPLOYMENT` response to `CONTRACT-AUTH-001@1.1.0-draft.1` is reconciled. Outstanding compatibility: `Secure` provider cookies, host-only configuration, `Path=/`, the exact `localhost` `Secure` exception, production JWT lifetime, callback infrastructure, server-side ephemeral correlation-store capability, secret injection, key rotation, cache safety and deployment topology. `SECURITY_REQUIRED / PENDING_AFFECTED_OWNER_COMPATIBILITY_REVIEW`. |
| `A2-BACKEND` consumer response | `CONSUMER_RESPONSE_OR_AFFECTED_BOUNDARY_CONFIRMATION_STILL_REQUIRED` | No `A2-BACKEND` response is reconciled. Outstanding compatibility: Bearer-only credential transport, the provider cookie not being a FastAPI credential, exact-origin CORS, the `<= 900`-second production access-token lifetime, post-sign-out residual JWT validity, one refresh plus one request retry, and Backend denial behavior. `SECURITY_REQUIRED / PENDING_AFFECTED_OWNER_COMPATIBILITY_REVIEW`. |
| `A2-INTEGRATION` consumer response | `ACCEPTED_WITH_CONSTRAINTS_AT_7ABE17AF / FINAL_REVIEW_PENDING` | Recorded against head `7abe17a`. Final `A2-INTEGRATION` review occurs only after every affected owner response and correction is complete, which includes the corrected PR #29 head. |
| `AUTH-002-A2-UI-CONSUMER-CONFLICT-CORRECTION-001-A3` | `CORRECTED / UNSTAGED / UNCOMMITTED / PENDING_A2_AUTH_REVIEW` | Reconciles the `A2-UI` consumer response (`AUTH-002-CONSUMER-REVIEW-A2-UI-001`, reviewed head `7abe17a`, disposition `SPECIFICATION_CONFLICT`) against the existing PR #29 draft, which stays `OPEN / DRAFT / NOT_MERGED`. Only the Auth-owned half of the conflict is executed here: `/` frozen as the default post-sign-in destination and as the preserved-session rejected-callback safe recovery destination, with the rejected intended-return destination `NEVER_USED`. Recorded as `AUTH-DEC-042` and `AUTH-DEC-043`; opened `AUTH-ISSUE-027`. The UI-owned `UI-DEC-013` cookie-custody supersession is `A2-UI`'s and was neither performed nor marked complete; no UI, Security or other-owner file was touched. Contract version and classification unchanged. Documentation only. A2-AUTH acceptance is not claimed. |
| `A2-UI` consumer response | `SPECIFICATION_CONFLICT_AT_7ABE17AF / UI_SIDE_CORRECTION_MERGED / AUTH_CORRECTION_IN_PROGRESS / REREVIEW_REQUIRED` | `AUTH-002-CONSUMER-REVIEW-A2-UI-001` against head `7abe17a`. Received, not accepted, and not converted to `ACCEPTED` or `ACCEPTED_WITH_CONSTRAINTS`. The UI-owned half of the conflict is `CORRECTED_AND_MERGED` via PR #30 (`UI-DEC-026`, `UI-DEC-027`, merge commit `63093f22`), which is owner-side reconciliation and not acceptance of any Auth head; the Auth-owned half is `CORRECTED_IN_WORKTREE / PENDING_A2_AUTH_ACCEPTANCE_AND_PUSH`. See `AUTH-DEC-052`. Accepted UI-facing areas: callback ownership, the nine-state session model, the two `REFRESH_PENDING` modes, `processCallback` with atomic final-session observability, the `getAccessTokenForApiRequest` boundary, the eleven error classifications, indistinguishable presentation of the four protected sign-in failures, relative-path-only redirects, fail-closed protected content, callback reload semantics, bounded callback correlation, preserved-session callback-failure separation, UI route protection as defense-in-depth, and no UI authorization authority. Blocking: the UI-owned cookie-custody conflict and the Auth-owned frozen route. `AUTH-DEP-012` remains `OPEN / NOT_ACCEPTED`. See `AUTH-ISSUE-027`. |
| Default post-sign-in and safe recovery destination | `FROZEN` | `/` for both, `A2_UI_PROPOSED / A2_AUTH_APPROVED`. `/` already exists as the implemented Overview destination, is same-origin, and depends on no Runs, Evidence, Benchmarks, API-runtime or Auth-specific feature route. A rejected callback that leaves an independently established, known-valid session standing recovers to `/`; the rejected attempt's intended-return destination is `NEVER_USED`, no callback success is reported, and the preserved session is still never correlation. Intended-return validation rules are unchanged. See `AUTH-DEC-043`. |
| `AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001-A3-C2` | `CORRECTED / UNSTAGED / PENDING_A2_AUTH_REVIEW` | A2-AUTH returned a second `CHANGES_REQUIRED_BEFORE_A2_AUTH_ACCEPTANCE` on the `A3-C1` text. Two corrections applied in the same seven files at the same baseline `006cc88`: (1) the callback-correlation record given a coherent two-phase lifecycle — `PENDING_ATTEMPT_CORRELATION` then `COMPLETED_CALLBACK_CORRELATION` — whose completed phase survives successful completion for a bounded, non-indefinite post-completion window, replacing text that required post-success duplicate correlation while also removing the record at the successful terminal outcome; (2) `INVALID_CALLBACK` narrowed to classify the callback attempt only, so an independently established, known-valid session is preserved rather than invalidated, while a session of unknown validity still fails closed. Recorded as `AUTH-DEC-040` and `AUTH-DEC-041`; no new issue opened, `AUTH-ISSUE-025` broadened. Contract version and classification unchanged. Documentation only. A2-AUTH acceptance is not claimed and remains outstanding. |
| `AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001-A3-C1` | `SUPERSEDED_BY_A3-C2 / CORRECTED / UNSTAGED / PENDING_A2_AUTH_REVIEW` | A2-AUTH returned `CHANGES_REQUIRED_BEFORE_A2_AUTH_ACCEPTANCE` on the original draft. Four corrections applied in the same seven files at baseline `006cc88`: fail-closed `REFRESH_PENDING` modes, callback duplicate/replay correlation, scoped cross-context refresh limits, and Auth-owned intended-return state binding. Recorded as `AUTH-DEC-036` through `AUTH-DEC-039`; opened `AUTH-ISSUE-025` and `AUTH-ISSUE-026`. Contract version and classification unchanged. Documentation only. Its callback-correlation lifetime and its `INVALID_CALLBACK` session outcome are superseded by the `A3-C2` corrections; the rest stands. |
| `AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001-A3` | `SUPERSEDED_BY_A3-C1 / DRAFTED / UNSTAGED` | Seven Auth-owned files drafted at baseline `006cc88`. `CONTRACT-AUTH-001` raised to `1.1.0-draft.1` with the `AUTH-002` sign-in, callback, session, custody, refresh, sign-out, redirect, adapter, error, Backend-boundary and Security sections plus 20 conceptual fixtures. Documentation only. Its `REFRESH_PENDING`, duplicate-callback, single-flight and return-path text is superseded by the `A3-C1` and `A3-C2` corrections. |
| `AUTH-DEPENDENCY-RECONCILIATION-001-A3` | `HISTORICAL / PASS / VERIFIED_COMPLETE / A2_AUTH_ACCEPTED / MERGED` | `COMPLETED`. The six-file reconciliation package merged through pull request #21, implementation commit `fb89d72`, merge commit `ba4247a`. Its commit, push and PR actions are finished; no action remains. The old reconciliation branch `agent2/auth-dependency-reconciliation` and worktree `/Users/omkar/Documents/TestGap-Miner-wt-auth-dependency-reconciliation` are `SUPERSEDED` and are not used by the current task. |
| `AUTH-001` | `PASS / VERIFIED_COMPLETE / MERGED` | `AUTH-001-C1`: `PASS`. `AUTH-001-C2`: `PASS`. A2-AUTH accepted the complete audit package and it merged through pull request #17; no additional audit repair is required. |
| `AUTH-DEP-004` | `ACCEPTED_WITH_CONSTRAINTS / ACKNOWLEDGED / MERGED` | A2-DEPLOYMENT accepted with constraints; A2-AUTH acknowledged. Durably merged through pull request #20, merge commit `fc549fa1a4c77f4835acefbb4f937c35ad6e8f76`. Evidence: `docs/components/deployment/DECISION_LOG.md`, `docs/components/deployment/ENVIRONMENT_VARIABLES.md`. |
| `AUTH-DEP-010` | `ACCEPTED_WITH_CONSTRAINTS / ACKNOWLEDGED` | A2-UI accepted with constraints; A2-AUTH acknowledged. UI ownership established through pull request #19. Evidence: `docs/specifications/A2_UI_MANAGER.md` and the UI-owned durable records under `docs/components/ui/`. |
| Accepted human identity architecture | `APPROVED_FOR_AUTH_CONTRACT_AND_DESIGN` | Deployment-owned design: `SUPABASE_AUTH_WITH_GITHUB_OAUTH`; canonical issuer `https://<SUPABASE_PROJECT_REF>.supabase.co/auth/v1`; audience `authenticated`; JWKS `https://<SUPABASE_PROJECT_REF>.supabase.co/auth/v1/.well-known/jwks.json`. Accepted design values only; not proof of configured runtime. |
| `AUTH-002` contract/design | `DRAFTED / PENDING_A2_AUTH_REVIEW / PENDING_CONSUMER_REVIEW` | Superseded `READY_FOR_AUTH_002_CONTRACT_AND_DESIGN`: the authorized contract/design task is executed and drafted. `CONTRACT-AUTH-001@1.1.0-draft.1` carries the full sign-in, callback, session, custody, refresh, sign-out, redirect, adapter, error, Backend-boundary, Security and fixture content. Not accepted, not implementation-ready. |
| `CONTRACT-AUTH-001@1.1.0-draft.1` | `DRAFT_FOR_CONSUMER_REVIEW / NOT_IMPLEMENTATION_READY / NOT_IMPLEMENTED / NOT_TESTED` | Additive compatible minor over `1.0.0-draft.2`; no breaking change. Now carries the four A2-AUTH corrections (`AUTH-DEC-036`–`AUTH-DEC-039`) plus the second-round corrections (`AUTH-DEC-040`, `AUTH-DEC-041`), which restrict, or repair an internal contradiction in, the drafted behavior rather than extending it; the version identifier is unchanged because the draft was never accepted and no consumer implemented against it. Required consumers: `A2-UI`, `A2-SECURITY`, `A2-DEPLOYMENT`, `A2-BACKEND`, `A2-INTEGRATION`. `A2-UI` responded `SPECIFICATION_CONFLICT` and `A2-SECURITY` responded `REJECTED_WITH_REASON`, both against head `7abe17a`; `A2-INTEGRATION` responded `ACCEPTED_WITH_CONSTRAINTS` at that head with final review pending; `A2-DEPLOYMENT` and `A2-BACKEND` have no reconciled response. Silence is not acceptance, a returned `SPECIFICATION_CONFLICT` is not acceptance, and a returned `REJECTED_WITH_REASON` is not acceptance. |
| Session refresh semantics | `CORRECTED_IN_DRAFT / A2_SECURITY_REREVIEW_REQUIRED / NOT_TESTED` | `REFRESH_PENDING` carries two modes: `PROVEN_CREDENTIAL` may keep existing content visible while deferring new protected requests; `UNPROVEN_CREDENTIAL` — expired token, Backend `401`, unknown validity — removes protected content and prohibits protected requests. Single-flight refresh is scoped to one adapter instance or browsing context; cross-tab, cross-request and cross-instance serialization is explicitly not claimed. `NOT_TESTED`. See `AUTH-ISSUE-026`. |
| Callback correlation and intended-return state | `FROZEN_BY_A2_SECURITY / SERVER_SIDE / EPHEMERAL / A2_DEPLOYMENT_COMPATIBILITY_PENDING` | A duplicate callback resolves only on proven correlation to the same sign-in attempt, flow and completed outcome; an existing session is not correlation. The intended-return state is Auth-owned, attempt-bound, expiry-limited, single-use and removed on success and failure alike, and is never accepted on syntactic safety alone. Both mechanisms are now **frozen** by `A2-SECURITY`: the callback-correlation mechanism is frozen and the intended-return mechanism is frozen; correlation is server-side and ephemeral, and intended-return state is server-side only, held inside the server-side pending correlation record. What remains outstanding is not a Security policy decision: the physical storage technology and the deployment topology are pending `A2-DEPLOYMENT` compatibility confirmation, and no vendor and no storage technology has been selected. See `AUTH-DEC-049`, `AUTH-DEC-050` and `AUTH-ISSUE-025`. |
| Callback-correlation lifecycle | `FROZEN_BY_A2_SECURITY / A2_DEPLOYMENT_COMPATIBILITY_PENDING / NOT_IMPLEMENTED / NOT_TESTED` | The correlation record is `PENDING_ATTEMPT_CORRELATION` from `beginSignIn` until the flow completes, then `COMPLETED_CALLBACK_CORRELATION` on successful first callback processing. The lifecycle is frozen: `PENDING_ATTEMPT_CORRELATION` has a maximum lifetime of 10 minutes from sign-in initiation; `COMPLETED_CALLBACK_CORRELATION` lives exactly 120 seconds from successful completion; the transition between them is `ATOMIC`; an unavailable store or an unverifiable handle is `FAIL_CLOSED`. The completed record therefore survives successful completion for that frozen window so an immediate duplicate invocation and a post-success reload correlate without another exchange and without another session; it is never valid indefinitely; and no failed, abandoned, malformed, expired or terminally rejected flow may produce one. After the window expires or the record is removed, a later invocation returns `INVALID_CALLBACK` with no exchange and no callback-directed navigation. The physical storage substrate and deployment topology are `PENDING_A2_DEPLOYMENT_CONFIRMATION`. See `AUTH-DEC-040`, `AUTH-DEC-049` and `AUTH-ISSUE-025`. |
| Invalid callback versus existing session | `SEMANTICS_DEFINED / CONSUMER_REVIEW_PENDING` | `INVALID_CALLBACK` classifies the callback attempt only. Every rejection creates no session, performs no exchange, performs no callback-directed navigation, clears callback parameters, removes the rejected attempt's return state and emits the Security event. The resulting session state is conditional: `TERMINAL_SESSION_ERROR` where no independently established, known-valid session pre-existed the callback or where a pre-existing session's validity is unknown; otherwise the known-valid session is preserved as `AUTHENTICATED` while the callback fails. A preserved session is still never correlation and never proof of callback success, and an invalid callback never revokes a separately valid provider session. See `AUTH-DEC-041`; A2-UI question 16 and A2-SECURITY question 16. |
| `AUTH-002` implementation | `NOT_AUTHORIZED` | Runtime implementation `NOT_AUTHORIZED`; frontend implementation `NOT_AUTHORIZED`; provider runtime `NOT_PROVISIONED / NOT_TESTED`. Neither accepted design status nor a drafted contract authorizes implementation. |
| Token custody decision | `DECIDED / SECURITY_POLICY_ACCEPTED / NOT_TESTED` | The accepted storage constraints are satisfiable by the official `@supabase/ssr` integration with `createBrowserClient`/`createServerClient` cookie-backed PKCE sessions. `HttpOnly` is not achievable for the browser-readable session and is not an accepted constraint. `A2-SECURITY` has now accepted this architecture as policy and frozen the cookie, CSRF and sign-out-scope posture — see `AUTH-DEC-045`, `AUTH-DEC-046` and `AUTH-DEC-047`; these are no longer unresolved `A2-SECURITY` decisions. `A2-DEPLOYMENT` runtime confirmation is outstanding. `NOT_IMPLEMENTED / NOT_TESTED`. |
| Provider provisioning | `NOT_STARTED / NOT_TESTED` | No Supabase project provisioning, GitHub OAuth provider configuration, Vercel project, production Dashboard hostname, TLS verification, production callback registration, or secret injection is proven by this repository. |
| `CONTRACT-AUTH-001@1.0.0-draft.2` | `HISTORICAL / ACKNOWLEDGED_AND_MERGED / SUPERSEDED_BY_1.1.0-draft.1` | A2-DATABASE recorded acknowledgement in `docs/components/database/COMPONENT_STATUS.md` and `DECISION_LOG.md`; merged into `origin/main`. Superseded as the current version by `1.1.0-draft.1`, which preserves all of its semantics. |
| `DB-002` | `PASS / VERIFIED_COMPLETE / MERGED` | Pull request #12, implementation commit `5506ab5`, merge commit `3701520`; closed by PR #13 (`1511f47`). Seven domain tables, five of them Auth-owned. |
| Contract task (`AUTH-DB002-CONTRACT-001`) | `PASS / COMPLETE` | Producer package accepted; consumer acknowledgement received and merged. No review action remains. |
| Auth identity persistence | `VERIFIED_COMPLETE` | `apps/api/app/db/models/auth.py`: `users`, `auth_subjects`, `github_installations`, `repositories`, `repository_access`. 21 Auth constraint tests executed 2026-08-02, all passing. |
| Auth implementation — human sign-in, session, OAuth callback | `NOT_STARTED` | Corrected at baseline `006cc88`: the earlier "no `apps/web`" evidence is `SUPERSEDED`. `apps/web` now exists, but it contains no Auth code. Verified: `apps/web/src/app` holds only `layout.tsx`, `page.tsx`, `providers.tsx`, `globals.css` and `page.test.tsx`; there is no `/auth/callback` route, no Auth adapter, no token-storage behavior, and no provider integration. `apps/web/package.json` lists no `@supabase/ssr` or `@supabase/supabase-js` dependency. |
| `apps/web` | `PRESENT / NO_AUTH_SURFACE` | Merged: `UI-002` Next.js scaffold (PR #26, `c5d4c8a`), `UI-003` MUI shell (PR #27, `e7de96f`), frontend regression foundation (PR #28, `006cc88`). Next.js 16 App Router with React 19 and MUI. UI-owned; not modified by this task. The UI durable records now match this evidence after `UI-DEC-027` merged in PR #30 — see `AUTH-ISSUE-023`. A merged frontend foundation is not Auth evidence. |
| `/auth/callback` route | `NOT_IMPLEMENTED` | Reserved. A2-UI owns route existence and UX; A2-AUTH owns semantics, frozen by `CONTRACT-AUTH-001@1.1.0-draft.1`; A2-DEPLOYMENT owns deployed registration. |
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

`AUTH-002` contract/design is `DRAFTED / PENDING_A2_AUTH_REVIEW /
PENDING_CONSUMER_REVIEW`. The prior `READY_FOR_AUTH_002_CONTRACT_AND_DESIGN`
state is `SUPERSEDED` because the authorized contract/design task has now been
executed. Both direct prerequisites remain satisfied: `AUTH-DEP-004` is
`SATISFIED_FOR_CONTRACT_AND_DESIGN` and `AUTH-DEP-010` is
`SATISFIED_FOR_OWNERSHIP_AND_COORDINATION`. `AUTH-DEP-006` is a future Backend
integration dependency, and `AUTH-DEP-009` is a GitHub App/webhook
configuration dependency; neither is a direct `AUTH-002` prerequisite. See
`AUTH-001_AUDIT.md` §13.

The drafted contract is not accepted. Consumer reviews received so far:

| Consumer | Response at head `7abe17a` | State |
|---|---|---|
| `A2-UI` | `SPECIFICATION_CONFLICT` | `SPECIFICATION_CONFLICT_AT_7ABE17AF / UI_SIDE_CORRECTION_MERGED / AUTH_CORRECTION_IN_PROGRESS / REREVIEW_REQUIRED / NOT_ACCEPTED` |
| `A2-SECURITY` | `REJECTED_WITH_REASON`, seven normative corrections | `REJECTED_WITH_REASON_AT_7ABE17AF / SEVEN_CORRECTIONS_APPLIED / REREVIEW_REQUIRED / NOT_ACCEPTED` |
| `A2-DEPLOYMENT` | none reconciled | `CONSUMER_RESPONSE_OR_AFFECTED_BOUNDARY_CONFIRMATION_STILL_REQUIRED` |
| `A2-BACKEND` | none reconciled | `CONSUMER_RESPONSE_OR_AFFECTED_BOUNDARY_CONFIRMATION_STILL_REQUIRED` |
| `A2-INTEGRATION` | `ACCEPTED_WITH_CONSTRAINTS` | `ACCEPTED_WITH_CONSTRAINTS_AT_7ABE17AF / FINAL_REREVIEW_REQUIRED` |

Two of the five reviews are rejections of the reviewed head, not acceptances of
the contract. Silence is not acceptance; neither is a rejection that Auth has
since corrected.

`CONTRACT-AUTH-001@1.1.0-draft.1` is `DRAFT_FOR_CONSUMER_REVIEW /
NOT_IMPLEMENTATION_READY`. It is not `ACCEPTED`, not `IMPLEMENTATION_READY`, not
`IMPLEMENTED`, and not `TESTED`. Auth runtime is `NOT_IMPLEMENTED /
NOT_TESTED`. Frontend Auth is `NOT_IMPLEMENTED / NOT_TESTED / NOT_AUTHORIZED`.
Provider runtime is `NOT_PROVISIONED / NOT_TESTED`. `UI-004` is
`NOT_AUTHORIZED`.

The A2-UI consumer response carries two authorized corrections, one per owner.
The Auth-owned correction is applied here and recorded as `AUTH-DEC-043`: `/`
frozen as the default post-sign-in destination and as the preserved-session
rejected-callback safe recovery destination, with the rejected intended-return
destination `NEVER_USED`. It is `CORRECTED_IN_WORKTREE /
PENDING_A2_AUTH_ACCEPTANCE_AND_PUSH`.

The UI-owned correction — superseding the conflicting `UI-DEC-013`
non-`HttpOnly` cookie meaning while preserving its `localStorage`,
`sessionStorage` and duplicate-store prohibitions — belongs to `A2-UI`, was not
performed or authored here, and is now `CORRECTED_AND_MERGED` by its owner as
`UI-DEC-026` and `UI-DEC-027` in PR #30 (implementation commit `30deb920`, merge
commit `63093f22`, current `origin/main`). Recorded on the Auth side as
`AUTH-DEC-052`. The merged UI records preserve the `localStorage` and
`sessionStorage` prohibitions, forbid any duplicate or shadow session store,
permit only the canonical Auth-owned `@supabase/ssr` session and only
conditionally on A2-SECURITY acceptance of the final cookie posture, propose `/`
as the UI default and safe recovery route, and keep `UI-004` `NOT_AUTHORIZED`.
The merged custody rule is therefore compatible with the canonical Auth-owned
session this contract requires.

That merge is owner-side reconciliation, not acceptance: the merged UI text
itself states it does not make Auth PR #29 acceptable and that `A2-UI` rereview
is still required. `AUTH-DEP-012` remains `OPEN / NOT_ACCEPTED` and
`AUTH-ISSUE-027` remains open until `A2-UI` rereviews the corrected PR #29 head.

The A2-SECURITY consumer response carries seven required normative corrections,
all Auth-owned and all applied here as `AUTH-DEC-045` through `AUTH-DEC-051`,
with the response itself recorded as `AUTH-DEC-044`. `A2-SECURITY` accepted the
selected architecture while rejecting the reviewed head, so the browser-readable
provider-session cookie is now accepted **policy** rather than a pending
question — which is why no record here still describes that posture as
`PENDING_A2_SECURITY_ACCEPTANCE`. Applying every required correction is not
`A2-SECURITY` acceptance: `AUTH-DEP-011` remains `OPEN / NOT_ACCEPTED`,
`AUTH-ISSUE-028` remains open, and `A2-SECURITY` rereview of the corrected PR
#29 head is required.

`A2-BACKEND` and `A2-DEPLOYMENT` compatibility confirmations are outstanding and
are not claimed anywhere. `AUTH-ISSUE-024` is not closed: the Security response
arrived through the coordinator, not through a `docs/components/security/`
record set, which still does not exist. No Security file was created by this
task.

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

`AUTH-ISSUE-011` is `RESOLVED_IN_DRAFT`. The `CONTRACT-AUTH-001` metadata no
longer describes DB-002 as a blocking, pending consumer. A2-DATABASE is now
recorded as `HISTORICAL_BLOCKING_CONSUMER / ACKNOWLEDGED_AND_IMPLEMENTED`, the
evidence baseline is updated to `006cc88`, and the closing limitations block
records `DB-002` as merged and unblocked. The resolution becomes durable only
after A2-AUTH acceptance and merge.

No Auth implementation, test, or configuration was created by this task. Auth
runtime remains `NOT_STARTED / NOT_TESTED`; frontend Auth behavior, provider
runtime and Backend JWT behavior remain `NOT_IMPLEMENTED / NOT_TESTED`.
`AUTH-002` implementation remains `NOT_AUTHORIZED`, and `UI-004` and
`AUTH-003` remain unauthorized.

The A2-AUTH correction round applied four required changes before acceptance
and closed no issue. It opened `AUTH-ISSUE-025` (undecided intended-return
state and callback-correlation mechanisms) and `AUTH-ISSUE-026` (cross-context
refresh is neither serialized nor tested). At that round both were pending an
A2-SECURITY decision. That is no longer their current state: `A2-SECURITY` has
since decided the `AUTH-ISSUE-025` mechanisms as policy under `AUTH-DEC-049` and
`AUTH-DEC-050`, leaving only the `A2-DEPLOYMENT`-owned storage substrate and
topology residue, and `AUTH-ISSUE-026` remains open on cross-context refresh
being untested rather than on a missing Security decision. `AUTH-ISSUE-024`
still stands — no `docs/components/security/` record set exists — and that
remains Agent 1's to resolve; no Security file was created here.

The second A2-AUTH correction round applied two further required changes before
acceptance, closed no issue and opened none. `AUTH-DEC-040` replaced a
contradiction internal to the `A3-C1` text — post-success duplicate correlation
was required while the correlation record was also removed at the successful
terminal outcome — with a two-phase lifecycle whose completed phase persists for
a bounded, non-indefinite post-completion window. `AUTH-DEC-041` separated
callback-attempt failure from session-validity failure, so `INVALID_CALLBACK` no
longer asserts that an independently established, known-valid session is
invalid. `AUTH-ISSUE-025` was broadened to carry the undecided window length,
representation, retention and cleanup; no sibling issue was opened for
`AUTH-DEC-041`, because it defers nothing to another owner. Every preserved
constraint from the first round still stands: two fail-closed `REFRESH_PENDING`
modes with one-way degradation, scoped single-flight refresh with no global
cross-tab claim, attempt-bound intended-return state, callback replay
resistance, an existing session never being correlation, the prohibited-storage
list, `Bearer`-only transport, and every `NOT_PROVISIONED`, `NOT_IMPLEMENTED`,
`NOT_TESTED` and `NOT_AUTHORIZED` status above.

Next action: A2-AUTH independent review of the corrected seven-file unstaged
draft, including SHA-256 verification of every changed file. On a pass, A2-AUTH
and the user manage staging, one additive documentation commit, and a normal
push to `agent2/auth-002-session-contract`, which updates the existing PR #29.
The commit `7abe17a` is not amended, nothing is rebased or force-pushed, no
second Auth pull request is opened, and PR #29 stays `OPEN / DRAFT /
NOT_MERGED`. The new head must then be recorded for rereview. The corrected head
requires at minimum `A2-UI` rereview, `A2-SECURITY` rereview, `A2-BACKEND`
affected-boundary review and `A2-DEPLOYMENT` affected-boundary review;
`A2-INTEGRATION` final review occurs only after all affected owner responses and
corrections are complete. Merge remains blocked until those reviews return
acceptable dispositions, material conflicts are reconciled, and Agent 1 records
the final cross-component semantic decision.
