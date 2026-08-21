from __future__ import annotations

import hashlib
import itertools
import os
import stat
import traceback
from pathlib import Path, PureWindowsPath
from types import SimpleNamespace

import pytest

import app.retrieval.indexing as indexing
from app.retrieval.indexing import (
    ContentKind,
    ExclusionReason,
    FileLanguage,
    FileRole,
    IndexedFile,
    IndexingErrorCode,
    RepositoryIndexingError,
    build_repository_manifest,
    index_repository,
)
from app.retrieval.localisation import (
    FileIdentity,
    LocalisationContractError,
    LocalisationErrorCode,
    ManifestFile,
    RepositoryIdentity,
    RepositoryManifest,
    RevisionIdentity,
)
from app.workflow.repository_workspace import PreparedRepositoryWorkspace, WorkspaceMode


REPOSITORY = RepositoryIdentity("example/safe-index")
REVISION = RevisionIdentity("1" * 40)


def workspace(root: Path, mode: WorkspaceMode = WorkspaceMode.READ_ONLY):
    return PreparedRepositoryWorkspace(REPOSITORY, REVISION, root, mode)


def paths(result: indexing.RepositoryIndex) -> list[str]:
    return [item.manifest_file.file_identity.value for item in result.files]


def test_manifest_preserves_workspace_binding_and_is_cwd_independent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "source"
    root.mkdir()
    (root / "b.py").write_bytes(b"print('b')\n")
    (root / "a.py").write_bytes(b"print('a')\n")
    prepared = workspace(root)

    first = build_repository_manifest(prepared)
    monkeypatch.chdir(tmp_path)
    second = build_repository_manifest(prepared)

    assert isinstance(first, RepositoryManifest)
    assert first == second
    assert first.repository_id is REPOSITORY
    assert first.revision_id is REVISION
    assert [file.file_identity.value for file in first.files] == ["a.py", "b.py"]
    assert str(root) not in first.canonical_json()


def test_git_metadata_cannot_override_pinned_identity(tmp_path: Path) -> None:
    root = tmp_path / "source"
    (root / ".git").mkdir(parents=True)
    (root / ".git" / "HEAD").write_text("ref: refs/heads/wrong\n")
    (root / "main.py").write_text("pass\n")

    manifest = build_repository_manifest(workspace(root))

    assert manifest.revision_id is REVISION
    assert [item.file_identity.value for item in manifest.files] == ["main.py"]


def test_hashes_exact_bytes_including_empty_binary_and_malformed_utf8(tmp_path: Path) -> None:
    root = tmp_path / "source"
    root.mkdir()
    content = b"\x00\xffexact\r\n"
    (root / "data.bin").write_bytes(content)
    (root / "empty").write_bytes(b"")
    (root / "malformed.txt").write_bytes(b"text\xff")

    result = index_repository(workspace(root))
    by_path = {item.manifest_file.file_identity.value: item for item in result.files}

    assert by_path["data.bin"].manifest_file.content_sha256 == hashlib.sha256(content).hexdigest()
    assert by_path["empty"].manifest_file.content_sha256 == hashlib.sha256(b"").hexdigest()
    assert by_path["data.bin"].content_kind is ContentKind.BINARY
    assert by_path["malformed.txt"].content_kind is ContentKind.BINARY
    assert by_path["empty"].content_kind is ContentKind.TEXT


def test_classifies_complete_content_and_split_utf8_sequences(tmp_path: Path) -> None:
    root = tmp_path / "source"
    root.mkdir()
    after_old_sample = b"x" * (8 * 1024 + 1)
    (root / "late-nul.txt").write_bytes(after_old_sample + b"\x00")
    (root / "late-invalid.txt").write_bytes(after_old_sample + b"\xff")
    split_utf8 = b"x" * (indexing._READ_CHUNK_BYTES - 1) + "\N{EURO SIGN}".encode()
    (root / "split-utf8.txt").write_bytes(split_utf8)

    by_path = {
        item.manifest_file.file_identity.value: item
        for item in index_repository(workspace(root)).files
    }

    assert by_path["late-nul.txt"].content_kind is ContentKind.BINARY
    assert by_path["late-invalid.txt"].content_kind is ContentKind.BINARY
    assert by_path["split-utf8.txt"].content_kind is ContentKind.TEXT
    assert by_path["split-utf8.txt"].manifest_file.content_sha256 == hashlib.sha256(
        split_utf8
    ).hexdigest()


