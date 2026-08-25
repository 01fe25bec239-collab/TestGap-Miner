"""DB-004 persistence behavior: INSERT / CONVERGE / CONFLICT aggregates."""

import threading
import time
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.db.db004_persistence import (
    DB004PersistenceConflictError,
    DB004UnresolvableReferenceError,
    persist_artefact_manifest_metadata,
    persist_artefact_reference_metadata,
    persist_candidate_metadata,
    persist_context_bundle_metadata,
    persist_execution_evidence_metadata,
)
from app.db.models.context import ContextBundle, ContextBundleItem
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
from app.evidence.artefact import (
    ARTEFACT_MANIFEST_SCHEMA_VERSION,
    ArtefactId,
    ArtefactManifestFinalizationState,
    ArtefactType,
)
from app.evidence.candidate import CandidatePatchId, ChangedFile
from app.evidence.execution import (
    EVIDENCE_CONTRACT_VERSION,
    CandidateVersionId,
    CorrelationId,
    ExecutionEvidenceId,
    ExecutionOutcome,
    ExecutionPhase,
    ExecutionTiming,
    FailureCategory,
    FailureEvidence,
    OpaqueReference,
    ProducerResultId,
    ProcessExit,
    QueueDeliveryId,
    QueueMessageId,
    ResourceCategory,
    ResourceEnforcementStatus,
    ResourceObservation,
    ResourceValue,
    RunId,
    TestResult,
    TestCaseResult,
    TestCaseStatus,
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
    make_fixed_execution_evidence,
    make_integrity,
)
from support import make_attempt, make_run, make_run_request, make_step


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
    patch = make_candidate_patch(run_id, str(workflow.attempt.id))
    version = make_candidate_version(
        run_id, str(workflow.attempt.id), **version_overrides
    )
    patch_row, version_row = persist_candidate_metadata(
        session, patch=patch, version=version
    )
    return SimpleNamespace(
        workflow=workflow,
        patch_row=patch_row,
        version_row=version_row,
    )


def _execution(session: Session, **overrides):
    aggregate = _candidate(session)
    evidence = make_execution_evidence(
        workflow_attempt_id=str(aggregate.workflow.attempt.id), **overrides
    )
    stored = persist_execution_evidence_metadata(session, evidence)
    return aggregate, evidence, stored


def _count(session: Session, model: type) -> int:
    return session.scalar(sa.select(sa.func.count()).select_from(model))


def _bundle_count(session: Session, bundle_id: str) -> int:
    return session.scalar(
        sa.select(sa.func.count())
        .select_from(ContextBundle)
        .where(ContextBundle.context_bundle_id == bundle_id)
    )


# ---------------------------------------------------------------------------
# RAG context metadata
# ---------------------------------------------------------------------------


def test_context_bundle_persists_with_ordered_items(session: Session) -> None:
    bundle = make_context_bundle(
        items=(
            make_context_item(
                context_item_id="item-a",
                file_identity="src/A.java",
                start_line=2,
                end_line=5,
                token_count=4,
            ),
            make_context_item(
                context_item_id="item-b", file_identity="src/B.java", token_count=6
            ),
        ),
        max_tokens=64,
    )
    stored = persist_context_bundle_metadata(session, bundle)

    assert stored.context_bundle_id == "context-bundle-1"
    assert (stored.repository_id, stored.revision_id) == (
        "benchmark-repo",
        REVISION_40,
    )
    assert (stored.max_tokens, stored.consumed_tokens) == (64, 10)
    assert [(i.position, i.context_item_id) for i in stored.items] == [
        (1, "item-a"),
        (2, "item-b"),
    ]
    assert [i.file_identity for i in stored.items] == ["src/A.java", "src/B.java"]
    assert [i.start_line for i in stored.items] == [2, 1]
    assert [i.end_line for i in stored.items] == [5, 3]
    assert all(i.trust_label == "UNTRUSTED_REPOSITORY_TEXT" for i in stored.items)


def test_context_metadata_keeps_no_raw_content(session: Session) -> None:
    item_columns = {c.name for c in ContextBundleItem.__table__.columns}
    bundle_columns = {c.name for c in ContextBundle.__table__.columns}
    forbidden = {"content", "text", "source_bytes", "blob", "payload"}
    assert not (item_columns | bundle_columns) & forbidden

    stored = persist_context_bundle_metadata(session, make_context_bundle())
    item = stored.items[0]
    assert item.token_count == 12
    assert len(item.content_sha256) == 64


def test_equivalent_duplicate_bundle_converges(session: Session) -> None:
    first = persist_context_bundle_metadata(session, make_context_bundle())
    again = persist_context_bundle_metadata(session, make_context_bundle())
    assert again.context_bundle_id == first.context_bundle_id
    assert _count(session, ContextBundle) == 1
    assert _count(session, ContextBundleItem) == 1


def test_conflicting_bundle_metadata_fails_closed(session: Session) -> None:
    persist_context_bundle_metadata(session, make_context_bundle())
    with pytest.raises(DB004PersistenceConflictError):
        persist_context_bundle_metadata(session, make_context_bundle(max_tokens=999))


def test_item_rebound_to_another_bundle_conflicts(session: Session) -> None:
    persist_context_bundle_metadata(session, make_context_bundle())
    moved = make_context_bundle(context_bundle_id="context-bundle-2")
    with pytest.raises(DB004PersistenceConflictError):
        persist_context_bundle_metadata(session, moved)


def test_reordered_items_under_same_bundle_conflict(session: Session) -> None:
    ordered = make_context_bundle(
        items=(
            make_context_item(context_item_id="item-a", token_count=4),
            make_context_item(context_item_id="item-b", token_count=6),
        ),
        max_tokens=64,
    )
    persist_context_bundle_metadata(session, ordered)
    reversed_bundle = make_context_bundle(
        items=(
            make_context_item(context_item_id="item-b", token_count=6),
            make_context_item(context_item_id="item-a", token_count=4),
        ),
        max_tokens=64,
    )
    with pytest.raises(DB004PersistenceConflictError):
        persist_context_bundle_metadata(session, reversed_bundle)


def test_duplicate_position_is_physically_rejected(session: Session) -> None:
    stored = persist_context_bundle_metadata(session, make_context_bundle())
    session.add(
        ContextBundleItem(
            context_item_id="item-shadow",
            context_bundle_id=stored.context_bundle_id,
            position=1,
            candidate_id="candidate-9",
            file_identity="src/C.java",
            start_line=1,
            end_line=1,
            content_sha256="0" * 64,
            trust_label="UNTRUSTED_REPOSITORY_TEXT",
            token_count=1,
        )
    )
    with pytest.raises(DBAPIError):
        session.flush()


# ---------------------------------------------------------------------------
# Candidate metadata
# ---------------------------------------------------------------------------


def test_initial_candidate_persists_distinct_patch_and_version_identities(
    session: Session,
) -> None:
    aggregate = _candidate(session)

    assert isinstance(aggregate.patch_row, CandidatePatchRecord)
    assert isinstance(aggregate.version_row, CandidateVersionRecord)
    assert aggregate.patch_row.candidate_patch_id == "candidate-patch-1"
    assert aggregate.patch_row.candidate_version_id == "candidate-version-1"
    assert aggregate.version_row.candidate_version_id == "candidate-version-1"
    assert aggregate.version_row.candidate_patch_id == "candidate-patch-1"
    assert aggregate.patch_row.candidate_patch_id != "candidate-version-1"
    assert aggregate.version_row.repair_level == 0
    assert aggregate.version_row.parent_candidate_version_id is None
    assert aggregate.version_row.producer_result_id is None
    assert aggregate.version_row.run_id == aggregate.workflow.run.id
    assert aggregate.version_row.workflow_attempt_id == aggregate.workflow.attempt.id
    assert aggregate.patch_row.test_only_scope is True
    assert aggregate.patch_row.source_revision == REVISION_40
    assert aggregate.patch_row.finalization_state == "CREATED"
    assert aggregate.patch_row.finalized_at is None


