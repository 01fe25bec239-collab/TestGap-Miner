"""Read-only typed projections over persisted run and Workflow data."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

import sqlalchemy as sa
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql import Executable

from app.db.models import Run, RunEvent, RunRequest, WorkflowStep, WorkflowStepAttempt
from app.workflow import ActorType, RequestKind, RunState, WorkflowStepKind


MAX_RUN_PAGE_SIZE = 100


class RunQueryErrorCode(StrEnum):
    INVALID_QUERY = "INVALID_QUERY"
    DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"
    PERSISTENCE_INCONSISTENCY = "PERSISTENCE_INCONSISTENCY"


class RunQueryError(RuntimeError):
    """Safe internal query failure with a stable machine-readable code."""

    def __init__(self, code: RunQueryErrorCode, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code.value}: {detail}")


class LookupStatus(StrEnum):
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"


@dataclass(frozen=True, slots=True)
class RunCursor:
    created_at: datetime
    run_id: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.created_at, datetime) or not isinstance(
            self.run_id, uuid.UUID
        ):
            _invalid("cursor requires a datetime and UUID")


@dataclass(frozen=True, slots=True)
class RunListQuery:
    limit: int = 50
    cursor: RunCursor | None = None
    repository_id: uuid.UUID | None = None

    def __post_init__(self) -> None:
        if type(self.limit) is not int or not 1 <= self.limit <= MAX_RUN_PAGE_SIZE:
            _invalid(f"limit must be between 1 and {MAX_RUN_PAGE_SIZE}")
        if self.cursor is not None and not isinstance(self.cursor, RunCursor):
            _invalid("cursor must be a RunCursor")
        if self.repository_id is not None and not isinstance(
            self.repository_id, uuid.UUID
        ):
            _invalid("repository_id must be a UUID")


@dataclass(frozen=True, slots=True)
class RunProjection:
    id: uuid.UUID
    run_request_id: uuid.UUID
    repository_id: uuid.UUID | None
    request_kind: RequestKind
    state: RunState
    contract_version: str
    review_required: bool
    created_at: datetime
    updated_at: datetime
    terminal_at: datetime | None
    failure_code: str | None
    abstention_code: str | None
    cancellation_code: str | None


@dataclass(frozen=True, slots=True)
class RunPage:
    items: tuple[RunProjection, ...]
    limit: int
    has_more: bool
    next_cursor: RunCursor | None


@dataclass(frozen=True, slots=True)
class RunDetailResult:
    status: LookupStatus
    run: RunProjection | None = None


@dataclass(frozen=True, slots=True)
class WorkflowStepProjection:
    id: uuid.UUID
    run_id: uuid.UUID
    kind: WorkflowStepKind
    occurrence: int
    created_at: datetime
    input_version: str


@dataclass(frozen=True, slots=True)
class WorkflowAttemptProjection:
    id: uuid.UUID
    step_id: uuid.UUID
    attempt_index: int
    started_at: datetime
    ended_at: datetime | None
    outcome: str | None
    actor_type: ActorType


@dataclass(frozen=True, slots=True)
class RunEventProjection:
    id: uuid.UUID
    run_id: uuid.UUID
    sequence: int
    event_type: str
    from_state: RunState | None
    to_state: RunState | None
    step_id: uuid.UUID | None
    step_kind: WorkflowStepKind | None
    attempt_index: int | None
    actor_type: ActorType
    occurred_at: datetime
    recorded_at: datetime
    causation_event_id: uuid.UUID | None
    contract_version: str
    payload_schema_version: str
    failure_code: str | None
    abstention_code: str | None
    cancellation_code: str | None


@dataclass(frozen=True, slots=True)
class WorkflowTimeline:
    run_id: uuid.UUID
    steps: tuple[WorkflowStepProjection, ...]
    attempts: tuple[WorkflowAttemptProjection, ...]
    events: tuple[RunEventProjection, ...]


@dataclass(frozen=True, slots=True)
class WorkflowTimelineResult:
    status: LookupStatus
    timeline: WorkflowTimeline | None = None


_RUN_COLUMNS = (
    Run.id.label("id"),
    Run.run_request_id.label("run_request_id"),
    RunRequest.repository_id.label("repository_id"),
    RunRequest.request_kind.label("request_kind"),
    Run.state.label("state"),
    Run.contract_version.label("contract_version"),
    Run.review_required.label("review_required"),
    Run.created_at.label("created_at"),
    Run.updated_at.label("updated_at"),
    Run.terminal_at.label("terminal_at"),
    Run.failure_code.label("failure_code"),
    Run.abstention_code.label("abstention_code"),
    Run.cancellation_code.label("cancellation_code"),
)


def list_runs(session: Session | None, query: RunListQuery = RunListQuery()) -> RunPage:
    """Return one deterministic, bounded keyset page without ORM instances."""

    _require_session(session)
    if not isinstance(query, RunListQuery):
        _invalid("query must be a RunListQuery")
    statement = sa.select(*_RUN_COLUMNS).join(
        RunRequest, Run.run_request_id == RunRequest.id
    )
    if query.repository_id is not None:
        statement = statement.where(RunRequest.repository_id == query.repository_id)
    if query.cursor is not None:
        statement = statement.where(
            sa.tuple_(Run.created_at, Run.id)
            < (query.cursor.created_at, query.cursor.run_id)
        )
    statement = statement.order_by(Run.created_at.desc(), Run.id.desc()).limit(
        query.limit + 1
    )
    rows = _mappings(session, statement)
    has_more = len(rows) > query.limit
    items = tuple(_run_projection(row) for row in rows[: query.limit])
    next_cursor = (
        RunCursor(items[-1].created_at, items[-1].id) if has_more else None
    )
    return RunPage(items, query.limit, has_more, next_cursor)


def get_run_detail(session: Session | None, run_id: uuid.UUID) -> RunDetailResult:
    """Look up one canonical run UUID and return an explicit outcome."""

    _require_session(session)
    _require_run_id(run_id)
    rows = _mappings(
        session,
        sa.select(*_RUN_COLUMNS)
        .join(RunRequest, Run.run_request_id == RunRequest.id)
        .where(Run.id == run_id),
    )
    if not rows:
        return RunDetailResult(LookupStatus.NOT_FOUND)
    if len(rows) != 1:
        _inconsistent("run detail query returned multiple rows")
    return RunDetailResult(LookupStatus.FOUND, _run_projection(rows[0]))


def get_workflow_timeline(
    session: Session | None, run_id: uuid.UUID
) -> WorkflowTimelineResult:
    """Read DB-003 steps, attempts, and events without synthesizing history."""

    _require_session(session)
    _require_run_id(run_id)
    exists = _mappings(
        session, sa.select(Run.id.label("id")).where(Run.id == run_id)
    )
    if not exists:
        return WorkflowTimelineResult(LookupStatus.NOT_FOUND)
    if len(exists) != 1:
        _inconsistent("run existence query returned multiple rows")

    step_rows = _mappings(
        session,
        sa.select(
            WorkflowStep.id.label("id"),
            WorkflowStep.run_id.label("run_id"),
            WorkflowStep.kind.label("kind"),
            WorkflowStep.occurrence.label("occurrence"),
            WorkflowStep.created_at.label("created_at"),
            WorkflowStep.input_version.label("input_version"),
        )
        .where(WorkflowStep.run_id == run_id)
        .order_by(WorkflowStep.kind, WorkflowStep.occurrence, WorkflowStep.id),
    )
    attempt_rows = _mappings(
        session,
        sa.select(
            WorkflowStepAttempt.id.label("id"),
            WorkflowStepAttempt.step_id.label("step_id"),
            WorkflowStepAttempt.attempt_index.label("attempt_index"),
            WorkflowStepAttempt.started_at.label("started_at"),
            WorkflowStepAttempt.ended_at.label("ended_at"),
            WorkflowStepAttempt.outcome.label("outcome"),
            WorkflowStepAttempt.actor_type.label("actor_type"),
        )
        .join(WorkflowStep, WorkflowStepAttempt.step_id == WorkflowStep.id)
        .where(WorkflowStep.run_id == run_id)
        .order_by(
            WorkflowStep.kind,
            WorkflowStep.occurrence,
            WorkflowStepAttempt.attempt_index,
            WorkflowStepAttempt.id,
        ),
    )
    event_rows = _mappings(
        session,
        sa.select(
            RunEvent.id.label("id"),
            RunEvent.run_id.label("run_id"),
            RunEvent.sequence.label("sequence"),
            RunEvent.event_type.label("event_type"),
            RunEvent.from_state.label("from_state"),
            RunEvent.to_state.label("to_state"),
            RunEvent.step_id.label("step_id"),
            RunEvent.step_kind.label("step_kind"),
            RunEvent.attempt_index.label("attempt_index"),
            RunEvent.actor_type.label("actor_type"),
            RunEvent.occurred_at.label("occurred_at"),
            RunEvent.recorded_at.label("recorded_at"),
            RunEvent.causation_event_id.label("causation_event_id"),
            RunEvent.contract_version.label("contract_version"),
            RunEvent.payload_schema_version.label("payload_schema_version"),
            RunEvent.failure_code.label("failure_code"),
            RunEvent.abstention_code.label("abstention_code"),
            RunEvent.cancellation_code.label("cancellation_code"),
        )
        .where(RunEvent.run_id == run_id)
        .order_by(RunEvent.sequence),
    )

    try:
        steps = tuple(
            WorkflowStepProjection(
                row["id"],
                row["run_id"],
                WorkflowStepKind(row["kind"]),
                row["occurrence"],
                row["created_at"],
                row["input_version"],
            )
            for row in step_rows
        )
        attempts = tuple(
            WorkflowAttemptProjection(
                row["id"],
                row["step_id"],
                row["attempt_index"],
                row["started_at"],
                row["ended_at"],
                row["outcome"],
                ActorType(row["actor_type"]),
            )
            for row in attempt_rows
        )
        events = tuple(_event_projection(row) for row in event_rows)
    except (TypeError, ValueError, KeyError):
        _inconsistent("persisted timeline contains an invalid value")

    _validate_timeline(run_id, steps, attempts, events)
    return WorkflowTimelineResult(
        LookupStatus.FOUND, WorkflowTimeline(run_id, steps, attempts, events)
    )


def _run_projection(row: RowMapping) -> RunProjection:
    try:
        return RunProjection(
            row["id"],
            row["run_request_id"],
            row["repository_id"],
            RequestKind(row["request_kind"]),
            RunState(row["state"]),
            row["contract_version"],
            row["review_required"],
            row["created_at"],
            row["updated_at"],
            row["terminal_at"],
            row["failure_code"],
            row["abstention_code"],
            row["cancellation_code"],
        )
    except (TypeError, ValueError, KeyError):
        _inconsistent("persisted run contains an invalid value")


def _event_projection(row: RowMapping) -> RunEventProjection:
    return RunEventProjection(
        row["id"],
        row["run_id"],
        row["sequence"],
        row["event_type"],
        RunState(row["from_state"]) if row["from_state"] is not None else None,
        RunState(row["to_state"]) if row["to_state"] is not None else None,
        row["step_id"],
        WorkflowStepKind(row["step_kind"])
        if row["step_kind"] is not None
        else None,
        row["attempt_index"],
        ActorType(row["actor_type"]),
        row["occurred_at"],
        row["recorded_at"],
        row["causation_event_id"],
        row["contract_version"],
        row["payload_schema_version"],
        row["failure_code"],
        row["abstention_code"],
        row["cancellation_code"],
    )


def _validate_timeline(
    run_id: uuid.UUID,
    steps: tuple[WorkflowStepProjection, ...],
    attempts: tuple[WorkflowAttemptProjection, ...],
    events: tuple[RunEventProjection, ...],
) -> None:
    step_kinds = {step.id: step.kind for step in steps}
    attempt_keys = {(attempt.step_id, attempt.attempt_index) for attempt in attempts}
    if any(step.run_id != run_id for step in steps) or any(
        attempt.step_id not in step_kinds for attempt in attempts
    ):
        _inconsistent("persisted timeline contains a cross-run step or attempt")
    previous_sequence = 0
    for event in events:
        if event.run_id != run_id or event.sequence <= previous_sequence:
            _inconsistent("persisted event sequence is not strictly increasing")
        previous_sequence = event.sequence
        if (
            event.step_id is not None
            and step_kinds.get(event.step_id) != event.step_kind
        ):
            _inconsistent("persisted event step attribution is inconsistent")
        if event.attempt_index is not None and (
            event.step_id,
            event.attempt_index,
        ) not in attempt_keys:
            _inconsistent("persisted event attempt attribution is inconsistent")


def _mappings(session: Session, statement: Executable) -> list[RowMapping]:
    try:
        return list(session.execute(statement).mappings().all())
    except SQLAlchemyError:
        raise RunQueryError(
            RunQueryErrorCode.DEPENDENCY_UNAVAILABLE,
            "database query dependency is unavailable",
        ) from None


def _require_session(session: Session | None) -> None:
    if session is None:
        raise RunQueryError(
            RunQueryErrorCode.DEPENDENCY_UNAVAILABLE,
            "database session is unavailable",
        )


def _require_run_id(run_id: uuid.UUID) -> None:
    if not isinstance(run_id, uuid.UUID):
        _invalid("run_id must be a UUID")


def _invalid(detail: str) -> None:
    raise RunQueryError(RunQueryErrorCode.INVALID_QUERY, detail)


def _inconsistent(detail: str) -> None:
    raise RunQueryError(RunQueryErrorCode.PERSISTENCE_INCONSISTENCY, detail)
