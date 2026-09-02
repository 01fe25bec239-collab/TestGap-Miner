//! Strict, versioned JSON export of validated Execution facts.

use crate::{
    BoundedOutputReference, CancellationOutcome, ExecutionFailure, ExecutionPhase, OutputStream,
    ProcessExit, ProducerOutcome, ProducerOutputKind, ProducerResult, ProducerResultId,
    ProducerRuntimeFacts, ResourceEnforcementStatus, ResourceLimitKind, ResourceLimitObservation,
    ResourceLimitValue, RuntimeFactAvailability, RuntimeMetadata, SupervisorTermination,
    TestRunSummary, TimeoutOutcome, WorkflowAttemptId,
};
use serde::{Deserialize, Serialize};
use std::fmt;
use std::io;
use std::time::Duration;

pub const EXECUTION_EXPORT_VERSION: &str = "testgap.execution-export.v1";
pub const MAX_EXECUTION_EXPORT_BYTES: usize = 1024 * 1024;

const SOURCE_FIXED_BYTES: usize = 16 * 1024;
const RESOURCE_OBSERVATION_FIXED_BYTES: usize = 512;
const FAILURE_FIXED_BYTES: usize = 128;
const OUTPUT_REFERENCE_FIXED_BYTES: usize = 256;

#[derive(Debug)]
pub enum ExecutionExportError {
    Json(serde_json::Error),
    Invalid(&'static str),
    EnvelopeTooLarge,
}

impl fmt::Display for ExecutionExportError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Json(error) => write!(formatter, "invalid execution export JSON: {error}"),
            Self::Invalid(reason) => write!(formatter, "invalid execution export: {reason}"),
            Self::EnvelopeTooLarge => formatter.write_str("execution export exceeds byte limit"),
        }
    }
}

impl std::error::Error for ExecutionExportError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Json(error) => Some(error),
            Self::Invalid(_) | Self::EnvelopeTooLarge => None,
        }
    }
}

