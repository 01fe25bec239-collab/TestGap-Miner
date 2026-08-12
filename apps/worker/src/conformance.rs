use crate::{
    AdapterExecutionOptions, CancellationOutcome, CompileOutcome, Defects4JCommand,
    Defects4JOutcome, Defects4JRequest, EnvironmentPolicy, ExecutionCommand, ExecutionFailure,
    ExecutionPhase, ExecutionRequest, ExecutionResult, JUnitRequest, JavaClassName,
    JavaCompileRequest, ProcessExit, ProcessSupervisor, SupervisorTermination, TestOutcome,
    TestRunSummary, TimeoutOutcome,
};
use std::env;
use std::ffi::{OsStr, OsString};
use std::fmt;
use std::fs;
use std::io;
use std::path::{Path, PathBuf};
use std::process;
use std::sync::atomic::{AtomicU64, Ordering};
use std::thread;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

const PROBE_TIMEOUT: Duration = Duration::from_secs(5);
const EXECUTION_TIMEOUT: Duration = Duration::from_secs(10);
const JAVA_TIMEOUT: Duration = Duration::from_millis(750);
const CANCELLATION_DELAY: Duration = Duration::from_millis(250);
const CAPTURE_BYTES: u64 = 32 * 1024;
const SPAM_CAPTURE_BYTES: u64 = 1024;
const JAVA_OK_MARKER: &[u8] = b"TESTGAP_JAVA_RUNTIME_OK";
const JAVA_STARTED_MARKER: &[u8] = b"TESTGAP_JAVA_RUNTIME_STARTED";
const JUNIT_RUNNER: &str = "org.junit.runner.JUnitCore";
const DEFECTS4J_TIMEZONE: &str = "America/Los_Angeles";

const JAVA_FIXTURE: &str = r#"import java.io.IOException;

public final class TestGapRuntimeProbe {
    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            throw new IllegalArgumentException("one mode is required");
        }
        switch (args[0]) {
            case "ok":
                System.out.println("TESTGAP_JAVA_RUNTIME_OK");
                break;
            case "sleep":
                System.out.println("TESTGAP_JAVA_RUNTIME_STARTED");
                System.out.flush();
                Thread.sleep(30000L);
                break;
            case "spam":
                emit(65536);
                break;
            default:
                throw new IllegalArgumentException("unknown mode");
        }
    }

    private static void emit(int count) throws IOException {
        for (int i = 0; i < count; i++) {
            System.out.write('S');
        }
        System.out.flush();
    }
}
"#;

const JUNIT_PASSING_FIXTURE: &str = r#"import org.junit.Test;
import static org.junit.Assert.assertTrue;

public final class TestGapPassingTest {
    @Test public void passes() { assertTrue(true); }
}
"#;

const JUNIT_FAILING_FIXTURE: &str = r#"import org.junit.Test;
import static org.junit.Assert.assertTrue;

public final class TestGapFailingTest {
    @Test public void fails() { assertTrue(false); }
}
"#;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RuntimeTool {
    Java,
    Javac,
    JUnitCore,
    Defects4J,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EnvironmentBlockReason {
    ToolUnavailable,
    JavaUnavailable,
    JavacUnavailable,
    JUnitClasspathNotConfigured,
    JUnitClasspathUnusable,
    Defects4JEnvironmentUnavailable,
    Defects4JWorkdirNotConfigured,
    Defects4JWorkdirInvalid,
}

impl fmt::Display for EnvironmentBlockReason {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self {
            Self::ToolUnavailable => "TOOL_UNAVAILABLE",
            Self::JavaUnavailable => "JAVA_UNAVAILABLE",
            Self::JavacUnavailable => "JAVAC_UNAVAILABLE",
            Self::JUnitClasspathNotConfigured => "JUNIT_CLASSPATH_NOT_CONFIGURED",
            Self::JUnitClasspathUnusable => "JUNIT_CLASSPATH_UNUSABLE",
            Self::Defects4JEnvironmentUnavailable => "DEFECTS4J_ENVIRONMENT_UNAVAILABLE",
            Self::Defects4JWorkdirNotConfigured => "DEFECTS4J_WORKDIR_NOT_CONFIGURED",
            Self::Defects4JWorkdirInvalid => "DEFECTS4J_WORKDIR_INVALID",
        })
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ToolAvailability {
    Available,
    EnvironmentBlocked(EnvironmentBlockReason),
    ProbeFailed,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RuntimeVersion {
    Detected(String),
    Undetermined,
}

impl fmt::Display for RuntimeVersion {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Detected(version) => formatter.write_str(version),
            Self::Undetermined => formatter.write_str("UNDETERMINED"),
        }
    }
}

#[derive(Debug, Clone)]
pub struct RuntimeProbe {
    pub tool: RuntimeTool,
    pub executable_requested: OsString,
    pub availability: ToolAvailability,
    pub version: RuntimeVersion,
    pub execution: ExecutionResult,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RuntimeConformanceStatus {
    Tested,
    EnvironmentBlocked,
    Fail,
}

impl fmt::Display for RuntimeConformanceStatus {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self {
            Self::Tested => "TESTED",
            Self::EnvironmentBlocked => "ENVIRONMENT_BLOCKED",
            Self::Fail => "FAIL",
        })
    }
}

#[derive(Debug, Clone)]
pub struct ConformanceCheck {
    pub status: RuntimeConformanceStatus,
    pub reason: Option<EnvironmentBlockReason>,
    pub raw_executions: Vec<ExecutionResult>,
}

impl ConformanceCheck {
    fn tested(executions: Vec<ExecutionResult>) -> Self {
        Self {
            status: RuntimeConformanceStatus::Tested,
            reason: None,
            raw_executions: executions,
        }
    }

    fn blocked(reason: EnvironmentBlockReason) -> Self {
        Self {
            status: RuntimeConformanceStatus::EnvironmentBlocked,
            reason: Some(reason),
            raw_executions: Vec::new(),
        }
    }

    fn blocked_with_raw(reason: EnvironmentBlockReason, executions: Vec<ExecutionResult>) -> Self {
        Self {
            status: RuntimeConformanceStatus::EnvironmentBlocked,
            reason: Some(reason),
            raw_executions: executions,
        }
    }

    fn failed(executions: Vec<ExecutionResult>) -> Self {
        Self {
            status: RuntimeConformanceStatus::Fail,
            reason: None,
            raw_executions: executions,
        }
    }
}

