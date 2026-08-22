"""Semantic tests for RAG-003 lexical and structural candidate generation."""

from __future__ import annotations

import hashlib
import os
import socket
import subprocess
from fractions import Fraction
from pathlib import Path

import pytest

import app.retrieval.candidates as candidates
from app.retrieval.candidates import (
    BUILD_METADATA_FILENAMES,
    MAX_CHANGED_FILES,
    RAG003_IMPLEMENTATION_SCORING_POLICY,
    RAG003_MAX_TOTAL_SCORE,
    SIGNAL_BUILD_METADATA,
    SIGNAL_DIFF_ADJACENCY,
    SIGNAL_JAVA_SYMBOL,
    SIGNAL_LEXICAL,
    SIGNAL_PATH_MATCH,
    SIGNAL_STACK_TRACE,
    SIGNAL_TEST_PROXIMITY,
    CandidateErrorCode,
    CandidateGenerationError,
    CandidateGenerationInput,
    candidate_identity,
    extract_java_symbols,
    generate_candidates,
    parse_stack_trace,
    recall_at_k,
    reciprocal_rank,
    tokenize,
)
from app.retrieval.indexing import (
    ContentKind,
    FileLanguage,
    FileRole,
    IndexedFile,
    RepositoryIndex,
    index_repository,
)
from app.retrieval.localisation import (
    MAX_CANDIDATES,
    MAX_QUERY_BYTES,
    CandidateFile,
    CandidateIdentity,
    FileIdentity,
    ManifestFile,
    RepositoryIdentity,
    RepositoryManifest,
    RevisionIdentity,
    load_localisation_dataset,
)
from app.workflow.repository_workspace import PreparedRepositoryWorkspace, WorkspaceMode


REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_DATASET = REPO_ROOT / "evaluation" / "datasets" / "localisation" / "LOCALISATION_BASELINE_V1.json"

REPOSITORY = RepositoryIdentity("example/rag-003")
REVISION = RevisionIdentity("a" * 40)

ORDER_SERVICE = """package com.example.service;

public class OrderService {
    public void placeOrder(String orderId) {
        validateOrder(orderId);
    }

    private void validateOrder(String orderId) {
        throw new IllegalStateException(orderId);
    }
}
"""

PAYMENT_GATEWAY = """package com.example.service;

public interface PaymentGateway {
    void capture(String reference);
}
"""

ORDER_SERVICE_TEST = """package com.example.service;

public class OrderServiceTest {
    public void placeOrderRejectsUnknownOrder() {
    }
}
"""

STACK_TRACE = """java.lang.IllegalStateException: order-1
\tat com.example.service.OrderService.validateOrder(OrderService.java:8)
\tat com.example.service.OrderService.placeOrder(OrderService.java:4)
"""

FIXTURE_FILES: dict[str, bytes] = {
    "pom.xml": b"<project><artifactId>orders</artifactId></project>\n",
    "build.gradle": b"dependencies { implementation 'com.example:orders' }\n",
    "src/main/java/com/example/service/OrderService.java": ORDER_SERVICE.encode(),
    "src/main/java/com/example/service/PaymentGateway.java": PAYMENT_GATEWAY.encode(),
    "src/main/java/com/example/util/Strings.java": (
        "package com.example.util;\n\npublic final class Strings {\n"
        "    public static String squeeze(String value) { return value; }\n}\n"
    ).encode(),
    "src/test/java/com/example/service/OrderServiceTest.java": ORDER_SERVICE_TEST.encode(),
    "docs/handbook.md": b"The order service handles checkout.\n",
    "assets/logo.bin": b"\x00\x01\x02\xff\xfe binary payload \x00",
    "node_modules/dep/index.js": b"module.exports = {};\n",
    ".git/HEAD": b"ref: refs/heads/main\n",
}


def build_fixture(root: Path, files: dict[str, bytes] = FIXTURE_FILES) -> Path:
    for relative, content in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    return root


def workspace(root: Path) -> PreparedRepositoryWorkspace:
    return PreparedRepositoryWorkspace(REPOSITORY, REVISION, root, WorkspaceMode.READ_ONLY)


@pytest.fixture
def repository(tmp_path: Path):
    root = build_fixture(tmp_path / "source")
    prepared = workspace(root)
    return prepared, index_repository(prepared)


def run(repository, **kwargs) -> tuple[CandidateFile, ...]:
    prepared, index = repository
    kwargs.setdefault("candidate_limit", 20)
    return generate_candidates(prepared, index, CandidateGenerationInput(**kwargs))


def paths(result: tuple[CandidateFile, ...]) -> list[str]:
    return [candidate.file_identity.value for candidate in result]


def signals(candidate: CandidateFile) -> dict[str, int]:
    return {signal.signal: signal.contribution for signal in candidate.explanation.signals}


def find(result: tuple[CandidateFile, ...], path: str) -> CandidateFile:
    for candidate in result:
        if candidate.file_identity.value == path:
            return candidate
    raise AssertionError(f"{path} is not among {paths(result)}")


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


# --------------------------------------------------------------------------
# Lexical
# --------------------------------------------------------------------------


