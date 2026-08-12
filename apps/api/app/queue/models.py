"""Immutable provider-neutral Queue state and decision values."""

from dataclasses import dataclass
from enum import StrEnum

from .identities import (
    ClaimOrLeaseId,
    ProducerResultId,
    PublicationIdentity,
    QueueDeliveryId,
    QueueMessageId,
    SemanticRequestId,
    WorkerServiceReference,
    WorkflowAttemptId,
)


class QueueConflictError(ValueError):
    """A stable Queue identity was presented with a conflicting binding."""


class QueueStateError(ValueError):
    """A requested Queue transition is not currently allowed."""


class PublicationState(StrEnum):
    NOT_ATTEMPTED = "publication_not_attempted"
    REJECTED_BEFORE_ACCEPTANCE = "publication_rejected_before_acceptance"
    CONFIRMED_FAILURE = "confirmed_publication_failure"
    RESULT_UNCERTAIN = "publication_result_uncertain"
    CONFIRMED_SUCCESS = "confirmed_publication_success"
    CONFIRMED_DUPLICATE_REQUEST = "confirmed_duplicate_publication_request"


class ClaimState(StrEnum):
    CURRENT = "current_valid_claim"
    REPLACED = "replaced_claim"
    REVOKED = "revoked_claim"
    RENEWAL_UNCERTAIN = "renewal_uncertain"
    CONFIRMED_LEASE_LOST = "confirmed_lease_loss"


class ControlState(StrEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    REVOKED = "revoked"
    DELETED = "deleted_tombstoned"
    SUPERSEDED = "superseded"


class DurableEffect(StrEnum):
    ACCEPTED_RESULT = "accepted_result"
    WORKFLOW_STATE = "workflow_state_effect"
    PROVENANCE = "provenance"
    AUDIT = "audit"
    EVIDENCE_REFERENCE = "evidence_reference"


class FailureClassification(StrEnum):
    TRANSPORT_RETRYABLE = "queue_transport_retryable_failure"
    POISON = "poison_unprocessable_queue_work"
    APPLICATION = "application_semantic_failure"
    SECURITY_REJECTION = "security_policy_rejection"


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Injected bounds; these values are not contract production defaults."""

    max_transport_attempts: int
    max_poison_attempts: int
    max_redrives: int

    def __post_init__(self) -> None:
        for name in self.__slots__:
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True, slots=True)
class PublicationRecord:
    publication_identity: PublicationIdentity
    semantic_request_id: SemanticRequestId
    queue_message_id: QueueMessageId
    state: PublicationState


@dataclass(frozen=True, slots=True)
class PublicationOutcomeRecord:
    publication_identity: PublicationIdentity
    state: PublicationState
    outcome_reference: str


@dataclass(frozen=True, slots=True)
class DeliveryRecord:
    queue_delivery_id: QueueDeliveryId
    semantic_request_id: SemanticRequestId
    queue_message_id: QueueMessageId
    workflow_attempt_id: WorkflowAttemptId | None
    original_provenance_reference: str
    provider_delivery_reference: str
    redelivery_number: int


@dataclass(frozen=True, slots=True)
class ClaimRecord:
    claim_or_lease_id: ClaimOrLeaseId
    queue_delivery_id: QueueDeliveryId
    worker_service_reference: WorkerServiceReference
    fence: int
    state: ClaimState


@dataclass(frozen=True, slots=True)
class ResultBinding:
    producer_result_id: ProducerResultId
    semantic_request_id: SemanticRequestId
    queue_message_id: QueueMessageId
    workflow_attempt_id: WorkflowAttemptId
    result_phase_or_slot_reference: str
    result_reference: str

    def __post_init__(self) -> None:
        expected = {
            "producer_result_id": ProducerResultId,
            "semantic_request_id": SemanticRequestId,
            "queue_message_id": QueueMessageId,
            "workflow_attempt_id": WorkflowAttemptId,
        }
        for name, identity_type in expected.items():
            if type(getattr(self, name)) is not identity_type:
                raise TypeError(f"{name} must be a {identity_type.__name__}")
        for name in ("result_phase_or_slot_reference", "result_reference"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a nonempty opaque reference")


@dataclass(frozen=True, slots=True)
class ResultSubmissionRecord:
    binding: ResultBinding
    submission_occurrence_reference: str
    queue_delivery_id: QueueDeliveryId
    worker_service_reference: WorkerServiceReference
    claim_or_lease_id: ClaimOrLeaseId
    fence: int
    contract_version: str
    schema_version: str
    integrity_metadata: str | None


@dataclass(frozen=True, slots=True)
class AdministrativeAuthorizationDecision:
    authorized: bool
    authorization_context_reference: str
    policy_version: str
    decision_reference: str

    def __post_init__(self) -> None:
        if type(self.authorized) is not bool:
            raise TypeError("authorized must be a bool")
        for name in (
            "authorization_context_reference",
            "policy_version",
            "decision_reference",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a nonempty opaque reference")


@dataclass(frozen=True, slots=True)
class RedriveRecord:
    replay_or_redrive_actor_reference: str
    original_provenance_reference: str
    source_queue_delivery_id: QueueDeliveryId
    source_queue_message_id: QueueMessageId
    semantic_request_id: SemanticRequestId
    new_queue_delivery_id: QueueDeliveryId
    source_failure_classification: FailureClassification
    authorization_context_reference: str
    policy_version: str
    authorization_decision_reference: str


@dataclass(frozen=True, slots=True)
class AckReadiness:
    execution_succeeded: bool
    ready_effects: frozenset[DurableEffect]

    def __post_init__(self) -> None:
        if type(self.execution_succeeded) is not bool:
            raise TypeError("execution_succeeded must be a bool")
        if not isinstance(self.ready_effects, frozenset) or any(
            not isinstance(effect, DurableEffect) for effect in self.ready_effects
        ):
            raise TypeError("ready_effects must be a frozenset of DurableEffect")


@dataclass(frozen=True, slots=True)
class RetryDecision:
    retry_allowed: bool
    dead_lettered: bool
    workflow_terminal: bool = False


@dataclass(frozen=True, slots=True)
class DeadLetterRecord:
    source_delivery: DeliveryRecord
    classification: FailureClassification
    workflow_terminal: bool = False
