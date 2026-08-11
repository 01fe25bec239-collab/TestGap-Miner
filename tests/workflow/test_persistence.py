"""Workflow-owned mapping and PostgreSQL lifecycle persistence evidence."""

import uuid
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.db.models import Run, RunEvent, RunRequest
from app.db.workflow_persistence import (
    RunProjectionConflictError,
    append_run_event,
)
from app.workflow import (
    WORKFLOW_CONTRACT_VERSION,
    AbstentionCode,
    ActorRef,
    ActorType,
    CancellationCode,
    HumanDisposition,
    InvalidDurableStateError,
    PersistenceConflictReason,
    PersistentTransitionRequest,
    PersistentTransitionStatus,
    RejectionReason,
    RequestKind,
    RunState,
    TransitionContext,
    lifecycle_snapshot_from_run,
    persist_transition,
    workflow_contract_version_from_durable,
)


NOW = datetime(2026, 8, 10, 12, tzinfo=UTC)
SYSTEM = ActorRef(ActorType.SYSTEM, "system:workflow-test")
HUMAN = ActorRef(ActorType.HUMAN, "human:reviewer-test")


def _request_record(request_kind: str = "GITHUB") -> RunRequest:
    unique = uuid.uuid4().hex
    values: dict[str, object] = {
        "request_kind": request_kind,
        "idempotency_key": unique,
        "idempotency_key_version": 1,
        "request_fingerprint": unique,
        "configuration_version": "cfg-1",
        "model_id": "model-1",
        "prompt_template_version": "prompt-1",
    }
    if request_kind == "GITHUB":
        values.update(
            github_delivery_guid=unique,
            github_repository_id=123,
            repository_sha="a" * 40,
        )
    elif request_kind == "BENCHMARK":
        values.update(benchmark_project_id="Lang", benchmark_bug_id=unique)
    return RunRequest(**values)


def _run_record(
    state: str = "RECEIVED",
    *,
    request_kind: str = "GITHUB",
    **overrides: object,
) -> Run:
    values: dict[str, object] = {
        "run_request": _request_record(request_kind),
        "state": state,
        "contract_version": "1.0.0-draft.1",
        "review_required": True,
        "repair_attempts_used": 0,
        "retry_attempts_used": 0,
        "retry_limit": 2,
        "version": 0,
        "terminal_at": None,
        "terminal_actor_type": None,
        "terminal_actor_id": None,
        "failure_code": None,
        "abstention_code": None,
        "cancellation_code": None,
    }
    values.update(overrides)
    return Run(**values)


def _persist_run(session: Session, state: str = "RECEIVED", **values: object) -> Run:
    run = _run_record(state, **values)
    session.add(run)
    session.flush()
    return run


def _transition_request(
    run: Run,
    target: RunState,
    context: TransitionContext | None = None,
    *,
    expected_state: RunState | None = None,
    expected_version: int | None = None,
    producer_event_id: str | None = None,
    fingerprint: str | None = None,
    occurred_at: datetime = NOW,
) -> PersistentTransitionRequest:
    producer_event_id = producer_event_id or uuid.uuid4().hex
    return PersistentTransitionRequest(
        run_id=run.id,
        expected_state=expected_state or RunState(run.state),
        expected_version=run.version if expected_version is None else expected_version,
        requested_target=target,
        transition_context=context or TransitionContext(actor=SYSTEM),
        occurred_at=occurred_at,
        producer_event_id=producer_event_id,
        producer_event_fingerprint=fingerprint or f"fingerprint-{producer_event_id}",
        producer_event_fingerprint_version=1,
        payload_schema_version="1",
        correlation_id="correlation-test",
    )


def _event_count(session: Session, run_id: uuid.UUID) -> int:
    return session.scalar(
        sa.select(sa.func.count())
        .select_from(RunEvent)
        .where(RunEvent.run_id == run_id)
    ) or 0


def test_exact_contract_version_adapter() -> None:
    assert (
        workflow_contract_version_from_durable("1.0.0-draft.1")
        == WORKFLOW_CONTRACT_VERSION
    )
    for unsupported in (
        "CONTRACT-WORKFLOW-001@1.0.0-draft.1",
        "1.0.0",
        " 1.0.0-draft.1",
        "1.0.0-DRAFT.1",
        RequestKind.GITHUB,
        None,
    ):
        with pytest.raises(InvalidDurableStateError):
            workflow_contract_version_from_durable(unsupported)


