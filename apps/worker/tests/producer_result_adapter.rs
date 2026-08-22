use std::io;
use std::time::Duration;

use testgap_worker::{
    producer_result_from_execution, BoundedOutput, CancellationOutcome, CandidateVersionReference,
    CorrelationReference, ExecutionFailure, ExecutionPhase, ExecutionResult, OutputStream,
    ProcessExit, ProducerOutcome, ProducerResult, ProducerResultConversionError,
    ProducerResultError, ProducerResultId, ProducerResultReferences, ResourceEnforcementStatus,
    ResourceLimitKind, ResourceLimitObservation, ResourceLimitValue, RuntimeFactAvailability,
    RuntimeMetadata, SupervisorTermination, TimeoutOutcome, WorkflowAttemptId,
};

const CAPTURE_LIMIT: u64 = 1024;

fn metadata(process_id: Option<u32>) -> RuntimeMetadata {
    RuntimeMetadata {
        operating_system: "test-os",
        architecture: "test-arch",
        process_id,
    }
}

fn bounded_output(
    total_bytes_observed: u64,
    retained_len: usize,
    truncated: bool,
) -> BoundedOutput {
    BoundedOutput {
        captured_bytes: vec![b'x'; retained_len],
        total_bytes_observed,
        capture_limit_bytes: CAPTURE_LIMIT,
        truncated,
    }
}

fn execution(
    phase: ExecutionPhase,
    process_exit: ProcessExit,
    timeout: TimeoutOutcome,
    cancellation: CancellationOutcome,
    failures: Vec<ExecutionFailure>,
) -> ExecutionResult {
    let process_id = if process_exit == ProcessExit::NeverStarted {
        None
    } else {
        Some(4242)
    };
    ExecutionResult {
        phase,
        runtime_metadata: metadata(process_id),
        process_exit,
        timeout,
        cancellation,
        stdout: BoundedOutput::empty(CAPTURE_LIMIT),
        stderr: BoundedOutput::empty(CAPTURE_LIMIT),
        duration: Duration::from_millis(25),
        resource_observations: Vec::new(),
        failures,
    }
}

fn success_execution(phase: ExecutionPhase) -> ExecutionResult {
    execution(
        phase,
        ProcessExit::ExitedWithCode(0),
        TimeoutOutcome::NotConfigured,
        CancellationOutcome::NotSelected,
        Vec::new(),
    )
}

fn nonzero_execution(phase: ExecutionPhase, code: Option<i32>) -> ExecutionResult {
    let process_exit = match code {
        Some(code) => ProcessExit::ExitedWithCode(code),
        None => ProcessExit::ExitedWithoutCode,
    };
    execution(
        phase,
        process_exit,
        TimeoutOutcome::NotConfigured,
        CancellationOutcome::NotSelected,
        vec![ExecutionFailure::NonZeroExit { code }],
    )
}

fn timeout_execution() -> ExecutionResult {
    execution(
        ExecutionPhase::BuggyExecution,
        ProcessExit::TerminatedBySupervisor {
            reason: SupervisorTermination::Timeout,
            code: None,
        },
        TimeoutOutcome::Triggered {
            limit: Duration::from_secs(30),
        },
        CancellationOutcome::NotSelected,
        vec![ExecutionFailure::Timeout],
    )
}

fn cancellation_execution() -> ExecutionResult {
    execution(
        ExecutionPhase::BuggyExecution,
        ProcessExit::TerminatedBySupervisor {
            reason: SupervisorTermination::Cancellation,
            code: None,
        },
        TimeoutOutcome::NotConfigured,
        CancellationOutcome::Selected,
        vec![ExecutionFailure::Cancelled],
    )
}

fn spawn_failure_execution() -> ExecutionResult {
    execution(
        ExecutionPhase::Compile,
        ProcessExit::NeverStarted,
        TimeoutOutcome::NotConfigured,
        CancellationOutcome::NotSelected,
        vec![ExecutionFailure::SpawnFailure {
            kind: io::ErrorKind::NotFound,
            message: "toolchain missing".to_owned(),
        }],
    )
}

fn terminating_resource_observation() -> ResourceLimitObservation {
    terminating_observation_with_status(ResourceEnforcementStatus::RuntimeLimitEnforced)
}

