mod defects4j;
mod java;
mod junit;

pub use defects4j::*;
pub use java::*;
pub use junit::*;

use crate::{
    CancellationOutcome, CancellationToken, EnvironmentPolicy, ExecutionCommand, ExecutionFailure,
    ExecutionPhase, ExecutionRequest, ExecutionResult, ProcessExit, ResourceLimitRequest,
    TimeoutOutcome,
};
use std::env;
use std::ffi::{OsStr, OsString};
use std::fmt;
use std::io;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone)]
pub struct AdapterExecutionOptions {
    pub working_directory: PathBuf,
    pub environment: EnvironmentPolicy,
    pub resource_limits: ResourceLimitRequest,
    pub cancellation: CancellationToken,
}

impl AdapterExecutionOptions {
    pub fn new(working_directory: impl Into<PathBuf>) -> Self {
        Self {
            working_directory: working_directory.into(),
            environment: EnvironmentPolicy::ClearAndSet(Vec::new()),
            resource_limits: ResourceLimitRequest::default(),
            cancellation: CancellationToken::new(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ExecutionAdapterError {
    InvalidExecutable,
    EmptySourceSet,
    EmptyTestTargetSet,
    ClasspathConstructionFailed,
    InvalidJavaClassName(String),
    InvalidDefects4JProject(String),
    InvalidDefects4JTestIdentifier(String),
    InvalidExecutionPhase(ExecutionPhase),
    InvalidRequest(&'static str),
}

impl fmt::Display for ExecutionAdapterError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidExecutable => formatter.write_str("executable must not be empty"),
            Self::EmptySourceSet => {
                formatter.write_str("at least one Java source file is required")
            }
            Self::EmptyTestTargetSet => {
                formatter.write_str("at least one JUnit test target is required")
            }
            Self::ClasspathConstructionFailed => {
                formatter.write_str("classpath could not be joined for this platform")
            }
            Self::InvalidJavaClassName(value) => {
                write!(formatter, "invalid Java class name: {value}")
            }
            Self::InvalidDefects4JProject(value) => {
                write!(formatter, "invalid Defects4J project identifier: {value}")
            }
            Self::InvalidDefects4JTestIdentifier(value) => {
                write!(formatter, "invalid Defects4J test identifier: {value}")
            }
            Self::InvalidExecutionPhase(phase) => {
                write!(formatter, "invalid execution phase: {phase:?}")
            }
            Self::InvalidRequest(message) => formatter.write_str(message),
        }
    }
}

impl std::error::Error for ExecutionAdapterError {}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct JavaClassName(String);

impl JavaClassName {
    pub fn new(value: impl Into<String>) -> Result<Self, ExecutionAdapterError> {
        let value = value.into();
        if is_java_qualified_name(&value) {
            Ok(Self(value))
        } else {
            Err(ExecutionAdapterError::InvalidJavaClassName(value))
        }
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

fn is_java_qualified_name(value: &str) -> bool {
    !value.is_empty() && value.split('.').all(is_java_identifier)
}

fn is_java_identifier(value: &str) -> bool {
    let mut characters = value.bytes();
    matches!(
        characters.next(),
        Some(b'a'..=b'z' | b'A'..=b'Z' | b'_' | b'$')
    ) && characters.all(|character| character.is_ascii_alphanumeric() || b"_$".contains(&character))
}

fn validate_executable(executable: &OsStr) -> Result<(), ExecutionAdapterError> {
    if executable.is_empty() {
        Err(ExecutionAdapterError::InvalidExecutable)
    } else {
        Ok(())
    }
}

fn validate_options(options: &AdapterExecutionOptions) -> Result<(), ExecutionAdapterError> {
    if options.working_directory.as_os_str().is_empty() {
        Err(ExecutionAdapterError::InvalidRequest(
            "working directory must not be empty",
        ))
    } else {
        Ok(())
    }
}

fn joined_classpath(paths: &[PathBuf]) -> Result<Option<OsString>, ExecutionAdapterError> {
    if paths.is_empty() {
        Ok(None)
    } else {
        env::join_paths(paths.iter().map(|path| java_tool_path(path)))
            .map(Some)
            .map_err(|_| ExecutionAdapterError::ClasspathConstructionFailed)
    }
}

fn java_tool_path(path: &Path) -> PathBuf {
    if !path.is_absolute()
        && matches!(
            path.as_os_str().as_encoded_bytes().first().copied(),
            Some(b'@' | b'-')
        )
    {
        PathBuf::from(".").join(path)
    } else {
        path.to_owned()
    }
}

fn execution_request(
    phase: ExecutionPhase,
    executable: &OsStr,
    arguments: Vec<OsString>,
    options: &AdapterExecutionOptions,
) -> ExecutionRequest {
    let command = ExecutionCommand {
        executable: executable.to_owned(),
        arguments,
        working_directory: options.working_directory.clone(),
        environment: options.environment.clone(),
    };
    ExecutionRequest {
        phase,
        command,
        resource_limits: options.resource_limits.clone(),
        cancellation: options.cancellation.clone(),
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum RawOutcome {
    Succeeded,
    Failed,
    ToolUnavailable,
    TimedOut,
    Cancelled,
    RunnerError,
}

fn classify(execution: &ExecutionResult) -> RawOutcome {
    if execution.cancellation == CancellationOutcome::Selected {
        return RawOutcome::Cancelled;
    }
    if matches!(execution.timeout, TimeoutOutcome::Triggered { .. }) {
        return RawOutcome::TimedOut;
    }
    if execution.failures.iter().any(|failure| {
        matches!(
            failure,
            ExecutionFailure::SpawnFailure {
                kind: io::ErrorKind::NotFound,
                ..
            }
        )
    }) {
        return RawOutcome::ToolUnavailable;
    }
    if execution.failures.iter().any(|failure| {
        !matches!(
            failure,
            ExecutionFailure::NonZeroExit { .. }
                | ExecutionFailure::Timeout
                | ExecutionFailure::Cancelled
        )
    }) {
        return RawOutcome::RunnerError;
    }
    match execution.process_exit {
        ProcessExit::ExitedWithCode(0) => RawOutcome::Succeeded,
        ProcessExit::ExitedWithCode(_) | ProcessExit::ExitedWithoutCode => RawOutcome::Failed,
        ProcessExit::NeverStarted | ProcessExit::TerminatedBySupervisor { .. } => {
            RawOutcome::RunnerError
        }
    }
}
