import pytest

from app.db.config import (
    DatabaseConfigurationError,
    resolve_migration_database_url,
    resolve_runtime_database_url,
    validate_database_url,
    validate_test_database_url,
)

URL = "postgresql+psycopg://user:top-secret@localhost/testgap"
TEST_URL = f"{URL}_test"


def test_runtime_url_accepts_psycopg_and_rejects_missing_or_other_schemes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert validate_database_url(URL) == URL
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(DatabaseConfigurationError, match="DATABASE_URL is required"):
        resolve_runtime_database_url()
    with pytest.raises(DatabaseConfigurationError, match="postgresql\\+psycopg"):
        validate_database_url("sqlite:///test.db")


def test_runtime_url_errors_do_not_expose_secrets() -> None:
    secret = "do-not-expose"
    with pytest.raises(DatabaseConfigurationError) as error:
        validate_database_url(f"not-a-url:{secret}")
    assert secret not in str(error.value)


def test_migration_url_precedence_and_local_fallback() -> None:
    migration = URL.replace("user", "migrator")
    assert (
        resolve_migration_database_url(
            {
                "MIGRATION_DATABASE_URL": migration,
                "DATABASE_URL": URL,
                "TESTGAP_RUNTIME": "local",
            }
        )
        == migration
    )
    assert (
        resolve_migration_database_url(
            {"DATABASE_URL": URL, "TESTGAP_RUNTIME": "local"}
        )
        == URL
    )


@pytest.mark.parametrize("runtime", ["ci", "", None])
def test_migration_runtime_fallback_fails_closed(runtime: str | None) -> None:
    values = {"DATABASE_URL": URL}
    if runtime is not None:
        values["TESTGAP_RUNTIME"] = runtime
    with pytest.raises(DatabaseConfigurationError) as error:
        resolve_migration_database_url(values)
    assert "top-secret" not in str(error.value)


def test_missing_migration_urls_fail_closed() -> None:
    with pytest.raises(DatabaseConfigurationError):
        resolve_migration_database_url({"TESTGAP_RUNTIME": "local"})


def test_test_database_url_accepts_safe_explicit_values() -> None:
    assert validate_test_database_url(TEST_URL, URL) == TEST_URL


@pytest.mark.parametrize(
    ("test_url", "database_url"),
    [
        ("", URL),
        ("sqlite:///testgap_test", URL),
        (URL, None),
        (TEST_URL, TEST_URL),
        (
            "postgresql+psycopg://user:do-not-expose@production/testgap",
            URL,
        ),
    ],
    ids=["missing", "non-postgresql", "missing-suffix", "same-url", "production-like"],
)
def test_test_database_url_rejects_unsafe_values_without_exposing_passwords(
    test_url: str,
    database_url: str | None,
) -> None:
    with pytest.raises(DatabaseConfigurationError) as error:
        validate_test_database_url(test_url, database_url)
    assert "top-secret" not in str(error.value)
    assert "do-not-expose" not in str(error.value)