def test_changed_files_persist_normalized_per_path(session: Session) -> None:
    _candidate(session)
    files = session.scalars(
        sa.select(CandidateChangedFile)
        .where(CandidateChangedFile.candidate_patch_id == "candidate-patch-1")
        .order_by(CandidateChangedFile.path)
    ).all()
    assert [f.path for f in files] == ["src/test/java/ExampleTest.java"]
    assert files[0].change_summary.startswith("added failing")


def test_repaired_candidate_links_initial_lineage(session: Session) -> None:
    initial = _candidate(session)
    workflow = initial.workflow
    run_id = str(workflow.run.id)
    attempt_id = str(workflow.attempt.id)

    patch_row, version_row = persist_candidate_metadata(
        session,
        patch=make_candidate_patch(
            run_id,
            attempt_id,
            candidate_patch_id=CandidatePatchId("candidate-patch-2"),
            candidate_version_id=CandidateVersionId("candidate-version-2"),
        ),
        version=make_candidate_version(
            run_id,
            attempt_id,
            repair_level=1,
            parent_candidate_version_id="candidate-version-1",
            candidate_version_id="candidate-version-2",
            candidate_patch_id="candidate-patch-2",
        ),
    )

    assert version_row.repair_level == 1
    assert version_row.parent_candidate_version_id == "candidate-version-1"
    assert patch_row.candidate_patch_id == "candidate-patch-2"
    assert patch_row.candidate_patch_id != initial.patch_row.candidate_patch_id
    assert version_row.run_id == initial.version_row.run_id


def test_parent_must_exist_and_be_an_initial_candidate(session: Session) -> None:
    base = _candidate(session)
    workflow = base.workflow
    run_id = str(workflow.run.id)
    attempt_id = str(workflow.attempt.id)

    # Parent does not exist.
    with pytest.raises(DB004UnresolvableReferenceError):
        persist_candidate_metadata(
            session,
            patch=make_candidate_patch(
                run_id,
                attempt_id,
                candidate_patch_id=CandidatePatchId("candidate-patch-4"),
                candidate_version_id=CandidateVersionId("candidate-version-4"),
            ),
            version=make_candidate_version(
                run_id,
                attempt_id,
                repair_level=1,
                parent_candidate_version_id="candidate-version-missing",
                candidate_version_id="candidate-version-4",
                candidate_patch_id="candidate-patch-4",
            ),
        )

    # Persist the repaired child, then prove a third candidate cannot parent
    # the repaired one: parents must be initial candidates only.
    _, repaired_row = persist_candidate_metadata(
        session,
        patch=make_candidate_patch(
            run_id,
            attempt_id,
            candidate_patch_id=CandidatePatchId("candidate-patch-2"),
            candidate_version_id=CandidateVersionId("candidate-version-2"),
        ),
        version=make_candidate_version(
            run_id,
            attempt_id,
            repair_level=1,
            parent_candidate_version_id="candidate-version-1",
            candidate_version_id="candidate-version-2",
            candidate_patch_id="candidate-patch-2",
        ),
    )
    assert repaired_row.repair_level == 1
    with pytest.raises(ValueError):
        persist_candidate_metadata(
            session,
            patch=make_candidate_patch(
                run_id,
                attempt_id,
                candidate_patch_id=CandidatePatchId("candidate-patch-5"),
                candidate_version_id=CandidateVersionId("candidate-version-5"),
            ),
            version=make_candidate_version(
                run_id,
                attempt_id,
                repair_level=1,
                parent_candidate_version_id=repaired_row.candidate_version_id,
                candidate_version_id="candidate-version-5",
                candidate_patch_id="candidate-patch-5",
            ),
        )


def test_producer_result_id_is_optional_but_preserved(session: Session) -> None:
    without = _candidate(session)
    assert without.version_row.producer_result_id is None

    workflow = without.workflow
    run_id = str(workflow.run.id)
    attempt_id = str(workflow.attempt.id)
    _, version_row = persist_candidate_metadata(
        session,
        patch=make_candidate_patch(
            run_id,
            attempt_id,
            candidate_patch_id=CandidatePatchId("candidate-patch-3"),
            candidate_version_id=CandidateVersionId("candidate-version-3"),
        ),
        version=make_candidate_version(
            run_id,
            attempt_id,
            producer_result_id="producer-result-77",
            candidate_version_id="candidate-version-3",
            candidate_patch_id="candidate-patch-3",
        ),
    )
    assert version_row.producer_result_id == "producer-result-77"


def test_equivalent_duplicate_candidate_converges(session: Session) -> None:
    aggregate = _candidate(session)
    run_id = str(aggregate.workflow.run.id)
    attempt_id = str(aggregate.workflow.attempt.id)
    patches_before = _count(session, CandidatePatchRecord)
    versions_before = _count(session, CandidateVersionRecord)
    _, converged_row = persist_candidate_metadata(
        session,
        patch=make_candidate_patch(run_id, attempt_id),
        version=make_candidate_version(run_id, attempt_id),
    )
    assert converged_row.candidate_version_id == "candidate-version-1"
    assert _count(session, CandidatePatchRecord) == patches_before
    assert _count(session, CandidateVersionRecord) == versions_before


def test_conflicting_candidate_metadata_fails_closed(session: Session) -> None:
    workflow = _workflow(session)
    run_id = str(workflow.run.id)
    attempt_id = str(workflow.attempt.id)
    persist_candidate_metadata(
        session,
        patch=make_candidate_patch(run_id, attempt_id),
        version=make_candidate_version(run_id, attempt_id),
    )
    with pytest.raises(DB004PersistenceConflictError):
        persist_candidate_metadata(
            session,
            patch=make_candidate_patch(
                run_id,
                attempt_id,
                patch_digest=OpaqueReference("sha256:" + "00" * 32),
            ),
            version=make_candidate_version(run_id, attempt_id),
        )


def test_contradictory_patch_version_binding_fails_closed(
    session: Session,
) -> None:
    workflow = _workflow(session)
    run_id = str(workflow.run.id)
    attempt_id = str(workflow.attempt.id)
    with pytest.raises(ValueError):
        persist_candidate_metadata(
            session,
            patch=make_candidate_patch(run_id, attempt_id),
            version=make_candidate_version(
                run_id,
                attempt_id,
                source_revision=OpaqueReference("cd" * 20),
            ),
        )


@pytest.mark.parametrize("bad_run_id", ["not-even-a-uuid", str(uuid.uuid4())])
def test_unmappable_or_unknown_run_reference_fails_closed(
    session: Session, bad_run_id: str
) -> None:
    workflow = _workflow(session)
    attempt_id = str(workflow.attempt.id)
    with pytest.raises(DB004UnresolvableReferenceError):
        persist_candidate_metadata(
            session,
            patch=make_candidate_patch(bad_run_id, attempt_id),
            version=make_candidate_version(bad_run_id, attempt_id),
        )


