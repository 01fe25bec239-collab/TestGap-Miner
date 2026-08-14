use std::any::TypeId;
use std::io;
use std::time::Duration;

use testgap_worker::{
    compare_producer_results, BoundedOutputReference, CancellationOutcome,
    CandidateVersionReference, CorrelationReference, ExecutionFailure, ExecutionPhase, ProcessExit,
    ProducerOutcome, ProducerOutputKind, ProducerResult, ProducerResultComparison,
    ProducerResultId, ProducerRuntimeFacts, ResourceEnforcementStatus, ResourceLimitKind,
    ResourceLimitObservation, ResourceLimitValue, RuntimeFactAvailability, RuntimeMetadata,
    SupervisorTermination, TimeoutOutcome, WorkflowAttemptId,
};

fn metadata() -> RuntimeMetadata {
    RuntimeMetadata {
        operating_system: "test-os",
        architecture: "test-arch",
        process_id: Some(7),
    }
}

fn runtime(process_exit: ProcessExit) -> ProducerRuntimeFacts {
    ProducerRuntimeFacts::new(metadata(), process_exit, Duration::from_millis(25))
}

fn runtime_without_process(process_exit: ProcessExit) -> ProducerRuntimeFacts {
    ProducerRuntimeFacts::new(
        RuntimeMetadata {
            process_id: None,
            ..metadata()
        },
        process_exit,
        Duration::from_millis(25),
    )
}

fn successful_result(id: &str) -> ProducerResult {
    ProducerResult::new(
        ProducerResultId::new(id).unwrap(),
        WorkflowAttemptId::new("attempt-1").unwrap(),
        ExecutionPhase::Compile,
        ProducerOutcome::Success,
        runtime(ProcessExit::ExitedWithCode(0)),
    )
    .unwrap()
}

fn nonzero_runtime(code: i32) -> ProducerRuntimeFacts {
    runtime(ProcessExit::ExitedWithCode(code))
        .with_failures(vec![ExecutionFailure::NonZeroExit { code: Some(code) }])
}

fn observation(kind: ResourceLimitKind, terminated_execution: bool) -> ResourceLimitObservation {
    ResourceLimitObservation {
        kind,
        configured_limit: ResourceLimitValue::Bytes(1024),
        observed_value: Some(ResourceLimitValue::Bytes(2048)),
        enforcement_status: if terminated_execution {
            ResourceEnforcementStatus::RuntimeLimitEnforced
        } else {
            ResourceEnforcementStatus::NotEnforced
        },
        terminated_execution,
        truncated: None,
    }
}

fn output(kind: ProducerOutputKind, reference: &str) -> BoundedOutputReference {
    BoundedOutputReference::new(kind, reference, 10, 8, 8, true).unwrap()
}

#[test]
fn valid_producer_result_carries_execution_and_workflow_provenance() {
    let result = successful_result("result-1")
        .with_candidate_version_reference(CandidateVersionReference::new("candidate-1").unwrap())
        .with_correlation_reference(CorrelationReference::new("correlation-1").unwrap());

    assert_eq!(result.producer_result_id().as_str(), "result-1");
    assert_eq!(result.workflow_attempt_id().as_str(), "attempt-1");
    assert_eq!(result.phase(), ExecutionPhase::Compile);
    assert_eq!(result.outcome(), ProducerOutcome::Success);
    assert_eq!(
        result.candidate_version_reference().unwrap().as_str(),
        "candidate-1"
    );
    assert_eq!(
        result.correlation_reference().unwrap().as_str(),
        "correlation-1"
    );
}

#[test]
fn empty_identity_values_are_rejected_without_normalizing_valid_values() {
    assert!(ProducerResultId::new("").is_err());
    assert!(ProducerResultId::new(" \t\n").is_err());
    assert!(WorkflowAttemptId::new("  ").is_err());
    assert_ne!(
        ProducerResultId::new("result-1").unwrap(),
        ProducerResultId::new(" result-1 ").unwrap()
    );
}

