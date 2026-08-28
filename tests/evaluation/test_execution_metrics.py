"""Adversarial tests for exact execution-outcome measurements."""

import hashlib
import inspect
import typing
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from pathlib import Path

import pytest

import evaluation.execution_metrics as execution_metrics
from app.evidence import (
    ArtefactId,
    ArtefactReference,
    ArtefactType,
    CandidatePatchId,
    CandidateVersionId,
    CompileResult,
    CompileStatus,
    EvidenceAvailability,
    EvidenceBundle,
    EvidenceBundleId,
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
)
from evaluation.defects4j_manifest import MANIFEST_VERSION, verify_file
from evaluation.execution_metrics import (
    ExactRate,
    ExecutionCaseMeasurement,
    ExecutionMetricError,
    ExecutionMetricErrorCode,
    ExecutionMetricObservation,
    ExecutionMetricsAggregate,
    MeasurementState,
    aggregate_execution_metrics,
    measure_execution_observation,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "benchmarks/defects4j/DEFECTS4J_MVP_V1.json"
LOCALISATION = REPO_ROOT / "evaluation/localisation_metrics.py"
STARTED_AT = datetime(2026, 8, 27, 8, 0, tzinfo=timezone.utc)
ENDED_AT = STARTED_AT + timedelta(seconds=1)
_CANONICAL = object()


def revision_pair(case: str) -> tuple[str, str]:
    manifest_case = next(
        value
        for value in verify_file(MANIFEST)["cases"]
        if value["benchmark_case_id"] == case
    )
    return (
        manifest_case["buggy_revision"]["defects4j_version_id"],
        manifest_case["fixed_revision"]["defects4j_version_id"],
    )


def integrity(state: EvidenceIntegrityState, suffix: str) -> IntegrityMetadata:
    return IntegrityMetadata(state, OpaqueReference(f"integrity:{suffix}"))


def artefact(identity: str, kind: ArtefactType) -> ArtefactReference:
    return ArtefactReference(
        artefact_id=ArtefactId(identity),
        artefact_type=kind,
        availability=EvidenceAvailability.AVAILABLE,
        integrity=integrity(EvidenceIntegrityState.VERIFIED, identity),
        content_digest=OpaqueReference(f"digest:{identity}"),
        digest_algorithm=OpaqueReference("sha256"),
        byte_size=1,
        media_type="text/plain",
        producer_id=OpaqueReference("producer:runner"),
        creation_timestamp=STARTED_AT,
        storage_locator=f"store:{identity}",
    )


def timing() -> ExecutionTiming:
    return ExecutionTiming(
        started_at=STARTED_AT,
        ended_at=ENDED_AT,
        duration=timedelta(seconds=1),
        upstream_fact_reference=OpaqueReference("timing:fact"),
    )


def passed_result() -> ExecutionTestResult:
    return ExecutionTestResult(
        executed_count=1,
        passed_count=1,
        failed_count=0,
        skipped_count=0,
        errored_count=0,
        test_cases=(
            ExecutionTestCaseResult(
                OpaqueReference("test:example"), ExecutionTestCaseStatus.PASSED
            ),
        ),
    )


def failed_result() -> ExecutionTestResult:
    return ExecutionTestResult(
        executed_count=1,
        passed_count=0,
        failed_count=1,
        skipped_count=0,
        errored_count=0,
        test_cases=(
            ExecutionTestCaseResult(
                OpaqueReference("test:example"),
                ExecutionTestCaseStatus.FAILED,
                OpaqueReference("failure:test:example"),
            ),
        ),
    )


_FAILURE_CATEGORY = {
    ExecutionOutcome.COMPILATION_FAILURE: FailureCategory.COMPILATION_FAILURE,
    ExecutionOutcome.TEST_FAILURE: FailureCategory.TEST_FAILURE,
    ExecutionOutcome.TIMEOUT: FailureCategory.TIMEOUT,
    ExecutionOutcome.CANCELLATION: FailureCategory.CANCELLATION,
    ExecutionOutcome.RESOURCE_BREACH: FailureCategory.RESOURCE_BREACH,
    ExecutionOutcome.RUNNER_ERROR: FailureCategory.RUNNER_ERROR,
}


def record(
    phase: ExecutionPhase,
    outcome: ExecutionOutcome,
    *,
    run: str = "run:1",
    completeness: EvidenceCompleteness = EvidenceCompleteness.COMPLETE,
    integrity_state: EvidenceIntegrityState | None = EvidenceIntegrityState.VERIFIED,
    source_revision: OpaqueReference | None = None,
    evidence_id: str | None = None,
) -> ExecutionEvidence:
    phase_name = phase.value.lower()
    compile_result = None
    test_result = None
    if phase is ExecutionPhase.COMPILE:
        compile_result = CompileResult(
            {
                ExecutionOutcome.SUCCESS: CompileStatus.SUCCESS,
                ExecutionOutcome.COMPILATION_FAILURE: CompileStatus.FAILURE,
            }.get(outcome, CompileStatus.NOT_COMPLETED),
            error_count=1 if outcome is ExecutionOutcome.COMPILATION_FAILURE else 0,
        )
        stdout_kind = stderr_kind = ArtefactType.COMPILE_LOG
    else:
        test_result = (
            failed_result()
            if outcome is ExecutionOutcome.TEST_FAILURE
            else passed_result()
            if outcome is ExecutionOutcome.SUCCESS
            else ExecutionTestResult(
                executed_count=0,
                passed_count=0,
                failed_count=0,
                skipped_count=0,
                errored_count=0,
                test_cases=(),
            )
        )
        source_revision = source_revision or (
            OpaqueReference("1b")
            if phase is ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST
            else OpaqueReference("1f")
        )
        stdout_kind, stderr_kind = ArtefactType.TEST_STDOUT, ArtefactType.TEST_STDERR

    failure_category = _FAILURE_CATEGORY.get(outcome)
    timeout = TimeoutMetadata(
        timed_out=outcome is ExecutionOutcome.TIMEOUT,
        classification=(
            OpaqueReference("timeout:wall-clock")
            if outcome is ExecutionOutcome.TIMEOUT
            else None
        ),
    )
    resources = (
        (
            ResourceObservation(
                category=ResourceCategory.MEMORY_BYTES,
                enforcement_status=ResourceEnforcementStatus.EXTERNAL_ENFORCED,
                terminated_execution=True,
                configured_value=ResourceValue(1, "bytes"),
                observed_value=ResourceValue(2, "bytes"),
                breached=True,
                upstream_fact_reference=OpaqueReference("resource:fact"),
            ),
        )
        if outcome is ExecutionOutcome.RESOURCE_BREACH
        else ()
    )
    return ExecutionEvidence(
        execution_evidence_id=ExecutionEvidenceId(
            evidence_id or f"evidence:{phase_name}:{run}"
        ),
        producer_result_id=ProducerResultId(f"result:{phase_name}:{run}"),
        workflow_attempt_id=WorkflowAttemptId(f"attempt:{run}"),
        candidate_version_id=CandidateVersionId(f"candidate:{run}"),
        execution_phase=phase,
        outcome=outcome,
        completeness=completeness,
        command_reference=OpaqueReference(f"command:{phase_name}"),
        execution_fact_reference=OpaqueReference(f"fact:{phase_name}"),
        compile_result=compile_result,
        test_result=test_result,
        run_id=RunId(run),
        source_revision=source_revision,
        execution_timing=timing(),
        timeout_metadata=timeout,
        process_exit=ProcessExit(
            exit_code=0,
            upstream_fact_reference=OpaqueReference(f"exit:{phase_name}"),
        ),
        stdout_artefact=artefact(f"artefact:{phase_name}:stdout:{run}", stdout_kind),
        stderr_artefact=artefact(f"artefact:{phase_name}:stderr:{run}", stderr_kind),
        execution_integrity=(
            None
            if integrity_state is None
            else integrity(integrity_state, f"execution:{phase_name}:{run}")
        ),
        failure=(
            None
            if failure_category is None
            else FailureEvidence(
                failure_category, OpaqueReference(f"failure:{outcome.value.lower()}")
            )
        ),
        resource_observations=resources,
    )


def bundle(
    *,
    case: str | None = "D4J-LANG-001",
    version: str | None = MANIFEST_VERSION,
    run: str = "run:1",
    records: tuple[ExecutionEvidence, ...] | None = None,
    bundle_id: str | None = None,
    completeness: EvidenceCompleteness = EvidenceCompleteness.PARTIAL,
    bundle_integrity: EvidenceIntegrityState | None = None,
    source_revision: object = _CANONICAL,
    target_reference_revision: object = _CANONICAL,
) -> EvidenceBundle:
    assert case is None or isinstance(case, str)
    try:
        canonical_buggy, canonical_fixed = revision_pair(case or "D4J-LANG-001")
    except StopIteration:
        canonical_buggy, canonical_fixed = "1b", "1f"
    source = (
        OpaqueReference(canonical_buggy)
        if source_revision is _CANONICAL
        else OpaqueReference(source_revision)
    )
    target = (
        OpaqueReference(canonical_fixed)
        if target_reference_revision is _CANONICAL
        else None
        if target_reference_revision is None
        else OpaqueReference(target_reference_revision)
    )
    if records is None:
        records = (
            record(ExecutionPhase.COMPILE, ExecutionOutcome.SUCCESS, run=run),
            record(
                ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST,
                ExecutionOutcome.TEST_FAILURE,
                run=run,
                source_revision=source,
            ),
            record(
                ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST,
                ExecutionOutcome.SUCCESS,
                run=run,
                source_revision=target,
            ),
        )
    return EvidenceBundle(
        evidence_bundle_id=EvidenceBundleId(
            bundle_id or f"bundle:{run}:{case or 'unbound'}"
        ),
        candidate_patch_id=CandidatePatchId(f"patch:{run}"),
        candidate_version_id=CandidateVersionId(f"candidate:{run}"),
        completeness=completeness,
        run_id=RunId(run),
        run_request_id=OpaqueReference(f"request:{run}"),
        workflow_attempt_id=WorkflowAttemptId(f"attempt:{run}"),
        workflow_step=OpaqueReference("step:evaluate"),
        producer_id=OpaqueReference("producer:runner"),
        runner_id=OpaqueReference("runner:1"),
        source_repository=OpaqueReference("repository:testgap"),
        source_revision=source,
        selected_context_manifest=OpaqueReference("context:1"),
        configuration_version=OpaqueReference("config:1"),
        model_identifier=OpaqueReference("model:1"),
        prompt_template_version=OpaqueReference("prompt:1"),
        producer_schema_version=OpaqueReference("schema:1"),
        execution_evidence=records,
        integrity_metadata=(
            None
            if bundle_integrity is None
            else integrity(bundle_integrity, f"bundle:{run}")
        ),
        target_reference_revision=target,
        evaluation_benchmark_case_reference=(
            None if case is None else OpaqueReference(case)
        ),
        evaluation_benchmark_manifest_version=(
            None if version is None else OpaqueReference(version)
        ),
    )


def observation(**changes: object) -> ExecutionMetricObservation:
    return ExecutionMetricObservation(bundle(**changes))


def assert_metric_error(code: ExecutionMetricErrorCode, operation: object) -> None:
    assert callable(operation)
    with pytest.raises(ExecutionMetricError) as raised:
        operation()
    assert raised.value.code is code


def test_all_required_positive_criteria_derive_from_bundle() -> None:
    value = observation()
    result = measure_execution_observation(value)
    assert result == ExecutionCaseMeasurement(value.evidence_bundle)
    assert (
        result.benchmark_case_id,
        result.run_id,
        result.compile_success,
        result.buggy_failure,
        result.fixed_reference_pass,
        result.regression_proof,
    ) == (
        "D4J-LANG-001",
        RunId("run:1"),
        MeasurementState.PROVEN,
        MeasurementState.PROVEN,
        MeasurementState.PROVEN,
        MeasurementState.PROVEN,
    )
    aggregate = aggregate_execution_metrics((value,))
    assert all(
        rate.score == Fraction(1, 1)
        for rate in (
            aggregate.compile_success_rate,
            aggregate.fail_on_buggy_rate,
            aggregate.pass_on_fixed_reference_rate,
            aggregate.regression_proof_rate,
        )
    )


def test_complete_negative_phase_facts_are_not_proven() -> None:
    value = observation(
        records=(
            record(ExecutionPhase.COMPILE, ExecutionOutcome.COMPILATION_FAILURE),
            record(
                ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST,
                ExecutionOutcome.SUCCESS,
            ),
            record(
                ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST,
                ExecutionOutcome.TEST_FAILURE,
            ),
        )
    )
    result = measure_execution_observation(value)
    assert (
        result.compile_success,
        result.buggy_failure,
        result.fixed_reference_pass,
        result.regression_proof,
    ) == (MeasurementState.NOT_PROVEN,) * 4


@pytest.mark.parametrize(
    "outcome",
    [
        ExecutionOutcome.TIMEOUT,
        ExecutionOutcome.CANCELLATION,
        ExecutionOutcome.RESOURCE_BREACH,
        ExecutionOutcome.RUNNER_ERROR,
    ],
)
def test_operational_failures_never_become_buggy_or_fixed_proof(
    outcome: ExecutionOutcome,
) -> None:
    records = (
        record(ExecutionPhase.COMPILE, ExecutionOutcome.SUCCESS),
        record(ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST, outcome),
        record(ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST, outcome),
    )
    result = measure_execution_observation(observation(records=records))
    assert result.buggy_failure is MeasurementState.NOT_PROVEN
    assert result.fixed_reference_pass is MeasurementState.NOT_PROVEN
    assert result.regression_proof is MeasurementState.NOT_PROVEN


@pytest.mark.parametrize(
    ("phase", "outcome", "completeness", "integrity_state", "field"),
    [
        (
            ExecutionPhase.COMPILE,
            ExecutionOutcome.SUCCESS,
            EvidenceCompleteness.PARTIAL,
            EvidenceIntegrityState.VERIFIED,
            "compile_success",
        ),
        (
            ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST,
            ExecutionOutcome.TEST_FAILURE,
            EvidenceCompleteness.UNAVAILABLE,
            None,
            "buggy_failure",
        ),
        (
            ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST,
            ExecutionOutcome.NOT_RUN,
            EvidenceCompleteness.UNAVAILABLE,
            None,
            "fixed_reference_pass",
        ),
    ],
)
def test_partial_unavailable_and_not_run_required_phases_are_missing(
    phase: ExecutionPhase,
    outcome: ExecutionOutcome,
    completeness: EvidenceCompleteness,
    integrity_state: EvidenceIntegrityState | None,
    field: str,
) -> None:
    records = {
        ExecutionPhase.COMPILE: record(ExecutionPhase.COMPILE, ExecutionOutcome.SUCCESS),
        ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST: record(
            ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST,
            ExecutionOutcome.TEST_FAILURE,
        ),
        ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST: record(
            ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST,
            ExecutionOutcome.SUCCESS,
        ),
    }
    records[phase] = record(
        phase,
        outcome,
        completeness=completeness,
        integrity_state=integrity_state,
    )
    result = measure_execution_observation(observation(records=tuple(records.values())))
    assert getattr(result, field) is MeasurementState.MISSING


def test_partial_bundle_preserves_complete_trustworthy_phase_measurement() -> None:
    value = measure_execution_observation(
        observation(
            records=(record(ExecutionPhase.COMPILE, ExecutionOutcome.SUCCESS),)
        )
    )
    assert value.compile_success is MeasurementState.PROVEN
    assert value.buggy_failure is value.fixed_reference_pass is MeasurementState.MISSING


@pytest.mark.parametrize(
    "completeness",
    [EvidenceCompleteness.CONFLICTING, EvidenceCompleteness.INVALID],
)
def test_conflicting_or_invalid_bundle_fails_closed(
    completeness: EvidenceCompleteness,
) -> None:
    assert_metric_error(
        ExecutionMetricErrorCode.CONFLICTING_EVIDENCE,
        lambda: observation(completeness=completeness),
    )


@pytest.mark.parametrize(
    "integrity_state",
    [EvidenceIntegrityState.TAMPERED, EvidenceIntegrityState.CORRUPT],
)
def test_tampered_or_corrupt_bundle_fails_closed(
    integrity_state: EvidenceIntegrityState,
) -> None:
    assert_metric_error(
        ExecutionMetricErrorCode.CONFLICTING_EVIDENCE,
        lambda: observation(bundle_integrity=integrity_state),
    )


@pytest.mark.parametrize(
    "completeness",
    [EvidenceCompleteness.CONFLICTING, EvidenceCompleteness.INVALID],
)
def test_conflicting_or_invalid_execution_record_fails_closed(
    completeness: EvidenceCompleteness,
) -> None:
    bad = record(
        ExecutionPhase.COMPILE,
        ExecutionOutcome.SUCCESS,
        completeness=completeness,
    )
    assert_metric_error(
        ExecutionMetricErrorCode.CONFLICTING_EVIDENCE,
        lambda: observation(records=(bad,)),
    )


@pytest.mark.parametrize(
    "integrity_state",
    [EvidenceIntegrityState.TAMPERED, EvidenceIntegrityState.CORRUPT],
)
def test_tampered_or_corrupt_execution_record_fails_closed(
    integrity_state: EvidenceIntegrityState,
) -> None:
    bad = record(
        ExecutionPhase.COMPILE,
        ExecutionOutcome.SUCCESS,
        completeness=EvidenceCompleteness.PARTIAL,
        integrity_state=integrity_state,
    )
    assert_metric_error(
        ExecutionMetricErrorCode.CONFLICTING_EVIDENCE,
        lambda: observation(records=(bad,)),
    )


@pytest.mark.parametrize(
    "integrity_state",
    [
        EvidenceIntegrityState.UNVERIFIABLE,
        EvidenceIntegrityState.MISSING,
        EvidenceIntegrityState.DELETED,
    ],
)
def test_unverifiable_bundle_integrity_cannot_establish_positive_proof(
    integrity_state: EvidenceIntegrityState,
) -> None:
    result = measure_execution_observation(
        observation(bundle_integrity=integrity_state)
    )
    assert (
        result.compile_success,
        result.buggy_failure,
        result.fixed_reference_pass,
        result.regression_proof,
    ) == (MeasurementState.MISSING,) * 4


def test_upstream_rejects_test_failure_with_all_passing_facts() -> None:
    valid = record(
        ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST,
        ExecutionOutcome.SUCCESS,
    )
    with pytest.raises(ValueError, match="test failure requires"):
        replace(
            valid,
            outcome=ExecutionOutcome.TEST_FAILURE,
            failure=FailureEvidence(FailureCategory.TEST_FAILURE),
        )


def test_upstream_rejects_success_with_failed_test_facts() -> None:
    valid = record(
        ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST,
        ExecutionOutcome.SUCCESS,
    )
    with pytest.raises(ValueError, match="successful test Evidence"):
        replace(valid, test_result=failed_result())


def test_upstream_rejects_incompatible_failure_category() -> None:
    valid = record(
        ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST,
        ExecutionOutcome.TEST_FAILURE,
    )
    with pytest.raises(ValueError, match="requires TEST_FAILURE"):
        replace(valid, failure=FailureEvidence(FailureCategory.RUNNER_ERROR))


@pytest.mark.parametrize("case", ["D4J-FAKE-999", "D4J-" + "X" * 10_001])
def test_fake_case_ids_fail_closed(case: str) -> None:
    assert_metric_error(
        ExecutionMetricErrorCode.INVALID_BENCHMARK_CASE_ID,
        lambda: observation(case=case),
    )


def test_wrong_manifest_version_and_missing_provenance_fail_closed() -> None:
    assert_metric_error(
        ExecutionMetricErrorCode.INVALID_BENCHMARK_MANIFEST_VERSION,
        lambda: observation(version="defects4j_mvp_v1"),
    )
    assert_metric_error(
        ExecutionMetricErrorCode.MISSING_BENCHMARK_PROVENANCE,
        lambda: observation(case=None, version=None),
    )
    with pytest.raises(ValueError, match="paired consistently"):
        bundle(case=None, version=MANIFEST_VERSION)
    with pytest.raises(ValueError, match="paired consistently"):
        bundle(case="D4J-LANG-001", version=None)


@pytest.mark.parametrize(
    ("case", "source_revision", "target_revision"),
    [
        ("D4J-LANG-001", "999b", "1f"),
        ("D4J-LANG-001", "1b", "999f"),
        ("D4J-LANG-001", "1f", "1b"),
        ("D4J-LANG-001", "550e8400-e29b-41d4-a716-446655440000", "1f"),
        ("D4J-LANG-001", "0123456789abcdef0123456789abcdef01234567", "1f"),
        ("D4J-LANG-001", "53b", "53f"),
        ("D4J-LANG-001", "1B", "1f"),
        ("D4J-LANG-001", "1b ", "1f"),
        ("D4J-LANG-001", "01b", "1f"),
        ("D4J-LANG-034", "1b", "1f"),
    ],
)
def test_frozen_revision_mismatches_fail_closed(
    case: str, source_revision: str, target_revision: str
) -> None:
    assert_metric_error(
        ExecutionMetricErrorCode.INVALID_BENCHMARK_REVISION,
        lambda: observation(
            case=case,
            source_revision=source_revision,
            target_reference_revision=target_revision,
        ),
    )


def test_exact_frozen_revision_pair_is_accepted_and_target_is_required() -> None:
    assert measure_execution_observation(observation()).regression_proof is MeasurementState.PROVEN
    assert_metric_error(
        ExecutionMetricErrorCode.INVALID_BENCHMARK_REVISION,
        lambda: observation(
            records=(record(ExecutionPhase.COMPILE, ExecutionOutcome.SUCCESS),),
            target_reference_revision=None,
        ),
    )


def test_valid_frozen_case_and_authoritative_run_are_derived_from_bundle() -> None:
    source = bundle(case="D4J-MATH-001", run="run:valid")
    value = ExecutionMetricObservation(source)
    assert value.evidence_bundle is source
    assert value.benchmark_case_id == "D4J-MATH-001"
    assert value.run_id == RunId("run:valid")
    with pytest.raises(TypeError):
        ExecutionMetricObservation(source, RunId("rebound"))  # type: ignore[call-arg]


def test_wrong_run_identity_type_and_raw_string_fail_at_upstream_boundary() -> None:
    source = bundle()
    with pytest.raises(TypeError, match="run_id must be a RunId"):
        replace(source, run_id="run:1")
    assert RunId("run:1") != "run:1"
    assert_metric_error(
        ExecutionMetricErrorCode.INVALID_EVIDENCE_BUNDLE,
        lambda: ExecutionMetricObservation("run:1"),  # type: ignore[arg-type]
    )


def test_same_bundle_and_same_case_run_duplicates_fail_closed() -> None:
    value = observation()
    assert_metric_error(
        ExecutionMetricErrorCode.DUPLICATE_OBSERVATION,
        lambda: aggregate_execution_metrics((value, value)),
    )
    other_bundle = observation(bundle_id="bundle:other")
    assert_metric_error(
        ExecutionMetricErrorCode.CONFLICTING_EVIDENCE,
        lambda: aggregate_execution_metrics((value, other_bundle)),
    )


def test_same_run_different_case_and_rebound_bundle_fail_closed() -> None:
    lang = observation(case="D4J-LANG-001", run="run:shared")
    math = observation(case="D4J-MATH-001", run="run:shared")
    assert_metric_error(
        ExecutionMetricErrorCode.INCONSISTENT_RUN_BINDING,
        lambda: aggregate_execution_metrics((lang, math)),
    )
    rebound = ExecutionMetricObservation(
        replace(
            lang.evidence_bundle,
            evaluation_benchmark_case_reference=OpaqueReference("D4J-MATH-001"),
        )
    )
    assert_metric_error(
        ExecutionMetricErrorCode.CONFLICTING_EVIDENCE,
        lambda: aggregate_execution_metrics((lang, rebound)),
    )


def test_valid_multiple_runs_and_cases_are_accepted() -> None:
    values = (
        observation(case="D4J-LANG-001", run="run:1"),
        observation(case="D4J-LANG-001", run="run:2"),
        observation(case="D4J-MATH-001", run="run:3"),
    )
    result = aggregate_execution_metrics(values)
    assert result.observation_count == 3
    assert tuple(item.run_id.value for item in result.case_measurements) == (
        "run:1",
        "run:2",
        "run:3",
    )


def test_execution_evidence_identity_is_globally_unique() -> None:
    first = observation(run="run:first")
    same_object = ExecutionMetricObservation(
        replace(
            first.evidence_bundle,
            evidence_bundle_id=EvidenceBundleId("bundle:same-object"),
        )
    )
    assert_metric_error(
        ExecutionMetricErrorCode.CONFLICTING_EVIDENCE,
        lambda: aggregate_execution_metrics((first, same_object)),
    )

    shared = "evidence:globally-shared"
    second = observation(
        run="run:second",
        records=(
            record(
                ExecutionPhase.COMPILE,
                ExecutionOutcome.SUCCESS,
                run="run:second",
                evidence_id=shared,
            ),
        ),
    )
    for outcome in (ExecutionOutcome.SUCCESS, ExecutionOutcome.COMPILATION_FAILURE):
        third = observation(
            run=f"run:third:{outcome.value}",
            records=(
                record(
                    ExecutionPhase.COMPILE,
                    outcome,
                    run=f"run:third:{outcome.value}",
                    evidence_id=shared,
                ),
            ),
        )
        assert_metric_error(
            ExecutionMetricErrorCode.CONFLICTING_EVIDENCE,
            lambda third=third: aggregate_execution_metrics((second, third)),
        )


def test_execution_evidence_identity_cannot_cross_frozen_cases() -> None:
    shared = "evidence:cross-case"
    lang = observation(
        case="D4J-LANG-001",
        run="run:lang",
        records=(
            record(
                ExecutionPhase.COMPILE,
                ExecutionOutcome.SUCCESS,
                run="run:lang",
                evidence_id=shared,
            ),
        ),
    )
    math = observation(
        case="D4J-MATH-001",
        run="run:math",
        records=(
            record(
                ExecutionPhase.COMPILE,
                ExecutionOutcome.SUCCESS,
                run="run:math",
                evidence_id=shared,
            ),
        ),
    )
    assert_metric_error(
        ExecutionMetricErrorCode.CONFLICTING_EVIDENCE,
        lambda: aggregate_execution_metrics((lang, math)),
    )


def test_distinct_execution_evidence_identities_are_accepted() -> None:
    result = aggregate_execution_metrics(
        (observation(run="run:distinct:1"), observation(run="run:distinct:2"))
    )
    assert result.observation_count == 2


def test_regression_proof_requires_both_positive_facts() -> None:
    buggy_missing = record(
        ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST,
        ExecutionOutcome.TEST_FAILURE,
        completeness=EvidenceCompleteness.PARTIAL,
    )
    missing = measure_execution_observation(
        observation(
            records=(
                record(ExecutionPhase.COMPILE, ExecutionOutcome.SUCCESS),
                buggy_missing,
                record(
                    ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST,
                    ExecutionOutcome.SUCCESS,
                ),
            )
        )
    )
    assert missing.regression_proof is MeasurementState.MISSING
    negative = measure_execution_observation(
        observation(
            records=(
                record(
                    ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST,
                    ExecutionOutcome.SUCCESS,
                ),
                record(
                    ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST,
                    ExecutionOutcome.SUCCESS,
                ),
            )
        )
    )
    assert negative.regression_proof is MeasurementState.NOT_PROVEN


@pytest.mark.parametrize(
    ("values", "error_type"),
    [
        ((True, 1, 0), TypeError),
        ((1, True, 0), TypeError),
        ((1, 1, True), TypeError),
        ((-1, 1, 0), ValueError),
        ((0, -1, 0), ValueError),
        ((0, 0, -1), ValueError),
        ((2, 1, 0), ValueError),
        ((1, 0, 0), ValueError),
    ],
)
def test_exact_rate_rejects_impossible_counters(
    values: tuple[object, object, object], error_type: type[Exception]
) -> None:
    with pytest.raises(error_type):
        ExactRate(*values)  # type: ignore[arg-type]


def test_exact_rate_derives_exact_or_unmeasured_score() -> None:
    assert ExactRate(0, 0, 3).score is None
    assert ExactRate(2, 3, 1).score == Fraction(2, 3)
    assert not isinstance(ExactRate(2, 3, 1).score, float)
    with pytest.raises(TypeError):
        ExactRate(1, 1, 0, score=0.5)  # type: ignore[call-arg]


def test_public_result_constructors_require_authoritative_provenance() -> None:
    source = bundle()
    measurement = ExecutionCaseMeasurement(source)
    assert measurement.regression_proof is MeasurementState.PROVEN
    with pytest.raises(TypeError):
        ExecutionCaseMeasurement(  # type: ignore[call-arg]
            benchmark_case_id="D4J-LANG-001",
            run_id=RunId("run:forged"),
            compile_success=MeasurementState.PROVEN,
            buggy_failure=MeasurementState.PROVEN,
            fixed_reference_pass=MeasurementState.PROVEN,
            regression_proof=MeasurementState.PROVEN,
        )
    with pytest.raises(ExecutionMetricError):
        ExecutionCaseMeasurement(object())  # type: ignore[arg-type]

    aggregate = ExecutionMetricsAggregate((measurement,))
    assert aggregate.observation_count == 1
    assert aggregate.regression_proof_rate == ExactRate(1, 1, 0)
    with pytest.raises(TypeError):
        ExecutionMetricsAggregate(  # type: ignore[call-arg]
            observation_count=1,
            case_measurements=(),
            compile_success_rate=ExactRate(1, 1, 0),
            fail_on_buggy_rate=ExactRate(1, 1, 0),
            pass_on_fixed_reference_rate=ExactRate(1, 1, 0),
            regression_proof_rate=ExactRate(1, 1, 0),
            evidence_eligible_observation_count=1,
        )
    with pytest.raises(ValueError):
        replace(aggregate, regression_proof_rate=ExactRate(0, 1, 0))


def test_public_aggregate_revalidates_duplicate_measurements() -> None:
    measurement = ExecutionCaseMeasurement(bundle())
    assert_metric_error(
        ExecutionMetricErrorCode.DUPLICATE_OBSERVATION,
        lambda: ExecutionMetricsAggregate((measurement, measurement)),
    )


def test_zero_eligible_and_empty_populations_have_no_fake_score() -> None:
    missing_fixed = record(
        ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST,
        ExecutionOutcome.SUCCESS,
        completeness=EvidenceCompleteness.PARTIAL,
    )
    zero_eligible = aggregate_execution_metrics(
        (
            observation(
                records=(
                    record(
                        ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST,
                        ExecutionOutcome.TEST_FAILURE,
                    ),
                    missing_fixed,
                )
            ),
        )
    )
    assert zero_eligible.evidence_eligible_observation_count == 0
    assert zero_eligible.regression_proof_rate.score is None
    empty = aggregate_execution_metrics(())
    assert empty.observation_count == empty.evidence_eligible_observation_count == 0
    assert all(
        rate.score is None
        for rate in (
            empty.compile_success_rate,
            empty.fail_on_buggy_rate,
            empty.pass_on_fixed_reference_rate,
            empty.regression_proof_rate,
        )
    )


def test_measurement_constructor_has_no_caller_controlled_truth_fields() -> None:
    parameters = inspect.signature(ExecutionCaseMeasurement).parameters
    assert tuple(parameters) == ("evidence_bundle",)
    assert not {
        "compile_success",
        "buggy_failure",
        "fixed_reference_pass",
        "regression_proof",
    } & parameters.keys()


def test_order_independence_repeatability_and_input_immutability() -> None:
    values = [
        observation(case="D4J-MATH-001", run="run:2"),
        observation(case="D4J-LANG-001", run="run:1"),
    ]
    snapshot = list(values)
    bundles_before = tuple(value.evidence_bundle.to_domain_json() for value in values)
    first = aggregate_execution_metrics(values)
    assert first == aggregate_execution_metrics(reversed(values))
    assert first == aggregate_execution_metrics(values)
    assert values == snapshot
    assert tuple(value.evidence_bundle.to_domain_json() for value in values) == bundles_before


def test_results_and_observation_are_frozen() -> None:
    value = observation()
    result = aggregate_execution_metrics((value,))
    with pytest.raises(FrozenInstanceError):
        value.evidence_bundle = bundle(run="run:other")  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.observation_count = 0  # type: ignore[misc]


def test_invalid_observation_collections_fail_closed() -> None:
    assert_metric_error(
        ExecutionMetricErrorCode.INVALID_OBSERVATIONS,
        lambda: aggregate_execution_metrics("not observations"),
    )
    assert_metric_error(
        ExecutionMetricErrorCode.INVALID_OBSERVATIONS,
        lambda: aggregate_execution_metrics((object(),)),
    )
    assert_metric_error(
        ExecutionMetricErrorCode.INVALID_OBSERVATIONS,
        lambda: measure_execution_observation(object()),
    )


def test_type_hints_resolve_for_all_candidate_functions() -> None:
    functions = [
        value
        for value in vars(execution_metrics).values()
        if inspect.isfunction(value) and value.__module__ == execution_metrics.__name__
    ]
    assert functions
    for function in functions:
        typing.get_type_hints(function)


def test_frozen_defects4j_and_localisation_inputs_remain_untouched() -> None:
    before = {
        path: (path.read_bytes(), hashlib.sha256(path.read_bytes()).hexdigest())
        for path in (MANIFEST, LOCALISATION)
    }
    aggregate_execution_metrics((observation(),))
    for path, (data, digest) in before.items():
        assert path.read_bytes() == data
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