def test_attempt_from_another_run_fails_closed(session: Session) -> None:
    first = _workflow(session)
    foreign = _workflow(session)

    run_id = str(first.run.id)
    with pytest.raises(ValueError):
        persist_candidate_metadata(
            session,
            patch=make_candidate_patch(run_id, str(foreign.attempt.id)),
            version=make_candidate_version(run_id, str(foreign.attempt.id)),
        )


def test_changed_file_paths_are_unique_per_candidate(session: Session) -> None:
    _candidate(session)
    session.add(
        CandidateChangedFile(
            candidate_patch_id="candidate-patch-1",
            path="src/test/java/ExampleTest.java",
            change_summary="a contradictory duplicate path",
        )
    )
    with pytest.raises(DBAPIError):
        session.flush()


# ---------------------------------------------------------------------------
# Execution evidence
# ---------------------------------------------------------------------------


def _compile_execution(session: Session, **overrides):
    aggregate = _candidate(session)
    evidence = make_compile_evidence(
        workflow_attempt_id=str(aggregate.workflow.attempt.id), **overrides
    )
    stored = persist_execution_evidence_metadata(session, evidence)
    return aggregate, evidence, stored


def test_compile_evidence_persists_phase_fields(session: Session) -> None:
    _, _, stored = _compile_execution(
        session, execution_evidence_id=ExecutionEvidenceId("exec-compile")
    )
    assert stored.execution_evidence_id == "exec-compile"
    assert stored.execution_phase == "COMPILE"
    assert stored.outcome == "SUCCESS"
    assert stored.compile_status == "SUCCESS"
    assert stored.test_executed_count is None
    assert stored.source_revision is None
    assert stored.producer_result_id == "producer-result-1"


def test_buggy_test_evidence_persists_counts_cases_and_timing(
    session: Session,
) -> None:
    aggregate, evidence, stored = _execution(session)
    assert stored.candidate_version_id == "candidate-version-1"
    assert stored.execution_phase == "BUGGY_OR_TARGET_REVISION_TEST"
    assert stored.outcome == "SUCCESS"
    assert stored.completeness == "PARTIAL"
    assert stored.source_revision == REVISION_40
    assert stored.test_executed_count == 2
    assert stored.test_passed_count == 2
    assert stored.duration_microseconds == 30_000_000
    assert stored.started_at is not None and stored.ended_at is not None

    cases = session.scalars(
        sa.select(ExecutionTestCaseResult)
        .where(ExecutionTestCaseResult.execution_evidence_id == "execution-evidence-1")
        .order_by(ExecutionTestCaseResult.ordinal)
    ).all()
    assert [c.ordinal for c in cases] == [1, 2]
    assert all(c.case_status == "PASSED" for c in cases)
    assert [c.test_reference for c in cases] == [
        "test://ExampleTest.testAnswer",
        "test://ExampleTest.testOther",
    ]


def test_fixed_execution_evidence_is_distinct_identity(
    session: Session,
) -> None:
    aggregate, evidence, stored = _execution(session)
    fixed = make_fixed_execution_evidence(
        workflow_attempt_id=str(aggregate.workflow.attempt.id)
    )
    stored_fixed = persist_execution_evidence_metadata(session, fixed)
    assert stored.execution_evidence_id == "execution-evidence-1"
    assert stored_fixed.execution_evidence_id == "execution-evidence-fixed"
    assert stored_fixed.execution_phase == "FIXED_OR_REFERENCE_REVISION_TEST"
    assert _count(session, ExecutionEvidenceRecord) == 2


def test_timeout_evidence_persists_timeout_facts(session: Session) -> None:
    _, _, stored = _execution(
        session,
        outcome=ExecutionOutcome.TIMEOUT,
        failure=FailureEvidence(FailureCategory.TIMEOUT),
        timeout_metadata=TimeoutMetadata(
            timed_out=True,
            classification=OpaqueReference("timeout://wall-clock-600s"),
            configured_limit=timedelta(seconds=600),
        ),
    )
    assert stored.outcome == "TIMEOUT"
    assert stored.failure_category == "TIMEOUT"
    assert stored.timeout_timed_out is True
    assert stored.timeout_classification == "timeout://wall-clock-600s"
    assert stored.timeout_limit_microseconds == 600_000_000


def test_failed_test_evidence_persists_process_exit(session: Session) -> None:
    _, _, stored = _execution(
        session,
        outcome=ExecutionOutcome.TEST_FAILURE,
        failure=FailureEvidence(FailureCategory.TEST_FAILURE),
        process_exit=ProcessExit(exit_code=1),
        test_result=TestResult(
            executed_count=2,
            passed_count=1,
            failed_count=1,
            test_cases=(
                TestCaseResult(
                    test_reference=OpaqueReference("test://ExampleTest.testAnswer"),
                    status=TestCaseStatus.PASSED,
                ),
                TestCaseResult(
                    test_reference=OpaqueReference("test://ExampleTest.testBug"),
                    status=TestCaseStatus.FAILED,
                    failure_reference=OpaqueReference("failure://assertion-1"),
                ),
            ),
        ),
    )
    assert stored.outcome == "TEST_FAILURE"
    assert stored.exit_code == 1
    assert stored.failure_category == "TEST_FAILURE"
    failing = session.scalars(
        sa.select(ExecutionTestCaseResult).where(
            ExecutionTestCaseResult.execution_evidence_id == "execution-evidence-1",
            ExecutionTestCaseResult.case_status.in_(["FAILED", "ERRORED"]),
        )
    ).one()
    assert failing.failure_reference == "failure://assertion-1"


def test_execution_requires_existing_candidate_version(session: Session) -> None:
    aggregate = _candidate(session)
    evidence = make_execution_evidence(
        workflow_attempt_id=str(aggregate.workflow.attempt.id),
        candidate_version_id=CandidateVersionId("candidate-version-missing"),
    )
    with pytest.raises(DB004UnresolvableReferenceError):
        persist_execution_evidence_metadata(session, evidence)


@pytest.mark.parametrize(
    "bad_attempt",
    ["attempt-placeholder", str(uuid.uuid4())],
)
def test_execution_requires_mappable_workflow_attempt(
    session: Session, bad_attempt: str
) -> None:
    aggregate = _candidate(session)
    evidence = make_execution_evidence(
        workflow_attempt_id=bad_attempt,
    )
    with pytest.raises(DB004UnresolvableReferenceError):
        persist_execution_evidence_metadata(session, evidence)


def test_execution_enforces_the_same_run_invariant(session: Session) -> None:
    aggregate = _candidate(session)
    foreign = _workflow(session)
    evidence = make_execution_evidence(
        workflow_attempt_id=str(foreign.attempt.id),
    )
    with pytest.raises(ValueError):
        persist_execution_evidence_metadata(session, evidence)


def test_execution_run_identity_may_be_supplied(session: Session) -> None:
    aggregate = _candidate(session)
    run_uuid = aggregate.workflow.run.id
    evidence = make_execution_evidence(
        workflow_attempt_id=str(aggregate.workflow.attempt.id),
        execution_evidence_id=ExecutionEvidenceId("exec-with-run"),
        producer_result_id=ProducerResultId("producer-with-run"),
        run_id=RunId(str(run_uuid)),
    )
    stored = persist_execution_evidence_metadata(session, evidence)
    assert stored.run_id == run_uuid


# ---------------------------------------------------------------------------
# Artefact references
# ---------------------------------------------------------------------------


