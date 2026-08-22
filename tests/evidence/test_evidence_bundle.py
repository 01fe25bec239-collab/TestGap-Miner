"""Contract coverage for the Evidence-owned immutable EvidenceBundle."""

import inspect
import json
from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timedelta, timezone

import pytest

import app.evidence
from app.evidence import (
    EVIDENCE_CONTRACT_VERSION,
    QUEUE_CONTRACT_VERSION,
    WORKFLOW_CONTRACT_VERSION,
    ArtefactId,
    ArtefactManifest,
    ArtefactManifestFinalizationState,
    ArtefactManifestId,
    ArtefactReference,
    ArtefactType,
    CandidatePatchId,
    CandidateVersionId,
    CompileResult,
    CompileStatus,
    CorrelationId,
    EvidenceAvailability,
    EvidenceBundle,
    EvidenceBundleId,
    EvidenceComparison,
    EvidenceCompleteness,
    EvidenceIntegrityState,
    ExecutionEvidence,
    ExecutionEvidenceId,
    ExecutionOutcome,
    ExecutionPhase,
    ExecutionTiming,
    FailureCategory,
    FailureEvidence,
    HumanDecisionId,
    IntegrityMetadata,
    OpaqueReference,
    ProcessExit,
    ProducerResultId,
    QueueDeliveryId,
    QueueMessageId,
    RunId,
    TestCaseResult as ExecutionTestCaseResult,
    TestCaseStatus as ExecutionTestCaseStatus,
    TestResult as ExecutionTestResult,
    TimeoutMetadata,
    WorkflowAttemptId,
    compare_evidence_bundles,
)
import app.evidence.bundle as bundle_module


STARTED_AT = datetime(2026, 8, 22, 9, 0, tzinfo=timezone.utc)
ENDED_AT = STARTED_AT + timedelta(seconds=2)
ARTEFACT_CREATED_AT = datetime(2026, 8, 22, 8, 55, tzinfo=timezone.utc)

BUGGY_REVISION = "revision:buggy:abc123"
FIXED_REVISION = "revision:fixed:def456"


def verified(reference: str) -> IntegrityMetadata:
    return IntegrityMetadata(
        EvidenceIntegrityState.VERIFIED,
        OpaqueReference(reference),
    )


def artefact(
    identity: str,
    artefact_type: ArtefactType,
    *,
    availability: EvidenceAvailability = EvidenceAvailability.AVAILABLE,
    integrity_state: EvidenceIntegrityState = EvidenceIntegrityState.VERIFIED,
) -> ArtefactReference:
    integrity_reference = (
        OpaqueReference(f"integrity:{identity}")
        if integrity_state is EvidenceIntegrityState.VERIFIED
        else OpaqueReference(f"integrity-observation:{identity}")
    )
    return ArtefactReference(
        artefact_id=ArtefactId(identity),
        artefact_type=artefact_type,
        availability=availability,
        integrity=IntegrityMetadata(integrity_state, integrity_reference),
        content_digest=OpaqueReference(f"digest:{identity}"),
        digest_algorithm=OpaqueReference("digest-algorithm:configured"),
        byte_size=64,
        media_type="text/plain",
        producer_id=OpaqueReference("producer:execution-runner"),
        creation_timestamp=ARTEFACT_CREATED_AT,
        storage_locator=f"locator:{identity}",
    )


def timing() -> ExecutionTiming:
    return ExecutionTiming(
        started_at=STARTED_AT,
        ended_at=ENDED_AT,
        duration=timedelta(seconds=2),
        upstream_fact_reference=OpaqueReference("execution-timing:1"),
    )


def passed_case() -> ExecutionTestCaseResult:
    return ExecutionTestCaseResult(OpaqueReference("test:example"), ExecutionTestCaseStatus.PASSED)


def failed_case() -> ExecutionTestCaseResult:
    return ExecutionTestCaseResult(
        OpaqueReference("test:example"),
        ExecutionTestCaseStatus.FAILED,
        OpaqueReference("failure:test:example"),
    )


def compile_record(**changes: object) -> ExecutionEvidence:
    values: dict[str, object] = {
        "execution_evidence_id": ExecutionEvidenceId("evidence:compile:1"),
        "producer_result_id": ProducerResultId("producer-result:compile:1"),
        "workflow_attempt_id": WorkflowAttemptId("attempt:1"),
        "candidate_version_id": CandidateVersionId("candidate-version:1"),
        "execution_phase": ExecutionPhase.COMPILE,
        "outcome": ExecutionOutcome.SUCCESS,
        "completeness": EvidenceCompleteness.COMPLETE,
        "command_reference": OpaqueReference("execution-command:compile:1"),
        "execution_fact_reference": OpaqueReference("execution-result:compile:1"),
        "compile_result": CompileResult(
            CompileStatus.SUCCESS,
            error_count=0,
            warning_count=0,
            compiler_metadata_reference=OpaqueReference("compiler-metadata:1"),
        ),
        "run_id": RunId("run:1"),
        "execution_timing": timing(),
        "timeout_metadata": TimeoutMetadata(timed_out=False),
        "process_exit": process_exit(),
        "stdout_artefact": artefact(
            "artefact:compile-stdout:1", ArtefactType.COMPILE_LOG
        ),
        "stderr_artefact": artefact(
            "artefact:compile-stderr:1", ArtefactType.COMPILE_LOG
        ),
        "execution_integrity": verified("integrity:execution:compile:1"),
    }
    values.update(changes)
    return ExecutionEvidence(**values)  # type: ignore[arg-type]


