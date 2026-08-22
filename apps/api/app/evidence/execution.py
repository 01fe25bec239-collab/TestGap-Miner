"""Immutable Evidence-domain representation of upstream Execution facts."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import TYPE_CHECKING, Final


EVIDENCE_CONTRACT_VERSION: Final = "CONTRACT-EVIDENCE-001@1.0.0-draft.3"

if TYPE_CHECKING:
    from .artefact import ArtefactId, ArtefactReference, ArtefactType


@dataclass(frozen=True, slots=True)
class _Identifier:
    value: str

    def __post_init__(self) -> None:
        if type(self.value) is not str or not self.value.strip():
            raise ValueError(f"{type(self).__name__} must contain a nonempty string")


class ExecutionEvidenceId(_Identifier):
    """Evidence-owned identity; never an alias for an upstream identity."""


class ProducerResultId(_Identifier):
    """Opaque A2-EXECUTION-owned result identity."""


class WorkflowAttemptId(_Identifier):
    """Opaque A2-AGENT-WORKFLOW-owned attempt identity."""


class CandidateVersionId(_Identifier):
    """Evidence-owned candidate-version identity."""


class RunId(_Identifier):
    """Opaque A2-AGENT-WORKFLOW-owned run identity."""


class QueueMessageId(_Identifier):
    """Opaque A2-QUEUE-owned message identity."""


class QueueDeliveryId(_Identifier):
    """Opaque A2-QUEUE-owned delivery identity."""


class CorrelationId(_Identifier):
    """Opaque cross-component tracing identity."""


@dataclass(frozen=True, slots=True)
class OpaqueReference:
    value: str

    def __post_init__(self) -> None:
        if type(self.value) is not str or not self.value.strip():
            raise ValueError("opaque reference must contain a nonempty string")


class ExecutionPhase(StrEnum):
    COMPILE = "COMPILE"
    BUGGY_OR_TARGET_REVISION_TEST = "BUGGY_OR_TARGET_REVISION_TEST"
    FIXED_OR_REFERENCE_REVISION_TEST = "FIXED_OR_REFERENCE_REVISION_TEST"


class ExecutionOutcome(StrEnum):
    SUCCESS = "SUCCESS"
    COMPILATION_FAILURE = "COMPILATION_FAILURE"
    TEST_FAILURE = "TEST_FAILURE"
    TIMEOUT = "TIMEOUT"
    CANCELLATION = "CANCELLATION"
    RESOURCE_BREACH = "RESOURCE_BREACH"
    RUNNER_ERROR = "RUNNER_ERROR"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_RUN = "NOT_RUN"


class FailureCategory(StrEnum):
    COMPILATION_FAILURE = "COMPILATION_FAILURE"
    TEST_FAILURE = "TEST_FAILURE"
    TIMEOUT = "TIMEOUT"
    CANCELLATION = "CANCELLATION"
    RESOURCE_BREACH = "RESOURCE_BREACH"
    RUNNER_ERROR = "RUNNER_ERROR"


class EvidenceCompleteness(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"
    INVALID = "INVALID"
    CONFLICTING = "CONFLICTING"
    REDACTED = "REDACTED"
    DELETED_OR_TOMBSTONED = "DELETED_OR_TOMBSTONED"


class EvidenceAvailability(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    EXPIRED = "EXPIRED"
    REDACTED = "REDACTED"
    DELETED_OR_TOMBSTONED = "DELETED_OR_TOMBSTONED"


class EvidenceIntegrityState(StrEnum):
    VERIFIED = "VERIFIED"
    UNVERIFIABLE = "UNVERIFIABLE"
    CORRUPT = "CORRUPT"
    TAMPERED = "TAMPERED"
    MISSING = "MISSING"
    DELETED = "DELETED"


@dataclass(frozen=True, slots=True)
class IntegrityMetadata:
    state: EvidenceIntegrityState
    verification_reference: OpaqueReference | None = None

    def __post_init__(self) -> None:
        _require_type(self.state, EvidenceIntegrityState, "state")
        _require_optional_type(
            self.verification_reference,
            OpaqueReference,
            "verification_reference",
        )
        if (
            self.state is EvidenceIntegrityState.VERIFIED
            and self.verification_reference is None
        ):
            raise ValueError("VERIFIED integrity requires a verification reference")


@dataclass(frozen=True, slots=True)
class ExecutionTiming:
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration: timedelta | None = None
    upstream_fact_reference: OpaqueReference | None = None

    def __post_init__(self) -> None:
        for name in ("started_at", "ended_at"):
            value = getattr(self, name)
            if value is not None:
                if not isinstance(value, datetime):
                    raise TypeError(f"{name} must be a datetime when supplied")
                if value.utcoffset() is None:
                    raise ValueError(f"{name} must be timezone-aware")
        if self.duration is not None:
            if not isinstance(self.duration, timedelta):
                raise TypeError("duration must be a timedelta when supplied")
            if self.duration < timedelta(0):
                raise ValueError("duration must not be negative")
        _require_optional_type(
            self.upstream_fact_reference,
            OpaqueReference,
            "upstream_fact_reference",
        )
        if self.started_at is not None and self.ended_at is not None:
            elapsed = self.ended_at - self.started_at
            if elapsed < timedelta(0):
                raise ValueError("execution end must not precede start")
            if self.duration is not None and self.duration != elapsed:
                raise ValueError("execution duration contradicts start and end")

    @property
    def is_complete(self) -> bool:
        return (
            self.started_at is not None
            and self.ended_at is not None
            and self.duration is not None
        )


@dataclass(frozen=True, slots=True)
class TimeoutMetadata:
    timed_out: bool
    classification: OpaqueReference | None = None
    configured_limit: timedelta | None = None
    upstream_fact_reference: OpaqueReference | None = None

    def __post_init__(self) -> None:
        if type(self.timed_out) is not bool:
            raise TypeError("timed_out must be a bool")
        _require_optional_type(self.classification, OpaqueReference, "classification")
        _require_optional_type(
            self.upstream_fact_reference,
            OpaqueReference,
            "upstream_fact_reference",
        )
        if self.configured_limit is not None:
            if not isinstance(self.configured_limit, timedelta):
                raise TypeError("configured_limit must be a timedelta when supplied")
            if self.configured_limit < timedelta(0):
                raise ValueError("configured timeout limit must not be negative")
        if self.timed_out and self.classification is None:
            raise ValueError("a timeout requires an explicit classification")


@dataclass(frozen=True, slots=True)
class ProcessExit:
    exit_code: int | None = None
    signal_number: int | None = None
    signal_name: str | None = None
    upstream_fact_reference: OpaqueReference | None = None

    def __post_init__(self) -> None:
        if self.exit_code is not None and type(self.exit_code) is not int:
            raise TypeError("exit_code must be an integer when supplied")
        if self.signal_number is not None and (
            type(self.signal_number) is not int or self.signal_number <= 0
        ):
            raise ValueError("signal_number must be a positive integer when supplied")
        if self.signal_name is not None and (
            type(self.signal_name) is not str or not self.signal_name.strip()
        ):
            raise ValueError("signal_name must be a nonempty string when supplied")
        _require_optional_type(
            self.upstream_fact_reference,
            OpaqueReference,
            "upstream_fact_reference",
        )
        if (
            self.exit_code is None
            and self.signal_number is None
            and self.signal_name is None
            and self.upstream_fact_reference is None
        ):
            raise ValueError("process exit must retain at least one supplied fact")


class ResourceCategory(StrEnum):
    CPU_TIME = "CPU_TIME"
    MEMORY_BYTES = "MEMORY_BYTES"
    DISK_TEMP_WORKSPACE_BYTES = "DISK_TEMP_WORKSPACE_BYTES"
    PROCESS_COUNT = "PROCESS_COUNT"
    FILE_COUNT = "FILE_COUNT"
    STDOUT_BYTES = "STDOUT_BYTES"
    STDERR_BYTES = "STDERR_BYTES"
    TIMEOUT = "TIMEOUT"
    OTHER = "OTHER"


class ResourceEnforcementStatus(StrEnum):
    NOT_ENFORCED = "NOT_ENFORCED"
    CAPTURE_BOUND_ENFORCED = "CAPTURE_BOUND_ENFORCED"
    SUPERVISOR_TIMEOUT_ENFORCED = "SUPERVISOR_TIMEOUT_ENFORCED"
    EXTERNAL_ENFORCED = "EXTERNAL_ENFORCED"


@dataclass(frozen=True, slots=True)
class ResourceValue:
    amount: int
    unit: str

    def __post_init__(self) -> None:
        if type(self.amount) is not int or self.amount < 0:
            raise ValueError("resource amount must be a non-negative integer")
        if type(self.unit) is not str or not self.unit.strip():
            raise ValueError("resource unit must be a nonempty string")


@dataclass(frozen=True, slots=True)
class ResourceObservation:
    category: ResourceCategory
    enforcement_status: ResourceEnforcementStatus
    terminated_execution: bool
    configured_value: ResourceValue | None = None
    configuration_reference: OpaqueReference | None = None
    observed_value: ResourceValue | None = None
    breached: bool | None = None
    truncated: bool | None = None
    upstream_fact_reference: OpaqueReference | None = None
    other_category: str | None = None

    def __post_init__(self) -> None:
        _require_type(self.category, ResourceCategory, "category")
        _require_type(
            self.enforcement_status,
            ResourceEnforcementStatus,
            "enforcement_status",
        )
        if type(self.terminated_execution) is not bool:
            raise TypeError("terminated_execution must be a bool")
        for name in ("breached", "truncated"):
            value = getattr(self, name)
            if value is not None and type(value) is not bool:
                raise TypeError(f"{name} must be a bool when supplied")
        _require_optional_type(self.configured_value, ResourceValue, "configured_value")
        _require_optional_type(
            self.configuration_reference,
            OpaqueReference,
            "configuration_reference",
        )
        _require_optional_type(self.observed_value, ResourceValue, "observed_value")
        _require_optional_type(
            self.upstream_fact_reference,
            OpaqueReference,
            "upstream_fact_reference",
        )
        if self.configured_value is None and self.configuration_reference is None:
            raise ValueError(
                "resource observation requires a configured value or configuration reference"
            )
        if self.category is ResourceCategory.OTHER:
            if type(self.other_category) is not str or not self.other_category.strip():
                raise ValueError("OTHER resource category requires other_category")
        elif self.other_category is not None:
            raise ValueError("other_category is valid only for OTHER resources")
        if (
            self.enforcement_status is ResourceEnforcementStatus.NOT_ENFORCED
            and self.terminated_execution
        ):
            raise ValueError("a not-enforced resource cannot terminate execution")


class CompileStatus(StrEnum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    NOT_COMPLETED = "NOT_COMPLETED"


@dataclass(frozen=True, slots=True)
class CompileResult:
    status: CompileStatus
    error_count: int | None = None
    warning_count: int | None = None
    compiler_metadata_reference: OpaqueReference | None = None
    diagnostic_artefacts: tuple[ArtefactReference, ...] = ()

    def __post_init__(self) -> None:
        from .artefact import ArtefactReference

        _require_type(self.status, CompileStatus, "status")
        for name in ("error_count", "warning_count"):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f"{name} must be a non-negative integer when supplied")
        if self.status is CompileStatus.SUCCESS and (self.error_count or 0) > 0:
            raise ValueError("successful compile result cannot contain errors")
        _require_optional_type(
            self.compiler_metadata_reference,
            OpaqueReference,
            "compiler_metadata_reference",
        )
        object.__setattr__(
            self,
            "diagnostic_artefacts",
            _immutable_tuple(
                self.diagnostic_artefacts,
                ArtefactReference,
                "diagnostic_artefacts",
                sort_semantically=True,
            ),
        )


class TestCaseStatus(StrEnum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    ERRORED = "ERRORED"


@dataclass(frozen=True, slots=True)
class TestCaseResult:
    test_reference: OpaqueReference
    status: TestCaseStatus
    failure_reference: OpaqueReference | None = None

    def __post_init__(self) -> None:
        _require_type(self.test_reference, OpaqueReference, "test_reference")
        _require_type(self.status, TestCaseStatus, "status")
        _require_optional_type(
            self.failure_reference,
            OpaqueReference,
            "failure_reference",
        )
        if (
            self.failure_reference is not None
            and self.status not in {TestCaseStatus.FAILED, TestCaseStatus.ERRORED}
        ):
            raise ValueError("failure_reference is valid only for failed or errored tests")


@dataclass(frozen=True, slots=True)
class TestResult:
    executed_count: int | None = None
    passed_count: int | None = None
    failed_count: int | None = None
    skipped_count: int | None = None
    errored_count: int | None = None
    test_cases: tuple[TestCaseResult, ...] | None = None
    failure_summary_reference: OpaqueReference | None = None

    def __post_init__(self) -> None:
        count_names = (
            "executed_count",
            "passed_count",
            "failed_count",
            "skipped_count",
            "errored_count",
        )
        for name in count_names:
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f"{name} must be a non-negative integer when supplied")
        _require_optional_type(
            self.failure_summary_reference,
            OpaqueReference,
            "failure_summary_reference",
        )
        known_result_count = sum(
            value
            for value in (
                self.passed_count,
                self.failed_count,
                self.skipped_count,
                self.errored_count,
            )
            if value is not None
        )
        if self.executed_count is not None and known_result_count > self.executed_count:
            raise ValueError("known test result counts exceed executed_count")
        if self.test_cases is not None:
            cases = tuple(
                sorted(
                    _immutable_tuple(
                        self.test_cases,
                        TestCaseResult,
                        "test_cases",
                    ),
                    key=lambda case: case.test_reference.value,
                )
            )
            object.__setattr__(self, "test_cases", cases)
            identities = [case.test_reference.value for case in cases]
            if len(identities) != len(set(identities)):
                raise ValueError("test case references must be unique")
            status_counts = {
                TestCaseStatus.PASSED: self.passed_count,
                TestCaseStatus.FAILED: self.failed_count,
                TestCaseStatus.SKIPPED: self.skipped_count,
                TestCaseStatus.ERRORED: self.errored_count,
            }
            for status, supplied_count in status_counts.items():
                observed = sum(case.status is status for case in cases)
                if supplied_count is not None and supplied_count != observed:
                    raise ValueError(f"{status.value.lower()} count contradicts test cases")
            if self.executed_count is not None and self.executed_count != len(cases):
                raise ValueError("executed_count contradicts test cases")


@dataclass(frozen=True, slots=True)
class FailureEvidence:
    category: FailureCategory
    upstream_failure_reference: OpaqueReference | None = None

    def __post_init__(self) -> None:
        _require_type(self.category, FailureCategory, "category")
        _require_optional_type(
            self.upstream_failure_reference,
            OpaqueReference,
            "upstream_failure_reference",
        )


_FAILURE_FOR_OUTCOME: Final = {
    ExecutionOutcome.COMPILATION_FAILURE: FailureCategory.COMPILATION_FAILURE,
    ExecutionOutcome.TEST_FAILURE: FailureCategory.TEST_FAILURE,
    ExecutionOutcome.TIMEOUT: FailureCategory.TIMEOUT,
    ExecutionOutcome.CANCELLATION: FailureCategory.CANCELLATION,
    ExecutionOutcome.RESOURCE_BREACH: FailureCategory.RESOURCE_BREACH,
    ExecutionOutcome.RUNNER_ERROR: FailureCategory.RUNNER_ERROR,
}


@dataclass(frozen=True, slots=True)
class ExecutionEvidence:
    execution_evidence_id: ExecutionEvidenceId
    producer_result_id: ProducerResultId
    workflow_attempt_id: WorkflowAttemptId
    candidate_version_id: CandidateVersionId
    execution_phase: ExecutionPhase
    outcome: ExecutionOutcome
    completeness: EvidenceCompleteness
    command_reference: OpaqueReference
    execution_fact_reference: OpaqueReference
    compile_result: CompileResult | None = None
    test_result: TestResult | None = None
    run_id: RunId | None = None
    queue_message_id: QueueMessageId | None = None
    queue_delivery_id: QueueDeliveryId | None = None
    correlation_id: CorrelationId | None = None
    source_revision: OpaqueReference | None = None
    execution_timing: ExecutionTiming | None = None
    timeout_metadata: TimeoutMetadata | None = None
    process_exit: ProcessExit | None = None
    stdout_artefact: ArtefactReference | None = None
    stderr_artefact: ArtefactReference | None = None
    execution_integrity: IntegrityMetadata | None = None
    runtime_metadata_reference: OpaqueReference | None = None
    sandbox_metadata_reference: OpaqueReference | None = None
    environment_metadata_reference: OpaqueReference | None = None
    flake_indication_reference: OpaqueReference | None = None
    failure: FailureEvidence | None = None
    secondary_failures: tuple[FailureEvidence, ...] = ()
    resource_observations: tuple[ResourceObservation, ...] = ()
    output_artefacts: tuple[ArtefactReference, ...] = ()
    contract_version: str = EVIDENCE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        from .artefact import ArtefactReference

        for name, expected in (
            ("execution_evidence_id", ExecutionEvidenceId),
            ("producer_result_id", ProducerResultId),
            ("workflow_attempt_id", WorkflowAttemptId),
            ("candidate_version_id", CandidateVersionId),
            ("execution_phase", ExecutionPhase),
            ("outcome", ExecutionOutcome),
            ("completeness", EvidenceCompleteness),
            ("command_reference", OpaqueReference),
            ("execution_fact_reference", OpaqueReference),
        ):
            _require_type(getattr(self, name), expected, name)
        for name, expected in (
            ("compile_result", CompileResult),
            ("test_result", TestResult),
            ("run_id", RunId),
            ("queue_message_id", QueueMessageId),
            ("queue_delivery_id", QueueDeliveryId),
            ("correlation_id", CorrelationId),
            ("source_revision", OpaqueReference),
            ("execution_timing", ExecutionTiming),
            ("timeout_metadata", TimeoutMetadata),
            ("process_exit", ProcessExit),
            ("stdout_artefact", ArtefactReference),
            ("stderr_artefact", ArtefactReference),
            ("execution_integrity", IntegrityMetadata),
            ("runtime_metadata_reference", OpaqueReference),
            ("sandbox_metadata_reference", OpaqueReference),
            ("environment_metadata_reference", OpaqueReference),
            ("flake_indication_reference", OpaqueReference),
            ("failure", FailureEvidence),
        ):
            _require_optional_type(getattr(self, name), expected, name)
        if self.contract_version != EVIDENCE_CONTRACT_VERSION:
            raise ValueError("unsupported Evidence contract version")

        object.__setattr__(
            self,
            "secondary_failures",
            _immutable_tuple(
                self.secondary_failures,
                FailureEvidence,
                "secondary_failures",
                sort_semantically=True,
            ),
        )
        object.__setattr__(
            self,
            "resource_observations",
            _immutable_tuple(
                self.resource_observations,
                ResourceObservation,
                "resource_observations",
                sort_semantically=True,
            ),
        )
        object.__setattr__(
            self,
            "output_artefacts",
            _immutable_tuple(
                self.output_artefacts,
                ArtefactReference,
                "output_artefacts",
                sort_semantically=True,
            ),
        )

        self._validate_identity_separation()
        self._validate_phase_result()
        self._validate_timeout()
        self._validate_outcome()
        self._validate_artefacts()
        self._validate_completeness()

    def _all_artefacts(self) -> tuple[ArtefactReference, ...]:
        artefacts = self.output_artefacts
        if self.stdout_artefact is not None:
            artefacts += (self.stdout_artefact,)
        if self.stderr_artefact is not None:
            artefacts += (self.stderr_artefact,)
        if self.compile_result is not None:
            artefacts += self.compile_result.diagnostic_artefacts
        return artefacts

    def _validate_identity_separation(self) -> None:
        evidence_value = self.execution_evidence_id.value
        external_ids = (
            self.producer_result_id,
            self.workflow_attempt_id,
            self.run_id,
            self.queue_message_id,
            self.queue_delivery_id,
            self.correlation_id,
        )
        if any(
            identity is not None and identity.value == evidence_value
            for identity in external_ids
        ):
            raise ValueError(
                "execution_evidence_id must be distinct from every external identity"
            )
        if self.candidate_version_id.value == evidence_value or any(
            artefact.artefact_id.value == evidence_value
            for artefact in self._all_artefacts()
        ):
            raise ValueError("distinct Evidence identity kinds must not share a value")

    def _validate_phase_result(self) -> None:
        if self.execution_phase is ExecutionPhase.COMPILE:
            if self.compile_result is None or self.test_result is not None:
                raise ValueError("COMPILE requires only compile_result")
            expected_status = {
                ExecutionOutcome.SUCCESS: CompileStatus.SUCCESS,
                ExecutionOutcome.COMPILATION_FAILURE: CompileStatus.FAILURE,
            }.get(self.outcome, CompileStatus.NOT_COMPLETED)
            if self.compile_result.status is not expected_status:
                raise ValueError("compile status contradicts execution outcome")
            if self.outcome is ExecutionOutcome.TEST_FAILURE:
                raise ValueError("compile Evidence cannot represent TEST_FAILURE")
        else:
            if self.test_result is None or self.compile_result is not None:
                raise ValueError("test phases require only test_result")
            if self.source_revision is None:
                raise ValueError("test phase requires exact source_revision provenance")
            if self.outcome is ExecutionOutcome.COMPILATION_FAILURE:
                raise ValueError("test Evidence cannot represent COMPILATION_FAILURE")
            failed_cases = (
                ()
                if self.test_result.test_cases is None
                else tuple(
                    case
                    for case in self.test_result.test_cases
                    if case.status in {TestCaseStatus.FAILED, TestCaseStatus.ERRORED}
                )
            )
            if self.outcome is ExecutionOutcome.SUCCESS and (
                (self.test_result.failed_count or 0) > 0
                or (self.test_result.errored_count or 0) > 0
                or failed_cases
            ):
                raise ValueError("successful test Evidence cannot contain failures or errors")
            if (
                self.outcome is ExecutionOutcome.TEST_FAILURE
                and (self.test_result.failed_count or 0) == 0
                and (self.test_result.errored_count or 0) == 0
                and not failed_cases
            ):
                raise ValueError("test failure requires a failed or errored test fact")

    def _validate_timeout(self) -> None:
        if self.outcome is ExecutionOutcome.TIMEOUT:
            if self.timeout_metadata is None or not self.timeout_metadata.timed_out:
                raise ValueError("TIMEOUT requires explicit timeout metadata")
        elif self.timeout_metadata is not None and self.timeout_metadata.timed_out:
            raise ValueError("timed_out metadata contradicts non-timeout outcome")

    def _validate_outcome(self) -> None:
        required_failure = _FAILURE_FOR_OUTCOME.get(self.outcome)
        if required_failure is None:
            if self.failure is not None or self.secondary_failures:
                raise ValueError("non-failure outcome must not carry failure Evidence")
        elif self.failure is None or self.failure.category is not required_failure:
            raise ValueError(
                f"{self.outcome.value} requires {required_failure.value} failure Evidence"
            )
        if self.outcome is ExecutionOutcome.SUCCESS and self.process_exit is not None:
            if self.process_exit.exit_code not in (None, 0):
                raise ValueError("successful Evidence cannot carry a nonzero exit code")
            if (
                self.process_exit.signal_number is not None
                or self.process_exit.signal_name is not None
            ):
                raise ValueError("successful Evidence cannot carry a termination signal")
        if self.outcome is ExecutionOutcome.RESOURCE_BREACH and not any(
            observation.breached is True for observation in self.resource_observations
        ):
            raise ValueError("RESOURCE_BREACH requires an explicitly supplied breach fact")

    def _validate_artefacts(self) -> None:
        from .artefact import ArtefactType

        artefacts = self._all_artefacts()
        artefact_ids = [artefact.artefact_id for artefact in artefacts]
        if len(artefact_ids) != len(set(artefact_ids)):
            raise ValueError("artefact references must have distinct logical identities")
        if self.execution_phase is ExecutionPhase.COMPILE:
            for name in ("stdout_artefact", "stderr_artefact"):
                artefact = getattr(self, name)
                if (
                    artefact is not None
                    and artefact.artefact_type is not ArtefactType.COMPILE_LOG
                ):
                    raise ValueError(
                        "compile stdout and stderr require COMPILE_LOG artefacts"
                    )
        else:
            if (
                self.stdout_artefact is not None
                and self.stdout_artefact.artefact_type is not ArtefactType.TEST_STDOUT
            ):
                raise ValueError("test stdout requires a TEST_STDOUT artefact")
            if (
                self.stderr_artefact is not None
                and self.stderr_artefact.artefact_type is not ArtefactType.TEST_STDERR
            ):
                raise ValueError("test stderr requires a TEST_STDERR artefact")

    def _validate_completeness(self) -> None:
        if self.completeness is not EvidenceCompleteness.COMPLETE:
            return
        if self.outcome in {ExecutionOutcome.UNAVAILABLE, ExecutionOutcome.NOT_RUN}:
            raise ValueError("unavailable or not-run Evidence cannot be COMPLETE")
        if self.execution_timing is None or not self.execution_timing.is_complete:
            raise ValueError("COMPLETE Evidence requires complete execution timing")
        if self.timeout_metadata is None:
            raise ValueError("COMPLETE Evidence requires timeout occurrence metadata")
        if self.stdout_artefact is None or self.stderr_artefact is None:
            raise ValueError("COMPLETE Evidence requires stdout and stderr artefacts")
        if self.execution_integrity is None or (
            self.execution_integrity.state is not EvidenceIntegrityState.VERIFIED
        ):
            raise ValueError("COMPLETE Evidence requires verified execution integrity")
        if (
            self.execution_phase is not ExecutionPhase.COMPILE
            and self.test_result is not None
            and self.test_result.test_cases is None
        ):
            raise ValueError("COMPLETE test Evidence requires individual test case facts")
        if any(
            artefact.availability is not EvidenceAvailability.AVAILABLE
            for artefact in self._all_artefacts()
        ):
            raise ValueError("COMPLETE Evidence cannot reference unavailable artefacts")
        if any(
            artefact.integrity.state is not EvidenceIntegrityState.VERIFIED
            for artefact in self._all_artefacts()
        ):
            raise ValueError("COMPLETE Evidence cannot reference unverified artefacts")

    def to_domain_dict(self) -> dict[str, object]:
        """Return deterministic domain data without mutating this value."""
        return _domain_value(self)  # type: ignore[return-value]

    def to_domain_json(self) -> str:
        """Serialize deterministically for domain comparison, not cryptography."""
        return json.dumps(
            self.to_domain_dict(),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )


class EvidenceComparison(StrEnum):
    DISTINCT_IDENTITY = "DISTINCT_IDENTITY"
    EQUIVALENT = "EQUIVALENT"
    CONFLICTING = "CONFLICTING"


def compare_execution_evidence(
    existing: ExecutionEvidence,
    incoming: ExecutionEvidence,
) -> EvidenceComparison:
    """Classify duplicate/conflict semantics without overwriting either value."""
    _require_type(existing, ExecutionEvidence, "existing")
    _require_type(incoming, ExecutionEvidence, "incoming")
    if existing.execution_evidence_id != incoming.execution_evidence_id:
        return EvidenceComparison.DISTINCT_IDENTITY
    if existing.to_domain_json() == incoming.to_domain_json():
        return EvidenceComparison.EQUIVALENT
    return EvidenceComparison.CONFLICTING


def _require_type(value: object, expected: type, name: str) -> None:
    if not isinstance(value, expected):
        raise TypeError(f"{name} must be a {expected.__name__}")


def _require_optional_type(value: object, expected: type, name: str) -> None:
    if value is not None:
        _require_type(value, expected, name)


def _immutable_tuple(
    values: Iterable[object],
    expected: type,
    name: str,
    *,
    sort_semantically: bool = False,
) -> tuple:
    if isinstance(values, (str, bytes, bytearray, set, frozenset, dict)):
        raise TypeError(f"{name} must be an ordered iterable of {expected.__name__}")
    try:
        result = tuple(values)
    except TypeError as error:
        raise TypeError(f"{name} must be iterable") from error
    if not all(isinstance(value, expected) for value in result):
        raise TypeError(f"{name} must contain only {expected.__name__} values")
    return tuple(sorted(result, key=_semantic_key)) if sort_semantically else result


def _semantic_key(value: object) -> str:
    """Stable key for domain collections whose source order has no meaning."""
    return json.dumps(
        _domain_value(value),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _domain_value(value: object) -> object:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, timedelta):
        return (
            value.days * 86_400_000_000
            + value.seconds * 1_000_000
            + value.microseconds
        )
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _domain_value(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, tuple):
        return [_domain_value(item) for item in value]
    return value


_COMPAT_ARTEFACT_NAMES: Final = frozenset(
    {"ArtefactId", "ArtefactReference", "ArtefactType"}
)


def __getattr__(name: str) -> object:
    """Re-export the one canonical artefact domain implementation on demand."""
    if name in _COMPAT_ARTEFACT_NAMES:
        from . import artefact as artefact_domain

        return getattr(artefact_domain, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
