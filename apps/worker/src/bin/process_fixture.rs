use std::env;
use std::ffi::OsString;
use std::fmt::Display;
use std::fs;
use std::io::{self, Write};
use std::path::PathBuf;
use std::process::{self, Command};
use std::str::FromStr;
use std::thread;
use std::time::Duration;

fn main() {
    match run() {
        Ok(code) => process::exit(code),
        Err(message) => {
            eprintln!("{message}");
            process::exit(2);
        }
    }
}

fn run() -> Result<i32, String> {
    if env::var_os("TESTGAP_FIXTURE_ADAPTER_MODE").is_some() {
        return run_adapter_mode();
    }

    let mut arguments = env::args_os().skip(1);
    let operation = required(&mut arguments, "operation")?;
    let operation = operation
        .to_str()
        .ok_or_else(|| "operation must be valid UTF-8".to_owned())?;

    match operation {
        "exit" => parse(&mut arguments, "exit code"),
        "stdout" => {
            let count = parse(&mut arguments, "stdout byte count")?;
            emit(io::stdout().lock(), b'O', count)?;
            Ok(0)
        }
        "stderr" => {
            let count = parse(&mut arguments, "stderr byte count")?;
            emit(io::stderr().lock(), b'E', count)?;
            Ok(0)
        }
        "stdout_text" => {
            write_os(
                io::stdout().lock(),
                required(&mut arguments, "stdout text")?,
            )?;
            Ok(0)
        }
        "stderr_text" => {
            write_os(
                io::stderr().lock(),
                required(&mut arguments, "stderr text")?,
            )?;
            Ok(0)
        }
        "echo_args" => {
            let mut stdout = io::stdout().lock();
            for argument in arguments {
                let argument = argument.to_string_lossy();
                writeln!(stdout, "{}:{argument}", argument.len()).map_err(io_error)?;
            }
            Ok(0)
        }
        "print_env" => {
            let name = required(&mut arguments, "environment variable name")?;
            let value = env::var_os(name).unwrap_or_else(|| OsString::from("<unset>"));
            write_os(io::stdout().lock(), value)?;
            Ok(0)
        }
        "print_cwd" => {
            write_os(
                io::stdout().lock(),
                env::current_dir().map_err(io_error)?.into(),
            )?;
            Ok(0)
        }
        "sleep_ms" => {
            let milliseconds = parse(&mut arguments, "sleep milliseconds")?;
            thread::sleep(Duration::from_millis(milliseconds));
            Ok(0)
        }
        "sleep_then_write" => {
            let milliseconds = parse(&mut arguments, "sleep milliseconds")?;
            let marker = PathBuf::from(required(&mut arguments, "marker path")?);
            thread::sleep(Duration::from_millis(milliseconds));
            fs::write(marker, b"written").map_err(io_error)?;
            Ok(0)
        }
        #[cfg(all(target_os = "linux", target_pointer_width = "64"))]
        "print_rlimit_cpu" => {
            let limits = read_own_rlimit_cpu()?;
            writeln!(
                io::stdout().lock(),
                "RLIMIT_CPU cur={} max={}",
                limits.rlim_cur,
                limits.rlim_max
            )
            .map_err(io_error)?;
            Ok(0)
        }
        "cpu_burn" => burn_until_terminated(),
        #[cfg(all(target_os = "linux", target_pointer_width = "64"))]
        "cpu_burn_ignore_sigxcpu" => {
            install_sigxcpu_disposition(cpu_fixture_sig_ign())?;
            emit_sigxcpu_ignore_ready()?;
            burn_until_terminated()
        }
        #[cfg(all(target_os = "linux", target_pointer_width = "64"))]
        "cpu_burn_catch_sigxcpu" => {
            install_sigxcpu_disposition(cpu_fixture_catch_handler())?;
            burn_until_terminated()
        }
        "spawn_descendant" => {
            let marker = PathBuf::from(required(&mut arguments, "descendant PID path")?);
            let milliseconds = required(&mut arguments, "descendant lifetime milliseconds")?;
            let mut descendant = Command::new(env::current_exe().map_err(io_error)?)
                .arg("sleep_ms")
                .arg(milliseconds)
                .spawn()
                .map_err(io_error)?;
            fs::write(marker, descendant.id().to_string()).map_err(io_error)?;
            descendant.wait().map_err(io_error)?;
            Ok(0)
        }
        "snapshot" => {
            let environment_name = required(&mut arguments, "environment variable name")?;
            let argument = required(&mut arguments, "snapshot argument")?;
            let cwd = env::current_dir().map_err(io_error)?;
            let value = env::var_os(environment_name).unwrap_or_else(|| OsString::from("<unset>"));
            writeln!(
                io::stdout().lock(),
                "cwd={}\nenv={}\narg={}",
                cwd.display(),
                value.to_string_lossy(),
                argument.to_string_lossy()
            )
            .map_err(io_error)?;
            Ok(0)
        }
        _ => Err(format!("unknown operation: {operation}")),
    }
}

