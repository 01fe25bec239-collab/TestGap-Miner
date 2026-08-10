from dataclasses import FrozenInstanceError

import pytest

from app.workflow import (
    ALLOWED_TRANSITIONS,
    TERMINAL_STATES,
    WORKFLOW_CONTRACT_VERSION,
    AbstentionCode,
    ActorRef,
    ActorType,
    AttemptId,
    CancellationCode,
    HumanDisposition,
    LifecycleSnapshot,
    RejectionReason,
    RequestKind,
    RunState,
    TransitionContext,
    evaluate_transition,
    parse_run_state,
)


EXPECTED_TRANSITIONS = {
    RunState.RECEIVED: {RunState.VALIDATING, RunState.CANCELLED},
    RunState.VALIDATING: {
        RunState.QUEUED,
        RunState.FAILED_INPUT,
        RunState.FAILED_INFRASTRUCTURE,
        RunState.FAILED_SECURITY,
        RunState.CANCELLED,
    },
    RunState.QUEUED: {
        RunState.PLANNING,
        RunState.FAILED_INFRASTRUCTURE,
        RunState.FAILED_SECURITY,
        RunState.CANCELLED,
    },
    RunState.PLANNING: {
        RunState.LOCALISING,
        RunState.ABSTAINED,
        RunState.FAILED_MODEL,
        RunState.FAILED_INFRASTRUCTURE,
        RunState.FAILED_SECURITY,
        RunState.CANCELLED,
    },
    RunState.LOCALISING: {
        RunState.GENERATING,
        RunState.ABSTAINED,
        RunState.FAILED_MODEL,
        RunState.FAILED_INFRASTRUCTURE,
        RunState.FAILED_SECURITY,
        RunState.CANCELLED,
    },
    RunState.GENERATING: {
        RunState.EXECUTING_BUGGY,
        RunState.ABSTAINED,
        RunState.FAILED_MODEL,
        RunState.FAILED_INFRASTRUCTURE,
        RunState.FAILED_SECURITY,
        RunState.CANCELLED,
    },
    RunState.EXECUTING_BUGGY: {
        RunState.EXECUTING_FIXED,
        RunState.REPAIRING,
        RunState.ABSTAINED,
        RunState.FAILED_EXECUTION,
        RunState.FAILED_INFRASTRUCTURE,
        RunState.FAILED_SECURITY,
        RunState.CANCELLED,
    },
    RunState.EXECUTING_FIXED: {
        RunState.REPAIRING,
        RunState.SCORING,
        RunState.ABSTAINED,
        RunState.FAILED_EXECUTION,
        RunState.FAILED_INFRASTRUCTURE,
        RunState.FAILED_SECURITY,
        RunState.CANCELLED,
    },
    RunState.REPAIRING: {
        RunState.EXECUTING_BUGGY,
        RunState.ABSTAINED,
        RunState.FAILED_MODEL,
        RunState.FAILED_INFRASTRUCTURE,
        RunState.FAILED_SECURITY,
        RunState.CANCELLED,
    },
    RunState.SCORING: {
        RunState.PUBLISHING,
        RunState.AWAITING_HUMAN_REVIEW,
        RunState.COMPLETED,
        RunState.ABSTAINED,
        RunState.FAILED_INFRASTRUCTURE,
        RunState.FAILED_SECURITY,
        RunState.CANCELLED,
    },
    RunState.PUBLISHING: {
        RunState.AWAITING_HUMAN_REVIEW,
        RunState.COMPLETED,
        RunState.FAILED_INFRASTRUCTURE,
        RunState.FAILED_SECURITY,
        RunState.CANCELLED,
    },
    RunState.AWAITING_HUMAN_REVIEW: {RunState.COMPLETED},
    RunState.COMPLETED: set(),
    RunState.ABSTAINED: set(),
    RunState.FAILED_INPUT: set(),
    RunState.FAILED_MODEL: set(),
    RunState.FAILED_EXECUTION: set(),
    RunState.FAILED_INFRASTRUCTURE: set(),
    RunState.FAILED_SECURITY: set(),
    RunState.CANCELLED: set(),
}

SYSTEM = ActorRef(ActorType.SYSTEM, "system:test")
HUMAN = ActorRef(ActorType.HUMAN, "human:test")
FAILURE_CODE = {
    RunState.FAILED_INPUT: "INPUT_MALFORMED",
    RunState.FAILED_MODEL: "MODEL_OUTPUT_INVALID",
    RunState.FAILED_EXECUTION: "EXECUTION_COMPILE_ERROR",
    RunState.FAILED_INFRASTRUCTURE: "INFRASTRUCTURE_QUEUE",
    RunState.FAILED_SECURITY: "SECURITY_TOOL_POLICY_VIOLATION",
}


