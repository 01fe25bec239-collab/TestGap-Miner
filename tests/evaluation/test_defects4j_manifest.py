"""Deterministic tests for the frozen Defects4J golden manifest.

No LLM call, no network, no Defects4J runtime: validating benchmark dataset
identity must never depend on the benchmark being installed.
"""

import copy
import json
from pathlib import Path

import pytest

from evaluation import defects4j_manifest as manifest_module

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "benchmarks" / "defects4j" / "DEFECTS4J_MVP_V1.json"
CHECKSUM_PATH = REPO_ROOT / "benchmarks" / "defects4j" / "DEFECTS4J_MVP_V1.sha256"
SOURCE_PATH = REPO_ROOT / "benchmarks" / "defects4j" / "SOURCE.md"
DOC_PATH = REPO_ROOT / "docs" / "evaluation" / "DEFECTS4J_MVP_V1.md"

FROZEN_CASE_IDS = [
    "D4J-CHART-001",
    "D4J-CHART-013",
    "D4J-GSON-001",
    "D4J-GSON-009",
    "D4J-JSOUP-001",
    "D4J-JSOUP-047",
    "D4J-LANG-001",
    "D4J-LANG-034",
    "D4J-MATH-001",
    "D4J-MATH-053",
    "D4J-TIME-001",
    "D4J-TIME-013",
]

PREDECLARED_SMOKE_CASE_IDS = ["D4J-GSON-001", "D4J-LANG-001", "D4J-MATH-001"]

SHA_A = "a" * 40
SHA_B = "b" * 40


@pytest.fixture
def manifest():
    return manifest_module.parse(MANIFEST_PATH.read_text(encoding="utf-8"))


def rejection(candidate) -> str:
    """Validate and return every error message joined, asserting it did fail."""
    with pytest.raises(manifest_module.ManifestValidationError) as raised:
        manifest_module.validate(candidate)
    return "\n".join(raised.value.errors)


def case_at(candidate, case_id):
    return next(case for case in candidate["cases"] if case["benchmark_case_id"] == case_id)


# --------------------------------------------------------------------------
# the checked-in V1 artifact
# --------------------------------------------------------------------------


def test_checked_in_manifest_is_valid_canonical_and_checksum_matched():
    manifest_module.verify_file(MANIFEST_PATH)


def test_valid_manifest_passes_validation(manifest):
    manifest_module.validate(manifest, path=MANIFEST_PATH)


def test_manifest_declares_the_frozen_identity(manifest):
    assert manifest["schema_version"] == "testgap.defects4j.golden-manifest.v1"
    assert manifest["manifest_version"] == "DEFECTS4J_MVP_V1"
    assert manifest["corpus"] == "DEFECTS4J_3_0_1"
    assert manifest["defects4j_release"] == "3.0.1"
    assert manifest["language"] == "JAVA"
    assert manifest["test_ecosystem"] == "JUNIT"
    assert manifest["required_java_major"] == 11
    assert manifest["required_timezone"] == "America/Los_Angeles"
    assert manifest["selection"]["methodology_id"] == "STRATIFIED_PROJECT_POSITION_V1"
    assert manifest["selection"]["frozen_before_model_outcomes"] is True
    assert manifest["selection"]["first_ordinal"] == 1
    assert manifest["selection"]["median_ordinal_formula"] == "floor((N + 1) / 2)"
    assert manifest["selection"]["median_even_n_policy"] == "LOWER_OF_TWO_MIDDLE_ACTIVE_BUGS"


def test_v1_declares_strict_byte_immutability(manifest):
    assert manifest["immutability"] == {
        "checksum_algorithm": "SHA-256",
        "checksum_file": "DEFECTS4J_MVP_V1.sha256",
        "policy": manifest_module.IMMUTABILITY_POLICY,
        "state": "FROZEN_ON_ACCEPTANCE",
    }


def test_no_post_acceptance_in_place_refinement_permission_remains(manifest):
    texts = [
        manifest["immutability"]["policy"],
        SOURCE_PATH.read_text(encoding="utf-8"),
        DOC_PATH.read_text(encoding="utf-8"),
    ]
    assert all("only permitted in-place refinement" not in text for text in texts)
    assert all("separately versioned evidence" in text for text in texts)