def test_execution_artefacts_are_reference_only_with_roles(
    session: Session,
) -> None:
    stdout = make_artefact_reference(
        artefact_id=ArtefactId("art.exec.stdout"),
        artefact_type="TEST_STDOUT",
        storage_locator="object-store://bucket/exec-1/stdout",
    )
    stderr = make_artefact_reference(
        artefact_id=ArtefactId("art.exec.stderr"),
        artefact_type="TEST_STDERR",
        storage_locator="object-store://bucket/exec-1/stderr",
    )
    report = make_artefact_reference(
        artefact_id=ArtefactId("art.exec.report"),
        artefact_type="CUSTOM_OUTPUT",
        storage_locator="object-store://bucket/exec-1/report.xml",
    )
    _, _, stored = _execution(
        session,
        stdout_artefact=stdout,
        stderr_artefact=stderr,
        output_artefacts=(report,),
    )

    roles = {
        row.artefact_id: row.role
        for row in session.execute(
            sa.select(ExecutionArtefactRole).where(
                ExecutionArtefactRole.execution_evidence_id == stored.execution_evidence_id
            )
        ).scalars()
    }
    assert roles == {
        "art.exec.stdout": "STDOUT",
        "art.exec.stderr": "STDERR",
        "art.exec.report": "OUTPUT",
    }
    locator = session.scalar(
        sa.select(ArtefactReferenceRecord.storage_locator).where(
            ArtefactReferenceRecord.artefact_id == "art.exec.stdout"
        )
    )
    assert locator == "object-store://bucket/exec-1/stdout"

    # Reference-only: no byte payload column exists anywhere on artefacts.
    types = {c.name: str(c.type) for c in ArtefactReferenceRecord.__table__.columns}
    assert not any("BLOB" in t or "BYTEA" in t for t in types.values())


def test_second_captured_stream_role_is_physically_rejected(
    session: Session,
) -> None:
    stdout = make_artefact_reference(artefact_id=ArtefactId("art.exec.stdout"))
    other = make_artefact_reference(
        artefact_id=ArtefactId("art.exec.stdout2"),
        storage_locator="object-store://bucket/exec-1/stdout-2",
    )
    aggregate, evidence, stored = _execution(session, stdout_artefact=stdout)

    session.add(
        ExecutionArtefactRole(
            execution_evidence_id=stored.execution_evidence_id,
            artefact_id="art.exec.stdout2",
            role="STDOUT",
        )
    )
    with pytest.raises(DBAPIError):
        session.flush()


def test_availability_and_integrity_are_independent_axes(session: Session) -> None:
    available_corrupt = persist_artefact_reference_metadata(
        session,
        make_artefact_reference(
            artefact_id=ArtefactId("art.corrupt"),
            availability="AVAILABLE",
            integrity=make_integrity(state="CORRUPT"),
            storage_locator="object-store://bucket/corrupt",
        ),
    )
    unavailable_verified = persist_artefact_reference_metadata(
        session,
        make_artefact_reference(
            artefact_id=ArtefactId("art.unavailable"),
            availability="UNAVAILABLE",
            integrity=make_integrity(
                state="VERIFIED", verification_reference="verify-ref://1"
            ),
            storage_locator="object-store://bucket/unavailable",
        ),
    )
    assert (available_corrupt.availability_state, available_corrupt.integrity_state) == (
        "AVAILABLE",
        "CORRUPT",
    )
    assert (
        unavailable_verified.availability_state,
        unavailable_verified.integrity_state,
    ) == ("UNAVAILABLE", "VERIFIED")


def test_artefact_links_require_durable_rows(session: Session) -> None:
    with pytest.raises(DB004UnresolvableReferenceError):
        persist_artefact_reference_metadata(
            session,
            make_artefact_reference(candidate_version_id=CandidateVersionId("nope")),
        )
    with pytest.raises(DB004UnresolvableReferenceError):
        persist_artefact_reference_metadata(
            session,
            make_artefact_reference(execution_evidence_id=ExecutionEvidenceId("nope")),
        )


def test_artefact_digest_size_media_and_locator_roundtrip(
    session: Session,
) -> None:
    stored = persist_artefact_reference_metadata(
        session,
        make_artefact_reference(
            byte_size=4096,
            media_type="text/x-diff",
            content_digest=OpaqueReference("sha256:" + "ab" * 32),
            digest_algorithm=OpaqueReference("SHA-256"),
        ),
    )
    assert stored.byte_size == 4096
    assert stored.media_type == "text/x-diff"
    assert stored.content_digest == "sha256:" + "ab" * 32
    assert stored.digest_algorithm == "SHA-256"
    assert stored.storage_locator != stored.artefact_id

    # Identity and physical locator are distinct concepts, physically.
    session.add(
        ArtefactReferenceRecord(
            artefact_id="locator-eq",
            artefact_type="CUSTOM_OUTPUT",
            availability_state="AVAILABLE",
            integrity_state="UNVERIFIABLE",
            content_digest="d" * 10,
            digest_algorithm="SHA-256",
            byte_size=1,
            media_type="text/plain",
            producer_id="producer://x",
            creation_timestamp=datetime.now(UTC),
            storage_locator="locator-eq",
            contract_version=EVIDENCE_CONTRACT_VERSION,
        )
    )
    with pytest.raises(DBAPIError):
        session.flush()


# ---------------------------------------------------------------------------
# Artefact manifests
# ---------------------------------------------------------------------------


def _manifest_members(session: Session, count: int = 1):
    members = []
    for index in range(1, count + 1):
        reference = make_artefact_reference(
            artefact_id=ArtefactId(f"art.member.{index}"),
            storage_locator=f"object-store://bucket/member-{index}",
        )
        persist_artefact_reference_metadata(session, reference)
        members.append(reference)
    return tuple(members)


def test_assembling_manifest_persists_without_finalization_timestamp(
    session: Session,
) -> None:
    members = _manifest_members(session, 2)
    manifest = make_artefact_manifest(members=members)
    stored = persist_artefact_manifest_metadata(session, manifest)

    assert stored.artefact_manifest_id == "manifest-1"
    assert stored.finalization_state == "ASSEMBLING"
    assert stored.finalization_timestamp is None
    stored_members = set(
        session.scalars(
            sa.select(ArtefactManifestMember.artefact_id).where(
                ArtefactManifestMember.artefact_manifest_id == "manifest-1"
            )
        )
    )
    assert stored_members == {"art.member.1", "art.member.2"}


def test_finalized_manifest_requires_and_keeps_final_metadata(
    session: Session,
) -> None:
    members = _manifest_members(session, 1)
    manifest = make_artefact_manifest(
        members=members,
        finalization_state=ArtefactManifestFinalizationState.FINALIZED,
        **make_finalized_manifest_fields(),
    )
    stored = persist_artefact_manifest_metadata(session, manifest)
    assert stored.finalization_state == "FINALIZED"
    assert stored.finalization_timestamp is not None
    assert stored.manifest_digest is not None
    assert stored.integrity_state == "VERIFIED"


def test_finalized_without_final_metadata_is_physically_rejected(
    session: Session,
) -> None:
    session.add(
        ArtefactManifestRecord(
            artefact_manifest_id="manifest-bad",
            creation_timestamp=datetime.now(UTC),
            finalization_state="FINALIZED",
            contract_version=EVIDENCE_CONTRACT_VERSION,
            schema_version=ARTEFACT_MANIFEST_SCHEMA_VERSION,
        )
    )
    with pytest.raises(DBAPIError):
        session.flush()


def test_membership_is_unique_per_manifest_with_no_cardinality_limit(
    session: Session,
) -> None:
    members = _manifest_members(session, 5)
    manifest = make_artefact_manifest(members=members)
    persist_artefact_manifest_metadata(session, manifest)

    session.add(
        ArtefactManifestMember(
            artefact_manifest_id="manifest-1", artefact_id="art.member.3"
        )
    )
    with pytest.raises(DBAPIError):
        session.flush()