def snapshot(
    state: RunState,
    *,
    repair_attempts_used: int | None = None,
    retry_attempts_used: int = 0,
    retry_limit: int = 2,
    request_kind: RequestKind = RequestKind.GITHUB,
    review_required: bool = True,
) -> LifecycleSnapshot:
    return LifecycleSnapshot(
        state=state,
        repair_attempts_used=(
            1
            if repair_attempts_used is None and state == RunState.REPAIRING
            else repair_attempts_used or 0
        ),
        retry_attempts_used=retry_attempts_used,
        retry_limit=retry_limit,
        request_kind=request_kind,
        review_required=review_required,
        current_attempt_id=AttemptId("attempt:current"),
    )


def valid_context(target: RunState, source: RunState) -> TransitionContext:
    if target == RunState.REPAIRING:
        return TransitionContext(repairable_failure_recorded=True)
    if target in FAILURE_CODE:
        return TransitionContext(actor=SYSTEM, failure_code=FAILURE_CODE[target])
    if target == RunState.ABSTAINED:
        return TransitionContext(
            actor=SYSTEM, abstention_code=AbstentionCode.INSUFFICIENT_CONTEXT
        )
    if target == RunState.CANCELLED:
        return TransitionContext(
            actor=SYSTEM, cancellation_code=CancellationCode.USER_REQUESTED
        )
    if target == RunState.COMPLETED and source == RunState.AWAITING_HUMAN_REVIEW:
        return TransitionContext(
            actor=HUMAN, human_disposition=HumanDisposition.APPROVED
        )
    if target == RunState.COMPLETED:
        return TransitionContext(actor=SYSTEM, evidence_packaged=True)
    return TransitionContext()


def test_run_states_are_exact_and_declaration_order_is_not_transition_order() -> None:
    assert [state.value for state in RunState] == [
        "RECEIVED",
        "VALIDATING",
        "QUEUED",
        "PLANNING",
        "LOCALISING",
        "GENERATING",
        "EXECUTING_BUGGY",
        "EXECUTING_FIXED",
        "REPAIRING",
        "SCORING",
        "PUBLISHING",
        "AWAITING_HUMAN_REVIEW",
        "COMPLETED",
        "ABSTAINED",
        "FAILED_INPUT",
        "FAILED_MODEL",
        "FAILED_EXECUTION",
        "FAILED_INFRASTRUCTURE",
        "FAILED_SECURITY",
        "CANCELLED",
    ]
    assert {state: set(targets) for state, targets in ALLOWED_TRANSITIONS.items()} == (
        EXPECTED_TRANSITIONS
    )


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (source, target)
        for source, targets in EXPECTED_TRANSITIONS.items()
        for target in targets
    ],
)
def test_every_canonical_transition_is_accepted(
    source: RunState, target: RunState
) -> None:
    current = snapshot(
        source,
        retry_attempts_used=(
            2 if target == RunState.FAILED_INFRASTRUCTURE else 0
        ),
        request_kind=(
            RequestKind.BENCHMARK if target == RunState.COMPLETED else RequestKind.GITHUB
        ),
        review_required=(
            False
            if target == RunState.COMPLETED
            and source in {RunState.SCORING, RunState.PUBLISHING}
            else True
        ),
    )

    decision = evaluate_transition(current, target, valid_context(target, source))

    assert decision.accepted
    assert decision.previous_snapshot == current
    assert decision.next_snapshot is not None
    assert decision.next_snapshot.state == target
    assert decision.next_snapshot.run_version == current.run_version + 1


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (RunState.GENERATING, RunState.EXECUTING_FIXED),
        (RunState.REPAIRING, RunState.EXECUTING_FIXED),
        (RunState.RECEIVED, RunState.COMPLETED),
        (RunState.VALIDATING, RunState.PLANNING),
        (RunState.AWAITING_HUMAN_REVIEW, RunState.CANCELLED),
        (RunState.SCORING, RunState.GENERATING),
        (RunState.PUBLISHING, RunState.SCORING),
    ],
)
def test_forbidden_transition_boundaries(source: RunState, target: RunState) -> None:
    current = snapshot(source)

    decision = evaluate_transition(current, target, valid_context(target, source))

    assert not decision.accepted
    assert decision.previous_snapshot == current
    assert decision.next_snapshot is None


