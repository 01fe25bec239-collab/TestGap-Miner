# Auth Dependency Requests

- Current task: `AUTH-DB002-CONTRACT-001`
- Scope: `DOCUMENTATION_ONLY`
- Evidence baseline: `739a331c9942ed64a1ad8276d611889bbee53a27`
- Auth implementation: `NOT_STARTED`
- Auth runtime: `NOT_TESTED`

## `DB-DEP-001` — Incoming Auth context request

- Requester: `A2-DATABASE`
- Owner: `A2-AUTH`
- Status: `ADDRESSED_PENDING_ACKNOWLEDGEMENT`
- Response: `CONTRACT-AUTH-001` version `1.0.0-draft.1` supplies canonical
  identity, installation, repository, exact access-scope, actor, lifecycle, and
  secret-exclusion semantics for DB-002.
- Remaining condition: A2-DATABASE consumer acknowledgement.

## `AUTH-DEP-001` — Database consumer acknowledgement

- Requested from: `A2-DATABASE`
- Status: `PENDING`
- Request: confirm that the conceptual records and guarantees fully answer
  DB-002's Auth dependency while preserving Database ownership of physical
  implementation.

## `AUTH-DEP-002` — Workflow actor compatibility

- Requested from: `A2-AGENT-WORKFLOW`
- Status: `PENDING`
- Request: confirm `CONTRACT-WORKFLOW-001` event attribution supports the four
  canonical actor types and traceable `PUBLICATION_EXECUTE` triggers.

## `AUTH-DEP-003` — Shared-registry correction

- Requested from: `A2-INTEGRATION` / Agent 1
- Status: `PENDING`
- Request: add A2-DATABASE as a blocking `CONTRACT-AUTH-001` consumer. Auth
  does not edit the shared registry.

## `AUTH-DEP-004` — Identity-provider runtime metadata

- Requested from: `A2-DEPLOYMENT`
- Status: `PENDING`
- Request: publish the owned runtime boundary for issuer, audience, callback,
  and secret injection without exposing secret values.

## `AUTH-DEP-005` — Security lifecycle and event guidance

- Requested from: `A2-SECURITY`
- Status: `PENDING`
- Request: freeze authorization freshness expectations, retention durations,
  security-event shapes, and redaction requirements.

DB-002 remains blocked until the Auth and Workflow contracts are accepted. No
dependency request authorizes code, tests, or Database implementation.