def test_byte_size_is_exact(tmp_path: Path) -> None:
    root = tmp_path / "source"
    root.mkdir()
    content = "hello \N{EURO SIGN}".encode()
    (root / "main.py").write_bytes(content)

    assert index_repository(workspace(root)).files[0].byte_size == len(content)


def test_file_size_exact_boundary_is_accepted(tmp_path: Path) -> None:
    root = tmp_path / "source"
    root.mkdir()
    content = b"x" * indexing.MAX_INDEX_FILE_BYTES
    (root / "boundary.bin").write_bytes(content)

    manifest = build_repository_manifest(workspace(root))

    assert manifest.files[0].content_sha256 == hashlib.sha256(content).hexdigest()


def test_file_size_boundary_plus_one_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "source"
    root.mkdir()
    (root / "large.bin").write_bytes(b"x" * (indexing.MAX_INDEX_FILE_BYTES + 1))

    with pytest.raises(RepositoryIndexingError) as raised:
        build_repository_manifest(workspace(root))

    assert raised.value.code is IndexingErrorCode.FILE_TOO_LARGE
    assert str(root) not in str(raised.value)


def test_file_count_exact_boundary_and_plus_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "source"
    root.mkdir()
    (root / "a").touch()
    (root / "b").touch()
    monkeypatch.setattr(indexing, "MAX_MANIFEST_FILES", 2)

    assert len(build_repository_manifest(workspace(root)).files) == 2
    (root / "c").touch()
    with pytest.raises(RepositoryIndexingError) as raised:
        build_repository_manifest(workspace(root))
    assert raised.value.code is IndexingErrorCode.FILE_LIMIT_EXCEEDED


@pytest.mark.parametrize(
    "excluded",
    [
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        "vendor",
        ".venv",
        "target",
        "dist",
        "build",
        "__pycache__",
    ],
)
def test_explicit_directory_exclusions(tmp_path: Path, excluded: str) -> None:
    root = tmp_path / "source"
    (root / excluded).mkdir(parents=True)
    (root / excluded / "hidden.py").write_text("pass\n")
    (root / "visible.py").write_text("pass\n")

    assert paths(index_repository(workspace(root))) == ["visible.py"]


GIT_POINTER = "gitdir: /some/host/path/.git/worktrees/example\n"


@pytest.mark.parametrize("name", [".git", ".hg", ".svn"])
def test_vcs_metadata_pointer_file_is_excluded_like_its_directory(
    tmp_path: Path, name: str
) -> None:
    root = tmp_path / "source"
    root.mkdir()
    (root / name).write_text(GIT_POINTER)
    (root / "visible.py").write_text("pass\n")

    result = index_repository(workspace(root))

    assert [(item.relative_path, item.reason) for item in result.exclusions] == [
        (name, ExclusionReason.VCS_METADATA)
    ]
    assert paths(result) == ["visible.py"]
    assert [item.file_identity.value for item in result.manifest.files] == ["visible.py"]
    pointer_digest = hashlib.sha256(GIT_POINTER.encode()).hexdigest()
    assert pointer_digest not in result.manifest.canonical_json()


def test_worktree_pointer_file_and_directory_exclusions_stay_ordered(tmp_path: Path) -> None:
    root = tmp_path / "source"
    (root / "node_modules").mkdir(parents=True)
    (root / ".git").write_text(GIT_POINTER)
    (root / "__pycache__").mkdir()
    (root / "visible.py").write_text("pass\n")

    first = index_repository(workspace(root))
    second = index_repository(workspace(root))

    assert first.exclusions == second.exclusions
    assert [(item.relative_path, item.reason) for item in first.exclusions] == [
        (".git", ExclusionReason.VCS_METADATA),
        ("__pycache__", ExclusionReason.CACHE),
        ("node_modules", ExclusionReason.VENDOR_DEPENDENCY),
    ]
    assert paths(first) == ["visible.py"]