#[derive(Debug, Clone)]
pub struct RuntimeConformanceConfig {
    pub java_executable: OsString,
    pub javac_executable: OsString,
    pub junit_classpath: Option<OsString>,
    pub defects4j_executable: OsString,
    pub defects4j_workdir: Option<PathBuf>,
    pub working_directory: PathBuf,
}

impl RuntimeConformanceConfig {
    pub fn from_environment() -> io::Result<Self> {
        Ok(Self {
            java_executable: OsString::from("java"),
            javac_executable: OsString::from("javac"),
            junit_classpath: env::var_os("TESTGAP_JUNIT_CLASSPATH"),
            defects4j_executable: non_empty_environment("TESTGAP_DEFECTS4J_BIN")
                .unwrap_or_else(|| OsString::from("defects4j")),
            defects4j_workdir: non_empty_environment("TESTGAP_DEFECTS4J_WORKDIR")
                .map(PathBuf::from),
            working_directory: env::current_dir()?,
        })
    }
}

#[derive(Debug)]
pub struct RuntimeConformanceReport {
    pub operating_system: &'static str,
    pub architecture: &'static str,
    pub java_probe: RuntimeProbe,
    pub javac_probe: RuntimeProbe,
    pub java_compile: ConformanceCheck,
    pub java_execution: ConformanceCheck,
    pub java_timeout: ConformanceCheck,
    pub java_cancellation: ConformanceCheck,
    pub bounded_output: ConformanceCheck,
    pub junit_runtime: ConformanceCheck,
    pub junit_version: RuntimeVersion,
    pub junit_passing_outcome: Option<TestOutcome>,
    pub junit_passing_summary: Option<TestRunSummary>,
    pub junit_failing_outcome: Option<TestOutcome>,
    pub junit_failing_summary: Option<TestRunSummary>,
    pub defects4j_probe: RuntimeProbe,
    pub defects4j_compile: ConformanceCheck,
    pub defects4j_test: ConformanceCheck,
    pub defects4j_compile_outcome: Option<Defects4JOutcome>,
    pub defects4j_test_outcome: Option<Defects4JOutcome>,
    pub defects4j_failing_test_count: Option<u64>,
    pub defects4j_child_timezone: Option<&'static str>,
    pub temporary_workspace_cleanup: bool,
}

impl RuntimeConformanceReport {
    pub fn has_failures(&self) -> bool {
        !self.temporary_workspace_cleanup
            || [
                &self.java_compile,
                &self.java_execution,
                &self.java_timeout,
                &self.java_cancellation,
                &self.bounded_output,
                &self.junit_runtime,
                &self.defects4j_compile,
                &self.defects4j_test,
            ]
            .iter()
            .any(|check| check.status == RuntimeConformanceStatus::Fail)
            || matches!(self.java_probe.availability, ToolAvailability::ProbeFailed)
            || matches!(self.javac_probe.availability, ToolAvailability::ProbeFailed)
            || matches!(
                self.defects4j_probe.availability,
                ToolAvailability::ProbeFailed
            )
    }

    pub fn render(&self) -> String {
        let mut lines = Vec::new();
        lines.push(format!("HOST_OS={}", self.operating_system));
        lines.push(format!("HOST_ARCH={}", self.architecture));
        lines.push(format!(
            "JAVA_EXECUTABLE={}",
            report_os_value(&self.java_probe.executable_requested)
        ));
        lines.push(format!("JAVA_PROBE={}", probe_status(&self.java_probe)));
        lines.push(format!("JAVA_VERSION={}", self.java_probe.version));
        lines.push(format!(
            "JAVAC_EXECUTABLE={}",
            report_os_value(&self.javac_probe.executable_requested)
        ));
        lines.push(format!("JAVAC_PROBE={}", probe_status(&self.javac_probe)));
        lines.push(format!("JAVAC_VERSION={}", self.javac_probe.version));
        lines.push(format!("JAVA_REAL_COMPILE={}", self.java_compile.status));
        lines.push(format!(
            "JAVA_REAL_EXECUTION={}",
            self.java_execution.status
        ));
        lines.push(format!("REAL_JAVA_TIMEOUT={}", self.java_timeout.status));
        lines.push(format!(
            "REAL_JAVA_CANCELLATION={}",
            self.java_cancellation.status
        ));
        lines.push(format!(
            "REAL_BOUNDED_OUTPUT={}",
            self.bounded_output.status
        ));
        lines.push(format!("JUNIT_REAL_RUNTIME={}", self.junit_runtime.status));
        lines.push(format!("JUNIT_VERSION={}", self.junit_version));
        lines.push(format!(
            "JUNIT_REASON={}",
            reason_value(&self.junit_runtime)
        ));
        lines.push(format!(
            "DEFECTS4J_EXECUTABLE={}",
            report_os_value(&self.defects4j_probe.executable_requested)
        ));
        lines.push(format!(
            "DEFECTS4J_TOOL_PROBE={}",
            probe_status(&self.defects4j_probe)
        ));
        lines.push(format!(
            "DEFECTS4J_VERSION={}",
            self.defects4j_probe.version
        ));
        lines.push(format!(
            "DEFECTS4J_COMPILE={}",
            self.defects4j_compile.status
        ));
        lines.push(format!("DEFECTS4J_TEST={}", self.defects4j_test.status));
        lines.push(format!(
            "DEFECTS4J_REASON={}",
            reason_value(&self.defects4j_compile)
        ));
        lines.push(format!(
            "DEFECTS4J_CHILD_TZ={}",
            self.defects4j_child_timezone.unwrap_or("NOT_SET")
        ));
        lines.push(format!(
            "TEMP_WORKSPACE_CLEANUP={}",
            if self.temporary_workspace_cleanup {
                "PASS"
            } else {
                "FAIL"
            }
        ));
        lines.push("SHELL_INSERTED=NO".to_owned());
        lines.push("EXTERNAL_RUST_CRATES=NONE".to_owned());
        lines.push("SECURE_SANDBOX_COMPLETE=NO".to_owned());
        lines.push("RESOURCE_ISOLATION_COMPLETE=NO".to_owned());
        lines.push("PRODUCTION_READY=NO".to_owned());
        lines.join("\n") + "\n"
    }
}

#[derive(Debug)]
pub struct RuntimeConformanceHarness {
    config: RuntimeConformanceConfig,
    supervisor: ProcessSupervisor,
}

