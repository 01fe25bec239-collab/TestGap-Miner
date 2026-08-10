"""Pure transition and retry decisions for Workflow lifecycle state."""

from __future__ import annotations

import re
from dataclasses import replace
from types import MappingProxyType
from typing import Final

from .types import (
    AbstentionCode,
    ActorRef,
    ActorType,
    AttemptId,
    CancellationCode,
    HumanDisposition,
    LifecycleSnapshot,
    RejectionReason,
    RequestKind,
    RetryDecision,
    RetryKind,
    RunState,
    StateParseResult,
    TransitionContext,
    TransitionDecision,
)


TERMINAL_STATES: Final = frozenset(
    {
        RunState.COMPLETED,
        RunState.ABSTAINED,
        RunState.FAILED_INPUT,
        RunState.FAILED_MODEL,
        RunState.FAILED_EXECUTION,
        RunState.FAILED_INFRASTRUCTURE,
        RunState.FAILED_SECURITY,
        RunState.CANCELLED,
    }
)

ALLOWED_TRANSITIONS: Final = MappingProxyType({
    RunState.RECEIVED: frozenset({RunState.VALIDATING, RunState.CANCELLED}),
    RunState.VALIDATING: frozenset(
        {
            RunState.QUEUED,
            RunState.FAILED_INPUT,
            RunState.FAILED_INFRASTRUCTURE,
            RunState.FAILED_SECURITY,
            RunState.CANCELLED,
        }
    ),
    RunState.QUEUED: frozenset(
        {
            RunState.PLANNING,
            RunState.FAILED_INFRASTRUCTURE,
            RunState.FAILED_SECURITY,
            RunState.CANCELLED,
        }
    ),
    RunState.PLANNING: frozenset(
        {
            RunState.LOCALISING,
            RunState.ABSTAINED,
            RunState.FAILED_MODEL,
            RunState.FAILED_INFRASTRUCTURE,
            RunState.FAILED_SECURITY,
            RunState.CANCELLED,
        }
    ),
    RunState.LOCALISING: frozenset(
        {
            RunState.GENERATING,
            RunState.ABSTAINED,
            RunState.FAILED_MODEL,
            RunState.FAILED_INFRASTRUCTURE,
            RunState.FAILED_SECURITY,
            RunState.CANCELLED,
        }
    ),
    RunState.GENERATING: frozenset(
        {
            RunState.EXECUTING_BUGGY,
            RunState.ABSTAINED,
            RunState.FAILED_MODEL,
            RunState.FAILED_INFRASTRUCTURE,
            RunState.FAILED_SECURITY,
            RunState.CANCELLED,
        }
    ),
    RunState.EXECUTING_BUGGY: frozenset(
        {
            RunState.EXECUTING_FIXED,
            RunState.REPAIRING,
            RunState.ABSTAINED,
            RunState.FAILED_EXECUTION,
            RunState.FAILED_INFRASTRUCTURE,
            RunState.FAILED_SECURITY,
            RunState.CANCELLED,
        }
    ),
    RunState.EXECUTING_FIXED: frozenset(
        {
            RunState.REPAIRING,
            RunState.SCORING,
            RunState.ABSTAINED,
            RunState.FAILED_EXECUTION,
            RunState.FAILED_INFRASTRUCTURE,
            RunState.FAILED_SECURITY,
            RunState.CANCELLED,
        }
    ),
    RunState.REPAIRING: frozenset(
        {
            RunState.EXECUTING_BUGGY,
            RunState.ABSTAINED,
            RunState.FAILED_MODEL,
            RunState.FAILED_INFRASTRUCTURE,
            RunState.FAILED_SECURITY,
            RunState.CANCELLED,
        }
    ),
    RunState.SCORING: frozenset(
        {
            RunState.PUBLISHING,
            RunState.AWAITING_HUMAN_REVIEW,
            RunState.COMPLETED,
            RunState.ABSTAINED,
            RunState.FAILED_INFRASTRUCTURE,
            RunState.FAILED_SECURITY,
            RunState.CANCELLED,
        }
    ),
    RunState.PUBLISHING: frozenset(
        {
            RunState.AWAITING_HUMAN_REVIEW,
            RunState.COMPLETED,
            RunState.FAILED_INFRASTRUCTURE,
            RunState.FAILED_SECURITY,
            RunState.CANCELLED,
        }
    ),
    RunState.AWAITING_HUMAN_REVIEW: frozenset({RunState.COMPLETED}),
    **{state: frozenset() for state in TERMINAL_STATES},
})

