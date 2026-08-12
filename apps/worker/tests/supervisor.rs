use std::env;
use std::ffi::OsString;
use std::fs;
use std::path::{Path, PathBuf};
use std::process;
use std::sync::atomic::{AtomicU64, Ordering};
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};
use testgap_worker::{
    CancellationOutcome, CancellationToken, EnvironmentPolicy, ExecutionCommand, ExecutionFailure,
    ExecutionPhase, ExecutionRequest, ProcessExit, ProcessSupervisor, ResourceEnforcementStatus,
    ResourceLimitKind, ResourceLimitObservation, ResourceLimitValue, SupervisorTermination,
    TimeoutOutcome,
};

const FIXTURE: &str = env!("CARGO_BIN_EXE_process_fixture");

fn strings(values: &[&str]) -> Vec<OsString> {
    values.iter().map(OsString::from).collect()
}

fn request(arguments: Vec<OsString>) -> ExecutionRequest {
    let mut command = ExecutionCommand::new(FIXTURE, env::current_dir().unwrap());
    command.arguments = arguments;
    ExecutionRequest::new(ExecutionPhase::Compile, command)
}

fn execute(arguments: &[&str]) -> testgap_worker::ExecutionResult {
    ProcessSupervisor.execute(request(strings(arguments)))
}

fn observation<'a>(
    result: &'a testgap_worker::ExecutionResult,
    kind: &ResourceLimitKind,
) -> &'a ResourceLimitObservation {
    result
        .resource_observations
        .iter()
        .find(|observation| &observation.kind == kind)
        .unwrap()
}

struct TestDirectory(PathBuf);

impl TestDirectory {
    fn new(label: &str) -> Self {
        static NEXT: AtomicU64 = AtomicU64::new(0);
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let path = env::temp_dir().join(format!(
            "testgap-worker-{label}-{}-{timestamp}-{}",
            process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&path).unwrap();
        Self(fs::canonicalize(path).unwrap())
    }

    fn path(&self) -> &Path {
        &self.0
    }
}

impl Drop for TestDirectory {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

#[cfg(unix)]
const SIGKILL: i32 = 9;

#[cfg(unix)]
struct DescendantGuard(Option<i32>);

#[cfg(unix)]
impl DescendantGuard {
    fn new(process_id: i32) -> Self {
        Self(Some(process_id))
    }

