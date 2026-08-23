"""Focused tests for the Evaluation-owned Defects4J runtime smoke harness.

No real Defects4J installation is required: every benchmark-flow scenario uses
a scripted fake runner through the injectable CommandRunner boundary. The
scripted outcomes model the real Defects4J 3.0.1 semantics verified against the
upstream sources:

* there is NO ``version`` subcommand (operability uses ``info -p <project>``);
* ``defects4j test`` exits 0 when the suite ran and prints a real-style
  ``Failing tests: N`` summary with ``  - <name>`` entries;
* trigger metadata comes from ``defects4j export -p tests.trigger -w <dir>``
  after checkout, one reference per line.

A small number of tests exercise the production SubprocessCommandRunner
directly against trivial stdlib processes (``sys.executable``, ``/bin/sh``
stubs) to prove output bounding, timeout enforcement, deterministic truncation
and spawn-error classification without any Java or Defects4J dependency.
"""

import hashlib
import json
import os
import shutil
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from evaluation import defects4j_manifest as manifest_module
import evaluation.defects4j_runtime_smoke as smoke_module
from evaluation.defects4j_runtime_smoke import (
    ABORT_OUTPUT_LIMIT_BYTES,
    DEFAULT_ABORT_TIMEOUT_SECONDS,
    DEFAULT_DEFECTS4J_RUNNER_IMAGE,
    DEFECTS4J_IDENTITY_PROVENANCE_DEPLOYMENT_ATTESTED,
    DEFECTS4J_IDENTITY_PROVENANCE_UNAVAILABLE,
    DockerContainerTransport,
    FROZEN_MANIFEST_SHA256,
    HostExecutableTransport,
    MANIFEST_PATH,
    REQUIRED_DEFECTS4J_VERSION,
    REPO_ROOT,
    RUNTIME_PROBE_ANCHOR_CASE_ID,
    RUNNER_CONTAINER_CONTAINMENT_ARGUMENTS,
    RUNNER_IMAGE_FRAMEWORK_HOME,
    RUNNER_IMAGE_WORKSPACE,
    SMOKE_CASE_IDS,
    FailureClassification,
    RuntimeBoundary,
    RuntimeCommand,
    SmokeHarnessError,
    StreamCapture,
    SubprocessCommandRunner,
    build_child_environment,
    load_smoke_cases,
    normalize_test_reference,
    probe_defects4j_runtime,
    probe_java,
    resolve_defects4j_release_identity,
    run_smoke,
)

AUTHORIZED_SMOKE_IDS = ("D4J-GSON-001", "D4J-LANG-001", "D4J-MATH-001")

JAVA_11_STDERR = (
    'openjdk version "11.0.29" 2025-10-21 LTS\n'
    "OpenJDK Runtime Environment Corretto-11.0.29.7.1 "
    "(build 11.0.29+7-LTS)\n"
)
JAVA_17_STDERR = 'openjdk version "17.0.2" 2022-01-18\n'
JAVA_8_STDERR = 'java version "1.8.0_292"\n'

DEFECTS4J_INFO_OUTPUT = (
    "Project: Lang\n"
    "Number of active bugs: 61\n"
)

# Real v3.0.1 style: `Failing tests: N` followed by `  - <name>` entries; the
# command exits 0 whenever the test suite ran.
FAILING_TEST_OUTPUT = (
    "Failing tests: 2\n"
    "  - com.google.gson.JsonPrimitiveTest::testDeepCopy\n"
    "  - com.google.gson.JsonNullTest::testNull\n"
)
TRIGGER_EXPORT_OUTPUT = (
    "com.google.gson.JsonPrimitiveTest::testDeepCopy\n"
    "com.google.gson.JsonNullTest::testNull\n"
)


# --------------------------------------------------------------------------
# fake runner: scripted outcomes through the injectable CommandRunner boundary
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Outcome:
    exit_code: int | None = 0
    stdout_text: str = ""
    stderr_text: str = ""
    timed_out: bool = False
    spawn_error: str | None = None
    # Overrides the reported stdout byte total so a scripted outcome can model
    # real bounded-capture truncation (total > limit) while ``stdout_text``
    # stays the honest captured prefix.
    stdout_total_bytes: int | None = None


@dataclass(frozen=True)
class Call:
    argv: tuple[str, ...]
    cwd: str
    env: dict[str, str]
    timeout_seconds: float
    stdout_limit_bytes: int
    stderr_limit_bytes: int


def command_result_from_outcome(
    call: Call, program: str, outcome: Outcome
) -> smoke_module.CommandResult:
    stdout_total = (
        outcome.stdout_total_bytes
        if outcome.stdout_total_bytes is not None
        else len(outcome.stdout_text.encode("utf-8"))
    )
    return smoke_module.CommandResult(
        program=program,
        exit_code=outcome.exit_code,
        timed_out=outcome.timed_out,
        timeout_seconds=call.timeout_seconds,
        stdout=StreamCapture(
            limit_bytes=call.stdout_limit_bytes,
            total_bytes=stdout_total,
            text=outcome.stdout_text,
        ),
        stderr=StreamCapture(
            limit_bytes=call.stderr_limit_bytes,
            total_bytes=len(outcome.stderr_text.encode("utf-8")),
            text=outcome.stderr_text,
        ),
        spawn_error=outcome.spawn_error,
        argv=call.argv,
    )


class ScriptedRunner:
    """Fake CommandRunner keyed by (program basename, subcommand)."""

    runner_kind = "fake.scripted.v1"

    def __init__(self, outcomes: dict[tuple[str, str], Outcome]):
        self._outcomes = dict(outcomes)
        self.calls: list[Call] = []

    def run(
        self,
        argv,
        *,
        cwd,
        env,
        timeout_seconds,
        stdout_limit_bytes,
        stderr_limit_bytes,
    ):
        call = Call(
            argv=tuple(argv),
            cwd=str(cwd),
            env=dict(env),
            timeout_seconds=timeout_seconds,
            stdout_limit_bytes=stdout_limit_bytes,
            stderr_limit_bytes=stderr_limit_bytes,
        )
        self.calls.append(call)
        key = (os.path.basename(str(argv[0])), str(argv[1]) if len(argv) > 1 else "")
        if key not in self._outcomes:
            raise AssertionError(f"unexpected command: {argv!r}")
        return command_result_from_outcome(call, key[0], self._outcomes[key])


class DockerScriptedRunner:
    """Fake CommandRunner for container mode, keyed by the INNER command.

    The outer ``docker run --name <unique> ... <image> <inner...>`` argv is
    unwrapped at the configured image token so scripted outcomes reuse the
    same logical keys as host mode (``("defects4j", "checkout")`` etc.).
    Abort commands (``docker rm --force <name>``) are recorded separately.
    """

    runner_kind = "fake.docker.scripted.v1"

    def __init__(
        self,
        image: str,
        outcomes: dict[tuple[str, str], Outcome],
        *,
        abort_spawn_error: str | None = None,
        abort_exit_code: int | None = 0,
    ):
        self._image = image
        self._outcomes = dict(outcomes)
        self._abort_spawn_error = abort_spawn_error
        self._abort_exit_code = abort_exit_code
        self.calls: list[Call] = []
        self.abort_calls: list[Call] = []

    @staticmethod
    def container_name(argv) -> str:
        return argv[list(argv).index("--name") + 1]

    def inner_argv(self, call: Call) -> tuple[str, ...]:
        argv = call.argv
        return tuple(argv[list(argv).index(self._image) + 1 :])

    def run(
        self,
        argv,
        *,
        cwd,
        env,
        timeout_seconds,
        stdout_limit_bytes,
        stderr_limit_bytes,
    ):
        call = Call(
            argv=tuple(argv),
            cwd=str(cwd),
            env=dict(env),
            timeout_seconds=timeout_seconds,
            stdout_limit_bytes=stdout_limit_bytes,
            stderr_limit_bytes=stderr_limit_bytes,
        )
        if len(argv) > 1 and argv[1] == "rm":
            self.abort_calls.append(call)
            outcome = Outcome(
                exit_code=self._abort_exit_code, spawn_error=self._abort_spawn_error
            )
            return command_result_from_outcome(call, "docker", outcome)
        if len(argv) > 1 and argv[1] == "run":
            self.calls.append(call)
            inner = self.inner_argv(call)
            key = (
                os.path.basename(inner[0]),
                inner[1] if len(inner) > 1 else "",
            )
            if key not in self._outcomes:
                raise AssertionError(f"unexpected container command: {inner!r}")
            return command_result_from_outcome(call, key[0], self._outcomes[key])
        raise AssertionError(f"unexpected docker invocation: {argv!r}")


def make_container_boundary(root: Path, **overrides) -> RuntimeBoundary:
    """Host-mode boundary plus the explicit Deployment container transport."""
    boundary = make_boundary(root, **overrides)
    return replace(
        boundary,
        defects4j_transport=DockerContainerTransport(
            image=DEFAULT_DEFECTS4J_RUNNER_IMAGE
        ),
    )


def run_calls_of(runner: DockerScriptedRunner):
    return runner.calls


def inner_of_run_call(runner: DockerScriptedRunner, call):
    return runner.inner_argv(call)


def volume_specs(call) -> list[str]:
    specs = []
    argv = list(call.argv)
    for index, token in enumerate(argv):
        if token == "--volume":
            specs.append(argv[index + 1])
    return specs


def happy_outcomes() -> dict[tuple[str, str], Outcome]:
    """Identical mocked inputs for every scenario needing a full PASS.

    Models real semantics: the mocked ``test`` command exits 0 even though the
    buggy revision reports failing tests.
    """
    return {
        ("java", "-version"): Outcome(stdout_text="", stderr_text=JAVA_11_STDERR),
        ("defects4j", "info"): Outcome(stdout_text=DEFECTS4J_INFO_OUTPUT),
        ("defects4j", "checkout"): Outcome(stdout_text="Checked out workspace\n"),
        ("defects4j", "compile"): Outcome(stdout_text=""),
        ("defects4j", "test"): Outcome(exit_code=0, stdout_text=FAILING_TEST_OUTPUT),
        ("defects4j", "export"): Outcome(stdout_text=TRIGGER_EXPORT_OUTPUT),
    }


def gate_only_outcomes(
    java_stderr=JAVA_11_STDERR,
    info_exit=0,
    info_stdout=DEFECTS4J_INFO_OUTPUT,
):
    return {
        ("java", "-version"): Outcome(stdout_text="", stderr_text=java_stderr),
        ("defects4j", "info"): Outcome(exit_code=info_exit, stdout_text=info_stdout),
    }


@pytest.fixture
def isolated_boundary_root(tmp_path):
    root = tmp_path / "smoke-temp"
    root.mkdir()
    return root


def attested_reader(value: str | None):
    return lambda: value


