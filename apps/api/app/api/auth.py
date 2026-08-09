"""Bearer access-token verification for protected FastAPI dependencies."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from threading import Condition
from typing import Any
from urllib.request import HTTPRedirectHandler, build_opener

import jwt
from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError, PyJWTError

from app.settings import Settings

_bearer = HTTPBearer(auto_error=False)
_ALGORITHMS = ("RS256", "ES256")


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, *args: object, **kwargs: object) -> None:
        return None


@dataclass(frozen=True)
class AuthenticatedRequestContext:
    """Validated claims made available to later authorization dependencies."""

    subject: str
    issuer: str
    audience: tuple[str, ...]
    claims: dict[str, Any]


class JwksCache:
    """Process-local JWKS cache with bounded unknown-key refreshes."""

    def __init__(
        self,
        url: str,
        timeout_seconds: float = 2.0,
        ttl_seconds: int = 300,
        refresh_cooldown_seconds: float = 30.0,
        negative_ttl_seconds: float = 30.0,
        max_negative_kids: int = 128,
    ) -> None:
        self.url = url
        self.timeout_seconds = timeout_seconds
        self.ttl_seconds = ttl_seconds
        self.refresh_cooldown_seconds = refresh_cooldown_seconds
        self.negative_ttl_seconds = negative_ttl_seconds
        self.max_negative_kids = max(0, max_negative_kids)
        self._keys: dict[str, dict[str, Any]] = {}
        self._expires_at = 0.0
        self._unknown_kids: dict[str, float] = {}
        self._next_refresh_at = 0.0
        self._refreshing = False
        self._condition = Condition()

    def _fetch(self) -> dict[str, dict[str, Any]]:
        with build_opener(_RejectRedirects()).open(  # nosec B310: URL is validated settings
            self.url, timeout=self.timeout_seconds
        ) as response:
            payload = json.load(response)
        keys = payload.get("keys") if isinstance(payload, dict) else None
        if not isinstance(keys, list):
            raise ValueError("JWKS response did not contain keys")
        parsed = {
            key["kid"]: key
            for key in keys
            if isinstance(key, dict) and isinstance(key.get("kid"), str)
        }
        if not parsed:
            raise ValueError("JWKS response contained no usable keys")
        return parsed

    def _remember_unknown(self, kid: str, now: float) -> None:
        if not self.max_negative_kids:
            return
        self._unknown_kids.pop(kid, None)
        self._unknown_kids[kid] = now + self.negative_ttl_seconds
        while len(self._unknown_kids) > self.max_negative_kids:
            self._unknown_kids.pop(next(iter(self._unknown_kids)))

    def get_key(self, kid: str) -> dict[str, Any] | None:
        while True:
            with self._condition:
                now = time.monotonic()
                cached = self._keys.get(kid)
                if cached is not None and now < self._expires_at:
                    return cached
                unknown_until = self._unknown_kids.get(kid)
                if unknown_until is not None:
                    if now < unknown_until:
                        return None
                    del self._unknown_kids[kid]
                if now < self._next_refresh_at:
                    self._remember_unknown(kid, now)
                    return None
                if self._refreshing:
                    self._condition.wait()
                    continue
                self._refreshing = True
                break

        try:
            keys = self._fetch()
        except Exception:
            keys = None

        with self._condition:
            now = time.monotonic()
            self._next_refresh_at = now + self.refresh_cooldown_seconds
            if keys is not None:
                self._keys = keys
                self._expires_at = now + self.ttl_seconds
            cached = keys.get(kid) if keys is not None else None
            if cached is None:
                self._remember_unknown(kid, now)
            self._refreshing = False
            self._condition.notify_all()
            return cached


class JwtVerifier:
    def __init__(self, settings: Settings, jwks_cache: JwksCache | None = None) -> None:
        self.settings = settings
        self.jwks_cache = jwks_cache or JwksCache(str(settings.auth_jwks_url))

    def verify(self, token: str) -> AuthenticatedRequestContext:
        try:
            header = jwt.get_unverified_header(token)
            algorithm = header.get("alg")
            kid = header.get("kid")
            if algorithm not in _ALGORITHMS or not isinstance(kid, str) or not kid:
                raise InvalidTokenError("unsupported signing configuration")
            jwk = self.jwks_cache.get_key(kid)
            key_ops = jwk.get("key_ops") if jwk is not None else None
            if (
                jwk is None
                or jwk.get("alg") not in {None, algorithm}
                or ("use" in jwk and jwk["use"] != "sig")
                or ("key_ops" in jwk and key_ops != ["verify"])
            ):
                raise InvalidTokenError("verification key unavailable")
            key = jwt.algorithms.get_default_algorithms()[algorithm].from_jwk(json.dumps(jwk))
            claims = jwt.decode(
                token,
                key=key,
                algorithms=[algorithm],
                audience=self.settings.auth_jwt_audience,
                issuer=self.settings.auth_jwt_issuer,
                options={"require": ["exp", "iat", "sub"]},
            )
        except (PyJWTError, ValueError, TypeError, json.JSONDecodeError):
            raise unauthenticated() from None
        subject = claims.get("sub")
        audience = claims.get("aud")
        if (
            not isinstance(subject, str)
            or not subject
            or not isinstance(audience, str)
            or audience != self.settings.auth_jwt_audience
        ):
            raise unauthenticated()
        return AuthenticatedRequestContext(
            subject=subject,
            issuer=claims["iss"],
            audience=(audience,),
            claims=claims,
        )


class AuthenticationRequired(Exception):
    """Safe, credential-agnostic authentication failure."""


def unauthenticated() -> AuthenticationRequired:
    return AuthenticationRequired()


async def require_authenticated_context(request: Request) -> AuthenticatedRequestContext:
    credentials: HTTPAuthorizationCredentials | None = await _bearer(request)
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise unauthenticated()
    verifier = getattr(request.app.state, "jwt_verifier", None)
    if not isinstance(verifier, JwtVerifier):
        try:
            verifier = JwtVerifier(Settings())
        except Exception:
            raise unauthenticated() from None
        request.app.state.jwt_verifier = verifier
    return await asyncio.to_thread(verifier.verify, credentials.credentials)
