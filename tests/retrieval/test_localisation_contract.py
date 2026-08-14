import hashlib
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from app.retrieval import (
    DATASET_SCHEMA_VERSION,
    CandidateFile,
    CandidateIdentity,
    ContextBundle,
    ContextBundleIdentity,
    ContextItem,
    ContextItemIdentity,
    DatasetCaseIdentity,
    DatasetIdentity,
    FileIdentity,
    LocalisationCase,
    LocalisationContractError,
    LocalisationDataset,
    LocalisationErrorCode,
    ManifestFile,
    Provenance,
    RankingExplanation,
    RankingSignal,
    RepositoryIdentity,
    RepositoryManifest,
    RevisionIdentity,
    TokenBudget,
    TrustLabel,
    load_localisation_dataset,
    ordered_candidates,
    parse_localisation_dataset,
)
from app.retrieval.localisation import MAX_CONTEXT_BYTES


ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = (
    ROOT / "evaluation" / "datasets" / "localisation" / "LOCALISATION_BASELINE_V1.json"
)
REPOSITORY_ID = RepositoryIdentity("01fe25bec239-collab/TestGap-Miner")
REVISION_ID = RevisionIdentity("1c5b8e9be0068c40df1f0144d6c42e53eda7d3e4")
FILE_ID = FileIdentity("apps/api/app/retrieval/localisation.py")
CONTENT = "def locate():\n    return 'context'"
CONTENT_SHA256 = hashlib.sha256(CONTENT.encode()).hexdigest()


def explanation(rank: int = 1, score: int = 100) -> RankingExplanation:
    return RankingExplanation(
        rank=rank,
        score=score,
        signals=(
            RankingSignal("path_match", 40, "Query term matched the repository path."),
            RankingSignal("symbol_match", 60, "Query term matched a declared symbol."),
        ),
    )


def candidate(**overrides: object) -> CandidateFile:
    values: dict[str, object] = {
        "candidate_id": CandidateIdentity("candidate-001"),
        "repository_id": REPOSITORY_ID,
        "revision_id": REVISION_ID,
        "file_identity": FILE_ID,
        "explanation": explanation(),
    }
    values.update(overrides)
    return CandidateFile(**values)  # type: ignore[arg-type]


def provenance(**overrides: object) -> Provenance:
    values: dict[str, object] = {
        "repository_id": REPOSITORY_ID,
        "revision_id": REVISION_ID,
        "file_identity": FILE_ID,
        "start_line": 1,
        "end_line": 2,
        "content_sha256": CONTENT_SHA256,
    }
    values.update(overrides)
    return Provenance(**values)  # type: ignore[arg-type]


def context_item(**overrides: object) -> ContextItem:
    values: dict[str, object] = {
        "context_item_id": ContextItemIdentity("context-001"),
        "candidate_id": CandidateIdentity("candidate-001"),
        "provenance": provenance(),
        "trust_label": TrustLabel.UNTRUSTED_REPOSITORY_TEXT,
        "content": CONTENT,
        "token_count": 5,
    }
    values.update(overrides)
    return ContextItem(**values)  # type: ignore[arg-type]


def dataset_case(**overrides: object) -> LocalisationCase:
    values: dict[str, object] = {
        "case_id": DatasetCaseIdentity("case-001"),
        "repository_id": REPOSITORY_ID,
        "revision_id": REVISION_ID,
        "query": "Locate the retrieval contract.",
        "relevant_file_identities": (FILE_ID,),
    }
    values.update(overrides)
    return LocalisationCase(**values)  # type: ignore[arg-type]


def assert_code(code: LocalisationErrorCode, operation) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(LocalisationContractError) as raised:
        operation()
    assert raised.value.code is code


def test_repository_manifest_is_valid_sorted_and_canonical() -> None:
    second = ManifestFile(FileIdentity("z.py"), "b" * 64)
    first = ManifestFile(FileIdentity("a.py"), "a" * 64)
    manifest = RepositoryManifest(REPOSITORY_ID, REVISION_ID, (second, first))

    assert manifest.files == (first, second)
    assert manifest == RepositoryManifest(REPOSITORY_ID, REVISION_ID, (first, second))
    assert manifest.canonical_json() == RepositoryManifest(
        REPOSITORY_ID, REVISION_ID, (first, second)
    ).canonical_json()


