//! Execution-owned command, path, and environment authority for restricted
//! (untrusted) process execution.
//!
//! This module is the trusted configuration side of the worker's execution
//! boundary. An [`ExecutionAuthority`] is built exclusively from
//! caller-side trusted configuration — never from repository, model,
//! candidate, or task data — and every authorization decision it makes at
//! request time fails closed before a target can spawn.
//!
//! What an authority controls:
//!
//! - **Workspace root confinement**: the canonical workspace root is
//!   established once at construction; every requested working directory is
//!   canonically resolved and must remain inside it.
//! - **Executable identity**: bare names are never resolved through `PATH`.
//!   A requested executable must canonically resolve to one of the
//!   pre-authorized canonical executables, and the spawned target is always
//!   that authorized canonical path itself.
//! - **Child environment**: default-deny. The child receives exactly the
//!   explicitly authorized key/value surface and never inherits the host
//!   environment. `EnvironmentPolicy::InheritAndOverride` is structurally
//!   rejected on this boundary.
//!
//! Truthful nonclaims: this is NOT memory, network, filesystem-wide,
//! container, namespace, mount, or device isolation, and it does not claim
//! protection against concurrent filesystem races beyond canonical
//! pre-spawn validation. It is not a complete secure sandbox.

use crate::EnvironmentPolicy;
use std::ffi::{OsStr, OsString};
use std::fmt;
use std::fs;
use std::io;
use std::path::{Component, Path, PathBuf};

/// Fails-closed error produced while establishing trusted execution
/// authority. No permissive partially-initialized authority can exist.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ExecutionAuthorityError {
    EmptyWorkspaceRoot,
    WorkspaceRootUnresolvable { path: PathBuf, reason: String },
    WorkspaceRootNotADirectory { path: PathBuf },
    EmptyExecutablePath,
    ExecutableUnresolvable { path: PathBuf, reason: String },
    ExecutableNotAFile { path: PathBuf },
    EmptyEnvironmentKey,
    DuplicateEnvironmentKey { key: OsString },
}

impl fmt::Display for ExecutionAuthorityError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::EmptyWorkspaceRoot => formatter.write_str(
                "workspace root must not be empty; refusing to create execution authority",
            ),
            Self::WorkspaceRootUnresolvable { path, reason } => write!(
                formatter,
                "workspace root {} does not canonically resolve: {reason}",
                path.display()
            ),
            Self::WorkspaceRootNotADirectory { path } => write!(
                formatter,
                "workspace root {} is not a directory",
                path.display()
            ),
            Self::EmptyExecutablePath => formatter.write_str(
                "authorized executable path must not be empty; \
                 refusing to create execution authority",
            ),
            Self::ExecutableUnresolvable { path, reason } => write!(
                formatter,
                "authorized executable {} does not canonically resolve: {reason}",
                path.display()
            ),
            Self::ExecutableNotAFile { path } => write!(
                formatter,
                "authorized executable {} is not a regular file",
                path.display()
            ),
            Self::EmptyEnvironmentKey => formatter.write_str("environment keys must not be empty"),
            Self::DuplicateEnvironmentKey { key } => write!(
                formatter,
                "environment key {key:?} was authorized more than once"
            ),
        }
    }
}

impl std::error::Error for ExecutionAuthorityError {}

/// Pre-spawn denial of an untrusted execution request. The target has not
/// been started and must never be started for this request.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct SpawnDenial {
    pub(crate) kind: io::ErrorKind,
    pub(crate) message: String,
}

impl SpawnDenial {
    fn invalid_input(message: String) -> Self {
        Self {
            kind: io::ErrorKind::InvalidInput,
            message,
        }
    }

    fn permission_denied(message: String) -> Self {
        Self {
            kind: io::ErrorKind::PermissionDenied,
            message,
        }
    }

    fn unresolvable(label: &str, path: &Path, error: &io::Error) -> Self {
        Self {
            kind: error.kind(),
            message: format!(
                "{label} {} does not canonically resolve: {error}",
                path.display()
            ),
        }
    }
}

