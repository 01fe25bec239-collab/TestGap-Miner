"""Provider-neutral localisation and bounded repository-context values."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, fields, is_dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Final, NoReturn


CONTRACT_VERSION: Final = "1.0.0-draft.1"
DATASET_SCHEMA_VERSION: Final = "testgap.localisation-baseline.v1"
MAX_IDENTITY_LENGTH: Final = 256
MAX_QUERY_BYTES: Final = 16_384
MAX_CONTEXT_BYTES: Final = 1_048_576
MAX_TOKEN_BUDGET: Final = 2_000_000
MAX_MANIFEST_FILES: Final = 1_000_000
MAX_CANDIDATES: Final = 100_000
MAX_CONTEXT_ITEMS: Final = 10_000
MAX_RANKING_SIGNALS: Final = 64
MAX_DATASET_CASES: Final = 10_000
MAX_RELEVANT_FILES: Final = 10_000

_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+\-]*\Z")
_REVISION = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class LocalisationErrorCode(StrEnum):
    INVALID_IDENTITY = "INVALID_IDENTITY"
    INVALID_REVISION = "INVALID_REVISION"
    INVALID_FILE_IDENTITY = "INVALID_FILE_IDENTITY"
    INVALID_RANKING = "INVALID_RANKING"
    INVALID_PROVENANCE = "INVALID_PROVENANCE"
    INVALID_TRUST_LABEL = "INVALID_TRUST_LABEL"
    INVALID_CONTEXT = "INVALID_CONTEXT"
    INVALID_TOKEN_BUDGET = "INVALID_TOKEN_BUDGET"
    DUPLICATE_IDENTITY = "DUPLICATE_IDENTITY"
    IDENTITY_CONFLICT = "IDENTITY_CONFLICT"
    INVALID_DATASET = "INVALID_DATASET"


class LocalisationContractError(ValueError):
    """Stable fail-closed error for malformed contract values."""

    def __init__(self, code: LocalisationErrorCode, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code.value}: {detail}")


class _CanonicalValue:
    def canonical_dict(self) -> dict[str, object]:
        value = _domain_value(self)
        if not isinstance(value, dict):  # pragma: no cover - dataclass invariant
            raise TypeError("canonical value must serialize to an object")
        return value

    def canonical_json(self) -> str:
        return json.dumps(
            self.canonical_dict(), ensure_ascii=False, separators=(",", ":"), sort_keys=True
        )


@dataclass(frozen=True, slots=True)
class _Identity:
    value: str

    def __post_init__(self) -> None:
        if (
            type(self.value) is not str
            or not 1 <= len(self.value) <= MAX_IDENTITY_LENGTH
            or _IDENTIFIER.fullmatch(self.value) is None
        ):
            _raise(LocalisationErrorCode.INVALID_IDENTITY, f"invalid {type(self).__name__}")


class RepositoryIdentity(_Identity):
    """Logical repository identity; never inferred from a local path."""


class RevisionIdentity(_Identity):
    """Pinned full Git object identity (SHA-1 or SHA-256)."""

    def __post_init__(self) -> None:
        if type(self.value) is not str or _REVISION.fullmatch(self.value) is None:
            _raise(
                LocalisationErrorCode.INVALID_REVISION,
                "revision must be a lowercase full 40- or 64-hex Git object identity",
            )


class FileIdentity(_Identity):
    """Canonical repository-relative POSIX path identity."""

    def __post_init__(self) -> None:
        value = self.value
        if type(value) is not str or not value or len(value) > 4_096:
            _raise(LocalisationErrorCode.INVALID_FILE_IDENTITY, "file identity is invalid")
        path = PurePosixPath(value)
        if (
            not value.isascii()
            or value != value.strip()
            or value == "."
            or "\x00" in value
            or "\\" in value
            or path.is_absolute()
            or path.as_posix() != value
            or any(part in {"", ".", ".."} for part in path.parts)
        ):
            _raise(
                LocalisationErrorCode.INVALID_FILE_IDENTITY,
                "file identity must be a canonical repository-relative POSIX path",
            )


class CandidateIdentity(_Identity):
    pass


class ContextItemIdentity(_Identity):
    pass


class ContextBundleIdentity(_Identity):
    pass


class DatasetIdentity(_Identity):
    pass


class DatasetCaseIdentity(_Identity):
    pass


class TrustLabel(StrEnum):
    UNTRUSTED_REPOSITORY_TEXT = "UNTRUSTED_REPOSITORY_TEXT"


@dataclass(frozen=True, slots=True)
class ManifestFile(_CanonicalValue):
    file_identity: FileIdentity
    content_sha256: str

    def __post_init__(self) -> None:
        _require_type(self.file_identity, FileIdentity, "file_identity")
        _require_sha256(self.content_sha256, "content_sha256")


@dataclass(frozen=True, slots=True)
class RepositoryManifest(_CanonicalValue):
    repository_id: RepositoryIdentity
    revision_id: RevisionIdentity
    files: tuple[ManifestFile, ...]

    def __post_init__(self) -> None:
        _require_type(self.repository_id, RepositoryIdentity, "repository_id")
        _require_type(self.revision_id, RevisionIdentity, "revision_id")
        supplied = _typed_tuple(self.files, ManifestFile, "files")
        if len(supplied) > MAX_MANIFEST_FILES:
            _raise(LocalisationErrorCode.INVALID_CONTEXT, "manifest file limit exceeded")
        _reject_duplicate_identities(supplied, "file_identity", "manifest file")
        object.__setattr__(
            self, "files", tuple(sorted(supplied, key=lambda item: item.file_identity.value))
        )


@dataclass(frozen=True, slots=True)
class RankingSignal(_CanonicalValue):
    signal: str
    contribution: int
    detail: str

    def __post_init__(self) -> None:
        _require_identifier_text(self.signal, "ranking signal")
        _bounded_integer(
            self.contribution,
            "ranking contribution",
            minimum=-1_000_000_000,
            maximum=1_000_000_000,
            code=LocalisationErrorCode.INVALID_RANKING,
        )
        _require_text(self.detail, "ranking detail", 4_096, LocalisationErrorCode.INVALID_RANKING)


@dataclass(frozen=True, slots=True)
class RankingExplanation(_CanonicalValue):
    rank: int
    score: int
    signals: tuple[RankingSignal, ...]

    def __post_init__(self) -> None:
        _bounded_integer(
            self.rank,
            "rank",
            minimum=1,
            maximum=MAX_CANDIDATES,
            code=LocalisationErrorCode.INVALID_RANKING,
        )
        _bounded_integer(
            self.score,
            "score",
            minimum=-1_000_000_000,
            maximum=1_000_000_000,
            code=LocalisationErrorCode.INVALID_RANKING,
        )
        supplied = _typed_tuple(self.signals, RankingSignal, "ranking signals")
        if not supplied or len(supplied) > MAX_RANKING_SIGNALS:
            _raise(
                LocalisationErrorCode.INVALID_RANKING,
                f"ranking explanation requires 1..{MAX_RANKING_SIGNALS} signals",
            )
        by_name: dict[str, RankingSignal] = {}
        for signal in supplied:
            if signal.signal in by_name:
                code = (
                    LocalisationErrorCode.DUPLICATE_IDENTITY
                    if by_name[signal.signal] == signal
                    else LocalisationErrorCode.IDENTITY_CONFLICT
                )
                _raise(code, f"duplicate ranking signal {signal.signal}")
            by_name[signal.signal] = signal
        object.__setattr__(
            self,
            "signals",
            tuple(sorted(supplied, key=lambda value: value.signal)),
        )


@dataclass(frozen=True, slots=True)
class CandidateFile(_CanonicalValue):
    candidate_id: CandidateIdentity
    repository_id: RepositoryIdentity
    revision_id: RevisionIdentity
    file_identity: FileIdentity
    explanation: RankingExplanation

    def __post_init__(self) -> None:
        _require_type(self.candidate_id, CandidateIdentity, "candidate_id")
        _require_type(self.repository_id, RepositoryIdentity, "repository_id")
        _require_type(self.revision_id, RevisionIdentity, "revision_id")
        _require_type(self.file_identity, FileIdentity, "file_identity")
        _require_type(self.explanation, RankingExplanation, "explanation")


def ordered_candidates(values: Iterable[CandidateFile]) -> tuple[CandidateFile, ...]:
    """Validate candidate identity uniqueness and return stable rank/identity order."""

    supplied = _typed_tuple(values, CandidateFile, "candidates")
    if len(supplied) > MAX_CANDIDATES:
        _raise(LocalisationErrorCode.INVALID_RANKING, "candidate limit exceeded")
    _reject_duplicate_identities(supplied, "candidate_id", "candidate")
    return tuple(
        sorted(supplied, key=lambda value: (value.explanation.rank, value.candidate_id.value))
    )


@dataclass(frozen=True, slots=True)
class Provenance(_CanonicalValue):
    repository_id: RepositoryIdentity
    revision_id: RevisionIdentity
    file_identity: FileIdentity
    start_line: int
    end_line: int
    content_sha256: str

    def __post_init__(self) -> None:
        _require_type(self.repository_id, RepositoryIdentity, "repository_id")
        _require_type(self.revision_id, RevisionIdentity, "revision_id")
        _require_type(self.file_identity, FileIdentity, "file_identity")
        _bounded_integer(
            self.start_line,
            "start_line",
            minimum=1,
            maximum=2_147_483_647,
            code=LocalisationErrorCode.INVALID_PROVENANCE,
        )
        _bounded_integer(
            self.end_line,
            "end_line",
            minimum=1,
            maximum=2_147_483_647,
            code=LocalisationErrorCode.INVALID_PROVENANCE,
        )
        if self.end_line < self.start_line:
            _raise(LocalisationErrorCode.INVALID_PROVENANCE, "end_line precedes start_line")
        _require_sha256(self.content_sha256, "content_sha256")


@dataclass(frozen=True, slots=True)
class ContextItem(_CanonicalValue):
    context_item_id: ContextItemIdentity
    candidate_id: CandidateIdentity
    provenance: Provenance
    trust_label: TrustLabel
    content: str
    token_count: int

    def __post_init__(self) -> None:
        _require_type(self.context_item_id, ContextItemIdentity, "context_item_id")
        _require_type(self.candidate_id, CandidateIdentity, "candidate_id")
        _require_type(self.provenance, Provenance, "provenance")
        if type(self.trust_label) is not TrustLabel:
            _raise(LocalisationErrorCode.INVALID_TRUST_LABEL, "trust_label is invalid")
        _require_context_content(self.content)
        if hashlib.sha256(self.content.encode("utf-8")).hexdigest() != self.provenance.content_sha256:
            _raise(
                LocalisationErrorCode.INVALID_PROVENANCE,
                "context content does not match provenance content_sha256",
            )
        _bounded_integer(
            self.token_count,
            "token_count",
            minimum=1,
            maximum=MAX_TOKEN_BUDGET,
            code=LocalisationErrorCode.INVALID_TOKEN_BUDGET,
        )


@dataclass(frozen=True, slots=True)
class TokenBudget(_CanonicalValue):
    max_tokens: int
    consumed_tokens: int

    def __post_init__(self) -> None:
        _bounded_integer(
            self.max_tokens,
            "max_tokens",
            minimum=1,
            maximum=MAX_TOKEN_BUDGET,
            code=LocalisationErrorCode.INVALID_TOKEN_BUDGET,
        )
        _bounded_integer(
            self.consumed_tokens,
            "consumed_tokens",
            minimum=0,
            maximum=MAX_TOKEN_BUDGET,
            code=LocalisationErrorCode.INVALID_TOKEN_BUDGET,
        )
        if self.consumed_tokens > self.max_tokens:
            _raise(LocalisationErrorCode.INVALID_TOKEN_BUDGET, "token budget overflow")

    @property
    def remaining_tokens(self) -> int:
        return self.max_tokens - self.consumed_tokens

    @property
    def within_budget(self) -> bool:
        return self.consumed_tokens <= self.max_tokens


@dataclass(frozen=True, slots=True)
class ContextBundle(_CanonicalValue):
    context_bundle_id: ContextBundleIdentity
    repository_id: RepositoryIdentity
    revision_id: RevisionIdentity
    items: tuple[ContextItem, ...]
    token_budget: TokenBudget

    def __post_init__(self) -> None:
        _require_type(self.context_bundle_id, ContextBundleIdentity, "context_bundle_id")
        _require_type(self.repository_id, RepositoryIdentity, "repository_id")
        _require_type(self.revision_id, RevisionIdentity, "revision_id")
        supplied = _typed_tuple(self.items, ContextItem, "context items")
        if len(supplied) > MAX_CONTEXT_ITEMS:
            _raise(LocalisationErrorCode.INVALID_CONTEXT, "context item limit exceeded")
        _reject_duplicate_identities(supplied, "context_item_id", "context item")
        _require_type(self.token_budget, TokenBudget, "token_budget")
        for item in supplied:
            if (
                item.provenance.repository_id != self.repository_id
                or item.provenance.revision_id != self.revision_id
            ):
                _raise(
                    LocalisationErrorCode.INVALID_PROVENANCE,
                    "context item source does not match bundle repository revision",
                )
        represented_tokens = sum(item.token_count for item in supplied)
        if represented_tokens != self.token_budget.consumed_tokens:
            _raise(
                LocalisationErrorCode.INVALID_TOKEN_BUDGET,
                "consumed_tokens must equal the represented context item token count",
            )
        object.__setattr__(self, "items", supplied)


@dataclass(frozen=True, slots=True)
class LocalisationCase(_CanonicalValue):
    case_id: DatasetCaseIdentity
    repository_id: RepositoryIdentity
    revision_id: RevisionIdentity
    query: str
    relevant_file_identities: tuple[FileIdentity, ...]

    def __post_init__(self) -> None:
        _require_type(self.case_id, DatasetCaseIdentity, "case_id")
        _require_type(self.repository_id, RepositoryIdentity, "repository_id")
        _require_type(self.revision_id, RevisionIdentity, "revision_id")
        _require_text(self.query, "query", MAX_QUERY_BYTES, LocalisationErrorCode.INVALID_DATASET)
        relevant = _typed_tuple(
            self.relevant_file_identities, FileIdentity, "relevant_file_identities"
        )
        if not relevant or len(relevant) > MAX_RELEVANT_FILES:
            _raise(
                LocalisationErrorCode.INVALID_DATASET,
                f"relevant_file_identities requires 1..{MAX_RELEVANT_FILES} values",
            )
        if len(set(relevant)) != len(relevant):
            _raise(LocalisationErrorCode.DUPLICATE_IDENTITY, "duplicate relevant file identity")
        object.__setattr__(
            self,
            "relevant_file_identities",
            tuple(sorted(relevant, key=lambda value: value.value)),
        )


@dataclass(frozen=True, slots=True)
class LocalisationDataset(_CanonicalValue):
    schema_version: str
    dataset_id: DatasetIdentity
    cases: tuple[LocalisationCase, ...]

    def __post_init__(self) -> None:
        if self.schema_version != DATASET_SCHEMA_VERSION:
            _raise(LocalisationErrorCode.INVALID_DATASET, "unsupported dataset schema_version")
        _require_type(self.dataset_id, DatasetIdentity, "dataset_id")
        supplied = _typed_tuple(self.cases, LocalisationCase, "cases")
        if not supplied or len(supplied) > MAX_DATASET_CASES:
            _raise(
                LocalisationErrorCode.INVALID_DATASET,
                f"dataset requires 1..{MAX_DATASET_CASES} cases",
            )
        _reject_duplicate_identities(supplied, "case_id", "dataset case")
        object.__setattr__(
            self, "cases", tuple(sorted(supplied, key=lambda case: case.case_id.value))
        )

    def canonical_json(self) -> str:
        return json.dumps(
            self.canonical_dict(), ensure_ascii=False, indent=2, sort_keys=True
        ) + "\n"


def parse_localisation_dataset(text: str) -> LocalisationDataset:
    if type(text) is not str:
        _raise(LocalisationErrorCode.INVALID_DATASET, "dataset JSON must be text")
    try:
        raw = json.loads(text, object_pairs_hook=_reject_duplicate_json_keys)
    except json.JSONDecodeError as error:
        _raise(LocalisationErrorCode.INVALID_DATASET, f"malformed dataset JSON: {error.msg}")
    root = _mapping(raw, {"schema_version", "dataset_id", "cases"}, "dataset")
    raw_cases = root["cases"]
    if type(raw_cases) is not list:
        _raise(LocalisationErrorCode.INVALID_DATASET, "cases must be an array")
    cases = tuple(_parse_case(value, index) for index, value in enumerate(raw_cases))
    return LocalisationDataset(
        schema_version=root["schema_version"],
        dataset_id=DatasetIdentity(root["dataset_id"]),
        cases=cases,
    )


def load_localisation_dataset(path: Path | str) -> LocalisationDataset:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, TypeError, UnicodeDecodeError, ValueError) as error:
        _raise(LocalisationErrorCode.INVALID_DATASET, f"cannot read dataset: {error}")
    return parse_localisation_dataset(text)


def _parse_case(raw: object, index: int) -> LocalisationCase:
    node = _mapping(
        raw,
        {"case_id", "repository_id", "revision_id", "query", "relevant_file_identities"},
        f"cases[{index}]",
    )
    relevant = node["relevant_file_identities"]
    if type(relevant) is not list:
        _raise(
            LocalisationErrorCode.INVALID_DATASET,
            f"cases[{index}].relevant_file_identities must be an array",
        )
    return LocalisationCase(
        case_id=DatasetCaseIdentity(node["case_id"]),
        repository_id=RepositoryIdentity(node["repository_id"]),
        revision_id=RevisionIdentity(node["revision_id"]),
        query=node["query"],
        relevant_file_identities=tuple(FileIdentity(value) for value in relevant),
    )


def _mapping(raw: object, keys: set[str], label: str) -> dict[str, object]:
    if type(raw) is not dict:
        _raise(LocalisationErrorCode.INVALID_DATASET, f"{label} must be an object")
    actual = set(raw)
    if actual != keys:
        _raise(
            LocalisationErrorCode.INVALID_DATASET,
            f"{label} fields must be exactly {sorted(keys)}",
        )
    return raw


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _raise(LocalisationErrorCode.DUPLICATE_IDENTITY, f"duplicate JSON key {key}")
        result[key] = value
    return result


def _typed_tuple(values: Iterable[object], expected: type, label: str) -> tuple:
    if isinstance(values, (str, bytes, bytearray, set, frozenset, dict)):
        _raise(LocalisationErrorCode.INVALID_CONTEXT, f"{label} must be an ordered iterable")
    try:
        supplied = tuple(values)
    except TypeError:
        _raise(LocalisationErrorCode.INVALID_CONTEXT, f"{label} must be iterable")
    if not all(isinstance(value, expected) for value in supplied):
        _raise(
            LocalisationErrorCode.INVALID_CONTEXT,
            f"{label} must contain only {expected.__name__} values",
        )
    return supplied


def _reject_duplicate_identities(values: tuple, attribute: str, label: str) -> None:
    seen: dict[object, object] = {}
    for value in values:
        identity = getattr(value, attribute)
        previous = seen.get(identity)
        if previous is not None:
            code = (
                LocalisationErrorCode.DUPLICATE_IDENTITY
                if previous == value
                else LocalisationErrorCode.IDENTITY_CONFLICT
            )
            _raise(code, f"duplicate {label} identity {identity.value}")
        seen[identity] = value


def _require_type(value: object, expected: type, label: str) -> None:
    if type(value) is not expected:
        _raise(LocalisationErrorCode.INVALID_CONTEXT, f"{label} must be {expected.__name__}")


def _require_identifier_text(value: object, label: str) -> None:
    if (
        type(value) is not str
        or not 1 <= len(value) <= MAX_IDENTITY_LENGTH
        or _IDENTIFIER.fullmatch(value) is None
    ):
        _raise(LocalisationErrorCode.INVALID_RANKING, f"{label} is invalid")


def _require_text(
    value: object, label: str, maximum_bytes: int, code: LocalisationErrorCode
) -> None:
    if type(value) is not str or not value or value != value.strip():
        _raise(code, f"{label} must be nonempty text without outer whitespace")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeEncodeError:
        _raise(code, f"{label} must be valid UTF-8 text")
    if size > maximum_bytes:
        _raise(code, f"{label} exceeds {maximum_bytes} UTF-8 bytes")


def _require_context_content(value: object) -> None:
    if type(value) is not str or not value:
        _raise(LocalisationErrorCode.INVALID_CONTEXT, "context content must be nonempty text")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeEncodeError:
        _raise(LocalisationErrorCode.INVALID_CONTEXT, "context content must be valid UTF-8 text")
    if size > MAX_CONTEXT_BYTES:
        _raise(
            LocalisationErrorCode.INVALID_CONTEXT,
            f"context content exceeds {MAX_CONTEXT_BYTES} UTF-8 bytes",
        )


def _require_sha256(value: object, label: str) -> None:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        _raise(LocalisationErrorCode.INVALID_PROVENANCE, f"{label} must be lowercase SHA-256")


def _bounded_integer(
    value: object,
    label: str,
    *,
    minimum: int,
    maximum: int,
    code: LocalisationErrorCode,
) -> None:
    if type(value) is not int or not minimum <= value <= maximum:
        _raise(code, f"{label} must be an integer in [{minimum}, {maximum}]")


def _domain_value(value: object) -> object:
    if isinstance(value, _Identity):
        return value.value
    if isinstance(value, StrEnum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _domain_value(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, tuple):
        return [_domain_value(item) for item in value]
    return value


def _raise(code: LocalisationErrorCode, detail: str) -> NoReturn:
    raise LocalisationContractError(code, detail)
