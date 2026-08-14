use crate::{
    CancellationOutcome, ExecutionFailure, ExecutionPhase, ProcessExit, ResourceEnforcementStatus,
    ResourceLimitKind, ResourceLimitObservation, RuntimeMetadata, SupervisorTermination,
    TimeoutOutcome,
};
use std::fmt;
use std::time::Duration;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ProducerResultError {
    EmptyValue(&'static str),
    UnknownPhase(String),
    InvalidOutput(&'static str),
    PhaseOutcomeMismatch,
    ContradictoryRuntimeFacts(&'static str),
}

impl fmt::Display for ProducerResultError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::EmptyValue(name) => write!(formatter, "{name} must not be empty"),
            Self::UnknownPhase(value) => write!(formatter, "unknown execution phase: {value}"),
            Self::InvalidOutput(message) => formatter.write_str(message),
            Self::PhaseOutcomeMismatch => {
                formatter.write_str("producer outcome does not apply to the execution phase")
            }
            Self::ContradictoryRuntimeFacts(message) => formatter.write_str(message),
        }
    }
}

impl std::error::Error for ProducerResultError {}

fn nonempty(value: &str, name: &'static str) -> Result<String, ProducerResultError> {
    if value.trim().is_empty() {
        Err(ProducerResultError::EmptyValue(name))
    } else {
        Ok(value.to_owned())
    }
}

/// Execution-owned identity for one Workflow-authorized result slot.
///
/// Queue and Evidence identities are deliberately not accepted:
///
/// ```compile_fail
/// use testgap_worker::ProducerResultId;
/// struct QueueMessageId(String);
/// impl From<QueueMessageId> for String {
///     fn from(value: QueueMessageId) -> Self { value.0 }
/// }
/// let queue_id = QueueMessageId("queue-1".to_owned());
/// let _ = ProducerResultId::new(queue_id);
/// ```
///
/// ```compile_fail
/// use testgap_worker::ProducerResultId;
/// struct ExecutionEvidenceId(String);
/// impl From<ExecutionEvidenceId> for String {
///     fn from(value: ExecutionEvidenceId) -> Self { value.0 }
/// }
/// let evidence_id = ExecutionEvidenceId("evidence-1".to_owned());
/// let _ = ProducerResultId::new(evidence_id);
/// ```
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct ProducerResultId(String);

