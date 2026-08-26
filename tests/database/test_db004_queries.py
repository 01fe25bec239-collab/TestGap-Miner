"""DB-004R read-side reconstruction behavior against real PostgreSQL.

Covers exact-identity readback for every DB-004 aggregate family, explicit and
deterministic child ordering, fail-closed malformed identities, explicit
not-found unknown identities, and the read-only guarantee: no autoflush, no
commit, no rollback, no row mutation, and no transaction control.
"""

import uuid
from dataclasses import fields as dataclass_fields
from datetime import timedelta
from types import MappingProxyType, SimpleNamespace

import pytest
import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Session

from app.db.db004_persistence import (
    persist_artefact_manifest_metadata,
    persist_artefact_reference_metadata,
    persist_candidate_metadata,
    persist_context_bundle_metadata,
    persist_execution_evidence_metadata,
)
from app.db.db004_queries import (
    DB004PersistedArtefactManifest,
    DB004PersistedArtefactReference,
    DB004PersistedCandidatePatch,
    DB004PersistedCandidateVersion,
    DB004PersistedContextBundle,
    DB004PersistedExecutionEvidence,
    DB004QueryInvalidIdentityError,
    DB004QueryNotFoundError,
    get_artefact_manifest_projection,
    get_artefact_reference_projection,
    get_candidate_patch_projection,
    get_candidate_version_projection,
    get_context_bundle_projection,
    get_execution_evidence_projection,
)
from app.db.models.context import ContextBundleItem
from app.db.models.evidence import (
    ArtefactManifestMember,
    CandidateChangedFile,
    ExecutionArtefactRole,
    ExecutionResourceObservation,
    ExecutionTestCaseResult,
)
from app.evidence.artefact import (
    ArtefactId,
    ArtefactManifestFinalizationState,
    ArtefactManifestId,
)
from app.evidence.candidate import (
    CandidateFinalizationState,
    CandidatePatchId,
    ChangedFile,
)
from app.evidence.execution import (
    CandidateVersionId,
    CompileResult,
    CompileStatus,
    CorrelationId,
    EVIDENCE_CONTRACT_VERSION,
    ExecutionEvidenceId,
    ExecutionOutcome,
    ExecutionPhase,
    ExecutionTiming,
    FailureCategory,
    FailureEvidence,
    OpaqueReference,
    ProcessExit,
    ProducerResultId,
    QueueDeliveryId,
    QueueMessageId,
    ResourceCategory,
    ResourceEnforcementStatus,
    ResourceObservation,
    ResourceValue,
    RunId,
    TestCaseResult,
    TestCaseStatus,
    TestResult,
    TimeoutMetadata,
    WorkflowAttemptId,
)
from db004_support import (
    GENERATED_AT,
    REVISION_40,
    make_artefact_manifest,
    make_artefact_reference,
    make_candidate_patch,
    make_candidate_version,
    make_compile_evidence,
    make_context_bundle,
    make_context_item,
    make_execution_evidence,
    make_finalized_manifest_fields,
    make_integrity,
)
from support import DB_004_TABLES, make_attempt, make_run, make_run_request, make_step


# ---------------------------------------------------------------------------
# Shared durable seeding (through the DB-004 persistence layer)
# ---------------------------------------------------------------------------


def _workflow(session: Session) -> SimpleNamespace:
    request = make_run_request()
    run = make_run(request)
    session.add_all([request, run])
    session.flush()
    step = make_step(run, kind="GENERATE_CANDIDATE")
    session.add(step)
    session.flush()
    attempt = make_attempt(step)
    session.add(attempt)
    session.flush()
    return SimpleNamespace(request=request, run=run, step=step, attempt=attempt)


def _candidate(session: Session, **version_overrides) -> SimpleNamespace:
    workflow = _workflow(session)
    run_id = str(workflow.run.id)
    patch_row, version_row = persist_candidate_metadata(
        session,
        patch=make_candidate_patch(run_id, str(workflow.attempt.id)),
        version=make_candidate_version(
            run_id, str(workflow.attempt.id), **version_overrides
        ),
    )
    return SimpleNamespace(
        workflow=workflow, patch_row=patch_row, version_row=version_row
    )


def _execution(session: Session, **overrides):
    aggregate = _candidate(session)
    evidence = make_execution_evidence(
        workflow_attempt_id=str(aggregate.workflow.attempt.id), **overrides
    )
    persist_execution_evidence_metadata(session, evidence)
    return aggregate, evidence


def _flush_rows(session: Session) -> None:
    session.flush()


def _table_counts(session: Session) -> dict[str, int]:
    return {
        name: session.scalar(sa.text(f"SELECT COUNT(*) FROM {name}"))
        for name in sorted(DB_004_TABLES)
    }


def _pending_item(
    item_id: str, position: int, digest_hex: str, bundle_id: str = "context-bundle-1"
) -> ContextBundleItem:
    return ContextBundleItem(
        context_item_id=item_id,
        context_bundle_id=bundle_id,
        position=position,
        candidate_id="candidate-pending",
        file_identity=f"src/{item_id}.java",
        start_line=1,
        end_line=1,
        content_sha256=digest_hex * 64,
        trust_label="UNTRUSTED_REPOSITORY_TEXT",
        token_count=1,
    )


# ---------------------------------------------------------------------------
# CONTEXT_BUNDLE_READBACK / CONTEXT_ITEM_ORDER
# ---------------------------------------------------------------------------


def test_context_bundle_readback_preserves_complete_root_and_item_metadata(
    session: Session,
) -> None:
    bundle = make_context_bundle(
        context_bundle_id="ctx-bundle-full",
        max_tokens=512,
        items=(
            make_context_item(
                context_item_id="ctx-item-full",
                candidate_id="candidate-full",
                file_identity="src/main/java/Full.java",
                start_line=7,
                end_line=9,
                token_count=21,
            ),
        ),
    )
    persist_context_bundle_metadata(session, bundle)

    projection = get_context_bundle_projection(session, "ctx-bundle-full")

    assert isinstance(projection, DB004PersistedContextBundle)
    assert projection.context_bundle_id == "ctx-bundle-full"
    assert projection.repository_id == "benchmark-repo"
    assert projection.revision_id == REVISION_40
    assert projection.contract_version == "1.0.0-draft.1"
    assert (projection.max_tokens, projection.consumed_tokens) == (512, 21)
    assert projection.created_at is not None

    assert len(projection.items) == 1
    item = projection.items[0]
    assert item.context_item_id == "ctx-item-full"
    assert item.context_bundle_id == "ctx-bundle-full"
    assert item.position == 1
    assert item.candidate_id == "candidate-full"
    assert item.file_identity == "src/main/java/Full.java"
    assert (item.start_line, item.end_line) == (7, 9)
    assert len(item.content_sha256) == 64
    assert item.trust_label == "UNTRUSTED_REPOSITORY_TEXT"
    assert item.token_count == 21