fn run_adapter_mode() -> Result<i32, String> {
    if let Some(milliseconds) = environment_parse("TESTGAP_FIXTURE_SLEEP_MS")? {
        thread::sleep(Duration::from_millis(milliseconds));
    }
    if let Some(count) = environment_parse("TESTGAP_FIXTURE_STDOUT_BYTES")? {
        emit(io::stdout().lock(), b'O', count)?;
    }
    if let Some(value) = env::var_os("TESTGAP_FIXTURE_STDOUT") {
        write_os(io::stdout().lock(), value)?;
    }
    if let Some(count) = environment_parse("TESTGAP_FIXTURE_STDERR_BYTES")? {
        emit(io::stderr().lock(), b'E', count)?;
    }
    if let Some(value) = env::var_os("TESTGAP_FIXTURE_STDERR") {
        write_os(io::stderr().lock(), value)?;
    }
    Ok(environment_parse("TESTGAP_FIXTURE_EXIT_CODE")?.unwrap_or(0))
}

fn environment_parse<T>(name: &str) -> Result<Option<T>, String>
where
    T: FromStr,
    T::Err: Display,
{
    env::var_os(name)
        .map(|value| {
            value
                .into_string()
                .map_err(|_| format!("{name} must be valid UTF-8"))?
                .parse()
                .map_err(|error| format!("invalid {name}: {error}"))
        })
        .transpose()
}

fn required(
    arguments: &mut impl Iterator<Item = OsString>,
    name: &str,
) -> Result<OsString, String> {
    arguments.next().ok_or_else(|| format!("missing {name}"))
}

fn parse<T>(arguments: &mut impl Iterator<Item = OsString>, name: &str) -> Result<T, String>
where
    T: FromStr,
    T::Err: Display,
{
    required(arguments, name)?
        .into_string()
        .map_err(|_| format!("{name} must be valid UTF-8"))?
        .parse()
        .map_err(|error| format!("invalid {name}: {error}"))
}

fn emit(mut writer: impl Write, byte: u8, mut remaining: usize) -> Result<(), String> {
    let chunk = [byte; 8192];
    while remaining > 0 {
        let count = remaining.min(chunk.len());
        writer.write_all(&chunk[..count]).map_err(io_error)?;
        remaining -= count;
    }
    Ok(())
}

fn write_os(mut writer: impl Write, value: OsString) -> Result<(), String> {
    writer
        .write_all(value.to_string_lossy().as_bytes())
        .map_err(io_error)
}

fn io_error(error: io::Error) -> String {
    error.to_string()
}

/// Consumes real CPU time indefinitely with arithmetic the optimizer cannot
/// fold away. Termination is expected from an external mechanism such as
/// RLIMIT_CPU or a supervisor wall timeout; it is never sleep-based.
fn burn_until_terminated() -> Result<i32, String> {
    let mut state: u64 = 0x9E37_79B9_7F4A_7C15;
    loop {
        state = state
            .wrapping_mul(6_364_136_223_846_793_005)
            .wrapping_add(1_442_695_040_888_963_407)
            ^ (state >> 7);
        std::hint::black_box(state);
    }
}

