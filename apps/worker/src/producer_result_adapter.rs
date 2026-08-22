//! Execution-owned conversion of runtime results into producer results.
//!
//! This adapter consumes an [`ExecutionResult`] plus caller-supplied
//! identities and logical output references, and produces a validated
//! [`ProducerResult`]. It generates no identities, embeds no raw output
//! bytes, and performs no persistence.

use crate::{
    BoundedOutput, BoundedOutputReference, CancellationOutcome, CandidateVersionReference,
    CorrelationReference, ExecutionFailure, ExecutionPhase, ExecutionResult, ProcessExit,
    ProducerOutcome, ProducerOutputKind, ProducerResult, ProducerResultError, ProducerResultId,
    ProducerRuntimeFacts, ResourceEnforcementStatus, RuntimeFactAvailability,
    SupervisorTermination, TimeoutOutcome, WorkflowAttemptId,
};
use std::fmt;

/// Typed conversion error. Contradictory execution facts fail closed.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ProducerResultConversionError {
    /// The execution result's runtime facts contradict each other, so no
    /// deterministic producer outcome exists.
    ContradictoryRuntimeFacts(&'static str),
    /// The converted value was rejected by authoritative producer-result
    /// validation.
    InvalidProducerResult(ProducerResultError),
}

impl fmt::Display for ProducerResultConversionError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::ContradictoryRuntimeFacts(reason) => {
                write!(formatter, "contradictory execution runtime facts: {reason}")
            }
            Self::InvalidProducerResult(error) => {
                write!(formatter, "converted producer result is invalid: {error}")
            }
        }
    }
}

impl std::error::Error for ProducerResultConversionError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::InvalidProducerResult(error) => Some(error),
            Self::ContradictoryRuntimeFacts(_) => None,
        }
    }
}

impl From<ProducerResultError> for ProducerResultConversionError {
    fn from(error: ProducerResultError) -> Self {
        Self::InvalidProducerResult(error)
    }
}

/// Caller-supplied optional references for a producer-result conversion.
///
/// The adapter never creates these values; it only carries them through.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct ProducerResultReferences<'a> {
    pub candidate_version_reference: Option<&'a CandidateVersionReference>,
    pub correlation_reference: Option<&'a CorrelationReference>,
    pub stdout_logical_reference: Option<&'a str>,
    pub stderr_logical_reference: Option<&'a str>,
}

/// Converts an [`ExecutionResult`] into a validated [`ProducerResult`].
///
/// - Identities come only from the caller; none are generated.
/// - Phase is copied exactly and never inferred from command, path, exit
///   code, output, or workflow state.
/// - `ExecutionResult.failures` order is preserved exactly; `failures[0]`
///   remains the primary classification.
/// - Raw stdout/stderr bytes are never embedded; only bounded reference
///   metadata for caller-supplied logical references is recorded.
pub fn producer_result_from_execution(
    execution: &ExecutionResult,
    producer_result_id: ProducerResultId,
    workflow_attempt_id: WorkflowAttemptId,
    references: ProducerResultReferences<'_>,
) -> Result<ProducerResult, ProducerResultConversionError> {
    let timeout_triggered = matches!(execution.timeout, TimeoutOutcome::Triggered { .. });
    let cancellation_selected = execution.cancellation == CancellationOutcome::Selected;
    let resource_breach = classify_resource_breach(execution)?;

    ensure_coherent_runtime_facts(
        execution,
        timeout_triggered,
        cancellation_selected,
        resource_breach,
    )?;

    let (outcome, availability) = classify_outcome(
        execution,
        timeout_triggered,
        cancellation_selected,
        resource_breach,
    )?;

    let runtime_facts = ProducerRuntimeFacts::new(
        execution.runtime_metadata,
        execution.process_exit.clone(),
        execution.duration,
    )
    .with_timeout(execution.timeout.clone())
    .with_cancellation(execution.cancellation)
    .with_availability(availability)
    .with_resource_observations(execution.resource_observations.clone())
    .with_failures(execution.failures.clone())
    .with_output_references(build_output_references(execution, references)?)?;

    let mut result = ProducerResult::new(
        producer_result_id,
        workflow_attempt_id,
        execution.phase,
        outcome,
        runtime_facts,
    )?;

    if let Some(candidate) = references.candidate_version_reference {
        result = result.with_candidate_version_reference(candidate.clone());
    }
    if let Some(correlation) = references.correlation_reference {
        result = result.with_correlation_reference(correlation.clone());
    }
    Ok(result)
}