def test_lexical_exact_token_scores_the_file_that_contains_it(repository) -> None:
    result = run(repository, query="squeeze")

    candidate = find(result, "src/main/java/com/example/util/Strings.java")
    assert signals(candidate)[SIGNAL_LEXICAL] > 0
    assert "squeeze:" in signals_detail(candidate, SIGNAL_LEXICAL)


def test_lexical_no_match_produces_no_candidate(repository) -> None:
    assert run(repository, query="zzqqxxnowherenearthiscorpus") == ()


def test_lexical_rewards_higher_in_document_frequency(tmp_path: Path) -> None:
    root = build_fixture(
        tmp_path / "source",
        {
            "dense.txt": b"checkout checkout checkout checkout checkout filler\n",
            "sparse.txt": b"checkout filler filler filler filler filler\n",
        },
    )
    prepared = workspace(root)
    result = generate_candidates(
        prepared, index_repository(prepared), CandidateGenerationInput(query="checkout")
    )

    assert paths(result) == ["dense.txt", "sparse.txt"]
    assert signals(find(result, "dense.txt"))[SIGNAL_LEXICAL] > signals(
        find(result, "sparse.txt")
    )[SIGNAL_LEXICAL]


def test_corpus_statistics_are_deterministic(repository) -> None:
    prepared, index = repository

    first = candidates._build_corpus(prepared, index)
    second = candidates._build_corpus(prepared, index)

    assert [document.path for document in first] == [document.path for document in second]
    assert [document.terms for document in first] == [document.terms for document in second]
    assert [document.length for document in first] == [document.length for document in second]


def test_tokenization_is_case_normalized_and_identifier_friendly() -> None:
    assert tokenize("OrderService.placeOrder") == [
        "orderservice",
        "order",
        "service",
        "placeorder",
        "place",
        "order",
    ]
    assert tokenize("model_domain") == ["model_domain", "model", "domain"]


# --------------------------------------------------------------------------
# Path match
# --------------------------------------------------------------------------


def test_path_match_prefers_exact_filename_over_weak_path_overlap(repository) -> None:
    result = run(repository, query="OrderService.java service")

    exact = signals(find(result, "src/main/java/com/example/service/OrderService.java"))
    weak = signals(find(result, "src/main/java/com/example/service/PaymentGateway.java"))
    assert exact[SIGNAL_PATH_MATCH] > weak[SIGNAL_PATH_MATCH]


def test_path_match_never_uses_host_absolute_paths(repository, tmp_path: Path) -> None:
    result = run(repository, query="OrderService.java")

    rendered = "".join(candidate.canonical_json() for candidate in result)
    assert str(tmp_path) not in rendered
    assert not any(path.startswith("/") for path in paths(result))


# --------------------------------------------------------------------------
# Java symbols
# --------------------------------------------------------------------------


def test_java_class_identifier_is_recognised(repository) -> None:
    result = run(repository, query="PaymentGateway")

    assert signals(find(result, "src/main/java/com/example/service/PaymentGateway.java"))[
        SIGNAL_JAVA_SYMBOL
    ] > 0


def test_java_method_identifier_is_recognised(repository) -> None:
    result = run(repository, query="capture")

    detail = dict(
        (signal.signal, signal.detail)
        for signal in find(
            result, "src/main/java/com/example/service/PaymentGateway.java"
        ).explanation.signals
    )
    assert "capture" in detail[SIGNAL_JAVA_SYMBOL]


def test_java_package_relation_is_recognised(repository) -> None:
    result = run(repository, query="com.example.service package")

    candidate = find(result, "src/main/java/com/example/service/PaymentGateway.java")
    assert "package=" in signals_detail(candidate, SIGNAL_JAVA_SYMBOL)


def signals_detail(candidate: CandidateFile, name: str) -> str:
    for signal in candidate.explanation.signals:
        if signal.signal == name:
            return signal.detail
    raise AssertionError(f"{name} not emitted for {candidate.file_identity.value}")


def test_java_symbol_extraction_is_conservative_and_never_claims_parsing() -> None:
    symbols = extract_java_symbols(ORDER_SERVICE)

    assert symbols.package == "com.example.service"
    assert symbols.types == frozenset({"OrderService"})
    assert symbols.methods == frozenset({"placeOrder", "validateOrder"})
    assert extract_java_symbols("not java at all").package == ""


def test_non_java_files_never_emit_java_symbol_signal(repository) -> None:
    result = run(repository, query="order service checkout handbook")

    assert SIGNAL_JAVA_SYMBOL not in signals(find(result, "docs/handbook.md"))


# --------------------------------------------------------------------------
# Stack trace
# --------------------------------------------------------------------------


def test_stack_trace_maps_class_file_and_method(repository) -> None:
    result = run(repository, query="order failure", stack_trace=STACK_TRACE)

    candidate = find(result, "src/main/java/com/example/service/OrderService.java")
    detail = signals_detail(candidate, SIGNAL_STACK_TRACE)
    assert signals(candidate)[SIGNAL_STACK_TRACE] > 0
    assert "com.example.service.OrderService" in detail
    assert "validateOrder" in detail


def test_stack_trace_parsing_extracts_bounded_frames() -> None:
    frames = parse_stack_trace(STACK_TRACE)

    assert [frame.method for frame in frames] == ["validateOrder", "placeOrder"]
    assert frames[0].source_file == "OrderService.java"
    assert frames[0].line == 8
    assert frames[0].package_path == "com/example/service"