fn terminating_observation_with_status(
    enforcement_status: ResourceEnforcementStatus,
) -> ResourceLimitObservation {
    ResourceLimitObservation {
        kind: ResourceLimitKind::MemoryBytes,
        configured_limit: ResourceLimitValue::Bytes(512),
        observed_value: Some(ResourceLimitValue::Bytes(1024)),
        enforcement_status,
        terminated_execution: true,
        truncated: None,
    }
}

fn convert(
    execution_result: &ExecutionResult,
) -> Result<ProducerResult, ProducerResultConversionError> {
    producer_result_from_execution(
        execution_result,
        ProducerResultId::new("result-1").unwrap(),
        WorkflowAttemptId::new("attempt-9").unwrap(),
        ProducerResultReferences::default(),
    )
}

#[test]
fn compile_success_maps_to_success() {
    let result = convert(&success_execution(ExecutionPhase::Compile)).unwrap();
    assert_eq!(result.outcome(), ProducerOutcome::Success);
}

#[test]
fn buggy_success_maps_to_success() {
    let result = convert(&success_execution(ExecutionPhase::BuggyExecution)).unwrap();
    assert_eq!(result.outcome(), ProducerOutcome::Success);
}

#[test]
fn fixed_success_maps_to_success() {
    let result = convert(&success_execution(ExecutionPhase::FixedExecution)).unwrap();
    assert_eq!(result.outcome(), ProducerOutcome::Success);
}

#[test]
fn compile_nonzero_exit_maps_to_compilation_failure() {
    let result = convert(&nonzero_execution(ExecutionPhase::Compile, Some(1))).unwrap();
    assert_eq!(result.outcome(), ProducerOutcome::CompilationFailure);
}

#[test]
fn buggy_nonzero_exit_maps_to_test_failure() {
    let result = convert(&nonzero_execution(ExecutionPhase::BuggyExecution, Some(2))).unwrap();
    assert_eq!(result.outcome(), ProducerOutcome::TestFailure);
}

#[test]
fn fixed_nonzero_exit_maps_to_test_failure() {
    let result = convert(&nonzero_execution(ExecutionPhase::FixedExecution, Some(3))).unwrap();
    assert_eq!(result.outcome(), ProducerOutcome::TestFailure);
}

#[test]
fn exited_without_code_with_nonzero_failure_maps_by_phase() {
    let buggy = convert(&nonzero_execution(ExecutionPhase::BuggyExecution, None)).unwrap();
    assert_eq!(buggy.outcome(), ProducerOutcome::TestFailure);

    let compile = convert(&nonzero_execution(ExecutionPhase::Compile, None)).unwrap();
    assert_eq!(compile.outcome(), ProducerOutcome::CompilationFailure);
}

#[test]
fn triggered_timeout_maps_to_timeout() {
    let result = convert(&timeout_execution()).unwrap();
    assert_eq!(result.outcome(), ProducerOutcome::Timeout);
    assert_eq!(
        result.runtime_facts().timeout(),
        &TimeoutOutcome::Triggered {
            limit: Duration::from_secs(30)
        }
    );
    assert_eq!(
        result.runtime_facts().availability(),
        RuntimeFactAvailability::Complete
    );
}

#[test]
fn selected_cancellation_maps_to_cancellation() {
    let result = convert(&cancellation_execution()).unwrap();
    assert_eq!(result.outcome(), ProducerOutcome::Cancellation);
    assert_eq!(
        result.runtime_facts().availability(),
        RuntimeFactAvailability::Complete
    );
}

#[test]
fn enforced_non_timeout_termination_maps_to_resource_breach() {
    let mut execution_result = nonzero_execution(ExecutionPhase::BuggyExecution, Some(137));
    execution_result
        .resource_observations
        .push(terminating_resource_observation());

    let result = convert(&execution_result).unwrap();
    assert_eq!(result.outcome(), ProducerOutcome::ResourceBreach);
}

#[test]
fn supervisor_timeout_enforced_non_timeout_termination_fails_closed() {
    let mut execution_result = nonzero_execution(ExecutionPhase::BuggyExecution, Some(137));
    execution_result
        .resource_observations
        .push(terminating_observation_with_status(
            ResourceEnforcementStatus::SupervisorTimeoutEnforced,
        ));

    assert_eq!(
        convert(&execution_result).unwrap_err(),
        ProducerResultConversionError::ContradictoryRuntimeFacts(
            "terminating non-timeout resource observation was not enforced as a runtime limit"
        )
    );
}

