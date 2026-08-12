from urllib.parse import urlparse

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic.networks import AnyUrl, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Ordinary API and worker runtime settings."""

    model_config = SettingsConfigDict(env_file=None, hide_input_in_errors=True)

    database_url: SecretStr
    auth_jwt_issuer: str
    auth_jwt_audience: str
    auth_jwks_url: AnyUrl
    dashboard_origin: str
    readiness_timeout_seconds: float = Field(default=2.0, gt=0, le=30)

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

    @field_validator("auth_jwt_issuer")
    @classmethod
    def require_https_issuer(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("AUTH_JWT_ISSUER must be an HTTPS URL")
        if value.endswith("/"):
            raise ValueError("AUTH_JWT_ISSUER must not end with a slash")
        return value

    @field_validator("auth_jwks_url")
    @classmethod
    def require_safe_jwks_url(cls, value: AnyUrl) -> AnyUrl:
        if value.scheme != "https":
            raise ValueError("AUTH_JWKS_URL must use HTTPS")
        return value

    @field_validator("dashboard_origin")
    @classmethod
    def require_origin(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("DASHBOARD_ORIGIN must be an HTTP(S) origin")
        if parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment:
            raise ValueError("DASHBOARD_ORIGIN must not include a path, query, or fragment")
        return f"{parsed.scheme}://{parsed.netloc}"