@pytest.mark.parametrize("state", list(RunState))
def test_every_self_transition_is_rejected(state: RunState) -> None:
    current = snapshot(state)
    decision = evaluate_transition(current, state)

    assert not decision.accepted
    assert decision.rejection_reason == RejectionReason.SELF_TRANSITION_NOT_ALLOWED
    assert decision.previous_snapshot == current
    assert decision.next_snapshot is None


@pytest.mark.parametrize("terminal", list(TERMINAL_STATES))
@pytest.mark.parametrize("target", list(RunState))
def test_every_terminal_state_rejects_every_outgoing_transition(
    terminal: RunState, target: RunState
) -> None:
    current = snapshot(terminal)
    decision = evaluate_transition(current, target, valid_context(target, terminal))

    assert not decision.accepted
    assert decision.previous_snapshot == current
    assert decision.next_snapshot is None


@pytest.mark.parametrize(
    ("source", "target", "accepted"),
    [
        (RunState.GENERATING, RunState.EXECUTING_BUGGY, True),
        (RunState.GENERATING, RunState.EXECUTING_FIXED, False),
        (RunState.REPAIRING, RunState.EXECUTING_BUGGY, True),
        (RunState.REPAIRING, RunState.EXECUTING_FIXED, False),
        (RunState.EXECUTING_BUGGY, RunState.EXECUTING_FIXED, True),
    ],
)
def test_buggy_fixed_ordering(
    source: RunState, target: RunState, accepted: bool
) -> None:
    decision = evaluate_transition(snapshot(source), target)
    assert decision.accepted is accepted


@pytest.mark.parametrize(
    "source", [RunState.EXECUTING_BUGGY, RunState.EXECUTING_FIXED]
)
def test_first_repair_consumes_exactly_one_allowance(source: RunState) -> None:
    current = snapshot(source, repair_attempts_used=0, retry_attempts_used=1)
    decision = evaluate_transition(
        current,
        RunState.REPAIRING,
        TransitionContext(repairable_failure_recorded=True),
    )

    assert decision.accepted
    assert decision.next_snapshot is not None
    assert decision.next_snapshot.repair_attempts_used == 1
    assert decision.next_snapshot.retry_attempts_used == 1


@pytest.mark.parametrize(
    "source", [RunState.EXECUTING_BUGGY, RunState.EXECUTING_FIXED]
)
def test_second_repair_is_rejected_without_mutation(source: RunState) -> None:
    current = snapshot(source, repair_attempts_used=1)
    decision = evaluate_transition(
        current,
        RunState.REPAIRING,
        TransitionContext(repairable_failure_recorded=True),
    )

    assert not decision.accepted
    assert decision.rejection_reason == RejectionReason.REPAIR_ALREADY_CONSUMED
    assert decision.previous_snapshot == current
    assert decision.next_snapshot is None


def test_repair_requires_a_recorded_repairable_failure() -> None:
    decision = evaluate_transition(
        snapshot(RunState.EXECUTING_BUGGY), RunState.REPAIRING
    )
    assert decision.rejection_reason == RejectionReason.REPAIR_FAILURE_NOT_RECORDED


@pytest.mark.parametrize(
    ("target", "context"),
    [
        (
            RunState.ABSTAINED,
            TransitionContext(
                actor=SYSTEM, abstention_code=AbstentionCode.REPAIR_LIMIT_EXHAUSTED
            ),
        ),
        (
            RunState.FAILED_MODEL,
            TransitionContext(actor=SYSTEM, failure_code="MODEL_OUTPUT_INVALID"),
        ),
        (
            RunState.FAILED_INFRASTRUCTURE,
            TransitionContext(actor=SYSTEM, failure_code="INFRASTRUCTURE_QUEUE"),
        ),
        (
            RunState.FAILED_SECURITY,
            TransitionContext(
                actor=SYSTEM, failure_code="SECURITY_TOOL_POLICY_VIOLATION"
            ),
        ),
        (
            RunState.CANCELLED,
            TransitionContext(
                actor=SYSTEM, cancellation_code=CancellationCode.USER_REQUESTED
            ),
        ),
    ],
)
def test_repair_terminal_exits_keep_consumed_allowance(
    target: RunState, context: TransitionContext
) -> None:
    decision = evaluate_transition(
        snapshot(
            RunState.REPAIRING,
            retry_attempts_used=(
                2 if target == RunState.FAILED_INFRASTRUCTURE else 0
            ),
        ),
        target,
        context,
    )
    assert decision.accepted
    assert decision.next_snapshot is not None
    assert decision.next_snapshot.repair_attempts_used == 1