def test_equivalent_duplicate_manifest_converges(session: Session) -> None:
    members = _manifest_members(session, 2)
    first = persist_artefact_manifest_metadata(
        session, make_artefact_manifest(members=members)
    )
    again = persist_artefact_manifest_metadata(
        session, make_artefact_manifest(members=members)
    )
    assert again.artefact_manifest_id == first.artefact_manifest_id
    assert _count(session, ArtefactManifestRecord) == 1
    assert _count(session, ArtefactManifestMember) == 2


def test_membership_change_under_same_identity_conflicts(session: Session) -> None:
    members = _manifest_members(session, 1)
    extra = make_artefact_reference(
        artefact_id=ArtefactId("art.member.extra"),
        storage_locator="object-store://bucket/extra",
    )
    persist_artefact_reference_metadata(session, extra)
    persist_artefact_manifest_metadata(session, make_artefact_manifest(members=members))

    grown = make_artefact_manifest(members=(members[0], extra))
    with pytest.raises(DB004PersistenceConflictError):
        persist_artefact_manifest_metadata(session, grown)


def test_manifest_members_must_exist_first(session: Session) -> None:
    ghost = make_artefact_reference(
        artefact_id=ArtefactId("art.ghost"),
        storage_locator="object-store://bucket/ghost",
    )
    manifest = make_artefact_manifest(members=(ghost,))
    with pytest.raises(DB004UnresolvableReferenceError):
        persist_artefact_manifest_metadata(session, manifest)


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------


def test_persistence_never_commits_the_caller_transaction(
    migrated_engine: Engine,
) -> None:
    with Session(migrated_engine) as writer:
        stored = persist_context_bundle_metadata(
            writer,
            make_context_bundle(
                context_bundle_id="bundle-commit-check",
                items=(
                    make_context_item(
                        context_item_id="item-commit-check", token_count=12
                    ),
                ),
            ),
        )
        assert writer.in_transaction()
        assert stored.context_bundle_id == "bundle-commit-check"
        with Session(migrated_engine) as outsider:
            assert _bundle_count(outsider, "bundle-commit-check") == 0
        writer.commit()
        with Session(migrated_engine) as outsider:
            assert _bundle_count(outsider, "bundle-commit-check") == 1


def test_caller_rollback_removes_the_whole_aggregate(
    migrated_engine: Engine,
) -> None:
    with Session(migrated_engine) as session:
        workflow_rows = _workflow(session)
        run_id = str(workflow_rows.run.id)
        persist_candidate_metadata(
            session,
            patch=make_candidate_patch(run_id, str(workflow_rows.attempt.id)),
            version=make_candidate_version(run_id, str(workflow_rows.attempt.id)),
        )
        session.rollback()
        assert _count(session, CandidatePatchRecord) == 0
        assert _count(session, CandidateVersionRecord) == 0
        assert _count(session, CandidateChangedFile) == 0


def test_aggregate_atomicity_rolls_back_partial_writes(
    session: Session,
) -> None:
    aggregate = _candidate(session)
    poisoned = make_execution_evidence(
        workflow_attempt_id=str(aggregate.workflow.attempt.id),
        execution_evidence_id=ExecutionEvidenceId("exec-poisoned"),
        stdout_artefact=make_artefact_reference(
            candidate_version_id=CandidateVersionId("candidate-version-missing")
        ),
    )
    with pytest.raises(DB004UnresolvableReferenceError):
        persist_execution_evidence_metadata(session, poisoned)

    # The execution root was rolled back with the failed aggregate...
    assert (
        session.get(ExecutionEvidenceRecord, {"execution_evidence_id": "exec-poisoned"})
        is None
    )
    # ...and the caller transaction remains usable.
    atomicity_bundle = f"bundle-atomicity-{uuid.uuid4().hex[:8]}"
    stored = persist_context_bundle_metadata(
        session, make_context_bundle(context_bundle_id=atomicity_bundle)
    )
    assert stored.context_bundle_id == atomicity_bundle


# ---------------------------------------------------------------------------
# Concurrency (independent PostgreSQL sessions)
# ---------------------------------------------------------------------------


def test_concurrent_equivalent_inserts_converge(migrated_engine: Engine) -> None:
    race_id = f"bundle-race-dup-{uuid.uuid4().hex[:8]}"
    race_item = f"item-race-dup-{uuid.uuid4().hex[:8]}"
    race_bundle = make_context_bundle(
        context_bundle_id=race_id,
        items=(make_context_item(context_item_id=race_item),),
    )
    committed_ids: list[str] = []

    def contender() -> None:
        with Session(migrated_engine) as s:
            row = persist_context_bundle_metadata(s, make_context_bundle(
                context_bundle_id=race_id,
                items=(make_context_item(context_item_id=race_item),),
            ))
            committed_ids.append(row.context_bundle_id)
            s.commit()

    thread = threading.Thread(target=contender)
    thread.start()
    with Session(migrated_engine) as main_session:
        row = persist_context_bundle_metadata(main_session, race_bundle)
        main_id = row.context_bundle_id
        main_session.commit()
    thread.join(timeout=20)
    assert not thread.is_alive(), "contender never converged"

    assert committed_ids == [main_id]
    with Session(migrated_engine) as verify:
        assert _bundle_count(verify, race_id) == 1


def test_concurrent_conflicting_insert_fails_closed(migrated_engine: Engine) -> None:
    race_id = f"bundle-race-conflict-{uuid.uuid4().hex[:8]}"
    race_item = f"item-race-conflict-{uuid.uuid4().hex[:8]}"
    outcome: dict[str, str] = {}

    def contender() -> None:
        try:
            with Session(migrated_engine) as s:
                persist_context_bundle_metadata(
                    s,
                    make_context_bundle(
                        context_bundle_id=race_id,
                        max_tokens=999,
                        items=(make_context_item(context_item_id=race_item),),
                    ),
                )
                s.commit()
                outcome["kind"] = "converged"
        except DB004PersistenceConflictError:
            outcome["kind"] = "conflict"

    thread = threading.Thread(target=contender)
    with Session(migrated_engine) as main_session:
        # The uncommitted winner parks the contender on the identity index.
        persist_context_bundle_metadata(
            main_session,
            make_context_bundle(
                context_bundle_id=race_id,
                max_tokens=100,
                items=(make_context_item(context_item_id=race_item),),
            ),
        )
        thread.start()
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and not thread.is_alive():
            time.sleep(0.05)
        time.sleep(0.5)
        assert thread.is_alive(), "contender finished before the winner committed"
        main_session.commit()
    thread.join(timeout=20)
    assert not thread.is_alive()
    assert outcome["kind"] == "conflict"

    with Session(migrated_engine) as verify:
        stored_max = verify.scalar(
            sa.select(ContextBundle.max_tokens).where(
                ContextBundle.context_bundle_id == race_id
            )
        )
    assert stored_max == 100


