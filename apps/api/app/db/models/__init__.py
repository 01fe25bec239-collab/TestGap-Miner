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
from app.db.models.workflow import (
    Run,
    RunEvent,
    RunRequest,
    WorkflowStep,
    WorkflowStepAttempt,
)

__all__ = [
    "AuthSubject",
    "Base",
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
