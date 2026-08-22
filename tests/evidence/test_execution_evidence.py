from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone

import pytest

from app.evidence import (
    ArtefactId,
    ArtefactReference,
    ArtefactType,
    CandidateVersionId,
    CompileResult,
    CompileStatus,
    CorrelationId,
    EvidenceAvailability,
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
    IntegrityMetadata,
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
    TestCaseResult as ExecutionTestCaseResult,
    TestCaseStatus as ExecutionTestCaseStatus,
    TestResult as ExecutionTestResult,
    TimeoutMetadata,
    WorkflowAttemptId,
    compare_execution_evidence,
)


STARTED_AT = datetime(2026, 8, 12, 8, 0, tzinfo=timezone.utc)
ENDED_AT = STARTED_AT + timedelta(seconds=3)
ARTEFACT_CREATED_AT = datetime(2026, 8, 12, 7, 55, tzinfo=timezone.utc)


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
        ArtefactId(identity),
        artefact_type,
        availability,
        IntegrityMetadata(integrity_state, integrity_reference),
        content_digest=OpaqueReference(f"digest:{identity}"),
        digest_algorithm=OpaqueReference("digest-algorithm:configured"),
        byte_size=64,
        media_type="text/plain",
        producer_id=OpaqueReference("producer:execution-runner"),
        creation_timestamp=ARTEFACT_CREATED_AT,
        storage_locator=f"locator:{identity}",
    )


def execution_timing() -> ExecutionTiming:
    return ExecutionTiming(
        started_at=STARTED_AT,
        ended_at=ENDED_AT,
        duration=timedelta(seconds=3),
        upstream_fact_reference=OpaqueReference("execution-timing:1"),
    )


def compile_evidence(**changes: object) -> ExecutionEvidence:
    values: dict[str, object] = {
        "execution_evidence_id": ExecutionEvidenceId("evidence:compile:1"),
        "producer_result_id": ProducerResultId("producer:compile:1"),
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
        "queue_message_id": QueueMessageId("queue-message:1"),
        "queue_delivery_id": QueueDeliveryId("queue-delivery:1"),
        "correlation_id": CorrelationId("correlation:1"),
        "source_revision": OpaqueReference("revision:buggy:abc123"),
        "execution_timing": execution_timing(),
        "timeout_metadata": TimeoutMetadata(timed_out=False),
        "process_exit": ProcessExit(
            exit_code=0,
            upstream_fact_reference=OpaqueReference("process-exit:compile:1"),
        ),
        "stdout_artefact": artefact(
            "artefact:compile-stdout:1", ArtefactType.COMPILE_LOG
        ),
        "stderr_artefact": artefact(
            "artefact:compile-stderr:1", ArtefactType.COMPILE_LOG
        ),
        "execution_integrity": verified("integrity:execution:compile:1"),
        "runtime_metadata_reference": OpaqueReference("runtime-fact:compile:1"),
        "sandbox_metadata_reference": OpaqueReference("sandbox-fact:compile:1"),
        "environment_metadata_reference": OpaqueReference(
            "environment-fact:compile:1"
        ),
    }
    values.update(changes)
    return ExecutionEvidence(**values)  # type: ignore[arg-type]


def passed_case(identity: str = "test:example") -> ExecutionTestCaseResult:
    return ExecutionTestCaseResult(
        OpaqueReference(identity), ExecutionTestCaseStatus.PASSED
    )


def make_test_evidence(**changes: object) -> ExecutionEvidence:
    values: dict[str, object] = {
        "execution_evidence_id": ExecutionEvidenceId("evidence:test:1"),
        "producer_result_id": ProducerResultId("producer:test:1"),
        "workflow_attempt_id": WorkflowAttemptId("attempt:1"),
        "candidate_version_id": CandidateVersionId("candidate-version:1"),
        "execution_phase": ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST,
        "outcome": ExecutionOutcome.SUCCESS,
        "completeness": EvidenceCompleteness.COMPLETE,
        "command_reference": OpaqueReference("execution-command:test:1"),
        "execution_fact_reference": OpaqueReference("execution-result:test:1"),
        "test_result": ExecutionTestResult(
            executed_count=1,
            passed_count=1,
            failed_count=0,
            skipped_count=0,
            errored_count=0,
            test_cases=(passed_case(),),
        ),
        "source_revision": OpaqueReference("revision:buggy:abc123"),
        "execution_timing": execution_timing(),
        "timeout_metadata": TimeoutMetadata(timed_out=False),
        "process_exit": ProcessExit(
            exit_code=0,
            upstream_fact_reference=OpaqueReference("process-exit:test:1"),
        ),
        "stdout_artefact": artefact(
            "artefact:test-stdout:1", ArtefactType.TEST_STDOUT
        ),
        "stderr_artefact": artefact(
            "artefact:test-stderr:1", ArtefactType.TEST_STDERR
        ),
        "execution_integrity": verified("integrity:execution:test:1"),
    }
    values.update(changes)
    return ExecutionEvidence(**values)  # type: ignore[arg-type]


