"""Focused tests for the Workflow-owned repository workspace descriptor."""

from __future__ import annotations

import ast
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

from app.retrieval.localisation import RepositoryIdentity, RevisionIdentity
from app.workflow.repository_workspace import (
    PreparedRepositoryWorkspace,
    RepositoryWorkspaceError,
    WorkspaceMode,
)

REPO_A = RepositoryIdentity("org/repo-a")
REPO_B = RepositoryIdentity("org/repo-b")
REVISION_A = RevisionIdentity("a" * 40)
REVISION_B = RevisionIdentity("b" * 40)
ROOT_A = PurePosixPath("/workspaces/a")
ROOT_B = PurePosixPath("/workspaces/b")
PRODUCTION_MODULE_PATH = (
    Path(__file__).resolve().parents[2] / "apps/api/app/workflow/repository_workspace.py"
)


def _make(**overrides: object) -> PreparedRepositoryWorkspace:
    values: dict[str, object] = {
        "repository_identity": REPO_A,
        "revision_identity": REVISION_A,
        "workspace_root": ROOT_A,
        "workspace_mode": WorkspaceMode.READ_ONLY,
    }
    values.update(overrides)
    return PreparedRepositoryWorkspace(**values)


def test_valid_workspace_with_real_rag_identities() -> None:
    workspace = _make()
    assert workspace.repository_identity == REPO_A
    assert workspace.revision_identity == REVISION_A


def test_repository_identity_preserved_exactly() -> None:
    workspace = _make(repository_identity=REPO_B)
    assert workspace.repository_identity is REPO_B


def test_revision_identity_preserved_exactly() -> None:
    workspace = _make(revision_identity=REVISION_B)
    assert workspace.revision_identity is REVISION_B


def test_workspace_root_preserved_exactly() -> None:
    workspace = _make(workspace_root=ROOT_B)
    assert workspace.workspace_root is ROOT_B


def test_pure_windows_root_preserved_exactly() -> None:
    windows_root = PureWindowsPath("C:\\workspaces\\a")
    workspace = _make(workspace_root=windows_root)
    assert workspace.workspace_root is windows_root


def test_concrete_path_root_accepted_when_absolute() -> None:
    concrete_root = Path("/workspaces/a")
    workspace = _make(workspace_root=concrete_root)
    assert workspace.workspace_root is concrete_root


def test_read_only_mode() -> None:
    workspace = _make(workspace_mode=WorkspaceMode.READ_ONLY)
    assert workspace.workspace_mode is WorkspaceMode.READ_ONLY


def test_disposable_mode() -> None:
    workspace = _make(workspace_mode=WorkspaceMode.DISPOSABLE)
    assert workspace.workspace_mode is WorkspaceMode.DISPOSABLE


def test_no_default_or_implicit_cwd() -> None:
    import inspect

    signature = inspect.signature(PreparedRepositoryWorkspace)
    for name in ("repository_identity", "revision_identity", "workspace_root", "workspace_mode"):
        assert signature.parameters[name].default is inspect.Parameter.empty


def test_relative_root_rejected() -> None:
    with pytest.raises(RepositoryWorkspaceError):
        _make(workspace_root=PurePosixPath("relative/path"))


def test_relative_root_rejected_for_str() -> None:
    with pytest.raises(RepositoryWorkspaceError):
        _make(workspace_root="relative/path")


def test_absolute_root_rejected_for_str() -> None:
    with pytest.raises(RepositoryWorkspaceError):
        _make(workspace_root="/workspaces/a")


def test_no_string_to_path_coercion() -> None:
    source = PRODUCTION_MODULE_PATH.read_text()
    assert "PurePosixPath(value)" not in source
    assert "PureWindowsPath(value)" not in source
    assert "Path(value)" not in source


@pytest.mark.parametrize(
    "root",
    [
        PurePosixPath("."),
        PurePosixPath("/workspaces/../a"),
        123,
        None,
    ],
)
def test_malformed_or_ambiguous_root_rejected(root: object) -> None:
    with pytest.raises(RepositoryWorkspaceError):
        _make(workspace_root=root)


def test_windows_relative_root_rejected() -> None:
    with pytest.raises(RepositoryWorkspaceError):
        _make(workspace_root=PureWindowsPath("relative\\path"))


def test_no_head_inference() -> None:
    source = PRODUCTION_MODULE_PATH.read_text()
    assert "HEAD" not in source
    assert "head" not in source.lower()


def test_no_branch_name_inference() -> None:
    source = PRODUCTION_MODULE_PATH.read_text()
    assert "branch" not in source.lower()