#[test]
fn identity_namespaces_are_distinct_rust_types() {
    struct QueueMessageId(String);
    struct QueueDeliveryId(String);
    struct ClaimOrLeaseId(String);
    struct ExecutionEvidenceId(String);

    assert_ne!(
        TypeId::of::<ProducerResultId>(),
        TypeId::of::<WorkflowAttemptId>()
    );
    assert_ne!(
        TypeId::of::<ProducerResultId>(),
        TypeId::of::<QueueMessageId>()
    );
    assert_ne!(
        TypeId::of::<ProducerResultId>(),
        TypeId::of::<QueueDeliveryId>()
    );
    assert_ne!(
        TypeId::of::<ProducerResultId>(),
        TypeId::of::<ClaimOrLeaseId>()
    );
    assert_ne!(
        TypeId::of::<ProducerResultId>(),
        TypeId::of::<ExecutionEvidenceId>()
    );

    let queue = QueueMessageId("queue-message-1".to_owned());
    let delivery = QueueDeliveryId("queue-delivery-1".to_owned());
    let claim = ClaimOrLeaseId("claim-1".to_owned());
    let evidence = ExecutionEvidenceId("evidence-1".to_owned());
    assert_eq!(queue.0, "queue-message-1");
    assert_eq!(delivery.0, "queue-delivery-1");
    assert_eq!(claim.0, "claim-1");
    assert_eq!(evidence.0, "evidence-1");
}

#[test]
fn external_phase_representation_is_closed_and_fails_unknown_values() {
    assert_eq!(
        ExecutionPhase::try_from("COMPILE").unwrap(),
        ExecutionPhase::Compile
    );
    assert_eq!(
        ExecutionPhase::try_from("BUGGY_OR_TARGET_REVISION_TEST").unwrap(),
        ExecutionPhase::BuggyExecution
    );
    assert_eq!(
        ExecutionPhase::try_from("FIXED_OR_REFERENCE_REVISION_TEST").unwrap(),
        ExecutionPhase::FixedExecution
    );
    assert_eq!(ExecutionPhase::Compile.as_external_str(), "COMPILE");
    assert!(ExecutionPhase::try_from("UNKNOWN").is_err());
    assert!(ExecutionPhase::try_from("compile").is_err());
}

#[test]
fn successful_runtime_result_requires_a_clean_zero_exit() {
    let result = successful_result("success");
    assert_eq!(
        result.runtime_facts().process_exit(),
        &ProcessExit::ExitedWithCode(0)
    );
    assert!(result.runtime_facts().failures().is_empty());
}

#[test]
fn nonzero_exit_represents_phase_specific_failure() {
    let compile = ProducerResult::new(
        ProducerResultId::new("compile-failure").unwrap(),
        WorkflowAttemptId::new("attempt-1").unwrap(),
        ExecutionPhase::Compile,
        ProducerOutcome::CompilationFailure,
        nonzero_runtime(1),
    )
    .unwrap();
    let test = ProducerResult::new(
        ProducerResultId::new("test-failure").unwrap(),
        WorkflowAttemptId::new("attempt-1").unwrap(),
        ExecutionPhase::BuggyExecution,
        ProducerOutcome::TestFailure,
        nonzero_runtime(2),
    )
    .unwrap();

    assert_eq!(compile.outcome(), ProducerOutcome::CompilationFailure);
    assert_eq!(test.outcome(), ProducerOutcome::TestFailure);
}

#[test]
fn timeout_result_requires_matching_observation_failure_and_termination() {
    let limit = Duration::from_secs(2);
    let facts = runtime(ProcessExit::TerminatedBySupervisor {
        reason: SupervisorTermination::Timeout,
        code: None,
    })
    .with_timeout(TimeoutOutcome::Triggered { limit })
    .with_failures(vec![ExecutionFailure::Timeout]);
    let result = ProducerResult::new(
        ProducerResultId::new("timeout").unwrap(),
        WorkflowAttemptId::new("attempt-1").unwrap(),
        ExecutionPhase::FixedExecution,
        ProducerOutcome::Timeout,
        facts,
    )
    .unwrap();

    assert_eq!(
        result.runtime_facts().timeout(),
        &TimeoutOutcome::Triggered { limit }
    );
}

