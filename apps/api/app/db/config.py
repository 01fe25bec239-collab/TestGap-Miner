import os
from collections.abc import Mapping

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class DatabaseConfigurationError(ValueError):
    """Safe database configuration failure."""


def validate_database_url(value: str | None, variable: str = "DATABASE_URL") -> str:
    if not value:
        raise DatabaseConfigurationError(f"{variable} is required")
    try:
        drivername = make_url(value).drivername
    except (ArgumentError, TypeError):
        raise DatabaseConfigurationError(
            f"{variable} must be a valid postgresql+psycopg URL"
        ) from None
    if drivername != "postgresql+psycopg":
        raise DatabaseConfigurationError(
            f"{variable} must use the postgresql+psycopg scheme"
        )
    return value


def resolve_runtime_database_url(database_url: str | None = None) -> str:
    return validate_database_url(
        os.getenv("DATABASE_URL") if database_url is None else database_url
    )


def validate_test_database_url(
    test_database_url: str | None = None,
    database_url: str | None = None,
) -> str:
    value = validate_database_url(
        os.getenv("TEST_DATABASE_URL")
        if test_database_url is None
        else test_database_url,
        "TEST_DATABASE_URL",
    )
    database_name = make_url(value).database
    if not database_name or not database_name.endswith("_test"):
        raise DatabaseConfigurationError(
            "TEST_DATABASE_URL database name must end with _test"
        )
    runtime_value = (
        os.getenv("DATABASE_URL") if database_url is None else database_url
    )
    if runtime_value and value == runtime_value:
        raise DatabaseConfigurationError(
            "TEST_DATABASE_URL must differ from DATABASE_URL"
        )
    return value


def resolve_migration_database_url(
    environ: Mapping[str, str] | None = None,
) -> str:
    values = os.environ if environ is None else environ
    migration_url = values.get("MIGRATION_DATABASE_URL")
    if migration_url:
        return validate_database_url(migration_url, "MIGRATION_DATABASE_URL")
    if values.get("TESTGAP_RUNTIME") == "local":
        return validate_database_url(values.get("DATABASE_URL"))
    raise DatabaseConfigurationError(
        "MIGRATION_DATABASE_URL is required outside local runtime"
    )
