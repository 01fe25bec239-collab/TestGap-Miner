"""Deterministic parsing, validation and canonical serialization for the frozen
Defects4J golden benchmark manifest.

Standard library only. The manifest is a small fixed-shape document whose whole
point is to be immutable and reproducible, so a schema dependency would buy
nothing that ~300 lines of explicit checks do not already give us -- and every
rejection here carries an actionable message instead of a generic schema path.

CLI:

    python -m evaluation.defects4j_manifest validate benchmarks/defects4j/DEFECTS4J_MVP_V1.json
    python -m evaluation.defects4j_manifest canonicalize benchmarks/defects4j/DEFECTS4J_MVP_V1.json
    python -m evaluation.defects4j_manifest checksum benchmarks/defects4j/DEFECTS4J_MVP_V1.json

`canonicalize` writes to stdout only; nothing in this module rewrites a
checked-in manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable, Iterable

SCHEMA_VERSION = "testgap.defects4j.golden-manifest.v1"
MANIFEST_VERSION = "DEFECTS4J_MVP_V1"
CORPUS = "DEFECTS4J_3_0_1"
DEFECTS4J_RELEASE = "3.0.1"
SELECTION_METHODOLOGY_ID = "STRATIFIED_PROJECT_POSITION_V1"

# Java-only / JUnit-only MVP, per the authoritative PRD.
SUPPORTED_LANGUAGES = ("JAVA",)
SUPPORTED_TEST_ECOSYSTEMS = ("JUNIT",)
REQUIRED_JAVA_MAJOR = 11
REQUIRED_TIMEZONE = "America/Los_Angeles"

VERIFICATION_STATES = ("VERIFIED", "UNVERIFIED")
EXCLUSION_STATES = ("NOT_EXCLUDED", "EXCLUDED")
VCS_TYPES = ("GIT", "SVN", "UNKNOWN")

IMMUTABILITY_POLICY = (
    "After A2 acceptance, DEFECTS4J_MVP_V1.json bytes and DEFECTS4J_MVP_V1.sha256 "
    "are immutable. Future runtime verification must be recorded as separately versioned "
    "evidence bound to DEFECTS4J_MVP_V1; no UNVERIFIED metadata may be promoted in place. "
    "Any golden-manifest change requires a new explicit manifest version "
    "(DEFECTS4J_MVP_V2 or later) under future authorization."
)
MEDIAN_ORDINAL_FORMULA = "floor((N + 1) / 2)"
MEDIAN_EVEN_N_POLICY = "LOWER_OF_TWO_MIDDLE_ACTIVE_BUGS"

EXPECTED_SELECTION_PROVENANCE = {
    "active_sets": [
        {"active_bug_count": 26, "active_bug_ids": "1-26", "median_bug_id": 13, "median_ordinal": 13, "project": "Chart"},
        {"active_bug_count": 18, "active_bug_ids": "1-18", "median_bug_id": 9, "median_ordinal": 9, "project": "Gson"},
        {"active_bug_count": 93, "active_bug_ids": "1-93", "median_bug_id": 47, "median_ordinal": 47, "project": "Jsoup"},
        {"active_bug_count": 61, "active_bug_ids": "1,3-17,19-24,26-47,49-65", "median_bug_id": 34, "median_ordinal": 31, "project": "Lang"},
        {"active_bug_count": 106, "active_bug_ids": "1-106", "median_bug_id": 53, "median_ordinal": 53, "project": "Math"},
        {"active_bug_count": 26, "active_bug_ids": "1-20,22-27", "median_bug_id": 13, "median_ordinal": 13, "project": "Time"},
    ],
    "first_ordinal": 1,
    "metadata_sources": ["README active-bug table", "framework/projects/<Project>/active-bugs.csv"],
    "scope": "CASE_MEMBERSHIP_ONLY",
    "upstream_project": "rjust/defects4j",
    "upstream_ref": "v3.0.1",
    "verification": "INDEPENDENTLY_CHECKED",
}

_COMMIT_SHA = re.compile(r"\A[0-9a-f]{40}\Z")


class ManifestValidationError(ValueError):
    """Raised with every validation failure found, not just the first."""

    def __init__(self, errors: Iterable[str]) -> None:
        self.errors = list(errors)
        joined = "\n".join(f"  - {error}" for error in self.errors)
        super().__init__(f"{len(self.errors)} manifest validation error(s):\n{joined}")


# --------------------------------------------------------------------------
# parsing / canonical serialization
# --------------------------------------------------------------------------


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError(f"duplicate JSON key {key!r}")
        seen[key] = value
    return seen


def parse(text: str) -> dict[str, Any]:
    """Parse manifest JSON. Duplicate keys are an error, never a silent overwrite."""
    return json.loads(text, object_pairs_hook=_reject_duplicate_keys)


def canonical_json(manifest: Any) -> str:
    """Canonical form: UTF-8, 2-space indent, sorted keys, one final newline.

    Deliberately free of timestamps and absolute paths so the same logical
    manifest always serializes to the same bytes on any machine.
    """
    return json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_recorded_checksum(checksum_path: Path) -> str:
    """Read a `<sha256>  <filename>` sidecar (the `shasum -a 256` format)."""
    fields = checksum_path.read_text(encoding="utf-8").split()
    if not fields or not re.fullmatch(r"[0-9a-f]{64}", fields[0]):
        raise ManifestValidationError(
            [f"{checksum_path.name}: does not start with a 64-character lowercase hex SHA-256 digest"]
        )
    return fields[0]


# --------------------------------------------------------------------------
# validation helpers
# --------------------------------------------------------------------------


def _non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _check_verified_scalar(
    where: str,
    node: Any,
    label: str,
    errors: list[str],
    *,
    validator: Callable[[str], bool] | None = None,
    expectation: str = "",
) -> str | None:
    """Validate a `{"status": VERIFIED|UNVERIFIED, "value": ...}` envelope.

    Returns the value only when it is VERIFIED and well formed. UNVERIFIED must
    carry a null value: that is what keeps unverified metadata from masquerading
    as fact.
    """
    if not isinstance(node, dict):
        errors.append(f"{where}: {label} is missing or is not an object")
        return None
    status = node.get("status")
    if status not in VERIFICATION_STATES:
        errors.append(
            f"{where}: {label}.status {status!r} is invalid; expected one of {list(VERIFICATION_STATES)}"
        )
        return None
    if "value" not in node:
        errors.append(f"{where}: {label}.value is missing")
        return None
    value = node["value"]
    if status == "UNVERIFIED":
        if value is not None:
            errors.append(
                f"{where}: {label}.status is UNVERIFIED so {label}.value must be null, got {value!r}"
            )
        return None
    if not _non_empty_str(value):
        errors.append(
            f"{where}: {label}.status is VERIFIED so {label}.value must be a non-empty string, got {value!r}"
        )
        return None
    if validator is not None and not validator(value):
        errors.append(f"{where}: {label}.value {value!r} is malformed{expectation}")
        return None
    return value


def _check_revision(
    where: str,
    case: dict[str, Any],
    key: str,
    suffix: str,
    bug_id: int | None,
    errors: list[str],
) -> tuple[str | None, tuple[str, str] | None]:
    """Validate one revision node. Returns (canonical ID, verified VCS revision)."""
    revision = case.get(key)
    if not isinstance(revision, dict):
        errors.append(f"{where}: {key} is missing or is not an object")
        return None, None

    version_id = revision.get("defects4j_version_id")
    if not _non_empty_str(version_id):
        errors.append(f"{where}: {key}.defects4j_version_id is missing or empty")
        version_id = None
    elif bug_id is not None:
        expected = f"{bug_id}{suffix}"
        if version_id != expected:
            errors.append(
                f"{where}: {key}.defects4j_version_id {version_id!r} does not match bug_id "
                f"{bug_id}; expected {expected!r}"
            )

    source = revision.get("source_revision")
    value = _check_verified_scalar(
        where, source, f"{key}.source_revision", errors
    )
    if not isinstance(source, dict):
        return version_id, None
    vcs = source.get("vcs")
    if vcs not in VCS_TYPES:
        errors.append(
            f"{where}: {key}.source_revision.vcs {vcs!r} is invalid; expected one of {list(VCS_TYPES)}"
        )
        return version_id, None
    if source.get("status") == "VERIFIED" and vcs == "UNKNOWN":
        errors.append(f"{where}: {key}.source_revision.vcs must be GIT or SVN when VERIFIED")
        return version_id, None
    if value is not None and vcs == "GIT" and not _COMMIT_SHA.match(value):
        errors.append(
            f"{where}: {key}.source_revision.value {value!r} is malformed; "
            "expected a 40-character lowercase hex commit SHA when vcs is GIT"
        )
        return version_id, None
    return version_id, (vcs, value) if value is not None else None


def _check_triggering_tests(where: str, case: dict[str, Any], errors: list[str]) -> None:
    node = case.get("triggering_tests")
    if not isinstance(node, dict):
        errors.append(f"{where}: triggering_tests is missing or is not an object")
        return
    status = node.get("status")
    if status not in VERIFICATION_STATES:
        errors.append(
            f"{where}: triggering_tests.status {status!r} is invalid; "
            f"expected one of {list(VERIFICATION_STATES)}"
        )
    values = node.get("values")
    if not isinstance(values, list) or not all(_non_empty_str(value) for value in values):
        errors.append(f"{where}: triggering_tests.values must be a list of non-empty strings")
        return

    if status == "VERIFIED" and not values:
        errors.append(f"{where}: triggering_tests.status is VERIFIED but values is empty")
    # An UNVERIFIED status must carry no tests at all; otherwise the manifest
    # would be recording test names nobody confirmed against Defects4J.
    if status == "UNVERIFIED" and values:
        errors.append(
            f"{where}: triggering_tests.status is UNVERIFIED so values must be empty, got {values!r}"
        )
    if len(set(values)) != len(values):
        duplicates = sorted({value for value in values if values.count(value) > 1})
        errors.append(f"{where}: triggering_tests.values contains duplicates: {duplicates}")
    if values != sorted(values):
        errors.append(
            f"{where}: triggering_tests.values must be sorted ascending for deterministic ordering"
        )


def _check_exclusion(where: str, case: dict[str, Any], errors: list[str]) -> None:
    selected = case.get("selected")
    state = case.get("exclusion_state")
    reason = case.get("exclusion_reason", "__missing__")

    if not isinstance(selected, bool):
        errors.append(f"{where}: selected must be a boolean, got {selected!r}")
    if state not in EXCLUSION_STATES:
        errors.append(
            f"{where}: exclusion_state {state!r} is invalid; expected one of {list(EXCLUSION_STATES)}"
        )
    if reason == "__missing__":
        errors.append(f"{where}: exclusion_reason is missing (use null when not excluded)")
        return

    if selected is True and state == "EXCLUDED":
        errors.append(f"{where}: selected is true but exclusion_state is EXCLUDED")
    if selected is False and state == "NOT_EXCLUDED":
        errors.append(f"{where}: selected is false but exclusion_state is NOT_EXCLUDED")
    if state == "EXCLUDED" and not _non_empty_str(reason):
        errors.append(f"{where}: exclusion_state is EXCLUDED but exclusion_reason is empty")
    if state == "NOT_EXCLUDED" and reason is not None:
        errors.append(
            f"{where}: exclusion_state is NOT_EXCLUDED so exclusion_reason must be null, got {reason!r}"
        )


def _check_case(
    case: Any, index: int, manifest_version: Any, errors: list[str]
) -> tuple[str | None, tuple[str, int] | None]:
    where = f"cases[{index}]"
    if not isinstance(case, dict):
        errors.append(f"{where}: expected a JSON object")
        return None, None

    case_id = case.get("benchmark_case_id")
    if _non_empty_str(case_id):
        where = f"case {case_id}"
    else:
        errors.append(f"{where}: benchmark_case_id is missing or empty")
        case_id = None

    project = case.get("project")
    if not _non_empty_str(project):
        errors.append(f"{where}: project is missing or empty")
        project = None

    bug_id = case.get("bug_id")
    if isinstance(bug_id, bool) or not isinstance(bug_id, int) or bug_id < 1:
        errors.append(f"{where}: bug_id is missing or is not a positive integer, got {bug_id!r}")
        bug_id = None

    if case.get("language") not in SUPPORTED_LANGUAGES:
        errors.append(
            f"{where}: language {case.get('language')!r} is unsupported; "
            f"expected one of {list(SUPPORTED_LANGUAGES)}"
        )
    if case.get("test_ecosystem") not in SUPPORTED_TEST_ECOSYSTEMS:
        errors.append(
            f"{where}: test_ecosystem {case.get('test_ecosystem')!r} is unsupported; "
            f"expected one of {list(SUPPORTED_TEST_ECOSYSTEMS)}"
        )
    if case.get("manifest_version") != manifest_version:
        errors.append(
            f"{where}: manifest_version {case.get('manifest_version')!r} does not match the "
            f"manifest-level version {manifest_version!r}"
        )

    buggy_id, buggy_source = _check_revision(where, case, "buggy_revision", "b", bug_id, errors)
    fixed_id, fixed_source = _check_revision(where, case, "fixed_revision", "f", bug_id, errors)
    if buggy_id is not None and buggy_id == fixed_id:
        errors.append(
            f"{where}: buggy and fixed defects4j_version_id are identical ({buggy_id!r})"
        )
    if buggy_source is not None and buggy_source == fixed_source:
        errors.append(
            f"{where}: the same verified source revision {buggy_source!r} is recorded as both the "
            "buggy and the fixed revision"
        )

    _check_triggering_tests(where, case, errors)
    _check_exclusion(where, case, errors)
    _check_verified_scalar(where, case.get("failure_shape"), "failure_shape", errors)

    if not _non_empty_str(case.get("selection_reason")):
        errors.append(f"{where}: selection_reason is missing or empty")
    if not _non_empty_str(case.get("domain_category")):
        errors.append(f"{where}: domain_category is missing or empty")

    provenance = case.get("metadata_provenance")
    if not isinstance(provenance, dict) or not provenance:
        errors.append(f"{where}: metadata_provenance is missing or is not a non-empty object")
    elif not all(_non_empty_str(value) for value in provenance.values()):
        errors.append(f"{where}: every metadata_provenance value must be a non-empty string")

    identity = (project, bug_id) if project is not None and bug_id is not None else None
    return case_id, identity


def _check_header(manifest: dict[str, Any], errors: list[str]) -> None:
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(
            f"schema_version {manifest.get('schema_version')!r} is unrecognized; "
            f"expected {SCHEMA_VERSION!r}"
        )
    if not _non_empty_str(manifest.get("manifest_version")):
        errors.append("manifest_version is missing or empty; the manifest must be explicitly versioned")
    if manifest.get("corpus") != CORPUS:
        errors.append(f"corpus {manifest.get('corpus')!r} is unrecognized; expected {CORPUS!r}")
    if manifest.get("defects4j_release") != DEFECTS4J_RELEASE:
        errors.append(
            f"defects4j_release {manifest.get('defects4j_release')!r} is unrecognized; "
            f"expected {DEFECTS4J_RELEASE!r}"
        )
    if manifest.get("language") not in SUPPORTED_LANGUAGES:
        errors.append(
            f"language {manifest.get('language')!r} is unsupported; expected one of {list(SUPPORTED_LANGUAGES)}"
        )
    if manifest.get("test_ecosystem") not in SUPPORTED_TEST_ECOSYSTEMS:
        errors.append(
            f"test_ecosystem {manifest.get('test_ecosystem')!r} is unsupported; "
            f"expected one of {list(SUPPORTED_TEST_ECOSYSTEMS)}"
        )
    if manifest.get("required_java_major") != REQUIRED_JAVA_MAJOR:
        errors.append(
            f"required_java_major {manifest.get('required_java_major')!r} is wrong; "
            f"Defects4J execution requires {REQUIRED_JAVA_MAJOR}"
        )
    if manifest.get("required_timezone") != REQUIRED_TIMEZONE:
        errors.append(
            f"required_timezone {manifest.get('required_timezone')!r} is wrong; "
            f"expected {REQUIRED_TIMEZONE!r}"
        )

    immutability = manifest.get("immutability")
    if not isinstance(immutability, dict):
        errors.append("immutability is missing or is not an object")
    else:
        expected = {
            "checksum_algorithm": "SHA-256",
            "checksum_file": "DEFECTS4J_MVP_V1.sha256",
            "policy": IMMUTABILITY_POLICY,
            "state": "FROZEN_ON_ACCEPTANCE",
        }
        if immutability != expected:
            errors.append("immutability must declare the strict DEFECTS4J_MVP_V1 byte policy")

    provenance = manifest.get("provenance")
    if not isinstance(provenance, dict) or not provenance:
        errors.append("provenance is missing or is not a non-empty object")
    elif not all(_non_empty_str(value) for value in provenance.values()):
        errors.append("every provenance value must be a non-empty string")


def _check_selection(manifest: dict[str, Any], errors: list[str]) -> None:
    selection = manifest.get("selection")
    if not isinstance(selection, dict):
        errors.append("selection is missing or is not an object")
        return
    if selection.get("methodology_id") != SELECTION_METHODOLOGY_ID:
        errors.append(
            f"selection.methodology_id {selection.get('methodology_id')!r} is unrecognized; "
            f"expected {SELECTION_METHODOLOGY_ID!r}"
        )
    if not _non_empty_str(selection.get("description")):
        errors.append("selection.description is missing or empty")
    if selection.get("frozen_before_model_outcomes") is not True:
        errors.append(
            "selection.frozen_before_model_outcomes must be true; case selection must predate "
            "any TestGap Miner model benchmark outcome"
        )
    if not _non_empty_str(selection.get("no_result_cherry_picking")):
        errors.append("selection.no_result_cherry_picking is missing or empty")
    if selection.get("first_ordinal") != 1:
        errors.append("selection.first_ordinal must be 1")
    if selection.get("median_ordinal_formula") != MEDIAN_ORDINAL_FORMULA:
        errors.append(f"selection.median_ordinal_formula must be {MEDIAN_ORDINAL_FORMULA!r}")
    if selection.get("median_even_n_policy") != MEDIAN_EVEN_N_POLICY:
        errors.append(f"selection.median_even_n_policy must be {MEDIAN_EVEN_N_POLICY!r}")
    if selection.get("provenance") != EXPECTED_SELECTION_PROVENANCE:
        errors.append("selection.provenance must match the independently checked Defects4J v3.0.1 active-bug metadata")

    strata = selection.get("strata")
    if not isinstance(strata, list) or not strata:
        errors.append("selection.strata must be a non-empty list")
        return
    projects: list[str] = []
    for index, stratum in enumerate(strata):
        if not isinstance(stratum, dict):
            errors.append(f"selection.strata[{index}]: expected a JSON object")
            continue
        if not _non_empty_str(stratum.get("project")):
            errors.append(f"selection.strata[{index}]: project is missing or empty")
        else:
            projects.append(stratum["project"])
        if not _non_empty_str(stratum.get("domain_category")):
            errors.append(f"selection.strata[{index}]: domain_category is missing or empty")
    duplicates = sorted({p for p in projects if projects.count(p) > 1})
    if duplicates:
        errors.append(f"selection.strata contains duplicate projects: {duplicates}")


def _check_cases(manifest: dict[str, Any], errors: list[str]) -> None:
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append("cases must be a non-empty list")
        return

    manifest_version = manifest.get("manifest_version")
    case_ids: list[str] = []
    identities: list[tuple[str, int]] = []
    for index, case in enumerate(cases):
        case_id, identity = _check_case(case, index, manifest_version, errors)
        if case_id is not None:
            case_ids.append(case_id)
        if identity is not None:
            identities.append(identity)

    duplicate_ids = sorted({c for c in case_ids if case_ids.count(c) > 1})
    if duplicate_ids:
        errors.append(f"cases: duplicate benchmark_case_id: {duplicate_ids}")

    duplicate_identities = sorted({i for i in identities if identities.count(i) > 1})
    if duplicate_identities:
        errors.append(
            "cases: duplicate project/bug_id identity: "
            + ", ".join(f"{project}-{bug_id}" for project, bug_id in duplicate_identities)
        )

    if case_ids != sorted(case_ids):
        errors.append(
            "cases must be ordered by benchmark_case_id ascending for deterministic serialization"
        )

    smoke_ids = manifest.get("smoke_case_ids")
    if not isinstance(smoke_ids, list) or not smoke_ids or not all(_non_empty_str(s) for s in smoke_ids):
        errors.append("smoke_case_ids must be a non-empty list of non-empty strings")
        return
    if smoke_ids != sorted(smoke_ids):
        errors.append("smoke_case_ids must be sorted ascending for deterministic ordering")
    if len(set(smoke_ids)) != len(smoke_ids):
        errors.append("smoke_case_ids contains duplicates")
    unknown = sorted(set(smoke_ids) - set(case_ids))
    if unknown:
        errors.append(f"smoke_case_ids references cases that are not in the manifest: {unknown}")


def _check_filename(manifest: dict[str, Any], path: Path, errors: list[str]) -> None:
    if path.stem != manifest.get("manifest_version"):
        errors.append(
            f"manifest filename {path.name!r} does not match manifest_version "
            f"{manifest.get('manifest_version')!r}"
        )


def validate(manifest: Any, *, path: Path | str | None = None) -> None:
    """Validate a parsed manifest. Raises ManifestValidationError listing every problem."""
    if not isinstance(manifest, dict):
        raise ManifestValidationError(["manifest: expected a JSON object at the top level"])

    errors: list[str] = []
    _check_header(manifest, errors)
    _check_selection(manifest, errors)
    _check_cases(manifest, errors)
    if path is not None:
        _check_filename(manifest, Path(path), errors)
    if errors:
        raise ManifestValidationError(errors)


def load(path: Path | str) -> dict[str, Any]:
    """Parse and validate a manifest file. Does not check canonical form or checksum."""
    path = Path(path)
    manifest = parse(path.read_text(encoding="utf-8"))
    validate(manifest, path=path)
    return manifest


def verify_file(path: Path | str) -> dict[str, Any]:
    """Full check: structure, canonical form on disk, and the recorded SHA-256."""
    path = Path(path)
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    manifest = parse(text)
    validate(manifest, path=path)

    errors: list[str] = []
    if text != canonical_json(manifest):
        errors.append(
            f"{path.name}: file is not in canonical form; run "
            f"`python -m evaluation.defects4j_manifest canonicalize {path}` to see the expected bytes"
        )

    checksum_path = path.with_suffix(".sha256")
    if not checksum_path.exists():
        errors.append(f"{checksum_path.name}: missing; the immutable manifest must record its SHA-256")
    else:
        actual = sha256_of_bytes(raw)
        recorded = read_recorded_checksum(checksum_path)
        if actual != recorded:
            errors.append(
                f"{checksum_path.name}: recorded digest {recorded} does not match the manifest "
                f"digest {actual}; V1 is immutable, so create a new manifest version instead of editing it"
            )
    if errors:
        raise ManifestValidationError(errors)
    return manifest


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m evaluation.defects4j_manifest")
    subcommands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("validate", "validate a manifest, its canonical form and its recorded checksum"),
        ("canonicalize", "print the canonical serialization to stdout (never writes the file)"),
        ("checksum", "print the SHA-256 of the manifest file as it is on disk"),
    ):
        subcommand = subcommands.add_parser(name, help=help_text)
        subcommand.add_argument("path", type=Path)

    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            verify_file(args.path)
            print(f"OK {args.path}: manifest is valid, canonical and checksum-matched")
        elif args.command == "canonicalize":
            sys.stdout.write(canonical_json(parse(args.path.read_text(encoding="utf-8"))))
        else:
            print(sha256_of_bytes(args.path.read_bytes()))
    except (ManifestValidationError, OSError, ValueError) as error:
        print(f"FAIL {args.path}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