fn ensure_coherent_runtime_facts(
    execution: &ExecutionResult,
    timeout_triggered: bool,
    cancellation_selected: bool,
    resource_breach: bool,
) -> Result<(), ProducerResultConversionError> {
    let process_started = execution.runtime_metadata.process_id.is_some();
    if (execution.process_exit == ProcessExit::NeverStarted) == process_started {
        return Err(ProducerResultConversionError::ContradictoryRuntimeFacts(
            "process exit contradicts process identity",
        ));
    }

    if usize::from(timeout_triggered)
        + usize::from(cancellation_selected)
        + usize::from(resource_breach)
        > 1
    {
        return Err(ProducerResultConversionError::ContradictoryRuntimeFacts(
            "multiple incompatible terminal runtime facts were supplied",
        ));
    }

    if timeout_triggered && !terminal_shape_matches(execution, SupervisorTermination::Timeout) {
        return Err(ProducerResultConversionError::ContradictoryRuntimeFacts(
            "triggered timeout lacks coherent timeout termination facts",
        ));
    }
    if cancellation_selected
        && !terminal_shape_matches(execution, SupervisorTermination::Cancellation)
    {
        return Err(ProducerResultConversionError::ContradictoryRuntimeFacts(
            "selected cancellation lacks coherent cancellation termination facts",
        ));
    }
    if resource_breach && !nonzero_exit_is_primary(execution) {
        return Err(ProducerResultConversionError::ContradictoryRuntimeFacts(
            "terminating resource observation contradicts process exit",
        ));
    }
    Ok(())
}

fn terminal_shape_matches(execution: &ExecutionResult, expected: SupervisorTermination) -> bool {
    let (reason_matches, primary_matches) =
        match (&execution.process_exit, execution.failures.first()) {
            (ProcessExit::TerminatedBySupervisor { reason, .. }, Some(primary)) => (
                *reason == expected,
                matches!(
                    (expected, primary),
                    (SupervisorTermination::Timeout, ExecutionFailure::Timeout)
                        | (
                            SupervisorTermination::Cancellation,
                            ExecutionFailure::Cancelled
                        )
                ),
            ),
            _ => (false, false),
        };
    reason_matches && primary_matches
}

fn classify_outcome(
    execution: &ExecutionResult,
    timeout_triggered: bool,
    cancellation_selected: bool,
    resource_breach: bool,
) -> Result<(ProducerOutcome, RuntimeFactAvailability), ProducerResultConversionError> {
    if execution
        .failures
        .iter()
        .any(|failure| matches!(failure, ExecutionFailure::SpawnFailure { .. }))
    {
        if execution.failures.len() != 1 {
            return Err(ProducerResultConversionError::ContradictoryRuntimeFacts(
                "spawn failure must be the sole runtime failure",
            ));
        }
        return Ok((
            ProducerOutcome::RunnerFailure,
            RuntimeFactAvailability::Unavailable,
        ));
    }

    if timeout_triggered {
        return Ok((ProducerOutcome::Timeout, started_availability(execution)));
    }
    if cancellation_selected {
        return Ok((
            ProducerOutcome::Cancellation,
            started_availability(execution),
        ));
    }
    if resource_breach {
        return Ok((
            ProducerOutcome::ResourceBreach,
            started_availability(execution),
        ));
    }

    if has_infrastructure_failure(execution) {
        if matches!(
            execution.failures.first(),
            Some(ExecutionFailure::TerminationFailure { .. })
        ) {
            return Err(ProducerResultConversionError::ContradictoryRuntimeFacts(
                "termination failure cannot be the primary runtime failure",
            ));
        }
        return Ok((
            ProducerOutcome::RunnerFailure,
            RuntimeFactAvailability::Incomplete,
        ));
    }

    match (&execution.process_exit, execution.failures.first()) {
        (ProcessExit::ExitedWithCode(0), None) => {
            Ok((ProducerOutcome::Success, RuntimeFactAvailability::Complete))
        }
        (_, Some(ExecutionFailure::NonZeroExit { .. })) if nonzero_exit_is_primary(execution) => {
            Ok((
                phase_failure_outcome(execution.phase),
                RuntimeFactAvailability::Complete,
            ))
        }
        _ => Err(ProducerResultConversionError::ContradictoryRuntimeFacts(
            "runtime facts do not determine a producer outcome",
        )),
    }
}

