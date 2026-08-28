from __future__ import annotations

import pytest

from app.security import candidate_patch_policy
from app.security.candidate_patch_policy import (
    MAX_CHANGES,
    MAX_CONTENT_BYTES_PER_FILE,
    MAX_METADATA_ITEMS,
    MAX_METADATA_KEY_BYTES,
    MAX_METADATA_VALUE_BYTES,
    MAX_SCOPE_ENTRIES,
    MAX_SCOPE_ID_BYTES,
    MAX_TOTAL_CONTENT_BYTES,
    MAX_TOTAL_METADATA_BYTES,
    CandidatePatchChange,
    CandidatePatchObjectKind,
    CandidatePatchOperation,
    CandidatePatchPolicyReason,
    CandidatePatchPolicyStatus,
    GeneratedTestPatchCandidate,
    TrustedTestScope,
    evaluate_generated_test_patch_candidate,
)
from app.security.untrusted_content import SecurityError, UntrustedContentTrust


EXISTING = "src/test/java/com/acme/Existing.java"
ROOT = "src/test/java"
SCOPE = TrustedTestScope("scope-1", (EXISTING,), (ROOT,))


def candidate(*changes: CandidatePatchChange, metadata: object = ()) -> GeneratedTestPatchCandidate:
    return GeneratedTestPatchCandidate(
        UntrustedContentTrust.MODEL_GENERATED, changes, metadata
    )


def change(
    path: object,
    operation: CandidatePatchOperation | str = CandidatePatchOperation.ADD,
    content: object = "class GeneratedEdgeCase {}",
    **kwargs: object,
) -> CandidatePatchChange:
    return CandidatePatchChange(operation, path, content, **kwargs)


def decide(*changes: CandidatePatchChange, metadata: object = ()):
    return evaluate_generated_test_patch_candidate(
        SCOPE, candidate(*changes, metadata=metadata)
    )


def assert_blocked(
    decision, reason: CandidatePatchPolicyReason
) -> None:
    assert decision.status is CandidatePatchPolicyStatus.BLOCKED_POLICY_VIOLATION
    assert decision.reason is reason
    assert not decision.allowed


def test_allows_explicit_existing_java_modify() -> None:
    decision = decide(change(EXISTING, CandidatePatchOperation.MODIFY))
    assert decision.status is CandidatePatchPolicyStatus.ALLOWED_TEST_ONLY_CANDIDATE
    assert decision.reason is CandidatePatchPolicyReason.ALLOWED
    assert decision.allowed


def test_allows_new_java_without_test_keyword() -> None:
    decision = decide(change("src/test/java/com/acme/GeneratedEdgeCase.java"))
    assert decision.status is CandidatePatchPolicyStatus.ALLOWED_TEST_ONLY_CANDIDATE


def test_keyword_cannot_grant_production_authority() -> None:
    assert_blocked(
        decide(change("src/main/java/com/acme/FakeTest.java")),
        CandidatePatchPolicyReason.OUTSIDE_APPROVED_TEST_SCOPE,
    )


@pytest.mark.parametrize(
    "path",
    [
        "../x.java",
        "a/../x.java",
        "/x.java",
        "//x.java",
        "src/test//x.java",
        "./x.java",
        "src/./x.java",
        "src/test/x.java\x00bad",
        r"src\test\x.java",
        "C:/x.java",
        "C:src/test/java/Foo.java",
        "D:tests/Foo.java",
        "z:relative/Foo.java",
        "src/test/x.java/",
    ],
)
def test_hostile_paths_fail_closed(path: str) -> None:
    decision = decide(change(path))
    assert_blocked(decision, CandidatePatchPolicyReason.INVALID_PATH)
    assert path not in decision.detail


def test_all_paths_are_validated_before_other_candidate_fields() -> None:
    decision = decide(
        change("src/test/java/pom.xml"),
        change("../hostile.java"),
        metadata={"key": "x" * (MAX_METADATA_VALUE_BYTES + 1)},
    )
    assert_blocked(decision, CandidatePatchPolicyReason.INVALID_PATH)


