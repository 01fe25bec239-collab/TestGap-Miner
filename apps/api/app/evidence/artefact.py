"""Immutable Evidence-domain artefact references and artefact manifests."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime
from enum import StrEnum
from typing import Final

from .execution import (
    EVIDENCE_CONTRACT_VERSION,
    CandidateVersionId,
    EvidenceAvailability,
    EvidenceComparison,
    EvidenceIntegrityState,
    ExecutionEvidenceId,
    ExecutionPhase,
    IntegrityMetadata,
    OpaqueReference,
    WorkflowAttemptId,
    _Identifier,
    _domain_value,
    _require_optional_type,
    _require_type,
    _semantic_key,
)


ARTEFACT_MANIFEST_CARDINALITY_BOUND: Final = "CONFIGURATION_VALUE_NOT_YET_SELECTED"
ARTEFACT_MANIFEST_SCHEMA_VERSION: Final = "ARTEFACT-MANIFEST-SCHEMA-V1"
MAX_ARTEFACT_METADATA_BYTES: Final = 16_384
MAX_MEDIA_TYPE_BYTES: Final = 255
MAX_STORAGE_LOCATOR_BYTES: Final = 16_384

_ARTEFACT_ID_PATTERN: Final = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:@+-]*")
_MEDIA_TYPE_PATTERN: Final = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]*/[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]*"
    r"(?:[ \t]*;.*)?"
)


class ArtefactId(_Identifier):
    """Evidence-owned opaque logical identity, never a physical locator."""

    def __post_init__(self) -> None:
        _Identifier.__post_init__(self)
        if _ARTEFACT_ID_PATTERN.fullmatch(self.value) is None:
            raise ValueError(
                "artefact identity must use the opaque logical-ID grammar, "
                "not a storage locator"
            )


class ArtefactManifestId(_Identifier):
    """Evidence-owned logical manifest identity, distinct from artefact identity."""


class ArtefactType(StrEnum):
    CANDIDATE_PATCH = "CANDIDATE_PATCH"
    COMPILE_LOG = "COMPILE_LOG"
    TEST_STDOUT = "TEST_STDOUT"
    TEST_STDERR = "TEST_STDERR"
    EXECUTION_LOG = "EXECUTION_LOG"
    CONTEXT_MANIFEST = "CONTEXT_MANIFEST"
    PUBLICATION_PAYLOAD = "PUBLICATION_PAYLOAD"
    CUSTOM_OUTPUT = "CUSTOM_OUTPUT"


class ArtefactManifestFinalizationState(StrEnum):
    ASSEMBLING = "ASSEMBLING"
    FINALIZED = "FINALIZED"


@dataclass(frozen=True, slots=True)
class ArtefactReference:
    """Immutable logical reference to one stored artefact.

    Availability and integrity are orthogonal dimensions; no state implies
    any other. Digests, locators, and producer identities are retained
    exactly as supplied and never generated, hashed, or resolved here.
    """

    artefact_id: ArtefactId
    artefact_type: ArtefactType
    availability: EvidenceAvailability
    integrity: IntegrityMetadata
    content_digest: OpaqueReference
    digest_algorithm: OpaqueReference
    byte_size: int
    media_type: str
    producer_id: OpaqueReference
    creation_timestamp: datetime
    storage_locator: str
    candidate_version_id: CandidateVersionId | None = None
    execution_evidence_id: ExecutionEvidenceId | None = None
    redaction_state: OpaqueReference | None = None
    contract_version: str = EVIDENCE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _require_type(self.artefact_id, ArtefactId, "artefact_id")
        _require_type(self.artefact_type, ArtefactType, "artefact_type")
        _require_type(self.availability, EvidenceAvailability, "availability")
        _require_type(self.integrity, IntegrityMetadata, "integrity")
        _require_type(self.content_digest, OpaqueReference, "content_digest")
        _require_type(self.digest_algorithm, OpaqueReference, "digest_algorithm")
        if type(self.byte_size) is not int or self.byte_size < 0:
            raise ValueError("byte_size must be a non-negative integer")
        _validate_media_type(self.media_type)
        _validate_reference(self.producer_id, "producer_id")
        _validate_timestamp(self.creation_timestamp, "creation_timestamp")
        _validate_storage_locator(self.storage_locator, self.artefact_id.value)
        _require_optional_type(
            self.candidate_version_id,
            CandidateVersionId,
            "candidate_version_id",
        )
        _require_optional_type(
            self.execution_evidence_id,
            ExecutionEvidenceId,
            "execution_evidence_id",
        )
        _validate_optional_reference(self.redaction_state, "redaction_state")
        if self.contract_version != EVIDENCE_CONTRACT_VERSION:
            raise ValueError("unsupported Evidence contract version")
        _require_distinct_identity_values(
            "artefact_id",
            self.artefact_id,
            self.candidate_version_id,
            self.execution_evidence_id,
        )

    @property
    def availability_state(self) -> EvidenceAvailability:
        return self.availability

    @property
    def integrity_state(self) -> EvidenceIntegrityState:
        return self.integrity.state

    def to_domain_dict(self) -> dict[str, object]:
        """Return deterministic domain data without mutating this value."""
        return _reference_domain_dict(self)

    def to_domain_json(self) -> str:
        """Serialize deterministically for domain comparison, not cryptography."""
        return _canonical_json(self)


@dataclass(frozen=True, slots=True)
class ArtefactManifest:
    """Immutable logical manifest of artefacts associated with Evidence.

    Membership order carries no meaning and is canonicalized; duplicate
    artefact identities fail closed. Finalization is a semantic distinction
    between immutable values, never in-place mutation.
    """

    artefact_manifest_id: ArtefactManifestId
    artefact_references: tuple[ArtefactReference, ...] | Iterable[ArtefactReference]
    creation_timestamp: datetime
    finalization_state: ArtefactManifestFinalizationState
    candidate_version_id: CandidateVersionId | None = None
    execution_evidence_id: ExecutionEvidenceId | None = None
    workflow_attempt_id: WorkflowAttemptId | None = None
    execution_phase: ExecutionPhase | None = None
    producer_provenance_reference: OpaqueReference | None = None
    manifest_digest: OpaqueReference | None = None
    manifest_digest_algorithm: OpaqueReference | None = None
    integrity_metadata: IntegrityMetadata | None = None
    finalization_timestamp: datetime | None = None
    contract_version: str = EVIDENCE_CONTRACT_VERSION
    schema_version: str = ARTEFACT_MANIFEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _require_type(
            self.artefact_manifest_id,
            ArtefactManifestId,
            "artefact_manifest_id",
        )
        _require_type(
            self.finalization_state,
            ArtefactManifestFinalizationState,
            "finalization_state",
        )
        _validate_timestamp(self.creation_timestamp, "creation_timestamp")
        for name, expected in (
            ("candidate_version_id", CandidateVersionId),
            ("execution_evidence_id", ExecutionEvidenceId),
            ("workflow_attempt_id", WorkflowAttemptId),
            ("execution_phase", ExecutionPhase),
        ):
            _require_optional_type(getattr(self, name), expected, name)
        _validate_optional_reference(
            self.producer_provenance_reference,
            "producer_provenance_reference",
        )
        _validate_optional_reference(self.manifest_digest, "manifest_digest")
        _validate_optional_reference(
            self.manifest_digest_algorithm,
            "manifest_digest_algorithm",
        )
        _require_optional_type(
            self.integrity_metadata,
            IntegrityMetadata,
            "integrity_metadata",
        )
        _validate_finalization(
            self.finalization_state,
            self.creation_timestamp,
            self.finalization_timestamp,
            producer_provenance_reference=self.producer_provenance_reference,
            manifest_digest=self.manifest_digest,
            manifest_digest_algorithm=self.manifest_digest_algorithm,
            integrity_metadata=self.integrity_metadata,
        )
        if (self.manifest_digest is None) != (self.manifest_digest_algorithm is None):
            raise ValueError(
                "manifest digest metadata requires both digest and algorithm"
            )
        if self.contract_version != EVIDENCE_CONTRACT_VERSION:
            raise ValueError("unsupported Evidence contract version")
        if self.schema_version != ARTEFACT_MANIFEST_SCHEMA_VERSION:
            raise ValueError("unsupported ArtefactManifest schema version")

        object.__setattr__(
            self,
            "artefact_references",
            _manifest_membership(self.artefact_references),
        )
        _require_distinct_identity_values(
            "artefact_manifest_id",
            self.artefact_manifest_id,
            self.candidate_version_id,
            self.execution_evidence_id,
            self.workflow_attempt_id,
        )
        member_identities = {
            reference.artefact_id.value for reference in self.artefact_references
        }
        if self.artefact_manifest_id.value in member_identities:
            raise ValueError(
                "artefact_manifest_id must remain distinct from member artefact identities"
            )

    @property
    def finalized(self) -> bool:
        return self.finalization_state is ArtefactManifestFinalizationState.FINALIZED

    def to_domain_dict(self) -> dict[str, object]:
        """Return deterministic domain data without mutating this value."""
        domain = _artefact_domain_value(self)
        assert isinstance(domain, dict)
        return domain

    def to_domain_json(self) -> str:
        """Serialize deterministically for domain comparison, not cryptography."""
        return _canonical_json(self)


def compare_artefact_references(
    existing: ArtefactReference,
    incoming: ArtefactReference,
) -> EvidenceComparison:
    """Classify immutable reference convergence without overwriting either value."""
    _require_type(existing, ArtefactReference, "existing")
    _require_type(incoming, ArtefactReference, "incoming")
    if existing.artefact_id != incoming.artefact_id:
        return EvidenceComparison.DISTINCT_IDENTITY
    if existing.to_domain_json() == incoming.to_domain_json():
        return EvidenceComparison.EQUIVALENT
    return EvidenceComparison.CONFLICTING


def compare_artefact_manifests(
    existing: ArtefactManifest,
    incoming: ArtefactManifest,
) -> EvidenceComparison:
    """Classify manifest convergence/conflict; changed content needs new identity."""
    _require_type(existing, ArtefactManifest, "existing")
    _require_type(incoming, ArtefactManifest, "incoming")
    if existing.artefact_manifest_id != incoming.artefact_manifest_id:
        return EvidenceComparison.DISTINCT_IDENTITY
    if existing.to_domain_json() == incoming.to_domain_json():
        return EvidenceComparison.EQUIVALENT
    return EvidenceComparison.CONFLICTING


def _manifest_membership(
    values: Iterable[ArtefactReference],
) -> tuple[ArtefactReference, ...]:
    if isinstance(values, (str, bytes, bytearray, set, frozenset, dict)):
        raise TypeError(
            "artefact_references must be an ordered iterable of ArtefactReference values"
        )
    try:
        result = tuple(values)
    except TypeError as error:
        raise TypeError("artefact_references must be iterable") from error
    if not all(isinstance(value, ArtefactReference) for value in result):
        raise TypeError("artefact_references must contain only ArtefactReference values")
    ordered = tuple(sorted(result, key=_semantic_key))
    identities = [value.artefact_id.value for value in ordered]
    if len(identities) != len(set(identities)):
        raise ValueError(
            "artefact manifest membership must not duplicate artefact identities"
        )
    return ordered


def _validate_timestamp(value: object, name: str) -> None:
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _validate_finalization(
    state: ArtefactManifestFinalizationState,
    creation_timestamp: datetime,
    finalization_timestamp: datetime | None,
    *,
    producer_provenance_reference: OpaqueReference | None,
    manifest_digest: OpaqueReference | None,
    manifest_digest_algorithm: OpaqueReference | None,
    integrity_metadata: IntegrityMetadata | None,
) -> None:
    if finalization_timestamp is not None:
        _validate_timestamp(finalization_timestamp, "finalization_timestamp")
    if (
        state is ArtefactManifestFinalizationState.ASSEMBLING
        and finalization_timestamp is not None
    ):
        raise ValueError("ASSEMBLING manifest must not carry finalization_timestamp")
    if state is ArtefactManifestFinalizationState.FINALIZED:
        required_final_metadata: tuple[tuple[str, object], ...] = (
            ("producer_provenance_reference", producer_provenance_reference),
            ("manifest_digest", manifest_digest),
            ("manifest_digest_algorithm", manifest_digest_algorithm),
            ("integrity_metadata", integrity_metadata),
        )
        if finalization_timestamp is None:
            raise ValueError("FINALIZED manifest requires finalization_timestamp")
        for name, value in required_final_metadata:
            if value is None:
                raise ValueError(f"FINALIZED manifest requires {name}")
    if (
        finalization_timestamp is not None
        and finalization_timestamp < creation_timestamp
    ):
        raise ValueError("finalization must not precede manifest creation")


def _validate_media_type(value: object) -> None:
    if type(value) is not str or not value.strip():
        raise ValueError("media_type must be a nonempty string")
    if len(value.encode("utf-8")) > MAX_MEDIA_TYPE_BYTES:
        raise ValueError(f"media_type exceeds {MAX_MEDIA_TYPE_BYTES} bytes")
    if _MEDIA_TYPE_PATTERN.fullmatch(value) is None:
        raise ValueError("media_type must be a bounded type/subtype media type")


def _validate_storage_locator(value: object, artefact_identity: str) -> None:
    if type(value) is not str or not value.strip():
        raise ValueError("storage_locator must be a nonempty string")
    if "\0" in value:
        raise ValueError("storage_locator must not contain NUL")
    if len(value.encode("utf-8")) > MAX_STORAGE_LOCATOR_BYTES:
        raise ValueError(f"storage_locator exceeds {MAX_STORAGE_LOCATOR_BYTES} bytes")
    if value == artefact_identity:
        raise ValueError("storage_locator must remain distinct from the artefact identity")


def _validate_reference(value: object, name: str) -> None:
    _require_type(value, OpaqueReference, name)
    assert isinstance(value, OpaqueReference)
    if len(value.value.encode("utf-8")) > MAX_ARTEFACT_METADATA_BYTES:
        raise ValueError(f"{name} exceeds {MAX_ARTEFACT_METADATA_BYTES} bytes")


def _validate_optional_reference(value: object, name: str) -> None:
    _require_optional_type(value, OpaqueReference, name)
    if value is not None:
        _validate_reference(value, name)


def _require_distinct_identity_values(
    owner_name: str,
    owner: _Identifier,
    *others: _Identifier | None,
) -> None:
    if any(value is not None and value.value == owner.value for value in others):
        raise ValueError(f"{owner_name} must be distinct from every related identity")


def _reference_domain_dict(reference: ArtefactReference) -> dict[str, object]:
    values = _domain_value(reference)
    assert isinstance(values, dict)
    domain = dict(values)
    domain["availability_state"] = domain.pop("availability")
    integrity = domain.pop("integrity")
    assert isinstance(integrity, dict)
    domain["integrity_state"] = integrity["state"]
    domain["integrity_verification_reference"] = integrity["verification_reference"]
    return domain


def _artefact_domain_value(value: object) -> object:
    if isinstance(value, ArtefactReference):
        return _reference_domain_dict(value)
    if isinstance(value, tuple):
        return [_artefact_domain_value(item) for item in value]
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _artefact_domain_value(getattr(value, field.name))
            for field in fields(value)
        }
    return _domain_value(value)


def _canonical_json(value: object) -> str:
    return json.dumps(
        _artefact_domain_value(value),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