def buggy_record(**changes: object) -> ExecutionEvidence:
    values: dict[str, object] = {
        "execution_evidence_id": ExecutionEvidenceId("evidence:buggy-test:1"),
        "producer_result_id": ProducerResultId("producer-result:buggy-test:1"),
        "workflow_attempt_id": WorkflowAttemptId("attempt:1"),
        "candidate_version_id": CandidateVersionId("candidate-version:1"),
        "execution_phase": ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST,
        "outcome": ExecutionOutcome.SUCCESS,
        "completeness": EvidenceCompleteness.COMPLETE,
        "command_reference": OpaqueReference("execution-command:buggy-test:1"),
        "execution_fact_reference": OpaqueReference("execution-result:buggy-test:1"),
        "test_result": ExecutionTestResult(
            executed_count=1,
            passed_count=1,
            failed_count=0,
            skipped_count=0,
            errored_count=0,
            test_cases=(passed_case(),),
        ),
        "run_id": RunId("run:1"),
        "source_revision": OpaqueReference(BUGGY_REVISION),
        "execution_timing": timing(),
        "timeout_metadata": TimeoutMetadata(timed_out=False),
        "process_exit": process_exit(),
        "stdout_artefact": artefact(
            "artefact:buggy-stdout:1", ArtefactType.TEST_STDOUT
        ),
        "stderr_artefact": artefact(
            "artefact:buggy-stderr:1", ArtefactType.TEST_STDERR
        ),
        "execution_integrity": verified("integrity:execution:buggy-test:1"),
    }
    values.update(changes)
    return ExecutionEvidence(**values)  # type: ignore[arg-type]


def fixed_record(**changes: object) -> ExecutionEvidence:
    values: dict[str, object] = {
        "execution_evidence_id": ExecutionEvidenceId("evidence:fixed-test:1"),
        "producer_result_id": ProducerResultId("producer-result:fixed-test:1"),
        "workflow_attempt_id": WorkflowAttemptId("attempt:1"),
        "candidate_version_id": CandidateVersionId("candidate-version:1"),
        "execution_phase": ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST,
        "outcome": ExecutionOutcome.SUCCESS,
        "completeness": EvidenceCompleteness.COMPLETE,
        "command_reference": OpaqueReference("execution-command:fixed-test:1"),
        "execution_fact_reference": OpaqueReference("execution-result:fixed-test:1"),
        "test_result": ExecutionTestResult(
            executed_count=1,
            passed_count=1,
            failed_count=0,
            skipped_count=0,
            errored_count=0,
            test_cases=(passed_case(),),
        ),
        "run_id": RunId("run:1"),
        "source_revision": OpaqueReference(FIXED_REVISION),
        "execution_timing": timing(),
        "timeout_metadata": TimeoutMetadata(timed_out=False),
        "process_exit": process_exit(),
        "stdout_artefact": artefact(
            "artefact:fixed-stdout:1", ArtefactType.TEST_STDOUT
        ),
        "stderr_artefact": artefact(
            "artefact:fixed-stderr:1", ArtefactType.TEST_STDERR
        ),
        "execution_integrity": verified("integrity:execution:fixed-test:1"),
    }
    values.update(changes)
    return ExecutionEvidence(**values)  # type: ignore[arg-type]


def manifest(**changes: object) -> ArtefactManifest:
    values: dict[str, object] = {
        "artefact_manifest_id": ArtefactManifestId("artefact-manifest:1"),
        "artefact_references": (
            artefact("artefact:manifest:2", ArtefactType.TEST_STDOUT),
            artefact("artefact:manifest:1", ArtefactType.CONTEXT_MANIFEST),
        ),
        "creation_timestamp": ARTEFACT_CREATED_AT,
        "finalization_state": ArtefactManifestFinalizationState.ASSEMBLING,
        "candidate_version_id": CandidateVersionId("candidate-version:1"),
        "workflow_attempt_id": WorkflowAttemptId("attempt:1"),
    }
    values.update(changes)
    return ArtefactManifest(**values)  # type: ignore[arg-type]


def finalized_manifest(**changes: object) -> ArtefactManifest:
    values = {
        "finalization_state": ArtefactManifestFinalizationState.FINALIZED,
        "producer_provenance_reference": OpaqueReference("producer-provenance:1"),
        "manifest_digest": OpaqueReference("manifest-digest:1"),
        "manifest_digest_algorithm": OpaqueReference("digest-algorithm:configured"),
        "integrity_metadata": verified("integrity:artefact-manifest:1"),
        "finalization_timestamp": ARTEFACT_CREATED_AT + timedelta(seconds=1),
    }
    values.update(changes)
    return manifest(**values)