impl ProducerResultId {
    pub fn new(value: &str) -> Result<Self, ProducerResultError> {
        nonempty(value, "producer_result_id").map(Self)
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

/// Opaque Workflow-owned reference; this crate does not create attempt semantics.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct WorkflowAttemptId(String);

impl WorkflowAttemptId {
    pub fn new(value: &str) -> Result<Self, ProducerResultError> {
        nonempty(value, "workflow_attempt_id").map(Self)
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct CandidateVersionReference(String);

impl CandidateVersionReference {
    pub fn new(value: &str) -> Result<Self, ProducerResultError> {
        nonempty(value, "candidate_version_reference").map(Self)
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct CorrelationReference(String);

impl CorrelationReference {
    pub fn new(value: &str) -> Result<Self, ProducerResultError> {
        nonempty(value, "correlation_reference").map(Self)
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl ExecutionPhase {
    pub const fn as_external_str(self) -> &'static str {
        match self {
            Self::Compile => "COMPILE",
            Self::BuggyExecution => "BUGGY_OR_TARGET_REVISION_TEST",
            Self::FixedExecution => "FIXED_OR_REFERENCE_REVISION_TEST",
        }
    }
}

impl TryFrom<&str> for ExecutionPhase {
    type Error = ProducerResultError;

    fn try_from(value: &str) -> Result<Self, Self::Error> {
        match value {
            "COMPILE" => Ok(Self::Compile),
            "BUGGY_OR_TARGET_REVISION_TEST" => Ok(Self::BuggyExecution),
            "FIXED_OR_REFERENCE_REVISION_TEST" => Ok(Self::FixedExecution),
            _ => Err(ProducerResultError::UnknownPhase(value.to_owned())),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum ProducerOutputKind {
    Stdout,
    Stderr,
    Log,
    ProducedArtefact,
    Diagnostic,
}

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct BoundedOutputReference {
    kind: ProducerOutputKind,
    reference: String,
    observed_bytes: u64,
    retained_bytes: u64,
    capture_limit_bytes: u64,
    truncated: bool,
}

impl BoundedOutputReference {
    pub const MAX_REFERENCE_BYTES: usize = 4 * 1024;

    pub fn new(
        kind: ProducerOutputKind,
        reference: &str,
        observed_bytes: u64,
        retained_bytes: u64,
        capture_limit_bytes: u64,
        truncated: bool,
    ) -> Result<Self, ProducerResultError> {
        let reference = nonempty(reference, "output_reference")?;
        if reference.len() > Self::MAX_REFERENCE_BYTES {
            return Err(ProducerResultError::InvalidOutput(
                "output reference exceeds the UTF-8 byte limit",
            ));
        }
        if retained_bytes > capture_limit_bytes {
            return Err(ProducerResultError::InvalidOutput(
                "retained output bytes exceed the capture limit",
            ));
        }
        if retained_bytes > observed_bytes {
            return Err(ProducerResultError::InvalidOutput(
                "retained output bytes exceed observed bytes",
            ));
        }
        if truncated != (observed_bytes > retained_bytes) {
            return Err(ProducerResultError::InvalidOutput(
                "output truncation flag contradicts byte counts",
            ));
        }
        Ok(Self {
            kind,
            reference,
            observed_bytes,
            retained_bytes,
            capture_limit_bytes,
            truncated,
        })
    }

    pub const fn kind(&self) -> ProducerOutputKind {
        self.kind
    }

    pub fn reference(&self) -> &str {
        &self.reference
    }

    pub const fn observed_bytes(&self) -> u64 {
        self.observed_bytes
    }

    pub const fn retained_bytes(&self) -> u64 {
        self.retained_bytes
    }

    pub const fn capture_limit_bytes(&self) -> u64 {
        self.capture_limit_bytes
    }

    pub const fn truncated(&self) -> bool {
        self.truncated
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RuntimeFactAvailability {
    Complete,
    Incomplete,
    Unavailable,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProducerRuntimeFacts {
    runtime_metadata: RuntimeMetadata,
    process_exit: ProcessExit,
    timeout: TimeoutOutcome,
    cancellation: CancellationOutcome,
    duration: Duration,
    availability: RuntimeFactAvailability,
    resource_observations: Vec<ResourceLimitObservation>,
    failures: Vec<ExecutionFailure>,
    output_references: Vec<BoundedOutputReference>,
}

impl ProducerRuntimeFacts {
    pub const MAX_OUTPUT_REFERENCES: usize = 128;
    pub const MAX_OUTPUT_REFERENCE_METADATA_BYTES: usize = 64 * 1024;

    pub fn new(
        runtime_metadata: RuntimeMetadata,
        process_exit: ProcessExit,
        duration: Duration,
    ) -> Self {
        Self {
            runtime_metadata,
            process_exit,
            timeout: TimeoutOutcome::NotConfigured,
            cancellation: CancellationOutcome::NotSelected,
            duration,
            availability: RuntimeFactAvailability::Complete,
            resource_observations: Vec::new(),
            failures: Vec::new(),
            output_references: Vec::new(),
        }
    }

    pub fn with_timeout(mut self, timeout: TimeoutOutcome) -> Self {
        self.timeout = timeout;
        self
    }

    pub fn with_cancellation(mut self, cancellation: CancellationOutcome) -> Self {
        self.cancellation = cancellation;
        self
    }

    pub fn with_availability(mut self, availability: RuntimeFactAvailability) -> Self {
        self.availability = availability;
        self
    }

    pub fn with_resource_observations(
        mut self,
        observations: impl IntoIterator<Item = ResourceLimitObservation>,
    ) -> Self {
        self.resource_observations = observations.into_iter().collect();
        self.resource_observations.sort();
        self
    }

    /// Failures retain their semantic order: primary classification first.
    pub fn with_failures(mut self, failures: Vec<ExecutionFailure>) -> Self {
        self.failures = failures;
        self
    }

    pub fn with_output_references(
        mut self,
        references: impl IntoIterator<Item = BoundedOutputReference>,
    ) -> Result<Self, ProducerResultError> {
        self.output_references = references.into_iter().collect();
        if self.output_references.len() > Self::MAX_OUTPUT_REFERENCES {
            return Err(ProducerResultError::InvalidOutput(
                "too many output references",
            ));
        }
        if self
            .output_references
            .iter()
            .map(|reference| reference.reference.len())
            .sum::<usize>()
            > Self::MAX_OUTPUT_REFERENCE_METADATA_BYTES
        {
            return Err(ProducerResultError::InvalidOutput(
                "output reference metadata exceeds the aggregate UTF-8 byte limit",
            ));
        }
        self.output_references.sort();
        Ok(self)
    }

    pub const fn runtime_metadata(&self) -> RuntimeMetadata {
        self.runtime_metadata
    }

    pub fn process_exit(&self) -> &ProcessExit {
        &self.process_exit
    }

    pub fn timeout(&self) -> &TimeoutOutcome {
        &self.timeout
    }

    pub const fn cancellation(&self) -> CancellationOutcome {
        self.cancellation
    }

    pub const fn duration(&self) -> Duration {
        self.duration
    }

    pub const fn availability(&self) -> RuntimeFactAvailability {
        self.availability
    }

    pub fn resource_observations(&self) -> &[ResourceLimitObservation] {
        &self.resource_observations
    }

    pub fn failures(&self) -> &[ExecutionFailure] {
        &self.failures
    }

    pub fn output_references(&self) -> &[BoundedOutputReference] {
        &self.output_references
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ProducerOutcome {
    Success,
    CompilationFailure,
    TestFailure,
    Timeout,
    Cancellation,
    ResourceBreach,
    RunnerFailure,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProducerResult {
    producer_result_id: ProducerResultId,
    workflow_attempt_id: WorkflowAttemptId,
    phase: ExecutionPhase,
    candidate_version_reference: Option<CandidateVersionReference>,
    correlation_reference: Option<CorrelationReference>,
    outcome: ProducerOutcome,
    runtime_facts: ProducerRuntimeFacts,
}

impl ProducerResult {
    pub fn new(
        producer_result_id: ProducerResultId,
        workflow_attempt_id: WorkflowAttemptId,
        phase: ExecutionPhase,
        outcome: ProducerOutcome,
        runtime_facts: ProducerRuntimeFacts,
    ) -> Result<Self, ProducerResultError> {
        validate_runtime_facts(phase, outcome, &runtime_facts)?;
        Ok(Self {
            producer_result_id,
            workflow_attempt_id,
            phase,
            candidate_version_reference: None,
            correlation_reference: None,
            outcome,
            runtime_facts,
        })
    }

    pub fn with_candidate_version_reference(
        mut self,
        reference: CandidateVersionReference,
    ) -> Self {
        self.candidate_version_reference = Some(reference);
        self
    }

    pub fn with_correlation_reference(mut self, reference: CorrelationReference) -> Self {
        self.correlation_reference = Some(reference);
        self
    }

    pub fn producer_result_id(&self) -> &ProducerResultId {
        &self.producer_result_id
    }

    pub fn workflow_attempt_id(&self) -> &WorkflowAttemptId {
        &self.workflow_attempt_id
    }

    pub const fn phase(&self) -> ExecutionPhase {
        self.phase
    }

    pub fn candidate_version_reference(&self) -> Option<&CandidateVersionReference> {
        self.candidate_version_reference.as_ref()
    }

    pub fn correlation_reference(&self) -> Option<&CorrelationReference> {
        self.correlation_reference.as_ref()
    }

    pub const fn outcome(&self) -> ProducerOutcome {
        self.outcome
    }

    pub fn runtime_facts(&self) -> &ProducerRuntimeFacts {
        &self.runtime_facts
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ProducerResultComparison {
    DuplicateConvergent,
    Conflict,
    Independent,
}

pub fn compare_producer_results(
    existing: &ProducerResult,
    incoming: &ProducerResult,
) -> ProducerResultComparison {
    if existing.producer_result_id != incoming.producer_result_id {
        ProducerResultComparison::Independent
    } else if existing == incoming {
        ProducerResultComparison::DuplicateConvergent
    } else {
        ProducerResultComparison::Conflict
    }
}

fn validate_runtime_facts(
    phase: ExecutionPhase,
    outcome: ProducerOutcome,
    facts: &ProducerRuntimeFacts,
) -> Result<(), ProducerResultError> {
    if matches!(outcome, ProducerOutcome::CompilationFailure) && phase != ExecutionPhase::Compile
        || matches!(outcome, ProducerOutcome::TestFailure) && phase == ExecutionPhase::Compile
    {
        return Err(ProducerResultError::PhaseOutcomeMismatch);
    }

    let timeout_triggered = matches!(facts.timeout, TimeoutOutcome::Triggered { .. });
    let cancellation_selected = facts.cancellation == CancellationOutcome::Selected;
    let resource_breach = facts.resource_observations.iter().any(|observation| {
        observation.terminated_execution && observation.kind != ResourceLimitKind::Timeout
    });
    if usize::from(timeout_triggered)
        + usize::from(cancellation_selected)
        + usize::from(resource_breach)
        > 1
    {
        return Err(ProducerResultError::ContradictoryRuntimeFacts(
            "multiple incompatible terminal runtime facts were supplied",
        ));
    }

    for observation in facts
        .resource_observations
        .iter()
        .filter(|observation| observation.kind == ResourceLimitKind::Timeout)
    {
        if observation.terminated_execution != timeout_triggered {
            return Err(ProducerResultError::ContradictoryRuntimeFacts(
                "timeout resource observation contradicts timeout outcome",
            ));
        }
    }
    if facts.resource_observations.iter().any(|observation| {
        observation.terminated_execution
            && matches!(
                observation.enforcement_status,
                ResourceEnforcementStatus::NotEnforced
                    | ResourceEnforcementStatus::CaptureBoundEnforced
            )
    }) {
        return Err(ProducerResultError::ContradictoryRuntimeFacts(
            "terminating resource observation was not enforced",
        ));
    }

    validate_primary_failure(facts)?;

    let recorded_timeout = facts
        .failures
        .iter()
        .any(|failure| matches!(failure, ExecutionFailure::Timeout));
    let recorded_cancellation = facts
        .failures
        .iter()
        .any(|failure| matches!(failure, ExecutionFailure::Cancelled));
    if recorded_timeout != timeout_triggered || recorded_cancellation != cancellation_selected {
        return Err(ProducerResultError::ContradictoryRuntimeFacts(
            "terminal failure classification contradicts runtime observations",
        ));
    }

    match facts.process_exit {
        ProcessExit::TerminatedBySupervisor {
            reason: SupervisorTermination::Timeout,
            ..
        } if !timeout_triggered => {
            return Err(ProducerResultError::ContradictoryRuntimeFacts(
                "timeout termination lacks a triggered timeout observation",
            ));
        }
        ProcessExit::TerminatedBySupervisor {
            reason: SupervisorTermination::Cancellation,
            ..
        } if !cancellation_selected => {
            return Err(ProducerResultError::ContradictoryRuntimeFacts(
                "cancellation termination lacks a selected cancellation observation",
            ));
        }
        _ => {}
    }

    let has_runner_failure = facts.failures.iter().any(|failure| {
        !matches!(
            failure,
            ExecutionFailure::NonZeroExit { .. }
                | ExecutionFailure::Timeout
                | ExecutionFailure::Cancelled
        )
    });

    let valid = match outcome {
        ProducerOutcome::Success => {
            facts.process_exit == ProcessExit::ExitedWithCode(0)
                && facts.failures.is_empty()
                && !timeout_triggered
                && !cancellation_selected
                && !resource_breach
                && facts.availability == RuntimeFactAvailability::Complete
        }
        ProducerOutcome::CompilationFailure | ProducerOutcome::TestFailure => {
            nonzero_exit_matches(facts)
                && !has_runner_failure
                && !timeout_triggered
                && !cancellation_selected
                && !resource_breach
        }
        ProducerOutcome::Timeout => {
            timeout_triggered
                && matches!(
                    facts.process_exit,
                    ProcessExit::TerminatedBySupervisor {
                        reason: SupervisorTermination::Timeout,
                        ..
                    }
                )
                && matches!(facts.failures.first(), Some(ExecutionFailure::Timeout))
        }
        ProducerOutcome::Cancellation => {
            cancellation_selected
                && matches!(
                    facts.process_exit,
                    ProcessExit::TerminatedBySupervisor {
                        reason: SupervisorTermination::Cancellation,
                        ..
                    }
                )
                && matches!(facts.failures.first(), Some(ExecutionFailure::Cancelled))
        }
        ProducerOutcome::ResourceBreach => resource_breach && nonzero_exit_matches(facts),
        ProducerOutcome::RunnerFailure => {
            has_runner_failure && !timeout_triggered && !cancellation_selected && !resource_breach
        }
    };

    if !valid {
        return Err(ProducerResultError::ContradictoryRuntimeFacts(
            "producer outcome contradicts runtime facts",
        ));
    }
    if facts.availability == RuntimeFactAvailability::Unavailable
        && facts.process_exit != ProcessExit::NeverStarted
    {
        return Err(ProducerResultError::ContradictoryRuntimeFacts(
            "unavailable runtime facts require a process that never started",
        ));
    }
    Ok(())
}

fn validate_primary_failure(facts: &ProducerRuntimeFacts) -> Result<(), ProducerResultError> {
    let process_started = facts.runtime_metadata.process_id.is_some();
    if matches!(facts.process_exit, ProcessExit::NeverStarted) == process_started {
        return Err(ProducerResultError::ContradictoryRuntimeFacts(
            "process exit contradicts process ID availability",
        ));
    }

    if facts
        .failures
        .iter()
        .any(|failure| matches!(failure, ExecutionFailure::SpawnFailure { .. }))
    {
        if facts.failures.len() == 1
            && facts.process_exit == ProcessExit::NeverStarted
            && !process_started
        {
            return Ok(());
        }
        return Err(ProducerResultError::ContradictoryRuntimeFacts(
            "spawn failure requires the sole failure from a process that never started",
        ));
    }

    let compatible = match facts.failures.first() {
        Some(ExecutionFailure::SpawnFailure { .. }) => false,
        Some(ExecutionFailure::NonZeroExit { .. }) => nonzero_exit_matches(facts),
        Some(ExecutionFailure::Timeout) => matches!(
            facts.process_exit,
            ProcessExit::TerminatedBySupervisor {
                reason: SupervisorTermination::Timeout,
                ..
            }
        ),
        Some(ExecutionFailure::Cancelled) => matches!(
            facts.process_exit,
            ProcessExit::TerminatedBySupervisor {
                reason: SupervisorTermination::Cancellation,
                ..
            }
        ),
        Some(ExecutionFailure::WaitFailure { .. }) => matches!(
            facts.process_exit,
            ProcessExit::TerminatedBySupervisor {
                reason: SupervisorTermination::WaitFailure,
                ..
            }
        ),
        Some(ExecutionFailure::OutputCaptureFailure { .. }) => matches!(
            facts.process_exit,
            ProcessExit::ExitedWithCode(0)
                | ProcessExit::TerminatedBySupervisor {
                    reason: SupervisorTermination::OutputCaptureFailure,
                    ..
                }
        ),
        Some(ExecutionFailure::TerminationFailure { .. }) => false,
        None => true,
    };
    if compatible {
        Ok(())
    } else {
        Err(ProducerResultError::ContradictoryRuntimeFacts(
            "primary runtime failure contradicts process exit",
        ))
    }
}

fn nonzero_exit_matches(facts: &ProducerRuntimeFacts) -> bool {
    match (&facts.process_exit, facts.failures.first()) {
        (
            ProcessExit::ExitedWithCode(exit_code),
            Some(ExecutionFailure::NonZeroExit {
                code: Some(failure_code),
            }),
        ) => *exit_code != 0 && exit_code == failure_code,
        (ProcessExit::ExitedWithoutCode, Some(ExecutionFailure::NonZeroExit { code: None })) => {
            true
        }
        _ => false,
    }
}
