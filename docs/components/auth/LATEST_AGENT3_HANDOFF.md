# Agent 3 Hand-off Record: AUTH-006-FINALIZE-CONTRACT-AUTH-001-V1.2.0-DRAFT.1-001-A3-R2

- Task ID: `AUTH-006-FINALIZE-CONTRACT-AUTH-001-V1.2.0-DRAFT.1-001-A3-R2`
- Authorized manager task: `AUTH-006-FINALIZE-CONTRACT-AUTH-001-V1.2.0-DRAFT.1-001`
- Authorizing coordinator: `Agent 1`
- Supervising manager: `A2-AUTH`
- Date: 2026-08-10
- Task Type: `DOCUMENTATION / CONTRACT FINALIZATION / NO_RUNTIME_IMPLEMENTATION`
- Target Branch: `agent2/auth-contract-1.2-finalization`
- Worktree: `/Users/omkar/Documents/TestGap-Miner-wt-auth-contract-1.2-finalization`
- Baseline: `5ffa8994b286e85d9f676336dbe0169cfbc89d2c`
- Target Contract Version: `CONTRACT-AUTH-001@1.2.0-draft.1`
- Modified Files: Auth-owned durable records under `docs/components/auth/`
- Git Working Tree State: All modifications UNSTAGED and UNCOMMITTED

---

## Executive Summary

`A3-AUTH` has executed the authorized contract finalization review correction task `AUTH-006-FINALIZE-CONTRACT-AUTH-001-V1.2.0-DRAFT.1-001-A3-R2`. This task finalizes `CONTRACT-AUTH-001` to version `1.2.0-draft.1` by incorporating all normative corrections from the accepted `AUTH-005` proposal across all four required consumer domains (`A2-UI`, `A2-SECURITY`, `A2-DEPLOYMENT`, `A2-INTEGRATION`, all `ACCEPTED_WITH_CONSTRAINTS`) along with R1/R2 targeted corrections resolving all A2-AUTH review feedback.

---

## 1. Normative Contract Finalization (`CONTRACT-AUTH-001@1.2.0-draft.1`) & R2 Corrections

1. **PKCE Provider Custody & OAuth State Ownership Preservation**:
   - PKCE remains `REQUIRED`. The PKCE verifier is created and held by the provider integration on the initiating device.
   - Auth code MUST NOT read the PKCE verifier; UI code MUST NOT read the PKCE verifier; Auth/UI MUST NOT copy, transmit, persist, or log the verifier.
   - Provider OAuth state generation and validation remain provider-integration-owned and MUST NOT become an Auth application return-path or correlation payload.
   - Dashboard intended-return state remains a distinct Auth-owned mechanism.
2. **Callback Correlation Record Separation**:
   - Callback-correlation records represent Auth-owned attempt/callback-flow correlation and the existing permitted pending intended-return binding.
   - Provider PKCE-verifier custody and provider OAuth-state generation/validation remain provider-integration-owned and are not transferred into Auth correlation records.
   - Session-binding records instead represent successful session establishment against an Auth context and Auth-context generation.
   - The two record types MUST NOT be merged.
3. **`SIGN_OUT_WINS` Principle**: Physical arrival of stale provider cookie material MUST NEVER qualify as an established or usable Auth session after a newer Auth-context fence exists.
4. **`ESTABLISHED_AUTH_SESSION` Criteria**: Requires ALL of: (1) valid provider session; (2) current Auth context; (3) valid session binding; (4) no active local sign-out tombstone; (5) verified synchronization authority; (6) no newer sign-out generation.
5. **Callback Generation Supersession & Same-Generation Concurrent Sign-In**:
   - A callback MUST fail closed as stale when the Auth-context generation to which its sign-in attempt is bound is no longer the authoritative current generation.
   - A later sign-in attempt does NOT automatically invalidate an earlier independently correlated attempt when both remain bound to the same current Auth-context generation.
   - Concurrent independent sign-in attempts MAY exist under the same current Auth-context generation.
6. **Explicit Sign-Out Tombstone Ordering**:
   - When `AuthAdapter.signOut()` is requested, Auth MUST establish `LOCAL_SIGN_OUT_TOMBSTONE` BEFORE relying on any cross-runtime `PUBLISH_SIGN_OUT` operation or provider sign-out completion.
   - Publication failure leaves tombstone active and Auth signed out locally.
7. **Explicit New Sign-In After Sign-Out Reconciliation**:
   - New sign-in while tombstone is active requires `PREPARE_SIGN_IN` / Auth-context reconciliation. Tombstone removal occurs ONLY after successful reconciliation.
8. **Session-Binding Record Exclusions & Response Fence Non-Mutation**:
   - Binding record MUST NOT contain: access token, refresh token, provider-session bytes, authorization code, PKCE verifier, intended-return path, identity claim, authorization capability.
   - Callback response MUST NOT mutate context handle or active newer tombstone.
