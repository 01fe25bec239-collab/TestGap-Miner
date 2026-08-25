"""DB-004 metadata persistence primitives: INSERT / CONVERGE / CONFLICT.

Every function receives a caller-owned :class:`~sqlalchemy.orm.Session`, may
flush, never commits, and never rolls back the caller's transaction; aggregate
writes run inside a single SAVEPOINT so a rejected aggregate leaves the
surrounding transaction usable.

Duplicate semantics follow ``CONTRACT-EVIDENCE-001`` and ``CONTRACT-RAG-001``:
the same immutable identity carrying equivalent semantic metadata converges to
the existing durable row, while any conflicting metadata raises
:class:`DB004PersistenceConflictError`. There is no update path: converged
rows are physically append-only.

Only bounded metadata and opaque references are persisted. Raw repository
bytes, ContextItem content, patch bytes, captured stdout/stderr, execution
logs, and artefact payloads have no destination here; object storage stays
outside Database scope behind provider-neutral locators.
"""

import json
import uuid
from collections.abc import Mapping
from datetime import timedelta

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db.models.context import ContextBundleItem
from app.db.models.context import ContextBundle as ContextBundleRow
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
from app.db.models.workflow import Run, WorkflowStep, WorkflowStepAttempt
from app.evidence.artefact import ArtefactManifest, ArtefactReference
from app.evidence.candidate import (
    CandidatePatch,
    CandidateVersion,
    validate_candidate_patch_version,
)
from app.evidence.execution import ExecutionEvidence, ExecutionOutcome
from app.retrieval.localisation import (
    CONTRACT_VERSION as RAG_CONTRACT_VERSION,
)
from app.retrieval.localisation import ContextBundle as RagContextBundle


class DB004PersistenceConflictError(RuntimeError):
    """The same immutable identity arrived with conflicting semantic metadata."""


class DB004UnresolvableReferenceError(LookupError):
    """A claimed Workflow/Candidate/Artefact identity has no durable match."""


def _require_type(value: object, expected: type, name: str) -> None:
    if not isinstance(value, expected):
        raise TypeError(f"{name} must be a {expected.__name__}")


def _reference_value(value: object) -> str | None:
    if value is None:
        return None
    return value.value  # type: ignore[attr-defined]


def _microseconds(delta: object) -> int | None:
    if delta is None:
        return None
    assert isinstance(delta, timedelta)
    return delta // timedelta(microseconds=1)


def _parse_durable_uuid(value: str, label: str) -> uuid.UUID:
    """Map an opaque string onto the durable UUID identity it claims to be.

    Arbitrary opaque strings are never reinterpreted: only the exact canonical
    lowercase UUID rendering is mappable, and anything else fails closed.
    """
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        raise DB004UnresolvableReferenceError(
            f"{label} {value!r} cannot safely map to a durable UUID identity"
        ) from None
    if str(parsed) != value:
        raise DB004UnresolvableReferenceError(
            f"{label} {value!r} is not a canonical durable UUID identity"
        )
    return parsed


def _resolve_run(session: Session, value: str | None) -> uuid.UUID | None:
    if value is None:
        return None
    run_uuid = _parse_durable_uuid(value, "run_id")
    if session.scalar(sa.select(Run.id).where(Run.id == run_uuid)) is None:
        raise DB004UnresolvableReferenceError(f"run not found: {run_uuid}")
    return run_uuid


def _resolve_attempt(
    session: Session, value: str, run_uuid: uuid.UUID | None = None
) -> uuid.UUID:
    attempt_uuid = _parse_durable_uuid(value, "workflow_attempt_id")
    row = session.execute(
        sa.select(WorkflowStepAttempt.id, WorkflowStep.run_id)
        .join(WorkflowStep, WorkflowStep.id == WorkflowStepAttempt.step_id)
        .where(WorkflowStepAttempt.id == attempt_uuid)
    ).first()
    if row is None:
        raise DB004UnresolvableReferenceError(
            f"workflow attempt not found: {attempt_uuid}"
        )
    if run_uuid is not None and row.run_id != run_uuid:
        raise ValueError(
            f"workflow attempt {attempt_uuid} does not belong to run {run_uuid}"
        )
    return attempt_uuid


def _require_candidate_version(
    session: Session, value: str
) -> Mapping[str, object]:
    stored = _stored_row(
        session, CandidateVersionRecord, {"candidate_version_id": value}
    )
    if stored is None:
        raise DB004UnresolvableReferenceError(f"candidate version not found: {value}")
    return stored


def _require_execution_evidence(session: Session, value: str) -> None:
    known = session.scalar(
        sa.select(ExecutionEvidenceRecord.execution_evidence_id).where(
            ExecutionEvidenceRecord.execution_evidence_id == value
        )
    )
    if known is None:
        raise DB004UnresolvableReferenceError(f"execution evidence not found: {value}")