def failure(category: FailureCategory, suffix: str = "primary") -> FailureEvidence:
    return FailureEvidence(
        category,
        OpaqueReference(f"execution-failure:{category.value.lower()}:{suffix}"),
    )


def resource_observation(
    category: ResourceCategory,
    configured: int,
    observed: int,
) -> ResourceObservation:
    return ResourceObservation(
        category=category,
        configured_value=ResourceValue(configured, "units"),
        observed_value=ResourceValue(observed, "units"),
        enforcement_status=ResourceEnforcementStatus.EXTERNAL_ENFORCED,
        terminated_execution=False,
        breached=False,
        upstream_fact_reference=OpaqueReference(f"resource-fact:{category.value.lower()}"),
    )


def resource_breach() -> ResourceObservation:
    return ResourceObservation(
        category=ResourceCategory.MEMORY_BYTES,
        configured_value=ResourceValue(1024, "bytes"),
        observed_value=ResourceValue(2048, "bytes"),
        enforcement_status=ResourceEnforcementStatus.EXTERNAL_ENFORCED,
        terminated_execution=True,
        breached=True,
        upstream_fact_reference=OpaqueReference("resource-fact:memory:breach"),
    )


def test_valid_compile_success_evidence() -> None:
    evidence = compile_evidence()

    assert evidence.execution_phase is ExecutionPhase.COMPILE
    assert evidence.compile_result.status is CompileStatus.SUCCESS
    assert evidence.test_result is None
    assert evidence.stdout_artefact.artefact_type is ArtefactType.COMPILE_LOG
    assert evidence.stderr_artefact.artefact_type is ArtefactType.COMPILE_LOG


@pytest.mark.parametrize(
    "changes",
    [
        {
            "stdout_artefact": artefact(
                "artefact:compile-stdout:test-type", ArtefactType.TEST_STDOUT
            )
        },
        {
            "stderr_artefact": artefact(
                "artefact:compile-stderr:test-type", ArtefactType.TEST_STDERR
            )
        },
        {
            "stdout_artefact": artefact(
                "artefact:compile-stdout:test-type", ArtefactType.TEST_STDOUT
            ),
            "stderr_artefact": artefact(
                "artefact:compile-stderr:test-type", ArtefactType.TEST_STDERR
            ),
        },
    ],
)
def test_complete_compile_rejects_available_verified_test_phase_output_types(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ValueError, match="COMPILE_LOG"):
        compile_evidence(**changes)


@pytest.mark.parametrize(
    "phase",
    [
        ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST,
        ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST,
    ],
)
@pytest.mark.parametrize(
    "changes",
    [
        {
            "stdout_artefact": artefact(
                "artefact:test-stdout:compile-type", ArtefactType.COMPILE_LOG
            )
        },
        {
            "stderr_artefact": artefact(
                "artefact:test-stderr:compile-type", ArtefactType.COMPILE_LOG
            )
        },
    ],
)
def test_test_phases_reject_non_test_output_artefact_types(
    phase: ExecutionPhase,
    changes: dict[str, object],
) -> None:
    with pytest.raises(ValueError, match="TEST_STDOUT|TEST_STDERR"):
        make_test_evidence(execution_phase=phase, **changes)