def bundle_values(**changes: object) -> dict[str, object]:
    values: dict[str, object] = {
        "evidence_bundle_id": EvidenceBundleId("bundle:1"),
        "candidate_patch_id": CandidatePatchId("patch:1"),
        "candidate_version_id": CandidateVersionId("candidate-version:1"),
        "completeness": EvidenceCompleteness.PARTIAL,
        "run_id": RunId("run:1"),
        "run_request_id": OpaqueReference("run-request:1"),
        "workflow_attempt_id": WorkflowAttemptId("attempt:1"),
        "workflow_step": OpaqueReference("workflow-step:1"),
        "producer_id": OpaqueReference("producer:runner-host"),
        "runner_id": OpaqueReference("runner:host-1"),
        "source_repository": OpaqueReference("repo:testgap/example"),
        "source_revision": OpaqueReference(BUGGY_REVISION),
        "selected_context_manifest": OpaqueReference("context-manifest:1"),
        "configuration_version": OpaqueReference("configuration:v1"),
        "model_identifier": OpaqueReference("model:test-model"),
        "prompt_template_version": OpaqueReference("prompt-template:v1"),
        "producer_schema_version": OpaqueReference("producer-schema:v1"),
    }
    values.update(changes)
    return values


def bundle(**changes: object) -> EvidenceBundle:
    return EvidenceBundle(**bundle_values(**changes))  # type: ignore[arg-type]


def aggregate_bundle(**changes: object) -> EvidenceBundle:
    values = bundle_values(
        target_reference_revision=OpaqueReference(FIXED_REVISION),
        execution_evidence=[compile_record(), buggy_record(), fixed_record()],
    )
    values.update(changes)
    return EvidenceBundle(**values)  # type: ignore[arg-type]


def complete_bundle(**changes: object) -> EvidenceBundle:
    values = bundle_values(
        completeness=EvidenceCompleteness.COMPLETE,
        target_reference_revision=OpaqueReference(FIXED_REVISION),
        execution_evidence=[compile_record(), buggy_record(), fixed_record()],
        integrity_metadata=verified("integrity:bundle:1"),
    )
    values.update(changes)
    return EvidenceBundle(**values)  # type: ignore[arg-type]


def process_exit() -> ProcessExit:
    return ProcessExit(
        exit_code=0,
        upstream_fact_reference=OpaqueReference("process-exit:1"),
    )


LEGACY_EXPORTS = frozenset(
    {
        "ARTEFACT_MANIFEST_CARDINALITY_BOUND",
        "ARTEFACT_MANIFEST_SCHEMA_VERSION",
        "EVIDENCE_CONTRACT_VERSION",
        "ArtefactId",
        "ArtefactManifest",
        "ArtefactManifestFinalizationState",
        "ArtefactManifestId",
        "ArtefactReference",
        "ArtefactType",
        "CandidateFinalizationState",
        "CandidatePatch",
        "CandidatePatchId",
        "CandidateVersion",
        "CandidateVersionId",
        "ChangedFile",
        "CompileStatus",
        "CompileResult",
        "CorrelationId",
        "DecisionDisposition",
        "EvidenceAvailability",
        "EvidenceBundleId",
        "EvidenceCardId",
        "EvidenceComparison",
        "EvidenceCompleteness",
        "EvidenceIntegrityState",
        "ExecutionEvidence",
        "ExecutionEvidenceId",
        "ExecutionOutcome",
        "ExecutionPhase",
        "ExecutionTiming",
        "FailureCategory",
        "FailureEvidence",
        "GenerationProvenance",
        "HumanDecisionId",
        "HumanDecisionLink",
        "HumanDecisionLinkId",
        "IntegrityMetadata",
        "OpaqueReference",
        "ProcessExit",
        "ProducerResultId",
        "QueueDeliveryId",
        "QueueMessageId",
        "ResourceCategory",
        "ResourceEnforcementStatus",
        "ResourceObservation",
        "ResourceValue",
        "RunId",
        "TestCaseResult",
        "TestCaseStatus",
        "TestResult",
        "TimeoutMetadata",
        "WorkflowAttemptId",
        "compare_artefact_manifests",
        "compare_artefact_references",
        "compare_candidate_patches",
        "compare_candidate_versions",
        "compare_execution_evidence",
        "compare_human_decision_links",
        "validate_candidate_lineage",
        "validate_candidate_patch_version",
    }
)


FORBIDDEN_RUNTIME_MEMBERS = (
    "ack",
    "claim",
    "connect",
    "cursor",
    "download",
    "execute",
    "migrate",
    "nack",
    "open",
    "presign",
    "publish",
    "redact",
    "retry",
    "score",
    "session",
    "subprocess",
    "transition",
    "upload",
)

FORBIDDEN_SOURCE_TOKENS = (
    "subprocess",
    "sqlalchemy",
    "boto3",
    "socket",
    "httpx",
    "requests",
    "uuid",
    "secrets",
    "random.",
    "datetime.now",
    "time.time",
)


