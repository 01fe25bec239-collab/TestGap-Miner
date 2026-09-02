use serde_json::{json, Value};
use std::io;
use std::time::Duration;
use testgap_worker::{
    from_json_bytes, producer_result_from_execution, to_json_bytes, BoundedOutput,
    BoundedOutputReference, CancellationOutcome, CandidateVersionReference, CorrelationReference,
    ExecutionExportError, ExecutionFailure, ExecutionPhase, ExecutionResult, ExecutionTestSummary,
    ProcessExit, ProducerOutcome, ProducerOutputKind, ProducerResult, ProducerResultId,
    ProducerResultReferences, ProducerRuntimeFacts, ResourceEnforcementStatus, ResourceLimitKind,
    ResourceLimitObservation, ResourceLimitValue, RuntimeFactAvailability, RuntimeMetadata,
    SupervisorTermination, TestRunSummary, TimeoutOutcome, WorkflowAttemptId,
    EXECUTION_EXPORT_VERSION, MAX_EXECUTION_EXPORT_BYTES,
};

fn metadata(process_id: Option<u32>) -> RuntimeMetadata {
    RuntimeMetadata {
        operating_system: "test-os",
        architecture: "test-arch",
        process_id,
    }
}

fn facts(exit: ProcessExit, duration: Duration) -> ProducerRuntimeFacts {
    ProducerRuntimeFacts::new(metadata(Some(41)), exit, duration)
}

fn result(
    phase: ExecutionPhase,
    outcome: ProducerOutcome,
    facts: ProducerRuntimeFacts,
) -> ProducerResult {
    ProducerResult::new(
        ProducerResultId::new("producer-result-1").unwrap(),
        WorkflowAttemptId::new("workflow-attempt-1").unwrap(),
        phase,
        outcome,
        facts,
    )
    .unwrap()
}

fn success(phase: ExecutionPhase) -> ProducerResult {
    result(
        phase,
        ProducerOutcome::Success,
        facts(ProcessExit::ExitedWithCode(0), Duration::new(1, 2)),
    )
}

fn nonzero(phase: ExecutionPhase, outcome: ProducerOutcome, code: i32) -> ProducerResult {
    result(
        phase,
        outcome,
        facts(ProcessExit::ExitedWithCode(code), Duration::from_millis(25))
            .with_failures(vec![ExecutionFailure::NonZeroExit { code: Some(code) }]),
    )
}

fn timeout_result() -> ProducerResult {
    result(
        ExecutionPhase::BuggyExecution,
        ProducerOutcome::Timeout,
        facts(
            ProcessExit::TerminatedBySupervisor {
                reason: SupervisorTermination::Timeout,
                code: None,
            },
            Duration::from_secs(1),
        )
        .with_timeout(TimeoutOutcome::Triggered {
            limit: Duration::from_secs(30),
        })
        .with_failures(vec![ExecutionFailure::Timeout]),
    )
}

fn cancellation_result() -> ProducerResult {
    result(
        ExecutionPhase::BuggyExecution,
        ProducerOutcome::Cancellation,
        facts(
            ProcessExit::TerminatedBySupervisor {
                reason: SupervisorTermination::Cancellation,
                code: None,
            },
            Duration::from_secs(1),
        )
        .with_cancellation(CancellationOutcome::Selected)
        .with_failures(vec![ExecutionFailure::Cancelled]),
    )
}

fn resource_breach_result() -> ProducerResult {
    let observation = ResourceLimitObservation {
        kind: ResourceLimitKind::MemoryBytes,
        configured_limit: ResourceLimitValue::Bytes(512),
        observed_value: Some(ResourceLimitValue::Bytes(1024)),
        enforcement_status: ResourceEnforcementStatus::RuntimeLimitEnforced,
        terminated_execution: true,
        truncated: None,
    };
    result(
        ExecutionPhase::BuggyExecution,
        ProducerOutcome::ResourceBreach,
        facts(ProcessExit::ExitedWithCode(137), Duration::from_secs(1))
            .with_resource_observations([observation])
            .with_failures(vec![ExecutionFailure::NonZeroExit { code: Some(137) }]),
    )
}