def test_exclusion_metadata_is_deterministic_and_content_stays_out_of_manifest(
    tmp_path: Path,
) -> None:
    root = tmp_path / "source"
    (root / ".git").mkdir(parents=True)
    (root / ".git" / "config").write_text("hidden\n")
    (root / "node_modules").mkdir()
    (root / "node_modules" / "package.js").write_text("hidden\n")
    (root / "dist").mkdir()
    (root / "dist" / "bundle.js").write_text("hidden\n")
    (root / "__pycache__").mkdir()
    (root / "__pycache__" / "cached.pyc").write_bytes(b"hidden")
    (root / "visible.py").write_text("pass\n")
    (root / "link").symlink_to(root / "visible.py")

    first = index_repository(workspace(root))
    second = index_repository(workspace(root))

    assert first.exclusions == second.exclusions
    assert [(item.relative_path, item.reason) for item in first.exclusions] == [
        (".git", ExclusionReason.VCS_METADATA),
        ("__pycache__", ExclusionReason.CACHE),
        ("dist", ExclusionReason.GENERATED_BUILD),
        ("link", ExclusionReason.SYMLINK),
        ("node_modules", ExclusionReason.VENDOR_DEPENDENCY),
    ]
    assert [item.file_identity.value for item in first.manifest.files] == ["visible.py"]


def test_symlink_files_directories_external_escape_loop_and_broken_are_skipped(
    tmp_path: Path,
) -> None:
    root = tmp_path / "source"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.py").write_text("secret\n")
    (root / "kept.py").write_text("kept\n")
    (root / "file-link").symlink_to(root / "kept.py")
    (root / "dir-link").symlink_to(outside, target_is_directory=True)
    (root / "loop").symlink_to(root, target_is_directory=True)
    (root / "broken").symlink_to(root / "missing")

    assert paths(index_repository(workspace(root))) == ["kept.py"]


def test_root_symlink_missing_file_and_incompatible_platform_fail_closed(
    tmp_path: Path,
) -> None:
    root = tmp_path / "source"
    root.mkdir()
    link = tmp_path / "link"
    link.symlink_to(root, target_is_directory=True)

    for prepared in (
        workspace(link),
        workspace(tmp_path / "missing"),
        PreparedRepositoryWorkspace(
            REPOSITORY,
            REVISION,
            PureWindowsPath("C:\\repo"),
            WorkspaceMode.READ_ONLY,
        ),
    ):
        with pytest.raises(RepositoryIndexingError) as raised:
            build_repository_manifest(prepared)
        assert raised.value.code is IndexingErrorCode.INVALID_ROOT


def test_non_directory_root_rejected(tmp_path: Path) -> None:
    root = tmp_path / "file"
    root.write_text("not a directory")
    with pytest.raises(RepositoryIndexingError):
        build_repository_manifest(workspace(root))


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="host has no FIFO support")
def test_special_non_regular_file_is_skipped_and_counted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "source"
    root.mkdir()
    os.mkfifo(root / "pipe")
    (root / "kept").touch()

    result = index_repository(workspace(root))

    assert paths(result) == ["kept"]
    assert [(item.relative_path, item.reason) for item in result.exclusions] == [
        ("pipe", ExclusionReason.SPECIAL_ENTRY)
    ]

    monkeypatch.setattr(indexing, "MAX_DISCOVERY_ENTRIES", 1)
    with pytest.raises(RepositoryIndexingError) as raised:
        index_repository(workspace(root))
    assert raised.value.code is IndexingErrorCode.DISCOVERY_ENTRY_LIMIT_EXCEEDED


def test_discovery_entry_exact_boundary_and_plus_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "source"
    root.mkdir()
    (root / "a").touch()
    (root / "b").mkdir()
    monkeypatch.setattr(indexing, "MAX_DISCOVERY_ENTRIES", 2)

    assert paths(index_repository(workspace(root))) == ["a"]
    (root / "c").symlink_to(root / "a")
    with pytest.raises(RepositoryIndexingError) as raised:
        index_repository(workspace(root))
    assert raised.value.code is IndexingErrorCode.DISCOVERY_ENTRY_LIMIT_EXCEEDED


