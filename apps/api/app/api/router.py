from fastapi import APIRouter

from app.api.runs import router as runs_router


api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(runs_router)
