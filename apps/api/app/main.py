from uuid import uuid4

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.api.auth import AuthenticationRequired
from app.settings import Settings


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

app = FastAPI()
app.add_middleware(ExactOriginCorsMiddleware)


@app.exception_handler(AuthenticationRequired)
async def authentication_required_handler(_: Request, __: AuthenticationRequired) -> JSONResponse:
    request_id = uuid4().hex
    return JSONResponse(
        status_code=401,
        content={
            "error": {
                "code": "AUTHENTICATION_REQUIRED",
                "message": "Authentication is required.",
                "request_id": request_id,
                "details": {},
            }
        },
        headers={"WWW-Authenticate": "Bearer", "X-Request-ID": request_id},
    )