fn spawn_failure_result() -> ProducerResult {
    result(
        ExecutionPhase::Compile,
        ProducerOutcome::RunnerFailure,
        ProducerRuntimeFacts::new(metadata(None), ProcessExit::NeverStarted, Duration::ZERO)
            .with_availability(RuntimeFactAvailability::Unavailable)
            .with_failures(vec![ExecutionFailure::SpawnFailure {
                kind: io::ErrorKind::NotFound,
                message: String::new(),
            }]),
    )
}

fn capture_failure_result() -> ProducerResult {
    result(
        ExecutionPhase::Compile,
        ProducerOutcome::RunnerFailure,
        facts(ProcessExit::ExitedWithCode(0), Duration::from_secs(1))
            .with_availability(RuntimeFactAvailability::Incomplete)
            .with_failures(vec![ExecutionFailure::OutputCaptureFailure {
                stream: testgap_worker::OutputStream::Stdout,
                kind: Some(io::ErrorKind::Other),
                message: String::new(),
            }]),
    )
}

fn assert_wire_rejected(label: &str, export: &Value) {
    assert!(
        from_json_bytes(&serde_json::to_vec(export).unwrap()).is_err(),
        "{label}"
    );
}

fn assert_source_precheck_rejected(result: &ProducerResult) {
    assert!(matches!(
        to_json_bytes(result, None),
        Err(ExecutionExportError::EnvelopeTooLarge)
    ));
}

fn value(result: &ProducerResult, summary: Option<ExecutionTestSummary>) -> Value {
    serde_json::from_slice(&to_json_bytes(result, summary).unwrap()).unwrap()
}

#[test]
fn version_compile_success_and_exact_wire_vocabulary_are_stable() {
    let export = value(&success(ExecutionPhase::Compile), None);

    assert_eq!(EXECUTION_EXPORT_VERSION, "testgap.execution-export.v1");
    assert_eq!(export["version"], EXECUTION_EXPORT_VERSION);
    assert_eq!(export["phase"], "COMPILE");
    assert_eq!(export["outcome"], "SUCCESS");
    assert_eq!(export["test_summary"], Value::Null);
    assert_eq!(export["runtime_facts"]["duration"]["seconds"], 1);
    assert_eq!(export["runtime_facts"]["duration"]["nanoseconds"], 2);
}

#[test]
fn compile_failure_is_exported_without_invented_diagnostics() {
    let export = value(
        &nonzero(
            ExecutionPhase::Compile,
            ProducerOutcome::CompilationFailure,
            2,
        ),
        None,
    );

    assert_eq!(export["outcome"], "COMPILATION_FAILURE");
    assert!(export.get("compiler_error_count").is_none());
    assert!(export.get("warning_count").is_none());
    assert!(export.get("diagnostic_count").is_none());
}

#[test]
fn junit_success_and_failure_aggregates_are_source_specific() {
    let passed = value(
        &success(ExecutionPhase::FixedExecution),
        Some(ExecutionTestSummary::JUnit(TestRunSummary {
            tests_run: 7,
            failures: 0,
        })),
    );
    let failed = value(
        &nonzero(
            ExecutionPhase::BuggyExecution,
            ProducerOutcome::TestFailure,
            1,
        ),
        Some(ExecutionTestSummary::JUnit(TestRunSummary {
            tests_run: 7,
            failures: 2,
        })),
    );

    assert_eq!(
        passed["test_summary"],
        json!({"source":"JUNIT","tests_run":7,"failures":0})
    );
    assert_eq!(
        failed["test_summary"],
        json!({"source":"JUNIT","tests_run":7,"failures":2})
    );
}

#[test]
fn defects4j_aggregate_is_source_specific() {
    let export = value(
        &nonzero(
            ExecutionPhase::FixedExecution,
            ProducerOutcome::TestFailure,
            1,
        ),
        Some(ExecutionTestSummary::Defects4J {
            failing_test_count: 3,
        }),
    );

    assert_eq!(
        export["test_summary"],
        json!({"source":"DEFECTS4J","failing_test_count":3})
    );
}

