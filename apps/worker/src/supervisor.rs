use crate::{
    BoundedOutput, CancellationOutcome, EnvironmentPolicy, ExecutionFailure, ExecutionRequest,
    ExecutionResult, OutputStream, ProcessExit, ResourceEnforcementStatus, ResourceLimitKind,
    ResourceLimitObservation, ResourceLimitRequest, ResourceLimitValue, RuntimeMetadata,
    SupervisorTermination, TimeoutOutcome,
};
use std::cmp;
use std::io::{self, Read};
use std::process::{Child, Command, ExitStatus, Stdio};
use std::thread::{self, JoinHandle};
use std::time::{Duration, Instant};

const POLL_INTERVAL: Duration = Duration::from_millis(5);

#[derive(Debug, Default)]
pub struct ProcessSupervisor;

impl ProcessSupervisor {
    pub fn execute(&self, request: ExecutionRequest) -> ExecutionResult {
        let started_at = Instant::now();
        let mut command = Command::new(&request.command.executable);
        command
            .args(&request.command.arguments)
            .current_dir(&request.command.working_directory)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());

        match &request.command.environment {
            EnvironmentPolicy::ClearAndSet(values) => {
                command.env_clear();
                command.envs(values.iter().map(|(key, value)| (key, value)));
            }
            EnvironmentPolicy::InheritAndOverride(values) => {
                command.envs(values.iter().map(|(key, value)| (key, value)));
            }
        }

        let mut child = match command.spawn() {
            Ok(child) => child,
            Err(error) => {
                let duration = started_at.elapsed();
                return finish_result(
                    &request,
                    None,
                    ProcessExit::NeverStarted,
                    TimeoutOutcome::from_limit(request.resource_limits.timeout, false),
                    CancellationOutcome::NotSelected,
                    BoundedOutput::empty(request.resource_limits.stdout_bytes),
                    BoundedOutput::empty(request.resource_limits.stderr_bytes),
                    duration,
                    vec![ExecutionFailure::SpawnFailure {
                        kind: error.kind(),
                        message: error.to_string(),
                    }],
                );
            }
        };
        let process_id = child.id();

        let (stdout_reader, stdout_setup_failure) = child
            .stdout
            .take()
            .map(|stdout| {
                spawn_reader(
                    stdout,
                    OutputStream::Stdout,
                    request.resource_limits.stdout_bytes,
                )
            })
            .map_or_else(
                || {
                    (
                        None,
                        Some(output_failure(
                            OutputStream::Stdout,
                            None,
                            "spawned child had no stdout pipe".to_owned(),
                        )),
                    )
                },
                |result| reader_or_failure(result, OutputStream::Stdout),
            );
        let (stderr_reader, stderr_setup_failure) = child
            .stderr
            .take()
            .map(|stderr| {
                spawn_reader(
                    stderr,
                    OutputStream::Stderr,
                    request.resource_limits.stderr_bytes,
                )
            })
            .map_or_else(
                || {
                    (
                        None,
                        Some(output_failure(
                            OutputStream::Stderr,
                            None,
                            "spawned child had no stderr pipe".to_owned(),
                        )),
                    )
                },
                |result| reader_or_failure(result, OutputStream::Stderr),
            );

        let mut failures = Vec::new();
        failures.extend(stdout_setup_failure);
        failures.extend(stderr_setup_failure);

        let (process_exit, timeout, cancellation) = if failures.is_empty() {
            supervise_child(&mut child, &request, started_at, &mut failures)
        } else {
            let process_exit = terminate_and_reap(
                &mut child,
                SupervisorTermination::OutputCaptureFailure,
                &mut failures,
            );
            (
                process_exit,
                TimeoutOutcome::from_limit(request.resource_limits.timeout, false),
                CancellationOutcome::NotSelected,
            )
        };

        let stdout = finish_reader(
            stdout_reader,
            OutputStream::Stdout,
            request.resource_limits.stdout_bytes,
            &mut failures,
        );
        let stderr = finish_reader(
            stderr_reader,
            OutputStream::Stderr,
            request.resource_limits.stderr_bytes,
            &mut failures,
        );

        finish_result(
            &request,
            Some(process_id),
            process_exit,
            timeout,
            cancellation,
            stdout,
            stderr,
            started_at.elapsed(),
            failures,
        )
    }
}

impl TimeoutOutcome {
    fn from_limit(limit: Option<Duration>, triggered: bool) -> Self {
        match (limit, triggered) {
            (None, _) => Self::NotConfigured,
            (Some(limit), true) => Self::Triggered { limit },
            (Some(limit), false) => Self::NotTriggered { limit },
        }
    }
}