#[test]
fn cancellation_result_requires_selected_cancellation() {
    let facts = runtime(ProcessExit::TerminatedBySupervisor {
        reason: SupervisorTermination::Cancellation,
        code: None,
    })
    .with_cancellation(CancellationOutcome::Selected)
    .with_failures(vec![ExecutionFailure::Cancelled]);
    let result = ProducerResult::new(
        ProducerResultId::new("cancelled").unwrap(),
        WorkflowAttemptId::new("attempt-1").unwrap(),
        ExecutionPhase::BuggyExecution,
        ProducerOutcome::Cancellation,
        facts,
    )
    .unwrap();

    assert_eq!(
        result.runtime_facts().cancellation(),
        CancellationOutcome::Selected
    );
}

#[test]
fn terminating_resource_observation_represents_resource_breach() {
    let facts = nonzero_runtime(137)
        .with_resource_observations([observation(ResourceLimitKind::MemoryBytes, true)]);
    let result = ProducerResult::new(
        ProducerResultId::new("resource-breach").unwrap(),
        WorkflowAttemptId::new("attempt-1").unwrap(),
        ExecutionPhase::FixedExecution,
        ProducerOutcome::ResourceBreach,
        facts,
    )
    .unwrap();

    assert!(result.runtime_facts().resource_observations()[0].terminated_execution);
}

#[test]
fn runner_failure_can_mark_runtime_facts_unavailable_or_incomplete() {
    let unavailable = runtime_without_process(ProcessExit::NeverStarted)
        .with_availability(RuntimeFactAvailability::Unavailable)
        .with_failures(vec![ExecutionFailure::SpawnFailure {
            kind: io::ErrorKind::NotFound,
            message: "runner not found".to_owned(),
        }]);
    let unavailable_result = ProducerResult::new(
        ProducerResultId::new("unavailable").unwrap(),
        WorkflowAttemptId::new("attempt-1").unwrap(),
        ExecutionPhase::Compile,
        ProducerOutcome::RunnerFailure,
        unavailable,
    )
    .unwrap();

    let incomplete = runtime(ProcessExit::TerminatedBySupervisor {
        reason: SupervisorTermination::OutputCaptureFailure,
        code: None,
    })
    .with_availability(RuntimeFactAvailability::Incomplete)
    .with_failures(vec![ExecutionFailure::OutputCaptureFailure {
        stream: testgap_worker::OutputStream::Stdout,
        kind: Some(io::ErrorKind::Other),
        message: "capture failed".to_owned(),
    }]);
    let incomplete_result = ProducerResult::new(
        ProducerResultId::new("incomplete").unwrap(),
        WorkflowAttemptId::new("attempt-1").unwrap(),
        ExecutionPhase::Compile,
        ProducerOutcome::RunnerFailure,
        incomplete,
    )
    .unwrap();

    assert_eq!(
        unavailable_result.runtime_facts().availability(),
        RuntimeFactAvailability::Unavailable
    );
    assert_eq!(
        incomplete_result.runtime_facts().availability(),
        RuntimeFactAvailability::Incomplete
    );
}

#[test]
fn contradictory_result_states_are_rejected() {
    let id = || ProducerResultId::new("contradiction").unwrap();
    let attempt = || WorkflowAttemptId::new("attempt-1").unwrap();

    assert!(ProducerResult::new(
        id(),
        attempt(),
        ExecutionPhase::Compile,
        ProducerOutcome::Success,
        nonzero_runtime(1),
    )
    .is_err());

    let timed_out = runtime(ProcessExit::TerminatedBySupervisor {
        reason: SupervisorTermination::Timeout,
        code: None,
    })
    .with_timeout(TimeoutOutcome::Triggered {
        limit: Duration::from_secs(1),
    })
    .with_failures(vec![ExecutionFailure::Timeout]);
    assert!(ProducerResult::new(
        id(),
        attempt(),
        ExecutionPhase::Compile,
        ProducerOutcome::Success,
        timed_out,
    )
    .is_err());

    let cancelled = runtime(ProcessExit::TerminatedBySupervisor {
        reason: SupervisorTermination::Cancellation,
        code: None,
    })
    .with_cancellation(CancellationOutcome::Selected)
    .with_failures(vec![ExecutionFailure::Cancelled]);
    assert!(ProducerResult::new(
        id(),
        attempt(),
        ExecutionPhase::Compile,
        ProducerOutcome::Success,
        cancelled,
    )
    .is_err());

    let breached = nonzero_runtime(137)
        .with_resource_observations([observation(ResourceLimitKind::ProcessCount, true)]);
    assert!(ProducerResult::new(
        id(),
        attempt(),
        ExecutionPhase::Compile,
        ProducerOutcome::Success,
        breached,
    )
    .is_err());

    let runner_failed =
        runtime(ProcessExit::NeverStarted).with_failures(vec![ExecutionFailure::SpawnFailure {
            kind: io::ErrorKind::Other,
            message: "spawn failed".to_owned(),
        }]);
    assert!(ProducerResult::new(
        id(),
        attempt(),
        ExecutionPhase::Compile,
        ProducerOutcome::Success,
        runner_failed,
    )
    .is_err());
}

