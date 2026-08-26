"""Immutable Evidence-owned opaque reference binding for Queue-facing identity.

An ``EvidenceReference`` binds one caller-supplied ``EvidenceReferenceId``
to exactly one supported Evidence-owned target identity plus bounded
provenance/accepted-result context. The Queue-facing surface exposes only
the opaque ``EvidenceReferenceId``; Queue can never infer the underlying
semantic target type from it.

This is a logical semantic binding only: never persistence, object storage,
a storage locator, a signed URL, cryptographic proof, an authentication
token, or an authorization capability. Identity is caller-supplied and
never generated; provenance is retained exactly as supplied and never
manufactured. A historical ``evidence_reference_id`` is immutable here:
the same id bound to changed content is a conflict, never a rebinding.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Final

from .artefact import ArtefactId, ArtefactManifestId
from .decision import EvidenceBundleId, EvidenceCardId
from .execution import (
    EVIDENCE_CONTRACT_VERSION,
    CandidateVersionId,
    CorrelationId,
    EvidenceComparison,
    ExecutionEvidenceId,
    OpaqueReference,
    ProducerResultId,
    QueueDeliveryId,
    QueueMessageId,
    RunId,
    WorkflowAttemptId,
    _Identifier,
    _domain_value,
    _require_optional_type,
    _require_type,
)


_EvidenceReferenceTarget = (
    EvidenceBundleId
    | EvidenceCardId
    | ExecutionEvidenceId
    | ArtefactManifestId
    | ArtefactId
    | CandidateVersionId
)


_TARGET_KIND_BY_EXACT_TYPE: Final[dict[type[_Identifier], str]] = {
    EvidenceBundleId: "EVIDENCE_BUNDLE",
    EvidenceCardId: "EVIDENCE_CARD",
    ExecutionEvidenceId: "EXECUTION_EVIDENCE",
    ArtefactManifestId: "ARTEFACT_MANIFEST",
    ArtefactId: "ARTEFACT_REFERENCE",
    CandidateVersionId: "CANDIDATE_VERSION",
}

_SUPPORTED_TARGET_IDENTITY_NAMES: Final[str] = ", ".join(
    sorted(identity.__name__ for identity in _TARGET_KIND_BY_EXACT_TYPE)
)


class EvidenceReferenceId(_Identifier):
    """Evidence-owned opaque Queue-facing reference identity.

    Caller-supplied and never generated; distinct from every other
    Evidence, Workflow, Queue, and Execution identity namespace.
    """


def _validate_target(value: object) -> None:
    if not isinstance(value, _Identifier) or (
        type(value) not in _TARGET_KIND_BY_EXACT_TYPE
    ):
        raise TypeError(
            "target must be one of the supported Evidence-owned target "
            f"identities: {_SUPPORTED_TARGET_IDENTITY_NAMES}"
        )


def _target_kind_for(target: _Identifier) -> str:
    kind = _TARGET_KIND_BY_EXACT_TYPE.get(type(target))
    if kind is None:
        raise TypeError(
            "target must be one of the supported Evidence-owned target "
            f"identities: {_SUPPORTED_TARGET_IDENTITY_NAMES}"
        )
    return kind


@dataclass(frozen=True, slots=True)
class EvidenceReference:
    """Immutable opaque binding of one reference id to one Evidence target.

    The exact target identity type mechanically determines the preserved
    target semantic kind; unsupported identities fail closed. Supplied
    provenance is preserved verbatim without inference of Workflow
    acceptance, authenticity, or authorization. There is no rebind path:
    the same reference id with different content is a conflict.
    """

    evidence_reference_id: EvidenceReferenceId
    target: _EvidenceReferenceTarget
    run_id: RunId | None = None
    workflow_attempt_id: WorkflowAttemptId | None = None
    producer_result_id: ProducerResultId | None = None
    queue_message_id: QueueMessageId | None = None
    queue_delivery_id: QueueDeliveryId | None = None
    correlation_id: CorrelationId | None = None
    accepted_result_reference: OpaqueReference | None = None
    contract_version: str = EVIDENCE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _require_type(
            self.evidence_reference_id,
            EvidenceReferenceId,
            "evidence_reference_id",
        )
        _validate_target(self.target)
        for name, expected in (
            ("run_id", RunId),
            ("workflow_attempt_id", WorkflowAttemptId),
            ("producer_result_id", ProducerResultId),
            ("queue_message_id", QueueMessageId),
            ("queue_delivery_id", QueueDeliveryId),
            ("correlation_id", CorrelationId),
        ):
            _require_optional_type(getattr(self, name), expected, name)
        _require_optional_type(
            self.accepted_result_reference,
            OpaqueReference,
            "accepted_result_reference",
        )
        if self.contract_version != EVIDENCE_CONTRACT_VERSION:
            raise ValueError("unsupported Evidence contract version")
        self._validate_identity_separation()

    @property
    def target_kind(self) -> str:
        """Semantic target kind derived mechanically from the target type."""
        return _target_kind_for(self.target)

    @property
    def queue_reference_id(self) -> EvidenceReferenceId:
        """The only Queue-facing fact: the opaque EvidenceReferenceId."""
        return self.evidence_reference_id

    def to_domain_dict(self) -> dict[str, object]:
        """Return deterministic domain data without mutating this value."""
        domain = _domain_value(self)
        assert isinstance(domain, dict)
        domain["target"] = {
            "kind": self.target_kind,
            "value": self.target.value,
        }
        return domain

    def to_domain_json(self) -> str:
        """Serialize deterministically for domain comparison, not cryptography."""
        return json.dumps(
            self.to_domain_dict(),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    def _validate_identity_separation(self) -> None:
        reference_value = self.evidence_reference_id.value
        related: list[_Identifier] = [
            self.target,
            self.run_id,
            self.workflow_attempt_id,
            self.producer_result_id,
            self.queue_message_id,
            self.queue_delivery_id,
            self.correlation_id,
        ]
        if any(
            identity is not None and identity.value == reference_value
            for identity in related
        ):
            raise ValueError(
                "evidence_reference_id must remain distinct from every "
                "related identity value"
            )
        accepted = self.accepted_result_reference
        if accepted is not None and accepted.value == reference_value:
            raise ValueError(
                "evidence_reference_id must not copy an externally owned reference"
            )


def compare_evidence_references(
    existing: EvidenceReference,
    incoming: EvidenceReference,
) -> EvidenceComparison:
    """Classify duplicate convergence/conflict without mutating either value.

    The same reference id with identical canonical bindings converges;
    a changed target identity, a changed target semantic type, or changed
    provenance conflicts. No mutation or last-write-wins occurs here.
    """
    _require_type(existing, EvidenceReference, "existing")
    _require_type(incoming, EvidenceReference, "incoming")
    if existing.evidence_reference_id != incoming.evidence_reference_id:
        return EvidenceComparison.DISTINCT_IDENTITY
    if existing.to_domain_json() == incoming.to_domain_json():
        return EvidenceComparison.EQUIVALENT
    return EvidenceComparison.CONFLICTING