#[test]
fn test_failure_without_summary_preserves_absence_and_fabricates_no_count() {
    let export = value(
        &nonzero(
            ExecutionPhase::BuggyExecution,
            ProducerOutcome::TestFailure,
            1,
        ),
        None,
    );

    assert_eq!(export["outcome"], "TEST_FAILURE");
    assert_eq!(export["test_summary"], Value::Null);
    assert!(!String::from_utf8(
        to_json_bytes(
            &nonzero(
                ExecutionPhase::BuggyExecution,
                ProducerOutcome::TestFailure,
                1
            ),
            None
        )
        .unwrap()
    )
    .unwrap()
    .contains("failures\":1"));
}

#[test]
fn timeout_and_ordered_failures_are_preserved_without_error_prose() {
    let facts = facts(
        ProcessExit::TerminatedBySupervisor {
            reason: SupervisorTermination::Timeout,
            code: None,
        },
        Duration::from_secs(9),
    )
    .with_timeout(TimeoutOutcome::Triggered {
        limit: Duration::new(30, 4),
    })
    .with_availability(RuntimeFactAvailability::Incomplete)
    .with_failures(vec![
        ExecutionFailure::Timeout,
        ExecutionFailure::TerminationFailure {
            kind: io::ErrorKind::PermissionDenied,
            message: "SECRET TERMINATION PROSE".to_owned(),
        },
    ]);
    let export = value(
        &result(
            ExecutionPhase::BuggyExecution,
            ProducerOutcome::Timeout,
            facts,
        ),
        None,
    );

    assert_eq!(export["outcome"], "TIMEOUT");
    assert_eq!(export["runtime_facts"]["availability"], "INCOMPLETE");
    assert_eq!(export["runtime_facts"]["timeout"]["kind"], "TRIGGERED");
    assert_eq!(export["runtime_facts"]["failures"][0]["kind"], "TIMEOUT");
    assert_eq!(
        export["runtime_facts"]["failures"][1],
        json!({"kind":"TERMINATION_FAILURE","error_kind":"PERMISSION_DENIED"})
    );
    assert!(!export.to_string().contains("SECRET TERMINATION PROSE"));
}

#[test]
fn cancellation_is_preserved() {
    let facts = facts(
        ProcessExit::TerminatedBySupervisor {
            reason: SupervisorTermination::Cancellation,
            code: Some(143),
        },
        Duration::from_secs(2),
    )
    .with_cancellation(CancellationOutcome::Selected)
    .with_failures(vec![ExecutionFailure::Cancelled]);
    let export = value(
        &result(
            ExecutionPhase::FixedExecution,
            ProducerOutcome::Cancellation,
            facts,
        ),
        None,
    );

    assert_eq!(export["outcome"], "CANCELLATION");
    assert_eq!(export["runtime_facts"]["cancellation"], "SELECTED");
    assert_eq!(
        export["runtime_facts"]["process_exit"]["reason"],
        "CANCELLATION"
    );
}

#[test]
fn resource_breach_and_enforcement_vocabulary_are_preserved_exactly() {
    let observation = ResourceLimitObservation {
        kind: ResourceLimitKind::MemoryBytes,
        configured_limit: ResourceLimitValue::Bytes(512),
        observed_value: Some(ResourceLimitValue::Bytes(1024)),
        enforcement_status: ResourceEnforcementStatus::RuntimeLimitEnforced,
        terminated_execution: true,
        truncated: None,
    };
    let facts = facts(ProcessExit::ExitedWithCode(137), Duration::from_millis(12))
        .with_resource_observations([observation])
        .with_failures(vec![ExecutionFailure::NonZeroExit { code: Some(137) }]);
    let export = value(
        &result(
            ExecutionPhase::BuggyExecution,
            ProducerOutcome::ResourceBreach,
            facts,
        ),
        None,
    );

    assert_eq!(export["outcome"], "RESOURCE_BREACH");
    assert_eq!(
        export["runtime_facts"]["resource_observations"][0]["enforcement_status"],
        "RUNTIME_LIMIT_ENFORCED"
    );
}

#[test]
fn capture_bound_is_not_upgraded_to_runtime_enforcement() {
    let observation = ResourceLimitObservation {
        kind: ResourceLimitKind::StdoutBytes,
        configured_limit: ResourceLimitValue::Bytes(8),
        observed_value: Some(ResourceLimitValue::Bytes(12)),
        enforcement_status: ResourceEnforcementStatus::CaptureBoundEnforced,
        terminated_execution: false,
        truncated: Some(true),
    };
    let facts = facts(ProcessExit::ExitedWithCode(0), Duration::from_millis(12))
        .with_resource_observations([observation]);
    let export = value(
        &result(
            ExecutionPhase::FixedExecution,
            ProducerOutcome::Success,
            facts,
        ),
        None,
    );

    assert_eq!(
        export["runtime_facts"]["resource_observations"][0]["enforcement_status"],
        "CAPTURE_BOUND_ENFORCED"
    );
}