KNOWN_FAILURES = {
    RunState.FAILED_INPUT: [
        "INPUT_MALFORMED",
        "INPUT_SOURCE_UNSUPPORTED",
        "INPUT_REFERENCE_INVALID",
        "INPUT_SCOPE_VIOLATION",
    ],
    RunState.FAILED_MODEL: [
        "MODEL_PROVIDER_UNAVAILABLE",
        "MODEL_OUTPUT_INVALID",
        "MODEL_BUDGET_EXHAUSTED",
        "MODEL_POLICY_REFUSAL",
    ],
    RunState.FAILED_EXECUTION: [
        "EXECUTION_COMPILE_ERROR",
        "EXECUTION_TIMEOUT",
        "EXECUTION_NONDETERMINISTIC",
        "EXECUTION_RUNNER_ERROR",
    ],
    RunState.FAILED_INFRASTRUCTURE: [
        "INFRASTRUCTURE_DATABASE",
        "INFRASTRUCTURE_OBJECT_STORE",
        "INFRASTRUCTURE_QUEUE",
        "INFRASTRUCTURE_CAPACITY",
        "INFRASTRUCTURE_RETRY_EXHAUSTED",
    ],
    RunState.FAILED_SECURITY: [
        "SECURITY_AUTHORIZATION_DENIED",
        "SECURITY_SECRET_DETECTED",
        "SECURITY_TOOL_POLICY_VIOLATION",
        "SECURITY_PRODUCTION_EDIT_ATTEMPT",
        "SECURITY_NETWORK_POLICY_VIOLATION",
    ],
}
FAILURE_SOURCE = {
    RunState.FAILED_INPUT: RunState.VALIDATING,
    RunState.FAILED_MODEL: RunState.PLANNING,
    RunState.FAILED_EXECUTION: RunState.EXECUTING_BUGGY,
    RunState.FAILED_INFRASTRUCTURE: RunState.VALIDATING,
    RunState.FAILED_SECURITY: RunState.VALIDATING,
}
INFRASTRUCTURE_FAILURE_SOURCES = [
    source
    for source, targets in EXPECTED_TRANSITIONS.items()
    if RunState.FAILED_INFRASTRUCTURE in targets
]


@pytest.mark.parametrize(
    ("target", "code"),
    [(target, code) for target, codes in KNOWN_FAILURES.items() for code in codes],
)
def test_every_known_failure_code_is_accepted(target: RunState, code: str) -> None:
    decision = evaluate_transition(
        snapshot(
            FAILURE_SOURCE[target],
            retry_attempts_used=(
                2 if target == RunState.FAILED_INFRASTRUCTURE else 0
            ),
        ),
        target,
        TransitionContext(actor=SYSTEM, failure_code=code),
    )
    assert decision.accepted
    assert decision.terminal_code == code
    assert decision.actor == SYSTEM


@pytest.mark.parametrize("target", list(KNOWN_FAILURES))
def test_additive_same_family_failure_code_is_accepted(target: RunState) -> None:
    prefix = target.value.removeprefix("FAILED_")
    code = f"{prefix}_PROVIDER_TEMPORARILY_UNAVAILABLE"
    decision = evaluate_transition(
        snapshot(
            FAILURE_SOURCE[target],
            retry_attempts_used=(
                2 if target == RunState.FAILED_INFRASTRUCTURE else 0
            ),
        ),
        target,
        TransitionContext(actor=SYSTEM, failure_code=code),
    )
    assert decision.accepted
    assert decision.terminal_code == code


@pytest.mark.parametrize(
    ("target", "wrong_code"),
    [
        (RunState.FAILED_EXECUTION, "MODEL_OUTPUT_INVALID"),
        (RunState.FAILED_SECURITY, "INFRASTRUCTURE_QUEUE"),
    ],
)
def test_cross_family_failure_code_is_rejected(
    target: RunState, wrong_code: str
) -> None:
    decision = evaluate_transition(
        snapshot(FAILURE_SOURCE[target]),
        target,
        TransitionContext(actor=SYSTEM, failure_code=wrong_code),
    )
    assert decision.rejection_reason == RejectionReason.FAILURE_CODE_STATE_MISMATCH


@pytest.mark.parametrize("target", list(KNOWN_FAILURES))
def test_missing_failure_code_is_rejected(target: RunState) -> None:
    decision = evaluate_transition(
        snapshot(FAILURE_SOURCE[target]), target, TransitionContext(actor=SYSTEM)
    )
    assert decision.rejection_reason == RejectionReason.FAILURE_CODE_REQUIRED