/// The fully validated spawn material for one restricted execution. Every
/// field is canonical and authorized; the supervisor must spawn exactly
/// these values rather than anything from the original request.
#[derive(Clone)]
pub(crate) struct PreparedSpawn {
    /// The authorized canonical executable that will actually be spawned.
    pub(crate) executable: PathBuf,
    /// The canonical working directory, proven to stay inside the
    /// authorized workspace root.
    pub(crate) working_directory: PathBuf,
    /// The complete deliberately constructed child environment. The host
    /// environment is never consulted.
    pub(crate) environment: Vec<(OsString, OsString)>,
}

impl fmt::Debug for PreparedSpawn {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter
            .debug_struct("PreparedSpawn")
            .field("executable", &self.executable)
            .field("working_directory", &self.working_directory)
            .field("environment_keys", &EnvironmentKeys(&self.environment))
            .finish()
    }
}

/// Debug projection rendering ONLY the keys of an authorized environment.
/// Values are structurally unreachable through `Debug`: credentials,
/// tokens, and other authorized secrets can therefore never surface via
/// any `{:?}` formatting of authority or supervisor state.
struct EnvironmentKeys<'a>(&'a [(OsString, OsString)]);

impl fmt::Debug for EnvironmentKeys<'_> {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter
            .debug_list()
            .entries(self.0.iter().map(|(key, _)| key))
            .finish()
    }
}

/// Trusted authority for restricted execution of untrusted requests.
///
/// Constructed only from trusted caller-side configuration. Each step
/// canonicalizes immediately and fails closed, so an [`ExecutionAuthority`]
/// value always represents fully established authority:
///
/// - the workspace root is a canonical existing directory;
/// - every authorized executable is a canonical existing regular file;
/// - the environment surface is an explicit allowlist of concrete
///   key/value pairs (default deny; the host environment is never read).
///
/// Requests cannot widen any of these sets.
#[derive(Clone, PartialEq, Eq)]
pub struct ExecutionAuthority {
    workspace_root: PathBuf,
    authorized_executables: Vec<PathBuf>,
    authorized_environment: Vec<(OsString, OsString)>,
}

impl fmt::Debug for ExecutionAuthority {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter
            .debug_struct("ExecutionAuthority")
            .field("workspace_root", &self.workspace_root)
            .field("authorized_executables", &self.authorized_executables)
            .field(
                "authorized_environment_keys",
                &EnvironmentKeys(&self.authorized_environment),
            )
            .finish()
    }
}

impl ExecutionAuthority {
    /// Establishes workspace authority over a canonicalized root directory.
    ///
    /// Fails closed when the root is empty, missing, unresolvable, or not a
    /// directory.
    pub fn restrict_to_workspace(root: impl AsRef<Path>) -> Result<Self, ExecutionAuthorityError> {
        let requested = root.as_ref();
        if requested.as_os_str().is_empty() {
            return Err(ExecutionAuthorityError::EmptyWorkspaceRoot);
        }
        let canonical = fs::canonicalize(requested).map_err(|error| {
            ExecutionAuthorityError::WorkspaceRootUnresolvable {
                path: requested.to_path_buf(),
                reason: error.to_string(),
            }
        })?;
        if !canonical.is_dir() {
            return Err(ExecutionAuthorityError::WorkspaceRootNotADirectory {
                path: requested.to_path_buf(),
            });
        }
        Ok(Self {
            workspace_root: canonical,
            authorized_executables: Vec::new(),
            authorized_environment: Vec::new(),
        })
    }

    /// Authorizes one executable location by canonical identity.
    ///
    /// The path must exist and resolve to a regular file. Symlinks are
    /// resolved during construction: it is the canonical *target* that is
    /// authorized, never the lexical request path. Fails closed otherwise.
    pub fn authorize_executable(
        mut self,
        executable: impl AsRef<Path>,
    ) -> Result<Self, ExecutionAuthorityError> {
        let requested = executable.as_ref();
        if requested.as_os_str().is_empty() {
            return Err(ExecutionAuthorityError::EmptyExecutablePath);
        }
        let canonical = fs::canonicalize(requested).map_err(|error| {
            ExecutionAuthorityError::ExecutableUnresolvable {
                path: requested.to_path_buf(),
                reason: error.to_string(),
            }
        })?;
        if !canonical.is_file() {
            return Err(ExecutionAuthorityError::ExecutableNotAFile {
                path: requested.to_path_buf(),
            });
        }
        if !self.authorized_executables.contains(&canonical) {
            self.authorized_executables.push(canonical);
            self.authorized_executables.sort();
        }
        Ok(self)
    }

