"""Authenticated HTTP adapter for durable run queries."""

from __future__ import annotations

import base64
import binascii
import json
import uuid
from dataclasses import asdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session

from app.api.auth import require_authenticated_context
from app.db.dependencies import get_db_session
from app.services.control_plane import (
    LookupStatus,
    RunCursor,
    RunListQuery,
    RunPage,
    RunProjection,
    RunQueryError,
    RunQueryErrorCode,
    WorkflowTimeline,
    get_run_detail,
    get_workflow_timeline,
    list_runs,
)


router = APIRouter(
    prefix="/runs", dependencies=[Depends(require_authenticated_context)]
)


def _encode_cursor(cursor: RunCursor) -> str:
    if cursor.created_at.tzinfo is None or cursor.created_at.utcoffset() is None:
        raise ValueError("cursor timestamp must include a timezone")
    payload = json.dumps(
        [cursor.created_at.isoformat(), str(cursor.run_id)],
        separators=(",", ":"),
    ).encode()
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode()


def _decode_cursor(value: str) -> RunCursor:
    if not 1 <= len(value) <= 256 or not value.replace("-", "A").replace(
        "_", "A"
    ).isalnum():
        raise ValueError("invalid cursor")
    try:
        raw = base64.b64decode(
            value + "=" * (-len(value) % 4), altchars=b"-_", validate=True
        )
        payload = json.loads(raw)
        if (
            not isinstance(payload, list)
            or len(payload) != 2
            or not all(isinstance(item, str) for item in payload)
        ):
            raise ValueError("invalid cursor")
        cursor = RunCursor(datetime.fromisoformat(payload[0]), uuid.UUID(payload[1]))
        if _encode_cursor(cursor) != value:
            raise ValueError("invalid cursor")
        return cursor
    except (
        binascii.Error,
        UnicodeDecodeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ):
        raise ValueError("invalid cursor") from None


def _raise_query_error(error: RunQueryError) -> None:
    if error.code is RunQueryErrorCode.INVALID_QUERY:
        raise RequestValidationError([]) from None
    status_code = {
        RunQueryErrorCode.DEPENDENCY_UNAVAILABLE: 503,
    }.get(error.code, 500)
    raise HTTPException(status_code=status_code) from None


def _page_response(page: RunPage) -> dict[str, object]:
    response = asdict(page)
    response["next_cursor"] = (
        _encode_cursor(page.next_cursor) if page.next_cursor is not None else None
    )
    return response


@router.get("")
def runs(
    limit: int = 50,
    repository_id: uuid.UUID | None = None,
    cursor: str | None = None,
    session: Session = Depends(get_db_session),
) -> dict[str, object]:
    try:
        query = RunListQuery(
            limit=limit,
            repository_id=repository_id,
            cursor=_decode_cursor(cursor) if cursor is not None else None,
        )
    except ValueError:
        raise RequestValidationError([]) from None
    except RunQueryError as error:
        _raise_query_error(error)
    try:
        page = list_runs(session, query)
    except RunQueryError as error:
        _raise_query_error(error)
    return _page_response(page)


@router.get("/{run_id}")
def run_detail(
    run_id: uuid.UUID, session: Session = Depends(get_db_session)
) -> RunProjection:
    try:
        result = get_run_detail(session, run_id)
    except RunQueryError as error:
        _raise_query_error(error)
    if result.status is LookupStatus.NOT_FOUND or result.run is None:
        raise HTTPException(status_code=404)
    return result.run


@router.get("/{run_id}/timeline")
def run_timeline(
    run_id: uuid.UUID, session: Session = Depends(get_db_session)
) -> WorkflowTimeline:
    try:
        result = get_workflow_timeline(session, run_id)
    except RunQueryError as error:
        _raise_query_error(error)
    if result.status is LookupStatus.NOT_FOUND or result.timeline is None:
        raise HTTPException(status_code=404)
    return result.timeline
