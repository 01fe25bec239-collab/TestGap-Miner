"""Immutable domain values for the pure Workflow lifecycle runtime."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final


WORKFLOW_CONTRACT_VERSION: Final = "CONTRACT-WORKFLOW-001@1.0.0-draft.1"


class RunState(StrEnum):
    RECEIVED = "RECEIVED"
    VALIDATING = "VALIDATING"
    QUEUED = "QUEUED"
    PLANNING = "PLANNING"
    LOCALISING = "LOCALISING"
    GENERATING = "GENERATING"
    EXECUTING_BUGGY = "EXECUTING_BUGGY"
    EXECUTING_FIXED = "EXECUTING_FIXED"
    REPAIRING = "REPAIRING"
    SCORING = "SCORING"
    PUBLISHING = "PUBLISHING"
    AWAITING_HUMAN_REVIEW = "AWAITING_HUMAN_REVIEW"
    COMPLETED = "COMPLETED"
    ABSTAINED = "ABSTAINED"
    FAILED_INPUT = "FAILED_INPUT"
    FAILED_MODEL = "FAILED_MODEL"
    FAILED_EXECUTION = "FAILED_EXECUTION"
    FAILED_INFRASTRUCTURE = "FAILED_INFRASTRUCTURE"
    FAILED_SECURITY = "FAILED_SECURITY"
    CANCELLED = "CANCELLED"


class RequestKind(StrEnum):
    GITHUB = "GITHUB"
    BENCHMARK = "BENCHMARK"


class WorkflowStepKind(StrEnum):
    VALIDATE_INPUT = "VALIDATE_INPUT"
    PLAN = "PLAN"
    LOCALISE = "LOCALISE"
    GENERATE_CANDIDATE = "GENERATE_CANDIDATE"
    EXECUTE_BUGGY = "EXECUTE_BUGGY"
    EXECUTE_FIXED = "EXECUTE_FIXED"
    REPAIR_CANDIDATE = "REPAIR_CANDIDATE"
    SCORE_EVIDENCE = "SCORE_EVIDENCE"
    PUBLISH_DRAFT = "PUBLISH_DRAFT"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class ActorType(StrEnum):
    SYSTEM = "SYSTEM"
    WORKFLOW = "WORKFLOW"
    WORKER = "WORKER"
    HUMAN = "HUMAN"


class AbstentionCode(StrEnum):
    UNSUPPORTED_LANGUAGE_OR_TEST_FRAMEWORK = "UNSUPPORTED_LANGUAGE_OR_TEST_FRAMEWORK"
    BUG_NOT_REPRODUCED = "BUG_NOT_REPRODUCED"
    INSUFFICIENT_LOCALISATION_CONFIDENCE = "INSUFFICIENT_LOCALISATION_CONFIDENCE"
    INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"
    NO_SAFE_TEST_ONLY_PATCH = "NO_SAFE_TEST_ONLY_PATCH"
    REPAIR_LIMIT_EXHAUSTED = "REPAIR_LIMIT_EXHAUSTED"
    EVIDENCE_INCONCLUSIVE = "EVIDENCE_INCONCLUSIVE"
    PUBLICATION_NOT_JUSTIFIED = "PUBLICATION_NOT_JUSTIFIED"


class CancellationCode(StrEnum):
    USER_REQUESTED = "USER_REQUESTED"
    SUPERSEDED = "SUPERSEDED"
    OPERATOR_REQUESTED = "OPERATOR_REQUESTED"
    SYSTEM_SHUTDOWN = "SYSTEM_SHUTDOWN"


class HumanDisposition(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DISMISSED = "DISMISSED"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    REGENERATION_REQUESTED = "REGENERATION_REQUESTED"


class RetryKind(StrEnum):
    INFRASTRUCTURE = "INFRASTRUCTURE"
    TRANSPORT = "TRANSPORT"


class ResumeMode(StrEnum):
    CONTINUE_CURRENT_ATTEMPT = "CONTINUE_CURRENT_ATTEMPT"
    APPEND_BOUNDED_RETRY_ATTEMPT = "APPEND_BOUNDED_RETRY_ATTEMPT"


class RejectionReason(StrEnum):
    UNKNOWN_STATE = "UNKNOWN_STATE"
    MALFORMED_STATE = "MALFORMED_STATE"
    SELF_TRANSITION_NOT_ALLOWED = "SELF_TRANSITION_NOT_ALLOWED"
    TERMINAL_STATE_IMMUTABLE = "TERMINAL_STATE_IMMUTABLE"
    TRANSITION_NOT_ALLOWED = "TRANSITION_NOT_ALLOWED"
    TERMINAL_ATTRIBUTION_REQUIRED = "TERMINAL_ATTRIBUTION_REQUIRED"
    FAILURE_CODE_REQUIRED = "FAILURE_CODE_REQUIRED"
    FAILURE_CODE_STATE_MISMATCH = "FAILURE_CODE_STATE_MISMATCH"
    ABSTENTION_CODE_REQUIRED = "ABSTENTION_CODE_REQUIRED"
    ABSTENTION_CODE_INVALID = "ABSTENTION_CODE_INVALID"
    CANCELLATION_CODE_REQUIRED = "CANCELLATION_CODE_REQUIRED"
    CANCELLATION_CODE_INVALID = "CANCELLATION_CODE_INVALID"
    CANCELLATION_AFTER_REVIEW_BOUNDARY = "CANCELLATION_AFTER_REVIEW_BOUNDARY"
    CANCELLATION_AFTER_PUBLICATION_COMMIT = (
        "CANCELLATION_AFTER_PUBLICATION_COMMIT"
    )
    REPAIR_FAILURE_NOT_RECORDED = "REPAIR_FAILURE_NOT_RECORDED"
    REPAIR_ALREADY_CONSUMED = "REPAIR_ALREADY_CONSUMED"
    REPAIR_SEQUENCE_VIOLATION = "REPAIR_SEQUENCE_VIOLATION"
    REPAIR_LIMIT_NOT_EXHAUSTED = "REPAIR_LIMIT_NOT_EXHAUSTED"
    RETRY_LIMIT_EXHAUSTED = "RETRY_LIMIT_EXHAUSTED"
    INFRASTRUCTURE_RETRY_BUDGET_REMAINS = (
        "INFRASTRUCTURE_RETRY_BUDGET_REMAINS"
    )
    INVALID_RETRY_COUNTERS = "INVALID_RETRY_COUNTERS"
    INVALID_REPAIR_COUNTERS = "INVALID_REPAIR_COUNTERS"
    INVALID_RETRY_KIND = "INVALID_RETRY_KIND"
    BENCHMARK_COMPLETION_NOT_ALLOWED = "BENCHMARK_COMPLETION_NOT_ALLOWED"
    BENCHMARK_EVIDENCE_NOT_PACKAGED = "BENCHMARK_EVIDENCE_NOT_PACKAGED"
    HUMAN_DECISION_REQUIRED = "HUMAN_DECISION_REQUIRED"
    INVALID_HUMAN_DISPOSITION = "INVALID_HUMAN_DISPOSITION"
    HUMAN_ATTRIBUTION_REQUIRED = "HUMAN_ATTRIBUTION_REQUIRED"
    CHECKPOINT_NOT_COMMITTED = "CHECKPOINT_NOT_COMMITTED"
    CHECKPOINT_CHECKSUM_INVALID = "CHECKPOINT_CHECKSUM_INVALID"
    CHECKPOINT_VERSION_MISMATCH = "CHECKPOINT_VERSION_MISMATCH"
    CHECKPOINT_CONTRACT_INCOMPATIBLE = "CHECKPOINT_CONTRACT_INCOMPATIBLE"
    TERMINAL_RUN_CANNOT_RESUME = "TERMINAL_RUN_CANNOT_RESUME"
    INVALID_RESUME_MODE = "INVALID_RESUME_MODE"
    ATTEMPT_ID_REQUIRED = "ATTEMPT_ID_REQUIRED"
    ATTEMPT_ID_NOT_DISTINCT = "ATTEMPT_ID_NOT_DISTINCT"


@dataclass(frozen=True, slots=True)
class AttemptId:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise ValueError("attempt identity must be a nonempty string")


@dataclass(frozen=True, slots=True)
class ActorRef:
    actor_type: ActorType
    identifier: str

    def __post_init__(self) -> None:
        if not isinstance(self.actor_type, ActorType):
            raise TypeError("actor_type must be an ActorType")
        if not isinstance(self.identifier, str) or not self.identifier.strip():
            raise ValueError("actor identifier must be a nonempty string")


@dataclass(frozen=True, slots=True)
class LifecycleSnapshot:
    state: RunState
    repair_attempts_used: int
    retry_attempts_used: int
    retry_limit: int
    request_kind: RequestKind
    review_required: bool
    contract_version: str = WORKFLOW_CONTRACT_VERSION
    run_version: int = 0
    current_attempt_id: AttemptId | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.state, RunState):
            raise TypeError("state must be a RunState")
        if not isinstance(self.request_kind, RequestKind):
            raise TypeError("request_kind must be a RequestKind")
        if type(self.review_required) is not bool:
            raise TypeError("review_required must be a bool")
        if self.contract_version != WORKFLOW_CONTRACT_VERSION:
            raise ValueError("unsupported workflow contract version")
        if not _is_nonnegative_int(self.run_version):
            raise ValueError("run_version must be a non-negative integer")
        if not _repair_counter_is_valid_for_state(
            self.state, self.repair_attempts_used
        ):
            if not _valid_repair_counter(self.repair_attempts_used):
                raise ValueError("repair_attempts_used must be 0 or 1")
            if self.state == RunState.REPAIRING:
                raise ValueError(
                    "REPAIRING requires the repair allowance to be consumed"
                )
            raise ValueError(
                f"{self.state.value} requires repair_attempts_used to be 0"
            )
        if not _valid_retry_counters(
            self.retry_attempts_used, self.retry_limit
        ):
            raise ValueError("retry counters must satisfy 0 <= used <= limit")
        if self.current_attempt_id is not None and not isinstance(
            self.current_attempt_id, AttemptId
        ):
            raise TypeError("current_attempt_id must be an AttemptId")


@dataclass(frozen=True, slots=True)
class TransitionContext:
    actor: ActorRef | None = None
    attempt_id: AttemptId | None = None
    failure_code: str | None = None
    abstention_code: AbstentionCode | str | None = None
    cancellation_code: CancellationCode | str | None = None
    repairable_failure_recorded: bool = False
    publication_side_effect_committed: bool = False
    evidence_packaged: bool = False
    human_disposition: HumanDisposition | str | None = None

    def __post_init__(self) -> None:
        if self.actor is not None and not isinstance(self.actor, ActorRef):
            raise TypeError("actor must be an ActorRef")
        if self.attempt_id is not None and not isinstance(self.attempt_id, AttemptId):
            raise TypeError("attempt_id must be an AttemptId")
        for name in (
            "repairable_failure_recorded",
            "publication_side_effect_committed",
            "evidence_packaged",
        ):
            if type(getattr(self, name)) is not bool:
                raise TypeError(f"{name} must be a bool")


@dataclass(frozen=True, slots=True)
class StateParseResult:
    accepted: bool
    state: RunState | None
    rejection_reason: RejectionReason | None


@dataclass(frozen=True, slots=True)
class TransitionDecision:
    accepted: bool
    previous_snapshot: LifecycleSnapshot
    next_snapshot: LifecycleSnapshot | None
    rejection_reason: RejectionReason | None
    attempt_id: AttemptId | None = None
    actor: ActorRef | None = None
    terminal_code: str | None = None
    human_disposition: HumanDisposition | None = None
    child_run_required: bool = False


@dataclass(frozen=True, slots=True)
class RetryDecision:
    accepted: bool
    previous_snapshot: LifecycleSnapshot
    next_snapshot: LifecycleSnapshot | None
    rejection_reason: RejectionReason | None
    attempt_id: AttemptId | None = None
    retry_kind: RetryKind | None = None


def _is_nonnegative_int(value: object) -> bool:
    return type(value) is int and value >= 0


def _valid_repair_counter(value: object) -> bool:
    return type(value) is int and value in (0, 1)


def _repair_counter_is_valid_for_state(state: RunState, value: object) -> bool:
    if not _valid_repair_counter(value):
        return False
    if state == RunState.REPAIRING:
        return value == 1
    if state in {
        RunState.RECEIVED,
        RunState.VALIDATING,
        RunState.QUEUED,
        RunState.PLANNING,
        RunState.LOCALISING,
        RunState.GENERATING,
        RunState.FAILED_INPUT,
    }:
        return value == 0
    return True


def _valid_retry_counters(used: object, limit: object) -> bool:
    return _is_nonnegative_int(used) and _is_nonnegative_int(limit) and used <= limit