def make_boundary(root: Path, **overrides) -> RuntimeBoundary:
    defaults = dict(
        temp_root=root,
        output_limit_bytes=4096,
        child_env_base={"PATH": "/usr/bin:/bin", "TESTGAP_SECRET": "do-not-leak"},
        defects4j_release_reader=attested_reader(REQUIRED_DEFECTS4J_VERSION),
    )
    defaults.update(overrides)
    return RuntimeBoundary(**defaults)


def case_by_id(run, case_id):
    return next(case for case in run.cases if case.case_id == case_id)


def expected_probe_project() -> str:
    _, resolved = load_smoke_cases()
    return next(
        case["project"]
        for case in resolved
        if case["benchmark_case_id"] == RUNTIME_PROBE_ANCHOR_CASE_ID
    )


# --------------------------------------------------------------------------
# frozen benchmark identity
# --------------------------------------------------------------------------


def test_authorized_smoke_set_is_exactly_three_ids():
    assert SMOKE_CASE_IDS == AUTHORIZED_SMOKE_IDS == tuple(sorted(SMOKE_CASE_IDS))


def test_manifest_smoke_membership_matches_the_authorized_set():
    _, resolved = load_smoke_cases()
    assert [case["benchmark_case_id"] for case in resolved] == list(AUTHORIZED_SMOKE_IDS)
    raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert sorted(raw["smoke_case_ids"]) == list(AUTHORIZED_SMOKE_IDS)


def test_no_case_substitution_membership_differs_fails_closed(tmp_path):
    raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    raw["smoke_case_ids"] = ["D4J-GSON-001", "D4J-LANG-001", "D4J-MATH-053"]
    tampered_dir = tmp_path / "tampered"
    tampered_dir.mkdir()
    tampered_manifest = tampered_dir / "DEFECTS4J_MVP_V1.json"
    tampered_manifest.write_text(
        manifest_module.canonical_json(raw), encoding="utf-8"
    )
    digest = hashlib.sha256(tampered_manifest.read_bytes()).hexdigest()
    (tampered_dir / "DEFECTS4J_MVP_V1.sha256").write_text(
        f"{digest}  DEFECTS4J_MVP_V1.json\n", encoding="utf-8"
    )
    with pytest.raises(SmokeHarnessError, match="membership differs"):
        load_smoke_cases(tampered_manifest)


def test_no_case_substitution_missing_case_fails_closed(tmp_path):
    """A smoke case disappearing from the manifest must never resolve."""
    raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    renamed = []
    for case in raw["cases"]:
        if case["benchmark_case_id"] == "D4J-LANG-001":
            case = dict(case)
            case["benchmark_case_id"] = "D4J-LANG-099"
        renamed.append(case)
    raw["cases"] = renamed
    tampered_dir = tmp_path / "tampered-missing"
    tampered_dir.mkdir()
    tampered_manifest = tampered_dir / "DEFECTS4J_MVP_V1.json"
    tampered_manifest.write_text(
        manifest_module.canonical_json(raw), encoding="utf-8"
    )
    digest = hashlib.sha256(tampered_manifest.read_bytes()).hexdigest()
    (tampered_dir / "DEFECTS4J_MVP_V1.sha256").write_text(
        f"{digest}  DEFECTS4J_MVP_V1.json\n", encoding="utf-8"
    )
    with pytest.raises(manifest_module.ManifestValidationError) as raised:
        load_smoke_cases(tampered_manifest)
    assert any(
        "D4J-LANG-001" in error for error in raised.value.errors
    )


def test_invalid_manifest_fails_closed(tmp_path):
    broken = tmp_path / "DEFECTS4J_MVP_V1.json"
    broken.write_text("{ not json", encoding="utf-8")
    with pytest.raises((SmokeHarnessError, ValueError)):
        load_smoke_cases(broken)


def test_case_metadata_resolved_through_canonical_manifest_loader():
    _, resolved = load_smoke_cases()
    raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    raw_by_id = {case["benchmark_case_id"]: case for case in raw["cases"]}
    assert resolved[0]["manifest_version"] == raw["manifest_version"]
    for case in resolved:
        expected = raw_by_id[case["benchmark_case_id"]]
        assert case["project"] == expected["project"]
        assert case["bug_id"] == expected["bug_id"]
        assert (
            case["buggy_revision"]["defects4j_version_id"]
            == expected["buggy_revision"]["defects4j_version_id"]
        )
        assert (
            case["fixed_revision"]["defects4j_version_id"]
            == expected["fixed_revision"]["defects4j_version_id"]
        )
        assert case["triggering_tests"]["status"] == "UNVERIFIED"


def test_frozen_manifest_checksum_is_unchanged():
    actual = hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest()
    assert FROZEN_MANIFEST_SHA256 == (
        "4e77e8e62ec5d09619d2e340ed56f3420066d221c53afdb370b92ed834fcd0c3"
    )
    assert actual == FROZEN_MANIFEST_SHA256
    sidecar = MANIFEST_PATH.with_suffix(".sha256").read_text(encoding="utf-8").split()[0]
    assert sidecar == FROZEN_MANIFEST_SHA256
    manifest_module.verify_file(MANIFEST_PATH)


def test_required_versions_come_from_the_manifest():
    manifest, _ = load_smoke_cases()
    assert manifest["defects4j_release"] == REQUIRED_DEFECTS4J_VERSION == "3.0.1"
    assert manifest["required_java_major"] == smoke_module.REQUIRED_JAVA_MAJOR == 11
    assert manifest["required_timezone"] == smoke_module.REQUIRED_TIMEZONE


# --------------------------------------------------------------------------
# no invented CLI surface (correction 1 + correction 3)
# --------------------------------------------------------------------------


def test_harness_never_invokes_a_version_or_query_subcommand():
    source = Path(smoke_module.__file__).read_text(encoding="utf-8")
    for literal in ('"version"', "'version'", '"query"', "'query'"):
        assert literal not in source, f"harness references invented subcommand {literal}"


def test_scripted_full_run_issues_only_supported_subcommands(isolated_boundary_root):
    runner = ScriptedRunner(happy_outcomes())
    run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    issued = {tuple(call.argv[:2]) for call in runner.calls}
    assert issued == {
        ("java", "-version"),
        ("defects4j", "info"),
        ("defects4j", "checkout"),
        ("defects4j", "compile"),
        ("defects4j", "test"),
        ("defects4j", "export"),
    }


# --------------------------------------------------------------------------
# environment gates: Java probe, supported runtime operability probe,
# exact-release identity from Deployment-owned provenance
# --------------------------------------------------------------------------


def test_java_11_probe_is_accepted_and_exact_version_preserved(isolated_boundary_root):
    runner = ScriptedRunner(happy_outcomes())
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    assert run.environment.required_java_major == 11
    assert run.environment.observed_java_major == 11
    assert run.environment.observed_java_version == "11.0.29"


def test_probe_java_accepts_major_11_directly():
    runner = ScriptedRunner(gate_only_outcomes())
    env = build_child_environment({"PATH": "/usr/bin:/bin"})
    probe = probe_java(runner, env=env)
    assert probe.classification is FailureClassification.PASS
    assert probe.observed_major == 11
    assert probe.observed_version == "11.0.29"


@pytest.mark.parametrize(
    ("stderr", "label"),
    [(JAVA_17_STDERR, "17"), (JAVA_8_STDERR, "8")],
)
def test_wrong_java_major_is_rejected_and_classified(isolated_boundary_root, stderr, label):
    runner = ScriptedRunner(gate_only_outcomes(java_stderr=stderr))
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    assert run.status == "ENVIRONMENT_BLOCKED"
    assert all(
        case.failure_class is FailureClassification.JAVA_VERSION_MISMATCH
        for case in run.cases
    )
    detail = run.cases[0].failure_detail
    assert "required Java major 11" in detail and label in detail
    invoked_subcommands = [call.argv[1] for call in runner.calls]
    assert "checkout" not in invoked_subcommands
    assert all(case.cleanup.attempted is False for case in run.cases)
    assert all(case.workspace_path is None for case in run.cases)


def test_unparsable_java_version_never_passes(isolated_boundary_root):
    runner = ScriptedRunner(gate_only_outcomes(java_stderr="java: not java at all"))
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    assert run.status == "ENVIRONMENT_BLOCKED"
    assert run.cases[0].failure_class is FailureClassification.JAVA_VERSION_MISMATCH


# --------------------------------------------------------------------------
# java probe execution success precedes any version-based verdict (A3)
# --------------------------------------------------------------------------


def test_java_probe_timeout_with_valid_version_text_cannot_pass():
    """A hung `java -version` that already printed valid Java 11 text never PASSes."""
    runner = ScriptedRunner(
        {
            ("java", "-version"): Outcome(
                exit_code=None,
                timed_out=True,
                stderr_text=JAVA_11_STDERR,
            )
        }
    )
    probe = probe_java(runner, env={"PATH": "/usr/bin:/bin"})
    assert probe.classification is not FailureClassification.PASS
    assert probe.classification is FailureClassification.JAVA_RUNTIME_NOT_OPERATIONAL
    assert "exceeded" in probe.detail
    assert probe.observed_version is None
    assert probe.observed_major is None
    command = probe.probe_command
    assert command.timed_out is True
    assert 'openjdk version "11.0.29"' in command.stderr.text


def test_java_probe_nonzero_exit_with_valid_version_text_cannot_pass():
    """A failed `java -version` whose output contains Java 11 text never PASSes."""
    runner = ScriptedRunner(
        {
            ("java", "-version"): Outcome(
                exit_code=1,
                stderr_text=JAVA_11_STDERR,
            )
        }
    )
    probe = probe_java(runner, env={"PATH": "/usr/bin:/bin"})
    assert probe.classification is not FailureClassification.PASS
    assert probe.classification is FailureClassification.JAVA_RUNTIME_NOT_OPERATIONAL
    assert probe.classification is not FailureClassification.JAVA_VERSION_MISMATCH
    assert "exited 1" in probe.detail
    assert probe.observed_version is None
    assert probe.observed_major is None
    command = probe.probe_command
    assert command.timed_out is False
    assert command.exit_code == 1
    assert 'openjdk version "11.0.29"' in command.stderr.text


@pytest.mark.parametrize(
    "java_outcome",
    [
        Outcome(exit_code=None, timed_out=True, stderr_text=JAVA_11_STDERR),
        Outcome(exit_code=3, stderr_text=JAVA_11_STDERR),
    ],
    ids=["timeout-with-valid-11-text", "nonzero-exit-with-valid-11-text"],
)
def test_unsuccessful_java_probe_blocks_benchmark_execution(
    isolated_boundary_root, java_outcome
):
    outcomes = gate_only_outcomes()
    outcomes[("java", "-version")] = java_outcome
    runner = ScriptedRunner(outcomes)
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    assert run.status == "ENVIRONMENT_BLOCKED"
    assert all(
        case.failure_class is FailureClassification.JAVA_RUNTIME_NOT_OPERATIONAL
        for case in run.cases
    )
    assert all(not case.passed for case in run.cases)
    for step in ("checkout", "compile", "test", "export"):
        assert not any(call.argv[1] == step for call in runner.calls)
    assert all(case.workspace_path is None for case in run.cases)
    assert all(case.cleanup.attempted is False for case in run.cases)