#[test]
fn not_enforced_non_timeout_termination_fails_closed() {
    let mut execution_result = nonzero_execution(ExecutionPhase::BuggyExecution, Some(137));
    execution_result
        .resource_observations
        .push(terminating_observation_with_status(
            ResourceEnforcementStatus::NotEnforced,
        ));

    assert_eq!(
        convert(&execution_result).unwrap_err(),
        ProducerResultConversionError::ContradictoryRuntimeFacts(
            "terminating non-timeout resource observation was not enforced as a runtime limit"
        )
    );
}

#[test]
fn capture_bound_enforced_non_timeout_termination_fails_closed() {
    let mut execution_result = nonzero_execution(ExecutionPhase::BuggyExecution, Some(137));
    execution_result
        .resource_observations
        .push(terminating_observation_with_status(
            ResourceEnforcementStatus::CaptureBoundEnforced,
        ));

    assert_eq!(
        convert(&execution_result).unwrap_err(),
        ProducerResultConversionError::ContradictoryRuntimeFacts(
            "terminating non-timeout resource observation was not enforced as a runtime limit"
        )
    );
}

#[test]
fn spawn_failure_maps_to_runner_failure_and_unavailable_facts() {
    let result = convert(&spawn_failure_execution()).unwrap();
    assert_eq!(result.outcome(), ProducerOutcome::RunnerFailure);
    assert_eq!(
        result.runtime_facts().availability(),
        RuntimeFactAvailability::Unavailable
    );
}

#[test]
fn wait_failure_maps_to_runner_failure_with_incomplete_facts() {
    let execution_result = execution(
        ExecutionPhase::Compile,
        ProcessExit::TerminatedBySupervisor {
            reason: SupervisorTermination::WaitFailure,
            code: None,
        },
        TimeoutOutcome::NotConfigured,
        CancellationOutcome::NotSelected,
        vec![ExecutionFailure::WaitFailure {
            kind: io::ErrorKind::Interrupted,
            message: "wait interrupted".to_owned(),
        }],
    );

    let result = convert(&execution_result).unwrap();
    assert_eq!(result.outcome(), ProducerOutcome::RunnerFailure);
    assert_eq!(
        result.runtime_facts().availability(),
        RuntimeFactAvailability::Incomplete
    );
}

#[test]
fn output_capture_failure_after_clean_exit_maps_to_runner_failure() {
    let mut execution_result = success_execution(ExecutionPhase::Compile);
    execution_result
        .failures
        .push(ExecutionFailure::OutputCaptureFailure {
            stream: OutputStream::Stdout,
            kind: Some(io::ErrorKind::UnexpectedEof),
            message: "stdout pipe closed early".to_owned(),
        });

    let result = convert(&execution_result).unwrap();
    assert_eq!(result.outcome(), ProducerOutcome::RunnerFailure);
    assert_eq!(
        result.runtime_facts().availability(),
        RuntimeFactAvailability::Incomplete
    );
}

#[test]
fn output_capture_failure_termination_maps_to_runner_failure() {
    let execution_result = execution(
        ExecutionPhase::Compile,
        ProcessExit::TerminatedBySupervisor {
            reason: SupervisorTermination::OutputCaptureFailure,
            code: None,
        },
        TimeoutOutcome::NotConfigured,
        CancellationOutcome::NotSelected,
        vec![ExecutionFailure::OutputCaptureFailure {
            stream: OutputStream::Stderr,
            kind: None,
            message: "spawned child had no stderr pipe".to_owned(),
        }],
    );

    let result = convert(&execution_result).unwrap();
    assert_eq!(result.outcome(), ProducerOutcome::RunnerFailure);
    assert_eq!(
        result.runtime_facts().availability(),
        RuntimeFactAvailability::Incomplete
    );
}