def _comparable_columns(model: type) -> tuple[str, ...]:
    return tuple(
        column.name
        for column in model.__table__.columns
        if column.server_default is None
    )


def _stored_row(
    session: Session, model: type, identity: Mapping[str, object]
) -> Mapping[str, object] | None:
    statement = sa.select(*model.__table__.columns).filter_by(**dict(identity))
    return session.execute(statement).mappings().first()


def _assert_equivalent(
    model_name: str,
    identity: Mapping[str, object],
    stored: Mapping[str, object],
    expected: Mapping[str, object],
) -> None:
    differing = sorted(
        name for name, value in expected.items() if stored[name] != value
    )
    if differing:
        raise DB004PersistenceConflictError(
            f"{model_name} {dict(identity)!r} already exists with conflicting"
            f" metadata for {differing}"
        )


def _converge_row(
    session: Session,
    model: type,
    values: Mapping[str, object],
    identity: Mapping[str, object],
) -> bool:
    """INSERT one row; converge on an identical stored row under any race.

    ``ON CONFLICT DO NOTHING`` waits out concurrent in-flight inserts from
    independent PostgreSQL sessions before classification, so a
    duplicate-equivalent payload converges instead of failing while a
    conflicting payload is rejected by explicit comparison.
    """
    comparable = {name: values[name] for name in _comparable_columns(model)}
    # A None bound through psycopg's JSONB adapter lands as jsonb null rather
    # than SQL NULL; absent optional JSONB columns stay truly NULL instead.
    jsonb_columns = {
        column.name
        for column in model.__table__.columns
        if isinstance(column.type, sa.JSON) or str(column.type).upper().startswith("JSON")
    }
    insert_values = {
        name: value
        for name, value in values.items()
        if not (name in jsonb_columns and value is None)
    }
    # RETURNING arbitrates insertion: a landed row comes back, a conflicting
    # no-op returns nothing (rowcount is unreliable across drivers here).
    returning = [model.__table__.columns[name] for name in identity]
    landed = session.execute(
        pg_insert(model.__table__)
        .values(**insert_values)
        .on_conflict_do_nothing()
        .returning(*returning)
    ).first()
    inserted = landed is not None
    if not inserted:
        stored = _stored_row(session, model, identity)
        if stored is None:
            # A secondary uniqueness rule rejected this payload while the
            # winning row lives under a different identity: binding conflict.
            raise DB004PersistenceConflictError(
                f"{model.__name__} conflicts with an existing binding:"
                f" {dict(identity)!r}"
            )
        _assert_equivalent(model.__name__, identity, stored, comparable)
    return inserted


# ---------------------------------------------------------------------------
# RAG context metadata
# ---------------------------------------------------------------------------


def persist_context_bundle_metadata(
    session: Session, bundle: RagContextBundle
) -> "ContextBundleRow":
    """Persist one ContextBundle and its ordered items as one aggregate."""
    _require_type(bundle, RagContextBundle, "bundle")

    bundle_values = {
        "context_bundle_id": bundle.context_bundle_id.value,
        "repository_id": bundle.repository_id.value,
        "revision_id": bundle.revision_id.value,
        "contract_version": RAG_CONTRACT_VERSION,
        "max_tokens": bundle.token_budget.max_tokens,
        "consumed_tokens": bundle.token_budget.consumed_tokens,
    }
    item_values = [
        {
            "context_item_id": item.context_item_id.value,
            "context_bundle_id": bundle.context_bundle_id.value,
            "position": position,
            "candidate_id": item.candidate_id.value,
            "file_identity": item.provenance.file_identity.value,
            "start_line": item.provenance.start_line,
            "end_line": item.provenance.end_line,
            "content_sha256": item.provenance.content_sha256,
            "trust_label": item.trust_label.value,
            "token_count": item.token_count,
        }
        for position, item in enumerate(bundle.items, start=1)
    ]

    with session.begin_nested():
        _converge_row(
            session,
            ContextBundleRow,
            bundle_values,
            {"context_bundle_id": bundle.context_bundle_id.value},
        )
        for values in item_values:
            _converge_row(
                session,
                ContextBundleItem,
                values,
                {"context_item_id": values["context_item_id"]},
            )

    return session.get(
        ContextBundleRow,
        {"context_bundle_id": bundle.context_bundle_id.value},
    )


# ---------------------------------------------------------------------------
# Candidate metadata
# ---------------------------------------------------------------------------