impl From<serde_json::Error> for ExecutionExportError {
    fn from(error: serde_json::Error) -> Self {
        Self::Json(error)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ExecutionTestSummary {
    JUnit(TestRunSummary),
    Defects4J { failing_test_count: u64 },
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ExecutionExportV1 {
    version: String,
    producer_result_id: String,
    workflow_attempt_id: String,
    phase: PhaseV1,
    candidate_version_reference: RequiredOption<String>,
    correlation_reference: RequiredOption<String>,
    outcome: OutcomeV1,
    test_summary: RequiredOption<TestSummaryV1>,
    runtime_facts: RuntimeFactsV1,
}

impl ExecutionExportV1 {
    pub fn version(&self) -> &str {
        &self.version
    }

    pub fn producer_result_id(&self) -> &str {
        &self.producer_result_id
    }

    pub fn workflow_attempt_id(&self) -> &str {
        &self.workflow_attempt_id
    }

    pub fn candidate_version_reference(&self) -> Option<&str> {
        self.candidate_version_reference.0.as_deref()
    }

    pub fn correlation_reference(&self) -> Option<&str> {
        self.correlation_reference.0.as_deref()
    }

    fn validate(&self) -> Result<(), ExecutionExportError> {
        if self.version != EXECUTION_EXPORT_VERSION {
            return Err(ExecutionExportError::Invalid("unsupported version"));
        }
        if self.producer_result_id.trim().is_empty() || self.workflow_attempt_id.trim().is_empty() {
            return Err(ExecutionExportError::Invalid("identity must not be empty"));
        }
        if self
            .candidate_version_reference
            .0
            .as_deref()
            .is_some_and(|value| value.trim().is_empty())
            || self
                .correlation_reference
                .0
                .as_deref()
                .is_some_and(|value| value.trim().is_empty())
        {
            return Err(ExecutionExportError::Invalid("reference must not be empty"));
        }
        if self.phase == PhaseV1::Compile && self.test_summary.0.is_some() {
            return Err(ExecutionExportError::Invalid(
                "test summary cannot apply to compile phase",
            ));
        }
        if let Some(TestSummaryV1::JUnit {
            tests_run,
            failures,
        }) = self.test_summary.0
        {
            if tests_run < failures {
                return Err(ExecutionExportError::Invalid(
                    "JUnit failures exceed tests run",
                ));
            }
        }
        if self.runtime_facts.duration.nanoseconds >= 1_000_000_000 {
            return Err(ExecutionExportError::Invalid(
                "duration nanoseconds are out of range",
            ));
        }
        validate_output_references(&self.runtime_facts.output_references)?;
        self.validate_runtime_consistency()
    }

    fn validate_runtime_consistency(&self) -> Result<(), ExecutionExportError> {
        let facts = self.runtime_facts.to_producer_runtime_facts()?;
        ProducerResult::new(
            ProducerResultId::new("execution-export-v1-validation")
                .expect("validation identity is non-empty"),
            WorkflowAttemptId::new("execution-export-v1-validation")
                .expect("validation identity is non-empty"),
            self.phase.into(),
            self.outcome.into(),
            facts,
        )
        .map(|_| ())
        .map_err(|_| ExecutionExportError::Invalid("runtime facts contradict producer result"))
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(transparent)]
struct RequiredOption<T>(Option<T>);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
enum PhaseV1 {
    #[serde(rename = "COMPILE")]
    Compile,
    #[serde(rename = "BUGGY_OR_TARGET_REVISION_TEST")]
    BuggyExecution,
    #[serde(rename = "FIXED_OR_REFERENCE_REVISION_TEST")]
    FixedExecution,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
enum OutcomeV1 {
    #[serde(rename = "SUCCESS")]
    Success,
    #[serde(rename = "COMPILATION_FAILURE")]
    CompilationFailure,
    #[serde(rename = "TEST_FAILURE")]
    TestFailure,
    #[serde(rename = "TIMEOUT")]
    Timeout,
    #[serde(rename = "CANCELLATION")]
    Cancellation,
    #[serde(rename = "RESOURCE_BREACH")]
    ResourceBreach,
    #[serde(rename = "RUNNER_FAILURE")]
    RunnerFailure,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "source", deny_unknown_fields)]
enum TestSummaryV1 {
    #[serde(rename = "JUNIT")]
    JUnit { tests_run: u64, failures: u64 },
    #[serde(rename = "DEFECTS4J")]
    Defects4J { failing_test_count: u64 },
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct RuntimeFactsV1 {
    metadata: RuntimeMetadataV1,
    process_exit: ProcessExitV1,
    timeout: TimeoutV1,
    cancellation: CancellationV1,
    duration: ExactDurationV1,
    availability: AvailabilityV1,
    resource_observations: Vec<ResourceObservationV1>,
    failures: Vec<FailureV1>,
    output_references: Vec<OutputReferenceV1>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct RuntimeMetadataV1 {
    operating_system: String,
    architecture: String,
    process_id: RequiredOption<u32>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", deny_unknown_fields)]
enum ProcessExitV1 {
    #[serde(rename = "NEVER_STARTED")]
    NeverStarted,
    #[serde(rename = "EXITED_WITH_CODE")]
    ExitedWithCode { code: i32 },
    #[serde(rename = "EXITED_WITHOUT_CODE")]
    ExitedWithoutCode,
    #[serde(rename = "TERMINATED_BY_SUPERVISOR")]
    TerminatedBySupervisor {
        reason: SupervisorTerminationV1,
        code: RequiredOption<i32>,
    },
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
enum SupervisorTerminationV1 {
    #[serde(rename = "TIMEOUT")]
    Timeout,
    #[serde(rename = "CANCELLATION")]
    Cancellation,
    #[serde(rename = "WAIT_FAILURE")]
    WaitFailure,
    #[serde(rename = "OUTPUT_CAPTURE_FAILURE")]
    OutputCaptureFailure,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", deny_unknown_fields)]
enum TimeoutV1 {
    #[serde(rename = "NOT_CONFIGURED")]
    NotConfigured,
    #[serde(rename = "NOT_TRIGGERED")]
    NotTriggered { limit: ExactDurationV1 },
    #[serde(rename = "TRIGGERED")]
    Triggered { limit: ExactDurationV1 },
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
enum CancellationV1 {
    #[serde(rename = "NOT_SELECTED")]
    NotSelected,
    #[serde(rename = "SELECTED")]
    Selected,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct ExactDurationV1 {
    seconds: u64,
    nanoseconds: u32,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
enum AvailabilityV1 {
    #[serde(rename = "COMPLETE")]
    Complete,
    #[serde(rename = "INCOMPLETE")]
    Incomplete,
    #[serde(rename = "UNAVAILABLE")]
    Unavailable,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct ResourceObservationV1 {
    kind: ResourceKindV1,
    configured_limit: ResourceValueV1,
    observed_value: RequiredOption<ResourceValueV1>,
    enforcement_status: EnforcementStatusV1,
    terminated_execution: bool,
    truncated: RequiredOption<bool>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", deny_unknown_fields)]
enum ResourceKindV1 {
    #[serde(rename = "CPU_TIME")]
    CpuTime,
    #[serde(rename = "MEMORY_BYTES")]
    MemoryBytes,
    #[serde(rename = "DISK_TEMP_WORKSPACE_BYTES")]
    DiskTempWorkspaceBytes,
    #[serde(rename = "PROCESS_COUNT")]
    ProcessCount,
    #[serde(rename = "FILE_COUNT")]
    FileCount,
    #[serde(rename = "STDOUT_BYTES")]
    StdoutBytes,
    #[serde(rename = "STDERR_BYTES")]
    StderrBytes,
    #[serde(rename = "TIMEOUT")]
    Timeout,
    #[serde(rename = "OTHER")]
    Other { name: String },
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", deny_unknown_fields)]
enum ResourceValueV1 {
    #[serde(rename = "DURATION")]
    Duration { value: ExactDurationV1 },
    #[serde(rename = "BYTES")]
    Bytes { value: u64 },
    #[serde(rename = "COUNT")]
    Count { value: u64 },
    #[serde(rename = "CUSTOM")]
    Custom { value: u64, unit: String },
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
enum EnforcementStatusV1 {
    #[serde(rename = "NOT_ENFORCED")]
    Not,
    #[serde(rename = "CAPTURE_BOUND_ENFORCED")]
    CaptureBound,
    #[serde(rename = "SUPERVISOR_TIMEOUT_ENFORCED")]
    SupervisorTimeout,
    #[serde(rename = "RUNTIME_LIMIT_ENFORCED")]
    RuntimeLimit,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", deny_unknown_fields)]
enum FailureV1 {
    #[serde(rename = "SPAWN_FAILURE")]
    SpawnFailure { error_kind: IoErrorKindV1 },
    #[serde(rename = "NON_ZERO_EXIT")]
    NonZeroExit { code: RequiredOption<i32> },
    #[serde(rename = "TIMEOUT")]
    Timeout,
    #[serde(rename = "CANCELLED")]
    Cancelled,
    #[serde(rename = "WAIT_FAILURE")]
    WaitFailure { error_kind: IoErrorKindV1 },
    #[serde(rename = "OUTPUT_CAPTURE_FAILURE")]
    OutputCaptureFailure {
        stream: OutputStreamV1,
        error_kind: RequiredOption<IoErrorKindV1>,
    },
    #[serde(rename = "TERMINATION_FAILURE")]
    TerminationFailure { error_kind: IoErrorKindV1 },
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
enum IoErrorKindV1 {
    #[serde(rename = "NOT_FOUND")]
    NotFound,
    #[serde(rename = "PERMISSION_DENIED")]
    PermissionDenied,
    #[serde(rename = "CONNECTION_REFUSED")]
    ConnectionRefused,
    #[serde(rename = "CONNECTION_RESET")]
    ConnectionReset,
    #[serde(rename = "HOST_UNREACHABLE")]
    HostUnreachable,
    #[serde(rename = "NETWORK_UNREACHABLE")]
    NetworkUnreachable,
    #[serde(rename = "CONNECTION_ABORTED")]
    ConnectionAborted,
    #[serde(rename = "NOT_CONNECTED")]
    NotConnected,
    #[serde(rename = "ADDR_IN_USE")]
    AddrInUse,
    #[serde(rename = "ADDR_NOT_AVAILABLE")]
    AddrNotAvailable,
    #[serde(rename = "NETWORK_DOWN")]
    NetworkDown,
    #[serde(rename = "BROKEN_PIPE")]
    BrokenPipe,
    #[serde(rename = "ALREADY_EXISTS")]
    AlreadyExists,
    #[serde(rename = "WOULD_BLOCK")]
    WouldBlock,
    #[serde(rename = "NOT_A_DIRECTORY")]
    NotADirectory,
    #[serde(rename = "IS_A_DIRECTORY")]
    IsADirectory,
    #[serde(rename = "DIRECTORY_NOT_EMPTY")]
    DirectoryNotEmpty,
    #[serde(rename = "READ_ONLY_FILESYSTEM")]
    ReadOnlyFilesystem,
    #[serde(rename = "STALE_NETWORK_FILE_HANDLE")]
    StaleNetworkFileHandle,
    #[serde(rename = "INVALID_INPUT")]
    InvalidInput,
    #[serde(rename = "INVALID_DATA")]
    InvalidData,
    #[serde(rename = "TIMED_OUT")]
    TimedOut,
    #[serde(rename = "WRITE_ZERO")]
    WriteZero,
    #[serde(rename = "STORAGE_FULL")]
    StorageFull,
    #[serde(rename = "NOT_SEEKABLE")]
    NotSeekable,
    #[serde(rename = "QUOTA_EXCEEDED")]
    QuotaExceeded,
    #[serde(rename = "FILE_TOO_LARGE")]
    FileTooLarge,
    #[serde(rename = "RESOURCE_BUSY")]
    ResourceBusy,
    #[serde(rename = "EXECUTABLE_FILE_BUSY")]
    ExecutableFileBusy,
    #[serde(rename = "DEADLOCK")]
    Deadlock,
    #[serde(rename = "CROSSES_DEVICES")]
    CrossesDevices,
    #[serde(rename = "TOO_MANY_LINKS")]
    TooManyLinks,
    #[serde(rename = "INVALID_FILENAME")]
    InvalidFilename,
    #[serde(rename = "ARGUMENT_LIST_TOO_LONG")]
    ArgumentListTooLong,
    #[serde(rename = "INTERRUPTED")]
    Interrupted,
    #[serde(rename = "UNSUPPORTED")]
    Unsupported,
    #[serde(rename = "UNEXPECTED_EOF")]
    UnexpectedEof,
    #[serde(rename = "OUT_OF_MEMORY")]
    OutOfMemory,
    #[serde(rename = "OTHER")]
    Other,
    #[serde(rename = "UNCATEGORIZED")]
    Uncategorized,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
enum OutputStreamV1 {
    #[serde(rename = "STDOUT")]
    Stdout,
    #[serde(rename = "STDERR")]
    Stderr,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct OutputReferenceV1 {
    kind: OutputKindV1,
    logical_reference: String,
    observed_bytes: u64,
    retained_bytes: u64,
    capture_limit_bytes: u64,
    truncated: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
enum OutputKindV1 {
    #[serde(rename = "STDOUT")]
    Stdout,
    #[serde(rename = "STDERR")]
    Stderr,
    #[serde(rename = "LOG")]
    Log,
    #[serde(rename = "PRODUCED_ARTEFACT")]
    ProducedArtefact,
    #[serde(rename = "DIAGNOSTIC")]
    Diagnostic,
}

/// Canonical compact UTF-8 encoding for one validated producer result.
pub fn to_json_bytes(
    result: &ProducerResult,
    summary: Option<ExecutionTestSummary>,
) -> Result<Vec<u8>, ExecutionExportError> {
    precheck_source_bound(result)?;
    let export = ExecutionExportV1::from_result(result, summary)?;
    let bytes = serde_json::to_vec(&export)?;
    if bytes.len() > MAX_EXECUTION_EXPORT_BYTES {
        return Err(ExecutionExportError::EnvelopeTooLarge);
    }
    Ok(bytes)
}

#[derive(Debug)]
struct SourceBudget {
    used: usize,
}

impl SourceBudget {
    fn new() -> Result<Self, ExecutionExportError> {
        let mut budget = Self { used: 0 };
        budget.add(SOURCE_FIXED_BYTES)?;
        Ok(budget)
    }

    fn add(&mut self, bytes: usize) -> Result<(), ExecutionExportError> {
        self.used = self
            .used
            .checked_add(bytes)
            .ok_or(ExecutionExportError::EnvelopeTooLarge)?;
        if self.used > MAX_EXECUTION_EXPORT_BYTES {
            return Err(ExecutionExportError::EnvelopeTooLarge);
        }
        Ok(())
    }

    fn add_items(&mut self, count: usize, bytes_each: usize) -> Result<(), ExecutionExportError> {
        self.add(
            count
                .checked_mul(bytes_each)
                .ok_or(ExecutionExportError::EnvelopeTooLarge)?,
        )
    }

    fn add_string(&mut self, value: &str) -> Result<(), ExecutionExportError> {
        self.add(
            value
                .len()
                .checked_mul(6)
                .ok_or(ExecutionExportError::EnvelopeTooLarge)?,
        )
    }
}

fn precheck_source_bound(result: &ProducerResult) -> Result<(), ExecutionExportError> {
    let facts = result.runtime_facts();
    let mut budget = SourceBudget::new()?;
    budget.add_string(result.producer_result_id().as_str())?;
    budget.add_string(result.workflow_attempt_id().as_str())?;
    if let Some(reference) = result.candidate_version_reference() {
        budget.add_string(reference.as_str())?;
    }
    if let Some(reference) = result.correlation_reference() {
        budget.add_string(reference.as_str())?;
    }
    budget.add_string(facts.runtime_metadata().operating_system)?;
    budget.add_string(facts.runtime_metadata().architecture)?;

    budget.add_items(
        facts.resource_observations().len(),
        RESOURCE_OBSERVATION_FIXED_BYTES,
    )?;
    for observation in facts.resource_observations() {
        if let ResourceLimitKind::Other(name) = &observation.kind {
            budget.add_string(name)?;
        }
        add_resource_value_source(&mut budget, &observation.configured_limit)?;
        if let Some(value) = &observation.observed_value {
            add_resource_value_source(&mut budget, value)?;
        }
    }

    budget.add_items(facts.failures().len(), FAILURE_FIXED_BYTES)?;
    budget.add_items(
        facts.output_references().len(),
        OUTPUT_REFERENCE_FIXED_BYTES,
    )?;
    for reference in facts.output_references() {
        budget.add_string(reference.reference())?;
    }
    Ok(())
}

fn add_resource_value_source(
    budget: &mut SourceBudget,
    value: &ResourceLimitValue,
) -> Result<(), ExecutionExportError> {
    if let ResourceLimitValue::Custom { unit, .. } = value {
        budget.add_string(unit)?;
    }
    Ok(())
}

/// Strictly decodes and validates an untrusted v1 wire envelope.
pub fn from_json_bytes(bytes: &[u8]) -> Result<ExecutionExportV1, ExecutionExportError> {
    if bytes.len() > MAX_EXECUTION_EXPORT_BYTES {
        return Err(ExecutionExportError::EnvelopeTooLarge);
    }
    let export: ExecutionExportV1 = serde_json::from_slice(bytes)?;
    export.validate()?;
    Ok(export)
}

impl ExecutionExportV1 {
    fn from_result(
        result: &ProducerResult,
        summary: Option<ExecutionTestSummary>,
    ) -> Result<Self, ExecutionExportError> {
        let facts = result.runtime_facts();
        let export = Self {
            version: EXECUTION_EXPORT_VERSION.to_owned(),
            producer_result_id: result.producer_result_id().as_str().to_owned(),
            workflow_attempt_id: result.workflow_attempt_id().as_str().to_owned(),
            phase: result.phase().into(),
            candidate_version_reference: RequiredOption(
                result
                    .candidate_version_reference()
                    .map(|reference| reference.as_str().to_owned()),
            ),
            correlation_reference: RequiredOption(
                result
                    .correlation_reference()
                    .map(|reference| reference.as_str().to_owned()),
            ),
            outcome: result.outcome().into(),
            test_summary: RequiredOption(summary.map(Into::into)),
            runtime_facts: RuntimeFactsV1 {
                metadata: facts.runtime_metadata().into(),
                process_exit: facts.process_exit().into(),
                timeout: facts.timeout().into(),
                cancellation: facts.cancellation().into(),
                duration: facts.duration().into(),
                availability: facts.availability().into(),
                resource_observations: facts
                    .resource_observations()
                    .iter()
                    .map(Into::into)
                    .collect(),
                failures: facts.failures().iter().map(Into::into).collect(),
                output_references: facts.output_references().iter().map(Into::into).collect(),
            },
        };
        export.validate()?;
        Ok(export)
    }
}

fn validate_output_references(
    references: &[OutputReferenceV1],
) -> Result<(), ExecutionExportError> {
    if references.len() > crate::ProducerRuntimeFacts::MAX_OUTPUT_REFERENCES
        || references
            .iter()
            .map(|reference| reference.logical_reference.len())
            .sum::<usize>()
            > crate::ProducerRuntimeFacts::MAX_OUTPUT_REFERENCE_METADATA_BYTES
    {
        return Err(ExecutionExportError::Invalid(
            "output reference collection exceeds bounds",
        ));
    }
    for reference in references {
        if reference.logical_reference.trim().is_empty()
            || reference.logical_reference.len() > BoundedOutputReference::MAX_REFERENCE_BYTES
            || reference.retained_bytes > reference.capture_limit_bytes
            || reference.retained_bytes > reference.observed_bytes
            || reference.truncated != (reference.observed_bytes > reference.retained_bytes)
        {
            return Err(ExecutionExportError::Invalid(
                "invalid output reference metadata",
            ));
        }
    }
    Ok(())
}

impl RuntimeFactsV1 {
    fn to_producer_runtime_facts(&self) -> Result<ProducerRuntimeFacts, ExecutionExportError> {
        let observations = self
            .resource_observations
            .iter()
            .map(ResourceObservationV1::to_resource_observation)
            .collect::<Result<Vec<_>, _>>()?;
        let failures = self
            .failures
            .iter()
            .map(FailureV1::to_execution_failure)
            .collect();
        Ok(ProducerRuntimeFacts::new(
            RuntimeMetadata {
                operating_system: "execution-export-v1-validation",
                architecture: "execution-export-v1-validation",
                process_id: self.metadata.process_id.0,
            },
            self.process_exit.into(),
            self.duration.to_duration()?,
        )
        .with_timeout(self.timeout.to_timeout()?)
        .with_cancellation(self.cancellation.into())
        .with_availability(self.availability.into())
        .with_resource_observations(observations)
        .with_failures(failures))
    }
}

impl ExactDurationV1 {
    fn to_duration(self) -> Result<Duration, ExecutionExportError> {
        if self.nanoseconds >= 1_000_000_000 {
            return Err(ExecutionExportError::Invalid(
                "duration nanoseconds are out of range",
            ));
        }
        Ok(Duration::new(self.seconds, self.nanoseconds))
    }
}

impl TimeoutV1 {
    fn to_timeout(self) -> Result<TimeoutOutcome, ExecutionExportError> {
        Ok(match self {
            Self::NotConfigured => TimeoutOutcome::NotConfigured,
            Self::NotTriggered { limit } => TimeoutOutcome::NotTriggered {
                limit: limit.to_duration()?,
            },
            Self::Triggered { limit } => TimeoutOutcome::Triggered {
                limit: limit.to_duration()?,
            },
        })
    }
}

impl ResourceObservationV1 {
    fn to_resource_observation(&self) -> Result<ResourceLimitObservation, ExecutionExportError> {
        Ok(ResourceLimitObservation {
            kind: self.kind.to_resource_kind(),
            configured_limit: self.configured_limit.to_resource_value()?,
            observed_value: self
                .observed_value
                .0
                .as_ref()
                .map(ResourceValueV1::to_resource_value)
                .transpose()?,
            enforcement_status: self.enforcement_status.into(),
            terminated_execution: self.terminated_execution,
            truncated: self.truncated.0,
        })
    }
}

impl ResourceKindV1 {
    fn to_resource_kind(&self) -> ResourceLimitKind {
        match self {
            Self::CpuTime => ResourceLimitKind::CpuTime,
            Self::MemoryBytes => ResourceLimitKind::MemoryBytes,
            Self::DiskTempWorkspaceBytes => ResourceLimitKind::DiskTempWorkspaceBytes,
            Self::ProcessCount => ResourceLimitKind::ProcessCount,
            Self::FileCount => ResourceLimitKind::FileCount,
            Self::StdoutBytes => ResourceLimitKind::StdoutBytes,
            Self::StderrBytes => ResourceLimitKind::StderrBytes,
            Self::Timeout => ResourceLimitKind::Timeout,
            Self::Other { name } => ResourceLimitKind::Other(name.clone()),
        }
    }
}

impl ResourceValueV1 {
    fn to_resource_value(&self) -> Result<ResourceLimitValue, ExecutionExportError> {
        Ok(match self {
            Self::Duration { value } => ResourceLimitValue::Duration(value.to_duration()?),
            Self::Bytes { value } => ResourceLimitValue::Bytes(*value),
            Self::Count { value } => ResourceLimitValue::Count(*value),
            Self::Custom { value, unit } => ResourceLimitValue::Custom {
                value: *value,
                unit: unit.clone(),
            },
        })
    }
}

impl FailureV1 {
    fn to_execution_failure(&self) -> ExecutionFailure {
        match self {
            Self::SpawnFailure { .. } => ExecutionFailure::SpawnFailure {
                kind: io::ErrorKind::Other,
                message: String::new(),
            },
            Self::NonZeroExit { code } => ExecutionFailure::NonZeroExit { code: code.0 },
            Self::Timeout => ExecutionFailure::Timeout,
            Self::Cancelled => ExecutionFailure::Cancelled,
            Self::WaitFailure { .. } => ExecutionFailure::WaitFailure {
                kind: io::ErrorKind::Other,
                message: String::new(),
            },
            Self::OutputCaptureFailure { stream, .. } => ExecutionFailure::OutputCaptureFailure {
                stream: (*stream).into(),
                kind: None,
                message: String::new(),
            },
            Self::TerminationFailure { .. } => ExecutionFailure::TerminationFailure {
                kind: io::ErrorKind::Other,
                message: String::new(),
            },
        }
    }
}

impl From<PhaseV1> for ExecutionPhase {
    fn from(value: PhaseV1) -> Self {
        match value {
            PhaseV1::Compile => Self::Compile,
            PhaseV1::BuggyExecution => Self::BuggyExecution,
            PhaseV1::FixedExecution => Self::FixedExecution,
        }
    }
}

impl From<OutcomeV1> for ProducerOutcome {
    fn from(value: OutcomeV1) -> Self {
        match value {
            OutcomeV1::Success => Self::Success,
            OutcomeV1::CompilationFailure => Self::CompilationFailure,
            OutcomeV1::TestFailure => Self::TestFailure,
            OutcomeV1::Timeout => Self::Timeout,
            OutcomeV1::Cancellation => Self::Cancellation,
            OutcomeV1::ResourceBreach => Self::ResourceBreach,
            OutcomeV1::RunnerFailure => Self::RunnerFailure,
        }
    }
}

impl From<ProcessExitV1> for ProcessExit {
    fn from(value: ProcessExitV1) -> Self {
        match value {
            ProcessExitV1::NeverStarted => Self::NeverStarted,
            ProcessExitV1::ExitedWithCode { code } => Self::ExitedWithCode(code),
            ProcessExitV1::ExitedWithoutCode => Self::ExitedWithoutCode,
            ProcessExitV1::TerminatedBySupervisor { reason, code } => {
                Self::TerminatedBySupervisor {
                    reason: reason.into(),
                    code: code.0,
                }
            }
        }
    }
}

impl From<SupervisorTerminationV1> for SupervisorTermination {
    fn from(value: SupervisorTerminationV1) -> Self {
        match value {
            SupervisorTerminationV1::Timeout => Self::Timeout,
            SupervisorTerminationV1::Cancellation => Self::Cancellation,
            SupervisorTerminationV1::WaitFailure => Self::WaitFailure,
            SupervisorTerminationV1::OutputCaptureFailure => Self::OutputCaptureFailure,
        }
    }
}

impl From<CancellationV1> for CancellationOutcome {
    fn from(value: CancellationV1) -> Self {
        match value {
            CancellationV1::NotSelected => Self::NotSelected,
            CancellationV1::Selected => Self::Selected,
        }
    }
}

impl From<AvailabilityV1> for RuntimeFactAvailability {
    fn from(value: AvailabilityV1) -> Self {
        match value {
            AvailabilityV1::Complete => Self::Complete,
            AvailabilityV1::Incomplete => Self::Incomplete,
            AvailabilityV1::Unavailable => Self::Unavailable,
        }
    }
}

impl From<EnforcementStatusV1> for ResourceEnforcementStatus {
    fn from(value: EnforcementStatusV1) -> Self {
        match value {
            EnforcementStatusV1::Not => Self::NotEnforced,
            EnforcementStatusV1::CaptureBound => Self::CaptureBoundEnforced,
            EnforcementStatusV1::SupervisorTimeout => Self::SupervisorTimeoutEnforced,
            EnforcementStatusV1::RuntimeLimit => Self::RuntimeLimitEnforced,
        }
    }
}

impl From<OutputStreamV1> for OutputStream {
    fn from(value: OutputStreamV1) -> Self {
        match value {
            OutputStreamV1::Stdout => Self::Stdout,
            OutputStreamV1::Stderr => Self::Stderr,
        }
    }
}

impl From<ExecutionPhase> for PhaseV1 {
    fn from(value: ExecutionPhase) -> Self {
        match value {
            ExecutionPhase::Compile => Self::Compile,
            ExecutionPhase::BuggyExecution => Self::BuggyExecution,
            ExecutionPhase::FixedExecution => Self::FixedExecution,
        }
    }
}

impl From<ProducerOutcome> for OutcomeV1 {
    fn from(value: ProducerOutcome) -> Self {
        match value {
            ProducerOutcome::Success => Self::Success,
            ProducerOutcome::CompilationFailure => Self::CompilationFailure,
            ProducerOutcome::TestFailure => Self::TestFailure,
            ProducerOutcome::Timeout => Self::Timeout,
            ProducerOutcome::Cancellation => Self::Cancellation,
            ProducerOutcome::ResourceBreach => Self::ResourceBreach,
            ProducerOutcome::RunnerFailure => Self::RunnerFailure,
        }
    }
}

impl From<ExecutionTestSummary> for TestSummaryV1 {
    fn from(value: ExecutionTestSummary) -> Self {
        match value {
            ExecutionTestSummary::JUnit(summary) => Self::JUnit {
                tests_run: summary.tests_run,
                failures: summary.failures,
            },
            ExecutionTestSummary::Defects4J { failing_test_count } => {
                Self::Defects4J { failing_test_count }
            }
        }
    }
}

impl From<crate::RuntimeMetadata> for RuntimeMetadataV1 {
    fn from(value: crate::RuntimeMetadata) -> Self {
        Self {
            operating_system: value.operating_system.to_owned(),
            architecture: value.architecture.to_owned(),
            process_id: RequiredOption(value.process_id),
        }
    }
}

impl From<&ProcessExit> for ProcessExitV1 {
    fn from(value: &ProcessExit) -> Self {
        match value {
            ProcessExit::NeverStarted => Self::NeverStarted,
            ProcessExit::ExitedWithCode(code) => Self::ExitedWithCode { code: *code },
            ProcessExit::ExitedWithoutCode => Self::ExitedWithoutCode,
            ProcessExit::TerminatedBySupervisor { reason, code } => Self::TerminatedBySupervisor {
                reason: (*reason).into(),
                code: RequiredOption(*code),
            },
        }
    }
}

impl From<SupervisorTermination> for SupervisorTerminationV1 {
    fn from(value: SupervisorTermination) -> Self {
        match value {
            SupervisorTermination::Timeout => Self::Timeout,
            SupervisorTermination::Cancellation => Self::Cancellation,
            SupervisorTermination::WaitFailure => Self::WaitFailure,
            SupervisorTermination::OutputCaptureFailure => Self::OutputCaptureFailure,
        }
    }
}

impl From<&TimeoutOutcome> for TimeoutV1 {
    fn from(value: &TimeoutOutcome) -> Self {
        match value {
            TimeoutOutcome::NotConfigured => Self::NotConfigured,
            TimeoutOutcome::NotTriggered { limit } => Self::NotTriggered {
                limit: (*limit).into(),
            },
            TimeoutOutcome::Triggered { limit } => Self::Triggered {
                limit: (*limit).into(),
            },
        }
    }
}

impl From<CancellationOutcome> for CancellationV1 {
    fn from(value: CancellationOutcome) -> Self {
        match value {
            CancellationOutcome::NotSelected => Self::NotSelected,
            CancellationOutcome::Selected => Self::Selected,
        }
    }
}

impl From<Duration> for ExactDurationV1 {
    fn from(value: Duration) -> Self {
        Self {
            seconds: value.as_secs(),
            nanoseconds: value.subsec_nanos(),
        }
    }
}

impl From<RuntimeFactAvailability> for AvailabilityV1 {
    fn from(value: RuntimeFactAvailability) -> Self {
        match value {
            RuntimeFactAvailability::Complete => Self::Complete,
            RuntimeFactAvailability::Incomplete => Self::Incomplete,
            RuntimeFactAvailability::Unavailable => Self::Unavailable,
        }
    }
}

impl From<&ResourceLimitObservation> for ResourceObservationV1 {
    fn from(value: &ResourceLimitObservation) -> Self {
        Self {
            kind: (&value.kind).into(),
            configured_limit: (&value.configured_limit).into(),
            observed_value: RequiredOption(value.observed_value.as_ref().map(Into::into)),
            enforcement_status: value.enforcement_status.into(),
            terminated_execution: value.terminated_execution,
            truncated: RequiredOption(value.truncated),
        }
    }
}

impl From<&ResourceLimitKind> for ResourceKindV1 {
    fn from(value: &ResourceLimitKind) -> Self {
        match value {
            ResourceLimitKind::CpuTime => Self::CpuTime,
            ResourceLimitKind::MemoryBytes => Self::MemoryBytes,
            ResourceLimitKind::DiskTempWorkspaceBytes => Self::DiskTempWorkspaceBytes,
            ResourceLimitKind::ProcessCount => Self::ProcessCount,
            ResourceLimitKind::FileCount => Self::FileCount,
            ResourceLimitKind::StdoutBytes => Self::StdoutBytes,
            ResourceLimitKind::StderrBytes => Self::StderrBytes,
            ResourceLimitKind::Timeout => Self::Timeout,
            ResourceLimitKind::Other(name) => Self::Other { name: name.clone() },
        }
    }
}

impl From<&ResourceLimitValue> for ResourceValueV1 {
    fn from(value: &ResourceLimitValue) -> Self {
        match value {
            ResourceLimitValue::Duration(value) => Self::Duration {
                value: (*value).into(),
            },
            ResourceLimitValue::Bytes(value) => Self::Bytes { value: *value },
            ResourceLimitValue::Count(value) => Self::Count { value: *value },
            ResourceLimitValue::Custom { value, unit } => Self::Custom {
                value: *value,
                unit: unit.clone(),
            },
        }
    }
}

impl From<ResourceEnforcementStatus> for EnforcementStatusV1 {
    fn from(value: ResourceEnforcementStatus) -> Self {
        match value {
            ResourceEnforcementStatus::NotEnforced => Self::Not,
            ResourceEnforcementStatus::CaptureBoundEnforced => Self::CaptureBound,
            ResourceEnforcementStatus::SupervisorTimeoutEnforced => Self::SupervisorTimeout,
            ResourceEnforcementStatus::RuntimeLimitEnforced => Self::RuntimeLimit,
        }
    }
}

impl From<&ExecutionFailure> for FailureV1 {
    fn from(value: &ExecutionFailure) -> Self {
        match value {
            ExecutionFailure::SpawnFailure { kind, .. } => Self::SpawnFailure {
                error_kind: (*kind).into(),
            },
            ExecutionFailure::NonZeroExit { code } => Self::NonZeroExit {
                code: RequiredOption(*code),
            },
            ExecutionFailure::Timeout => Self::Timeout,
            ExecutionFailure::Cancelled => Self::Cancelled,
            ExecutionFailure::WaitFailure { kind, .. } => Self::WaitFailure {
                error_kind: (*kind).into(),
            },
            ExecutionFailure::OutputCaptureFailure { stream, kind, .. } => {
                Self::OutputCaptureFailure {
                    stream: (*stream).into(),
                    error_kind: RequiredOption(kind.map(Into::into)),
                }
            }
            ExecutionFailure::TerminationFailure { kind, .. } => Self::TerminationFailure {
                error_kind: (*kind).into(),
            },
        }
    }
}

impl From<io::ErrorKind> for IoErrorKindV1 {
    fn from(value: io::ErrorKind) -> Self {
        match value {
            io::ErrorKind::NotFound => Self::NotFound,
            io::ErrorKind::PermissionDenied => Self::PermissionDenied,
            io::ErrorKind::ConnectionRefused => Self::ConnectionRefused,
            io::ErrorKind::ConnectionReset => Self::ConnectionReset,
            io::ErrorKind::HostUnreachable => Self::HostUnreachable,
            io::ErrorKind::NetworkUnreachable => Self::NetworkUnreachable,
            io::ErrorKind::ConnectionAborted => Self::ConnectionAborted,
            io::ErrorKind::NotConnected => Self::NotConnected,
            io::ErrorKind::AddrInUse => Self::AddrInUse,
            io::ErrorKind::AddrNotAvailable => Self::AddrNotAvailable,
            io::ErrorKind::NetworkDown => Self::NetworkDown,
            io::ErrorKind::BrokenPipe => Self::BrokenPipe,
            io::ErrorKind::AlreadyExists => Self::AlreadyExists,
            io::ErrorKind::WouldBlock => Self::WouldBlock,
            io::ErrorKind::NotADirectory => Self::NotADirectory,
            io::ErrorKind::IsADirectory => Self::IsADirectory,
            io::ErrorKind::DirectoryNotEmpty => Self::DirectoryNotEmpty,
            io::ErrorKind::ReadOnlyFilesystem => Self::ReadOnlyFilesystem,
            io::ErrorKind::StaleNetworkFileHandle => Self::StaleNetworkFileHandle,
            io::ErrorKind::InvalidInput => Self::InvalidInput,
            io::ErrorKind::InvalidData => Self::InvalidData,
            io::ErrorKind::TimedOut => Self::TimedOut,
            io::ErrorKind::WriteZero => Self::WriteZero,
            io::ErrorKind::StorageFull => Self::StorageFull,
            io::ErrorKind::NotSeekable => Self::NotSeekable,
            io::ErrorKind::QuotaExceeded => Self::QuotaExceeded,
            io::ErrorKind::FileTooLarge => Self::FileTooLarge,
            io::ErrorKind::ResourceBusy => Self::ResourceBusy,
            io::ErrorKind::ExecutableFileBusy => Self::ExecutableFileBusy,
            io::ErrorKind::Deadlock => Self::Deadlock,
            io::ErrorKind::CrossesDevices => Self::CrossesDevices,
            io::ErrorKind::TooManyLinks => Self::TooManyLinks,
            io::ErrorKind::InvalidFilename => Self::InvalidFilename,
            io::ErrorKind::ArgumentListTooLong => Self::ArgumentListTooLong,
            io::ErrorKind::Interrupted => Self::Interrupted,
            io::ErrorKind::Unsupported => Self::Unsupported,
            io::ErrorKind::UnexpectedEof => Self::UnexpectedEof,
            io::ErrorKind::OutOfMemory => Self::OutOfMemory,
            io::ErrorKind::Other => Self::Other,
            _ => Self::Uncategorized,
        }
    }
}

impl From<OutputStream> for OutputStreamV1 {
    fn from(value: OutputStream) -> Self {
        match value {
            OutputStream::Stdout => Self::Stdout,
            OutputStream::Stderr => Self::Stderr,
        }
    }
}

impl From<&BoundedOutputReference> for OutputReferenceV1 {
    fn from(value: &BoundedOutputReference) -> Self {
        Self {
            kind: value.kind().into(),
            logical_reference: value.reference().to_owned(),
            observed_bytes: value.observed_bytes(),
            retained_bytes: value.retained_bytes(),
            capture_limit_bytes: value.capture_limit_bytes(),
            truncated: value.truncated(),
        }
    }
}

impl From<ProducerOutputKind> for OutputKindV1 {
    fn from(value: ProducerOutputKind) -> Self {
        match value {
            ProducerOutputKind::Stdout => Self::Stdout,
            ProducerOutputKind::Stderr => Self::Stderr,
            ProducerOutputKind::Log => Self::Log,
            ProducerOutputKind::ProducedArtefact => Self::ProducedArtefact,
            ProducerOutputKind::Diagnostic => Self::Diagnostic,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{ExecutionExportError, SourceBudget, MAX_EXECUTION_EXPORT_BYTES};

    #[test]
    fn source_budget_checked_arithmetic_fails_closed() {
        let mut budget = SourceBudget {
            used: MAX_EXECUTION_EXPORT_BYTES - 1,
        };
        assert!(matches!(
            budget.add(usize::MAX),
            Err(ExecutionExportError::EnvelopeTooLarge)
        ));
        assert!(matches!(
            budget.add_items(usize::MAX, 2),
            Err(ExecutionExportError::EnvelopeTooLarge)
        ));
    }
}
