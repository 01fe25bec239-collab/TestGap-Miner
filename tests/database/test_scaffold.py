import importlib
import sys
from unittest.mock import Mock

import pytest
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.db.dependencies import get_db_session
from app.db.engine import (
    DatabaseConnectivityError,
    check_database_connection,
    create_database_engine,
)
from app.db.session import create_session_factory

URL = "postgresql+psycopg://user:password@localhost/testgap"


def test_import_does_not_create_an_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    create_engine_mock = Mock()
    monkeypatch.setattr(sqlalchemy, "create_engine", create_engine_mock)
    sys.modules.pop("app.db.engine", None)
    importlib.import_module("app.db.engine")
    create_engine_mock.assert_not_called()


def test_engine_and_session_factory_are_synchronous() -> None:
    engine = create_database_engine(URL)
    assert isinstance(engine, Engine)
    assert engine.pool._pre_ping is True
    engine.dispose()

    sqlite_engine = create_engine("sqlite://")
    factory = create_session_factory(sqlite_engine)
    session = factory()
    assert isinstance(session, Session)
    assert session.autoflush is False
    assert session.expire_on_commit is False
    session.close()
    sqlite_engine.dispose()


def test_connectivity_failure_does_not_expose_credentials() -> None:
    secret = "do-not-expose"
    engine = Mock(spec=Engine)
    engine.connect.side_effect = OperationalError(
        "connect", {}, RuntimeError(secret)
    )
    with pytest.raises(DatabaseConnectivityError) as error:
        check_database_connection(engine)
    assert secret not in str(error.value)


def test_successful_dependency_closes_without_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = Mock(spec=Session)
    monkeypatch.setattr(
        "app.db.dependencies._runtime_session_factory",
        lambda: Mock(return_value=session),
    )
    dependency = get_db_session()
    assert next(dependency) is session
    with pytest.raises(StopIteration):
        next(dependency)
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_called_once_with()


def test_dependency_rolls_back_closes_and_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = Mock(spec=Session)
    monkeypatch.setattr(
        "app.db.dependencies._runtime_session_factory",
        lambda: Mock(return_value=session),
    )
    dependency = get_db_session()
    next(dependency)
    with pytest.raises(RuntimeError, match="request failed"):
        dependency.throw(RuntimeError("request failed"))
    session.rollback.assert_called_once_with()
    session.close.assert_called_once_with()