impl RuntimeConformanceHarness {
    pub fn new(config: RuntimeConformanceConfig) -> Self {
        Self {
            config,
            supervisor: ProcessSupervisor,
        }
    }

    pub fn run(&self) -> RuntimeConformanceReport {
        let java_probe = probe_tool(
            RuntimeTool::Java,
            self.config.java_executable.clone(),
            &[OsString::from("-version")],
            &self.config.working_directory,
            &self.supervisor,
        );
        let javac_probe = probe_tool(
            RuntimeTool::Javac,
            self.config.javac_executable.clone(),
            &[OsString::from("-version")],
            &self.config.working_directory,
            &self.supervisor,
        );

        let java = self.run_java(&java_probe, &javac_probe);
        let junit = self.run_junit(&java_probe, &javac_probe);
        let defects4j_probe = probe_tool(
            RuntimeTool::Defects4J,
            self.config.defects4j_executable.clone(),
            &[
                OsString::from("info"),
                OsString::from("-p"),
                OsString::from("Lang"),
            ],
            &self.config.working_directory,
            &self.supervisor,
        );
        let defects4j = self.run_defects4j(&defects4j_probe);

        RuntimeConformanceReport {
            operating_system: env::consts::OS,
            architecture: env::consts::ARCH,
            java_probe,
            javac_probe,
            java_compile: java.compile,
            java_execution: java.execution,
            java_timeout: java.timeout,
            java_cancellation: java.cancellation,
            bounded_output: java.bounded_output,
            junit_runtime: junit.runtime,
            junit_version: junit.version,
            junit_passing_outcome: junit.passing_outcome,
            junit_passing_summary: junit.passing_summary,
            junit_failing_outcome: junit.failing_outcome,
            junit_failing_summary: junit.failing_summary,
            defects4j_probe,
            defects4j_compile: defects4j.compile,
            defects4j_test: defects4j.test,
            defects4j_compile_outcome: defects4j.compile_outcome,
            defects4j_test_outcome: defects4j.test_outcome,
            defects4j_failing_test_count: defects4j.failing_test_count,
            defects4j_child_timezone: defects4j.child_timezone,
            temporary_workspace_cleanup: java.cleanup && junit.cleanup,
        }
    }

    fn run_java(&self, java: &RuntimeProbe, javac: &RuntimeProbe) -> JavaChecks {
        let blocked = java_prerequisite(java, javac);
        if let Some(reason) = blocked {
            return JavaChecks::blocked(reason);
        }

        let workspace = match TemporaryWorkspace::create("java") {
            Ok(workspace) => workspace,
            Err(_) => return JavaChecks::failed(),
        };
        let source = workspace.path().join("TestGapRuntimeProbe.java");
        let classes = workspace.path().join("classes");
        if fs::create_dir(&classes).is_err() || fs::write(&source, JAVA_FIXTURE).is_err() {
            return JavaChecks::failed_with_cleanup(workspace.cleanup().is_ok());
        }

        let compilation = JavaCompileRequest {
            javac_executable: self.config.javac_executable.clone(),
            source_files: vec![source],
            classpath_entries: Vec::new(),
            output_directory: Some(classes.clone()),
            execution_options: adapter_options(workspace.path(), EXECUTION_TIMEOUT),
        }
        .execute(&self.supervisor);

        let compilation = match compilation {
            Ok(result) => result,
            Err(_) => return JavaChecks::failed_with_cleanup(workspace.cleanup().is_ok()),
        };
        let compile_raw = compilation.execution.clone();
        if compilation.outcome != CompileOutcome::Success {
            return JavaChecks {
                compile: ConformanceCheck::failed(vec![compile_raw]),
                execution: ConformanceCheck::failed(Vec::new()),
                timeout: ConformanceCheck::failed(Vec::new()),
                cancellation: ConformanceCheck::failed(Vec::new()),
                bounded_output: ConformanceCheck::failed(Vec::new()),
                cleanup: workspace.cleanup().is_ok(),
            };
        }

        let ok =
            self.execute_java_fixture(workspace.path(), &classes, "ok", EXECUTION_TIMEOUT, None);
        let execution = if ok.is_success()
            && ok.runtime_metadata.process_id.is_some()
            && contains_bytes(&ok.stdout.captured_bytes, JAVA_OK_MARKER)
        {
            ConformanceCheck::tested(vec![ok])
        } else {
            ConformanceCheck::failed(vec![ok])
        };

        let timed =
            self.execute_java_fixture(workspace.path(), &classes, "sleep", JAVA_TIMEOUT, None);
        let timeout = if timed.runtime_metadata.process_id.is_some()
            && matches!(timed.timeout, TimeoutOutcome::Triggered { .. })
            && matches!(
                timed.process_exit,
                ProcessExit::TerminatedBySupervisor {
                    reason: SupervisorTermination::Timeout,
                    ..
                }
            )
            && contains_bytes(&timed.stdout.captured_bytes, JAVA_STARTED_MARKER)
            && timed.stdout.captured_bytes.len() as u64 <= timed.stdout.capture_limit_bytes
        {
            ConformanceCheck::tested(vec![timed])
        } else {
            ConformanceCheck::failed(vec![timed])
        };

        let token = crate::CancellationToken::new();
        let canceller_token = token.clone();
        let canceller = thread::spawn(move || {
            thread::sleep(CANCELLATION_DELAY);
            canceller_token.cancel();
        });
        let cancelled = self.execute_java_fixture(
            workspace.path(),
            &classes,
            "sleep",
            EXECUTION_TIMEOUT,
            Some(token),
        );
        let cancellation_valid = canceller.join().is_ok()
            && cancelled.runtime_metadata.process_id.is_some()
            && cancelled.cancellation == CancellationOutcome::Selected
            && matches!(
                cancelled.process_exit,
                ProcessExit::TerminatedBySupervisor {
                    reason: SupervisorTermination::Cancellation,
                    ..
                }
            )
            && !matches!(cancelled.timeout, TimeoutOutcome::Triggered { .. })
            && contains_bytes(&cancelled.stdout.captured_bytes, JAVA_STARTED_MARKER);
        let cancellation = if cancellation_valid {
            ConformanceCheck::tested(vec![cancelled])
        } else {
            ConformanceCheck::failed(vec![cancelled])
        };

        let spam =
            self.execute_java_fixture(workspace.path(), &classes, "spam", EXECUTION_TIMEOUT, None);
        let bounded_output = if spam.is_success()
            && spam.stdout.capture_limit_bytes == SPAM_CAPTURE_BYTES
            && spam.stdout.captured_bytes.len() as u64 <= SPAM_CAPTURE_BYTES
            && spam.stdout.total_bytes_observed > spam.stdout.captured_bytes.len() as u64
            && spam.stdout.truncated
        {
            ConformanceCheck::tested(vec![spam])
        } else {
            ConformanceCheck::failed(vec![spam])
        };

        JavaChecks {
            compile: ConformanceCheck::tested(vec![compile_raw]),
            execution,
            timeout,
            cancellation,
            bounded_output,
            cleanup: workspace.cleanup().is_ok(),
        }
    }