#[test]
fn timeout_classification_fails_closed_without_triggered_observation() {
    let facts = runtime(ProcessExit::TerminatedBySupervisor {
        reason: SupervisorTermination::Timeout,
        code: None,
    });
    assert!(ProducerResult::new(
        ProducerResultId::new("bad-timeout").unwrap(),
        WorkflowAttemptId::new("attempt-1").unwrap(),
        ExecutionPhase::Compile,
        ProducerOutcome::Timeout,
        facts,
    )
    .is_err());
}

#[test]
fn incompatible_terminal_facts_fail_closed() {
    let facts = runtime(ProcessExit::TerminatedBySupervisor {
        reason: SupervisorTermination::Cancellation,
        code: None,
    })
    .with_timeout(TimeoutOutcome::Triggered {
        limit: Duration::from_secs(1),
    })
    .with_cancellation(CancellationOutcome::Selected)
    .with_failures(vec![ExecutionFailure::Cancelled, ExecutionFailure::Timeout]);
    assert!(ProducerResult::new(
        ProducerResultId::new("terminal-conflict").unwrap(),
        WorkflowAttemptId::new("attempt-1").unwrap(),
        ExecutionPhase::Compile,
        ProducerOutcome::Cancellation,
        facts,
    )
    .is_err());
}

#[test]
fn compile_and_test_outcomes_cannot_cross_phase_boundaries() {
    assert!(ProducerResult::new(
        ProducerResultId::new("wrong-phase-1").unwrap(),
        WorkflowAttemptId::new("attempt-1").unwrap(),
        ExecutionPhase::BuggyExecution,
        ProducerOutcome::CompilationFailure,
        nonzero_runtime(1),
    )
    .is_err());
    assert!(ProducerResult::new(
        ProducerResultId::new("wrong-phase-2").unwrap(),
        WorkflowAttemptId::new("attempt-1").unwrap(),
        ExecutionPhase::Compile,
        ProducerOutcome::TestFailure,
        nonzero_runtime(1),
    )
    .is_err());
}

#[test]
fn unordered_fact_inputs_have_deterministic_semantic_representation() {
    let resources = [
        observation(ResourceLimitKind::MemoryBytes, false),
        observation(ResourceLimitKind::FileCount, false),
    ];
    let outputs = [
        output(ProducerOutputKind::Stderr, "stderr-ref"),
        output(ProducerOutputKind::Stdout, "stdout-ref"),
    ];
    let first = ProducerResult::new(
        ProducerResultId::new("deterministic").unwrap(),
        WorkflowAttemptId::new("attempt-1").unwrap(),
        ExecutionPhase::Compile,
        ProducerOutcome::Success,
        runtime(ProcessExit::ExitedWithCode(0))
            .with_resource_observations(resources.clone())
            .with_output_references(outputs.clone())
            .unwrap(),
    )
    .unwrap();
    let second = ProducerResult::new(
        ProducerResultId::new("deterministic").unwrap(),
        WorkflowAttemptId::new("attempt-1").unwrap(),
        ExecutionPhase::Compile,
        ProducerOutcome::Success,
        runtime(ProcessExit::ExitedWithCode(0))
            .with_resource_observations(resources.into_iter().rev())
            .with_output_references(outputs.into_iter().rev())
            .unwrap(),
    )
    .unwrap();

    assert_eq!(first, second);
    assert_eq!(format!("{first:?}"), format!("{second:?}"));
}

