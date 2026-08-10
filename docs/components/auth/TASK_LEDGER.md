# Auth Task Ledger

- Date: 2026-08-10
- Current task:
  `AUTH-006-FINALIZE-CONTRACT-AUTH-001-V1.2.0-DRAFT.1-001-A3-R2`
- Authorized manager task:
  `AUTH-006-FINALIZE-CONTRACT-AUTH-001-V1.2.0-DRAFT.1-001`
- Authorizing coordinator:
  `Agent 1`
- Task type:
  `DOCUMENTATION / CONTRACT FINALIZATION / NO_RUNTIME_IMPLEMENTATION`
- Consumer reviews for AUTH-005 additions:
  `A2-UI` (`ACCEPTED_WITH_CONSTRAINTS`), `A2-SECURITY` (`ACCEPTED_WITH_CONSTRAINTS`),
  `A2-DEPLOYMENT` (`ACCEPTED_WITH_CONSTRAINTS`), `A2-INTEGRATION` (`ACCEPTED_WITH_CONSTRAINTS`)
- Baseline: `5ffa8994b286e85d9f676336dbe0169cfbc89d2c`
- Worktree: `/Users/omkar/Documents/TestGap-Miner-wt-auth-contract-1.2-finalization`
- Branch: `agent2/auth-contract-1.2-finalization`
- `CONTRACT-AUTH-001@1.2.0-draft.1`: `FINALIZED_CONTRACT_DRAFT_FOR_A2_REVIEW / NOT_IMPLEMENTATION_READY`
- Auth identity persistence: `VERIFIED_COMPLETE` and merged
- Auth runtime status: `EXISTING_MERGED_CODE_IN_APPS_WEB_SRC_AUTH / AUTH_006_RUNTIME_MODIFICATION_AUTHORIZED=NONE / FENCE_CORRECTION_RUNTIME=NOT_YET_AUTHORIZED`
- `ASSUMED`: `NONE`

