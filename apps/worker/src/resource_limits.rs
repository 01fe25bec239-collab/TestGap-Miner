//! CPU runtime-limit preparation and child-local application.
//!
//! Platform policy (frozen for EXEC-007C):
//!
//! - Linux 64-bit: a requested CPU-time limit is hard enforced by installing
//!   `RLIMIT_CPU` inside the child via [`CommandExt::pre_exec`] *before*
//!   `exec`. Limit values are fully prepared and validated in the parent
//!   before fork — caller `Duration` → checked rounded seconds → checked hard
//!   backstop → checked finite native `rlim_t` values (the kernel's
//!   representable-but-unlimited `RLIM_INFINITY` sentinel is rejected) → a
//!   fully prepared `Copy` `repr(C)` `RLimit` — so the child-side closure
//!   only performs the single
//!   prepared `setrlimit` syscall and converts syscall failure into an
//!   [`io::Error`]. If installation fails, `spawn` reports an error and the
//!   target never executes.
//! - Every other platform (including macOS): there is no truthful
//!   non-cooperative hard CPU backstop, so any requested CPU limit fails
//!   closed before spawn. The target MUST NOT execute.
//!
//! No parent-worker global resource-limit state exists here; each limited
//! child owns its own copied limit values, so concurrent executions are safe.

use std::time::Duration;

#[cfg(all(target_os = "linux", target_pointer_width = "64"))]
use std::io;
#[cfg(all(target_os = "linux", target_pointer_width = "64"))]
use std::os::unix::process::CommandExt;
#[cfg(all(target_os = "linux", target_pointer_width = "64"))]
use std::process::Command;

/// Decision derived from a requested CPU-time limit, computed entirely in the
/// long-lived parent process before any fork.
#[derive(Debug, Clone)]
pub(crate) enum CpuTimeDecision {
    /// No CPU limit was requested; existing behavior is unchanged.
    None,
    /// A validated finite soft/hard pair to install child-locally on Linux.
    #[cfg_attr(
        not(all(target_os = "linux", target_pointer_width = "64")),
        expect(dead_code)
    )]
    EnforceChildLocal(CpuLimits),
    /// A requested CPU limit cannot be truthfully enforced here; the target
    /// must not be started. The message is deterministic parent-side text.
    FailClosedBeforeSpawn(String),
}

/// Finite kernel limit values in whole seconds (`rlim_t` units).
///
/// Policy: `soft = ceil(caller Duration)` whole seconds and
/// `hard = soft + 1` as a finite non-cooperative kernel backstop. A child
/// that ignores or catches `SIGXCPU` still receives `SIGKILL` from the
/// kernel at the hard ceiling, which cannot be caught, ignored, or blocked.
///
/// On Linux 64-bit the struct holds the *fully prepared* native `repr(C)`
/// limit pair: every check and conversion happened in the parent before any
/// fork, so the later `pre_exec` closure captures only this `Copy` value and
/// contains no validation, conversion, formatting, allocation, or panic path.
///
/// Both prepared fields are guaranteed strictly finite: neither `rlim_cur`
/// nor `rlim_max` can ever equal the native [`ffi::RLIM_INFINITY`] sentinel,
/// which would silently mean "no limit".
#[derive(Debug, Clone, Copy)]
pub(crate) struct CpuLimits {
    /// The prepared native `setrlimit` payload: `rlim_cur = soft`,
    /// `rlim_max = hard`, already converted into kernel `rlim_t` units with
    /// checked, fail-closed conversions in [`CpuLimits::prepare`].
    #[cfg(all(target_os = "linux", target_pointer_width = "64"))]
    pub(crate) native: ffi::RLimit,

