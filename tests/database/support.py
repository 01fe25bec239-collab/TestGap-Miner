"""Shared DB-002 test constants and helpers.

`tests` is not an importable package under the Backend-owned pytest
configuration, so shared helpers live in this sibling module rather than being
imported from `conftest`.
"""

import re
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.db.models import (
    GitHubInstallation,
    Repository,
    RepositoryAccess,
    Run,
    RunRequest,
    User,
)
from app.db.models.workflow import FAILURE_CODES, TERMINAL_RUN_STATES

DB_002_TABLES = frozenset(
    {
        "users",
        "auth_subjects",
        "github_installations",
        "repositories",
        "repository_access",
        "run_requests",
        "runs",
    }
)

# DB-003 and later domains that must not exist yet.
FORBIDDEN_TABLES = frozenset(
    {
        "workflow_steps",
        "steps",
        "workflow_step_attempts",
        "step_attempts",
        "attempts",
        "run_events",
        "events",
        "event_sequences",
        "run_transitions",
        "checkpoints",
        "context_selections",
        "candidate_patches",
        "patch_contents",
        "execution_attempts",
        "execution_evidence",
        "artifacts",
        "artefacts",
        "publications",
        "human_decisions",
        "benchmark_cases",
        "evaluation_runs",
        "metric_results",
        "audit_logs",
        "security_events",
        "model_usage",
        "notifications",
        "organizations",
        "tenants",
        "roles",
        "permissions",
        "role_permissions",
        "user_roles",
        "api_keys",
        "embeddings",
        "billing_accounts",
        "invoices",
    }
)

# Names that would indicate a credential or raw secret reached a domain table.
SECRET_NAME_PATTERN = re.compile(
    r"password|passwd|secret|token|private_key|api_key|credential|"
    r"authorization_header|session_key|signing_key|jwt",
    re.IGNORECASE,
)


def assert_rejected(session: Session, *objects: object) -> None:
    """Assert the database refuses these rows. Must be a test's final action:
    the failed flush leaves the surrounding transaction unusable."""
    session.add_all(objects)
    with pytest.raises(DBAPIError):
        session.flush()


def active_grant(
    session: Session,
    user: User,
    installation: GitHubInstallation,
    repository: Repository,
) -> RepositoryAccess | None:
    """Exact-tuple authorization lookup: user + installation + repository."""
    return session.scalars(
        select(RepositoryAccess).where(
            RepositoryAccess.user_id == user.id,
            RepositoryAccess.installation_id == installation.id,
            RepositoryAccess.repository_id == repository.id,
            RepositoryAccess.status == "ACTIVE",
        )
    ).one_or_none()


def make_run_request(**overrides: object) -> RunRequest:
    """A valid BENCHMARK request with a unique idempotency key."""
    unique = uuid.uuid4().hex
    values: dict[str, object] = {
        "request_kind": "BENCHMARK",
        "idempotency_key": unique,
        "idempotency_key_version": 1,
        "request_fingerprint": unique,
        "benchmark_project_id": "Lang",
        "benchmark_bug_id": "1",
        "configuration_version": "cfg-1",
        "model_id": "claude-opus-5",
        "prompt_template_version": "prompt-1",
    }
    values.update(overrides)
    return RunRequest(**values)


def make_run(
    run_request: RunRequest, state: str = "RECEIVED", **overrides: object
) -> Run:
    """A run projection consistent with `state`'s contract requirements."""
    values: dict[str, object] = {
        "run_request": run_request,
        "state": state,
        "contract_version": "1.0.0-draft.1",
        "review_required": True,
        "retry_limit": 3,
    }
    if state in TERMINAL_RUN_STATES:
        values["terminal_at"] = datetime.now(UTC)
        values["terminal_actor_type"] = "SYSTEM"
        values["terminal_actor_id"] = "workflow-runtime"
    if state in FAILURE_CODES:
        values["failure_code"] = FAILURE_CODES[state][0]
    if state == "ABSTAINED":
        values["abstention_code"] = "EVIDENCE_INCONCLUSIVE"
    if state == "CANCELLED":
        values["cancellation_code"] = "USER_REQUESTED"
    values.update(overrides)
    return Run(**values)