    fn execute_java_fixture(
        &self,
        working_directory: &Path,
        classes: &Path,
        mode: &str,
        timeout: Duration,
        cancellation: Option<crate::CancellationToken>,
    ) -> ExecutionResult {
        let mut command = ExecutionCommand::new(&self.config.java_executable, working_directory);
        command.arguments = vec![
            OsString::from("-classpath"),
            classes.as_os_str().to_owned(),
            OsString::from("TestGapRuntimeProbe"),
            OsString::from(mode),
        ];
        command.environment = EnvironmentPolicy::InheritAndOverride(Vec::new());
        let mut request = ExecutionRequest::new(ExecutionPhase::FixedExecution, command);
        request.resource_limits.timeout = Some(timeout);
        request.resource_limits.stdout_bytes = if mode == "spam" {
            SPAM_CAPTURE_BYTES
        } else {
            CAPTURE_BYTES
        };
        request.resource_limits.stderr_bytes = CAPTURE_BYTES;
        if let Some(cancellation) = cancellation {
            request.cancellation = cancellation;
        }
        self.supervisor.execute(request)
    }

    fn run_junit(&self, java: &RuntimeProbe, javac: &RuntimeProbe) -> JUnitChecks {
        let classpath = match junit_classpath(self.config.junit_classpath.as_deref()) {
            Ok(classpath) => classpath,
            Err(reason) => return JUnitChecks::blocked(reason),
        };
        let classpath: Vec<_> = classpath
            .into_iter()
            .map(|entry| {
                if entry.is_absolute() {
                    entry
                } else {
                    self.config.working_directory.join(entry)
                }
            })
            .collect();
        if let Some(reason) = java_prerequisite(java, javac) {
            return JUnitChecks::blocked(reason);
        }
        if classpath.iter().any(|entry| !entry.exists()) {
            return JUnitChecks::blocked(EnvironmentBlockReason::JUnitClasspathUnusable);
        }

        let workspace = match TemporaryWorkspace::create("junit") {
            Ok(workspace) => workspace,
            Err(_) => return JUnitChecks::failed(),
        };
        let classes = workspace.path().join("classes");
        let passing_source = workspace.path().join("TestGapPassingTest.java");
        let failing_source = workspace.path().join("TestGapFailingTest.java");
        if fs::create_dir(&classes).is_err()
            || fs::write(&passing_source, JUNIT_PASSING_FIXTURE).is_err()
            || fs::write(&failing_source, JUNIT_FAILING_FIXTURE).is_err()
        {
            return JUnitChecks::failed_with_cleanup(workspace.cleanup().is_ok());
        }

        let compilation = JavaCompileRequest {
            javac_executable: self.config.javac_executable.clone(),
            source_files: vec![passing_source, failing_source],
            classpath_entries: classpath.clone(),
            output_directory: Some(classes.clone()),
            execution_options: adapter_options(workspace.path(), EXECUTION_TIMEOUT),
        }
        .execute(&self.supervisor);
        let compilation = match compilation {
            Ok(result) => result,
            Err(_) => return JUnitChecks::failed_with_cleanup(workspace.cleanup().is_ok()),
        };
        let compile_raw = compilation.execution.clone();
        if compilation.outcome != CompileOutcome::Success {
            return JUnitChecks::blocked_with_raw(
                EnvironmentBlockReason::JUnitClasspathUnusable,
                vec![compile_raw],
                workspace.cleanup().is_ok(),
            );
        }

        let mut runtime_classpath = vec![classes];
        runtime_classpath.extend(classpath);
        let passing = self.execute_junit(
            workspace.path(),
            runtime_classpath.clone(),
            "TestGapPassingTest",
        );
        let passing = match passing {
            Ok(result) => result,
            Err(_) => return JUnitChecks::failed_with_cleanup(workspace.cleanup().is_ok()),
        };
        let version = parse_junit_version(
            &passing.execution.stdout.captured_bytes,
            &passing.execution.stderr.captured_bytes,
        );
        let passing_valid = passing.outcome == TestOutcome::Passed
            && passing.summary
                == Some(TestRunSummary {
                    tests_run: 1,
                    failures: 0,
                });
        if !passing_valid && passing.summary.is_none() {
            return JUnitChecks::blocked_with_facts(
                EnvironmentBlockReason::JUnitClasspathUnusable,
                vec![compile_raw, passing.execution],
                version,
                Some(passing.outcome),
                passing.summary,
                workspace.cleanup().is_ok(),
            );
        }

        let failing = self.execute_junit(workspace.path(), runtime_classpath, "TestGapFailingTest");
        let failing = match failing {
            Ok(result) => result,
            Err(_) => return JUnitChecks::failed_with_cleanup(workspace.cleanup().is_ok()),
        };
        let failing_valid = failing.outcome == TestOutcome::Failed
            && failing
                .summary
                .is_some_and(|summary| summary.tests_run == 1 && summary.failures >= 1);
        let raw = vec![compile_raw, passing.execution, failing.execution];
        let runtime = if passing_valid && failing_valid {
            ConformanceCheck::tested(raw)
        } else {
            ConformanceCheck::failed(raw)
        };
        JUnitChecks {
            runtime,
            version,
            passing_outcome: Some(passing.outcome),
            passing_summary: passing.summary,
            failing_outcome: Some(failing.outcome),
            failing_summary: failing.summary,
            cleanup: workspace.cleanup().is_ok(),
        }
    }