def test_minimal_valid_evidence_bundle() -> None:
    supplied = EvidenceBundleId("bundle:minimal")
    value = bundle(evidence_bundle_id=supplied)
    assert value.evidence_bundle_id is supplied
    assert value.candidate_patch_id == CandidatePatchId("patch:1")
    assert value.candidate_version_id == CandidateVersionId("candidate-version:1")
    assert value.completeness is EvidenceCompleteness.PARTIAL
    assert value.execution_evidence == ()
    assert value.artefact_manifest is None
    assert value.integrity_metadata is None


def test_compile_buggy_fixed_aggregate_preserves_each_phase() -> None:
    records = [compile_record(), buggy_record(), fixed_record()]
    value = aggregate_bundle(execution_evidence=records)
    by_phase = {record.execution_phase: record for record in value.execution_evidence}
    assert set(by_phase) == set(ExecutionPhase)
    assert by_phase[ExecutionPhase.COMPILE].compile_result is not None
    assert by_phase[ExecutionPhase.COMPILE].test_result is None
    assert by_phase[
        ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST
    ].test_result is not None
    assert by_phase[ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST].compile_result is None
    assert by_phase[
        ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST
    ].test_result is not None
    assert {id(record) for record in value.execution_evidence} == {
        id(record) for record in records
    }


def test_caller_supplied_identity_is_retained_without_generation() -> None:
    supplied = EvidenceBundleId("bundle:caller-owned")
    first = bundle(evidence_bundle_id=supplied)
    second = bundle(evidence_bundle_id=supplied)
    assert first.evidence_bundle_id is supplied
    assert second.evidence_bundle_id == first.evidence_bundle_id
    generators = [
        name
        for name in dir(bundle_module)
        if any(token in name.lower() for token in ("generate", "mint"))
    ]
    generators += [
        name
        for name in vars(EvidenceBundle)
        if any(token in name.lower() for token in ("generate", "mint", "new_"))
    ]
    assert not generators


@pytest.mark.parametrize(
    ("field", "identity_type"),
    [
        ("candidate_patch_id", CandidatePatchId),
        ("candidate_version_id", CandidateVersionId),
        ("run_id", RunId),
        ("workflow_attempt_id", WorkflowAttemptId),
    ],
)
def test_bundle_identity_rejects_core_identity_collisions(
    field: str,
    identity_type: type,
) -> None:
    colliding = {field: identity_type("shared:value")}
    with pytest.raises(ValueError, match="distinct"):
        bundle(evidence_bundle_id=EvidenceBundleId("shared:value"), **colliding)


@pytest.mark.parametrize(
    ("field", "identity_type"),
    [
        ("queue_message_id", QueueMessageId),
        ("queue_delivery_id", QueueDeliveryId),
        ("correlation_id", CorrelationId),
        ("human_decision_id", HumanDecisionId),
    ],
)
def test_bundle_identity_rejects_optional_identity_collisions(
    field: str,
    identity_type: type,
) -> None:
    colliding = {field: identity_type("shared:value")}
    with pytest.raises(ValueError, match="distinct"):
        bundle(evidence_bundle_id=EvidenceBundleId("shared:value"), **colliding)


def test_bundle_identity_rejects_execution_and_producer_collisions() -> None:
    with pytest.raises(ValueError, match="distinct"):
        bundle(
            execution_evidence=[
                buggy_record(execution_evidence_id=ExecutionEvidenceId("bundle:1"))
            ]
        )
    with pytest.raises(ValueError, match="distinct"):
        bundle(
            execution_evidence=[
                buggy_record(producer_result_id=ProducerResultId("bundle:1"))
            ]
        )


def test_bundle_identity_rejects_manifest_and_member_collisions() -> None:
    with pytest.raises(ValueError, match="distinct"):
        bundle(
            artefact_manifest=manifest(
                artefact_manifest_id=ArtefactManifestId("bundle:1")
            )
        )
    with pytest.raises(ValueError, match="distinct"):
        bundle(
            artefact_manifest=manifest(
                artefact_references=(
                    artefact("bundle:1", ArtefactType.TEST_STDOUT),
                )
            )
        )


def test_candidate_patch_and_version_binding_stays_distinct() -> None:
    value = bundle()
    assert type(value.candidate_patch_id) is CandidatePatchId
    assert type(value.candidate_version_id) is CandidateVersionId
    same_value_pair = (CandidatePatchId("shared"), CandidateVersionId("shared"))
    assert same_value_pair[0] != same_value_pair[1]
    assert same_value_pair[0].value == same_value_pair[1].value
    with pytest.raises(ValueError, match="distinct"):
        bundle(candidate_patch_id=CandidatePatchId("bundle:1"))
    with pytest.raises(ValueError, match="distinct"):
        bundle(candidate_version_id=CandidateVersionId("bundle:1"))


def test_deterministic_phase_ordering_regardless_of_input_order() -> None:
    forward = [compile_record(), buggy_record(), fixed_record()]
    shuffled = [fixed_record(), compile_record(), buggy_record()]
    expected = tuple(sorted(forward, key=lambda record: record.to_domain_json()))
    left = aggregate_bundle(execution_evidence=forward)
    right = aggregate_bundle(execution_evidence=shuffled)
    assert left.execution_evidence == expected
    assert left.execution_phases == tuple(
        record.execution_phase for record in expected
    )
    assert len(set(left.execution_phases)) == 3
    assert right == left
    assert right.to_domain_json() == left.to_domain_json()


