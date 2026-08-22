"""Deterministic lexical and structural repository candidate generation (RAG-003).

Consumes the RAG-002 ``RepositoryIndex`` and produces CONTRACT-RAG-001
``CandidateFile`` values with exact ``RankingExplanation`` evidence.

Everything here is standard library only: no network, no subprocess, no Git,
no embeddings, no model call. Scoring is integer/fixed point so a given
(index, input) pair always produces byte-identical candidates.
"""

from __future__ import annotations

import hashlib
import os
import re
import stat
from collections import Counter
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Final, NoReturn

from app.retrieval.indexing import (
    MAX_DISCOVERY_ENTRIES,
    MAX_INDEX_FILE_BYTES,
    ContentKind,
    FileLanguage,
    FileRole,
    IndexedFile,
    RepositoryIndex,
)
from app.retrieval.localisation import (
    MAX_CANDIDATES,
    MAX_QUERY_BYTES,
    CandidateFile,
    CandidateIdentity,
    FileIdentity,
    RankingExplanation,
    RankingSignal,
    ordered_candidates,
)
from app.workflow.repository_workspace import PreparedRepositoryWorkspace


# --------------------------------------------------------------------------
# RAG-003 implementation policy. These are NOT CONTRACT-RAG-001 values.
# --------------------------------------------------------------------------

SIGNAL_LEXICAL: Final = "LEXICAL"
SIGNAL_PATH_MATCH: Final = "PATH_MATCH"
SIGNAL_JAVA_SYMBOL: Final = "JAVA_SYMBOL"
SIGNAL_STACK_TRACE: Final = "STACK_TRACE"
SIGNAL_DIFF_ADJACENCY: Final = "DIFF_ADJACENCY"
SIGNAL_TEST_PROXIMITY: Final = "TEST_PROXIMITY"
SIGNAL_BUILD_METADATA: Final = "BUILD_METADATA"

RAG003_IMPLEMENTATION_SCORING_POLICY: Final = {
    SIGNAL_LEXICAL: 500_000,
    SIGNAL_PATH_MATCH: 100_000,
    SIGNAL_JAVA_SYMBOL: 150_000,
    SIGNAL_STACK_TRACE: 200_000,
    SIGNAL_DIFF_ADJACENCY: 120_000,
    SIGNAL_TEST_PROXIMITY: 80_000,
    SIGNAL_BUILD_METADATA: 60_000,
}
RAG003_MAX_TOTAL_SCORE: Final = sum(RAG003_IMPLEMENTATION_SCORING_POLICY.values())

# Input bounds. Combined textual evidence is additionally bounded by
# MAX_QUERY_BYTES, which is the CONTRACT-RAG-001 query bound.
MAX_CHANGED_FILES: Final = 1_000
MAX_BUILD_HINTS: Final = 64
MAX_BUILD_HINT_BYTES: Final = 256

# Bounded source access. A subset of the RAG-002 per-file limit.
MAX_ANALYZED_FILE_BYTES: Final = 1 * 1024 * 1024
# Explicit repository-analysis file bound. RAG-002 discovery admits at most
# MAX_DISCOVERY_ENTRIES entries per repository, so every genuinely produced
# RAG-002 index fits inside this bound; a larger supplied index fails closed
# instead of being silently truncated to a prefix of its canonical order.
MAX_ANALYZED_FILES: Final = MAX_DISCOVERY_ENTRIES
MAX_TOKENS_PER_FILE: Final = 20_000
MAX_TERM_FREQUENCY: Final = 255
MAX_STACK_TRACE_FRAMES: Final = 128
MAX_JAVA_SYMBOLS: Final = 512
MAX_DETAIL_ITEMS: Final = 8

# BM25-style fixed point. k1 = 1.2, b = 0.75, all scaled by 1000.
_BM25_K1_1000: Final = 1_200
_BM25_B_1000: Final = 750
_LEXICAL_SCALE: Final = 5

_PATH_FILENAME_WEIGHT: Final = 60_000
_PATH_STEM_WEIGHT: Final = 40_000
_PATH_COMPONENT_WEIGHT: Final = 6_000

_JAVA_TYPE_WEIGHT: Final = 60_000
_JAVA_FILENAME_TYPE_WEIGHT: Final = 20_000
_JAVA_METHOD_WEIGHT: Final = 25_000
_JAVA_PACKAGE_WEIGHT: Final = 15_000

_STACK_QUALIFIED_WEIGHT: Final = 120_000
_STACK_FILENAME_WEIGHT: Final = 60_000
_STACK_METHOD_WEIGHT: Final = 20_000
_STACK_FRAME_DEPTH_WEIGHT: Final = 40_000

