use std::ffi::OsString;
use std::io;
use std::path::PathBuf;
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc,
};
use std::time::Duration;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ExecutionPhase {
    Compile,
    BuggyExecution,
    FixedExecution,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum EnvironmentPolicy {
    ClearAndSet(Vec<(OsString, OsString)>),
    InheritAndOverride(Vec<(OsString, OsString)>),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ExecutionCommand {
    pub executable: OsString,
    pub arguments: Vec<OsString>,
    pub working_directory: PathBuf,
    pub environment: EnvironmentPolicy,
}

impl ExecutionCommand {
    pub fn new(executable: impl Into<OsString>, working_directory: impl Into<PathBuf>) -> Self {
        Self {
            executable: executable.into(),
            arguments: Vec::new(),
            working_directory: working_directory.into(),
            environment: EnvironmentPolicy::ClearAndSet(Vec::new()),
        }
    }
}

#[derive(Debug, Clone, Default)]
pub struct CancellationToken(Arc<AtomicBool>);

impl CancellationToken {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn cancel(&self) {
        self.0.store(true, Ordering::Release);
    }

    pub fn is_cancelled(&self) -> bool {
        self.0.load(Ordering::Acquire)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OtherResourceLimitRequest {
    pub name: String,
    pub limit: ResourceLimitValue,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ResourceLimitRequest {
    pub cpu_time: Option<Duration>,
    pub memory_bytes: Option<u64>,
    pub disk_temp_workspace_bytes: Option<u64>,
    pub process_count: Option<u32>,
    pub file_count: Option<u64>,
    pub stdout_bytes: u64,
    pub stderr_bytes: u64,
    pub timeout: Option<Duration>,
    pub other: Vec<OtherResourceLimitRequest>,
}

impl Default for ResourceLimitRequest {
    fn default() -> Self {
        Self {
            cpu_time: None,
            memory_bytes: None,
            disk_temp_workspace_bytes: None,
            process_count: None,
            file_count: None,
            stdout_bytes: 1024 * 1024,
            stderr_bytes: 1024 * 1024,
            timeout: None,
            other: Vec::new(),
        }
    }
}

#[derive(Debug, Clone)]
pub struct ExecutionRequest {
    pub phase: ExecutionPhase,
    pub command: ExecutionCommand,
    pub resource_limits: ResourceLimitRequest,
    pub cancellation: CancellationToken,
}

impl ExecutionRequest {
    pub fn new(phase: ExecutionPhase, command: ExecutionCommand) -> Self {
        Self {
            phase,
            command,
            resource_limits: ResourceLimitRequest::default(),
            cancellation: CancellationToken::new(),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SupervisorTermination {
    Timeout,
    Cancellation,
    WaitFailure,
    OutputCaptureFailure,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ProcessExit {
    NeverStarted,
    ExitedWithCode(i32),
    ExitedWithoutCode,
    TerminatedBySupervisor {
        reason: SupervisorTermination,
        code: Option<i32>,
    },
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TimeoutOutcome {
    NotConfigured,
    NotTriggered { limit: Duration },
    Triggered { limit: Duration },
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CancellationOutcome {
    NotSelected,
    Selected,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OutputStream {
    Stdout,
    Stderr,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BoundedOutput {
    pub captured_bytes: Vec<u8>,
    pub total_bytes_observed: u64,
    pub capture_limit_bytes: u64,
    pub truncated: bool,
}

impl BoundedOutput {
    pub fn empty(capture_limit_bytes: u64) -> Self {
        Self {
            captured_bytes: Vec::new(),
            total_bytes_observed: 0,
            capture_limit_bytes,
            truncated: false,
        }
    }

    pub fn to_string_lossy(&self) -> String {
        String::from_utf8_lossy(&self.captured_bytes).into_owned()
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ExecutionFailure {
    SpawnFailure {
        kind: io::ErrorKind,
        message: String,
    },
    NonZeroExit {
        code: Option<i32>,
    },
    Timeout,
    Cancelled,
    WaitFailure {
        kind: io::ErrorKind,
        message: String,
    },
    OutputCaptureFailure {
        stream: OutputStream,
        kind: Option<io::ErrorKind>,
        message: String,
    },
    TerminationFailure {
        kind: io::ErrorKind,
        message: String,
    },
}

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub enum ResourceLimitKind {
    CpuTime,
    MemoryBytes,
    DiskTempWorkspaceBytes,
    ProcessCount,
    FileCount,
    StdoutBytes,
    StderrBytes,
    Timeout,
    Other(String),
}

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub enum ResourceLimitValue {
    Duration(Duration),
    Bytes(u64),
    Count(u64),
    Custom { value: u64, unit: String },
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum ResourceEnforcementStatus {
    NotEnforced,
    CaptureBoundEnforced,
    SupervisorTimeoutEnforced,
    RuntimeLimitEnforced,
}

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct ResourceLimitObservation {
    pub kind: ResourceLimitKind,
    pub configured_limit: ResourceLimitValue,
    pub observed_value: Option<ResourceLimitValue>,
    pub enforcement_status: ResourceEnforcementStatus,
    pub terminated_execution: bool,
    pub truncated: Option<bool>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct RuntimeMetadata {
    pub operating_system: &'static str,
    pub architecture: &'static str,
    pub process_id: Option<u32>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ExecutionResult {
    pub phase: ExecutionPhase,
    pub runtime_metadata: RuntimeMetadata,
    pub process_exit: ProcessExit,
    pub timeout: TimeoutOutcome,
    pub cancellation: CancellationOutcome,
    pub stdout: BoundedOutput,
    pub stderr: BoundedOutput,
    pub duration: Duration,
    pub resource_observations: Vec<ResourceLimitObservation>,
    /// Ordered runtime failures. The first item is the deterministic primary
    /// classification; later items preserve cleanup/capture failures.
    pub failures: Vec<ExecutionFailure>,
}

impl ExecutionResult {
    pub fn primary_failure(&self) -> Option<&ExecutionFailure> {
        self.failures.first()
    }

    pub fn is_success(&self) -> bool {
        self.failures.is_empty() && self.process_exit == ProcessExit::ExitedWithCode(0)
    }
}