def test_received_durable_run_maps_exactly() -> None:
    run = _run_record(
        request_kind="BENCHMARK",
        review_required=False,
        repair_attempts_used=0,
        retry_attempts_used=2,
        retry_limit=3,
        version=7,
    )
    snapshot = lifecycle_snapshot_from_run(run)
    assert snapshot.state == RunState.RECEIVED
    assert snapshot.request_kind == RequestKind.BENCHMARK
    assert snapshot.review_required is False
    assert snapshot.repair_attempts_used == 0
    assert snapshot.retry_attempts_used == 2
    assert snapshot.retry_limit == 3
    assert snapshot.run_version == 7
    assert snapshot.contract_version == WORKFLOW_CONTRACT_VERSION
    assert snapshot.current_attempt_id is None


@pytest.mark.parametrize("state", ["UNKNOWN", "received", " RECEIVED"])
def test_durable_state_mapping_rejects_unknown_or_noncanonical_state(
    state: str,
) -> None:
    with pytest.raises(InvalidDurableStateError):
        lifecycle_snapshot_from_run(_run_record(state))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("repair_attempts_used", True),
        ("repair_attempts_used", 1.0),
        ("repair_attempts_used", -1),
        ("repair_attempts_used", 2),
        ("retry_attempts_used", True),
        ("retry_attempts_used", 1.0),
        ("retry_attempts_used", -1),
        ("retry_limit", True),
        ("retry_limit", 1.0),
        ("retry_limit", -1),
        ("version", True),
        ("version", 1.0),
        ("version", -1),
        ("review_required", 1),
    ],
)
def test_durable_mapping_rejects_malformed_typed_facts(
    field: str, value: object
) -> None:
    with pytest.raises(InvalidDurableStateError):
        lifecycle_snapshot_from_run(_run_record(**{field: value}))


def test_durable_mapping_rejects_impossible_repair_pair_and_request_kind() -> None:
    with pytest.raises(InvalidDurableStateError):
        lifecycle_snapshot_from_run(_run_record("REPAIRING", repair_attempts_used=0))
    with pytest.raises(InvalidDurableStateError):
        lifecycle_snapshot_from_run(_run_record(request_kind="github"))


@pytest.mark.parametrize(
    ("retry_attempts_used", "retry_limit", "accepted"),
    [(0, 2, False), (1, 2, False), (2, 2, True), (0, 0, True)],
)
def test_durable_infrastructure_failure_requires_exhausted_retry_budget(
    retry_attempts_used: int, retry_limit: int, accepted: bool
) -> None:
    run = _run_record(
        "FAILED_INFRASTRUCTURE",
        retry_attempts_used=retry_attempts_used,
        retry_limit=retry_limit,
        terminal_at=NOW,
        terminal_actor_type="SYSTEM",
        terminal_actor_id=SYSTEM.identifier,
        failure_code="INFRASTRUCTURE_DATABASE",
    )
    if accepted:
        assert lifecycle_snapshot_from_run(run).state == RunState.FAILED_INFRASTRUCTURE
    else:
        with pytest.raises(InvalidDurableStateError, match="unexhausted retry"):
            lifecycle_snapshot_from_run(run)


@pytest.mark.parametrize(
    ("abstention_code", "repair_attempts_used", "accepted"),
    [
        (AbstentionCode.REPAIR_LIMIT_EXHAUSTED.value, 0, False),
        (AbstentionCode.REPAIR_LIMIT_EXHAUSTED.value, 1, True),
        (AbstentionCode.INSUFFICIENT_CONTEXT.value, 0, True),
    ],
)
def test_durable_repair_limit_abstention_requires_consumed_repair(
    abstention_code: str, repair_attempts_used: int, accepted: bool
) -> None:
    run = _run_record(
        "ABSTAINED",
        abstention_code=abstention_code,
        repair_attempts_used=repair_attempts_used,
        terminal_at=NOW,
        terminal_actor_type="SYSTEM",
        terminal_actor_id=SYSTEM.identifier,
    )
    if accepted:
        assert lifecycle_snapshot_from_run(run).state == RunState.ABSTAINED
    else:
        with pytest.raises(InvalidDurableStateError, match="no consumed repair"):
            lifecycle_snapshot_from_run(run)


@pytest.mark.parametrize(
    ("state", "overrides"),
    [
        ("RECEIVED", {"terminal_at": NOW}),
        (
            "FAILED_INPUT",
            {
                "terminal_at": NOW,
                "terminal_actor_type": "SYSTEM",
                "terminal_actor_id": "system:test",
            },
        ),
        (
            "ABSTAINED",
            {
                "terminal_at": NOW,
                "terminal_actor_type": "SYSTEM",
                "terminal_actor_id": "system:test",
                "abstention_code": "UNKNOWN",
            },
        ),
        (
            "CANCELLED",
            {
                "terminal_at": NOW,
                "terminal_actor_type": "ROBOT",
                "terminal_actor_id": "robot:test",
                "cancellation_code": "USER_REQUESTED",
            },
        ),
        (
            "COMPLETED",
            {
                "terminal_at": NOW,
                "terminal_actor_type": "SYSTEM",
                "terminal_actor_id": "system:test",
                "failure_code": "INPUT_MALFORMED",
            },
        ),
    ],
)
def test_durable_mapping_rejects_malformed_terminal_shapes(
    state: str, overrides: dict[str, object]
) -> None:
    with pytest.raises(InvalidDurableStateError):
        lifecycle_snapshot_from_run(_run_record(state, **overrides))


