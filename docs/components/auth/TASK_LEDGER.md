# Auth Task Ledger

- Current task: `AUTH-DB002-CONTRACT-001`
- Scope: `DOCUMENTATION_ONLY`
- Evidence baseline: `739a331c9942ed64a1ad8276d611889bbee53a27`
- Worktree: `/Users/omkar/Documents/TestGap-Miner-wt-auth-contract`
- Branch: `agent2/auth-contract-db002`

| Task | Status | Evidence / blocker |
|---|---|---|
| `AUTH-DB002-CONTRACT-001` — Publish DB-002 Auth contract and records | `ACTIVE` | `CONTRACT-AUTH-001` `1.0.0-draft.1` and six records authored; pending A2-AUTH review and A2-DATABASE acknowledgement. |
| `AUTH-001` — Auth repository/runtime reconciliation | `NOT_STARTED` | No implementation work authorized. |
| `AUTH-002` — Human identity implementation | `BLOCKED` | Requires accepted Auth contract and Database implementation boundary. |
| `AUTH-003` — External subject authentication | `BLOCKED` | Provider runtime metadata is not frozen. |
| `AUTH-004` — GitHub App installation authentication | `BLOCKED` | Runtime token behavior is outside this documentation task. |
| `AUTH-005` — Repository authorization enforcement | `BLOCKED` | Requires persistence and Backend integration. |
| `AUTH-006` — Actor attribution integration | `BLOCKED` | Awaits `CONTRACT-WORKFLOW-001` and Security event guidance. |
| `AUTH-007` — Lifecycle and revocation enforcement | `BLOCKED` | Freshness and retention rules are not frozen. |
| `AUTH-008` — Auth acceptance and consumer handoff | `BLOCKED` | Requires implementation, runtime tests, and consumer acknowledgements. |

Only the current documentation task is active. Auth implementation is missing,
Auth runtime is `NOT_TESTED`, and no code or test work occurred. DB-002 remains
blocked until the Auth and Workflow contracts are accepted.