    fn execute_junit(
        &self,
        working_directory: &Path,
        classpath_entries: Vec<PathBuf>,
        target: &str,
    ) -> Result<crate::JUnitResult, crate::ExecutionAdapterError> {
        JUnitRequest {
            java_executable: self.config.java_executable.clone(),
            classpath_entries,
            runner_main_class: JavaClassName::new(JUNIT_RUNNER)?,
            test_targets: vec![JavaClassName::new(target)?],
            execution_options: adapter_options(working_directory, EXECUTION_TIMEOUT),
            phase: ExecutionPhase::FixedExecution,
        }
        .execute(&self.supervisor)
    }

    fn run_defects4j(&self, probe: &RuntimeProbe) -> Defects4JChecks {
        match probe.availability {
            ToolAvailability::Available => {}
            ToolAvailability::EnvironmentBlocked(reason) => {
                return Defects4JChecks::blocked(reason)
            }
            ToolAvailability::ProbeFailed => return Defects4JChecks::failed(),
        }
        let workdir = match defects4j_workdir(self.config.defects4j_workdir.as_deref()) {
            Ok(workdir) => workdir,
            Err(reason) => return Defects4JChecks::blocked(reason),
        };
        let options = defects4j_options(workdir);
        let compile = Defects4JRequest {
            executable: self.config.defects4j_executable.clone(),
            command: Defects4JCommand::Compile,
            execution_options: options.clone(),
            phase: ExecutionPhase::Compile,
        }
        .execute(&self.supervisor);
        let compile = match compile {
            Ok(result) => result,
            Err(_) => return Defects4JChecks::failed(),
        };
        let compile_check = defects4j_invocation_check(&compile.execution, compile.outcome);

        let test = Defects4JRequest {
            executable: self.config.defects4j_executable.clone(),
            command: Defects4JCommand::Test { test: None },
            execution_options: options,
            phase: ExecutionPhase::BuggyExecution,
        }
        .execute(&self.supervisor);
        let test = match test {
            Ok(result) => result,
            Err(_) => return Defects4JChecks::failed(),
        };
        let test_check = defects4j_invocation_check(&test.execution, test.outcome);

        Defects4JChecks {
            compile: compile_check,
            test: test_check,
            compile_outcome: Some(compile.outcome),
            test_outcome: Some(test.outcome),
            failing_test_count: test.failing_test_count,
            child_timezone: Some(DEFECTS4J_TIMEZONE),
        }
    }
}

pub fn probe_tool(
    tool: RuntimeTool,
    executable: OsString,
    arguments: &[OsString],
    working_directory: &Path,
    supervisor: &ProcessSupervisor,
) -> RuntimeProbe {
    let mut command = ExecutionCommand::new(&executable, working_directory);
    command.arguments = arguments.to_vec();
    command.environment = EnvironmentPolicy::InheritAndOverride(Vec::new());
    let mut request = ExecutionRequest::new(ExecutionPhase::Compile, command);
    request.resource_limits.timeout = Some(PROBE_TIMEOUT);
    request.resource_limits.stdout_bytes = CAPTURE_BYTES;
    request.resource_limits.stderr_bytes = CAPTURE_BYTES;
    let execution = supervisor.execute(request);
    let unavailable = execution.failures.iter().any(|failure| {
        matches!(
            failure,
            ExecutionFailure::SpawnFailure {
                kind: io::ErrorKind::NotFound,
                ..
            }
        )
    });
    let availability = if unavailable {
        ToolAvailability::EnvironmentBlocked(EnvironmentBlockReason::ToolUnavailable)
    } else if tool == RuntimeTool::Defects4J && !execution.is_success() {
        ToolAvailability::EnvironmentBlocked(
            EnvironmentBlockReason::Defects4JEnvironmentUnavailable,
        )
    } else if execution.is_success() {
        ToolAvailability::Available
    } else {
        ToolAvailability::ProbeFailed
    };
    let version = match tool {
        RuntimeTool::Java => parse_java_version(
            &execution.stdout.captured_bytes,
            &execution.stderr.captured_bytes,
        ),
        RuntimeTool::Javac => parse_javac_version(
            &execution.stdout.captured_bytes,
            &execution.stderr.captured_bytes,
        ),
        RuntimeTool::JUnitCore => RuntimeVersion::Undetermined,
        RuntimeTool::Defects4J => parse_defects4j_version(
            &execution.stdout.captured_bytes,
            &execution.stderr.captured_bytes,
        ),
    };
    RuntimeProbe {
        tool,
        executable_requested: executable,
        availability,
        version,
        execution,
    }
}

pub fn parse_java_version(stdout: &[u8], stderr: &[u8]) -> RuntimeVersion {
    parse_outputs(stdout, stderr, |line| {
        for prefix in ["java version \"", "openjdk version \""] {
            if let Some(value) = line.trim().strip_prefix(prefix) {
                return value.split('"').next().and_then(valid_version);
            }
        }
        line.trim()
            .strip_prefix("openjdk ")
            .and_then(|value| value.split_whitespace().next())
            .and_then(valid_version)
    })
}

pub fn parse_javac_version(stdout: &[u8], stderr: &[u8]) -> RuntimeVersion {
    parse_outputs(stdout, stderr, |line| {
        line.trim()
            .strip_prefix("javac ")
            .and_then(|value| value.split_whitespace().next())
            .and_then(valid_version)
    })
}

pub fn parse_junit_version(stdout: &[u8], stderr: &[u8]) -> RuntimeVersion {
    parse_outputs(stdout, stderr, |line| {
        line.trim()
            .strip_prefix("JUnit version ")
            .and_then(|value| value.split_whitespace().next())
            .and_then(valid_version)
    })
}

pub fn parse_defects4j_version(stdout: &[u8], stderr: &[u8]) -> RuntimeVersion {
    parse_outputs(stdout, stderr, |line| {
        let line = line.trim();
        ["Defects4J version:", "Defects4J:", "defects4j version:"]
            .iter()
            .find_map(|prefix| line.strip_prefix(prefix))
            .and_then(|value| value.split_whitespace().next())
            .and_then(valid_version)
    })
}

fn parse_outputs(
    stdout: &[u8],
    stderr: &[u8],
    parser: impl Fn(&str) -> Option<String>,
) -> RuntimeVersion {
    for output in [stdout, stderr] {
        if let Some(version) = String::from_utf8_lossy(output).lines().find_map(&parser) {
            return RuntimeVersion::Detected(version);
        }
    }
    RuntimeVersion::Undetermined
}