def test_persistent_request_requires_attribution_and_strict_identity_facts() -> None:
    run = _run_record()
    run.id = uuid.uuid4()
    with pytest.raises(ValueError, match="actor attribution"):
        _transition_request(
            run,
            RunState.VALIDATING,
            TransitionContext(),
        )
    with pytest.raises(ValueError, match="positive integer"):
        replace(
            _transition_request(run, RunState.VALIDATING),
            producer_event_fingerprint_version=True,
        )


@pytest.mark.parametrize(
    ("state", "target", "run_values", "context", "reason"),
    [
        (
            "RECEIVED",
            RunState.RECEIVED,
            {},
            TransitionContext(actor=SYSTEM),
            RejectionReason.SELF_TRANSITION_NOT_ALLOWED,
        ),
        (
            "RECEIVED",
            RunState.PLANNING,
            {},
            TransitionContext(actor=SYSTEM),
            RejectionReason.TRANSITION_NOT_ALLOWED,
        ),
        (
            "EXECUTING_BUGGY",
            RunState.REPAIRING,
            {"repair_attempts_used": 1},
            TransitionContext(actor=SYSTEM, repairable_failure_recorded=True),
            RejectionReason.REPAIR_ALREADY_CONSUMED,
        ),
        (
            "EXECUTING_BUGGY",
            RunState.REPAIRING,
            {},
            TransitionContext(actor=SYSTEM),
            RejectionReason.REPAIR_FAILURE_NOT_RECORDED,
        ),
        (
            "VALIDATING",
            RunState.FAILED_INFRASTRUCTURE,
            {"retry_attempts_used": 0, "retry_limit": 1},
            TransitionContext(
                actor=SYSTEM, failure_code="INFRASTRUCTURE_DATABASE"
            ),
            RejectionReason.INFRASTRUCTURE_RETRY_BUDGET_REMAINS,
        ),
        (
            "PLANNING",
            RunState.ABSTAINED,
            {},
            TransitionContext(
                actor=SYSTEM,
                abstention_code=AbstentionCode.REPAIR_LIMIT_EXHAUSTED,
            ),
            RejectionReason.REPAIR_LIMIT_NOT_EXHAUSTED,
        ),
        (
            "AWAITING_HUMAN_REVIEW",
            RunState.CANCELLED,
            {},
            TransitionContext(
                actor=SYSTEM, cancellation_code=CancellationCode.USER_REQUESTED
            ),
            RejectionReason.CANCELLATION_AFTER_REVIEW_BOUNDARY,
        ),
        (
            "PUBLISHING",
            RunState.CANCELLED,
            {},
            TransitionContext(
                actor=SYSTEM,
                cancellation_code=CancellationCode.USER_REQUESTED,
                publication_side_effect_committed=True,
            ),
            RejectionReason.CANCELLATION_AFTER_PUBLICATION_COMMIT,
        ),
    ],
)
def test_rejected_transition_makes_no_persistent_change(
    workflow_pg_engine: Engine,
    state: str,
    target: RunState,
    run_values: dict[str, object],
    context: TransitionContext,
    reason: RejectionReason,
) -> None:
    with Session(workflow_pg_engine) as session:
        run = _persist_run(session, state, **run_values)
        session.commit()
        before = (
            run.state,
            run.version,
            run.repair_attempts_used,
            run.retry_attempts_used,
            run.terminal_at,
            run.terminal_actor_type,
            run.terminal_actor_id,
        )
        result = persist_transition(session, _transition_request(run, target, context))
        assert result.status == PersistentTransitionStatus.REJECTED
        assert result.decision is not None
        assert result.decision.rejection_reason == reason
        session.commit()
        session.refresh(run)
        assert (
            run.state,
            run.version,
            run.repair_attempts_used,
            run.retry_attempts_used,
            run.terminal_at,
            run.terminal_actor_type,
            run.terminal_actor_id,
        ) == before
        assert _event_count(session, run.id) == 0