def test_context_items_are_position_ordered_over_adversarial_insertion(
    session: Session,
) -> None:
    bundle = make_context_bundle(
        context_bundle_id="ctx-bundle-order",
        max_tokens=64,
        items=(make_context_item(context_item_id="ctx-item-p1", token_count=4),),
    )
    persist_context_bundle_metadata(session, bundle)
    # Insert later positions first so physical insertion order differs from
    # position ASC; an unspecified SELECT would expose the insertion order.
    session.add(
        ContextBundleItem(
            context_item_id="ctx-item-p3",
            context_bundle_id="ctx-bundle-order",
            position=3,
            candidate_id="candidate-3",
            file_identity="src/C.java",
            start_line=3,
            end_line=3,
            content_sha256="c" * 64,
            trust_label="UNTRUSTED_REPOSITORY_TEXT",
            token_count=3,
        )
    )
    session.add(
        ContextBundleItem(
            context_item_id="ctx-item-p2",
            context_bundle_id="ctx-bundle-order",
            position=2,
            candidate_id="candidate-2",
            file_identity="src/B.java",
            start_line=2,
            end_line=2,
            content_sha256="b" * 64,
            trust_label="UNTRUSTED_REPOSITORY_TEXT",
            token_count=2,
        )
    )
    _flush_rows(session)

    projection = get_context_bundle_projection(session, "ctx-bundle-order")

    assert [(i.position, i.context_item_id) for i in projection.items] == [
        (1, "ctx-item-p1"),
        (2, "ctx-item-p2"),
        (3, "ctx-item-p3"),
    ]
    assert [i.file_identity for i in projection.items] == [
        "src/main/java/Example.java",
        "src/B.java",
        "src/C.java",
    ]


def test_context_projection_exposes_no_raw_content(session: Session) -> None:
    persist_context_bundle_metadata(session, make_context_bundle())
    projection = get_context_bundle_projection(session, "context-bundle-1")
    rendered = repr(projection) + repr(projection.items[0])
    assert "class Example" not in rendered
    item_names = {f.name for f in dataclass_fields(projection.items[0])}
    root_names = {f.name for f in dataclass_fields(projection)}
    for forbidden in ("content", "payload", "text", "source_bytes", "blob"):
        assert forbidden not in root_names
        assert forbidden not in item_names
    assert not hasattr(projection.items[0], "content")


# ---------------------------------------------------------------------------
# CANDIDATE_PATCH_READBACK / CANDIDATE_VERSION_READBACK / LINEAGE / CHANGED FILES
# ---------------------------------------------------------------------------


def test_candidate_patch_readback_preserves_every_persisted_field(
    session: Session,
) -> None:
    workflow = _workflow(session)
    run_id = str(workflow.run.id)
    finalized_at = GENERATED_AT + timedelta(hours=1)
    patch = make_candidate_patch(
        run_id,
        str(workflow.attempt.id),
        candidate_patch_id=CandidatePatchId("patch-final"),
        candidate_version_id=CandidateVersionId("version-final"),
        changed_files_manifest=(
            ChangedFile(path="z-last/Path.java", change_summary="rewrote handler"),
            ChangedFile(path="a-first/Path.java", change_summary="created handler"),
        ),
        finalization_state=CandidateFinalizationState.FINALIZED,
        finalized_at=finalized_at,
        target_reference_revision=OpaqueReference(REVISION_40),
        patch_content_reference=OpaqueReference("content://patch-final"),
        model_identifier=OpaqueReference("model://claude-opus-5"),
        prompt_template_version=OpaqueReference("prompt://v7"),
        localisation_provenance_reference=OpaqueReference("locprov://slot-1"),
        correlation_id=CorrelationId("corr-patch-1"),
    )
    version = make_candidate_version(
        run_id,
        str(workflow.attempt.id),
        candidate_version_id="version-final",
        candidate_patch_id="patch-final",
        target_reference_revision=OpaqueReference(REVISION_40),
        model_identifier=OpaqueReference("model://claude-opus-5"),
        prompt_template_version=OpaqueReference("prompt://v7"),
        localisation_provenance_reference=OpaqueReference("locprov://slot-1"),
        correlation_id=CorrelationId("corr-patch-1"),
    )
    persist_candidate_metadata(session, patch=patch, version=version)

    projection = get_candidate_patch_projection(session, "patch-final")

    assert isinstance(projection, DB004PersistedCandidatePatch)
    assert projection.candidate_patch_id == "patch-final"
    assert projection.candidate_version_id == "version-final"
    assert projection.run_id == workflow.run.id
    assert projection.workflow_attempt_id == workflow.attempt.id
    assert projection.source_repository == "github://example/example-repo"
    assert projection.source_revision == REVISION_40
    assert projection.target_reference_revision == REVISION_40
    assert projection.patch_digest == "sha256:" + "cd" * 32
    assert projection.digest_algorithm == "SHA-256"
    assert projection.test_only_scope is True
    assert projection.test_only_scope_reference == "scope-ref://patch-1"
    assert projection.generator_reference == "generator://test-generator-v1"
    assert projection.tool_version_reference == "tool://javac-21.0.1"
    assert projection.generated_at == GENERATED_AT
    assert projection.configuration_version == "config-v1"
    assert projection.finalization_state == "FINALIZED"
    assert projection.finalized_at == finalized_at
    assert projection.patch_content_reference == "content://patch-final"
    assert projection.model_identifier == "model://claude-opus-5"
    assert projection.prompt_template_version == "prompt://v7"
    assert projection.localisation_provenance_reference == "locprov://slot-1"
    assert projection.correlation_id == "corr-patch-1"
    assert projection.contract_version == EVIDENCE_CONTRACT_VERSION