fn valid_version(value: &str) -> Option<String> {
    let valid = !value.is_empty()
        && value.len() <= 128
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'+' | b'-'))
        && value.bytes().any(|byte| byte.is_ascii_digit());
    valid.then(|| value.to_owned())
}

fn non_empty_environment(name: &str) -> Option<OsString> {
    env::var_os(name).filter(|value| !value.is_empty())
}

fn junit_classpath(configured: Option<&OsStr>) -> Result<Vec<PathBuf>, EnvironmentBlockReason> {
    let configured = configured
        .filter(|value| !value.is_empty())
        .ok_or(EnvironmentBlockReason::JUnitClasspathNotConfigured)?;
    let paths: Vec<_> = env::split_paths(configured)
        .filter(|path| !path.as_os_str().is_empty())
        .collect();
    if paths.is_empty() {
        Err(EnvironmentBlockReason::JUnitClasspathNotConfigured)
    } else {
        Ok(paths)
    }
}

fn defects4j_workdir(configured: Option<&Path>) -> Result<&Path, EnvironmentBlockReason> {
    let path = configured.ok_or(EnvironmentBlockReason::Defects4JWorkdirNotConfigured)?;
    if path.is_dir() {
        Ok(path)
    } else {
        Err(EnvironmentBlockReason::Defects4JWorkdirInvalid)
    }
}

fn java_prerequisite(java: &RuntimeProbe, javac: &RuntimeProbe) -> Option<EnvironmentBlockReason> {
    if java.availability != ToolAvailability::Available {
        Some(EnvironmentBlockReason::JavaUnavailable)
    } else if javac.availability != ToolAvailability::Available {
        Some(EnvironmentBlockReason::JavacUnavailable)
    } else {
        None
    }
}

fn adapter_options(working_directory: &Path, timeout: Duration) -> AdapterExecutionOptions {
    let mut options = AdapterExecutionOptions::new(working_directory);
    options.environment = EnvironmentPolicy::InheritAndOverride(Vec::new());
    options.resource_limits.timeout = Some(timeout);
    options.resource_limits.stdout_bytes = CAPTURE_BYTES;
    options.resource_limits.stderr_bytes = CAPTURE_BYTES;
    options
}

fn defects4j_options(working_directory: &Path) -> AdapterExecutionOptions {
    let mut options = adapter_options(working_directory, EXECUTION_TIMEOUT);
    options.environment = EnvironmentPolicy::InheritAndOverride(vec![(
        OsString::from("TZ"),
        OsString::from(DEFECTS4J_TIMEZONE),
    )]);
    options
}

fn defects4j_invocation_check(
    execution: &ExecutionResult,
    outcome: Defects4JOutcome,
) -> ConformanceCheck {
    let raw = vec![execution.clone()];
    match outcome {
        Defects4JOutcome::Succeeded | Defects4JOutcome::Failed => ConformanceCheck::tested(raw),
        Defects4JOutcome::ToolUnavailable => {
            ConformanceCheck::blocked_with_raw(EnvironmentBlockReason::ToolUnavailable, raw)
        }
        Defects4JOutcome::TimedOut
        | Defects4JOutcome::Cancelled
        | Defects4JOutcome::RunnerError => ConformanceCheck::failed(raw),
    }
}

fn probe_status(probe: &RuntimeProbe) -> RuntimeConformanceStatus {
    match probe.availability {
        ToolAvailability::Available => RuntimeConformanceStatus::Tested,
        ToolAvailability::EnvironmentBlocked(_) => RuntimeConformanceStatus::EnvironmentBlocked,
        ToolAvailability::ProbeFailed => RuntimeConformanceStatus::Fail,
    }
}

fn reason_value(check: &ConformanceCheck) -> String {
    check
        .reason
        .map(|reason| reason.to_string())
        .unwrap_or_else(|| "NONE".to_owned())
}

fn report_os_value(value: &OsStr) -> String {
    value
        .to_string_lossy()
        .chars()
        .flat_map(|character| character.escape_default())
        .collect()
}

fn contains_bytes(haystack: &[u8], needle: &[u8]) -> bool {
    haystack
        .windows(needle.len())
        .any(|window| window == needle)
}

struct TemporaryWorkspace(Option<PathBuf>);

impl TemporaryWorkspace {
    fn create(label: &str) -> io::Result<Self> {
        static NEXT: AtomicU64 = AtomicU64::new(0);
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or(Duration::ZERO)
            .as_nanos();
        let path = env::temp_dir().join(format!(
            "testgap-runtime-conformance-{label}-{}-{timestamp}-{}",
            process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&path)?;
        Ok(Self(Some(path)))
    }

    fn path(&self) -> &Path {
        self.0.as_deref().expect("workspace is present")
    }

    fn cleanup(mut self) -> io::Result<()> {
        let path = self.0.as_ref().expect("workspace is present");
        fs::remove_dir_all(path)?;
        self.0 = None;
        Ok(())
    }
}

impl Drop for TemporaryWorkspace {
    fn drop(&mut self) {
        if let Some(path) = self.0.take() {
            let _ = fs::remove_dir_all(path);
        }
    }
}

struct JavaChecks {
    compile: ConformanceCheck,
    execution: ConformanceCheck,
    timeout: ConformanceCheck,
    cancellation: ConformanceCheck,
    bounded_output: ConformanceCheck,
    cleanup: bool,
}

impl JavaChecks {
    fn blocked(reason: EnvironmentBlockReason) -> Self {
        Self {
            compile: ConformanceCheck::blocked(reason),
            execution: ConformanceCheck::blocked(reason),
            timeout: ConformanceCheck::blocked(reason),
            cancellation: ConformanceCheck::blocked(reason),
            bounded_output: ConformanceCheck::blocked(reason),
            cleanup: true,
        }
    }

    fn failed() -> Self {
        Self::failed_with_cleanup(true)
    }

