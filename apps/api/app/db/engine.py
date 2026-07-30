from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.db.config import resolve_runtime_database_url


class DatabaseConnectivityError(RuntimeError):
    """Safe connectivity-check failure."""


def create_database_engine(database_url: str | None = None) -> Engine:
    return create_engine(
        resolve_runtime_database_url(database_url),
        pool_pre_ping=True,
    )


def check_database_connection(engine: Engine) -> bool:
    try:
        with engine.connect() as connection:
            if connection.execute(text("SELECT 1")).scalar_one() != 1:
                raise DatabaseConnectivityError(
                    "Database connectivity check returned an unexpected result"
                )
    except SQLAlchemyError:
        raise DatabaseConnectivityError("Database connectivity check failed") from None
    return True

