use super::{
    classify, execution_request, java_tool_path, joined_classpath, validate_executable,
    validate_options, AdapterExecutionOptions, ExecutionAdapterError, RawOutcome,
};
use crate::{ExecutionCommand, ExecutionPhase, ExecutionResult, ProcessSupervisor};
use std::ffi::OsString;
use std::path::PathBuf;

#[derive(Debug, Clone)]
pub struct JavaCompileRequest {
    pub javac_executable: OsString,
    pub source_files: Vec<PathBuf>,
    pub classpath_entries: Vec<PathBuf>,
    pub output_directory: Option<PathBuf>,
    pub execution_options: AdapterExecutionOptions,
}

impl JavaCompileRequest {
    pub fn command(&self) -> Result<ExecutionCommand, ExecutionAdapterError> {
        validate_executable(&self.javac_executable)?;
        validate_options(&self.execution_options)?;
        if self.source_files.is_empty() {
            return Err(ExecutionAdapterError::EmptySourceSet);
        }

        let mut arguments = Vec::new();
        if let Some(directory) = &self.output_directory {
            arguments.push(OsString::from("-d"));
            arguments.push(java_tool_path(directory).into_os_string());
        }
        if let Some(classpath) = joined_classpath(&self.classpath_entries)? {
            arguments.push(OsString::from("-classpath"));
            arguments.push(classpath);
        }
        arguments.extend(
            self.source_files
                .iter()
                .map(|path| java_tool_path(path).into_os_string()),
        );

        Ok(execution_request(
            ExecutionPhase::Compile,
            &self.javac_executable,
            arguments,
            &self.execution_options,
        )
        .command)
    }

    pub fn execute(
        &self,
        supervisor: &ProcessSupervisor,
    ) -> Result<JavaCompileResult, ExecutionAdapterError> {
        let command = self.command()?;
        let execution = supervisor.execute(execution_request(
            ExecutionPhase::Compile,
            &command.executable,
            command.arguments,
            &self.execution_options,
        ));
        Ok(JavaCompileResult {
            outcome: CompileOutcome::from(classify(&execution)),
            execution,
        })
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CompileOutcome {
    Success,
    CompilationFailed,
    ToolUnavailable,
    TimedOut,
    Cancelled,
    RunnerError,
}

impl From<RawOutcome> for CompileOutcome {
    fn from(value: RawOutcome) -> Self {
        match value {
            RawOutcome::Succeeded => Self::Success,
            RawOutcome::Failed => Self::CompilationFailed,
            RawOutcome::ToolUnavailable => Self::ToolUnavailable,
            RawOutcome::TimedOut => Self::TimedOut,
            RawOutcome::Cancelled => Self::Cancelled,
            RawOutcome::RunnerError => Self::RunnerError,
        }
    }
}

#[derive(Debug)]
pub struct JavaCompileResult {
    pub outcome: CompileOutcome,
    pub execution: ExecutionResult,
}