def test_changed_file_membership_is_exact_and_path_ordered(
    session: Session,
) -> None:
    _candidate(session)
    # Persisted membership arrives path-sorted; append a lexicographically
    # first path afterwards so unspecified selection would misorder it.
    session.add(
        CandidateChangedFile(
            candidate_patch_id="candidate-patch-1",
            path="aaa-first/Example.java",
            change_summary="inserted after the durable manifest",
        )
    )
    _flush_rows(session)

    projection = get_candidate_patch_projection(session, "candidate-patch-1")

    assert [
        (f.path, f.change_summary, f.candidate_patch_id)
        for f in projection.changed_files
    ] == [
        (
            "aaa-first/Example.java",
            "inserted after the durable manifest",
            "candidate-patch-1",
        ),
        (
            "src/test/java/ExampleTest.java",
            "added failing assertions for bug 1",
            "candidate-patch-1",
        ),
    ]


def test_candidate_version_readback_preserves_every_persisted_field(
    session: Session,
) -> None:
    aggregate = _candidate(session)
    workflow = aggregate.workflow
    _, version_row = persist_candidate_metadata(
        session,
        patch=make_candidate_patch(
            str(workflow.run.id),
            str(workflow.attempt.id),
            candidate_patch_id=CandidatePatchId("patch-child"),
            candidate_version_id=CandidateVersionId("version-child"),
            target_reference_revision=OpaqueReference(REVISION_40),
            model_identifier=OpaqueReference("model://claude-opus-5"),
            prompt_template_version=OpaqueReference("prompt://v7"),
            localisation_provenance_reference=OpaqueReference("locprov://slot-2"),
            correlation_id=CorrelationId("corr-version-1"),
        ),
        version=make_candidate_version(
            str(workflow.run.id),
            str(workflow.attempt.id),
            candidate_version_id="version-child",
            candidate_patch_id="patch-child",
            repair_level=1,
            parent_candidate_version_id="candidate-version-1",
            producer_result_id="producer-result-42",
            target_reference_revision=OpaqueReference(REVISION_40),
            model_identifier=OpaqueReference("model://claude-opus-5"),
            prompt_template_version=OpaqueReference("prompt://v7"),
            localisation_provenance_reference=OpaqueReference("locprov://slot-2"),
            correlation_id=CorrelationId("corr-version-1"),
        ),
    )

    projection = get_candidate_version_projection(session, "version-child")

    assert version_row.candidate_version_id == "version-child"
    assert isinstance(projection, DB004PersistedCandidateVersion)
    assert projection.candidate_version_id == "version-child"
    assert projection.candidate_patch_id == "patch-child"
    assert projection.run_id == workflow.run.id
    assert projection.workflow_attempt_id == workflow.attempt.id
    assert projection.producer_result_id == "producer-result-42"
    assert projection.repair_level == 1
    assert projection.parent_candidate_version_id == "candidate-version-1"
    assert projection.source_repository == "github://example/example-repo"
    assert projection.source_revision == REVISION_40
    assert projection.target_reference_revision == REVISION_40
    assert projection.generator_reference == "generator://test-generator-v1"
    assert projection.tool_version_reference == "tool://javac-21.0.1"
    assert projection.generated_at == GENERATED_AT
    assert projection.configuration_version == "config-v1"
    assert projection.finalization_state == "CREATED"
    assert projection.finalized_at is None
    assert projection.model_identifier == "model://claude-opus-5"
    assert projection.prompt_template_version == "prompt://v7"
    assert projection.localisation_provenance_reference == "locprov://slot-2"
    assert projection.correlation_id == "corr-version-1"
    assert projection.contract_version == EVIDENCE_CONTRACT_VERSION


def test_candidate_lineage_and_identity_separation_survive_reconstruction(
    session: Session,
) -> None:
    aggregate = _candidate(session)
    workflow = aggregate.workflow
    persist_candidate_metadata(
        session,
        patch=make_candidate_patch(
            str(workflow.run.id),
            str(workflow.attempt.id),
            candidate_patch_id=CandidatePatchId("patch-repaired"),
            candidate_version_id=CandidateVersionId("version-repaired"),
        ),
        version=make_candidate_version(
            str(workflow.run.id),
            str(workflow.attempt.id),
            candidate_version_id="version-repaired",
            candidate_patch_id="patch-repaired",
            repair_level=1,
            parent_candidate_version_id="candidate-version-1",
        ),
    )

    initial = get_candidate_version_projection(session, "candidate-version-1")
    repaired = get_candidate_version_projection(session, "version-repaired")
    initial_patch = get_candidate_patch_projection(session, "candidate-patch-1")
    repaired_patch = get_candidate_patch_projection(session, "patch-repaired")

    assert initial.repair_level == 0
    assert initial.parent_candidate_version_id is None
    assert repaired.parent_candidate_version_id == initial.candidate_version_id
    assert repaired.repair_level == 1
    assert repaired.run_id == initial.run_id
    assert repaired.workflow_attempt_id == initial.workflow_attempt_id
    # Patch and version identities stay distinct durable identity kinds.
    assert initial_patch.candidate_patch_id != initial.candidate_version_id
    assert repaired_patch.candidate_patch_id != repaired.candidate_version_id
    assert initial_patch.candidate_version_id == initial.candidate_version_id
    assert repaired_patch.candidate_version_id == repaired.candidate_version_id


# ---------------------------------------------------------------------------
# EXECUTION_EVIDENCE_READBACK / EXECUTION_CHILD_METADATA
# ---------------------------------------------------------------------------


def _memory_observation() -> ResourceObservation:
    return ResourceObservation(
        category=ResourceCategory.MEMORY_BYTES,
        enforcement_status=ResourceEnforcementStatus.CAPTURE_BOUND_ENFORCED,
        terminated_execution=False,
        configured_value=ResourceValue(amount=1024, unit="bytes"),
        observed_value=ResourceValue(amount=512, unit="bytes"),
        breached=False,
    )