def test_permissive_in_place_refinement_policy_is_rejected(manifest):
    manifest["immutability"]["policy"] = (
        "Verifying previously UNVERIFIED metadata is permitted in place."
    )
    assert "strict DEFECTS4J_MVP_V1 byte policy" in rejection(manifest)


def test_selection_provenance_matches_defects4j_v3_0_1(manifest):
    assert manifest["selection"]["provenance"] == manifest_module.EXPECTED_SELECTION_PROVENANCE


def test_manifest_contains_exactly_the_twelve_frozen_cases(manifest):
    assert [case["benchmark_case_id"] for case in manifest["cases"]] == FROZEN_CASE_IDS


def test_every_frozen_case_is_selected_and_not_excluded(manifest):
    for case in manifest["cases"]:
        assert case["selected"] is True
        assert case["exclusion_state"] == "NOT_EXCLUDED"
        assert case["exclusion_reason"] is None


def test_predeclared_smoke_subset_is_frozen(manifest):
    assert manifest["smoke_case_ids"] == PREDECLARED_SMOKE_CASE_IDS


def test_v1_fabricates_no_triggering_tests_and_no_source_revisions(manifest):
    for case in manifest["cases"]:
        assert case["triggering_tests"] == {"status": "UNVERIFIED", "values": []}
        for key in ("buggy_revision", "fixed_revision"):
            assert case[key]["source_revision"] == {
                "status": "UNVERIFIED",
                "value": None,
                "vcs": "UNKNOWN",
            }


def test_canonical_revision_ids_follow_the_bug_id(manifest):
    for case in manifest["cases"]:
        bug_id = case["bug_id"]
        assert case["buggy_revision"]["defects4j_version_id"] == f"{bug_id}b"
        assert case["fixed_revision"]["defects4j_version_id"] == f"{bug_id}f"


# --------------------------------------------------------------------------
# case identity
# --------------------------------------------------------------------------


def test_duplicate_benchmark_case_id_is_rejected(manifest):
    manifest["cases"][1]["benchmark_case_id"] = manifest["cases"][0]["benchmark_case_id"]
    assert "duplicate benchmark_case_id" in rejection(manifest)


def test_duplicate_project_and_bug_identity_is_rejected(manifest):
    duplicate = manifest["cases"][1]
    duplicate["bug_id"] = manifest["cases"][0]["bug_id"]
    duplicate["buggy_revision"]["defects4j_version_id"] = "1b"
    duplicate["fixed_revision"]["defects4j_version_id"] = "1f"
    assert "duplicate project/bug_id identity: Chart-1" in rejection(manifest)


def test_missing_project_is_rejected(manifest):
    del manifest["cases"][0]["project"]
    assert "project is missing or empty" in rejection(manifest)


def test_missing_bug_id_is_rejected(manifest):
    del manifest["cases"][0]["bug_id"]
    assert "bug_id is missing or is not a positive integer" in rejection(manifest)


def test_missing_buggy_revision_is_rejected(manifest):
    del manifest["cases"][0]["buggy_revision"]
    assert "buggy_revision is missing or is not an object" in rejection(manifest)


def test_missing_fixed_revision_is_rejected(manifest):
    del manifest["cases"][0]["fixed_revision"]
    assert "fixed_revision is missing or is not an object" in rejection(manifest)


def test_revision_id_not_matching_the_bug_id_is_rejected(manifest):
    manifest["cases"][0]["buggy_revision"]["defects4j_version_id"] = "99b"
    assert "does not match bug_id 1; expected '1b'" in rejection(manifest)


def test_identical_buggy_and_fixed_revision_ids_are_rejected(manifest):
    case = manifest["cases"][0]
    case["fixed_revision"]["defects4j_version_id"] = "1b"
    assert "buggy and fixed defects4j_version_id are identical" in rejection(manifest)


def test_invalid_revision_relationship_representation_is_rejected(manifest):
    manifest["cases"][0]["buggy_revision"] = "1b"
    assert "buggy_revision is missing or is not an object" in rejection(manifest)


