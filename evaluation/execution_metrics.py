"""Exact execution metrics derived from authoritative Evidence bundles."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum
from fractions import Fraction
from pathlib import Path
from typing import NoReturn

from app.evidence import (
    EvidenceBundle,
    EvidenceCompleteness,
    EvidenceIntegrityState,
    ExecutionEvidence,
    ExecutionOutcome,
    ExecutionPhase,
    RunId,
)
from evaluation.defects4j_manifest import MANIFEST_VERSION, verify_file


_MANIFEST_PATH = (
    Path(__file__).resolve().parents[1]
    / "benchmarks"
    / "defects4j"
    / f"{MANIFEST_VERSION}.json"
)
_FAIL_CLOSED_COMPLETENESS = frozenset(
    {EvidenceCompleteness.CONFLICTING, EvidenceCompleteness.INVALID}
)
_FAIL_CLOSED_INTEGRITY = frozenset(
    {EvidenceIntegrityState.CORRUPT, EvidenceIntegrityState.TAMPERED}
)


class ExecutionMetricErrorCode(StrEnum):
    INVALID_EVIDENCE_BUNDLE = "INVALID_EVIDENCE_BUNDLE"
    MISSING_BENCHMARK_PROVENANCE = "MISSING_BENCHMARK_PROVENANCE"
    INVALID_BENCHMARK_MANIFEST_VERSION = "INVALID_BENCHMARK_MANIFEST_VERSION"
    INVALID_BENCHMARK_CASE_ID = "INVALID_BENCHMARK_CASE_ID"
    INVALID_BENCHMARK_REVISION = "INVALID_BENCHMARK_REVISION"
    INVALID_RUN_ID = "INVALID_RUN_ID"
    INVALID_OBSERVATIONS = "INVALID_OBSERVATIONS"
    DUPLICATE_OBSERVATION = "DUPLICATE_OBSERVATION"
    INCONSISTENT_RUN_BINDING = "INCONSISTENT_RUN_BINDING"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"


class ExecutionMetricError(ValueError):
    def __init__(self, code: ExecutionMetricErrorCode, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code.value}: {detail}")


class MeasurementState(StrEnum):
    PROVEN = "PROVEN"
    NOT_PROVEN = "NOT_PROVEN"
    MISSING = "MISSING"


@dataclass(frozen=True, slots=True)
class ExecutionMetricObservation:
    evidence_bundle: EvidenceBundle

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_bundle, EvidenceBundle):
            _raise(
                ExecutionMetricErrorCode.INVALID_EVIDENCE_BUNDLE,
                "evidence_bundle must be an EvidenceBundle",
            )
        _validate_bundle(self.evidence_bundle)

    @property
    def benchmark_case_id(self) -> str:
        reference = self.evidence_bundle.evaluation_benchmark_case_reference
        assert reference is not None
        return reference.value

    @property
    def run_id(self) -> RunId:
        return self.evidence_bundle.run_id


@dataclass(frozen=True, slots=True)
class ExecutionCaseMeasurement:
    evidence_bundle: EvidenceBundle
    benchmark_case_id: str = field(init=False)
    run_id: RunId = field(init=False)
    compile_success: MeasurementState = field(init=False)
    buggy_failure: MeasurementState = field(init=False)
    fixed_reference_pass: MeasurementState = field(init=False)
    regression_proof: MeasurementState = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_bundle, EvidenceBundle):
            _raise(
                ExecutionMetricErrorCode.INVALID_EVIDENCE_BUNDLE,
                "evidence_bundle must be an EvidenceBundle",
            )
        values = _measurement_values(self.evidence_bundle)
        for name, value in values.items():
            object.__setattr__(self, name, value)


@dataclass(frozen=True, slots=True)
class ExactRate:
    numerator: int
    denominator: int
    missing_count: int

    def __post_init__(self) -> None:
        for name in ("numerator", "denominator", "missing_count"):
            _require_nonnegative_exact_int(getattr(self, name), name)
        if self.numerator > self.denominator:
            raise ValueError("numerator must not exceed denominator")

    @property
    def score(self) -> Fraction | None:
        return None if self.denominator == 0 else Fraction(self.numerator, self.denominator)


@dataclass(frozen=True, slots=True)
class ExecutionMetricsAggregate:
    case_measurements: tuple[ExecutionCaseMeasurement, ...] | Iterable[ExecutionCaseMeasurement]
    observation_count: int = field(init=False)
    compile_success_rate: ExactRate = field(init=False)
    fail_on_buggy_rate: ExactRate = field(init=False)
    pass_on_fixed_reference_rate: ExactRate = field(init=False)
    regression_proof_rate: ExactRate = field(init=False)
    evidence_eligible_observation_count: int = field(init=False)

    def __post_init__(self) -> None:
        if isinstance(self.case_measurements, (str, bytes, bytearray, dict)):
            _raise(
                ExecutionMetricErrorCode.INVALID_OBSERVATIONS,
                "case_measurements must be an iterable of ExecutionCaseMeasurement values",
            )
        try:
            supplied = tuple(self.case_measurements)
        except TypeError:
            _raise(
                ExecutionMetricErrorCode.INVALID_OBSERVATIONS,
                "case_measurements must be iterable",
            )
        if not all(isinstance(value, ExecutionCaseMeasurement) for value in supplied):
            _raise(
                ExecutionMetricErrorCode.INVALID_OBSERVATIONS,
                "case_measurements must contain only ExecutionCaseMeasurement values",
            )
        for measurement in supplied:
            expected = _measurement_values(measurement.evidence_bundle)
            if any(getattr(measurement, name) != value for name, value in expected.items()):
                _raise(
                    ExecutionMetricErrorCode.CONFLICTING_EVIDENCE,
                    "measurement contradicts its authoritative EvidenceBundle",
                )
        _validate_population(supplied)
        measured = tuple(
            sorted(supplied, key=lambda value: (value.benchmark_case_id, value.run_id.value))
        )
        object.__setattr__(self, "case_measurements", measured)
        object.__setattr__(self, "observation_count", len(measured))
        object.__setattr__(self, "compile_success_rate", _rate(measured, "compile_success"))
        object.__setattr__(self, "fail_on_buggy_rate", _rate(measured, "buggy_failure"))
        object.__setattr__(
            self,
            "pass_on_fixed_reference_rate",
            _rate(measured, "fixed_reference_pass"),
        )
        regression_rate = _rate(measured, "regression_proof")
        object.__setattr__(self, "regression_proof_rate", regression_rate)
        object.__setattr__(
            self, "evidence_eligible_observation_count", regression_rate.denominator
        )


def measure_execution_observation(
    observation: ExecutionMetricObservation,
) -> ExecutionCaseMeasurement:
    if not isinstance(observation, ExecutionMetricObservation):
        _raise(
            ExecutionMetricErrorCode.INVALID_OBSERVATIONS,
            "observation must be an ExecutionMetricObservation",
        )
    bundle = observation.evidence_bundle
    return ExecutionCaseMeasurement(bundle)


def aggregate_execution_metrics(
    observations: Iterable[ExecutionMetricObservation],
) -> ExecutionMetricsAggregate:
    if isinstance(observations, (str, bytes, bytearray, dict)):
        _raise(
            ExecutionMetricErrorCode.INVALID_OBSERVATIONS,
            "observations must be an iterable of ExecutionMetricObservation values",
        )
    try:
        supplied = tuple(observations)
    except TypeError:
        _raise(ExecutionMetricErrorCode.INVALID_OBSERVATIONS, "observations must be iterable")
    if not all(isinstance(value, ExecutionMetricObservation) for value in supplied):
        _raise(
            ExecutionMetricErrorCode.INVALID_OBSERVATIONS,
            "observations must contain only ExecutionMetricObservation values",
        )

    return ExecutionMetricsAggregate(
        measure_execution_observation(value) for value in supplied
    )


def _frozen_cases() -> dict[str, dict[str, object]]:
    manifest = verify_file(_MANIFEST_PATH)
    return {case["benchmark_case_id"]: case for case in manifest["cases"]}


def _validate_bundle(bundle: EvidenceBundle) -> None:
    case_reference = bundle.evaluation_benchmark_case_reference
    version_reference = bundle.evaluation_benchmark_manifest_version
    if case_reference is None or version_reference is None:
        _raise(
            ExecutionMetricErrorCode.MISSING_BENCHMARK_PROVENANCE,
            "benchmark case and manifest-version provenance are required",
        )
    if version_reference.value != MANIFEST_VERSION:
        _raise(
            ExecutionMetricErrorCode.INVALID_BENCHMARK_MANIFEST_VERSION,
            f"benchmark manifest version must be exactly {MANIFEST_VERSION}",
        )
    case = _frozen_cases().get(case_reference.value)
    if case is None:
        _raise(
            ExecutionMetricErrorCode.INVALID_BENCHMARK_CASE_ID,
            "benchmark case is not a member of the frozen selected benchmark",
        )
    buggy_revision = case["buggy_revision"]
    fixed_revision = case["fixed_revision"]
    assert isinstance(buggy_revision, dict) and isinstance(fixed_revision, dict)
    if bundle.source_revision.value != buggy_revision["defects4j_version_id"]:
        _raise(
            ExecutionMetricErrorCode.INVALID_BENCHMARK_REVISION,
            "source revision does not exactly match the frozen buggy Defects4J version ID",
        )
    if (
        bundle.target_reference_revision is None
        or bundle.target_reference_revision.value
        != fixed_revision["defects4j_version_id"]
    ):
        _raise(
            ExecutionMetricErrorCode.INVALID_BENCHMARK_REVISION,
            "target reference revision does not exactly match the frozen fixed Defects4J version ID",
        )
    if bundle.completeness in _FAIL_CLOSED_COMPLETENESS:
        _raise(
            ExecutionMetricErrorCode.CONFLICTING_EVIDENCE,
            "invalid or conflicting EvidenceBundle cannot be measured",
        )
    if (
        bundle.integrity_metadata is not None
        and bundle.integrity_metadata.state in _FAIL_CLOSED_INTEGRITY
    ):
        _raise(
            ExecutionMetricErrorCode.CONFLICTING_EVIDENCE,
            "corrupt or tampered EvidenceBundle cannot be measured",
        )
    for record in bundle.execution_evidence:
        if record.completeness in _FAIL_CLOSED_COMPLETENESS:
            _raise(
                ExecutionMetricErrorCode.CONFLICTING_EVIDENCE,
                "invalid or conflicting ExecutionEvidence cannot be measured",
            )
        if (
            record.execution_integrity is not None
            and record.execution_integrity.state in _FAIL_CLOSED_INTEGRITY
        ):
            _raise(
                ExecutionMetricErrorCode.CONFLICTING_EVIDENCE,
                "corrupt or tampered ExecutionEvidence cannot be measured",
            )


def _measurement_values(bundle: EvidenceBundle) -> dict[str, object]:
    _validate_bundle(bundle)
    records = {record.execution_phase: record for record in bundle.execution_evidence}
    eligible = _bundle_is_measurement_eligible(bundle)
    buggy_failure = _phase_state(
        records.get(ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST),
        positive_outcome=ExecutionOutcome.TEST_FAILURE,
        bundle_eligible=eligible,
    )
    fixed_pass = _phase_state(
        records.get(ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST),
        positive_outcome=ExecutionOutcome.SUCCESS,
        bundle_eligible=eligible,
    )
    return {
        "benchmark_case_id": bundle.evaluation_benchmark_case_reference.value,
        "run_id": bundle.run_id,
        "compile_success": _phase_state(
            records.get(ExecutionPhase.COMPILE),
            positive_outcome=ExecutionOutcome.SUCCESS,
            bundle_eligible=eligible,
        ),
        "buggy_failure": buggy_failure,
        "fixed_reference_pass": fixed_pass,
        "regression_proof": _regression_state(buggy_failure, fixed_pass),
    }


def _validate_population(measurements: tuple[ExecutionCaseMeasurement, ...]) -> None:
    bundle_ids: dict[object, ExecutionCaseMeasurement] = {}
    runs: dict[RunId, ExecutionCaseMeasurement] = {}
    case_runs: set[tuple[str, RunId]] = set()
    execution_evidence_ids: set[object] = set()
    for measurement in measurements:
        bundle = measurement.evidence_bundle
        previous_bundle = bundle_ids.get(bundle.evidence_bundle_id)
        if previous_bundle is not None:
            _raise(
                ExecutionMetricErrorCode.DUPLICATE_OBSERVATION
                if previous_bundle == measurement
                else ExecutionMetricErrorCode.CONFLICTING_EVIDENCE,
                f"EvidenceBundle identity supplied more than once: {bundle.evidence_bundle_id.value}",
            )
        bundle_ids[bundle.evidence_bundle_id] = measurement
        previous_run = runs.get(bundle.run_id)
        if previous_run is not None:
            if previous_run.benchmark_case_id != measurement.benchmark_case_id:
                _raise(
                    ExecutionMetricErrorCode.INCONSISTENT_RUN_BINDING,
                    "one run identity cannot be bound to two benchmark cases",
                )
            _raise(
                ExecutionMetricErrorCode.DUPLICATE_OBSERVATION
                if previous_run == measurement
                else ExecutionMetricErrorCode.CONFLICTING_EVIDENCE,
                "run identity supplied more than once",
            )
        runs[bundle.run_id] = measurement
        case_run = (measurement.benchmark_case_id, bundle.run_id)
        if case_run in case_runs:
            _raise(
                ExecutionMetricErrorCode.DUPLICATE_OBSERVATION,
                "benchmark case/run identity supplied more than once",
            )
        case_runs.add(case_run)
        for record in bundle.execution_evidence:
            if record.execution_evidence_id in execution_evidence_ids:
                _raise(
                    ExecutionMetricErrorCode.CONFLICTING_EVIDENCE,
                    "ExecutionEvidence identity supplied more than once: "
                    f"{record.execution_evidence_id.value}",
                )
            execution_evidence_ids.add(record.execution_evidence_id)


def _bundle_is_measurement_eligible(bundle: EvidenceBundle) -> bool:
    if bundle.completeness not in {
        EvidenceCompleteness.COMPLETE,
        EvidenceCompleteness.PARTIAL,
    }:
        return False
    return bundle.integrity_metadata is None or (
        bundle.integrity_metadata.state is EvidenceIntegrityState.VERIFIED
    )


def _phase_state(
    record: ExecutionEvidence | None,
    *,
    positive_outcome: ExecutionOutcome,
    bundle_eligible: bool,
) -> MeasurementState:
    if not bundle_eligible or record is None:
        return MeasurementState.MISSING
    if (
        record.completeness is not EvidenceCompleteness.COMPLETE
        or record.outcome in {ExecutionOutcome.UNAVAILABLE, ExecutionOutcome.NOT_RUN}
        or record.execution_integrity is None
        or record.execution_integrity.state is not EvidenceIntegrityState.VERIFIED
    ):
        return MeasurementState.MISSING
    return (
        MeasurementState.PROVEN
        if record.outcome is positive_outcome
        else MeasurementState.NOT_PROVEN
    )


def _regression_state(
    buggy_failure: MeasurementState,
    fixed_pass: MeasurementState,
) -> MeasurementState:
    if MeasurementState.MISSING in (buggy_failure, fixed_pass):
        return MeasurementState.MISSING
    if buggy_failure is fixed_pass is MeasurementState.PROVEN:
        return MeasurementState.PROVEN
    return MeasurementState.NOT_PROVEN


def _rate(
    measured: tuple[ExecutionCaseMeasurement, ...], field: str
) -> ExactRate:
    states = tuple(getattr(value, field) for value in measured)
    missing = states.count(MeasurementState.MISSING)
    return ExactRate(
        numerator=states.count(MeasurementState.PROVEN),
        denominator=len(states) - missing,
        missing_count=missing,
    )


def _require_nonnegative_exact_int(value: object, name: str) -> None:
    if type(value) is not int:
        raise TypeError(f"{name} must be an exact int")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


def _raise(code: ExecutionMetricErrorCode, detail: str) -> NoReturn:
    raise ExecutionMetricError(code, detail)
