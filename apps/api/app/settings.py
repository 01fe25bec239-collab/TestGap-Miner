from pydantic import SecretStr, field_validator, model_validator
from pydantic.networks import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Ordinary API and worker runtime settings."""

    model_config = SettingsConfigDict(env_file=None, hide_input_in_errors=True)

    database_url: SecretStr

    @model_validator(mode="before")
    @classmethod
    def redact_database_url_input(cls, values: object) -> object:
        if isinstance(values, dict) and isinstance(values.get("database_url"), str):
            return {**values, "database_url": SecretStr(values["database_url"])}
        return values

    @field_validator("database_url", mode="after")
    @classmethod
    def require_psycopg_url(cls, value: SecretStr) -> SecretStr:
        try:
            url = PostgresDsn(value.get_secret_value())
        except ValueError:
            raise ValueError("DATABASE_URL must be a PostgreSQL psycopg URL") from None
        if url.scheme != "postgresql+psycopg":
            raise ValueError("DATABASE_URL must use the postgresql+psycopg scheme")
        return value