#[test]
fn primary_failure_remains_first_in_converted_facts() {
    let mut execution_result = timeout_execution();
    execution_result
        .failures
        .push(ExecutionFailure::TerminationFailure {
            kind: io::ErrorKind::PermissionDenied,
            message: "process-group kill failed".to_owned(),
        });

    let result = convert(&execution_result).unwrap();
    assert_eq!(result.outcome(), ProducerOutcome::Timeout);
    assert_eq!(
        result.runtime_facts().failures().first(),
        Some(&ExecutionFailure::Timeout)
    );
    assert_eq!(
        result.runtime_facts().availability(),
        RuntimeFactAvailability::Incomplete
    );
}

#[test]
fn secondary_failure_order_is_preserved_exactly() {
    let termination_failure = ExecutionFailure::TerminationFailure {
        kind: io::ErrorKind::PermissionDenied,
        message: "process-group kill failed".to_owned(),
    };
    let wait_failure = ExecutionFailure::WaitFailure {
        kind: io::ErrorKind::BrokenPipe,
        message: "reap failed".to_owned(),
    };

    let mut expected = timeout_execution();
    expected.failures = vec![
        ExecutionFailure::Timeout,
        termination_failure.clone(),
        wait_failure.clone(),
    ];

    let result = convert(&expected).unwrap();
    assert_eq!(
        result.runtime_facts().failures(),
        &[ExecutionFailure::Timeout, termination_failure, wait_failure]
    );
}

#[test]
fn triggered_timeout_with_selected_cancellation_is_rejected() {
    let mut execution_result = timeout_execution();
    execution_result.cancellation = CancellationOutcome::Selected;

    assert_eq!(
        convert(&execution_result).unwrap_err(),
        ProducerResultConversionError::ContradictoryRuntimeFacts(
            "multiple incompatible terminal runtime facts were supplied"
        )
    );
}

#[test]
fn triggered_timeout_with_terminating_resource_observation_is_rejected() {
    let mut execution_result = timeout_execution();
    execution_result
        .resource_observations
        .push(terminating_resource_observation());

    assert_eq!(
        convert(&execution_result).unwrap_err(),
        ProducerResultConversionError::ContradictoryRuntimeFacts(
            "multiple incompatible terminal runtime facts were supplied"
        )
    );
}

#[test]
fn selected_cancellation_without_coherent_termination_is_rejected() {
    let mut execution_result = success_execution(ExecutionPhase::Compile);
    execution_result.cancellation = CancellationOutcome::Selected;

    assert_eq!(
        convert(&execution_result).unwrap_err(),
        ProducerResultConversionError::ContradictoryRuntimeFacts(
            "selected cancellation lacks coherent cancellation termination facts"
        )
    );
}

#[test]
fn triggered_timeout_without_coherent_termination_is_rejected() {
    let mut execution_result = success_execution(ExecutionPhase::Compile);
    execution_result.timeout = TimeoutOutcome::Triggered {
        limit: Duration::from_secs(1),
    };

    assert_eq!(
        convert(&execution_result).unwrap_err(),
        ProducerResultConversionError::ContradictoryRuntimeFacts(
            "triggered timeout lacks coherent timeout termination facts"
        )
    );
}

#[test]
fn timeout_observation_contradicting_triggered_timeout_is_rejected() {
    let mut execution_result = timeout_execution();
    execution_result
        .resource_observations
        .push(ResourceLimitObservation {
            kind: ResourceLimitKind::Timeout,
            configured_limit: ResourceLimitValue::Duration(Duration::from_secs(30)),
            observed_value: Some(ResourceLimitValue::Duration(Duration::from_millis(25))),
            enforcement_status: ResourceEnforcementStatus::SupervisorTimeoutEnforced,
            terminated_execution: false,
            truncated: None,
        });

    assert_eq!(
        convert(&execution_result).unwrap_err(),
        ProducerResultConversionError::InvalidProducerResult(
            ProducerResultError::ContradictoryRuntimeFacts(
                "timeout resource observation contradicts timeout outcome"
            )
        )
    );
}

#[test]
fn process_identity_contradicting_process_exit_is_rejected() {
    let mut execution_result = spawn_failure_execution();
    execution_result.runtime_metadata.process_id = Some(4242);

    assert_eq!(
        convert(&execution_result).unwrap_err(),
        ProducerResultConversionError::ContradictoryRuntimeFacts(
            "process exit contradicts process identity"
        )
    );
}