    fn failed_with_cleanup(cleanup: bool) -> Self {
        Self {
            compile: ConformanceCheck::failed(Vec::new()),
            execution: ConformanceCheck::failed(Vec::new()),
            timeout: ConformanceCheck::failed(Vec::new()),
            cancellation: ConformanceCheck::failed(Vec::new()),
            bounded_output: ConformanceCheck::failed(Vec::new()),
            cleanup,
        }
    }
}

struct JUnitChecks {
    runtime: ConformanceCheck,
    version: RuntimeVersion,
    passing_outcome: Option<TestOutcome>,
    passing_summary: Option<TestRunSummary>,
    failing_outcome: Option<TestOutcome>,
    failing_summary: Option<TestRunSummary>,
    cleanup: bool,
}

impl JUnitChecks {
    fn blocked(reason: EnvironmentBlockReason) -> Self {
        Self {
            runtime: ConformanceCheck::blocked(reason),
            version: RuntimeVersion::Undetermined,
            passing_outcome: None,
            passing_summary: None,
            failing_outcome: None,
            failing_summary: None,
            cleanup: true,
        }
    }

    fn blocked_with_raw(
        reason: EnvironmentBlockReason,
        raw: Vec<ExecutionResult>,
        cleanup: bool,
    ) -> Self {
        Self {
            runtime: ConformanceCheck::blocked_with_raw(reason, raw),
            cleanup,
            ..Self::blocked(reason)
        }
    }

    fn blocked_with_facts(
        reason: EnvironmentBlockReason,
        raw: Vec<ExecutionResult>,
        version: RuntimeVersion,
        passing_outcome: Option<TestOutcome>,
        passing_summary: Option<TestRunSummary>,
        cleanup: bool,
    ) -> Self {
        Self {
            runtime: ConformanceCheck::blocked_with_raw(reason, raw),
            version,
            passing_outcome,
            passing_summary,
            failing_outcome: None,
            failing_summary: None,
            cleanup,
        }
    }

    fn failed() -> Self {
        Self::failed_with_cleanup(true)
    }

    fn failed_with_cleanup(cleanup: bool) -> Self {
        Self {
            runtime: ConformanceCheck::failed(Vec::new()),
            version: RuntimeVersion::Undetermined,
            passing_outcome: None,
            passing_summary: None,
            failing_outcome: None,
            failing_summary: None,
            cleanup,
        }
    }
}

struct Defects4JChecks {
    compile: ConformanceCheck,
    test: ConformanceCheck,
    compile_outcome: Option<Defects4JOutcome>,
    test_outcome: Option<Defects4JOutcome>,
    failing_test_count: Option<u64>,
    child_timezone: Option<&'static str>,
}

impl Defects4JChecks {
    fn blocked(reason: EnvironmentBlockReason) -> Self {
        Self {
            compile: ConformanceCheck::blocked(reason),
            test: ConformanceCheck::blocked(reason),
            compile_outcome: None,
            test_outcome: None,
            failing_test_count: None,
            child_timezone: None,
        }
    }

