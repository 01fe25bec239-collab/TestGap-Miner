from __future__ import annotations

import inspect
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

import app.api.runs as runs_api
from app.api.auth import AuthenticatedRequestContext, require_authenticated_context
from app.db.dependencies import get_db_session
from app.main import app
from app.services.control_plane import (
    LookupStatus,
    RunCursor,
    RunDetailResult,
    RunEventProjection,
    RunListQuery,
    RunPage,
    RunProjection,
    RunQueryError,
    RunQueryErrorCode,
    WorkflowAttemptProjection,
    WorkflowStepProjection,
    WorkflowTimeline,
    WorkflowTimelineResult,
)
from app.workflow import ActorType, RequestKind, RunState, WorkflowStepKind


NOW = datetime(2026, 8, 29, 10, 30, tzinfo=UTC)
RUN_ID = uuid.UUID("00000000-0000-0000-0000-000000000101")
REQUEST_ID = uuid.UUID("00000000-0000-0000-0000-000000000201")
REPOSITORY_ID = uuid.UUID("00000000-0000-0000-0000-000000000301")


def run_projection(run_id: uuid.UUID = RUN_ID) -> RunProjection:
    return RunProjection(
        id=run_id,
        run_request_id=REQUEST_ID,
        repository_id=REPOSITORY_ID,
        request_kind=RequestKind.BENCHMARK,
        state=RunState.RECEIVED,
        contract_version="1.0.0-draft.1",
        review_required=True,
        created_at=NOW,
        updated_at=NOW,
        terminal_at=None,
        failure_code=None,
        abstention_code=None,
        cancellation_code=None,
    )


def timeline() -> WorkflowTimeline:
    step_id = uuid.UUID("00000000-0000-0000-0000-000000000401")
    return WorkflowTimeline(
        run_id=RUN_ID,
        steps=(
            WorkflowStepProjection(
                id=step_id,
                run_id=RUN_ID,
                kind=WorkflowStepKind.PLAN,
                occurrence=1,
                created_at=NOW,
                input_version="v1",
            ),
        ),
        attempts=(
            WorkflowAttemptProjection(
                id=uuid.UUID("00000000-0000-0000-0000-000000000501"),
                step_id=step_id,
                attempt_index=0,
                started_at=NOW,
                ended_at=None,
                outcome=None,
                actor_type=ActorType.WORKER,
            ),
        ),
        events=(
            RunEventProjection(
                id=uuid.UUID("00000000-0000-0000-0000-000000000601"),
                run_id=RUN_ID,
                sequence=1,
                event_type="RUN_RECEIVED",
                from_state=None,
                to_state=RunState.RECEIVED,
                step_id=None,
                step_kind=None,
                attempt_index=None,
                actor_type=ActorType.WORKFLOW,
                occurred_at=NOW,
                recorded_at=NOW,
                causation_event_id=None,
                contract_version="1.0.0-draft.1",
                payload_schema_version="1",
                failure_code=None,
                abstention_code=None,
                cancellation_code=None,
            ),
        ),
    )


@pytest.fixture
def client() -> Iterator[TestClient]:
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[require_authenticated_context] = lambda: (
        AuthenticatedRequestContext(
            subject="user-1",
            issuer="https://issuer.test/auth/v1",
            audience=("authenticated",),
            claims={},
        )
    )
    app.dependency_overrides[get_db_session] = lambda: object()
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/runs",
        f"/api/v1/runs/{RUN_ID}",
        f"/api/v1/runs/{RUN_ID}/timeline",
    ],
)
def test_authentication_is_required_on_every_route(path: str) -> None:
    previous = app.dependency_overrides.copy()
    app.dependency_overrides.pop(require_authenticated_context, None)
    app.dependency_overrides[get_db_session] = lambda: object()
    try:
        with TestClient(app) as unauthenticated_client:
            response = unauthenticated_client.get(path)
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_list_happy_path_and_typed_serialization(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        runs_api,
        "list_runs",
        lambda session, query: RunPage(
            items=(run_projection(),), limit=query.limit, has_more=False, next_cursor=None
        ),
    )

    response = client.get("/api/v1/runs", params={"limit": 7})

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": str(RUN_ID),
                "run_request_id": str(REQUEST_ID),
                "repository_id": str(REPOSITORY_ID),
                "request_kind": "BENCHMARK",
                "state": "RECEIVED",
                "contract_version": "1.0.0-draft.1",
                "review_required": True,
                "created_at": "2026-08-29T10:30:00Z",
                "updated_at": "2026-08-29T10:30:00Z",
                "terminal_at": None,
                "failure_code": None,
                "abstention_code": None,
                "cancellation_code": None,
            }
        ],
        "limit": 7,
        "has_more": False,
        "next_cursor": None,
    }


@pytest.mark.parametrize("limit", [0, 101])
def test_list_limit_is_bounded(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, limit: int
) -> None:
    monkeypatch.setattr(
        runs_api,
        "list_runs",
        lambda *_: pytest.fail("invalid limit reached query service"),
    )

    response = client.get("/api/v1/runs", params={"limit": limit})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"