def test_execution_evidence_readback_covers_every_persisted_root_field(
    session: Session,
) -> None:
    aggregate = _candidate(session)
    workflow = aggregate.workflow
    persist_execution_evidence_metadata(
        session,
        make_execution_evidence(
            workflow_attempt_id=str(workflow.attempt.id),
            run_id=RunId(str(workflow.run.id)),
            queue_message_id=QueueMessageId("queue-message-1"),
            queue_delivery_id=QueueDeliveryId("queue-delivery-1"),
            correlation_id=CorrelationId("correlation-1"),
            execution_timing=ExecutionTiming(
                started_at=GENERATED_AT,
                ended_at=GENERATED_AT + timedelta(seconds=30),
                duration=timedelta(seconds=30),
                upstream_fact_reference=OpaqueReference("fact://timing-1"),
            ),
            timeout_metadata=TimeoutMetadata(timed_out=False),
            runtime_metadata_reference=OpaqueReference("runtime://meta-1"),
            sandbox_metadata_reference=OpaqueReference("sandbox://meta-1"),
            environment_metadata_reference=OpaqueReference("environment://meta-1"),
            flake_indication_reference=OpaqueReference("flake://indication-1"),
            execution_integrity=make_integrity(),
            resource_observations=(_memory_observation(),),
            test_result=TestResult(
                executed_count=2,
                passed_count=1,
                skipped_count=1,
                test_cases=(
                    TestCaseResult(
                        test_reference=OpaqueReference("test://Zed.testZ"),
                        status=TestCaseStatus.SKIPPED,
                    ),
                    TestCaseResult(
                        test_reference=OpaqueReference("test://Alpha.testA"),
                        status=TestCaseStatus.PASSED,
                    ),
                ),
            ),
        ),
    )

    projection = get_execution_evidence_projection(session, "execution-evidence-1")

    assert isinstance(projection, DB004PersistedExecutionEvidence)
    assert projection.execution_evidence_id == "execution-evidence-1"
    assert projection.producer_result_id == "producer-result-1"
    # DB-004 correction fields survive exactly and separately.
    assert projection.queue_message_id == "queue-message-1"
    assert projection.queue_delivery_id == "queue-delivery-1"
    assert projection.correlation_id == "correlation-1"
    assert projection.timing_fact_reference == "fact://timing-1"
    assert projection.candidate_version_id == "candidate-version-1"
    assert projection.run_id == workflow.run.id
    assert projection.workflow_attempt_id == workflow.attempt.id
    assert projection.execution_phase == "BUGGY_OR_TARGET_REVISION_TEST"
    assert projection.outcome == "SUCCESS"
    assert projection.completeness == "PARTIAL"
    assert projection.command_reference == "command://mvn-test-1"
    assert projection.execution_fact_reference == "execution-fact://run-1"
    assert projection.source_revision == REVISION_40
    assert projection.started_at == GENERATED_AT
    assert projection.ended_at == GENERATED_AT + timedelta(seconds=30)
    assert projection.duration_microseconds == 30_000_000
    assert projection.timeout_timed_out is False
    assert projection.timeout_classification is None
    assert projection.timeout_limit_microseconds is None
    assert projection.timeout_fact_reference is None
    assert projection.exit_code is None
    assert projection.signal_number is None
    assert projection.signal_name is None
    assert projection.exit_fact_reference is None
    assert projection.integrity_state == "UNVERIFIABLE"
    assert projection.integrity_verification_reference is None
    assert projection.runtime_metadata_reference == "runtime://meta-1"
    assert projection.sandbox_metadata_reference == "sandbox://meta-1"
    assert projection.environment_metadata_reference == "environment://meta-1"
    assert projection.flake_indication_reference == "flake://indication-1"
    assert projection.failure_category is None
    assert projection.failure_reference is None
    assert projection.secondary_failures is None
    assert projection.compile_status is None
    assert projection.compile_error_count is None
    assert projection.compile_warning_count is None
    assert projection.compile_metadata_reference is None
    assert projection.test_executed_count == 2
    assert projection.test_passed_count == 1
    assert projection.test_skipped_count == 1
    assert projection.test_failed_count is None
    assert projection.test_errored_count is None
    assert projection.test_failure_summary_reference is None
    assert projection.contract_version == EVIDENCE_CONTRACT_VERSION


def test_execution_failure_timeout_and_secondary_failures_round_trip(
    session: Session,
) -> None:
    _execution(
        session,
        outcome=ExecutionOutcome.TIMEOUT,
        failure=FailureEvidence(
            FailureCategory.TIMEOUT,
            upstream_failure_reference=OpaqueReference("failure://timeout-1"),
        ),
        secondary_failures=(
            FailureEvidence(
                FailureCategory.TIMEOUT,
                upstream_failure_reference=OpaqueReference("failure://timeout-2"),
            ),
            FailureEvidence(
                FailureCategory.CANCELLATION,
                upstream_failure_reference=OpaqueReference("failure://cancel-2"),
            ),
        ),
        timeout_metadata=TimeoutMetadata(
            timed_out=True,
            classification=OpaqueReference("timeout://wall-clock-600s"),
            configured_limit=timedelta(seconds=600),
            upstream_fact_reference=OpaqueReference("fact://timeout-config"),
        ),
        process_exit=ProcessExit(
            signal_number=9,
            signal_name="SIGKILL",
            upstream_fact_reference=OpaqueReference("fact://signal"),
        ),
    )

    projection = get_execution_evidence_projection(session, "execution-evidence-1")

    assert projection.outcome == "TIMEOUT"
    assert projection.failure_category == "TIMEOUT"
    assert projection.failure_reference == "failure://timeout-1"
    assert projection.timeout_timed_out is True
    assert projection.timeout_classification == "timeout://wall-clock-600s"
    assert projection.timeout_limit_microseconds == 600_000_000
    assert projection.timeout_fact_reference == "fact://timeout-config"
    # Absent facts stay absent: an exit code was never supplied.
    assert projection.exit_code is None
    assert projection.signal_number == 9
    assert projection.signal_name == "SIGKILL"
    assert projection.exit_fact_reference == "fact://signal"
    assert projection.secondary_failures is not None
    assert len(projection.secondary_failures) == 2
    assert all(
        isinstance(entry, MappingProxyType)
        for entry in projection.secondary_failures
    )
    assert [
        dict(entry)["category"] for entry in projection.secondary_failures
    ] == ["CANCELLATION", "TIMEOUT"]
    assert dict(projection.secondary_failures[0])["upstream_failure_reference"] == (
        "failure://cancel-2"
    )
    with pytest.raises(TypeError):
        projection.secondary_failures[0]["category"] = "MUTATED"


