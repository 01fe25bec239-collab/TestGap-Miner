"""Deterministic, read-only discovery of a prepared repository workspace."""

from __future__ import annotations

import codecs
import hashlib
import os
import stat
from dataclasses import dataclass
from enum import StrEnum
from pathlib import PureWindowsPath
from typing import Final

from app.retrieval.localisation import (
    MAX_MANIFEST_FILES,
    FileIdentity,
    ManifestFile,
    RepositoryManifest,
)
from app.workflow.repository_workspace import PreparedRepositoryWorkspace


# RAG-002 indexing safety policy, not a CONTRACT-RAG-001 content limit.
MAX_INDEX_FILE_BYTES: Final = 8 * 1024 * 1024
MAX_INDEX_DEPTH: Final = 256
MAX_DISCOVERY_ENTRIES: Final = 100_000
MAX_TOTAL_SOURCE_BYTES: Final = 512 * 1024 * 1024
_READ_CHUNK_BYTES: Final = 64 * 1024
_LANGUAGES: Final = {
    ".java": "JAVA",
    ".js": "JAVASCRIPT",
    ".jsx": "JAVASCRIPT",
    ".mjs": "JAVASCRIPT",
    ".cjs": "JAVASCRIPT",
    ".py": "PYTHON",
    ".rs": "RUST",
    ".ts": "TYPESCRIPT",
    ".tsx": "TYPESCRIPT",
    ".mts": "TYPESCRIPT",
    ".cts": "TYPESCRIPT",
}


class IndexingErrorCode(StrEnum):
    INVALID_ROOT = "INVALID_ROOT"
    FILESYSTEM_FAILURE = "FILESYSTEM_FAILURE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    FILE_LIMIT_EXCEEDED = "FILE_LIMIT_EXCEEDED"
    DISCOVERY_ENTRY_LIMIT_EXCEEDED = "DISCOVERY_ENTRY_LIMIT_EXCEEDED"
    TOTAL_SOURCE_BYTES_EXCEEDED = "TOTAL_SOURCE_BYTES_EXCEEDED"
    DEPTH_LIMIT_EXCEEDED = "DEPTH_LIMIT_EXCEEDED"
    SOURCE_CHANGED = "SOURCE_CHANGED"


class RepositoryIndexingError(RuntimeError):
    """Fail-closed error without leaking host paths."""

    def __init__(self, code: IndexingErrorCode, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code.value}: {detail}")


def _verify_same_object(fd: int, expected: os.stat_result, detail: str) -> os.stat_result:
    """Confirm an opened descriptor is the object inspected just before opening."""

    try:
        opened = os.fstat(fd)
    except OSError:
        raise RepositoryIndexingError(
            IndexingErrorCode.FILESYSTEM_FAILURE, "repository entry cannot be inspected"
        ) from None
    if (expected.st_dev, expected.st_ino, stat.S_IFMT(expected.st_mode)) != (
        opened.st_dev,
        opened.st_ino,
        stat.S_IFMT(opened.st_mode),
    ):
        raise RepositoryIndexingError(IndexingErrorCode.SOURCE_CHANGED, detail)
    return opened


class FileLanguage(StrEnum):
    JAVA = "JAVA"
    PYTHON = "PYTHON"
    RUST = "RUST"
    JAVASCRIPT = "JAVASCRIPT"
    TYPESCRIPT = "TYPESCRIPT"
    UNKNOWN = "UNKNOWN"


class FileRole(StrEnum):
    SOURCE = "SOURCE"
    TEST = "TEST"
    UNKNOWN = "UNKNOWN"


class ContentKind(StrEnum):
    TEXT = "TEXT"
    BINARY = "BINARY"


class ExclusionReason(StrEnum):
    VCS_METADATA = "VCS_METADATA"
    VENDOR_DEPENDENCY = "VENDOR_DEPENDENCY"
    GENERATED_BUILD = "GENERATED_BUILD"
    CACHE = "CACHE"
    SYMLINK = "SYMLINK"
    SPECIAL_ENTRY = "SPECIAL_ENTRY"


_EXCLUDED_DIRECTORIES: Final = {
    ".git": ExclusionReason.VCS_METADATA,
    ".hg": ExclusionReason.VCS_METADATA,
    ".svn": ExclusionReason.VCS_METADATA,
    ".venv": ExclusionReason.VENDOR_DEPENDENCY,
    "node_modules": ExclusionReason.VENDOR_DEPENDENCY,
    "vendor": ExclusionReason.VENDOR_DEPENDENCY,
    "build": ExclusionReason.GENERATED_BUILD,
    "dist": ExclusionReason.GENERATED_BUILD,
    "target": ExclusionReason.GENERATED_BUILD,
    "__pycache__": ExclusionReason.CACHE,
}


