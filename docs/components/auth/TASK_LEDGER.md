# Auth Task Ledger

- Date: 2026-08-03
- Current task: `AUTH-DEPENDENCY-RECONCILIATION-001-C1`
- Parent task: `AUTH-DEPENDENCY-RECONCILIATION-001-A3`
- Prompt type: `A2_AUTH_ACCEPTANCE_CORRECTION_COMMIT_AND_PUSH`
- Scope: `AUTH_DOCUMENTATION_CORRECTION_FINALIZATION_COMMIT_AND_PUSH`
- Base commit: `fc549fa1a4c77f4835acefbb4f937c35ad6e8f76`
- Worktree: `/Users/omkar/Documents/TestGap-Miner-wt-auth-dependency-reconciliation`
- Branch: `agent2/auth-dependency-reconciliation`
- `CONTRACT-AUTH-001@1.0.0-draft.2`: `ACKNOWLEDGED_AND_MERGED`
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
| `AUTH-DEPENDENCY-RECONCILIATION-001-A3` — Post-dependency-merge durable reconciliation | `PASS / VERIFIED_COMPLETE / A2_AUTH_ACCEPTED / PENDING_MERGE` | Auth-owned durable records reconciled with merged `AUTH-DEP-004` (PR #20, merge commit `fc549fa`) and `AUTH-DEP-010` (PR #19) evidence. Documentation only: no Auth implementation, test, contract, or configuration change. |
| `AUTH-002` — Dashboard sign-in and session contract | `READY_FOR_CONTRACT_AND_DESIGN / IMPLEMENTATION_NOT_AUTHORIZED` | Direct dependencies satisfied: `AUTH-DEP-004` `SATISFIED_FOR_CONTRACT_AND_DESIGN`; `AUTH-DEP-010` `SATISFIED_FOR_OWNERSHIP_AND_COORDINATION`. Contract/design may begin only as a separate, newly authorized A2-AUTH task. Runtime implementation `NOT_AUTHORIZED`; frontend implementation `NOT_AUTHORIZED`; provider runtime `NOT_PROVISIONED / NOT_TESTED`. `AUTH-DEP-006` and `AUTH-DEP-009` remain non-`AUTH-002` dependencies. See `AUTH-001_AUDIT.md` §13. |
| `AUTH-003` — Backend JWT validation and user context | `NOT_AUTHORIZED` | Still requires sequential `AUTH-002` design work and Backend JWT/runtime coordination through `AUTH-DEP-006` (no route surface; no JWT/JWKS dependency in `apps/api/pyproject.toml`). `AUTH-DEP-004` acceptance supplies issuer, audience, and JWKS as accepted design values only, not as a provisioned runtime. |
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

No task above is marked ready on assumption. `AUTH-002` is ready for
**contract and design only** because `AUTH-DEP-004` and `AUTH-DEP-010` are
accepted, acknowledged and merged. No runtime task is marked ready merely
because those two dependencies were accepted: `AUTH-003` is `NOT_AUTHORIZED`,
and `AUTH-004` through `AUTH-008` retain every sequential, Security, Workflow,
Backend and runtime prerequisite listed above.