def test_compile_evidence_absent_optional_fields_stay_absent(
    session: Session,
) -> None:
    aggregate = _candidate(session)
    persist_execution_evidence_metadata(
        session,
        make_compile_evidence(
            workflow_attempt_id=str(aggregate.workflow.attempt.id),
            execution_evidence_id=ExecutionEvidenceId("exec-compile-absent"),
            compile_result=CompileResult(status=CompileStatus.SUCCESS),
            execution_timing=None,
            timeout_metadata=None,
        ),
    )

    projection = get_execution_evidence_projection(session, "exec-compile-absent")

    assert projection.execution_phase == "COMPILE"
    assert projection.outcome == "SUCCESS"
    assert projection.compile_status == "SUCCESS"
    assert projection.compile_error_count is None
    assert projection.compile_warning_count is None
    assert projection.compile_metadata_reference is None
    assert projection.source_revision is None
    assert projection.run_id is None
    assert projection.started_at is None
    assert projection.ended_at is None
    assert projection.duration_microseconds is None
    assert projection.timing_fact_reference is None
    assert projection.queue_message_id is None
    assert projection.queue_delivery_id is None
    assert projection.correlation_id is None
    assert projection.integrity_state is None
    assert projection.failure_category is None
    assert projection.secondary_failures is None
    assert projection.test_executed_count is None
    assert projection.test_cases == ()
    assert projection.resource_observations == ()
    assert projection.artefact_roles == ()


def test_execution_child_collections_are_exact_and_deterministically_ordered(
    session: Session,
) -> None:
    aggregate = _candidate(session)
    persist_execution_evidence_metadata(
        session,
        make_execution_evidence(
            workflow_attempt_id=str(aggregate.workflow.attempt.id),
            test_result=TestResult(executed_count=0),
            resource_observations=(),
        ),
    )
    # Children carry durable semantic keys, not insertion chronology: insert
    # each collection in descending key order to expose any unspecified SELECT.
    for ordinal, reference in (
        (3, "test://Gamma.g"),
        (2, "test://Beta.b"),
        (1, "test://Alpha.a"),
    ):
        session.add(
            ExecutionTestCaseResult(
                execution_evidence_id="execution-evidence-1",
                ordinal=ordinal,
                test_reference=reference,
                case_status="PASSED",
                failure_reference=None,
            )
        )
    for ordinal, category, amount, unit in (
        (3, ResourceCategory.FILE_COUNT, 12, "files"),
        (2, ResourceCategory.CPU_TIME, 4, "milliseconds"),
        (1, ResourceCategory.MEMORY_BYTES, 2048, "bytes"),
    ):
        session.add(
            ExecutionResourceObservation(
                execution_evidence_id="execution-evidence-1",
                ordinal=ordinal,
                resource_category=category.value,
                enforcement_status="CAPTURE_BOUND_ENFORCED",
                terminated_execution=False,
                configured_amount=amount,
                configured_unit=unit,
                configuration_reference=f"config://{category.value.lower()}",
                observed_amount=None,
                observed_unit=None,
                breached=False,
                truncated=False,
                fact_reference=None,
                other_category=None,
            )
        )
    for artefact_id in ("art.roles.c", "art.roles.b", "art.roles.a"):
        reference = make_artefact_reference(
            artefact_id=ArtefactId(artefact_id),
            artefact_type="CUSTOM_OUTPUT",
            storage_locator=f"object-store://bucket/roles/{artefact_id}",
        )
        persist_artefact_reference_metadata(session, reference)
        session.add(
            ExecutionArtefactRole(
                execution_evidence_id="execution-evidence-1",
                artefact_id=artefact_id,
                role="OUTPUT",
            )
        )
    _flush_rows(session)

    projection = get_execution_evidence_projection(session, "execution-evidence-1")

    assert [
        (c.ordinal, c.test_reference, c.case_status, c.failure_reference)
        for c in projection.test_cases
    ] == [
        (1, "test://Alpha.a", "PASSED", None),
        (2, "test://Beta.b", "PASSED", None),
        (3, "test://Gamma.g", "PASSED", None),
    ]
    assert [
        (o.ordinal, o.resource_category, o.configured_unit, o.configured_amount)
        for o in projection.resource_observations
    ] == [
        (1, "MEMORY_BYTES", "bytes", 2048),
        (2, "CPU_TIME", "milliseconds", 4),
        (3, "FILE_COUNT", "files", 12),
    ]
    # Role bindings have no ordinal: their durable key pair ends in
    # artefact_id, so artefact_id ASC is the faithful physical order.
    assert [(r.artefact_id, r.role) for r in projection.artefact_roles] == [
        ("art.roles.a", "OUTPUT"),
        ("art.roles.b", "OUTPUT"),
        ("art.roles.c", "OUTPUT"),
    ]


# ---------------------------------------------------------------------------
# ARTEFACT_REFERENCE_READBACK / ARTEFACT_MANIFEST_READBACK / MEMBERSHIP
# ---------------------------------------------------------------------------


def test_artefact_reference_readback_preserves_all_persisted_metadata(
    session: Session,
) -> None:
    _execution(session)
    created = GENERATED_AT + timedelta(minutes=2)
    stored = persist_artefact_reference_metadata(
        session,
        make_artefact_reference(
            artefact_id=ArtefactId("art.reference.full"),
            artefact_type="CUSTOM_OUTPUT",
            availability="AVAILABLE",
            integrity=make_integrity(
                state="VERIFIED", verification_reference="verify-ref://full"
            ),
            content_digest=OpaqueReference("sha256:" + "11" * 32),
            digest_algorithm=OpaqueReference("SHA-256"),
            byte_size=4096,
            media_type="application/xml",
            producer_id=OpaqueReference("producer://runner-1"),
            creation_timestamp=created,
            storage_locator="s3://evidence-bucket/reference-full/payload.bin",
            candidate_version_id=CandidateVersionId("candidate-version-1"),
            execution_evidence_id=ExecutionEvidenceId("execution-evidence-1"),
            redaction_state=OpaqueReference("redaction://applied"),
        ),
    )
    assert stored.artefact_id == "art.reference.full"

    projection = get_artefact_reference_projection(session, "art.reference.full")

    assert isinstance(projection, DB004PersistedArtefactReference)
    assert projection.artefact_id == "art.reference.full"
    assert projection.artefact_type == "CUSTOM_OUTPUT"
    assert projection.availability_state == "AVAILABLE"
    assert projection.integrity_state == "VERIFIED"
    assert projection.integrity_verification_reference == "verify-ref://full"
    assert projection.content_digest == "sha256:" + "11" * 32
    assert projection.digest_algorithm == "SHA-256"
    assert projection.byte_size == 4096
    assert projection.media_type == "application/xml"
    assert projection.producer_id == "producer://runner-1"
    assert projection.creation_timestamp == created
    # Availability and integrity stay independent axes; the locator survives
    # verbatim as opaque metadata and stays distinct from logical identity.
    assert projection.storage_locator == (
        "s3://evidence-bucket/reference-full/payload.bin"
    )
    assert projection.storage_locator != projection.artefact_id
    assert projection.candidate_version_id == "candidate-version-1"
    assert projection.execution_evidence_id == "execution-evidence-1"
    assert projection.redaction_state == "redaction://applied"
    assert projection.contract_version == EVIDENCE_CONTRACT_VERSION