@pytest.mark.parametrize(
    "second",
    [
        {"execution_evidence_id": ExecutionEvidenceId("evidence:buggy-test:2")},
        {},
    ],
)
def test_duplicate_semantic_execution_phase_fails_closed(
    second: dict[str, object],
) -> None:
    with pytest.raises(ValueError, match="duplicate semantic execution phase"):
        bundle(execution_evidence=[buggy_record(), buggy_record(**second)])


def test_producer_result_multiplicity_preserved_without_collapse() -> None:
    value = aggregate_bundle()
    producer_ids = [record.producer_result_id for record in value.execution_evidence]
    assert len({producer_id.value for producer_id in producer_ids}) == 3
    assert not hasattr(value, "producer_result_id")
    assert "producer_result_id" not in {
        field.name for field in fields(EvidenceBundle)
    }


def test_artefact_manifest_binding_is_preserved_as_supplied() -> None:
    supplied = manifest()
    value = bundle(artefact_manifest=supplied)
    assert value.artefact_manifest is supplied
    unbound = bundle(
        artefact_manifest=manifest(candidate_version_id=None, workflow_attempt_id=None)
    )
    assert unbound.artefact_manifest is not None


def test_artefact_manifest_binding_mismatch_rejected() -> None:
    with pytest.raises(ValueError, match="candidate_version_id"):
        bundle(
            artefact_manifest=manifest(
                candidate_version_id=CandidateVersionId("candidate-version:2")
            )
        )
    with pytest.raises(ValueError, match="workflow_attempt_id"):
        bundle(
            artefact_manifest=manifest(
                workflow_attempt_id=WorkflowAttemptId("attempt:2")
            )
        )


def test_candidate_version_mismatch_rejected() -> None:
    with pytest.raises(ValueError, match="candidate_version_id"):
        bundle(
            execution_evidence=[
                buggy_record(
                    candidate_version_id=CandidateVersionId("candidate-version:2")
                )
            ]
        )


def test_workflow_attempt_mismatch_rejected() -> None:
    with pytest.raises(ValueError, match="workflow_attempt_id"):
        bundle(
            execution_evidence=[
                buggy_record(workflow_attempt_id=WorkflowAttemptId("attempt:2"))
            ]
        )


def test_run_id_must_agree_only_where_supplied() -> None:
    without_run = bundle(execution_evidence=[buggy_record(run_id=None)])
    assert len(without_run.execution_evidence) == 1
    with pytest.raises(ValueError, match="run_id"):
        bundle(execution_evidence=[buggy_record(run_id=RunId("run:2"))])


@pytest.mark.parametrize(
    "state",
    list(EvidenceCompleteness),
)
def test_every_completeness_state_is_representable(state: EvidenceCompleteness) -> None:
    if state is EvidenceCompleteness.COMPLETE:
        value: EvidenceBundle = complete_bundle()
    else:
        value = bundle(completeness=state)
    assert value.completeness is state


def test_complete_requires_aggregate_execution_evidence() -> None:
    with pytest.raises(ValueError, match="aggregate"):
        bundle(completeness=EvidenceCompleteness.COMPLETE)


def test_complete_rejects_incomplete_contained_records() -> None:
    with pytest.raises(ValueError, match="incomplete"):
        complete_bundle(
            execution_evidence=[
                buggy_record(completeness=EvidenceCompleteness.PARTIAL)
            ]
        )


def test_complete_requires_bundle_integrity_metadata() -> None:
    with pytest.raises(ValueError, match="requires verified bundle integrity"):
        complete_bundle(integrity_metadata=None)


@pytest.mark.parametrize(
    "state",
    [EvidenceIntegrityState.CORRUPT, EvidenceIntegrityState.UNVERIFIABLE],
)
def test_complete_cannot_carry_unverified_bundle_integrity(
    state: EvidenceIntegrityState,
) -> None:
    with pytest.raises(ValueError, match="unverified integrity"):
        complete_bundle(
            execution_evidence=[buggy_record()],
            integrity_metadata=IntegrityMetadata(
                state,
                OpaqueReference("integrity-observation:bundle:1"),
            ),
        )


def test_complete_rejects_assembling_artefact_manifest() -> None:
    with pytest.raises(ValueError, match="unfinalized ArtefactManifest"):
        complete_bundle(artefact_manifest=manifest())


def test_complete_rejects_finalized_manifest_without_verified_integrity() -> None:
    with pytest.raises(
        ValueError,
        match="manifest without verified manifest integrity",
    ):
        complete_bundle(
            artefact_manifest=finalized_manifest(
                integrity_metadata=IntegrityMetadata(
                    EvidenceIntegrityState.CORRUPT,
                    OpaqueReference("integrity-observation:artefact-manifest:1"),
                )
            )
        )