fn supervise_child(
    child: &mut Child,
    request: &ExecutionRequest,
    started_at: Instant,
    failures: &mut Vec<ExecutionFailure>,
) -> (ProcessExit, TimeoutOutcome, CancellationOutcome) {
    loop {
        // This ordering is intentional: cancellation wins if both conditions
        // are first observed in the same polling iteration.
        if request.cancellation.is_cancelled() {
            failures.push(ExecutionFailure::Cancelled);
            return (
                terminate_and_reap(child, SupervisorTermination::Cancellation, failures),
                TimeoutOutcome::from_limit(request.resource_limits.timeout, false),
                CancellationOutcome::Selected,
            );
        }

        if request
            .resource_limits
            .timeout
            .is_some_and(|limit| started_at.elapsed() >= limit)
        {
            failures.push(ExecutionFailure::Timeout);
            return (
                terminate_and_reap(child, SupervisorTermination::Timeout, failures),
                TimeoutOutcome::from_limit(request.resource_limits.timeout, true),
                CancellationOutcome::NotSelected,
            );
        }

        match child.try_wait() {
            Ok(Some(status)) => {
                let process_exit = completed_exit(status, failures);
                return (
                    process_exit,
                    TimeoutOutcome::from_limit(request.resource_limits.timeout, false),
                    CancellationOutcome::NotSelected,
                );
            }
            Ok(None) => thread::sleep(next_poll_delay(
                request.resource_limits.timeout,
                started_at.elapsed(),
            )),
            Err(error) => {
                failures.push(ExecutionFailure::WaitFailure {
                    kind: error.kind(),
                    message: error.to_string(),
                });
                return (
                    terminate_and_reap(child, SupervisorTermination::WaitFailure, failures),
                    TimeoutOutcome::from_limit(request.resource_limits.timeout, false),
                    CancellationOutcome::NotSelected,
                );
            }
        }
    }
}

fn next_poll_delay(timeout: Option<Duration>, elapsed: Duration) -> Duration {
    timeout
        .map(|limit| cmp::min(POLL_INTERVAL, limit.saturating_sub(elapsed)))
        .unwrap_or(POLL_INTERVAL)
}

fn completed_exit(status: ExitStatus, failures: &mut Vec<ExecutionFailure>) -> ProcessExit {
    match status.code() {
        Some(0) => ProcessExit::ExitedWithCode(0),
        Some(code) => {
            failures.push(ExecutionFailure::NonZeroExit { code: Some(code) });
            ProcessExit::ExitedWithCode(code)
        }
        None => {
            failures.push(ExecutionFailure::NonZeroExit { code: None });
            ProcessExit::ExitedWithoutCode
        }
    }
}

fn terminate_and_reap(
    child: &mut Child,
    reason: SupervisorTermination,
    failures: &mut Vec<ExecutionFailure>,
) -> ProcessExit {
    if let Err(error) = child.kill() {
        failures.push(ExecutionFailure::TerminationFailure {
            kind: error.kind(),
            message: error.to_string(),
        });
    }

    let code = match child.wait() {
        Ok(status) => status.code(),
        Err(error) => {
            failures.push(ExecutionFailure::WaitFailure {
                kind: error.kind(),
                message: error.to_string(),
            });
            None
        }
    };

    ProcessExit::TerminatedBySupervisor { reason, code }
}

struct CaptureOutcome {
    output: BoundedOutput,
    failure: Option<ExecutionFailure>,
}

fn spawn_reader<R>(
    reader: R,
    stream: OutputStream,
    limit: u64,
) -> io::Result<JoinHandle<CaptureOutcome>>
where
    R: Read + Send + 'static,
{
    let name = match stream {
        OutputStream::Stdout => "worker-stdout-reader",
        OutputStream::Stderr => "worker-stderr-reader",
    };
    thread::Builder::new()
        .name(name.to_owned())
        .spawn(move || capture_output(reader, stream, limit))
}

type ReaderSetup = (Option<JoinHandle<CaptureOutcome>>, Option<ExecutionFailure>);

fn reader_or_failure(
    result: io::Result<JoinHandle<CaptureOutcome>>,
    stream: OutputStream,
) -> ReaderSetup {
    match result {
        Ok(handle) => (Some(handle), None),
        Err(error) => (
            None,
            Some(output_failure(
                stream,
                Some(error.kind()),
                error.to_string(),
            )),
        ),
    }
}

fn capture_output<R: Read>(mut reader: R, stream: OutputStream, limit: u64) -> CaptureOutcome {
    let mut output = BoundedOutput::empty(limit);
    let mut chunk = [0_u8; 8192];

    loop {
        match reader.read(&mut chunk) {
            Ok(0) => break,
            Ok(read) => {
                output.total_bytes_observed = output
                    .total_bytes_observed
                    .saturating_add(u64::try_from(read).unwrap_or(u64::MAX));
                let remaining = limit.saturating_sub(output.captured_bytes.len() as u64);
                let retained = cmp::min(read, usize::try_from(remaining).unwrap_or(usize::MAX));
                output.captured_bytes.extend_from_slice(&chunk[..retained]);
            }
            Err(error) => {
                output.truncated = output.total_bytes_observed > limit;
                return CaptureOutcome {
                    output,
                    failure: Some(output_failure(
                        stream,
                        Some(error.kind()),
                        error.to_string(),
                    )),
                };
            }
        }
    }

    output.truncated = output.total_bytes_observed > limit;
    CaptureOutcome {
        output,
        failure: None,
    }
}