def test_artefact_manifest_readback_assembling_then_finalized(
    session: Session,
) -> None:
    member = make_artefact_reference(
        artefact_id=ArtefactId("art.manifest.readback"),
        artefact_type="CUSTOM_OUTPUT",
        storage_locator="object-store://bucket/readback-member",
    )
    persist_artefact_reference_metadata(session, member)
    assembling = persist_artefact_manifest_metadata(
        session, make_artefact_manifest(members=(member,))
    )
    assert assembling.artefact_manifest_id == "manifest-1"

    assembling_projection = get_artefact_manifest_projection(session, "manifest-1")

    assert isinstance(assembling_projection, DB004PersistedArtefactManifest)
    assert assembling_projection.artefact_manifest_id == "manifest-1"
    assert assembling_projection.creation_timestamp == GENERATED_AT
    assert assembling_projection.finalization_state == "ASSEMBLING"
    assert assembling_projection.finalization_timestamp is None
    assert assembling_projection.producer_provenance_reference is None
    assert assembling_projection.manifest_digest is None
    assert assembling_projection.manifest_digest_algorithm is None
    assert assembling_projection.integrity_state is None
    assert assembling_projection.integrity_verification_reference is None
    assert assembling_projection.candidate_version_id is None
    assert assembling_projection.execution_evidence_id is None
    assert assembling_projection.workflow_attempt_id is None
    assert assembling_projection.execution_phase is None
    assert assembling_projection.contract_version == EVIDENCE_CONTRACT_VERSION
    assert assembling_projection.schema_version == "ARTEFACT-MANIFEST-SCHEMA-V1"

    aggregate, _ = _execution(session)
    finalized_member = make_artefact_reference(
        artefact_id=ArtefactId("art.manifest.final"),
        artefact_type="CUSTOM_OUTPUT",
        storage_locator="object-store://bucket/final-member",
    )
    persist_artefact_reference_metadata(session, finalized_member)
    persist_artefact_manifest_metadata(
        session,
        make_artefact_manifest(
            artefact_manifest_id=ArtefactManifestId("manifest-final"),
            members=(finalized_member,),
            finalization_state=ArtefactManifestFinalizationState.FINALIZED,
            candidate_version_id=CandidateVersionId("candidate-version-1"),
            execution_evidence_id=ExecutionEvidenceId("execution-evidence-1"),
            workflow_attempt_id=WorkflowAttemptId(str(aggregate.workflow.attempt.id)),
            execution_phase=ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST,
            **make_finalized_manifest_fields(),
        ),
    )

    finalized_projection = get_artefact_manifest_projection(session, "manifest-final")

    assert finalized_projection.finalization_state == "FINALIZED"
    assert finalized_projection.finalization_timestamp == (
        GENERATED_AT + timedelta(minutes=5)
    )
    assert finalized_projection.producer_provenance_reference == (
        "producer-result://slot-1"
    )
    assert finalized_projection.manifest_digest == "sha256:" + "9a" * 32
    assert finalized_projection.manifest_digest_algorithm == "SHA-256"
    assert finalized_projection.integrity_state == "VERIFIED"
    assert finalized_projection.integrity_verification_reference == (
        "verify-ref://manifest-1"
    )
    assert finalized_projection.candidate_version_id == "candidate-version-1"
    assert finalized_projection.execution_evidence_id == "execution-evidence-1"
    assert finalized_projection.workflow_attempt_id == aggregate.workflow.attempt.id
    assert finalized_projection.execution_phase == "BUGGY_OR_TARGET_REVISION_TEST"


def test_manifest_membership_is_exact_and_deterministically_ordered(
    session: Session,
) -> None:
    late = make_artefact_reference(
        artefact_id=ArtefactId("zzz.member.late"),
        artefact_type="CUSTOM_OUTPUT",
        storage_locator="object-store://bucket/late",
    )
    early = make_artefact_reference(
        artefact_id=ArtefactId("aaa.member.early"),
        artefact_type="CUSTOM_OUTPUT",
        storage_locator="object-store://bucket/early",
    )
    persist_artefact_reference_metadata(session, late)
    persist_artefact_reference_metadata(session, early)
    persist_artefact_manifest_metadata(
        session, make_artefact_manifest(members=(late,))
    )
    # Membership rows carry no order semantics; their durable compound primary
    # key ends in artefact_id, appended here out of lexical order to expose
    # any unspecified selection.
    session.add(
        ArtefactManifestMember(
            artefact_manifest_id="manifest-1", artefact_id="aaa.member.early"
        )
    )
    _flush_rows(session)

    projection = get_artefact_manifest_projection(session, "manifest-1")

    assert [
        (m.artefact_manifest_id, m.artefact_id) for m in projection.members
    ] == [
        ("manifest-1", "aaa.member.early"),
        ("manifest-1", "zzz.member.late"),
    ]


# ---------------------------------------------------------------------------
# IDENTITIES: MALFORMED_ID FAIL_CLOSED / UNKNOWN_ID EXPLICIT_NOT_FOUND
# ---------------------------------------------------------------------------

_RAG_BOUND = 256
_EVIDENCE_BOUND = 255

_FAMILIES = {
    "context": get_context_bundle_projection,
    "manifest": get_artefact_manifest_projection,
    "patch": get_candidate_patch_projection,
    "reference": get_artefact_reference_projection,
    "version": get_candidate_version_projection,
    "execution": get_execution_evidence_projection,
}

_KNOWN_IDS = {
    "context": ("context-bundle-1", _RAG_BOUND),
    "manifest": ("manifest-1", _EVIDENCE_BOUND),
    "patch": ("candidate-patch-1", _EVIDENCE_BOUND),
    "reference": ("art.known", _EVIDENCE_BOUND),
    "version": ("candidate-version-1", _EVIDENCE_BOUND),
    "execution": ("execution-evidence-1", _EVIDENCE_BOUND),
}


