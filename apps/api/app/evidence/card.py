"""Immutable EvidenceCard: bounded human-review projection of an EvidenceBundle.

EvidenceCard is Evidence-owned semantic data for human review. It is data
content only: never a UI component, transport DTO, persistence model,
Workflow decision, Evaluation score, storage object, or transfer mechanism.
Every card fact either projects the exact reviewed EvidenceBundle or is
explicitly marked absent; missing execution is never presented as success
and confidence metadata never upgrades Evidence truthfulness.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Final

from .artefact import ArtefactManifest, ArtefactReference, _artefact_domain_value
from .bundle import EvidenceBundle
from .candidate import CandidatePatchId
from .decision import EvidenceBundleId, EvidenceCardId, HumanDecisionId
from .execution import (
    EVIDENCE_CONTRACT_VERSION,
    CandidateVersionId,
    CompileStatus,
    CorrelationId,
    EvidenceComparison,
    EvidenceCompleteness,
    EvidenceIntegrityState,
    ExecutionEvidenceId,
    ExecutionOutcome,
    ExecutionPhase,
    FailureCategory,
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


_TEST_COUNT_FIELDS: Final = (
    "executed_count",
    "passed_count",
    "failed_count",
    "skipped_count",
    "errored_count",
)

_PHASE_FACT_FIELDS: Final = (
    "outcome",
    "completeness",
    "integrity_state",
    "compile_status",
) + _TEST_COUNT_FIELDS + ("failure_category",)


@dataclass(frozen=True, slots=True)
class EvidenceCardPhaseSummary:
    """Bounded card-local summary of exactly one execution phase.

    A summary either projects the exact supplied ``ExecutionEvidence`` for
    its phase or represents that phase as absent with an optional reason.
    An absent phase carries no execution facts at all, so a missing phase can
    never be mistaken for a successful one.
    """

    phase: ExecutionPhase
    execution_evidence_id: ExecutionEvidenceId | None = None
    outcome: ExecutionOutcome | None = None
    completeness: EvidenceCompleteness | None = None
    integrity_state: EvidenceIntegrityState | None = None
    compile_status: CompileStatus | None = None
    executed_count: int | None = None
    passed_count: int | None = None
    failed_count: int | None = None
    skipped_count: int | None = None
    errored_count: int | None = None
    failure_category: FailureCategory | None = None
    unavailable_reason: OpaqueReference | None = None

    def __post_init__(self) -> None:
        _require_type(self.phase, ExecutionPhase, "phase")
        _require_optional_type(
            self.execution_evidence_id,
            ExecutionEvidenceId,
            "execution_evidence_id",
        )
        _require_optional_type(self.outcome, ExecutionOutcome, "outcome")
        _require_optional_type(
            self.completeness,
            EvidenceCompleteness,
            "completeness",
        )
        _require_optional_type(
            self.integrity_state,
            EvidenceIntegrityState,
            "integrity_state",
        )
        _require_optional_type(self.compile_status, CompileStatus, "compile_status")
        for name in _TEST_COUNT_FIELDS:
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f"{name} must be a non-negative integer when supplied")
        _require_optional_type(
            self.failure_category,
            FailureCategory,
            "failure_category",
        )
        _require_optional_type(
            self.unavailable_reason,
            OpaqueReference,
            "unavailable_reason",
        )

        if self.execution_evidence_id is None:
            for name in _PHASE_FACT_FIELDS:
                if getattr(self, name) is not None:
                    raise ValueError(
                        "an absent execution phase must not carry execution facts"
                    )
            if (
                self.phase is ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST
                and self.unavailable_reason is None
            ):
                raise ValueError(
                    "an absent fixed/reference revision test summary requires "
                    "an explicit unavailable reason"
                )
        else:
            if self.outcome is None or self.completeness is None:
                raise ValueError(
                    "a projected execution phase requires its supplied outcome "
                    "and completeness facts"
                )
            if self.unavailable_reason is not None:
                raise ValueError(
                    "unavailable_reason applies only to an absent execution phase"
                )
        if self.phase is ExecutionPhase.COMPILE:
            if any(getattr(self, name) is not None for name in _TEST_COUNT_FIELDS):
                raise ValueError("COMPILE summary cannot carry test count facts")
        elif self.compile_status is not None:
            raise ValueError("test-phase summary cannot carry compile status")


@dataclass(frozen=True, slots=True)
class EvidenceCardContext:
    """Immutable invocation/source provenance copied exactly from the bundle.

    Every field retains the bundle's supplied value; nothing is inferred,
    generated, or upgraded here.
    """

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
    target_reference_revision: OpaqueReference | None = None
    queue_message_id: QueueMessageId | None = None
    queue_delivery_id: QueueDeliveryId | None = None
    claim_or_lease_id: OpaqueReference | None = None
    publication_identity: OpaqueReference | None = None
    causation_id: OpaqueReference | None = None
    correlation_id: CorrelationId | None = None
    human_decision_id: HumanDecisionId | None = None

    def __post_init__(self) -> None:
        for name, expected in (
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
        ):
            _require_optional_type(getattr(self, name), OpaqueReference, name)


@dataclass(frozen=True, slots=True)
class EvidenceCard:
    """Bounded, human-review-facing semantic projection of one EvidenceBundle.

    The card binds to exactly one reviewed ``EvidenceBundleId`` and derives
    every Evidence fact mechanically from that bundle. Existence of a card
    never implies COMPLETE, verified integrity, or Workflow success, and
    INVALID Evidence is never silently turned into a normal review card.
    """

    evidence_card_id: EvidenceCardId
    reviewed_evidence_bundle_id: EvidenceBundleId
    candidate_patch_id: CandidatePatchId
    candidate_version_id: CandidateVersionId
    completeness: EvidenceCompleteness
    integrity_state: EvidenceIntegrityState | None
    selected_files_manifest_summary: OpaqueReference
    review_context: EvidenceCardContext
    execution_summaries: (
        tuple[EvidenceCardPhaseSummary, ...] | Iterable[EvidenceCardPhaseSummary]
    )
    artefact_references: tuple[ArtefactReference, ...] | Iterable[ArtefactReference]
    ai_generated: bool
    human_review_required: bool
    explanation_or_rationale_reference: OpaqueReference | None = None
    confidence_reference: OpaqueReference | None = None
    uncertainty_flag: bool = False
    uncertainty_category: OpaqueReference | None = None
    assessment_producer: OpaqueReference | None = None
    calibration_metadata: OpaqueReference | None = None
    governing_contract_version: str = EVIDENCE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name, expected in (
            ("evidence_card_id", EvidenceCardId),
            ("reviewed_evidence_bundle_id", EvidenceBundleId),
            ("candidate_patch_id", CandidatePatchId),
            ("candidate_version_id", CandidateVersionId),
            ("completeness", EvidenceCompleteness),
            ("selected_files_manifest_summary", OpaqueReference),
            ("review_context", EvidenceCardContext),
        ):
            _require_type(getattr(self, name), expected, name)
        _require_optional_type(
            self.integrity_state,
            EvidenceIntegrityState,
            "integrity_state",
        )
        for name in (
            "explanation_or_rationale_reference",
            "confidence_reference",
            "uncertainty_category",
            "assessment_producer",
            "calibration_metadata",
        ):
            _require_optional_type(getattr(self, name), OpaqueReference, name)
        for name in ("ai_generated", "human_review_required", "uncertainty_flag"):
            if type(getattr(self, name)) is not bool:
                raise TypeError(f"{name} must be a bool")
        if self.governing_contract_version != EVIDENCE_CONTRACT_VERSION:
            raise ValueError("unsupported Evidence contract version")
        if self.completeness is EvidenceCompleteness.INVALID:
            raise ValueError(
                "INVALID Evidence is not compatible with a normal "
                "human-review card"
            )

        object.__setattr__(
            self,
            "execution_summaries",
            _canonical_execution_summaries(self.execution_summaries),
        )
        object.__setattr__(
            self,
            "artefact_references",
            _canonical_artefact_references(self.artefact_references),
        )
        self._validate_identity_separation()

    @property
    def phase_summaries_by_phase(self) -> dict[ExecutionPhase, EvidenceCardPhaseSummary]:
        return {summary.phase: summary for summary in self.execution_summaries}

    def to_domain_dict(self) -> dict[str, object]:
        """Return deterministic domain data without mutating this value."""
        domain = _card_domain_value(self)
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

    def _validate_identity_separation(self) -> None:
        card_value = self.evidence_card_id.value
        related: list[_Identifier] = [
            self.reviewed_evidence_bundle_id,
            self.candidate_patch_id,
            self.candidate_version_id,
            self.review_context.run_id,
            self.review_context.workflow_attempt_id,
        ]
        related.extend(
            identity
            for identity in (
                self.review_context.queue_message_id,
                self.review_context.queue_delivery_id,
                self.review_context.correlation_id,
                self.review_context.human_decision_id,
            )
            if identity is not None
        )
        related.extend(
            summary.execution_evidence_id
            for summary in self.execution_summaries
            if summary.execution_evidence_id is not None
        )
        related.extend(
            reference.artefact_id for reference in self.artefact_references
        )
        if any(identity.value == card_value for identity in related):
            raise ValueError(
                "evidence_card_id must remain distinct from every related "
                "identity value"
            )


def project_evidence_card(
    bundle: EvidenceBundle,
    *,
    evidence_card_id: EvidenceCardId,
    ai_generated: bool,
    human_review_required: bool,
    explanation_or_rationale_reference: OpaqueReference | None = None,
    confidence_reference: OpaqueReference | None = None,
    uncertainty_flag: bool = False,
    uncertainty_category: OpaqueReference | None = None,
    assessment_producer: OpaqueReference | None = None,
    calibration_metadata: OpaqueReference | None = None,
    missing_phase_reasons: Mapping[ExecutionPhase, OpaqueReference] | None = None,
) -> EvidenceCard:
    """Project the exact supplied EvidenceBundle into a bounded review card.

    Identity is caller-supplied and never generated. Every Evidence fact is
    derived mechanically from the bundle; only card-specific semantics that
    are not derivable from it are accepted as inputs. The bundle is never
    mutated and no source fact is altered or upgraded; absent phases stay
    honestly absent and confidence metadata never implies proof. A missing
    fixed/reference revision test phase requires an explicit caller-supplied
    unavailable reason.
    """
    _require_type(bundle, EvidenceBundle, "bundle")
    _require_type(evidence_card_id, EvidenceCardId, "evidence_card_id")
    if type(ai_generated) is not bool:
        raise TypeError("ai_generated must be a bool")
    if type(human_review_required) is not bool:
        raise TypeError("human_review_required must be a bool")
    if type(uncertainty_flag) is not bool:
        raise TypeError("uncertainty_flag must be a bool")

    if bundle.completeness is EvidenceCompleteness.INVALID:
        raise ValueError(
            "INVALID Evidence is not compatible with a normal "
            "human-review card"
        )
    _validate_projection_identity_separation(bundle, evidence_card_id)

    return EvidenceCard(
        evidence_card_id=evidence_card_id,
        reviewed_evidence_bundle_id=bundle.evidence_bundle_id,
        candidate_patch_id=bundle.candidate_patch_id,
        candidate_version_id=bundle.candidate_version_id,
        completeness=bundle.completeness,
        integrity_state=(
            bundle.integrity_metadata.state
            if bundle.integrity_metadata is not None
            else None
        ),
        selected_files_manifest_summary=bundle.selected_context_manifest,
        review_context=_review_context_from_bundle(bundle),
        execution_summaries=_phase_summaries_from_bundle(
            bundle,
            missing_phase_reasons,
        ),
        artefact_references=_artefact_references_from_bundle(bundle),
        ai_generated=ai_generated,
        human_review_required=human_review_required,
        explanation_or_rationale_reference=explanation_or_rationale_reference,
        confidence_reference=confidence_reference,
        uncertainty_flag=uncertainty_flag,
        uncertainty_category=uncertainty_category,
        assessment_producer=assessment_producer,
        calibration_metadata=calibration_metadata,
    )


def _validate_projection_identity_separation(
    bundle: EvidenceBundle,
    evidence_card_id: EvidenceCardId,
) -> None:
    card_value = evidence_card_id.value
    related: list[_Identifier] = [
        record.producer_result_id for record in bundle.execution_evidence
    ]
    manifest = bundle.artefact_manifest
    if isinstance(manifest, ArtefactManifest):
        related.append(manifest.artefact_manifest_id)
    if any(identity.value == card_value for identity in related):
        raise ValueError(
            "evidence_card_id must remain distinct from every related "
            "identity value"
        )


def compare_evidence_cards(
    existing: EvidenceCard,
    incoming: EvidenceCard,
) -> EvidenceComparison:
    """Classify duplicate convergence/conflict without mutating either value."""
    _require_type(existing, EvidenceCard, "existing")
    _require_type(incoming, EvidenceCard, "incoming")
    if existing.evidence_card_id != incoming.evidence_card_id:
        return EvidenceComparison.DISTINCT_IDENTITY
    if existing.to_domain_json() == incoming.to_domain_json():
        return EvidenceComparison.EQUIVALENT
    return EvidenceComparison.CONFLICTING


def _review_context_from_bundle(bundle: EvidenceBundle) -> EvidenceCardContext:
    return EvidenceCardContext(
        run_id=bundle.run_id,
        run_request_id=bundle.run_request_id,
        workflow_attempt_id=bundle.workflow_attempt_id,
        workflow_step=bundle.workflow_step,
        producer_id=bundle.producer_id,
        runner_id=bundle.runner_id,
        source_repository=bundle.source_repository,
        source_revision=bundle.source_revision,
        selected_context_manifest=bundle.selected_context_manifest,
        configuration_version=bundle.configuration_version,
        model_identifier=bundle.model_identifier,
        prompt_template_version=bundle.prompt_template_version,
        producer_schema_version=bundle.producer_schema_version,
        target_reference_revision=bundle.target_reference_revision,
        queue_message_id=bundle.queue_message_id,
        queue_delivery_id=bundle.queue_delivery_id,
        claim_or_lease_id=bundle.claim_or_lease_id,
        publication_identity=bundle.publication_identity,
        causation_id=bundle.causation_id,
        correlation_id=bundle.correlation_id,
        human_decision_id=bundle.human_decision_id,
    )


def _phase_summaries_from_bundle(
    bundle: EvidenceBundle,
    missing_phase_reasons: Mapping[ExecutionPhase, OpaqueReference] | None,
) -> tuple[EvidenceCardPhaseSummary, ...]:
    supplied = {record.execution_phase: record for record in bundle.execution_evidence}
    reasons: dict[ExecutionPhase, OpaqueReference] = {}
    if missing_phase_reasons is not None:
        for phase, reason in missing_phase_reasons.items():
            _require_type(phase, ExecutionPhase, "missing-phase key")
            _require_type(reason, OpaqueReference, "missing-phase reason")
            if phase in supplied:
                raise ValueError(
                    "an unavailable reason contradicts supplied execution "
                    "evidence for its phase"
                )
            reasons[phase] = reason
    summaries: list[EvidenceCardPhaseSummary] = []
    for phase in ExecutionPhase:
        record = supplied.get(phase)
        if record is None:
            if (
                phase is ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST
                and phase not in reasons
            ):
                raise ValueError(
                    "a missing fixed/reference revision test execution "
                    "phase requires an explicit caller-supplied "
                    "unavailable reason"
                )
            summaries.append(
                EvidenceCardPhaseSummary(
                    phase=phase,
                    unavailable_reason=reasons.get(phase),
                )
            )
            continue
        counts: dict[str, int | None] = {}
        if record.test_result is not None:
            counts = {name: getattr(record.test_result, name) for name in _TEST_COUNT_FIELDS}
        summaries.append(
            EvidenceCardPhaseSummary(
                phase=phase,
                execution_evidence_id=record.execution_evidence_id,
                outcome=record.outcome,
                completeness=record.completeness,
                integrity_state=(
                    record.execution_integrity.state
                    if record.execution_integrity is not None
                    else None
                ),
                compile_status=(
                    record.compile_result.status
                    if record.compile_result is not None
                    else None
                ),
                failure_category=(
                    record.failure.category if record.failure is not None else None
                ),
                **counts,
            )
        )
    return tuple(summaries)


def _artefact_references_from_bundle(
    bundle: EvidenceBundle,
) -> tuple[ArtefactReference, ...]:
    collected: list[ArtefactReference] = []
    manifest = bundle.artefact_manifest
    if isinstance(manifest, ArtefactManifest):
        collected.extend(manifest.artefact_references)
    for record in bundle.execution_evidence:
        if record.stdout_artefact is not None:
            collected.append(record.stdout_artefact)
        if record.stderr_artefact is not None:
            collected.append(record.stderr_artefact)
        if record.compile_result is not None:
            collected.extend(record.compile_result.diagnostic_artefacts)
        collected.extend(record.output_artefacts)
    return _canonical_artefact_references(collected)


def _canonical_execution_summaries(
    values: Iterable[EvidenceCardPhaseSummary],
) -> tuple[EvidenceCardPhaseSummary, ...]:
    if isinstance(values, (str, bytes, bytearray, set, frozenset, dict)):
        raise TypeError(
            "execution_summaries must be an ordered iterable of "
            "EvidenceCardPhaseSummary values"
        )
    try:
        result = tuple(values)
    except TypeError as error:
        raise TypeError("execution_summaries must be iterable") from error
    if not all(isinstance(value, EvidenceCardPhaseSummary) for value in result):
        raise TypeError(
            "execution_summaries must contain only EvidenceCardPhaseSummary values"
        )
    declaration_order = {phase: index for index, phase in enumerate(ExecutionPhase)}
    ordered = sorted(result, key=lambda value: declaration_order[value.phase])
    phases = [summary.phase for summary in ordered]
    if len(phases) != len(set(phases)):
        raise ValueError("duplicate semantic execution phase summary must fail closed")
    if len(phases) != len(ExecutionPhase):
        raise ValueError(
            "a card requires exactly one summary per known execution phase, "
            "projected or explicitly absent"
        )
    return tuple(ordered)


def _canonical_artefact_references(
    values: Iterable[ArtefactReference],
) -> tuple[ArtefactReference, ...]:
    if isinstance(values, (str, bytes, bytearray, set, frozenset, dict)):
        raise TypeError(
            "artefact_references must be an ordered iterable of "
            "ArtefactReference values"
        )
    try:
        result = tuple(values)
    except TypeError as error:
        raise TypeError("artefact_references must be iterable") from error
    if not all(isinstance(value, ArtefactReference) for value in result):
        raise TypeError("artefact_references must contain only ArtefactReference values")
    by_identity: dict[str, ArtefactReference] = {}
    for reference in result:
        identity = reference.artefact_id.value
        existing = by_identity.get(identity)
        if existing is None:
            by_identity[identity] = reference
        elif existing.to_domain_json() != reference.to_domain_json():
            raise ValueError(
                "conflicting duplicate logical artefact identity must fail closed"
            )
    return tuple(sorted(by_identity.values(), key=_semantic_key))


def _card_domain_value(value: object) -> object:
    return _artefact_domain_value(value)