def test_accepted_transition_commits_projection_and_event(
    workflow_pg_engine: Engine,
) -> None:
    with Session(workflow_pg_engine) as session:
        run = _persist_run(session)
        run_id = run.id
        session.commit()
        request = _transition_request(run, RunState.VALIDATING)
        result = persist_transition(session, request)
        assert result.status == PersistentTransitionStatus.APPLIED
        session.commit()

    with Session(workflow_pg_engine) as session:
        stored = session.get(Run, run_id)
        event = session.scalar(sa.select(RunEvent).where(RunEvent.run_id == run_id))
        assert stored is not None and event is not None
        assert (stored.state, stored.version) == ("VALIDATING", 1)
        assert event.sequence == 1
        assert event.event_type == "STATE_TRANSITIONED"
        assert (event.from_state, event.to_state) == ("RECEIVED", "VALIDATING")
        assert (event.actor_type, event.actor_id) == (
            SYSTEM.actor_type.value,
            SYSTEM.identifier,
        )
        assert event.contract_version == "1.0.0-draft.1"


def test_sequences_follow_append_order_not_occurred_at(
    workflow_pg_engine: Engine,
) -> None:
    with Session(workflow_pg_engine) as session:
        run = _persist_run(session)
        run_id = run.id
        session.commit()
        transitions = (
            (RunState.RECEIVED, RunState.VALIDATING, 0, NOW + timedelta(minutes=2)),
            (RunState.VALIDATING, RunState.QUEUED, 1, NOW),
            (RunState.QUEUED, RunState.PLANNING, 2, NOW + timedelta(minutes=1)),
        )
        for source, target, version, occurred_at in transitions:
            request = _transition_request(
                run,
                target,
                expected_state=source,
                expected_version=version,
                occurred_at=occurred_at,
            )
            assert persist_transition(session, request).status == "APPLIED"
        session.commit()

    with Session(workflow_pg_engine) as session:
        events = session.scalars(
            sa.select(RunEvent)
            .where(RunEvent.run_id == run_id)
            .order_by(RunEvent.sequence)
        ).all()
        assert [event.sequence for event in events] == [1, 2, 3]
        assert [event.to_state for event in events] == [
            "VALIDATING",
            "QUEUED",
            "PLANNING",
        ]
        assert [event.occurred_at for event in events] != sorted(
            event.occurred_at for event in events
        )


@pytest.mark.parametrize(
    ("state", "target", "run_values", "context", "code_field", "code"),
    [
        (
            "QUEUED",
            RunState.FAILED_INFRASTRUCTURE,
            {"retry_attempts_used": 2, "retry_limit": 2},
            TransitionContext(
                actor=SYSTEM, failure_code="INFRASTRUCTURE_RETRY_EXHAUSTED"
            ),
            "failure_code",
            "INFRASTRUCTURE_RETRY_EXHAUSTED",
        ),
        (
            "PLANNING",
            RunState.ABSTAINED,
            {},
            TransitionContext(
                actor=SYSTEM,
                abstention_code=AbstentionCode.INSUFFICIENT_CONTEXT,
            ),
            "abstention_code",
            "INSUFFICIENT_CONTEXT",
        ),
        (
            "EXECUTING_BUGGY",
            RunState.ABSTAINED,
            {"repair_attempts_used": 1},
            TransitionContext(
                actor=SYSTEM,
                abstention_code=AbstentionCode.REPAIR_LIMIT_EXHAUSTED,
            ),
            "abstention_code",
            "REPAIR_LIMIT_EXHAUSTED",
        ),
        (
            "RECEIVED",
            RunState.CANCELLED,
            {},
            TransitionContext(
                actor=SYSTEM, cancellation_code=CancellationCode.USER_REQUESTED
            ),
            "cancellation_code",
            "USER_REQUESTED",
        ),
    ],
)
def test_terminal_transition_maps_projection_and_event_reason(
    workflow_pg_engine: Engine,
    state: str,
    target: RunState,
    run_values: dict[str, object],
    context: TransitionContext,
    code_field: str,
    code: str,
) -> None:
    with Session(workflow_pg_engine) as session:
        run = _persist_run(session, state, **run_values)
        run_id = run.id
        old_repair = run.repair_attempts_used
        old_retry = run.retry_attempts_used
        session.commit()
        result = persist_transition(
            session, _transition_request(run, target, context)
        )
        assert result.status == PersistentTransitionStatus.APPLIED
        session.commit()

    with Session(workflow_pg_engine) as session:
        stored = session.get(Run, run_id)
        event = session.scalar(sa.select(RunEvent).where(RunEvent.run_id == run_id))
        assert stored is not None and event is not None
        assert (stored.state, stored.version, stored.terminal_at) == (
            target.value,
            1,
            NOW,
        )
        assert (stored.terminal_actor_type, stored.terminal_actor_id) == (
            SYSTEM.actor_type.value,
            SYSTEM.identifier,
        )
        assert getattr(stored, code_field) == code
        assert getattr(event, code_field) == code
        assert stored.repair_attempts_used == old_repair
        assert stored.retry_attempts_used == old_retry