def test_malformed_git_source_revision_is_rejected(manifest):
    manifest["cases"][0]["buggy_revision"]["source_revision"] = {
        "status": "VERIFIED",
        "value": "not-a-sha",
        "vcs": "GIT",
    }
    assert "expected a 40-character lowercase hex commit SHA when vcs is GIT" in rejection(manifest)


def test_malformed_source_revision_vcs_is_rejected(manifest):
    manifest["cases"][0]["buggy_revision"]["source_revision"] = {
        "status": "VERIFIED",
        "value": "2264",
        "vcs": "CVS",
    }
    assert "source_revision.vcs 'CVS' is invalid" in rejection(manifest)


def test_unverified_source_revision_must_not_carry_a_value(manifest):
    manifest["cases"][0]["buggy_revision"]["source_revision"] = {
        "status": "UNVERIFIED",
        "value": SHA_A,
        "vcs": "UNKNOWN",
    }
    assert "UNVERIFIED so buggy_revision.source_revision.value must be null" in rejection(manifest)


def test_same_verified_source_revision_for_buggy_and_fixed_is_rejected(manifest):
    case = manifest["cases"][0]
    case["buggy_revision"]["source_revision"] = {
        "status": "VERIFIED",
        "value": SHA_A,
        "vcs": "GIT",
    }
    case["fixed_revision"]["source_revision"] = {
        "status": "VERIFIED",
        "value": SHA_A,
        "vcs": "GIT",
    }
    assert "is recorded as both the buggy and the fixed revision" in rejection(manifest)


def test_distinct_verified_git_source_revisions_are_accepted(manifest):
    case = manifest["cases"][0]
    case["buggy_revision"]["source_revision"] = {
        "status": "VERIFIED",
        "value": SHA_A,
        "vcs": "GIT",
    }
    case["fixed_revision"]["source_revision"] = {
        "status": "VERIFIED",
        "value": SHA_B,
        "vcs": "GIT",
    }
    case["metadata_provenance"]["source_revision_ids"] = "defects4j query -p Chart -q revision.id.buggy"
    manifest_module.validate(manifest)


def test_opaque_numeric_svn_source_revisions_are_accepted(manifest):
    case = manifest["cases"][0]
    case["buggy_revision"]["source_revision"] = {
        "status": "VERIFIED",
        "value": "2264",
        "vcs": "SVN",
    }
    case["fixed_revision"]["source_revision"] = {
        "status": "VERIFIED",
        "value": "2266",
        "vcs": "SVN",
    }
    manifest_module.validate(manifest)


def test_verified_source_revision_must_identify_the_vcs(manifest):
    manifest["cases"][0]["buggy_revision"]["source_revision"] = {
        "status": "VERIFIED",
        "value": "2264",
        "vcs": "UNKNOWN",
    }
    assert "vcs must be GIT or SVN when VERIFIED" in rejection(manifest)


# --------------------------------------------------------------------------
# language / ecosystem / versioning
# --------------------------------------------------------------------------


def test_unsupported_case_language_is_rejected(manifest):
    manifest["cases"][0]["language"] = "PYTHON"
    assert "language 'PYTHON' is unsupported" in rejection(manifest)


def test_unsupported_case_test_ecosystem_is_rejected(manifest):
    manifest["cases"][0]["test_ecosystem"] = "PYTEST"
    assert "test_ecosystem 'PYTEST' is unsupported" in rejection(manifest)


def test_unsupported_manifest_language_is_rejected(manifest):
    manifest["language"] = "KOTLIN"
    assert "language 'KOTLIN' is unsupported" in rejection(manifest)


def test_unversioned_manifest_is_rejected(manifest):
    del manifest["manifest_version"]
    assert "manifest_version is missing or empty" in rejection(manifest)


def test_unrecognized_schema_version_is_rejected(manifest):
    manifest["schema_version"] = "testgap.defects4j.golden-manifest.v99"
    assert "is unrecognized; expected 'testgap.defects4j.golden-manifest.v1'" in rejection(manifest)


def test_manifest_and_case_version_mismatch_is_rejected(manifest):
    manifest["cases"][0]["manifest_version"] = "DEFECTS4J_MVP_V2"
    assert "does not match the manifest-level version" in rejection(manifest)