#[test]
fn same_id_identical_results_converge_and_conflicts_fail_closed() {
    let first = successful_result("same-id");
    let duplicate = successful_result("same-id");
    let conflict = successful_result("same-id")
        .with_correlation_reference(CorrelationReference::new("different").unwrap());

    assert_eq!(
        compare_producer_results(&first, &duplicate),
        ProducerResultComparison::DuplicateConvergent
    );
    assert_eq!(
        compare_producer_results(&first, &conflict),
        ProducerResultComparison::Conflict
    );
}

#[test]
fn different_producer_result_ids_are_independent() {
    assert_eq!(
        compare_producer_results(&successful_result("one"), &successful_result("two")),
        ProducerResultComparison::Independent
    );
}

#[test]
fn bounded_output_references_hold_metadata_not_output_bytes() {
    let stdout = output(ProducerOutputKind::Stdout, "logical:stdout:1");
    assert_eq!(stdout.reference(), "logical:stdout:1");
    assert_eq!(stdout.observed_bytes(), 10);
    assert_eq!(stdout.retained_bytes(), 8);
    assert_eq!(stdout.capture_limit_bytes(), 8);
    assert!(stdout.truncated());

    assert!(
        BoundedOutputReference::new(ProducerOutputKind::Log, "logical:log:1", 5, 6, 6, false,)
            .is_err()
    );
    assert!(BoundedOutputReference::new(
        ProducerOutputKind::Diagnostic,
        "logical:diagnostic:1",
        5,
        5,
        5,
        true,
    )
    .is_err());
}

#[test]
fn output_reference_metadata_is_structurally_bounded_by_utf8_bytes() {
    let exact_reference = "é".repeat(BoundedOutputReference::MAX_REFERENCE_BYTES / 2);
    let exact =
        BoundedOutputReference::new(ProducerOutputKind::Log, &exact_reference, 0, 0, 0, false)
            .unwrap();
    assert_eq!(
        exact.reference().len(),
        BoundedOutputReference::MAX_REFERENCE_BYTES
    );

    let over_reference = format!("{exact_reference}x");
    assert!(
        BoundedOutputReference::new(ProducerOutputKind::Log, &over_reference, 0, 0, 0, false,)
            .is_err()
    );

    let excessive_count = vec![
        output(ProducerOutputKind::Log, "ref");
        ProducerRuntimeFacts::MAX_OUTPUT_REFERENCES + 1
    ];
    assert!(runtime(ProcessExit::ExitedWithCode(0))
        .with_output_references(excessive_count)
        .is_err());

    let exact_aggregate = vec![
        exact.clone();
        ProducerRuntimeFacts::MAX_OUTPUT_REFERENCE_METADATA_BYTES
            / BoundedOutputReference::MAX_REFERENCE_BYTES
    ];
    assert!(runtime(ProcessExit::ExitedWithCode(0))
        .with_output_references(exact_aggregate)
        .is_ok());

    let excessive_aggregate = vec![
        exact;
        ProducerRuntimeFacts::MAX_OUTPUT_REFERENCE_METADATA_BYTES
            / BoundedOutputReference::MAX_REFERENCE_BYTES
            + 1
    ];
    assert!(runtime(ProcessExit::ExitedWithCode(0))
        .with_output_references(excessive_aggregate)
        .is_err());
}

#[test]
fn spawn_failure_requires_never_started_without_a_process_id() {
    let spawn_failure = || ExecutionFailure::SpawnFailure {
        kind: io::ErrorKind::Other,
        message: "spawn failed".to_owned(),
    };
    let result = |facts| {
        ProducerResult::new(
            ProducerResultId::new("spawn-failure").unwrap(),
            WorkflowAttemptId::new("attempt-1").unwrap(),
            ExecutionPhase::Compile,
            ProducerOutcome::RunnerFailure,
            facts,
        )
    };

    assert!(
        result(runtime(ProcessExit::ExitedWithCode(0)).with_failures(vec![spawn_failure()]))
            .is_err()
    );
    assert!(
        result(runtime(ProcessExit::ExitedWithCode(7)).with_failures(vec![spawn_failure()]))
            .is_err()
    );
    assert!(
        result(runtime(ProcessExit::NeverStarted).with_failures(vec![spawn_failure()])).is_err()
    );
    assert!(result(
        runtime(ProcessExit::TerminatedBySupervisor {
            reason: SupervisorTermination::OutputCaptureFailure,
            code: None,
        })
        .with_failures(vec![spawn_failure()])
    )
    .is_err());
    assert!(result(
        runtime_without_process(ProcessExit::NeverStarted).with_failures(vec![spawn_failure()])
    )
    .is_ok());
}