def test_successful_java_11_probe_still_passes_after_correction():
    runner = ScriptedRunner(
        {("java", "-version"): Outcome(exit_code=0, stderr_text=JAVA_11_STDERR)}
    )
    probe = probe_java(runner, env={"PATH": "/usr/bin:/bin"})
    assert probe.classification is FailureClassification.PASS
    assert probe.observed_major == 11
    assert probe.observed_version == "11.0.29"
    assert probe.probe_command.exit_code == 0
    assert probe.probe_command.timed_out is False


def test_successful_wrong_java_major_is_still_a_version_mismatch():
    runner = ScriptedRunner(
        {("java", "-version"): Outcome(exit_code=0, stderr_text=JAVA_17_STDERR)}
    )
    probe = probe_java(runner, env={"PATH": "/usr/bin:/bin"})
    assert probe.classification is FailureClassification.JAVA_VERSION_MISMATCH
    assert probe.observed_major == 17


def test_runtime_operability_probe_uses_supported_info_subcommand(
    isolated_boundary_root,
):
    """The install/runtime probe must be the documented `info -p` interface."""
    project = expected_probe_project()
    runner = ScriptedRunner(happy_outcomes())
    run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    info_calls = [call for call in runner.calls if call.argv[1] == "info"]
    assert len(info_calls) == 1
    assert tuple(info_calls[0].argv) == ("defects4j", "info", "-p", project)


def test_probe_defects4j_runtime_classifies_operable_installation():
    project = expected_probe_project()
    runner = ScriptedRunner(gate_only_outcomes())
    probe = probe_defects4j_runtime(
        runner,
        probe_project=project,
        env={"PATH": "/usr/bin:/bin"},
    )
    assert probe.classification is FailureClassification.PASS
    assert probe.observed_version is None
    command = probe.probe_command
    assert tuple(command.argv) == ("defects4j", "info", "-p", project)


def test_probe_defects4j_runtime_rejects_failing_info_probe():
    project = expected_probe_project()
    runner = ScriptedRunner(gate_only_outcomes(info_exit=2))
    probe = probe_defects4j_runtime(
        runner,
        probe_project=project,
        env={"PATH": "/usr/bin:/bin"},
    )
    assert probe.classification is FailureClassification.DEFECTS4J_RUNTIME_NOT_OPERATIONAL
    assert "exited 2" in probe.detail


def test_probe_defects4j_runtime_rejects_silent_success():
    project = expected_probe_project()
    runner = ScriptedRunner(gate_only_outcomes(info_stdout=""))
    probe = probe_defects4j_runtime(
        runner,
        probe_project=project,
        env={"PATH": "/usr/bin:/bin"},
    )
    assert probe.classification is FailureClassification.DEFECTS4J_RUNTIME_NOT_OPERATIONAL


def test_non_operational_defects4j_runtime_blocks_the_run(isolated_boundary_root):
    runner = ScriptedRunner(gate_only_outcomes(info_exit=9))
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    assert run.status == "ENVIRONMENT_BLOCKED"
    assert all(
        case.failure_class is FailureClassification.DEFECTS4J_RUNTIME_NOT_OPERATIONAL
        for case in run.cases
    )
    assert not any(call.argv[1] == "checkout" for call in runner.calls)


def test_missing_defects4j_classified_as_runtime_tool_missing(isolated_boundary_root):
    outcomes = gate_only_outcomes()
    outcomes[("defects4j", "info")] = Outcome(spawn_error="ENOENT")
    runner = ScriptedRunner(outcomes)
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    assert run.status == "ENVIRONMENT_BLOCKED"
    assert all(
        case.failure_class is FailureClassification.RUNTIME_TOOL_MISSING
        for case in run.cases
    )
    assert all("ENOENT" in case.failure_detail for case in run.cases)
    assert all(case.workspace_path is None for case in run.cases)
    assert all(case.cleanup.attempted is False for case in run.cases)


# --------------------------------------------------------------------------
# exact release identity: Deployment-owned provenance only, fail closed
# --------------------------------------------------------------------------


def test_resolve_identity_passes_only_on_exact_attestation():
    probe = resolve_defects4j_release_identity(
        required_version="3.0.1",
        provenance_reader=attested_reader("3.0.1"),
    )
    assert probe.classification is FailureClassification.PASS
    assert probe.observed_version == "3.0.1"


@pytest.mark.parametrize("attested", ["2.2.0", "3.0.0", "", None])
def test_resolve_identity_rejects_anything_but_exact_release(attested):
    probe = resolve_defects4j_release_identity(
        required_version="3.0.1",
        provenance_reader=attested_reader(attested),
    )
    assert probe.classification is FailureClassification.DEFECTS4J_VERSION_MISMATCH
    assert probe.observed_version == (attested or None) or attested in ("", None)


def test_resolve_identity_without_provenance_source_never_passes():
    probe = resolve_defects4j_release_identity(
        required_version="3.0.1",
        provenance_reader=None,
    )
    assert probe.classification is FailureClassification.DEFECTS4J_VERSION_MISMATCH
    assert "no Deployment-owned provenance" in probe.detail


def test_resolve_identity_reader_failure_never_passes():
    def broken_reader():
        raise RuntimeError("provenance store unavailable")

    probe = resolve_defects4j_release_identity(
        required_version="3.0.1",
        provenance_reader=broken_reader,
    )
    assert probe.classification is FailureClassification.DEFECTS4J_VERSION_MISMATCH
    assert "RuntimeError" in probe.detail


def test_exact_version_mismatch_remains_fail_closed_even_with_operable_runtime(
    isolated_boundary_root,
):
    """Runtime works but attests another release: no PASS may be produced."""
    runner = ScriptedRunner(happy_outcomes())
    run = run_smoke(
        runner,
        boundary=make_boundary(
            isolated_boundary_root, defects4j_release_reader=attested_reader("2.2.0")
        ),
    )
    assert run.status == "ENVIRONMENT_BLOCKED"
    assert all(
        case.failure_class is FailureClassification.DEFECTS4J_VERSION_MISMATCH
        for case in run.cases
    )
    detail = run.cases[0].failure_detail
    assert "required Defects4J 3.0.1" in detail and "2.2.0" in detail
    assert not any(call.argv[1] == "checkout" for call in runner.calls)
    assert all(case.workspace_path is None for case in run.cases)
    assert all(case.cleanup.attempted is False for case in run.cases)


def test_unattested_identity_blocks_the_run_before_any_benchmark_step(
    isolated_boundary_root,
):
    """Default boundary binds no provenance reader: fail closed by design."""
    runner = ScriptedRunner(happy_outcomes())
    run = run_smoke(
        runner,
        boundary=make_boundary(isolated_boundary_root, defects4j_release_reader=None),
    )
    assert run.status == "ENVIRONMENT_BLOCKED"
    assert run.environment.observed_defects4j_version is None
    assert (
        run.environment.defects4j_identity_provenance
        == DEFECTS4J_IDENTITY_PROVENANCE_UNAVAILABLE
    )
    assert all(
        case.failure_class is FailureClassification.DEFECTS4J_VERSION_MISMATCH
        for case in run.cases
    )
    assert "refusing to pass" in run.cases[0].failure_detail
    assert not any(call.argv[1] == "checkout" for call in runner.calls)


def test_attested_identity_is_recorded_in_environment_facts(isolated_boundary_root):
    runner = ScriptedRunner(happy_outcomes())
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    assert run.environment.required_defects4j_version == "3.0.1"
    assert run.environment.observed_defects4j_version == "3.0.1"
    assert (
        run.environment.defects4j_identity_provenance
        == DEFECTS4J_IDENTITY_PROVENANCE_DEPLOYMENT_ATTESTED
    )


def test_provenance_label_exact_attestation_is_deployment_attested(
    isolated_boundary_root,
):
    """Successful exact attestation -> deployment.attested.v1."""
    runner = ScriptedRunner(happy_outcomes())
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    assert (
        run.environment.defects4j_identity_provenance
        == DEFECTS4J_IDENTITY_PROVENANCE_DEPLOYMENT_ATTESTED
        == "deployment.attested.v1"
    )
    assert run.status == "PASS"


def test_provenance_label_missing_reader_is_unavailable(isolated_boundary_root):
    runner = ScriptedRunner(happy_outcomes())
    run = run_smoke(
        runner,
        boundary=make_boundary(isolated_boundary_root, defects4j_release_reader=None),
    )
    assert (
        run.environment.defects4j_identity_provenance
        == DEFECTS4J_IDENTITY_PROVENANCE_UNAVAILABLE
        == "unavailable"
    )
    assert run.status == "ENVIRONMENT_BLOCKED"


def test_provenance_label_raising_reader_is_unavailable(isolated_boundary_root):
    def broken_reader():
        raise RuntimeError("provenance store unavailable")

    runner = ScriptedRunner(happy_outcomes())
    run = run_smoke(
        runner,
        boundary=make_boundary(
            isolated_boundary_root, defects4j_release_reader=broken_reader
        ),
    )
    assert (
        run.environment.defects4j_identity_provenance
        == DEFECTS4J_IDENTITY_PROVENANCE_UNAVAILABLE
    )
    assert run.environment.observed_defects4j_version is None
    assert run.status == "ENVIRONMENT_BLOCKED"
    assert not any(call.argv[1] == "checkout" for call in runner.calls)


@pytest.mark.parametrize("attested", [None, "", "   "])
def test_provenance_label_empty_or_none_reader_value_is_unavailable(
    isolated_boundary_root, attested
):
    """A bound reader is not attestation: only a concrete value counts."""
    runner = ScriptedRunner(happy_outcomes())
    run = run_smoke(
        runner,
        boundary=make_boundary(
            isolated_boundary_root, defects4j_release_reader=attested_reader(attested)
        ),
    )
    assert (
        run.environment.defects4j_identity_provenance
        == DEFECTS4J_IDENTITY_PROVENANCE_UNAVAILABLE
    )
    assert run.environment.observed_defects4j_version is None
    assert run.status == "ENVIRONMENT_BLOCKED"


def test_provenance_label_wrong_version_still_deployment_attested_but_gate_fails(
    isolated_boundary_root,
):
    """Deployment objectively attested the wrong version: label retained,
    version gate still fails, and no PASS can occur."""
    runner = ScriptedRunner(happy_outcomes())
    run = run_smoke(
        runner,
        boundary=make_boundary(
            isolated_boundary_root, defects4j_release_reader=attested_reader("2.2.0")
        ),
    )
    assert (
        run.environment.defects4j_identity_provenance
        == DEFECTS4J_IDENTITY_PROVENANCE_DEPLOYMENT_ATTESTED
    )
    assert run.environment.observed_defects4j_version == "2.2.0"
    assert run.status == "ENVIRONMENT_BLOCKED"
    assert all(
        case.failure_class is FailureClassification.DEFECTS4J_VERSION_MISMATCH
        for case in run.cases
    )
    assert not any(case.passed for case in run.cases)