    fn disarm(&mut self) {
        self.0 = None;
    }
}

#[cfg(unix)]
impl Drop for DescendantGuard {
    fn drop(&mut self) {
        if let Some(process_id) = self.0 {
            // SAFETY: the positive PID came from the fixture's freshly written
            // descendant marker; SIGKILL is a bounded panic-cleanup fallback.
            unsafe {
                kill(process_id, SIGKILL);
            }
        }
    }
}

#[cfg(unix)]
fn wait_for_descendant(path: &Path, deadline: Instant) -> i32 {
    while Instant::now() < deadline {
        if let Ok(contents) = fs::read_to_string(path) {
            let process_id = contents.parse().unwrap();
            if process_is_alive(process_id) {
                return process_id;
            }
        }
        thread::sleep(Duration::from_millis(5));
    }
    panic!("fixture did not create a live descendant before the deadline");
}

#[cfg(unix)]
fn wait_for_process_exit(process_id: i32, deadline: Instant) -> bool {
    while Instant::now() < deadline {
        if !process_is_alive(process_id) {
            return true;
        }
        thread::sleep(Duration::from_millis(5));
    }
    !process_is_alive(process_id)
}

#[cfg(unix)]
fn process_is_alive(process_id: i32) -> bool {
    #[cfg(target_os = "linux")]
    if fs::read_to_string(format!("/proc/{process_id}/stat"))
        .ok()
        .and_then(|stat| {
            stat.rsplit_once(") ")
                .and_then(|(_, rest)| rest.chars().next())
        })
        == Some('Z')
    {
        return false;
    }

    // kill(pid, 0) has an unavoidable PID-reuse race; these tests minimize it
    // by probing only freshly spawned PIDs and disarming cleanup immediately.
    // SAFETY: signal 0 performs no termination and process_id is positive.
    let result = unsafe { kill(process_id, 0) };
    if result == 0 {
        return true;
    }

    match std::io::Error::last_os_error().raw_os_error() {
        Some(1) => true,  // EPERM: the process exists.
        Some(3) => false, // ESRCH: the process no longer exists.
        error => panic!("unexpected kill(pid, 0) error: {error:?}"),
    }
}

#[cfg(unix)]
unsafe extern "C" {
    fn kill(pid: i32, signal: i32) -> i32;
}

#[test]
fn cancellation_token_handles_share_state() {
    let token = CancellationToken::new();
    let another_handle = token.clone();
    another_handle.cancel();
    assert!(token.is_cancelled());
}

#[test]
fn successful_process() {
    let result = execute(&["exit", "0"]);

    assert!(result.is_success());
    assert_eq!(result.process_exit, ProcessExit::ExitedWithCode(0));
    assert_eq!(result.timeout, TimeoutOutcome::NotConfigured);
    assert_eq!(result.cancellation, CancellationOutcome::NotSelected);
    assert!(result.failures.is_empty());
}

#[test]
fn successful_process_reports_runtime_metadata() {
    let result = execute(&["exit", "0"]);

    assert_eq!(result.runtime_metadata.operating_system, env::consts::OS);
    assert_eq!(result.runtime_metadata.architecture, env::consts::ARCH);
    assert!(result.runtime_metadata.process_id.is_some_and(|id| id > 0));
}

#[test]
fn spawn_failure_reports_runtime_metadata_without_process_id() {
    let directory = TestDirectory::new("runtime-metadata-spawn-failure");
    let mut request = request(Vec::new());
    request.command.executable = directory.path().join("absent-executable").into_os_string();
    let result = ProcessSupervisor.execute(request);

    assert_eq!(result.runtime_metadata.operating_system, env::consts::OS);
    assert_eq!(result.runtime_metadata.architecture, env::consts::ARCH);
    assert_eq!(result.runtime_metadata.process_id, None);
}

#[test]
fn repeated_executions_each_report_a_process_id() {
    let first = execute(&["exit", "0"]);
    let second = execute(&["exit", "0"]);

    assert!(first.runtime_metadata.process_id.is_some_and(|id| id > 0));
    assert!(second.runtime_metadata.process_id.is_some_and(|id| id > 0));
}

#[test]
fn non_zero_exit() {
    let result = execute(&["exit", "23"]);

    assert!(!result.is_success());
    assert_eq!(result.process_exit, ProcessExit::ExitedWithCode(23));
    assert!(matches!(
        result.primary_failure(),
        Some(ExecutionFailure::NonZeroExit { code: Some(23) })
    ));
    assert_eq!(result.timeout, TimeoutOutcome::NotConfigured);
    assert_eq!(result.cancellation, CancellationOutcome::NotSelected);
}

#[test]
fn stdout_capture_preserves_exact_bytes() {
    let result = execute(&["stdout_text", "hello\nstdout"]);

    assert!(result.is_success());
    assert_eq!(result.stdout.captured_bytes, b"hello\nstdout");
    assert_eq!(result.stdout.total_bytes_observed, 12);
    assert!(!result.stdout.truncated);
}

#[test]
fn stderr_capture_preserves_exact_bytes() {
    let result = execute(&["stderr_text", "hello\nstderr"]);

    assert!(result.is_success());
    assert_eq!(result.stderr.captured_bytes, b"hello\nstderr");
    assert_eq!(result.stderr.total_bytes_observed, 12);
    assert!(!result.stderr.truncated);
}

#[test]
fn bounded_stdout_is_fully_drained() {
    let mut request = request(strings(&["stdout", "100000"]));
    request.resource_limits.stdout_bytes = 1024;
    let result = ProcessSupervisor.execute(request);

    assert!(result.is_success());
    assert_eq!(result.stdout.captured_bytes, vec![b'O'; 1024]);
    assert_eq!(result.stdout.total_bytes_observed, 100_000);
    assert_eq!(result.stdout.capture_limit_bytes, 1024);
    assert!(result.stdout.truncated);
}

#[test]
fn bounded_stderr_is_fully_drained_independently() {
    let mut request = request(strings(&["stderr", "100000"]));
    request.resource_limits.stderr_bytes = 513;
    let result = ProcessSupervisor.execute(request);

    assert!(result.is_success());
    assert_eq!(result.stderr.captured_bytes, vec![b'E'; 513]);
    assert_eq!(result.stderr.total_bytes_observed, 100_000);
    assert_eq!(result.stderr.capture_limit_bytes, 513);
    assert!(result.stderr.truncated);
    assert_eq!(result.stdout.total_bytes_observed, 0);
}

#[test]
fn timeout_terminates_and_reaps_direct_child() {
    let mut request = request(strings(&["sleep_ms", "2000"]));
    request.resource_limits.timeout = Some(Duration::from_millis(40));
    let started_at = Instant::now();
    let result = ProcessSupervisor.execute(request);

    assert!(started_at.elapsed() < Duration::from_secs(1));
    assert!(matches!(
        result.process_exit,
        ProcessExit::TerminatedBySupervisor {
            reason: SupervisorTermination::Timeout,
            ..
        }
    ));
    assert_eq!(
        result.timeout,
        TimeoutOutcome::Triggered {
            limit: Duration::from_millis(40)
        }
    );
    assert_eq!(result.cancellation, CancellationOutcome::NotSelected);
    assert!(matches!(
        result.primary_failure(),
        Some(ExecutionFailure::Timeout)
    ));
}

#[test]
fn cancellation_terminates_and_reaps_direct_child() {
    let mut request = request(strings(&["sleep_ms", "2000"]));
    request.resource_limits.timeout = Some(Duration::from_secs(1));
    let token = request.cancellation.clone();
    let canceller = thread::spawn(move || {
        thread::sleep(Duration::from_millis(40));
        token.cancel();
    });
    let started_at = Instant::now();
    let result = ProcessSupervisor.execute(request);
    canceller.join().unwrap();

    assert!(started_at.elapsed() < Duration::from_secs(1));
    assert!(matches!(
        result.process_exit,
        ProcessExit::TerminatedBySupervisor {
            reason: SupervisorTermination::Cancellation,
            ..
        }
    ));
    assert_eq!(result.cancellation, CancellationOutcome::Selected);
    assert_eq!(
        result.timeout,
        TimeoutOutcome::NotTriggered {
            limit: Duration::from_secs(1)
        }
    );
    assert!(matches!(
        result.primary_failure(),
        Some(ExecutionFailure::Cancelled)
    ));
}

#[cfg(unix)]
#[test]
fn timeout_terminates_real_descendant_tree() {
    let directory = TestDirectory::new("timeout-descendant");
    let descendant_path = directory.path().join("descendant-pid");
    let mut request = request(vec![
        OsString::from("spawn_descendant"),
        descendant_path.clone().into_os_string(),
        OsString::from("5000"),
    ]);
    request.resource_limits.timeout = Some(Duration::from_millis(500));

    let started_at = Instant::now();
    let execution = thread::spawn(move || ProcessSupervisor.execute(request));
    let descendant_id = wait_for_descendant(
        &descendant_path,
        Instant::now() + Duration::from_millis(400),
    );
    let mut descendant_guard = DescendantGuard::new(descendant_id);
    let result = execution.join().unwrap();
    let direct_child_id = i32::try_from(result.runtime_metadata.process_id.unwrap()).unwrap();

    assert!(started_at.elapsed() < Duration::from_secs(2));
    assert!(matches!(
        result.process_exit,
        ProcessExit::TerminatedBySupervisor {
            reason: SupervisorTermination::Timeout,
            ..
        }
    ));
    assert_eq!(
        result.timeout,
        TimeoutOutcome::Triggered {
            limit: Duration::from_millis(500)
        }
    );
    assert_eq!(result.cancellation, CancellationOutcome::NotSelected);
    assert!(matches!(
        result.primary_failure(),
        Some(ExecutionFailure::Timeout)
    ));
    assert!(wait_for_process_exit(
        direct_child_id,
        Instant::now() + Duration::from_secs(1)
    ));
    assert!(wait_for_process_exit(
        descendant_id,
        Instant::now() + Duration::from_secs(1)
    ));
    descendant_guard.disarm();
}

#[cfg(unix)]
#[test]
fn cancellation_terminates_real_descendant_tree() {
    let directory = TestDirectory::new("cancellation-descendant");
    let descendant_path = directory.path().join("descendant-pid");
    let mut request = request(vec![
        OsString::from("spawn_descendant"),
        descendant_path.clone().into_os_string(),
        OsString::from("5000"),
    ]);
    request.resource_limits.timeout = Some(Duration::from_secs(2));
    let token = request.cancellation.clone();

    let started_at = Instant::now();
    let execution = thread::spawn(move || ProcessSupervisor.execute(request));
    let descendant_id =
        wait_for_descendant(&descendant_path, Instant::now() + Duration::from_secs(1));
    let mut descendant_guard = DescendantGuard::new(descendant_id);
    token.cancel();
    let result = execution.join().unwrap();
    let direct_child_id = i32::try_from(result.runtime_metadata.process_id.unwrap()).unwrap();

    assert!(started_at.elapsed() < Duration::from_secs(1));
    assert!(matches!(
        result.process_exit,
        ProcessExit::TerminatedBySupervisor {
            reason: SupervisorTermination::Cancellation,
            ..
        }
    ));
    assert_eq!(result.cancellation, CancellationOutcome::Selected);
    assert_eq!(
        result.timeout,
        TimeoutOutcome::NotTriggered {
            limit: Duration::from_secs(2)
        }
    );
    assert!(matches!(
        result.primary_failure(),
        Some(ExecutionFailure::Cancelled)
    ));
    assert!(wait_for_process_exit(
        direct_child_id,
        Instant::now() + Duration::from_secs(1)
    ));
    assert!(wait_for_process_exit(
        descendant_id,
        Instant::now() + Duration::from_secs(1)
    ));
    descendant_guard.disarm();
}

#[test]
fn cleanup_after_timeout_prevents_late_marker_write() {
    let directory = TestDirectory::new("timeout-cleanup");
    let marker = directory.path().join("marker");
    let mut request = request(vec![
        OsString::from("sleep_then_write"),
        OsString::from("500"),
        marker.clone().into_os_string(),
    ]);
    request.resource_limits.timeout = Some(Duration::from_millis(40));

    let result = ProcessSupervisor.execute(request);
    assert!(matches!(
        result.primary_failure(),
        Some(ExecutionFailure::Timeout)
    ));
    thread::sleep(Duration::from_millis(650));
    assert!(!marker.exists());
}

#[test]
fn cleanup_after_cancellation_prevents_late_marker_write() {
    let directory = TestDirectory::new("cancellation-cleanup");
    let marker = directory.path().join("marker");
    let mut request = request(vec![
        OsString::from("sleep_then_write"),
        OsString::from("500"),
        marker.clone().into_os_string(),
    ]);
    request.resource_limits.timeout = Some(Duration::from_secs(2));
    let token = request.cancellation.clone();
    let canceller = thread::spawn(move || {
        thread::sleep(Duration::from_millis(40));
        token.cancel();
    });

    let result = ProcessSupervisor.execute(request);
    canceller.join().unwrap();
    assert!(matches!(
        result.primary_failure(),
        Some(ExecutionFailure::Cancelled)
    ));
    thread::sleep(Duration::from_millis(650));
    assert!(!marker.exists());
}

#[test]
fn working_directory_is_applied() {
    let directory = TestDirectory::new("cwd");
    let mut request = request(strings(&["print_cwd"]));
    request.command.working_directory = directory.path().to_path_buf();
    let result = ProcessSupervisor.execute(request);

    assert!(result.is_success());
    assert_eq!(
        PathBuf::from(String::from_utf8(result.stdout.captured_bytes).unwrap()),
        directory.path()
    );
}

#[test]
fn argument_vector_preserves_boundaries_and_metacharacters() {
    let values = [
        "hello world",
        "semi;colon",
        "quote\"value",
        "single'quote",
        "$(not-a-command)",
        "&&",
        "*",
    ];
    let mut arguments = vec![OsString::from("echo_args")];
    arguments.extend(values.iter().map(OsString::from));
    let result = ProcessSupervisor.execute(request(arguments));
    let expected: String = values
        .iter()
        .map(|value| format!("{}:{value}\n", value.len()))
        .collect();

    assert!(result.is_success());
    assert_eq!(result.stdout.captured_bytes, expected.as_bytes());
}

#[test]
fn clear_environment_sets_only_explicit_values() {
    assert!(env::var_os("PATH").is_some());
    let mut explicit = request(strings(&["print_env", "WORKER_TEST_VALUE"]));
    explicit.command.environment = EnvironmentPolicy::ClearAndSet(vec![(
        OsString::from("WORKER_TEST_VALUE"),
        OsString::from("known-value"),
    )]);
    let explicit_result = ProcessSupervisor.execute(explicit);

    let mut parent_only = request(strings(&["print_env", "PATH"]));
    parent_only.command.environment = EnvironmentPolicy::ClearAndSet(vec![(
        OsString::from("WORKER_TEST_VALUE"),
        OsString::from("known-value"),
    )]);
    let parent_only_result = ProcessSupervisor.execute(parent_only);

    assert_eq!(explicit_result.stdout.captured_bytes, b"known-value");
    assert_eq!(parent_only_result.stdout.captured_bytes, b"<unset>");
}

#[test]
fn deterministic_classification_and_cancellation_precedence() {
    let success = execute(&["exit", "0"]);
    let non_zero = execute(&["exit", "7"]);

    let directory = TestDirectory::new("classification");
    let mut invalid = request(strings(&["unused"]));
    invalid.command.executable = directory.path().join("does-not-exist").into_os_string();
    let spawn_failure = ProcessSupervisor.execute(invalid);

    let mut timed = request(strings(&["sleep_ms", "500"]));
    timed.resource_limits.timeout = Some(Duration::from_millis(20));
    let timeout = ProcessSupervisor.execute(timed);

    let mut cancelled = request(strings(&["sleep_ms", "500"]));
    cancelled.resource_limits.timeout = Some(Duration::ZERO);
    cancelled.cancellation.cancel();
    let cancellation = ProcessSupervisor.execute(cancelled);

    assert!(success.primary_failure().is_none());
    assert!(matches!(
        non_zero.primary_failure(),
        Some(ExecutionFailure::NonZeroExit { code: Some(7) })
    ));
    assert!(matches!(
        spawn_failure.primary_failure(),
        Some(ExecutionFailure::SpawnFailure { .. })
    ));
    assert!(matches!(
        timeout.primary_failure(),
        Some(ExecutionFailure::Timeout)
    ));
    assert!(matches!(
        cancellation.primary_failure(),
        Some(ExecutionFailure::Cancelled)
    ));
    assert_eq!(cancellation.cancellation, CancellationOutcome::Selected);
    assert_eq!(
        cancellation.timeout,
        TimeoutOutcome::NotTriggered {
            limit: Duration::ZERO
        }
    );
}

#[test]
fn invalid_executable_is_a_typed_spawn_failure() {
    let directory = TestDirectory::new("invalid-executable");
    let mut request = request(Vec::new());
    request.command.executable = directory.path().join("absent-executable").into_os_string();
    request.resource_limits.timeout = Some(Duration::ZERO);
    request.cancellation.cancel();
    let result = ProcessSupervisor.execute(request);

    assert_eq!(result.process_exit, ProcessExit::NeverStarted);
    assert!(matches!(
        result.primary_failure(),
        Some(ExecutionFailure::SpawnFailure { .. })
    ));
    assert!(result.stdout.captured_bytes.is_empty());
    assert!(result.stderr.captured_bytes.is_empty());
    assert_eq!(result.cancellation, CancellationOutcome::NotSelected);
    assert_eq!(
        result.timeout,
        TimeoutOutcome::NotTriggered {
            limit: Duration::ZERO
        }
    );
}

#[test]
fn resource_observations_preserve_units_and_enforcement_truth() {
    let mut request = request(strings(&["stdout_text", "abc"]));
    request.resource_limits.cpu_time = Some(Duration::from_secs(2));
    request.resource_limits.memory_bytes = Some(10_000);
    request.resource_limits.disk_temp_workspace_bytes = Some(20_000);
    request.resource_limits.process_count = Some(3);
    request.resource_limits.file_count = Some(40);
    request.resource_limits.stdout_bytes = 8;
    request.resource_limits.stderr_bytes = 9;
    request.resource_limits.timeout = Some(Duration::from_secs(1));
    let result = ProcessSupervisor.execute(request);

    for kind in [
        ResourceLimitKind::CpuTime,
        ResourceLimitKind::MemoryBytes,
        ResourceLimitKind::DiskTempWorkspaceBytes,
        ResourceLimitKind::ProcessCount,
        ResourceLimitKind::FileCount,
    ] {
        let observation = observation(&result, &kind);
        assert_eq!(
            observation.enforcement_status,
            ResourceEnforcementStatus::NotEnforced
        );
        assert_eq!(observation.observed_value, None);
        assert!(!observation.terminated_execution);
    }

    assert_eq!(
        observation(&result, &ResourceLimitKind::CpuTime).configured_limit,
        ResourceLimitValue::Duration(Duration::from_secs(2))
    );
    assert_eq!(
        observation(&result, &ResourceLimitKind::MemoryBytes).configured_limit,
        ResourceLimitValue::Bytes(10_000)
    );
    assert_eq!(
        observation(&result, &ResourceLimitKind::DiskTempWorkspaceBytes).configured_limit,
        ResourceLimitValue::Bytes(20_000)
    );
    assert_eq!(
        observation(&result, &ResourceLimitKind::ProcessCount).configured_limit,
        ResourceLimitValue::Count(3)
    );
    assert_eq!(
        observation(&result, &ResourceLimitKind::FileCount).configured_limit,
        ResourceLimitValue::Count(40)
    );

    let stdout = observation(&result, &ResourceLimitKind::StdoutBytes);
    assert_eq!(
        stdout.enforcement_status,
        ResourceEnforcementStatus::CaptureBoundEnforced
    );
    assert_eq!(stdout.configured_limit, ResourceLimitValue::Bytes(8));
    assert_eq!(stdout.observed_value, Some(ResourceLimitValue::Bytes(3)));
    assert_eq!(stdout.truncated, Some(false));

    let stderr = observation(&result, &ResourceLimitKind::StderrBytes);
    assert_eq!(
        stderr.enforcement_status,
        ResourceEnforcementStatus::CaptureBoundEnforced
    );
    assert_eq!(stderr.configured_limit, ResourceLimitValue::Bytes(9));
    assert_eq!(stderr.observed_value, Some(ResourceLimitValue::Bytes(0)));

    let timeout = observation(&result, &ResourceLimitKind::Timeout);
    assert_eq!(
        timeout.enforcement_status,
        ResourceEnforcementStatus::SupervisorTimeoutEnforced
    );
    assert_eq!(
        timeout.configured_limit,
        ResourceLimitValue::Duration(Duration::from_secs(1))
    );
    assert!(matches!(
        timeout.observed_value,
        Some(ResourceLimitValue::Duration(_))
    ));
    assert!(!timeout.terminated_execution);
}

#[test]
fn suspicious_argument_is_data_not_shell_input() {
    let directory = TestDirectory::new("no-shell");
    let marker = directory.path().join("marker");
    let payload = format!("; touch {}", marker.display());
    let result = ProcessSupervisor.execute(request(vec![
        OsString::from("echo_args"),
        OsString::from(&payload),
    ]));
    let expected = format!("{}:{payload}\n", payload.len());

    assert!(result.is_success());
    assert_eq!(result.stdout.captured_bytes, expected.as_bytes());
    assert!(!marker.exists());
}

#[test]
fn repeated_executions_do_not_leak_request_state() {
    let first_directory = TestDirectory::new("isolation-a");
    let second_directory = TestDirectory::new("isolation-b");

    let mut first = request(strings(&["snapshot", "RUN_VALUE", "alpha"]));
    first.command.working_directory = first_directory.path().to_path_buf();
    first.command.environment = EnvironmentPolicy::ClearAndSet(vec![(
        OsString::from("RUN_VALUE"),
        OsString::from("first"),
    )]);
    first.resource_limits.stdout_bytes = 256;

    let mut second = request(strings(&["snapshot", "RUN_VALUE", "beta"]));
    second.command.working_directory = second_directory.path().to_path_buf();
    second.command.environment = EnvironmentPolicy::ClearAndSet(Vec::new());
    second.resource_limits.stdout_bytes = 512;

    let first_result = ProcessSupervisor.execute(first);
    let second_result = ProcessSupervisor.execute(second);
    let first_expected = format!(
        "cwd={}\nenv=first\narg=alpha\n",
        first_directory.path().display()
    );
    let second_expected = format!(
        "cwd={}\nenv=<unset>\narg=beta\n",
        second_directory.path().display()
    );

    assert!(first_result.is_success());
    assert!(second_result.is_success());
    assert_eq!(first_result.stdout.capture_limit_bytes, 256);
    assert_eq!(second_result.stdout.capture_limit_bytes, 512);
    assert_eq!(
        first_result.stdout.captured_bytes,
        first_expected.as_bytes()
    );
    assert_eq!(
        second_result.stdout.captured_bytes,
        second_expected.as_bytes()
    );
}