def test_complete_rejects_unavailable_or_unverified_manifest_members() -> None:
    with pytest.raises(ValueError, match="unavailable artefacts"):
        complete_bundle(
            artefact_manifest=finalized_manifest(
                artefact_references=(
                    artefact(
                        "artefact:manifest:gone",
                        ArtefactType.TEST_STDOUT,
                        availability=EvidenceAvailability.UNAVAILABLE,
                    ),
                )
            )
        )
    with pytest.raises(ValueError, match="unverified artefacts"):
        complete_bundle(
            artefact_manifest=finalized_manifest(
                artefact_references=(
                    artefact(
                        "artefact:manifest:tampered",
                        ArtefactType.TEST_STDOUT,
                        integrity_state=EvidenceIntegrityState.CORRUPT,
                    ),
                )
            )
        )


def test_complete_accepts_verified_available_manifest_members() -> None:
    value = complete_bundle(artefact_manifest=finalized_manifest())
    assert value.completeness is EvidenceCompleteness.COMPLETE
    assert value.artefact_manifest is not None
    assert value.artefact_manifest.finalization_state is (
        ArtefactManifestFinalizationState.FINALIZED
    )


def test_bundle_existence_does_not_imply_complete() -> None:
    unavailable = bundle(completeness=EvidenceCompleteness.UNAVAILABLE)
    assert unavailable.execution_evidence == ()
    partial_with_records = bundle(
        execution_evidence=[buggy_record()],
    )
    assert len(partial_with_records.execution_evidence) == 1
    assert partial_with_records.completeness is EvidenceCompleteness.PARTIAL
    assert unavailable.completeness is EvidenceCompleteness.UNAVAILABLE


def test_complete_does_not_imply_workflow_success() -> None:
    failing_buggy = buggy_record(
        outcome=ExecutionOutcome.TEST_FAILURE,
        failure=FailureEvidence(
            FailureCategory.TEST_FAILURE,
            OpaqueReference("failure-ref:buggy-test:1"),
        ),
        test_result=ExecutionTestResult(
            executed_count=1,
            failed_count=1,
            test_cases=(failed_case(),),
        ),
    )
    value = bundle(
        completeness=EvidenceCompleteness.COMPLETE,
        execution_evidence=[failing_buggy],
        integrity_metadata=verified("integrity:bundle:failing"),
    )
    assert value.completeness is EvidenceCompleteness.COMPLETE
    for forbidden in ("run_state", "transition", "authorize", "approve"):
        assert not hasattr(value, forbidden)


def test_integrity_metadata_preserved_exactly_as_supplied() -> None:
    supplied = verified("integrity:bundle:supplied")
    value = bundle(integrity_metadata=supplied)
    assert value.integrity_metadata is supplied
    unverifiable = IntegrityMetadata(
        EvidenceIntegrityState.UNVERIFIABLE,
        OpaqueReference("integrity-observation:bundle:2"),
    )
    assert bundle(completeness=EvidenceCompleteness.INVALID, integrity_metadata=unverifiable).integrity_metadata is unverifiable


def test_source_repository_and_context_manifest_provenance() -> None:
    value = bundle(
        source_repository=OpaqueReference("repo:testgap/other"),
        selected_context_manifest=OpaqueReference("context-manifest:v9"),
    )
    assert value.source_repository.value == "repo:testgap/other"
    assert value.selected_context_manifest.value == "context-manifest:v9"


def test_buggy_source_revision_agreement_enforced() -> None:
    value = bundle(execution_evidence=[buggy_record()])
    assert value.execution_evidence[0].source_revision == OpaqueReference(BUGGY_REVISION)
    with pytest.raises(ValueError, match="source_revision"):
        bundle(
            execution_evidence=[
                buggy_record(source_revision=OpaqueReference("revision:buggy:zzz"))
            ]
        )


def test_fixed_reference_revision_fail_closed_when_absent() -> None:
    with pytest.raises(ValueError, match="target_reference_revision"):
        bundle(execution_evidence=[fixed_record()])


def test_fixed_reference_revision_mismatch_rejected() -> None:
    with pytest.raises(ValueError, match="target_reference_revision"):
        bundle(
            target_reference_revision=OpaqueReference("revision:fixed:other"),
            execution_evidence=[fixed_record()],
        )
    agreed = bundle(
        target_reference_revision=OpaqueReference(FIXED_REVISION),
        execution_evidence=[fixed_record()],
    )
    assert agreed.execution_evidence[0].source_revision == OpaqueReference(FIXED_REVISION)


def test_workflow_provenance_retained() -> None:
    value = bundle(
        run_id=RunId("run:r-77"),
        run_request_id=OpaqueReference("run-request:rq-77"),
        workflow_attempt_id=WorkflowAttemptId("attempt:a-77"),
        workflow_step=OpaqueReference("workflow-step:s-77"),
    )
    assert value.run_id == RunId("run:r-77")
    assert value.run_request_id.value == "run-request:rq-77"
    assert value.workflow_attempt_id == WorkflowAttemptId("attempt:a-77")
    assert value.workflow_step.value == "workflow-step:s-77"


