from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.api.router import api_v1_router


@pytest.fixture(autouse=True)
def valid_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in {
        "DATABASE_URL": "postgresql+psycopg://user:password@localhost/testgap",
        "AUTH_JWT_ISSUER": "https://issuer.test/auth/v1",
        "AUTH_JWT_AUDIENCE": "authenticated",
        "AUTH_JWKS_URL": "https://testserver/jwks.json",
        "DASHBOARD_ORIGIN": "http://dashboard.test",
    }.items():
        monkeypatch.setenv(name, value)


@contextmanager
def route(path: str, endpoint) -> Iterator[None]:  # type: ignore[no-untyped-def]
    main.app.get(path)(endpoint)
    added = main.app.router.routes[-1]
    try:
        yield
    finally:
        main.app.router.routes.remove(added)


def test_health_is_process_only(monkeypatch: pytest.MonkeyPatch) -> None:
    def dependency_access_is_a_failure(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("health accessed a dependency")

    monkeypatch.setattr(main, "Settings", dependency_access_is_a_failure)
    monkeypatch.setattr(main, "create_database_engine", dependency_access_is_a_failure)
    monkeypatch.setattr(main, "check_database_connection", dependency_access_is_a_failure)

    with TestClient(main.app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize(
    ("database_result", "status_code", "body"),
    [
        (True, 200, {"status": "ready"}),
        (RuntimeError("unavailable"), 503, {"status": "not_ready"}),
    ],
)
def test_readiness_uses_controlled_database_check(
    monkeypatch: pytest.MonkeyPatch,
    database_result: bool | Exception,
    status_code: int,
    body: dict[str, str],
) -> None:
    fake_engine = type("Engine", (), {"dispose": lambda self: None})()
    monkeypatch.setattr(main, "create_database_engine", lambda _: fake_engine)

    def check_database(candidate) -> bool:  # type: ignore[no-untyped-def]
        assert candidate is fake_engine
        if isinstance(database_result, Exception):
            raise database_result
        return database_result

    monkeypatch.setattr(main, "check_database_connection", check_database)

    with TestClient(main.app) as client:
        response = client.get("/readyz")

    assert response.status_code == status_code
    assert response.json() == body
    assert "unavailable" not in response.text


def test_missing_critical_configuration_fails_readiness_without_import_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for variable in (
        "DATABASE_URL",
        "AUTH_JWT_ISSUER",
        "AUTH_JWT_AUDIENCE",
        "AUTH_JWKS_URL",
        "DASHBOARD_ORIGIN",
    ):
        monkeypatch.delenv(variable, raising=False)

    with TestClient(main.app) as client:
        response = client.get("/readyz")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}


def test_valid_request_and_correlation_ids_are_effective() -> None:
    with TestClient(main.app) as client:
        response = client.get(
            "/healthz",
            headers={
                "X-Request-ID": "request.valid-1",
                "X-Correlation-ID": "correlation:valid_1",
            },
        )

    assert response.headers["x-request-id"] == "request.valid-1"
    assert response.headers["x-correlation-id"] == "correlation:valid_1"


@pytest.mark.parametrize("invalid", ["", "contains space", "x" * 129])
def test_invalid_request_and_correlation_ids_are_replaced(invalid: str) -> None:
    with TestClient(main.app) as client:
        response = client.get(
            "/healthz",
            headers={"X-Request-ID": invalid, "X-Correlation-ID": invalid},
        )

    assert response.headers["x-request-id"] != invalid
    assert response.headers["x-correlation-id"] != invalid
    assert len(response.headers["x-request-id"]) == 32
    assert len(response.headers["x-correlation-id"]) == 32


def test_non_ascii_id_is_invalid() -> None:
    assert main._effective_id("é") != "é"


def test_correlation_defaults_to_effective_request_id() -> None:
    with TestClient(main.app) as client:
        response = client.get(
            "/healthz", headers={"X-Request-ID": "request.default-correlation"}
        )

    assert response.headers["x-correlation-id"] == response.headers["x-request-id"]


def test_generic_exception_maps_to_safe_error_envelope() -> None:
    async def fail() -> None:
        raise RuntimeError("secret /internal/path")

    with route("/__test__/failure", fail), TestClient(main.app) as client:
        response = client.get(
            "/__test__/failure", headers={"X-Request-ID": "request.failure-1"}
        )

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred.",
            "request_id": "request.failure-1",
            "details": {},
        }
    }
    assert "secret" not in response.text
    assert "detail" not in response.json()


@pytest.mark.parametrize("path", ["/missing", "/api/v1/missing"])
def test_unknown_paths_return_safe_error_envelope(path: str) -> None:
    with TestClient(main.app) as client:
        response = client.get(
            path,
            headers={
                "X-Request-ID": "request.not-found",
                "X-Correlation-ID": "correlation.not-found",
            },
        )

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "RESOURCE_NOT_FOUND",
            "message": "Resource not found.",
            "request_id": "request.not-found",
            "details": {},
        }
    }
    assert response.headers["x-request-id"] == "request.not-found"
    assert response.headers["x-correlation-id"] == "correlation.not-found"
    assert "detail" not in response.json()


def test_unsupported_method_returns_safe_error_envelope() -> None:
    with TestClient(main.app) as client:
        response = client.post(
            "/healthz",
            headers={
                "X-Request-ID": "request.method",
                "X-Correlation-ID": "correlation.method",
            },
        )

    assert response.status_code == 405
    assert response.json() == {
        "error": {
            "code": "METHOD_NOT_ALLOWED",
            "message": "Method not allowed.",
            "request_id": "request.method",
            "details": {},
        }
    }
    assert response.headers["x-request-id"] == "request.method"
    assert response.headers["x-correlation-id"] == "correlation.method"
    assert "detail" not in response.json()


def test_request_validation_returns_safe_error_envelope() -> None:
    async def validate(limit: int) -> dict[str, int]:
        return {"limit": limit}

    with route("/__test__/validation", validate), TestClient(main.app) as client:
        response = client.get(
            "/__test__/validation",
            params={"limit": "raw-secret-input"},
            headers={
                "X-Request-ID": "request.validation",
                "X-Correlation-ID": "correlation.validation",
            },
        )

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "VALIDATION_FAILED",
            "message": "Request validation failed.",
            "request_id": "request.validation",
            "details": {},
        }
    }
    assert response.headers["x-request-id"] == "request.validation"
    assert response.headers["x-correlation-id"] == "correlation.validation"
    assert "raw-secret-input" not in response.text
    assert "detail" not in response.json()


def test_versioned_router_exists_without_business_routes() -> None:
    assert api_v1_router.prefix == "/api/v1"
    assert not [
        path for path in main.app.openapi()["paths"] if path.startswith("/api/v1")
    ]