def test_malformed_stack_trace_is_ignored_rather_than_trusted(repository) -> None:
    garbage = "at at at ((((\n\tat /etc/passwd\n\x01\x02 not a frame"

    result = run(repository, query="OrderService", stack_trace=garbage)

    assert parse_stack_trace(garbage) == ()
    assert all(SIGNAL_STACK_TRACE not in signals(candidate) for candidate in result)


def test_stack_trace_paths_are_never_followed_outside_the_index(repository) -> None:
    trace = "\tat com.evil.Thing.run(/etc/passwd:1)\n\tat com.evil.Thing.go(../../secret.java:2)"

    result = run(repository, query="thing", stack_trace=trace)

    assert all(SIGNAL_STACK_TRACE not in signals(candidate) for candidate in result)


# --------------------------------------------------------------------------
# Diff adjacency
# --------------------------------------------------------------------------


def test_diff_adjacency_scores_the_same_file_highest(repository) -> None:
    changed = (FileIdentity("src/main/java/com/example/service/OrderService.java"),)

    result = run(repository, query="order", changed_files=changed)

    same = signals(find(result, changed[0].value))[SIGNAL_DIFF_ADJACENCY]
    sibling = signals(
        find(result, "src/main/java/com/example/service/PaymentGateway.java")
    )[SIGNAL_DIFF_ADJACENCY]
    assert same > sibling > 0


def test_diff_package_adjacency_excludes_unrelated_packages(repository) -> None:
    changed = (FileIdentity("src/main/java/com/example/service/OrderService.java"),)

    result = run(repository, query="order squeeze", changed_files=changed)

    unrelated = find(result, "src/main/java/com/example/util/Strings.java")
    assert SIGNAL_DIFF_ADJACENCY not in signals(unrelated)
    assert SIGNAL_DIFF_ADJACENCY in signals(
        find(result, "src/main/java/com/example/service/PaymentGateway.java")
    )


def test_changed_files_outside_the_index_fail_closed(repository) -> None:
    with pytest.raises(CandidateGenerationError) as error:
        run(repository, query="order", changed_files=(FileIdentity("src/absent/Nope.java"),))

    assert error.value.code == CandidateErrorCode.UNKNOWN_CHANGED_FILE


# --------------------------------------------------------------------------
# Test proximity
# --------------------------------------------------------------------------


def test_test_proximity_boosts_the_conventional_counterpart(repository) -> None:
    changed = (FileIdentity("src/main/java/com/example/service/OrderService.java"),)

    result = run(repository, query="order", changed_files=changed)

    assert signals(find(result, "src/test/java/com/example/service/OrderServiceTest.java"))[
        SIGNAL_TEST_PROXIMITY
    ] > 0


def test_source_and_test_stem_relation_is_recognised(repository) -> None:
    result = run(repository, query="OrderService")

    detail = signals_detail(
        find(result, "src/test/java/com/example/service/OrderServiceTest.java"),
        SIGNAL_TEST_PROXIMITY,
    )
    assert "orderservice" in detail


def test_non_test_files_never_emit_test_proximity(repository) -> None:
    result = run(repository, query="OrderService")

    assert SIGNAL_TEST_PROXIMITY not in signals(
        find(result, "src/main/java/com/example/service/OrderService.java")
    )


# --------------------------------------------------------------------------
# Build metadata
# --------------------------------------------------------------------------


def test_build_metadata_recognises_known_manifests(repository) -> None:
    result = run(repository, query="gradle build dependency", build_hints=("pom.xml",))

    assert signals(find(result, "pom.xml"))[SIGNAL_BUILD_METADATA] == 60_000
    assert signals(find(result, "build.gradle"))[SIGNAL_BUILD_METADATA] == 20_000
    assert BUILD_METADATA_FILENAMES >= {"pom.xml", "build.gradle", "settings.gradle.kts"}


def test_unknown_build_hint_produces_no_build_metadata_signal(repository) -> None:
    result = run(repository, query="locate the order service", build_hints=("cargo.toml",))

    assert all(SIGNAL_BUILD_METADATA not in signals(candidate) for candidate in result)


# --------------------------------------------------------------------------
# Scoring and ranking
# --------------------------------------------------------------------------


def test_multi_signal_candidate_composes_every_applicable_signal(repository) -> None:
    result = run(
        repository,
        query="OrderService.java placeOrder com.example.service",
        stack_trace=STACK_TRACE,
        changed_files=(FileIdentity("src/main/java/com/example/service/OrderService.java"),),
        build_hints=("pom.xml",),
    )

    emitted = signals(find(result, "src/main/java/com/example/service/OrderService.java"))
    assert set(emitted) == {
        SIGNAL_LEXICAL,
        SIGNAL_PATH_MATCH,
        SIGNAL_JAVA_SYMBOL,
        SIGNAL_STACK_TRACE,
        SIGNAL_DIFF_ADJACENCY,
    }


def test_score_is_exactly_the_sum_of_emitted_contributions(repository) -> None:
    result = run(repository, query="OrderService placeOrder", stack_trace=STACK_TRACE)

    for candidate in result:
        assert candidate.explanation.score == sum(signals(candidate).values())


