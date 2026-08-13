from __future__ import annotations

import os
import re
import uuid
from collections.abc import Iterator
from dataclasses import fields, is_dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.config import validate_test_database_url
from app.db.models import (
    Repository,
    Run,
    RunEvent,
    RunRequest,
    WorkflowStep,
    WorkflowStepAttempt,
)
from app.services.control_plane import (
    LookupStatus,
    RunCursor,
    RunListQuery,
    RunQueryError,
    RunQueryErrorCode,
    get_run_detail,
    get_workflow_timeline,
    list_runs,
)


ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = ROOT / "apps/api/alembic.ini"
NOW = datetime(2026, 8, 13, 10, 30, tzinfo=UTC)


class _FailingSession:
    def execute(self, statement: object) -> None:
        raise SQLAlchemyError("database detail must not escape")


class _UnexpectedSession:
    def execute(self, statement: object) -> None:
        raise AssertionError("invalid input must be rejected before database access")


def _test_database_url() -> str:
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is unavailable")
    return validate_test_database_url(url, os.getenv("DATABASE_URL"))


@pytest.fixture(scope="module")
def query_engine() -> Iterator[Engine]:
    test_url = _test_database_url()
    migration_url = os.getenv("MIGRATION_DATABASE_URL")
    if not migration_url:
        pytest.skip("MIGRATION_DATABASE_URL is unavailable")
    migration_url = (
        make_url(migration_url)
        .set(database=make_url(test_url).database)
        .render_as_string(hide_password=False)
    )
    previous = os.environ.get("MIGRATION_DATABASE_URL")
    os.environ["MIGRATION_DATABASE_URL"] = migration_url
    config = Config(str(ALEMBIC_INI))
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    engine = create_engine(test_url)
    try:
        yield engine
    finally:
        engine.dispose()
        command.downgrade(config, "base")
        if previous is None:
            del os.environ["MIGRATION_DATABASE_URL"]
        else:
            os.environ["MIGRATION_DATABASE_URL"] = previous


@pytest.fixture
def query_session(query_engine: Engine) -> Iterator[Session]:
    with query_engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
            yield db
        transaction.rollback()


def _persist_run(
    session: Session,
    *,
    run_id: uuid.UUID,
    created_at: datetime,
    repository: Repository | None = None,
) -> Run:
    request = RunRequest(
        request_kind="BENCHMARK",
        idempotency_key=run_id.hex,
        idempotency_key_version=1,
        request_fingerprint=run_id.hex,
        benchmark_project_id="Lang",
        benchmark_bug_id=run_id.hex,
        configuration_version="cfg-1",
        model_id="model-1",
        prompt_template_version="prompt-1",
        repository=repository,
    )
    run = Run(
        id=run_id,
        run_request=request,
        state="RECEIVED",
        contract_version="1.0.0-draft.1",
        review_required=True,
        retry_limit=2,
        created_at=created_at,
        updated_at=created_at,
    )
    session.add(run)
    session.flush()
    return run


def _persist_event(
    session: Session,
    run: Run,
    *,
    sequence: int,
    occurred_at: datetime,
    step: WorkflowStep | None = None,
    attempt_index: int | None = None,
) -> RunEvent:
    event_id = uuid.UUID(int=1000 + sequence)
    event = RunEvent(
        id=event_id,
        run_id=run.id,
        sequence=sequence,
        event_type="CHECKPOINT_COMMITTED",
        step_id=step.id if step else None,
        step_kind=step.kind if step else None,
        attempt_index=attempt_index,
        actor_type="WORKFLOW",
        actor_id="workflow-runtime",
        occurred_at=occurred_at,
        recorded_at=occurred_at + timedelta(seconds=1),
        producer_event_id=event_id.hex,
        contract_version="1.0.0-draft.1",
        payload_schema_version="1",
        payload={},
        producer_event_fingerprint=event_id.hex,
        producer_event_fingerprint_version=1,
    )
    session.add(event)
    return event