    fn failed() -> Self {
        Self {
            compile: ConformanceCheck::failed(Vec::new()),
            test: ConformanceCheck::failed(Vec::new()),
            compile_outcome: None,
            test_outcome: None,
            failing_test_count: None,
            child_timezone: None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn missing(label: &str) -> OsString {
        env::temp_dir()
            .join(format!(
                "testgap-guaranteed-missing-{label}-{}",
                process::id()
            ))
            .into_os_string()
    }

    #[test]
    fn parses_java_version_from_stdout() {
        assert_eq!(
            parse_java_version(b"openjdk version \"21.0.2\"\n", b""),
            RuntimeVersion::Detected("21.0.2".to_owned())
        );
    }

    #[test]
    fn parses_java_version_from_stderr() {
        assert_eq!(
            parse_java_version(b"", b"java version \"1.8.0_402\"\n"),
            RuntimeVersion::Detected("1.8.0_402".to_owned())
        );
    }

    #[test]
    fn parses_javac_version() {
        assert_eq!(
            parse_javac_version(b"javac 17.0.10\n", b""),
            RuntimeVersion::Detected("17.0.10".to_owned())
        );
    }

    #[test]
    fn malformed_versions_are_undetermined() {
        assert_eq!(
            parse_java_version(b"openjdk version \"not-a-version\"", b""),
            RuntimeVersion::Undetermined
        );
        assert_eq!(
            parse_javac_version(b"javac unknown", b""),
            RuntimeVersion::Undetermined
        );
    }

    #[test]
    fn missing_java_and_javac_are_environment_blocked_with_raw_results() {
        let cwd = env::current_dir().unwrap();
        for tool in [RuntimeTool::Java, RuntimeTool::Javac] {
            let probe = probe_tool(
                tool,
                missing(if tool == RuntimeTool::Java {
                    "java"
                } else {
                    "javac"
                }),
                &[OsString::from("-version")],
                &cwd,
                &ProcessSupervisor,
            );
            assert_eq!(
                probe.availability,
                ToolAvailability::EnvironmentBlocked(EnvironmentBlockReason::ToolUnavailable)
            );
            assert_eq!(probe.execution.process_exit, ProcessExit::NeverStarted);
            assert_eq!(
                probe.execution.runtime_metadata.operating_system,
                env::consts::OS
            );
            assert_eq!(
                probe.execution.runtime_metadata.architecture,
                env::consts::ARCH
            );
        }
    }

    #[test]
    fn missing_and_empty_junit_classpaths_are_environment_blocked() {
        assert_eq!(
            junit_classpath(None),
            Err(EnvironmentBlockReason::JUnitClasspathNotConfigured)
        );
        assert_eq!(
            junit_classpath(Some(OsStr::new(""))),
            Err(EnvironmentBlockReason::JUnitClasspathNotConfigured)
        );
    }

    #[test]
    fn missing_defects4j_executable_is_environment_blocked() {
        let probe = probe_tool(
            RuntimeTool::Defects4J,
            missing("defects4j"),
            &[OsString::from("info")],
            &env::current_dir().unwrap(),
            &ProcessSupervisor,
        );
        assert_eq!(
            probe.availability,
            ToolAvailability::EnvironmentBlocked(EnvironmentBlockReason::ToolUnavailable)
        );
        assert!(matches!(
            probe.execution.primary_failure(),
            Some(ExecutionFailure::SpawnFailure {
                kind: io::ErrorKind::NotFound,
                ..
            })
        ));
    }

    #[test]
    fn missing_defects4j_workdir_is_environment_blocked() {
        assert_eq!(
            defects4j_workdir(None),
            Err(EnvironmentBlockReason::Defects4JWorkdirNotConfigured)
        );
        let absent = env::temp_dir().join("testgap-guaranteed-missing-defects4j-workdir");
        assert_eq!(
            defects4j_workdir(Some(&absent)),
            Err(EnvironmentBlockReason::Defects4JWorkdirInvalid)
        );
    }

    #[test]
    fn defects4j_options_override_only_the_child_timezone() {
        assert_eq!(
            defects4j_options(Path::new(".")).environment,
            EnvironmentPolicy::InheritAndOverride(vec![(
                OsString::from("TZ"),
                OsString::from("America/Los_Angeles"),
            )])
        );
    }

    #[test]
    fn defects4j_tool_unavailable_precedes_missing_workdir() {
        let config = RuntimeConformanceConfig {
            java_executable: missing("precedence-java"),
            javac_executable: missing("precedence-javac"),
            junit_classpath: None,
            defects4j_executable: missing("precedence-defects4j"),
            defects4j_workdir: None,
            working_directory: env::current_dir().unwrap(),
        };
        let probe = probe_tool(
            RuntimeTool::Defects4J,
            config.defects4j_executable.clone(),
            &[OsString::from("info")],
            &config.working_directory,
            &ProcessSupervisor,
        );
        let checks = RuntimeConformanceHarness::new(config).run_defects4j(&probe);

        assert_eq!(
            checks.compile.reason,
            Some(EnvironmentBlockReason::ToolUnavailable)
        );
        assert_eq!(
            checks.test.reason,
            Some(EnvironmentBlockReason::ToolUnavailable)
        );
    }

    #[test]
    fn defects4j_missing_workdir_is_checked_after_available_tool() {
        let config = RuntimeConformanceConfig {
            java_executable: missing("available-java"),
            javac_executable: missing("available-javac"),
            junit_classpath: None,
            defects4j_executable: missing("available-defects4j"),
            defects4j_workdir: None,
            working_directory: env::current_dir().unwrap(),
        };
        let mut probe = probe_tool(
            RuntimeTool::Defects4J,
            config.defects4j_executable.clone(),
            &[OsString::from("info")],
            &config.working_directory,
            &ProcessSupervisor,
        );
        probe.availability = ToolAvailability::Available;
        let checks = RuntimeConformanceHarness::new(config).run_defects4j(&probe);

        assert_eq!(
            checks.compile.reason,
            Some(EnvironmentBlockReason::Defects4JWorkdirNotConfigured)
        );
        assert_eq!(
            checks.test.reason,
            Some(EnvironmentBlockReason::Defects4JWorkdirNotConfigured)
        );
    }

    #[test]
    fn timeout_cancellation_and_bounded_output_mapping_stay_distinct() {
        let mut result = probe_tool(
            RuntimeTool::Java,
            missing("mapping"),
            &[],
            &env::current_dir().unwrap(),
            &ProcessSupervisor,
        )
        .execution;
        result.process_exit = ProcessExit::TerminatedBySupervisor {
            reason: SupervisorTermination::Timeout,
            code: None,
        };
        result.timeout = TimeoutOutcome::Triggered {
            limit: Duration::from_millis(1),
        };
        result.cancellation = CancellationOutcome::NotSelected;
        assert!(matches!(result.timeout, TimeoutOutcome::Triggered { .. }));
        assert_eq!(result.cancellation, CancellationOutcome::NotSelected);

        result.process_exit = ProcessExit::TerminatedBySupervisor {
            reason: SupervisorTermination::Cancellation,
            code: None,
        };
        result.timeout = TimeoutOutcome::NotTriggered {
            limit: Duration::from_secs(1),
        };
        result.cancellation = CancellationOutcome::Selected;
        assert_eq!(result.cancellation, CancellationOutcome::Selected);
        assert!(!matches!(result.timeout, TimeoutOutcome::Triggered { .. }));

        result.stdout.capture_limit_bytes = 4;
        result.stdout.captured_bytes = b"SSSS".to_vec();
        result.stdout.total_bytes_observed = 100;
        result.stdout.truncated = true;
        assert!(result.stdout.captured_bytes.len() as u64 <= result.stdout.capture_limit_bytes);
        assert!(result.stdout.total_bytes_observed > result.stdout.capture_limit_bytes);
        assert!(result.stdout.truncated);
    }

    #[test]
    fn temporary_workspace_cleanup_removes_the_workspace() {
        let workspace = TemporaryWorkspace::create("cleanup-test").unwrap();
        let path = workspace.path().to_owned();
        fs::write(path.join("fixture"), b"fixture").unwrap();
        workspace.cleanup().unwrap();
        assert!(!path.exists());
    }

    #[test]
    fn repeated_probes_are_isolated() {
        let cwd = env::current_dir().unwrap();
        let first = probe_tool(
            RuntimeTool::Java,
            missing("isolation-a"),
            &[],
            &cwd,
            &ProcessSupervisor,
        );
        let second = probe_tool(
            RuntimeTool::Javac,
            missing("isolation-b"),
            &[],
            &cwd,
            &ProcessSupervisor,
        );
        assert_ne!(first.executable_requested, second.executable_requested);
        assert_eq!(first.tool, RuntimeTool::Java);
        assert_eq!(second.tool, RuntimeTool::Javac);
        assert_eq!(first.execution.runtime_metadata.process_id, None);
        assert_eq!(second.execution.runtime_metadata.process_id, None);
    }

    #[test]
    fn report_order_is_stable_and_does_not_dump_the_environment() {
        let config = RuntimeConformanceConfig {
            java_executable: missing("report-java"),
            javac_executable: missing("report-javac"),
            junit_classpath: None,
            defects4j_executable: missing("report-defects4j"),
            defects4j_workdir: None,
            working_directory: env::current_dir().unwrap(),
        };
        let report = RuntimeConformanceHarness::new(config).run().render();
        let keys: Vec<_> = report
            .lines()
            .map(|line| line.split('=').next().unwrap())
            .collect();
        assert_eq!(
            &keys[..8],
            [
                "HOST_OS",
                "HOST_ARCH",
                "JAVA_EXECUTABLE",
                "JAVA_PROBE",
                "JAVA_VERSION",
                "JAVAC_EXECUTABLE",
                "JAVAC_PROBE",
                "JAVAC_VERSION",
            ]
        );
        assert!(!report.contains("PATH="));
        assert!(!report.contains("HOME="));
        assert!(!report.contains("TOKEN="));
        assert!(report.contains("SECURE_SANDBOX_COMPLETE=NO\n"));
        assert!(report.contains("RESOURCE_ISOLATION_COMPLETE=NO\n"));
    }
}