@pytest.mark.parametrize(
    "operation,code",
    [
        (lambda: RepositoryIdentity("/tmp/inferred"), LocalisationErrorCode.INVALID_IDENTITY),
        (lambda: RevisionIdentity("abc123"), LocalisationErrorCode.INVALID_REVISION),
        (lambda: RevisionIdentity("A" * 40), LocalisationErrorCode.INVALID_REVISION),
        (lambda: FileIdentity("../outside.py"), LocalisationErrorCode.INVALID_FILE_IDENTITY),
        (
            lambda: RepositoryManifest("repo", REVISION_ID, ()),
            LocalisationErrorCode.INVALID_CONTEXT,
        ),
    ],
)
def test_repository_manifest_rejects_malformed_values(operation, code) -> None:  # type: ignore[no-untyped-def]
    assert_code(code, operation)


@pytest.mark.parametrize(
    "value",
    [
        ".",
        "\x00",
        "a\x00b",
        "dir/\x00file.py",
        "",
        "/absolute/path.py",
        "../outside.py",
        "./file.py",
        "dir/../file.py",
        "dir\\file.py",
        " file.py",
        "file.py ",
        "dir//file.py",
        "a" * 4_097,
    ],
)
def test_file_identity_rejects_noncanonical_or_impossible_paths(value: str) -> None:
    assert_code(
        LocalisationErrorCode.INVALID_FILE_IDENTITY,
        lambda: FileIdentity(value),
    )


def test_file_identity_accepts_canonical_repository_relative_path() -> None:
    assert FileIdentity(
        "apps/api/app/retrieval/localisation.py"
    ).value == "apps/api/app/retrieval/localisation.py"


def test_manifest_duplicate_and_conflicting_file_identities_fail_closed() -> None:
    first = ManifestFile(FileIdentity("a.py"), "a" * 64)
    assert_code(
        LocalisationErrorCode.DUPLICATE_IDENTITY,
        lambda: RepositoryManifest(REPOSITORY_ID, REVISION_ID, (first, first)),
    )
    assert_code(
        LocalisationErrorCode.IDENTITY_CONFLICT,
        lambda: RepositoryManifest(
            REPOSITORY_ID,
            REVISION_ID,
            (first, ManifestFile(FileIdentity("a.py"), "b" * 64)),
        ),
    )


def test_candidate_has_explicit_nonconflated_identity_and_structured_explanation() -> None:
    value = candidate()

    assert value.candidate_id == CandidateIdentity("candidate-001")
    assert value.candidate_id != RepositoryIdentity("candidate-001")
    assert value.explanation.rank == 1
    assert [signal.signal for signal in value.explanation.signals] == [
        "path_match",
        "symbol_match",
    ]
    assert json.loads(value.canonical_json())["explanation"]["signals"][0]["contribution"] == 40


@pytest.mark.parametrize(
    "operation",
    [
        lambda: candidate(candidate_id="candidate-001"),
        lambda: candidate(file_identity=FileIdentity("../bad.py")),
        lambda: RankingExplanation(0, 0, (RankingSignal("path", 1, "Path evidence"),)),
        lambda: RankingExplanation(1, 0, ()),
        lambda: RankingSignal("opaque string", 1, "Not structured"),
    ],
)
def test_candidate_and_ranking_explanation_reject_malformed_values(operation) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(LocalisationContractError):
        operation()


def test_candidate_ordering_is_deterministic() -> None:
    later = candidate(
        candidate_id=CandidateIdentity("candidate-002"), explanation=explanation(rank=2)
    )
    first = candidate()

    assert ordered_candidates((later, first)) == (first, later)


def test_candidate_duplicate_and_conflicting_identity_behavior() -> None:
    first = candidate()
    assert_code(
        LocalisationErrorCode.DUPLICATE_IDENTITY,
        lambda: ordered_candidates((first, first)),
    )
    assert_code(
        LocalisationErrorCode.IDENTITY_CONFLICT,
        lambda: ordered_candidates(
            (first, candidate(file_identity=FileIdentity("different.py")))
        ),
    )


def test_provenance_is_explicit_and_canonical() -> None:
    value = provenance()

    assert value.repository_id is REPOSITORY_ID
    assert value.revision_id is REVISION_ID
    assert value.file_identity is FILE_ID
    assert json.loads(value.canonical_json())["content_sha256"] == CONTENT_SHA256


@pytest.mark.parametrize(
    "operation",
    [
        lambda: provenance(start_line=0),
        lambda: provenance(start_line=3, end_line=2),
        lambda: provenance(content_sha256="ABC"),
    ],
)
def test_provenance_rejects_malformed_ranges_and_hashes(operation) -> None:  # type: ignore[no-untyped-def]
    assert_code(LocalisationErrorCode.INVALID_PROVENANCE, operation)


