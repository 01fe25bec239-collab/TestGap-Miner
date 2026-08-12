"""Allowlist-first logical Queue envelope validation."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, fields
from typing import Final, TypeAlias

from .identities import (
    CausationId,
    ClaimOrLeaseId,
    CorrelationId,
    ProducerResultId,
    PublicationIdentity,
    QueueDeliveryId,
    QueueMessageId,
    QueueProducerServiceReference,
    SemanticRequestId,
    WorkerServiceReference,
    WorkflowAttemptId,
)
from .models import FailureClassification, PublicationState


QUEUE_CONTRACT_VERSION: Final = "1.0.0-draft.2"
MetadataScalar: TypeAlias = str | int | bool
SecurityPolicy: TypeAlias = Callable[[str, MetadataScalar], bool]


class QueueValidationError(ValueError):
    """An envelope failed closed validation."""


@dataclass(frozen=True, slots=True)
class QueueRuntimeLimits:
    """Injected limits; the Queue contract selects no production values."""

    max_field_length: int
    max_envelope_bytes: int
    max_metadata_items: int
    max_metadata_key_length: int
    max_metadata_value_length: int

    def __post_init__(self) -> None:
        for name in self.__slots__:
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True, slots=True)
class QueueEnvelope:
    contract_version: str
    schema_version: str
    semantic_request_id: SemanticRequestId
    queue_message_id: QueueMessageId
    operation_kind: str
    queue_producer_service_reference: QueueProducerServiceReference
    publication_actor_reference: str
    requester_actor_reference: str
    authorization_context_reference: str
    policy_version: str
    queue_delivery_id: QueueDeliveryId | None = None
    correlation_id: CorrelationId | None = None
    causation_id: CausationId | None = None
    workflow_attempt_id: WorkflowAttemptId | None = None
    claim_or_lease_id: ClaimOrLeaseId | None = None
    worker_service_reference: WorkerServiceReference | None = None
    fence: int | None = None
    producer_result_id: ProducerResultId | None = None
    evidence_reference_id: str | None = None
    input_reference: str | None = None
    checkpoint_reference: str | None = None
    result_reference: str | None = None
    result_phase_or_slot_reference: str | None = None
    publication_identity: PublicationIdentity | None = None
    publication_state: str | None = None
    delivery_attempt_metadata: int | None = None
    retry_classification: str | None = None
    cancellation_actor_reference: str | None = None
    cancellation_intent_reference: str | None = None
    replay_or_redrive_actor_reference: str | None = None
    original_provenance_reference: str | None = None
    integrity_metadata: str | None = None
    bounded_metadata: tuple[tuple[str, MetadataScalar], ...] = ()


_REQUIRED_FIELDS = frozenset(
    {
        "contract_version",
        "schema_version",
        "semantic_request_id",
        "queue_message_id",
        "operation_kind",
        "queue_producer_service_reference",
        "publication_actor_reference",
        "requester_actor_reference",
        "authorization_context_reference",
        "policy_version",
    }
)
_ALLOWED_FIELDS = frozenset(QueueEnvelope.__dataclass_fields__)
_PROHIBITED_FIELDS = frozenset(
    {
        "payload",
        "credentials",
        "bearer_token",
        "access_token",
        "refresh_token",
        "cookie",
        "cookies",
        "authorization",
        "authorization_header",
        "private_key",
        "signing_key",
        "encryption_key",
        "repository",
        "archive",
        "patch",
        "prompt",
        "model_context",
        "transcript",
        "logs",
        "evidence_bytes",
        "artefact_bytes",
        "command",
    }
)
_PROHIBITED_CONTENT_MARKERS = (
    "authorization:",
    "bearer ",
    "cookie:",
    "cookie=",
    "access_token",
    "refresh_token",
    "private_key",
    "signing_key",
    "encryption_key",
    "-----begin private key-----",
    "rm -rf",
    "raw command:",
    "prompt:",
    "prompt text",
    "diff --git",
    "@@ -",
    "--- a/",
    "+++ b/",
    "raw patch",
    "patch content",
    "patch/repository",
    "embedded patch",
    "raw repository",
    "repository content",
    "repository contents",
    "embedded repository",
    "full prompt",
    "model context",
    "model-context",
    "full transcript",
    "full log",
    "evidence bytes",
    "artefact bytes",
    "artifact bytes",
    "arbitrary command",
)
_IDENTITY_FIELDS = {
    "semantic_request_id": SemanticRequestId,
    "queue_message_id": QueueMessageId,
    "queue_delivery_id": QueueDeliveryId,
    "queue_producer_service_reference": QueueProducerServiceReference,
    "correlation_id": CorrelationId,
    "causation_id": CausationId,
    "workflow_attempt_id": WorkflowAttemptId,
    "claim_or_lease_id": ClaimOrLeaseId,
    "worker_service_reference": WorkerServiceReference,
    "producer_result_id": ProducerResultId,
    "publication_identity": PublicationIdentity,
}


@dataclass(frozen=True, slots=True)
class EnvelopeValidator:
    supported_schema_versions: frozenset[str]
    allowed_operations: frozenset[str]
    allowed_metadata_keys: frozenset[str]
    limits: QueueRuntimeLimits
    security_policy: SecurityPolicy | None = None

    def __post_init__(self) -> None:
        for name in (
            "supported_schema_versions",
            "allowed_operations",
            "allowed_metadata_keys",
        ):
            if not isinstance(getattr(self, name), frozenset):
                raise TypeError(f"{name} must be a frozenset")
        if not self.supported_schema_versions or not self.allowed_operations:
            raise ValueError("supported schemas and operations must be explicit")
        if self.allowed_metadata_keys & _PROHIBITED_FIELDS:
            raise ValueError("prohibited metadata keys cannot be allowlisted")
        if self.security_policy is not None and not callable(self.security_policy):
            raise TypeError("security_policy must be callable")

    def validate(self, raw: Mapping[str, object]) -> QueueEnvelope:
        if not isinstance(raw, Mapping):
            raise QueueValidationError("envelope must be a mapping")
        if any(not isinstance(key, str) for key in raw):
            raise QueueValidationError("envelope field names must be strings")
        fields = frozenset(raw)
        prohibited = fields & _PROHIBITED_FIELDS
        if prohibited:
            raise QueueValidationError(
                f"prohibited envelope fields: {sorted(prohibited)}"
            )
        unknown = fields - _ALLOWED_FIELDS
        if unknown:
            raise QueueValidationError(f"unknown envelope fields: {sorted(unknown)}")
        missing = _REQUIRED_FIELDS - fields
        if missing:
            raise QueueValidationError(f"missing envelope fields: {sorted(missing)}")
        if not isinstance(raw["contract_version"], str) or raw[
            "contract_version"
        ] != QUEUE_CONTRACT_VERSION:
            raise QueueValidationError("unsupported Queue contract version")
        if not isinstance(raw["schema_version"], str) or raw[
            "schema_version"
        ] not in self.supported_schema_versions:
            raise QueueValidationError("unsupported Queue schema version")
        if not isinstance(raw["operation_kind"], str) or raw[
            "operation_kind"
        ] not in self.allowed_operations:
            raise QueueValidationError("unknown operation kind")
        if raw.get("publication_state") is not None and raw[
            "publication_state"
        ] not in {state.value for state in PublicationState}:
            raise QueueValidationError("unknown publication state")
        if raw.get("retry_classification") is not None and raw[
            "retry_classification"
        ] not in {state.value for state in FailureClassification}:
            raise QueueValidationError("unknown retry classification")

        values = dict(raw)
        for name, identity_type in _IDENTITY_FIELDS.items():
            value = values.get(name)
            if value is not None:
                values[name] = self._identity(name, value, identity_type)
        seen_identities: dict[str, str] = {}
        for name in _IDENTITY_FIELDS:
            value = values.get(name)
            if value is None:
                continue
            prior = seen_identities.setdefault(value.value, name)
            if prior != name:
                raise QueueValidationError(
                    f"identity values are conflated: {prior} and {name}"
                )
        for name, value in values.items():
            if name == "bounded_metadata" or value is None:
                continue
            if name in {"fence", "delivery_attempt_metadata"}:
                if type(value) is not int or value < 0:
                    raise QueueValidationError(f"{name} must be non-negative")
            elif name not in _IDENTITY_FIELDS:
                self._bounded_string(name, value)
        if (values.get("claim_or_lease_id") is None) != (
            values.get("worker_service_reference") is None
        ):
            raise QueueValidationError("claim and worker references must appear together")
        if values.get("claim_or_lease_id") is not None and values.get("fence") is None:
            raise QueueValidationError("claimed work requires a fence")
        if values.get("fence") is not None and values.get("claim_or_lease_id") is None:
            raise QueueValidationError("a fence requires a claim")
        if values.get("claim_or_lease_id") is not None and values.get(
            "queue_delivery_id"
        ) is None:
            raise QueueValidationError("claimed work requires a delivery identity")
        self._conditional_groups(values)
        values["bounded_metadata"] = self._metadata(
            values.get("bounded_metadata", {})
        )
        size = sum(
            len(item.encode())
            for value in values.values()
            for item in self._serialized_scalars(value)
        )
        if size > self.limits.max_envelope_bytes:
            raise QueueValidationError("envelope exceeds its configured byte bound")
        return QueueEnvelope(**values)  # type: ignore[arg-type]

    def validate_envelope(self, envelope: QueueEnvelope) -> QueueEnvelope:
        """Defensively revalidate an already-constructed public-boundary value."""
        if type(envelope) is not QueueEnvelope:
            raise QueueValidationError("publication requires a QueueEnvelope")
        for name, identity_type in _IDENTITY_FIELDS.items():
            value = getattr(envelope, name)
            if value is not None and type(value) is not identity_type:
                raise QueueValidationError(
                    f"{name} must be exactly {identity_type.__name__}"
                )
        metadata = envelope.bounded_metadata
        if not isinstance(metadata, tuple) or any(
            not isinstance(pair, tuple) or len(pair) != 2 for pair in metadata
        ):
            raise QueueValidationError("bounded_metadata must be a normalized tuple")
        metadata_mapping = dict(metadata)
        if len(metadata_mapping) != len(metadata):
            raise QueueValidationError("bounded_metadata keys must be unique")
        raw = {field.name: getattr(envelope, field.name) for field in fields(envelope)}
        raw["bounded_metadata"] = metadata_mapping
        return self.validate(raw)

    def validate_reference(self, name: str, value: object) -> str:
        """Apply the Queue-owned bounded content boundary to an opaque reference."""
        self._bounded_string(name, value)
        return value  # type: ignore[return-value]

    def validate_identity(self, name: str, value: object, identity_type: type) -> object:
        """Validate a typed identity and its serialized value at a public boundary."""
        if type(value) is not identity_type:
            raise QueueValidationError(f"{name} must be exactly {identity_type.__name__}")
        self._bounded_string(name, value.value)
        return value

    def _identity(self, name: str, value: object, identity_type: type) -> object:
        if type(value) is identity_type:
            return self.validate_identity(name, value, identity_type)
        self._bounded_string(name, value)
        return identity_type(value)

    def _bounded_string(self, name: str, value: object) -> None:
        if not isinstance(value, str) or not value.strip():
            raise QueueValidationError(f"{name} must be a nonempty string")
        if len(value) > self.limits.max_field_length:
            raise QueueValidationError(f"{name} exceeds its configured bound")
        lowered = value.casefold()
        if any(marker in lowered for marker in _PROHIBITED_CONTENT_MARKERS):
            raise QueueValidationError(f"{name} contains prohibited content")
        if self.security_policy is not None and not self.security_policy(name, value):
            raise QueueValidationError("Security policy rejected serialized content")

    @staticmethod
    def _conditional_groups(values: Mapping[str, object]) -> None:
        result_fields = {
            "producer_result_id",
            "result_reference",
            "result_phase_or_slot_reference",
        }
        if any(values.get(name) is not None for name in result_fields):
            required = result_fields | {
                "workflow_attempt_id",
                "queue_delivery_id",
                "claim_or_lease_id",
                "worker_service_reference",
                "fence",
            }
            missing = sorted(name for name in required if values.get(name) is None)
            if missing:
                raise QueueValidationError(
                    f"result submission is missing bindings: {missing}"
                )

        cancellation = {
            "cancellation_actor_reference",
            "cancellation_intent_reference",
        }
        if any(values.get(name) is not None for name in cancellation) and any(
            values.get(name) is None for name in cancellation
        ):
            raise QueueValidationError(
                "cancellation actor and intent references must appear together"
            )

        redrive = {
            "replay_or_redrive_actor_reference",
            "original_provenance_reference",
            "queue_delivery_id",
        }
        if values.get("replay_or_redrive_actor_reference") is not None:
            missing = sorted(name for name in redrive if values.get(name) is None)
            if missing:
                raise QueueValidationError(
                    f"redrive is missing administrative bindings: {missing}"
                )

        publication = {"publication_identity", "publication_state"}
        if any(values.get(name) is not None for name in publication) and any(
            values.get(name) is None for name in publication
        ):
            raise QueueValidationError(
                "publication identity and state must appear together"
            )

        if (
            values.get("checkpoint_reference") is not None
            and values.get("workflow_attempt_id") is None
        ):
            raise QueueValidationError(
                "checkpoint reference requires a Workflow attempt binding"
            )

    def _metadata(self, value: object) -> tuple[tuple[str, MetadataScalar], ...]:
        if value in ({}, (), None):
            return ()
        if not isinstance(value, Mapping):
            raise QueueValidationError("bounded_metadata must be a mapping")
        if len(value) > self.limits.max_metadata_items:
            raise QueueValidationError("bounded_metadata exceeds its item bound")
        result: list[tuple[str, MetadataScalar]] = []
        for key, item in value.items():
            if not isinstance(key, str) or key not in self.allowed_metadata_keys:
                raise QueueValidationError("unknown metadata key")
            if key.casefold() in _PROHIBITED_FIELDS:
                raise QueueValidationError("prohibited metadata key")
            if len(key) > self.limits.max_metadata_key_length:
                raise QueueValidationError("metadata key exceeds its configured bound")
            if type(item) not in (str, int, bool):
                raise QueueValidationError("metadata values must be scalar")
            if len(str(item)) > self.limits.max_metadata_value_length:
                raise QueueValidationError(
                    "metadata value exceeds its configured bound"
                )
            if isinstance(item, str):
                lowered = item.casefold()
                if any(marker in lowered for marker in _PROHIBITED_CONTENT_MARKERS):
                    raise QueueValidationError("prohibited metadata content")
            if self.security_policy is not None and not self.security_policy(key, item):
                raise QueueValidationError("Security policy rejected metadata")
            result.append((key, item))
        return tuple(sorted(result))

    @staticmethod
    def _serialized_scalars(value: object) -> tuple[str, ...]:
        if value is None:
            return ()
        if hasattr(value, "value") and isinstance(value.value, str):
            return (value.value,)
        if isinstance(value, tuple):
            return tuple(str(item) for pair in value for item in pair)
        return (str(value),)