#[test]
fn runner_failure_and_unavailable_runtime_facts_are_preserved() {
    let facts =
        ProducerRuntimeFacts::new(metadata(None), ProcessExit::NeverStarted, Duration::ZERO)
            .with_availability(RuntimeFactAvailability::Unavailable)
            .with_failures(vec![ExecutionFailure::SpawnFailure {
                kind: io::ErrorKind::NotFound,
                message: "SECRET SPAWN PROSE".to_owned(),
            }]);
    let export = value(
        &result(
            ExecutionPhase::Compile,
            ProducerOutcome::RunnerFailure,
            facts,
        ),
        None,
    );

    assert_eq!(export["outcome"], "RUNNER_FAILURE");
    assert_eq!(export["runtime_facts"]["availability"], "UNAVAILABLE");
    assert_eq!(
        export["runtime_facts"]["failures"][0],
        json!({"kind":"SPAWN_FAILURE","error_kind":"NOT_FOUND"})
    );
    assert!(!export.to_string().contains("SECRET SPAWN PROSE"));
}

#[test]
fn identities_and_optional_references_are_preserved_exactly() {
    let result = success(ExecutionPhase::Compile)
        .with_candidate_version_reference(CandidateVersionReference::new(" candidate:v1 ").unwrap())
        .with_correlation_reference(CorrelationReference::new("correlation:abc").unwrap());
    let bytes = to_json_bytes(&result, None).unwrap();
    let decoded = from_json_bytes(&bytes).unwrap();

    assert_eq!(decoded.producer_result_id(), "producer-result-1");
    assert_eq!(decoded.workflow_attempt_id(), "workflow-attempt-1");
    assert_eq!(
        decoded.candidate_version_reference(),
        Some(" candidate:v1 ")
    );
    assert_eq!(decoded.correlation_reference(), Some("correlation:abc"));
}

#[test]
fn output_metadata_crosses_wire_but_raw_stdout_and_stderr_do_not() {
    const STDOUT_SECRET: &[u8] = b"RAW-STDOUT-SECRET";
    const STDERR_SECRET: &[u8] = b"RAW-STDERR-SECRET";
    let execution = ExecutionResult {
        phase: ExecutionPhase::Compile,
        runtime_metadata: metadata(Some(41)),
        process_exit: ProcessExit::ExitedWithCode(0),
        timeout: TimeoutOutcome::NotConfigured,
        cancellation: CancellationOutcome::NotSelected,
        stdout: BoundedOutput {
            captured_bytes: STDOUT_SECRET.to_vec(),
            total_bytes_observed: 40,
            capture_limit_bytes: STDOUT_SECRET.len() as u64,
            truncated: true,
        },
        stderr: BoundedOutput {
            captured_bytes: STDERR_SECRET.to_vec(),
            total_bytes_observed: STDERR_SECRET.len() as u64,
            capture_limit_bytes: STDERR_SECRET.len() as u64,
            truncated: false,
        },
        duration: Duration::from_millis(5),
        resource_observations: Vec::new(),
        failures: Vec::new(),
    };
    let producer = producer_result_from_execution(
        &execution,
        ProducerResultId::new("producer-result-1").unwrap(),
        WorkflowAttemptId::new("workflow-attempt-1").unwrap(),
        ProducerResultReferences {
            stdout_logical_reference: Some("logical://stdout"),
            stderr_logical_reference: Some("logical://stderr"),
            ..ProducerResultReferences::default()
        },
    )
    .unwrap();
    let bytes = to_json_bytes(&producer, None).unwrap();
    let rendered = String::from_utf8(bytes).unwrap();
    let export: Value = serde_json::from_str(&rendered).unwrap();

    assert!(!rendered.contains("RAW-STDOUT-SECRET"));
    assert!(!rendered.contains("RAW-STDERR-SECRET"));
    assert_eq!(
        export["runtime_facts"]["output_references"][0],
        json!({
            "kind":"STDOUT",
            "logical_reference":"logical://stdout",
            "observed_bytes":40,
            "retained_bytes":STDOUT_SECRET.len(),
            "capture_limit_bytes":STDOUT_SECRET.len(),
            "truncated":true
        })
    );
}