| Task | Status | Evidence / blocker |
|---|---|---|
| `AUTH-006-FINALIZE-CONTRACT-AUTH-001-V1.2.0-DRAFT.1-001-A3-R2` — Finalize Auth contract 1.2.0-draft.1 | `IMPLEMENTED / UNSTAGED / UNCOMMITTED / PENDING_A2_AUTH_REVIEW` | Finalizes `CONTRACT-AUTH-001@1.2.0-draft.1` incorporating accepted `AUTH-005` normative corrections (`SIGN_OUT_WINS`, `ESTABLISHED_AUTH_SESSION` 6 criteria, context/binding handles, local sign-out tombstone, tombstone ordering before publication, new-sign-in reconciliation, session-binding exclusions, response fence non-mutation, `/auth/session-fence` UI host boundary, security event follow-up, production/local sync authority constraints, and 11 future integration test requirements). Incorporates R1/R2 targeted corrections: PKCE provider custody & OAuth state ownership preservation, callback correlation record separation, Auth runtime unit test reconciliation (`PRESENT_IN_BASELINE`), Auth CSRF/cookie foundation reconciliation (`PRESENT_IN_BASELINE`), OPEN_ISSUES impact wording fix, callback generation supersession, tombstone ordering before publication, new-sign-in reconciliation, session-binding record exclusions, response fence non-mutation, and reconciled current runtime status. All required consumer reviews complete (`ACCEPTED_WITH_CONSTRAINTS`). Contract status `FINALIZED_CONTRACT_DRAFT_FOR_A2_REVIEW`. Existing merged Auth runtime code exists under `apps/web/src/auth/**`; `AUTH-006` authorizes NO runtime modification; `AUTH-003`/`AUTH-005` fence correction runtime is `NOT_YET_AUTHORIZED / NOT_YET_IMPLEMENTED`. |
| `AUTH-002-FINAL-READINESS-RECONCILIATION-001-A3` — Final non-normative readiness reconciliation | `IMPLEMENTED / UNSTAGED / UNCOMMITTED / PENDING_A2_AUTH_REVIEW` | Reconciles non-normative readiness state across all five consumer domains (`A2-UI`, `A2-SECURITY`, `A2-BACKEND`, `A2-DEPLOYMENT`, `A2-INTEGRATION`) against corrected HEAD `84ad9e322d886f8963c34386f87074a444b3fa2b`. All five owners returned `ACCEPTED_WITH_CONSTRAINTS`. Reconciles merged shared registry PR #31 (`a80145e2` / `1057ba72`), setting `AUTH-DEP-003` to `COMPLETE / VERSION_AWARE_SHARED_REGISTRY_RECONCILED` and `AUTH-ISSUE-002` to `CLOSED / VERSION_AWARE_REGISTRY_RECONCILED`. Preserves historical responses at `7abe17af` (`A2-UI` `SPECIFICATION_CONFLICT`, `A2-SECURITY` `REJECTED_WITH_REASON`, `A2-INTEGRATION` `ACCEPTED_WITH_CONSTRAINTS`). Adds decision `AUTH-DEC-053`. `CONTRACT-AUTH-001.md` blob SHA `8ed2154561785566b4b17baa16535e1fad8e662c` is byte-identical and untouched. Auth runtime remains `NOT_IMPLEMENTED / NOT_TESTED / NOT_AUTHORIZED`, Provider runtime `NOT_PROVISIONED / NOT_TESTED`, `UI-004` `NOT_AUTHORIZED`, Release `NOT_READY`. PR #29 remains `OPEN / DRAFT / NOT_MERGED` pending final Agent 1 readiness decision. |
| `AUTH-002-CONSUMER-CORRECTION-UI-SECURITY-001-A3-PR30` — PR #30 merged-state reconciliation | `RECONCILED / UNSTAGED / UNCOMMITTED / PENDING_A2_AUTH_REVIEW` | Continuation of `AUTH-002-CONSUMER-CORRECTION-UI-SECURITY-001-A3` in the same branch and worktree; the existing uncommitted seven-file Auth package was preserved, not discarded or recreated. Reconciles that package to the new `origin/main` `63093f22c37a0fc6affe168f7d5230107b05cdf3`, produced by the merged UI correction PR #30 — `docs(ui): reconcile Auth session custody and merged frontend state`, implementation commit `30deb92000a20d3837b2423b6bdee3ea3335a7f1`, merge commit `63093f22c37a0fc6affe168f7d5230107b05cdf3`, six UI durable-record files, no `docs/components/auth/**` path. Records the UI-owned half of the `A2-UI` conflict as `CORRECTED_AND_MERGED` via `UI-DEC-026`/`UI-DEC-027`, which preserve the `localStorage` and `sessionStorage` prohibitions, the no-duplicate/shadow-store rule and canonical Auth-owned `@supabase/ssr` custody, propose `/` as the UI default and safe recovery route, and keep `UI-004` `NOT_AUTHORIZED`. Adds `AUTH-DEC-052`; `AUTH-DEC-042`–`AUTH-DEC-051` unchanged. The historical `A2-UI` `SPECIFICATION_CONFLICT` at `7abe17af` is preserved, not rewritten. `AUTH-DEP-012` moved to `OPEN / RESPONSE_RECEIVED / SPECIFICATION_CONFLICT_AT_7ABE17AF / UI_OWNER_CORRECTION_MERGED_VIA_PR_30 / AUTH_OWNER_CORRECTION_IN_PROGRESS / CORRECTED_HEAD_REREVIEW_REQUIRED / NOT_ACCEPTED`; `AUTH-ISSUE-027` stays `OPEN` with the UI side `CORRECTED_AND_MERGED` and the Auth side `CORRECTED_IN_WORKTREE / PENDING_A2_AUTH_ACCEPTANCE_AND_PUSH`; `AUTH-ISSUE-023` resolved by `UI-DEC-027`. No merge, rebase, cherry-pick, reset, amend or force-push; branch HEAD remains `7abe17af`. No Backend or Deployment acceptance invented. Contract version `1.1.0-draft.1` and classification `ADDITIVE_COMPATIBLE_MINOR` unchanged. Same seven authorized Auth files; no eighth path; no UI file modified — PR #30 is external merged evidence only; nothing staged, committed, pushed or merged. |
| `AUTH-DB002-CONTRACT-001` — Publish DB-002 Auth contract and records | `PASS / COMPLETE / MERGED_AND_ACKNOWLEDGED` | Producer package accepted by A2-AUTH; A2-DATABASE recorded `CONTRACT-AUTH-001@1.0.0-draft.2` as `ACKNOWLEDGED_AND_MERGED`; DB-002 implemented against it and merged. No review action remains. |
| `AUTH-DB002-CONTRACT-001-C2` — Issuer and access-grant expiration clarification | `PASS / COMPLETE` | Both clarifications are implemented in the merged schema and covered by passing constraint tests: exact case-sensitive un-normalized `issuer`/`subject`, and `expires_at`/`expired_at`/`revoked_at` kept distinct. |
| `AUTH-001` — Authentication and trust-boundary audit | `PASS / VERIFIED_COMPLETE / MERGED` | Complete inventory; 13 boundaries; 22 paths; 15 risks; five new dependency requests; `AUTH-001-C1` and `AUTH-001-C2` reconciliations accepted; merged through PR #17; no Auth implementation created. |
| `AUTH-005` — Webhook authenticity and idempotency precheck | `BLOCKED` | Blocked by sequential predecessor `AUTH-004`, `AUTH-DEP-006` (raw-body webhook route contract), and `AUTH-DEP-009` (webhook secret name and endpoint configuration). Durable delivery-GUID persistence is deferred to downstream integration and does not directly block the verifier task. |
| `AUTH-006` — Repository-scoped authorization | `BLOCKED` | Blocked by `AUTH-003`, `AUTH-DEP-006`, `AUTH-DEP-007` (run requests carry no installation reference, so the exact tuple is not reconstructable from a request row), and `AUTH-DEP-008`. Grant persistence itself is `VERIFIED_COMPLETE`. |
| `AUTH-007` — Auth hardening and observability | `BLOCKED` | Blocked by `AUTH-DEP-005` (Security event, freshness, retention and redaction guidance) and all prior Auth implementation. `AUTH-DEP-004` is accepted for contract and design, but the production Dashboard hostname and TLS verification remain `NOT_PROVISIONED / NOT_TESTED`, so hardening acceptance still requires deployed evidence. |
| `AUTH-008` — Authentication final acceptance | `BLOCKED` | Blocked by every prior Auth task, final A2-SECURITY review, unresolved machine publication attribution through `AUTH-DEP-008`, and unresolved end-to-end delivery idempotency. |