def test_environment_classes_are_distinct_values():
    classes = {member.value for member in FailureClassification}
    assert {
        "PASS",
        "ENVIRONMENT_BLOCKED",
        "RUNTIME_TOOL_MISSING",
        "JAVA_VERSION_MISMATCH",
        "JAVA_RUNTIME_NOT_OPERATIONAL",
        "DEFECTS4J_RUNTIME_NOT_OPERATIONAL",
        "DEFECTS4J_VERSION_MISMATCH",
        "CHECKOUT_FAILURE",
        "COMPILE_FAILURE",
        "TEST_FAILURE",
        "BENCHMARK_CASE_FAILURE",
        "TIMEOUT",
        "HARNESS_FAILURE",
    } <= classes


# --------------------------------------------------------------------------
# benchmark flow: checkout / compile / test exit semantics / trigger metadata
# --------------------------------------------------------------------------


def test_full_happy_path_passes_all_three_cases(isolated_boundary_root):
    runner = ScriptedRunner(happy_outcomes())
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    assert run.status == "PASS"
    assert [case.case_id for case in run.cases] == list(AUTHORIZED_SMOKE_IDS)
    assert all(case.passed for case in run.cases)


def test_successful_test_command_may_report_benchmark_failures(
    isolated_boundary_root,
):
    """Exit 0 plus failing buggy-revision tests is the designed happy shape."""
    runner = ScriptedRunner(happy_outcomes())
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    for case in run.cases:
        assert case.test_command.exit_code == 0
        assert case.failing_tests_declared_count == 2
        assert case.failing_tests_observed == (
            "com.google.gson.JsonPrimitiveTest::testDeepCopy",
            "com.google.gson.JsonNullTest::testNull",
        )


def test_successful_command_with_matching_triggers_passes(isolated_boundary_root):
    runner = ScriptedRunner(happy_outcomes())
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    for case in run.cases:
        assert case.failure_class is FailureClassification.PASS
        assert case.trigger_probe.available is True
        assert case.trigger_probe.observed_trigger_tests
        assert set(case.trigger_probe.observed_trigger_tests) <= set(
            case.failing_tests_observed
        )
        assert "reproduced every triggering test" in case.failure_detail


def test_successful_command_without_triggering_failures_is_case_failure(
    isolated_boundary_root,
):
    """All tests passing on a buggy revision contradicts benchmark design."""
    outcomes = happy_outcomes()
    outcomes[("defects4j", "test")] = Outcome(exit_code=0, stdout_text="")
    runner = ScriptedRunner(outcomes)
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    assert run.status == "FAIL"
    infrastructure = {
        FailureClassification.CHECKOUT_FAILURE,
        FailureClassification.COMPILE_FAILURE,
        FailureClassification.TEST_FAILURE,
        FailureClassification.TIMEOUT,
    }
    for case in run.cases:
        assert case.test_command.exit_code == 0
        assert case.failure_class is FailureClassification.BENCHMARK_CASE_FAILURE
        assert case.failure_class not in infrastructure
        assert "not reproduced" in case.failure_detail


def test_zero_declared_failures_is_case_failure_not_infrastructure(
    isolated_boundary_root,
):
    outcomes = happy_outcomes()
    outcomes[("defects4j", "test")] = Outcome(exit_code=0, stdout_text="Failing tests: 0\n")
    runner = ScriptedRunner(outcomes)
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    for case in run.cases:
        assert case.failing_tests_declared_count == 0
        assert case.failing_tests_observed == ()
        assert case.failure_class is FailureClassification.BENCHMARK_CASE_FAILURE


def test_unrelated_failing_test_does_not_satisfy_trigger_reproduction(
    isolated_boundary_root,
):
    outcomes = happy_outcomes()
    outcomes[("defects4j", "test")] = Outcome(
        exit_code=0,
        stdout_text=(
            "Failing tests: 2\n"
            "  - com.example.UnrelatedTest::otherThing\n"
            "  - com.example.AnotherUnrelatedTest::alsoOther\n"
        ),
    )
    runner = ScriptedRunner(outcomes)
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    assert run.status == "FAIL"
    for case in run.cases:
        assert case.failing_tests_declared_count == 2
        assert case.failure_class is FailureClassification.BENCHMARK_CASE_FAILURE
        for trigger in (
            "com.google.gson.JsonPrimitiveTest::testDeepCopy",
            "com.google.gson.JsonNullTest::testNull",
        ):
            assert trigger in case.failure_detail


def test_extra_failures_beyond_reproduced_triggers_still_pass(isolated_boundary_root):
    """The minimum bar is reproduction of every authorized triggering test."""
    outcomes = happy_outcomes()
    outcomes[("defects4j", "test")] = Outcome(
        exit_code=0,
        stdout_text=(
            "Failing tests: 3\n"
            "  - com.example.UnrelatedTest::otherThing\n"
            "  - com.google.gson.JsonPrimitiveTest::testDeepCopy\n"
            "  - com.google.gson.JsonNullTest::testNull\n"
        ),
    )
    runner = ScriptedRunner(outcomes)
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    assert run.status == "PASS"
    assert all(case.passed for case in run.cases)


def test_unavailable_trigger_metadata_never_yields_case_pass(isolated_boundary_root):
    outcomes = happy_outcomes()
    outcomes[("defects4j", "export")] = Outcome(exit_code=5)
    runner = ScriptedRunner(outcomes)
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    case = case_by_id(run, "D4J-MATH-001")
    assert case.trigger_probe.attempted is True
    assert case.trigger_probe.available is False
    assert case.trigger_probe.observed_trigger_tests == ()
    assert "exited 5" in case.trigger_probe.detail
    assert case.failure_class is FailureClassification.BENCHMARK_CASE_FAILURE
    assert "PASS is not claimed" in case.failure_detail


def test_empty_or_unparsable_trigger_export_never_yields_case_pass(
    isolated_boundary_root,
):
    for stdout_text in ("", "ant echoed some diagnostics\n"):
        outcomes = happy_outcomes()
        outcomes[("defects4j", "export")] = Outcome(stdout_text=stdout_text)
        runner = ScriptedRunner(outcomes)
        run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
        for case in run.cases:
            assert case.failure_class is FailureClassification.BENCHMARK_CASE_FAILURE


def test_trigger_metadata_uses_supported_export_interface(isolated_boundary_root):
    runner = ScriptedRunner(happy_outcomes())
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    export_calls = [call for call in runner.calls if call.argv[1] == "export"]
    assert len(export_calls) == 3
    for call, case in zip(export_calls, run.cases):
        assert tuple(call.argv[:4]) == ("defects4j", "export", "-p", "tests.trigger")
        assert call.argv[4] == "-w"
        assert call.argv[5] == str(case.workspace_path)
        assert call.cwd == str(case.workspace_path)
    assert not any(call.argv[1] == "query" for call in runner.calls)
    semantic = run.to_semantic_dict()["cases"][0]
    assert "trigger_export" in semantic
    evidence = run.to_evidence_dict()["cases"][0]["trigger_export"]
    assert evidence["argv"][1:4] == ["export", "-p", "tests.trigger"]


def test_checkout_success_records_objective_command_facts(isolated_boundary_root):
    runner = ScriptedRunner(happy_outcomes())
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    case = case_by_id(run, "D4J-GSON-001")
    assert case.checkout_command.program == "defects4j"
    assert case.checkout_command.exit_code == 0
    assert case.checkout_command.timed_out is False
    checkout_calls = [call for call in runner.calls if call.argv[1] == "checkout"]
    assert len(checkout_calls) == 3


def test_checkout_argv_targets_exact_buggy_revision_and_workspace(
    isolated_boundary_root,
):
    runner = ScriptedRunner(happy_outcomes())
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    case = case_by_id(run, "D4J-GSON-001")
    workspace = str(case.workspace_path)
    checkout_call = next(call for call in runner.calls if call.argv[1] == "checkout")
    assert checkout_call.argv[:6] == ("defects4j", "checkout", "-p", "Gson", "-v", "1b")
    assert checkout_call.argv[6] == "-w"
    assert checkout_call.argv[7] == workspace
    assert checkout_call.cwd == workspace


def test_checkout_failure_is_classified_and_stops_the_case(isolated_boundary_root):
    outcomes = happy_outcomes()
    outcomes[("defects4j", "checkout")] = Outcome(exit_code=3)
    runner = ScriptedRunner(outcomes)
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    assert run.status == "FAIL"
    assert all(
        case.failure_class is FailureClassification.CHECKOUT_FAILURE
        for case in run.cases
    )
    for step in ("compile", "test", "export"):
        assert not any(call.argv[1] == step for call in runner.calls)


def test_compile_failure_is_classified_distinctly(isolated_boundary_root):
    outcomes = happy_outcomes()
    outcomes[("defects4j", "compile")] = Outcome(exit_code=2, stderr_text="BUILD FAILURE")
    runner = ScriptedRunner(outcomes)
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    assert run.status == "FAIL"
    assert all(
        case.failure_class is FailureClassification.COMPILE_FAILURE
        for case in run.cases
    )
    assert not any(call.argv[1] == "test" for call in runner.calls)


def test_compile_spawn_failure_is_classified_as_compile_failure(
    isolated_boundary_root,
):
    outcomes = happy_outcomes()
    outcomes[("defects4j", "compile")] = Outcome(spawn_error="EACCES")
    runner = ScriptedRunner(outcomes)
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    assert all(
        case.failure_class is FailureClassification.COMPILE_FAILURE
        for case in run.cases
    )
    assert all("EACCES" in case.failure_detail for case in run.cases)


def test_test_infrastructure_failure_is_classified_as_test_failure(
    isolated_boundary_root,
):
    """A non-zero test exit means the step failed; never a benchmark verdict."""
    outcomes = happy_outcomes()
    outcomes[("defects4j", "test")] = Outcome(exit_code=7, stderr_text="JUnit crashed")
    runner = ScriptedRunner(outcomes)
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    assert run.status == "FAIL"
    assert all(
        case.failure_class is FailureClassification.TEST_FAILURE for case in run.cases
    )
    assert all(case.failing_tests_declared_count is None for case in run.cases)
    assert "exited 7" in run.cases[0].failure_detail


def test_test_spawn_failure_is_classified_as_test_failure(isolated_boundary_root):
    outcomes = happy_outcomes()
    outcomes[("defects4j", "test")] = Outcome(spawn_error="ENOENT")
    runner = ScriptedRunner(outcomes)
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    assert all(
        case.failure_class is FailureClassification.TEST_FAILURE for case in run.cases
    )
    assert all("could not start" in case.failure_detail for case in run.cases)


# --------------------------------------------------------------------------
# normalization of real Defects4J output formats (correction 3)
# --------------------------------------------------------------------------