fn finish_reader(
    reader: Option<JoinHandle<CaptureOutcome>>,
    stream: OutputStream,
    limit: u64,
    failures: &mut Vec<ExecutionFailure>,
) -> BoundedOutput {
    let outcome = match reader {
        Some(reader) => match reader.join() {
            Ok(outcome) => outcome,
            Err(_) => CaptureOutcome {
                output: BoundedOutput::empty(limit),
                failure: Some(output_failure(
                    stream,
                    None,
                    "output reader thread panicked".to_owned(),
                )),
            },
        },
        None => CaptureOutcome {
            output: BoundedOutput::empty(limit),
            failure: None,
        },
    };

    failures.extend(outcome.failure);
    outcome.output
}

fn output_failure(
    stream: OutputStream,
    kind: Option<io::ErrorKind>,
    message: String,
) -> ExecutionFailure {
    ExecutionFailure::OutputCaptureFailure {
        stream,
        kind,
        message,
    }
}

#[allow(clippy::too_many_arguments)]
fn finish_result(
    request: &ExecutionRequest,
    process_id: Option<u32>,
    process_exit: ProcessExit,
    timeout: TimeoutOutcome,
    cancellation: CancellationOutcome,
    stdout: BoundedOutput,
    stderr: BoundedOutput,
    duration: Duration,
    failures: Vec<ExecutionFailure>,
) -> ExecutionResult {
    let resource_observations = resource_observations(
        &request.resource_limits,
        &stdout,
        &stderr,
        duration,
        matches!(timeout, TimeoutOutcome::Triggered { .. }),
    );

    ExecutionResult {
        phase: request.phase,
        runtime_metadata: RuntimeMetadata {
            operating_system: std::env::consts::OS,
            architecture: std::env::consts::ARCH,
            process_id,
        },
        process_exit,
        timeout,
        cancellation,
        stdout,
        stderr,
        duration,
        resource_observations,
        failures,
    }
}

fn resource_observations(
    limits: &ResourceLimitRequest,
    stdout: &BoundedOutput,
    stderr: &BoundedOutput,
    duration: Duration,
    timeout_terminated: bool,
) -> Vec<ResourceLimitObservation> {
    let mut observations = Vec::new();

    if let Some(limit) = limits.cpu_time {
        observations.push(not_enforced(
            ResourceLimitKind::CpuTime,
            ResourceLimitValue::Duration(limit),
        ));
    }
    if let Some(limit) = limits.memory_bytes {
        observations.push(not_enforced(
            ResourceLimitKind::MemoryBytes,
            ResourceLimitValue::Bytes(limit),
        ));
    }
    if let Some(limit) = limits.disk_temp_workspace_bytes {
        observations.push(not_enforced(
            ResourceLimitKind::DiskTempWorkspaceBytes,
            ResourceLimitValue::Bytes(limit),
        ));
    }
    if let Some(limit) = limits.process_count {
        observations.push(not_enforced(
            ResourceLimitKind::ProcessCount,
            ResourceLimitValue::Count(u64::from(limit)),
        ));
    }
    if let Some(limit) = limits.file_count {
        observations.push(not_enforced(
            ResourceLimitKind::FileCount,
            ResourceLimitValue::Count(limit),
        ));
    }

    observations.push(capture_observation(
        ResourceLimitKind::StdoutBytes,
        limits.stdout_bytes,
        stdout,
    ));
    observations.push(capture_observation(
        ResourceLimitKind::StderrBytes,
        limits.stderr_bytes,
        stderr,
    ));

    if let Some(limit) = limits.timeout {
        observations.push(ResourceLimitObservation {
            kind: ResourceLimitKind::Timeout,
            configured_limit: ResourceLimitValue::Duration(limit),
            observed_value: Some(ResourceLimitValue::Duration(duration)),
            enforcement_status: ResourceEnforcementStatus::SupervisorTimeoutEnforced,
            terminated_execution: timeout_terminated,
            truncated: None,
        });
    }

    observations.extend(limits.other.iter().map(|limit| ResourceLimitObservation {
        kind: ResourceLimitKind::Other(limit.name.clone()),
        configured_limit: limit.limit.clone(),
        observed_value: None,
        enforcement_status: ResourceEnforcementStatus::NotEnforced,
        terminated_execution: false,
        truncated: None,
    }));
    observations
}

fn not_enforced(
    kind: ResourceLimitKind,
    configured_limit: ResourceLimitValue,
) -> ResourceLimitObservation {
    ResourceLimitObservation {
        kind,
        configured_limit,
        observed_value: None,
        enforcement_status: ResourceEnforcementStatus::NotEnforced,
        terminated_execution: false,
        truncated: None,
    }
}

fn capture_observation(
    kind: ResourceLimitKind,
    configured_limit: u64,
    output: &BoundedOutput,
) -> ResourceLimitObservation {
    ResourceLimitObservation {
        kind,
        configured_limit: ResourceLimitValue::Bytes(configured_limit),
        observed_value: Some(ResourceLimitValue::Bytes(output.total_bytes_observed)),
        enforcement_status: ResourceEnforcementStatus::CaptureBoundEnforced,
        terminated_execution: false,
        truncated: Some(output.truncated),
    }
}
