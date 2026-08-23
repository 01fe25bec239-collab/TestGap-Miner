"""Evaluation-owned Defects4J runtime smoke harness for the frozen EVAL-001
benchmark (`DEFECTS4J_MVP_V1`).

This module executes -- or objectively classifies -- the real Defects4J runtime
path for exactly the three predeclared smoke cases:

    D4J-GSON-001, D4J-LANG-001, D4J-MATH-001

Every case identity (project, bug id, revision ids, manifest version, required
Java major, required timezone, required Defects4J release) is resolved through
the canonical manifest loader in :mod:`evaluation.defects4j_manifest`; the only
benchmark fact fixed here is the smoke-set membership itself. The harness fails
closed when the manifest is invalid, when its checksum sidecar disagrees, or
when smoke membership differs from the authorized three IDs.

Only behavior documented for the real Defects4J 3.0.1 command-line interface is
used. There is deliberately NO ``version`` subcommand anywhere in this harness
(no such subcommand exists in Defects4J 3.0.1):

* The runtime is consumed through an injectable transport
  (:class:`RuntimeTransport`). Two modes exist and nothing else is invented:

  - host executable mode (default): logical commands map to the configured
    ``java``/``defects4j`` executables on PATH;
  - explicit Deployment container mode (opt-in): :class:`DockerContainerTransport`
    wraps the same logical commands into a ``docker run --rm --name <unique>``
    invocation of the Deployment-built runner image, mirroring the containment
    posture of the compose ``runner`` service (network none, read-only rootfs,
    init, cap-drop ALL, no-new-privileges, bounded pids/memory/cpu, tmpfs
    /tmp) and binding each case's disposable host workspace to the image's own
    ``/workspace``. No image is built, pulled or searched for here; the image
    reference is explicit configuration. Every container command carries a
    unique name so a timed-out outer CLI can be remediated deterministically
    with ``docker rm --force <name>`` without leaving orphan benchmark
    containers behind.
* Runtime operability is probed with ``defects4j info -p <project>`` against a
  project anchored in the frozen manifest. A successful answer proves the
  installed framework runs and its project metadata is readable.
* Exact release identity cannot be fabricated from command output: Defects4J
  3.0.1 exposes no runtime command that reports the framework release. It is
  therefore taken exclusively from an injectable Deployment-owned provenance
  reader on :class:`RuntimeBoundary`. When no reader is bound -- or when the
  reader fails, returns nothing, or attests a different release -- the run is
  classified ``DEFECTS4J_VERSION_MISMATCH`` and never passes. The recorded
  provenance label reflects the actual probe result: ``deployment.attested.v1``
  only when a concrete attestation value was obtained (even a wrong one,
  which Deployment objectively attested), and ``unavailable`` otherwise.
* Triggering-test metadata is read with the supported version-specific
  interface ``defects4j export -p tests.trigger -w <workspace>`` *after*
  checkout. Trigger names are never invented by this harness.
* ``defects4j test`` exit codes mean command/runtime success, not benchmark
  success: a successful command (exit 0) may legitimately report failing tests
  on a buggy revision. Classification separates the two:

  - timeout -> ``TIMEOUT``;
  - spawn/tool/runtime failure -> ``TEST_FAILURE``;
  - successful command AND every runtime-exported triggering test reproduced
    among the observed failures -> ``PASS``;
  - successful command otherwise -> ``BENCHMARK_CASE_FAILURE`` (including when
    trigger metadata is unavailable or its export output was truncated: an
    unverifiable case never passes);
  - a truncated bounded capture of ``test`` stdout likewise fails closed as
    ``BENCHMARK_CASE_FAILURE``: a partial failing-test list is never
    sufficient benchmark evidence, and no missing name is ever invented.

Boundaries respected by this module:

* Deployment owns Defects4J packaging/runtime images; Execution owns worker and
  runtime semantics. Evaluation owns only this smoke harness and its evidence.
  Nothing here modifies Deployment or Execution artifacts.
* All external processes run through an injectable :class:`CommandRunner`
  boundary. The production runner uses structured argv only, never a shell,
  an explicit working directory, an explicitly controlled child environment,
  a timeout on every command, and bounded stdout/stderr capture with explicit
  truncation metadata. No unbounded ``communicate``/``read`` exists anywhere.
* Each case runs in its own fresh disposable workspace created outside any Git
  working tree -- the main repository, this Evaluation worktree, and every
  other linked worktree are all excluded by scanning the workspace's ancestor
  chain for Git markers (a ``.git`` directory or a worktree ``.git`` file) --
  and cleaned up on both success and failure, with cleanup failures preserved
  in evidence without ever erasing the primary runtime outcome.
* ``TZ=America/Los_Angeles`` is forced into every benchmark child process; the
  parent/global timezone is never mutated.
* Infrastructure/runtime problems (missing tools, wrong versions, spawn errors,
  timeouts) stay distinct from benchmark behavior. A buggy benchmark revision
  whose triggering tests fail is the *expected* benchmark shape and never an
  infrastructure failure; conversely an infrastructure command failure is never
  reported as benchmark success.

Determinism: volatile data (disposable-workspace paths, wall-clock time) is
kept out of :meth:`CaseSmokeResult.to_semantic_dict` /
:meth:`SmokeRunResult.to_semantic_dict`. Identical mocked inputs produce
identical semantic results; raw command facts (full argv, bounded captured
output, workspace location) remain available through the ``*_evidence_dict``
accessors. Real and mocked executions are distinguishable via
``execution_mode`` and ``runner_kind``.

Standard library only; no new dependencies.
"""

from __future__ import annotations

import errno
import os
import platform
import re
import shutil
import subprocess
import tempfile
import threading
import uuid
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Callable, ClassVar, Mapping, Protocol, Sequence

