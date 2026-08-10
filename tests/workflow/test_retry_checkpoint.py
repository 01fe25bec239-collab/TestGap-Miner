from dataclasses import replace
from inspect import signature

import pytest

from app.workflow import (
    WORKFLOW_CONTRACT_VERSION,
    ActorRef,
    ActorType,
    AttemptId,
    CheckpointSnapshot,
    LifecycleSnapshot,
    RejectionReason,
    RequestKind,
    ResumeMode,
    RetryKind,
    RunState,
    TransitionContext,
    evaluate_transition,
    schedule_retry,
    validate_resume,
)


SYSTEM = ActorRef(ActorType.SYSTEM, "system:test")
CURRENT_ATTEMPT = AttemptId("attempt:current")
NEXT_ATTEMPT = AttemptId("attempt:next")


def snapshot(
    *,
    state: RunState = RunState.PLANNING,
    repair_attempts_used: int = 0,
    retry_attempts_used: int = 0,
    retry_limit: int = 2,
) -> LifecycleSnapshot:
    return LifecycleSnapshot(
        state=state,
        repair_attempts_used=repair_attempts_used,
        retry_attempts_used=retry_attempts_used,
        retry_limit=retry_limit,
        request_kind=RequestKind.GITHUB,
        review_required=True,
        run_version=4,
        current_attempt_id=CURRENT_ATTEMPT,
    )