#[test]
fn spawn_failure_must_be_the_sole_failure() {
    let mut execution_result = spawn_failure_execution();
    execution_result
        .failures
        .push(ExecutionFailure::WaitFailure {
            kind: io::ErrorKind::Interrupted,
            message: "unreachable wait failure".to_owned(),
        });

    assert_eq!(
        convert(&execution_result).unwrap_err(),
        ProducerResultConversionError::ContradictoryRuntimeFacts(
            "spawn failure must be the sole runtime failure"
        )
    );
}

#[test]
fn undeterminable_runtime_fails_are_fail_closed() {
    let execution_result = execution(
        ExecutionPhase::Compile,
        ProcessExit::ExitedWithCode(7),
        TimeoutOutcome::NotConfigured,
        CancellationOutcome::NotSelected,
        Vec::new(),
    );

    assert_eq!(
        convert(&execution_result).unwrap_err(),
        ProducerResultConversionError::ContradictoryRuntimeFacts(
            "runtime facts do not determine a producer outcome"
        )
    );
}

#[test]
fn phase_is_copied_exactly_for_every_conversion() {
    for phase in [
        ExecutionPhase::Compile,
        ExecutionPhase::BuggyExecution,
        ExecutionPhase::FixedExecution,
    ] {
        let result = convert(&success_execution(phase)).unwrap();
        assert_eq!(result.phase(), phase);
    }
}

#[test]
fn caller_supplied_producer_result_id_is_preserved() {
    let result = producer_result_from_execution(
        &success_execution(ExecutionPhase::Compile),
        ProducerResultId::new("caller-result-77").unwrap(),
        WorkflowAttemptId::new("attempt-9").unwrap(),
        ProducerResultReferences::default(),
    )
    .unwrap();

    assert_eq!(result.producer_result_id().as_str(), "caller-result-77");
}

#[test]
fn caller_supplied_workflow_attempt_id_is_preserved() {
    let result = producer_result_from_execution(
        &success_execution(ExecutionPhase::Compile),
        ProducerResultId::new("result-1").unwrap(),
        WorkflowAttemptId::new("caller-attempt-12").unwrap(),
        ProducerResultReferences::default(),
    )
    .unwrap();

    assert_eq!(result.workflow_attempt_id().as_str(), "caller-attempt-12");
}

#[test]
fn optional_candidate_reference_is_carried_through_only_when_supplied() {
    let without = convert(&success_execution(ExecutionPhase::Compile)).unwrap();
    assert!(without.candidate_version_reference().is_none());
    assert!(without.correlation_reference().is_none());

    let candidate = CandidateVersionReference::new("candidate-42").unwrap();
    let with = producer_result_from_execution(
        &success_execution(ExecutionPhase::Compile),
        ProducerResultId::new("result-1").unwrap(),
        WorkflowAttemptId::new("attempt-9").unwrap(),
        ProducerResultReferences {
            candidate_version_reference: Some(&candidate),
            ..ProducerResultReferences::default()
        },
    )
    .unwrap();

    assert_eq!(
        with.candidate_version_reference().unwrap().as_str(),
        "candidate-42"
    );
}

#[test]
fn optional_correlation_reference_is_carried_through_only_when_supplied() {
    let correlation = CorrelationReference::new("correlation-17").unwrap();
    let with = producer_result_from_execution(
        &success_execution(ExecutionPhase::Compile),
        ProducerResultId::new("result-1").unwrap(),
        WorkflowAttemptId::new("attempt-9").unwrap(),
        ProducerResultReferences {
            correlation_reference: Some(&correlation),
            ..ProducerResultReferences::default()
        },
    )
    .unwrap();

    assert_eq!(
        with.correlation_reference().unwrap().as_str(),
        "correlation-17"
    );
}