from evaluation.defects4j_manifest import (
    REQUIRED_JAVA_MAJOR,
    REQUIRED_TIMEZONE,
    verify_file,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "benchmarks" / "defects4j" / "DEFECTS4J_MVP_V1.json"

# The ONLY benchmark information fixed in this harness: the exact smoke-set
# identity authorized for EVAL-001, plus which authorized case anchors the
# runtime operability probe (its project id is read from the frozen manifest,
# never hard-coded here). Everything else comes from the manifest.
SMOKE_CASE_IDS = ("D4J-GSON-001", "D4J-LANG-001", "D4J-MATH-001")
RUNTIME_PROBE_ANCHOR_CASE_ID = "D4J-LANG-001"

# Recorded for cross-checking against the canonical loader; the loader itself
# verifies the bytes against benchmarks/defects4j/DEFECTS4J_MVP_V1.sha256.
FROZEN_MANIFEST_SHA256 = (
    "4e77e8e62ec5d09619d2e340ed56f3420066d221c53afdb370b92ed834fcd0c3"
)
REQUIRED_DEFECTS4J_VERSION = "3.0.1"

DEFAULT_OUTPUT_LIMIT_BYTES = 20480

DEFAULT_PROBE_TIMEOUT_SECONDS = 60.0
DEFAULT_CHECKOUT_TIMEOUT_SECONDS = 600.0
DEFAULT_COMPILE_TIMEOUT_SECONDS = 900.0
DEFAULT_TEST_TIMEOUT_SECONDS = 1800.0
DEFAULT_TRIGGER_EXPORT_TIMEOUT_SECONDS = 120.0

# Remediation of a timed-out container command: the outer CLI is killed on
# timeout, but the containerized workload itself lives under the daemon, not
# under the CLI process tree. Every container command therefore runs with a
# unique --name so this single bounded follow-up can remove any orphan.
DEFAULT_ABORT_TIMEOUT_SECONDS = 30.0
ABORT_OUTPUT_LIMIT_BYTES = 4096

# Deployment-owned runner consumption facts. These mirror the repository's
# existing Deployment contracts verbatim and are consumed, never redefined:
# the image reference and /workspace layout come from compose.yml's `runner`
# service (image: testgap-defects4j-runner:3.0.1, volumes: runner-workspace:
# /workspace) built by Dockerfile.runner (DEFECTS4J_HOME=/opt/defects4j,
# WORKDIR /workspace); the containment flags mirror that same service
# definition (network_mode none, init, read_only, tmpfs /tmp:size=512m,
# cap_drop ALL, no-new-privileges, pids_limit 512, mem_limit 4g, cpus 2.0).
DEFAULT_DEFECTS4J_RUNNER_IMAGE = "testgap-defects4j-runner:3.0.1"
RUNNER_IMAGE_WORKSPACE = "/workspace"
RUNNER_IMAGE_FRAMEWORK_HOME = "/opt/defects4j"
RUNNER_CONTAINER_CONTAINMENT_ARGUMENTS: tuple[str, ...] = (
    "--init",
    "--network",
    "none",
    "--read-only",
    "--cap-drop",
    "ALL",
    "--security-opt",
    "no-new-privileges:true",
    "--pids-limit",
    "512",
    "--memory",
    "4g",
    "--cpus",
    "2.0",
    "--tmpfs",
    "/tmp:size=512m,mode=1777",
)

_READ_CHUNK_BYTES = 4096
_READER_JOIN_TIMEOUT_SECONDS = 5.0

# Defects4J 3.0.1 prints, on a successful `defects4j test`, exactly:
#     Failing tests: <N>
# followed by one failing test per line, each prefixed with two spaces, a dash
# and a space (`  - pkg.Class::method` or `  - pkg.Class`). Class-level entries
# carry no method suffix. The command exits zero whenever the test suite ran;
# a non-zero exit means the step itself failed.
_FAILING_TESTS_LINE = re.compile(r"^Failing tests:\s*(\d+)\s*$", re.MULTILINE)
_LEADING_ENTRY_DECORATION = re.compile(r"^(?:[-*\u2022]|\d+\s*[.)])\s*")
_TRAILING_REPEAT_COUNT = re.compile(r"\s*\(\d+\)\s*$")

# A normalized test reference is either `pkg.Class` or `pkg.Class::method`.
_TEST_REFERENCE_SHAPE = re.compile(r"\A[^:\s]+(?:::[^:\s]+)?\Z")

_JAVA_VERSION_TOKEN = re.compile(r'version\s+"([^"]+)"')

_CHILD_ENV_ALLOWLIST = ("HOME", "JAVA_HOME", "LANG", "LC_ALL", "LC_CTYPE", "PATH")

WORKSPACE_PREFIX = "testgap-d4j-smoke-"

TRIGGER_PROPERTY_NAME = "tests.trigger"

# Provenance labels recorded for the exact Defects4J release identity.
DEFECTS4J_IDENTITY_PROVENANCE_UNAVAILABLE = "unavailable"
DEFECTS4J_IDENTITY_PROVENANCE_DEPLOYMENT_ATTESTED = "deployment.attested.v1"


class SmokeHarnessError(RuntimeError):
    """Raised when the harness cannot proceed safely (fail closed)."""


class FailureClassification(str, Enum):
    """Objective, mutually distinct failure classes.

    Infrastructure/runtime problems are never merged with benchmark behavior:
    ``CHECKOUT_FAILURE``/``COMPILE_FAILURE``/``TEST_FAILURE`` mean the toolchain
    step itself failed; ``BENCHMARK_CASE_FAILURE`` means the case ran but the
    designed buggy-revision behavior was not reproduced (or could not be
    verified); ``TIMEOUT`` means a bounded command exceeded its deadline; the
    remaining environment classes describe the configured environment rather
    than any benchmark case.
    """

    PASS = "PASS"
    ENVIRONMENT_BLOCKED = "ENVIRONMENT_BLOCKED"
    RUNTIME_TOOL_MISSING = "RUNTIME_TOOL_MISSING"
    JAVA_VERSION_MISMATCH = "JAVA_VERSION_MISMATCH"
    JAVA_RUNTIME_NOT_OPERATIONAL = "JAVA_RUNTIME_NOT_OPERATIONAL"
    DEFECTS4J_RUNTIME_NOT_OPERATIONAL = "DEFECTS4J_RUNTIME_NOT_OPERATIONAL"
    DEFECTS4J_VERSION_MISMATCH = "DEFECTS4J_VERSION_MISMATCH"
    CHECKOUT_FAILURE = "CHECKOUT_FAILURE"
    COMPILE_FAILURE = "COMPILE_FAILURE"
    TEST_FAILURE = "TEST_FAILURE"
    BENCHMARK_CASE_FAILURE = "BENCHMARK_CASE_FAILURE"
    TIMEOUT = "TIMEOUT"
    HARNESS_FAILURE = "HARNESS_FAILURE"


ENVIRONMENT_CLASSES = frozenset(
    {
        FailureClassification.RUNTIME_TOOL_MISSING,
        FailureClassification.JAVA_VERSION_MISMATCH,
        FailureClassification.JAVA_RUNTIME_NOT_OPERATIONAL,
        FailureClassification.DEFECTS4J_RUNTIME_NOT_OPERATIONAL,
        FailureClassification.DEFECTS4J_VERSION_MISMATCH,
    }
)


@dataclass(frozen=True)
class StreamCapture:
    """Bounded capture of one output stream with explicit truncation metadata."""

    limit_bytes: int
    total_bytes: int
    text: str

    @property
    def truncated(self) -> bool:
        return self.total_bytes > self.limit_bytes


@dataclass(frozen=True)
class TimeoutAbortEvidence:
    """Outcome of the bounded abort issued after a timed-out container command.

    Recorded as objective evidence only: it never changes the primary
    classification (the command still counts as timed out) and never raises.
    """

    attempted: bool
    exit_code: int | None = None
    timed_out: bool = False
    spawn_error: str | None = None


@dataclass(frozen=True)
class CommandResult:
    """Raw, objective facts about one external command.

    ``program`` keeps only the executable basename so evidence never embeds
    host-specific absolute paths or usernames. Full argv is available to the
    evidence layer via the caller (the harness records it there); it is
    deliberately absent from the deterministic semantic layer because it
    contains disposable-workspace paths.

    ``timeout_abort`` carries the remediation outcome when a transport-backed
    command exceeded its deadline and an explicit abort invocation was issued;
    it is ``None`` for every non-timeout result and for host-mode commands.
    """

    program: str
    exit_code: int | None
    timed_out: bool
    timeout_seconds: float
    stdout: StreamCapture
    stderr: StreamCapture
    spawn_error: str | None = None
    argv: tuple[str, ...] = ()
    timeout_abort: TimeoutAbortEvidence | None = None


class CommandRunner(Protocol):
    """Injectable process-execution boundary.

    Implementations MUST: accept structured argv only (no shell string),
    honor ``cwd`` and ``env`` exactly as given, apply ``timeout_seconds`` to
    every command, bound both captured streams to their explicit limits, and
    report truncation honestly.
    """

    runner_kind: str

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str],
        timeout_seconds: float,
        stdout_limit_bytes: int,
        stderr_limit_bytes: int,
    ) -> CommandResult: ...


def _drain_bounded(stream: Any, limit: int, sink: list[tuple[bytes, int]]) -> None:
    """Read a pipe to EOF, retaining at most ``limit`` bytes.

    Reading continues (and discards) past the limit so the child can never
    deadlock on a full pipe while memory stays bounded; ``total`` preserves how
    many bytes the child produced so truncation is explicit metadata.
    """
    kept = bytearray()
    total = 0
    try:
        while True:
            chunk = stream.read(_READ_CHUNK_BYTES)
            if not chunk:
                break
            total += len(chunk)
            room = limit - len(kept)
            if room > 0:
                kept.extend(chunk[:room])
    finally:
        try:
            stream.close()
        except OSError:
            pass
    sink.append((bytes(kept[:limit]), total))


def _capture(raw: bytes, total: int, limit: int) -> StreamCapture:
    return StreamCapture(
        limit_bytes=int(limit),
        total_bytes=int(total),
        text=raw.decode("utf-8", errors="replace"),
    )


def _empty_capture(limit: int) -> StreamCapture:
    return StreamCapture(limit_bytes=int(limit), total_bytes=0, text="")


def _errno_label(error: OSError) -> str:
    code = getattr(error, "errno", None)
    if isinstance(code, int) and code in errno.errorcode:
        return errno.errorcode[code]
    return type(error).__name__