_FAILURE_PREFIXES: Final = MappingProxyType({
    RunState.FAILED_INPUT: "INPUT",
    RunState.FAILED_MODEL: "MODEL",
    RunState.FAILED_EXECUTION: "EXECUTION",
    RunState.FAILED_INFRASTRUCTURE: "INFRASTRUCTURE",
    RunState.FAILED_SECURITY: "SECURITY",
})


def parse_run_state(value: object) -> StateParseResult:
    """Parse an external state value without coercing case or unknown values."""

    if isinstance(value, RunState):
        return StateParseResult(True, value, None)
    if not isinstance(value, str) or not value:
        return StateParseResult(False, None, RejectionReason.MALFORMED_STATE)
    try:
        return StateParseResult(True, RunState(value), None)
    except ValueError:
        return StateParseResult(False, None, RejectionReason.UNKNOWN_STATE)


def evaluate_transition(
    current_snapshot: LifecycleSnapshot,
    requested_target: object,
    semantic_context: TransitionContext | None = None,
) -> TransitionDecision:
    """Evaluate one requested lifecycle transition without side effects."""

    context = semantic_context or TransitionContext()
    parsed = parse_run_state(requested_target)
    if not parsed.accepted:
        return _transition_rejection(current_snapshot, parsed.rejection_reason)
    target = parsed.state
    assert target is not None

    current = current_snapshot.state
    if target == current:
        return _transition_rejection(
            current_snapshot, RejectionReason.SELF_TRANSITION_NOT_ALLOWED
        )
    if current in TERMINAL_STATES:
        return _transition_rejection(
            current_snapshot, RejectionReason.TERMINAL_STATE_IMMUTABLE
        )
    if target == RunState.CANCELLED:
        cancellation_error = _validate_cancellation(current_snapshot, context)
        if cancellation_error is not None:
            return _transition_rejection(current_snapshot, cancellation_error)
    if current == RunState.REPAIRING and target == RunState.EXECUTING_FIXED:
        return _transition_rejection(
            current_snapshot, RejectionReason.REPAIR_SEQUENCE_VIOLATION
        )
    if target not in ALLOWED_TRANSITIONS[current]:
        return _transition_rejection(
            current_snapshot, RejectionReason.TRANSITION_NOT_ALLOWED
        )
    if target == RunState.REPAIRING:
        if current_snapshot.repair_attempts_used == 1:
            return _transition_rejection(
                current_snapshot, RejectionReason.REPAIR_ALREADY_CONSUMED
            )
        if not context.repairable_failure_recorded:
            return _transition_rejection(
                current_snapshot, RejectionReason.REPAIR_FAILURE_NOT_RECORDED
            )

    human_disposition: HumanDisposition | None = None
    child_run_required = False
    if current == RunState.AWAITING_HUMAN_REVIEW and target == RunState.COMPLETED:
        human_disposition, error = _validate_human_completion(context)
        if error is not None:
            return _transition_rejection(current_snapshot, error)
        child_run_required = (
            human_disposition == HumanDisposition.REGENERATION_REQUESTED
        )
    elif target == RunState.COMPLETED:
        if (
            current_snapshot.request_kind != RequestKind.BENCHMARK
            or current_snapshot.review_required
        ):
            return _transition_rejection(
                current_snapshot,
                RejectionReason.BENCHMARK_COMPLETION_NOT_ALLOWED,
            )
        if not context.evidence_packaged:
            return _transition_rejection(
                current_snapshot,
                RejectionReason.BENCHMARK_EVIDENCE_NOT_PACKAGED,
            )

    terminal_code: str | None = None
    if target in _FAILURE_PREFIXES:
        if context.failure_code is None:
            return _transition_rejection(
                current_snapshot, RejectionReason.FAILURE_CODE_REQUIRED
            )
        prefix = _FAILURE_PREFIXES[target]
        if not isinstance(context.failure_code, str) or re.fullmatch(
            rf"{prefix}_[A-Z0-9]+(?:_[A-Z0-9]+)*", context.failure_code
        ) is None:
            return _transition_rejection(
                current_snapshot, RejectionReason.FAILURE_CODE_STATE_MISMATCH
            )
        if (
            target == RunState.FAILED_INFRASTRUCTURE
            and current_snapshot.retry_attempts_used
            != current_snapshot.retry_limit
        ):
            return _transition_rejection(
                current_snapshot,
                RejectionReason.INFRASTRUCTURE_RETRY_BUDGET_REMAINS,
            )
        terminal_code = context.failure_code
    elif target == RunState.ABSTAINED:
        if context.abstention_code is None:
            return _transition_rejection(
                current_snapshot, RejectionReason.ABSTENTION_CODE_REQUIRED
            )
        abstention = _parse_enum(AbstentionCode, context.abstention_code)
        if abstention is None:
            return _transition_rejection(
                current_snapshot, RejectionReason.ABSTENTION_CODE_INVALID
            )
        if (
            abstention == AbstentionCode.REPAIR_LIMIT_EXHAUSTED
            and current_snapshot.repair_attempts_used != 1
        ):
            return _transition_rejection(
                current_snapshot, RejectionReason.REPAIR_LIMIT_NOT_EXHAUSTED
            )
        terminal_code = abstention.value
    elif target == RunState.CANCELLED:
        cancellation = _parse_enum(CancellationCode, context.cancellation_code)
        if cancellation is None:
            reason = (
                RejectionReason.CANCELLATION_CODE_REQUIRED
                if context.cancellation_code is None
                else RejectionReason.CANCELLATION_CODE_INVALID
            )
            return _transition_rejection(current_snapshot, reason)
        terminal_code = cancellation.value

    if target in TERMINAL_STATES and not isinstance(context.actor, ActorRef):
        return _transition_rejection(
            current_snapshot, RejectionReason.TERMINAL_ATTRIBUTION_REQUIRED
        )

    next_snapshot = replace(
        current_snapshot,
        state=target,
        repair_attempts_used=(
            1 if target == RunState.REPAIRING else current_snapshot.repair_attempts_used
        ),
        run_version=current_snapshot.run_version + 1,
    )
    return TransitionDecision(
        accepted=True,
        previous_snapshot=current_snapshot,
        next_snapshot=next_snapshot,
        rejection_reason=None,
        attempt_id=context.attempt_id,
        actor=context.actor,
        terminal_code=terminal_code,
        human_disposition=human_disposition,
        child_run_required=child_run_required,
    )