@pytest.mark.parametrize("source", INFRASTRUCTURE_FAILURE_SOURCES)
@pytest.mark.parametrize("retry_attempts_used", [0, 1])
def test_infrastructure_failure_rejects_remaining_retry_budget(
    source: RunState, retry_attempts_used: int
) -> None:
    current = snapshot(
        source,
        retry_attempts_used=retry_attempts_used,
        retry_limit=2,
    )
    decision = evaluate_transition(
        current,
        RunState.FAILED_INFRASTRUCTURE,
        TransitionContext(actor=SYSTEM, failure_code="INFRASTRUCTURE_DATABASE"),
    )

    assert not decision.accepted
    assert decision.rejection_reason == (
        RejectionReason.INFRASTRUCTURE_RETRY_BUDGET_REMAINS
    )
    assert decision.previous_snapshot == current
    assert decision.next_snapshot is None


@pytest.mark.parametrize("source", INFRASTRUCTURE_FAILURE_SOURCES)
@pytest.mark.parametrize(
    ("retry_attempts_used", "retry_limit"), [(2, 2), (0, 0)]
)
def test_infrastructure_failure_accepts_exhausted_retry_budget(
    source: RunState, retry_attempts_used: int, retry_limit: int
) -> None:
    decision = evaluate_transition(
        snapshot(
            source,
            retry_attempts_used=retry_attempts_used,
            retry_limit=retry_limit,
        ),
        RunState.FAILED_INFRASTRUCTURE,
        TransitionContext(actor=SYSTEM, failure_code="INFRASTRUCTURE_QUEUE"),
    )

    assert decision.accepted
    assert decision.next_snapshot is not None
    assert decision.next_snapshot.state == RunState.FAILED_INFRASTRUCTURE


def test_retry_exhausted_failure_code_rejects_remaining_retry_budget() -> None:
    decision = evaluate_transition(
        snapshot(RunState.PLANNING, retry_attempts_used=1, retry_limit=2),
        RunState.FAILED_INFRASTRUCTURE,
        TransitionContext(
            actor=SYSTEM, failure_code="INFRASTRUCTURE_RETRY_EXHAUSTED"
        ),
    )

    assert decision.rejection_reason == (
        RejectionReason.INFRASTRUCTURE_RETRY_BUDGET_REMAINS
    )


@pytest.mark.parametrize("code", list(AbstentionCode))
def test_every_abstention_code_is_accepted(code: AbstentionCode) -> None:
    repair_exhausted = code == AbstentionCode.REPAIR_LIMIT_EXHAUSTED
    decision = evaluate_transition(
        snapshot(
            RunState.EXECUTING_FIXED if repair_exhausted else RunState.PLANNING,
            repair_attempts_used=1 if repair_exhausted else 0,
        ),
        RunState.ABSTAINED,
        TransitionContext(actor=SYSTEM, abstention_code=code),
    )
    assert decision.accepted
    assert decision.terminal_code == code.value


@pytest.mark.parametrize(
    ("code", "reason"),
    [
        (None, RejectionReason.ABSTENTION_CODE_REQUIRED),
        ("UNKNOWN_ABSTENTION", RejectionReason.ABSTENTION_CODE_INVALID),
    ],
)
def test_missing_or_unknown_abstention_is_rejected(
    code: str | None, reason: RejectionReason
) -> None:
    decision = evaluate_transition(
        snapshot(RunState.PLANNING),
        RunState.ABSTAINED,
        TransitionContext(actor=SYSTEM, abstention_code=code),
    )
    assert decision.rejection_reason == reason


def test_repair_limit_abstention_does_not_restore_repair_allowance() -> None:
    current = snapshot(RunState.EXECUTING_FIXED, repair_attempts_used=1)
    decision = evaluate_transition(
        current,
        RunState.ABSTAINED,
        TransitionContext(
            actor=SYSTEM, abstention_code=AbstentionCode.REPAIR_LIMIT_EXHAUSTED
        ),
    )
    assert decision.accepted
    assert decision.next_snapshot is not None
    assert decision.next_snapshot.repair_attempts_used == 1


@pytest.mark.parametrize(
    "source",
    [
        RunState.PLANNING,
        RunState.EXECUTING_BUGGY,
        RunState.EXECUTING_FIXED,
        RunState.SCORING,
    ],
)
def test_repair_limit_abstention_requires_consumed_repair(
    source: RunState,
) -> None:
    current = snapshot(source, repair_attempts_used=0)
    decision = evaluate_transition(
        current,
        RunState.ABSTAINED,
        TransitionContext(
            actor=SYSTEM, abstention_code=AbstentionCode.REPAIR_LIMIT_EXHAUSTED
        ),
    )

    assert not decision.accepted
    assert decision.rejection_reason == RejectionReason.REPAIR_LIMIT_NOT_EXHAUSTED
    assert decision.previous_snapshot == current
    assert decision.next_snapshot is None