_DIFF_SAME_FILE_WEIGHT: Final = 80_000
_DIFF_SAME_DIRECTORY_WEIGHT: Final = 30_000
_DIFF_COUNTERPART_WEIGHT: Final = 25_000
_DIFF_SAME_STEM_WEIGHT: Final = 20_000

_TEST_STEM_WEIGHT: Final = 40_000
_TEST_COUNTERPART_WEIGHT: Final = 30_000
_TEST_DIRECTORY_WEIGHT: Final = 25_000
_TEST_SYMBOL_WEIGHT: Final = 20_000

_BUILD_HINT_WEIGHT: Final = 40_000
_BUILD_QUERY_TOKEN_WEIGHT: Final = 20_000

BUILD_METADATA_FILENAMES: Final = frozenset(
    {
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "settings.gradle",
        "settings.gradle.kts",
    }
)
_BUILD_QUERY_TOKENS: Final = frozenset(
    {
        "build",
        "gradle",
        "maven",
        "pom",
        "dependency",
        "dependencies",
        "settings",
        "plugin",
        "plugins",
        "classpath",
        "artifact",
    }
)
_TEST_AFFIXES: Final = ("test", "tests", "spec", "it")


class CandidateErrorCode:
    INVALID_QUERY = "INVALID_QUERY"
    INVALID_LIMIT = "INVALID_LIMIT"
    INVALID_CHANGED_FILES = "INVALID_CHANGED_FILES"
    INVALID_BUILD_HINTS = "INVALID_BUILD_HINTS"
    UNKNOWN_CHANGED_FILE = "UNKNOWN_CHANGED_FILE"
    WORKSPACE_INDEX_MISMATCH = "WORKSPACE_INDEX_MISMATCH"
    INDEX_FILE_LIMIT_EXCEEDED = "INDEX_FILE_LIMIT_EXCEEDED"
    INVALID_ROOT = "INVALID_ROOT"
    SOURCE_CHANGED = "SOURCE_CHANGED"
    FILESYSTEM_FAILURE = "FILESYSTEM_FAILURE"