def test_valid_compile_failure_evidence_can_be_complete() -> None:
    evidence = compile_evidence(
        outcome=ExecutionOutcome.COMPILATION_FAILURE,
        process_exit=ProcessExit(exit_code=1),
        compile_result=CompileResult(
            CompileStatus.FAILURE,
            error_count=2,
            warning_count=1,
        ),
        failure=failure(FailureCategory.COMPILATION_FAILURE),
    )

    assert evidence.completeness is EvidenceCompleteness.COMPLETE
    assert evidence.failure.category is FailureCategory.COMPILATION_FAILURE
    assert evidence.compile_result.error_count == 2
    assert evidence.compile_result.warning_count == 1


def test_valid_buggy_or_target_revision_test_evidence() -> None:
    failed = ExecutionTestCaseResult(
        OpaqueReference("test:failing"),
        ExecutionTestCaseStatus.FAILED,
        OpaqueReference("test-failure:failing"),
    )
    evidence = make_test_evidence(
        outcome=ExecutionOutcome.TEST_FAILURE,
        process_exit=ProcessExit(exit_code=1),
        test_result=ExecutionTestResult(
            executed_count=2,
            passed_count=1,
            failed_count=1,
            skipped_count=0,
            errored_count=0,
            test_cases=(failed, passed_case()),
        ),
        failure=failure(FailureCategory.TEST_FAILURE),
    )

    assert evidence.source_revision == OpaqueReference("revision:buggy:abc123")
    assert evidence.test_result.test_cases[0].test_reference.value == "test:example"
    assert (
        evidence.test_result.test_cases[1].status
        is ExecutionTestCaseStatus.FAILED
    )


def test_valid_fixed_or_reference_revision_test_evidence() -> None:
    evidence = make_test_evidence(
        execution_evidence_id=ExecutionEvidenceId("evidence:test:fixed:1"),
        producer_result_id=ProducerResultId("producer:test:fixed:1"),
        execution_phase=ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST,
        source_revision=OpaqueReference("revision:fixed:def456"),
    )

    assert evidence.execution_phase is ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST
    assert evidence.source_revision == OpaqueReference("revision:fixed:def456")


@pytest.mark.parametrize(
    ("outcome", "category", "resources", "timeout"),
    [
        (
            ExecutionOutcome.TIMEOUT,
            FailureCategory.TIMEOUT,
            (),
            TimeoutMetadata(
                timed_out=True,
                classification=OpaqueReference("timeout:wall-clock"),
                configured_limit=timedelta(seconds=30),
                upstream_fact_reference=OpaqueReference("timeout-fact:1"),
            ),
        ),
        (
            ExecutionOutcome.CANCELLATION,
            FailureCategory.CANCELLATION,
            (),
            TimeoutMetadata(timed_out=False),
        ),
        (
            ExecutionOutcome.RESOURCE_BREACH,
            FailureCategory.RESOURCE_BREACH,
            (resource_breach(),),
            TimeoutMetadata(timed_out=False),
        ),
        (
            ExecutionOutcome.RUNNER_ERROR,
            FailureCategory.RUNNER_ERROR,
            (),
            TimeoutMetadata(timed_out=False),
        ),
    ],
)
def test_distinct_execution_failure_representations(
    outcome: ExecutionOutcome,
    category: FailureCategory,
    resources: tuple[ResourceObservation, ...],
    timeout: TimeoutMetadata,
) -> None:
    evidence = make_test_evidence(
        outcome=outcome,
        process_exit=ProcessExit(upstream_fact_reference=OpaqueReference("process-exit:1")),
        test_result=ExecutionTestResult(test_cases=()),
        failure=failure(category),
        resource_observations=resources,
        timeout_metadata=timeout,
    )

    assert evidence.outcome is outcome
    assert evidence.failure.category is category
    assert evidence.timeout_metadata.timed_out is (outcome is ExecutionOutcome.TIMEOUT)


def test_timeout_threshold_and_classification_are_retained() -> None:
    timeout = TimeoutMetadata(
        timed_out=True,
        classification=OpaqueReference("timeout:supervisor-wall-clock"),
        configured_limit=timedelta(milliseconds=1500),
        upstream_fact_reference=OpaqueReference("timeout-fact:42"),
    )
    evidence = make_test_evidence(
        outcome=ExecutionOutcome.TIMEOUT,
        test_result=ExecutionTestResult(test_cases=()),
        process_exit=ProcessExit(signal_number=9, signal_name="SIGKILL"),
        failure=failure(FailureCategory.TIMEOUT),
        timeout_metadata=timeout,
    )

    assert evidence.timeout_metadata == timeout
    assert evidence.timeout_metadata.configured_limit == timedelta(milliseconds=1500)
    assert evidence.process_exit.signal_name == "SIGKILL"