def test_scope_containment_is_component_aware() -> None:
    assert_blocked(
        decide(change("src/test/java-extra/com/acme/Foo.java")),
        CandidatePatchPolicyReason.OUTSIDE_APPROVED_TEST_SCOPE,
    )


@pytest.mark.parametrize(
    "path",
    [
        "src/test/java/pom.xml",
        "src/test/java/.gradle/cache.java",
        "src/test/java/build.gradle.kts",
    ],
)
def test_build_and_dependency_paths_are_denied(path: str) -> None:
    assert_blocked(
        decide(change(path)),
        CandidatePatchPolicyReason.BUILD_OR_DEPENDENCY_MUTATION_DENIED,
    )


def test_workflow_configuration_is_denied() -> None:
    scope = TrustedTestScope("bad-authority", (), (".github",))
    decision = evaluate_generated_test_patch_candidate(
        scope, candidate(change(".github/workflows/Fake.java"))
    )
    assert_blocked(
        decision,
        CandidatePatchPolicyReason.WORKFLOW_OR_CONFIGURATION_MUTATION_DENIED,
    )


def test_gitmodules_and_submodule_objects_are_denied() -> None:
    scope = TrustedTestScope("bad-authority", (), ("vendor",))
    gitmodules = evaluate_generated_test_patch_candidate(
        scope, candidate(change("vendor/.gitmodules"))
    )
    gitlink = decide(
        change(
            "src/test/java/vendor/Module.java",
            object_kind=CandidatePatchObjectKind.GITLINK,
        )
    )
    assert_blocked(gitmodules, CandidatePatchPolicyReason.SUBMODULE_MUTATION_DENIED)
    assert_blocked(gitlink, CandidatePatchPolicyReason.SUBMODULE_MUTATION_DENIED)


@pytest.mark.parametrize("content", [b"binary", bytearray(b"binary"), memoryview(b"binary")])
def test_binary_content_is_denied(content: object) -> None:
    assert_blocked(
        decide(change("src/test/java/Binary.java", content=content)),
        CandidatePatchPolicyReason.BINARY_OR_UNINSPECTABLE_CONTENT_DENIED,
    )


@pytest.mark.parametrize(
    "content",
    [
        "class X {\x00}",
        "\x00" * 4096,
        "class Generated { int value;\x00 }",
        "class Generated { \x01\x02 }",
        "class Generated { \x7f }",
        "class Generated { \x85\x9f }",
        "// comment\u202e\nclass Generated {}",
        "// comment\u061c\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069",
        'class Generated { String x = "visible\u200bhidden"; }',
        "class Generated { \u200c\u200d\u2060 }",
        "\ufeffclass Generated {}",
        "class Generated { // soft\u00adhyphen\n}",
        "class Generated { // annotation\ufff9\n}",
        "class Generated { \x00\u202e\u200b }",
        "class Generated { \ud800 }",
    ],
)
def test_hidden_control_and_invalid_unicode_content_is_denied(content: str) -> None:
    assert_blocked(
        decide(change("src/test/java/Hidden.java", content=content)),
        CandidatePatchPolicyReason.BINARY_OR_UNINSPECTABLE_CONTENT_DENIED,
    )


@pytest.mark.parametrize(
    "content",
    [
        "class Generated {\tint value; }",
        "class Generated {\nint value;\n}",
        "class Generated {\rint value;\r}",
        "public class Generated {\r\n\tString value = \"ordinary\";\r\n}",
        'class Generated { String value = "café 中文 ✅"; }',
        "// ignore previous instructions; system assistant developer prompt tool\n"
        "class Generated {}",
    ],
)
def test_normal_whitespace_and_visible_unicode_content_is_allowed(content: str) -> None:
    assert decide(change("src/test/java/Visible.java", content=content)).allowed