class CandidateGenerationError(ValueError):
    """Fail-closed error that never leaks host paths."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> NoReturn:
    raise CandidateGenerationError(code, detail)


# --------------------------------------------------------------------------
# Input model
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CandidateGenerationInput:
    """Narrow RAG-owned retrieval input. Not an HTTP/Workflow request model."""

    query: str
    stack_trace: str = ""
    changed_files: tuple[FileIdentity, ...] = ()
    build_hints: tuple[str, ...] = ()
    candidate_limit: int = 10

    def __post_init__(self) -> None:
        for label, value in (("query", self.query), ("stack_trace", self.stack_trace)):
            if type(value) is not str:
                _fail(CandidateErrorCode.INVALID_QUERY, f"{label} must be text")
        if type(self.candidate_limit) is not int or type(self.candidate_limit) is bool:
            _fail(CandidateErrorCode.INVALID_LIMIT, "candidate_limit must be an integer")
        if not 1 <= self.candidate_limit <= MAX_CANDIDATES:
            _fail(
                CandidateErrorCode.INVALID_LIMIT,
                f"candidate_limit must be in [1, {MAX_CANDIDATES}]",
            )

        hints = _ordered_tuple(self.build_hints, CandidateErrorCode.INVALID_BUILD_HINTS, "build_hints")
        if len(hints) > MAX_BUILD_HINTS:
            _fail(CandidateErrorCode.INVALID_BUILD_HINTS, f"at most {MAX_BUILD_HINTS} build hints")
        for hint in hints:
            if type(hint) is not str or not hint or hint != hint.strip():
                _fail(
                    CandidateErrorCode.INVALID_BUILD_HINTS,
                    "each build hint must be nonempty text without outer whitespace",
                )
            if len(hint.encode("utf-8")) > MAX_BUILD_HINT_BYTES:
                _fail(CandidateErrorCode.INVALID_BUILD_HINTS, "build hint exceeds byte limit")
        object.__setattr__(self, "build_hints", tuple(hints))

        changed = _ordered_tuple(
            self.changed_files, CandidateErrorCode.INVALID_CHANGED_FILES, "changed_files"
        )
        if len(changed) > MAX_CHANGED_FILES:
            _fail(
                CandidateErrorCode.INVALID_CHANGED_FILES,
                f"at most {MAX_CHANGED_FILES} changed files",
            )
        if not all(type(value) is FileIdentity for value in changed):
            _fail(
                CandidateErrorCode.INVALID_CHANGED_FILES,
                "changed_files must contain only FileIdentity values",
            )
        if len(set(changed)) != len(changed):
            _fail(CandidateErrorCode.INVALID_CHANGED_FILES, "duplicate changed file identity")
        object.__setattr__(self, "changed_files", tuple(changed))

        combined = len(self.query.encode("utf-8")) + len(self.stack_trace.encode("utf-8"))
        combined += sum(len(hint.encode("utf-8")) for hint in hints)
        if combined > MAX_QUERY_BYTES:
            _fail(
                CandidateErrorCode.INVALID_QUERY,
                f"combined textual evidence exceeds {MAX_QUERY_BYTES} UTF-8 bytes",
            )


def _ordered_tuple(values: object, code: str, label: str) -> tuple:
    if isinstance(values, (str, bytes, bytearray, set, frozenset, dict)):
        _fail(code, f"{label} must be an ordered iterable")
    try:
        return tuple(values)  # type: ignore[call-overload]
    except TypeError:
        _fail(code, f"{label} must be iterable")


# --------------------------------------------------------------------------
# Deterministic tokenization
# --------------------------------------------------------------------------

_WORD = re.compile(r"[A-Za-z0-9_]+")
_CAMEL = re.compile(r"[A-Z]+(?![a-z])|[A-Z][a-z0-9]*|[a-z][a-z0-9]*|[0-9]+")


def tokenize(text: str, *, limit: int = MAX_TOKENS_PER_FILE) -> list[str]:
    """Case-normalized, identifier and path friendly deterministic tokens."""

    tokens: list[str] = []
    for word in _WORD.findall(text):
        if len(tokens) >= limit:
            break
        tokens.append(word.lower())
        parts = [part for segment in word.split("_") if segment for part in _CAMEL.findall(segment)]
        if len(parts) > 1:
            tokens.extend(part.lower() for part in parts[: limit - len(tokens)])
    return tokens[:limit]


def _path_tokens(path: str) -> list[str]:
    return tokenize(path.replace("/", " ").replace(".", " "))


def _stem(filename: str) -> str:
    return filename.split(".", 1)[0] if "." in filename else filename


def _split_path(path: str) -> tuple[str, str, str]:
    """Return (directory, filename, stem) for a canonical POSIX file identity."""

    directory, _, filename = path.rpartition("/")
    return directory, filename, _stem(filename)


# --------------------------------------------------------------------------
# Integer fixed-point natural log (units of 1/1000). No float arithmetic.
# --------------------------------------------------------------------------

_LN2_Q32: Final = 2_977_044_472  # round(ln(2) * 2**32)
_Q32: Final = 1 << 32


def _ln_milli(numerator: int, denominator: int) -> int:
    """ln(numerator/denominator) in units of 1/1000, integer arithmetic only."""

    shift = numerator.bit_length() - denominator.bit_length()
    if shift > 0:
        denominator <<= shift
    elif shift < 0:
        numerator <<= -shift
    z = ((numerator - denominator) * _Q32) // (numerator + denominator)
    total = term = z
    z_squared = (z * z) // _Q32
    divisor = 3
    while divisor <= 21:
        term = (term * z_squared) // _Q32
        total += term // divisor
        divisor += 2
    return ((shift * _LN2_Q32) + 2 * total) * 1_000 // _Q32


# --------------------------------------------------------------------------
# Bounded, verified, read-only source access
# --------------------------------------------------------------------------


def _open_root(workspace: PreparedRepositoryWorkspace) -> int:
    root = os.fspath(workspace.workspace_root)
    try:
        metadata = os.lstat(root)
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            _fail(CandidateErrorCode.INVALID_ROOT, "workspace root must be a regular directory")
        return os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except CandidateGenerationError:
        raise
    except (OSError, TypeError, ValueError):
        _fail(CandidateErrorCode.INVALID_ROOT, "workspace root is not structurally usable")


def _read_indexed_text(root_fd: int, indexed: IndexedFile) -> str | None:
    """Read one already-indexed text file, verified against its manifest digest.

    Returns None when the file is deliberately not analyzed (binary, or beyond
    the RAG-003 analysis byte bound). Any integrity or path-safety doubt fails
    closed rather than degrading to a best-effort read.
    """

    if indexed.content_kind is not ContentKind.TEXT:
        return None
    if indexed.byte_size > min(MAX_ANALYZED_FILE_BYTES, MAX_INDEX_FILE_BYTES):
        return None

    parts = indexed.manifest_file.file_identity.value.split("/")
    open_fds: list[int] = []
    directory_fd = root_fd
    try:
        for component in parts[:-1]:
            directory_fd = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=directory_fd,
            )
            open_fds.append(directory_fd)
        file_fd = os.open(
            parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory_fd
        )
        with os.fdopen(file_fd, "rb") as source:
            metadata = os.fstat(source.fileno())
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != indexed.byte_size:
                _fail(CandidateErrorCode.SOURCE_CHANGED, "indexed file changed since indexing")
            data = source.read(indexed.byte_size + 1)
    except CandidateGenerationError:
        raise
    except OSError:
        _fail(CandidateErrorCode.FILESYSTEM_FAILURE, "indexed file cannot be read safely")
    finally:
        for opened in open_fds:
            os.close(opened)

    if (
        len(data) != indexed.byte_size
        or hashlib.sha256(data).hexdigest() != indexed.manifest_file.content_sha256
    ):
        _fail(CandidateErrorCode.SOURCE_CHANGED, "indexed file changed since indexing")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        _fail(CandidateErrorCode.SOURCE_CHANGED, "indexed text file is no longer valid UTF-8")


# --------------------------------------------------------------------------
# Conservative Java symbol extraction (regex only; never a Java parser)
# --------------------------------------------------------------------------

_JAVA_PACKAGE = re.compile(r"^\s*package\s+([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\s*;", re.M)
_JAVA_TYPE = re.compile(r"\b(?:class|interface|enum|record)\s+([A-Za-z_$][\w$]*)")
# Line-anchored declaration shape: a return type followed by a name and "(".
# Statement keywords are excluded so call sites are never mistaken for
# declarations. This is a conservative heuristic, not a Java parser.
_JAVA_METHOD = re.compile(
    r"^[ \t]*"
    r"(?!(?:return|throw|new|if|for|while|switch|catch|else|do|assert|import|package)\b)"
    r"(?:(?:public|protected|private|static|final|synchronized|abstract|native|default|strictfp)\s+)*"
    r"(?:<[^>\n]{0,120}>\s*)?"
    r"[A-Za-z_$][\w$.<>\[\],?\s]*?\s+([A-Za-z_$][\w$]*)\s*\(",
    re.M,
)


@dataclass(frozen=True, slots=True)
class JavaSymbols:
    """Bounded, conservative Java evidence. UNKNOWN beats fabricated certainty."""

    package: str
    types: frozenset[str]
    methods: frozenset[str]

    @property
    def package_segments(self) -> tuple[str, ...]:
        return tuple(self.package.split(".")) if self.package else ()


_NO_SYMBOLS: Final = JavaSymbols("", frozenset(), frozenset())


def extract_java_symbols(source: str) -> JavaSymbols:
    package = _JAVA_PACKAGE.search(source)
    types = {name for name in _JAVA_TYPE.findall(source)[:MAX_JAVA_SYMBOLS]}
    methods = {
        name
        for name in _JAVA_METHOD.findall(source)[:MAX_JAVA_SYMBOLS]
        if name not in {"if", "for", "while", "switch", "catch", "return", "new"}
    } - types
    return JavaSymbols(package.group(1) if package else "", frozenset(types), frozenset(methods))


# --------------------------------------------------------------------------
# Conservative Java stack-trace parsing. Content is never executed and paths
# inside a trace are never opened; frames only address indexed files.
# --------------------------------------------------------------------------

_FRAME = re.compile(
    r"\bat\s+([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\.([A-Za-z_$<][\w$>]*)"
    r"\(([^()\n]*?)(?::(\d{1,7}))?\)"
)


@dataclass(frozen=True, slots=True)
class StackFrame:
    declaring_class: str
    method: str
    source_file: str
    line: int | None

    @property
    def simple_class(self) -> str:
        return self.declaring_class.rsplit(".", 1)[-1].split("$", 1)[0]

    @property
    def package_path(self) -> str:
        package = self.declaring_class.rsplit(".", 1)[0] if "." in self.declaring_class else ""
        return package.replace(".", "/")


def parse_stack_trace(text: str) -> tuple[StackFrame, ...]:
    frames: list[StackFrame] = []
    for match in _FRAME.finditer(text):
        if len(frames) >= MAX_STACK_TRACE_FRAMES:
            break
        declaring, method, location, line = match.groups()
        source_file = location.strip()
        if source_file in {"Native Method", "Unknown Source"} or "/" in source_file:
            source_file = ""
        frames.append(StackFrame(declaring, method, source_file, int(line) if line else None))
    return tuple(frames)


# --------------------------------------------------------------------------
# Candidate identity
# --------------------------------------------------------------------------

_IDENTITY_DOMAIN: Final = b"testgap.rag-003.candidate-identity.v1"


def candidate_identity(
    repository_id_value: str, revision_id_value: str, file_identity_value: str
) -> CandidateIdentity:
    """Deterministic, length-safe candidate identity. No uuid/time/pid/random."""

    digest = hashlib.sha256()
    for part in (
        _IDENTITY_DOMAIN,
        repository_id_value.encode("utf-8"),
        revision_id_value.encode("utf-8"),
        file_identity_value.encode("utf-8"),
    ):
        digest.update(len(part).to_bytes(8, "big"))
        digest.update(part)
        digest.update(b"\x1f")
    return CandidateIdentity(f"candidate:{digest.hexdigest()}")


# --------------------------------------------------------------------------
# Corpus
# --------------------------------------------------------------------------


@dataclass(slots=True)
class _Document:
    indexed: IndexedFile
    directory: str
    filename: str
    stem: str
    path_tokens: frozenset[str]
    terms: dict[str, int] = field(default_factory=dict)
    length: int = 0
    java: JavaSymbols = _NO_SYMBOLS
    content_tokens: frozenset[str] = frozenset()

    @property
    def path(self) -> str:
        return self.indexed.manifest_file.file_identity.value


def _build_corpus(
    workspace: PreparedRepositoryWorkspace, index: RepositoryIndex
) -> list[_Document]:
    documents: list[_Document] = []
    root_fd = _open_root(workspace)
    try:
        # The complete accepted index is analyzed. There is deliberately no
        # internal slice: a file must never become unreachable merely because
        # its canonical ordering places it after an arbitrary boundary.
        for indexed in index.files:
            path = indexed.manifest_file.file_identity.value
            directory, filename, stem = _split_path(path)
            document = _Document(
                indexed, directory, filename, stem, frozenset(_path_tokens(path))
            )
            tokens = list(document.path_tokens)
            source = _read_indexed_text(root_fd, indexed)
            if source is not None:
                content = tokenize(source)
                document.content_tokens = frozenset(content)
                tokens.extend(content)
                if indexed.language is FileLanguage.JAVA:
                    document.java = extract_java_symbols(source)
            counts = Counter(tokens)
            document.terms = {
                term: min(count, MAX_TERM_FREQUENCY) for term, count in counts.items()
            }
            document.length = sum(document.terms.values())
            documents.append(document)
    finally:
        os.close(root_fd)
    return documents


# --------------------------------------------------------------------------
# Signals
# --------------------------------------------------------------------------


def _clamp(value: int, signal: str) -> int:
    return max(0, min(value, RAG003_IMPLEMENTATION_SCORING_POLICY[signal]))


def _detail(pairs: list[str]) -> str:
    return " ".join(pairs[:MAX_DETAIL_ITEMS])[:4_096].strip()


def _lexical(
    document: _Document,
    query_terms: tuple[str, ...],
    document_frequency: dict[str, int],
    total_documents: int,
    average_length: int,
) -> tuple[int, str]:
    raw = 0
    evidence: list[tuple[str, int]] = []
    for term in query_terms:
        frequency = document.terms.get(term, 0)
        if frequency == 0:
            continue
        # Non-negative BM25 idf variant: ln((2N + 2) / (2df + 1)).
        idf = max(0, _ln_milli(2 * total_documents + 2, 2 * document_frequency[term] + 1))
        norm = 1_000 - _BM25_B_1000 + _BM25_B_1000 * document.length // average_length
        saturation = _BM25_K1_1000 * norm // 1_000
        component = frequency * (_BM25_K1_1000 + 1_000) * 1_000 // (
            frequency * 1_000 + saturation
        )
        contribution = idf * component // 1_000
        raw += contribution
        evidence.append((term, frequency))
    if raw <= 0:
        return 0, ""
    evidence.sort(key=lambda item: (-item[1], item[0]))
    detail = _detail(
        [f"terms={len(evidence)}", f"dl={document.length}"]
        + [f"{term}:{count}" for term, count in evidence[:6]]
    )
    return _clamp(raw * _LEXICAL_SCALE, SIGNAL_LEXICAL), detail


def _path_match(document: _Document, evidence_tokens: frozenset[str]) -> tuple[int, str]:
    score = 0
    reasons: list[str] = []
    if document.filename.lower() in evidence_tokens:
        score += _PATH_FILENAME_WEIGHT
        reasons.append(f"filename={document.filename}")
    if document.stem.lower() in evidence_tokens:
        score += _PATH_STEM_WEIGHT
        reasons.append(f"stem={document.stem}")
    components = sorted(
        {
            token
            for component in document.directory.split("/")
            if component
            for token in _path_tokens(component)
        }
        & evidence_tokens
    )
    if components:
        score += _PATH_COMPONENT_WEIGHT * len(components)
        reasons.append("path=" + ",".join(components[:4]))
    if score <= 0:
        return 0, ""
    return _clamp(score, SIGNAL_PATH_MATCH), _detail(reasons)


def _java_symbol(document: _Document, evidence_tokens: frozenset[str]) -> tuple[int, str]:
    if document.indexed.language is not FileLanguage.JAVA:
        return 0, ""
    symbols = document.java
    score = 0
    reasons: list[str] = []
    types = sorted(name for name in symbols.types if name.lower() in evidence_tokens)
    if types:
        score += _JAVA_TYPE_WEIGHT
        reasons.append("type=" + ",".join(types[:3]))
        if document.stem in symbols.types and document.stem.lower() in evidence_tokens:
            score += _JAVA_FILENAME_TYPE_WEIGHT
            reasons.append("filename_matches_type")
    methods = sorted(name for name in symbols.methods if name.lower() in evidence_tokens)
    if methods:
        score += _JAVA_METHOD_WEIGHT * min(len(methods), 2)
        reasons.append("method=" + ",".join(methods[:3]))
    packages = sorted(set(symbols.package_segments) & evidence_tokens)
    if packages:
        score += _JAVA_PACKAGE_WEIGHT
        reasons.append("package=" + ".".join(packages[:4]))
    if score <= 0:
        return 0, ""
    return _clamp(score, SIGNAL_JAVA_SYMBOL), _detail(reasons)


def _stack_trace(document: _Document, frames: tuple[StackFrame, ...]) -> tuple[int, str]:
    score = 0
    reasons: list[str] = []
    path = document.path
    for depth, frame in enumerate(frames):
        matched = False
        if frame.source_file:
            suffix = (
                f"{frame.package_path}/{frame.source_file}"
                if frame.package_path
                else frame.source_file
            )
            if path == suffix or path.endswith("/" + suffix):
                score += _STACK_QUALIFIED_WEIGHT
                reasons.append(f"frame{depth}={frame.declaring_class}")
                matched = True
            elif document.filename == frame.source_file:
                score += _STACK_FILENAME_WEIGHT
                reasons.append(f"file{depth}={frame.source_file}")
                matched = True
        elif document.stem == frame.simple_class:
            score += _STACK_FILENAME_WEIGHT
            reasons.append(f"class{depth}={frame.simple_class}")
            matched = True
        if not matched:
            continue
        score += _STACK_FRAME_DEPTH_WEIGHT // (depth + 1)
        if frame.method in document.java.methods:
            score += _STACK_METHOD_WEIGHT
            reasons.append(f"method={frame.method}")
        break
    if score <= 0:
        return 0, ""
    return _clamp(score, SIGNAL_STACK_TRACE), _detail(reasons)


def _counterpart_directories(directory: str) -> frozenset[str]:
    """Conventional source/test directory counterparts, both directions."""

    swaps = (("src/main/", "src/test/"), ("/main/", "/test/"), ("src/", "test/"))
    results = {directory}
    for left, right in swaps:
        if left in directory:
            results.add(directory.replace(left, right, 1))
        if right in directory:
            results.add(directory.replace(right, left, 1))
    return frozenset(results)


def _test_bases(stem: str) -> frozenset[str]:
    """Plausible source stems for a test file stem, lowercased."""

    lowered = stem.lower()
    bases = {lowered}
    for affix in _TEST_AFFIXES:
        for prefix in (affix, affix + "_"):
            if lowered.startswith(prefix) and len(lowered) > len(prefix):
                bases.add(lowered[len(prefix) :])
        for suffix in (affix, "_" + affix):
            if lowered.endswith(suffix) and len(lowered) > len(suffix):
                bases.add(lowered[: -len(suffix)])
    return frozenset(base.strip("_") for base in bases if base.strip("_"))


def _diff_adjacency(
    document: _Document, changed: tuple[tuple[str, str, str], ...]
) -> tuple[int, str]:
    score = 0
    reasons: list[str] = []
    for directory, filename, stem in changed:
        if document.path == (f"{directory}/{filename}" if directory else filename):
            score += _DIFF_SAME_FILE_WEIGHT
            reasons.append("same_file")
            continue
        if document.directory == directory:
            score += _DIFF_SAME_DIRECTORY_WEIGHT
            reasons.append(f"same_dir={directory or '.'}")
        elif document.directory in _counterpart_directories(directory):
            score += _DIFF_COUNTERPART_WEIGHT
            reasons.append("counterpart_dir")
        if document.stem != stem and _test_bases(document.stem) & _test_bases(stem):
            score += _DIFF_SAME_STEM_WEIGHT
            reasons.append(f"stem~{stem}")
        elif document.stem == stem:
            score += _DIFF_SAME_STEM_WEIGHT
            reasons.append(f"stem={stem}")
    if score <= 0:
        return 0, ""
    return _clamp(score, SIGNAL_DIFF_ADJACENCY), _detail(sorted(set(reasons)))


def _test_proximity(
    document: _Document,
    evidence_stems: frozenset[str],
    evidence_symbols: frozenset[str],
    changed: tuple[tuple[str, str, str], ...],
) -> tuple[int, str]:
    if document.indexed.role is not FileRole.TEST:
        return 0, ""
    score = 0
    reasons: list[str] = []
    bases = _test_bases(document.stem)
    related = sorted(bases & evidence_stems)
    if related:
        score += _TEST_STEM_WEIGHT
        reasons.append("relates=" + ",".join(related[:3]))
    for directory, _filename, stem in changed:
        if document.directory == directory:
            score += _TEST_DIRECTORY_WEIGHT
            reasons.append("same_dir")
            break
        if document.directory in _counterpart_directories(directory) and bases & _test_bases(stem):
            score += _TEST_COUNTERPART_WEIGHT
            reasons.append("counterpart")
            break
    shared = sorted({name.lower() for name in document.java.types} & evidence_symbols)
    if shared:
        score += _TEST_SYMBOL_WEIGHT
        reasons.append("symbol=" + ",".join(shared[:3]))
    if score <= 0:
        return 0, ""
    return _clamp(score, SIGNAL_TEST_PROXIMITY), _detail(reasons)


def _build_metadata(
    document: _Document, hint_tokens: frozenset[str], query_tokens: frozenset[str]
) -> tuple[int, str]:
    if document.filename not in BUILD_METADATA_FILENAMES:
        return 0, ""
    score = 0
    reasons: list[str] = []
    if document.filename in hint_tokens or document.stem.lower() in hint_tokens:
        score += _BUILD_HINT_WEIGHT
        reasons.append(f"hint={document.filename}")
    matched = sorted((query_tokens | hint_tokens) & _BUILD_QUERY_TOKENS)
    if matched:
        score += _BUILD_QUERY_TOKEN_WEIGHT
        reasons.append("tokens=" + ",".join(matched[:4]))
    if score <= 0:
        return 0, ""
    return _clamp(score, SIGNAL_BUILD_METADATA), _detail(reasons)


# --------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------


def _require_bound_workspace_index(
    workspace: PreparedRepositoryWorkspace, index: RepositoryIndex
) -> None:
    """Fail closed unless workspace and index describe exactly one revision.

    Identity comes only from the supplied contract values; HEAD, branch names,
    paths and Git output are never consulted. Without this binding a mismatched
    pair could read one source tree and emit candidates labelled as another.
    """

    if (
        workspace.repository_identity != index.manifest.repository_id
        or workspace.revision_identity != index.manifest.revision_id
    ):
        _fail(
            CandidateErrorCode.WORKSPACE_INDEX_MISMATCH,
            "workspace and index do not describe the same repository revision",
        )


def generate_candidates(
    workspace: PreparedRepositoryWorkspace,
    index: RepositoryIndex,
    request: CandidateGenerationInput,
) -> tuple[CandidateFile, ...]:
    """Produce deterministically ranked candidates for one indexed revision.

    Only files present in ``index`` may become candidates, and only files with
    strictly positive evidence are emitted at all.
    """

    if type(request) is not CandidateGenerationInput:
        _fail(CandidateErrorCode.INVALID_QUERY, "request must be a CandidateGenerationInput")

    # Bind identity and enforce the analysis bound before any source access.
    _require_bound_workspace_index(workspace, index)
    if len(index.files) > MAX_ANALYZED_FILES:
        _fail(
            CandidateErrorCode.INDEX_FILE_LIMIT_EXCEEDED,
            f"repository index exceeds the explicit analysis bound of {MAX_ANALYZED_FILES} files",
        )

    indexed_paths = {item.manifest_file.file_identity.value for item in index.files}
    unknown = sorted(
        value.value for value in request.changed_files if value.value not in indexed_paths
    )
    if unknown:
        _fail(
            CandidateErrorCode.UNKNOWN_CHANGED_FILE,
            f"changed file is not present in the supplied repository index: {unknown[0]}",
        )

    documents = _build_corpus(workspace, index)
    if not documents:
        return ()

    document_frequency: Counter[str] = Counter()
    for document in documents:
        document_frequency.update(document.terms.keys())
    total_documents = len(documents)
    average_length = max(1, sum(document.length for document in documents) // total_documents)

    query_tokens = tokenize(request.query)
    hint_tokens = frozenset(token for hint in request.build_hints for token in tokenize(hint))
    hint_tokens |= {hint.lower() for hint in request.build_hints}
    query_terms = tuple(dict.fromkeys(query_tokens))
    evidence_tokens = frozenset(query_tokens) | hint_tokens
    frames = parse_stack_trace(request.stack_trace)

    changed = tuple(
        _split_path(value.value) for value in request.changed_files
    )
    evidence_stems = frozenset(
        {stem.lower() for _directory, _filename, stem in changed}
        | {frame.simple_class.lower() for frame in frames}
        | set(query_tokens)
    )
    evidence_symbols = frozenset(
        {frame.simple_class.lower() for frame in frames} | set(query_tokens)
    )

    candidates: list[CandidateFile] = []
    scored: list[tuple[int, str, tuple[RankingSignal, ...]]] = []
    for document in documents:
        emitted: list[RankingSignal] = []
        for name, (contribution, detail) in (
            (
                SIGNAL_LEXICAL,
                _lexical(
                    document, query_terms, document_frequency, total_documents, average_length
                ),
            ),
            (SIGNAL_PATH_MATCH, _path_match(document, evidence_tokens)),
            (SIGNAL_JAVA_SYMBOL, _java_symbol(document, evidence_tokens)),
            (SIGNAL_STACK_TRACE, _stack_trace(document, frames)),
            (SIGNAL_DIFF_ADJACENCY, _diff_adjacency(document, changed)),
            (
                SIGNAL_TEST_PROXIMITY,
                _test_proximity(document, evidence_stems, evidence_symbols, changed),
            ),
            (SIGNAL_BUILD_METADATA, _build_metadata(document, hint_tokens, evidence_tokens)),
        ):
            if contribution > 0:
                emitted.append(RankingSignal(name, contribution, detail or name))
        if not emitted:
            continue
        scored.append((sum(signal.contribution for signal in emitted), document.path, tuple(emitted)))

    scored.sort(key=lambda item: (-item[0], item[1]))
    for rank, (score, path, signals) in enumerate(scored[: request.candidate_limit], start=1):
        candidates.append(
            CandidateFile(
                candidate_id=candidate_identity(
                    index.manifest.repository_id.value, index.manifest.revision_id.value, path
                ),
                repository_id=index.manifest.repository_id,
                revision_id=index.manifest.revision_id,
                file_identity=FileIdentity(path),
                explanation=RankingExplanation(rank, score, signals),
            )
        )
    return ordered_candidates(candidates)


# --------------------------------------------------------------------------
# Evidence-only retrieval metrics
# --------------------------------------------------------------------------


def recall_at_k(predicted: tuple[str, ...], relevant: frozenset[str], k: int) -> Fraction:
    """Exact Recall@K as a stdlib ``Fraction``.

    Recall@K is the number of distinct relevant files retrieved within the
    first k predictions divided by the total number of relevant files. This is
    deliberately not the hit rate: with multiple relevant files, retrieving
    some but not all of them yields a fraction, not 1. Duplicated predictions
    never inflate recall because retrieval is measured over a set. An empty
    relevant set has no defined denominator and fails closed.
    """

    if type(k) is not int or k < 0:
        raise ValueError("k must be a non-negative integer")
    if not relevant:
        raise ValueError("relevant must contain at least one file")
    retrieved = {path for path in predicted[:k] if path in relevant}
    return Fraction(len(retrieved), len(relevant))


def reciprocal_rank(predicted: tuple[str, ...], relevant: frozenset[str]) -> tuple[int, int]:
    """Reciprocal rank as an exact (numerator, denominator) pair; (0, 1) if unfound."""

    for position, path in enumerate(predicted, start=1):
        if path in relevant:
            return 1, position
    return 0, 1