def _provenance_values(source: CandidatePatch | CandidateVersion) -> dict[str, object]:
    provenance = source.generation_provenance
    return {
        "source_repository": source.source_repository.value,
        "source_revision": source.source_revision.value,
        "target_reference_revision": _reference_value(
            source.target_reference_revision
        ),
        "generator_reference": provenance.generator_reference.value,
        "tool_version_reference": provenance.tool_version_reference.value,
        "generated_at": provenance.generated_at,
        "configuration_version": source.configuration_version.value,
        "model_identifier": _reference_value(source.model_identifier),
        "prompt_template_version": _reference_value(source.prompt_template_version),
        "localisation_provenance_reference": _reference_value(
            source.localisation_provenance_reference
        ),
        "correlation_id": _reference_value(source.correlation_id),
    }


def _validate_parent_lineage(
    session: Session, version: CandidateVersion, run_uuid: uuid.UUID | None
) -> None:
    if version.parent_candidate_version_id is None:
        return
    parent = _stored_row(
        session,
        CandidateVersionRecord,
        {"candidate_version_id": version.parent_candidate_version_id.value},
    )
    if parent is None:
        raise DB004UnresolvableReferenceError(
            "parent candidate version not found:"
            f" {version.parent_candidate_version_id.value}"
        )
    if parent["repair_level"] != 0:
        raise ValueError("repaired candidates must parent an initial candidate")
    if run_uuid is not None and parent["run_id"] != run_uuid:
        raise ValueError("candidate lineage must remain within one originating run")


def persist_candidate_metadata(
    session: Session,
    *,
    patch: CandidatePatch,
    version: CandidateVersion,
) -> tuple[CandidatePatchRecord, CandidateVersionRecord]:
    """Persist one CandidatePatch plus its CandidateVersion as one aggregate.

    Both Evidence-owned identities stay distinct durable rows bound by the
    patch identity; neither collapses into the other. A contradictory
    patch/version binding fails closed before any write.
    """
    _require_type(patch, CandidatePatch, "patch")
    _require_type(version, CandidateVersion, "version")
    validate_candidate_patch_version(patch, version)

    run_uuid = _resolve_run(session, patch.run_id.value)
    attempt_uuid = _resolve_attempt(session, patch.workflow_attempt_id.value, run_uuid)

    patch_values = {
        "candidate_patch_id": patch.candidate_patch_id.value,
        "candidate_version_id": patch.candidate_version_id.value,
        "run_id": run_uuid,
        "workflow_attempt_id": attempt_uuid,
        **_provenance_values(patch),
        "patch_digest": patch.patch_digest.value,
        "digest_algorithm": patch.digest_algorithm.value,
        "test_only_scope": patch.test_only_scope,
        "test_only_scope_reference": patch.test_only_scope_reference.value,
        "finalization_state": patch.finalization_state.value,
        "finalized_at": patch.finalized_at,
        "patch_content_reference": _reference_value(patch.patch_content_reference),
        "contract_version": patch.contract_version,
    }

    _validate_parent_lineage(session, version, run_uuid)
    version_values = {
        "candidate_version_id": version.candidate_version_id.value,
        "candidate_patch_id": version.candidate_patch_id.value,
        "run_id": run_uuid,
        "workflow_attempt_id": attempt_uuid,
        "producer_result_id": _reference_value(version.producer_result_id),
        "repair_level": version.repair_level,
        "parent_candidate_version_id": _reference_value(
            version.parent_candidate_version_id
        ),
        **_provenance_values(version),
        "finalization_state": version.finalization_state.value,
        "finalized_at": version.finalized_at,
        "contract_version": version.contract_version,
    }

    changed_file_values = [
        {
            "candidate_patch_id": patch.candidate_patch_id.value,
            "path": entry.path,
            "change_summary": entry.change_summary,
        }
        for entry in patch.changed_files_manifest
    ]

    incoming_files = {
        values["path"]: values["change_summary"] for values in changed_file_values
    }

    with session.begin_nested():
        patch_newly_inserted = _converge_row(
            session,
            CandidatePatchRecord,
            patch_values,
            {"candidate_patch_id": patch.candidate_patch_id.value},
        )
        _converge_row(
            session,
            CandidateVersionRecord,
            version_values,
            {"candidate_version_id": version.candidate_version_id.value},
        )
        # The changed-file manifest is an immutable set under the patch
        # identity. When the patch row already existed, the COMPLETE stored
        # manifest must equal the COMPLETE incoming manifest before any child
        # membership is added; growth or shrinkage means a changed aggregate
        # and fails closed without leaving a partial child behind.
        if not patch_newly_inserted:
            stored_files = {
                row.path: row.change_summary
                for row in session.execute(
                    sa.select(
                        CandidateChangedFile.path, CandidateChangedFile.change_summary
                    ).where(
                        CandidateChangedFile.candidate_patch_id
                        == patch.candidate_patch_id.value
                    )
                )
            }
            if stored_files != incoming_files:
                raise DB004PersistenceConflictError(
                    f"changed-file manifest conflicts for {patch.candidate_patch_id.value}"
                )
        for values in changed_file_values:
            _converge_row(
                session,
                CandidateChangedFile,
                values,
                {
                    "candidate_patch_id": values["candidate_patch_id"],
                    "path": values["path"],
                },
            )

    return (
        session.get(
            CandidatePatchRecord,
            {"candidate_patch_id": patch.candidate_patch_id.value},
        ),
        session.get(
            CandidateVersionRecord,
            {"candidate_version_id": version.candidate_version_id.value},
        ),
    )


