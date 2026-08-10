"""DB-003 workflow-step, attempt, event, and transaction persistence tests."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.db.models import Run, RunEvent, RunRequest, WorkflowStep, WorkflowStepAttempt
from app.db.workflow_persistence import (
    ProducerEventConflictError,
    RunProjectionConflictError,
    append_run_event,
    compare_and_swap_run,
)
from support import (
    DB_003_TABLES,
    assert_rejected,
    make_attempt,
    make_event,
    make_run,
    make_run_request,
    make_step,
)


def _persist_run(session: Session, state: str = "RECEIVED", **overrides: object) -> Run:
    request = make_run_request()
    run = make_run(request, state, **overrides)
    session.add_all([request, run])
    session.flush()
    return run


def _persist_step(session: Session, run: Run, **overrides: object) -> WorkflowStep:
    step = make_step(run, **overrides)
    session.add(step)
    session.flush()
    return step


def test_valid_workflow_step_persists(session: Session) -> None:
    run = _persist_run(session)
    step = _persist_step(session, run, kind="VALIDATE_INPUT")
    session.expire(step)
    assert step.run_id == run.id
    assert step.kind == "VALIDATE_INPUT"
    assert step.occurrence == 1
    assert step.created_at is not None


def test_workflow_step_requires_an_existing_run(session: Session) -> None:
    assert_rejected(
        session,
        WorkflowStep(
            run_id=uuid.uuid4(),
            kind="PLAN",
            occurrence=1,
            input_reference="input://redacted/1",
            input_version="v1",
        ),
    )


def test_unknown_workflow_step_kind_is_rejected(session: Session) -> None:
    run = _persist_run(session)
    assert_rejected(session, make_step(run, kind="QUEUE_WAIT"))


@pytest.mark.parametrize("occurrence", [0, -1])
def test_non_positive_workflow_step_occurrence_is_rejected(
    session: Session, occurrence: int
) -> None:
    run = _persist_run(session)
    assert_rejected(session, make_step(run, occurrence=occurrence))


def test_duplicate_workflow_step_occurrence_is_rejected(session: Session) -> None:
    run = _persist_run(session)
    session.add(make_step(run))
    session.flush()
    assert_rejected(session, make_step(run))


def test_workflow_step_input_binding_is_immutable(session: Session) -> None:
    step = _persist_step(session, _persist_run(session))
    step.input_reference = "input://redacted/rewrite"
    assert_rejected(session, step)


def test_valid_workflow_attempt_persists(session: Session) -> None:
    step = _persist_step(session, _persist_run(session))
    attempt = make_attempt(step)
    session.add(attempt)
    session.flush()
    assert isinstance(attempt.id, uuid.UUID)
    assert attempt.step_id == step.id
    assert attempt.attempt_index == 0


def test_attempt_requires_an_existing_step(session: Session) -> None:
    assert_rejected(
        session,
        WorkflowStepAttempt(
            step_id=uuid.uuid4(),
            attempt_index=0,
            started_at=datetime.now(UTC),
            actor_type="WORKER",
            actor_id="worker-1",
        ),
    )


def test_negative_attempt_index_is_rejected(session: Session) -> None:
    step = _persist_step(session, _persist_run(session))
    assert_rejected(session, make_attempt(step, attempt_index=-1))


def test_duplicate_attempt_index_is_rejected(session: Session) -> None:
    step = _persist_step(session, _persist_run(session))
    session.add(make_attempt(step))
    session.flush()
    assert_rejected(session, make_attempt(step))


def test_attempt_cannot_end_before_it_started(session: Session) -> None:
    step = _persist_step(session, _persist_run(session))
    started_at = datetime.now(UTC)
    assert_rejected(
        session,
        make_attempt(
            step,
            started_at=started_at,
            ended_at=started_at - timedelta(seconds=1),
            outcome="FAILED",
        ),
    )


def test_completed_attempt_requires_an_outcome(session: Session) -> None:
    step = _persist_step(session, _persist_run(session))
    assert_rejected(session, make_attempt(step, ended_at=datetime.now(UTC)))


def test_retry_adds_an_attempt_without_replacing_history_or_repair(
    session: Session,
) -> None:
    run = _persist_run(session)
    request_count = session.scalar(sa.select(sa.func.count()).select_from(RunRequest))
    step = _persist_step(session, run, kind="EXECUTE_BUGGY")
    first = make_attempt(step, attempt_index=0)
    retry = make_attempt(step, attempt_index=1)
    session.add_all([first, retry])
    session.flush()

    attempts = session.scalars(
        sa.select(WorkflowStepAttempt)
        .where(WorkflowStepAttempt.step_id == step.id)
        .order_by(WorkflowStepAttempt.attempt_index)
    ).all()
    assert [attempt.attempt_index for attempt in attempts] == [0, 1]
    assert session.scalar(
        sa.select(sa.func.count()).select_from(RunRequest)
    ) == request_count
    assert run.repair_attempts_used == 0


def test_active_attempt_can_be_completed(session: Session) -> None:
    step = _persist_step(session, _persist_run(session))
    attempt = make_attempt(step)
    session.add(attempt)
    session.flush()
    attempt.ended_at = attempt.started_at + timedelta(seconds=1)
    attempt.outcome = "SUCCEEDED"
    attempt.evidence_reference = "evidence://opaque/1"
    session.flush()
    assert attempt.outcome == "SUCCEEDED"


def test_active_attempt_identity_cannot_be_rewritten(session: Session) -> None:
    step = _persist_step(session, _persist_run(session))
    attempt = make_attempt(step)
    session.add(attempt)
    session.flush()
    attempt.actor_id = "replacement-worker"
    assert_rejected(session, attempt)


def test_completed_attempt_cannot_be_rewritten(session: Session) -> None:
    step = _persist_step(session, _persist_run(session))
    now = datetime.now(UTC)
    attempt = make_attempt(
        step, started_at=now, ended_at=now, outcome="SUCCEEDED"
    )
    session.add(attempt)
    session.flush()
    attempt.outcome = "REPLACED"
    assert_rejected(session, attempt)


def test_completed_attempt_cannot_be_deleted(session: Session) -> None:
    step = _persist_step(session, _persist_run(session))
    now = datetime.now(UTC)
    attempt = make_attempt(
        step, started_at=now, ended_at=now, outcome="SUCCEEDED"
    )
    session.add(attempt)
    session.flush()
    session.delete(attempt)
    with pytest.raises(DBAPIError):
        session.flush()


def test_active_attempt_cannot_be_deleted(session: Session) -> None:
    step = _persist_step(session, _persist_run(session))
    attempt = make_attempt(step)
    session.add(attempt)
    session.flush()
    session.delete(attempt)
    with pytest.raises(DBAPIError):
        session.flush()


def test_event_append_orders_per_run_and_runs_are_independent(session: Session) -> None:
    first_run = _persist_run(session)
    second_run = _persist_run(session)
    first_events = [
        append_run_event(session, make_event(first_run)) for _ in range(3)
    ]
    second_event = append_run_event(session, make_event(second_run))
    assert [event.sequence for event in first_events] == [1, 2, 3]
    assert second_event.sequence == 1


def test_duplicate_event_sequence_is_rejected(session: Session) -> None:
    run = _persist_run(session)
    session.add(make_event(run, sequence=1))
    session.flush()
    assert_rejected(session, make_event(run, sequence=1))


def test_duplicate_producer_event_id_is_rejected_by_storage(session: Session) -> None:
    run = _persist_run(session)
    first = make_event(run, producer_event_id="producer-1")
    session.add(first)
    session.flush()
    assert_rejected(
        session,
        make_event(run, sequence=2, producer_event_id="producer-1"),
    )


def test_producer_event_idempotency_returns_identical_and_rejects_conflict(
    session: Session,
) -> None:
    run = _persist_run(session)
    first = append_run_event(
        session,
        make_event(
            run,
            producer_event_id="stable-event-1",
            producer_event_fingerprint="a" * 64,
            producer_event_fingerprint_version=2,
        ),
    )
    duplicate = append_run_event(
        session,
        make_event(
            run,
            producer_event_id="stable-event-1",
            producer_event_fingerprint="a" * 64,
            producer_event_fingerprint_version=2,
        ),
    )
    assert duplicate.id == first.id
    assert session.scalar(sa.select(sa.func.count()).select_from(RunEvent)) == 1

    with pytest.raises(ProducerEventConflictError):
        append_run_event(
            session,
            make_event(
                run,
                producer_event_id="stable-event-1",
                producer_event_fingerprint="b" * 64,
                producer_event_fingerprint_version=2,
            ),
        )
    assert session.scalar(sa.select(sa.func.count()).select_from(RunEvent)) == 1


@pytest.mark.parametrize(
    ("from_state", "to_state"),
    [
        ("UNKNOWN", "VALIDATING"),
        ("received", "VALIDATING"),
        ("PLANNING", "SCORING"),
        ("RECEIVED", "RECEIVED"),
    ],
)
def test_invalid_transition_history_is_rejected(
    session: Session, from_state: str, to_state: str
) -> None:
    run = _persist_run(session)
    assert_rejected(
        session,
        make_event(
            run,
            event_type="STATE_TRANSITIONED",
            from_state=from_state,
            to_state=to_state,
        ),
    )


def test_valid_frozen_transition_history_is_accepted(session: Session) -> None:
    run = _persist_run(session)
    event = make_event(
        run,
        event_type="STATE_TRANSITIONED",
        from_state="RECEIVED",
        to_state="VALIDATING",
    )
    session.add(event)
    session.flush()
    assert event.to_state == "VALIDATING"


@pytest.mark.parametrize(
    ("from_state", "to_state"),
    [(None, None), ("RECEIVED", None), (None, "VALIDATING")],
)
def test_transition_history_requires_both_states(
    session: Session, from_state: str | None, to_state: str | None
) -> None:
    run = _persist_run(session)
    assert_rejected(
        session,
        make_event(
            run,
            event_type="STATE_TRANSITIONED",
            from_state=from_state,
            to_state=to_state,
        ),
    )


@pytest.mark.parametrize("event_type", ["CHECKPOINT_COMMITTED", "STEP_ATTEMPT_STARTED"])
def test_non_transition_history_prohibits_states(
    session: Session, event_type: str
) -> None:
    run = _persist_run(session)
    assert_rejected(
        session,
        make_event(
            run,
            event_type=event_type,
            from_state="RECEIVED",
            to_state="VALIDATING",
        ),
    )


def test_non_transition_history_without_states_is_accepted(session: Session) -> None:
    run = _persist_run(session)
    event = make_event(run, event_type="CHECKPOINT_COMMITTED")
    session.add(event)
    session.flush()
    assert event.from_state is None and event.to_state is None


@pytest.mark.parametrize("code", ["INPUT_MALFORMED", "INPUT_NEW_REASON"])
def test_failure_history_accepts_published_and_additive_family_codes(
    session: Session, code: str
) -> None:
    run = _persist_run(session)
    event = make_event(
        run,
        event_type="STATE_TRANSITIONED",
        from_state="VALIDATING",
        to_state="FAILED_INPUT",
        failure_code=code,
    )
    session.add(event)
    session.flush()
    assert event.failure_code == code


@pytest.mark.parametrize(
    "event_overrides",
    [
        {
            "event_type": "STATE_TRANSITIONED",
            "from_state": "VALIDATING",
            "to_state": "FAILED_INPUT",
            "failure_code": "MODEL_OUTPUT_INVALID",
        },
        {
            "event_type": "STATE_TRANSITIONED",
            "from_state": "VALIDATING",
            "to_state": "FAILED_INPUT",
            "failure_code": "INPUT_bad",
        },
        {"failure_code": "INPUT_MALFORMED"},
        {
            "event_type": "STATE_TRANSITIONED",
            "from_state": "RECEIVED",
            "to_state": "VALIDATING",
            "failure_code": "INPUT_MALFORMED",
        },
    ],
)
def test_failure_history_rejects_wrong_or_malformed_reason_shape(
    session: Session, event_overrides: dict[str, object]
) -> None:
    run = _persist_run(session)
    assert_rejected(session, make_event(run, **event_overrides))


def test_timeline_is_complete_and_sequence_not_timestamp_order(
    session: Session,
) -> None:
    run = _persist_run(session)
    now = datetime.now(UTC)
    append_run_event(session, make_event(run, occurred_at=now + timedelta(minutes=2)))
    append_run_event(session, make_event(run, occurred_at=now))
    append_run_event(session, make_event(run, occurred_at=now + timedelta(minutes=1)))
    timeline = session.scalars(
        sa.select(RunEvent)
        .where(RunEvent.run_id == run.id)
        .order_by(RunEvent.sequence)
    ).all()
    assert [event.sequence for event in timeline] == [1, 2, 3]
    assert [event.occurred_at for event in timeline] != sorted(
        event.occurred_at for event in timeline
    )


def test_run_event_update_is_rejected(session: Session) -> None:
    run = _persist_run(session)
    event = append_run_event(session, make_event(run))
    event.actor_id = "rewritten"
    assert_rejected(session, event)


def test_run_event_delete_is_rejected(session: Session) -> None:
    run = _persist_run(session)
    event = append_run_event(session, make_event(run))
    session.delete(event)
    with pytest.raises(DBAPIError):
        session.flush()


def test_event_step_kind_must_match_step(session: Session) -> None:
    run = _persist_run(session)
    step = _persist_step(session, run, kind="PLAN")
    assert_rejected(
        session,
        make_event(run, step_id=step.id, step_kind="LOCALISE"),
    )


def test_event_attempt_index_must_exist_under_step(session: Session) -> None:
    run = _persist_run(session)
    step = _persist_step(session, run)
    assert_rejected(
        session,
        make_event(
            run,
            step_id=step.id,
            step_kind=step.kind,
            attempt_index=7,
        ),
    )


def test_event_can_reference_an_existing_attempt(session: Session) -> None:
    run = _persist_run(session)
    step = _persist_step(session, run, kind="EXECUTE_BUGGY")
    attempt = make_attempt(step)
    session.add(attempt)
    session.flush()
    event = make_event(
        run,
        step_id=step.id,
        step_kind=step.kind,
        attempt_index=attempt.attempt_index,
    )
    session.add(event)
    session.flush()
    assert (event.step_id, event.attempt_index) == (step.id, 0)


def test_run_cas_updates_once_and_rejects_stale_or_wrong_expectations(
    session: Session,
) -> None:
    run = _persist_run(session)
    updated = compare_and_swap_run(
        session,
        run_id=run.id,
        expected_state="RECEIVED",
        expected_version=0,
        updates={"state": "VALIDATING"},
    )
    assert updated.state == "VALIDATING"
    assert updated.version == 1

    with pytest.raises(RunProjectionConflictError):
        compare_and_swap_run(
            session,
            run_id=run.id,
            expected_state="VALIDATING",
            expected_version=0,
            updates={"state": "QUEUED"},
        )
    with pytest.raises(RunProjectionConflictError):
        compare_and_swap_run(
            session,
            run_id=run.id,
            expected_state="RECEIVED",
            expected_version=1,
            updates={"state": "QUEUED"},
        )
    session.refresh(run)
    assert (run.state, run.version) == ("VALIDATING", 1)


def test_cas_and_event_commit_atomically(migrated_engine: Engine) -> None:
    with Session(migrated_engine) as session:
        run = _persist_run(session)
        session.commit()
        compare_and_swap_run(
            session,
            run_id=run.id,
            expected_state="RECEIVED",
            expected_version=0,
            updates={"state": "VALIDATING"},
        )
        append_run_event(
            session,
            make_event(
                run,
                event_type="STATE_TRANSITIONED",
                from_state="RECEIVED",
                to_state="VALIDATING",
            ),
        )
        session.commit()
        stored = session.get(Run, run.id)
        assert stored is not None
        assert (stored.state, stored.version) == ("VALIDATING", 1)
        assert session.scalar(
            sa.select(sa.func.count())
            .select_from(RunEvent)
            .where(RunEvent.run_id == run.id)
        ) == 1


def test_invalid_event_rolls_back_projection_and_event(
    migrated_engine: Engine,
) -> None:
    with Session(migrated_engine) as session:
        run = _persist_run(session)
        session.commit()
        compare_and_swap_run(
            session,
            run_id=run.id,
            expected_state="RECEIVED",
            expected_version=0,
            updates={"state": "VALIDATING"},
        )
        with pytest.raises(DBAPIError):
            append_run_event(
                session,
                make_event(
                    run,
                    event_type="STATE_TRANSITIONED",
                    from_state="RECEIVED",
                    to_state="RECEIVED",
                ),
            )
        session.rollback()
        stored = session.get(Run, run.id)
        assert stored is not None
        assert (stored.state, stored.version) == ("RECEIVED", 0)
        assert session.scalar(
            sa.select(sa.func.count())
            .select_from(RunEvent)
            .where(RunEvent.run_id == run.id)
        ) == 0


def test_terminal_run_facts_cannot_be_rewritten_after_commit(
    migrated_engine: Engine,
) -> None:
    with Session(migrated_engine) as session:
        run = _persist_run(session, "COMPLETED")
        session.commit()
        original_terminal_at = run.terminal_at
        with pytest.raises(DBAPIError):
            session.execute(
                sa.update(Run)
                .where(Run.id == run.id)
                .values(
                    terminal_at=original_terminal_at + timedelta(seconds=1),
                    terminal_actor_id="rewritten",
                )
            )
        session.rollback()
        stored = session.get(Run, run.id)
        assert stored is not None
        assert stored.terminal_at == original_terminal_at
        assert stored.terminal_actor_id == "workflow-runtime"


def test_event_payload_is_physically_bounded(session: Session) -> None:
    run = _persist_run(session)
    assert_rejected(session, make_event(run, payload={"value": "x" * 65536}))


def test_db_003_has_no_raw_or_queue_storage_columns() -> None:
    forbidden = {
        "queue_message_id",
        "queue_delivery_id",
        "claim_or_lease_id",
        "provider_receipt",
        "raw_repository",
        "raw_prompt",
        "patch_bytes",
        "log_bytes",
        "token",
        "evidence_bytes",
        "artefact_bytes",
    }
    actual = {
        column.name
        for table_name in DB_003_TABLES
        for column in Run.metadata.tables[table_name].columns
    }
    assert actual & forbidden == set()
    assert "id" in WorkflowStepAttempt.__table__.columns
    assert WorkflowStepAttempt.__table__.columns.id.type.python_type is uuid.UUID


def test_db_003_adds_no_second_repair_allowance() -> None:
    repair_columns = [
        column.name
        for table_name in DB_003_TABLES
        for column in Run.metadata.tables[table_name].columns
        if "repair" in column.name
    ]
    assert repair_columns == []