class SubprocessCommandRunner:
    """Production runner: bounded, timeout-enforced, shell-free subprocesses."""

    runner_kind = "subprocess.bounded.v1"

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str],
        timeout_seconds: float,
        stdout_limit_bytes: int,
        stderr_limit_bytes: int,
    ) -> CommandResult:
        argv_list = [os.fspath(argument) for argument in argv]
        program = os.path.basename(argv_list[0]) if argv_list else ""
        try:
            process = subprocess.Popen(
                argv_list,
                shell=False,
                cwd=os.fspath(cwd),
                env=dict(env),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                close_fds=True,
            )
        except OSError as error:
            return CommandResult(
                program=program,
                exit_code=None,
                timed_out=False,
                timeout_seconds=float(timeout_seconds),
                stdout=_empty_capture(stdout_limit_bytes),
                stderr=_empty_capture(stderr_limit_bytes),
                spawn_error=_errno_label(error),
                argv=tuple(argv_list),
            )

        stdout_sink: list[tuple[bytes, int]] = []
        stderr_sink: list[tuple[bytes, int]] = []
        stdout_reader = threading.Thread(
            target=_drain_bounded,
            args=(process.stdout, stdout_limit_bytes, stdout_sink),
            daemon=True,
        )
        stderr_reader = threading.Thread(
            target=_drain_bounded,
            args=(process.stderr, stderr_limit_bytes, stderr_sink),
            daemon=True,
        )
        stdout_reader.start()
        stderr_reader.start()

        timed_out = False
        try:
            process.wait(timeout=float(timeout_seconds))
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            try:
                process.wait(timeout=_READER_JOIN_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                pass
        stdout_reader.join(timeout=_READER_JOIN_TIMEOUT_SECONDS)
        stderr_reader.join(timeout=_READER_JOIN_TIMEOUT_SECONDS)

        stdout_raw, stdout_total = (
            stdout_sink[0] if stdout_sink else (b"", 0)
        )
        stderr_raw, stderr_total = (
            stderr_sink[0] if stderr_sink else (b"", 0)
        )
        return CommandResult(
            program=program,
            exit_code=int(process.returncode)
            if process.returncode is not None
            else None,
            timed_out=timed_out,
            timeout_seconds=float(timeout_seconds),
            stdout=_capture(stdout_raw, stdout_total, stdout_limit_bytes),
            stderr=_capture(stderr_raw, stderr_total, stderr_limit_bytes),
            argv=tuple(argv_list),
        )


def build_child_environment(
    base: Mapping[str, str] | None = None,
    *,
    timezone: str = REQUIRED_TIMEZONE,
) -> dict[str, str]:
    """Explicitly controlled child environment.

    Only allowlisted variable names pass through from ``base`` (the parent
    environment by default); everything else -- including any secret-bearing
    variables -- is dropped. ``TZ`` is always forced to the benchmark timezone;
    the parent/global environment is never modified.
    """
    source = os.environ if base is None else base
    child = {
        key: value
        for key, value in source.items()
        if key in _CHILD_ENV_ALLOWLIST and isinstance(value, str)
    }
    child.setdefault("PATH", os.defpath)
    child["TZ"] = timezone
    return dict(sorted(child.items()))


@dataclass(frozen=True)
class RuntimeCommand:
    """One logical runtime-tool invocation, before transport wrapping.

    ``tool`` is ``"java"``, ``"defects4j"``, or ``"container-inspection"``.
    For the two benchmark tools, ``arguments`` are the complete logical
    arguments WITHOUT the binary name -- each transport supplies its own
    configured executable (host path in host mode, the in-image binary in
    container mode). ``workspace``, when set (``defects4j`` only), makes the
    transport map that HOST workspace into the runtime and append the tool's
    standard working-directory flag with the runtime-visible path (host path
    for host mode, mapped container path for container mode).
    A ``container-inspection`` command carries the complete read-only inner
    argv as-is and is understood by :class:`DockerContainerTransport` only.
    """

    tool: str
    arguments: tuple[str, ...]
    workspace: Path | None = None


@dataclass(frozen=True)
class TransportInvocation:
    """Structured argv for one execution plus its optional timeout abort.

    ``argv`` is the full structured outer command (never a shell string).
    ``abort_argv``, when present, deterministically removes the exact resource
    launched by ``argv`` and is issued by the harness only after the primary
    command timed out.
    """

    argv: tuple[str, ...]
    abort_argv: tuple[str, ...] | None = None


class RuntimeTransport(Protocol):
    """How logical runtime commands become concrete structured argv.

    Implementations MUST return fully structured argv (no shell), keep the
    child environment under the harness's control, and map a command's HOST
    workspace into the runtime exactly once per invocation.
    """

    transport_kind: str

    def prepare(self, command: RuntimeCommand) -> TransportInvocation: ...


@dataclass(frozen=True)
class HostExecutableTransport:
    """Direct host-executable mode (the pre-correction behavior, preserved)."""

    java_executable: str = "java"
    defects4j_executable: str = "defects4j"
    transport_kind: ClassVar[str] = "host.executable.v1"

    def prepare(self, command: RuntimeCommand) -> TransportInvocation:
        if command.tool == "java":
            if command.workspace is not None:
                raise SmokeHarnessError(
                    "the java tool never carries a benchmark workspace"
                )
            executable = self.java_executable
        elif command.tool == "defects4j":
            executable = self.defects4j_executable
        else:
            raise SmokeHarnessError(f"unsupported runtime tool {command.tool!r}")
        arguments = list(command.arguments)
        if command.workspace is not None:
            arguments += ["-w", os.fspath(command.workspace)]
        return TransportInvocation(argv=(executable, *arguments))


@dataclass(frozen=True)
class DockerContainerTransport:
    """Explicit opt-in consumption of the Deployment-owned runner image.

    Each invocation runs ``docker run --rm --name <unique>`` on the explicitly
    configured Deployment-built image, mirroring the containment posture of the
    compose ``runner`` service. A per-case HOST workspace is bind-mounted onto
    the image's own writable ``/workspace`` and inner Defects4J commands refer
    to that container path only. Nothing is built, pulled or discovered here.

    The unique ``--name`` makes timeout remediation deterministic:
    ``abort_argv`` removes exactly this ephemeral container, so killing the
    outer CLI can never silently orphan long-running benchmark containers.
    """

    image: str
    docker_executable: str = "docker"
    container_workspace: str = RUNNER_IMAGE_WORKSPACE
    transport_kind: ClassVar[str] = "docker.container.v1"

    def prepare(self, command: RuntimeCommand) -> TransportInvocation:
        if command.workspace is not None and command.tool != "defects4j":
            raise SmokeHarnessError(
                "only defects4j commands carry a mappable benchmark workspace"
            )
        name = f"{WORKSPACE_PREFIX}{uuid.uuid4().hex}"
        prefix = [
            self.docker_executable,
            "run",
            "--rm",
            "--name",
            name,
            *RUNNER_CONTAINER_CONTAINMENT_ARGUMENTS,
            "--env",
            f"TZ={REQUIRED_TIMEZONE}",
        ]
        if command.tool == "container-inspection":
            inner = list(command.arguments)
        elif command.tool in ("java", "defects4j"):
            # The runner image exposes both tools on its own PATH.
            inner = [command.tool, *command.arguments]
        else:
            raise SmokeHarnessError(f"unsupported runtime tool {command.tool!r}")
        if command.workspace is not None:
            prefix += [
                "--volume",
                f"{os.fspath(command.workspace)}:{self.container_workspace}",
                "--workdir",
                self.container_workspace,
            ]
            inner += ["-w", self.container_workspace]
        argv = (*prefix, self.image, *inner)
        abort_argv = (self.docker_executable, "rm", "--force", name)
        return TransportInvocation(argv=argv, abort_argv=abort_argv)

    def prepare_container_command(
        self, inner_argv: Sequence[str], *, workspace: Path | None = None
    ) -> TransportInvocation:
        """Wrap an arbitrary read-only inspection command in the same runtime."""
        return self.prepare(
            RuntimeCommand(
                tool="container-inspection",
                arguments=tuple(inner_argv),
                workspace=workspace,
            )
        )


def execute_runtime_command(
    runner: CommandRunner,
    invocation: TransportInvocation,
    *,
    cwd: Path,
    env: Mapping[str, str],
    timeout_seconds: float,
    stdout_limit_bytes: int,
    stderr_limit_bytes: int,
) -> CommandResult:
    """Run one transport invocation; abort the named container on timeout.

    The primary result and classification are decided exactly as before; when
    the primary command timed out and the transport provides an abort command,
    it is executed once with its own finite timeout and bounded capture, and
    its outcome is recorded as evidence without ever masking the TIMEOUT
    verdict or raising into the harness.
    """
    result = runner.run(
        invocation.argv,
        cwd=cwd,
        env=env,
        timeout_seconds=timeout_seconds,
        stdout_limit_bytes=stdout_limit_bytes,
        stderr_limit_bytes=stderr_limit_bytes,
    )
    if not result.timed_out or invocation.abort_argv is None:
        return result
    abort = runner.run(
        invocation.abort_argv,
        cwd=Path(tempfile.gettempdir()),
        env=env,
        timeout_seconds=DEFAULT_ABORT_TIMEOUT_SECONDS,
        stdout_limit_bytes=ABORT_OUTPUT_LIMIT_BYTES,
        stderr_limit_bytes=ABORT_OUTPUT_LIMIT_BYTES,
    )
    return replace(
        result,
        timeout_abort=TimeoutAbortEvidence(
            attempted=True,
            exit_code=abort.exit_code,
            timed_out=abort.timed_out,
            spawn_error=abort.spawn_error,
        ),
    )


@dataclass(frozen=True)
class ToolProbe:
    """Outcome of probing one external runtime fact.

    ``probe_command`` is ``None`` for probes that are not backed by a single
    external command (for example the Deployment-owned release-identity
    attestation).
    """

    tool: str
    observed_version: str | None
    observed_major: int | None
    classification: FailureClassification
    detail: str
    probe_command: CommandResult | None = None


def _java_major(version_token: str) -> int | None:
    parts = version_token.split(".")
    if not parts or not parts[0].isdigit():
        return None
    if parts[0] == "1" and len(parts) > 1 and parts[1].isdigit():
        return int(parts[1])
    return int(parts[0])


def _combined_text(result: CommandResult) -> str:
    return result.stdout.text + "\n" + result.stderr.text


def probe_java(
    runner: CommandRunner,
    *,
    executable: str = "java",
    env: Mapping[str, str],
    timeout_seconds: float = DEFAULT_PROBE_TIMEOUT_SECONDS,
    output_limit_bytes: int = DEFAULT_OUTPUT_LIMIT_BYTES,
    argv: Sequence[str] | None = None,
) -> ToolProbe:
    """Probe the actual configured Java runtime (never assume it).

    ``argv`` overrides the default ``[executable, "-version"]`` with a
    transport-built invocation (for example the same logical probe executed
    inside the Deployment runner container); classification is identical.
    """
    resolved_argv = (
        tuple(os.fspath(argument) for argument in argv)
        if argv is not None
        else (executable, "-version")
    )
    result = runner.run(
        resolved_argv,
        cwd=Path(tempfile.gettempdir()),
        env=env,
        timeout_seconds=timeout_seconds,
        stdout_limit_bytes=output_limit_bytes,
        stderr_limit_bytes=output_limit_bytes,
    )
    if result.spawn_error is not None:
        return ToolProbe(
            tool="java",
            observed_version=None,
            observed_major=None,
            classification=FailureClassification.RUNTIME_TOOL_MISSING,
            detail=f"java -version could not start ({result.spawn_error})",
            probe_command=result,
        )
    if result.timed_out:
        return ToolProbe(
            tool="java",
            observed_version=None,
            observed_major=None,
            classification=FailureClassification.JAVA_RUNTIME_NOT_OPERATIONAL,
            detail=(
                f"java -version exceeded {timeout_seconds:g}s and was "
                "terminated before completing; captured output cannot "
                "establish an operational Java runtime"
            ),
            probe_command=result,
        )
    if result.exit_code != 0:
        return ToolProbe(
            tool="java",
            observed_version=None,
            observed_major=None,
            classification=FailureClassification.JAVA_RUNTIME_NOT_OPERATIONAL,
            detail=(
                f"java -version exited {result.exit_code}; the Java runtime "
                "probe did not complete successfully, so no version parsed "
                "from its output may be accepted"
            ),
            probe_command=result,
        )
    match = _JAVA_VERSION_TOKEN.search(_combined_text(result))
    if match is None:
        return ToolProbe(
            tool="java",
            observed_version=None,
            observed_major=None,
            classification=FailureClassification.JAVA_VERSION_MISMATCH,
            detail="java -version produced no parsable version string",
            probe_command=result,
        )
    observed = match.group(1)
    major = _java_major(observed)
    if major != REQUIRED_JAVA_MAJOR:
        return ToolProbe(
            tool="java",
            observed_version=observed,
            observed_major=major,
            classification=FailureClassification.JAVA_VERSION_MISMATCH,
            detail=f"required Java major {REQUIRED_JAVA_MAJOR}, observed {observed!r}",
            probe_command=result,
        )
    return ToolProbe(
        tool="java",
        observed_version=observed,
        observed_major=major,
        classification=FailureClassification.PASS,
        detail=f"Java major {major} matches requirement",
        probe_command=result,
    )


def probe_defects4j_runtime(
    runner: CommandRunner,
    *,
    executable: str = "defects4j",
    probe_project: str,
    env: Mapping[str, str],
    timeout_seconds: float = DEFAULT_PROBE_TIMEOUT_SECONDS,
    output_limit_bytes: int = DEFAULT_OUTPUT_LIMIT_BYTES,
    argv: Sequence[str] | None = None,
) -> ToolProbe:
    """Probe runtime operability with the supported install probe.

    Runs ``<executable> info -p <probe_project>`` -- a documented Defects4J 3.0.1
    subcommand that answers only when the framework is installed, runnable, and
    its project metadata is intact. ``argv`` overrides the default host
    invocation with a transport-built one (for example the same logical probe
    executed inside the Deployment runner container). This proves operability
    only; it does NOT report the framework release (no such runtime interface
    exists in 3.0.1), so exact-version identity is resolved separately through
    :func:`resolve_defects4j_release_identity`.
    """
    resolved_argv = (
        tuple(os.fspath(argument) for argument in argv)
        if argv is not None
        else (executable, "info", "-p", probe_project)
    )
    result = runner.run(
        resolved_argv,
        cwd=Path(tempfile.gettempdir()),
        env=env,
        timeout_seconds=timeout_seconds,
        stdout_limit_bytes=output_limit_bytes,
        stderr_limit_bytes=output_limit_bytes,
    )
    if result.spawn_error is not None:
        return ToolProbe(
            tool="defects4j",
            observed_version=None,
            observed_major=None,
            classification=FailureClassification.RUNTIME_TOOL_MISSING,
            detail=(
                f"defects4j info -p {probe_project} could not start "
                f"({result.spawn_error})"
            ),
            probe_command=result,
        )
    if result.timed_out:
        return ToolProbe(
            tool="defects4j",
            observed_version=None,
            observed_major=None,
            classification=FailureClassification.TIMEOUT,
            detail=(
                f"defects4j info -p {probe_project} exceeded "
                f"{timeout_seconds:g}s"
            ),
            probe_command=result,
        )
    if result.exit_code != 0:
        return ToolProbe(
            tool="defects4j",
            observed_version=None,
            observed_major=None,
            classification=FailureClassification.DEFECTS4J_RUNTIME_NOT_OPERATIONAL,
            detail=(
                f"defects4j info -p {probe_project} exited {result.exit_code}; "
                "the installed runtime did not answer the supported install probe"
            ),
            probe_command=result,
        )
    if not result.stdout.text.strip():
        return ToolProbe(
            tool="defects4j",
            observed_version=None,
            observed_major=None,
            classification=FailureClassification.DEFECTS4J_RUNTIME_NOT_OPERATIONAL,
            detail=(
                f"defects4j info -p {probe_project} returned no project "
                "information"
            ),
            probe_command=result,
        )
    return ToolProbe(
        tool="defects4j",
        observed_version=None,
        observed_major=None,
        classification=FailureClassification.PASS,
        detail=(
            f"defects4j info -p {probe_project} succeeded; runtime is installed "
            "and operational (release identity is verified separately)"
        ),
        probe_command=result,
    )


def resolve_defects4j_release_identity(
    *,
    required_version: str,
    provenance_reader: Callable[[], str | None] | None,
) -> ToolProbe:
    """Resolve the exact Defects4J release identity without inventing output.

    Defects4J 3.0.1 provides no runtime command that reports the framework
    release, so identity must come from objectively available Deployment-owned
    provenance: the injectable ``provenance_reader`` bound onto
    :class:`RuntimeBoundary`. Anything other than an exact match with
    ``required_version`` -- including a missing reader, a reader failure, or an
    empty/unset attestation -- is classified ``DEFECTS4J_VERSION_MISMATCH`` so
    the run can never pass on an unverified identity.
    """
    if provenance_reader is None:
        return ToolProbe(
            tool="defects4j.release",
            observed_version=None,
            observed_major=None,
            classification=FailureClassification.DEFECTS4J_VERSION_MISMATCH,
            detail=(
                f"exact Defects4J {required_version} identity could not be "
                "established: no Deployment-owned provenance source is bound "
                "(the runtime itself exposes no release-reporting command); "
                "refusing to pass"
            ),
        )
    try:
        attested = provenance_reader()
    except Exception as error:  # noqa: BLE001 - injected readers may raise anything
        return ToolProbe(
            tool="defects4j.release",
            observed_version=None,
            observed_major=None,
            classification=FailureClassification.DEFECTS4J_VERSION_MISMATCH,
            detail=(
                f"exact Defects4J {required_version} identity could not be "
                f"established: Deployment-owned provenance reader raised "
                f"{type(error).__name__}: {error}"
            ),
        )
    if attested is None:
        return ToolProbe(
            tool="defects4j.release",
            observed_version=None,
            observed_major=None,
            classification=FailureClassification.DEFECTS4J_VERSION_MISMATCH,
            detail=(
                f"exact Defects4J {required_version} identity could not be "
                "established: Deployment-owned provenance attested no release"
            ),
        )
    observed = str(attested).strip()
    if not observed:
        return ToolProbe(
            tool="defects4j.release",
            observed_version=None,
            observed_major=None,
            classification=FailureClassification.DEFECTS4J_VERSION_MISMATCH,
            detail=(
                f"exact Defects4J {required_version} identity could not be "
                "established: Deployment-owned provenance attestation is empty"
            ),
        )
    if observed != required_version:
        return ToolProbe(
            tool="defects4j.release",
            observed_version=observed,
            observed_major=None,
            classification=FailureClassification.DEFECTS4J_VERSION_MISMATCH,
            detail=(
                f"required Defects4J {required_version}, Deployment-owned "
                f"provenance attests {observed!r}"
            ),
        )
    return ToolProbe(
        tool="defects4j.release",
        observed_version=observed,
        observed_major=None,
        classification=FailureClassification.PASS,
        detail=(
            f"Defects4J {observed} attested by Deployment-owned provenance"
        ),
    )


def deployment_image_release_reader(
    *,
    runner: CommandRunner,
    transport: RuntimeTransport,
    env: Mapping[str, str],
    timeout_seconds: float = DEFAULT_PROBE_TIMEOUT_SECONDS,
    output_limit_bytes: int = DEFAULT_OUTPUT_LIMIT_BYTES,
) -> Callable[[], str | None]:
    """Objective release attestation from the Deployment-built runner image.

    Source: the Defects4J framework clone baked into the Deployment runner
    image at ``RUNNER_IMAGE_FRAMEWORK_HOME``. Deployment's own Dockerfile pins
    the framework tag and verifies its exact commit at build time, so the
    read-only git metadata inside the already-built image is an objective,
    Deployment-owned provenance source -- no new contract is created here and
    nothing is written anywhere (the per-invocation ``safe.directory`` override
    is process-local; no global git configuration is touched).

    The reader returns the attested release string (upstream tags releases as
    ``v<version>``; the conventional leading ``v`` is normalized away), or
    ``None`` whenever anything is unavailable or ambiguous -- every such case
    keeps the existing exact-version gate fail-closed. Only usable with
    :class:`DockerContainerTransport`; any other transport is rejected eagerly.
    """
    if not isinstance(transport, DockerContainerTransport):
        raise SmokeHarnessError(
            "deployment_image_release_reader requires the Deployment container "
            f"transport, got {transport.transport_kind!r}"
        )
    framework_home = RUNNER_IMAGE_FRAMEWORK_HOME

    def reader() -> str | None:
        invocation = transport.prepare_container_command(
            (
                "git",
                "-c",
                f"safe.directory={framework_home}",
                "-C",
                framework_home,
                "tag",
                "--points-at",
                "HEAD",
            )
        )
        result = execute_runtime_command(
            runner,
            invocation,
            cwd=Path(tempfile.gettempdir()),
            env=env,
            timeout_seconds=timeout_seconds,
            stdout_limit_bytes=output_limit_bytes,
            stderr_limit_bytes=output_limit_bytes,
        )
        if (
            result.spawn_error is not None
            or result.timed_out
            or result.exit_code != 0
        ):
            return None
        tags = [line.strip() for line in result.stdout.text.splitlines()]
        tags = [tag for tag in tags if tag]
        if len(tags) != 1:
            # Zero or multiple tags at HEAD: identity is ambiguous, never guessed.
            return None
        tag = tags[0]
        if tag.startswith("v"):
            tag = tag[1:]
        return tag or None

    return reader


def _identity_provenance_label(identity_probe: ToolProbe) -> str:
    """Record provenance strictly according to what was actually obtained.

    ``deployment.attested.v1`` is claimed only when a concrete attestation
    value was read from the Deployment-owned source (even if that attested
    value disagrees with the required release -- the version gate still fails,
    while the fact that Deployment attested *that* value stays objective). A
    missing reader, a reader failure, or an empty/unset answer is recorded as
    ``unavailable``; the evidence never says a release was attested when no
    attestation value was obtained.
    """
    if identity_probe.observed_version is not None:
        return DEFECTS4J_IDENTITY_PROVENANCE_DEPLOYMENT_ATTESTED
    return DEFECTS4J_IDENTITY_PROVENANCE_UNAVAILABLE


@dataclass(frozen=True)
class CleanupEvidence:
    """Disposable-workspace cleanup outcome; never masks a primary failure."""

    attempted: bool
    removed: bool
    error: str | None


@dataclass(frozen=True)
class TriggerProbe:
    """Triggering-test metadata availability; never fabricated."""

    attempted: bool
    available: bool
    observed_trigger_tests: tuple[str, ...]
    detail: str


@dataclass(frozen=True)
class EnvironmentFacts:
    """Non-sensitive runtime/environment identity for one smoke run."""

    os_name: str
    machine: str
    runner_kind: str
    execution_mode: str
    runtime_transport: str
    required_java_major: int
    observed_java_version: str | None
    observed_java_major: int | None
    required_defects4j_version: str
    observed_defects4j_version: str | None
    defects4j_identity_provenance: str
    timezone: str


@dataclass(frozen=True)
class CaseSmokeResult:
    """Structured smoke evidence for exactly one benchmark case."""

    manifest_version: str
    case_id: str
    project: str
    bug_id: int
    buggy_version_id: str
    fixed_version_id: str
    environment: EnvironmentFacts
    checkout_command: CommandResult | None
    compile_command: CommandResult | None
    test_command: CommandResult | None
    trigger_command: CommandResult | None
    trigger_probe: TriggerProbe
    manifest_trigger_status: str
    failing_tests_declared_count: int | None
    failing_tests_observed: tuple[str, ...]
    failure_class: FailureClassification
    failure_detail: str
    cleanup: CleanupEvidence
    workspace_path: Path | None

    @property
    def passed(self) -> bool:
        return self.failure_class is FailureClassification.PASS

    @property
    def environment_blocked(self) -> bool:
        return self.failure_class in ENVIRONMENT_CLASSES

    @staticmethod
    def _step_facts(command: CommandResult | None) -> dict[str, Any] | None:
        if command is None:
            return None
        abort = command.timeout_abort
        return {
            "program": command.program,
            "exit_code": command.exit_code,
            "timed_out": command.timed_out,
            "timeout_seconds": command.timeout_seconds,
            "spawn_error": command.spawn_error,
            "stdout_truncated": command.stdout.truncated,
            "stderr_truncated": command.stderr.truncated,
            "stdout_total_bytes": command.stdout.total_bytes,
            "stderr_total_bytes": command.stderr.total_bytes,
            "stdout_limit_bytes": command.stdout.limit_bytes,
            "stderr_limit_bytes": command.stderr.limit_bytes,
            "timeout_abort": None
            if abort is None
            else {
                "attempted": abort.attempted,
                "exit_code": abort.exit_code,
                "timed_out": abort.timed_out,
                "spawn_error": abort.spawn_error,
            },
        }

    def to_semantic_dict(self) -> dict[str, Any]:
        """Deterministic semantics: no volatile paths, timestamps or raw text."""
        return {
            "manifest_version": self.manifest_version,
            "case_id": self.case_id,
            "project": self.project,
            "bug_id": self.bug_id,
            "buggy_version_id": self.buggy_version_id,
            "fixed_version_id": self.fixed_version_id,
            "environment": _environment_semantic_dict(self.environment),
            "checkout": self._step_facts(self.checkout_command),
            "compile": self._step_facts(self.compile_command),
            "test": self._step_facts(self.test_command),
            "trigger_export": self._step_facts(self.trigger_command),
            "trigger_probe": {
                "attempted": self.trigger_probe.attempted,
                "available": self.trigger_probe.available,
                "observed_trigger_tests": list(self.trigger_probe.observed_trigger_tests),
                "detail": self.trigger_probe.detail,
            },
            "manifest_trigger_status": self.manifest_trigger_status,
            "failing_tests_declared_count": self.failing_tests_declared_count,
            "failing_tests_observed": list(self.failing_tests_observed),
            "failure_class": self.failure_class.value,
            "failure_detail": self.failure_detail,
            "cleanup": {
                "attempted": self.cleanup.attempted,
                "removed": self.cleanup.removed,
                "error": self.cleanup.error,
            },
        }

    def to_evidence_dict(self) -> dict[str, Any]:
        """Full evidence: adds bounded raw output, argv and workspace location."""
        evidence = self.to_semantic_dict()
        evidence["workspace_path"] = (
            str(self.workspace_path) if self.workspace_path is not None else None
        )
        for key, command in (
            ("checkout", self.checkout_command),
            ("compile", self.compile_command),
            ("test", self.test_command),
            ("trigger_export", self.trigger_command),
        ):
            if command is None:
                continue
            evidence[key]["argv"] = list(command.argv)
            evidence[key]["stdout_text"] = command.stdout.text
            evidence[key]["stderr_text"] = command.stderr.text
        return evidence


def _environment_semantic_dict(environment: EnvironmentFacts) -> dict[str, Any]:
    return {
        "os_name": environment.os_name,
        "machine": environment.machine,
        "runner_kind": environment.runner_kind,
        "execution_mode": environment.execution_mode,
        "runtime_transport": environment.runtime_transport,
        "required_java_major": environment.required_java_major,
        "observed_java_version": environment.observed_java_version,
        "observed_java_major": environment.observed_java_major,
        "required_defects4j_version": environment.required_defects4j_version,
        "observed_defects4j_version": environment.observed_defects4j_version,
        "defects4j_identity_provenance": environment.defects4j_identity_provenance,
        "timezone": environment.timezone,
    }


@dataclass(frozen=True)
class SmokeRunResult:
    """Structured smoke evidence for one complete smoke run."""

    manifest_version: str
    smoke_case_ids: tuple[str, ...]
    status: str
    environment: EnvironmentFacts
    cases: tuple[CaseSmokeResult, ...]

    @property
    def passed(self) -> bool:
        return self.status == "PASS"

    def to_semantic_dict(self) -> dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "smoke_case_ids": list(self.smoke_case_ids),
            "status": self.status,
            "environment": _environment_semantic_dict(self.environment),
            "cases": [case.to_semantic_dict() for case in self.cases],
        }

    def to_evidence_dict(self) -> dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "smoke_case_ids": list(self.smoke_case_ids),
            "status": self.status,
            "environment": _environment_semantic_dict(self.environment),
            "cases": [case.to_evidence_dict() for case in self.cases],
        }


