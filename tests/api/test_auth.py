from __future__ import annotations

import json
import time
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from threading import Barrier, Event
from urllib.error import HTTPError
from urllib.request import Request

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends
from fastapi.testclient import TestClient

from app.api.auth import (
    AuthenticatedRequestContext,
    AuthenticationRequired,
    JwksCache,
    JwtVerifier,
    require_authenticated_context,
)
from app.main import app as production_app
from app.settings import Settings


ISSUER = "https://issuer.test/auth/v1"
AUDIENCE = "authenticated"
MISSING_AUDIENCE = object()


@pytest.fixture
def signing_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="postgresql+psycopg://user:password@localhost/testgap",
        auth_jwt_issuer=ISSUER,
        auth_jwt_audience=AUDIENCE,
        auth_jwks_url="https://testserver/jwks.json",
        dashboard_origin="http://dashboard.test",
    )


def jwk(private_key: rsa.RSAPrivateKey, kid: str) -> dict[str, object]:
    result = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    result.update({"kid": kid, "alg": "RS256", "use": "sig", "key_ops": ["verify"]})
    return result


def token(
    private_key: rsa.RSAPrivateKey,
    kid: str = "key-1",
    aud: object = AUDIENCE,
    **overrides: object,
) -> str:
    now = int(time.time())
    payload: dict[str, object] = {
        "sub": "user-123",
        "iss": ISSUER,
        "iat": now,
        "nbf": now - 1,
        "exp": now + 300,
    }
    if aud is not MISSING_AUDIENCE:
        payload["aud"] = aud
    payload.update(overrides)
    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": kid})


def verifier(
    settings: Settings,
    fetch: Callable[[], dict[str, dict[str, object]]],
    **cache_options: float | int,
) -> JwtVerifier:
    cache = JwksCache(
        str(settings.auth_jwks_url),
        timeout_seconds=0.1,
        ttl_seconds=300,
        **cache_options,
    )
    cache._fetch = fetch  # type: ignore[method-assign]
    return JwtVerifier(settings, cache)


@contextmanager
def protected_client(jwt_verifier: JwtVerifier) -> Iterator[TestClient]:
    route_path = "/__test__/protected"
    previous_verifier = getattr(production_app.state, "jwt_verifier", None)
    had_verifier = hasattr(production_app.state, "jwt_verifier")
    previous_openapi = production_app.openapi_schema

    @production_app.get(route_path)
    async def protected(
        context: AuthenticatedRequestContext = Depends(require_authenticated_context),
    ) -> dict[str, object]:
        return {
            "typed_context": isinstance(context, AuthenticatedRequestContext),
            "subject": context.subject,
            "issuer": context.issuer,
            "audience": context.audience,
        }

    route = production_app.router.routes[-1]
    production_app.state.jwt_verifier = jwt_verifier
    production_app.openapi_schema = None
    try:
        with TestClient(production_app) as client:
            yield client
    finally:
        production_app.router.routes.remove(route)
        if had_verifier:
            production_app.state.jwt_verifier = previous_verifier
        else:
            del production_app.state.jwt_verifier
        production_app.openapi_schema = previous_openapi


def safe_401(response) -> None:  # type: ignore[no-untyped-def]
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    request_id = response.headers["x-request-id"]
    assert response.json() == {
        "error": {
            "code": "AUTHENTICATION_REQUIRED",
            "message": "Authentication is required.",
            "request_id": request_id,
            "details": {},
        }
    }
    assert "detail" not in response.json()
    assert len(request_id) == 32