fn phase_failure_outcome(phase: ExecutionPhase) -> ProducerOutcome {
    match phase {
        ExecutionPhase::Compile => ProducerOutcome::CompilationFailure,
        ExecutionPhase::BuggyExecution | ExecutionPhase::FixedExecution => {
            ProducerOutcome::TestFailure
        }
    }
}

fn started_availability(execution: &ExecutionResult) -> RuntimeFactAvailability {
    if has_infrastructure_failure(execution) {
        RuntimeFactAvailability::Incomplete
    } else {
        RuntimeFactAvailability::Complete
    }
}

fn has_infrastructure_failure(execution: &ExecutionResult) -> bool {
    execution.failures.iter().any(|failure| {
        matches!(
            failure,
            ExecutionFailure::WaitFailure { .. }
                | ExecutionFailure::OutputCaptureFailure { .. }
                | ExecutionFailure::TerminationFailure { .. }
        )
    })
}

/// Classifies whether the execution terminated because of a runtime-enforced
/// non-timeout resource limit.
///
/// Only a terminating non-timeout observation whose enforcement status is
/// [`ResourceEnforcementStatus::RuntimeLimitEnforced`] qualifies as a real
/// resource breach. Any other enforcement status on a terminating non-timeout
/// observation is a contradictory runtime fact and fails closed.
fn classify_resource_breach(
    execution: &ExecutionResult,
) -> Result<bool, ProducerResultConversionError> {
    let mut breach = false;
    for observation in &execution.resource_observations {
        if !observation.terminated_execution
            || observation.kind == crate::ResourceLimitKind::Timeout
        {
            continue;
        }
        match observation.enforcement_status {
            ResourceEnforcementStatus::RuntimeLimitEnforced => breach = true,
            ResourceEnforcementStatus::NotEnforced
            | ResourceEnforcementStatus::CaptureBoundEnforced
            | ResourceEnforcementStatus::SupervisorTimeoutEnforced => {
                return Err(ProducerResultConversionError::ContradictoryRuntimeFacts(
                    "terminating non-timeout resource observation was not enforced as a runtime limit",
                ));
            }
        }
    }
    Ok(breach)
}

fn nonzero_exit_is_primary(execution: &ExecutionResult) -> bool {
    match (&execution.process_exit, execution.failures.first()) {
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

fn build_output_references(
    execution: &ExecutionResult,
    references: ProducerResultReferences<'_>,
) -> Result<Vec<BoundedOutputReference>, ProducerResultConversionError> {
    let mut output_references = Vec::new();
    if let Some(reference) = references.stdout_logical_reference {
        output_references.push(bounded_reference(
            ProducerOutputKind::Stdout,
            reference,
            &execution.stdout,
        )?);
    }
    if let Some(reference) = references.stderr_logical_reference {
        output_references.push(bounded_reference(
            ProducerOutputKind::Stderr,
            reference,
            &execution.stderr,
        )?);
    }
    Ok(output_references)
}

fn bounded_reference(
    kind: ProducerOutputKind,
    reference: &str,
    output: &BoundedOutput,
) -> Result<BoundedOutputReference, ProducerResultConversionError> {
    BoundedOutputReference::new(
        kind,
        reference,
        output.total_bytes_observed,
        u64::try_from(output.captured_bytes.len()).unwrap_or(u64::MAX),
        output.capture_limit_bytes,
        output.truncated,
    )
    .map_err(ProducerResultConversionError::from)
}