    /// Authorizes one exact environment key/value pair for the child.
    ///
    /// This is the ONLY mechanism by which a value reaches the child
    /// environment of restricted execution. Keys must be non-empty and
    /// unique. Values are carried verbatim and never logged. Fails closed
    /// on invalid or duplicated keys.
    pub fn authorize_environment_entry(
        mut self,
        key: impl Into<OsString>,
        value: impl Into<OsString>,
    ) -> Result<Self, ExecutionAuthorityError> {
        let key = key.into();
        let value = value.into();
        if key.is_empty() {
            return Err(ExecutionAuthorityError::EmptyEnvironmentKey);
        }
        if self
            .authorized_environment
            .iter()
            .any(|(existing, _)| *existing == key)
        {
            return Err(ExecutionAuthorityError::DuplicateEnvironmentKey { key });
        }
        self.authorized_environment.push((key, value));
        self.authorized_environment.sort_by(|a, b| a.0.cmp(&b.0));
        Ok(self)
    }

    /// Canonical workspace root this authority confines working directories
    /// to.
    pub fn workspace_root(&self) -> &Path {
        &self.workspace_root
    }

    /// Authorized canonical executables, sorted.
    pub fn authorized_executables(&self) -> &[PathBuf] {
        &self.authorized_executables
    }

    /// Authorized child-environment surface, sorted by key.
    pub fn authorized_environment(&self) -> &[(OsString, OsString)] {
        &self.authorized_environment
    }

    /// Validates an untrusted request against this authority, entirely
    /// before any spawn attempt.
    pub(crate) fn prepare(
        &self,
        executable: &OsStr,
        working_directory: &Path,
        environment: &EnvironmentPolicy,
    ) -> Result<PreparedSpawn, SpawnDenial> {
        let spawn_executable = self.authorize_request_executable(executable)?;
        let spawn_directory = self.confine_working_directory(working_directory)?;
        let child_environment = self.build_child_environment(environment)?;

        Ok(PreparedSpawn {
            executable: spawn_executable,
            working_directory: spawn_directory,
            environment: child_environment,
        })
    }

    /// Resolves the requested executable against the authorized set.
    ///
    /// Rejections, all before spawn:
    /// - empty executables;
    /// - relative executables of ANY shape (bare names, `./name`,
    ///   `dir/name`, `../name`) so ambient `PATH` and cwd-relative lookup
    ///   can never select the target;
    /// - absolute paths whose canonical resolution is missing or errors;
    /// - absolute paths whose canonical identity differs from every
    ///   authorized executable (alternate binaries, PATH shadows placed in
    ///   the workspace, symlinks escaping to unauthorized targets).
    ///
    /// On success the returned path is the AUTHORIZED CANONICAL entry
    /// itself, guaranteeing the spawned binary is exactly the configured
    /// tool even when the request spelled the path differently.
    fn authorize_request_executable(&self, requested: &OsStr) -> Result<PathBuf, SpawnDenial> {
        if requested.is_empty() {
            return Err(SpawnDenial::invalid_input(
                "executable must not be empty".to_owned(),
            ));
        }
        let requested_path = Path::new(requested);
        if !requested_path.is_absolute() {
            return Err(SpawnDenial::invalid_input(format!(
                "relative executable {requested:?} is rejected: the restricted boundary \
                 resolves executables only through explicit canonical authorization, \
                 never through PATH or cwd-relative lookup"
            )));
        }
        let canonical = match fs::canonicalize(requested_path) {
            Ok(path) => path,
            Err(error) => {
                return Err(SpawnDenial::unresolvable(
                    "requested executable",
                    requested_path,
                    &error,
                ))
            }
        };
        // Component hygiene on the resolved target: canonicalize removes
        // traversal components, so any survivor would be unexpected.
        if has_traversal_components(&canonical) {
            return Err(SpawnDenial::permission_denied(format!(
                "requested executable {requested:?} did not resolve to a clean canonical path"
            )));
        }
        match self
            .authorized_executables
            .iter()
            .find(|authorized| **authorized == canonical)
        {
            Some(authorized) => Ok(authorized.clone()),
            None => Err(SpawnDenial::permission_denied(format!(
                "requested executable {requested:?} is not an authorized executable identity"
            ))),
        }
    }