def test_filename_and_version_mismatch_is_rejected(manifest, tmp_path):
    stray = tmp_path / "DEFECTS4J_MVP_V2.json"
    with pytest.raises(manifest_module.ManifestValidationError) as raised:
        manifest_module.validate(manifest, path=stray)
    assert "does not match manifest_version" in "\n".join(raised.value.errors)


def test_selection_that_does_not_predate_model_outcomes_is_rejected(manifest):
    manifest["selection"]["frozen_before_model_outcomes"] = False
    assert "must predate" in rejection(manifest)


# --------------------------------------------------------------------------
# exclusion semantics
# --------------------------------------------------------------------------


def test_excluded_case_with_a_reason_is_accepted(manifest):
    case = case_at(manifest, "D4J-TIME-013")
    case["selected"] = False
    case["exclusion_state"] = "EXCLUDED"
    case["exclusion_reason"] = "Superseded by a corrected case identity in a later manifest version"
    manifest_module.validate(manifest)


def test_excluded_case_without_a_reason_is_rejected(manifest):
    case = case_at(manifest, "D4J-TIME-013")
    case["selected"] = False
    case["exclusion_state"] = "EXCLUDED"
    case["exclusion_reason"] = "   "
    assert "EXCLUDED but exclusion_reason is empty" in rejection(manifest)


def test_selected_and_excluded_simultaneously_is_rejected(manifest):
    case = manifest["cases"][0]
    case["exclusion_state"] = "EXCLUDED"
    case["exclusion_reason"] = "some reason"
    assert "selected is true but exclusion_state is EXCLUDED" in rejection(manifest)


def test_unselected_case_without_an_exclusion_is_rejected(manifest):
    manifest["cases"][0]["selected"] = False
    assert "selected is false but exclusion_state is NOT_EXCLUDED" in rejection(manifest)


def test_not_excluded_case_with_a_reason_is_rejected(manifest):
    manifest["cases"][0]["exclusion_reason"] = "compile was slow"
    assert "NOT_EXCLUDED so exclusion_reason must be null" in rejection(manifest)


def test_invalid_exclusion_state_is_rejected(manifest):
    manifest["cases"][0]["exclusion_state"] = "MAYBE"
    assert "exclusion_state 'MAYBE' is invalid" in rejection(manifest)


# --------------------------------------------------------------------------
# triggering tests
# --------------------------------------------------------------------------


def test_verified_triggering_tests_with_empty_values_are_rejected(manifest):
    manifest["cases"][0]["triggering_tests"] = {"status": "VERIFIED", "values": []}
    assert "VERIFIED but values is empty" in rejection(manifest)


def test_unverified_triggering_tests_with_empty_values_are_accepted(manifest):
    manifest["cases"][0]["triggering_tests"] = {"status": "UNVERIFIED", "values": []}
    manifest_module.validate(manifest)


def test_verified_triggering_tests_with_values_are_accepted(manifest):
    case = manifest["cases"][0]
    case["triggering_tests"] = {
        "status": "VERIFIED",
        "values": ["org.example.ATest::testA", "org.example.BTest::testB"],
    }
    case["metadata_provenance"]["triggering_tests"] = "defects4j query -p Chart -q tests.trigger"
    manifest_module.validate(manifest)


def test_unverified_triggering_tests_may_not_carry_values(manifest):
    manifest["cases"][0]["triggering_tests"] = {
        "status": "UNVERIFIED",
        "values": ["org.example.ATest::testA"],
    }
    assert "UNVERIFIED so values must be empty" in rejection(manifest)


def test_duplicate_triggering_tests_are_rejected(manifest):
    manifest["cases"][0]["triggering_tests"] = {
        "status": "VERIFIED",
        "values": ["org.example.ATest::testA", "org.example.ATest::testA"],
    }
    assert "triggering_tests.values contains duplicates" in rejection(manifest)


def test_unsorted_triggering_tests_are_rejected(manifest):
    manifest["cases"][0]["triggering_tests"] = {
        "status": "VERIFIED",
        "values": ["org.example.BTest::testB", "org.example.ATest::testA"],
    }
    assert "must be sorted ascending" in rejection(manifest)