def checkpoint(**overrides: object) -> CheckpointSnapshot:
    values: dict[str, object] = {
        "contract_version": WORKFLOW_CONTRACT_VERSION,
        "state": RunState.EXECUTING_BUGGY,
        "run_version": 7,
        "checksum_valid": True,
        "is_latest_committed": True,
        "run_version_matches": True,
        "is_terminal": False,
        "repair_attempts_used": 1,
        "retry_attempts_used": 1,
        "retry_limit": 3,
        "request_kind": RequestKind.GITHUB,
        "review_required": True,
        "current_attempt_id": CURRENT_ATTEMPT,
    }
    values.update(overrides)
    return CheckpointSnapshot(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("retry_kind", list(RetryKind))
def test_retry_scheduling_is_bounded_and_does_not_transition(
    retry_kind: RetryKind,
) -> None:
    current = snapshot(
        state=RunState.EXECUTING_BUGGY,
        repair_attempts_used=1,
        retry_attempts_used=1,
    )
    decision = schedule_retry(current, NEXT_ATTEMPT, retry_kind)

    assert decision.accepted
    assert decision.previous_snapshot == current
    assert decision.next_snapshot is not None
    assert decision.next_snapshot.state == current.state
    assert decision.next_snapshot.retry_attempts_used == 2
    assert decision.next_snapshot.repair_attempts_used == 1
    assert decision.next_snapshot.current_attempt_id == NEXT_ATTEMPT
    assert decision.next_snapshot.run_version == current.run_version + 1
    assert decision.attempt_id == NEXT_ATTEMPT
    assert decision.retry_kind == retry_kind


def test_retry_at_limit_is_rejected_without_increment() -> None:
    current = snapshot(retry_attempts_used=2, retry_limit=2)
    decision = schedule_retry(current, NEXT_ATTEMPT, RetryKind.INFRASTRUCTURE)

    assert not decision.accepted
    assert decision.rejection_reason == RejectionReason.RETRY_LIMIT_EXHAUSTED
    assert decision.previous_snapshot == current
    assert decision.next_snapshot is None


def test_retry_attempt_identity_must_be_present_and_distinct() -> None:
    current = snapshot()
    assert schedule_retry(
        current, None, RetryKind.TRANSPORT
    ).rejection_reason == RejectionReason.ATTEMPT_ID_REQUIRED
    assert schedule_retry(
        current, CURRENT_ATTEMPT, RetryKind.TRANSPORT
    ).rejection_reason == RejectionReason.ATTEMPT_ID_NOT_DISTINCT


def test_retry_kind_is_typed() -> None:
    decision = schedule_retry(snapshot(), NEXT_ATTEMPT, "QUEUE")
    assert decision.rejection_reason == RejectionReason.INVALID_RETRY_KIND


def test_terminal_run_cannot_schedule_retry() -> None:
    decision = schedule_retry(
        snapshot(state=RunState.COMPLETED),
        NEXT_ATTEMPT,
        RetryKind.INFRASTRUCTURE,
    )
    assert decision.rejection_reason == RejectionReason.TERMINAL_STATE_IMMUTABLE


def test_retry_exhaustion_failure_is_a_separate_transition() -> None:
    current = snapshot(retry_attempts_used=1, retry_limit=2)
    retry = schedule_retry(current, NEXT_ATTEMPT, RetryKind.INFRASTRUCTURE)
    assert retry.accepted and retry.next_snapshot is not None
    assert retry.next_snapshot.state == RunState.PLANNING

    failure = evaluate_transition(
        retry.next_snapshot,
        RunState.FAILED_INFRASTRUCTURE,
        TransitionContext(
            actor=SYSTEM, failure_code="INFRASTRUCTURE_RETRY_EXHAUSTED"
        ),
    )
    assert failure.accepted
    assert failure.next_snapshot is not None
    assert failure.next_snapshot.state == RunState.FAILED_INFRASTRUCTURE


def test_retry_api_has_no_queue_or_redelivery_identity() -> None:
    assert set(signature(schedule_retry).parameters) == {
        "snapshot",
        "attempt_identity",
        "retry_kind",
    }


def test_continue_current_attempt_preserves_checkpoint_semantics() -> None:
    source = checkpoint()
    decision = validate_resume(source, ResumeMode.CONTINUE_CURRENT_ATTEMPT)

    assert decision.accepted
    assert decision.checkpoint == source
    assert decision.snapshot is not None
    assert decision.snapshot.state == source.state
    assert decision.snapshot.repair_attempts_used == source.repair_attempts_used
    assert decision.snapshot.retry_attempts_used == source.retry_attempts_used
    assert decision.snapshot.run_version == source.run_version
    assert decision.snapshot.current_attempt_id == CURRENT_ATTEMPT
    assert decision.attempt_id == CURRENT_ATTEMPT


def test_append_bounded_retry_attempt_preserves_state_and_repair_counter() -> None:
    source = checkpoint()
    decision = validate_resume(
        source, ResumeMode.APPEND_BOUNDED_RETRY_ATTEMPT, NEXT_ATTEMPT
    )

    assert decision.accepted
    assert decision.snapshot is not None
    assert decision.snapshot.state == source.state
    assert decision.snapshot.repair_attempts_used == source.repair_attempts_used
    assert decision.snapshot.retry_attempts_used == source.retry_attempts_used + 1
    assert decision.snapshot.current_attempt_id == NEXT_ATTEMPT
    assert decision.snapshot.run_version == source.run_version + 1


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"checksum_valid": False}, RejectionReason.CHECKPOINT_CHECKSUM_INVALID),
        ({"is_latest_committed": False}, RejectionReason.CHECKPOINT_NOT_COMMITTED),
        (
            {"contract_version": "CONTRACT-WORKFLOW-001@2.0.0"},
            RejectionReason.CHECKPOINT_CONTRACT_INCOMPATIBLE,
        ),
        (
            {"run_version_matches": False},
            RejectionReason.CHECKPOINT_VERSION_MISMATCH,
        ),
        ({"run_version": -1}, RejectionReason.CHECKPOINT_VERSION_MISMATCH),
        (
            {"state": RunState.COMPLETED, "is_terminal": True},
            RejectionReason.TERMINAL_RUN_CANNOT_RESUME,
        ),
        ({"is_terminal": True}, RejectionReason.TERMINAL_RUN_CANNOT_RESUME),
        (
            {"retry_attempts_used": -1},
            RejectionReason.INVALID_RETRY_COUNTERS,
        ),
        ({"retry_limit": -1}, RejectionReason.INVALID_RETRY_COUNTERS),
        (
            {"retry_attempts_used": 4, "retry_limit": 3},
            RejectionReason.INVALID_RETRY_COUNTERS,
        ),
        (
            {"repair_attempts_used": 2},
            RejectionReason.INVALID_REPAIR_COUNTERS,
        ),
        (
            {"state": RunState.REPAIRING, "repair_attempts_used": 0},
            RejectionReason.INVALID_REPAIR_COUNTERS,
        ),
    ],
)
def test_checkpoint_integrity_and_counter_rejections(
    overrides: dict[str, object], reason: RejectionReason
) -> None:
    decision = validate_resume(
        checkpoint(**overrides), ResumeMode.CONTINUE_CURRENT_ATTEMPT
    )
    assert not decision.accepted
    assert decision.rejection_reason == reason
    assert decision.snapshot is None


@pytest.mark.parametrize("value", [True, False, 1.0, 0.0])
def test_checkpoint_repair_counter_requires_exact_integer(value: object) -> None:
    decision = validate_resume(
        checkpoint(repair_attempts_used=value),
        ResumeMode.CONTINUE_CURRENT_ATTEMPT,
    )
    assert not decision.accepted
    assert decision.rejection_reason == RejectionReason.INVALID_REPAIR_COUNTERS
    assert decision.snapshot is None