def test_empty_repository_identity_fails_at_rag_owner_boundary() -> None:
    with pytest.raises(Exception):
        RepositoryIdentity("")


def test_malformed_revision_identity_fails_at_rag_owner_boundary() -> None:
    with pytest.raises(Exception):
        RevisionIdentity("not-a-valid-revision")


def test_empty_revision_identity_fails_at_rag_owner_boundary() -> None:
    with pytest.raises(Exception):
        RevisionIdentity("")


def test_descriptor_is_immutable() -> None:
    workspace = _make()
    with pytest.raises(Exception):
        workspace.repository_identity = REPO_B  # type: ignore[misc]


def test_deterministic_equality_for_equivalent_values() -> None:
    assert _make() == _make()


def test_differing_repository_identity_differs() -> None:
    assert _make() != _make(repository_identity=REPO_B)


def test_differing_revision_differs() -> None:
    assert _make() != _make(revision_identity=REVISION_B)


def test_differing_root_differs() -> None:
    assert _make() != _make(workspace_root=ROOT_B)


def test_differing_workspace_mode_differs() -> None:
    assert _make() != _make(workspace_mode=WorkspaceMode.DISPOSABLE)


def test_none_repository_identity_fails_closed() -> None:
    with pytest.raises(RepositoryWorkspaceError):
        _make(repository_identity=None)


def test_none_revision_identity_fails_closed() -> None:
    with pytest.raises(RepositoryWorkspaceError):
        _make(revision_identity=None)


def test_none_workspace_mode_fails_closed() -> None:
    with pytest.raises(RepositoryWorkspaceError):
        _make(workspace_mode=None)


def test_no_credential_fields() -> None:
    fields = set(PreparedRepositoryWorkspace.__dataclass_fields__)
    forbidden_substrings = ("token", "secret", "credential", "password", "auth", "key")
    for field in fields:
        lowered = field.lower()
        assert not any(term in lowered for term in forbidden_substrings)


def test_no_raw_source_byte_field() -> None:
    fields = set(PreparedRepositoryWorkspace.__dataclass_fields__)
    forbidden = {"bytes", "content", "manifest", "files", "payload"}
    assert fields.isdisjoint(forbidden)


def test_no_identifier_generation() -> None:
    source = PRODUCTION_MODULE_PATH.read_text()
    assert "uuid" not in source.lower()


def test_no_network_or_provider_assumptions() -> None:
    source = PRODUCTION_MODULE_PATH.read_text()
    for term in ("socket", "requests", "httpx", "urllib", "subprocess", "os.system"):
        assert term not in source


def test_no_execution_dependency() -> None:
    source = PRODUCTION_MODULE_PATH.read_text()
    assert "ExecutionCommand" not in source
    assert "ExecutionResult" not in source


def test_no_rag_indexing_behavior() -> None:
    source = PRODUCTION_MODULE_PATH.read_text()
    for term in ("glob", "rglob", "iterdir", ".resolve(", ".exists(", ".is_dir("):
        assert term not in source


def test_production_module_does_not_import_app_retrieval() -> None:
    tree = ast.parse(PRODUCTION_MODULE_PATH.read_text())
    imported_modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.append(node.module)
    forbidden_prefixes = (
        "app.retrieval",
        "app.worker",
        "app.api",
        "app.db",
        "app.queue",
        "app.evidence",
    )
    for module in imported_modules:
        assert not any(
            module == prefix or module.startswith(prefix + ".") for prefix in forbidden_prefixes
        )


def test_production_module_path_is_cwd_independent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    assert PRODUCTION_MODULE_PATH.name == "repository_workspace.py"
    assert PRODUCTION_MODULE_PATH.parent.name == "workflow"
    monkeypatch.chdir(tmp_path)
    assert "class PreparedRepositoryWorkspace" in PRODUCTION_MODULE_PATH.read_text()


def test_module_imports_independently() -> None:
    module_name = "app.workflow.repository_workspace"
    sys.modules.pop(module_name, None)
    import importlib

    module = importlib.import_module(module_name)
    assert hasattr(module, "PreparedRepositoryWorkspace")
    assert hasattr(module, "WorkspaceMode")


def test_public_semantics_are_explicit() -> None:
    workspace = _make()
    assert workspace.repository_identity is REPO_A
    assert workspace.revision_identity is REVISION_A
    assert workspace.workspace_root == ROOT_A
    assert workspace.workspace_mode is WorkspaceMode.READ_ONLY
