"""Deterministic context assembly over ranked repository candidates (RAG-005).

Converts already-ranked RAG-003 ``CandidateFile`` evidence into CONTRACT-RAG-001
``ContextItem`` and ``ContextBundle`` values containing exact repository source
text under a caller-supplied context-token budget.

RAG-004 semantic retrieval is deliberately absent: no embeddings, no vector
store, no model or provider calls, no network, no subprocess, no Git execution.
Candidate selection consumes only the supplied deterministic RAG-003 ranking.
Existing objective structural signal detail (conservative Java type/method
evidence carried by ``RankingSignal.detail``) may refine where a bounded source
window is opened; it never invents candidates or scores, and detail text outside
a very small closed grammar is never trusted as a location command.

Candidates are accepted only when they carry genuine RAG-003 rank structure:
ranks exactly 1..N, scores descending, and score ties broken by ascending
canonical FileIdentity. Malformed ranking structure (duplicate ranks, gaps,
ranks not starting at 1, or order inconsistent with the deterministic RAG-003
ranking rule) fails closed and is never silently repaired. Packing reuses the
CONTRACT-RAG-001 limits MAX_CONTEXT_BYTES and MAX_CONTEXT_ITEMS: a ContextItem
is never constructed with content larger than MAX_CONTEXT_BYTES (an oversized
whole line skips its proposal instead of being split), and the emitted item
count never exceeds MAX_CONTEXT_ITEMS, so no oversized ContextBundle is ever
built and left for the RAG-001 constructor to reject.

Every source read is descriptor-relative, symlink-free (O_NOFOLLOW),
regular-file verified, byte-size and SHA-256 checked against the supplied
RAG-002 index, and additionally verified to still be the same inspected object
at open time (st_dev/st_ino/file-type comparison after every lstat/open pair,
closing stat/open replacement races for the workspace root, intermediate
directories and the source file). Assembly fails closed on any integrity doubt.
Error strings never contain host paths. Token counting is the conservative
accounting policy ``1 UTF-8 byte == 1 RAG context token``; it is budget
bookkeeping only and is deliberately not claimed to equal any provider
tokenizer or billing count.
"""

from __future__ import annotations

import hashlib
import os
import re
import stat
from dataclasses import dataclass
from typing import Final, NoReturn

from app.retrieval.candidates import (
    SIGNAL_JAVA_SYMBOL,
    SIGNAL_STACK_TRACE,
    candidate_identity,
)
from app.retrieval.indexing import ContentKind, IndexedFile, RepositoryIndex
from app.retrieval.localisation import (
    MAX_CONTEXT_BYTES,
    MAX_CONTEXT_ITEMS,
    MAX_TOKEN_BUDGET,
    CandidateFile,
    ContextBundle,
    ContextBundleIdentity,
    ContextItem,
    ContextItemIdentity,
    Provenance,
    TokenBudget,
    TrustLabel,
    ordered_candidates,
)
from app.workflow.repository_workspace import PreparedRepositoryWorkspace


# --------------------------------------------------------------------------
# RAG-005 implementation policy. These are NOT CONTRACT-RAG-001 values.
# --------------------------------------------------------------------------

MAX_CONTEXT_WINDOW_LINES: Final = 80
_SYMBOL_WINDOW_LINES_BEFORE: Final = 20
_MAX_LOCATION_SYMBOLS: Final = 16
_MAX_PROPOSALS_PER_CANDIDATE: Final = 16

_ITEM_IDENTITY_DOMAIN: Final = b"testgap.rag-005.context-item.v1"
_BUNDLE_IDENTITY_DOMAIN: Final = b"testgap.rag-005.context-bundle.v1"
_CONTEXT_ITEM_PREFIX: Final = "context-item:"
_CONTEXT_BUNDLE_PREFIX: Final = "context-bundle:"

_DIRECTORY_OPEN_FLAGS: Final = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_FILE_OPEN_FLAGS: Final = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC


class ContextErrorCode:
    """Stable fail-closed error taxonomy for RAG-005 context assembly."""

    INVALID_BUDGET = "INVALID_BUDGET"
    WORKSPACE_INDEX_MISMATCH = "WORKSPACE_INDEX_MISMATCH"
    CANDIDATE_INDEX_MISMATCH = "CANDIDATE_INDEX_MISMATCH"
    UNKNOWN_CANDIDATE_FILE = "UNKNOWN_CANDIDATE_FILE"
    INVALID_CANDIDATE = "INVALID_CANDIDATE"
    SOURCE_CHANGED = "SOURCE_CHANGED"
    FILESYSTEM_FAILURE = "FILESYSTEM_FAILURE"
    INVALID_CONTEXT_REQUEST = "INVALID_CONTEXT_REQUEST"


