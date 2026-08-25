"""Database models. Importing this package registers every table on the shared
MetaData used by Alembic autogenerate."""

from app.db.base import Base
from app.db.models.auth import (
    AuthSubject,
    GitHubInstallation,
    Repository,
    RepositoryAccess,
    User,
)
from app.db.models.context import ContextBundle, ContextBundleItem
from app.db.models.evidence import (
    ArtefactManifestMember,
    ArtefactManifestRecord,
    ArtefactReferenceRecord,
    CandidateChangedFile,
    CandidatePatchRecord,
    CandidateVersionRecord,
    ExecutionArtefactRole,
    ExecutionEvidenceRecord,
    ExecutionResourceObservation,
    ExecutionTestCaseResult,
)
from app.db.models.workflow import (
    Run,
    RunEvent,
    RunRequest,
    WorkflowStep,
    WorkflowStepAttempt,
)

__all__ = [
    "ArtefactManifestMember",
    "ArtefactManifestRecord",
    "ArtefactReferenceRecord",
    "AuthSubject",
    "Base",
    "CandidateChangedFile",
    "CandidatePatchRecord",
    "CandidateVersionRecord",
    "ContextBundle",
    "ContextBundleItem",
    "ExecutionArtefactRole",
    "ExecutionEvidenceRecord",
    "ExecutionResourceObservation",
    "ExecutionTestCaseResult",
    "GitHubInstallation",
    "Repository",
    "RepositoryAccess",
    "Run",
    "RunEvent",
    "RunRequest",
    "User",
    "WorkflowStep",
    "WorkflowStepAttempt",
]