@dataclass(frozen=True)
class RuntimeBoundary:
    """Configured runtime boundary for one smoke run.

    Defects4J is consumed through ``defects4j_transport``. The default of
    ``None`` preserves direct host-executable mode via ``defects4j_executable``
    (and ``java_executable`` for the Java probe). Setting an explicit
    :class:`DockerContainerTransport` opts into the Deployment-owned runner
    image: the same logical commands are executed inside ephemeral containers
    built by Deployment, each case's disposable host workspace is mapped to the
    image's ``/workspace``, and no host ``defects4j`` binary is required. No
    image is ever built, pulled, or silently discovered here.

    ``defects4j_release_reader`` is the Deployment-owned provenance hook for
    the exact release identity of the configured runtime (for example a reader
    built with :func:`deployment_image_release_reader` over the container
    transport). It must return the attested release string, or ``None`` when
    unavailable. The default of ``None`` intentionally blocks every pass: the
    harness never fabricates version identity, and Defects4J 3.0.1 exposes no
    runtime command that reports it.

    ``defects4j_info_project`` optionally overrides which project id the
    operability probe targets; by default the project of the probe-anchor case
    is read from the frozen manifest.
    """

    java_executable: str = "java"
    defects4j_executable: str = "defects4j"
    defects4j_transport: RuntimeTransport | None = None
    defects4j_release_reader: Callable[[], str | None] | None = None
    defects4j_info_project: str | None = None
    child_env_base: Mapping[str, str] | None = None
    temp_root: Path | None = None
    output_limit_bytes: int = DEFAULT_OUTPUT_LIMIT_BYTES
    probe_timeout_seconds: float = DEFAULT_PROBE_TIMEOUT_SECONDS
    checkout_timeout_seconds: float = DEFAULT_CHECKOUT_TIMEOUT_SECONDS
    compile_timeout_seconds: float = DEFAULT_COMPILE_TIMEOUT_SECONDS
    test_timeout_seconds: float = DEFAULT_TEST_TIMEOUT_SECONDS
    trigger_export_timeout_seconds: float = DEFAULT_TRIGGER_EXPORT_TIMEOUT_SECONDS
    remove_workspace: Callable[[Path], None] | None = None