def test_concurrent_equivalent_candidates_converge(migrated_engine: Engine) -> None:
    race_patch_id = f"candidate-patch-race-{uuid.uuid4().hex[:8]}"
    race_version_value = f"candidate-version-race-{uuid.uuid4().hex[:8]}"

    with Session(migrated_engine) as setup:
        workflow = _workflow(setup)
        run_id = str(workflow.run.id)
        attempt_id = str(workflow.attempt.id)
        setup.commit()
    committed: list[str] = []

    def contender() -> None:
        with Session(migrated_engine) as s:
            _, version_row = persist_candidate_metadata(
                s,
                patch=make_candidate_patch(
                    run_id,
                    attempt_id,
                    candidate_patch_id=CandidatePatchId(race_patch_id),
                    candidate_version_id=CandidateVersionId(race_version_value),
                ),
                version=make_candidate_version(
                    run_id,
                    attempt_id,
                    candidate_version_id=race_version_value,
                    candidate_patch_id=race_patch_id,
                ),
            )
            committed.append(version_row.candidate_version_id)
            s.commit()

    thread = threading.Thread(target=contender)
    thread.start()
    with Session(migrated_engine) as main_session:
        _, version_row = persist_candidate_metadata(
            main_session,
            patch=make_candidate_patch(
                run_id,
                attempt_id,
                candidate_patch_id=CandidatePatchId(race_patch_id),
                candidate_version_id=CandidateVersionId(race_version_value),
            ),
            version=make_candidate_version(
                run_id,
                attempt_id,
                candidate_version_id=race_version_value,
                candidate_patch_id=race_patch_id,
            ),
        )
        race_version_id = version_row.candidate_version_id
        main_session.commit()
    thread.join(timeout=20)
    assert not thread.is_alive()

    assert committed == [race_version_id]
    with Session(migrated_engine) as verify:
        assert (
            verify.scalar(
                sa.select(sa.func.count())
                .select_from(CandidateVersionRecord)
                .where(
                    CandidateVersionRecord.candidate_version_id
                    == race_version_value
                )
            )
            == 1
        )


# ---------------------------------------------------------------------------
# C1: execution provenance fields (queue/tracing/timing references)
# ---------------------------------------------------------------------------


def _provenance_evidence(aggregate: SimpleNamespace, **overrides):
    base = dict(
        workflow_attempt_id=str(aggregate.workflow.attempt.id),
        queue_message_id=QueueMessageId("queue-message-1"),
        queue_delivery_id=QueueDeliveryId("queue-delivery-1"),
        correlation_id=CorrelationId("correlation-1"),
        execution_timing=ExecutionTiming(
            started_at=GENERATED_AT,
            ended_at=GENERATED_AT + timedelta(seconds=30),
            duration=timedelta(seconds=30),
            upstream_fact_reference=OpaqueReference("fact://timing-1"),
        ),
    )
    base.update(overrides)
    return make_execution_evidence(**base)


def test_execution_provenance_fields_round_trip_and_converge(
    session: Session,
) -> None:
    aggregate = _candidate(session)
    stored = persist_execution_evidence_metadata(
        session, _provenance_evidence(aggregate)
    )
    assert stored.queue_message_id == "queue-message-1"
    assert stored.queue_delivery_id == "queue-delivery-1"
    assert stored.correlation_id == "correlation-1"
    assert stored.timing_fact_reference == "fact://timing-1"
    assert stored.producer_result_id == "producer-result-1"

    # The same identity with equivalent provenance converges.
    again = persist_execution_evidence_metadata(
        session, _provenance_evidence(aggregate)
    )
    assert again.execution_evidence_id == stored.execution_evidence_id
    assert _count(session, ExecutionEvidenceRecord) == 1


def test_execution_provenance_absent_then_supplied_conflicts(
    session: Session,
) -> None:
    aggregate = _candidate(session)
    persist_execution_evidence_metadata(
        session,
        make_execution_evidence(
            workflow_attempt_id=str(aggregate.workflow.attempt.id)
        ),
    )
    supplied = _provenance_evidence(aggregate, queue_delivery_id=None, correlation_id=None, execution_timing=ExecutionTiming(
        started_at=GENERATED_AT,
        ended_at=GENERATED_AT + timedelta(seconds=30),
        duration=timedelta(seconds=30),
    ))
    with pytest.raises(DB004PersistenceConflictError):
        persist_execution_evidence_metadata(session, supplied)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("queue_message_id", QueueMessageId("queue-message-other")),
        ("queue_delivery_id", QueueDeliveryId("queue-delivery-other")),
        ("correlation_id", CorrelationId("correlation-other")),
        (
            "execution_timing",
            ExecutionTiming(
                started_at=GENERATED_AT,
                ended_at=GENERATED_AT + timedelta(seconds=30),
                duration=timedelta(seconds=30),
                upstream_fact_reference=OpaqueReference("fact://timing-other"),
            ),
        ),
    ],
)
def test_execution_provenance_difference_conflicts(
    session: Session, field: str, value: object
) -> None:
    aggregate = _candidate(session)
    persist_execution_evidence_metadata(
        session, _provenance_evidence(aggregate)
    )
    differing = _provenance_evidence(aggregate, **{field: value})
    with pytest.raises(DB004PersistenceConflictError):
        persist_execution_evidence_metadata(session, differing)
    # The stored row keeps its original provenance.
    kept = session.get(
        ExecutionEvidenceRecord, {"execution_evidence_id": "execution-evidence-1"}
    )
    assert kept.queue_message_id == "queue-message-1"


# ---------------------------------------------------------------------------
# C2: immutable aggregate growth is rejected without partial writes
# ---------------------------------------------------------------------------


def test_candidate_changed_file_growth_conflicts_without_partial_write(
    session: Session,
) -> None:
    aggregate = _candidate(session)
    run_id = str(aggregate.workflow.run.id)
    attempt_id = str(aggregate.workflow.attempt.id)

    grown_patch = make_candidate_patch(
        run_id,
        attempt_id,
        changed_files_manifest=(
            ChangedFile(
                path="src/test/java/ExampleTest.java",
                change_summary="added failing assertions for bug 1",
            ),
            ChangedFile(
                path="src/main/java/Example.java",
                change_summary="growth that must not survive",
            ),
        ),
    )
    with pytest.raises(DB004PersistenceConflictError):
        persist_candidate_metadata(
            session,
            patch=grown_patch,
            version=make_candidate_version(run_id, attempt_id),
        )

    remaining = session.scalars(
        sa.select(CandidateChangedFile.path).where(
            CandidateChangedFile.candidate_patch_id == "candidate-patch-1"
        )
    ).all()
    assert remaining == ["src/test/java/ExampleTest.java"]


def test_candidate_changed_file_shrinkage_conflicts(session: Session) -> None:
    aggregate = _candidate(session)
    run_id = str(aggregate.workflow.run.id)
    attempt_id = str(aggregate.workflow.attempt.id)

    shrunk_patch = make_candidate_patch(
        run_id,
        attempt_id,
        changed_files_manifest=(
            ChangedFile(
                path="src/test/java/OtherTest.java",
                change_summary="replacement set missing the original path",
            ),
        ),
    )
    with pytest.raises(DB004PersistenceConflictError):
        persist_candidate_metadata(
            session,
            patch=shrunk_patch,
            version=make_candidate_version(run_id, attempt_id),
        )
    remaining = session.scalars(
        sa.select(CandidateChangedFile.path).where(
            CandidateChangedFile.candidate_patch_id == "candidate-patch-1"
        )
    ).all()
    assert remaining == ["src/test/java/ExampleTest.java"]


def _output_artefact(suffix: str):
    return make_artefact_reference(
        artefact_id=ArtefactId(f"art.report.{suffix}"),
        artefact_type="CUSTOM_OUTPUT",
        storage_locator=f"object-store://bucket/report-{suffix}",
    )