#[test]
fn stdout_logical_reference_records_bounded_metadata_only() {
    let mut execution_result = success_execution(ExecutionPhase::Compile);
    execution_result.stdout = bounded_output(120, 120, false);

    let result = producer_result_from_execution(
        &execution_result,
        ProducerResultId::new("result-1").unwrap(),
        WorkflowAttemptId::new("attempt-9").unwrap(),
        ProducerResultReferences {
            stdout_logical_reference: Some("mem://run/stdout"),
            ..ProducerResultReferences::default()
        },
    )
    .unwrap();

    let references = result.runtime_facts().output_references();
    assert_eq!(references.len(), 1);
    assert_eq!(
        references[0].kind(),
        testgap_worker::ProducerOutputKind::Stdout
    );
    assert_eq!(references[0].reference(), "mem://run/stdout");
    assert_eq!(references[0].observed_bytes(), 120);
    assert_eq!(references[0].retained_bytes(), 120);
    assert_eq!(references[0].capture_limit_bytes(), CAPTURE_LIMIT);
    assert!(!references[0].truncated());
}

#[test]
fn stderr_logical_reference_records_bounded_metadata_only() {
    let mut execution_result = success_execution(ExecutionPhase::Compile);
    execution_result.stderr = bounded_output(500, 100, true);

    let result = producer_result_from_execution(
        &execution_result,
        ProducerResultId::new("result-1").unwrap(),
        WorkflowAttemptId::new("attempt-9").unwrap(),
        ProducerResultReferences {
            stderr_logical_reference: Some("mem://run/stderr"),
            ..ProducerResultReferences::default()
        },
    )
    .unwrap();

    let references = result.runtime_facts().output_references();
    assert_eq!(references.len(), 1);
    assert_eq!(
        references[0].kind(),
        testgap_worker::ProducerOutputKind::Stderr
    );
    assert_eq!(references[0].reference(), "mem://run/stderr");
    assert_eq!(references[0].observed_bytes(), 500);
    assert_eq!(references[0].retained_bytes(), 100);
    assert_eq!(references[0].capture_limit_bytes(), CAPTURE_LIMIT);
    assert!(references[0].truncated());
}

#[test]
fn zero_byte_output_yields_consistent_reference_metadata() {
    let mut execution_result = success_execution(ExecutionPhase::Compile);
    execution_result.stdout = BoundedOutput::empty(CAPTURE_LIMIT);

    let result = producer_result_from_execution(
        &execution_result,
        ProducerResultId::new("result-1").unwrap(),
        WorkflowAttemptId::new("attempt-9").unwrap(),
        ProducerResultReferences {
            stdout_logical_reference: Some("mem://run/empty"),
            ..ProducerResultReferences::default()
        },
    )
    .unwrap();

    let reference = &result.runtime_facts().output_references()[0];
    assert_eq!(reference.observed_bytes(), 0);
    assert_eq!(reference.retained_bytes(), 0);
    assert!(!reference.truncated());
}

#[test]
fn empty_or_oversized_logical_references_are_rejected() {
    let execution_result = success_execution(ExecutionPhase::Compile);
    let references = |stdout: &'static str| ProducerResultReferences {
        stdout_logical_reference: Some(stdout),
        ..ProducerResultReferences::default()
    };

    let empty = producer_result_from_execution(
        &execution_result,
        ProducerResultId::new("result-1").unwrap(),
        WorkflowAttemptId::new("attempt-9").unwrap(),
        references(""),
    )
    .unwrap_err();
    assert_eq!(
        empty,
        ProducerResultConversionError::InvalidProducerResult(ProducerResultError::EmptyValue(
            "output_reference"
        ))
    );

    let oversized = "r".repeat(testgap_worker::BoundedOutputReference::MAX_REFERENCE_BYTES + 1);
    let too_long = producer_result_from_execution(
        &execution_result,
        ProducerResultId::new("result-1").unwrap(),
        WorkflowAttemptId::new("attempt-9").unwrap(),
        ProducerResultReferences {
            stdout_logical_reference: Some(oversized.as_str()),
            ..ProducerResultReferences::default()
        },
    )
    .unwrap_err();
    assert_eq!(
        too_long,
        ProducerResultConversionError::InvalidProducerResult(ProducerResultError::InvalidOutput(
            "output reference exceeds the UTF-8 byte limit"
        ))
    );
}