CANCELLABLE_STATES = [
    RunState.RECEIVED,
    RunState.VALIDATING,
    RunState.QUEUED,
    RunState.PLANNING,
    RunState.LOCALISING,
    RunState.GENERATING,
    RunState.EXECUTING_BUGGY,
    RunState.EXECUTING_FIXED,
    RunState.REPAIRING,
    RunState.SCORING,
    RunState.PUBLISHING,
]


@pytest.mark.parametrize("source", CANCELLABLE_STATES)
def test_cancellation_is_accepted_from_every_permitted_state(source: RunState) -> None:
    decision = evaluate_transition(
        snapshot(source),
        RunState.CANCELLED,
        TransitionContext(
            actor=SYSTEM,
            cancellation_code=CancellationCode.USER_REQUESTED,
            publication_side_effect_committed=False,
        ),
    )
    assert decision.accepted


@pytest.mark.parametrize("code", list(CancellationCode))
def test_every_cancellation_code_is_accepted(code: CancellationCode) -> None:
    decision = evaluate_transition(
        snapshot(RunState.RECEIVED),
        RunState.CANCELLED,
        TransitionContext(actor=SYSTEM, cancellation_code=code),
    )
    assert decision.accepted


def test_cancellation_after_publication_commit_is_rejected() -> None:
    decision = evaluate_transition(
        snapshot(RunState.PUBLISHING),
        RunState.CANCELLED,
        TransitionContext(
            actor=SYSTEM,
            cancellation_code=CancellationCode.USER_REQUESTED,
            publication_side_effect_committed=True,
        ),
    )
    assert decision.rejection_reason == (
        RejectionReason.CANCELLATION_AFTER_PUBLICATION_COMMIT
    )


def test_cancellation_after_review_boundary_is_rejected() -> None:
    decision = evaluate_transition(
        snapshot(RunState.AWAITING_HUMAN_REVIEW),
        RunState.CANCELLED,
        TransitionContext(
            actor=SYSTEM, cancellation_code=CancellationCode.USER_REQUESTED
        ),
    )
    assert decision.rejection_reason == (
        RejectionReason.CANCELLATION_AFTER_REVIEW_BOUNDARY
    )


@pytest.mark.parametrize(
    ("code", "reason"),
    [
        (None, RejectionReason.CANCELLATION_CODE_REQUIRED),
        ("UNKNOWN", RejectionReason.CANCELLATION_CODE_INVALID),
    ],
)
def test_missing_or_unknown_cancellation_code_is_rejected(
    code: str | None, reason: RejectionReason
) -> None:
    decision = evaluate_transition(
        snapshot(RunState.RECEIVED),
        RunState.CANCELLED,
        TransitionContext(actor=SYSTEM, cancellation_code=code),
    )
    assert decision.rejection_reason == reason


@pytest.mark.parametrize("source", [RunState.SCORING, RunState.PUBLISHING])
def test_no_review_benchmark_completion(source: RunState) -> None:
    decision = evaluate_transition(
        snapshot(
            source,
            request_kind=RequestKind.BENCHMARK,
            review_required=False,
        ),
        RunState.COMPLETED,
        TransitionContext(actor=SYSTEM, evidence_packaged=True),
    )
    assert decision.accepted


@pytest.mark.parametrize("source", [RunState.SCORING, RunState.PUBLISHING])
@pytest.mark.parametrize(
    ("request_kind", "review_required", "evidence_packaged", "actor", "reason"),
    [
        (
            RequestKind.GITHUB,
            False,
            True,
            SYSTEM,
            RejectionReason.BENCHMARK_COMPLETION_NOT_ALLOWED,
        ),
        (
            RequestKind.BENCHMARK,
            True,
            True,
            SYSTEM,
            RejectionReason.BENCHMARK_COMPLETION_NOT_ALLOWED,
        ),
        (
            RequestKind.BENCHMARK,
            False,
            False,
            SYSTEM,
            RejectionReason.BENCHMARK_EVIDENCE_NOT_PACKAGED,
        ),
        (
            RequestKind.BENCHMARK,
            False,
            True,
            None,
            RejectionReason.TERMINAL_ATTRIBUTION_REQUIRED,
        ),
    ],
)
def test_no_review_completion_guards(
    source: RunState,
    request_kind: RequestKind,
    review_required: bool,
    evidence_packaged: bool,
    actor: ActorRef | None,
    reason: RejectionReason,
) -> None:
    decision = evaluate_transition(
        snapshot(
            source,
            request_kind=request_kind,
            review_required=review_required,
        ),
        RunState.COMPLETED,
        TransitionContext(actor=actor, evidence_packaged=evidence_packaged),
    )
    assert decision.rejection_reason == reason