def test_real_style_failing_tests_summary_is_normalized():
    count, names = smoke_module._parse_failing_tests(
        "Running ant junit...\n"
        "Failing tests: 3\n"
        "\t1) org.apache.commons.lang3.math.NumberUtilsTest::TestLang747(1)\n"
        "  - com.google.gson.JsonPrimitiveTest::testDeepCopy\n"
        "\tcom.example.PlainListingTest::plain\n"
        "\n"
        "BUILD SUCCESSFUL\n"
    )
    assert count == 3
    assert names == (
        "org.apache.commons.lang3.math.NumberUtilsTest::TestLang747",
        "com.google.gson.JsonPrimitiveTest::testDeepCopy",
        "com.example.PlainListingTest::plain",
    )


def test_class_level_failing_entry_is_normalized():
    count, names = smoke_module._parse_failing_tests(
        "Failing tests: 1\n  - org.apache.commons.lang3.LocaleUtilsTest\n"
    )
    assert count == 1
    assert names == ("org.apache.commons.lang3.LocaleUtilsTest",)


def test_missing_failing_tests_summary_parses_to_unknown():
    assert smoke_module._parse_failing_tests("all quiet here\n") == (None, ())


def test_trigger_export_output_normalizes_separators_and_decorations():
    parsed = smoke_module._parse_trigger_tests(
        "org.apache.commons.lang3.math.NumberUtilsTest::TestLang747\n"
        "com.google.gson.JsonNullTest::testNull;\n"
        "com.a.ATest::one,com.a.BTest::two\n"
        "\t- com.c.CTest::decorated(2)\n"
    )
    assert parsed == (
        "org.apache.commons.lang3.math.NumberUtilsTest::TestLang747",
        "com.google.gson.JsonNullTest::testNull",
        "com.a.ATest::one",
        "com.a.BTest::two",
        "com.c.CTest::decorated",
    )


def test_normalize_test_reference_strips_decorations_only():
    assert normalize_test_reference("  - org.foo.BarTest::baz(1)\n") == (
        "org.foo.BarTest::baz"
    )
    assert normalize_test_reference("\t12)\torg.foo.QuxTest::qux") == (
        "org.foo.QuxTest::qux"
    )
    assert normalize_test_reference("org.foo.Plain") == "org.foo.Plain"


def test_decorated_test_listings_match_plain_trigger_export(isolated_boundary_root):
    outcomes = happy_outcomes()
    outcomes[("defects4j", "test")] = Outcome(
        exit_code=0,
        stdout_text=(
            "Failing tests: 2\n"
            "\t1) com.google.gson.JsonPrimitiveTest::testDeepCopy(1)\n"
            "\t2) com.google.gson.JsonNullTest::testNull(1)\n"
        ),
    )
    runner = ScriptedRunner(outcomes)
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    assert run.status == "PASS"
    for case in run.cases:
        assert case.failing_tests_observed == (
            "com.google.gson.JsonPrimitiveTest::testDeepCopy",
            "com.google.gson.JsonNullTest::testNull",
        )
        assert case.trigger_probe.observed_trigger_tests == case.failing_tests_observed


# --------------------------------------------------------------------------
# truncated verdict evidence must fail closed
# --------------------------------------------------------------------------


_TRUNCATED_TOTAL_BYTES = 10_000_000


def test_truncated_test_output_cannot_pass(isolated_boundary_root):
    """A partial failing-test capture is never sufficient benchmark evidence."""
    outcomes = happy_outcomes()
    outcomes[("defects4j", "test")] = Outcome(
        exit_code=0,
        stdout_text=FAILING_TEST_OUTPUT,
        stdout_total_bytes=_TRUNCATED_TOTAL_BYTES,
    )
    runner = ScriptedRunner(outcomes)
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    assert run.status == "FAIL"
    for case in run.cases:
        assert case.test_command.exit_code == 0
        assert case.test_command.stdout.truncated is True
        assert case.test_command.stdout.total_bytes == _TRUNCATED_TOTAL_BYTES
        assert case.failure_class is FailureClassification.BENCHMARK_CASE_FAILURE
        assert not case.passed
        assert "truncated" in case.failure_detail
        assert "PASS is not claimed" in case.failure_detail


def test_truncated_trigger_export_cannot_pass_even_with_matching_prefix(
    isolated_boundary_root,
):
    """Matching names inside a truncated capture never decide a PASS."""
    outcomes = happy_outcomes()
    # The captured prefix contains exactly the matching trigger names, but the
    # export was really larger than the capture bound.
    outcomes[("defects4j", "export")] = Outcome(
        exit_code=0,
        stdout_text=TRIGGER_EXPORT_OUTPUT,
        stdout_total_bytes=_TRUNCATED_TOTAL_BYTES,
    )
    runner = ScriptedRunner(outcomes)
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    assert run.status == "FAIL"
    for case in run.cases:
        assert case.trigger_command.exit_code == 0
        assert case.trigger_command.stdout.truncated is True
        assert case.trigger_probe.attempted is True
        assert case.trigger_probe.available is False
        assert case.trigger_probe.observed_trigger_tests == ()
        assert "truncated" in case.trigger_probe.detail
        assert case.failure_class is FailureClassification.BENCHMARK_CASE_FAILURE
        assert not case.passed
        assert "PASS is not claimed" in case.failure_detail


def test_non_truncated_matching_evidence_still_passes(isolated_boundary_root):
    runner = ScriptedRunner(happy_outcomes())
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    assert run.status == "PASS"
    for case in run.cases:
        assert case.test_command.stdout.truncated is False
        assert case.trigger_command.stdout.truncated is False
        assert case.trigger_probe.available is True
        assert case.failure_class is FailureClassification.PASS


def test_truncation_metadata_is_preserved_in_semantic_evidence(
    isolated_boundary_root,
):
    outcomes = happy_outcomes()
    outcomes[("defects4j", "test")] = Outcome(
        exit_code=0,
        stdout_text=FAILING_TEST_OUTPUT,
        stdout_total_bytes=_TRUNCATED_TOTAL_BYTES,
    )
    outcomes[("defects4j", "export")] = Outcome(
        exit_code=0,
        stdout_text=TRIGGER_EXPORT_OUTPUT,
        stdout_total_bytes=_TRUNCATED_TOTAL_BYTES,
    )
    runner = ScriptedRunner(outcomes)
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    semantic = case_by_id(run, "D4J-GSON-001").to_semantic_dict()
    assert semantic["test"]["stdout_truncated"] is True
    assert semantic["test"]["stdout_total_bytes"] > semantic["test"]["stdout_limit_bytes"]
    assert semantic["trigger_export"]["stdout_truncated"] is True
    assert (
        semantic["trigger_export"]["stdout_total_bytes"]
        > semantic["trigger_export"]["stdout_limit_bytes"]
    )


def test_truncated_capture_is_deterministic_across_identical_runs():
    """The production runner reports identical bounded prefixes and totals."""
    payload = "Y" * 40000
    runner = SubprocessCommandRunner()
    results = [
        runner.run(
            [sys.executable, "-c", f"print('{payload}')"],
            cwd=Path("/tmp"),
            env={"PATH": "/usr/bin:/bin"},
            timeout_seconds=60,
            stdout_limit_bytes=512,
            stderr_limit_bytes=64,
        )
        for _ in range(2)
    ]
    assert results[0].stdout.truncated is True
    assert results[0].stdout.text == results[1].stdout.text
    assert results[0].stdout.total_bytes == results[1].stdout.total_bytes


# --------------------------------------------------------------------------
# timeouts
# --------------------------------------------------------------------------


def test_phase_timeout_is_classified_and_stops_the_case(isolated_boundary_root):
    outcomes = happy_outcomes()
    outcomes[("defects4j", "compile")] = Outcome(timed_out=True, exit_code=None)
    runner = ScriptedRunner(outcomes)
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    assert run.status == "FAIL"
    assert all(case.failure_class is FailureClassification.TIMEOUT for case in run.cases)
    assert not any(call.argv[1] == "test" for call in runner.calls)
    facts = run.cases[0].to_semantic_dict()["compile"]
    assert facts["timed_out"] is True


def test_production_runner_enforces_timeout_on_every_command():
    runner = SubprocessCommandRunner()
    result = runner.run(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        cwd=Path("/tmp"),
        env={"PATH": "/usr/bin:/bin"},
        timeout_seconds=0.5,
        stdout_limit_bytes=1024,
        stderr_limit_bytes=1024,
    )
    assert result.timed_out is True
    assert result.timeout_seconds == 0.5


def test_every_external_command_receives_a_finite_timeout(isolated_boundary_root):
    runner = ScriptedRunner(happy_outcomes())
    boundary = make_boundary(isolated_boundary_root)
    run_smoke(runner, boundary=boundary)
    assert runner.calls
    assert all(call.timeout_seconds > 0 for call in runner.calls)
    per_subcommand: dict[str, set[float]] = {}
    for call in runner.calls:
        per_subcommand.setdefault(call.argv[1], set()).add(call.timeout_seconds)
    assert per_subcommand == {
        "-version": {boundary.probe_timeout_seconds},
        "info": {boundary.probe_timeout_seconds},
        "checkout": {boundary.checkout_timeout_seconds},
        "compile": {boundary.compile_timeout_seconds},
        "test": {boundary.test_timeout_seconds},
        "export": {boundary.trigger_export_timeout_seconds},
    }


# --------------------------------------------------------------------------
# bounded output and truncation metadata (production runner)
# --------------------------------------------------------------------------


def test_stdout_capture_is_bounded_with_truncation_metadata():
    runner = SubprocessCommandRunner()
    limit = 2048
    result = runner.run(
        [sys.executable, "-c", f"print('B' * {limit * 4})"],
        cwd=Path("/tmp"),
        env={"PATH": "/usr/bin:/bin"},
        timeout_seconds=60,
        stdout_limit_bytes=limit,
        stderr_limit_bytes=limit,
    )
    assert result.exit_code == 0
    assert result.stdout.truncated is True
    assert result.stdout.limit_bytes == limit
    assert result.stdout.total_bytes > limit
    assert len(result.stdout.text) <= limit


def test_stderr_capture_is_bounded_with_truncation_metadata():
    runner = SubprocessCommandRunner()
    limit = 2048
    result = runner.run(
        [
            sys.executable,
            "-c",
            f"import sys; sys.stderr.write('E' * {limit * 4})",
        ],
        cwd=Path("/tmp"),
        env={"PATH": "/usr/bin:/bin"},
        timeout_seconds=60,
        stdout_limit_bytes=limit,
        stderr_limit_bytes=limit,
    )
    assert result.exit_code == 0
    assert result.stderr.truncated is True
    assert result.stderr.limit_bytes == limit
    assert result.stderr.total_bytes > limit
    assert len(result.stderr.text) <= limit