def test_every_signal_contribution_respects_its_policy_envelope(repository) -> None:
    result = run(
        repository,
        query="OrderService.java placeOrder validateOrder com.example.service order gradle",
        stack_trace=STACK_TRACE,
        changed_files=(FileIdentity("src/main/java/com/example/service/OrderService.java"),),
        build_hints=("pom.xml", "build.gradle"),
    )

    for candidate in result:
        for name, contribution in signals(candidate).items():
            assert 0 < contribution <= RAG003_IMPLEMENTATION_SCORING_POLICY[name]
        assert 0 < candidate.explanation.score <= RAG003_MAX_TOTAL_SCORE


def test_ties_break_on_canonical_file_identity_ascending(tmp_path: Path) -> None:
    root = build_fixture(
        tmp_path / "source",
        {"b/same.txt": b"checkout\n", "a/same.txt": b"checkout\n", "c/same.txt": b"checkout\n"},
    )
    prepared = workspace(root)
    result = generate_candidates(
        prepared, index_repository(prepared), CandidateGenerationInput(query="checkout")
    )

    scores = {candidate.explanation.score for candidate in result}
    assert len(scores) == 1
    assert paths(result) == ["a/same.txt", "b/same.txt", "c/same.txt"]


def test_ranks_are_contiguous_from_one(repository) -> None:
    result = run(repository, query="order service com.example gradle", build_hints=("pom.xml",))

    assert [candidate.explanation.rank for candidate in result] == list(
        range(1, len(result) + 1)
    )


def test_repeated_generation_is_byte_identical(repository) -> None:
    request = dict(
        query="OrderService placeOrder",
        stack_trace=STACK_TRACE,
        changed_files=(FileIdentity("src/main/java/com/example/service/OrderService.java"),),
        build_hints=("pom.xml",),
    )

    first = run(repository, **request)
    second = run(repository, **request)

    assert [candidate.canonical_json() for candidate in first] == [
        candidate.canonical_json() for candidate in second
    ]


def test_candidate_limit_is_applied_after_deterministic_ordering(repository) -> None:
    query = "order service com.example gradle build"

    full = run(repository, query=query, candidate_limit=20)
    limited = run(repository, query=query, candidate_limit=2)

    assert len(full) > 2
    assert paths(limited) == paths(full)[:2]
    assert [candidate.explanation.rank for candidate in limited] == [1, 2]


@pytest.mark.parametrize("limit", [0, -1, MAX_CANDIDATES + 1, True, "3", 1.0, None])
def test_invalid_candidate_limit_fails_closed(limit) -> None:
    with pytest.raises(CandidateGenerationError) as error:
        CandidateGenerationInput(query="order", candidate_limit=limit)

    assert error.value.code == CandidateErrorCode.INVALID_LIMIT


def test_zero_signal_files_are_never_emitted(repository) -> None:
    result = run(repository, query="squeeze")

    assert "docs/handbook.md" not in paths(result)
    assert all(candidate.explanation.signals for candidate in result)
    assert all(candidate.explanation.score > 0 for candidate in result)


def test_empty_evidence_legitimately_produces_zero_candidates(repository) -> None:
    assert run(repository, query="") == ()


# --------------------------------------------------------------------------
# Identity preservation
# --------------------------------------------------------------------------


def test_repository_and_revision_identities_are_preserved(repository) -> None:
    _prepared, index = repository

    result = run(repository, query="OrderService")

    assert result
    for candidate in result:
        assert candidate.repository_id is index.manifest.repository_id
        assert candidate.revision_id is index.manifest.revision_id


def test_file_identities_come_only_from_the_supplied_index(repository) -> None:
    _prepared, index = repository
    indexed = {item.file_identity.value for item in index.manifest.files}

    result = run(repository, query="order service com.example gradle", build_hints=("pom.xml",))

    assert result
    assert set(paths(result)) <= indexed


def test_candidate_identity_is_deterministic_and_distinct_from_file_identity() -> None:
    first = candidate_identity(REPOSITORY.value, REVISION.value, "src/Main.java")
    again = candidate_identity(REPOSITORY.value, REVISION.value, "src/Main.java")
    other_revision = candidate_identity(REPOSITORY.value, "b" * 40, "src/Main.java")
    other_file = candidate_identity(REPOSITORY.value, REVISION.value, "src/Other.java")

    assert type(first) is CandidateIdentity
    assert first == again
    assert first.value.startswith("candidate:")
    assert len(first.value) == len("candidate:") + 64
    assert first.value[10:] == first.value[10:].lower()
    assert first != other_revision != other_file
    assert first.value != "src/Main.java"
    assert not isinstance(FileIdentity("src/Main.java"), CandidateIdentity)


def test_signal_names_are_unique_per_candidate(repository) -> None:
    result = run(
        repository,
        query="OrderService.java placeOrder com.example.service",
        stack_trace=STACK_TRACE,
        changed_files=(FileIdentity("src/main/java/com/example/service/OrderService.java"),),
    )

    for candidate in result:
        names = [signal.signal for signal in candidate.explanation.signals]
        assert len(names) == len(set(names))
        assert names == sorted(names)


# --------------------------------------------------------------------------
# Input bounds
# --------------------------------------------------------------------------


def test_oversized_combined_evidence_fails_closed() -> None:
    with pytest.raises(CandidateGenerationError) as error:
        CandidateGenerationInput(query="q" * (MAX_QUERY_BYTES + 1))

    assert error.value.code == CandidateErrorCode.INVALID_QUERY