def test_execution_output_artefact_growth_conflicts_without_partial_write(
    session: Session,
) -> None:
    aggregate = _candidate(session)
    report_a = _output_artefact("a")
    persist_execution_evidence_metadata(
        session,
        make_execution_evidence(
            workflow_attempt_id=str(aggregate.workflow.attempt.id),
            output_artefacts=(report_a,),
        ),
    )

    report_b = _output_artefact("b")
    grown = make_execution_evidence(
        workflow_attempt_id=str(aggregate.workflow.attempt.id),
        output_artefacts=(report_a, report_b),
    )
    with pytest.raises(DB004PersistenceConflictError):
        persist_execution_evidence_metadata(session, grown)

    roles = {
        row.artefact_id: row.role
        for row in session.execute(
            sa.select(ExecutionArtefactRole).where(
                ExecutionArtefactRole.execution_evidence_id
                == "execution-evidence-1"
            )
        ).scalars()
    }
    assert roles == {"art.report.a": "OUTPUT"}
    assert (
        session.scalar(
            sa.select(sa.func.count())
            .select_from(ArtefactReferenceRecord)
            .where(ArtefactReferenceRecord.artefact_id == "art.report.b")
        )
        == 0
    )
    assert (
        session.scalar(
            sa.select(sa.func.count()).select_from(ArtefactManifestMember)
        )
        == 0
    )


def _memory_observation() -> ResourceObservation:
    return ResourceObservation(
        category=ResourceCategory.MEMORY_BYTES,
        enforcement_status=ResourceEnforcementStatus.CAPTURE_BOUND_ENFORCED,
        terminated_execution=False,
        configured_value=ResourceValue(amount=536_870_912, unit="bytes"),
        observed_value=ResourceValue(amount=1_048_576, unit="bytes"),
        breached=False,
    )


def _cpu_observation() -> ResourceObservation:
    return ResourceObservation(
        category=ResourceCategory.CPU_TIME,
        enforcement_status=ResourceEnforcementStatus.NOT_ENFORCED,
        terminated_execution=False,
        configuration_reference=OpaqueReference("config://cpu-limit"),
    )


def test_execution_resource_observation_growth_conflicts(
    session: Session,
) -> None:
    aggregate = _candidate(session)
    persist_execution_evidence_metadata(
        session,
        make_execution_evidence(
            workflow_attempt_id=str(aggregate.workflow.attempt.id),
            resource_observations=(_memory_observation(),),
        ),
    )

    grown = make_execution_evidence(
        workflow_attempt_id=str(aggregate.workflow.attempt.id),
        resource_observations=(_memory_observation(), _cpu_observation()),
    )
    with pytest.raises(DB004PersistenceConflictError):
        persist_execution_evidence_metadata(session, grown)

    ordinals = session.scalars(
        sa.select(ExecutionResourceObservation.ordinal).where(
            ExecutionResourceObservation.execution_evidence_id
            == "execution-evidence-1"
        )
    ).all()
    assert ordinals == [1]


def test_execution_test_case_growth_conflicts_without_partial_write(
    session: Session,
) -> None:
    aggregate = _candidate(session)
    persist_execution_evidence_metadata(
        session, make_execution_evidence(workflow_attempt_id=str(aggregate.workflow.attempt.id))
    )

    grown = make_execution_evidence(
        workflow_attempt_id=str(aggregate.workflow.attempt.id),
        test_result=TestResult(
            executed_count=3,
            passed_count=3,
            test_cases=(
                TestCaseResult(
                    test_reference=OpaqueReference("test://ExampleTest.testAnswer"),
                    status=TestCaseStatus.PASSED,
                ),
                TestCaseResult(
                    test_reference=OpaqueReference("test://ExampleTest.testOther"),
                    status=TestCaseStatus.PASSED,
                ),
                TestCaseResult(
                    test_reference=OpaqueReference("test://ExampleTest.testGrown"),
                    status=TestCaseStatus.PASSED,
                ),
            ),
        ),
    )
    with pytest.raises(DB004PersistenceConflictError):
        persist_execution_evidence_metadata(session, grown)

    ordinals = session.scalars(
        sa.select(ExecutionTestCaseResult.ordinal).where(
            ExecutionTestCaseResult.execution_evidence_id == "execution-evidence-1"
        )
    ).all()
    assert ordinals == [1, 2]
    assert (
        session.scalar(
            sa.select(sa.func.count()).select_from(ExecutionEvidenceRecord)
        )
        == 1
    )


# ---------------------------------------------------------------------------
# C3: cross-row provenance consistency
# ---------------------------------------------------------------------------


def test_execution_supplied_run_must_match_the_candidate_run(
    session: Session,
) -> None:
    aggregate = _candidate(session)
    foreign = _workflow(session)
    evidence = make_execution_evidence(
        workflow_attempt_id=str(foreign.attempt.id),
        run_id=RunId(str(foreign.run.id)),
    )
    with pytest.raises(ValueError):
        persist_execution_evidence_metadata(session, evidence)
    assert (
        session.get(
            ExecutionEvidenceRecord,
            {"execution_evidence_id": "execution-evidence-1"},
        )
        is None
    )


def _second_candidate(session: Session, aggregate: SimpleNamespace) -> None:
    workflow = aggregate.workflow
    run_id = str(workflow.run.id)
    attempt_id = str(workflow.attempt.id)
    persist_candidate_metadata(
        session,
        patch=make_candidate_patch(
            run_id,
            attempt_id,
            candidate_patch_id=CandidatePatchId("candidate-patch-2"),
            candidate_version_id=CandidateVersionId("candidate-version-2"),
        ),
        version=make_candidate_version(
            run_id,
            attempt_id,
            candidate_version_id="candidate-version-2",
            candidate_patch_id="candidate-patch-2",
        ),
    )


def test_embedded_artefact_conflicting_candidate_linkage_rejected(
    session: Session,
) -> None:
    aggregate = _candidate(session)
    _second_candidate(session, aggregate)
    poisoned = make_execution_evidence(
        workflow_attempt_id=str(aggregate.workflow.attempt.id),
        stdout_artefact=make_artefact_reference(
            artefact_id=ArtefactId("art.link.stdout"),
            storage_locator="object-store://bucket/link-stdout",
            candidate_version_id=CandidateVersionId("candidate-version-2"),
        ),
    )
    with pytest.raises(ValueError):
        persist_execution_evidence_metadata(session, poisoned)


def test_embedded_artefact_with_matching_linkages_persist(session: Session) -> None:
    aggregate = _candidate(session)
    stdout = make_artefact_reference(
        artefact_id=ArtefactId("art.link.stdout.ok"),
        storage_locator="object-store://bucket/link-ok",
        candidate_version_id=CandidateVersionId("candidate-version-1"),
    )
    stored = persist_execution_evidence_metadata(
        session,
        make_execution_evidence(
            workflow_attempt_id=str(aggregate.workflow.attempt.id),
            stdout_artefact=stdout,
        ),
    )
    roles = {
        row.artefact_id: row.role
        for row in session.execute(
            sa.select(ExecutionArtefactRole).where(
                ExecutionArtefactRole.execution_evidence_id
                == stored.execution_evidence_id
            )
        ).scalars()
    }
    assert roles == {"art.link.stdout.ok": "STDOUT"}


def test_standalone_artefact_cross_candidate_linkage_rejected(
    session: Session,
) -> None:
    aggregate = _candidate(session)
    evidence = make_execution_evidence(
        workflow_attempt_id=str(aggregate.workflow.attempt.id)
    )
    persist_execution_evidence_metadata(session, evidence)
    _second_candidate(session, aggregate)

    cross_linked = make_artefact_reference(
        artefact_id=ArtefactId("art.cross.candidate"),
        artefact_type="CUSTOM_OUTPUT",
        storage_locator="object-store://bucket/cross-candidate",
        candidate_version_id=CandidateVersionId("candidate-version-2"),
        execution_evidence_id=ExecutionEvidenceId("execution-evidence-1"),
    )
    with pytest.raises(ValueError):
        persist_artefact_reference_metadata(session, cross_linked)