    /// Canonically confines the requested working directory inside the
    /// authorized workspace root.
    ///
    /// The ORIGINAL untrusted request is inspected lexically BEFORE any
    /// canonicalization: `fs::canonicalize` silently removes `.` and `..`
    /// components, so a request carrying a parent-directory component is
    /// denied outright even when it would normalize back inside the root.
    ///
    /// Containment then uses component-aware canonical path comparison,
    /// never a lexical string prefix, so absolute escapes, sibling
    /// workspaces, and in-root symlinks pointing outside are all rejected.
    /// Unresolvable (for example nonexistent) directories fail closed, as
    /// does any resolution that is not an actual directory.
    fn confine_working_directory(&self, requested: &Path) -> Result<PathBuf, SpawnDenial> {
        if requested.as_os_str().is_empty() {
            return Err(SpawnDenial::invalid_input(
                "working directory must not be empty".to_owned(),
            ));
        }
        // Lexical gate on the request itself. This can never be replaced by
        // a check on the canonicalized result: canonicalization erases the
        // very components being denied here.
        if requested
            .components()
            .any(|component| component == Component::ParentDir)
        {
            return Err(SpawnDenial::permission_denied(format!(
                "working directory {requested:?} contains parent-directory traversal; \
                 parent traversal is denied without normalization"
            )));
        }
        let canonical = match fs::canonicalize(requested) {
            Ok(path) => path,
            Err(error) => {
                return Err(SpawnDenial::unresolvable(
                    "working directory",
                    requested,
                    &error,
                ))
            }
        };
        // Defensive post-canonicalization scan: canonical paths never carry
        // `.` or `..` components, so any survivor signals an unexpected
        // resolution result.
        if has_traversal_components(&canonical) {
            return Err(SpawnDenial::permission_denied(
                "working directory did not resolve to a clean canonical path".to_owned(),
            ));
        }
        if !canonical.is_dir() {
            return Err(SpawnDenial::permission_denied(format!(
                "working directory {} exists but is not a directory",
                canonical.display()
            )));
        }
        // `Path::starts_with` compares whole components, so a sibling root
        // such as `/tmp/ws2` does not satisfy a `/tmp/ws` prefix.
        if !canonical.starts_with(&self.workspace_root) {
            return Err(SpawnDenial::permission_denied(format!(
                "working directory {} resolves outside the authorized workspace root {}",
                canonical.display(),
                self.workspace_root.display()
            )));
        }
        Ok(canonical)
    }

    /// Builds the deliberate child environment under default deny.
    ///
    /// - `ClearAndSet`: every requested pair must already be authorized with
    ///   the identical value; non-allowlisted keys and value mismatches are
    ///   rejected before spawn. The child still receives the full authorized
    ///   surface, which alone defines its environment.
    /// - `InheritAndOverride`: structurally forbidden here. Host/ambient
    ///   inheritance can never be reactivated by request data on this
    ///   boundary.
    ///
    /// Failure messages name offending KEYS only and never carry values.
    fn build_child_environment(
        &self,
        policy: &EnvironmentPolicy,
    ) -> Result<Vec<(OsString, OsString)>, SpawnDenial> {
        match policy {
            EnvironmentPolicy::InheritAndOverride(_) => {
                return Err(SpawnDenial::permission_denied(
                    "environment policy InheritAndOverride is forbidden on the restricted \
                     boundary; child environments are constructed exclusively from the \
                     authorized allowlist"
                        .to_owned(),
                ));
            }
            EnvironmentPolicy::ClearAndSet(requested) => {
                for (key, value) in requested {
                    let Some((_, authorized_value)) = self
                        .authorized_environment
                        .iter()
                        .find(|(candidate, _)| candidate == key)
                    else {
                        return Err(SpawnDenial::permission_denied(format!(
                            "environment key {key:?} is not authorized for restricted execution"
                        )));
                    };
                    if authorized_value != value {
                        return Err(SpawnDenial::permission_denied(format!(
                            "environment key {key:?} does not match its authorized value"
                        )));
                    }
                }
            }
        }
        Ok(self.authorized_environment.clone())
    }
}

/// Defensive component scan: canonical paths never carry `.` or `..`
/// components, so any survivor signals an unexpected resolution result.
fn has_traversal_components(path: &Path) -> bool {
    path.components()
        .any(|component| matches!(component, Component::ParentDir | Component::CurDir))
}