@pytest.mark.parametrize("disposition", list(HumanDisposition))
def test_every_human_disposition_completes_current_run(
    disposition: HumanDisposition,
) -> None:
    decision = evaluate_transition(
        snapshot(RunState.AWAITING_HUMAN_REVIEW),
        RunState.COMPLETED,
        TransitionContext(actor=HUMAN, human_disposition=disposition),
    )
    assert decision.accepted
    assert decision.next_snapshot is not None
    assert decision.next_snapshot.state == RunState.COMPLETED
    assert decision.human_disposition == disposition
    assert decision.actor == HUMAN
    assert decision.child_run_required is (
        disposition == HumanDisposition.REGENERATION_REQUESTED
    )


@pytest.mark.parametrize(
    ("context", "reason"),
    [
        (TransitionContext(actor=HUMAN), RejectionReason.HUMAN_DECISION_REQUIRED),
        (
            TransitionContext(actor=HUMAN, human_disposition="UNKNOWN"),
            RejectionReason.INVALID_HUMAN_DISPOSITION,
        ),
        (
            TransitionContext(human_disposition=HumanDisposition.APPROVED),
            RejectionReason.HUMAN_ATTRIBUTION_REQUIRED,
        ),
        (
            TransitionContext(
                actor=SYSTEM, human_disposition=HumanDisposition.APPROVED
            ),
            RejectionReason.HUMAN_ATTRIBUTION_REQUIRED,
        ),
    ],
)
def test_human_completion_guards(
    context: TransitionContext, reason: RejectionReason
) -> None:
    decision = evaluate_transition(
        snapshot(RunState.AWAITING_HUMAN_REVIEW), RunState.COMPLETED, context
    )
    assert decision.rejection_reason == reason


@pytest.mark.parametrize(
    ("value", "accepted", "reason"),
    [
        ("COMPLETED", True, None),
        ("FOO", False, RejectionReason.UNKNOWN_STATE),
        ("", False, RejectionReason.MALFORMED_STATE),
        ("completed", False, RejectionReason.UNKNOWN_STATE),
        (None, False, RejectionReason.MALFORMED_STATE),
        (7, False, RejectionReason.MALFORMED_STATE),
    ],
)
def test_external_state_parser_is_exact(
    value: object, accepted: bool, reason: RejectionReason | None
) -> None:
    result = parse_run_state(value)
    assert result.accepted is accepted
    assert result.rejection_reason == reason
    assert result.state == (RunState.COMPLETED if accepted else None)


def test_unknown_transition_target_is_a_semantic_rejection() -> None:
    current = snapshot(RunState.RECEIVED)
    decision = evaluate_transition(current, "FOO")
    assert decision.rejection_reason == RejectionReason.UNKNOWN_STATE
    assert decision.previous_snapshot == current


@pytest.mark.parametrize(
    "kwargs",
    [
        {"repair_attempts_used": -1},
        {"repair_attempts_used": 2},
        {"retry_attempts_used": -1},
        {"retry_limit": -1},
        {"retry_attempts_used": 3, "retry_limit": 2},
    ],
)
def test_invalid_snapshot_counters_fail_deterministically(
    kwargs: dict[str, int]
) -> None:
    with pytest.raises(ValueError):
        snapshot(RunState.RECEIVED, **kwargs)


@pytest.mark.parametrize("value", [True, False, 1.0, 0.0, -1, 2])
def test_repair_counter_requires_exact_bounded_integer(value: object) -> None:
    with pytest.raises(ValueError, match="repair_attempts_used"):
        LifecycleSnapshot(
            state=RunState.RECEIVED,
            repair_attempts_used=value,  # type: ignore[arg-type]
            retry_attempts_used=0,
            retry_limit=2,
            request_kind=RequestKind.GITHUB,
            review_required=True,
        )


@pytest.mark.parametrize("value", [0, 1])
def test_repair_counter_accepts_exact_bounded_integers(value: int) -> None:
    current = snapshot(RunState.EXECUTING_BUGGY, repair_attempts_used=value)
    assert current.repair_attempts_used == value


@pytest.mark.parametrize(
    "state",
    [
        RunState.RECEIVED,
        RunState.VALIDATING,
        RunState.QUEUED,
        RunState.PLANNING,
        RunState.LOCALISING,
        RunState.GENERATING,
        RunState.FAILED_INPUT,
    ],
)
def test_pre_repair_states_reject_consumed_repair_counter(state: RunState) -> None:
    with pytest.raises(ValueError, match=rf"{state.value} requires"):
        snapshot(state, repair_attempts_used=1)