9. **Reconciled Auth Test Status**:
   - Auth runtime unit tests: `PRESENT_IN_BASELINE` under `apps/web/src/auth/**` (including `adapter.test.ts`).
   - `tests/auth/`: `ABSENT`.
   - AUTH-005 cross-runtime/browser-network acceptance: `NOT_YET_TESTED / FUTURE_INTEGRATION_REQUIREMENT`. Vitest/jsdom-only proof is INSUFFICIENT for stale HTTP response/browser-cookie ordering acceptance.
10. **Reconciled Auth CSRF / Cookie Status**:
    - Auth-owned CSRF / cookie foundation: `PRESENT_IN_BASELINE` under `apps/web/src/auth/**` (`csrf.ts`).
    - Backend CORS implementation: separately `A2-BACKEND-OWNED`.
    - AUTH-005 session-fence runtime correction: `NOT_YET_AUTHORIZED / NOT_YET_IMPLEMENTED`.
11. **Reconciled Open Issues Impact Wording**:
    - Reconciled `AUTH-ISSUE-001` impact statement to distinguish existing merged browser runtime foundations under `apps/web/src/auth/**` from missing hosted UI integration (`/auth/callback`) and separate incomplete Backend runtime boundaries.

---

## 2. Decisional Audit Trail (`AUTH-DEC-054` .. `AUTH-DEC-067`)

- `AUTH-DEC-054` .. `AUTH-DEC-066`: R1 contract finalization decisions (accepted `AUTH-005` normative corrections, handles, tombstone, UI host boundary, sync authority, integration test requirements, callback generation supersession, tombstone ordering, new sign-in reconciliation, session-binding exclusions).
- `AUTH-DEC-067`: R2 final targeted review corrections: PKCE provider custody & OAuth state ownership preservation, callback correlation record separation, Auth runtime unit test status reconciliation (`PRESENT_IN_BASELINE`), Auth CSRF/cookie foundation reconciliation (`PRESENT_IN_BASELINE`), and OPEN_ISSUES impact wording fix.

---

## 3. Reconciled Runtime Status & Preserved Boundaries

- Existing merged Auth runtime state: Present in baseline `5ffa8994b286e85d9f676336dbe0169cfbc89d2c` under `apps/web/src/auth/**` (including `AuthAdapter`, state machine, correlation, storage boundary, redirect, types, and unit tests).
- `AUTH-006` runtime modification authorization: `NONE / NO_RUNTIME_MODIFICATION_AUTHORIZED` under this task.
- `AUTH-003` / `AUTH-005` fence correction runtime implementation: `NOT_YET_AUTHORIZED / NOT_YET_IMPLEMENTED`.
- Frontend Auth `/auth/callback` route: `NOT_IMPLEMENTED / NOT_AUTHORIZED`
- Backend JWT/JWKS (`apps/api`): `NOT_IMPLEMENTED / NOT_AUTHORIZED`
- Provider runtime: `NOT_PROVISIONED / NOT_TESTED`
- `UI-004`: `NOT_AUTHORIZED`
- `AUTH-003`: `NOT_AUTHORIZED`
- Release readiness: `NOT_READY`

---

## 4. Modified Files Summary

1. `docs/components/auth/CONTRACT-AUTH-001.md` — Replaced defective callback correlation sentence with exact wording establishing PKCE verifier custody & OAuth state verification as provider-integration-owned, distinct from Auth-owned correlation records.
2. `docs/components/auth/COMPONENT_STATUS.md` — Updated metadata, task ID to R2, state table, reconciled Auth test status (`PRESENT_IN_BASELINE`), and Auth CSRF/cookie foundation status (`PRESENT_IN_BASELINE`).
3. `docs/components/auth/DECISION_LOG.md` — Appended decision `AUTH-DEC-067` for R2 final targeted review corrections.
4. `docs/components/auth/DEPENDENCY_REQUESTS.md` — Updated metadata header to task R2.
5. `docs/components/auth/OPEN_ISSUES.md` — Fixed `AUTH-ISSUE-001` impact statement and reconciled `AUTH-ISSUE-010` test status.
6. `docs/components/auth/TASK_LEDGER.md` — Updated metadata header, task ledger entry to R2, and reconciled test status summary.
7. `docs/components/auth/LATEST_AGENT3_HANDOFF.md` — Overwritten to summarize ONLY task `AUTH-006-FINALIZE-CONTRACT-AUTH-001-V1.2.0-DRAFT.1-001-A3-R2`.

---

## 5. Next Action

`A2-AUTH` review of this finalized contract package (`CONTRACT-AUTH-001@1.2.0-draft.1`) across all modified durable records.
