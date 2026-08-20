"""Provider-neutral repository workspace/source binding descriptor.

Represents the Workflow-owned assertion that the source bytes visible beneath
one explicit workspace root are supplied by an upstream source/workspace
producer as the source tree for one exact repository identity and one exact
pinned revision.

This module does not crawl, index, verify, or materialize source bytes, and
does not perform any Git or filesystem inspection. Repository and revision
identity values are treated as opaque values owned and validated by their
producing component (for example RAG); this module must not import or
redefine that owner's identity semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import PurePosixPath, PureWindowsPath
from typing import Generic, TypeVar

RepositoryIdentityT = TypeVar("RepositoryIdentityT")
RevisionIdentityT = TypeVar("RevisionIdentityT")


class WorkspaceMode(Enum):
    """How a consumer is expected to treat the prepared workspace root."""

    READ_ONLY = "READ_ONLY"
    DISPOSABLE = "DISPOSABLE"


class RepositoryWorkspaceError(ValueError):
    """Fail-closed error for a structurally invalid workspace descriptor."""


def _require_identity(value: object, label: str) -> None:
    if value is None:
        raise RepositoryWorkspaceError(f"{label} must not be None")


def _require_absolute_root(value: object) -> PurePosixPath | PureWindowsPath:
    if isinstance(value, (PureWindowsPath, PurePosixPath)):
        root = value
    else:
        raise RepositoryWorkspaceError(
            "workspace_root must be a PurePosixPath or PureWindowsPath"
        )

    if not root.is_absolute():
        raise RepositoryWorkspaceError("workspace_root must be an absolute path")
    if ".." in root.parts:
        raise RepositoryWorkspaceError("workspace_root must not contain '..' segments")
    return root


def _require_workspace_mode(value: object) -> WorkspaceMode:
    if type(value) is not WorkspaceMode:
        raise RepositoryWorkspaceError("workspace_mode must be a WorkspaceMode value")
    return value


@dataclass(frozen=True, slots=True)
class PreparedRepositoryWorkspace(Generic[RepositoryIdentityT, RevisionIdentityT]):
    """Producer-side assertion binding a workspace root to a pinned revision.

    The bytes beneath ``workspace_root`` are asserted by the producer to be
    the source tree for exactly ``repository_identity`` at exactly
    ``revision_identity``. This descriptor does not prove that assertion.
    """

    repository_identity: RepositoryIdentityT
    revision_identity: RevisionIdentityT
    workspace_root: PurePosixPath | PureWindowsPath
    workspace_mode: WorkspaceMode

    def __post_init__(self) -> None:
        _require_identity(self.repository_identity, "repository_identity")
        _require_identity(self.revision_identity, "revision_identity")
        root = _require_absolute_root(self.workspace_root)
        object.__setattr__(self, "workspace_root", root)
        mode = _require_workspace_mode(self.workspace_mode)
        object.__setattr__(self, "workspace_mode", mode)