    // Off Linux 64-bit these values are intentionally constructed and then
    // discarded by fail-closed policy, so the fields are legitimately unread.
    #[cfg(not(all(target_os = "linux", target_pointer_width = "64")))]
    #[cfg_attr(
        not(all(target_os = "linux", target_pointer_width = "64")),
        expect(dead_code)
    )]
    pub(crate) soft: u64,
    #[cfg(not(all(target_os = "linux", target_pointer_width = "64")))]
    #[cfg_attr(
        not(all(target_os = "linux", target_pointer_width = "64")),
        expect(dead_code)
    )]
    pub(crate) hard: u64,
}

impl CpuLimits {
    /// Converts a caller duration into finite kernel seconds.
    ///
    /// - `Duration::ZERO` fails closed.
    /// - Positive fractional durations CEILING to the next whole second,
    ///   matching kernel granularity (never truncated toward zero).
    /// - Any arithmetic that would overflow the kernel representation (and
    ///   therefore risk saturating toward unlimited) fails closed.
    /// - On Linux 64-bit the checked whole-second pair is additionally
    ///   converted to native `rlim_t` here, still in the parent. The
    ///   conversion is *finite-only*: a value that cannot be represented
    ///   natively, or that lands on the representable-but-unlimited
    ///   `RLIM_INFINITY` sentinel, fails closed instead of ever reaching a
    ///   panic-capable `pre_exec` path — so no caller input can produce an
    ///   unlimited limit while this module claims enforcement.
    pub(crate) fn prepare(duration: Duration) -> Result<Self, String> {
        if duration == Duration::ZERO {
            return Err(
                "a zero cpu_time limit cannot be enforced; refusing to start the target".to_owned(),
            );
        }

        let seconds = duration.as_secs();
        let rounded_seconds = seconds
            .checked_add(u64::from(duration.subsec_nanos() != 0))
            .ok_or_else(|| {
                format!("cpu_time limit {duration:?} overflows kernel second granularity")
            })?;

        // The hard backstop must stay strictly finite; overflowing while
        // computing it would silently approach an unlimited ceiling, so fail
        // closed instead. This arithmetic guard alone is not sufficient: on
        // LP64 Linux `u64::MAX` fits natively yet equals the kernel's
        // unlimited `RLIM_INFINITY` sentinel, so the finite-only native
        // conversion below provides the second, independent guard.
        let hard_backstop = rounded_seconds.checked_add(1).ok_or_else(|| {
            format!("cpu_time hard backstop for {duration:?} overflows the kernel representation")
        })?;

        Ok(Self {
            #[cfg(all(target_os = "linux", target_pointer_width = "64"))]
            native: ffi::RLimit {
                rlim_cur: checked_finite_rlim_t(rounded_seconds)?,
                rlim_max: checked_finite_rlim_t(hard_backstop)?,
            },
            #[cfg(not(all(target_os = "linux", target_pointer_width = "64")))]
            soft: rounded_seconds,
            #[cfg(not(all(target_os = "linux", target_pointer_width = "64")))]
            hard: hard_backstop,
        })
    }
}

/// Classifies a requested CPU-time limit into the platform decision above.
pub(crate) fn decide(cpu_time: Option<Duration>) -> CpuTimeDecision {
    let Some(duration) = cpu_time else {
        return CpuTimeDecision::None;
    };

    match CpuLimits::prepare(duration) {
        Ok(limits) => {
            #[cfg(all(target_os = "linux", target_pointer_width = "64"))]
            {
                CpuTimeDecision::EnforceChildLocal(limits)
            }
            #[cfg(not(all(target_os = "linux", target_pointer_width = "64")))]
            {
                let _ = limits;
                CpuTimeDecision::FailClosedBeforeSpawn(format!(
                    "requested cpu_time limit {duration:?} has no truthful non-cooperative \
                     hard enforcement on {} and the target was not started",
                    std::env::consts::OS,
                ))
            }
        }
        Err(reason) => CpuTimeDecision::FailClosedBeforeSpawn(format!(
            "requested cpu_time limit {duration:?} failed validation: {reason}"
        )),
    }
}