def test_total_source_bytes_exact_boundary_and_plus_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "source"
    root.mkdir()
    (root / "a").write_bytes(b"ab")
    (root / "b").write_bytes(b"c")
    monkeypatch.setattr(indexing, "MAX_TOTAL_SOURCE_BYTES", 3)

    assert [item.byte_size for item in index_repository(workspace(root)).files] == [2, 1]
    (root / "c").write_bytes(b"d")
    with pytest.raises(RepositoryIndexingError) as raised:
        index_repository(workspace(root))
    assert raised.value.code is IndexingErrorCode.TOTAL_SOURCE_BYTES_EXCEEDED


@pytest.mark.parametrize(
    "filename,language",
    [
        ("Main.java", FileLanguage.JAVA),
        ("main.py", FileLanguage.PYTHON),
        ("lib.rs", FileLanguage.RUST),
        ("app.js", FileLanguage.JAVASCRIPT),
        ("view.tsx", FileLanguage.TYPESCRIPT),
        ("README", FileLanguage.UNKNOWN),
    ],
)
def test_language_classification(tmp_path: Path, filename: str, language: FileLanguage) -> None:
    root = tmp_path / "source"
    root.mkdir()
    (root / filename).touch()
    assert index_repository(workspace(root)).files[0].language is language


def test_test_source_and_ambiguous_roles(tmp_path: Path) -> None:
    root = tmp_path / "source"
    (root / "tests").mkdir(parents=True)
    (root / "tests" / "thing.py").touch()
    (root / "service.py").touch()
    (root / "contest.txt").touch()

    result = index_repository(workspace(root))
    roles = {item.manifest_file.file_identity.value: item.role for item in result.files}

    assert roles == {
        "contest.txt": FileRole.UNKNOWN,
        "service.py": FileRole.SOURCE,
        "tests/thing.py": FileRole.TEST,
    }


def test_noncanonical_host_filename_fails_at_existing_file_identity_boundary(
    tmp_path: Path,
) -> None:
    root = tmp_path / "source"
    root.mkdir()
    (root / "back\\slash.py").touch()

    with pytest.raises(LocalisationContractError) as raised:
        build_repository_manifest(workspace(root))
    assert raised.value.code is LocalisationErrorCode.INVALID_FILE_IDENTITY


def test_unicode_normalization_conflict_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "source"
    root.mkdir()
    (root / "\N{LATIN SMALL LETTER E WITH ACUTE}.py").touch()
    (root / "e\N{COMBINING ACUTE ACCENT}.py").touch()

    with pytest.raises(LocalisationContractError) as raised:
        build_repository_manifest(workspace(root))
    assert raised.value.code is LocalisationErrorCode.INVALID_FILE_IDENTITY


def test_duplicate_and_conflicting_logical_identity_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "source"
    root.mkdir()
    first = IndexedFile(
        ManifestFile(FileIdentity("same.py"), "a" * 64),
        FileLanguage.PYTHON,
        FileRole.SOURCE,
        ContentKind.TEXT,
        0,
    )

    for other_hash, expected in (
        ("a" * 64, LocalisationErrorCode.DUPLICATE_IDENTITY),
        ("b" * 64, LocalisationErrorCode.IDENTITY_CONFLICT),
    ):
        other = IndexedFile(
            ManifestFile(FileIdentity("same.py"), other_hash),
            FileLanguage.PYTHON,
            FileRole.SOURCE,
            ContentKind.TEXT,
            0,
        )
        monkeypatch.setattr(
            indexing,
            "_walk",
            lambda _fd, _parent, files, _exclusions, _state, _depth: files.extend(
                (first, other)
            ),
        )
        with pytest.raises(LocalisationContractError) as raised:
            index_repository(workspace(root))
        assert raised.value.code is expected


