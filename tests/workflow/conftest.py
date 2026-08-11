"""Workflow-local migrated PostgreSQL fixtures."""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url

from app.db.config import validate_test_database_url


ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = ROOT / "apps/api/alembic.ini"


def _test_url() -> str:
    value = os.getenv("TEST_DATABASE_URL")
    if not value:
        pytest.skip("TEST_DATABASE_URL is unavailable")
    return validate_test_database_url(value, os.getenv("DATABASE_URL"))


@pytest.fixture(scope="session")
def workflow_pg_engine() -> Iterator[Engine]:
    test_url = _test_url()
    migration_url = os.getenv("MIGRATION_DATABASE_URL")
    if not migration_url:
        pytest.skip("MIGRATION_DATABASE_URL is unavailable")
    migration_url = (
        make_url(migration_url)
        .set(database=make_url(test_url).database)
        .render_as_string(hide_password=False)
    )
    previous = os.environ.get("MIGRATION_DATABASE_URL")
    os.environ["MIGRATION_DATABASE_URL"] = migration_url
    config = Config(str(ALEMBIC_INI))
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    engine = create_engine(test_url)
    try:
        yield engine
    finally:
        engine.dispose()
        command.downgrade(config, "base")
        if previous is None:
            del os.environ["MIGRATION_DATABASE_URL"]
        else:
            os.environ["MIGRATION_DATABASE_URL"] = previous