# ---------------------------------------------------------------------------
# Artefact references
# ---------------------------------------------------------------------------


def _artefact_values(reference: ArtefactReference) -> dict[str, object]:
    return {
        "artefact_id": reference.artefact_id.value,
        "artefact_type": reference.artefact_type.value,
        "availability_state": reference.availability.value,
        "integrity_state": reference.integrity.state.value,
        "integrity_verification_reference": _reference_value(
            reference.integrity.verification_reference
        ),
        "content_digest": reference.content_digest.value,
        "digest_algorithm": reference.digest_algorithm.value,
        "byte_size": reference.byte_size,
        "media_type": reference.media_type,
        "producer_id": reference.producer_id.value,
        "creation_timestamp": reference.creation_timestamp,
        "storage_locator": reference.storage_locator,
        "candidate_version_id": _reference_value(reference.candidate_version_id),
        "execution_evidence_id": _reference_value(reference.execution_evidence_id),
        "redaction_state": _reference_value(reference.redaction_state),
        "contract_version": reference.contract_version,
    }


def persist_artefact_reference_metadata(
    session: Session, reference: ArtefactReference
) -> ArtefactReferenceRecord:
    """Persist one immutable ArtefactReference; converge or fail closed."""
    _require_type(reference, ArtefactReference, "reference")
    if reference.candidate_version_id is not None:
        _require_candidate_version(session, reference.candidate_version_id.value)
    if reference.execution_evidence_id is not None:
        _require_execution_evidence(session, reference.execution_evidence_id.value)
        # Relational provenance consistency: when both linkages are supplied,
        # the referenced execution evidence must belong to that same candidate.
        if reference.candidate_version_id is not None:
            linked_candidate = session.scalar(
                sa.select(ExecutionEvidenceRecord.candidate_version_id).where(
                    ExecutionEvidenceRecord.execution_evidence_id
                    == reference.execution_evidence_id.value
                )
            )
            if linked_candidate != reference.candidate_version_id.value:
                raise ValueError(
                    "artefact links execution evidence"
                    f" {reference.execution_evidence_id.value} to candidate"
                    f" {reference.candidate_version_id.value} but that evidence"
                    f" belongs to candidate {linked_candidate}"
                )

    values = _artefact_values(reference)
    with session.begin_nested():
        _converge_row(
            session,
            ArtefactReferenceRecord,
            values,
            {"artefact_id": reference.artefact_id.value},
        )
    return session.get(
        ArtefactReferenceRecord, {"artefact_id": reference.artefact_id.value}
    )


# ---------------------------------------------------------------------------
# Execution evidence
# ---------------------------------------------------------------------------

_EMBEDDED_ROLE_BINDINGS: tuple[tuple[str, str], ...] = (
    ("stdout_artefact", "STDOUT"),
    ("stderr_artefact", "STDERR"),
)


def _secondary_failure_payload(evidence: ExecutionEvidence) -> list[dict[str, object]] | None:
    payload = [
        {
            "category": failure.category.value,
            "upstream_failure_reference": _reference_value(
                failure.upstream_failure_reference
            ),
        }
        for failure in evidence.secondary_failures
    ]
    if not payload:
        # No secondary failures means no structured payload at all.
        return None
    return sorted(payload, key=lambda entry: json.dumps(entry, sort_keys=True))


