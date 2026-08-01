"""DB-002 database test fixtures.

Schema work runs as the DDL-capable migration role; every DML assertion runs as
the test role through `TEST_DATABASE_URL`, exactly as CONTRACT-DEPLOY-001
defines those boundaries. No new environment variable is introduced: the
test-database migration URL is the existing migration role pointed at the
existing isolated test database, which `testgap_migrator` already owns.
"""

import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session

from app.db.config import validate_test_database_url
from app.db.models import (
    AuthSubject,
    GitHubInstallation,
    Repository,
    RepositoryAccess,
    User,
)

ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = ROOT / "apps/api/alembic.ini"


def _test_database_url() -> str:
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is unavailable")
    return validate_test_database_url(url, os.getenv("DATABASE_URL"))


def _test_migration_url(test_url: str) -> str:
    migration_url = os.getenv("MIGRATION_DATABASE_URL")
    if not migration_url:
        pytest.skip("MIGRATION_DATABASE_URL is unavailable")
    return (
        make_url(migration_url)
        .set(database=make_url(test_url).database)
        .render_as_string(hide_password=False)
    )


@pytest.fixture(scope="session")
def alembic_config() -> Iterator[Config]:
    """Alembic configured to target the isolated test database.

    `alembic/env.py` resolves its URL from the environment, so the test
    migration URL is exported for the duration of the session and restored
    afterwards.
    """
    migration_url = _test_migration_url(_test_database_url())
    previous = os.environ.get("MIGRATION_DATABASE_URL")
    os.environ["MIGRATION_DATABASE_URL"] = migration_url
    try:
        yield Config(str(ALEMBIC_INI))
    finally:
        if previous is None:
            del os.environ["MIGRATION_DATABASE_URL"]
        else:
            os.environ["MIGRATION_DATABASE_URL"] = previous


@pytest.fixture(scope="session")
def migrated_engine(alembic_config: Config) -> Iterator[Engine]:
    """Test database upgraded from empty to head, connected as the DML role."""
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")
    engine = create_engine(_test_database_url())
    try:
        yield engine
    finally:
        engine.dispose()
        command.downgrade(alembic_config, "base")


@pytest.fixture
def session(migrated_engine: Engine) -> Iterator[Session]:
    """One session per test inside a transaction that is always rolled back."""
    with migrated_engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
            yield db
        transaction.rollback()


@pytest.fixture
def fixture_two(session: Session) -> SimpleNamespace:
    """The accepted Auth acceptance fixture.

    Two users with active subjects, two installations, two repositories, and one
    active grant each: User A + Installation A + Repository A, and
    User B + Installation B + Repository B.
    """
    now = datetime.now(UTC)
    user_a, user_b = User(), User()
    subject_a = AuthSubject(
        user=user_a, issuer="https://issuer.example/", subject="Subject-A"
    )
    subject_b = AuthSubject(
        user=user_b, issuer="https://issuer.example/", subject="Subject-B"
    )
    installation_a = GitHubInstallation(
        github_installation_id=1001, github_account_id=2001, account_type="ORGANIZATION"
    )
    installation_b = GitHubInstallation(
        github_installation_id=1002, github_account_id=2002, account_type="USER"
    )
    repository_a = Repository(github_repository_id=3001)
    repository_b = Repository(github_repository_id=3002)
    grant_a = RepositoryAccess(
        user=user_a,
        installation=installation_a,
        repository=repository_a,
        expires_at=now + timedelta(days=1),
    )
    grant_b = RepositoryAccess(
        user=user_b, installation=installation_b, repository=repository_b
    )
    session.add_all(
        [
            subject_a,
            subject_b,
            installation_a,
            installation_b,
            repository_a,
            repository_b,
            grant_a,
            grant_b,
        ]
    )
    session.flush()
    return SimpleNamespace(
        user_a=user_a,
        user_b=user_b,
        subject_a=subject_a,
        subject_b=subject_b,
        installation_a=installation_a,
        installation_b=installation_b,
        repository_a=repository_a,
        repository_b=repository_b,
        grant_a=grant_a,
        grant_b=grant_b,
    )
