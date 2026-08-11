"""Transactional persistence integration for Workflow lifecycle transitions.

The caller owns the surrounding SQLAlchemy transaction.  ``APPLIED`` means
the event and projection update were flushed together; durability follows when
that surrounding transaction commits.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Final

import sqlalchemy as sa
from sqlalchemy.orm import Session, contains_eager

from app.db.models import Run, RunEvent, RunRequest
from app.db.workflow_persistence import (
    ProducerEventConflictError,
    RunProjectionConflictError,
    append_run_event,
    compare_and_swap_run,
)

from .engine import TERMINAL_STATES, evaluate_transition, parse_run_state
from .types import (
    WORKFLOW_CONTRACT_VERSION,
    AbstentionCode,
    ActorRef,
    ActorType,
    CancellationCode,
    HumanDisposition,
    LifecycleSnapshot,
    RequestKind,
    RunState,
    TransitionContext,
    TransitionDecision,
)


DURABLE_WORKFLOW_CONTRACT_VERSION: Final = "1.0.0-draft.1"

_FAILURE_PREFIXES: Final = {
    RunState.FAILED_INPUT: "INPUT",
    RunState.FAILED_MODEL: "MODEL",
    RunState.FAILED_EXECUTION: "EXECUTION",
    RunState.FAILED_INFRASTRUCTURE: "INFRASTRUCTURE",
    RunState.FAILED_SECURITY: "SECURITY",
}


class InvalidDurableStateError(ValueError):
    """A durable Run cannot be interpreted under the frozen Workflow contract."""


class PersistentTransitionStatus(StrEnum):
    APPLIED = "APPLIED"
    IDEMPOTENT_REPLAY = "IDEMPOTENT_REPLAY"
    REJECTED = "REJECTED"
    CONFLICT = "CONFLICT"
    INVALID_DURABLE_STATE = "INVALID_DURABLE_STATE"
    RUN_NOT_FOUND = "RUN_NOT_FOUND"


class PersistenceConflictReason(StrEnum):
    STALE_PROJECTION = "STALE_PROJECTION"
    PRODUCER_EVENT_CONFLICT = "PRODUCER_EVENT_CONFLICT"
    PERSISTENCE_INCONSISTENCY = "PERSISTENCE_INCONSISTENCY"


@dataclass(frozen=True, slots=True)
class PersistentTransitionRequest:
    run_id: uuid.UUID
    expected_state: RunState
    expected_version: int
    requested_target: RunState
    transition_context: TransitionContext
    occurred_at: datetime
    producer_event_id: str
    producer_event_fingerprint: str
    producer_event_fingerprint_version: int
    payload_schema_version: str
    correlation_id: str | None = None
    causation_event_id: uuid.UUID | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.run_id, uuid.UUID):
            raise TypeError("run_id must be a UUID")
        if not isinstance(self.expected_state, RunState):
            raise TypeError("expected_state must be a RunState")
        if type(self.expected_version) is not int or self.expected_version < 0:
            raise ValueError("expected_version must be a non-negative integer")
        if not isinstance(self.requested_target, RunState):
            raise TypeError("requested_target must be a RunState")
        if not isinstance(self.transition_context, TransitionContext):
            raise TypeError("transition_context must be a TransitionContext")
        if not isinstance(self.transition_context.actor, ActorRef):
            raise ValueError("persistent transitions require actor attribution")
        if len(self.transition_context.actor.identifier) > 255:
            raise ValueError("actor identifier exceeds the durable bound")
        if not isinstance(self.occurred_at, datetime) or (
            self.occurred_at.tzinfo is None
            or self.occurred_at.utcoffset() is None
        ):
            raise ValueError("occurred_at must be a timezone-aware datetime")
        _bounded_text("producer_event_id", self.producer_event_id, 255)
        _bounded_text(
            "producer_event_fingerprint", self.producer_event_fingerprint, 128
        )
        if (
            type(self.producer_event_fingerprint_version) is not int
            or self.producer_event_fingerprint_version < 1
        ):
            raise ValueError(
                "producer_event_fingerprint_version must be a positive integer"
            )
        _bounded_text("payload_schema_version", self.payload_schema_version, 64)
        if self.correlation_id is not None:
            _bounded_text("correlation_id", self.correlation_id, 255)
        if self.causation_event_id is not None and not isinstance(
            self.causation_event_id, uuid.UUID
        ):
            raise TypeError("causation_event_id must be a UUID")


@dataclass(frozen=True, slots=True)
class PersistentTransitionResult:
    status: PersistentTransitionStatus
    decision: TransitionDecision | None = None
    conflict_reason: PersistenceConflictReason | None = None
    event_id: uuid.UUID | None = None
    run_version: int | None = None
    detail: str | None = None


class _RollbackResult(Exception):
    def __init__(self, result: PersistentTransitionResult) -> None:
        self.result = result


def workflow_contract_version_from_durable(value: object) -> str:
    """Map the one accepted DB representation to the Workflow representation."""

    if type(value) is not str or value != DURABLE_WORKFLOW_CONTRACT_VERSION:
        raise InvalidDurableStateError("unsupported durable workflow contract version")
    return WORKFLOW_CONTRACT_VERSION


def lifecycle_snapshot_from_run(run: Run) -> LifecycleSnapshot:
    """Fail-closed mapping from an explicitly loaded durable Run projection."""

    if type(run.state) is not str:
        raise InvalidDurableStateError("malformed durable run state")
    parsed = parse_run_state(run.state)
    if not parsed.accepted:
        raise InvalidDurableStateError("unknown or malformed durable run state")
    state = parsed.state
    assert state is not None
    _validate_terminal_shape(run, state)
    try:
        durable_request_kind = run.run_request.request_kind
        if type(durable_request_kind) is not str:
            raise TypeError
        request_kind = RequestKind(durable_request_kind)
    except (AttributeError, TypeError, ValueError):
        raise InvalidDurableStateError("malformed durable request kind") from None
    try:
        snapshot = LifecycleSnapshot(
            state=state,
            repair_attempts_used=run.repair_attempts_used,
            retry_attempts_used=run.retry_attempts_used,
            retry_limit=run.retry_limit,
            request_kind=request_kind,
            review_required=run.review_required,
            contract_version=workflow_contract_version_from_durable(
                run.contract_version
            ),
            run_version=run.version,
            current_attempt_id=None,
        )
    except (TypeError, ValueError) as error:
        raise InvalidDurableStateError(str(error)) from error
    _validate_durable_terminal_semantics(run, snapshot)
    return snapshot


def persist_transition(
    session: Session, request: PersistentTransitionRequest
) -> PersistentTransitionResult:
    """Flush one event plus CAS projection update in a caller-owned transaction."""

    try:
        with session.begin_nested():
            run = session.scalar(
                sa.select(Run)
                .join(RunRequest, Run.run_request_id == RunRequest.id)
                .options(contains_eager(Run.run_request))
                .where(Run.id == request.run_id)
                .with_for_update(of=Run)
            )
            if run is None:
                return PersistentTransitionResult(
                    PersistentTransitionStatus.RUN_NOT_FOUND
                )

            try:
                snapshot = lifecycle_snapshot_from_run(run)
            except InvalidDurableStateError as error:
                return PersistentTransitionResult(
                    PersistentTransitionStatus.INVALID_DURABLE_STATE,
                    detail=str(error),
                )

            if (
                run.state != request.expected_state.value
                or run.version != request.expected_version
            ):
                return _probe_replay_or_conflict(session, request, run.version)

            decision = evaluate_transition(
                snapshot,
                request.requested_target,
                request.transition_context,
            )
            if not decision.accepted:
                return PersistentTransitionResult(
                    PersistentTransitionStatus.REJECTED,
                    decision=decision,
                    run_version=run.version,
                )

            event = _transition_event(request, decision)
            try:
                appended = append_run_event(session, event)
            except ProducerEventConflictError:
                raise _RollbackResult(
                    _conflict(PersistenceConflictReason.PRODUCER_EVENT_CONFLICT)
                ) from None
            if appended is not event:
                return _conflict(
                    PersistenceConflictReason.PERSISTENCE_INCONSISTENCY,
                    event_id=appended.id,
                    run_version=run.version,
                )

            try:
                updated = compare_and_swap_run(
                    session,
                    run_id=run.id,
                    expected_state=request.expected_state.value,
                    expected_version=request.expected_version,
                    updates=_projection_updates(decision, request.occurred_at),
                )
            except RunProjectionConflictError:
                raise _RollbackResult(
                    _conflict(PersistenceConflictReason.STALE_PROJECTION)
                ) from None

            return PersistentTransitionResult(
                PersistentTransitionStatus.APPLIED,
                decision=decision,
                event_id=event.id,
                run_version=updated.version,
            )
    except _RollbackResult as rollback:
        return rollback.result


def _probe_replay_or_conflict(
    session: Session,
    request: PersistentTransitionRequest,
    current_version: int,
) -> PersistentTransitionResult:
    existing = session.scalar(
        sa.select(RunEvent.id).where(
            RunEvent.run_id == request.run_id,
            RunEvent.producer_event_id == request.producer_event_id,
        )
    )
    if existing is None:
        return _conflict(
            PersistenceConflictReason.STALE_PROJECTION,
            run_version=current_version,
        )

    event = _transition_event(request)
    try:
        appended = append_run_event(session, event)
    except ProducerEventConflictError:
        raise _RollbackResult(
            _conflict(PersistenceConflictReason.PRODUCER_EVENT_CONFLICT)
        ) from None
    return PersistentTransitionResult(
        PersistentTransitionStatus.IDEMPOTENT_REPLAY,
        event_id=appended.id,
        run_version=current_version,
    )


def _transition_event(
    request: PersistentTransitionRequest,
    decision: TransitionDecision | None = None,
) -> RunEvent:
    actor = request.transition_context.actor
    assert isinstance(actor, ActorRef)
    target = request.requested_target
    terminal_code = (
        decision.terminal_code if decision is not None else _requested_terminal_code(request)
    )
    disposition = (
        decision.human_disposition
        if decision is not None
        else _human_disposition(request.transition_context.human_disposition)
    )
    payload: dict[str, object] = {}
    if disposition is not None:
        payload = {
            "human_disposition": disposition.value,
            "child_run_required": (
                decision.child_run_required
                if decision is not None
                else disposition == HumanDisposition.REGENERATION_REQUESTED
            ),
        }
    return RunEvent(
        run_id=request.run_id,
        event_type="STATE_TRANSITIONED",
        from_state=request.expected_state.value,
        to_state=target.value,
        actor_type=actor.actor_type.value,
        actor_id=actor.identifier,
        occurred_at=request.occurred_at,
        correlation_id=request.correlation_id,
        causation_event_id=request.causation_event_id,
        producer_event_id=request.producer_event_id,
        contract_version=DURABLE_WORKFLOW_CONTRACT_VERSION,
        payload_schema_version=request.payload_schema_version,
        payload=payload,
        producer_event_fingerprint=request.producer_event_fingerprint,
        producer_event_fingerprint_version=(
            request.producer_event_fingerprint_version
        ),
        failure_code=(terminal_code if target in _FAILURE_PREFIXES else None),
        abstention_code=(
            terminal_code if target == RunState.ABSTAINED else None
        ),
        cancellation_code=(
            terminal_code if target == RunState.CANCELLED else None
        ),
    )


def _projection_updates(
    decision: TransitionDecision, occurred_at: datetime
) -> dict[str, object]:
    next_snapshot = decision.next_snapshot
    assert next_snapshot is not None
    terminal = next_snapshot.state in TERMINAL_STATES
    actor = decision.actor
    return {
        "state": next_snapshot.state.value,
        "repair_attempts_used": next_snapshot.repair_attempts_used,
        "retry_attempts_used": next_snapshot.retry_attempts_used,
        "terminal_at": occurred_at if terminal else None,
        "terminal_actor_type": actor.actor_type.value if terminal and actor else None,
        "terminal_actor_id": actor.identifier if terminal and actor else None,
        "failure_code": (
            decision.terminal_code
            if next_snapshot.state in _FAILURE_PREFIXES
            else None
        ),
        "abstention_code": (
            decision.terminal_code
            if next_snapshot.state == RunState.ABSTAINED
            else None
        ),
        "cancellation_code": (
            decision.terminal_code
            if next_snapshot.state == RunState.CANCELLED
            else None
        ),
    }


def _requested_terminal_code(request: PersistentTransitionRequest) -> str | None:
    context = request.transition_context
    if request.requested_target in _FAILURE_PREFIXES:
        return context.failure_code
    if request.requested_target == RunState.ABSTAINED:
        return (
            context.abstention_code.value
            if isinstance(context.abstention_code, AbstentionCode)
            else context.abstention_code
        )
    if request.requested_target == RunState.CANCELLED:
        return (
            context.cancellation_code.value
            if isinstance(context.cancellation_code, CancellationCode)
            else context.cancellation_code
        )
    return None


def _human_disposition(value: object) -> HumanDisposition | None:
    try:
        return HumanDisposition(value)
    except (TypeError, ValueError):
        return None


def _validate_terminal_shape(run: Run, state: RunState) -> None:
    terminal_facts = (
        run.terminal_at,
        run.terminal_actor_type,
        run.terminal_actor_id,
        run.failure_code,
        run.abstention_code,
        run.cancellation_code,
    )
    if state not in TERMINAL_STATES:
        if any(value is not None for value in terminal_facts):
            raise InvalidDurableStateError(
                "non-terminal durable run carries terminal facts"
            )
        return
    if not isinstance(run.terminal_at, datetime):
        raise InvalidDurableStateError("terminal durable run lacks terminal_at")
    try:
        ActorRef(ActorType(run.terminal_actor_type), run.terminal_actor_id)
    except (TypeError, ValueError):
        raise InvalidDurableStateError(
            "terminal durable run has invalid actor attribution"
        ) from None

    if state in _FAILURE_PREFIXES:
        prefix = _FAILURE_PREFIXES[state]
        if not isinstance(run.failure_code, str) or re.fullmatch(
            rf"{prefix}_[A-Z0-9]+(?:_[A-Z0-9]+)*", run.failure_code
        ) is None:
            raise InvalidDurableStateError(
                "terminal durable run has incompatible failure code"
            )
        if run.abstention_code is not None or run.cancellation_code is not None:
            raise InvalidDurableStateError("terminal durable run mixes reason families")
    elif state == RunState.ABSTAINED:
        try:
            AbstentionCode(run.abstention_code)
        except (TypeError, ValueError):
            raise InvalidDurableStateError(
                "abstained durable run has invalid abstention code"
            ) from None
        if run.failure_code is not None or run.cancellation_code is not None:
            raise InvalidDurableStateError("terminal durable run mixes reason families")
    elif state == RunState.CANCELLED:
        try:
            CancellationCode(run.cancellation_code)
        except (TypeError, ValueError):
            raise InvalidDurableStateError(
                "cancelled durable run has invalid cancellation code"
            ) from None
        if run.failure_code is not None or run.abstention_code is not None:
            raise InvalidDurableStateError("terminal durable run mixes reason families")
    elif any(
        value is not None
        for value in (run.failure_code, run.abstention_code, run.cancellation_code)
    ):
        raise InvalidDurableStateError("completed durable run carries a terminal code")


def _validate_durable_terminal_semantics(
    run: Run, snapshot: LifecycleSnapshot
) -> None:
    if (
        snapshot.state == RunState.FAILED_INFRASTRUCTURE
        and snapshot.retry_attempts_used != snapshot.retry_limit
    ):
        raise InvalidDurableStateError(
            "failed infrastructure durable run has unexhausted retry budget"
        )
    if (
        snapshot.state == RunState.ABSTAINED
        and run.abstention_code == AbstentionCode.REPAIR_LIMIT_EXHAUSTED.value
        and snapshot.repair_attempts_used != 1
    ):
        raise InvalidDurableStateError(
            "repair-limit durable abstention has no consumed repair"
        )


def _bounded_text(name: str, value: object, maximum: int) -> None:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ValueError(f"{name} must be nonempty and at most {maximum} characters")


def _conflict(
    reason: PersistenceConflictReason,
    *,
    event_id: uuid.UUID | None = None,
    run_version: int | None = None,
) -> PersistentTransitionResult:
    return PersistentTransitionResult(
        PersistentTransitionStatus.CONFLICT,
        conflict_reason=reason,
        event_id=event_id,
        run_version=run_version,
    )