Auth identity persistence is `VERIFIED_COMPLETE` and merged. Existing merged Auth runtime code exists in baseline under `apps/web/src/auth/**` (including `AuthAdapter`, state machine, correlation, storage boundary, redirect, types, and unit tests). `tests/auth/` is `ABSENT`. Auth runtime unit tests are `PRESENT_IN_BASELINE` under `apps/web/src/auth/**`, while AUTH-005 cross-runtime/browser-network acceptance is `NOT_YET_TESTED / FUTURE_INTEGRATION_REQUIREMENT` (Vitest/jsdom-only proof is INSUFFICIENT for stale HTTP response/browser-cookie ordering acceptance).

No task above is marked ready on assumption. `AUTH-002` contract and design is
**drafted, corrected three times, and not accepted**. Applying A2-AUTH
corrections is not A2-AUTH acceptance, a later correction round does not make an
earlier one accepted, and reconciling a consumer's `SPECIFICATION_CONFLICT` is
not that consumer's acceptance. No Auth runtime implementation, `UI-004`,
`AUTH-003`, `AUTH-004` or provider provisioning was started by the consumer
correction task. Drafting a contract is not acceptance, is not
implementation readiness, and is not implementation authorization. No runtime
task is marked ready because a contract was drafted: `AUTH-003` is
`NOT_AUTHORIZED`, and `AUTH-004` through `AUTH-008` retain every sequential,
Security, Workflow, Backend and runtime prerequisite listed above.

`UI-004` is not authorized by `CONTRACT-AUTH-001@1.1.0-draft.1`. The contract
defines the semantics a future, separately authorized `UI-004` may consume; it
grants no UI implementation authority. `A2-UI` has now reviewed the contract and
returned `SPECIFICATION_CONFLICT` against head `7abe17a`, and `A2-SECURITY` has
returned `REJECTED_WITH_REASON` against the same head; both authorize `UI-004`
no more than silence did. The merged UI correction PR #30 does not authorize it
either — `UI-DEC-026` and `UI-DEC-027` keep `UI-004` `BLOCKED / NOT_AUTHORIZED`
in the UI's own records.

No Auth runtime, `UI-004`, `AUTH-003`, `AUTH-004`, provider provisioning,
Backend work or Deployment work was started by the consolidated consumer
correction. Recording a Security requirement is not implementing it: no key was
generated, no secret manager selected, no cookie set, no CSRF runtime built, no
correlation storage created, no JWT lifetime configured, no CORS configured, no
`@supabase/ssr` package installed, and no provider provisioned.