@dataclass(frozen=True, slots=True)
class IndexedFile:
    manifest_file: ManifestFile
    language: FileLanguage
    role: FileRole
    content_kind: ContentKind
    byte_size: int


@dataclass(frozen=True, slots=True)
class ExcludedEntry:
    relative_path: str
    reason: ExclusionReason


@dataclass(slots=True)
class _TraversalState:
    discovered_entries: int = 0
    total_source_bytes: int = 0


@dataclass(frozen=True, slots=True)
class RepositoryIndex:
    manifest: RepositoryManifest
    files: tuple[IndexedFile, ...]
    exclusions: tuple[ExcludedEntry, ...]


def build_repository_manifest(workspace: PreparedRepositoryWorkspace) -> RepositoryManifest:
    """Build the existing RAG manifest from only the supplied workspace root."""

    return index_repository(workspace).manifest


def index_repository(workspace: PreparedRepositoryWorkspace) -> RepositoryIndex:
    """Discover and classify regular files without following links."""

    # Validate the Workflow-supplied identities before touching the filesystem.
    RepositoryManifest(workspace.repository_identity, workspace.revision_identity, ())
    if isinstance(workspace.workspace_root, PureWindowsPath):
        raise RepositoryIndexingError(
            IndexingErrorCode.INVALID_ROOT, "workspace root is incompatible with this host"
        )

    root = os.fspath(workspace.workspace_root)
    try:
        root_stat = os.lstat(root)
        if stat.S_ISLNK(root_stat.st_mode) or not stat.S_ISDIR(root_stat.st_mode):
            raise RepositoryIndexingError(
                IndexingErrorCode.INVALID_ROOT, "workspace root must be a regular directory"
            )
        root_fd = os.open(
            root,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
    except RepositoryIndexingError:
        raise
    except (OSError, TypeError, ValueError):
        raise RepositoryIndexingError(
            IndexingErrorCode.INVALID_ROOT, "workspace root is not structurally usable"
        ) from None

    files: list[IndexedFile] = []
    exclusions: list[ExcludedEntry] = []
    state = _TraversalState()
    try:
        _verify_same_object(root_fd, root_stat, "workspace root changed while indexing")
        _walk(root_fd, (), files, exclusions, state, 0)
    finally:
        os.close(root_fd)

    ordered = tuple(sorted(files, key=lambda item: item.manifest_file.file_identity.value))
    manifest = RepositoryManifest(
        workspace.repository_identity,
        workspace.revision_identity,
        tuple(item.manifest_file for item in ordered),
    )
    return RepositoryIndex(
        manifest,
        ordered,
        tuple(sorted(exclusions, key=lambda item: item.relative_path)),
    )


def _walk(
    directory_fd: int,
    parent: tuple[str, ...],
    files: list[IndexedFile],
    exclusions: list[ExcludedEntry],
    state: _TraversalState,
    depth: int,
) -> None:
    try:
        with os.scandir(directory_fd) as entries:
            ordered = []
            for entry in entries:
                state.discovered_entries += 1
                if state.discovered_entries > MAX_DISCOVERY_ENTRIES:
                    raise RepositoryIndexingError(
                        IndexingErrorCode.DISCOVERY_ENTRY_LIMIT_EXCEEDED,
                        "repository discovery entry limit exceeded",
                    )
                ordered.append(entry)
    except OSError:
        raise RepositoryIndexingError(
            IndexingErrorCode.FILESYSTEM_FAILURE, "repository directory cannot be enumerated"
        ) from None

    ordered.sort(key=lambda entry: entry.name)
    for entry in ordered:
        parts = (*parent, entry.name)
        relative_path = "/".join(parts)
        try:
            metadata = os.stat(entry.name, dir_fd=directory_fd, follow_symlinks=False)
        except OSError:
            raise RepositoryIndexingError(
                IndexingErrorCode.FILESYSTEM_FAILURE, "repository entry cannot be inspected"
            ) from None

        if stat.S_ISLNK(metadata.st_mode):
            exclusions.append(ExcludedEntry(relative_path, ExclusionReason.SYMLINK))
            continue
        if stat.S_ISDIR(metadata.st_mode):
            if reason := _EXCLUDED_DIRECTORIES.get(entry.name):
                exclusions.append(ExcludedEntry(relative_path, reason))
                continue
            if depth >= MAX_INDEX_DEPTH:
                raise RepositoryIndexingError(
                    IndexingErrorCode.DEPTH_LIMIT_EXCEEDED,
                    "repository directory depth limit exceeded",
                )
            try:
                child_fd = os.open(
                    entry.name,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=directory_fd,
                )
            except OSError:
                raise RepositoryIndexingError(
                    IndexingErrorCode.FILESYSTEM_FAILURE,
                    "repository directory cannot be opened safely",
                ) from None
            try:
                _verify_same_object(
                    child_fd, metadata, "repository directory changed while indexing"
                )
                _walk(child_fd, parts, files, exclusions, state, depth + 1)
            finally:
                os.close(child_fd)
            continue
        if not stat.S_ISREG(metadata.st_mode):
            exclusions.append(ExcludedEntry(relative_path, ExclusionReason.SPECIAL_ENTRY))
            continue
        if len(files) >= MAX_MANIFEST_FILES:
            raise RepositoryIndexingError(
                IndexingErrorCode.FILE_LIMIT_EXCEEDED, "manifest file limit exceeded"
            )
        identity = FileIdentity("/".join(parts))
        digest, byte_size, content_kind = _hash_file(
            directory_fd,
            entry.name,
            metadata,
            MAX_TOTAL_SOURCE_BYTES - state.total_source_bytes,
        )
        state.total_source_bytes += byte_size
        files.append(
            IndexedFile(
                ManifestFile(identity, digest),
                _classify_language(identity.value),
                _classify_role(identity.value),
                content_kind,
                byte_size,
            )
        )


def _hash_file(
    directory_fd: int,
    name: str,
    expected: os.stat_result,
    remaining_source_bytes: int,
) -> tuple[str, int, ContentKind]:
    try:
        file_fd = os.open(
            name,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=directory_fd,
        )
        with os.fdopen(file_fd, "rb") as source:
            before = _verify_same_object(
                source.fileno(), expected, "repository file changed while indexing"
            )
            if before.st_size > MAX_INDEX_FILE_BYTES:
                raise RepositoryIndexingError(
                    IndexingErrorCode.FILE_TOO_LARGE, "repository file exceeds indexing byte limit"
                )
            if before.st_size > remaining_source_bytes:
                raise RepositoryIndexingError(
                    IndexingErrorCode.TOTAL_SOURCE_BYTES_EXCEEDED,
                    "repository total source byte limit exceeded",
                )
            digest = hashlib.sha256()
            decoder = codecs.getincrementaldecoder("utf-8")()
            content_kind = ContentKind.TEXT
            total = 0
            while chunk := source.read(_READ_CHUNK_BYTES):
                total += len(chunk)
                if total > MAX_INDEX_FILE_BYTES:
                    raise RepositoryIndexingError(
                        IndexingErrorCode.FILE_TOO_LARGE,
                        "repository file exceeds indexing byte limit",
                    )
                if total > remaining_source_bytes:
                    raise RepositoryIndexingError(
                        IndexingErrorCode.TOTAL_SOURCE_BYTES_EXCEEDED,
                        "repository total source byte limit exceeded",
                    )
                digest.update(chunk)
                if content_kind is ContentKind.TEXT:
                    if b"\x00" in chunk:
                        content_kind = ContentKind.BINARY
                    else:
                        try:
                            decoder.decode(chunk)
                        except UnicodeDecodeError:
                            content_kind = ContentKind.BINARY
            if content_kind is ContentKind.TEXT:
                try:
                    decoder.decode(b"", final=True)
                except UnicodeDecodeError:
                    content_kind = ContentKind.BINARY
            after = os.fstat(source.fileno())
            if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                after.st_size,
                after.st_mtime_ns,
                after.st_ctime_ns,
            ):
                raise RepositoryIndexingError(
                    IndexingErrorCode.SOURCE_CHANGED, "repository file changed while indexing"
                )
            return digest.hexdigest(), total, content_kind
    except RepositoryIndexingError:
        raise
    except OSError:
        raise RepositoryIndexingError(
            IndexingErrorCode.FILESYSTEM_FAILURE, "repository file cannot be read safely"
        ) from None


def _classify_language(path: str) -> FileLanguage:
    filename = path.rsplit("/", 1)[-1]
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return FileLanguage(_LANGUAGES.get(suffix, "UNKNOWN"))


def _classify_role(path: str) -> FileRole:
    parts = path.lower().split("/")
    filename = parts[-1]
    stem = filename.rsplit(".", 1)[0]
    if any(part in {"test", "tests", "__tests__"} for part in parts[:-1]):
        return FileRole.TEST
    if (
        stem.startswith("test_")
        or stem.endswith("_test")
        or ".test." in filename
        or ".spec." in filename
    ):
        return FileRole.TEST
    if _classify_language(path) is not FileLanguage.UNKNOWN:
        return FileRole.SOURCE
    return FileRole.UNKNOWN