def _execution_values(evidence: ExecutionEvidence) -> dict[str, object]:
    timing = evidence.execution_timing
    timeout = evidence.timeout_metadata
    process_exit = evidence.process_exit
    integrity = evidence.execution_integrity
    failure = evidence.failure
    compile_result = evidence.compile_result
    test_result = evidence.test_result

    return {
        "execution_evidence_id": evidence.execution_evidence_id.value,
        "producer_result_id": evidence.producer_result_id.value,
        # Opaque queue/tracing provenance: persisted as bounded metadata only,
        # never interpreted, never a foreign key, never part of Evidence
        # identity, and never conflated with producer_result_id.
        "queue_message_id": _reference_value(evidence.queue_message_id),
        "queue_delivery_id": _reference_value(evidence.queue_delivery_id),
        "correlation_id": _reference_value(evidence.correlation_id),
        "candidate_version_id": evidence.candidate_version_id.value,
        "run_id": None,  # filled by the caller after durable-run resolution
        "workflow_attempt_id": None,  # filled by the caller likewise
        "execution_phase": evidence.execution_phase.value,
        "outcome": evidence.outcome.value,
        "completeness": evidence.completeness.value,
        "command_reference": evidence.command_reference.value,
        "execution_fact_reference": evidence.execution_fact_reference.value,
        "source_revision": _reference_value(evidence.source_revision),
        "started_at": timing.started_at if timing else None,
        "ended_at": timing.ended_at if timing else None,
        "duration_microseconds": _microseconds(timing.duration) if timing else None,
        "timing_fact_reference": _reference_value(
            timing.upstream_fact_reference if timing else None
        ),
        "timeout_timed_out": timeout.timed_out if timeout else None,
        "timeout_classification": _reference_value(timeout.classification if timeout else None),
        "timeout_limit_microseconds": _microseconds(
            timeout.configured_limit if timeout else None
        ),
        "timeout_fact_reference": _reference_value(
            timeout.upstream_fact_reference if timeout else None
        ),
        "exit_code": process_exit.exit_code if process_exit else None,
        "signal_number": process_exit.signal_number if process_exit else None,
        "signal_name": process_exit.signal_name if process_exit else None,
        "exit_fact_reference": _reference_value(
            process_exit.upstream_fact_reference if process_exit else None
        ),
        "integrity_state": integrity.state.value if integrity else None,
        "integrity_verification_reference": _reference_value(
            integrity.verification_reference if integrity else None
        ),
        "runtime_metadata_reference": _reference_value(
            evidence.runtime_metadata_reference
        ),
        "sandbox_metadata_reference": _reference_value(
            evidence.sandbox_metadata_reference
        ),
        "environment_metadata_reference": _reference_value(
            evidence.environment_metadata_reference
        ),
        "flake_indication_reference": _reference_value(
            evidence.flake_indication_reference
        ),
        "failure_category": failure.category.value if failure else None,
        "failure_reference": _reference_value(
            failure.upstream_failure_reference if failure else None
        ),
        "secondary_failures": _secondary_failure_payload(evidence),
        "compile_status": compile_result.status.value if compile_result else None,
        "compile_error_count": compile_result.error_count if compile_result else None,
        "compile_warning_count": compile_result.warning_count if compile_result else None,
        "compile_metadata_reference": _reference_value(
            compile_result.compiler_metadata_reference if compile_result else None
        ),
        "test_executed_count": test_result.executed_count if test_result else None,
        "test_passed_count": test_result.passed_count if test_result else None,
        "test_failed_count": test_result.failed_count if test_result else None,
        "test_skipped_count": test_result.skipped_count if test_result else None,
        "test_errored_count": test_result.errored_count if test_result else None,
        "test_failure_summary_reference": _reference_value(
            test_result.failure_summary_reference if test_result else None
        ),
        "contract_version": evidence.contract_version,
    }


def _observation_payload(observation: object) -> dict[str, object]:
    configured = observation.configured_value  # type: ignore[attr-defined]
    observed = observation.observed_value  # type: ignore[attr-defined]
    return {
        "resource_category": observation.category.value,  # type: ignore[attr-defined]
        "enforcement_status": observation.enforcement_status.value,  # type: ignore[attr-defined]
        "terminated_execution": observation.terminated_execution,  # type: ignore[attr-defined]
        "configured_amount": configured.amount if configured else None,
        "configured_unit": configured.unit if configured else None,
        "configuration_reference": _reference_value(
            observation.configuration_reference  # type: ignore[attr-defined]
        ),
        "observed_amount": observed.amount if observed else None,
        "observed_unit": observed.unit if observed else None,
        "breached": observation.breached,  # type: ignore[attr-defined]
        "truncated": observation.truncated,  # type: ignore[attr-defined]
        "fact_reference": _reference_value(
            observation.upstream_fact_reference  # type: ignore[attr-defined]
        ),
        "other_category": observation.other_category,  # type: ignore[attr-defined]
    }


def _observation_key(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, sort_keys=True)


def _embedded_role_pairs(
    evidence: ExecutionEvidence,
) -> list[tuple[ArtefactReference, str]]:
    pairs: list[tuple[ArtefactReference, str]] = []
    for attribute, role in _EMBEDDED_ROLE_BINDINGS:
        reference = getattr(evidence, attribute)
        if reference is not None:
            pairs.append((reference, role))
    for reference in evidence.output_artefacts:
        pairs.append((reference, "OUTPUT"))
    if evidence.compile_result is not None:
        for reference in evidence.compile_result.diagnostic_artefacts:
            pairs.append((reference, "COMPILE_DIAGNOSTIC"))
    return pairs