class ContextAssemblyError(ValueError):
    """Fail-closed error that never leaks host paths."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> NoReturn:
    raise ContextAssemblyError(code, detail)


@dataclass(frozen=True, slots=True)
class ContextAssemblyInput:
    """Narrow RAG-owned input. Not an HTTP/Workflow request model.

    The caller (Workflow) supplies the explicit ``context_token_budget``; this
    module enforces exactly that value and owns no part of any wider model
    prompt budget. Candidates must already be ranked RAG-003 output; the
    supplied sequence itself is validated against the canonical RAG-003
    ranking rule BEFORE any normalization or reordering, so out-of-order,
    duplicated, gapped or tie-inconsistent rankings fail closed instead of
    being silently repaired. Only after that validation is the sequence
    deterministically normalized for internal use.
    """

    workspace: PreparedRepositoryWorkspace
    index: RepositoryIndex
    candidates: tuple[CandidateFile, ...]
    context_token_budget: int

    def __post_init__(self) -> None:
        if type(self.workspace) is not PreparedRepositoryWorkspace:
            _fail(
                ContextErrorCode.INVALID_CONTEXT_REQUEST,
                "workspace must be a PreparedRepositoryWorkspace",
            )
        if type(self.index) is not RepositoryIndex:
            _fail(ContextErrorCode.INVALID_CONTEXT_REQUEST, "index must be a RepositoryIndex")
        budget = self.context_token_budget
        if type(budget) is not int or type(budget) is bool:
            _fail(ContextErrorCode.INVALID_BUDGET, "context_token_budget must be an integer")
        if not 1 <= budget <= MAX_TOKEN_BUDGET:
            _fail(
                ContextErrorCode.INVALID_BUDGET,
                f"context_token_budget must be in [1, {MAX_TOKEN_BUDGET}]",
            )
        if isinstance(self.candidates, (str, bytes, bytearray, set, frozenset, dict)):
            _fail(
                ContextErrorCode.INVALID_CONTEXT_REQUEST, "candidates must be an ordered iterable"
            )
        try:
            supplied = tuple(self.candidates)
        except TypeError:
            _fail(ContextErrorCode.INVALID_CONTEXT_REQUEST, "candidates must be iterable")
        if not all(isinstance(value, CandidateFile) for value in supplied):
            _fail(
                ContextErrorCode.INVALID_CONTEXT_REQUEST,
                "candidates must contain only CandidateFile values",
            )
        _require_rag003_rank_semantics(supplied)
        ordered = ordered_candidates(supplied)
        object.__setattr__(self, "candidates", ordered)


def _require_rag003_rank_semantics(candidates: tuple[CandidateFile, ...]) -> None:
    """Fail closed unless the supplied sequence carries genuine RAG-003 rank order.

    RAG-003 emits ranks exactly 1..N, orders scores descending, and breaks
    score ties by ascending canonical FileIdentity. The caller-supplied
    sequence itself must already satisfy this rule; it is validated verbatim
    BEFORE :func:`ordered_candidates` normalization, so a malformed supply is
    never silently sorted into validity. Duplicate ranks, rank gaps, ranks
    that do not begin at 1, or an order inconsistent with this deterministic
    rule are rejected.
    """

    previous: CandidateFile | None = None
    for position, candidate in enumerate(candidates, start=1):
        if candidate.explanation.rank != position:
            _fail(
                ContextErrorCode.INVALID_CANDIDATE,
                "candidate ranks must be exactly 1..N without duplicates or gaps",
            )
        if previous is not None:
            if candidate.explanation.score > previous.explanation.score:
                _fail(
                    ContextErrorCode.INVALID_CANDIDATE,
                    "candidate scores must descend as ranks ascend",
                )
            if (
                candidate.explanation.score == previous.explanation.score
                and candidate.file_identity.value <= previous.file_identity.value
            ):
                _fail(
                    ContextErrorCode.INVALID_CANDIDATE,
                    "equal candidate scores must break ties by ascending file identity",
                )
        previous = candidate


# --------------------------------------------------------------------------
# Canonical identities: length-prefixed, domain-separated SHA-256
# --------------------------------------------------------------------------


def _domain_digest(domain: bytes, parts: list[str]) -> str:
    digest = hashlib.sha256()
    digest.update(len(domain).to_bytes(8, "big"))
    digest.update(domain)
    for part in parts:
        encoded = part.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
    return digest.hexdigest()


def _context_item_identity(
    repository_value: str,
    revision_value: str,
    candidate_value: str,
    file_value: str,
    start_line: int,
    end_line: int,
    content_sha256: str,
    token_count: int,
) -> ContextItemIdentity:
    value = _CONTEXT_ITEM_PREFIX + _domain_digest(
        _ITEM_IDENTITY_DOMAIN,
        [
            repository_value,
            revision_value,
            candidate_value,
            file_value,
            str(start_line),
            str(end_line),
            content_sha256,
            TrustLabel.UNTRUSTED_REPOSITORY_TEXT.value,
            str(token_count),
        ],
    )
    return ContextItemIdentity(value)


def _context_bundle_identity(
    repository_value: str,
    revision_value: str,
    items: tuple[ContextItem, ...],
    max_tokens: int,
    consumed_tokens: int,
) -> ContextBundleIdentity:
    value = _CONTEXT_BUNDLE_PREFIX + _domain_digest(
        _BUNDLE_IDENTITY_DOMAIN,
        [repository_value, revision_value]
        + [item.context_item_id.value for item in items]
        + [str(max_tokens), str(consumed_tokens)],
    )
    return ContextBundleIdentity(value)


# --------------------------------------------------------------------------
# Bounded, verified, read-only source access
# --------------------------------------------------------------------------


def _verify_same_object(fd: int, expected: os.stat_result, detail: str) -> os.stat_result:
    """Confirm an opened descriptor is the object inspected just before opening.

    Closes stat/open replacement races: a path swapped between inspection and
    open fails closed even when the replacement holds identical bytes. Only
    host-independent identity is compared (device, inode, file type).
    """

    try:
        opened = os.fstat(fd)
    except OSError:
        _fail(ContextErrorCode.FILESYSTEM_FAILURE, "workspace object cannot be inspected")
    if (expected.st_dev, expected.st_ino, stat.S_IFMT(expected.st_mode)) != (
        opened.st_dev,
        opened.st_ino,
        stat.S_IFMT(opened.st_mode),
    ):
        _fail(ContextErrorCode.SOURCE_CHANGED, detail)
    return opened


def _open_root(workspace: PreparedRepositoryWorkspace) -> int:
    root = os.fspath(workspace.workspace_root)
    try:
        metadata = os.lstat(root)
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            _fail(
                ContextErrorCode.FILESYSTEM_FAILURE,
                "workspace root must be a regular directory",
            )
        root_fd = os.open(root, _DIRECTORY_OPEN_FLAGS)
    except ContextAssemblyError:
        raise
    except (OSError, TypeError, ValueError):
        _fail(ContextErrorCode.FILESYSTEM_FAILURE, "workspace root is not structurally usable")
    try:
        _verify_same_object(
            root_fd, metadata, "workspace root changed between inspection and open"
        )
    except BaseException:
        os.close(root_fd)
        raise
    return root_fd


def _read_verified_lines(root_fd: int, indexed: IndexedFile) -> tuple[str, ...] | None:
    """Read one already-indexed file, verified against its manifest digest.

    Returns the exact source lines (original endings preserved), or ``None``
    when the file is deliberately not turned into context (binary content).
    Every opened path component is proven to still be the inspected object;
    any integrity doubt fails closed instead of degrading to best effort.
    """

    parts = indexed.manifest_file.file_identity.value.split("/")
    open_fds: list[int] = []
    directory_fd = root_fd
    try:
        for component in parts[:-1]:
            expected = os.stat(component, dir_fd=directory_fd, follow_symlinks=False)
            directory_fd = os.open(component, _DIRECTORY_OPEN_FLAGS, dir_fd=directory_fd)
            open_fds.append(directory_fd)
            _verify_same_object(
                directory_fd,
                expected,
                "indexed directory changed between inspection and open",
            )
        expected_file = os.stat(parts[-1], dir_fd=directory_fd, follow_symlinks=False)
        file_fd = os.open(parts[-1], _FILE_OPEN_FLAGS, dir_fd=directory_fd)
        with os.fdopen(file_fd, "rb") as source:
            metadata = _verify_same_object(
                source.fileno(),
                expected_file,
                "indexed file changed between inspection and open",
            )
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != indexed.byte_size:
                _fail(ContextErrorCode.SOURCE_CHANGED, "indexed file changed since indexing")
            data = source.read(indexed.byte_size + 1)
    except ContextAssemblyError:
        raise
    except OSError:
        _fail(ContextErrorCode.FILESYSTEM_FAILURE, "indexed file cannot be read safely")
    finally:
        for opened in open_fds:
            os.close(opened)

    if (
        len(data) != indexed.byte_size
        or hashlib.sha256(data).hexdigest() != indexed.manifest_file.content_sha256
    ):
        _fail(ContextErrorCode.SOURCE_CHANGED, "indexed file changed since indexing")
    if indexed.content_kind is ContentKind.BINARY:
        return None
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        _fail(ContextErrorCode.SOURCE_CHANGED, "indexed text file is no longer valid UTF-8")
    if "\x00" in text:
        return None
    return _split_source_lines(text)


def _split_source_lines(text: str) -> tuple[str, ...]:
    """Split on newline terminators, preserving each original line ending.

    Line numbers follow the ``\\n``/``\\r\\n`` convention that compiler and stack
    trace line references use; a lone ``\\r`` is also treated as a terminator.
    The trailing fragment of a file without a final newline is kept verbatim.
    """

    lines: list[str] = []
    start = 0
    index = 0
    total = len(text)
    while index < total:
        character = text[index]
        if character == "\n":
            lines.append(text[start : index + 1])
            start = index + 1
            index += 1
        elif character == "\r":
            end = index + 2 if index + 1 < total and text[index + 1] == "\n" else index + 1
            lines.append(text[start:end])
            start = end
            index = end
        else:
            index += 1
    if start < total:
        lines.append(text[start:])
    return tuple(lines)


# --------------------------------------------------------------------------
# Conservative structural window targeting from the closed detail grammar
# --------------------------------------------------------------------------

_STRUCTURED_SIGNAL_NAMES: Final = frozenset({SIGNAL_JAVA_SYMBOL, SIGNAL_STACK_TRACE})
_STRUCTURE_DETAIL_PAIR = re.compile(r"(?:\A|\s)(type|method)=([^\s]+)")
_STRUCTURE_SYMBOL = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]{0,127}\Z")


def _structural_symbols(candidate: CandidateFile) -> tuple[tuple[str, str], ...]:
    """Extract (kind, symbol) pairs from the small closed detail grammar.

    Only ``type=<symbol>`` and ``method=<symbol>`` pairs inside JAVA_SYMBOL or
    STACK_TRACE signal details are recognized; every other key and every other
    signal is ignored. Values are comma separated simple identifiers.
    """

    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for signal in candidate.explanation.signals:
        if signal.signal not in _STRUCTURED_SIGNAL_NAMES:
            continue
        for match in _STRUCTURE_DETAIL_PAIR.finditer(signal.detail):
            kind = match.group(1)
            raw = match.group(2)
            for symbol in raw.split(","):
                pair = (kind, symbol)
                if symbol.isascii() and _STRUCTURE_SYMBOL.fullmatch(symbol) and pair not in seen:
                    seen.add(pair)
                    pairs.append(pair)
                    if len(pairs) >= _MAX_LOCATION_SYMBOLS:
                        return tuple(pairs)
    return tuple(pairs)


def _locate_symbol(lines: tuple[str, ...], kind: str, symbol: str) -> int | None:
    """Conservatively locate a declaration line; UNKNOWN beats fabricated precision."""

    escaped = re.escape(symbol)
    word = rf"(?<![A-Za-z0-9_$]){escaped}(?![A-Za-z0-9_$])"
    if kind == "method":
        patterns = (re.compile(rf"{word}[ \t]*\("),)
    else:
        patterns = (
            re.compile(
                rf"(?<![A-Za-z0-9_$])(?:class|interface|enum|record|@interface)[ \t]+{escaped}"
                rf"(?![A-Za-z0-9_$])"
            ),
            re.compile(word),
        )
    for pattern in patterns:
        for number, line in enumerate(lines, start=1):
            if pattern.search(line):
                return number
    return None


@dataclass(slots=True)
class _Proposal:
    start: int
    end: int
    target: int | None


def _select_windows(lines: tuple[str, ...], candidate: CandidateFile) -> list[_Proposal]:
    """Deterministic bounded windows for one candidate's already-read source.

    Each objectively located structural symbol yields one bounded window that
    contains its declaration line (at most MAX_CONTEXT_WINDOW_LINES lines,
    beginning _SYMBOL_WINDOW_LINES_BEFORE lines above it when available).
    Without a defensible location the single documented fallback applies: the
    bounded prefix window starting at line 1.
    """

    count = len(lines)
    if count == 0:
        return []
    located: list[int] = []
    for kind, symbol in _structural_symbols(candidate):
        line = _locate_symbol(lines, kind, symbol)
        if line is not None and line not in located:
            located.append(line)
    located.sort()
    proposals: list[_Proposal] = []
    for line in located[:_MAX_PROPOSALS_PER_CANDIDATE]:
        start = max(1, line - _SYMBOL_WINDOW_LINES_BEFORE)
        end = min(count, start + MAX_CONTEXT_WINDOW_LINES - 1)
        proposals.append(_Proposal(start, end, line))
    if proposals:
        return proposals
    return [_Proposal(1, min(count, MAX_CONTEXT_WINDOW_LINES), None)]


def _merge_proposals(proposals: list[_Proposal]) -> list[_Proposal]:
    """Same-file overlap policy: merge identical, nested and partial overlap.

    Overlapping ranges collapse into their union range; the retained target is
    the first non-unknown target in deterministic (start, end) order. Ranges
    that merely touch (next start == current end + 1) are deliberately NOT
    merged: adjacency is not overlap, so adjacent windows stay separate items.
    Different files are never merged regardless of textual equality because
    source identity and provenance win over content equality.
    """

    merged: list[_Proposal] = []
    for proposal in sorted(proposals, key=lambda item: (item.start, item.end)):
        if merged and proposal.start <= merged[-1].end:
            anchor = merged[-1]
            anchor.end = max(anchor.end, proposal.end)
            if anchor.target is None:
                anchor.target = proposal.target
        else:
            merged.append(_Proposal(proposal.start, proposal.end, proposal.target))
    return merged


# --------------------------------------------------------------------------
# Whole-line budget fitting
# --------------------------------------------------------------------------


def _line_byte_prefix(lines: tuple[str, ...]) -> list[int]:
    prefix = [0]
    running = 0
    for line in lines:
        running += len(line.encode("utf-8"))
        prefix.append(running)
    return prefix


def _fit_span(span: _Proposal, prefix: list[int], capacity: int) -> tuple[int, int] | None:
    """Shrink a proposed range to whole source lines that fit ``capacity``.

    The caller bounds ``capacity`` by both the remaining context token budget
    and MAX_CONTEXT_BYTES, so no fitted item can exceed either limit. Targeted
    windows preserve the target line and expand deterministically around it
    (toward later lines first) inside the original proposal bounds. Fallback
    prefix windows grow deterministically from the first line. When even the
    smallest permitted one-line item does not fit, the proposal is skipped
    entirely rather than truncating arbitrary UTF-8 bytes.
    """

    if prefix[span.end] - prefix[span.start - 1] <= capacity:
        return span.start, span.end
    if span.target is None:
        taken = 0
        used = 0
        for line in range(span.start, span.end + 1):
            cost = prefix[line] - prefix[line - 1]
            if used + cost > capacity:
                break
            used += cost
            taken += 1
        if taken == 0:
            return None
        return span.start, span.start + taken - 1
    low = high = min(max(span.target, span.start), span.end)
    used = prefix[low] - prefix[low - 1]
    if used > capacity:
        return None
    while True:
        progressed = False
        if high < span.end:
            cost = prefix[high + 1] - prefix[high]
            if used + cost <= capacity:
                high += 1
                used += cost
                progressed = True
        if low > span.start:
            cost = prefix[low] - prefix[low - 1]
            if used + cost <= capacity:
                low -= 1
                used += cost
                progressed = True
        if not progressed:
            return low, high


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------


def _require_bound_workspace_index(
    workspace: PreparedRepositoryWorkspace, index: RepositoryIndex
) -> None:
    """Fail closed unless workspace and index describe exactly one revision.

    Identity comes only from the supplied contract values; HEAD, branch names,
    working directories and environment state are never consulted.
    """

    if (
        workspace.repository_identity != index.manifest.repository_id
        or workspace.revision_identity != index.manifest.revision_id
    ):
        _fail(
            ContextErrorCode.WORKSPACE_INDEX_MISMATCH,
            "workspace and index do not describe the same repository revision",
        )


def assemble_context(request: ContextAssemblyInput) -> ContextBundle:
    """Assemble the canonical context bundle for the supplied ranked candidates.

    Every emitted ``ContextItem`` carries exact repository provenance, the
    UNTRUSTED_REPOSITORY_TEXT trust label, byte-exact source content whose
    SHA-256 equals its provenance digest, and a conservative byte-based token
    count. The returned bundle never exceeds the supplied budget, the
    CONTRACT-RAG-001 MAX_CONTEXT_BYTES per-item limit, or the MAX_CONTEXT_ITEMS
    count limit, and is fully determined by its semantic inputs.
    """

    if type(request) is not ContextAssemblyInput:
        _fail(ContextErrorCode.INVALID_CONTEXT_REQUEST, "request must be a ContextAssemblyInput")

    workspace = request.workspace
    index = request.index
    manifest = index.manifest
    _require_bound_workspace_index(workspace, index)

    indexed_files: dict[str, IndexedFile] = {
        item.manifest_file.file_identity.value: item for item in index.files
    }
    candidates = request.candidates
    for candidate in candidates:
        if (
            candidate.repository_id != manifest.repository_id
            or candidate.revision_id != manifest.revision_id
        ):
            _fail(
                ContextErrorCode.CANDIDATE_INDEX_MISMATCH,
                "candidate does not belong to the indexed repository revision",
            )
        if candidate.file_identity.value not in indexed_files:
            _fail(
                ContextErrorCode.UNKNOWN_CANDIDATE_FILE,
                f"candidate file {candidate.file_identity.value} is not present in the "
                "supplied repository index",
            )
        expected = candidate_identity(
            manifest.repository_id.value, manifest.revision_id.value, candidate.file_identity.value
        )
        if candidate.candidate_id != expected:
            _fail(
                ContextErrorCode.INVALID_CANDIDATE,
                "candidate identity does not match the deterministic identity for its "
                "repository revision and file",
            )

    groups: list[tuple[CandidateFile, tuple[str, ...], list[int], list[_Proposal]]] = []
    root_fd = _open_root(workspace)
    try:
        sources: dict[str, tuple[str, ...] | None] = {}
        prefixes: dict[str, list[int]] = {}
        for candidate in candidates:
            path = candidate.file_identity.value
            if path not in sources:
                sources[path] = _read_verified_lines(root_fd, indexed_files[path])
                prefixes[path] = _line_byte_prefix(sources[path] or ())
            lines = sources[path]
            if not lines:
                continue
            spans = _merge_proposals(_select_windows(lines, candidate))
            if spans:
                groups.append((candidate, lines, prefixes[path], spans))
    finally:
        os.close(root_fd)

    items: list[ContextItem] = []
    remaining = request.context_token_budget
    for candidate, lines, prefix, spans in groups:
        if len(items) >= MAX_CONTEXT_ITEMS:
            break
        for span in spans:
            if len(items) >= MAX_CONTEXT_ITEMS:
                break
            # CONTRACT-RAG-001 packing bound: an item is never constructed
            # with content larger than MAX_CONTEXT_BYTES nor beyond the
            # caller's remaining budget; no oversized bundle is ever built.
            capacity = min(remaining, MAX_CONTEXT_BYTES)
            fitted = _fit_span(span, prefix, capacity)
            if fitted is None:
                continue
            start_line, end_line = fitted
            content = "".join(lines[start_line - 1 : end_line])
            encoded = content.encode("utf-8")
            content_sha256 = hashlib.sha256(encoded).hexdigest()
            token_count = len(encoded)
            item = ContextItem(
                _context_item_identity(
                    manifest.repository_id.value,
                    manifest.revision_id.value,
                    candidate.candidate_id.value,
                    candidate.file_identity.value,
                    start_line,
                    end_line,
                    content_sha256,
                    token_count,
                ),
                candidate.candidate_id,
                Provenance(
                    manifest.repository_id,
                    manifest.revision_id,
                    candidate.file_identity,
                    start_line,
                    end_line,
                    content_sha256,
                ),
                TrustLabel.UNTRUSTED_REPOSITORY_TEXT,
                content,
                token_count,
            )
            items.append(item)
            remaining -= token_count

    consumed_tokens = sum(item.token_count for item in items)
    bundle = ContextBundle(
        _context_bundle_identity(
            manifest.repository_id.value,
            manifest.revision_id.value,
            tuple(items),
            request.context_token_budget,
            consumed_tokens,
        ),
        manifest.repository_id,
        manifest.revision_id,
        tuple(items),
        TokenBudget(request.context_token_budget, consumed_tokens),
    )
    return bundle