#[test]
fn equivalent_inputs_are_byte_identical_and_round_trip() {
    let first = success(ExecutionPhase::FixedExecution);
    let second = success(ExecutionPhase::FixedExecution);
    let first_bytes = to_json_bytes(&first, None).unwrap();
    let second_bytes = to_json_bytes(&second, None).unwrap();

    assert_eq!(first_bytes, second_bytes);
    let decoded = from_json_bytes(&first_bytes).unwrap();
    assert_eq!(decoded.version(), EXECUTION_EXPORT_VERSION);
    assert_eq!(decoded, from_json_bytes(&second_bytes).unwrap());
    assert!(!first_bytes.contains(&b'\n'));
}

#[test]
fn every_supported_outcome_encodes_then_decodes() {
    let cases = [
        success(ExecutionPhase::Compile),
        nonzero(
            ExecutionPhase::Compile,
            ProducerOutcome::CompilationFailure,
            2,
        ),
        nonzero(
            ExecutionPhase::BuggyExecution,
            ProducerOutcome::TestFailure,
            1,
        ),
        timeout_result(),
        cancellation_result(),
        resource_breach_result(),
        spawn_failure_result(),
    ];

    for case in cases {
        let bytes = to_json_bytes(&case, None).unwrap();
        assert!(from_json_bytes(&bytes).is_ok(), "{:?}", case.outcome());
    }
}