def test_truncation_is_deterministic_across_identical_runs():
    runner = SubprocessCommandRunner()
    payload = "X" * 50000
    results = [
        runner.run(
            [sys.executable, "-c", f"print('{payload}')"],
            cwd=Path("/tmp"),
            env={"PATH": "/usr/bin:/bin"},
            timeout_seconds=60,
            stdout_limit_bytes=1234,
            stderr_limit_bytes=64,
        )
        for _ in range(2)
    ]
    assert results[0].stdout.text == results[1].stdout.text
    assert results[0].stdout.total_bytes == results[1].stdout.total_bytes
    assert results[0].stdout.truncated is True


def test_evidence_step_facts_expose_explicit_truncation_metadata(
    isolated_boundary_root,
):
    runner = ScriptedRunner(happy_outcomes())
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    facts = case_by_id(run, "D4J-GSON-001").to_semantic_dict()["checkout"]
    for key in (
        "stdout_truncated",
        "stderr_truncated",
        "stdout_total_bytes",
        "stderr_total_bytes",
        "stdout_limit_bytes",
        "stderr_limit_bytes",
    ):
        assert key in facts
    evidence = case_by_id(run, "D4J-GSON-001").to_evidence_dict()["checkout"]
    assert isinstance(evidence["stdout_text"], str)
    assert isinstance(evidence["stderr_text"], str)


def test_spawn_failure_of_a_missing_binary_is_reported_not_raised():
    runner = SubprocessCommandRunner()
    result = runner.run(
        ["testgap-definitely-not-a-binary-xyz"],
        cwd=Path("/tmp"),
        env={"PATH": "/usr/bin:/bin"},
        timeout_seconds=10,
        stdout_limit_bytes=128,
        stderr_limit_bytes=128,
    )
    assert result.exit_code is None
    assert result.spawn_error == "ENOENT"


# --------------------------------------------------------------------------
# disposable workspaces and cleanup
# --------------------------------------------------------------------------


def test_every_case_gets_a_fresh_unique_workspace(isolated_boundary_root):
    runner = ScriptedRunner(happy_outcomes())
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    paths = [str(case.workspace_path) for case in run.cases]
    assert len(set(paths)) == 3
    for case in run.cases:
        prefix = f"{smoke_module.WORKSPACE_PREFIX}{case.case_id.lower()}-"
        assert Path(case.workspace_path).name.startswith(prefix)
    checkout_calls = [call for call in runner.calls if call.argv[1] == "checkout"]
    assert sorted(call.cwd for call in checkout_calls) == sorted(paths)


def test_workspace_lives_outside_repository_and_worktrees(isolated_boundary_root):
    runner = ScriptedRunner(happy_outcomes())
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    repo_root = REPO_ROOT.resolve()
    for case in run.cases:
        resolved = Path(case.workspace_path).resolve()
        assert resolved.is_relative_to(isolated_boundary_root.resolve())
        common = os.path.commonpath([str(resolved), str(repo_root)])
        assert common != str(repo_root)


def test_workspace_inside_repository_fails_closed(monkeypatch, tmp_path):
    fake_repo = tmp_path / "fake-repo"
    (fake_repo / "sub").mkdir(parents=True)
    monkeypatch.setattr(smoke_module, "REPO_ROOT", fake_repo)
    with pytest.raises(SmokeHarnessError, match="inside the repository"):
        smoke_module._create_disposable_workspace("D4J-X-001", fake_repo / "sub")
    assert not any((fake_repo / "sub").iterdir())


@pytest.mark.parametrize("marker_is_file", [True, False])
def test_workspace_inside_any_git_worktree_marker_fails_closed(tmp_path, marker_is_file):
    """A `.git` directory OR a linked-worktree `.git` file both reject."""
    second_worktree = tmp_path / "agent3-other-worktree"
    outside = second_worktree / "scratch"
    outside.mkdir(parents=True)
    marker = second_worktree / ".git"
    if marker_is_file:
        marker.write_text(
            "gitdir: /somewhere/else/TestGap-Miner/.git/worktrees/other\n",
            encoding="utf-8",
        )
    else:
        marker.mkdir()
    assert smoke_module.REPO_ROOT not in outside.resolve().parents
    with pytest.raises(SmokeHarnessError, match="Git working tree"):
        smoke_module._create_disposable_workspace("D4J-X-002", outside)
    assert not any(outside.iterdir())


def test_workspace_under_the_live_repository_or_worktree_is_rejected():
    """The real checkout itself carries a Git marker and must be rejected."""
    live_marker = REPO_ROOT / ".git"
    assert live_marker.is_dir() or live_marker.is_file()
    hypothetical = REPO_ROOT / "never-created-by-this-test" / "nested"
    with pytest.raises(SmokeHarnessError, match="inside the repository"):
        smoke_module._ensure_outside_repository(hypothetical)


def test_ordinary_external_temp_root_without_git_markers_is_accepted(tmp_path):
    external = tmp_path / "plain-external-temp"
    external.mkdir()
    workspace = smoke_module._create_disposable_workspace("D4J-X-003", external)
    try:
        assert workspace.resolve().is_relative_to(external.resolve())
        assert workspace.is_dir()
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
    assert list(external.iterdir()) == []


def test_cleanup_on_success_removes_every_workspace(isolated_boundary_root):
    runner = ScriptedRunner(happy_outcomes())
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    assert all(case.cleanup.attempted for case in run.cases)
    assert all(case.cleanup.removed for case in run.cases)
    assert list(isolated_boundary_root.iterdir()) == []


def test_cleanup_attempted_on_failure(isolated_boundary_root):
    outcomes = happy_outcomes()
    outcomes[("defects4j", "compile")] = Outcome(exit_code=2)
    runner = ScriptedRunner(outcomes)
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    assert all(case.cleanup.attempted for case in run.cases)
    assert all(case.cleanup.removed for case in run.cases)
    assert list(isolated_boundary_root.iterdir()) == []


def test_cleanup_failure_preserved_without_erasing_primary_failure(
    isolated_boundary_root,
):
    def refusing_remover(path):
        raise PermissionError(1, "denied")

    outcomes = happy_outcomes()
    outcomes[("defects4j", "compile")] = Outcome(exit_code=2)
    runner = ScriptedRunner(outcomes)
    boundary_config = make_boundary(
        isolated_boundary_root, remove_workspace=refusing_remover
    )
    run = run_smoke(runner, boundary=boundary_config)
    assert run.status == "FAIL"
    for case in run.cases:
        assert case.failure_class is FailureClassification.COMPILE_FAILURE
        assert case.cleanup.attempted is True
        assert case.cleanup.removed is False
        assert case.cleanup.error == "EPERM"


def test_cleanup_records_non_os_errors_too(isolated_boundary_root):
    def exploding_remover(path):
        raise ValueError("not a filesystem error")

    runner = ScriptedRunner(happy_outcomes())
    run = run_smoke(
        runner,
        boundary=make_boundary(isolated_boundary_root, remove_workspace=exploding_remover),
    )
    for case in run.cases:
        assert case.cleanup.error == "ValueError"
        assert case.failure_class is FailureClassification.PASS


def test_harness_failure_is_a_distinct_classification(tmp_path):
    runner = ScriptedRunner(happy_outcomes())
    run = run_smoke(
        runner,
        boundary=make_boundary(tmp_path / "does-not-exist"),
    )
    assert run.status == "FAIL"
    assert all(
        case.failure_class is FailureClassification.HARNESS_FAILURE
        for case in run.cases
    )
    assert all(case.cleanup.attempted is False for case in run.cases)


# --------------------------------------------------------------------------
# child environment and timezone discipline
# --------------------------------------------------------------------------


def test_timezone_is_forced_into_every_benchmark_child_process(
    isolated_boundary_root,
):
    runner = ScriptedRunner(happy_outcomes())
    before = dict(os.environ)
    run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    assert dict(os.environ) == before
    assert runner.calls
    for call in runner.calls:
        assert call.env["TZ"] == "America/Los_Angeles"


def test_child_environment_is_allowlisted_and_drops_secrets():
    child = build_child_environment(
        {
            "PATH": "/usr/bin:/bin",
            "HOME": "/home/runner",
            "DATABASE_URL": "postgresql://secret",
            "AWS_SECRET_ACCESS_KEY": "secret",
            "TZ": "UTC",
        }
    )
    assert set(child) <= {"HOME", "JAVA_HOME", "LANG", "LC_ALL", "LC_CTYPE", "PATH", "TZ"}
    assert child["TZ"] == "America/Los_Angeles"
    assert "DATABASE_URL" not in child
    assert "AWS_SECRET_ACCESS_KEY" not in child
    assert build_child_environment({})["TZ"] == "America/Los_Angeles"
    parent_before = dict(os.environ)
    build_child_environment(None)
    assert dict(os.environ) == parent_before


# --------------------------------------------------------------------------
# determinism and real-vs-mocked distinguishability
# --------------------------------------------------------------------------


def test_mocked_runs_are_deterministic(tmp_path):
    runs = []
    for index in range(2):
        root = tmp_path / f"run-{index}"
        root.mkdir()
        run = run_smoke(
            ScriptedRunner(happy_outcomes()), boundary=make_boundary(root)
        )
        runs.append(run.to_semantic_dict())
    assert runs[0] == runs[1]
    assert json.dumps(runs[0], sort_keys=True) == json.dumps(runs[1], sort_keys=True)


def test_semantic_results_contain_no_volatile_paths_or_timestamps(
    isolated_boundary_root,
):
    runner = ScriptedRunner(happy_outcomes())
    semantic = run_smoke(
        runner, boundary=make_boundary(isolated_boundary_root)
    ).to_semantic_dict()

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                yield key, value
                yield from walk(value)
        elif isinstance(node, list):
            for value in node:
                yield from walk(value)

    for key, value in walk(semantic):
        if isinstance(value, str):
            assert str(isolated_boundary_root) not in value
            assert "testgap-d4j-smoke-" not in value
    assert "workspace_path" not in semantic["cases"][0]
    evidence = run_smoke(
        ScriptedRunner(happy_outcomes()),
        boundary=make_boundary(isolated_boundary_root),
    ).to_evidence_dict()
    assert evidence["cases"][0]["workspace_path"].startswith(
        str(isolated_boundary_root)
    )


def _write_runtime_stubs(tmp_path):
    java_stub = tmp_path / "stub-java"
    defects4j_stub = tmp_path / "stub-defects4j"
    java_stub.write_text(
        "#!/bin/sh\necho 'openjdk version \"11.0.29\"' >&2\n", encoding="utf-8"
    )
    # Real-semantics stub: no `version` subcommand anywhere; `info` answers;
    # `test` exits 0 while reporting failing tests; `export` reads triggers.
    defects4j_stub.write_text(
        "#!/bin/sh\n"
        'cmd="${1:-}"\n'
        'if [ "$cmd" = "info" ]; then echo "Project information"; exit 0; fi\n'
        'if [ "$cmd" = "checkout" ]; then exit 0; fi\n'
        'if [ "$cmd" = "compile" ]; then exit 0; fi\n'
        'if [ "$cmd" = "test" ]; then printf "Failing tests: 1\\n  - com.ExampleTest::trigger\\n"; exit 0; fi\n'
        'if [ "$cmd" = "export" ]; then printf "com.ExampleTest::trigger\\n"; exit 0; fi\n'
        "exit 97\n",
        encoding="utf-8",
    )
    java_stub.chmod(0o755)
    defects4j_stub.chmod(0o755)
    return java_stub, defects4j_stub


