# Auth Task Ledger

- Date: 2026-08-06
- Current task:
  `AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001-A3-C2`
- Prior correction task:
  `AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001-A3-C1`
- Originating task: `AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001-A3`
- Parent task: `AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001`
- A2-AUTH review of the originating draft:
  `CHANGES_REQUIRED_BEFORE_A2_AUTH_ACCEPTANCE`
- Prompt type: `A2_AUTH_CORRECTION / A3_DOCUMENTATION_EXECUTION_AND_VALIDATION`
- Scope: `AUTH_CONTRACT_AND_DESIGN_DOCUMENTATION_ONLY`
- Base commit: `006cc885161ff49be582a9fa08f353a70c31c7b1`
- Worktree: `/Users/omkar/Documents/TestGap-Miner-wt-auth-002-session-contract`
- Branch: `agent2/auth-002-session-contract`
- `CONTRACT-AUTH-001@1.1.0-draft.1`: `DRAFT_FOR_CONSUMER_REVIEW /
  NOT_IMPLEMENTATION_READY / NOT_IMPLEMENTED / NOT_TESTED`
- `CONTRACT-AUTH-001@1.0.0-draft.2`: `HISTORICAL / ACKNOWLEDGED_AND_MERGED`,
  superseded as the current version by `1.1.0-draft.1`
- `AUTH-DEPENDENCY-RECONCILIATION-001`: `COMPLETED / MERGED_VIA_PR_21`
  (implementation `fb89d72`, merge `ba4247a`). Its branch and worktree are
  `SUPERSEDED`.