#[test]
fn unsupported_missing_and_malformed_version_fail_closed() {
    let bytes = to_json_bytes(&success(ExecutionPhase::Compile), None).unwrap();
    let mut export: Value = serde_json::from_slice(&bytes).unwrap();
    export["version"] = json!("testgap.execution-export.v2");
    assert!(from_json_bytes(&serde_json::to_vec(&export).unwrap()).is_err());

    export.as_object_mut().unwrap().remove("version");
    assert!(from_json_bytes(&serde_json::to_vec(&export).unwrap()).is_err());
    assert!(from_json_bytes(br#"{"version": "testgap.execution-export.v1""#).is_err());
}

#[test]
fn missing_required_field_and_malformed_type_fail_closed() {
    let bytes = to_json_bytes(&success(ExecutionPhase::Compile), None).unwrap();
    let mut missing: Value = serde_json::from_slice(&bytes).unwrap();
    missing.as_object_mut().unwrap().remove("outcome");
    assert!(from_json_bytes(&serde_json::to_vec(&missing).unwrap()).is_err());

    let mut malformed: Value = serde_json::from_slice(&bytes).unwrap();
    malformed["runtime_facts"]["duration"]["seconds"] = json!(1.5);
    assert!(from_json_bytes(&serde_json::to_vec(&malformed).unwrap()).is_err());
}

#[test]
fn all_adversarial_authority_fields_are_rejected() {
    let bytes = to_json_bytes(&success(ExecutionPhase::Compile), None).unwrap();
    for field in [
        "command",
        "shell",
        "permissions",
        "is_authorized",
        "can_execute",
        "workflow_transition",
        "queue_message",
        "database_id",
        "access_token",
        "secret",
    ] {
        let mut export: Value = serde_json::from_slice(&bytes).unwrap();
        export
            .as_object_mut()
            .unwrap()
            .insert(field.to_owned(), json!(true));
        assert!(
            from_json_bytes(&serde_json::to_vec(&export).unwrap()).is_err(),
            "{field}"
        );
    }

    let mut nested: Value = serde_json::from_slice(&bytes).unwrap();
    nested["runtime_facts"]["command"] = json!("run me");
    assert!(from_json_bytes(&serde_json::to_vec(&nested).unwrap()).is_err());
}

#[test]
fn summary_phase_contradiction_and_invalid_junit_counts_fail_closed() {
    assert!(to_json_bytes(
        &success(ExecutionPhase::Compile),
        Some(ExecutionTestSummary::JUnit(TestRunSummary {
            tests_run: 1,
            failures: 0
        }))
    )
    .is_err());

    assert!(to_json_bytes(
        &success(ExecutionPhase::FixedExecution),
        Some(ExecutionTestSummary::JUnit(TestRunSummary {
            tests_run: 1,
            failures: 2
        }))
    )
    .is_err());

    let compile = to_json_bytes(&success(ExecutionPhase::Compile), None).unwrap();
    let mut contradictory: Value = serde_json::from_slice(&compile).unwrap();
    contradictory["test_summary"] = json!({"source":"DEFECTS4J","failing_test_count":1});
    assert!(from_json_bytes(&serde_json::to_vec(&contradictory).unwrap()).is_err());

    let test = to_json_bytes(&success(ExecutionPhase::FixedExecution), None).unwrap();
    let mut invalid_counts: Value = serde_json::from_slice(&test).unwrap();
    invalid_counts["test_summary"] = json!({"source":"JUNIT","tests_run":1,"failures":2});
    assert!(from_json_bytes(&serde_json::to_vec(&invalid_counts).unwrap()).is_err());
}

#[test]
fn decoded_output_metadata_is_revalidated() {
    let reference = BoundedOutputReference::new(
        ProducerOutputKind::Stdout,
        "logical://stdout",
        8,
        8,
        8,
        false,
    )
    .unwrap();
    let facts = facts(ProcessExit::ExitedWithCode(0), Duration::from_millis(1))
        .with_output_references([reference])
        .unwrap();
    let bytes = to_json_bytes(
        &result(ExecutionPhase::Compile, ProducerOutcome::Success, facts),
        None,
    )
    .unwrap();
    let mut export: Value = serde_json::from_slice(&bytes).unwrap();
    export["runtime_facts"]["output_references"][0]["retained_bytes"] = json!(9);

    assert!(from_json_bytes(&serde_json::to_vec(&export).unwrap()).is_err());
}

#[test]
fn decoded_runtime_contradictions_fail_closed() {
    let success = value(&success(ExecutionPhase::Compile), None);

    let mut invalid = success.clone();
    invalid["runtime_facts"]["process_exit"] = json!({"kind":"EXITED_WITH_CODE","code":7});
    assert_wire_rejected("success with non-zero exit", &invalid);

    let mut invalid = success.clone();
    invalid["runtime_facts"]["failures"] =
        json!([{"kind":"OUTPUT_CAPTURE_FAILURE","stream":"STDOUT","error_kind":null}]);
    assert_wire_rejected("success with runtime failure", &invalid);

    for availability in ["INCOMPLETE", "UNAVAILABLE"] {
        let mut invalid = success.clone();
        invalid["runtime_facts"]["availability"] = json!(availability);
        assert_wire_rejected("success with incomplete runtime facts", &invalid);
    }

    let mut invalid = value(
        &nonzero(
            ExecutionPhase::Compile,
            ProducerOutcome::CompilationFailure,
            2,
        ),
        None,
    );
    invalid["phase"] = json!("BUGGY_OR_TARGET_REVISION_TEST");
    assert_wire_rejected("compile failure on test phase", &invalid);

    let mut invalid = value(
        &nonzero(
            ExecutionPhase::BuggyExecution,
            ProducerOutcome::TestFailure,
            1,
        ),
        None,
    );
    invalid["phase"] = json!("COMPILE");
    assert_wire_rejected("test failure on compile phase", &invalid);

    let timeout = value(&timeout_result(), None);
    let mut invalid = timeout.clone();
    invalid["runtime_facts"]["timeout"] = json!({"kind":"NOT_CONFIGURED"});
    assert_wire_rejected("timeout without triggered facts", &invalid);

    let mut invalid = timeout.clone();
    invalid["outcome"] = json!("RUNNER_FAILURE");
    assert_wire_rejected("triggered timeout with incompatible outcome", &invalid);

    let cancellation = value(&cancellation_result(), None);
    let mut invalid = cancellation.clone();
    invalid["runtime_facts"]["cancellation"] = json!("NOT_SELECTED");
    assert_wire_rejected("cancellation without selection", &invalid);

    let mut invalid = cancellation.clone();
    invalid["outcome"] = json!("RUNNER_FAILURE");
    assert_wire_rejected("selected cancellation with incompatible outcome", &invalid);

    let mut invalid = timeout.clone();
    invalid["runtime_facts"]["timeout"] =
        json!({"kind":"NOT_TRIGGERED","limit":{"seconds":30,"nanoseconds":0}});
    assert_wire_rejected("timeout termination without trigger", &invalid);

    let mut invalid = cancellation.clone();
    invalid["runtime_facts"]["cancellation"] = json!("NOT_SELECTED");
    assert_wire_rejected("cancellation termination without selection", &invalid);

    let resource_breach = value(&resource_breach_result(), None);
    let mut invalid = resource_breach.clone();
    invalid["runtime_facts"]["resource_observations"] = json!([]);
    assert_wire_rejected("resource breach without terminating evidence", &invalid);

    let mut invalid = resource_breach.clone();
    invalid["runtime_facts"]["resource_observations"][0]["enforcement_status"] =
        json!("NOT_ENFORCED");
    assert_wire_rejected("terminating resource without enforcement", &invalid);

    let spawn_failure = value(&spawn_failure_result(), None);
    let mut invalid = spawn_failure.clone();
    invalid["runtime_facts"]["metadata"]["process_id"] = json!(41);
    assert_wire_rejected("never started with process ID", &invalid);

    let mut invalid = success.clone();
    invalid["runtime_facts"]["metadata"]["process_id"] = Value::Null;
    assert_wire_rejected("started process without process ID", &invalid);

    let capture_failure = value(&capture_failure_result(), None);
    let mut invalid = capture_failure.clone();
    invalid["runtime_facts"]["availability"] = json!("UNAVAILABLE");
    assert_wire_rejected("unavailable facts for started process", &invalid);

    let mut invalid = spawn_failure.clone();
    invalid["runtime_facts"]["failures"]
        .as_array_mut()
        .unwrap()
        .push(json!({"kind":"WAIT_FAILURE","error_kind":"OTHER"}));
    assert_wire_rejected("spawn failure with additional failure", &invalid);

    let mut invalid = spawn_failure;
    invalid["runtime_facts"]["process_exit"] = json!({"kind":"EXITED_WITH_CODE","code":0});
    invalid["runtime_facts"]["metadata"]["process_id"] = json!(41);
    assert_wire_rejected("spawn failure with started process", &invalid);

    let mut invalid = capture_failure;
    invalid["runtime_facts"]["process_exit"] = json!({"kind":"EXITED_WITHOUT_CODE"});
    assert_wire_rejected("primary failure incompatible with process exit", &invalid);

    let mut invalid = value(
        &nonzero(
            ExecutionPhase::Compile,
            ProducerOutcome::CompilationFailure,
            7,
        ),
        None,
    );
    invalid["runtime_facts"]["process_exit"]["code"] = json!(8);
    assert_wire_rejected("non-zero exit with mismatched failure code", &invalid);
}

#[test]
fn source_precheck_rejects_oversized_identity_and_reference_strings() {
    let oversized = "x".repeat(180_000);
    assert!(oversized.len() < MAX_EXECUTION_EXPORT_BYTES);

    let producer_id = ProducerResult::new(
        ProducerResultId::new(&oversized).unwrap(),
        WorkflowAttemptId::new("attempt").unwrap(),
        ExecutionPhase::Compile,
        ProducerOutcome::Success,
        facts(ProcessExit::ExitedWithCode(0), Duration::ZERO),
    )
    .unwrap();
    assert_source_precheck_rejected(&producer_id);

    let workflow_id = ProducerResult::new(
        ProducerResultId::new("result").unwrap(),
        WorkflowAttemptId::new(&oversized).unwrap(),
        ExecutionPhase::Compile,
        ProducerOutcome::Success,
        facts(ProcessExit::ExitedWithCode(0), Duration::ZERO),
    )
    .unwrap();
    assert_source_precheck_rejected(&workflow_id);

    let candidate = success(ExecutionPhase::Compile)
        .with_candidate_version_reference(CandidateVersionReference::new(&oversized).unwrap());
    assert_source_precheck_rejected(&candidate);

    let correlation = success(ExecutionPhase::Compile)
        .with_correlation_reference(CorrelationReference::new(&oversized).unwrap());
    assert_source_precheck_rejected(&correlation);
}

#[test]
fn source_precheck_rejects_oversized_resource_strings() {
    let oversized = "x".repeat(180_000);
    let other = ResourceLimitObservation {
        kind: ResourceLimitKind::Other(oversized.clone()),
        configured_limit: ResourceLimitValue::Count(1),
        observed_value: None,
        enforcement_status: ResourceEnforcementStatus::NotEnforced,
        terminated_execution: false,
        truncated: None,
    };
    let result_with_other = result(
        ExecutionPhase::Compile,
        ProducerOutcome::Success,
        facts(ProcessExit::ExitedWithCode(0), Duration::ZERO).with_resource_observations([other]),
    );
    assert_source_precheck_rejected(&result_with_other);

    let custom = ResourceLimitObservation {
        kind: ResourceLimitKind::ProcessCount,
        configured_limit: ResourceLimitValue::Custom {
            value: 1,
            unit: oversized,
        },
        observed_value: None,
        enforcement_status: ResourceEnforcementStatus::NotEnforced,
        terminated_execution: false,
        truncated: None,
    };
    let result_with_custom = result(
        ExecutionPhase::Compile,
        ProducerOutcome::Success,
        facts(ProcessExit::ExitedWithCode(0), Duration::ZERO).with_resource_observations([custom]),
    );
    assert_source_precheck_rejected(&result_with_custom);
}

#[test]
fn source_precheck_rejects_excessive_borrowed_collections() {
    let observation = ResourceLimitObservation {
        kind: ResourceLimitKind::MemoryBytes,
        configured_limit: ResourceLimitValue::Bytes(1),
        observed_value: None,
        enforcement_status: ResourceEnforcementStatus::NotEnforced,
        terminated_execution: false,
        truncated: None,
    };
    let resources = result(
        ExecutionPhase::Compile,
        ProducerOutcome::Success,
        facts(ProcessExit::ExitedWithCode(0), Duration::ZERO)
            .with_resource_observations(vec![observation; 2_049]),
    );
    assert_source_precheck_rejected(&resources);

    let mut failures = vec![ExecutionFailure::Timeout];
    failures.extend(vec![
        ExecutionFailure::TerminationFailure {
            kind: io::ErrorKind::Other,
            message: String::new(),
        };
        8_192
    ]);
    let failures = result(
        ExecutionPhase::Compile,
        ProducerOutcome::Timeout,
        facts(
            ProcessExit::TerminatedBySupervisor {
                reason: SupervisorTermination::Timeout,
                code: None,
            },
            Duration::ZERO,
        )
        .with_timeout(TimeoutOutcome::Triggered {
            limit: Duration::from_secs(1),
        })
        .with_failures(failures),
    );
    assert_source_precheck_rejected(&failures);
}

#[test]
fn source_precheck_rejects_cumulative_individually_small_values() {
    let observations = (0..1_000)
        .map(|index| ResourceLimitObservation {
            kind: ResourceLimitKind::Other(format!("resource-{index:04}-{}", "x".repeat(80))),
            configured_limit: ResourceLimitValue::Custom {
                value: 1,
                unit: "small-unit".to_owned(),
            },
            observed_value: None,
            enforcement_status: ResourceEnforcementStatus::NotEnforced,
            terminated_execution: false,
            truncated: None,
        })
        .collect::<Vec<_>>();
    let cumulative = result(
        ExecutionPhase::Compile,
        ProducerOutcome::Success,
        facts(ProcessExit::ExitedWithCode(0), Duration::ZERO)
            .with_resource_observations(observations),
    );

    assert_source_precheck_rejected(&cumulative);
}

#[test]
fn envelope_is_explicitly_bounded() {
    let oversized = vec![b' '; MAX_EXECUTION_EXPORT_BYTES + 1];
    assert!(from_json_bytes(&oversized).is_err());
}

#[test]
fn export_module_adds_no_evidence_workflow_queue_db_network_or_execution_capability() {
    let source = include_str!("../src/execution_export.rs");
    for prohibited in [
        "ExecutionEvidence",
        "EvidenceCard",
        "EvidenceBundle",
        "workflow_transition",
        "queue_message",
        "database_id",
        "std::net",
        "std::process::Command",
    ] {
        assert!(!source.contains(prohibited), "{prohibited}");
    }
}