def test_context_item_validates_trust_content_hash_and_separate_identity() -> None:
    value = context_item()

    assert value.trust_label is TrustLabel.UNTRUSTED_REPOSITORY_TEXT
    assert value.context_item_id != ContextItemIdentity(value.candidate_id.value)
    assert value.candidate_id != CandidateIdentity(value.context_item_id.value)


def test_context_item_rejects_invalid_trust_and_provenance() -> None:
    assert_code(
        LocalisationErrorCode.INVALID_TRUST_LABEL,
        lambda: context_item(trust_label="UNTRUSTED_REPOSITORY_TEXT"),
    )
    assert_code(
        LocalisationErrorCode.INVALID_PROVENANCE,
        lambda: context_item(content="changed content"),
    )


def test_context_item_preserves_source_whitespace_and_hashes_exact_bytes() -> None:
    original_content = "    if authenticated:\n        return session\n"
    digest = hashlib.sha256(original_content.encode("utf-8")).hexdigest()
    item = context_item(
        content=original_content,
        provenance=provenance(content_sha256=digest),
    )

    assert item.content == original_content
    serialized = json.loads(item.canonical_json())
    assert serialized["content"] == original_content
    assert serialized["provenance"]["content_sha256"] == digest


@pytest.mark.parametrize(
    "original_content", [" ", "\t", "\n", "\nline1\n", "\tindented\n", "line1 "]
)
def test_context_item_accepts_and_preserves_nonempty_whitespace(
    original_content: str,
) -> None:
    digest = hashlib.sha256(original_content.encode("utf-8")).hexdigest()
    item = context_item(
        content=original_content,
        provenance=provenance(content_sha256=digest),
    )

    assert item.content == original_content
    assert json.loads(item.canonical_json())["content"] == original_content


def test_context_item_rejects_whitespace_change_with_stale_digest() -> None:
    original_content = "    indented = True\n"
    digest = hashlib.sha256(original_content.encode("utf-8")).hexdigest()

    assert_code(
        LocalisationErrorCode.INVALID_PROVENANCE,
        lambda: context_item(
            content=original_content.rstrip(),
            provenance=provenance(content_sha256=digest),
        ),
    )


@pytest.mark.parametrize(
    "content", ["", "\ud800", "x" * (MAX_CONTEXT_BYTES + 1)]
)
def test_context_item_rejects_empty_invalid_utf8_and_oversized_content(content: str) -> None:
    assert_code(
        LocalisationErrorCode.INVALID_CONTEXT,
        lambda: context_item(content=content),
    )


def test_query_and_ranking_detail_still_reject_outer_whitespace() -> None:
    assert_code(
        LocalisationErrorCode.INVALID_DATASET,
        lambda: dataset_case(query=" query"),
    )
    assert_code(
        LocalisationErrorCode.INVALID_RANKING,
        lambda: RankingSignal("path", 1, "detail "),
    )


def test_context_bundle_preserves_semantic_order_and_exact_token_accounting() -> None:
    first = context_item()
    second_content = "second bounded item"
    second = context_item(
        context_item_id=ContextItemIdentity("context-002"),
        candidate_id=CandidateIdentity("candidate-002"),
        provenance=provenance(
            file_identity=FileIdentity("second.py"),
            content_sha256=hashlib.sha256(second_content.encode()).hexdigest(),
        ),
        content=second_content,
        token_count=7,
    )
    bundle = ContextBundle(
        ContextBundleIdentity("bundle-001"),
        REPOSITORY_ID,
        REVISION_ID,
        (second, first),
        TokenBudget(max_tokens=12, consumed_tokens=12),
    )

    assert bundle.items == (second, first)
    assert bundle.token_budget.within_budget
    assert bundle.token_budget.remaining_tokens == 0
    assert json.loads(bundle.canonical_json())["items"][0]["context_item_id"] == "context-002"


def test_token_budget_accepts_exact_boundary_and_rejects_overflow() -> None:
    assert TokenBudget(10, 10).within_budget
    assert_code(
        LocalisationErrorCode.INVALID_TOKEN_BUDGET,
        lambda: TokenBudget(10, 11),
    )


@pytest.mark.parametrize(
    "operation",
    [
        lambda: TokenBudget(0, 0),
        lambda: TokenBudget(True, 0),
        lambda: TokenBudget(10, -1),
        lambda: TokenBudget(2_000_001, 0),
        lambda: context_item(token_count=0),
    ],
)
def test_malformed_token_values_fail_closed(operation) -> None:  # type: ignore[no-untyped-def]
    assert_code(LocalisationErrorCode.INVALID_TOKEN_BUDGET, operation)