/// Attaches the child-local `setrlimit(RLIMIT_CPU)` to the command on Linux
/// and reports whether child-local enforcement was requested.
///
/// Must only receive decisions produced by [`decide`]; all validation,
/// overflow checks, and native `rlim_t` conversion already happened in the
/// parent during [`CpuLimits::prepare`], before this point.
#[cfg(all(target_os = "linux", target_pointer_width = "64"))]
pub(crate) fn prepare_command(command: &mut Command, decision: &CpuTimeDecision) -> bool {
    match decision {
        CpuTimeDecision::EnforceChildLocal(limits) => {
            // The only value captured by the pre_exec closure: a fully
            // prepared `Copy` `repr(C)` limit pair built in the parent.
            let prepared = limits.native;
            // SAFETY: `CommandExt::pre_exec` requires the closure to be safe
            // to run between fork and exec in the forked child. This closure
            // captures exactly one fully prepared `Copy` `repr(C)` `RLimit`
            // whose values were zero-checked, ceiling-rounded, hard-backstop-
            // overflow-checked, and natively converted to `rlim_t` in the
            // parent before fork (see CpuLimits::prepare), so the closure has
            // no validation, formatting, allocation, or panic path. It calls
            // apply_cpu_limit, which performs exactly one async-signal-safe
            // `setrlimit(RLIMIT_CPU)` syscall, does no logging, locking,
            // filesystem, or environment access, mutates only the child's own
            // limit table, leaves the long-lived parent worker's RLIMIT_CPU
            // untouched, and aborts the pre-exec sequence with Err so the
            // target can never execute unrestricted if installation fails.
            unsafe {
                command.pre_exec(move || apply_cpu_limit(&prepared));
            }
            true
        }
        CpuTimeDecision::None | CpuTimeDecision::FailClosedBeforeSpawn(_) => false,
    }
}

/// Off Linux 64-bit every requested limit fails closed before spawn, so no
/// enforcement attachment can ever be reached here.
#[cfg(not(all(target_os = "linux", target_pointer_width = "64")))]
pub(crate) fn prepare_command(
    _command: &mut std::process::Command,
    decision: &CpuTimeDecision,
) -> bool {
    match decision {
        CpuTimeDecision::None => false,
        CpuTimeDecision::FailClosedBeforeSpawn(_) => false,
        CpuTimeDecision::EnforceChildLocal(_) => {
            unreachable!("CPU decisions are fail-closed before spawn off Linux 64-bit")
        }
    }
}

/// Reports whether an exit status proves the freshly installed CPU soft limit
/// itself terminated the child (default-disposition `SIGXCPU` death).
///
/// `SIGKILL` deaths are deliberately NOT attributed: they may come from the
/// supervisor, the OOM killer, or operators, so they stay unclaimed.
#[cfg(all(target_os = "linux", target_pointer_width = "64"))]
pub(crate) fn terminated_by_installed_cpu_limit(
    installed: bool,
    status: &std::process::ExitStatus,
) -> bool {
    use std::os::unix::process::ExitStatusExt;

    installed && status.signal() == Some(SIGXCPU_LINUX)
}

/// Off Linux 64-bit nothing ever terminates through this feature.
#[cfg(not(all(target_os = "linux", target_pointer_width = "64")))]
pub(crate) fn terminated_by_installed_cpu_limit(
    _installed: bool,
    _status: &std::process::ExitStatus,
) -> bool {
    false
}