@pytest.mark.parametrize("state", [RunState.PLANNING, RunState.GENERATING])
def test_checkpoint_rejects_impossible_state_repair_counter(
    state: RunState,
) -> None:
    decision = validate_resume(
        checkpoint(state=state, repair_attempts_used=1),
        ResumeMode.CONTINUE_CURRENT_ATTEMPT,
    )

    assert not decision.accepted
    assert decision.rejection_reason == RejectionReason.INVALID_REPAIR_COUNTERS
    assert decision.snapshot is None


def test_repaired_executing_buggy_checkpoint_still_resumes() -> None:
    decision = validate_resume(
        checkpoint(state=RunState.EXECUTING_BUGGY, repair_attempts_used=1),
        ResumeMode.CONTINUE_CURRENT_ATTEMPT,
    )

    assert decision.accepted
    assert decision.snapshot is not None
    assert decision.snapshot.state == RunState.EXECUTING_BUGGY
    assert decision.snapshot.repair_attempts_used == 1


@pytest.mark.parametrize("mode", list(ResumeMode))
def test_malformed_checkpoint_attempt_id_returns_rejection(mode: ResumeMode) -> None:
    decision = validate_resume(
        checkpoint(current_attempt_id="attempt:raw"),
        mode,
        NEXT_ATTEMPT,
    )
    assert not decision.accepted
    assert decision.rejection_reason == RejectionReason.ATTEMPT_ID_REQUIRED
    assert decision.snapshot is None


def test_retry_resume_rejects_exhausted_budget() -> None:
    source = checkpoint(retry_attempts_used=3, retry_limit=3)
    decision = validate_resume(
        source, ResumeMode.APPEND_BOUNDED_RETRY_ATTEMPT, NEXT_ATTEMPT
    )
    assert decision.rejection_reason == RejectionReason.RETRY_LIMIT_EXHAUSTED


@pytest.mark.parametrize(
    ("mode", "source", "attempt", "reason"),
    [
        (
            ResumeMode.CONTINUE_CURRENT_ATTEMPT,
            checkpoint(current_attempt_id=None),
            None,
            RejectionReason.ATTEMPT_ID_REQUIRED,
        ),
        (
            ResumeMode.APPEND_BOUNDED_RETRY_ATTEMPT,
            checkpoint(),
            None,
            RejectionReason.ATTEMPT_ID_REQUIRED,
        ),
        (
            ResumeMode.APPEND_BOUNDED_RETRY_ATTEMPT,
            checkpoint(),
            CURRENT_ATTEMPT,
            RejectionReason.ATTEMPT_ID_NOT_DISTINCT,
        ),
        (
            "RESTART_FROM_PLANNING",
            checkpoint(),
            NEXT_ATTEMPT,
            RejectionReason.INVALID_RESUME_MODE,
        ),
    ],
)
def test_resume_mode_and_attempt_guards(
    mode: object,
    source: CheckpointSnapshot,
    attempt: AttemptId | None,
    reason: RejectionReason,
) -> None:
    decision = validate_resume(source, mode, attempt)
    assert decision.rejection_reason == reason


def test_resume_never_resets_repair_or_skips_repaired_buggy_execution() -> None:
    source = checkpoint(
        state=RunState.REPAIRING,
        repair_attempts_used=1,
        retry_attempts_used=0,
    )
    decision = validate_resume(source, ResumeMode.CONTINUE_CURRENT_ATTEMPT)

    assert decision.accepted
    assert decision.snapshot is not None
    assert decision.snapshot.state == RunState.REPAIRING
    assert decision.snapshot.repair_attempts_used == 1
    assert decision.snapshot.retry_attempts_used == 0


def test_malformed_checkpoint_state_is_rejected() -> None:
    decision = validate_resume(
        checkpoint(state="completed"), ResumeMode.CONTINUE_CURRENT_ATTEMPT
    )
    assert decision.rejection_reason == RejectionReason.UNKNOWN_STATE


@pytest.mark.parametrize(
    "operation",
    [
        lambda: evaluate_transition(
            snapshot(state=RunState.EXECUTING_BUGGY), RunState.EXECUTING_FIXED
        ),
        lambda: schedule_retry(snapshot(), NEXT_ATTEMPT, RetryKind.TRANSPORT),
        lambda: validate_resume(
            checkpoint(), ResumeMode.APPEND_BOUNDED_RETRY_ATTEMPT, NEXT_ATTEMPT
        ),
    ],
)
def test_pure_decisions_are_deterministic(operation) -> None:  # type: ignore[no-untyped-def]
    expected = operation()
    assert [operation() for _ in range(10)] == [expected] * 10


def test_retry_counter_cannot_be_constructed_above_limit() -> None:
    with pytest.raises(ValueError, match="retry counters"):
        replace(snapshot(), retry_attempts_used=3, retry_limit=2)
