use std::env;
use std::ffi::OsString;
use std::fs;
use std::path::{Path, PathBuf};
use std::process;
use std::sync::atomic::{AtomicU64, Ordering};
use std::thread;
use std::time::{Duration, SystemTime, UNIX_EPOCH};
use testgap_worker::{
    parse_defects4j_failing_test_count, parse_junit_summary, AdapterExecutionOptions,
    CancellationOutcome, CompileOutcome, Defects4JCommand, Defects4JOutcome, Defects4JProjectId,
    Defects4JRequest, Defects4JTestIdentifier, EnvironmentPolicy, ExecutionAdapterError,
    ExecutionFailure, ExecutionPhase, JUnitRequest, JavaClassName, JavaCompileRequest, ProcessExit,
    ProcessSupervisor, TestOutcome, TestRunSummary, TimeoutOutcome,
};

const FIXTURE: &str = env!("CARGO_BIN_EXE_process_fixture");

struct TestDirectory(PathBuf);

impl TestDirectory {
    fn new(label: &str) -> Self {
        static NEXT: AtomicU64 = AtomicU64::new(0);
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let path = env::temp_dir().join(format!(
            "testgap-adapter-{label}-{}-{timestamp}-{}",
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

fn name(value: &str) -> JavaClassName {
    JavaClassName::new(value).unwrap()
}

fn options(directory: &Path, values: &[(&str, &str)]) -> AdapterExecutionOptions {
    let mut options = AdapterExecutionOptions::new(directory);
    let environment = std::iter::once((
        OsString::from("TESTGAP_FIXTURE_ADAPTER_MODE"),
        OsString::from("1"),
    ))
    .chain(
        values
            .iter()
            .map(|(key, value)| (OsString::from(key), OsString::from(value))),
    )
    .collect();
    options.environment = EnvironmentPolicy::ClearAndSet(environment);
    options
}

fn compile_request(directory: &Path, values: &[(&str, &str)]) -> JavaCompileRequest {
    JavaCompileRequest {
        javac_executable: OsString::from(FIXTURE),
        source_files: vec![PathBuf::from("src/Main.java")],
        classpath_entries: Vec::new(),
        output_directory: None,
        execution_options: options(directory, values),
    }
}

fn junit_request(directory: &Path, values: &[(&str, &str)], targets: &[&str]) -> JUnitRequest {
    JUnitRequest {
        java_executable: OsString::from(FIXTURE),
        classpath_entries: vec![PathBuf::from("classes")],
        runner_main_class: name("org.junit.runner.JUnitCore"),
        test_targets: targets.iter().map(|target| name(target)).collect(),
        execution_options: options(directory, values),
        phase: ExecutionPhase::BuggyExecution,
    }
}

#[test]
fn javac_command_preserves_exact_argument_boundaries() {
    let directory = TestDirectory::new("javac-argv");
    let request = JavaCompileRequest {
        javac_executable: OsString::from("javac"),
        source_files: vec![
            PathBuf::from("source folder/First.java"),
            PathBuf::from("source folder/Second.java"),
        ],
        classpath_entries: vec![
            PathBuf::from("library folder/first.jar"),
            PathBuf::from("library folder/second.jar"),
        ],
        output_directory: Some(PathBuf::from("output folder/classes")),
        execution_options: AdapterExecutionOptions::new(directory.path()),
    };
    let command = request.command().unwrap();
    let classpath = env::join_paths(&request.classpath_entries).unwrap();

    assert_eq!(command.executable, "javac");
    assert_eq!(
        command.arguments,
        vec![
            OsString::from("-d"),
            OsString::from("output folder/classes"),
            OsString::from("-classpath"),
            classpath,
            OsString::from("source folder/First.java"),
            OsString::from("source folder/Second.java"),
        ]
    );
}

#[test]
fn javac_disambiguates_java_tool_path_operands() {
    let directory = TestDirectory::new("javac-path-operands");
    let absolute_source = directory.path().join("@Absolute.java");
    let request = JavaCompileRequest {
        javac_executable: OsString::from("javac"),
        source_files: vec![
            PathBuf::from("@compiler.args"),
            PathBuf::from("-Xplugin:malicious.java"),
            absolute_source.clone(),
        ],
        classpath_entries: vec![
            PathBuf::from("@libraries"),
            PathBuf::from("ordinary-libraries"),
        ],
        output_directory: Some(PathBuf::from("@classes")),
        execution_options: AdapterExecutionOptions::new(directory.path()),
    };

    assert_eq!(
        request.command().unwrap().arguments,
        vec![
            OsString::from("-d"),
            PathBuf::from(".").join("@classes").into_os_string(),
            OsString::from("-classpath"),
            env::join_paths([
                PathBuf::from(".").join("@libraries"),
                PathBuf::from("ordinary-libraries"),
            ])
            .unwrap(),
            PathBuf::from(".").join("@compiler.args").into_os_string(),
            PathBuf::from(".")
                .join("-Xplugin:malicious.java")
                .into_os_string(),
            absolute_source.into_os_string(),
        ]
    );
}

#[test]
fn invalid_javac_is_tool_unavailable_and_preserves_raw_result() {
    let directory = TestDirectory::new("javac-unavailable");
    let mut request = compile_request(directory.path(), &[]);
    request.javac_executable = directory
        .path()
        .join("guaranteed-absent-javac")
        .into_os_string();
    let result = request.execute(&ProcessSupervisor).unwrap();

    assert_eq!(result.outcome, CompileOutcome::ToolUnavailable);
    assert_eq!(result.execution.process_exit, ProcessExit::NeverStarted);
    assert!(matches!(
        result.execution.primary_failure(),
        Some(ExecutionFailure::SpawnFailure {
            kind: std::io::ErrorKind::NotFound,
            ..
        })
    ));
}

#[test]
fn compile_success_and_failure_preserve_raw_facts() {
    let directory = TestDirectory::new("compile-results");
    let success = compile_request(directory.path(), &[])
        .execute(&ProcessSupervisor)
        .unwrap();
    let failure = compile_request(
        directory.path(),
        &[
            ("TESTGAP_FIXTURE_EXIT_CODE", "7"),
            ("TESTGAP_FIXTURE_STDOUT", "compiler stdout"),
            ("TESTGAP_FIXTURE_STDERR", "compiler stderr"),
        ],
    )
    .execute(&ProcessSupervisor)
    .unwrap();

    assert_eq!(success.outcome, CompileOutcome::Success);
    assert!(success.execution.is_success());
    assert_eq!(failure.outcome, CompileOutcome::CompilationFailed);
    assert_eq!(
        failure.execution.process_exit,
        ProcessExit::ExitedWithCode(7)
    );
    assert_eq!(failure.execution.stdout.captured_bytes, b"compiler stdout");
    assert_eq!(failure.execution.stderr.captured_bytes, b"compiler stderr");
    assert_eq!(
        failure.execution.runtime_metadata.operating_system,
        env::consts::OS
    );
    assert_eq!(
        failure.execution.runtime_metadata.architecture,
        env::consts::ARCH
    );
    assert!(failure.execution.runtime_metadata.process_id.is_some());
}

#[test]
fn junitcore_command_preserves_exact_argument_boundaries() {
    let directory = TestDirectory::new("junit-argv");
    let request = JUnitRequest {
        java_executable: OsString::from("java"),
        classpath_entries: vec![
            PathBuf::from("build classes"),
            PathBuf::from("jars/junit jar.jar"),
        ],
        runner_main_class: name("org.junit.runner.JUnitCore"),
        test_targets: vec![
            name("com.example.FirstTest"),
            name("com.example.SecondTest"),
        ],
        execution_options: AdapterExecutionOptions::new(directory.path()),
        phase: ExecutionPhase::FixedExecution,
    };
    let command = request.command().unwrap();

    assert_eq!(command.executable, "java");
    assert_eq!(
        command.arguments,
        vec![
            OsString::from("-classpath"),
            env::join_paths(&request.classpath_entries).unwrap(),
            OsString::from("org.junit.runner.JUnitCore"),
            OsString::from("com.example.FirstTest"),
            OsString::from("com.example.SecondTest"),
        ]
    );
}

#[test]
fn junit_disambiguates_classpath_entries_before_joining() {
    let directory = TestDirectory::new("junit-classpath");
    let request = JUnitRequest {
        java_executable: OsString::from("java"),
        classpath_entries: vec![
            PathBuf::from("@runtime-libs"),
            PathBuf::from("ordinary-runtime-libs"),
        ],
        runner_main_class: name("org.junit.runner.JUnitCore"),
        test_targets: vec![name("com.example.SomeTest")],
        execution_options: AdapterExecutionOptions::new(directory.path()),
        phase: ExecutionPhase::BuggyExecution,
    };

    assert_eq!(
        request.command().unwrap().arguments,
        vec![
            OsString::from("-classpath"),
            env::join_paths([
                PathBuf::from(".").join("@runtime-libs"),
                PathBuf::from("ordinary-runtime-libs"),
            ])
            .unwrap(),
            OsString::from("org.junit.runner.JUnitCore"),
            OsString::from("com.example.SomeTest"),
        ]
    );
}

#[test]
fn junit_pass_and_failure_use_exit_and_parse_supported_summaries() {
    let directory = TestDirectory::new("junit-results");
    let passed = junit_request(
        directory.path(),
        &[(
            "TESTGAP_FIXTURE_STDOUT",
            "JUnit version 4.13\nOK (2 tests)\n",
        )],
        &["com.example.FirstTest", "com.example.SecondTest"],
    )
    .execute(&ProcessSupervisor)
    .unwrap();
    let failed = junit_request(
        directory.path(),
        &[
            ("TESTGAP_FIXTURE_EXIT_CODE", "1"),
            ("TESTGAP_FIXTURE_STDOUT", "Tests run: 3,  Failures: 1\n"),
        ],
        &["com.example.FailingTest"],
    )
    .execute(&ProcessSupervisor)
    .unwrap();

    assert_eq!(passed.outcome, TestOutcome::Passed);
    assert_eq!(
        passed.summary,
        Some(TestRunSummary {
            tests_run: 2,
            failures: 0,
        })
    );
    assert_eq!(failed.outcome, TestOutcome::Failed);
    assert_eq!(
        failed.summary,
        Some(TestRunSummary {
            tests_run: 3,
            failures: 1,
        })
    );
    assert_eq!(
        failed.execution.stdout.captured_bytes,
        b"Tests run: 3,  Failures: 1\n"
    );
}

#[test]
fn defects4j_commands_use_separate_arguments() {
    let directory = TestDirectory::new("defects4j-argv");
    let build = |command, phase| Defects4JRequest {
        executable: OsString::from("defects4j"),
        command,
        execution_options: AdapterExecutionOptions::new(directory.path()),
        phase,
    };
    let compile = build(Defects4JCommand::Compile, ExecutionPhase::Compile)
        .command()
        .unwrap();
    let test = build(
        Defects4JCommand::Test { test: None },
        ExecutionPhase::BuggyExecution,
    )
    .command()
    .unwrap();
    let selected = build(
        Defects4JCommand::Test {
            test: Some(Defects4JTestIdentifier::new("com.example.SomeTest::testMethod").unwrap()),
        },
        ExecutionPhase::FixedExecution,
    )
    .command()
    .unwrap();

    assert_eq!(compile.arguments, vec![OsString::from("compile")]);
    assert_eq!(test.arguments, vec![OsString::from("test")]);
    assert_eq!(
        selected.arguments,
        vec![
            OsString::from("test"),
            OsString::from("-t"),
            OsString::from("com.example.SomeTest::testMethod"),
        ]
    );
}

#[test]
fn unavailable_defects4j_is_not_a_test_failure() {
    let directory = TestDirectory::new("defects4j-unavailable");
    let request = Defects4JRequest {
        executable: directory
            .path()
            .join("guaranteed-absent-defects4j")
            .into_os_string(),
        command: Defects4JCommand::Test { test: None },
        execution_options: AdapterExecutionOptions::new(directory.path()),
        phase: ExecutionPhase::BuggyExecution,
    };
    let result = request.execute(&ProcessSupervisor).unwrap();

    assert_eq!(result.outcome, Defects4JOutcome::ToolUnavailable);
    assert_eq!(result.execution.process_exit, ProcessExit::NeverStarted);
}

#[test]
fn timeout_and_cancellation_propagate_from_supervisor() {
    let directory = TestDirectory::new("termination");
    let mut timed = compile_request(directory.path(), &[("TESTGAP_FIXTURE_SLEEP_MS", "500")]);
    timed.execution_options.resource_limits.timeout = Some(Duration::from_millis(20));
    let timed = timed.execute(&ProcessSupervisor).unwrap();

    let cancelled = compile_request(directory.path(), &[("TESTGAP_FIXTURE_SLEEP_MS", "500")]);
    let token = cancelled.execution_options.cancellation.clone();
    let canceller = thread::spawn(move || {
        thread::sleep(Duration::from_millis(20));
        token.cancel();
    });
    let cancelled = cancelled.execute(&ProcessSupervisor).unwrap();
    canceller.join().unwrap();

    assert_eq!(timed.outcome, CompileOutcome::TimedOut);
    assert!(matches!(
        timed.execution.timeout,
        TimeoutOutcome::Triggered { .. }
    ));
    assert_eq!(cancelled.outcome, CompileOutcome::Cancelled);
    assert_eq!(
        cancelled.execution.cancellation,
        CancellationOutcome::Selected
    );
}

#[test]
fn bounded_output_and_runtime_metadata_are_preserved() {
    let directory = TestDirectory::new("bounded-output");
    let mut request = compile_request(
        directory.path(),
        &[
            ("TESTGAP_FIXTURE_STDOUT_BYTES", "2000"),
            ("TESTGAP_FIXTURE_STDERR_BYTES", "3000"),
        ],
    );
    request.execution_options.resource_limits.stdout_bytes = 111;
    request.execution_options.resource_limits.stderr_bytes = 222;
    let result = request.execute(&ProcessSupervisor).unwrap();

    assert_eq!(result.execution.stdout.captured_bytes, vec![b'O'; 111]);
    assert_eq!(result.execution.stdout.total_bytes_observed, 2000);
    assert_eq!(result.execution.stdout.capture_limit_bytes, 111);
    assert!(result.execution.stdout.truncated);
    assert_eq!(result.execution.stderr.captured_bytes, vec![b'E'; 222]);
    assert_eq!(result.execution.stderr.total_bytes_observed, 3000);
    assert_eq!(result.execution.stderr.capture_limit_bytes, 222);
    assert!(result.execution.stderr.truncated);
    assert_eq!(
        result.execution.runtime_metadata.operating_system,
        env::consts::OS
    );
    assert_eq!(
        result.execution.runtime_metadata.architecture,
        env::consts::ARCH
    );
    assert!(result.execution.runtime_metadata.process_id.is_some());
}

#[test]
fn invalid_identifiers_and_phases_are_rejected_before_spawn() {
    assert!(matches!(
        JavaClassName::new("com.example.Bad;Name"),
        Err(ExecutionAdapterError::InvalidJavaClassName(_))
    ));
    assert!(matches!(
        Defects4JProjectId::new("../Chart"),
        Err(ExecutionAdapterError::InvalidDefects4JProject(_))
    ));
    assert!(matches!(
        Defects4JTestIdentifier::new("com.example.Test;rm -rf::method"),
        Err(ExecutionAdapterError::InvalidDefects4JTestIdentifier(_))
    ));

    let directory = TestDirectory::new("invalid-request");
    let mut junit = junit_request(directory.path(), &[], &["com.example.Test"]);
    junit.phase = ExecutionPhase::Compile;
    assert!(matches!(
        junit.execute(&ProcessSupervisor),
        Err(ExecutionAdapterError::InvalidExecutionPhase(
            ExecutionPhase::Compile
        ))
    ));
}

#[test]
fn path_metacharacters_remain_literal_and_no_shell_is_inserted() {
    let directory = TestDirectory::new("literal-paths");
    let opaque_paths = [
        "folder with spaces/Main.java",
        "semi;colon/Second.java",
        "$(not-command)/Third.java",
        "&&/Fourth.java",
        "*/Fifth.java",
    ];
    let mut request = compile_request(directory.path(), &[]);
    request.source_files = opaque_paths.iter().map(PathBuf::from).collect();
    request.classpath_entries = vec![PathBuf::from("class path/semi;colon.jar")];
    request.output_directory = Some(PathBuf::from("output/$(not-command) && *"));
    let command = request.command().unwrap();
    let result = request.execute(&ProcessSupervisor).unwrap();

    assert_eq!(command.executable, FIXTURE);
    for path in opaque_paths {
        assert!(command.arguments.contains(&OsString::from(path)));
    }
    assert!(command
        .arguments
        .contains(&OsString::from("output/$(not-command) && *")));
    assert!(!matches!(
        command.executable.to_string_lossy().as_ref(),
        "sh" | "bash" | "zsh"
    ));
    assert_eq!(result.outcome, CompileOutcome::Success);
}

#[test]
fn parsers_are_deterministic_and_conservative() {
    assert_eq!(
        parse_junit_summary(b"OK (1 test)\n"),
        Some(TestRunSummary {
            tests_run: 1,
            failures: 0,
        })
    );
    assert_eq!(
        parse_junit_summary(b"Tests run: 3,  Failures: 1\n"),
        Some(TestRunSummary {
            tests_run: 3,
            failures: 1,
        })
    );
    assert_eq!(parse_junit_summary(b"OK (many tests)\xff"), None);
    assert_eq!(
        parse_defects4j_failing_test_count(b"Failing tests: 12\n"),
        Some(12)
    );
    assert_eq!(
        parse_defects4j_failing_test_count(b"Failing tests: unknown\xff"),
        None
    );
}

#[test]
fn repeated_adapter_executions_do_not_leak_request_state() {
    let first_directory = TestDirectory::new("isolation-a");
    let second_directory = TestDirectory::new("isolation-b");
    let mut first = junit_request(
        first_directory.path(),
        &[
            ("TESTGAP_FIXTURE_STDOUT", "OK (1 test)\n"),
            ("RUN_VALUE", "first"),
        ],
        &["com.first.OneTest"],
    );
    first.classpath_entries = vec![PathBuf::from("first classpath")];
    first.execution_options.resource_limits.stdout_bytes = 64;
    let mut second = junit_request(
        second_directory.path(),
        &[
            ("TESTGAP_FIXTURE_STDOUT", "OK (2 tests)\n"),
            ("RUN_VALUE", "second"),
        ],
        &["com.second.OneTest", "com.second.TwoTest"],
    );
    second.classpath_entries = vec![PathBuf::from("second classpath")];
    second.execution_options.resource_limits.stdout_bytes = 128;
    second.phase = ExecutionPhase::FixedExecution;

    let first_command = first.command().unwrap();
    let second_command = second.command().unwrap();
    let first_result = first.execute(&ProcessSupervisor).unwrap();
    let second_result = second.execute(&ProcessSupervisor).unwrap();

    assert!(first_command
        .arguments
        .contains(&OsString::from("first classpath")));
    assert!(second_command
        .arguments
        .contains(&OsString::from("second classpath")));
    assert!(first_command
        .arguments
        .contains(&OsString::from("com.first.OneTest")));
    assert!(second_command
        .arguments
        .contains(&OsString::from("com.second.TwoTest")));
    assert_eq!(first_result.execution.stdout.capture_limit_bytes, 64);
    assert_eq!(second_result.execution.stdout.capture_limit_bytes, 128);
    assert_eq!(first_result.execution.phase, ExecutionPhase::BuggyExecution);
    assert_eq!(
        second_result.execution.phase,
        ExecutionPhase::FixedExecution
    );
    assert_eq!(first_result.summary.unwrap().tests_run, 1);
    assert_eq!(second_result.summary.unwrap().tests_run, 2);
}

#[test]
fn structurally_invalid_requests_fail_without_execution_results() {
    let directory = TestDirectory::new("structural-validation");
    let mut compile = compile_request(directory.path(), &[]);
    compile.source_files.clear();
    assert!(matches!(
        compile.execute(&ProcessSupervisor),
        Err(ExecutionAdapterError::EmptySourceSet)
    ));

    compile.source_files.push(PathBuf::from("Main.java"));
    compile.javac_executable = OsString::new();
    assert!(matches!(
        compile.execute(&ProcessSupervisor),
        Err(ExecutionAdapterError::InvalidExecutable)
    ));

    compile.javac_executable = OsString::from(FIXTURE);
    #[cfg(windows)]
    compile.classpath_entries.push(PathBuf::from("bad;entry"));
    #[cfg(not(windows))]
    compile.classpath_entries.push(PathBuf::from("bad:entry"));
    assert!(matches!(
        compile.execute(&ProcessSupervisor),
        Err(ExecutionAdapterError::ClasspathConstructionFailed)
    ));

    let mut junit = junit_request(directory.path(), &[], &["com.example.Test"]);
    junit.test_targets.clear();
    assert!(matches!(
        junit.execute(&ProcessSupervisor),
        Err(ExecutionAdapterError::EmptyTestTargetSet)
    ));
}