/// Readiness marker proving the SIGXCPU-ignore disposition was installed and
/// the burner entered its loop. Emitted through the normal stdout path BEFORE
/// any CPU is consumed, so the parent-side test can distinguish "burning with
/// SIGXCPU ignored" from "died unseen at the soft boundary".
#[cfg(all(target_os = "linux", target_pointer_width = "64"))]
const SIGXCPU_IGNORED_READY_MARKER: &[u8] = b"SIGXCPU_IGNORED_READY\n";

/// Fixed bytes written by the catch-fixture's SIGXCPU handler via a raw
/// `write(2)` syscall, giving the parent-side test externally observable
/// proof that the signal was actually delivered to an installed handler.
#[cfg(all(target_os = "linux", target_pointer_width = "64"))]
const SIGXCPU_CAUGHT_MARKER: &[u8] = b"SIGXCPU_CAUGHT\n";

/// Standard-output descriptor, already open when the supervisor spawns this
/// fixture with piped stdout.
#[cfg(all(target_os = "linux", target_pointer_width = "64"))]
const STDOUT_FILENO: std::ffi::c_int = 1;

/// Emits [`SIGXCPU_IGNORED_READY_MARKER`] through the fixture's normal stdout
/// path (with an explicit flush) after the disposition install succeeded but
/// before burning starts.
#[cfg(all(target_os = "linux", target_pointer_width = "64"))]
fn emit_sigxcpu_ignore_ready() -> Result<(), String> {
    let mut stdout = io::stdout().lock();
    stdout
        .write_all(SIGXCPU_IGNORED_READY_MARKER)
        .map_err(io_error)?;
    stdout.flush().map_err(io_error)
}

/// SIGXCPU handler for the catch fixture.
///
/// Records delivery by performing one async-signal-safe `write(2)` of fixed
/// static bytes to the already-open stdout descriptor, then returns so the
/// burner resumes and is subsequently forced onto the finite hard ceiling.
/// The parent cannot inspect process memory after a fatal signal, so this
/// syscall side effect is the only evidence channel that survives.
#[cfg(all(target_os = "linux", target_pointer_width = "64"))]
extern "C" fn cpu_burn_sigxcpu_handler(_signum: i32) {
    // SAFETY: async-signal-safety constraints for handlers are met exactly:
    // - `write` is on POSIX's list of async-signal-safe functions;
    // - STDOUT_FILENO was inherited open at spawn and is never closed by this
    //   process, so no descriptor lifecycle race exists;
    // - the buffer is a fixed immutable byte constant with static lifetime:
    //   no allocation, formatting, locking, or Rust stdio machinery runs here;
    // - the 15-byte payload is far below PIPE_BUF, so the kernel writes it
    //   atomically even if a re-delivered SIGXCPU interrupts an earlier
    //   invocation mid-handler, and the ignored return value cannot corrupt
    //   any state observable by the parent;
    // - the loop only advances over the fixed buffer and terminates.
    unsafe {
        let mut written = 0_usize;
        while written < SIGXCPU_CAUGHT_MARKER.len() {
            let count = cpu_fixture_ffi::write(
                STDOUT_FILENO,
                SIGXCPU_CAUGHT_MARKER[written..].as_ptr().cast(),
                SIGXCPU_CAUGHT_MARKER.len() - written,
            );
            if count <= 0 {
                // Retryable or fatal failure; never loop forever in a handler.
                break;
            }
            written += count as usize;
        }
    }
}

#[cfg(all(target_os = "linux", target_pointer_width = "64"))]
fn cpu_fixture_sig_ign() -> usize {
    cpu_fixture_ffi::SIG_IGN
}

#[cfg(all(target_os = "linux", target_pointer_width = "64"))]
fn cpu_fixture_catch_handler() -> usize {
    // The intermediate function-pointer type keeps the cast explicit and
    // ABI-checked before it becomes a `sighandler_t`-shaped address.
    cpu_burn_sigxcpu_handler as extern "C" fn(i32) as usize
}