def test_real_app_exact_audience_produces_typed_context_and_keeps_cors_and_cache(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
    signing_key: rsa.RSAPrivateKey,
) -> None:
    for name, value in {
        "DATABASE_URL": "postgresql+psycopg://user:password@localhost/testgap",
        "AUTH_JWT_ISSUER": ISSUER,
        "AUTH_JWT_AUDIENCE": AUDIENCE,
        "AUTH_JWKS_URL": "https://testserver/jwks.json",
        "DASHBOARD_ORIGIN": "http://dashboard.test",
    }.items():
        monkeypatch.setenv(name, value)
    calls = 0

    def fetch() -> dict[str, dict[str, object]]:
        nonlocal calls
        calls += 1
        return {"key-1": jwk(signing_key, "key-1")}

    schema_before = production_app.openapi()
    original_verifier = getattr(production_app.state, "jwt_verifier", None)
    had_verifier = hasattr(production_app.state, "jwt_verifier")
    with protected_client(verifier(settings, fetch)) as client:
        assert "/__test__/protected" in production_app.openapi()["paths"]
        response = client.get(
            "/__test__/protected",
            headers={
                "Authorization": f"Bearer {token(signing_key)}",
                "Origin": "http://dashboard.test",
            },
        )
        cached_response = client.get(
            "/__test__/protected",
            headers={"Authorization": f"Bearer {token(signing_key)}"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "typed_context": True,
        "subject": "user-123",
        "issuer": ISSUER,
        "audience": [AUDIENCE],
    }
    assert cached_response.status_code == 200
    assert calls == 1
    assert response.headers["access-control-allow-origin"] == "http://dashboard.test"
    assert "*" not in response.headers["access-control-allow-origin"]
    assert "/__test__/protected" not in production_app.openapi()["paths"]
    assert production_app.openapi() == schema_before
    assert hasattr(production_app.state, "jwt_verifier") is had_verifier
    assert getattr(production_app.state, "jwt_verifier", None) is original_verifier


@pytest.mark.parametrize(
    "audience",
    [
        [AUDIENCE, "other-service"],
        ["other-service", AUDIENCE],
        "Authenticated",
        "",
        MISSING_AUDIENCE,
    ],
    ids=["expected-first", "expected-last", "case-variation", "empty", "missing"],
)
def test_audience_must_be_exact_string(
    settings: Settings,
    signing_key: rsa.RSAPrivateKey,
    audience: object,
) -> None:
    with protected_client(verifier(settings, lambda: {"key-1": jwk(signing_key, "key-1")})) as client:
        safe_401(
            client.get(
                "/__test__/protected",
                headers={"Authorization": f"Bearer {token(signing_key, aud=audience)}"},
            )
        )


def test_slow_unknown_key_refresh_does_not_block_cached_key_request(
    settings: Settings,
    signing_key: rsa.RSAPrivateKey,
) -> None:
    refresh_started = Event()
    release_refresh = Event()

    def fetch() -> dict[str, dict[str, object]]:
        refresh_started.set()
        assert release_refresh.wait(timeout=10)
        return {"key-1": jwk(signing_key, "key-1")}

    jwt_verifier = verifier(settings, fetch)
    jwt_verifier.jwks_cache._keys = {"key-1": jwk(signing_key, "key-1")}
    jwt_verifier.jwks_cache._expires_at = float("inf")
    schema_before = production_app.openapi()
    original_verifier = getattr(production_app.state, "jwt_verifier", None)
    had_verifier = hasattr(production_app.state, "jwt_verifier")

    with protected_client(jwt_verifier) as client, ThreadPoolExecutor(max_workers=2) as pool:
        unknown = pool.submit(
            client.get,
            "/__test__/protected",
            headers={"Authorization": f"Bearer {token(signing_key, kid='missing')}"},
        )
        assert refresh_started.wait(timeout=5)
        cached = pool.submit(
            client.get,
            "/__test__/protected",
            headers={"Authorization": f"Bearer {token(signing_key)}"},
        )
        try:
            cached_response = cached.result(timeout=5)
            assert cached_response.status_code == 200
            assert not unknown.done()
        finally:
            release_refresh.set()
        safe_401(unknown.result(timeout=5))

    assert "/__test__/protected" not in production_app.openapi()["paths"]
    assert production_app.openapi() == schema_before
    assert hasattr(production_app.state, "jwt_verifier") is had_verifier
    assert getattr(production_app.state, "jwt_verifier", None) is original_verifier


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Basic abc"},
        {"Authorization": "Bearer"},
        {"Authorization": "Bearer not-a-jwt"},
    ],
)
def test_missing_or_malformed_authorization_is_safe_401(
    settings: Settings, signing_key: rsa.RSAPrivateKey, headers: dict[str, str]
) -> None:
    with protected_client(verifier(settings, lambda: {"key-1": jwk(signing_key, "key-1")})) as client:
        safe_401(client.get("/__test__/protected", headers=headers))