def test_queue_message_and_delivery_provenance_retained() -> None:
    plain = bundle()
    assert plain.queue_message_id is None
    assert plain.queue_delivery_id is None
    value = bundle(
        queue_message_id=QueueMessageId("queue-message:q-1"),
        queue_delivery_id=QueueDeliveryId("queue-delivery:d-1"),
    )
    assert value.queue_message_id == QueueMessageId("queue-message:q-1")
    assert value.queue_delivery_id == QueueDeliveryId("queue-delivery:d-1")


def test_claim_lease_and_publication_provenance_retained() -> None:
    plain = bundle()
    assert plain.claim_or_lease_id is None
    assert plain.publication_identity is None
    value = bundle(
        claim_or_lease_id=OpaqueReference("claim-or-lease:lease-9"),
        publication_identity=OpaqueReference("publication:p-9"),
    )
    assert value.claim_or_lease_id.value == "claim-or-lease:lease-9"
    assert value.publication_identity.value == "publication:p-9"


def test_cross_component_provenance_retained() -> None:
    value = bundle(
        causation_id=OpaqueReference("causation:c-1"),
        correlation_id=CorrelationId("correlation:k-1"),
        human_decision_id=HumanDecisionId("human-decision:h-1"),
    )
    assert value.causation_id.value == "causation:c-1"
    assert value.correlation_id == CorrelationId("correlation:k-1")
    assert value.human_decision_id == HumanDecisionId("human-decision:h-1")


def test_producer_and_runner_provenance_retained() -> None:
    value = bundle(
        producer_id=OpaqueReference("producer:host-a"),
        runner_id=OpaqueReference("runner:instance-42"),
    )
    assert value.producer_id.value == "producer:host-a"
    assert value.runner_id.value == "runner:instance-42"


def test_configuration_model_prompt_and_schema_provenance_retained() -> None:
    value = bundle(
        configuration_version=OpaqueReference("configuration:rc-2"),
        model_identifier=OpaqueReference("model:gpt-x"),
        prompt_template_version=OpaqueReference("prompt-template:v12"),
        producer_schema_version=OpaqueReference("producer-schema:v3"),
    )
    assert value.configuration_version.value == "configuration:rc-2"
    assert value.model_identifier.value == "model:gpt-x"
    assert value.prompt_template_version.value == "prompt-template:v12"
    assert value.producer_schema_version.value == "producer-schema:v3"


def test_benchmark_provenance_paired_and_preserved() -> None:
    value = aggregate_bundle(
        evaluation_benchmark_case_reference=OpaqueReference(
            "eval-benchmark-case:case-42"
        ),
        evaluation_benchmark_manifest_version=OpaqueReference(
            "eval-benchmark-manifest:v7"
        ),
    )
    assert value.evaluation_benchmark_case_reference.value == (
        "eval-benchmark-case:case-42"
    )
    assert value.evaluation_benchmark_manifest_version.value == (
        "eval-benchmark-manifest:v7"
    )


@pytest.mark.parametrize(
    "pair",
    [
        {"evaluation_benchmark_case_reference": OpaqueReference("case-only:1")},
        {"evaluation_benchmark_manifest_version": OpaqueReference("version-only:1")},
    ],
)
def test_single_sided_benchmark_provenance_rejected(pair: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="paired"):
        bundle(**pair)


def test_non_benchmark_bundles_need_no_taxonomy() -> None:
    plain = bundle()
    assert plain.evaluation_benchmark_case_reference is None
    assert plain.evaluation_benchmark_manifest_version is None
    not_applicable = bundle(
        evaluation_benchmark_case_reference=OpaqueReference("NOT_APPLICABLE"),
        evaluation_benchmark_manifest_version=OpaqueReference("NOT_APPLICABLE"),
    )
    assert not_applicable.evaluation_benchmark_case_reference.value == "NOT_APPLICABLE"


def test_contract_version_defaults_are_exact() -> None:
    value = bundle()
    assert value.evidence_contract_version == EVIDENCE_CONTRACT_VERSION
    assert QUEUE_CONTRACT_VERSION == "CONTRACT-QUEUE-001@1.0.0-draft.2"
    assert WORKFLOW_CONTRACT_VERSION == "CONTRACT-WORKFLOW-001@1.0.0-draft.1"
    assert value.queue_contract_version == QUEUE_CONTRACT_VERSION
    assert value.workflow_contract_version == WORKFLOW_CONTRACT_VERSION


@pytest.mark.parametrize(
    ("field", "unsupported"),
    [
        ("evidence_contract_version", "CONTRACT-EVIDENCE-001@1.0.0-draft.4"),
        ("queue_contract_version", "CONTRACT-QUEUE-001@1.0.0-draft.3"),
        ("workflow_contract_version", "CONTRACT-WORKFLOW-001@1.0.0-draft.2"),
    ],
)
def test_unsupported_contract_versions_fail_closed(
    field: str,
    unsupported: str,
) -> None:
    with pytest.raises(ValueError, match="unsupported"):
        bundle(**{field: unsupported})


