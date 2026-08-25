//! Adversarial coverage for the SEC-003 restricted execution boundary.
//!
//! Every denial asserted here must happen entirely before spawn: the target
//! process is never started (`ProcessExit::NeverStarted`), no process ID is
//! reported, and any side effect the denied target would have produced (a
//! filesystem marker written by the target binary or a rogue script) is
//! provably absent.

use std::env;
use std::ffi::OsString;
use std::fs;
use std::io;
use std::os::unix::fs::{symlink, PermissionsExt};
use std::path::{Path, PathBuf};
use std::process;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, SystemTime, UNIX_EPOCH};
use testgap_worker::{
    AdapterExecutionOptions, CompileOutcome, EnvironmentPolicy, ExecutionAuthority,
    ExecutionAuthorityError, ExecutionCommand, ExecutionFailure, ExecutionPhase, ExecutionRequest,
    ExecutionResult, JavaCompileRequest, ProcessExit, ProcessSupervisor, ResourceLimitRequest,
};

const FIXTURE: &str = env!("CARGO_BIN_EXE_process_fixture");

const FAKE_HOST_SECRET_KEY: &str = "TESTGAP_SEC003_FAKE_HOST_SECRET";
const FAKE_HOST_SECRET_VALUE: &str = "fake-host-secret-NOT-REAL";
const FAKE_CREDENTIAL_KEY: &str = "TESTGAP_SEC003_FAKE_AWS_SECRET_ACCESS_KEY";
const FAKE_CREDENTIAL_VALUE: &str = "FAKEKEY-not-a-real-credential";
const FAKE_UNRELATED_KEY: &str = "TESTGAP_SEC003_FAKE_UNRELATED_PARENT_VAR";
const FAKE_UNRELATED_VALUE: &str = "parent-only-value";
const ALLOWED_ENV_KEY: &str = "TESTGAP_SEC003_ALLOWED_VAR";
const ALLOWED_ENV_VALUE: &str = "allowed-value";

/// Parent-environment mutation is process-global; serialize every test in
/// this binary so fake-secret installation can never race a concurrent
/// spawn's environment snapshot.
static ENV_LOCK: Mutex<()> = Mutex::new(());

fn env_lock() -> std::sync::MutexGuard<'static, ()> {
    ENV_LOCK
        .lock()
        .unwrap_or_else(|poisoned| poisoned.into_inner())
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
            "testgap-exec-authority-{label}-{}-{timestamp}-{}",
            process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&path).unwrap();
        Self(fs::canonicalize(path).unwrap())
    }

    fn path(&self) -> &Path {
        &self.0
    }

    fn subdir(&self, label: &str) -> PathBuf {
        let path = self.0.join(label);
        fs::create_dir(&path).unwrap();
        path
    }
}