def test_repair_counter_changes_once_and_retry_counter_does_not(
    workflow_pg_engine: Engine,
) -> None:
    with Session(workflow_pg_engine) as session:
        run = _persist_run(session, "EXECUTING_BUGGY", retry_attempts_used=1)
        run_id = run.id
        session.commit()
        first = persist_transition(
            session,
            _transition_request(
                run,
                RunState.REPAIRING,
                TransitionContext(actor=SYSTEM, repairable_failure_recorded=True),
            ),
        )
        assert first.status == "APPLIED"
        second = persist_transition(
            session,
            _transition_request(
                run,
                RunState.EXECUTING_BUGGY,
                expected_state=RunState.REPAIRING,
                expected_version=1,
            ),
        )
        assert second.status == "APPLIED"
        rejected = persist_transition(
            session,
            _transition_request(
                run,
                RunState.REPAIRING,
                TransitionContext(actor=SYSTEM, repairable_failure_recorded=True),
                expected_state=RunState.EXECUTING_BUGGY,
                expected_version=2,
            ),
        )
        assert rejected.status == "REJECTED"
        assert rejected.decision is not None
        assert rejected.decision.rejection_reason == RejectionReason.REPAIR_ALREADY_CONSUMED
        session.commit()

    with Session(workflow_pg_engine) as session:
        stored = session.get(Run, run_id)
        assert stored is not None
        assert (stored.state, stored.version) == ("EXECUTING_BUGGY", 2)
        assert (stored.repair_attempts_used, stored.retry_attempts_used) == (1, 1)
        assert _event_count(session, run_id) == 2


def test_stale_illegal_transition_pair_does_not_append_or_overwrite(
    workflow_pg_engine: Engine,
) -> None:
    with Session(workflow_pg_engine) as session:
        run = _persist_run(session, "VALIDATING", version=1)
        run_id = run.id
        session.commit()
        stale = _transition_request(
            run,
            RunState.PLANNING,
            expected_state=RunState.RECEIVED,
            expected_version=0,
        )
        result = persist_transition(session, stale)
        assert result.status == PersistentTransitionStatus.CONFLICT
        assert result.conflict_reason == PersistenceConflictReason.STALE_PROJECTION
        session.commit()
        stored = session.get(Run, run_id)
        assert stored is not None
        assert (stored.state, stored.version) == ("VALIDATING", 1)
        assert _event_count(session, run_id) == 0


def test_stale_physically_invalid_candidate_does_not_append_or_overwrite(
    workflow_pg_engine: Engine,
) -> None:
    with Session(workflow_pg_engine) as session:
        run = _persist_run(session, "VALIDATING", version=1)
        run_id = run.id
        session.commit()
        stale = replace(
            _transition_request(
                run,
                RunState.VALIDATING,
                expected_state=RunState.RECEIVED,
                expected_version=0,
            ),
            causation_event_id=uuid.uuid4(),
        )
        result = persist_transition(session, stale)
        assert result.status == PersistentTransitionStatus.CONFLICT
        assert result.conflict_reason == PersistenceConflictReason.STALE_PROJECTION
        session.commit()
        stored = session.get(Run, run_id)
        assert stored is not None
        assert (stored.state, stored.version) == ("VALIDATING", 1)
        assert _event_count(session, run_id) == 0


def test_stale_expected_state_is_independently_rejected(
    workflow_pg_engine: Engine,
) -> None:
    with Session(workflow_pg_engine) as session:
        run = _persist_run(session)
        run_id = run.id
        session.commit()
        result = persist_transition(
            session,
            _transition_request(
                run,
                RunState.QUEUED,
                expected_state=RunState.VALIDATING,
                expected_version=0,
            ),
        )
        assert result.conflict_reason == PersistenceConflictReason.STALE_PROJECTION
        session.commit()
        assert _event_count(session, run_id) == 0


def test_missing_and_invalid_durable_runs_return_explicit_results(
    workflow_pg_engine: Engine,
) -> None:
    with Session(workflow_pg_engine) as session:
        missing = PersistentTransitionRequest(
            run_id=uuid.uuid4(),
            expected_state=RunState.RECEIVED,
            expected_version=0,
            requested_target=RunState.VALIDATING,
            transition_context=TransitionContext(actor=SYSTEM),
            occurred_at=NOW,
            producer_event_id="missing-run",
            producer_event_fingerprint="missing-run-fingerprint",
            producer_event_fingerprint_version=1,
            payload_schema_version="1",
        )
        assert persist_transition(session, missing).status == "RUN_NOT_FOUND"

        run = _persist_run(session, contract_version="unsupported")
        session.commit()
        result = persist_transition(
            session, _transition_request(run, RunState.VALIDATING)
        )
        assert result.status == PersistentTransitionStatus.INVALID_DURABLE_STATE
        session.commit()
        session.refresh(run)
        assert (run.state, run.version, _event_count(session, run.id)) == (
            "RECEIVED",
            0,
            0,
        )