/// Minimal private Linux fixture FFI mirroring `<sys/resource.h>` and
/// `<signal.h>` for LP64 Linux (`rlim_t` = unsigned long, `RLIMIT_CPU` = 0,
/// `SIG_IGN` = 1). `SIGXCPU` numbering follows the production mapping in
/// resource_limits.rs: 24 on every LP64 architecture outside the MIPS family
/// and 30 on MIPS-family targets, selected by cfg so each build compiles the
/// constant that is actually correct for its architecture.
#[cfg(all(target_os = "linux", target_pointer_width = "64"))]
mod cpu_fixture_ffi {
    use std::ffi::{c_int, c_ulong};

    #[repr(C)]
    #[derive(Clone, Copy)]
    pub struct RLimit {
        pub rlim_cur: c_ulong,
        pub rlim_max: c_ulong,
    }

    pub const RLIMIT_CPU: c_int = 0;

    /// Matches production `SIGXCPU_LINUX` in resource_limits.rs.
    #[cfg(not(any(target_arch = "mips", target_arch = "mips64")))]
    pub const SIGXCPU: c_int = 24;

    /// Matches production `SIGXCPU_LINUX` in resource_limits.rs; MIPS-family
    /// Linux numbers SIGXCPU differently from every other LP64 architecture.
    #[cfg(any(target_arch = "mips", target_arch = "mips64"))]
    pub const SIGXCPU: c_int = 30;

    pub const SIG_IGN: usize = 1;

    unsafe extern "C" {
        pub fn getrlimit(resource: c_int, rlim: *mut RLimit) -> c_int;
        pub fn signal(signum: c_int, handler: usize) -> usize;
        /// Raw `write(2)` used only by the SIGXCPU handler because Rust
        /// stdio machinery is not async-signal-safe.
        pub fn write(fd: c_int, buf: *const u8, count: usize) -> isize;
    }
}

#[cfg(all(target_os = "linux", target_pointer_width = "64"))]
fn read_own_rlimit_cpu() -> Result<cpu_fixture_ffi::RLimit, String> {
    let mut limits = cpu_fixture_ffi::RLimit {
        rlim_cur: 0,
        rlim_max: 0,
    };
    // SAFETY: `getrlimit` receives RLIMIT_CPU's stable Linux resource number
    // and a valid, initialized, `repr(C)` pointer that mirrors glibc/musl's
    // `struct rlimit` layout exactly on LP64 Linux. The kernel writes at most
    // the two fields of this local during the call, no pointers outlive it,
    // and this is ordinary process context (not pre_exec), so failure is
    // reported as a normal fixture error instead of aborting anything.
    let result = unsafe { cpu_fixture_ffi::getrlimit(cpu_fixture_ffi::RLIMIT_CPU, &mut limits) };
    if result == 0 {
        Ok(limits)
    } else {
        Err(format!(
            "getrlimit(RLIMIT_CPU) failed: {}",
            io::Error::last_os_error()
        ))
    }
}

#[cfg(all(target_os = "linux", target_pointer_width = "64"))]
fn install_sigxcpu_disposition(handler: usize) -> Result<(), String> {
    use cpu_fixture_ffi::SIGXCPU;

    // SAFETY: `signal` receives the stable Linux SIGXCPU number and
    // either SIG_IGN (1) or the address of `cpu_burn_sigxcpu_handler`,
    // whose `extern "C" fn(i32)` signature matches `sighandler_t`. The
    // returned previous handler is intentionally ignored because these
    // fixtures never restore dispositions. This runs in ordinary process
    // context before burning starts, not inside pre_exec.
    let result = unsafe { cpu_fixture_ffi::signal(SIGXCPU, handler) };
    if result == LIBC_SIG_ERR {
        Err(format!(
            "signal(SIGXCPU) failed: {}",
            io::Error::last_os_error()
        ))
    } else {
        Ok(())
    }
}

#[cfg(all(target_os = "linux", target_pointer_width = "64"))]
const LIBC_SIG_ERR: usize = usize::MAX;
