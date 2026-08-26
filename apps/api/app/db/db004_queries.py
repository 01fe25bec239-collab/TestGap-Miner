"""DB-004R read-side reconstruction of persisted DB-004 metadata.

Every public function is a read-only exact-identity lookup over the physical
DB-004 schema. Each returns an immutable Database-owned projection of the
durable rows — never a domain semantic object, never an HTTP DTO. Reads never
flush, commit, or roll back the caller's transaction: execution runs under the
Session's no-autoflush guard, and no session mutation API is ever invoked.

Malformed identities fail closed before any SQL executes; validly shaped but
unknown identities raise an explicit not-found error. Identity handling mirrors
the durable column bounds exactly: no stripping, folding, truncation, or
coercion ever occurs.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, fields
from datetime import datetime
from types import MappingProxyType
from typing import Any
import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.db.models.context import IDENTITY_LENGTH as RAG_IDENTITY_LENGTH
from app.db.models.context import ContextBundle, ContextBundleItem
from app.db.models.evidence import IDENTITY_LENGTH as EVIDENCE_IDENTITY_LENGTH
from app.db.models.evidence import (
    ArtefactManifestMember,
    ArtefactManifestRecord,
    ArtefactReferenceRecord,
    CandidateChangedFile,
    CandidatePatchRecord,
    CandidateVersionRecord,
    ExecutionArtefactRole,
    ExecutionEvidenceRecord,
    ExecutionResourceObservation,
    ExecutionTestCaseResult,
)


class DB004QueryError(RuntimeError):
    """Base class for Database-local read-side failures."""


class DB004QueryInvalidIdentityError(DB004QueryError, ValueError):
    """The supplied identity is malformed and can never match a durable row."""


class DB004QueryNotFoundError(DB004QueryError, LookupError):
    """The identity is validly shaped but has no durable row."""


# ---------------------------------------------------------------------------
# Persisted Database projections
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DB004PersistedContextItem:
    """One persisted selected-context unit without any raw content."""

    context_item_id: str
    context_bundle_id: str
    position: int
    candidate_id: str
    file_identity: str
    start_line: int
    end_line: int
    content_sha256: str
    trust_label: str
    token_count: int


@dataclass(frozen=True, slots=True)
class DB004PersistedContextBundle:
    """Persisted ContextBundle root metadata with ordered items."""

    context_bundle_id: str
    repository_id: str
    revision_id: str
    contract_version: str
    max_tokens: int
    consumed_tokens: int
    created_at: datetime
    items: tuple[DB004PersistedContextItem, ...]


@dataclass(frozen=True, slots=True)
class DB004PersistedChangedFile:
    """One persisted changed-file entry keyed by its repository-relative path."""

    candidate_patch_id: str
    path: str
    change_summary: str


@dataclass(frozen=True, slots=True)
class DB004PersistedCandidatePatch:
    """Persisted CandidatePatch value with its changed-file manifest."""

    candidate_patch_id: str
    candidate_version_id: str
    run_id: uuid.UUID
    workflow_attempt_id: uuid.UUID
    source_repository: str
    source_revision: str
    target_reference_revision: str | None
    patch_digest: str
    digest_algorithm: str
    test_only_scope: bool
    test_only_scope_reference: str
    generator_reference: str
    tool_version_reference: str
    generated_at: datetime
    configuration_version: str
    finalization_state: str
    finalized_at: datetime | None
    patch_content_reference: str | None
    model_identifier: str | None
    prompt_template_version: str | None
    localisation_provenance_reference: str | None
    correlation_id: str | None
    contract_version: str
    changed_files: tuple[DB004PersistedChangedFile, ...]


@dataclass(frozen=True, slots=True)
class DB004PersistedCandidateVersion:
    """Persisted CandidateVersion lineage instance."""

    candidate_version_id: str
    candidate_patch_id: str
    run_id: uuid.UUID
    workflow_attempt_id: uuid.UUID
    producer_result_id: str | None
    repair_level: int
    parent_candidate_version_id: str | None
    source_repository: str
    source_revision: str
    target_reference_revision: str | None
    generator_reference: str
    tool_version_reference: str
    generated_at: datetime
    configuration_version: str
    finalization_state: str
    finalized_at: datetime | None
    model_identifier: str | None
    prompt_template_version: str | None
    localisation_provenance_reference: str | None
    correlation_id: str | None
    contract_version: str


@dataclass(frozen=True, slots=True)
class DB004PersistedExecutionTestCase:
    """One persisted individual test-case fact at its durable ordinal."""

    execution_evidence_id: str
    ordinal: int
    test_reference: str
    case_status: str
    failure_reference: str | None


@dataclass(frozen=True, slots=True)
class DB004PersistedExecutionResourceObservation:
    """One persisted typed runtime resource observation."""

    execution_evidence_id: str
    ordinal: int
    resource_category: str
    enforcement_status: str
    terminated_execution: bool
    configured_amount: int | None
    configured_unit: str | None
    configuration_reference: str | None
    observed_amount: int | None
    observed_unit: str | None
    breached: bool | None
    truncated: bool | None
    fact_reference: str | None
    other_category: str | None


@dataclass(frozen=True, slots=True)
class DB004PersistedExecutionArtefactRole:
    """One persisted role binding between an execution and an artefact."""

    execution_evidence_id: str
    artefact_id: str
    role: str


@dataclass(frozen=True, slots=True)
class DB004PersistedExecutionEvidence:
    """Persisted phase-specific ExecutionEvidence aggregate."""

    execution_evidence_id: str
    producer_result_id: str
    queue_message_id: str | None
    queue_delivery_id: str | None
    correlation_id: str | None
    candidate_version_id: str
    run_id: uuid.UUID | None
    workflow_attempt_id: uuid.UUID
    execution_phase: str
    outcome: str
    completeness: str
    command_reference: str
    execution_fact_reference: str
    source_revision: str | None
    started_at: datetime | None
    ended_at: datetime | None
    duration_microseconds: int | None
    timing_fact_reference: str | None
    timeout_timed_out: bool | None
    timeout_classification: str | None
    timeout_limit_microseconds: int | None
    timeout_fact_reference: str | None
    exit_code: int | None
    signal_number: int | None
    signal_name: str | None
    exit_fact_reference: str | None
    integrity_state: str | None
    integrity_verification_reference: str | None
    runtime_metadata_reference: str | None
    sandbox_metadata_reference: str | None
    environment_metadata_reference: str | None
    flake_indication_reference: str | None
    failure_category: str | None
    failure_reference: str | None
    secondary_failures: tuple[Mapping[str, object], ...] | None
    compile_status: str | None
    compile_error_count: int | None
    compile_warning_count: int | None
    compile_metadata_reference: str | None
    test_executed_count: int | None
    test_passed_count: int | None
    test_failed_count: int | None
    test_skipped_count: int | None
    test_errored_count: int | None
    test_failure_summary_reference: str | None
    contract_version: str
    test_cases: tuple[DB004PersistedExecutionTestCase, ...]
    resource_observations: tuple[DB004PersistedExecutionResourceObservation, ...]
    artefact_roles: tuple[DB004PersistedExecutionArtefactRole, ...]


@dataclass(frozen=True, slots=True)
class DB004PersistedArtefactReference:
    """Persisted logical artefact reference; the locator is opaque metadata."""

    artefact_id: str
    artefact_type: str
    availability_state: str
    integrity_state: str
    integrity_verification_reference: str | None
    content_digest: str
    digest_algorithm: str
    byte_size: int
    media_type: str
    producer_id: str
    creation_timestamp: datetime
    storage_locator: str
    candidate_version_id: str | None
    execution_evidence_id: str | None
    redaction_state: str | None
    contract_version: str


@dataclass(frozen=True, slots=True)
class DB004PersistedArtefactManifestMember:
    """One persisted relational manifest membership entry."""

    artefact_manifest_id: str
    artefact_id: str


@dataclass(frozen=True, slots=True)
class DB004PersistedArtefactManifest:
    """Persisted ArtefactManifest root metadata with exact membership."""

    artefact_manifest_id: str
    creation_timestamp: datetime
    finalization_state: str
    candidate_version_id: str | None
    execution_evidence_id: str | None
    workflow_attempt_id: uuid.UUID | None
    execution_phase: str | None
    producer_provenance_reference: str | None
    manifest_digest: str | None
    manifest_digest_algorithm: str | None
    integrity_state: str | None
    integrity_verification_reference: str | None
    finalization_timestamp: datetime | None
    contract_version: str
    schema_version: str
    members: tuple[DB004PersistedArtefactManifestMember, ...]


# ---------------------------------------------------------------------------
# Internal read machinery
# ---------------------------------------------------------------------------

_ROOT_COLLECTION_FIELDS = {
    DB004PersistedContextBundle: frozenset({"items"}),
    DB004PersistedCandidatePatch: frozenset({"changed_files"}),
    DB004PersistedExecutionEvidence: frozenset(
        {"test_cases", "resource_observations", "artefact_roles"}
    ),
    DB004PersistedArtefactManifest: frozenset({"members"}),
}


def _scalar_fields(projection_type: type) -> tuple[str, ...]:
    excluded = _ROOT_COLLECTION_FIELDS.get(projection_type, frozenset())
    return tuple(
        f.name for f in fields(projection_type) if f.name not in excluded
    )


def _identity(value: object, label: str, maximum_length: int) -> str:
    if not isinstance(value, str):
        raise DB004QueryInvalidIdentityError(f"{label} must be a string")
    if not value:
        raise DB004QueryInvalidIdentityError(f"{label} must not be empty")
    if len(value) > maximum_length:
        raise DB004QueryInvalidIdentityError(
            f"{label} exceeds its {maximum_length}-character durable bound"
        )
    return value


def _selected_rows(
    session: Session,
    model: type,
    names: Iterable[str],
    *conditions: sa.ColumnElement[Any],
    order_by: Iterable[sa.ColumnElement[Any]] = (),
) -> list[Mapping[str, object]]:
    statement = sa.select(
        *(model.__table__.columns[name] for name in names)
    ).where(*conditions)
    for element in order_by:
        statement = statement.order_by(element)
    return list(session.execute(statement).mappings())


def _build_projection(
    projection_type: type, record: Mapping[str, object]
) -> object:
    return projection_type(
        **{name: record[name] for name in _scalar_fields(projection_type)}
    )


def _frozen_json_array(
    value: object,
) -> tuple[Mapping[str, object], ...] | None:
    if value is None:
        return None
    return tuple(MappingProxyType(dict(entry)) for entry in value)


# ---------------------------------------------------------------------------
# Public read-side operations
# ---------------------------------------------------------------------------


def get_context_bundle_projection(
    session: Session, context_bundle_id: str
) -> DB004PersistedContextBundle:
    """Reconstruct one persisted ContextBundle with position-ordered items."""
    bundle_id = _identity(
        context_bundle_id, "context_bundle_id", RAG_IDENTITY_LENGTH
    )
    with session.no_autoflush:
        root = _selected_rows(
            session,
            ContextBundle,
            _scalar_fields(DB004PersistedContextBundle),
            ContextBundle.__table__.columns["context_bundle_id"] == bundle_id,
        )
        if not root:
            raise DB004QueryNotFoundError(
                f"context bundle not found: {bundle_id}"
            )
        item_records = _selected_rows(
            session,
            ContextBundleItem,
            _scalar_fields(DB004PersistedContextItem),
            ContextBundleItem.__table__.columns["context_bundle_id"] == bundle_id,
            order_by=(ContextBundleItem.position.asc(),),
        )
    return DB004PersistedContextBundle(
        **{name: root[0][name] for name in _scalar_fields(DB004PersistedContextBundle)},
        items=tuple(_build_projection(DB004PersistedContextItem, r) for r in item_records),
    )


def get_candidate_patch_projection(
    session: Session, candidate_patch_id: str
) -> DB004PersistedCandidatePatch:
    """Reconstruct one persisted CandidatePatch with path-ordered changed files."""
    patch_id = _identity(
        candidate_patch_id, "candidate_patch_id", EVIDENCE_IDENTITY_LENGTH
    )
    with session.no_autoflush:
        root = _selected_rows(
            session,
            CandidatePatchRecord,
            _scalar_fields(DB004PersistedCandidatePatch),
            CandidatePatchRecord.__table__.columns["candidate_patch_id"] == patch_id,
        )
        if not root:
            raise DB004QueryNotFoundError(f"candidate patch not found: {patch_id}")
        file_records = _selected_rows(
            session,
            CandidateChangedFile,
            _scalar_fields(DB004PersistedChangedFile),
            CandidateChangedFile.__table__.columns["candidate_patch_id"] == patch_id,
            order_by=(CandidateChangedFile.path.asc(),),
        )
    return DB004PersistedCandidatePatch(
        **{
            name: root[0][name]
            for name in _scalar_fields(DB004PersistedCandidatePatch)
        },
        changed_files=tuple(
            _build_projection(DB004PersistedChangedFile, r) for r in file_records
        ),
    )


def get_candidate_version_projection(
    session: Session, candidate_version_id: str
) -> DB004PersistedCandidateVersion:
    """Reconstruct one persisted CandidateVersion lineage instance."""
    version_id = _identity(
        candidate_version_id, "candidate_version_id", EVIDENCE_IDENTITY_LENGTH
    )
    with session.no_autoflush:
        records = _selected_rows(
            session,
            CandidateVersionRecord,
            _scalar_fields(DB004PersistedCandidateVersion),
            CandidateVersionRecord.__table__.columns["candidate_version_id"]
            == version_id,
        )
    if not records:
        raise DB004QueryNotFoundError(
            f"candidate version not found: {version_id}"
        )
    return _build_projection(DB004PersistedCandidateVersion, records[0])


def get_execution_evidence_projection(
    session: Session, execution_evidence_id: str
) -> DB004PersistedExecutionEvidence:
    """Reconstruct one persisted ExecutionEvidence aggregate and its children."""
    evidence_id = _identity(
        execution_evidence_id, "execution_evidence_id", EVIDENCE_IDENTITY_LENGTH
    )
    scalar_names = _scalar_fields(DB004PersistedExecutionEvidence)
    with session.no_autoflush:
        root = _selected_rows(
            session,
            ExecutionEvidenceRecord,
            scalar_names,
            ExecutionEvidenceRecord.__table__.columns["execution_evidence_id"]
            == evidence_id,
        )
        if not root:
            raise DB004QueryNotFoundError(
                f"execution evidence not found: {evidence_id}"
            )
        case_records = _selected_rows(
            session,
            ExecutionTestCaseResult,
            _scalar_fields(DB004PersistedExecutionTestCase),
            ExecutionTestCaseResult.__table__.columns["execution_evidence_id"]
            == evidence_id,
            order_by=(ExecutionTestCaseResult.ordinal.asc(),),
        )
        observation_records = _selected_rows(
            session,
            ExecutionResourceObservation,
            _scalar_fields(DB004PersistedExecutionResourceObservation),
            ExecutionResourceObservation.__table__.columns["execution_evidence_id"]
            == evidence_id,
            order_by=(ExecutionResourceObservation.ordinal.asc(),),
        )
        role_records = _selected_rows(
            session,
            ExecutionArtefactRole,
            _scalar_fields(DB004PersistedExecutionArtefactRole),
            ExecutionArtefactRole.__table__.columns["execution_evidence_id"]
            == evidence_id,
            order_by=(ExecutionArtefactRole.artefact_id.asc(),),
        )
    record = dict(root[0])
    record["secondary_failures"] = _frozen_json_array(record["secondary_failures"])
    return DB004PersistedExecutionEvidence(
        **{name: record[name] for name in scalar_names},
        test_cases=tuple(
            _build_projection(DB004PersistedExecutionTestCase, r)
            for r in case_records
        ),
        resource_observations=tuple(
            _build_projection(DB004PersistedExecutionResourceObservation, r)
            for r in observation_records
        ),
        artefact_roles=tuple(
            _build_projection(DB004PersistedExecutionArtefactRole, r)
            for r in role_records
        ),
    )


def get_artefact_reference_projection(
    session: Session, artefact_id: str
) -> DB004PersistedArtefactReference:
    """Reconstruct one persisted ArtefactReference without touching storage."""
    identity = _identity(artefact_id, "artefact_id", EVIDENCE_IDENTITY_LENGTH)
    with session.no_autoflush:
        records = _selected_rows(
            session,
            ArtefactReferenceRecord,
            _scalar_fields(DB004PersistedArtefactReference),
            ArtefactReferenceRecord.__table__.columns["artefact_id"] == identity,
        )
    if not records:
        raise DB004QueryNotFoundError(f"artefact reference not found: {identity}")
    return _build_projection(DB004PersistedArtefactReference, records[0])


def get_artefact_manifest_projection(
    session: Session, artefact_manifest_id: str
) -> DB004PersistedArtefactManifest:
    """Reconstruct one persisted ArtefactManifest with identity-ordered members."""
    manifest_id = _identity(
        artefact_manifest_id, "artefact_manifest_id", EVIDENCE_IDENTITY_LENGTH
    )
    with session.no_autoflush:
        root = _selected_rows(
            session,
            ArtefactManifestRecord,
            _scalar_fields(DB004PersistedArtefactManifest),
            ArtefactManifestRecord.__table__.columns["artefact_manifest_id"]
            == manifest_id,
        )
        if not root:
            raise DB004QueryNotFoundError(
                f"artefact manifest not found: {manifest_id}"
            )
        member_records = _selected_rows(
            session,
            ArtefactManifestMember,
            _scalar_fields(DB004PersistedArtefactManifestMember),
            ArtefactManifestMember.__table__.columns["artefact_manifest_id"]
            == manifest_id,
            order_by=(ArtefactManifestMember.artefact_id.asc(),),
        )
    return DB004PersistedArtefactManifest(
        **{
            name: root[0][name]
            for name in _scalar_fields(DB004PersistedArtefactManifest)
        },
        members=tuple(
            _build_projection(DB004PersistedArtefactManifestMember, r)
            for r in member_records
        ),
    )
