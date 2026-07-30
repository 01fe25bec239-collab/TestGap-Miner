# Agent Workflow Component Status

- Date: 2026-07-31
- Branch: `agent2/agent-workflow-contract-db002`
- Task: `AGW-DB002-CONTRACT-001-C2`
- Prompt type: `BUG_FIX`
- Contract: `CONTRACT-WORKFLOW-001@1.0.0-draft.1`
- Contract status: `DRAFT_COMPLETE — PENDING_A2_DATABASE_ACKNOWLEDGEMENT`
- Component classification: documentation contract `IMPLEMENTED`; runtime
  workflow `NOT_TESTED` and not implemented

## Current result

The versioned workflow lifecycle contract and all six Agent Workflow
management records now exist. The contract defines the canonical 20 states,
allowed transitions, eight immutable terminal states, one automated repair,
DB-002 projections, DB-003 step/event boundaries, ordered append-only events,
checkpoint/resume, retry, codes, cancellation, human review, versioning, and
acceptance fixtures.

The C2 correction keeps buggy execution as the only non-terminal repair
continuation while permitting five safe terminal repair exits. It also limits
`PUBLISHING -> CANCELLED` to the period before an external side effect commits.
The C1 repair sequence, review rules, canonical enumeration, and contract
version remain unchanged.

## Evidence

- Authoritative manager:
  `docs/specifications/A2_DATABASE_MANAGER(1).md`
- Consumer request:
  `docs/components/database/DEPENDENCY_REQUESTS.md`, `DB-DEP-004`
- Contract:
  `docs/components/agent-workflow/CONTRACT-WORKFLOW-001.md`
- Validation evidence and exact results:
  `docs/components/agent-workflow/LATEST_AGENT3_HANDOFF.md`
- C2 transition-invariant validation: two repair-entry sources, one
  non-terminal continuation, five terminal exits, review-required and
  benchmark completion paths, and late-cancellation rules all passed.
- Original task starting state: clean base
  `739a331c9942ed64a1ad8276d611889bbee53a27` with no Agent Workflow directory.
- C1 and C2 starting state: exactly the seven permitted untracked Markdown
  files under `docs/components/agent-workflow/` and no other changed path.

## Scope boundary

- DB-002: run-request and current-run projections only.
- DB-003: workflow steps, attempts, and ordered events; not implemented here.
- Auth-owned identity fields remain provisional.
- Queue envelope/transport fields remain provisional.
- Evidence and queue contracts were not created.
- No workflow engine, runtime behavior, migration, model, route, test, prompt,
  worker, sandbox, or infrastructure change was made.

## Blockers

- `A2-DATABASE` acknowledgement of this exact version: `BLOCKED`/pending.
- Independent `CONTRACT-AUTH-001` prerequisite for DB-002: `BLOCKED`/pending.
- Runtime implementation and runtime tests: `NOT_TESTED`; outside this task.
- Corrected C2 semantics still require consumer acknowledgement before
  Database implementation.
- No standalone A2 draft artefact was present; `ASSUMED` baseline is the
  manager specification, `DB-DEP-004`, and the issued task requirements.

## Next action

`A2-DATABASE` reviews and acknowledges
`CONTRACT-WORKFLOW-001@1.0.0-draft.1`, records any non-breaking physical naming
mapping, and keeps DB-002 blocked until `CONTRACT-AUTH-001` is also available.

## Explicit labels

- `IMPLEMENTED`: focused C2 correction across the seven documentation files.
- `TESTED`: documentation structure, state/transition invariants, diff scope,
  and whitespace validation.
- `NOT_TESTED`: workflow engine, database persistence, migrations, API,
  queue/worker behavior, and runtime acceptance fixtures.
- `BLOCKED`: A2-DATABASE acknowledgement and independent Auth contract.
- `ASSUMED`: prompt plus repository manager/request records are the substantive
  A2 draft baseline because no separate draft file existed.