def test_execution_timing_is_retained_and_serialized() -> None:
    evidence = compile_evidence()

    assert evidence.execution_timing.started_at == STARTED_AT
    assert evidence.execution_timing.duration == timedelta(seconds=3)
    assert '"duration":3000000' in evidence.to_domain_json()


def test_bounded_execution_metadata_references_are_retained() -> None:
    evidence = compile_evidence(
        flake_indication_reference=OpaqueReference("flake-indication:1")
    )

    assert evidence.runtime_metadata_reference.value == "runtime-fact:compile:1"
    assert evidence.sandbox_metadata_reference.value == "sandbox-fact:compile:1"
    assert (
        evidence.environment_metadata_reference.value
        == "environment-fact:compile:1"
    )
    assert evidence.flake_indication_reference.value == "flake-indication:1"


@pytest.mark.parametrize(
    "timing",
    [
        ExecutionTiming(duration=timedelta(0)),
        ExecutionTiming(started_at=STARTED_AT),
        ExecutionTiming(ended_at=ENDED_AT),
    ],
)
def test_complete_evidence_requires_complete_timing(timing: ExecutionTiming) -> None:
    with pytest.raises(ValueError, match="complete execution timing"):
        compile_evidence(execution_timing=timing)


def test_invalid_or_contradictory_timing_fails_closed() -> None:
    with pytest.raises(ValueError, match="must not be negative"):
        ExecutionTiming(duration=timedelta(microseconds=-1))
    with pytest.raises(ValueError, match="contradicts"):
        ExecutionTiming(
            started_at=STARTED_AT,
            ended_at=ENDED_AT,
            duration=timedelta(seconds=4),
        )
    with pytest.raises(ValueError, match="must not precede"):
        ExecutionTiming(started_at=ENDED_AT, ended_at=STARTED_AT)
    with pytest.raises(ValueError, match="timezone-aware"):
        ExecutionTiming(started_at=datetime(2026, 8, 12, 8, 0))


def test_invalid_timeout_metadata_fails_closed() -> None:
    with pytest.raises(ValueError, match="explicit classification"):
        TimeoutMetadata(timed_out=True)
    with pytest.raises(ValueError, match="must not be negative"):
        TimeoutMetadata(timed_out=False, configured_limit=timedelta(seconds=-1))


def test_complete_evidence_requires_timeout_occurrence_metadata() -> None:
    with pytest.raises(ValueError, match="timeout occurrence metadata"):
        compile_evidence(timeout_metadata=None)


def test_configured_resource_is_not_represented_as_enforced() -> None:
    observation = ResourceObservation(
        category=ResourceCategory.CPU_TIME,
        configured_value=ResourceValue(10, "seconds"),
        enforcement_status=ResourceEnforcementStatus.NOT_ENFORCED,
        terminated_execution=False,
        upstream_fact_reference=OpaqueReference("resource-fact:cpu:1"),
    )
    evidence = compile_evidence(resource_observations=[observation])

    assert observation.configured_value is not None
    assert observation.enforcement_status is ResourceEnforcementStatus.NOT_ENFORCED
    assert evidence.resource_observations == (observation,)


def test_identity_types_are_distinct_and_equal_raw_values_fail_closed() -> None:
    assert ProducerResultId("same") != ExecutionEvidenceId("same")
    assert WorkflowAttemptId("same") != ExecutionEvidenceId("same")

    with pytest.raises(ValueError, match="distinct from every external identity"):
        compile_evidence(producer_result_id=ProducerResultId("evidence:compile:1"))
    with pytest.raises(ValueError, match="distinct from every external identity"):
        compile_evidence(workflow_attempt_id=WorkflowAttemptId("evidence:compile:1"))


def test_queue_message_id_cannot_substitute_for_execution_evidence_id() -> None:
    with pytest.raises(TypeError, match="execution_evidence_id"):
        compile_evidence(execution_evidence_id=QueueMessageId("queue-message:substitute"))