#[test]
fn spawn_failure_is_rejected_as_a_secondary_failure_for_every_runtime_exit() {
    let output_capture = || ExecutionFailure::OutputCaptureFailure {
        stream: testgap_worker::OutputStream::Stdout,
        kind: Some(io::ErrorKind::Other),
        message: "capture failed".to_owned(),
    };
    let spawn_failure = || ExecutionFailure::SpawnFailure {
        kind: io::ErrorKind::Other,
        message: "spawn failed".to_owned(),
    };
    let result = |id, facts| {
        ProducerResult::new(
            ProducerResultId::new(id).unwrap(),
            WorkflowAttemptId::new("attempt-1").unwrap(),
            ExecutionPhase::Compile,
            ProducerOutcome::RunnerFailure,
            facts,
        )
    };

    let cases = [
        (
            "spawn-after-zero-exit",
            runtime(ProcessExit::ExitedWithCode(0))
                .with_failures(vec![output_capture(), spawn_failure()]),
        ),
        (
            "spawn-after-nonzero-exit",
            runtime(ProcessExit::ExitedWithCode(7)).with_failures(vec![
                ExecutionFailure::NonZeroExit { code: Some(7) },
                spawn_failure(),
            ]),
        ),
        (
            "spawn-after-exit-without-code",
            runtime(ProcessExit::ExitedWithoutCode)
                .with_failures(vec![output_capture(), spawn_failure()]),
        ),
        (
            "spawn-after-supervisor-termination",
            runtime(ProcessExit::TerminatedBySupervisor {
                reason: SupervisorTermination::OutputCaptureFailure,
                code: None,
            })
            .with_failures(vec![output_capture(), spawn_failure()]),
        ),
        (
            "spawn-with-process-id",
            runtime(ProcessExit::NeverStarted)
                .with_failures(vec![output_capture(), spawn_failure()]),
        ),
    ];

    for (id, facts) in cases {
        assert!(result(id, facts).is_err(), "{id}");
    }
}

#[test]
fn spawn_failure_is_rejected_with_any_secondary_failure() {
    let facts = runtime_without_process(ProcessExit::NeverStarted).with_failures(vec![
        ExecutionFailure::SpawnFailure {
            kind: io::ErrorKind::Other,
            message: "spawn failed".to_owned(),
        },
        ExecutionFailure::OutputCaptureFailure {
            stream: testgap_worker::OutputStream::Stdout,
            kind: Some(io::ErrorKind::Other),
            message: "capture failed".to_owned(),
        },
    ]);

    assert!(ProducerResult::new(
        ProducerResultId::new("failure-after-spawn").unwrap(),
        WorkflowAttemptId::new("attempt-1").unwrap(),
        ExecutionPhase::Compile,
        ProducerOutcome::RunnerFailure,
        facts,
    )
    .is_err());
}

