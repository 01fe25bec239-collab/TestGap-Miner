"""Pure checkpoint resume validation for Workflow lifecycle state."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .engine import TERMINAL_STATES, parse_run_state
from .types import (
    WORKFLOW_CONTRACT_VERSION,
    AttemptId,
    LifecycleSnapshot,
    RejectionReason,
    RequestKind,
    ResumeMode,
    RunState,
    _is_nonnegative_int,
    _repair_counter_is_valid_for_state,
    _valid_retry_counters,
)


@dataclass(frozen=True, slots=True)
class CheckpointSnapshot:
    contract_version: str
    state: RunState | object
    run_version: int
    checksum_valid: bool
    is_latest_committed: bool
    run_version_matches: bool
    is_terminal: bool
    repair_attempts_used: int
    retry_attempts_used: int
    retry_limit: int
    request_kind: RequestKind
    review_required: bool
    current_attempt_id: AttemptId | None


@dataclass(frozen=True, slots=True)
class ResumeDecision:
    accepted: bool
    checkpoint: CheckpointSnapshot
    snapshot: LifecycleSnapshot | None
    rejection_reason: RejectionReason | None
    attempt_id: AttemptId | None = None
    resume_mode: ResumeMode | None = None


def validate_resume(
    checkpoint: CheckpointSnapshot,
    resume_mode: ResumeMode | object,
    new_attempt_identity: AttemptId | None = None,
) -> ResumeDecision:
    """Validate a resume without persistence, time, random, or hidden mutation."""

    parsed = parse_run_state(checkpoint.state)
    if not parsed.accepted:
        return _reject(checkpoint, parsed.rejection_reason)
    state = parsed.state
    assert state is not None
    if checkpoint.is_latest_committed is not True:
        return _reject(checkpoint, RejectionReason.CHECKPOINT_NOT_COMMITTED)
    if checkpoint.checksum_valid is not True:
        return _reject(checkpoint, RejectionReason.CHECKPOINT_CHECKSUM_INVALID)
    if (
        not _is_nonnegative_int(checkpoint.run_version)
        or checkpoint.run_version_matches is not True
    ):
        return _reject(checkpoint, RejectionReason.CHECKPOINT_VERSION_MISMATCH)
    if checkpoint.contract_version != WORKFLOW_CONTRACT_VERSION:
        return _reject(checkpoint, RejectionReason.CHECKPOINT_CONTRACT_INCOMPATIBLE)
    if checkpoint.is_terminal is not False or state in TERMINAL_STATES:
        return _reject(checkpoint, RejectionReason.TERMINAL_RUN_CANNOT_RESUME)
    if not _repair_counter_is_valid_for_state(
        state, checkpoint.repair_attempts_used
    ):
        return _reject(checkpoint, RejectionReason.INVALID_REPAIR_COUNTERS)
    if not _valid_retry_counters(
        checkpoint.retry_attempts_used, checkpoint.retry_limit
    ):
        return _reject(checkpoint, RejectionReason.INVALID_RETRY_COUNTERS)
    if not isinstance(resume_mode, ResumeMode):
        return _reject(checkpoint, RejectionReason.INVALID_RESUME_MODE)
    if not isinstance(checkpoint.request_kind, RequestKind) or (
        type(checkpoint.review_required) is not bool
    ):
        return _reject(checkpoint, RejectionReason.INVALID_RESUME_MODE)
    if checkpoint.current_attempt_id is not None and not isinstance(
        checkpoint.current_attempt_id, AttemptId
    ):
        return _reject(checkpoint, RejectionReason.ATTEMPT_ID_REQUIRED)

    snapshot = LifecycleSnapshot(
        state=state,
        repair_attempts_used=checkpoint.repair_attempts_used,
        retry_attempts_used=checkpoint.retry_attempts_used,
        retry_limit=checkpoint.retry_limit,
        request_kind=checkpoint.request_kind,
        review_required=checkpoint.review_required,
        contract_version=checkpoint.contract_version,
        run_version=checkpoint.run_version,
        current_attempt_id=checkpoint.current_attempt_id,
    )
    if resume_mode == ResumeMode.CONTINUE_CURRENT_ATTEMPT:
        if not isinstance(checkpoint.current_attempt_id, AttemptId):
            return _reject(checkpoint, RejectionReason.ATTEMPT_ID_REQUIRED)
        return ResumeDecision(
            True,
            checkpoint,
            snapshot,
            None,
            checkpoint.current_attempt_id,
            resume_mode,
        )

    if not isinstance(new_attempt_identity, AttemptId):
        return _reject(checkpoint, RejectionReason.ATTEMPT_ID_REQUIRED)
    if new_attempt_identity == checkpoint.current_attempt_id:
        return _reject(checkpoint, RejectionReason.ATTEMPT_ID_NOT_DISTINCT)
    if checkpoint.retry_attempts_used == checkpoint.retry_limit:
        return _reject(checkpoint, RejectionReason.RETRY_LIMIT_EXHAUSTED)
    return ResumeDecision(
        True,
        checkpoint,
        replace(
            snapshot,
            retry_attempts_used=snapshot.retry_attempts_used + 1,
            current_attempt_id=new_attempt_identity,
            run_version=snapshot.run_version + 1,
        ),
        None,
        new_attempt_identity,
        resume_mode,
    )


def _reject(
    checkpoint: CheckpointSnapshot, reason: RejectionReason | None
) -> ResumeDecision:
    assert reason is not None
    return ResumeDecision(False, checkpoint, None, reason)