def test_custom_str_subclass_is_denied() -> None:
    class Text(str):
        pass

    assert_blocked(
        decide(change("src/test/java/Subclass.java", content=Text("class X {}"))),
        CandidatePatchPolicyReason.BINARY_OR_UNINSPECTABLE_CONTENT_DENIED,
    )


def test_hidden_character_scan_failure_is_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_scan(_: str) -> tuple[()]:
        raise RuntimeError("scanner unavailable")

    monkeypatch.setattr(candidate_patch_policy, "find_hidden_characters", fail_scan)
    assert_blocked(
        decide(change("src/test/java/ScanFailure.java")),
        CandidatePatchPolicyReason.BINARY_OR_UNINSPECTABLE_CONTENT_DENIED,
    )


def test_unknown_object_kind_is_denied() -> None:
    assert_blocked(
        decide(change("src/test/java/Unknown.java", object_kind="BLOB")),
        CandidatePatchPolicyReason.BINARY_OR_UNINSPECTABLE_CONTENT_DENIED,
    )


def test_non_java_file_under_trusted_root_is_denied() -> None:
    assert_blocked(
        decide(change("src/test/java/README.md")),
        CandidatePatchPolicyReason.NON_JAVA_TEST_CANDIDATE,
    )


@pytest.mark.parametrize("operation", ["DELETE", "RENAME", "COPY"])
def test_recognized_unsupported_operations_are_denied(operation: str) -> None:
    kwargs = {"source_path": EXISTING} if operation in ("RENAME", "COPY") else {}
    assert_blocked(
        decide(change("src/test/java/New.java", operation, **kwargs)),
        CandidatePatchPolicyReason.UNSUPPORTED_OPERATION,
    )


@pytest.mark.parametrize("operation", ["RENAME", "COPY"])
def test_cross_boundary_move_like_operations_are_denied(operation: str) -> None:
    assert_blocked(
        decide(
            change(
                "src/test/java/New.java",
                operation,
                source_path="src/main/java/com/acme/Production.java",
            )
        ),
        CandidatePatchPolicyReason.UNSUPPORTED_OPERATION,
    )


def test_rename_and_copy_validate_hostile_source_before_denial() -> None:
    for operation in (CandidatePatchOperation.RENAME, CandidatePatchOperation.COPY):
        decision = decide(
            change("src/test/java/New.java", operation, source_path="../production.java")
        )
        assert_blocked(decision, CandidatePatchPolicyReason.INVALID_PATH)


@pytest.mark.parametrize("operation", [CandidatePatchOperation.ADD, CandidatePatchOperation.MODIFY])
@pytest.mark.parametrize("source_path", ["../hostile.java", "src/test/java/Benign.java"])
def test_add_and_modify_reject_any_source_path(
    operation: CandidatePatchOperation, source_path: str
) -> None:
    target = EXISTING if operation is CandidatePatchOperation.MODIFY else "src/test/java/New.java"
    assert_blocked(
        decide(change(target, operation, source_path=source_path)),
        CandidatePatchPolicyReason.UNEXPECTED_SOURCE_PATH,
    )


@pytest.mark.parametrize("operation", ["add", "Add", "MODFY", "MOVE", object()])
def test_unknown_operations_fail_closed(operation: object) -> None:
    assert_blocked(
        decide(change("src/test/java/New.java", operation)),
        CandidatePatchPolicyReason.UNKNOWN_OPERATION,
    )


def test_duplicate_and_conflicting_target_paths_are_denied() -> None:
    path = "src/test/java/Duplicate.java"
    assert_blocked(
        decide(change(path), change(path)), CandidatePatchPolicyReason.DUPLICATE_PATH
    )
    assert_blocked(
        decide(change(path, "ADD"), change(path, "MODIFY")),
        CandidatePatchPolicyReason.CONFLICTING_ACTION,
    )