@pytest.mark.parametrize(
    "missing",
    [
        "producer_result_id",
        "workflow_attempt_id",
        "candidate_version_id",
        "command_reference",
        "execution_fact_reference",
    ],
)
def test_missing_required_provenance_fails_validation(missing: str) -> None:
    with pytest.raises(TypeError, match=missing):
        compile_evidence(**{missing: None})


@pytest.mark.parametrize(
    "phase",
    [
        ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST,
        ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST,
    ],
)
def test_test_phase_without_source_revision_fails_closed(phase: ExecutionPhase) -> None:
    with pytest.raises(ValueError, match="source_revision"):
        make_test_evidence(execution_phase=phase, source_revision=None)


@pytest.mark.parametrize("invalid", ["", "   "])
def test_empty_test_source_revision_is_rejected(invalid: str) -> None:
    with pytest.raises(ValueError, match="nonempty"):
        OpaqueReference(invalid)


@pytest.mark.parametrize(
    "phase",
    [
        ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST,
        ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST,
    ],
)
@pytest.mark.parametrize("invalid", ["", "   "])
def test_test_phase_rejects_invalid_raw_source_revision(
    phase: ExecutionPhase,
    invalid: str,
) -> None:
    with pytest.raises(TypeError, match="source_revision"):
        make_test_evidence(execution_phase=phase, source_revision=invalid)


def test_compile_does_not_unnecessarily_require_source_revision() -> None:
    evidence = compile_evidence(source_revision=None)

    assert evidence.source_revision is None


def test_evidence_and_nested_collections_are_immutable() -> None:
    observations = [resource_observation(ResourceCategory.STDOUT_BYTES, 1024, 100)]
    evidence = compile_evidence(resource_observations=observations)
    observations.clear()

    with pytest.raises(FrozenInstanceError):
        evidence.outcome = ExecutionOutcome.RUNNER_ERROR  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        evidence.resource_observations[0].breached = True  # type: ignore[misc]
    assert len(evidence.resource_observations) == 1
    assert isinstance(evidence.resource_observations, tuple)


def test_resource_collection_reversed_order_serializes_identically() -> None:
    memory = resource_observation(ResourceCategory.MEMORY_BYTES, 100, 50)
    cpu = resource_observation(ResourceCategory.CPU_TIME, 10, 5)
    first = compile_evidence(resource_observations=(memory, cpu))
    second = compile_evidence(resource_observations=(cpu, memory))

    assert first.to_domain_json() == second.to_domain_json()
    assert first.resource_observations == second.resource_observations


def test_artefact_collection_reversed_order_serializes_identically() -> None:
    xml = artefact("artefact:report:xml", ArtefactType.CUSTOM_OUTPUT)
    trace = artefact("artefact:trace:json", ArtefactType.EXECUTION_LOG)
    first = compile_evidence(output_artefacts=(xml, trace))
    second = compile_evidence(output_artefacts=(trace, xml))

    assert first.to_domain_json() == second.to_domain_json()
    assert compare_execution_evidence(first, second) is EvidenceComparison.EQUIVALENT


def test_diagnostic_artefact_reversed_order_is_semantically_equivalent() -> None:
    one = artefact("artefact:diagnostic:1", ArtefactType.COMPILE_LOG)
    two = artefact("artefact:diagnostic:2", ArtefactType.COMPILE_LOG)
    first = compile_evidence(
        compile_result=CompileResult(
            CompileStatus.SUCCESS,
            error_count=0,
            diagnostic_artefacts=(one, two),
        )
    )
    second = compile_evidence(
        compile_result=CompileResult(
            CompileStatus.SUCCESS,
            error_count=0,
            diagnostic_artefacts=(two, one),
        )
    )

    assert compare_execution_evidence(first, second) is EvidenceComparison.EQUIVALENT


def test_same_identity_with_different_semantic_content_is_conflicting() -> None:
    existing = compile_evidence()
    incoming = replace(existing, source_revision=OpaqueReference("revision:different"))

    assert compare_execution_evidence(existing, incoming) is EvidenceComparison.CONFLICTING