@pytest.mark.parametrize("state", [RunState.EXECUTING_BUGGY, RunState.SCORING])
@pytest.mark.parametrize("repair_attempts_used", [0, 1])
def test_compatible_later_states_accept_repair_counter(
    state: RunState, repair_attempts_used: int
) -> None:
    current = snapshot(state, repair_attempts_used=repair_attempts_used)
    assert current.repair_attempts_used == repair_attempts_used


@pytest.mark.parametrize("value", [1, "yes", object()])
@pytest.mark.parametrize(
    "fact",
    [
        "repairable_failure_recorded",
        "evidence_packaged",
        "publication_side_effect_committed",
    ],
)
def test_owner_produced_facts_require_actual_booleans(
    fact: str, value: object
) -> None:
    with pytest.raises(TypeError, match=rf"{fact} must be a bool"):
        TransitionContext(**{fact: value})  # type: ignore[arg-type]


@pytest.mark.parametrize("field", ["actor", "attempt_id"])
def test_optional_domain_references_require_typed_values(field: str) -> None:
    with pytest.raises(TypeError):
        TransitionContext(**{field: "raw"})  # type: ignore[arg-type]


def test_repairing_snapshot_requires_consumed_allowance() -> None:
    with pytest.raises(ValueError, match="repair allowance"):
        snapshot(RunState.REPAIRING, repair_attempts_used=0)


def test_domain_values_are_immutable_and_opaque_identities_are_nonempty() -> None:
    current = snapshot(RunState.RECEIVED)
    with pytest.raises(FrozenInstanceError):
        current.state = RunState.VALIDATING  # type: ignore[misc]
    with pytest.raises(ValueError):
        AttemptId("  ")
    with pytest.raises(ValueError):
        ActorRef(ActorType.SYSTEM, "")
    assert current.contract_version == WORKFLOW_CONTRACT_VERSION


def test_terminal_transition_requires_attribution() -> None:
    decision = evaluate_transition(
        snapshot(RunState.PLANNING),
        RunState.ABSTAINED,
        TransitionContext(abstention_code=AbstentionCode.INSUFFICIENT_CONTEXT),
    )
    assert decision.rejection_reason == RejectionReason.TERMINAL_ATTRIBUTION_REQUIRED


def test_transition_carries_caller_owned_attempt_identity() -> None:
    attempt = AttemptId("attempt:next")
    decision = evaluate_transition(
        snapshot(RunState.RECEIVED),
        RunState.VALIDATING,
        TransitionContext(attempt_id=attempt),
    )
    assert decision.accepted
    assert decision.attempt_id == attempt


def test_successful_human_review_acceptance_fixture() -> None:
    current = snapshot(RunState.RECEIVED)
    path = [
        RunState.VALIDATING,
        RunState.QUEUED,
        RunState.PLANNING,
        RunState.LOCALISING,
        RunState.GENERATING,
        RunState.EXECUTING_BUGGY,
        RunState.EXECUTING_FIXED,
        RunState.SCORING,
        RunState.PUBLISHING,
        RunState.AWAITING_HUMAN_REVIEW,
        RunState.COMPLETED,
    ]

    for target in path:
        context = (
            TransitionContext(
                actor=HUMAN, human_disposition=HumanDisposition.APPROVED
            )
            if target == RunState.COMPLETED
            else TransitionContext()
        )
        decision = evaluate_transition(current, target, context)
        assert decision.accepted
        assert decision.next_snapshot is not None
        current = decision.next_snapshot

    assert current.state == RunState.COMPLETED


@pytest.mark.parametrize(
    "source", [RunState.EXECUTING_BUGGY, RunState.EXECUTING_FIXED]
)
def test_single_repair_success_acceptance_fixture(source: RunState) -> None:
    repair = evaluate_transition(
        snapshot(source),
        RunState.REPAIRING,
        TransitionContext(repairable_failure_recorded=True),
    )
    assert repair.accepted and repair.next_snapshot is not None

    buggy = evaluate_transition(repair.next_snapshot, RunState.EXECUTING_BUGGY)
    assert buggy.accepted and buggy.next_snapshot is not None

    fixed = evaluate_transition(buggy.next_snapshot, RunState.EXECUTING_FIXED)
    assert fixed.accepted and fixed.next_snapshot is not None
    assert fixed.next_snapshot.repair_attempts_used == 1