def test_combined_evidence_bound_covers_every_textual_field() -> None:
    half = "q" * (MAX_QUERY_BYTES // 2)

    CandidateGenerationInput(query=half, stack_trace=half[:-1])
    with pytest.raises(CandidateGenerationError):
        CandidateGenerationInput(query=half, stack_trace=half, build_hints=("x",))


def test_changed_file_and_build_hint_counts_are_bounded() -> None:
    with pytest.raises(CandidateGenerationError) as changed:
        CandidateGenerationInput(
            query="q",
            changed_files=tuple(
                FileIdentity(f"src/f{index}.java") for index in range(MAX_CHANGED_FILES + 1)
            ),
        )
    assert changed.value.code == CandidateErrorCode.INVALID_CHANGED_FILES

    with pytest.raises(CandidateGenerationError) as hints:
        CandidateGenerationInput(query="q", build_hints=tuple(f"h{i}" for i in range(65)))
    assert hints.value.code == CandidateErrorCode.INVALID_BUILD_HINTS


@pytest.mark.parametrize(
    "kwargs",
    [
        {"query": 7},
        {"query": "q", "stack_trace": b"bytes"},
        {"query": "q", "build_hints": (" padded ",)},
        {"query": "q", "build_hints": ("",)},
        {"query": "q", "build_hints": "pom.xml"},
        {"query": "q", "changed_files": ("src/a.java",)},
        {"query": "q", "changed_files": {FileIdentity("src/a.java")}},
        {"query": "q", "changed_files": (FileIdentity("a.java"), FileIdentity("a.java"))},
    ],
)
def test_malformed_input_fails_closed(kwargs) -> None:
    with pytest.raises(CandidateGenerationError):
        CandidateGenerationInput(**kwargs)


# --------------------------------------------------------------------------
# Safety
# --------------------------------------------------------------------------


def test_source_tree_is_never_mutated(repository, tmp_path: Path) -> None:
    prepared, _index = repository
    before = tree_digest(Path(prepared.workspace_root))

    run(
        repository,
        query="OrderService placeOrder gradle",
        stack_trace=STACK_TRACE,
        changed_files=(FileIdentity("src/main/java/com/example/service/OrderService.java"),),
        build_hints=("pom.xml",),
    )

    assert tree_digest(Path(prepared.workspace_root)) == before


def test_vcs_and_vendor_exclusions_are_never_candidates(repository) -> None:
    result = run(repository, query="git head ref refs module exports dep index main")

    assert not any(
        path.startswith((".git", "node_modules", "build/", "dist/", "target/"))
        for path in paths(result)
    )


def test_binary_files_are_never_decoded_as_source_text(repository) -> None:
    prepared, index = repository
    binary = next(
        item for item in index.files if item.manifest_file.file_identity.value == "assets/logo.bin"
    )
    assert binary.content_kind is ContentKind.BINARY

    document = next(
        doc for doc in candidates._build_corpus(prepared, index) if doc.path == "assets/logo.bin"
    )

    assert document.content_tokens == frozenset()
    assert set(document.terms) == set(document.path_tokens)


def test_content_changing_after_indexing_fails_closed(repository) -> None:
    prepared, index = repository
    target = Path(prepared.workspace_root) / "docs" / "handbook.md"
    target.write_bytes(b"the order service was rewritten after indexing\n")

    with pytest.raises(CandidateGenerationError) as error:
        run(repository, query="order")

    assert error.value.code == CandidateErrorCode.SOURCE_CHANGED


def test_symlinked_indexed_path_is_never_followed(repository, tmp_path: Path) -> None:
    prepared, index = repository
    root = Path(prepared.workspace_root)
    outside = tmp_path / "outside.md"
    outside.write_bytes(b"secret\n")
    target = root / "docs" / "handbook.md"
    target.unlink()
    target.symlink_to(outside)

    with pytest.raises(CandidateGenerationError) as error:
        run(repository, query="order")

    assert error.value.code in {
        CandidateErrorCode.FILESYSTEM_FAILURE,
        CandidateErrorCode.SOURCE_CHANGED,
    }


def test_generation_requires_no_subprocess_or_network(
    repository, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("candidate generation must not call out")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(os, "system", forbidden)

    assert run(repository, query="OrderService placeOrder", stack_trace=STACK_TRACE)


def test_module_declares_no_retrieval_or_model_dependencies() -> None:
    source = Path(candidates.__file__).read_text(encoding="utf-8")
    imported = {
        line.split()[1].split(".")[0]
        for line in source.splitlines()
        if line.startswith(("import ", "from "))
    }

    assert imported == {
        "__future__",
        "fractions",
        "hashlib",
        "os",
        "re",
        "stat",
        "collections",
        "dataclasses",
        "typing",
        "app",
    }


# --------------------------------------------------------------------------
# Workspace / index identity binding
# --------------------------------------------------------------------------


def prepared_workspace(
    root: Path,
    repository: RepositoryIdentity = REPOSITORY,
    revision: RevisionIdentity = REVISION,
) -> PreparedRepositoryWorkspace:
    return PreparedRepositoryWorkspace(repository, revision, root, WorkspaceMode.READ_ONLY)


def test_matching_identities_continue_to_generate_candidates(tmp_path: Path) -> None:
    root = build_fixture(tmp_path / "source")
    prepared = prepared_workspace(root)
    index = index_repository(prepared)

    result = generate_candidates(prepared, index, CandidateGenerationInput(query="OrderService"))

    assert result
    assert all(candidate.repository_id is REPOSITORY for candidate in result)


def test_repository_identity_mismatch_fails_closed(tmp_path: Path) -> None:
    root = build_fixture(tmp_path / "source")
    owner = prepared_workspace(root, repository=RepositoryIdentity("example/index-owner"))
    mismatched = prepared_workspace(root, repository=RepositoryIdentity("example/imposter"))
    index = index_repository(owner)

    with pytest.raises(CandidateGenerationError) as error:
        generate_candidates(mismatched, index, CandidateGenerationInput(query="OrderService"))

    assert error.value.code == CandidateErrorCode.WORKSPACE_INDEX_MISMATCH


def test_revision_identity_mismatch_fails_closed(tmp_path: Path) -> None:
    root = build_fixture(tmp_path / "source")
    owner = prepared_workspace(root, revision=RevisionIdentity("b" * 40))
    mismatched = prepared_workspace(root, revision=RevisionIdentity("c" * 40))
    index = index_repository(owner)

    with pytest.raises(CandidateGenerationError) as error:
        generate_candidates(mismatched, index, CandidateGenerationInput(query="OrderService"))

    assert error.value.code == CandidateErrorCode.WORKSPACE_INDEX_MISMATCH


def test_mismatch_is_detected_before_any_source_access(tmp_path: Path) -> None:
    root = build_fixture(tmp_path / "source")
    owner = prepared_workspace(root)
    index = index_repository(owner)
    # This mutation would normally fail with SOURCE_CHANGED during corpus
    # construction; the binding check must reject the pair before that point.
    (root / "docs" / "handbook.md").write_bytes(b"mutated after indexing\n")
    stale = prepared_workspace(root, revision=RevisionIdentity("d" * 40))

    with pytest.raises(CandidateGenerationError) as error:
        generate_candidates(stale, index, CandidateGenerationInput(query="order"))

    assert error.value.code == CandidateErrorCode.WORKSPACE_INDEX_MISMATCH


# --------------------------------------------------------------------------
# Explicit analysis bound: the complete index is scored, never truncated
# --------------------------------------------------------------------------


def test_corpus_covers_the_complete_accepted_index(repository) -> None:
    prepared, index = repository

    documents = candidates._build_corpus(prepared, index)

    indexed_paths = {item.manifest_file.file_identity.value for item in index.files}
    assert len(documents) == len(index.files)
    assert {document.path for document in documents} == indexed_paths


def test_candidate_after_every_internal_boundary_remains_retrievable(tmp_path: Path) -> None:
    files = {f"filler_{position:03d}.txt": b"unrelated padding\n" for position in range(16)}
    files["zzz/last_needle_target.txt"] = b"needleword\n"
    root = build_fixture(tmp_path / "source", files)
    prepared = prepared_workspace(root)

    result = generate_candidates(
        prepared, index_repository(prepared), CandidateGenerationInput(query="needleword")
    )

    assert paths(result)[0] == "zzz/last_needle_target.txt"


def test_explicit_changed_file_is_eligible_for_diff_adjacency_scoring(tmp_path: Path) -> None:
    files = {f"filler_{position:03d}.txt": b"unrelated padding\n" for position in range(16)}
    files["zzz/LateChange.java"] = b"public class LateChange {}\n"
    root = build_fixture(tmp_path / "source", files)
    prepared = prepared_workspace(root)
    changed = (FileIdentity("zzz/LateChange.java"),)

    result = generate_candidates(
        prepared,
        index_repository(prepared),
        CandidateGenerationInput(query="late change", changed_files=changed),
    )

    assert signals(find(result, changed[0].value))[SIGNAL_DIFF_ADJACENCY] > 0


def test_oversized_index_fails_closed_instead_of_truncating(tmp_path: Path) -> None:
    root = build_fixture(tmp_path / "source", {"a.txt": b"content\n"})
    prepared = prepared_workspace(root)
    digest = hashlib.sha256(b"content\n").hexdigest()
    overflow_files = tuple(
        ManifestFile(FileIdentity(f"overflow/file{position:07d}.txt"), digest)
        for position in range(candidates.MAX_ANALYZED_FILES + 1)
    )
    manifest = RepositoryManifest(REPOSITORY, REVISION, overflow_files)
    oversized = RepositoryIndex(
        manifest,
        tuple(
            IndexedFile(item, FileLanguage.UNKNOWN, FileRole.UNKNOWN, ContentKind.TEXT, 9)
            for item in manifest.files
        ),
        (),
    )

    with pytest.raises(CandidateGenerationError) as error:
        generate_candidates(prepared, oversized, CandidateGenerationInput(query="content"))

    assert error.value.code == CandidateErrorCode.INDEX_FILE_LIMIT_EXCEEDED


# --------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------


def test_recall_at_k_single_relevant_hit_is_exact() -> None:
    relevant = frozenset({"b.py"})

    assert recall_at_k(("a.py", "b.py"), relevant, 2) == Fraction(1)
    assert recall_at_k(("a.py", "b.py"), relevant, 1) == Fraction(0)


def test_recall_at_k_single_relevant_miss_is_zero() -> None:
    assert recall_at_k(("a.py", "b.py"), frozenset({"z.py"}), 5) == Fraction(0)
    assert recall_at_k((), frozenset({"a.py"}), 5) == Fraction(0)


def test_recall_at_k_counts_distinct_relevant_files_not_mere_hits() -> None:
    relevant = frozenset({"a.py", "c.py"})

    assert type(recall_at_k(("a.py",), relevant, 1)) is Fraction
    assert recall_at_k(("a.py", "x.py", "y.py"), relevant, 5) == Fraction(1, 2)
    assert recall_at_k(("a.py", "x.py", "c.py"), relevant, 5) == Fraction(1)
    assert recall_at_k(("x.py", "y.py", "z.py"), relevant, 5) == Fraction(0)


def test_recall_at_k_duplicate_predictions_never_double_count() -> None:
    relevant = frozenset({"a.py", "b.py"})

    assert recall_at_k(("a.py", "a.py", "a.py"), relevant, 3) == Fraction(1, 2)
    assert recall_at_k(("a.py", "a.py", "b.py"), relevant, 3) == Fraction(1)


def test_recall_at_k_boundary_is_inclusive_and_invalid_input_fails_closed() -> None:
    predicted = ("a.py", "b.py", "c.py")
    relevant = frozenset({"c.py"})

    assert recall_at_k(predicted, relevant, 2) == Fraction(0)
    assert recall_at_k(predicted, relevant, 3) == Fraction(1)
    assert recall_at_k(predicted, relevant, 99) == Fraction(1)
    assert recall_at_k(predicted, relevant, 0) == Fraction(0)

    for bad_k in (-1, True, "3", 1.5):
        with pytest.raises(ValueError):
            recall_at_k(predicted, relevant, bad_k)
    with pytest.raises(ValueError):
        recall_at_k(predicted, frozenset(), 3)


def test_reciprocal_rank_is_exact_and_position_based() -> None:
    predicted = ("a.py", "b.py", "c.py")

    assert reciprocal_rank(predicted, frozenset({"a.py"})) == (1, 1)
    assert reciprocal_rank(predicted, frozenset({"b.py"})) == (1, 2)
    assert reciprocal_rank(predicted, frozenset({"b.py", "c.py"})) == (1, 2)
    assert reciprocal_rank(predicted, frozenset({"z.py"})) == (0, 1)


def test_macro_metric_aggregation_over_actual_predictions_is_exact(tmp_path: Path) -> None:
    """Macro recall/MRR derivation stays proven without the historical workspace."""

    root = build_fixture(
        tmp_path / "source",
        {
            "alpha/QueryEnvelope.py": b"envelope validation\n",
            "beta/QueryIdentities.py": b"identity definitions\n",
            "gamma/unrelated.py": b"nothing relevant lives here\n",
        },
    )
    prepared = prepared_workspace(root)
    index = index_repository(prepared)

    cases = (
        ("synthetic-001", "envelope", frozenset({"alpha/QueryEnvelope.py"})),
        (
            "synthetic-002",
            "identity definitions",
            frozenset({"alpha/QueryEnvelope.py", "beta/QueryIdentities.py"}),
        ),
    )
    predictions = {}
    for case_id, query, _relevant in cases:
        result = generate_candidates(
            prepared, index, CandidateGenerationInput(query=query, candidate_limit=5)
        )
        predictions[case_id] = tuple(candidate.file_identity.value for candidate in result)

    recalls = {
        k: sum(
            (
                recall_at_k(predictions[case_id], relevant, k)
                for case_id, _query, relevant in cases
            ),
            Fraction(0),
        )
        / len(cases)
        for k in (1, 3, 5)
    }
    mrr = sum(
        (
            Fraction(*reciprocal_rank(predictions[case_id], relevant))
            for case_id, _query, relevant in cases
        ),
        Fraction(0),
    ) / len(cases)

    # Case 001 retrieves its single relevant file first; case 002 retrieves
    # exactly one of its two relevant files (rank one), so every Recall@K >= 1
    # is 3/4 and MRR is (1/1 + 1/1) / 2.
    assert recalls[1] == Fraction(3, 4)
    assert recalls[3] == Fraction(3, 4)
    assert recalls[5] == Fraction(3, 4)
    assert mrr == Fraction(1)


# --------------------------------------------------------------------------
# Baseline evidence (evaluation/datasets/localisation/LOCALISATION_BASELINE_V1.json)
# --------------------------------------------------------------------------


BASELINE_REPOSITORY_ID = RepositoryIdentity("01fe25bec239-collab/TestGap-Miner")
BASELINE_REVISION_ID = RevisionIdentity("1c5b8e9be0068c40df1f0144d6c42e53eda7d3e4")
HISTORICAL_WORKSPACE_VARIABLE = "RAG003_BASELINE_WORKSPACE"


@pytest.fixture(scope="module")
def baseline_index():
    """Bind the pinned baseline revision to an independently prepared workspace.

    The dataset pins revision 1c5b8e9be0068c40df1f0144d6c42e53eda7d3e4, whose
    source bytes are not the bytes of this checkout, so REPO_ROOT must never
    stand in for that revision. The root of a workspace prepared at exactly
    that revision (for example a detached Git worktree or a ``git archive``
    extraction) is supplied through the RAG003_BASELINE_WORKSPACE environment
    variable. When it is absent the historical integration tests skip instead
    of silently asserting that the current checkout is the pinned revision.
    """

    supplied = os.environ.get(HISTORICAL_WORKSPACE_VARIABLE)
    if not supplied:
        pytest.skip("historical pinned baseline workspace not supplied")
    root = Path(supplied).resolve()
    if not root.is_dir():
        pytest.fail(
            f"{HISTORICAL_WORKSPACE_VARIABLE} must point at the prepared "
            f"historical workspace directory, got: {root}"
        )
    prepared = PreparedRepositoryWorkspace(
        BASELINE_REPOSITORY_ID,
        BASELINE_REVISION_ID,
        root,
        WorkspaceMode.READ_ONLY,
    )
    return prepared, index_repository(prepared)


def baseline_predictions(baseline_index, case, limit: int = 5) -> tuple[str, ...]:
    prepared, index = baseline_index
    result = generate_candidates(
        prepared, index, CandidateGenerationInput(query=case.query, candidate_limit=limit)
    )
    return tuple(candidate.file_identity.value for candidate in result)


def test_baseline_single_relevant_case_is_retrieved(baseline_index) -> None:
    dataset = load_localisation_dataset(BASELINE_DATASET)
    case = next(c for c in dataset.cases if c.case_id.value == "RAG-BASELINE-001")
    assert len(case.relevant_file_identities) == 1

    predicted = baseline_predictions(baseline_index, case)
    relevant = frozenset(value.value for value in case.relevant_file_identities)

    # On the pinned historical tree the single relevant file is ranked first.
    assert recall_at_k(predicted, relevant, 1) == Fraction(1)
    assert recall_at_k(predicted, relevant, 5) == Fraction(1)


def test_baseline_multi_relevant_case_has_partial_top_five_recall(baseline_index) -> None:
    dataset = load_localisation_dataset(BASELINE_DATASET)
    case = next(c for c in dataset.cases if c.case_id.value == "RAG-BASELINE-002")
    assert len(case.relevant_file_identities) == 2

    predicted = baseline_predictions(baseline_index, case)
    relevant = frozenset(value.value for value in case.relevant_file_identities)

    # On the pinned historical tree exactly one of the two relevant files
    # appears within the first five predictions, so true Recall@K is exactly
    # one half, not a hit rate of 1.
    assert recall_at_k(predicted, relevant, 1) == Fraction(1, 2)
    assert recall_at_k(predicted, relevant, 3) == Fraction(1, 2)
    assert recall_at_k(predicted, relevant, 5) == Fraction(1, 2)


def test_baseline_macro_metrics_are_derived_from_actual_predictions(baseline_index) -> None:
    _prepared, index = baseline_index
    dataset = load_localisation_dataset(BASELINE_DATASET)

    recalls = {
        k: sum(
            (
                recall_at_k(
                    baseline_predictions(baseline_index, case),
                    frozenset(value.value for value in case.relevant_file_identities),
                    k,
                )
                for case in dataset.cases
            ),
            Fraction(0),
        )
        / len(dataset.cases)
        for k in (1, 3, 5)
    }
    mrr = (
        sum(
            (
                Fraction(
                    *reciprocal_rank(
                        baseline_predictions(baseline_index, case),
                        frozenset(value.value for value in case.relevant_file_identities),
                    )
                )
                for case in dataset.cases
            ),
            Fraction(0),
        )
        / len(dataset.cases)
    )

    # Regression pins measured against the pinned historical revision
    # 1c5b8e9be0068c40df1f0144d6c42e53eda7d3e4. Each value follows from the
    # generated rankings on that tree: case 001 places its single relevant
    # file first; case 002 retrieves exactly one of its two relevant files
    # (rank one), so every Recall@K >= 1 is 3/4 and MRR is (1/1 + 1/1) / 2.
    assert index.manifest.repository_id.value == "01fe25bec239-collab/TestGap-Miner"
    assert recalls[1] == Fraction(3, 4)
    assert recalls[3] == Fraction(3, 4)
    assert recalls[5] == Fraction(3, 4)
    assert mrr == Fraction(1)


def test_baseline_score_breakdown_is_deterministic(baseline_index) -> None:
    prepared, index = baseline_index
    dataset = load_localisation_dataset(BASELINE_DATASET)
    case = dataset.cases[0]
    request = CandidateGenerationInput(query=case.query, candidate_limit=5)

    first = generate_candidates(prepared, index, request)
    second = generate_candidates(prepared, index, request)

    assert [candidate.canonical_json() for candidate in first] == [
        candidate.canonical_json() for candidate in second
    ]
    assert all(
        candidate.explanation.score == sum(signals(candidate).values()) for candidate in first
    )


def test_baseline_dataset_is_unmodified() -> None:
    dataset = load_localisation_dataset(BASELINE_DATASET)

    assert dataset.dataset_id.value == "LOCALISATION_BASELINE_V1"
    assert [case.case_id.value for case in dataset.cases] == [
        "RAG-BASELINE-001",
        "RAG-BASELINE-002",
    ]
    assert dataset.canonical_json() == BASELINE_DATASET.read_text(encoding="utf-8")
