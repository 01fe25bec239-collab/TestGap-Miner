import pytest
from pydantic import ValidationError

from app.settings import Settings


def test_database_url_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:password@localhost/testgap")

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
    assert set(Settings.model_fields) == {"database_url"}