def _durable_member(session: Session, name: str):
    reference = make_artefact_reference(
        artefact_id=ArtefactId(name),
        artefact_type="CUSTOM_OUTPUT",
        storage_locator=f"object-store://bucket/{name}",
    )
    persist_artefact_reference_metadata(session, reference)
    return reference


def test_manifest_candidate_must_match_execution_evidence_candidate(
    session: Session,
) -> None:
    aggregate, _, _ = _execution(session)
    _second_candidate(session, aggregate)
    member = _durable_member(session, "art.manifest.mismatch")

    manifest = make_artefact_manifest(
        members=(member,),
        candidate_version_id=CandidateVersionId("candidate-version-2"),
        execution_evidence_id=ExecutionEvidenceId("execution-evidence-1"),
    )
    with pytest.raises(ValueError):
        persist_artefact_manifest_metadata(session, manifest)


def test_manifest_attempt_must_match_execution_evidence_attempt(
    session: Session,
) -> None:
    _, _, _ = _execution(session)
    foreign = _workflow(session)
    member = _durable_member(session, "art.manifest.attempt")

    manifest = make_artefact_manifest(
        members=(member,),
        execution_evidence_id=ExecutionEvidenceId("execution-evidence-1"),
        workflow_attempt_id=WorkflowAttemptId(str(foreign.attempt.id)),
    )
    with pytest.raises(ValueError):
        persist_artefact_manifest_metadata(session, manifest)


def test_manifest_phase_must_match_execution_evidence_phase(
    session: Session,
) -> None:
    _, _, _ = _execution(session)
    member = _durable_member(session, "art.manifest.phase")

    manifest = make_artefact_manifest(
        members=(member,),
        execution_evidence_id=ExecutionEvidenceId("execution-evidence-1"),
        execution_phase=ExecutionPhase.COMPILE,
    )
    with pytest.raises(ValueError):
        persist_artefact_manifest_metadata(session, manifest)


def test_manifest_attempt_must_belong_to_the_candidate_run(
    session: Session,
) -> None:
    aggregate, _, _ = _execution(session)
    foreign = _workflow(session)
    member = _durable_member(session, "art.manifest.ownership")

    manifest = make_artefact_manifest(
        members=(member,),
        candidate_version_id=CandidateVersionId("candidate-version-1"),
        workflow_attempt_id=WorkflowAttemptId(str(foreign.attempt.id)),
    )
    with pytest.raises(ValueError):
        persist_artefact_manifest_metadata(session, manifest)
    assert aggregate.patch_row.candidate_patch_id == "candidate-patch-1"


def test_manifest_with_consistent_provenance_persists(session: Session) -> None:
    aggregate, _, _ = _execution(session)
    member = _durable_member(session, "art.manifest.consistent")

    stored = persist_artefact_manifest_metadata(
        session,
        make_artefact_manifest(
            members=(member,),
            candidate_version_id=CandidateVersionId("candidate-version-1"),
            execution_evidence_id=ExecutionEvidenceId("execution-evidence-1"),
            workflow_attempt_id=WorkflowAttemptId(str(aggregate.workflow.attempt.id)),
            execution_phase=ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST,
        ),
    )
    assert stored.artefact_manifest_id == "manifest-1"
    assert stored.candidate_version_id == "candidate-version-1"
    assert stored.execution_phase == "BUGGY_OR_TARGET_REVISION_TEST"


# ---------------------------------------------------------------------------
# C4: manifest members must match durable artefact reference metadata
# ---------------------------------------------------------------------------


def test_manifest_member_equivalent_metadata_passes(session: Session) -> None:
    member = make_artefact_reference(
        artefact_id=ArtefactId("art.member.equivalent"),
        artefact_type="CUSTOM_OUTPUT",
        storage_locator="object-store://bucket/equivalent",
    )
    persist_artefact_reference_metadata(session, member)
    stored = persist_artefact_manifest_metadata(
        session, make_artefact_manifest(members=(member,))
    )
    assert stored.artefact_manifest_id == "manifest-1"


_CONFLICTING_MEMBER_OVERRIDES = [
    {"content_digest": OpaqueReference("sha256:" + "01" * 32)},
    {"digest_algorithm": OpaqueReference("MD5")},
    {"byte_size": 999},
    {"media_type": "application/json"},
    {"storage_locator": "object-store://bucket/elsewhere"},
    {"availability": "EXPIRED"},
    {"integrity": make_integrity(state="CORRUPT")},
    {"producer_id": OpaqueReference("producer://someone-else")},
    {"redaction_state": OpaqueReference("redaction://applied")},
    {"creation_timestamp": GENERATED_AT + timedelta(seconds=1)},
    {
        "integrity": make_integrity(
            state="VERIFIED", verification_reference="verify-ref://other"
        )
    },
]


@pytest.mark.parametrize("override", _CONFLICTING_MEMBER_OVERRIDES)
def test_manifest_member_conflicting_metadata_fails_closed(
    session: Session, override: dict[str, object]
) -> None:
    values = dict(
        artefact_id=ArtefactId("art.member.conflict"),
        artefact_type="CUSTOM_OUTPUT",
        storage_locator="object-store://bucket/conflict",
    )
    durable = make_artefact_reference(**values)
    persist_artefact_reference_metadata(session, durable)

    impostor = make_artefact_reference(**{**values, **override})
    with pytest.raises(DB004PersistenceConflictError):
        persist_artefact_manifest_metadata(
            session, make_artefact_manifest(members=(impostor,))
        )
    # The durable reference was not overwritten by the impostor.
    kept = session.get(
        ArtefactReferenceRecord, {"artefact_id": "art.member.conflict"}
    )
    assert kept.byte_size == durable.byte_size
    assert kept.media_type == durable.media_type


def test_manifest_member_candidate_linkage_conflict_fails_closed(
    session: Session,
) -> None:
    aggregate = _candidate(session)
    values = dict(
        artefact_id=ArtefactId("art.member.linkage"),
        artefact_type="CUSTOM_OUTPUT",
        storage_locator="object-store://bucket/linkage",
    )
    durable = make_artefact_reference(**values)
    persist_artefact_reference_metadata(session, durable)

    impostor = make_artefact_reference(
        **values,
        candidate_version_id=CandidateVersionId("candidate-version-1"),
    )
    with pytest.raises(DB004PersistenceConflictError):
        persist_artefact_manifest_metadata(
            session, make_artefact_manifest(members=(impostor,))
        )


def test_manifest_member_execution_linkage_conflict_fails_closed(
    session: Session,
) -> None:
    _, _, _ = _execution(session)
    values = dict(
        artefact_id=ArtefactId("art.member.exec.linkage"),
        artefact_type="CUSTOM_OUTPUT",
        storage_locator="object-store://bucket/exec-linkage",
    )
    durable = make_artefact_reference(**values)
    persist_artefact_reference_metadata(session, durable)

    impostor = make_artefact_reference(
        **values,
        execution_evidence_id=ExecutionEvidenceId("execution-evidence-1"),
    )
    with pytest.raises(DB004PersistenceConflictError):
        persist_artefact_manifest_metadata(
            session, make_artefact_manifest(members=(impostor,))
        )
