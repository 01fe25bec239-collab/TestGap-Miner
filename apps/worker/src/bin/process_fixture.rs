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