impl Drop for TestDirectory {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

/// Writes an executable shell script which, if it were ever spawned, would
/// immediately create `marker`. Used to PROVE denied targets never run.
fn write_rogue_script(path: &Path, marker: &Path) {
    fs::write(
        path,
        format!("#!/bin/sh\nprintf rogue-ran > {}\n", marker.display()),
    )
    .unwrap();
    fs::set_permissions(path, fs::Permissions::from_mode(0o755)).unwrap();
}

fn authority_for(root: &Path) -> ExecutionAuthority {
    ExecutionAuthority::restrict_to_workspace(root)
        .unwrap()
        .authorize_executable(FIXTURE)
        .unwrap()
}

fn restricted_supervisor_for(root: &Path) -> ProcessSupervisor {
    ProcessSupervisor::restricted(authority_for(root))
}

fn request_with(exe: &Path, cwd: &Path, arguments: Vec<OsString>) -> ExecutionRequest {
    let mut command = ExecutionCommand::new(exe.as_os_str(), cwd);
    command.arguments = arguments;
    ExecutionRequest::new(ExecutionPhase::Compile, command)
}

fn marker_arguments(marker: &Path) -> Vec<OsString> {
    vec![
        OsString::from("sleep_then_write"),
        OsString::from("0"),
        marker.as_os_str().to_owned(),
    ]
}

fn assert_never_started(result: &ExecutionResult, expected_kind: io::ErrorKind) {
    assert_eq!(
        result.process_exit,
        ProcessExit::NeverStarted,
        "denied target must never start: {result:?}"
    );
    assert_eq!(
        result.runtime_metadata.process_id, None,
        "denied target must report no process ID"
    );
    match result.primary_failure() {
        Some(ExecutionFailure::SpawnFailure { kind, message }) => {
            assert_eq!(kind, &expected_kind, "unexpected denial kind: {message}");
        }
        other => panic!("expected a spawn failure, got {other:?}"),
    }
    assert!(result.stdout.captured_bytes.is_empty());
    assert!(result.stderr.captured_bytes.is_empty());
}

fn assert_marker_absent(marker: &Path) {
    // Generous settle time: if a bug ever allowed the denied target to run,
    // its very first action is creating this marker.
    thread::sleep(Duration::from_millis(150));
    assert!(
        !marker.exists(),
        "denied target must never execute, but its marker appeared"
    );
}

// ===========================================================================
// Trusted executable authority (section 6/7)
// ===========================================================================

#[test]
fn authorized_executable_runs_against_the_canonical_target() {
    let _guard = env_lock();
    let root = TestDirectory::new("exec-accept");
    let supervisor = restricted_supervisor_for(root.path());

    let result = supervisor.execute(request_with(
        Path::new(FIXTURE),
        root.path(),
        vec![OsString::from("exit"), OsString::from("0")],
    ));

    assert!(result.is_success(), "{result:?}");
    assert!(result.runtime_metadata.process_id.is_some());
}

#[test]
fn arbitrary_absolute_executable_is_rejected_before_spawn() {
    let _guard = env_lock();
    let root = TestDirectory::new("exec-arbitrary");
    let outside = TestDirectory::new("exec-arbitrary-outside");
    let marker = root.path().join("marker");
    let rogue = outside.path().join("rogue");
    write_rogue_script(&rogue, &marker);

    let supervisor = restricted_supervisor_for(root.path());
    let result = supervisor.execute(request_with(&rogue, root.path(), marker_arguments(&marker)));

    assert_never_started(&result, io::ErrorKind::PermissionDenied);
    assert_marker_absent(&marker);
}

#[test]
fn bare_name_executable_gets_no_path_authority() {
    let _guard = env_lock();
    let root = TestDirectory::new("exec-bare-name");
    let marker = root.path().join("marker");
    let supervisor = restricted_supervisor_for(root.path());

    // The fixture's own file name, unqualified: if ambient PATH lookup were
    // consulted anywhere, this would resolve and run. It must not.
    let bare_name = Path::new(FIXTURE).file_name().map(PathBuf::from).unwrap();
    let result = supervisor.execute(request_with(
        &bare_name,
        root.path(),
        marker_arguments(&marker),
    ));

    assert_never_started(&result, io::ErrorKind::InvalidInput);
    assert_marker_absent(&marker);
}

#[test]
fn workspace_relative_path_executable_gets_no_cwd_authority() {
    let _guard = env_lock();
    let root = TestDirectory::new("exec-relative");
    let tools = root.subdir("tools");
    let marker = root.path().join("marker");
    // An existing executable at the relative location: rejection must come
    // from the relative-form rule, not from absence.
    let shadow = tools.join("shadow-tool");
    write_rogue_script(&shadow, &marker);

    let supervisor = restricted_supervisor_for(root.path());
    let relative = PathBuf::from("./tools/shadow-tool");
    let result = supervisor.execute(request_with(
        &relative,
        root.path(),
        marker_arguments(&marker),
    ));

    assert_never_started(&result, io::ErrorKind::InvalidInput);
    assert_marker_absent(&marker);
}

#[test]
fn same_basename_shadow_inside_workspace_is_rejected() {
    let _guard = env_lock();
    let root = TestDirectory::new("exec-shadow");
    let tools = root.subdir("tools");
    let marker = root.path().join("marker");
    // Identical file NAME as the authorized tool, planted inside the
    // workspace: only canonical identity, never a name, grants authority.
    let shadow = tools.join(Path::new(FIXTURE).file_name().map(PathBuf::from).unwrap());
    write_rogue_script(&shadow, &marker);

    let supervisor = restricted_supervisor_for(root.path());
    let result = supervisor.execute(request_with(
        &shadow,
        root.path(),
        marker_arguments(&marker),
    ));

    assert_never_started(&result, io::ErrorKind::PermissionDenied);
    assert_marker_absent(&marker);
}

#[test]
fn alternate_absolute_executable_outside_root_is_rejected() {
    let _guard = env_lock();
    let root = TestDirectory::new("exec-alternate");
    let marker = root.path().join("marker");
    // A real, executable, absolutely spelled binary that simply was never
    // authorized: the test harness itself.
    let alternate = env::current_exe().unwrap();

    let supervisor = restricted_supervisor_for(root.path());
    let result = supervisor.execute(request_with(
        &alternate,
        root.path(),
        marker_arguments(&marker),
    ));

    assert_never_started(&result, io::ErrorKind::PermissionDenied);
    assert_marker_absent(&marker);
}

#[test]
fn executable_symlink_escaping_the_workspace_is_rejected() {
    let _guard = env_lock();
    let root = TestDirectory::new("exec-symlink-escape");
    let outside = TestDirectory::new("exec-symlink-escape-outside");
    let marker = root.path().join("marker");
    let rogue = outside.path().join("rogue");
    write_rogue_script(&rogue, &marker);

    // Lexically inside the workspace, canonically outside it.
    let link = root.path().join("innocent-link");
    symlink(&rogue, &link).unwrap();

    let supervisor = restricted_supervisor_for(root.path());
    let result = supervisor.execute(request_with(&link, root.path(), marker_arguments(&marker)));

    assert_never_started(&result, io::ErrorKind::PermissionDenied);
    assert_marker_absent(&marker);
}

#[test]
fn symlink_to_the_authorized_tool_spawns_only_the_canonical_tool() {
    let _guard = env_lock();
    let root = TestDirectory::new("exec-symlink-canonical");
    let link = root.path().join("tool-link");
    symlink(FIXTURE, &link).unwrap();

    let supervisor = restricted_supervisor_for(root.path());
    // Accepted precisely because its CANONICAL identity is the authorized
    // executable; the authorized canonical path itself is what spawns.
    let result = supervisor.execute(request_with(
        &link,
        root.path(),
        vec![OsString::from("exit"), OsString::from("0")],
    ));

    assert!(result.is_success(), "{result:?}");
}

#[test]
fn authorized_executable_removed_after_setup_fails_closed_at_request_time() {
    let _guard = env_lock();
    let root = TestDirectory::new("exec-vanished");
    let outside = TestDirectory::new("exec-vanished-outside");
    let marker = root.path().join("marker");
    let tool = outside.path().join("vanishing-tool");
    write_rogue_script(&tool, &marker);

    let authority = ExecutionAuthority::restrict_to_workspace(root.path())
        .unwrap()
        .authorize_executable(&tool)
        .unwrap();
    fs::remove_file(&tool).unwrap();

    let supervisor = ProcessSupervisor::restricted(authority);
    let result = supervisor.execute(request_with(&tool, root.path(), marker_arguments(&marker)));

    assert_never_started(&result, io::ErrorKind::NotFound);
    assert_marker_absent(&marker);
}

#[test]
fn authority_setup_rejects_noncanonical_executable_configuration() {
    let _guard = env_lock();
    let root = TestDirectory::new("setup-exe");

    // Bare names can never be authorized: setup itself refuses before any
    // request exists, so PATH can never enter the trust calculation.
    assert!(matches!(
        ExecutionAuthority::restrict_to_workspace(root.path())
            .unwrap()
            .authorize_executable("definitely-not-on-any-trusted-path"),
        Err(ExecutionAuthorityError::ExecutableUnresolvable { .. })
    ));

    // A directory is not an executable identity.
    let tools = root.subdir("tools");
    assert!(matches!(
        ExecutionAuthority::restrict_to_workspace(root.path())
            .unwrap()
            .authorize_executable(&tools),
        Err(ExecutionAuthorityError::ExecutableNotAFile { .. })
    ));

    assert!(matches!(
        ExecutionAuthority::restrict_to_workspace(root.path())
            .unwrap()
            .authorize_executable(""),
        Err(ExecutionAuthorityError::EmptyExecutablePath)
    ));
}

// ===========================================================================
// Workspace root / cwd confinement (sections 8/9)
// ===========================================================================

#[test]
fn canonical_in_root_cwd_is_accepted() {
    let _guard = env_lock();
    let root = TestDirectory::new("cwd-accept");
    let sub = root.subdir("sub");

    let supervisor = restricted_supervisor_for(root.path());
    for cwd in [root.path().to_path_buf(), sub.clone()] {
        let result = supervisor.execute(request_with(
            Path::new(FIXTURE),
            &cwd,
            vec![OsString::from("print_cwd")],
        ));
        assert!(result.is_success(), "{result:?}");
        assert_eq!(
            PathBuf::from(String::from_utf8(result.stdout.captured_bytes).unwrap()),
            fs::canonicalize(&cwd).unwrap()
        );
    }
}

#[test]
fn parentdir_request_that_normalizes_inside_the_root_is_denied_before_spawn() {
    let _guard = env_lock();
    let root = TestDirectory::new("cwd-inside-traversal");
    let sub = root.subdir("sub");
    let marker = root.path().join("marker");

    let supervisor = restricted_supervisor_for(root.path());
    // `sub/.././sub` resolves back INSIDE the root, yet the parent-directory
    // component in the ORIGINAL request is denied before any normalization
    // or spawn can occur.
    let winding = root.path().join("sub").join("..").join(".").join("sub");
    assert_eq!(fs::canonicalize(&winding).unwrap(), sub);

    let result = supervisor.execute(request_with(
        Path::new(FIXTURE),
        &winding,
        marker_arguments(&marker),
    ));

    assert_never_started(&result, io::ErrorKind::PermissionDenied);
    assert_marker_absent(&marker);
}

#[test]
fn parent_traversal_escape_is_rejected_before_spawn() {
    let _guard = env_lock();
    let root = TestDirectory::new("cwd-parent-traversal");
    let outside = TestDirectory::new("cwd-parent-traversal-outside");
    let marker = root.path().join("marker");

    let supervisor = restricted_supervisor_for(root.path());
    let escaping = root
        .path()
        .join("..")
        .join(outside.path().file_name().unwrap());
    let result = supervisor.execute(request_with(
        Path::new(FIXTURE),
        &escaping,
        marker_arguments(&marker),
    ));

    assert_never_started(&result, io::ErrorKind::PermissionDenied);
    assert_marker_absent(&marker);
}

#[test]
fn absolute_host_path_escape_is_rejected_before_spawn() {
    let _guard = env_lock();
    let root = TestDirectory::new("cwd-absolute-escape");
    let marker = root.path().join("marker");

    let supervisor = restricted_supervisor_for(root.path());
    let result = supervisor.execute(request_with(
        Path::new(FIXTURE),
        Path::new("/"),
        marker_arguments(&marker),
    ));

    assert_never_started(&result, io::ErrorKind::PermissionDenied);
    assert_marker_absent(&marker);
}

#[test]
fn sibling_workspace_escape_is_rejected_before_spawn() {
    let _guard = env_lock();
    let root = TestDirectory::new("cwd-sibling");
    let sibling = TestDirectory::new("cwd-sibling-two");
    let marker = root.path().join("marker");

    let supervisor = restricted_supervisor_for(root.path());
    let result = supervisor.execute(request_with(
        Path::new(FIXTURE),
        sibling.path(),
        marker_arguments(&marker),
    ));

    assert_never_started(&result, io::ErrorKind::PermissionDenied);
    assert_marker_absent(&marker);
}

#[test]
fn symlinked_cwd_escaping_the_root_is_rejected_before_spawn() {
    let _guard = env_lock();
    let root = TestDirectory::new("cwd-symlink-escape");
    let outside = TestDirectory::new("cwd-symlink-escape-outside");
    let marker = root.path().join("marker");

    // Directory symlink living inside the root, targeting a directory
    // outside it: lexical membership must not confer authority.
    let link = root.path().join("roomy");
    symlink(outside.path(), &link).unwrap();

    let supervisor = restricted_supervisor_for(root.path());
    let result = supervisor.execute(request_with(
        Path::new(FIXTURE),
        &link,
        marker_arguments(&marker),
    ));

    assert_never_started(&result, io::ErrorKind::PermissionDenied);
    assert_marker_absent(&marker);
}

#[test]
fn nonexistent_cwd_fails_closed_without_resolution() {
    let _guard = env_lock();
    let root = TestDirectory::new("cwd-missing");
    let marker = root.path().join("marker");
    let missing = root.path().join("guaranteed-missing-subdirectory");

    let supervisor = restricted_supervisor_for(root.path());
    let result = supervisor.execute(request_with(
        Path::new(FIXTURE),
        &missing,
        marker_arguments(&marker),
    ));

    assert_never_started(&result, io::ErrorKind::NotFound);
    assert_marker_absent(&marker);
}

#[test]
fn existing_regular_file_as_cwd_is_rejected_before_spawn() {
    let _guard = env_lock();
    let root = TestDirectory::new("cwd-not-a-dir");
    let marker = root.path().join("marker");
    // An EXISTING regular file inside the workspace: it canonicalizes fine,
    // but a working directory must be a directory.
    let file_cwd = root.path().join("plain-file");
    fs::write(&file_cwd, b"data").unwrap();
    assert!(file_cwd.is_file());

    let supervisor = restricted_supervisor_for(root.path());
    let result = supervisor.execute(request_with(
        Path::new(FIXTURE),
        &file_cwd,
        marker_arguments(&marker),
    ));

    assert_never_started(&result, io::ErrorKind::PermissionDenied);
    assert_marker_absent(&marker);
}

#[test]
fn empty_working_directory_is_rejected() {
    let _guard = env_lock();
    let root = TestDirectory::new("cwd-empty");

    let supervisor = restricted_supervisor_for(root.path());
    let result = supervisor.execute(request_with(
        Path::new(FIXTURE),
        Path::new(""),
        vec![OsString::from("exit"), OsString::from("0")],
    ));

    assert_never_started(&result, io::ErrorKind::InvalidInput);
}

// ===========================================================================
// Authority setup failures (section 13)
// ===========================================================================

#[test]
fn workspace_authority_setup_failures_are_fail_closed() {
    let _guard = env_lock();

    assert_eq!(
        ExecutionAuthority::restrict_to_workspace(""),
        Err(ExecutionAuthorityError::EmptyWorkspaceRoot)
    );

    assert!(matches!(
        ExecutionAuthority::restrict_to_workspace(Path::new(
            "/testgap-guaranteed-missing-workspace-root",
        )),
        Err(ExecutionAuthorityError::WorkspaceRootUnresolvable { .. })
    ));

    // A file is not a workspace root.
    let root = TestDirectory::new("setup-file-root");
    let file_root = root.path().join("plain-file");
    fs::write(&file_root, b"data").unwrap();
    assert!(matches!(
        ExecutionAuthority::restrict_to_workspace(&file_root),
        Err(ExecutionAuthorityError::WorkspaceRootNotADirectory { .. })
    ));
}

#[test]
fn environment_authority_setup_rejects_invalid_entries() {
    let _guard = env_lock();
    let root = TestDirectory::new("setup-env");

    assert!(matches!(
        ExecutionAuthority::restrict_to_workspace(root.path())
            .unwrap()
            .authorize_environment_entry("", "value"),
        Err(ExecutionAuthorityError::EmptyEnvironmentKey)
    ));

    assert!(matches!(
        ExecutionAuthority::restrict_to_workspace(root.path())
            .unwrap()
            .authorize_environment_entry(ALLOWED_ENV_KEY, "first")
            .unwrap()
            .authorize_environment_entry(ALLOWED_ENV_KEY, "second"),
        Err(ExecutionAuthorityError::DuplicateEnvironmentKey { .. })
    ));
}

// ===========================================================================
// Child environment authority (section 10)
// ===========================================================================

fn install_fake_host_secrets() {
    env::set_var(FAKE_HOST_SECRET_KEY, FAKE_HOST_SECRET_VALUE);
    env::set_var(FAKE_CREDENTIAL_KEY, FAKE_CREDENTIAL_VALUE);
    env::set_var(FAKE_UNRELATED_KEY, FAKE_UNRELATED_VALUE);
}

fn remove_fake_host_secrets() {
    env::remove_var(FAKE_HOST_SECRET_KEY);
    env::remove_var(FAKE_CREDENTIAL_KEY);
    env::remove_var(FAKE_UNRELATED_KEY);
}

fn authority_with_allowed_env(root: &Path) -> ExecutionAuthority {
    authority_for(root)
        .authorize_environment_entry(ALLOWED_ENV_KEY, ALLOWED_ENV_VALUE)
        .unwrap()
}

fn child_env_value(supervisor: &ProcessSupervisor, root: &Path, key: &str) -> String {
    let result = supervisor.execute(request_with(
        Path::new(FIXTURE),
        root,
        vec![OsString::from("print_env"), OsString::from(key)],
    ));
    assert!(result.is_success(), "print_env({key}) failed: {result:?}");
    String::from_utf8(result.stdout.captured_bytes).unwrap()
}

#[test]
fn host_secrets_credentials_and_unrelated_env_never_reach_the_child() {
    let _guard = env_lock();
    install_fake_host_secrets();
    let root = TestDirectory::new("env-deny");
    let supervisor = ProcessSupervisor::restricted(authority_with_allowed_env(root.path()));

    assert_eq!(
        child_env_value(&supervisor, root.path(), FAKE_HOST_SECRET_KEY),
        "<unset>"
    );
    assert_eq!(
        child_env_value(&supervisor, root.path(), FAKE_CREDENTIAL_KEY),
        "<unset>"
    );
    assert_eq!(
        child_env_value(&supervisor, root.path(), FAKE_UNRELATED_KEY),
        "<unset>"
    );

    remove_fake_host_secrets();
}

#[test]
fn explicitly_authorized_env_reaches_the_child() {
    let _guard = env_lock();
    let root = TestDirectory::new("env-allowed");
    let supervisor = ProcessSupervisor::restricted(authority_with_allowed_env(root.path()));

    assert_eq!(
        child_env_value(&supervisor, root.path(), ALLOWED_ENV_KEY),
        ALLOWED_ENV_VALUE
    );
}

#[test]
fn child_environment_is_exactly_the_authorized_surface() {
    let _guard = env_lock();
    let root = TestDirectory::new("env-exact");
    // Even a deliberately narrower request cannot change what the child
    // receives: the authorized surface alone defines the environment.
    let supervisor = ProcessSupervisor::restricted(authority_with_allowed_env(root.path()));
    let mut command = ExecutionCommand::new(FIXTURE, root.path());
    command.arguments = vec![OsString::from("print_env"), OsString::from(ALLOWED_ENV_KEY)];
    command.environment = EnvironmentPolicy::ClearAndSet(Vec::new());
    let result = supervisor.execute(ExecutionRequest::new(ExecutionPhase::Compile, command));

    assert!(result.is_success(), "{result:?}");
    assert_eq!(
        String::from_utf8(result.stdout.captured_bytes).unwrap(),
        ALLOWED_ENV_VALUE
    );
}

#[test]
fn non_allowlisted_requested_env_key_is_rejected_before_spawn() {
    let _guard = env_lock();
    let root = TestDirectory::new("env-extra-key");
    let marker = root.path().join("marker");
    let supervisor = ProcessSupervisor::restricted(authority_with_allowed_env(root.path()));

    let mut command = ExecutionCommand::new(FIXTURE, root.path());
    command.arguments = marker_arguments(&marker);
    command.environment = EnvironmentPolicy::ClearAndSet(vec![(
        OsString::from("TESTGAP_SEC003_EVIL_WIDENING_KEY"),
        OsString::from("attacker-value"),
    )]);
    let result = supervisor.execute(ExecutionRequest::new(ExecutionPhase::Compile, command));

    assert_never_started(&result, io::ErrorKind::PermissionDenied);
    assert_marker_absent(&marker);
}

#[test]
fn authorized_key_with_tampered_value_is_rejected_before_spawn() {
    let _guard = env_lock();
    let root = TestDirectory::new("env-tampered");
    let marker = root.path().join("marker");
    let supervisor = ProcessSupervisor::restricted(authority_with_allowed_env(root.path()));

    let mut command = ExecutionCommand::new(FIXTURE, root.path());
    command.arguments = marker_arguments(&marker);
    command.environment = EnvironmentPolicy::ClearAndSet(vec![(
        OsString::from(ALLOWED_ENV_KEY),
        OsString::from("tampered-value"),
    )]);
    let result = supervisor.execute(ExecutionRequest::new(ExecutionPhase::Compile, command));

    assert_never_started(&result, io::ErrorKind::PermissionDenied);
    assert_marker_absent(&marker);
}

#[test]
fn inherit_and_override_cannot_reactivate_host_inheritance() {
    let _guard = env_lock();
    install_fake_host_secrets();
    let root = TestDirectory::new("env-inherit");
    let marker = root.path().join("marker");
    let supervisor = ProcessSupervisor::restricted(authority_with_allowed_env(root.path()));

    // Empty override list...
    let mut plain = ExecutionCommand::new(FIXTURE, root.path());
    plain.arguments = marker_arguments(&marker);
    plain.environment = EnvironmentPolicy::InheritAndOverride(Vec::new());
    let result = supervisor.execute(ExecutionRequest::new(ExecutionPhase::Compile, plain));
    assert_never_started(&result, io::ErrorKind::PermissionDenied);
    assert_marker_absent(&marker);

    // ...and even a perfectly allowlist-shaped override list: the unsafe
    // inheritance MODE itself is forbidden, structurally, before spawn.
    let mut shaped = ExecutionCommand::new(FIXTURE, root.path());
    shaped.arguments = marker_arguments(&marker);
    shaped.environment = EnvironmentPolicy::InheritAndOverride(vec![(
        OsString::from(ALLOWED_ENV_KEY),
        OsString::from(ALLOWED_ENV_VALUE),
    )]);
    let result = supervisor.execute(ExecutionRequest::new(ExecutionPhase::Compile, shaped));
    assert_never_started(&result, io::ErrorKind::PermissionDenied);
    assert_marker_absent(&marker);

    // The host secret stayed confined to the parent either way.
    let probe = supervisor.execute(request_with(
        Path::new(FIXTURE),
        root.path(),
        vec![
            OsString::from("print_env"),
            OsString::from(FAKE_HOST_SECRET_KEY),
        ],
    ));
    assert!(probe.is_success());
    assert_eq!(
        String::from_utf8(probe.stdout.captured_bytes).unwrap(),
        "<unset>"
    );

    remove_fake_host_secrets();
}

#[test]
fn denial_messages_never_contain_environment_values() {
    let _guard = env_lock();
    let root = TestDirectory::new("env-message-hygiene");
    let secret_value = "super-secret-value-must-not-leak";
    let supervisor = ProcessSupervisor::restricted(authority_with_allowed_env(root.path()));

    let mut unknown = ExecutionCommand::new(FIXTURE, root.path());
    unknown.environment = EnvironmentPolicy::ClearAndSet(vec![(
        OsString::from("TESTGAP_SEC003_UNKNOWN_KEY"),
        OsString::from(secret_value),
    )]);
    let result = supervisor.execute(ExecutionRequest::new(ExecutionPhase::Compile, unknown));
    match result.primary_failure() {
        Some(ExecutionFailure::SpawnFailure { message, .. }) => {
            assert!(!message.contains(secret_value));
            assert!(!message.contains("TESTGAP_SEC003_UNKNOWN_KEY="));
        }
        other => panic!("expected denial, got {other:?}"),
    }

    let mut tampered = ExecutionCommand::new(FIXTURE, root.path());
    tampered.environment = EnvironmentPolicy::ClearAndSet(vec![(
        OsString::from(ALLOWED_ENV_KEY),
        OsString::from("tampered-secret-value"),
    )]);
    let result = supervisor.execute(ExecutionRequest::new(ExecutionPhase::Compile, tampered));
    match result.primary_failure() {
        Some(ExecutionFailure::SpawnFailure { message, .. }) => {
            assert!(!message.contains("tampered-secret-value"));
        }
        other => panic!("expected denial, got {other:?}"),
    }
}

// ===========================================================================
// Secret/debug hygiene (section 11)
// ===========================================================================

const FAKE_DEBUG_SECRET_VALUE: &str = "TESTGAP_FAKE_DEBUG_SECRET_VALUE_7e2d0f4c9a1b";

#[test]
fn debug_formatting_of_authority_and_supervisor_never_carries_env_values() {
    let _guard = env_lock();
    let root = TestDirectory::new("debug-hygiene");
    let authority = ExecutionAuthority::restrict_to_workspace(root.path())
        .unwrap()
        .authorize_executable(FIXTURE)
        .unwrap()
        .authorize_environment_entry(ALLOWED_ENV_KEY, FAKE_DEBUG_SECRET_VALUE)
        .unwrap();

    // Keys MAY be visible; the authorized VALUE must be structurally absent
    // from Debug output, never merely discouraged by convention.
    let authority_rendered = format!("{authority:?}");
    assert!(
        !authority_rendered.contains(FAKE_DEBUG_SECRET_VALUE),
        "ExecutionAuthority Debug leaked an authorized environment value"
    );
    assert!(authority_rendered.contains(ALLOWED_ENV_KEY));

    let supervisor = ProcessSupervisor::restricted(authority);
    let supervisor_rendered = format!("{supervisor:?}");
    assert!(
        !supervisor_rendered.contains(FAKE_DEBUG_SECRET_VALUE),
        "ProcessSupervisor Debug leaked an authorized environment value"
    );
}

// ===========================================================================
// Composition with supervision and adapters (sections 14/16)
// ===========================================================================

#[test]
fn restricted_boundary_keeps_structured_argv_literal() {
    let _guard = env_lock();
    let root = TestDirectory::new("restricted-argv");
    let payload = "$(rm -rf /); `id` && sh -c 'echo pwned' | cat /etc/passwd";

    let supervisor = restricted_supervisor_for(root.path());
    let result = supervisor.execute(request_with(
        Path::new(FIXTURE),
        root.path(),
        vec![OsString::from("echo_args"), OsString::from(payload)],
    ));

    assert!(result.is_success(), "{result:?}");
    assert_eq!(
        result.stdout.captured_bytes,
        format!("{}:{payload}\n", payload.len()).as_bytes()
    );
}

#[test]
fn restricted_boundary_keeps_timeout_supervision() {
    let _guard = env_lock();
    let root = TestDirectory::new("restricted-timeout");
    let mut request = request_with(
        Path::new(FIXTURE),
        root.path(),
        vec![OsString::from("sleep_ms"), OsString::from("5000")],
    );
    request.resource_limits.timeout = Some(Duration::from_millis(50));

    let supervisor = restricted_supervisor_for(root.path());
    let result = supervisor.execute(request);

    assert!(matches!(
        result.primary_failure(),
        Some(ExecutionFailure::Timeout)
    ));
    assert!(result.runtime_metadata.process_id.is_some());
}

#[test]
fn restricted_boundary_keeps_cpu_limit_fail_closed_semantics() {
    let _guard = env_lock();
    let root = TestDirectory::new("restricted-cpu");
    let marker = root.path().join("marker");
    let mut request = request_with(Path::new(FIXTURE), root.path(), marker_arguments(&marker));
    request.resource_limits.cpu_time = Some(Duration::from_secs(1));
    request.resource_limits.timeout = Some(Duration::from_secs(5));

    // On platforms without truthful hard CPU enforcement (macOS), the frozen
    // EXEC-007C policy fails closed BEFORE the target executes — composing
    // with, not bypassing, resource_limits::decide.
    let supervisor = restricted_supervisor_for(root.path());
    let result = supervisor.execute(request);

    if cfg!(all(target_os = "linux", target_pointer_width = "64")) {
        assert_ne!(result.process_exit, ProcessExit::NeverStarted);
    } else {
        assert_never_started(&result, io::ErrorKind::Unsupported);
        assert_marker_absent(&marker);
    }
}

fn adapter_options(directory: &Path) -> AdapterExecutionOptions {
    let mut options = AdapterExecutionOptions::new(directory);
    options.resource_limits = ResourceLimitRequest::default();
    options
}

#[test]
fn adapter_requests_run_through_the_restricted_boundary_when_authorized() {
    let _guard = env_lock();
    let root = TestDirectory::new("adapter-restricted-ok");
    let authority = authority_for(root.path())
        .authorize_environment_entry("TESTGAP_FIXTURE_ADAPTER_MODE", "1")
        .unwrap();
    let supervisor = ProcessSupervisor::restricted(authority);

    let result = JavaCompileRequest {
        javac_executable: OsString::from(FIXTURE),
        source_files: vec![PathBuf::from("src/Main.java")],
        classpath_entries: Vec::new(),
        output_directory: None,
        execution_options: adapter_options(root.path()),
    }
    .execute(&supervisor)
    .unwrap();

    assert_eq!(result.outcome, CompileOutcome::Success);
}

#[test]
fn adapter_request_material_cannot_bypass_restricted_authority() {
    let _guard = env_lock();
    let root = TestDirectory::new("adapter-restricted-deny");
    let outside = TestDirectory::new("adapter-restricted-deny-outside");
    let marker = root.path().join("marker");
    let rogue = outside.path().join("rogue-javac");
    write_rogue_script(&rogue, &marker);

    // Adapter-level validation accepts this executable (non-empty string);
    // the process-level authority is what rejects it, before spawn.
    let supervisor = restricted_supervisor_for(root.path());
    let result = JavaCompileRequest {
        javac_executable: OsString::from(rogue.as_os_str()),
        source_files: vec![PathBuf::from("src/Main.java")],
        classpath_entries: Vec::new(),
        output_directory: None,
        execution_options: adapter_options(root.path()),
    }
    .execute(&supervisor)
    .unwrap();

    assert_eq!(result.execution.process_exit, ProcessExit::NeverStarted);
    assert_eq!(result.execution.runtime_metadata.process_id, None);
    assert_eq!(result.outcome, CompileOutcome::RunnerError);
    assert_marker_absent(&marker);
}
