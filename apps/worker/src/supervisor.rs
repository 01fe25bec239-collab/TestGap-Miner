use crate::{
    execution_authority::{ExecutionAuthority, SpawnDenial},
    resource_limits::{self, CpuTimeDecision},
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

#[cfg(unix)]
use std::os::unix::process::CommandExt;

const POLL_INTERVAL: Duration = Duration::from_millis(5);

/// Zero-sized witness of an explicit, caller-side opt-in to UNRESTRICTED
/// trusted local execution.
///
/// This type exists so that ambient-host behavior — `PATH`-resolved bare
/// executable names, unconfined working directories, and inherited host
/// environments (`EnvironmentPolicy::InheritAndOverride`) — remains
/// available exclusively to genuinely trusted local workloads such as the
/// developer runtime-conformance harness. It can never be constructed from
/// execution request data, repository data, model output, candidate data, or
/// task data: choosing it is a deliberate act by the calling code.
///
/// Untrusted process execution MUST go through
/// [`ProcessSupervisor::restricted`] instead.
#[derive(Debug, Clone, Copy)]
pub struct TrustedLocalExecution {
    _private: (),
}

impl TrustedLocalExecution {
    /// Explicitly opts this caller into unrestricted trusted local
    /// execution. Intended only for local conformance and developer
    /// harnesses running operator-controlled tooling.
    pub fn for_local_conformance_and_developer_harnesses() -> Self {
        Self { _private: () }
    }
}

#[derive(Debug)]
enum SupervisorMode {
    /// The untrusted execution boundary. Every request is validated against
    /// pre-established [`ExecutionAuthority`] (canonical authorized
    /// executable identity, confined workspace root, default-deny child
    /// environment) before any spawn attempt; every violation fails closed
    /// with the target never started.
    Restricted(Box<ExecutionAuthority>),
    /// Deliberately opted-in unrestricted local execution for trusted
    /// callers. Never reachable through request data.
    TrustedLocal(TrustedLocalExecution),
}

/// Deterministic process supervisor.
///
/// Trust class is fixed at construction and can never be upgraded by
/// request content:
///
/// - [`ProcessSupervisor::restricted`] enforces command/executable/path/
///   workspace/environment authority before spawning and is the ONLY
///   appropriate boundary for untrusted repository, model, candidate, or
///   task material.
/// - [`ProcessSupervisor::trusted_local`] preserves the historical
///   unrestricted behavior for explicitly opted-in trusted local callers.
///
/// Supervision itself is unchanged: structured argv with no shell,
/// Unix process groups, cancellation-before-timeout ordering, wall
/// timeouts, process-tree termination with direct-child fallback,
/// concurrent bounded stdout/stderr draining, and child wait/reap.
#[derive(Debug)]
pub struct ProcessSupervisor {
    mode: SupervisorMode,
}

impl ProcessSupervisor {
    /// Creates the restricted (untrusted) execution boundary backed by
    /// pre-established trusted authority.
    ///
    /// The authority must have been built from trusted configuration; its
    /// own construction already failed closed on any canonicalization or
    /// validation problem. Request data cannot widen, replace, or select
    /// around it.
    pub fn restricted(authority: ExecutionAuthority) -> Self {
        Self {
            mode: SupervisorMode::Restricted(Box::new(authority)),
        }
    }

    /// Creates an unrestricted supervisor for explicitly opted-in trusted
    /// local execution only.
    ///
    /// NEVER hand request-derived, repository-derived, model-derived,
    /// candidate-derived, or task-derived command material to this
    /// supervisor: it resolves bare executables through the ambient host
    /// `PATH`, applies working directories verbatim, and honors
    /// `EnvironmentPolicy::InheritAndOverride`, inheriting the full host
    /// environment.
    pub fn trusted_local(witness: TrustedLocalExecution) -> Self {
        Self {
            mode: SupervisorMode::TrustedLocal(witness),
        }
    }

    pub fn execute(&self, request: ExecutionRequest) -> ExecutionResult {
        let started_at = Instant::now();
        match &self.mode {
            SupervisorMode::Restricted(authority) => {
                self.execute_restricted(authority, request, started_at)
            }
            SupervisorMode::TrustedLocal(_) => self.execute_trusted_local(request, started_at),
        }
    }

    /// Restricted boundary: authority checks run entirely before spawn and
    /// deny with `NeverStarted`; the spawned values are the authorized
    /// canonical ones rather than anything from the request.
    fn execute_restricted(
        &self,
        authority: &ExecutionAuthority,
        request: ExecutionRequest,
        started_at: Instant,
    ) -> ExecutionResult {
        // Command/executable/workspace/environment authorization happens
        // first, entirely before any fork: a denied target can never start.
        let prepared = match authority.prepare(
            &request.command.executable,
            &request.command.working_directory,
            &request.command.environment,
        ) {
            Ok(prepared) => prepared,
            Err(SpawnDenial { kind, message }) => {
                return fail_closed_before_spawn(&request, started_at, kind, message)
            }
        };

        // CPU runtime-limit policy is resolved before any fork. A limit that
        // cannot be truthfully enforced on this platform fails closed before
        // spawn so the target can never run unrestricted.
        let cpu_decision = resource_limits::decide(request.resource_limits.cpu_time);
        if let CpuTimeDecision::FailClosedBeforeSpawn(message) = &cpu_decision {
            return fail_closed_before_spawn(
                &request,
                started_at,
                io::ErrorKind::Unsupported,
                message.clone(),
            );
        }

        // Spawn material comes exclusively from validated authority state.
        // Command::new receives the authorized CANONICAL executable, never
        // the requested spelling, so no PATH or lexical-path authority
        // exists at the OS boundary either.
        let mut command = Command::new(&prepared.executable);
        command
            .args(&request.command.arguments)
            .current_dir(&prepared.working_directory)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());

        #[cfg(unix)]
        command.process_group(0);

        // Default-deny child environment: wipe everything, then apply only
        // the explicitly authorized surface. The parent's environment is
        // never inherited on this boundary.
        command.env_clear();
        command.envs(prepared.environment.iter().map(|(key, value)| (key, value)));

        // Attaches the child-local RLIMIT_CPU pre_exec on Linux and reports
        // whether a limit was requested; other platforms already failed
        // closed above.
        let cpu_limit_requested = resource_limits::prepare_command(&mut command, &cpu_decision);

        match command.spawn() {
            Ok(child) => {
                // pre_exec closures complete before exec, so a successfully
                // spawned child is guaranteed to carry its own CPU limits.
                self.supervise_started_process(request, started_at, child, cpu_limit_requested)
            }
            Err(error) => {
                fail_closed_before_spawn(&request, started_at, error.kind(), error.to_string())
            }
        }
    }

    /// Historical unrestricted path, available only behind an explicit
    /// [`TrustedLocalExecution`] opt-in. Behavior is unchanged.
    fn execute_trusted_local(
        &self,
        request: ExecutionRequest,
        started_at: Instant,
    ) -> ExecutionResult {
        // CPU runtime-limit policy is resolved before any fork. A limit that
        // cannot be truthfully enforced on this platform fails closed before
        // spawn so the target can never run unrestricted.
        let cpu_decision = resource_limits::decide(request.resource_limits.cpu_time);
        if let CpuTimeDecision::FailClosedBeforeSpawn(message) = &cpu_decision {
            return fail_closed_before_spawn(
                &request,
                started_at,
                io::ErrorKind::Unsupported,
                message.clone(),
            );
        }

        let mut command = Command::new(&request.command.executable);
        command
            .args(&request.command.arguments)
            .current_dir(&request.command.working_directory)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());

        #[cfg(unix)]
        command.process_group(0);

        match &request.command.environment {
            EnvironmentPolicy::ClearAndSet(values) => {
                command.env_clear();
                command.envs(values.iter().map(|(key, value)| (key, value)));
            }
            EnvironmentPolicy::InheritAndOverride(values) => {
                command.envs(values.iter().map(|(key, value)| (key, value)));
            }
        }

        // Attaches the child-local RLIMIT_CPU pre_exec on Linux and reports
        // whether a limit was requested; other platforms already failed
        // closed above.
        let cpu_limit_requested = resource_limits::prepare_command(&mut command, &cpu_decision);

        match command.spawn() {
            Ok(child) => {
                // pre_exec closures complete before exec, so a successfully
                // spawned child is guaranteed to carry its own CPU limits.
                self.supervise_started_process(request, started_at, child, cpu_limit_requested)
            }
            Err(error) => {
                fail_closed_before_spawn(&request, started_at, error.kind(), error.to_string())
            }
        }
    }

    fn supervise_started_process(
        &self,
        request: ExecutionRequest,
        started_at: Instant,
        mut child: Child,
        cpu_limit_installed: bool,
    ) -> ExecutionResult {
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

        let (process_exit, timeout, cancellation, terminated_by_cpu_limit) = if failures.is_empty()
        {
            supervise_child(
                &mut child,
                &request,
                started_at,
                cpu_limit_installed,
                &mut failures,
            )
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
                false,
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
            if cpu_limit_installed {
                Some(terminated_by_cpu_limit)
            } else {
                None
            },
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

type SupervisedOutcome = (ProcessExit, TimeoutOutcome, CancellationOutcome, bool);

fn supervise_child(
    child: &mut Child,
    request: &ExecutionRequest,
    started_at: Instant,
    cpu_limit_installed: bool,
    failures: &mut Vec<ExecutionFailure>,
) -> SupervisedOutcome {
    loop {
        // This ordering is intentional: cancellation wins if both conditions
        // are first observed in the same polling iteration.
        if request.cancellation.is_cancelled() {
            failures.push(ExecutionFailure::Cancelled);
            return (
                terminate_and_reap(child, SupervisorTermination::Cancellation, failures),
                TimeoutOutcome::from_limit(request.resource_limits.timeout, false),
                CancellationOutcome::Selected,
                false,
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
                false,
            );
        }

        match child.try_wait() {
            Ok(Some(status)) => {
                let process_exit = completed_exit(status, failures);
                return (
                    process_exit,
                    TimeoutOutcome::from_limit(request.resource_limits.timeout, false),
                    CancellationOutcome::NotSelected,
                    resource_limits::terminated_by_installed_cpu_limit(
                        cpu_limit_installed,
                        &status,
                    ),
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
                    false,
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
    if let Err(error) = terminate_process_tree(child) {
        failures.push(ExecutionFailure::TerminationFailure {
            kind: error.kind(),
            message: format!(
                "{} termination failed: {error}",
                if cfg!(unix) {
                    "process-group"
                } else {
                    "direct-child"
                }
            ),
        });

        #[cfg(unix)]
        if let Err(error) = child.kill() {
            failures.push(ExecutionFailure::TerminationFailure {
                kind: error.kind(),
                message: format!("direct-child fallback termination failed: {error}"),
            });
        }
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

#[cfg(unix)]
fn terminate_process_tree(child: &mut Child) -> io::Result<()> {
    const SIGKILL: i32 = 9;

    let process_group = i32::try_from(child.id())
        .ok()
        .filter(|process_group| *process_group > 0)
        .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "invalid child process ID"))?;

    // SAFETY: every Unix child is spawned above with process_group(0), so its
    // positive PID names an isolated group owned by this supervisor. Negating
    // that checked PID targets only that group and can never select group 0.
    let result = unsafe { kill(-process_group, SIGKILL) };
    if result == 0 {
        Ok(())
    } else {
        Err(io::Error::last_os_error())
    }
}

#[cfg(not(unix))]
fn terminate_process_tree(child: &mut Child) -> io::Result<()> {
    child.kill()
}

#[cfg(unix)]
unsafe extern "C" {
    fn kill(pid: i32, signal: i32) -> i32;
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

/// Deterministic pre-spawn failure shape shared by every authorization and
/// setup denial: the target never starts, no process ID exists, and the
/// single failure is a spawn failure.
fn fail_closed_before_spawn(
    request: &ExecutionRequest,
    started_at: Instant,
    kind: io::ErrorKind,
    message: String,
) -> ExecutionResult {
    finish_result(
        request,
        None,
        ProcessExit::NeverStarted,
        TimeoutOutcome::from_limit(request.resource_limits.timeout, false),
        CancellationOutcome::NotSelected,
        BoundedOutput::empty(request.resource_limits.stdout_bytes),
        BoundedOutput::empty(request.resource_limits.stderr_bytes),
        started_at.elapsed(),
        vec![ExecutionFailure::SpawnFailure { kind, message }],
        None,
    )
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
    cpu_limit_enforced: Option<bool>,
) -> ExecutionResult {
    let resource_observations = resource_observations(
        &request.resource_limits,
        &stdout,
        &stderr,
        duration,
        matches!(timeout, TimeoutOutcome::Triggered { .. }),
        cpu_limit_enforced,
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
    cpu_limit_enforced: Option<bool>,
) -> Vec<ResourceLimitObservation> {
    let mut observations = Vec::new();

    if let Some(limit) = limits.cpu_time {
        // `Some(terminated)` is only produced after a child actually started
        // with its own RLIMIT_CPU installed; `None` keeps the conservative
        // NotEnforced claim (including every fail-closed rejection).
        let observation = match cpu_limit_enforced {
            Some(terminated_execution) => ResourceLimitObservation {
                kind: ResourceLimitKind::CpuTime,
                configured_limit: ResourceLimitValue::Duration(limit),
                observed_value: None,
                enforcement_status: ResourceEnforcementStatus::RuntimeLimitEnforced,
                terminated_execution,
                truncated: None,
            },
            None => not_enforced(
                ResourceLimitKind::CpuTime,
                ResourceLimitValue::Duration(limit),
            ),
        };
        observations.push(observation);
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
