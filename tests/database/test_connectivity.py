import os

import pytest
from sqlalchemy import create_engine

from app.db.config import validate_test_database_url
from app.db.engine import check_database_connection, create_database_engine


def _required_url(name: str) -> str:
    value = os.getenv(name)
    if not value:
        pytest.skip(f"{name} is unavailable")
    return value


def test_runtime_database_connectivity() -> None:
    engine = create_database_engine(_required_url("DATABASE_URL"))
    try:
        assert check_database_connection(engine)
    finally:
        engine.dispose()


def test_test_database_connectivity() -> None:
    test_url = validate_test_database_url(
        _required_url("TEST_DATABASE_URL"),
        os.getenv("DATABASE_URL"),
    )
    engine = create_engine(test_url, pool_pre_ping=True)
    try:
        assert check_database_connection(engine)
    finally:
        engine.dispose()


def test_migration_database_connectivity() -> None:
    engine = create_database_engine(_required_url("MIGRATION_DATABASE_URL"))
    try:
        assert check_database_connection(engine)
    finally:
        engine.dispose()