@pytest.mark.parametrize("mode", [WorkspaceMode.READ_ONLY, WorkspaceMode.DISPOSABLE])
def test_both_modes_are_read_only_and_source_tree_is_unchanged(
    tmp_path: Path, mode: WorkspaceMode
) -> None:
    root = tmp_path / "source"
    root.mkdir()
    source = root / "main.py"
    source.write_bytes(b"print('unchanged')\n")
    before = (source.read_bytes(), source.stat().st_mode, source.stat().st_mtime_ns)

    build_repository_manifest(workspace(root, mode))

    assert (source.read_bytes(), source.stat().st_mode, source.stat().st_mtime_ns) == before


def test_canonical_manifest_representation_and_output_order_are_deterministic(
    tmp_path: Path,
) -> None:
    root = tmp_path / "source"
    (root / "z").mkdir(parents=True)
    (root / "a").mkdir()
    (root / "z" / "last.rs").touch()
    (root / "a" / "first.java").touch()

    first = build_repository_manifest(workspace(root))
    second = build_repository_manifest(workspace(root))

    assert first.canonical_json() == second.canonical_json()
    assert [item.file_identity.value for item in first.files] == ["a/first.java", "z/last.rs"]


def formatted_exception(error: BaseException) -> str:
    return "".join(traceback.format_exception(type(error), error, error.__traceback__))


@pytest.mark.parametrize("failing", ["open", "scandir", "fdopen"])
def test_filesystem_failures_do_not_leak_host_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failing: str
) -> None:
    root = tmp_path / "source"
    root.mkdir()
    (root / "main.py").write_text("pass\n")

    def raising(*_args: object, **_kwargs: object):
        raise OSError(13, "Permission denied", str(root))

    monkeypatch.setattr(indexing.os, failing, raising)

    with pytest.raises(RepositoryIndexingError) as raised:
        build_repository_manifest(workspace(root))

    report = formatted_exception(raised.value)
    assert str(root) not in report
    assert str(tmp_path) not in report
    assert "Permission denied" not in report
    assert raised.value.__cause__ is None
    assert raised.value.__suppress_context__


def corrupt_nth_fstat(
    monkeypatch: pytest.MonkeyPatch, target: int, *, replacement_mode: int | None = None
) -> None:
    """Simulate a replaced object by returning a foreign identity for one fstat call."""

    real_fstat = os.fstat
    counter = itertools.count(1)

    def fake_fstat(fd: int):
        result = real_fstat(fd)
        if next(counter) != target:
            return result
        return SimpleNamespace(
            st_dev=result.st_dev,
            st_ino=result.st_ino if replacement_mode is not None else result.st_ino + 1,
            st_mode=replacement_mode if replacement_mode is not None else result.st_mode,
        )

    monkeypatch.setattr(indexing.os, "fstat", fake_fstat)


def test_root_replaced_between_stat_and_open_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "source"
    root.mkdir()
    (root / "main.py").write_text("pass\n")
    corrupt_nth_fstat(monkeypatch, 1)

    with pytest.raises(RepositoryIndexingError) as raised:
        build_repository_manifest(workspace(root))

    assert raised.value.code is IndexingErrorCode.SOURCE_CHANGED
    assert str(root) not in str(raised.value)


def test_child_directory_replaced_between_stat_and_open_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "source"
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "main.py").write_text("pass\n")
    corrupt_nth_fstat(monkeypatch, 2)

    with pytest.raises(RepositoryIndexingError) as raised:
        build_repository_manifest(workspace(root))

    assert raised.value.code is IndexingErrorCode.SOURCE_CHANGED


def test_regular_file_replaced_between_stat_and_open_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "source"
    root.mkdir()
    (root / "main.py").write_text("pass\n")
    corrupt_nth_fstat(monkeypatch, 2)

    with pytest.raises(RepositoryIndexingError) as raised:
        build_repository_manifest(workspace(root))

    assert raised.value.code is IndexingErrorCode.SOURCE_CHANGED


def test_file_type_change_with_same_inode_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "source"
    root.mkdir()
    (root / "main.py").write_text("pass\n")
    corrupt_nth_fstat(monkeypatch, 2, replacement_mode=stat.S_IFDIR | 0o755)

    with pytest.raises(RepositoryIndexingError) as raised:
        build_repository_manifest(workspace(root))

    assert raised.value.code is IndexingErrorCode.SOURCE_CHANGED