def test_invalid_durable_run_precedes_stale_projection_classification(
    workflow_pg_engine: Engine,
) -> None:
    with Session(workflow_pg_engine) as session:
        run = _persist_run(
            session,
            "VALIDATING",
            version=1,
            contract_version="unsupported",
        )
        run_id = run.id
        session.commit()
        result = persist_transition(
            session,
            _transition_request(
                run,
                RunState.PLANNING,
                expected_state=RunState.RECEIVED,
                expected_version=0,
            ),
        )
        assert result.status == PersistentTransitionStatus.INVALID_DURABLE_STATE
        session.commit()
        stored = session.get(Run, run_id)
        assert stored is not None
        assert (stored.state, stored.version) == ("VALIDATING", 1)
        assert _event_count(session, run_id) == 0


def test_existing_event_with_old_projection_is_persistence_inconsistency(
    workflow_pg_engine: Engine,
) -> None:
    with Session(workflow_pg_engine) as session:
        run = _persist_run(session)
        request = _transition_request(
            run,
            RunState.VALIDATING,
            producer_event_id="inconsistent-event",
            fingerprint="inconsistent-fingerprint",
        )
        event = RunEvent(
            run_id=run.id,
            event_type="STATE_TRANSITIONED",
            from_state="RECEIVED",
            to_state="VALIDATING",
            actor_type="SYSTEM",
            actor_id=SYSTEM.identifier,
            occurred_at=NOW,
            producer_event_id=request.producer_event_id,
            contract_version="1.0.0-draft.1",
            payload_schema_version="1",
            payload={},
            producer_event_fingerprint=request.producer_event_fingerprint,
            producer_event_fingerprint_version=1,
        )
        append_run_event(session, event)
        session.commit()

        result = persist_transition(session, request)
        assert result.status == PersistentTransitionStatus.CONFLICT
        assert (
            result.conflict_reason
            == PersistenceConflictReason.PERSISTENCE_INCONSISTENCY
        )
        session.commit()
        session.refresh(run)
        assert (run.state, run.version, _event_count(session, run.id)) == (
            "RECEIVED",
            0,
            1,
        )


