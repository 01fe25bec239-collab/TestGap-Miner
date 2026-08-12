import asyncio
import re
from contextlib import asynccontextmanager
from threading import Lock
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse, Response

from app.api.auth import AuthenticationRequired
from app.api.router import api_v1_router
from app.db.engine import check_database_connection, create_database_engine
from app.settings import Settings


_OPAQUE_ID = re.compile(r"[A-Za-z0-9._:-]{1,128}\Z", re.ASCII)
_engine_lock = Lock()


def _effective_id(value: str | None) -> str:
    return value if value is not None and _OPAQUE_ID.fullmatch(value) else uuid4().hex


def _error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request.state.request_id,
                "details": {},
            }
        },
        headers=headers,
    )


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):  # type: ignore[no-untyped-def]
        request_id = _effective_id(request.headers.get("x-request-id"))
        correlation_value = request.headers.get("x-correlation-id")
        correlation_id = (
            request_id if correlation_value is None else _effective_id(correlation_value)
        )
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        try:
            response = await call_next(request)
        except Exception:
            response = _error_response(
                request, 500, "INTERNAL_ERROR", "An unexpected error occurred."
            )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id
        return response


class ExactOriginCorsMiddleware(BaseHTTPMiddleware):
    """Only grants CORS access to the configured Dashboard origin."""

    async def dispatch(self, request, call_next):  # type: ignore[no-untyped-def]
        origin = request.headers.get("origin")
        try:
            allowed_origin = Settings().dashboard_origin
        except Exception:
            allowed_origin = None
        if origin and origin != allowed_origin:
            return Response(status_code=400)
        if request.method == "OPTIONS" and origin:
            return Response(
                status_code=204,
                headers={
                    "Access-Control-Allow-Origin": allowed_origin,
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                    "Access-Control-Allow-Headers": "Authorization, Content-Type",
                    "Vary": "Origin",
                },
            )
        response = await call_next(request)
        if origin and origin == allowed_origin:
            response.headers["Access-Control-Allow-Origin"] = allowed_origin
            response.headers["Vary"] = "Origin"
        return response


def _database_is_ready(application: FastAPI, settings: Settings) -> bool:
    engine = getattr(application.state, "database_engine", None)
    if engine is None:
        with _engine_lock:
            engine = getattr(application.state, "database_engine", None)
            if engine is None:
                engine = create_database_engine(settings.database_url.get_secret_value())
                application.state.database_engine = engine
    return check_database_connection(engine)


@asynccontextmanager
async def lifespan(application: FastAPI):  # type: ignore[no-untyped-def]
    yield
    engine = getattr(application.state, "database_engine", None)
    if engine is not None:
        engine.dispose()
        del application.state.database_engine


app = FastAPI(lifespan=lifespan)
app.add_middleware(ExactOriginCorsMiddleware)
app.add_middleware(RequestContextMiddleware)
app.include_router(api_v1_router)


@app.get("/healthz", include_in_schema=False)
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz", include_in_schema=False)
async def readiness(request: Request) -> JSONResponse:
    try:
        settings = Settings()
        ready = await asyncio.wait_for(
            run_in_threadpool(_database_is_ready, request.app, settings),
            timeout=settings.readiness_timeout_seconds,
        )
    except Exception:
        ready = False
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ready" if ready else "not_ready"},
    )


@app.exception_handler(AuthenticationRequired)
async def authentication_required_handler(
    request: Request, __: AuthenticationRequired
) -> JSONResponse:
    return _error_response(
        request,
        401,
        "AUTHENTICATION_REQUIRED",
        "Authentication is required.",
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(
    request: Request, exception: StarletteHTTPException
) -> JSONResponse:
    code, message = {
        404: ("RESOURCE_NOT_FOUND", "Resource not found."),
        405: ("METHOD_NOT_ALLOWED", "Method not allowed."),
    }.get(exception.status_code, ("HTTP_ERROR", "Request could not be completed."))
    return _error_response(request, exception.status_code, code, message)


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    request: Request, _: RequestValidationError
) -> JSONResponse:
    return _error_response(
        request, 422, "VALIDATION_FAILED", "Request validation failed."
    )