def test_serialization_is_deterministic_across_equivalent_inputs() -> None:
    left = complete_bundle()
    right = complete_bundle(
        execution_evidence=[fixed_record(), compile_record(), buggy_record()]
    )
    assert left == right
    assert left.to_domain_dict() == right.to_domain_dict()
    serialized = left.to_domain_json()
    assert serialized == right.to_domain_json()
    assert serialized == left.to_domain_json()
    assert "0x" not in serialized
    reparsed = json.loads(serialized)
    assert reparsed["evidence_bundle_id"] == {"value": "bundle:1"}
    assert reparsed["completeness"] == "COMPLETE"


def test_caller_collection_mutation_does_not_affect_bundle() -> None:
    records = [compile_record()]
    value = bundle(execution_evidence=records)
    records.append(buggy_record())
    records.clear()
    assert len(value.execution_evidence) == 1
    assert value.execution_evidence[0].execution_phase is ExecutionPhase.COMPILE


def test_duplicate_convergence_classification() -> None:
    existing = complete_bundle()
    incoming = complete_bundle(
        execution_evidence=[fixed_record(), buggy_record(), compile_record()]
    )
    assert compare_evidence_bundles(existing, incoming) is EvidenceComparison.EQUIVALENT


def test_material_conflict_classification_without_mutation() -> None:
    existing = bundle(execution_evidence=[buggy_record()])
    conflicting_content = bundle(
        execution_evidence=[
            buggy_record(command_reference=OpaqueReference("execution-command:changed"))
        ]
    )
    conflicting_state = replace(existing, completeness=EvidenceCompleteness.INVALID)
    existing_snapshot = existing.to_domain_json()
    incoming_snapshot = conflicting_content.to_domain_json()
    assert compare_evidence_bundles(existing, conflicting_content) is (
        EvidenceComparison.CONFLICTING
    )
    assert compare_evidence_bundles(existing, conflicting_state) is (
        EvidenceComparison.CONFLICTING
    )
    assert existing.to_domain_json() == existing_snapshot
    assert conflicting_content.to_domain_json() == incoming_snapshot


def test_distinct_identity_comparison() -> None:
    existing = bundle()
    other = replace(existing, evidence_bundle_id=EvidenceBundleId("bundle:2"))
    assert compare_evidence_bundles(existing, other) is EvidenceComparison.DISTINCT_IDENTITY


def test_canonical_evidence_bundle_id_is_reused_not_redeclared() -> None:
    import app.evidence.decision as decision_module

    assert app.evidence.EvidenceBundleId is decision_module.EvidenceBundleId
    assert bundle_module.EvidenceBundleId is decision_module.EvidenceBundleId
    assert isinstance(bundle().evidence_bundle_id, decision_module.EvidenceBundleId)
    redeclared = [
        name
        for name, member in vars(bundle_module).items()
        if isinstance(member, type)
        and name.startswith("EvidenceBundle")
        and name not in ("EvidenceBundle", "EvidenceBundleId")
    ]
    assert redeclared == []


def test_legacy_evidence_exports_are_preserved() -> None:
    for name in LEGACY_EXPORTS:
        assert hasattr(app.evidence, name), name
        assert name in app.evidence.__all__, name


def test_no_runtime_component_behavior_is_exposed() -> None:
    for member in FORBIDDEN_RUNTIME_MEMBERS:
        assert not hasattr(bundle_module, member), member
        assert not hasattr(EvidenceBundle, member), member
    source = inspect.getsource(bundle_module)
    for token in FORBIDDEN_SOURCE_TOKENS:
        assert token not in source, token


def test_no_second_reference_size_policy_is_invented() -> None:
    assert not hasattr(bundle_module, "MAX_BUNDLE_REFERENCE_BYTES")
    invented_bounds = [
        name
        for name in vars(bundle_module)
        if "REFERENCE" in name.upper()
        and (
            "BYTES" in name.upper()
            or "LIMIT" in name.upper()
            or "MAX" in name.upper()
        )
    ]
    assert invented_bounds == []
    source = inspect.getsource(bundle_module)
    assert "MAX_BUNDLE_REFERENCE_BYTES" not in source
    assert "exceeds" not in source


def test_bundle_defers_to_shared_opaque_reference_semantics() -> None:
    beyond_removed_bound = "x" * 16_385
    reference = OpaqueReference(beyond_removed_bound)
    value = bundle(run_request_id=reference)
    assert value.run_request_id is reference


def test_no_evidence_card_is_implemented_here() -> None:
    assert not hasattr(bundle_module, "EvidenceCard")
    assert "evidence_card_id" not in {
        field.name for field in fields(EvidenceBundle)
    }
    assert "to_card" not in vars(EvidenceBundle)


def test_bundle_is_immutable_and_replace_creates_new_value() -> None:
    value = bundle()
    snapshot = value.to_domain_json()
    with pytest.raises(FrozenInstanceError):
        value.completeness = EvidenceCompleteness.INVALID  # type: ignore[misc]
    replaced = replace(value, completeness=EvidenceCompleteness.UNAVAILABLE)
    assert value.to_domain_json() == snapshot
    assert replaced is not value
    assert replaced.evidence_bundle_id == value.evidence_bundle_id
    assert replaced.completeness is EvidenceCompleteness.UNAVAILABLE