def persist_execution_evidence_metadata(
    session: Session, evidence: ExecutionEvidence
) -> ExecutionEvidenceRecord:
    """Persist one phase-specific ExecutionEvidence aggregate.

    The execution row, every embedded stream/output/diagnostic artefact
    reference, the execution↔artefact role bindings, individual test-case
    facts, and typed resource observations land as one atomic unit.
    """
    _require_type(evidence, ExecutionEvidence, "evidence")
    if evidence.outcome is ExecutionOutcome.RESOURCE_BREACH and not any(
        observation.breached is True for observation in evidence.resource_observations
    ):
        raise ValueError("RESOURCE_BREACH requires an explicitly supplied breach fact")

    evidence_id = evidence.execution_evidence_id.value
    run_uuid = _resolve_run(session, _reference_value(evidence.run_id))
    # The candidate row anchors the durable run: a supplied run identity must
    # agree with it, and the attempt must belong to that same run regardless
    # of which identity supplied it.
    candidate_row = _require_candidate_version(
        session, evidence.candidate_version_id.value
    )
    if run_uuid is not None and candidate_row["run_id"] != run_uuid:
        raise ValueError(
            f"evidence claims run {run_uuid} but its candidate version belongs"
            f" to run {candidate_row['run_id']}"
        )
    expected_run = (
        run_uuid if run_uuid is not None else candidate_row["run_id"]
    )
    attempt_uuid = _resolve_attempt(session, evidence.workflow_attempt_id.value, expected_run)

    values = _execution_values(evidence)
    values["run_id"] = run_uuid
    values["workflow_attempt_id"] = attempt_uuid

    role_pairs = _embedded_role_pairs(evidence)
    for reference, _role in role_pairs:
        declared_link = _reference_value(reference.execution_evidence_id)
        if declared_link is not None and declared_link != evidence_id:
            raise ValueError(
                "embedded artefact declares a conflicting execution linkage:"
                f" {reference.artefact_id.value}"
            )
        declared_candidate = _reference_value(reference.candidate_version_id)
        if (
            declared_candidate is not None
            and declared_candidate != evidence.candidate_version_id.value
        ):
            # A nonexistent candidate keeps failing later as an unresolved
            # reference; an existing foreign candidate is a cross-candidate
            # linkage conflict.
            foreign = _stored_row(
                session,
                CandidateVersionRecord,
                {"candidate_version_id": declared_candidate},
            )
            if foreign is not None:
                raise ValueError(
                    "embedded artefact declares a conflicting candidate linkage:"
                    f" {reference.artefact_id.value}"
                )

    ordered_cases = sorted(
        evidence.test_result.test_cases or (),
        key=lambda case: case.test_reference.value,
    ) if evidence.test_result is not None else []
    case_values = [
        {
            "execution_evidence_id": evidence_id,
            "ordinal": ordinal,
            "test_reference": case.test_reference.value,
            "case_status": case.status.value,
            "failure_reference": _reference_value(case.failure_reference),
        }
        for ordinal, case in enumerate(ordered_cases, start=1)
    ]

    ordered_observation_payloads = sorted(
        (_observation_payload(observation) for observation in evidence.resource_observations),
        key=_observation_key,
    )
    observation_values = [
        {"execution_evidence_id": evidence_id, "ordinal": ordinal, **payload}
        for ordinal, payload in enumerate(ordered_observation_payloads, start=1)
    ]

    incoming_roles = {
        reference.artefact_id.value: role for reference, role in role_pairs
    }
    incoming_cases = {
        (value["ordinal"], value["test_reference"]): (
            value["case_status"],
            value["failure_reference"],
        )
        for value in case_values
    }
    incoming_observations = {
        index + 1: _observation_key(payload)
        for index, payload in enumerate(ordered_observation_payloads)
    }

    with session.begin_nested():
        root_newly_inserted = _converge_row(
            session,
            ExecutionEvidenceRecord,
            values,
            {"execution_evidence_id": evidence_id},
        )
        # Every child collection below is immutable under the evidence
        # identity. When the root row already existed, the COMPLETE stored
        # collections must equal the COMPLETE incoming collections before any
        # child membership is added; an added, removed, or changed child means
        # a changed aggregate and fails closed with no partial write.
        if not root_newly_inserted:
            stored_roles = {
                row.artefact_id: row.role
                for row in session.execute(
                    sa.select(
                        ExecutionArtefactRole.artefact_id, ExecutionArtefactRole.role
                    ).where(ExecutionArtefactRole.execution_evidence_id == evidence_id)
                )
            }
            if stored_roles != incoming_roles:
                raise DB004PersistenceConflictError(
                    f"execution artefact roles conflict for {evidence_id}"
                )
            stored_cases = {
                (row.ordinal, row.test_reference): (
                    row.case_status,
                    row.failure_reference,
                )
                for row in session.execute(
                    sa.select(
                        ExecutionTestCaseResult.ordinal,
                        ExecutionTestCaseResult.test_reference,
                        ExecutionTestCaseResult.case_status,
                        ExecutionTestCaseResult.failure_reference,
                    ).where(ExecutionTestCaseResult.execution_evidence_id == evidence_id)
                )
            }
            if stored_cases != incoming_cases:
                raise DB004PersistenceConflictError(
                    f"execution test-case facts conflict for {evidence_id}"
                )
            stored_observations = {
                row.ordinal: _observation_key(_observation_stored_payload(row))
                for row in session.execute(
                    sa.select(ExecutionResourceObservation).where(
                        ExecutionResourceObservation.execution_evidence_id == evidence_id
                    )
                ).scalars()
            }
            if stored_observations != incoming_observations:
                raise DB004PersistenceConflictError(
                    f"execution resource observations conflict for {evidence_id}"
                )

        for reference, role in role_pairs:
            persist_artefact_reference_metadata(session, reference)
            _converge_row(
                session,
                ExecutionArtefactRole,
                {
                    "execution_evidence_id": evidence_id,
                    "artefact_id": reference.artefact_id.value,
                    "role": role,
                },
                {
                    "execution_evidence_id": evidence_id,
                    "artefact_id": reference.artefact_id.value,
                },
            )

        for case_value in case_values:
            _converge_row(
                session,
                ExecutionTestCaseResult,
                case_value,
                {
                    "execution_evidence_id": evidence_id,
                    "ordinal": case_value["ordinal"],
                },
            )

        for observation_value in observation_values:
            _converge_row(
                session,
                ExecutionResourceObservation,
                observation_value,
                {
                    "execution_evidence_id": evidence_id,
                    "ordinal": observation_value["ordinal"],
                },
            )

    return session.get(ExecutionEvidenceRecord, {"execution_evidence_id": evidence_id})