def test_stdout_and_stderr_references_are_retained_without_raw_bytes() -> None:
    evidence = compile_evidence()
    domain = evidence.to_domain_dict()

    assert evidence.stdout_artefact.artefact_id == ArtefactId(
        "artefact:compile-stdout:1"
    )
    assert evidence.stderr_artefact.artefact_id == ArtefactId(
        "artefact:compile-stderr:1"
    )
    assert "stdout" not in domain
    assert "stderr" not in domain


@pytest.mark.parametrize("missing", ["stdout_artefact", "stderr_artefact"])
def test_complete_without_required_output_artefact_fails(missing: str) -> None:
    with pytest.raises(ValueError, match="stdout and stderr"):
        compile_evidence(**{missing: None})


def test_complete_with_unavailable_required_artefact_fails() -> None:
    unavailable = artefact(
        "artefact:compile-stdout:unavailable",
        ArtefactType.COMPILE_LOG,
        availability=EvidenceAvailability.UNAVAILABLE,
    )
    with pytest.raises(ValueError, match="unavailable artefacts"):
        compile_evidence(stdout_artefact=unavailable)


def test_complete_with_unverified_required_artefact_fails() -> None:
    unverified = artefact(
        "artefact:compile-stderr:unverified",
        ArtefactType.COMPILE_LOG,
        integrity_state=EvidenceIntegrityState.UNVERIFIABLE,
    )
    with pytest.raises(ValueError, match="unverified artefacts"):
        compile_evidence(stderr_artefact=unverified)


def test_complete_with_unverified_execution_integrity_fails() -> None:
    with pytest.raises(ValueError, match="verified execution integrity"):
        compile_evidence(
            execution_integrity=IntegrityMetadata(
                EvidenceIntegrityState.UNVERIFIABLE,
                OpaqueReference("integrity-observation:execution"),
            )
        )


def test_duplicate_log_artefact_identity_fails_closed() -> None:
    duplicate = artefact("artefact:duplicate-log:1", ArtefactType.COMPILE_LOG)
    with pytest.raises(ValueError, match="distinct logical identities"):
        compile_evidence(stdout_artefact=duplicate, stderr_artefact=duplicate)


def test_complete_failed_execution_is_valid_when_required_evidence_is_verified() -> None:
    failed_case = ExecutionTestCaseResult(
        OpaqueReference("test:failed"),
        ExecutionTestCaseStatus.FAILED,
        OpaqueReference("failure:test:failed"),
    )
    evidence = make_test_evidence(
        outcome=ExecutionOutcome.TEST_FAILURE,
        process_exit=ProcessExit(exit_code=1),
        test_result=ExecutionTestResult(
            executed_count=1,
            passed_count=0,
            failed_count=1,
            skipped_count=0,
            errored_count=0,
            test_cases=(failed_case,),
        ),
        failure=failure(FailureCategory.TEST_FAILURE),
    )

    assert evidence.completeness is EvidenceCompleteness.COMPLETE
    assert evidence.outcome is ExecutionOutcome.TEST_FAILURE


def test_unavailable_artefact_does_not_turn_execution_into_failure() -> None:
    unavailable_log = artefact(
        "artefact:additional-log:1",
        ArtefactType.EXECUTION_LOG,
        availability=EvidenceAvailability.UNAVAILABLE,
        integrity_state=EvidenceIntegrityState.MISSING,
    )
    evidence = compile_evidence(
        completeness=EvidenceCompleteness.PARTIAL,
        output_artefacts=[unavailable_log],
    )

    assert evidence.outcome is ExecutionOutcome.SUCCESS
    assert evidence.output_artefacts[0].availability is EvidenceAvailability.UNAVAILABLE
    assert evidence.output_artefacts[0].integrity.state is EvidenceIntegrityState.MISSING


@pytest.mark.parametrize(
    "locator",
    [
        "logs/stdout.txt",
        "./logs/stdout.txt",
        "../logs/stdout.txt",
        "/tmp/stdout.txt",
        r"logs\stdout.txt",
        "s3://bucket/item",
        "https://example.test/item",
    ],
)
def test_artefact_identity_cannot_be_a_storage_locator(locator: str) -> None:
    with pytest.raises(ValueError, match="storage locator"):
        ArtefactId(locator)


