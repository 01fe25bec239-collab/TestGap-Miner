use super::{
    classify, execution_request, joined_classpath, validate_executable, validate_options,
    AdapterExecutionOptions, ExecutionAdapterError, JavaClassName, RawOutcome,
};
use crate::{ExecutionCommand, ExecutionPhase, ExecutionResult, ProcessSupervisor};
use std::ffi::OsString;
use std::path::PathBuf;

#[derive(Debug, Clone)]
pub struct JUnitRequest {
    pub java_executable: OsString,
    pub classpath_entries: Vec<PathBuf>,
    pub runner_main_class: JavaClassName,
    pub test_targets: Vec<JavaClassName>,
    pub execution_options: AdapterExecutionOptions,
    pub phase: ExecutionPhase,
}

impl JUnitRequest {
    pub fn command(&self) -> Result<ExecutionCommand, ExecutionAdapterError> {
        validate_executable(&self.java_executable)?;
        validate_options(&self.execution_options)?;
        validate_test_phase(self.phase)?;
        if self.test_targets.is_empty() {
            return Err(ExecutionAdapterError::EmptyTestTargetSet);
        }

        let mut arguments = Vec::new();
        if let Some(classpath) = joined_classpath(&self.classpath_entries)? {
            arguments.push(OsString::from("-classpath"));
            arguments.push(classpath);
        }
        arguments.push(OsString::from(self.runner_main_class.as_str()));
        arguments.extend(
            self.test_targets
                .iter()
                .map(|target| OsString::from(target.as_str())),
        );

        Ok(execution_request(
            self.phase,
            &self.java_executable,
            arguments,
            &self.execution_options,
        )
        .command)
    }

    pub fn execute(
        &self,
        supervisor: &ProcessSupervisor,
    ) -> Result<JUnitResult, ExecutionAdapterError> {
        let command = self.command()?;
        let execution = supervisor.execute(execution_request(
            self.phase,
            &command.executable,
            command.arguments,
            &self.execution_options,
        ));
        let summary = parse_junit_summary(&execution.stdout.captured_bytes)
            .or_else(|| parse_junit_summary(&execution.stderr.captured_bytes));
        Ok(JUnitResult {
            outcome: TestOutcome::from(classify(&execution)),
            summary,
            execution,
        })
    }
}

fn validate_test_phase(phase: ExecutionPhase) -> Result<(), ExecutionAdapterError> {
    match phase {
        ExecutionPhase::BuggyExecution | ExecutionPhase::FixedExecution => Ok(()),
        ExecutionPhase::Compile => Err(ExecutionAdapterError::InvalidExecutionPhase(phase)),
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TestOutcome {
    Passed,
    Failed,
    ToolUnavailable,
    TimedOut,
    Cancelled,
    RunnerError,
}

impl From<RawOutcome> for TestOutcome {
    fn from(value: RawOutcome) -> Self {
        match value {
            RawOutcome::Succeeded => Self::Passed,
            RawOutcome::Failed => Self::Failed,
            RawOutcome::ToolUnavailable => Self::ToolUnavailable,
            RawOutcome::TimedOut => Self::TimedOut,
            RawOutcome::Cancelled => Self::Cancelled,
            RawOutcome::RunnerError => Self::RunnerError,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct TestRunSummary {
    pub tests_run: u64,
    pub failures: u64,
}

#[derive(Debug)]
pub struct JUnitResult {
    pub outcome: TestOutcome,
    pub summary: Option<TestRunSummary>,
    pub execution: ExecutionResult,
}

pub fn parse_junit_summary(output: &[u8]) -> Option<TestRunSummary> {
    String::from_utf8_lossy(output)
        .lines()
        .find_map(parse_junit_summary_line)
}

fn parse_junit_summary_line(line: &str) -> Option<TestRunSummary> {
    let line = line.trim();
    if let Some(body) = line
        .strip_prefix("OK (")
        .and_then(|body| body.strip_suffix(')'))
    {
        let (count, noun) = body.split_once(' ')?;
        let tests_run = count.parse().ok()?;
        if (tests_run == 1 && noun == "test") || (tests_run != 1 && noun == "tests") {
            return Some(TestRunSummary {
                tests_run,
                failures: 0,
            });
        }
        return None;
    }

    let (tests, failures) = line.split_once(',')?;
    let tests_run = tests
        .trim()
        .strip_prefix("Tests run:")?
        .trim()
        .parse()
        .ok()?;
    let failures = failures
        .trim()
        .strip_prefix("Failures:")?
        .trim()
        .parse()
        .ok()?;
    Some(TestRunSummary {
        tests_run,
        failures,
    })
}