def test_repository_filter_reaches_query_service(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[RunListQuery] = []

    def fake_list(session: object, query: RunListQuery) -> RunPage:
        seen.append(query)
        return RunPage((), query.limit, False, None)

    monkeypatch.setattr(runs_api, "list_runs", fake_list)

    response = client.get(
        "/api/v1/runs", params={"repository_id": str(REPOSITORY_ID)}
    )

    assert response.status_code == 200
    assert seen[0].repository_id == REPOSITORY_ID


def test_cursor_is_url_safe_and_round_trips_to_query_service(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    cursor = RunCursor(NOW, RUN_ID)
    seen: list[RunListQuery] = []

    def fake_list(session: object, query: RunListQuery) -> RunPage:
        seen.append(query)
        return (
            RunPage((run_projection(),), 1, True, cursor)
            if len(seen) == 1
            else RunPage((), 1, False, None)
        )

    monkeypatch.setattr(runs_api, "list_runs", fake_list)
    first = client.get("/api/v1/runs", params={"limit": 1})
    token = first.json()["next_cursor"]
    second = client.get("/api/v1/runs", params={"limit": 1, "cursor": token})

    assert first.status_code == second.status_code == 200
    assert token and all(character.isalnum() or character in "-_" for character in token)
    assert seen[1].cursor == cursor


@pytest.mark.parametrize(
    "params",
    [
        {"cursor": "not-a-cursor"},
        {"cursor": "A" * 257},
        {"repository_id": "not-a-uuid"},
        {"limit": "not-an-integer"},
    ],
)
def test_invalid_cursor_and_query_input_fail_closed(
    client: TestClient, params: dict[str, str]
) -> None:
    response = client.get("/api/v1/runs", params=params)

    assert response.status_code == 422
    assert response.json()["error"] == {
        "code": "VALIDATION_FAILED",
        "message": "Request validation failed.",
        "request_id": response.headers["x-request-id"],
        "details": {},
    }
    assert next(iter(params.values())) not in response.text


def test_run_detail_found_and_not_found(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        runs_api,
        "get_run_detail",
        lambda session, run_id: RunDetailResult(
            LookupStatus.FOUND, run_projection(run_id)
        ),
    )
    found = client.get(f"/api/v1/runs/{RUN_ID}")
    monkeypatch.setattr(
        runs_api,
        "get_run_detail",
        lambda *_: RunDetailResult(LookupStatus.NOT_FOUND),
    )
    missing = client.get(f"/api/v1/runs/{RUN_ID}")

    assert found.status_code == 200
    assert found.json()["id"] == str(RUN_ID)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_malformed_run_uuid_is_safe_validation_error(client: TestClient) -> None:
    response = client.get("/api/v1/runs/not-a-uuid")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"
    assert "not-a-uuid" not in response.text


def test_timeline_found_not_found_and_typed_serialization(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        runs_api,
        "get_workflow_timeline",
        lambda *_: WorkflowTimelineResult(LookupStatus.FOUND, timeline()),
    )
    found = client.get(f"/api/v1/runs/{RUN_ID}/timeline")
    monkeypatch.setattr(
        runs_api,
        "get_workflow_timeline",
        lambda *_: WorkflowTimelineResult(LookupStatus.NOT_FOUND),
    )
    missing = client.get(f"/api/v1/runs/{RUN_ID}/timeline")

    assert found.status_code == 200
    assert found.json()["run_id"] == str(RUN_ID)
    assert found.json()["steps"][0]["kind"] == "PLAN"
    assert found.json()["attempts"][0]["actor_type"] == "WORKER"
    assert found.json()["events"][0]["recorded_at"] == "2026-08-29T10:30:00Z"
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.parametrize(
    ("path", "service_name"),
    [
        ("/api/v1/runs", "list_runs"),
        (f"/api/v1/runs/{RUN_ID}", "get_run_detail"),
        (f"/api/v1/runs/{RUN_ID}/timeline", "get_workflow_timeline"),
    ],
)
def test_query_failures_map_to_safe_5xx_without_internal_details(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    service_name: str,
) -> None:
    def fail(*_: object) -> None:
        raise RunQueryError(
            RunQueryErrorCode.DEPENDENCY_UNAVAILABLE,
            "password=secret sql=SELECT * FROM runs /internal/path",
        )

    monkeypatch.setattr(runs_api, service_name, fail)
    response = client.get(path)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "HTTP_ERROR"
    assert not any(
        detail in response.text
        for detail in ("password", "secret", "SELECT", "/internal/path")
    )


def test_handlers_use_query_service_without_sql_or_orm_access() -> None:
    source = inspect.getsource(runs_api)

    assert all(
        name in source
        for name in ("list_runs", "get_run_detail", "get_workflow_timeline")
    )
    assert "app.db.models" not in source
    assert ".execute(" not in source
    assert "select(" not in source


def test_only_get_run_routes_are_exposed() -> None:
    paths = {
        path: operations
        for path, operations in app.openapi()["paths"].items()
        if path.startswith("/api/v1/runs")
    }

    assert set(paths) == {
        "/api/v1/runs",
        "/api/v1/runs/{run_id}",
        "/api/v1/runs/{run_id}/timeline",
    }
    assert all(set(operations) == {"get"} for operations in paths.values())