@pytest.mark.parametrize(
    "claims",
    [
        {"exp": int(time.time()) - 1},
        {"nbf": int(time.time()) + 300},
        {"iss": "https://other.test/auth/v1"},
        {"iss": f"{ISSUER}/"},
        {"aud": "other-audience"},
    ],
)
def test_invalid_claims_are_safe_401(
    settings: Settings, signing_key: rsa.RSAPrivateKey, claims: dict[str, object]
) -> None:
    with protected_client(verifier(settings, lambda: {"key-1": jwk(signing_key, "key-1")})) as client:
        safe_401(
            client.get(
                "/__test__/protected",
                headers={"Authorization": f"Bearer {token(signing_key, **claims)}"},
            )
        )


def test_bad_signature_and_algorithm_substitution_are_safe_401(
    settings: Settings, signing_key: rsa.RSAPrivateKey
) -> None:
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    hs_token = jwt.encode(
        {"sub": "user-123", "iss": ISSUER, "aud": AUDIENCE, "iat": int(time.time()), "exp": int(time.time()) + 300},
        "not-an-rsa-key",
        algorithm="HS256",
        headers={"kid": "key-1"},
    )
    with protected_client(verifier(settings, lambda: {"key-1": jwk(signing_key, "key-1")})) as client:
        safe_401(
            client.get(
                "/__test__/protected",
                headers={"Authorization": f"Bearer {token(other_key)}"},
            )
        )
        safe_401(
            client.get(
                "/__test__/protected",
                headers={"Authorization": f"Bearer {hs_token}"},
            )
        )


def test_same_unknown_kid_repeated_five_times_fetches_once_during_cooldown(
    settings: Settings, signing_key: rsa.RSAPrivateKey
) -> None:
    calls = 0

    def fetch() -> dict[str, dict[str, object]]:
        nonlocal calls
        calls += 1
        return {"key-1": jwk(signing_key, "key-1")}

    with protected_client(verifier(settings, fetch, refresh_cooldown_seconds=60)) as client:
        for _ in range(5):
            safe_401(
                client.get(
                    "/__test__/protected",
                    headers={"Authorization": f"Bearer {token(signing_key, kid='missing')}"},
                )
            )

    assert calls == 1


def test_varied_unknown_kids_fetch_once_during_cooldown(
    settings: Settings, signing_key: rsa.RSAPrivateKey
) -> None:
    calls = 0

    def fetch() -> dict[str, dict[str, object]]:
        nonlocal calls
        calls += 1
        return {"key-1": jwk(signing_key, "key-1")}

    jwt_verifier = verifier(settings, fetch, refresh_cooldown_seconds=60)
    for index in range(5):
        with pytest.raises(AuthenticationRequired):
            jwt_verifier.verify(token(signing_key, kid=f"missing-{index}"))

    assert calls == 1


def test_concurrent_unknown_kids_launch_at_most_one_fetch(
    settings: Settings, signing_key: rsa.RSAPrivateKey
) -> None:
    calls = 0
    barrier = Barrier(5)

    def fetch() -> dict[str, dict[str, object]]:
        nonlocal calls
        calls += 1
        return {"key-1": jwk(signing_key, "key-1")}

    jwt_verifier = verifier(settings, fetch, refresh_cooldown_seconds=60)
    tokens = [token(signing_key, kid=f"missing-{index}") for index in range(5)]

    def verify_unknown(encoded_token: str) -> None:
        barrier.wait()
        with pytest.raises(AuthenticationRequired):
            jwt_verifier.verify(encoded_token)

    with ThreadPoolExecutor(max_workers=5) as pool:
        list(pool.map(verify_unknown, tokens))

    assert calls == 1


def test_negative_kid_cache_has_a_fixed_entry_bound(
    settings: Settings, signing_key: rsa.RSAPrivateKey
) -> None:
    jwt_verifier = verifier(
        settings,
        lambda: {"key-1": jwk(signing_key, "key-1")},
        refresh_cooldown_seconds=60,
        max_negative_kids=3,
    )

    for index in range(10):
        with pytest.raises(AuthenticationRequired):
            jwt_verifier.verify(token(signing_key, kid=f"missing-{index}"))

    assert len(jwt_verifier.jwks_cache._unknown_kids) == 3