/// Converts a checked whole-second limit into a *finite* native kernel
/// `rlim_t`.
///
/// Runs in the long-lived parent during [`CpuLimits::prepare`], never inside
/// `pre_exec`, so an unrepresentable value fails the whole request closed
/// instead of leaving a panic path in the forked child.
///
/// Two independent guards, because representable does not mean finite:
///
/// 1. range: the value must fit natively in `rlim_t` at all;
/// 2. sentinel: on LP64 Linux `rlim_t` is unsigned and `RLIM_INFINITY ==
///    (rlim_t)-1 == u64::MAX`, so `u64::MAX` converts without any overflow
///    yet means "no limit". Returning it would silently produce unlimited
///    CPU while claiming enforcement, so the sentinel is rejected outright.
#[cfg(all(target_os = "linux", target_pointer_width = "64"))]
fn checked_finite_rlim_t(value: u64) -> Result<ffi::RlimT, String> {
    let native = ffi::RlimT::try_from(value)
        .map_err(|_| format!("cpu_time limit {value} exceeds the kernel rlim_t range"))?;
    if native == ffi::RLIM_INFINITY {
        return Err(format!(
            "cpu_time limit {value} equals the kernel RLIM_INFINITY unlimited sentinel \
             and can never enforce a finite limit"
        ));
    }
    Ok(native)
}

/// Applies a fully prepared native limit pair to the calling (forked,
/// pre-exec) child.
///
/// Every validation step — zero rejection, ceiling rounding, hard-backstop
/// overflow checking, and `rlim_t` conversion — already completed in the
/// parent before fork, so this function contains no panic, formatting,
/// allocation, or validation path: it is exactly one syscall plus
/// errno-to-[`io::Error`] translation.
#[cfg(all(target_os = "linux", target_pointer_width = "64"))]
fn apply_cpu_limit(prepared: &ffi::RLimit) -> Result<(), io::Error> {
    // SAFETY: `setrlimit` receives RLIMIT_CPU's stable Linux resource number
    // and a pointer to the fully prepared `repr(C)` struct mirroring
    // glibc/musl's `struct rlimit { rlim_t rlim_cur; rlim_t rlim_max; }`,
    // where `rlim_t` is `unsigned long` (u64) on every LP64 Linux ABI, so
    // layout matches exactly. Both field values were checked and natively
    // converted in the parent before fork and copied into the closure by
    // value; no parent state, allocation, formatting, locking, or I/O happens
    // here. The call runs at most once per child between fork and exec
    // (single async-signal-safe syscall), mutates only the forked child's own
    // limit table, never touches the long-lived parent worker's RLIMIT_CPU,
    // and on failure returns Err so the pre-exec sequence aborts and the
    // target binary can never execute unrestricted.
    let result = unsafe { ffi::setrlimit(ffi::RLIMIT_CPU, prepared) };
    if result == 0 {
        Ok(())
    } else {
        Err(io::Error::last_os_error())
    }
}

/// Minimal private Linux FFI mirror of `<sys/resource.h>`.
///
/// Independently audited for 64-bit Linux (glibc and musl):
/// - `RLIMIT_CPU == 0` (asm-generic/resource.h, shared by both libcs).
/// - `rlim_t` is `unsigned long` == u64 on every LP64 ABI.
/// - `struct rlimit` is two `rlim_t` fields with no padding on LP64.
/// - Signature is `int setrlimit(int, const struct rlimit *)`, returning
///   0 on success and -1 with errno on failure.
/// - `RLIM_INFINITY` is `(rlim_t)-1`; because `rlim_t` is unsigned, that is
///   exactly `RlimT::MAX` (all ones) on every LP64 ABI — a *representable*
///   value meaning "no limit", never an overflow.
///
/// These assumptions are additionally proven at runtime by tests that read
/// the child's own `getrlimit(RLIMIT_CPU)` values back and observe real
/// `SIGXCPU`/`SIGKILL` bounding of CPU burners.
#[cfg(all(target_os = "linux", target_pointer_width = "64"))]
mod ffi {
    use std::ffi::{c_int, c_ulong};

    pub type RlimT = c_ulong;

    #[repr(C)]
    #[derive(Clone, Copy, Debug)]
    pub struct RLimit {
        pub rlim_cur: RlimT,
        pub rlim_max: RlimT,
    }

    pub const RLIMIT_CPU: c_int = 0;

    /// Native unlimited sentinel: any limit equal to this value disables
    /// enforcement, so [`super::checked_finite_rlim_t`] rejects it.
    pub const RLIM_INFINITY: RlimT = RlimT::MAX;