def test_event_append_rolls_back_when_cas_fails(
    workflow_pg_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.workflow.persistence as persistence

    with Session(workflow_pg_engine) as session:
        run = _persist_run(session)
        run_id = run.id
        session.commit()

        def fail_cas(*args: object, **kwargs: object) -> None:
            raise RunProjectionConflictError("forced CAS conflict")

        monkeypatch.setattr(persistence, "compare_and_swap_run", fail_cas)
        result = persist_transition(
            session, _transition_request(run, RunState.VALIDATING)
        )
        assert result.conflict_reason == PersistenceConflictReason.STALE_PROJECTION
        session.commit()

    with Session(workflow_pg_engine) as session:
        stored = session.get(Run, run_id)
        assert stored is not None
        assert (stored.state, stored.version) == ("RECEIVED", 0)
        assert _event_count(session, run_id) == 0


def test_event_persistence_failure_leaves_projection_unchanged(
    workflow_pg_engine: Engine,
) -> None:
    with Session(workflow_pg_engine) as session:
        run = _persist_run(session)
        run_id = run.id
        session.commit()
        request = replace(
            _transition_request(run, RunState.VALIDATING),
            causation_event_id=uuid.uuid4(),
        )
        with pytest.raises(DBAPIError):
            persist_transition(session, request)
        session.commit()

    with Session(workflow_pg_engine) as session:
        stored = session.get(Run, run_id)
        assert stored is not None
        assert (stored.state, stored.version) == ("RECEIVED", 0)
        assert _event_count(session, run_id) == 0


def test_exact_replay_is_an_accepted_noop(workflow_pg_engine: Engine) -> None:
    with Session(workflow_pg_engine) as session:
        run = _persist_run(session)
        run_id = run.id
        session.commit()
        request = _transition_request(
            run,
            RunState.VALIDATING,
            producer_event_id="stable-transition",
            fingerprint="a" * 64,
        )
        assert persist_transition(session, request).status == "APPLIED"
        session.commit()

    with Session(workflow_pg_engine) as session:
        replay = persist_transition(session, request)
        assert replay.status == PersistentTransitionStatus.IDEMPOTENT_REPLAY
        session.commit()
        stored = session.get(Run, run_id)
        assert stored is not None
        assert (stored.state, stored.version) == ("VALIDATING", 1)
        assert _event_count(session, run_id) == 1


def test_invalid_durable_run_precedes_exact_replay_classification(
    workflow_pg_engine: Engine,
) -> None:
    with Session(workflow_pg_engine) as session:
        run = _persist_run(session)
        run_id = run.id
        request = _transition_request(
            run,
            RunState.VALIDATING,
            producer_event_id="invalid-durable-replay",
            fingerprint="a" * 64,
        )
        session.commit()
        applied = persist_transition(session, request)
        assert applied.status == PersistentTransitionStatus.APPLIED
        event_id = applied.event_id
        session.commit()
        session.execute(
            sa.update(Run)
            .where(Run.id == run_id)
            .values(contract_version="unsupported")
        )
        session.commit()

        replay = persist_transition(session, request)
        assert replay.status == PersistentTransitionStatus.INVALID_DURABLE_STATE
        session.commit()
        stored = session.get(Run, run_id)
        event = session.scalar(sa.select(RunEvent).where(RunEvent.run_id == run_id))
        assert stored is not None and event is not None
        assert (stored.state, stored.version, stored.contract_version) == (
            "VALIDATING",
            1,
            "unsupported",
        )
        assert event.id == event_id
        assert _event_count(session, run_id) == 1


def test_unexhausted_infrastructure_failure_precedes_exact_replay(
    workflow_pg_engine: Engine,
) -> None:
    with Session(workflow_pg_engine) as session:
        run = _persist_run(
            session, "QUEUED", retry_attempts_used=2, retry_limit=2
        )
        run_id = run.id
        request = _transition_request(
            run,
            RunState.FAILED_INFRASTRUCTURE,
            TransitionContext(
                actor=SYSTEM, failure_code="INFRASTRUCTURE_DATABASE"
            ),
            producer_event_id="invalid-infrastructure-replay",
            fingerprint="a" * 64,
        )
        session.commit()
        applied = persist_transition(session, request)
        assert applied.status == PersistentTransitionStatus.APPLIED
        event_id = applied.event_id
        session.commit()
        session.execute(
            sa.update(Run)
            .where(Run.id == run_id)
            .values(retry_attempts_used=1)
        )
        session.commit()

        replay = persist_transition(session, request)
        assert replay.status == PersistentTransitionStatus.INVALID_DURABLE_STATE
        session.commit()
        stored = session.get(Run, run_id)
        event = session.scalar(sa.select(RunEvent).where(RunEvent.run_id == run_id))
        assert stored is not None and event is not None
        assert (stored.state, stored.version, stored.retry_attempts_used) == (
            "FAILED_INFRASTRUCTURE",
            1,
            1,
        )
        assert event.id == event_id
        assert _event_count(session, run_id) == 1


def test_unconsumed_repair_limit_abstention_precedes_exact_replay(
    workflow_pg_engine: Engine,
) -> None:
    with Session(workflow_pg_engine) as session:
        run = _persist_run(session, "EXECUTING_BUGGY", repair_attempts_used=1)
        run_id = run.id
        request = _transition_request(
            run,
            RunState.ABSTAINED,
            TransitionContext(
                actor=SYSTEM,
                abstention_code=AbstentionCode.REPAIR_LIMIT_EXHAUSTED,
            ),
            producer_event_id="invalid-repair-limit-replay",
            fingerprint="a" * 64,
        )
        session.commit()
        applied = persist_transition(session, request)
        assert applied.status == PersistentTransitionStatus.APPLIED
        event_id = applied.event_id
        session.commit()
        session.execute(
            sa.update(Run)
            .where(Run.id == run_id)
            .values(repair_attempts_used=0)
        )
        session.commit()

        replay = persist_transition(session, request)
        assert replay.status == PersistentTransitionStatus.INVALID_DURABLE_STATE
        session.commit()
        stored = session.get(Run, run_id)
        event = session.scalar(sa.select(RunEvent).where(RunEvent.run_id == run_id))
        assert stored is not None and event is not None
        assert (stored.state, stored.version, stored.repair_attempts_used) == (
            "ABSTAINED",
            1,
            0,
        )
        assert event.id == event_id
        assert _event_count(session, run_id) == 1


def test_valid_terminal_run_accepts_old_exact_event_replay(
    workflow_pg_engine: Engine,
) -> None:
    with Session(workflow_pg_engine) as session:
        run = _persist_run(session)
        run_id = run.id
        request = _transition_request(
            run,
            RunState.CANCELLED,
            TransitionContext(
                actor=SYSTEM,
                cancellation_code=CancellationCode.USER_REQUESTED,
            ),
            producer_event_id="terminal-replay",
            fingerprint="a" * 64,
        )
        session.commit()
        assert persist_transition(session, request).status == "APPLIED"
        session.commit()

        replay = persist_transition(session, request)
        assert replay.status == PersistentTransitionStatus.IDEMPOTENT_REPLAY
        session.commit()
        stored = session.get(Run, run_id)
        assert stored is not None
        assert (stored.state, stored.version) == ("CANCELLED", 1)
        assert _event_count(session, run_id) == 1


def test_applied_transition_is_rolled_back_with_callers_transaction(
    workflow_pg_engine: Engine,
) -> None:
    with Session(workflow_pg_engine) as session:
        run = _persist_run(session)
        run_id = run.id
        session.commit()
        result = persist_transition(
            session, _transition_request(run, RunState.VALIDATING)
        )
        assert result.status == PersistentTransitionStatus.APPLIED
        session.rollback()

    with Session(workflow_pg_engine) as session:
        stored = session.get(Run, run_id)
        assert stored is not None
        assert (stored.state, stored.version) == ("RECEIVED", 0)
        assert _event_count(session, run_id) == 0


def test_reused_producer_id_with_new_fingerprint_conflicts(
    workflow_pg_engine: Engine,
) -> None:
    with Session(workflow_pg_engine) as session:
        run = _persist_run(session)
        run_id = run.id
        session.commit()
        request = _transition_request(
            run,
            RunState.VALIDATING,
            producer_event_id="stable-conflict",
            fingerprint="a" * 64,
        )
        assert persist_transition(session, request).status == "APPLIED"
        session.commit()

    with Session(workflow_pg_engine) as session:
        conflict = persist_transition(
            session, replace(request, producer_event_fingerprint="b" * 64)
        )
        assert conflict.status == PersistentTransitionStatus.CONFLICT
        assert (
            conflict.conflict_reason
            == PersistenceConflictReason.PRODUCER_EVENT_CONFLICT
        )
        session.commit()
        stored = session.get(Run, run_id)
        assert stored is not None
        assert (stored.state, stored.version) == ("VALIDATING", 1)
        assert _event_count(session, run_id) == 1


@pytest.mark.parametrize("disposition", list(HumanDisposition))
def test_human_review_completion_preserves_disposition_without_child_creation(
    workflow_pg_engine: Engine, disposition: HumanDisposition
) -> None:
    with Session(workflow_pg_engine) as session:
        run = _persist_run(session, "AWAITING_HUMAN_REVIEW")
        run_id = run.id
        request_count = session.scalar(
            sa.select(sa.func.count()).select_from(RunRequest)
        )
        session.commit()
        result = persist_transition(
            session,
            _transition_request(
                run,
                RunState.COMPLETED,
                TransitionContext(actor=HUMAN, human_disposition=disposition),
            ),
        )
        assert result.status == "APPLIED"
        session.commit()
        event = session.scalar(sa.select(RunEvent).where(RunEvent.run_id == run_id))
        assert event is not None
        assert event.payload == {
            "human_disposition": disposition.value,
            "child_run_required": (
                disposition == HumanDisposition.REGENERATION_REQUESTED
            ),
        }
        stored = session.get(Run, run_id)
        assert stored is not None
        assert (stored.state, stored.terminal_actor_type, stored.version) == (
            "COMPLETED",
            "HUMAN",
            1,
        )
        assert session.scalar(
            sa.select(sa.func.count()).select_from(RunRequest)
        ) == request_count


def test_benchmark_completion_uses_pure_decision_and_rejects_other_shapes(
    workflow_pg_engine: Engine,
) -> None:
    with Session(workflow_pg_engine) as session:
        accepted = _persist_run(
            session,
            "SCORING",
            request_kind="BENCHMARK",
            review_required=False,
        )
        github = _persist_run(session, "SCORING", review_required=False)
        review = _persist_run(
            session,
            "SCORING",
            request_kind="BENCHMARK",
            review_required=True,
        )
        evidence = _persist_run(
            session,
            "PUBLISHING",
            request_kind="BENCHMARK",
            review_required=False,
        )
        session.commit()

        applied = persist_transition(
            session,
            _transition_request(
                accepted,
                RunState.COMPLETED,
                TransitionContext(actor=SYSTEM, evidence_packaged=True),
            ),
        )
        assert applied.status == "APPLIED"
        for run, context in (
            (github, TransitionContext(actor=SYSTEM, evidence_packaged=True)),
            (review, TransitionContext(actor=SYSTEM, evidence_packaged=True)),
            (evidence, TransitionContext(actor=SYSTEM, evidence_packaged=False)),
        ):
            result = persist_transition(
                session, _transition_request(run, RunState.COMPLETED, context)
            )
            assert result.status == "REJECTED"
        session.commit()
        assert _event_count(session, accepted.id) == 1
        for run in (github, review, evidence):
            session.refresh(run)
            assert run.version == 0
            assert _event_count(session, run.id) == 0