@pytest.mark.parametrize(["family"], [(name,) for name in sorted(_FAMILIES)])
@pytest.mark.parametrize(
    ["case", "bad_value"],
    [
        ("none", None),
        ("wrong-type-int", 7),
        ("wrong-type-bytes", b"identity"),
        ("empty-string", ""),
        ("over-bound", "OVERBOUND"),
    ],
)
def test_malformed_identity_fails_closed_without_querying(
    session: Session, family: str, case: str, bad_value: object
) -> None:
    operation = _FAMILIES[family]
    value = bad_value
    if case == "over-bound":
        value = "x" * (_KNOWN_IDS[family][1] + 1)

    with pytest.raises(DB004QueryInvalidIdentityError):
        operation(session, value)


@pytest.mark.parametrize(["family"], [(name,) for name in sorted(_FAMILIES)])
def test_unknown_valid_shaped_identity_is_explicit_not_found(
    session: Session, family: str
) -> None:
    operation = _FAMILIES[family]
    missing = f"missing-{uuid.uuid4().hex[:8]}"

    with pytest.raises(DB004QueryNotFoundError):
        operation(session, missing)

    # Seed the durable row for this family: the unknown identity above was
    # genuinely absent, never silently normalized onto the stored row.
    if family == "context":
        persist_context_bundle_metadata(session, make_context_bundle())
    elif family in {"patch", "version"}:
        _candidate(session)
    elif family == "execution":
        _execution(session)
    elif family == "reference":
        _execution(session)
        persist_artefact_reference_metadata(
            session,
            make_artefact_reference(
                artefact_id=ArtefactId("art.known"),
                artefact_type="CUSTOM_OUTPUT",
                storage_locator="object-store://bucket/known",
            ),
        )
    elif family == "manifest":
        member = make_artefact_reference(
            artefact_id=ArtefactId("art.known.member"),
            artefact_type="CUSTOM_OUTPUT",
            storage_locator="object-store://bucket/known-member",
        )
        persist_artefact_reference_metadata(session, member)
        persist_artefact_manifest_metadata(
            session, make_artefact_manifest(members=(member,))
        )

    found_id, _ = _KNOWN_IDS[family]
    assert operation(session, found_id) is not None


def test_identity_matching_never_normalizes_existing_values(
    session: Session,
) -> None:
    persist_context_bundle_metadata(session, make_context_bundle())
    _candidate(session)

    # Case differences and surrounding whitespace are distinct identities:
    # none may resolve onto the stored row by silent normalization.
    with pytest.raises(DB004QueryNotFoundError):
        get_context_bundle_projection(session, "CONTEXT-BUNDLE-1")
    with pytest.raises(DB004QueryNotFoundError):
        get_candidate_patch_projection(session, "candidate-patch-1 ")
    with pytest.raises(DB004QueryNotFoundError):
        get_candidate_version_projection(session, " candidate-version-1")


def test_over_bound_identity_is_malformed_not_truncated_onto_a_real_row(
    session: Session,
) -> None:
    persist_context_bundle_metadata(session, make_context_bundle())
    padded = "context-bundle-1" + "x" * _RAG_BOUND
    assert len(padded) > _RAG_BOUND
    with pytest.raises(DB004QueryInvalidIdentityError):
        get_context_bundle_projection(session, padded)


# ---------------------------------------------------------------------------
# READ-ONLY GUARANTEE
# ---------------------------------------------------------------------------


def test_control_plain_select_flushes_pending_caller_state(
    session: Session,
) -> None:
    """Sensitivity check: a bare SELECT must expose any accidental autoflush."""
    persist_context_bundle_metadata(session, make_context_bundle())
    pending = _pending_item("control-pending", 2, "d")
    session.add(pending)
    assert inspect(pending).pending

    session.execute(sa.select(sa.func.count()).select_from(ContextBundleItem))

    assert len(session.new) == 0
    assert inspect(pending).persistent


def test_reads_do_not_flush_pending_caller_state(session: Session) -> None:
    persist_context_bundle_metadata(session, make_context_bundle())
    pending = _pending_item("pending-not-flushed", 2, "e")
    session.add(pending)
    assert inspect(pending).pending

    projection = get_context_bundle_projection(session, "context-bundle-1")

    assert inspect(pending).pending
    assert inspect(pending).persistent is False
    assert "pending-not-flushed" in {o.context_item_id for o in session.new}
    # The unflushed row stays invisible to the read's physical SELECT.
    assert [i.context_item_id for i in projection.items] == ["context-item-1"]

    # Every other read family behaves identically under fresh pending state.
    _candidate(session)
    more_pending = _pending_item("pending-still-unflushed", 3, "f")
    session.add(more_pending)
    get_candidate_patch_projection(session, "candidate-patch-1")
    get_candidate_version_projection(session, "candidate-version-1")
    assert inspect(more_pending).pending
    assert "pending-still-unflushed" in {o.context_item_id for o in session.new}


def test_reads_commit_or_rollback_nothing_and_caller_keeps_the_transaction(
    migrated_engine: Engine,
) -> None:
    # Engine-level events observe real DBAPI COMMIT/ROLLBACK only; SQLAlchemy
    # session-level after_commit also fires on savepoint releases, which the
    # DB-004 persistence layer legitimately uses internally.
    dbapi_outcomes: list[str] = []
    event.listen(migrated_engine, "commit", lambda c: dbapi_outcomes.append("commit"))
    event.listen(
        migrated_engine, "rollback", lambda c: dbapi_outcomes.append("rollback")
    )
    with Session(migrated_engine) as caller:
        caller.begin()

        # Unique identities: this test is the only one that commits, so its
        # rows must never collide with other tests' fixed identities.
        suffix = uuid.uuid4().hex[:8]
        workflow = _workflow(caller)
        run_id = str(workflow.run.id)
        attempt_id = str(workflow.attempt.id)
        patch_id = f"patch-owner-{suffix}"
        version_id = f"version-owner-{suffix}"
        evidence_id = f"exec-owner-{suffix}"
        bundle_id = f"bundle-owner-{suffix}"
        item_id = f"item-owner-{suffix}"
        persist_candidate_metadata(
            caller,
            patch=make_candidate_patch(
                run_id,
                attempt_id,
                candidate_patch_id=CandidatePatchId(patch_id),
                candidate_version_id=CandidateVersionId(version_id),
                changed_files_manifest=(
                    ChangedFile(path=f"owner/{suffix}.java", change_summary="owner"),
                ),
            ),
            version=make_candidate_version(
                run_id,
                attempt_id,
                candidate_version_id=version_id,
                candidate_patch_id=patch_id,
            ),
        )
        persist_execution_evidence_metadata(
            caller,
            make_execution_evidence(
                workflow_attempt_id=attempt_id,
                execution_evidence_id=ExecutionEvidenceId(evidence_id),
                producer_result_id=ProducerResultId(f"producer-owner-{suffix}"),
                candidate_version_id=CandidateVersionId(version_id),
            ),
        )
        persist_context_bundle_metadata(
            caller,
            make_context_bundle(
                context_bundle_id=bundle_id,
                items=(make_context_item(context_item_id=item_id),),
            ),
        )
        pending = _pending_item(item_id + "-pending", 2, "0", bundle_id)
        caller.add(pending)

        assert dbapi_outcomes == []
        assert caller.in_transaction()
        get_candidate_patch_projection(caller, patch_id)
        get_candidate_version_projection(caller, version_id)
        get_execution_evidence_projection(caller, evidence_id)
        get_context_bundle_projection(caller, bundle_id)

        # No transaction control was exercised by any read...
        assert dbapi_outcomes == []
        assert caller.in_transaction()
        # ...the pending caller state survived unflushed...
        assert inspect(pending).pending
        # ...and the caller still owns the outcome of its own transaction.
        caller.commit()

    assert dbapi_outcomes == ["commit"]
    with Session(migrated_engine) as outsider:
        assert (
            outsider.scalar(
                sa.select(sa.func.count())
                .select_from(ContextBundleItem)
                .where(ContextBundleItem.context_item_id == item_id + "-pending")
            )
            == 1
        )