    unsafe extern "C" {
        pub fn setrlimit(resource: c_int, rlim: *const RLimit) -> c_int;
    }
}

/// `SIGXCPU` on 64-bit Linux. Every LP64 architecture except the MIPS family
/// numbers it 24; MIPS numbers it 30. Attribution stays truthful per-arch.
#[cfg(all(
    target_os = "linux",
    target_pointer_width = "64",
    not(any(target_arch = "mips", target_arch = "mips64"))
))]
const SIGXCPU_LINUX: i32 = 24;
#[cfg(all(
    target_os = "linux",
    target_pointer_width = "64",
    any(target_arch = "mips", target_arch = "mips64")
))]
const SIGXCPU_LINUX: i32 = 30;

/// Parent-side precision tests for the finite-only native conversion. They
/// pin the exact distinction between arithmetic overflow and the
/// representable `RLIM_INFINITY` sentinel without spawning anything.
#[cfg(all(test, target_os = "linux", target_pointer_width = "64"))]
mod linux_native_conversion_tests {
    use super::*;
    use std::time::Duration;

    #[test]
    fn sentinel_is_representable_and_equals_u64_max() {
        // RLIM_INFINITY == (rlim_t)-1, and unsigned -1 is the all-ones
        // maximum: it converts from u64 with NO overflow whatsoever.
        assert_eq!(ffi::RlimT::try_from(u64::MAX), Ok(ffi::RLIM_INFINITY));
        assert_eq!(ffi::RLIM_INFINITY, ffi::RlimT::MAX);
    }

    #[test]
    fn finite_values_pass_through_unchanged() {
        assert_eq!(checked_finite_rlim_t(0), Ok(0));
        assert_eq!(
            checked_finite_rlim_t(u64::MAX - 2),
            Ok(ffi::RLIM_INFINITY - 2)
        );
    }

    #[test]
    fn representable_infinity_sentinel_is_rejected_despite_no_overflow() {
        let error = checked_finite_rlim_t(u64::MAX)
            .expect_err("the RLIM_INFINITY sentinel must never pass as a finite limit");
        assert!(
            error.contains("RLIM_INFINITY"),
            "failure must name the sentinel, got: {error}"
        );
    }

    #[test]
    fn near_infinity_duration_fails_on_sentinel_not_on_arithmetic() {
        // u64::MAX - 1 survives EVERY pure-arithmetic step: rounding is a
        // no-op (whole seconds) and soft + 1 == u64::MAX fits exactly. Only
        // the finite-native guard may reject it.
        let error = CpuLimits::prepare(Duration::from_secs(u64::MAX - 1))
            .expect_err("a hard backstop landing on RLIM_INFINITY must fail closed");
        assert!(
            error.contains("RLIM_INFINITY"),
            "wrong failure reason, expected sentinel rejection, got: {error}"
        );

        // Contrast: Duration::MAX fails EARLIER, in the hard-backstop
        // addition itself — a genuinely different guard.
        let error = CpuLimits::prepare(Duration::MAX)
            .expect_err("an unrepresentable hard backstop must fail closed");
        assert!(
            error.contains("overflows"),
            "wrong failure reason, expected arithmetic overflow, got: {error}"
        );
    }

    #[test]
    fn accepted_limits_never_hold_an_unlimited_native_field() {
        // The largest caller duration that can possibly be accepted must
        // still yield two strictly finite native fields.
        let limits =
            CpuLimits::prepare(Duration::from_secs(u64::MAX - 2)).expect("must be acceptable");
        assert_ne!(limits.native.rlim_cur, ffi::RLIM_INFINITY);
        assert_ne!(limits.native.rlim_max, ffi::RLIM_INFINITY);
        assert_eq!(limits.native.rlim_cur, u64::MAX - 2);
        assert_eq!(limits.native.rlim_max, u64::MAX - 1);
    }
}