@pytest.mark.parametrize(
    "identity",
    ["artefact:stdout:01", "artifact_01.test+v2@example", "A-1"],
)
def test_valid_opaque_artefact_ids(identity: str) -> None:
    assert ArtefactId(identity).value == identity


def test_compile_structured_facts_are_retained_without_fabricating_counts() -> None:
    supplied = CompileResult(
        CompileStatus.FAILURE,
        error_count=7,
        warning_count=3,
        compiler_metadata_reference=OpaqueReference("build-metadata:7"),
        diagnostic_artefacts=(
            artefact("artefact:compiler-diagnostics:7", ArtefactType.COMPILE_LOG),
        ),
    )
    evidence = compile_evidence(
        outcome=ExecutionOutcome.COMPILATION_FAILURE,
        process_exit=ProcessExit(exit_code=2),
        compile_result=supplied,
        failure=failure(FailureCategory.COMPILATION_FAILURE),
    )

    assert evidence.compile_result == supplied
    assert CompileResult(CompileStatus.FAILURE).error_count is None


def test_compile_status_and_outcome_cannot_contradict() -> None:
    with pytest.raises(ValueError, match="compile status contradicts"):
        compile_evidence(compile_result=CompileResult(CompileStatus.FAILURE))
    with pytest.raises(ValueError, match="cannot contain errors"):
        CompileResult(CompileStatus.SUCCESS, error_count=1)


def test_individual_test_case_statuses_are_retained_and_normalized() -> None:
    passed = passed_case("test:z")
    skipped = ExecutionTestCaseResult(
        OpaqueReference("test:a"), ExecutionTestCaseStatus.SKIPPED
    )
    result = ExecutionTestResult(
        executed_count=2,
        passed_count=1,
        failed_count=0,
        skipped_count=1,
        errored_count=0,
        test_cases=(passed, skipped),
    )
    evidence = make_test_evidence(test_result=result)

    assert [case.test_reference.value for case in evidence.test_result.test_cases] == [
        "test:a",
        "test:z",
    ]
    assert (
        evidence.test_result.test_cases[0].status
        is ExecutionTestCaseStatus.SKIPPED
    )


def test_aggregate_only_test_results_do_not_manufacture_cases() -> None:
    evidence = make_test_evidence(
        completeness=EvidenceCompleteness.PARTIAL,
        test_result=ExecutionTestResult(executed_count=5, failed_count=2),
        outcome=ExecutionOutcome.TEST_FAILURE,
        process_exit=ProcessExit(exit_code=1),
        failure=failure(FailureCategory.TEST_FAILURE),
    )

    assert evidence.test_result.test_cases is None
    assert evidence.test_result.passed_count is None


def test_complete_test_evidence_requires_individual_cases() -> None:
    with pytest.raises(ValueError, match="individual test case facts"):
        make_test_evidence(
            test_result=ExecutionTestResult(executed_count=1, passed_count=1)
        )


def test_contradictory_test_counts_and_cases_fail_closed() -> None:
    with pytest.raises(ValueError, match="passed count contradicts"):
        ExecutionTestResult(
            executed_count=1,
            passed_count=0,
            test_cases=(passed_case(),),
        )


def test_secondary_failures_are_normalized_without_losing_attribution() -> None:
    secondary = (
        failure(FailureCategory.RUNNER_ERROR, "secondary-1"),
        failure(FailureCategory.RESOURCE_BREACH, "secondary-2"),
    )
    evidence = make_test_evidence(
        outcome=ExecutionOutcome.TIMEOUT,
        process_exit=ProcessExit(signal_number=9),
        test_result=ExecutionTestResult(test_cases=()),
        timeout_metadata=TimeoutMetadata(
            timed_out=True,
            classification=OpaqueReference("timeout:wall-clock"),
        ),
        failure=failure(FailureCategory.TIMEOUT),
        secondary_failures=secondary,
    )

    assert evidence.failure.category is FailureCategory.TIMEOUT
    assert {
        (item.category, item.upstream_failure_reference.value)
        for item in evidence.secondary_failures
    } == {
        (
            FailureCategory.RUNNER_ERROR,
            "execution-failure:runner_error:secondary-1",
        ),
        (
            FailureCategory.RESOURCE_BREACH,
            "execution-failure:resource_breach:secondary-2",
        ),
    }

    reordered = replace(evidence, secondary_failures=tuple(reversed(secondary)))
    assert evidence.to_domain_json() == reordered.to_domain_json()
    assert (
        compare_execution_evidence(evidence, reordered)
        is EvidenceComparison.EQUIVALENT
    )