def test_real_vs_mocked_execution_modes_are_distinguishable(tmp_path):
    java_stub, defects4j_stub = _write_runtime_stubs(tmp_path)

    root = tmp_path / "real-mode"
    root.mkdir()
    run = run_smoke(
        boundary=RuntimeBoundary(
            java_executable=str(java_stub),
            defects4j_executable=str(defects4j_stub),
            defects4j_release_reader=attested_reader("3.0.1"),
            temp_root=root,
            child_env_base={"PATH": "/usr/bin:/bin"},
            probe_timeout_seconds=30,
            checkout_timeout_seconds=30,
            compile_timeout_seconds=30,
            test_timeout_seconds=30,
            trigger_export_timeout_seconds=30,
        ),
    )
    assert run.environment.execution_mode == "REAL_RUNTIME"
    assert run.environment.runner_kind == "subprocess.bounded.v1"
    assert run.status == "PASS"

    mocked_root = tmp_path / "mocked-mode"
    mocked_root.mkdir()
    mocked = run_smoke(
        ScriptedRunner(happy_outcomes()),
        boundary=make_boundary(mocked_root),
    )
    assert mocked.environment.execution_mode == "MOCKED_RUNNER"
    assert mocked.environment.runner_kind == "fake.scripted.v1"
    assert (
        mocked.to_semantic_dict()["environment"]["execution_mode"]
        != run.to_semantic_dict()["environment"]["execution_mode"]
    )


def test_real_operable_runtime_without_attestation_is_blocked_end_to_end(tmp_path):
    """Even through real subprocesses, missing provenance blocks every pass."""
    java_stub, defects4j_stub = _write_runtime_stubs(tmp_path)
    root = tmp_path / "real-unattested"
    root.mkdir()
    run = run_smoke(
        boundary=RuntimeBoundary(
            java_executable=str(java_stub),
            defects4j_executable=str(defects4j_stub),
            defects4j_release_reader=None,
            temp_root=root,
            child_env_base={"PATH": "/usr/bin:/bin"},
            probe_timeout_seconds=30,
            trigger_export_timeout_seconds=30,
        ),
    )
    assert run.status == "ENVIRONMENT_BLOCKED"
    assert run.environment.execution_mode == "REAL_RUNTIME"
    assert all(
        case.failure_class is FailureClassification.DEFECTS4J_VERSION_MISMATCH
        for case in run.cases
    )
    assert not any(
        case.checkout_command is not None for case in run.cases
    )


# --------------------------------------------------------------------------
# no duplicated foreign benchmark definition
# --------------------------------------------------------------------------


def test_harness_source_contains_no_foreign_benchmark_definition():
    source = Path(smoke_module.__file__).read_text(encoding="utf-8")
    forbidden = [
        '"Gson"',
        "'Gson'",
        '"Lang"',
        "'Lang'",
        '"Math"',
        "'Math'",
        '"Chart"',
        '"Jsoup"',
        '"Time"',
        '"1b"',
        "'1b'",
        '"1f"',
        "'1f'",
        "D4J-CHART",
        "D4J-JSOUP",
        "D4J-TIME",
        "D4J-GSON-009",
        "D4J-LANG-034",
        "D4J-MATH-053",
    ]
    for literal in forbidden:
        assert literal not in source, f"harness hard-codes foreign metadata: {literal}"
    for case_id in AUTHORIZED_SMOKE_IDS:
        assert case_id in source


def test_run_status_fails_when_any_single_case_fails(isolated_boundary_root):
    outcomes = happy_outcomes()
    runner = ScriptedRunner(outcomes)

    original_run = runner.run

    def fail_lang_compile(argv, **kwargs):
        result = original_run(argv, **kwargs)
        if argv[1] == "compile" and "-w" in argv:
            workspace = Path(kwargs.get("cwd"))
            if "lang" in workspace.name:
                return smoke_module.CommandResult(
                    program=result.program,
                    exit_code=2,
                    timed_out=False,
                    timeout_seconds=result.timeout_seconds,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    argv=result.argv,
                )
        return result

    runner.run = fail_lang_compile
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    statuses = {
        case.case_id: case.failure_class for case in run.cases
    }
    assert statuses["D4J-LANG-001"] is FailureClassification.COMPILE_FAILURE
    assert statuses["D4J-GSON-001"] is FailureClassification.PASS
    assert run.status == "FAIL"


# --------------------------------------------------------------------------
# Deployment runtime boundary: explicit container transport (correction 4)
# --------------------------------------------------------------------------


def test_host_mode_remains_the_default_transport_and_argv_shape(
    isolated_boundary_root,
):
    """Without an explicit transport, host executables behave exactly as before."""
    runner = ScriptedRunner(happy_outcomes())
    run = run_smoke(runner, boundary=make_boundary(isolated_boundary_root))
    assert run.environment.runtime_transport == "host.executable.v1"
    checkout_call = next(call for call in runner.calls if call.argv[1] == "checkout")
    assert checkout_call.argv[:6] == ("defects4j", "checkout", "-p", "Gson", "-v", "1b")
    assert checkout_call.argv[6] == "-w"
    assert checkout_call.argv[7] == str(case_by_id(run, "D4J-GSON-001").workspace_path)
    invocation = HostExecutableTransport().prepare(
        RuntimeCommand(tool="java", arguments=("-version",))
    )
    assert invocation.argv == ("java", "-version")
    assert invocation.abort_argv is None


def test_container_operability_probe_uses_owner_runtime_invocation(
    isolated_boundary_root,
):
    """Container mode wraps `defects4j info -p <project>` in the documented
    Deployment runner invocation: structured argv, no shell, containment
    posture mirrored from compose.yml's runner service."""
    project = expected_probe_project()
    runner = DockerScriptedRunner(
        DEFAULT_DEFECTS4J_RUNNER_IMAGE, gate_only_outcomes()
    )
    run = run_smoke(
        runner,
        boundary=make_container_boundary(
            isolated_boundary_root, defects4j_release_reader=None
        ),
    )
    assert run.environment.runtime_transport == "docker.container.v1"
    info_calls = [
        call
        for call in runner.calls
        if runner.inner_argv(call)[:2] == ("defects4j", "info")
    ]
    assert len(info_calls) == 1
    argv = info_calls[0].argv
    assert all(isinstance(token, str) for token in argv)
    assert argv[:4] == ("docker", "run", "--rm", "--name")
    name = DockerScriptedRunner.container_name(argv)
    assert name.startswith(smoke_module.WORKSPACE_PREFIX)
    assert argv[5 : 5 + len(RUNNER_CONTAINER_CONTAINMENT_ARGUMENTS)] == (
        RUNNER_CONTAINER_CONTAINMENT_ARGUMENTS
    )
    assert argv[-5:] == (DEFAULT_DEFECTS4J_RUNNER_IMAGE, "defects4j", "info", "-p", project)
    assert "--volume" not in argv
    # The java probe runs inside the same configured container runtime.
    java_calls = [
        call for call in runner.calls if runner.inner_argv(call)[:1] == ("java",)
    ]
    assert len(java_calls) == 1
    assert runner.inner_argv(java_calls[0]) == ("java", "-version")
    assert "--volume" not in java_calls[0].argv


def test_container_mode_maps_each_case_workspace_and_keeps_inner_commands_valid(
    isolated_boundary_root,
):
    """checkout/compile/test/export use the mapped CONTAINER workspace while
    the outer bind mount uses each case's own HOST workspace."""
    runner = DockerScriptedRunner(DEFAULT_DEFECTS4J_RUNNER_IMAGE, happy_outcomes())
    run = run_smoke(runner, boundary=make_container_boundary(isolated_boundary_root))
    assert run.status == "PASS"
    host_paths = [str(case.workspace_path) for case in run.cases]
    assert len(set(host_paths)) == 3

    per_case: dict[str, list[tuple[str, ...]]] = {}
    for call in runner.calls:
        for spec in volume_specs(call):
            host_side = spec.rsplit(":", 1)[0]
            assert spec.endswith(f":{RUNNER_IMAGE_WORKSPACE}")
            per_case.setdefault(host_side, []).append(runner.inner_argv(call))
    assert set(per_case) == set(host_paths)

    names = [DockerScriptedRunner.container_name(call.argv) for call in runner.calls]
    assert len(set(names)) == len(names)

    for case in run.cases:
        spec = f"{case.workspace_path}:{RUNNER_IMAGE_WORKSPACE}"
        inners = per_case[str(case.workspace_path)]
        mount_call = next(
            call for call in runner.calls if spec in volume_specs(call)
        )
        argv = mount_call.argv
        assert argv[list(argv).index("--volume") + 2 :] and (
            argv[list(argv).index("--workdir") + 1] == RUNNER_IMAGE_WORKSPACE
        )
        assert case.workspace_path is not None
        assert mount_call.cwd == str(case.workspace_path)
        checkout_inner = next(
            i for i in inners if i[:2] == ("defects4j", "checkout")
        )
        compile_inner = next(i for i in inners if i[:2] == ("defects4j", "compile"))
        test_inner = next(i for i in inners if i[:2] == ("defects4j", "test"))
        export_inner = next(i for i in inners if i[:2] == ("defects4j", "export"))
        assert checkout_inner == (
            "defects4j",
            "checkout",
            "-p",
            case.project,
            "-v",
            case.buggy_version_id,
            "-w",
            RUNNER_IMAGE_WORKSPACE,
        )
        assert compile_inner == ("defects4j", "compile", "-w", RUNNER_IMAGE_WORKSPACE)
        assert test_inner == ("defects4j", "test", "-w", RUNNER_IMAGE_WORKSPACE)
        assert export_inner == (
            "defects4j",
            "export",
            "-p",
            "tests.trigger",
            "-w",
            RUNNER_IMAGE_WORKSPACE,
        )


def test_three_cases_get_independent_mounts_and_unique_containers(
    isolated_boundary_root,
):
    runner = DockerScriptedRunner(DEFAULT_DEFECTS4J_RUNNER_IMAGE, happy_outcomes())
    run = run_smoke(runner, boundary=make_container_boundary(isolated_boundary_root))
    specs_per_case = {
        str(case.workspace_path): f"{case.workspace_path}:{RUNNER_IMAGE_WORKSPACE}"
        for case in run.cases
    }
    assert len(specs_per_case) == 3
    mounted = {spec for call in runner.calls for spec in volume_specs(call)}
    assert mounted == set(specs_per_case.values())
    # One case must never see another case's checkout.
    for call in runner.calls:
        for spec in volume_specs(call):
            assert spec.count(":") >= 1
            host_side = spec.rsplit(":", 1)[0]
            assert host_side in specs_per_case