#[test]
fn raw_output_bytes_are_never_embedded_in_the_producer_result() {
    const PAYLOAD: &[u8] = b"SECRET-PAYLOAD-CONTENT";

    let mut execution_result = success_execution(ExecutionPhase::Compile);
    execution_result.stdout = BoundedOutput {
        captured_bytes: PAYLOAD.to_vec(),
        total_bytes_observed: PAYLOAD.len() as u64,
        capture_limit_bytes: CAPTURE_LIMIT,
        truncated: false,
    };
    execution_result.stderr = BoundedOutput {
        captured_bytes: PAYLOAD.to_vec(),
        total_bytes_observed: PAYLOAD.len() as u64,
        capture_limit_bytes: CAPTURE_LIMIT,
        truncated: false,
    };

    let result = producer_result_from_execution(
        &execution_result,
        ProducerResultId::new("result-1").unwrap(),
        WorkflowAttemptId::new("attempt-9").unwrap(),
        ProducerResultReferences {
            stdout_logical_reference: Some("mem://run/stdout"),
            stderr_logical_reference: Some("mem://run/stderr"),
            ..ProducerResultReferences::default()
        },
    )
    .unwrap();

    let rendered = format!("{result:?}");
    assert!(!rendered.contains("SECRET-PAYLOAD-CONTENT"));
    for reference in result.runtime_facts().output_references() {
        assert_eq!(reference.retained_bytes(), PAYLOAD.len() as u64);
        assert_eq!(reference.observed_bytes(), PAYLOAD.len() as u64);
    }
}

#[test]
fn availability_reflects_observation_completeness() {
    let complete = convert(&success_execution(ExecutionPhase::Compile)).unwrap();
    assert_eq!(
        complete.runtime_facts().availability(),
        RuntimeFactAvailability::Complete
    );

    let mut incomplete = success_execution(ExecutionPhase::Compile);
    incomplete.process_exit = ProcessExit::TerminatedBySupervisor {
        reason: SupervisorTermination::WaitFailure,
        code: None,
    };
    incomplete.failures = vec![ExecutionFailure::WaitFailure {
        kind: io::ErrorKind::Interrupted,
        message: "wait interrupted".to_owned(),
    }];
    let incomplete = convert(&incomplete).unwrap();
    assert_eq!(
        incomplete.runtime_facts().availability(),
        RuntimeFactAvailability::Incomplete
    );

    let unavailable = convert(&spawn_failure_execution()).unwrap();
    assert_eq!(
        unavailable.runtime_facts().availability(),
        RuntimeFactAvailability::Unavailable
    );
}

#[test]
fn resource_observations_are_preserved_as_values() {
    let mut expected = vec![
        terminating_resource_observation(),
        ResourceLimitObservation {
            kind: ResourceLimitKind::CpuTime,
            configured_limit: ResourceLimitValue::Duration(Duration::from_secs(10)),
            observed_value: None,
            enforcement_status: ResourceEnforcementStatus::NotEnforced,
            terminated_execution: false,
            truncated: None,
        },
    ];

    let mut execution_result = nonzero_execution(ExecutionPhase::BuggyExecution, Some(137));
    execution_result.resource_observations = expected.clone();

    let result = convert(&execution_result).unwrap();
    expected.sort();
    assert_eq!(
        result.runtime_facts().resource_observations(),
        &expected[..]
    );
    assert_eq!(result.outcome(), ProducerOutcome::ResourceBreach);
}

#[test]
fn conversion_is_deterministic_for_identical_inputs() {
    let first = convert(&timeout_execution()).unwrap();
    let second = convert(&timeout_execution()).unwrap();
    assert_eq!(first, second);
}

#[test]
fn adapter_generates_no_identities_of_its_own() {
    let execution_result = success_execution(ExecutionPhase::Compile);

    let first = producer_result_from_execution(
        &execution_result,
        ProducerResultId::new("identity-a").unwrap(),
        WorkflowAttemptId::new("attempt-a").unwrap(),
        ProducerResultReferences::default(),
    )
    .unwrap();
    let second = producer_result_from_execution(
        &execution_result,
        ProducerResultId::new("identity-b").unwrap(),
        WorkflowAttemptId::new("attempt-b").unwrap(),
        ProducerResultReferences::default(),
    )
    .unwrap();

    assert_eq!(first.producer_result_id().as_str(), "identity-a");
    assert_eq!(second.producer_result_id().as_str(), "identity-b");
    assert_eq!(first.workflow_attempt_id().as_str(), "attempt-a");
    assert_eq!(second.workflow_attempt_id().as_str(), "attempt-b");
}