def test_persisted_run_list_is_ordered_scoped_and_keyset_paginated(
    query_session: Session,
) -> None:
    repository_a = Repository(github_repository_id=91001)
    repository_b = Repository(github_repository_id=91002)
    query_session.add_all([repository_a, repository_b])
    query_session.flush()

    expected_ids = [
        uuid.UUID(int=101),
        uuid.UUID(int=104),
        uuid.UUID(int=103),
        uuid.UUID(int=102),
    ]
    timestamps = [
        NOW + timedelta(seconds=1),
        NOW,
        NOW,
        NOW - timedelta(seconds=1),
    ]
    for run_id, created_at in reversed(list(zip(expected_ids, timestamps))):
        _persist_run(
            query_session,
            run_id=run_id,
            created_at=created_at,
            repository=repository_a,
        )
    other_repository_run = uuid.UUID(int=999)
    _persist_run(
        query_session,
        run_id=other_repository_run,
        created_at=NOW + timedelta(days=1),
        repository=repository_b,
    )

    first = list_runs(
        query_session, RunListQuery(limit=2, repository_id=repository_a.id)
    )
    second = list_runs(
        query_session,
        RunListQuery(
            limit=2,
            repository_id=repository_a.id,
            cursor=first.next_cursor,
        ),
    )
    traversed_ids = [item.id for page in (first, second) for item in page.items]

    assert [item.id for item in first.items] == expected_ids[:2]
    assert [item.id for item in second.items] == expected_ids[2:]
    assert traversed_ids == expected_ids
    assert len(traversed_ids) == len(set(traversed_ids))
    assert other_repository_run not in traversed_ids
    assert all(
        item.repository_id == repository_a.id
        for page in (first, second)
        for item in page.items
    )
    assert first.limit == second.limit == 2
    assert first.has_more is True
    assert first.next_cursor == RunCursor(
        first.items[-1].created_at, first.items[-1].id
    )
    assert second.has_more is False
    assert second.next_cursor is None
    _assert_projection_only(first)


def test_persisted_run_list_empty_page_and_detail_outcomes(
    query_session: Session,
) -> None:
    run = _persist_run(
        query_session,
        run_id=uuid.UUID(int=201),
        created_at=NOW,
    )

    empty = list_runs(
        query_session,
        RunListQuery(limit=7, repository_id=uuid.UUID(int=123456)),
    )
    found = get_run_detail(query_session, run.id)
    missing = get_run_detail(query_session, uuid.UUID(int=202))

    assert empty.items == ()
    assert empty.limit == 7
    assert empty.has_more is False
    assert empty.next_cursor is None
    assert found.status == LookupStatus.FOUND
    assert found.run is not None
    assert found.run.id == run.id
    assert found.run.run_request_id == run.run_request_id
    assert found.run.id != found.run.run_request_id
    assert found.run.repository_id is None
    assert found.run.created_at == NOW
    assert found.run.updated_at == NOW
    assert found.run.terminal_at is None
    assert found.run.failure_code is None
    assert missing.status == LookupStatus.NOT_FOUND
    assert missing.run is None


def test_persisted_timeline_uses_sequence_and_deterministic_child_order(
    query_session: Session,
) -> None:
    run = _persist_run(
        query_session,
        run_id=uuid.UUID(int=301),
        created_at=NOW,
    )
    execute_step = WorkflowStep(
        id=uuid.UUID(int=401),
        run_id=run.id,
        kind="EXECUTE_BUGGY",
        occurrence=1,
        created_at=NOW + timedelta(seconds=3),
        input_reference="input://execute",
        input_version="execute-v1",
    )
    plan_second = WorkflowStep(
        id=uuid.UUID(int=403),
        run_id=run.id,
        kind="PLAN",
        occurrence=2,
        created_at=NOW,
        input_reference="input://plan/2",
        input_version="plan-v2",
    )
    plan_first = WorkflowStep(
        id=uuid.UUID(int=402),
        run_id=run.id,
        kind="PLAN",
        occurrence=1,
        created_at=NOW + timedelta(seconds=4),
        input_reference="input://plan/1",
        input_version="plan-v1",
    )
    query_session.add_all([plan_second, plan_first, execute_step])
    query_session.flush()

    execute_retry = WorkflowStepAttempt(
        id=uuid.UUID(int=503),
        step_id=execute_step.id,
        attempt_index=1,
        started_at=NOW + timedelta(seconds=2),
        actor_type="WORKER",
        actor_id="worker-2",
    )
    plan_attempt = WorkflowStepAttempt(
        id=uuid.UUID(int=502),
        step_id=plan_first.id,
        attempt_index=0,
        started_at=NOW,
        actor_type="WORKER",
        actor_id="worker-1",
    )
    execute_first = WorkflowStepAttempt(
        id=uuid.UUID(int=501),
        step_id=execute_step.id,
        attempt_index=0,
        started_at=NOW + timedelta(seconds=3),
        actor_type="WORKER",
        actor_id="worker-1",
    )
    query_session.add_all([execute_retry, plan_attempt, execute_first])
    query_session.flush()

    events = [
        _persist_event(
            query_session,
            run,
            sequence=3,
            occurred_at=NOW + timedelta(hours=1),
        ),
        _persist_event(
            query_session,
            run,
            sequence=1,
            occurred_at=NOW + timedelta(days=1),
        ),
        _persist_event(
            query_session,
            run,
            sequence=2,
            occurred_at=NOW - timedelta(days=1),
            step=execute_step,
            attempt_index=0,
        ),
    ]
    query_session.flush()

    result = get_workflow_timeline(query_session, run.id)

    assert result.status == LookupStatus.FOUND
    assert result.timeline is not None
    assert [step.id for step in result.timeline.steps] == [
        execute_step.id,
        plan_first.id,
        plan_second.id,
    ]
    assert [attempt.id for attempt in result.timeline.attempts] == [
        execute_first.id,
        execute_retry.id,
        plan_attempt.id,
    ]
    assert [event.sequence for event in result.timeline.events] == [1, 2, 3]
    assert [event.id for event in result.timeline.events] == [
        events[1].id,
        events[2].id,
        events[0].id,
    ]
    assert [event.occurred_at for event in result.timeline.events] != sorted(
        event.occurred_at for event in result.timeline.events
    )
    assert result.timeline.events[1].step_id == execute_step.id
    assert result.timeline.events[1].attempt_index == 0
    _assert_projection_only(result)


