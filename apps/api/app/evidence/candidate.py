"""Immutable Evidence-domain candidate patch and lineage values."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from .execution import (
    EVIDENCE_CONTRACT_VERSION,
    CandidateVersionId,
    CorrelationId,
    EvidenceComparison,
    OpaqueReference,
    ProducerResultId,
    RunId,
    WorkflowAttemptId,
    _Identifier,
    _domain_value,
    _require_optional_type,
    _require_type,
)


MAX_CHANGED_FILES = 4_096
MAX_CHANGED_FILE_PATH_BYTES = 4_096
MAX_CHANGE_SUMMARY_BYTES = 16_384
MAX_CANDIDATE_REFERENCE_BYTES = 16_384


class CandidatePatchId(_Identifier):
    """Evidence-owned candidate-patch identity."""


class CandidateFinalizationState(StrEnum):
    CREATED = "CREATED"
    FINALIZED = "FINALIZED"


@dataclass(frozen=True, slots=True)
class GenerationProvenance:
    generator_reference: OpaqueReference
    tool_version_reference: OpaqueReference
    generated_at: datetime

    def __post_init__(self) -> None:
        _validate_reference(self.generator_reference, "generator_reference")
        _validate_reference(self.tool_version_reference, "tool_version_reference")
        _validate_timestamp(self.generated_at, "generated_at")


@dataclass(frozen=True, slots=True)
class ChangedFile:
    path: str
    change_summary: str

    def __post_init__(self) -> None:
        _validate_changed_path(self.path)
        _validate_text(
            self.change_summary,
            "change_summary",
            MAX_CHANGE_SUMMARY_BYTES,
        )


@dataclass(frozen=True, slots=True)
class CandidatePatch:
    candidate_patch_id: CandidatePatchId
    candidate_version_id: CandidateVersionId
    run_id: RunId
    workflow_attempt_id: WorkflowAttemptId
    source_repository: OpaqueReference
    source_revision: OpaqueReference
    patch_digest: OpaqueReference
    digest_algorithm: OpaqueReference
    test_only_scope: bool
    test_only_scope_reference: OpaqueReference
    changed_files_manifest: tuple[ChangedFile, ...] | Iterable[ChangedFile]
    generation_provenance: GenerationProvenance
    configuration_version: OpaqueReference
    finalization_state: CandidateFinalizationState
    finalized_at: datetime | None = None
    target_reference_revision: OpaqueReference | None = None
    patch_content_reference: OpaqueReference | None = None
    model_identifier: OpaqueReference | None = None
    prompt_template_version: OpaqueReference | None = None
    localisation_provenance_reference: OpaqueReference | None = None
    correlation_id: CorrelationId | None = None
    contract_version: str = EVIDENCE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name, expected in (
            ("candidate_patch_id", CandidatePatchId),
            ("candidate_version_id", CandidateVersionId),
            ("run_id", RunId),
            ("workflow_attempt_id", WorkflowAttemptId),
            ("generation_provenance", GenerationProvenance),
            ("finalization_state", CandidateFinalizationState),
        ):
            _require_type(getattr(self, name), expected, name)
        for name in (
            "source_repository",
            "source_revision",
            "patch_digest",
            "digest_algorithm",
            "test_only_scope_reference",
            "configuration_version",
        ):
            _validate_reference(getattr(self, name), name)
        for name in (
            "target_reference_revision",
            "patch_content_reference",
            "model_identifier",
            "prompt_template_version",
            "localisation_provenance_reference",
        ):
            _validate_optional_reference(getattr(self, name), name)
        _require_optional_type(self.correlation_id, CorrelationId, "correlation_id")
        if type(self.test_only_scope) is not bool:
            raise TypeError("test_only_scope must be a bool")
        if self.contract_version != EVIDENCE_CONTRACT_VERSION:
            raise ValueError("unsupported Evidence contract version")

        manifest = _changed_files(self.changed_files_manifest)
        object.__setattr__(self, "changed_files_manifest", manifest)
        _validate_finalization(self.finalization_state, self.finalized_at)
        _require_distinct_identity_values(
            "candidate_patch_id",
            self.candidate_patch_id,
            self.candidate_version_id,
            self.run_id,
            self.workflow_attempt_id,
            self.correlation_id,
        )

    def to_domain_dict(self) -> dict[str, object]:
        return _domain_value(self)  # type: ignore[return-value]

    def to_domain_json(self) -> str:
        return _canonical_json(self)


@dataclass(frozen=True, slots=True)
class CandidateVersion:
    candidate_version_id: CandidateVersionId
    candidate_patch_id: CandidatePatchId
    run_id: RunId
    workflow_attempt_id: WorkflowAttemptId
    repair_level: int
    generation_provenance: GenerationProvenance
    source_repository: OpaqueReference
    source_revision: OpaqueReference
    configuration_version: OpaqueReference
    finalization_state: CandidateFinalizationState
    parent_candidate_version_id: CandidateVersionId | None = None
    producer_result_id: ProducerResultId | None = None
    finalized_at: datetime | None = None
    target_reference_revision: OpaqueReference | None = None
    model_identifier: OpaqueReference | None = None
    prompt_template_version: OpaqueReference | None = None
    localisation_provenance_reference: OpaqueReference | None = None
    correlation_id: CorrelationId | None = None
    contract_version: str = EVIDENCE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name, expected in (
            ("candidate_version_id", CandidateVersionId),
            ("candidate_patch_id", CandidatePatchId),
            ("run_id", RunId),
            ("workflow_attempt_id", WorkflowAttemptId),
            ("generation_provenance", GenerationProvenance),
            ("finalization_state", CandidateFinalizationState),
        ):
            _require_type(getattr(self, name), expected, name)
        for name in (
            "source_repository",
            "source_revision",
            "configuration_version",
        ):
            _validate_reference(getattr(self, name), name)
        for name in (
            "target_reference_revision",
            "model_identifier",
            "prompt_template_version",
            "localisation_provenance_reference",
        ):
            _validate_optional_reference(getattr(self, name), name)
        _require_optional_type(
            self.parent_candidate_version_id,
            CandidateVersionId,
            "parent_candidate_version_id",
        )
        _require_optional_type(
            self.producer_result_id,
            ProducerResultId,
            "producer_result_id",
        )
        _require_optional_type(self.correlation_id, CorrelationId, "correlation_id")
        if self.contract_version != EVIDENCE_CONTRACT_VERSION:
            raise ValueError("unsupported Evidence contract version")
        if type(self.repair_level) is not int or self.repair_level not in (0, 1):
            raise ValueError("repair_level must be the integer 0 or 1")
        if self.repair_level == 0 and self.parent_candidate_version_id is not None:
            raise ValueError("initial candidate must not have a parent")
        if self.repair_level == 1 and self.parent_candidate_version_id is None:
            raise ValueError("repaired candidate requires a parent")
        if self.parent_candidate_version_id == self.candidate_version_id:
            raise ValueError("candidate version must not be its own parent")

        _validate_finalization(self.finalization_state, self.finalized_at)
        _require_distinct_identity_values(
            "candidate_version_id",
            self.candidate_version_id,
            self.candidate_patch_id,
            self.run_id,
            self.workflow_attempt_id,
            self.producer_result_id,
            self.correlation_id,
        )

    def to_domain_dict(self) -> dict[str, object]:
        return _domain_value(self)  # type: ignore[return-value]

    def to_domain_json(self) -> str:
        return _canonical_json(self)


def compare_candidate_patches(
    existing: CandidatePatch,
    incoming: CandidatePatch,
) -> EvidenceComparison:
    _require_type(existing, CandidatePatch, "existing")
    _require_type(incoming, CandidatePatch, "incoming")
    return _compare(
        existing.candidate_patch_id,
        incoming.candidate_patch_id,
        existing.to_domain_json(),
        incoming.to_domain_json(),
    )


def compare_candidate_versions(
    existing: CandidateVersion,
    incoming: CandidateVersion,
) -> EvidenceComparison:
    _require_type(existing, CandidateVersion, "existing")
    _require_type(incoming, CandidateVersion, "incoming")
    return _compare(
        existing.candidate_version_id,
        incoming.candidate_version_id,
        existing.to_domain_json(),
        incoming.to_domain_json(),
    )


def validate_candidate_patch_version(
    patch: CandidatePatch,
    version: CandidateVersion,
) -> None:
    """Reject contradictory bindings when both immutable values are available."""
    _require_type(patch, CandidatePatch, "patch")
    _require_type(version, CandidateVersion, "version")
    shared = (
        "candidate_patch_id",
        "candidate_version_id",
        "run_id",
        "workflow_attempt_id",
        "source_repository",
        "source_revision",
        "target_reference_revision",
        "generation_provenance",
        "configuration_version",
        "model_identifier",
        "prompt_template_version",
        "localisation_provenance_reference",
        "correlation_id",
    )
    for name in shared:
        if getattr(patch, name) != getattr(version, name):
            raise ValueError(f"candidate patch and version disagree on {name}")


def validate_candidate_lineage(
    initial: CandidateVersion,
    repaired: CandidateVersion,
) -> None:
    """Validate supplied V0 -> V1 lineage without enforcing Workflow policy."""
    _require_type(initial, CandidateVersion, "initial")
    _require_type(repaired, CandidateVersion, "repaired")
    if initial.repair_level != 0 or repaired.repair_level != 1:
        raise ValueError("candidate lineage requires an initial V0 and repaired V1")
    if repaired.parent_candidate_version_id != initial.candidate_version_id:
        raise ValueError("repaired candidate parent does not identify the initial version")
    if repaired.candidate_patch_id == initial.candidate_patch_id:
        raise ValueError("repaired candidate requires a distinct candidate_patch_id")
    if repaired.run_id != initial.run_id:
        raise ValueError("candidate lineage must remain within one originating run")


def _changed_files(values: Iterable[ChangedFile]) -> tuple[ChangedFile, ...]:
    if isinstance(values, (str, bytes, bytearray, set, frozenset, dict)):
        raise TypeError("changed_files_manifest must be an ordered iterable")
    try:
        result = tuple(values)
    except TypeError as error:
        raise TypeError("changed_files_manifest must be iterable") from error
    if not result:
        raise ValueError("changed_files_manifest must not be empty")
    if len(result) > MAX_CHANGED_FILES:
        raise ValueError(f"changed_files_manifest exceeds {MAX_CHANGED_FILES} entries")
    if not all(isinstance(value, ChangedFile) for value in result):
        raise TypeError("changed_files_manifest must contain only ChangedFile values")
    paths = [value.path for value in result]
    if len(paths) != len(set(paths)):
        raise ValueError("changed file paths must be unique")
    return tuple(sorted(result, key=lambda value: value.path))


def _validate_changed_path(path: object) -> None:
    _validate_text(path, "changed file path", MAX_CHANGED_FILE_PATH_BYTES)
    assert isinstance(path, str)
    if path != path.strip() or path.startswith("/") or any(
        part in ("", ".", "..") for part in path.split("/")
    ):
        raise ValueError("changed file path must be a repository-relative logical path")
    if "\0" in path:
        raise ValueError("changed file path must not contain NUL")


def _validate_text(value: object, name: str, maximum_bytes: int) -> None:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")
    if len(value.encode("utf-8")) > maximum_bytes:
        raise ValueError(f"{name} exceeds {maximum_bytes} bytes")


def _validate_reference(value: object, name: str) -> None:
    _require_type(value, OpaqueReference, name)
    _validate_text(value.value, name, MAX_CANDIDATE_REFERENCE_BYTES)


def _validate_optional_reference(value: object, name: str) -> None:
    _require_optional_type(value, OpaqueReference, name)
    if value is not None:
        _validate_reference(value, name)


def _validate_timestamp(value: object, name: str) -> None:
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _validate_finalization(
    state: CandidateFinalizationState,
    finalized_at: datetime | None,
) -> None:
    if finalized_at is not None:
        _validate_timestamp(finalized_at, "finalized_at")
    if state is CandidateFinalizationState.CREATED and finalized_at is not None:
        raise ValueError("CREATED candidate must not have finalized_at")
    if state is CandidateFinalizationState.FINALIZED and finalized_at is None:
        raise ValueError("FINALIZED candidate requires finalized_at")


def _require_distinct_identity_values(
    owner_name: str,
    owner: _Identifier,
    *others: _Identifier | None,
) -> None:
    if any(value is not None and value.value == owner.value for value in others):
        raise ValueError(f"{owner_name} must be distinct from every related identity")


def _canonical_json(value: object) -> str:
    return json.dumps(
        _domain_value(value),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _compare(
    existing_id: _Identifier,
    incoming_id: _Identifier,
    existing_content: str,
    incoming_content: str,
) -> EvidenceComparison:
    if existing_id != incoming_id:
        return EvidenceComparison.DISTINCT_IDENTITY
    if existing_content == incoming_content:
        return EvidenceComparison.EQUIVALENT
    return EvidenceComparison.CONFLICTING
