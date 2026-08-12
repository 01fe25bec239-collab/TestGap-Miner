import pytest
from pydantic import ValidationError

from app.settings import Settings


@pytest.fixture(autouse=True)
def authentication_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:password@localhost/testgap")
    monkeypatch.setenv("AUTH_JWT_ISSUER", "https://issuer.test/auth/v1")
    monkeypatch.setenv("AUTH_JWT_AUDIENCE", "authenticated")
    monkeypatch.setenv("AUTH_JWKS_URL", "https://testserver/jwks.json")
    monkeypatch.setenv("DASHBOARD_ORIGIN", "http://dashboard.test")


def test_database_url_is_accepted() -> None:

    settings = Settings()

    assert "postgresql+psycopg" in settings.database_url.get_secret_value()
    assert "password" not in repr(settings)


@pytest.mark.parametrize(
    "database_url",
    [None, "postgresql://user:secret-password@localhost/testgap"],
)
def test_database_url_failures_are_redacted(
    monkeypatch: pytest.MonkeyPatch, database_url: str | None
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    if database_url is not None:
        monkeypatch.setenv("DATABASE_URL", database_url)

    with pytest.raises(ValidationError) as error:
        Settings()

    assert all(
        "secret-password" not in rendered
        for rendered in (str(error.value), repr(error.value), error.value.json())
    )


def test_settings_only_define_the_ordinary_database_url() -> None:
    assert set(Settings.model_fields) == {
        "database_url",
        "auth_jwt_issuer",
        "auth_jwt_audience",
        "auth_jwks_url",
        "dashboard_origin",
        "readiness_timeout_seconds",
    }


@pytest.mark.parametrize("timeout", ["0", "31"])
def test_readiness_timeout_is_bounded(
    monkeypatch: pytest.MonkeyPatch, timeout: str
) -> None:
    monkeypatch.setenv("READINESS_TIMEOUT_SECONDS", timeout)

    with pytest.raises(ValidationError):
        Settings()


@pytest.mark.parametrize(
    "jwks_url",
    [
        "http://localhost/keys",
        "http://127.0.0.1/keys",
        "http://testserver/keys",
        "http://jwks.example.test/keys",
    ],
)
def test_jwks_must_use_https(
    monkeypatch: pytest.MonkeyPatch, jwks_url: str
) -> None:
    monkeypatch.setenv("AUTH_JWKS_URL", jwks_url)

    with pytest.raises(ValidationError, match="AUTH_JWKS_URL must use HTTPS"):
        Settings()


def test_trailing_slash_issuer_is_rejected_without_normalization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTH_JWT_ISSUER", "https://issuer.test/auth/v1/")

    with pytest.raises(ValidationError, match="must not end with a slash"):
        Settings()