def test_rotated_key_authenticates_after_one_controlled_refresh(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
    signing_key: rsa.RSAPrivateKey,
) -> None:
    rotated_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = 100.0
    calls = 0

    def fetch() -> dict[str, dict[str, object]]:
        nonlocal calls
        calls += 1
        if calls == 1:
            return {"key-1": jwk(signing_key, "key-1")}
        return {"key-2": jwk(rotated_key, "key-2")}

    monkeypatch.setattr("app.api.auth.time.monotonic", lambda: now)
    jwt_verifier = verifier(
        settings,
        fetch,
        refresh_cooldown_seconds=10,
        negative_ttl_seconds=10,
    )
    assert jwt_verifier.verify(token(signing_key)).subject == "user-123"
    with pytest.raises(AuthenticationRequired):
        jwt_verifier.verify(token(rotated_key, kid="key-2"))
    assert calls == 1

    now = 111.0
    assert jwt_verifier.verify(token(rotated_key, kid="key-2")).subject == "user-123"
    assert calls == 2


def test_unknown_kid_and_jwks_refresh_failure_fail_closed(settings: Settings, signing_key: rsa.RSAPrivateKey) -> None:
    def failing_fetch() -> dict[str, dict[str, object]]:
        raise OSError("network unavailable")

    with protected_client(verifier(settings, failing_fetch)) as client:
        response = client.get(
            "/__test__/protected",
            headers={"Authorization": f"Bearer {token(signing_key, kid='missing')}"},
        )
        safe_401(response)
        assert "network unavailable" not in response.text
        assert "testserver" not in response.text


def test_jwks_redirect_to_http_is_not_followed(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
    signing_key: rsa.RSAPrivateKey,
) -> None:
    calls = 0

    class RedirectingOpener:
        def open(self, url: str, timeout: float) -> None:
            nonlocal calls
            calls += 1
            raise HTTPError(url, 302, "Found", {}, None)

    def build_redirect_rejecting_opener(handler: object) -> RedirectingOpener:
        redirected_request = handler.redirect_request(  # type: ignore[attr-defined]
            Request("https://jwks.example.test/keys"),
            None,
            302,
            "Found",
            {},
            "http://attacker.example.test/keys",
        )
        assert redirected_request is None
        return RedirectingOpener()

    monkeypatch.setattr("app.api.auth.build_opener", build_redirect_rejecting_opener)
    cache = JwksCache("https://jwks.example.test/keys", timeout_seconds=0.5)
    with protected_client(JwtVerifier(settings, cache)) as client:
        safe_401(
            client.get(
                "/__test__/protected",
                headers={"Authorization": f"Bearer {token(signing_key)}"},
            )
        )
    assert calls == 1


@pytest.mark.parametrize(
    "incompatible_usage",
    [
        {"use": "enc"},
        {"key_ops": ["verify", "encrypt"]},
        {"key_ops": ["verify", "wrapKey"]},
        {"key_ops": ["sign"]},
        {"key_ops": "verify"},
        {"key_ops": ["verify", "verify"]},
    ],
    ids=[
        "encryption-use",
        "verify-and-encrypt",
        "verify-and-wrap-key",
        "sign-only",
        "non-list-key-operations",
        "duplicate-verify",
    ],
)
def test_incompatible_jwk_usage_is_safe_401(
    settings: Settings,
    signing_key: rsa.RSAPrivateKey,
    incompatible_usage: dict[str, object],
) -> None:
    unusable_jwk: dict[str, object] = jwk(signing_key, "key-1")
    unusable_jwk.update(incompatible_usage)
    with protected_client(verifier(settings, lambda: {"key-1": unusable_jwk})) as client:
        safe_401(
            client.get(
                "/__test__/protected",
                headers={"Authorization": f"Bearer {token(signing_key)}"},
            )
        )


def test_refresh_tokens_cookies_and_query_values_are_not_credentials(
    settings: Settings, signing_key: rsa.RSAPrivateKey
) -> None:
    valid_token = token(signing_key)

    with protected_client(verifier(settings, lambda: {"key-1": jwk(signing_key, "key-1")})) as client:
        safe_401(client.get("/__test__/protected", params={"access_token": valid_token}))
        safe_401(
            client.get(
                "/__test__/protected",
                cookies={"refresh_token": valid_token, "access_token": valid_token},
            )
        )
        safe_401(
            client.get(
                "/__test__/protected",
                headers={"Authorization": "Bearer refresh-token"},
            )
        )