def _observation_stored_payload(row: ExecutionResourceObservation) -> dict[str, object]:
    return {
        "resource_category": row.resource_category,
        "enforcement_status": row.enforcement_status,
        "terminated_execution": row.terminated_execution,
        "configured_amount": row.configured_amount,
        "configured_unit": row.configured_unit,
        "configuration_reference": row.configuration_reference,
        "observed_amount": row.observed_amount,
        "observed_unit": row.observed_unit,
        "breached": row.breached,
        "truncated": row.truncated,
        "fact_reference": row.fact_reference,
        "other_category": row.other_category,
    }


# ---------------------------------------------------------------------------
# Artefact manifests
# ---------------------------------------------------------------------------


def persist_artefact_manifest_metadata(
    session: Session, manifest: ArtefactManifest
) -> ArtefactManifestRecord:
    """Persist one ArtefactManifest and its relational membership atomically.

    EVIDENCE-009 finalization shape is enforced physically; membership is
    relational and unordered, and a changed membership under the same manifest
    identity is a conflict because changed manifests need distinct identities.
    """
    _require_type(manifest, ArtefactManifest, "manifest")
    manifest_id = manifest.artefact_manifest_id.value

    candidate_row = None
    if manifest.candidate_version_id is not None:
        candidate_row = _require_candidate_version(
            session, manifest.candidate_version_id.value
        )
    evidence_row = None
    if manifest.execution_evidence_id is not None:
        evidence_row = _stored_row(
            session,
            ExecutionEvidenceRecord,
            {"execution_evidence_id": manifest.execution_evidence_id.value},
        )
        if evidence_row is None:
            raise DB004UnresolvableReferenceError(
                f"execution evidence not found: {manifest.execution_evidence_id.value}"
            )
    attempt_uuid = None
    attempt_run_id = None
    if manifest.workflow_attempt_id is not None:
        attempt_uuid = _parse_durable_uuid(
            manifest.workflow_attempt_id.value, "workflow_attempt_id"
        )
        row = session.execute(
            sa.select(WorkflowStepAttempt.id, WorkflowStep.run_id)
            .join(WorkflowStep, WorkflowStep.id == WorkflowStepAttempt.step_id)
            .where(WorkflowStepAttempt.id == attempt_uuid)
        ).first()
        if row is None:
            raise DB004UnresolvableReferenceError(
                f"workflow attempt not found: {attempt_uuid}"
            )
        attempt_run_id = row.run_id

    # Relational provenance consistency only: wherever multiple linkage
    # fields are supplied, they must describe the same durable relationships.
    if (
        evidence_row is not None
        and candidate_row is not None
        and evidence_row["candidate_version_id"] != manifest.candidate_version_id.value
    ):
        raise ValueError(
            "manifest links execution evidence"
            f" {evidence_row['execution_evidence_id']} to candidate"
            f" {manifest.candidate_version_id.value} but that evidence belongs"
            f" to candidate {evidence_row['candidate_version_id']}"
        )
    if (
        evidence_row is not None
        and attempt_uuid is not None
        and evidence_row["workflow_attempt_id"] != attempt_uuid
    ):
        raise ValueError(
            f"manifest links execution evidence {manifest.execution_evidence_id.value}"
            f" to attempt {attempt_uuid} but that evidence was produced by"
            f" attempt {evidence_row['workflow_attempt_id']}"
        )
    phase_value = (
        manifest.execution_phase.value if manifest.execution_phase is not None else None
    )
    if evidence_row is not None and evidence_row["execution_phase"] != phase_value:
        raise ValueError(
            f"manifest declares execution phase {phase_value} but its execution"
            f" evidence {manifest.execution_evidence_id.value} was recorded in"
            f" phase {evidence_row['execution_phase']}"
        )
    if candidate_row is not None and attempt_run_id is not None:
        if candidate_row["run_id"] != attempt_run_id:
            raise ValueError(
                f"workflow attempt {attempt_uuid} does not belong to run"
                f" {candidate_row['run_id']} owning candidate"
                f" {manifest.candidate_version_id.value}"
            )

    integrity = manifest.integrity_metadata
    values = {
        "artefact_manifest_id": manifest_id,
        "creation_timestamp": manifest.creation_timestamp,
        "finalization_state": manifest.finalization_state.value,
        "candidate_version_id": _reference_value(manifest.candidate_version_id),
        "execution_evidence_id": _reference_value(manifest.execution_evidence_id),
        "workflow_attempt_id": attempt_uuid,
        "execution_phase": manifest.execution_phase.value
        if manifest.execution_phase is not None
        else None,
        "producer_provenance_reference": _reference_value(
            manifest.producer_provenance_reference
        ),
        "manifest_digest": _reference_value(manifest.manifest_digest),
        "manifest_digest_algorithm": _reference_value(
            manifest.manifest_digest_algorithm
        ),
        "integrity_state": integrity.state.value if integrity else None,
        "integrity_verification_reference": _reference_value(
            integrity.verification_reference if integrity else None
        ),
        "finalization_timestamp": manifest.finalization_timestamp,
        "contract_version": manifest.contract_version,
        "schema_version": manifest.schema_version,
    }

    member_ids = [entry.artefact_id.value for entry in manifest.artefact_references]
    if len(member_ids) != len(set(member_ids)):
        raise ValueError("manifest membership must not duplicate artefact identities")
    # Manifest members must already have durable ArtefactReference rows, and
    # the supplied member metadata must be equivalent to the stored row for
    # that artefact identity; any conflicting field fails closed.
    for entry in manifest.artefact_references:
        artefact_id = entry.artefact_id.value
        stored = _stored_row(
            session, ArtefactReferenceRecord, {"artefact_id": artefact_id}
        )
        if stored is None:
            raise DB004UnresolvableReferenceError(f"artefact not found: {artefact_id}")
        _assert_equivalent(
            "ArtefactReferenceRecord",
            {"artefact_id": artefact_id},
            stored,
            {
                name: value
                for name, value in _artefact_values(entry).items()
                if name != "artefact_id"
            },
        )

    with session.begin_nested():
        root_existed = not _converge_row(
            session,
            ArtefactManifestRecord,
            values,
            {"artefact_manifest_id": manifest_id},
        )
        # Membership is immutable per identity: a manifest that already
        # exists must arrive with exactly its stored membership; growth or
        # shrinkage means a changed manifest and needs a distinct identity.
        if root_existed:
            stored_members = {
                row.artefact_id
                for row in session.execute(
                    sa.select(ArtefactManifestMember.artefact_id).where(
                        ArtefactManifestMember.artefact_manifest_id == manifest_id
                    )
                )
            }
            if stored_members != set(member_ids):
                raise DB004PersistenceConflictError(
                    f"manifest membership conflicts for {manifest_id};"
                    " changed manifests need a distinct identity"
                )
        else:
            for artefact_id in sorted(member_ids):
                _converge_row(
                    session,
                    ArtefactManifestMember,
                    {
                        "artefact_manifest_id": manifest_id,
                        "artefact_id": artefact_id,
                    },
                    {
                        "artefact_manifest_id": manifest_id,
                        "artefact_id": artefact_id,
                    },
                )

    return session.get(ArtefactManifestRecord, {"artefact_manifest_id": manifest_id})