- `apps/web`: `PRESENT / NO_AUTH_SURFACE` (`UI-002` PR #26, `UI-003` PR #27,
  frontend regression foundation PR #28)
- `ASSUMED`: `NONE`
- `DB-002`: `PASS / VERIFIED_COMPLETE / MERGED` (PR #12, merge commit
  `3701520`; closed by PR #13, `1511f47`)
- `AUTH-DEP-004`: `ACCEPTED_WITH_CONSTRAINTS / ACKNOWLEDGED_BY_A2_AUTH /
  MERGED_VIA_PR_20`
- `AUTH-DEP-010`: `ACCEPTED_WITH_CONSTRAINTS / ACKNOWLEDGED_BY_A2_AUTH /
  UI_OWNERSHIP_ESTABLISHED_VIA_PR_19`

| Task | Status | Evidence / blocker |
|---|---|---|
| `AUTH-DB002-CONTRACT-001` — Publish DB-002 Auth contract and records | `PASS / COMPLETE / MERGED_AND_ACKNOWLEDGED` | Producer package accepted by A2-AUTH; A2-DATABASE recorded `CONTRACT-AUTH-001@1.0.0-draft.2` as `ACKNOWLEDGED_AND_MERGED`; DB-002 implemented against it and merged. No review action remains. |
| `AUTH-DB002-CONTRACT-001-C2` — Issuer and access-grant expiration clarification | `PASS / COMPLETE` | Both clarifications are implemented in the merged schema and covered by passing constraint tests: exact case-sensitive un-normalized `issuer`/`subject`, and `expires_at`/`expired_at`/`revoked_at` kept distinct. |
| `AUTH-001` — Authentication and trust-boundary audit | `PASS / VERIFIED_COMPLETE / MERGED` | Complete inventory; 13 boundaries; 22 paths; 15 risks; five new dependency requests; `AUTH-001-C1` and `AUTH-001-C2` reconciliations accepted; merged through PR #17; no Auth implementation created. |
| `AUTH-DEPENDENCY-RECONCILIATION-001-A3` — Post-dependency-merge durable reconciliation | `HISTORICAL / PASS / VERIFIED_COMPLETE / A2_AUTH_ACCEPTED / MERGED` | `COMPLETED`. Auth-owned durable records reconciled with merged `AUTH-DEP-004` (PR #20, merge commit `fc549fa`) and `AUTH-DEP-010` (PR #19) evidence. Merged through PR #21, implementation `fb89d72`, merge `ba4247a`. Documentation only. No action remains; the branch and worktree are `SUPERSEDED`. |
| `AUTH-002` — Dashboard sign-in and session contract | `CONTRACT_AND_DESIGN_CORRECTED / PENDING_A2_AUTH_REVIEW / IMPLEMENTATION_NOT_AUTHORIZED` | Superseded `READY_FOR_CONTRACT_AND_DESIGN`: the authorized contract/design task has been executed and then corrected under `A3-C1` and again under `A3-C2`. `CONTRACT-AUTH-001@1.1.0-draft.1` defines sign-in initiation with Auth-owned intended-return state binding, callback ownership with a two-phase completion-correlation lifecycle bounded by a post-completion correlation window, the nine-state session model with two `REFRESH_PENDING` modes, token custody, scoped refresh, sign-out, safe redirect, the Auth-owned UI adapter interface, an eleven-code error vocabulary whose `INVALID_CALLBACK` resulting session state is conditional rather than always terminal, the Backend boundary, twenty-one Security requirements, and 20 conceptual fixtures plus seven lettered correction sub-fixtures. Not accepted, not implementation-ready. Runtime implementation `NOT_AUTHORIZED`; frontend implementation `NOT_AUTHORIZED`; provider runtime `NOT_PROVISIONED / NOT_TESTED`. `AUTH-DEP-006` and `AUTH-DEP-009` remain non-`AUTH-002` dependencies. |
| `AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001-A3` — Contract and design execution | `SUPERSEDED_BY_A3-C1 / DRAFTED / UNSTAGED / UNCOMMITTED` | Seven authorized Auth-owned files changed at baseline `006cc88`. Token custody determined from current primary Supabase documentation, not from remembered SDK behavior. Five new consumer dependency requests opened: `AUTH-DEP-011` through `AUTH-DEP-015`. No file created, deleted or renamed; no application, test, manifest, lockfile, environment or other-owner file touched. A2-AUTH returned `CHANGES_REQUIRED_BEFORE_A2_AUTH_ACCEPTANCE`. |
| `AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001-A3-C1` — A2-AUTH correction round | `SUPERSEDED_IN_PART_BY_A3-C2 / CORRECTED / UNSTAGED / UNCOMMITTED / PENDING_A2_AUTH_REVIEW` | Four manager corrections applied in the same seven files at the same baseline `006cc88`: (1) `REFRESH_PENDING` split into fail-closed-aware modes `PROVEN_CREDENTIAL` and `UNPROVEN_CREDENTIAL`; (2) duplicate and replayed callbacks resolve only on proven correlation to the same sign-in attempt, flow and completed outcome, an existing session being explicitly insufficient; (3) single-flight refresh scoped to one adapter instance or browsing context, with cross-tab, cross-request and cross-instance serialization no longer claimed; (4) the Dashboard intended-return state separated from provider OAuth state and made Auth-owned, attempt-bound, expiry-limited, single-use and removed on success and failure. Recorded as `AUTH-DEC-036`–`AUTH-DEC-039`; opened `AUTH-ISSUE-025` and `AUTH-ISSUE-026`. Contract version `1.1.0-draft.1` and classification `ADDITIVE_COMPATIBLE_MINOR` unchanged. No eighth file; nothing staged or committed. A2-AUTH returned a second `CHANGES_REQUIRED_BEFORE_A2_AUTH_ACCEPTANCE` against correction (2): its correlation-record lifetime contradicted its own post-success duplicate-correlation requirement, and it treated every `INVALID_CALLBACK` as invalidating the whole browser session. Both are superseded by `A3-C2`; corrections (1), (3) and (4) stand unchanged. |
| `AUTH-002-DASHBOARD-SIGN-IN-SESSION-CONTRACT-001-A3-C2` — Second A2-AUTH correction round | `CORRECTED / UNSTAGED / UNCOMMITTED / PENDING_A2_AUTH_REVIEW` | Two manager corrections applied in the same seven files at the same baseline `006cc88`: (1) the callback-correlation record given a coherent lifecycle — `PENDING_ATTEMPT_CORRELATION` created at sign-in, transitioned or replaced by `COMPLETED_CALLBACK_CORRELATION` on successful first callback processing, the completed record proving only the originating attempt, the flow, the completed outcome and reuse eligibility, remaining available for a bounded post-completion correlation window so an immediate duplicate invocation or a post-success reload correlates without another exchange or another session, never valid indefinitely, and never producible by a failed, abandoned, malformed, expired or terminally rejected flow; (2) `INVALID_CALLBACK` narrowed to classify the callback attempt only — always no session, no exchange, no callback-directed navigation, callback parameters cleared, the rejected attempt's return state removed and the Security event emitted, with the resulting session state conditional: `TERMINAL_SESSION_ERROR / UNAUTHENTICATED` where no independently established, known-valid session pre-existed or where validity is unknown, and the known-valid pre-existing session preserved as `AUTHENTICATED` otherwise, never used as proof of callback success and never revoked because the callback was invalid. Recorded as `AUTH-DEC-040` and `AUTH-DEC-041`; `AUTH-ISSUE-025` broadened; no new issue opened; `AUTH-DEP-011` extended to sixteen Security decisions and `AUTH-DEP-012` to sixteen A2-UI questions. Storage, integrity, representation, retention duration and cleanup — including the window length — remain `PENDING_A2_SECURITY_ACCEPTANCE`; no duration and no Security mechanism was invented. Contract version `1.1.0-draft.1` and classification `ADDITIVE_COMPATIBLE_MINOR` unchanged. No eighth file; nothing staged or committed. |
| `AUTH-003` — Backend JWT validation and user context | `NOT_AUTHORIZED` | Still requires Backend JWT/runtime coordination through `AUTH-DEP-006` (no route surface; no JWT/JWKS dependency in `apps/api/pyproject.toml`). The sequential `AUTH-002` design work is now drafted but not accepted, so the design prerequisite is not yet satisfied. `AUTH-DEP-004` acceptance supplies issuer, audience, and JWKS as accepted design values only, not as a provisioned runtime. |
| `AUTH-004` — GitHub App machine authentication | `BLOCKED` | Blocked by sequential predecessor `AUTH-003` and `AUTH-DEP-009` (App ID, private-key and least-privilege permission configuration; no GitHub App manifest exists). Database installation records are satisfied. `AUTH-DEP-008` is not an `AUTH-004` blocker. |
| `AUTH-005` — Webhook authenticity and idempotency precheck | `BLOCKED` | Blocked by sequential predecessor `AUTH-004`, `AUTH-DEP-006` (raw-body webhook route contract), and `AUTH-DEP-009` (webhook secret name and endpoint configuration). Durable delivery-GUID persistence is deferred to downstream integration and does not directly block the verifier task. |
| `AUTH-006` — Repository-scoped authorization | `BLOCKED` | Blocked by `AUTH-003`, `AUTH-DEP-006`, `AUTH-DEP-007` (run requests carry no installation reference, so the exact tuple is not reconstructable from a request row), and `AUTH-DEP-008`. Grant persistence itself is `VERIFIED_COMPLETE`. |
| `AUTH-007` — Auth hardening and observability | `BLOCKED` | Blocked by `AUTH-DEP-005` (Security event, freshness, retention and redaction guidance) and all prior Auth implementation. `AUTH-DEP-004` is accepted for contract and design, but the production Dashboard hostname and TLS verification remain `NOT_PROVISIONED / NOT_TESTED`, so hardening acceptance still requires deployed evidence. |
| `AUTH-008` — Authentication final acceptance | `BLOCKED` | Blocked by every prior Auth task, final A2-SECURITY review, unresolved machine publication attribution through `AUTH-DEP-008`, and unresolved end-to-end delivery idempotency. |

Auth identity persistence is `VERIFIED_COMPLETE` and merged. Every Auth
runtime area remains `NOT_STARTED` or `PARTIAL`, and Auth runtime remains
`NOT_TESTED`: `tests/auth/` does not exist, so the
**AUTH-SPECIFIC TEST SUITE is `NOT_STARTED` / `NOT_TESTED`**. Database
constraint tests prove schema semantics only and are not evidence of Auth
runtime behavior.

No task above is marked ready on assumption. `AUTH-002` contract and design is
**drafted and twice corrected, not accepted**. Applying A2-AUTH corrections is
not A2-AUTH acceptance, and a second correction round does not make the first
accepted. Drafting a contract is not acceptance, is not
implementation readiness, and is not implementation authorization. No runtime
task is marked ready because a contract was drafted: `AUTH-003` is
`NOT_AUTHORIZED`, and `AUTH-004` through `AUTH-008` retain every sequential,
Security, Workflow, Backend and runtime prerequisite listed above.

`UI-004` is not authorized by `CONTRACT-AUTH-001@1.1.0-draft.1`. The contract
defines the semantics a future, separately authorized `UI-004` may consume; it
grants no UI implementation authority, and `A2-UI` has not reviewed it.
