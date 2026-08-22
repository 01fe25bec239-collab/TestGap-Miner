"""Immutable Evidence-owned EvidenceBundle aggregate domain values."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final

from .artefact import ArtefactManifest, ArtefactManifestFinalizationState, _artefact_domain_value
from .candidate import CandidatePatchId
from .decision import EvidenceBundleId, HumanDecisionId
from .execution import (
    EVIDENCE_CONTRACT_VERSION,
    CandidateVersionId,
    CorrelationId,
    EvidenceAvailability,
    EvidenceComparison,
    EvidenceCompleteness,
    EvidenceIntegrityState,
    ExecutionEvidence,
    ExecutionPhase,
    IntegrityMetadata,
    OpaqueReference,
    QueueDeliveryId,
    QueueMessageId,
    RunId,
    WorkflowAttemptId,
    _Identifier,
    _require_optional_type,
    _require_type,
    _semantic_key,
)


QUEUE_CONTRACT_VERSION: Final = "CONTRACT-QUEUE-001@1.0.0-draft.2"
WORKFLOW_CONTRACT_VERSION: Final = "CONTRACT-WORKFLOW-001@1.0.0-draft.1"


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    """Authoritative aggregate of Evidence for one candidate version and attempt.

    Existence never implies COMPLETE and COMPLETE never implies Workflow
    success; completeness is a caller-supplied classification that only
    triggers fail-closed aggregate consistency checks. Identities are never
    generated here and provenance is retained exactly as supplied.
    """

    evidence_bundle_id: EvidenceBundleId
    candidate_patch_id: CandidatePatchId
    candidate_version_id: CandidateVersionId
    completeness: EvidenceCompleteness
    run_id: RunId
    run_request_id: OpaqueReference
    workflow_attempt_id: WorkflowAttemptId
    workflow_step: OpaqueReference
    producer_id: OpaqueReference
    runner_id: OpaqueReference
    source_repository: OpaqueReference
    source_revision: OpaqueReference
    selected_context_manifest: OpaqueReference
    configuration_version: OpaqueReference
    model_identifier: OpaqueReference
    prompt_template_version: OpaqueReference
    producer_schema_version: OpaqueReference
    execution_evidence: tuple[ExecutionEvidence, ...] | Iterable[ExecutionEvidence] = ()
    artefact_manifest: ArtefactManifest | None = None
    integrity_metadata: IntegrityMetadata | None = None
    target_reference_revision: OpaqueReference | None = None
    queue_message_id: QueueMessageId | None = None
    queue_delivery_id: QueueDeliveryId | None = None
    claim_or_lease_id: OpaqueReference | None = None
    publication_identity: OpaqueReference | None = None
    causation_id: OpaqueReference | None = None
    correlation_id: CorrelationId | None = None
    human_decision_id: HumanDecisionId | None = None
    evaluation_benchmark_case_reference: OpaqueReference | None = None
    evaluation_benchmark_manifest_version: OpaqueReference | None = None
    evidence_contract_version: str = EVIDENCE_CONTRACT_VERSION
    queue_contract_version: str = QUEUE_CONTRACT_VERSION
    workflow_contract_version: str = WORKFLOW_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name, expected in (
            ("evidence_bundle_id", EvidenceBundleId),
            ("candidate_patch_id", CandidatePatchId),
            ("candidate_version_id", CandidateVersionId),
            ("completeness", EvidenceCompleteness),
            ("run_id", RunId),
            ("workflow_attempt_id", WorkflowAttemptId),
        ):
            _require_type(getattr(self, name), expected, name)
        for name in (
            "run_request_id",
            "workflow_step",
            "producer_id",
            "runner_id",
            "source_repository",
            "source_revision",
            "selected_context_manifest",
            "configuration_version",
            "model_identifier",
            "prompt_template_version",
            "producer_schema_version",
        ):
            _require_type(getattr(self, name), OpaqueReference, name)
        for name, expected in (
            ("artefact_manifest", ArtefactManifest),
            ("integrity_metadata", IntegrityMetadata),
            ("queue_message_id", QueueMessageId),
            ("queue_delivery_id", QueueDeliveryId),
            ("correlation_id", CorrelationId),
            ("human_decision_id", HumanDecisionId),
        ):
            _require_optional_type(getattr(self, name), expected, name)
        for name in (
            "target_reference_revision",
            "claim_or_lease_id",
            "publication_identity",
            "causation_id",
            "evaluation_benchmark_case_reference",
            "evaluation_benchmark_manifest_version",
        ):
            value = getattr(self, name)
            _require_optional_type(value, OpaqueReference, name)

        if self.evidence_contract_version != EVIDENCE_CONTRACT_VERSION:
            raise ValueError("unsupported Evidence contract version")
        if self.queue_contract_version != QUEUE_CONTRACT_VERSION:
            raise ValueError("unsupported Queue contract version")
        if self.workflow_contract_version != WORKFLOW_CONTRACT_VERSION:
            raise ValueError("unsupported Workflow contract version")

        if (self.evaluation_benchmark_case_reference is None) != (
            self.evaluation_benchmark_manifest_version is None
        ):
            raise ValueError(
                "benchmark provenance requires case reference and manifest "
                "version to be paired consistently"
            )

        object.__setattr__(
            self,
            "execution_evidence",
            _canonical_execution_evidence(self.execution_evidence),
        )

        self._validate_execution_aggregate()
        self._validate_source_revisions()
        self._validate_artefact_manifest_binding()
        self._validate_identity_separation()
        self._validate_complete_aggregate()

    @property
    def execution_phases(self) -> tuple[ExecutionPhase, ...]:
        return tuple(record.execution_phase for record in self.execution_evidence)

    def to_domain_dict(self) -> dict[str, object]:
        """Return deterministic domain data without mutating this value."""
        domain = _artefact_domain_value(self)
        assert isinstance(domain, dict)
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

    def _validate_execution_aggregate(self) -> None:
        for record in self.execution_evidence:
            if record.candidate_version_id != self.candidate_version_id:
                raise ValueError(
                    "execution evidence contradicts bundle candidate_version_id"
                )
            if record.workflow_attempt_id != self.workflow_attempt_id:
                raise ValueError(
                    "execution evidence contradicts bundle workflow_attempt_id"
                )
            if record.run_id is not None and record.run_id != self.run_id:
                raise ValueError("execution evidence contradicts bundle run_id")

    def _validate_source_revisions(self) -> None:
        for record in self.execution_evidence:
            supplied = record.source_revision
            if (
                record.execution_phase is ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST
                and supplied is not None
                and supplied != self.source_revision
            ):
                raise ValueError(
                    "buggy/target test evidence contradicts bundle source_revision"
                )
            if (
                record.execution_phase
                is ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST
            ):
                if self.target_reference_revision is None:
                    raise ValueError(
                        "fixed/reference test evidence requires bundle "
                        "target_reference_revision"
                    )
                if supplied is not None and supplied != self.target_reference_revision:
                    raise ValueError(
                        "fixed/reference test evidence contradicts bundle "
                        "target_reference_revision"
                    )

    def _validate_artefact_manifest_binding(self) -> None:
        manifest = self.artefact_manifest
        if manifest is None:
            return
        if (
            manifest.candidate_version_id is not None
            and manifest.candidate_version_id != self.candidate_version_id
        ):
            raise ValueError(
                "artefact manifest contradicts bundle candidate_version_id"
            )
        if (
            manifest.workflow_attempt_id is not None
            and manifest.workflow_attempt_id != self.workflow_attempt_id
        ):
            raise ValueError(
                "artefact manifest contradicts bundle workflow_attempt_id"
            )

    def _validate_identity_separation(self) -> None:
        bundle_value = self.evidence_bundle_id.value
        related: list[_Identifier] = [
            self.candidate_patch_id,
            self.candidate_version_id,
            self.run_id,
            self.workflow_attempt_id,
        ]
        related.extend(
            identity
            for identity in (
                self.queue_message_id,
                self.queue_delivery_id,
                self.correlation_id,
                self.human_decision_id,
            )
            if identity is not None
        )
        for record in self.execution_evidence:
            related.append(record.execution_evidence_id)
            related.append(record.producer_result_id)
        manifest = self.artefact_manifest
        if manifest is not None:
            related.append(manifest.artefact_manifest_id)
            related.extend(
                reference.artefact_id for reference in manifest.artefact_references
            )
        if any(identity.value == bundle_value for identity in related):
            raise ValueError(
                "evidence_bundle_id must remain distinct from every related "
                "identity value"
            )

    def _validate_complete_aggregate(self) -> None:
        if self.completeness is not EvidenceCompleteness.COMPLETE:
            return
        if not self.execution_evidence:
            raise ValueError("COMPLETE requires aggregate execution Evidence")
        if any(
            record.completeness is not EvidenceCompleteness.COMPLETE
            for record in self.execution_evidence
        ):
            raise ValueError(
                "COMPLETE cannot contain incomplete execution Evidence records"
            )
        if self.integrity_metadata is None:
            raise ValueError("COMPLETE requires verified bundle integrity metadata")
        if (
            self.integrity_metadata.state is not EvidenceIntegrityState.VERIFIED
        ):
            raise ValueError("COMPLETE cannot carry unverified integrity metadata")
        manifest = self.artefact_manifest
        if manifest is None:
            return
        if manifest.finalization_state is not ArtefactManifestFinalizationState.FINALIZED:
            raise ValueError(
                "COMPLETE cannot carry an unfinalized ArtefactManifest"
            )
        if manifest.integrity_metadata is None or (
            manifest.integrity_metadata.state is not EvidenceIntegrityState.VERIFIED
        ):
            raise ValueError(
                "COMPLETE cannot carry a manifest without verified manifest "
                "integrity metadata"
            )
        for reference in manifest.artefact_references:
            if reference.availability is not EvidenceAvailability.AVAILABLE:
                raise ValueError(
                    "COMPLETE cannot reference unavailable artefacts"
                )
            if reference.integrity.state is not EvidenceIntegrityState.VERIFIED:
                raise ValueError(
                    "COMPLETE cannot reference unverified artefacts"
                )


def compare_evidence_bundles(
    existing: EvidenceBundle,
    incoming: EvidenceBundle,
) -> EvidenceComparison:
    """Classify duplicate convergence/conflict without mutating either value."""
    _require_type(existing, EvidenceBundle, "existing")
    _require_type(incoming, EvidenceBundle, "incoming")
    if existing.evidence_bundle_id != incoming.evidence_bundle_id:
        return EvidenceComparison.DISTINCT_IDENTITY
    if existing.to_domain_json() == incoming.to_domain_json():
        return EvidenceComparison.EQUIVALENT
    return EvidenceComparison.CONFLICTING


def _canonical_execution_evidence(
    values: Iterable[ExecutionEvidence],
) -> tuple[ExecutionEvidence, ...]:
    if isinstance(values, (str, bytes, bytearray, set, frozenset, dict)):
        raise TypeError(
            "execution_evidence must be an ordered iterable of "
            "ExecutionEvidence values"
        )
    try:
        result = tuple(values)
    except TypeError as error:
        raise TypeError("execution_evidence must be iterable") from error
    if not all(isinstance(value, ExecutionEvidence) for value in result):
        raise TypeError("execution_evidence must contain only ExecutionEvidence values")
    ordered = tuple(sorted(result, key=_semantic_key))
    phases = [record.execution_phase for record in ordered]
    if len(phases) != len(set(phases)):
        raise ValueError("duplicate semantic execution phase must fail closed")
    return ordered
