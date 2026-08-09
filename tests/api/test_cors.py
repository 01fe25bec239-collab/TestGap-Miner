from fastapi.testclient import TestClient

from app.main import app


def test_exact_origin_cors_allows_only_configured_origin(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:password@localhost/testgap")
    monkeypatch.setenv("AUTH_JWT_ISSUER", "https://issuer.test/auth/v1")
    monkeypatch.setenv("AUTH_JWT_AUDIENCE", "authenticated")
    monkeypatch.setenv("AUTH_JWKS_URL", "https://testserver/jwks.json")
    monkeypatch.setenv("DASHBOARD_ORIGIN", "https://dashboard.example.test")
    client = TestClient(app)

    approved = client.options(
        "/openapi.json",
        headers={"Origin": "https://dashboard.example.test", "Access-Control-Request-Method": "GET"},
    )
    rejected = client.options(
        "/openapi.json",
        headers={"Origin": "https://other.example.test", "Access-Control-Request-Method": "GET"},
    )
    rejected_request = client.get("/openapi.json", headers={"Origin": "https://other.example.test"})

    assert approved.status_code == 204
    assert approved.headers["access-control-allow-origin"] == "https://dashboard.example.test"
    assert approved.headers["access-control-allow-headers"] == "Authorization, Content-Type"
    assert "*" not in approved.headers["access-control-allow-origin"]
    assert rejected.status_code == 400
    assert "access-control-allow-origin" not in rejected.headers
    assert rejected_request.status_code == 400
