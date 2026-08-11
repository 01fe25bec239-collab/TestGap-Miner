use super::{
    classify, execution_request, is_java_identifier, is_java_qualified_name, validate_executable,
    validate_options, AdapterExecutionOptions, ExecutionAdapterError, RawOutcome,
};
use crate::{ExecutionCommand, ExecutionPhase, ExecutionResult, ProcessSupervisor};
use std::ffi::OsString;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Defects4JProjectId(String);

impl Defects4JProjectId {
    pub fn new(value: impl Into<String>) -> Result<Self, ExecutionAdapterError> {
        let value = value.into();
        let mut characters = value.bytes();
        let valid = characters
            .next()
            .is_some_and(|first| first.is_ascii_alphabetic())
            && characters.all(|character| {
                character.is_ascii_alphanumeric() || character == b'_' || character == b'-'
            });
        if valid {
            Ok(Self(value))
        } else {
            Err(ExecutionAdapterError::InvalidDefects4JProject(value))
        }
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Defects4JTestIdentifier(String);

impl Defects4JTestIdentifier {
    pub fn new(value: impl Into<String>) -> Result<Self, ExecutionAdapterError> {
        let value = value.into();
        let valid = value.split_once("::").is_some_and(|(class, method)| {
            !method.contains("::") && is_java_qualified_name(class) && is_java_identifier(method)
        });
        if valid {
            Ok(Self(value))
        } else {
            Err(ExecutionAdapterError::InvalidDefects4JTestIdentifier(value))
        }
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Defects4JCommand {
    Compile,
    Test {
        test: Option<Defects4JTestIdentifier>,
    },
}

#[derive(Debug, Clone)]
pub struct Defects4JRequest {
    pub executable: OsString,
    pub command: Defects4JCommand,
    pub execution_options: AdapterExecutionOptions,
    pub phase: ExecutionPhase,
}

impl Defects4JRequest {
    pub fn command(&self) -> Result<ExecutionCommand, ExecutionAdapterError> {
        validate_executable(&self.executable)?;
        validate_options(&self.execution_options)?;
        validate_phase(&self.command, self.phase)?;

        let arguments = match &self.command {
            Defects4JCommand::Compile => vec![OsString::from("compile")],
            Defects4JCommand::Test { test: None } => vec![OsString::from("test")],
            Defects4JCommand::Test { test: Some(test) } => vec![
                OsString::from("test"),
                OsString::from("-t"),
                OsString::from(test.as_str()),
            ],
        };

        Ok(execution_request(
            self.phase,
            &self.executable,
            arguments,
            &self.execution_options,
        )
        .command)
    }

    pub fn execute(
        &self,
        supervisor: &ProcessSupervisor,
    ) -> Result<Defects4JResult, ExecutionAdapterError> {
        let command = self.command()?;
        let execution = supervisor.execute(execution_request(
            self.phase,
            &command.executable,
            command.arguments,
            &self.execution_options,
        ));
        let failing_test_count = if matches!(self.command, Defects4JCommand::Test { .. }) {
            parse_defects4j_failing_test_count(&execution.stdout.captured_bytes)
                .or_else(|| parse_defects4j_failing_test_count(&execution.stderr.captured_bytes))
        } else {
            None
        };
        Ok(Defects4JResult {
            outcome: Defects4JOutcome::from(classify(&execution)),
            failing_test_count,
            execution,
        })
    }
}

fn validate_phase(
    command: &Defects4JCommand,
    phase: ExecutionPhase,
) -> Result<(), ExecutionAdapterError> {
    match (command, phase) {
        (Defects4JCommand::Compile, ExecutionPhase::Compile)
        | (
            Defects4JCommand::Test { .. },
            ExecutionPhase::BuggyExecution | ExecutionPhase::FixedExecution,
        ) => Ok(()),
        _ => Err(ExecutionAdapterError::InvalidExecutionPhase(phase)),
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Defects4JOutcome {
    Succeeded,
    Failed,
    ToolUnavailable,
    TimedOut,
    Cancelled,
    RunnerError,
}

impl From<RawOutcome> for Defects4JOutcome {
    fn from(value: RawOutcome) -> Self {
        match value {
            RawOutcome::Succeeded => Self::Succeeded,
            RawOutcome::Failed => Self::Failed,
            RawOutcome::ToolUnavailable => Self::ToolUnavailable,
            RawOutcome::TimedOut => Self::TimedOut,
            RawOutcome::Cancelled => Self::Cancelled,
            RawOutcome::RunnerError => Self::RunnerError,
        }
    }
}

#[derive(Debug)]
pub struct Defects4JResult {
    pub outcome: Defects4JOutcome,
    pub failing_test_count: Option<u64>,
    pub execution: ExecutionResult,
}

pub fn parse_defects4j_failing_test_count(output: &[u8]) -> Option<u64> {
    String::from_utf8_lossy(output).lines().find_map(|line| {
        line.trim()
            .strip_prefix("Failing tests:")
            .and_then(|count| count.trim().parse().ok())
    })
}