def test_invalid_triggering_test_verification_state_is_rejected(manifest):
    manifest["cases"][0]["triggering_tests"] = {"status": "PROBABLY", "values": []}
    assert "triggering_tests.status 'PROBABLY' is invalid" in rejection(manifest)


# --------------------------------------------------------------------------
# ordering, determinism, immutability
# --------------------------------------------------------------------------


def test_unsorted_case_ordering_is_rejected(manifest):
    manifest["cases"].reverse()
    assert "must be ordered by benchmark_case_id ascending" in rejection(manifest)


def test_smoke_case_ids_must_reference_known_cases(manifest):
    manifest["smoke_case_ids"] = ["D4J-NOPE-001"]
    assert "references cases that are not in the manifest" in rejection(manifest)


def test_parse_serialize_roundtrip_is_deterministic(manifest):
    text = MANIFEST_PATH.read_text(encoding="utf-8")
    assert manifest_module.canonical_json(manifest) == text
    assert manifest_module.parse(manifest_module.canonical_json(manifest)) == manifest


def test_canonical_serialization_is_independent_of_key_order(manifest):
    shuffled = {key: manifest[key] for key in reversed(list(manifest))}
    assert manifest_module.canonical_json(shuffled) == manifest_module.canonical_json(manifest)


def test_canonical_form_ends_with_exactly_one_newline(manifest):
    text = manifest_module.canonical_json(manifest)
    assert text.endswith("}\n") and not text.endswith("\n\n")


def test_duplicate_json_keys_are_rejected():
    with pytest.raises(ValueError, match="duplicate JSON key"):
        manifest_module.parse('{"manifest_version": "a", "manifest_version": "b"}')


def test_recorded_checksum_matches_the_v1_manifest():
    recorded = manifest_module.read_recorded_checksum(CHECKSUM_PATH)
    assert recorded == manifest_module.sha256_of_bytes(MANIFEST_PATH.read_bytes())


def test_checksum_mismatch_is_rejected(manifest, tmp_path):
    copied = tmp_path / MANIFEST_PATH.name
    tampered = copy.deepcopy(manifest)
    tampered["cases"][0]["domain_category"] = "TAMPERED"
    copied.write_text(manifest_module.canonical_json(tampered), encoding="utf-8")
    (tmp_path / CHECKSUM_PATH.name).write_text(
        CHECKSUM_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    with pytest.raises(manifest_module.ManifestValidationError) as raised:
        manifest_module.verify_file(copied)
    assert "does not match the manifest digest" in "\n".join(raised.value.errors)


def test_non_canonical_file_is_rejected(manifest, tmp_path):
    copied = tmp_path / MANIFEST_PATH.name
    copied.write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path / CHECKSUM_PATH.name).write_text(
        f"{manifest_module.sha256_of_bytes(copied.read_bytes())}  {copied.name}\n",
        encoding="utf-8",
    )
    with pytest.raises(manifest_module.ManifestValidationError) as raised:
        manifest_module.verify_file(copied)
    assert "is not in canonical form" in "\n".join(raised.value.errors)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def test_cli_validate_accepts_the_checked_in_manifest(capsys):
    assert manifest_module.main(["validate", str(MANIFEST_PATH)]) == 0
    assert "OK" in capsys.readouterr().out


def test_cli_validate_reports_failure_without_raising(tmp_path, capsys):
    broken = tmp_path / "DEFECTS4J_MVP_V1.json"
    broken.write_text('{"schema_version": "nope"}\n', encoding="utf-8")
    assert manifest_module.main(["validate", str(broken)]) == 1
    assert "FAIL" in capsys.readouterr().err


def test_cli_canonicalize_does_not_modify_the_checked_in_manifest(capsys):
    before = MANIFEST_PATH.read_bytes()
    assert manifest_module.main(["canonicalize", str(MANIFEST_PATH)]) == 0
    assert capsys.readouterr().out == before.decode("utf-8")
    assert MANIFEST_PATH.read_bytes() == before


def test_cli_checksum_prints_the_recorded_digest(capsys):
    assert manifest_module.main(["checksum", str(MANIFEST_PATH)]) == 0
    assert capsys.readouterr().out.strip() == manifest_module.read_recorded_checksum(CHECKSUM_PATH)