def test_reads_leave_database_row_counts_and_projections_unchanged(
    session: Session,
) -> None:
    persist_context_bundle_metadata(session, make_context_bundle())
    _execution(
        session,
        queue_message_id=QueueMessageId("qm-1"),
        queue_delivery_id=QueueDeliveryId("qd-1"),
        correlation_id=CorrelationId("co-1"),
    )
    reference = make_artefact_reference(
        artefact_id=ArtefactId("art.immutable"),
        artefact_type="CUSTOM_OUTPUT",
        storage_locator="object-store://bucket/immutable",
    )
    persist_artefact_reference_metadata(session, reference)
    persist_artefact_manifest_metadata(
        session, make_artefact_manifest(members=(reference,))
    )

    def read_everything():
        return (
            get_context_bundle_projection(session, "context-bundle-1"),
            get_candidate_patch_projection(session, "candidate-patch-1"),
            get_candidate_version_projection(session, "candidate-version-1"),
            get_execution_evidence_projection(session, "execution-evidence-1"),
            get_artefact_reference_projection(session, "art.immutable"),
            get_artefact_manifest_projection(session, "manifest-1"),
        )

    before = _table_counts(session)
    first = read_everything()
    middle = _table_counts(session)
    second = read_everything()
    after = _table_counts(session)

    assert before == middle == after
    assert first == second


# ---------------------------------------------------------------------------
# DETERMINISM across every family
# ---------------------------------------------------------------------------


def test_repeated_reads_are_value_equal_with_identical_child_ordering(
    session: Session,
) -> None:
    persist_context_bundle_metadata(
        session,
        make_context_bundle(
            context_bundle_id="det-bundle",
            items=(
                make_context_item(context_item_id="det-item-1", token_count=4),
                make_context_item(context_item_id="det-item-2", token_count=6),
            ),
        ),
    )
    _execution(
        session,
        resource_observations=(
            _memory_observation(),
            ResourceObservation(
                category=ResourceCategory.CPU_TIME,
                enforcement_status=ResourceEnforcementStatus.NOT_ENFORCED,
                terminated_execution=False,
                configuration_reference=OpaqueReference("config://cpu"),
            ),
        ),
        output_artefacts=(
            make_artefact_reference(
                artefact_id=ArtefactId("art.det.report"),
                artefact_type="CUSTOM_OUTPUT",
                storage_locator="object-store://bucket/det-report",
            ),
        ),
    )
    reference = make_artefact_reference(
        artefact_id=ArtefactId("art.det.member"),
        artefact_type="CUSTOM_OUTPUT",
        storage_locator="object-store://bucket/det-member",
    )
    persist_artefact_reference_metadata(session, reference)
    persist_artefact_manifest_metadata(
        session, make_artefact_manifest(members=(reference,))
    )

    readers = (
        lambda: get_context_bundle_projection(session, "det-bundle"),
        lambda: get_candidate_patch_projection(session, "candidate-patch-1"),
        lambda: get_candidate_version_projection(session, "candidate-version-1"),
        lambda: get_execution_evidence_projection(session, "execution-evidence-1"),
        lambda: get_artefact_reference_projection(session, "art.det.member"),
        lambda: get_artefact_manifest_projection(session, "manifest-1"),
    )
    first = [read() for read in readers]
    second = [read() for read in readers]

    for once, twice in zip(first, second):
        assert once == twice

    bundle_once, bundle_twice = first[0], second[0]
    assert [i.position for i in bundle_once.items] == [1, 2]
    assert [i.position for i in bundle_twice.items] == [1, 2]

    evidence_once, evidence_twice = first[3], second[3]
    assert [o.ordinal for o in evidence_once.resource_observations] == [1, 2]
    assert [o.ordinal for o in evidence_twice.resource_observations] == [1, 2]
    assert [r.artefact_id for r in evidence_once.artefact_roles] == [
        r.artefact_id for r in evidence_twice.artefact_roles
    ]

    manifest_once, manifest_twice = first[5], second[5]
    assert [m.artefact_id for m in manifest_once.members] == [
        m.artefact_id for m in manifest_twice.members
    ]


# ---------------------------------------------------------------------------
# NO RAW PAYLOAD EXPOSURE across the new projection surface
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "projection_type",
    [
        DB004PersistedContextBundle,
        DB004PersistedCandidatePatch,
        DB004PersistedCandidateVersion,
        DB004PersistedExecutionEvidence,
        DB004PersistedArtefactReference,
        DB004PersistedArtefactManifest,
    ],
)
def test_projection_types_carry_only_bounded_metadata_fields(
    projection_type: type,
) -> None:
    forbidden_exact = {
        "content",
        "text",
        "payload",
        "source_bytes",
        "blob",
        "stdout",
        "stderr",
        "log",
        "patch_body",
        "secret",
        "token",
        "credential",
    }
    names = {f.name for f in dataclass_fields(projection_type)}
    assert not names & forbidden_exact