def test_secondary_failure_duplicates_are_retained() -> None:
    duplicate = failure(FailureCategory.RUNNER_ERROR, "duplicate")
    evidence = make_test_evidence(
        outcome=ExecutionOutcome.TIMEOUT,
        process_exit=ProcessExit(signal_number=9),
        test_result=ExecutionTestResult(test_cases=()),
        timeout_metadata=TimeoutMetadata(
            timed_out=True,
            classification=OpaqueReference("timeout:wall-clock"),
        ),
        failure=failure(FailureCategory.TIMEOUT),
        secondary_failures=(duplicate, duplicate),
    )

    assert evidence.secondary_failures == (duplicate, duplicate)


def test_changed_secondary_failure_content_is_conflicting() -> None:
    evidence = make_test_evidence(
        outcome=ExecutionOutcome.TIMEOUT,
        process_exit=ProcessExit(signal_number=9),
        test_result=ExecutionTestResult(test_cases=()),
        timeout_metadata=TimeoutMetadata(
            timed_out=True,
            classification=OpaqueReference("timeout:wall-clock"),
        ),
        failure=failure(FailureCategory.TIMEOUT),
        secondary_failures=(
            failure(FailureCategory.RESOURCE_BREACH, "secondary-2"),
        ),
    )
    changed = replace(
        evidence,
        secondary_failures=(
            FailureEvidence(
                FailureCategory.RESOURCE_BREACH,
                OpaqueReference("execution-failure:resource_breach:changed"),
            ),
        ),
    )

    assert (
        compare_execution_evidence(evidence, changed)
        is EvidenceComparison.CONFLICTING
    )


def test_phase_specific_results_cannot_collapse() -> None:
    with pytest.raises(ValueError, match="requires only compile_result"):
        compile_evidence(test_result=ExecutionTestResult())
    with pytest.raises(ValueError, match="test phases require only test_result"):
        make_test_evidence(compile_result=CompileResult(CompileStatus.SUCCESS))


@pytest.mark.parametrize(
    "outcome",
    [ExecutionOutcome.UNAVAILABLE, ExecutionOutcome.NOT_RUN],
)
def test_unavailable_and_not_run_are_explicit_nonfailure_outcomes(
    outcome: ExecutionOutcome,
) -> None:
    evidence = compile_evidence(
        outcome=outcome,
        completeness=EvidenceCompleteness.UNAVAILABLE,
        compile_result=CompileResult(CompileStatus.NOT_COMPLETED),
        process_exit=None,
        failure=None,
    )

    assert evidence.outcome is outcome
    assert evidence.failure is None


def test_impossible_complete_unavailable_evidence_is_rejected() -> None:
    with pytest.raises(ValueError, match="cannot be COMPLETE"):
        compile_evidence(
            outcome=ExecutionOutcome.UNAVAILABLE,
            compile_result=CompileResult(CompileStatus.NOT_COMPLETED),
            process_exit=None,
        )


def test_timeout_outcome_requires_explicit_timeout_metadata() -> None:
    with pytest.raises(ValueError, match="explicit timeout metadata"):
        make_test_evidence(
            outcome=ExecutionOutcome.TIMEOUT,
            completeness=EvidenceCompleteness.PARTIAL,
            test_result=ExecutionTestResult(),
            process_exit=None,
            timeout_metadata=None,
            failure=failure(FailureCategory.TIMEOUT),
        )


def test_verified_integrity_requires_independent_reference() -> None:
    with pytest.raises(ValueError, match="verification reference"):
        IntegrityMetadata(EvidenceIntegrityState.VERIFIED)


def test_integrity_state_vocabulary_is_exact() -> None:
    assert {state.value for state in EvidenceIntegrityState} == {
        "VERIFIED",
        "UNVERIFIABLE",
        "CORRUPT",
        "TAMPERED",
        "MISSING",
        "DELETED",
    }


def test_empty_process_exit_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least one supplied fact"):
        ProcessExit()