def load_smoke_cases(
    manifest_path: Path | str = MANIFEST_PATH,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    """Resolve the authorized smoke set through the canonical manifest loader.

    Fails closed unless the manifest validates (structure, canonical form and
    recorded SHA-256), its smoke membership is exactly the three authorized IDs,
    and every ID resolves to exactly one case.
    """
    path = Path(manifest_path)
    manifest = verify_file(path)
    release = manifest.get("defects4j_release")
    if release != REQUIRED_DEFECTS4J_VERSION:
        raise SmokeHarnessError(
            f"manifest defects4j_release {release!r} does not match the "
            f"authorized {REQUIRED_DEFECTS4J_VERSION!r}"
        )
    membership = manifest.get("smoke_case_ids")
    if sorted(membership) != sorted(SMOKE_CASE_IDS):
        raise SmokeHarnessError(
            "smoke membership differs from the authorized smoke set "
            f"{list(SMOKE_CASE_IDS)}: {membership!r}"
        )
    resolved: list[dict[str, Any]] = []
    for case_id in SMOKE_CASE_IDS:
        matches = [
            case
            for case in manifest["cases"]
            if case.get("benchmark_case_id") == case_id
        ]
        if len(matches) != 1:
            raise SmokeHarnessError(
                f"case {case_id!r} resolves ambiguously ({len(matches)} matches)"
            )
        resolved.append(matches[0])
    return manifest, tuple(resolved)


def _resolve_info_probe_project(
    boundary: RuntimeBoundary, cases: tuple[dict[str, Any], ...]
) -> str:
    """Pick the operability-probe project without hard-coded benchmark facts."""
    override = boundary.defects4j_info_project
    if override:
        return override
    for case in cases:
        if case.get("benchmark_case_id") == RUNTIME_PROBE_ANCHOR_CASE_ID:
            project = case.get("project")
            if isinstance(project, str) and project.strip():
                return project.strip()
    raise SmokeHarnessError(
        "cannot resolve a project for the runtime operability probe: "
        f"anchor case {RUNTIME_PROBE_ANCHOR_CASE_ID!r} is missing from the manifest"
    )


def _ensure_outside_repository(workspace: Path) -> None:
    """Fail closed for any workspace inside a Git working tree.

    Checkout must never target the main repository, this Evaluation worktree,
    or any other linked A2-style worktree. Both containment under this
    worktree's root and the presence of a Git working-tree marker (a ``.git``
    directory or a worktree ``.git`` file) anywhere from the workspace up to
    the filesystem root are rejected. Only plain filesystem reads are used --
    no mutation-heavy Git commands.
    """
    repo_root = REPO_ROOT.resolve()
    resolved = workspace.resolve()
    if resolved == repo_root or repo_root in resolved.parents:
        shutil.rmtree(resolved, ignore_errors=True)
        raise SmokeHarnessError(
            f"refusing disposable workspace inside the repository: {resolved}"
        )
    for ancestor in (resolved, *resolved.parents):
        marker = ancestor / ".git"
        if marker.is_dir() or marker.is_file():
            shutil.rmtree(resolved, ignore_errors=True)
            raise SmokeHarnessError(
                "refusing disposable workspace inside a Git working tree: "
                f"{resolved} (Git marker found at {ancestor})"
            )


def _create_disposable_workspace(case_id: str, temp_root: Path | None) -> Path:
    directory = Path(
        tempfile.mkdtemp(
            prefix=f"{WORKSPACE_PREFIX}{case_id.lower()}-",
            dir=os.fspath(temp_root) if temp_root is not None else None,
        )
    )
    _ensure_outside_repository(directory)
    return directory.resolve()


def _attempt_cleanup(
    workspace: Path | None, remover: Callable[[Path], None]
) -> CleanupEvidence:
    if workspace is None:
        return CleanupEvidence(attempted=False, removed=False, error=None)
    try:
        remover(workspace)
    except OSError as error:
        return CleanupEvidence(
            attempted=True, removed=False, error=_errno_label(error)
        )
    except Exception as error:  # noqa: BLE001 - injected removers may raise anything
        return CleanupEvidence(attempted=True, removed=False, error=type(error).__name__)
    return CleanupEvidence(attempted=True, removed=True, error=None)


def normalize_test_reference(raw: str) -> str:
    """Normalize one printed test reference to ``pkg.Class`` / ``pkg.Class::m``.

    Strips surrounding whitespace, leading bullet/ordinal decorations
    (``- ``, ``* ``, ``12)``, ``12.``) and trailing repetition counts such as
    ``(1)``, so decorated listings still compare equal to plain references.
    """
    text = raw.strip()
    text = _LEADING_ENTRY_DECORATION.sub("", text)
    text = _TRAILING_REPEAT_COUNT.sub("", text)
    return text.strip()


def _is_test_reference(text: str) -> bool:
    if not text or any(character.isspace() for character in text):
        return False
    if not _TEST_REFERENCE_SHAPE.fullmatch(text):
        return False
    class_part = text.split("::", 1)[0]
    return "." in class_part


def _parse_failing_tests(stdout_text: str) -> tuple[int | None, tuple[str, ...]]:
    """Parse a real ``Failing tests: N`` summary into normalized names.

    Accepts the native format (entries like ``  - pkg.Class::method``, one per
    line) plus tolerated decorations; stops at the first blank or unshaped
    line so unrelated output is never mistaken for a test name.
    """
    match = _FAILING_TESTS_LINE.search(stdout_text)
    if match is None:
        return None, ()
    names: list[str] = []
    for line in stdout_text[match.end() :].splitlines():
        if not line.strip():
            if names:
                break
            continue
        candidate = normalize_test_reference(line)
        if not candidate or not _is_test_reference(candidate):
            break
        names.append(candidate)
    return int(match.group(1)), tuple(names)


def _parse_trigger_tests(stdout_text: str) -> tuple[str, ...]:
    """Normalize real ``tests.trigger`` export output.

    The Defects4J 3.0.1 export writes one reference per line (its separator
    characters are replaced by newlines); splitting also tolerates commas and
    semicolons so raw CSV-shaped values normalize identically. Names are never
    invented: only well-shaped references survive.
    """
    tokens: list[str] = []
    for chunk in re.split(r"[,;\r\n]+", stdout_text):
        candidate = normalize_test_reference(chunk)
        if candidate and _is_test_reference(candidate):
            tokens.append(candidate)
    return tuple(tokens)


def _classify_benchmark_outcome(
    observed_failures: tuple[str, ...],
    trigger_probe: TriggerProbe,
    *,
    test_output_truncated: bool = False,
) -> tuple[FailureClassification, str]:
    """Decide the benchmark verdict from observed failures vs runtime triggers.

    A successful ``defects4j test`` command passes only when EVERY triggering
    test exported by the checked-out workspace is reproduced among the observed
    failures. Unrelated failures alone, missing or truncated trigger metadata,
    an empty trigger export, and a truncated ``test`` capture never produce
    PASS: incomplete evidence is unverifiable evidence, and unverifiable
    evidence fails closed without inventing any name.
    """
    if test_output_truncated:
        return (
            FailureClassification.BENCHMARK_CASE_FAILURE,
            "the bounded defects4j test capture was truncated, so the declared "
            "failing-test list is incomplete; failing-test evidence is not "
            "verifiable from a partial capture, so case PASS is not claimed",
        )
    if not trigger_probe.available:
        return (
            FailureClassification.BENCHMARK_CASE_FAILURE,
            "triggering-test metadata was not obtainable from the checked-out "
            "workspace; the designed behavior cannot be verified so case PASS "
            "is not claimed",
        )
    expected = trigger_probe.observed_trigger_tests
    if not expected:
        return (
            FailureClassification.BENCHMARK_CASE_FAILURE,
            "the runtime exported no triggering tests; the designed "
            "buggy-revision behavior cannot be verified",
        )
    observed = set(observed_failures)
    missing = [name for name in expected if name not in observed]
    if missing:
        return (
            FailureClassification.BENCHMARK_CASE_FAILURE,
            "expected triggering test(s) were not reproduced: "
            + ", ".join(sorted(missing)),
        )
    return (
        FailureClassification.PASS,
        "buggy revision reproduced every triggering test exported by the "
        "runtime for the checked-out workspace",
    )


def run_smoke(
    runner: CommandRunner | None = None,
    *,
    boundary: RuntimeBoundary | None = None,
    manifest_path: Path | str = MANIFEST_PATH,
) -> SmokeRunResult:
    """Run (or objectively classify) the EVAL-001 Defects4J runtime smoke."""
    boundary = boundary or RuntimeBoundary()
    runner = runner or SubprocessCommandRunner()

    manifest, cases = load_smoke_cases(manifest_path)
    child_env = build_child_environment(boundary.child_env_base)

    transport = boundary.defects4j_transport or HostExecutableTransport(
        java_executable=boundary.java_executable,
        defects4j_executable=boundary.defects4j_executable,
    )

    probe_project = _resolve_info_probe_project(boundary, cases)
    java_probe = probe_java(
        runner,
        env=child_env,
        argv=transport.prepare(
            RuntimeCommand(tool="java", arguments=("-version",))
        ).argv,
        timeout_seconds=boundary.probe_timeout_seconds,
        output_limit_bytes=boundary.output_limit_bytes,
    )
    defects4j_probe = probe_defects4j_runtime(
        runner,
        probe_project=probe_project,
        env=child_env,
        argv=transport.prepare(
            RuntimeCommand(
                tool="defects4j",
                arguments=("info", "-p", probe_project),
            )
        ).argv,
        timeout_seconds=boundary.probe_timeout_seconds,
        output_limit_bytes=boundary.output_limit_bytes,
    )
    identity_probe = resolve_defects4j_release_identity(
        required_version=str(manifest["defects4j_release"]),
        provenance_reader=boundary.defects4j_release_reader,
    )

    gate = FailureClassification.PASS
    gate_detail = ""
    for probe in (java_probe, defects4j_probe, identity_probe):
        if probe.classification is not FailureClassification.PASS:
            gate = probe.classification
            gate_detail = probe.detail
            break

    execution_mode = (
        "REAL_RUNTIME" if isinstance(runner, SubprocessCommandRunner) else "MOCKED_RUNNER"
    )
    environment = EnvironmentFacts(
        os_name=platform.system(),
        machine=platform.machine(),
        runner_kind=runner.runner_kind,
        execution_mode=execution_mode,
        runtime_transport=transport.transport_kind,
        required_java_major=REQUIRED_JAVA_MAJOR,
        observed_java_version=java_probe.observed_version,
        observed_java_major=java_probe.observed_major,
        required_defects4j_version=str(manifest["defects4j_release"]),
        observed_defects4j_version=identity_probe.observed_version,
        defects4j_identity_provenance=_identity_provenance_label(identity_probe),
        timezone=REQUIRED_TIMEZONE,
    )

    results: list[CaseSmokeResult] = []
    for case in cases:
        if gate is not FailureClassification.PASS:
            results.append(
                CaseSmokeResult(
                    manifest_version=str(manifest["manifest_version"]),
                    case_id=case["benchmark_case_id"],
                    project=case["project"],
                    bug_id=int(case["bug_id"]),
                    buggy_version_id=case["buggy_revision"]["defects4j_version_id"],
                    fixed_version_id=case["fixed_revision"]["defects4j_version_id"],
                    environment=environment,
                    checkout_command=None,
                    compile_command=None,
                    test_command=None,
                    trigger_command=None,
                    trigger_probe=TriggerProbe(
                        attempted=False,
                        available=False,
                        observed_trigger_tests=(),
                        detail="not attempted: environment gate blocked the run",
                    ),
                    manifest_trigger_status=case["triggering_tests"]["status"],
                    failing_tests_declared_count=None,
                    failing_tests_observed=(),
                    failure_class=gate,
                    failure_detail=gate_detail,
                    cleanup=CleanupEvidence(attempted=False, removed=False, error=None),
                    workspace_path=None,
                )
            )
            continue
        results.append(
            _run_single_case(
                case,
                manifest_version=str(manifest["manifest_version"]),
                environment=environment,
                runner=runner,
                transport=transport,
                boundary=boundary,
                child_env=child_env,
            )
        )

    if any(result.environment_blocked for result in results):
        status = "ENVIRONMENT_BLOCKED"
    elif all(result.passed for result in results):
        status = "PASS"
    else:
        status = "FAIL"
    return SmokeRunResult(
        manifest_version=str(manifest["manifest_version"]),
        smoke_case_ids=tuple(str(case_id) for case_id in manifest["smoke_case_ids"]),
        status=status,
        environment=environment,
        cases=tuple(results),
    )


def _run_single_case(
    case: Mapping[str, Any],
    *,
    manifest_version: str,
    environment: EnvironmentFacts,
    runner: CommandRunner,
    transport: RuntimeTransport,
    boundary: RuntimeBoundary,
    child_env: Mapping[str, str],
) -> CaseSmokeResult:
    """Execute one case in a fresh disposable workspace; cleanup always runs."""
    case_id = case["benchmark_case_id"]
    workspace: Path | None = None
    checkout: CommandResult | None = None
    compile_result: CommandResult | None = None
    test_result: CommandResult | None = None
    trigger_result: CommandResult | None = None
    trigger_probe = TriggerProbe(
        attempted=False,
        available=False,
        observed_trigger_tests=(),
        detail="not attempted",
    )
    declared_count: int | None = None
    observed_failures: tuple[str, ...] = ()
    failure_class = FailureClassification.HARNESS_FAILURE
    failure_detail = "case did not complete"
    remover = boundary.remove_workspace or shutil.rmtree

    try:
        workspace = _create_disposable_workspace(case_id, boundary.temp_root)

        checkout = execute_runtime_command(
            runner,
            transport.prepare(
                RuntimeCommand(
                    tool="defects4j",
                    arguments=(
                        "checkout",
                        "-p",
                        case["project"],
                        "-v",
                        case["buggy_revision"]["defects4j_version_id"],
                    ),
                    workspace=workspace,
                )
            ),
            cwd=workspace,
            env=child_env,
            timeout_seconds=boundary.checkout_timeout_seconds,
            stdout_limit_bytes=boundary.output_limit_bytes,
            stderr_limit_bytes=boundary.output_limit_bytes,
        )
        if checkout.spawn_error is not None:
            failure_class = FailureClassification.CHECKOUT_FAILURE
            failure_detail = (
                f"checkout could not start ({checkout.spawn_error})"
            )
        elif checkout.timed_out:
            failure_class = FailureClassification.TIMEOUT
            failure_detail = f"checkout exceeded {boundary.checkout_timeout_seconds:g}s"
        elif checkout.exit_code != 0:
            failure_class = FailureClassification.CHECKOUT_FAILURE
            failure_detail = f"checkout exited {checkout.exit_code}"
        else:
            compile_result = execute_runtime_command(
                runner,
                transport.prepare(
                    RuntimeCommand(
                        tool="defects4j",
                        arguments=("compile",),
                        workspace=workspace,
                    )
                ),
                cwd=workspace,
                env=child_env,
                timeout_seconds=boundary.compile_timeout_seconds,
                stdout_limit_bytes=boundary.output_limit_bytes,
                stderr_limit_bytes=boundary.output_limit_bytes,
            )
            if compile_result.spawn_error is not None:
                failure_class = FailureClassification.COMPILE_FAILURE
                failure_detail = (
                    f"compile could not start ({compile_result.spawn_error})"
                )
            elif compile_result.timed_out:
                failure_class = FailureClassification.TIMEOUT
                failure_detail = (
                    f"compile exceeded {boundary.compile_timeout_seconds:g}s"
                )
            elif compile_result.exit_code != 0:
                failure_class = FailureClassification.COMPILE_FAILURE
                failure_detail = f"compile exited {compile_result.exit_code}"
            else:
                # A successful `defects4j test` command may absolutely report
                # failing tests on a buggy revision: exit status alone says
                # nothing about the benchmark verdict.
                test_result = execute_runtime_command(
                    runner,
                    transport.prepare(
                        RuntimeCommand(
                            tool="defects4j",
                            arguments=("test",),
                            workspace=workspace,
                        )
                    ),
                    cwd=workspace,
                    env=child_env,
                    timeout_seconds=boundary.test_timeout_seconds,
                    stdout_limit_bytes=boundary.output_limit_bytes,
                    stderr_limit_bytes=boundary.output_limit_bytes,
                )
                if test_result.spawn_error is not None:
                    failure_class = FailureClassification.TEST_FAILURE
                    failure_detail = (
                        f"test command could not start ({test_result.spawn_error})"
                    )
                elif test_result.timed_out:
                    failure_class = FailureClassification.TIMEOUT
                    failure_detail = (
                        f"test exceeded {boundary.test_timeout_seconds:g}s"
                    )
                elif test_result.exit_code != 0:
                    failure_class = FailureClassification.TEST_FAILURE
                    failure_detail = (
                        f"test exited {test_result.exit_code}; the test step "
                        "itself failed instead of reporting benchmark results"
                    )
                else:
                    (
                        declared_count,
                        observed_failures,
                    ) = _parse_failing_tests(test_result.stdout.text)
                    # Version-specific trigger metadata, read from the actual
                    # checked-out workspace with the supported interface.
                    trigger_result = execute_runtime_command(
                        runner,
                        transport.prepare(
                            RuntimeCommand(
                                tool="defects4j",
                                arguments=(
                                    "export",
                                    "-p",
                                    TRIGGER_PROPERTY_NAME,
                                ),
                                workspace=workspace,
                            )
                        ),
                        cwd=workspace,
                        env=child_env,
                        timeout_seconds=boundary.trigger_export_timeout_seconds,
                        stdout_limit_bytes=boundary.output_limit_bytes,
                        stderr_limit_bytes=boundary.output_limit_bytes,
                    )
                    trigger_probe = _classify_trigger_probe(trigger_result)
                    failure_class, failure_detail = _classify_benchmark_outcome(
                        observed_failures,
                        trigger_probe,
                        test_output_truncated=test_result.stdout.truncated,
                    )
    except Exception as error:  # noqa: BLE001 - preserved as HARNESS_FAILURE evidence
        failure_class = FailureClassification.HARNESS_FAILURE
        failure_detail = f"{type(error).__name__}: {error}"
    finally:
        cleanup = _attempt_cleanup(workspace, remover)

    return CaseSmokeResult(
        manifest_version=manifest_version,
        case_id=case_id,
        project=case["project"],
        bug_id=int(case["bug_id"]),
        buggy_version_id=case["buggy_revision"]["defects4j_version_id"],
        fixed_version_id=case["fixed_revision"]["defects4j_version_id"],
        environment=environment,
        checkout_command=checkout,
        compile_command=compile_result,
        test_command=test_result,
        trigger_command=trigger_result,
        trigger_probe=trigger_probe,
        manifest_trigger_status=case["triggering_tests"]["status"],
        failing_tests_declared_count=declared_count,
        failing_tests_observed=observed_failures,
        failure_class=failure_class,
        failure_detail=failure_detail,
        cleanup=cleanup,
        workspace_path=workspace,
    )


def _classify_trigger_probe(result: CommandResult) -> TriggerProbe:
    if result.timed_out:
        return TriggerProbe(
            attempted=True,
            available=False,
            observed_trigger_tests=(),
            detail="tests.trigger export exceeded its timeout",
        )
    if result.spawn_error is not None:
        return TriggerProbe(
            attempted=True,
            available=False,
            observed_trigger_tests=(),
            detail=(
                f"tests.trigger export could not start ({result.spawn_error})"
            ),
        )
    if result.exit_code != 0:
        return TriggerProbe(
            attempted=True,
            available=False,
            observed_trigger_tests=(),
            detail=f"tests.trigger export exited {result.exit_code}",
        )
    if result.stdout.truncated:
        # A truncated export cannot prove its list is complete: even when the
        # captured prefix happens to contain matching names, treating it as
        # the full trigger set would let an incomplete capture decide a PASS.
        return TriggerProbe(
            attempted=True,
            available=False,
            observed_trigger_tests=(),
            detail=(
                "tests.trigger export output was truncated at "
                f"{result.stdout.limit_bytes} of {result.stdout.total_bytes} "
                "bytes; the exported trigger list cannot be treated as "
                "complete, so case PASS is not claimed"
            ),
        )
    if not result.stdout.text.strip():
        return TriggerProbe(
            attempted=True,
            available=False,
            observed_trigger_tests=(),
            detail="tests.trigger export produced no data",
        )
    parsed = _parse_trigger_tests(result.stdout.text)
    if not parsed:
        return TriggerProbe(
            attempted=True,
            available=False,
            observed_trigger_tests=(),
            detail="tests.trigger export contained no parsable test references",
        )
    return TriggerProbe(
        attempted=True,
        available=True,
        observed_trigger_tests=parsed,
        detail=(
            "triggering tests obtained from the checked-out workspace via the "
            "supported version-specific export interface"
        ),
    )
