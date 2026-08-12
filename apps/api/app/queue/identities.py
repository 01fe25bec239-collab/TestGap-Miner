"""Separately typed logical identities at the Queue boundary."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class _Identity:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise ValueError(f"{type(self).__name__} must be a nonempty string")


@dataclass(frozen=True, slots=True)
class SemanticRequestId(_Identity):
    pass


@dataclass(frozen=True, slots=True)
class QueueMessageId(_Identity):
    pass


@dataclass(frozen=True, slots=True)
class QueueDeliveryId(_Identity):
    pass


@dataclass(frozen=True, slots=True)
class ClaimOrLeaseId(_Identity):
    pass


@dataclass(frozen=True, slots=True)
class PublicationIdentity(_Identity):
    pass


@dataclass(frozen=True, slots=True)
class QueueProducerServiceReference(_Identity):
    pass


@dataclass(frozen=True, slots=True)
class WorkerServiceReference(_Identity):
    pass


@dataclass(frozen=True, slots=True)
class WorkflowAttemptId(_Identity):
    """Workflow-owned identity; Queue may only receive and reference it."""


@dataclass(frozen=True, slots=True)
class ProducerResultId(_Identity):
    """Execution/Workflow-owned identity; Queue may only reference it."""


@dataclass(frozen=True, slots=True)
class CorrelationId(_Identity):
    pass


@dataclass(frozen=True, slots=True)
class CausationId(_Identity):
    pass