def test_persisted_timeline_not_found_is_explicit(query_session: Session) -> None:
    result = get_workflow_timeline(query_session, uuid.UUID(int=999999))

    assert result.status == LookupStatus.NOT_FOUND
    assert result.timeline is None


@pytest.mark.parametrize("limit", [True, 0, -1, 101])
def test_invalid_limit_is_explicit(limit: int) -> None:
    with pytest.raises(RunQueryError) as raised:
        RunListQuery(limit=limit)

    assert raised.value.code == RunQueryErrorCode.INVALID_QUERY


@pytest.mark.parametrize(
    ("created_at", "run_id"),
    [("not-a-datetime", uuid.uuid4()), (NOW, "not-a-uuid")],
)
def test_malformed_cursor_is_explicit(created_at: object, run_id: object) -> None:
    with pytest.raises(RunQueryError) as raised:
        RunCursor(created_at, run_id)  # type: ignore[arg-type]

    assert raised.value.code == RunQueryErrorCode.INVALID_QUERY


def test_invalid_cursor_repository_and_query_objects_are_explicit() -> None:
    for construct in (
        lambda: RunListQuery(cursor=object()),
        lambda: RunListQuery(repository_id="not-a-uuid"),
        lambda: list_runs(_UnexpectedSession(), object()),
    ):
        with pytest.raises(RunQueryError) as raised:
            construct()  # type: ignore[arg-type]
        assert raised.value.code == RunQueryErrorCode.INVALID_QUERY


@pytest.mark.parametrize("lookup", [get_run_detail, get_workflow_timeline])
def test_invalid_run_id_is_explicit(lookup: object) -> None:
    with pytest.raises(RunQueryError) as raised:
        lookup(_UnexpectedSession(), "not-a-uuid")  # type: ignore[operator]

    assert raised.value.code == RunQueryErrorCode.INVALID_QUERY


def test_secret_bearing_persistence_fields_are_absent_from_projections() -> None:
    from app.services.control_plane import (
        RunEventProjection,
        RunProjection,
        WorkflowAttemptProjection,
        WorkflowStepProjection,
    )

    names = {
        field.name
        for projection in (
            RunProjection,
            WorkflowStepProjection,
            WorkflowAttemptProjection,
            RunEventProjection,
        )
        for field in fields(projection)
    }

    assert not names & {
        "actor_id",
        "checkpoint_ref",
        "error_reference",
        "evidence_reference",
        "input_reference",
        "model_id",
        "payload",
        "producer_event_fingerprint",
        "producer_event_id",
        "prompt_template_version",
        "request_fingerprint",
    }
    assert not any(
        re.search(r"password|secret|token|credential", name) for name in names
    )


def test_unavailable_session_and_persisted_inconsistency_are_explicit() -> None:
    with pytest.raises(RunQueryError) as unavailable:
        list_runs(None)
    assert unavailable.value.code == RunQueryErrorCode.DEPENDENCY_UNAVAILABLE

    with pytest.raises(RunQueryError) as query_failure:
        list_runs(_FailingSession())  # type: ignore[arg-type]
    assert query_failure.value.code == RunQueryErrorCode.DEPENDENCY_UNAVAILABLE
    assert "database detail" not in str(query_failure.value)


def _assert_projection_only(value: object) -> None:
    if is_dataclass(value) and not isinstance(value, type):
        assert not type(value).__module__.startswith("app.db.models")
        for field in fields(value):
            _assert_projection_only(getattr(value, field.name))
    elif isinstance(value, (tuple, list)):
        for item in value:
            _assert_projection_only(item)
    else:
        assert isinstance(
            value,
            (str, int, bool, datetime, uuid.UUID, Enum, type(None)),
        )