def schedule_retry(
    snapshot: LifecycleSnapshot,
    attempt_identity: AttemptId | None,
    retry_kind: RetryKind | object,
) -> RetryDecision:
    """Schedule one bounded retry attempt without changing lifecycle state."""

    if snapshot.state in TERMINAL_STATES:
        return _retry_rejection(snapshot, RejectionReason.TERMINAL_STATE_IMMUTABLE)
    if not isinstance(retry_kind, RetryKind):
        return _retry_rejection(snapshot, RejectionReason.INVALID_RETRY_KIND)
    if not isinstance(attempt_identity, AttemptId):
        return _retry_rejection(snapshot, RejectionReason.ATTEMPT_ID_REQUIRED)
    if attempt_identity == snapshot.current_attempt_id:
        return _retry_rejection(snapshot, RejectionReason.ATTEMPT_ID_NOT_DISTINCT)
    if snapshot.retry_attempts_used == snapshot.retry_limit:
        return _retry_rejection(snapshot, RejectionReason.RETRY_LIMIT_EXHAUSTED)
    return RetryDecision(
        accepted=True,
        previous_snapshot=snapshot,
        next_snapshot=replace(
            snapshot,
            retry_attempts_used=snapshot.retry_attempts_used + 1,
            current_attempt_id=attempt_identity,
            run_version=snapshot.run_version + 1,
        ),
        rejection_reason=None,
        attempt_id=attempt_identity,
        retry_kind=retry_kind,
    )


def _validate_cancellation(
    snapshot: LifecycleSnapshot, context: TransitionContext
) -> RejectionReason | None:
    if snapshot.state == RunState.AWAITING_HUMAN_REVIEW:
        return RejectionReason.CANCELLATION_AFTER_REVIEW_BOUNDARY
    if (
        snapshot.state == RunState.PUBLISHING
        and context.publication_side_effect_committed
    ):
        return RejectionReason.CANCELLATION_AFTER_PUBLICATION_COMMIT
    return None


def _validate_human_completion(
    context: TransitionContext,
) -> tuple[HumanDisposition | None, RejectionReason | None]:
    if context.human_disposition is None:
        return None, RejectionReason.HUMAN_DECISION_REQUIRED
    disposition = _parse_enum(HumanDisposition, context.human_disposition)
    if disposition is None:
        return None, RejectionReason.INVALID_HUMAN_DISPOSITION
    if not isinstance(context.actor, ActorRef) or (
        context.actor.actor_type != ActorType.HUMAN
    ):
        return None, RejectionReason.HUMAN_ATTRIBUTION_REQUIRED
    return disposition, None


def _parse_enum(enum_type, value):  # type: ignore[no-untyped-def]
    try:
        return enum_type(value)
    except (TypeError, ValueError):
        return None


def _transition_rejection(
    snapshot: LifecycleSnapshot, reason: RejectionReason | None
) -> TransitionDecision:
    assert reason is not None
    return TransitionDecision(False, snapshot, None, reason)


def _retry_rejection(
    snapshot: LifecycleSnapshot, reason: RejectionReason
) -> RetryDecision:
    return RetryDecision(False, snapshot, None, reason)