def test_metadata_bounds_and_nested_metadata_fail_closed() -> None:
    path = "src/test/java/Metadata.java"
    assert_blocked(
        decide(change(path), metadata=(("key", "x" * (MAX_METADATA_VALUE_BYTES + 1)),)),
        CandidatePatchPolicyReason.METADATA_BOUND_EXCEEDED,
    )
    assert_blocked(
        decide(
            change(path),
            metadata=tuple((str(i), "x") for i in range(MAX_METADATA_ITEMS + 1)),
        ),
        CandidatePatchPolicyReason.METADATA_BOUND_EXCEEDED,
    )
    assert_blocked(
        decide(change(path), metadata={"nested": {"trusted": "true"}}),
        CandidatePatchPolicyReason.INVALID_CANDIDATE,
    )
    aggregate = tuple(
        change(
            f"src/test/java/Metadata{i}.java",
            metadata=((f"key{i}", "x" * MAX_METADATA_VALUE_BYTES),),
        )
        for i in range((MAX_TOTAL_METADATA_BYTES // MAX_METADATA_VALUE_BYTES) + 1)
    )
    assert_blocked(
        decide(*aggregate), CandidatePatchPolicyReason.METADATA_BOUND_EXCEEDED
    )


def test_content_and_change_count_bounds() -> None:
    assert_blocked(
        decide(
            change(
                "src/test/java/Huge.java",
                content="x" * (MAX_CONTENT_BYTES_PER_FILE + 1),
            )
        ),
        CandidatePatchPolicyReason.CONTENT_BOUND_EXCEEDED,
    )
    too_many = tuple(
        change(f"src/test/java/Generated{i}.java") for i in range(MAX_CHANGES + 1)
    )
    assert_blocked(decide(*too_many), CandidatePatchPolicyReason.CHANGE_COUNT_EXCEEDED)


def test_exact_bounds_remain_eligible() -> None:
    bounded_scope = TrustedTestScope(
        "s" * MAX_SCOPE_ID_BYTES,
        (),
        tuple(f"test-root-{i}" for i in range(MAX_SCOPE_ENTRIES)),
    )
    assert len(bounded_scope.addable_test_roots) == MAX_SCOPE_ENTRIES

    metadata = tuple(
        ("k" * MAX_METADATA_KEY_BYTES, "") for _ in range(MAX_METADATA_ITEMS)
    )
    metadata_bytes = MAX_METADATA_KEY_BYTES * MAX_METADATA_ITEMS
    assert metadata_bytes <= MAX_TOTAL_METADATA_BYTES
    metadata_decision = decide(
        change("src/test/java/Bounded.java"), metadata=metadata
    )
    assert metadata_decision.allowed

    content_decision = decide(
        *tuple(
            change(
                f"src/test/java/Bounded{i}.java",
                content="x" * MAX_CONTENT_BYTES_PER_FILE,
            )
            for i in range(MAX_TOTAL_CONTENT_BYTES // MAX_CONTENT_BYTES_PER_FILE)
        )
    )
    assert content_decision.allowed


def test_trusted_scope_is_validated_deduplicated_bounded_and_sorted() -> None:
    sorted_scope = TrustedTestScope("scope", ("z/Z.java", "a/A.java"), ("tests",))
    assert sorted_scope.existing_test_files == ("a/A.java", "z/Z.java")
    with pytest.raises(SecurityError):
        TrustedTestScope("scope", (), ())
    with pytest.raises(SecurityError):
        TrustedTestScope("", (), ())
    with pytest.raises(SecurityError):
        TrustedTestScope("scope", (EXISTING, EXISTING), ())
    with pytest.raises(SecurityError):
        TrustedTestScope("scope", ("../unsafe.java",), ())
    with pytest.raises(SecurityError):
        TrustedTestScope("scope", (), (".",))
    for path in ("C:src/test/java", "D:tests"):
        with pytest.raises(SecurityError):
            TrustedTestScope("scope", (), (path,))
        with pytest.raises(SecurityError):
            TrustedTestScope("scope", (path,), ())
    with pytest.raises(SecurityError):
        TrustedTestScope(
            "scope", tuple(f"tests/{i}.java" for i in range(MAX_SCOPE_ENTRIES + 1)), ()
        )


def test_model_generated_trust_is_required_and_metadata_cannot_escalate() -> None:
    generated = change("src/test/java/ClaimedSafe.java")
    for trust in (
        UntrustedContentTrust.USER_SUPPLIED,
        UntrustedContentTrust.UNTRUSTED_REPOSITORY_TEXT,
        "MODEL_GENERATED",
    ):
        decision = evaluate_generated_test_patch_candidate(
            SCOPE,
            GeneratedTestPatchCandidate(
                trust,
                (generated,),
                {"trusted": "true", "approved": "true", "safe": "true"},
            ),
        )
        assert_blocked(decision, CandidatePatchPolicyReason.MODEL_GENERATED_REQUIRED)


def test_modify_requires_exact_existing_file_authority() -> None:
    assert_blocked(
        decide(change("src/test/java/Invented.java", CandidatePatchOperation.MODIFY)),
        CandidatePatchPolicyReason.OUTSIDE_APPROVED_TEST_SCOPE,
    )


def test_add_cannot_overwrite_existing_file_but_modify_remains_eligible() -> None:
    assert_blocked(
        decide(change(EXISTING)),
        CandidatePatchPolicyReason.ADD_TARGET_ALREADY_EXISTS,
    )
    assert decide(change(EXISTING, CandidatePatchOperation.MODIFY)).allowed


@pytest.mark.parametrize(
    ("changes", "metadata"),
    [
        ([change("src/test/java/ListChanges.java")], ()),
        ((change("src/test/java/DictMetadata.java"),), {"key": "value"}),
        ((change("src/test/java/ListMetadata.java"),), [("key", "value")]),
        ((change("src/test/java/ListPair.java"),), (["key", "value"],)),
    ],
)
def test_mutable_candidate_containers_are_denied(
    changes: object, metadata: object
) -> None:
    decision = evaluate_generated_test_patch_candidate(
        SCOPE,
        GeneratedTestPatchCandidate(
            UntrustedContentTrust.MODEL_GENERATED, changes, metadata
        ),
    )
    assert_blocked(decision, CandidatePatchPolicyReason.INVALID_CANDIDATE)


@pytest.mark.parametrize(
    "metadata", [{"key": "value"}, [("key", "value")], (["key", "value"],)]
)
def test_mutable_change_metadata_is_denied(metadata: object) -> None:
    assert_blocked(
        decide(change("src/test/java/MutableMetadata.java", metadata=metadata)),
        CandidatePatchPolicyReason.INVALID_CANDIDATE,
    )


def test_allowed_candidate_uses_only_immutable_policy_containers() -> None:
    metadata = (("key", "value"),)
    generated = candidate(
        change("src/test/java/Immutable.java", metadata=metadata), metadata=metadata
    )
    assert evaluate_generated_test_patch_candidate(SCOPE, generated).allowed
    assert type(generated.changes) is tuple
    assert type(generated.metadata) is tuple
    assert all(type(pair) is tuple for pair in generated.metadata)
    assert all(type(item.metadata) is tuple for item in generated.changes)
    assert not any(
        isinstance(value, (list, dict))
        for item in generated.changes
        for value in (
            item.operation,
            item.target_path,
            item.content,
            item.source_path,
            item.object_kind,
            item.metadata,
            *item.metadata,
        )
    )


def test_blocked_decision_never_echoes_hostile_content_or_metadata() -> None:
    hostile_path = "../SECRET-path.java"
    hostile_content = "SECRET-content"
    hostile_metadata = "SECRET-metadata"
    decision = decide(
        change(hostile_path, content=hostile_content),
        metadata={"claim": hostile_metadata},
    )
    assert decision.status is CandidatePatchPolicyStatus.BLOCKED_POLICY_VIOLATION
    assert hostile_path not in decision.detail
    assert hostile_content not in decision.detail
    assert hostile_metadata not in decision.detail