def test_configured_container_runtime_never_reports_false_tool_missing(
    isolated_boundary_root,
):
    """No host defects4j binary exists in this scenario at all; only the
    configured Deployment container answers -- so RUNTIME_TOOL_MISSING must
    not appear anywhere."""
    runner = DockerScriptedRunner(DEFAULT_DEFECTS4J_RUNNER_IMAGE, happy_outcomes())
    run = run_smoke(runner, boundary=make_container_boundary(isolated_boundary_root))
    assert run.status == "PASS"
    assert all(
        case.failure_class is not FailureClassification.RUNTIME_TOOL_MISSING
        for case in run.cases
    )

    blocked_runner = DockerScriptedRunner(
        DEFAULT_DEFECTS4J_RUNNER_IMAGE, gate_only_outcomes()
    )
    blocked = run_smoke(
        blocked_runner,
        boundary=make_container_boundary(
            isolated_boundary_root, defects4j_release_reader=None
        ),
    )
    assert blocked.status == "ENVIRONMENT_BLOCKED"
    assert all(
        case.failure_class is FailureClassification.DEFECTS4J_VERSION_MISMATCH
        for case in blocked.cases
    )
    assert all(
        case.failure_class is not FailureClassification.RUNTIME_TOOL_MISSING
        for case in blocked.cases
    )
    assert not any(
        blocked_runner.inner_argv(call)[:2] == ("defects4j", "checkout")
        for call in blocked_runner.calls
    )


def test_operable_container_without_attestation_still_fails_closed(
    isolated_boundary_root,
):
    """The image answers, but no objective release attestation is bound:
    the exact-version gate refuses to pass (honest ENVIRONMENT_BLOCKED)."""
    runner = DockerScriptedRunner(
        DEFAULT_DEFECTS4J_RUNNER_IMAGE, happy_outcomes()
    )
    run = run_smoke(
        runner,
        boundary=make_container_boundary(
            isolated_boundary_root, defects4j_release_reader=None
        ),
    )
    assert run.status == "ENVIRONMENT_BLOCKED"
    assert run.environment.observed_defects4j_version is None
    assert (
        run.environment.defects4j_identity_provenance
        == DEFECTS4J_IDENTITY_PROVENANCE_UNAVAILABLE
    )
    assert all(
        case.failure_class is FailureClassification.DEFECTS4J_VERSION_MISMATCH
        for case in run.cases
    )
    assert not any(
        runner.inner_argv(call)[:2] == ("defects4j", "checkout") for call in runner.calls
    )


def test_objective_image_attestation_enables_the_exact_version_gate(
    isolated_boundary_root,
):
    """Binding the read-only image-tag reader keeps existing exact-version
    semantics: v-prefixed tag normalized, wrong release still rejected."""
    def outcomes_with_tag(tag_stdout):
        outcomes = happy_outcomes()
        outcomes[("git", "-c")] = Outcome(stdout_text=tag_stdout)
        return outcomes

    runner = DockerScriptedRunner(
        DEFAULT_DEFECTS4J_RUNNER_IMAGE, outcomes_with_tag("v3.0.1\n")
    )
    reader = smoke_module.deployment_image_release_reader(
        runner=runner,
        transport=DockerContainerTransport(image=DEFAULT_DEFECTS4J_RUNNER_IMAGE),
        env=build_child_environment({"PATH": "/usr/bin:/bin"}),
    )
    run = run_smoke(
        runner,
        boundary=make_container_boundary(
            isolated_boundary_root, defects4j_release_reader=reader
        ),
    )
    assert run.status == "PASS"
    assert run.environment.observed_defects4j_version == "3.0.1"
    assert (
        run.environment.defects4j_identity_provenance
        == DEFECTS4J_IDENTITY_PROVENANCE_DEPLOYMENT_ATTESTED
    )

    wrong_runner = DockerScriptedRunner(
        DEFAULT_DEFECTS4J_RUNNER_IMAGE, outcomes_with_tag("v2.2.0\n")
    )
    wrong_reader = smoke_module.deployment_image_release_reader(
        runner=wrong_runner,
        transport=DockerContainerTransport(image=DEFAULT_DEFECTS4J_RUNNER_IMAGE),
        env=build_child_environment({"PATH": "/usr/bin:/bin"}),
    )
    wrong = run_smoke(
        wrong_runner,
        boundary=make_container_boundary(
            isolated_boundary_root, defects4j_release_reader=wrong_reader
        ),
    )
    assert wrong.status == "ENVIRONMENT_BLOCKED"
    assert wrong.environment.observed_defects4j_version == "2.2.0"
    assert all(
        case.failure_class is FailureClassification.DEFECTS4J_VERSION_MISMATCH
        for case in wrong.cases
    )
    assert not any(
        wrong_runner.inner_argv(call)[:2] == ("defects4j", "checkout")
        for call in wrong_runner.calls
    )


def test_image_release_reader_is_read_only_and_fails_closed():
    transport = DockerContainerTransport(image=DEFAULT_DEFECTS4J_RUNNER_IMAGE)

    def reader_for(outcome: Outcome):
        runner = DockerScriptedRunner(DEFAULT_DEFECTS4J_RUNNER_IMAGE, {})
        runner._outcomes[("git", "-c")] = outcome
        reader = smoke_module.deployment_image_release_reader(
            runner=runner,
            transport=transport,
            env={"PATH": "/usr/bin:/bin"},
        )
        return reader, runner

    reader, runner = reader_for(Outcome(stdout_text="v3.0.1\n"))
    assert reader() == REQUIRED_DEFECTS4J_VERSION
    git_call = runner.calls[0]
    inner = runner.inner_argv(git_call)
    assert inner[:3] == ("git", "-c", f"safe.directory={RUNNER_IMAGE_FRAMEWORK_HOME}")
    assert inner[3:6] == ("-C", RUNNER_IMAGE_FRAMEWORK_HOME, "tag")
    assert inner[6:] == ("--points-at", "HEAD")
    assert "--volume" not in git_call.argv

    for outcome in (
        Outcome(stdout_text=""),
        Outcome(stdout_text="v3.0.1\nv3.0.1-rc1\n"),
        Outcome(exit_code=128, stderr_text="fatal: not a git repository"),
        Outcome(timed_out=True, exit_code=None),
        Outcome(spawn_error="ENOENT"),
    ):
        ambiguous_reader, _ = reader_for(outcome)
        assert ambiguous_reader() is None

    with pytest.raises(SmokeHarnessError, match="container"):
        smoke_module.deployment_image_release_reader(
            runner=ScriptedRunner({}),
            transport=HostExecutableTransport(),
            env={"PATH": "/usr/bin:/bin"},
        )


def test_container_timeout_aborts_exactly_the_named_container(isolated_boundary_root):
    outcomes = happy_outcomes()
    outcomes[("defects4j", "compile")] = Outcome(timed_out=True, exit_code=None)
    runner = DockerScriptedRunner(DEFAULT_DEFECTS4J_RUNNER_IMAGE, outcomes)
    run = run_smoke(runner, boundary=make_container_boundary(isolated_boundary_root))
    assert run.status == "FAIL"
    assert all(case.failure_class is FailureClassification.TIMEOUT for case in run.cases)
    compile_calls = [
        call
        for call in runner.calls
        if runner.inner_argv(call)[:2] == ("defects4j", "compile")
    ]
    assert len(compile_calls) == 3
    assert len(runner.abort_calls) == 3
    for compile_call, abort_call in zip(compile_calls, runner.abort_calls):
        name = DockerScriptedRunner.container_name(compile_call.argv)
        assert abort_call.argv == ("docker", "rm", "--force", name)
        assert abort_call.timeout_seconds == DEFAULT_ABORT_TIMEOUT_SECONDS > 0
        assert abort_call.stdout_limit_bytes == ABORT_OUTPUT_LIMIT_BYTES
        assert abort_call.stderr_limit_bytes == ABORT_OUTPUT_LIMIT_BYTES
        assert abort_call.env["TZ"] == "America/Los_Angeles"
    facts = run.cases[0].to_semantic_dict()["compile"]
    assert facts["timed_out"] is True
    assert facts["timeout_abort"]["attempted"] is True
    assert facts["timeout_abort"]["exit_code"] == 0

    successful = DockerScriptedRunner(
        DEFAULT_DEFECTS4J_RUNNER_IMAGE, happy_outcomes()
    )
    ok_run = run_smoke(
        successful, boundary=make_container_boundary(isolated_boundary_root)
    )
    assert ok_run.status == "PASS"
    assert successful.abort_calls == []


def test_failed_abort_never_masks_the_timeout_classification(
    isolated_boundary_root,
):
    outcomes = happy_outcomes()
    outcomes[("defects4j", "test")] = Outcome(timed_out=True, exit_code=None)
    runner = DockerScriptedRunner(
        DEFAULT_DEFECTS4J_RUNNER_IMAGE,
        outcomes,
        abort_spawn_error="ENOENT",
        abort_exit_code=None,
    )
    run = run_smoke(runner, boundary=make_container_boundary(isolated_boundary_root))
    assert run.status == "FAIL"
    assert all(case.failure_class is FailureClassification.TIMEOUT for case in run.cases)
    facts = run.cases[0].to_semantic_dict()["test"]
    assert facts["timeout_abort"]["attempted"] is True
    assert facts["timeout_abort"]["spawn_error"] == "ENOENT"


def test_container_mode_child_environment_and_timeouts_stay_bounded(
    isolated_boundary_root,
):
    runner = DockerScriptedRunner(DEFAULT_DEFECTS4J_RUNNER_IMAGE, happy_outcomes())
    boundary = make_container_boundary(isolated_boundary_root)
    run_smoke(runner, boundary=boundary)
    assert runner.calls
    for call in runner.calls + runner.abort_calls:
        assert call.timeout_seconds > 0
        assert call.stdout_limit_bytes == boundary.output_limit_bytes
        assert call.stderr_limit_bytes == boundary.output_limit_bytes
        assert call.env["TZ"] == "America/Los_Angeles"
        assert "TESTGAP_SECRET" not in call.env
    per_subcommand: dict[tuple[str, ...], set[float]] = {}
    for call in runner.calls:
        key = runner.inner_argv(call)[:2]
        per_subcommand.setdefault(key, set()).add(call.timeout_seconds)
    assert per_subcommand[("java", "-version")] == {boundary.probe_timeout_seconds}
    assert per_subcommand[("defects4j", "info")] == {boundary.probe_timeout_seconds}
    assert per_subcommand[("defects4j", "checkout")] == {
        boundary.checkout_timeout_seconds
    }
    assert per_subcommand[("defects4j", "compile")] == {
        boundary.compile_timeout_seconds
    }
    assert per_subcommand[("defects4j", "test")] == {boundary.test_timeout_seconds}
    assert per_subcommand[("defects4j", "export")] == {
        boundary.trigger_export_timeout_seconds
    }