def test_bundle_rejects_count_mismatch_source_mismatch_and_duplicate_items() -> None:
    item = context_item()
    build = lambda items, budget: ContextBundle(  # noqa: E731
        ContextBundleIdentity("bundle-001"), REPOSITORY_ID, REVISION_ID, items, budget
    )
    assert_code(
        LocalisationErrorCode.INVALID_TOKEN_BUDGET,
        lambda: build((item,), TokenBudget(10, 4)),
    )
    assert_code(
        LocalisationErrorCode.INVALID_PROVENANCE,
        lambda: build(
            (
                context_item(
                    provenance=provenance(
                        revision_id=RevisionIdentity("a" * 40)
                    )
                ),
            ),
            TokenBudget(5, 5),
        ),
    )
    assert_code(
        LocalisationErrorCode.DUPLICATE_IDENTITY,
        lambda: build((item, item), TokenBudget(10, 10)),
    )
    assert_code(
        LocalisationErrorCode.IDENTITY_CONFLICT,
        lambda: build(
            (item, context_item(token_count=6)),
            TokenBudget(11, 11),
        ),
    )


def test_checked_in_dataset_is_valid_labelled_and_metric_compatible() -> None:
    dataset = load_localisation_dataset(DATASET_PATH)

    assert dataset.schema_version == DATASET_SCHEMA_VERSION
    assert len(dataset.cases) == 2
    assert [len(case.relevant_file_identities) for case in dataset.cases] == [1, 2]
    for case in dataset.cases:
        assert all((ROOT / file_id.value).is_file() for file_id in case.relevant_file_identities)
        predicted = [FileIdentity("unrelated.py"), *case.relevant_file_identities]
        relevant = set(case.relevant_file_identities)
        recall_at_2 = len(set(predicted[:2]) & relevant) / len(relevant)
        first_relevant_rank = next(
            rank for rank, file_id in enumerate(predicted, start=1) if file_id in relevant
        )
        assert recall_at_2 > 0
        assert first_relevant_rank == 2


def test_dataset_loading_and_serialization_are_deterministic() -> None:
    first = load_localisation_dataset(DATASET_PATH)
    second = parse_localisation_dataset(DATASET_PATH.read_text(encoding="utf-8"))

    assert first == second
    assert first.canonical_json() == DATASET_PATH.read_text(encoding="utf-8")


def test_dataset_loader_rejects_non_utf8_through_contract_error(tmp_path: Path) -> None:
    path = tmp_path / "invalid-utf8.json"
    path.write_bytes(b"\xff\xfe")

    assert_code(
        LocalisationErrorCode.INVALID_DATASET,
        lambda: load_localisation_dataset(path),
    )


def test_dataset_loader_rejects_nul_path_through_contract_error() -> None:
    assert_code(
        LocalisationErrorCode.INVALID_DATASET,
        lambda: load_localisation_dataset("\x00"),
    )


def test_zero_ground_truth_and_duplicate_relevant_files_are_rejected() -> None:
    assert_code(
        LocalisationErrorCode.INVALID_DATASET,
        lambda: dataset_case(relevant_file_identities=()),
    )
    assert_code(
        LocalisationErrorCode.DUPLICATE_IDENTITY,
        lambda: dataset_case(relevant_file_identities=(FILE_ID, FILE_ID)),
    )


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        '{"schema_version":"testgap.localisation-baseline.v1"}',
        '{"schema_version":"v","schema_version":"v2","dataset_id":"d","cases":[]}',
        json.dumps(
            {
                "schema_version": DATASET_SCHEMA_VERSION,
                "dataset_id": "dataset",
                "cases": [
                    {
                        "case_id": "case",
                        "repository_id": "repo",
                        "revision_id": "a" * 40,
                        "query": "query",
                        "relevant_file_identities": ["../bad.py"],
                    }
                ],
            }
        ),
    ],
)
def test_malformed_dataset_records_fail_closed(text: str) -> None:
    with pytest.raises(LocalisationContractError):
        parse_localisation_dataset(text)


def test_duplicate_and_conflicting_dataset_cases_are_rejected() -> None:
    first = dataset_case()
    create = lambda cases: LocalisationDataset(  # noqa: E731
        DATASET_SCHEMA_VERSION, DatasetIdentity("dataset"), cases
    )
    assert_code(
        LocalisationErrorCode.DUPLICATE_IDENTITY,
        lambda: create((first, first)),
    )
    assert_code(
        LocalisationErrorCode.IDENTITY_CONFLICT,
        lambda: create((first, dataset_case(query="Different query."))),
    )


def test_contract_values_are_frozen() -> None:
    with pytest.raises(FrozenInstanceError):
        candidate().file_identity = FileIdentity("changed.py")  # type: ignore[misc]