#[test]
fn runner_failure_preserves_emitted_primary_and_secondary_failure_combinations() {
    let output_capture = || ExecutionFailure::OutputCaptureFailure {
        stream: testgap_worker::OutputStream::Stdout,
        kind: Some(io::ErrorKind::Other),
        message: "capture failed".to_owned(),
    };
    let termination = || ExecutionFailure::TerminationFailure {
        kind: io::ErrorKind::Other,
        message: "termination failed".to_owned(),
    };
    let wait = || ExecutionFailure::WaitFailure {
        kind: io::ErrorKind::Other,
        message: "wait failed".to_owned(),
    };

    let capture_after_success =
        runtime(ProcessExit::ExitedWithCode(0)).with_failures(vec![output_capture()]);
    assert!(ProducerResult::new(
        ProducerResultId::new("capture-after-success").unwrap(),
        WorkflowAttemptId::new("attempt-1").unwrap(),
        ExecutionPhase::Compile,
        ProducerOutcome::RunnerFailure,
        capture_after_success,
    )
    .is_ok());

    let capture_setup_failure = runtime(ProcessExit::TerminatedBySupervisor {
        reason: SupervisorTermination::OutputCaptureFailure,
        code: None,
    })
    .with_failures(vec![output_capture(), termination(), wait()]);
    assert!(ProducerResult::new(
        ProducerResultId::new("capture-setup-failure").unwrap(),
        WorkflowAttemptId::new("attempt-1").unwrap(),
        ExecutionPhase::Compile,
        ProducerOutcome::RunnerFailure,
        capture_setup_failure,
    )
    .is_ok());

    let timeout_limit = Duration::from_secs(1);
    let timeout_cleanup_failure = runtime(ProcessExit::TerminatedBySupervisor {
        reason: SupervisorTermination::Timeout,
        code: None,
    })
    .with_timeout(TimeoutOutcome::Triggered {
        limit: timeout_limit,
    })
    .with_failures(vec![ExecutionFailure::Timeout, termination(), wait()]);
    assert!(ProducerResult::new(
        ProducerResultId::new("timeout-cleanup-failure").unwrap(),
        WorkflowAttemptId::new("attempt-1").unwrap(),
        ExecutionPhase::Compile,
        ProducerOutcome::Timeout,
        timeout_cleanup_failure,
    )
    .is_ok());

    let capture_after_nonzero = runtime(ProcessExit::ExitedWithCode(7)).with_failures(vec![
        ExecutionFailure::NonZeroExit { code: Some(7) },
        output_capture(),
    ]);
    assert!(ProducerResult::new(
        ProducerResultId::new("capture-after-nonzero").unwrap(),
        WorkflowAttemptId::new("attempt-1").unwrap(),
        ExecutionPhase::Compile,
        ProducerOutcome::RunnerFailure,
        capture_after_nonzero,
    )
    .is_ok());
}

#[test]
fn other_impossible_primary_failure_exit_pairs_fail_closed() {
    let output_capture = || ExecutionFailure::OutputCaptureFailure {
        stream: testgap_worker::OutputStream::Stdout,
        kind: Some(io::ErrorKind::Other),
        message: "capture failed".to_owned(),
    };
    let runner_result = |id, facts| {
        ProducerResult::new(
            ProducerResultId::new(id).unwrap(),
            WorkflowAttemptId::new("attempt-1").unwrap(),
            ExecutionPhase::Compile,
            ProducerOutcome::RunnerFailure,
            facts,
        )
    };

    let wait_after_exit = runtime(ProcessExit::ExitedWithCode(0)).with_failures(vec![
        ExecutionFailure::WaitFailure {
            kind: io::ErrorKind::Other,
            message: "wait failed".to_owned(),
        },
    ]);
    assert!(runner_result("wait-after-exit", wait_after_exit).is_err());

    let capture_after_signal =
        runtime(ProcessExit::ExitedWithoutCode).with_failures(vec![output_capture()]);
    assert!(runner_result("capture-after-signal", capture_after_signal).is_err());

    let termination_as_primary = runtime(ProcessExit::TerminatedBySupervisor {
        reason: SupervisorTermination::WaitFailure,
        code: None,
    })
    .with_failures(vec![ExecutionFailure::TerminationFailure {
        kind: io::ErrorKind::Other,
        message: "termination failed".to_owned(),
    }]);
    assert!(runner_result("termination-as-primary", termination_as_primary).is_err());

    let mismatched_nonzero = runtime(ProcessExit::ExitedWithCode(8)).with_failures(vec![
        ExecutionFailure::NonZeroExit { code: Some(7) },
        output_capture(),
    ]);
    assert!(runner_result("mismatched-nonzero", mismatched_nonzero).is_err());
}

#[test]
fn producer_result_has_no_raw_secret_token_prompt_or_repository_byte_field() {
    let source = include_str!("../src/producer_result.rs");
    for prohibited_field in [
        "secret:",
        "token:",
        "prompt:",
        "repository_bytes:",
        "source_bytes:",
        "patch_bytes:",
    ] {
        assert!(!source.contains(prohibited_field), "{prohibited_field}");
    }
}
