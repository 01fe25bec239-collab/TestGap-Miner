"""Workflow projection constraint tests for CONTRACT-WORKFLOW-001@1.0.0-draft.1.

DB-002 implements no transition service, so nothing here claims that transition
orchestration is tested. These tests cover only which run-request and current-run
projection rows the database will store.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Repository, Run, RunRequest
from app.db.models.workflow import (
    ABSTENTION_CODES,
    CANCELLATION_CODES,
    FAILURE_CODES,
    RUN_STATES,
    TERMINAL_RUN_STATES,
)
from support import assert_rejected, make_run, make_run_request


def test_run_states_cover_the_exact_canonical_enumeration() -> None:
    assert len(RUN_STATES) == 20
    assert RUN_STATES[0] == "RECEIVED"
    assert RUN_STATES[-1] == "CANCELLED"
    assert all(state == state.upper() for state in RUN_STATES)


@pytest.mark.parametrize("state", RUN_STATES)
def test_every_canonical_run_state_is_accepted(session: Session, state: str) -> None:
    request = make_run_request()
    run = make_run(request, state)
    session.add_all([request, run])
    session.flush()
    session.expire(run)
    assert run.state == state


def test_unknown_run_state_is_rejected(session: Session) -> None:
    request = make_run_request()
    assert_rejected(session, request, make_run(request, "RETRYING"))


def test_lowercase_run_state_is_rejected(session: Session) -> None:
    request = make_run_request()
    assert_rejected(session, request, make_run(request, "received"))


@pytest.mark.parametrize("used", [0, 1])
def test_repair_attempts_used_accepts_zero_and_one(session: Session, used: int) -> None:
    request = make_run_request()
    run = make_run(request, repair_attempts_used=used)
    session.add_all([request, run])
    session.flush()
    assert run.repair_attempts_used == used


@pytest.mark.parametrize("used", [-1, 2])
def test_repair_attempts_used_rejects_a_second_repair(
    session: Session, used: int
) -> None:
    request = make_run_request()
    assert_rejected(session, request, make_run(request, repair_attempts_used=used))


def test_negative_optimistic_concurrency_version_is_rejected(session: Session) -> None:
    request = make_run_request()
    assert_rejected(session, request, make_run(request, version=-1))


def test_negative_retry_counters_are_rejected(session: Session) -> None:
    request = make_run_request()
    assert_rejected(session, request, make_run(request, retry_attempts_used=-1))


def test_retry_attempts_used_may_not_exceed_the_retry_limit(session: Session) -> None:
    request = make_run_request()
    assert_rejected(
        session, request, make_run(request, retry_limit=2, retry_attempts_used=3)
    )


def test_retry_and_repair_counters_are_independent(session: Session) -> None:
    request = make_run_request()
    run = make_run(request, retry_limit=5, retry_attempts_used=5, repair_attempts_used=0)
    session.add_all([request, run])
    session.flush()
    assert run.retry_attempts_used == 5
    assert run.repair_attempts_used == 0


def test_duplicate_request_idempotency_is_rejected(session: Session) -> None:
    first = make_run_request(idempotency_key="shared-key", request_fingerprint="a" * 8)
    session.add(first)
    session.flush()
    conflicting = make_run_request(
        idempotency_key="shared-key",
        request_fingerprint="b" * 8,
        benchmark_bug_id="2",
    )
    assert_rejected(session, conflicting)


def test_a_new_idempotency_key_version_does_not_collide(session: Session) -> None:
    session.add_all(
        [
            make_run_request(idempotency_key="shared-key", idempotency_key_version=1),
            make_run_request(idempotency_key="shared-key", idempotency_key_version=2),
        ]
    )
    session.flush()
    stored = session.scalars(
        select(RunRequest).where(RunRequest.idempotency_key == "shared-key")
    ).all()
    assert {row.idempotency_key_version for row in stored} == {1, 2}


def test_zero_idempotency_key_version_is_rejected(session: Session) -> None:
    assert_rejected(session, make_run_request(idempotency_key_version=0))


def test_github_request_requires_its_source_identity(session: Session) -> None:
    assert_rejected(
        session,
        make_run_request(
            request_kind="GITHUB",
            benchmark_project_id=None,
            benchmark_bug_id=None,
            github_delivery_guid="delivery-1",
        ),
    )


def test_github_request_may_not_carry_benchmark_identity(session: Session) -> None:
    assert_rejected(
        session,
        make_run_request(
            request_kind="GITHUB",
            github_delivery_guid="delivery-1",
            github_repository_id=3001,
            repository_sha="a" * 40,
        ),
    )


def test_benchmark_request_may_not_carry_a_delivery_guid(session: Session) -> None:
    assert_rejected(session, make_run_request(github_delivery_guid="delivery-1"))


def test_unknown_request_kind_is_rejected(session: Session) -> None:
    assert_rejected(session, make_run_request(request_kind="MANUAL"))


def test_internal_uuid_and_external_identity_stay_separate(session: Session) -> None:
    repository = Repository(github_repository_id=4242)
    request = make_run_request(
        request_kind="GITHUB",
        benchmark_project_id=None,
        benchmark_bug_id=None,
        github_delivery_guid="8f5b0e2c-0000-4000-8000-000000000001",
        github_repository_id=4242,
        repository_sha="b" * 40,
        repository=repository,
    )
    session.add_all([repository, request])
    session.flush()

    assert isinstance(repository.id, uuid.UUID)
    assert isinstance(request.id, uuid.UUID)
    assert request.id != repository.id
    # The GitHub numeric ID and the delivery GUID are separately typed values
    # and never populate an internal UUID.
    assert request.github_repository_id == 4242
    assert repository.github_repository_id == 4242
    assert str(request.id) != request.github_delivery_guid
    assert request.repository_id == repository.id


def test_run_requests_and_runs_both_exist(session: Session) -> None:
    request = make_run_request()
    run = make_run(request)
    session.add_all([request, run])
    session.flush()
    assert session.get(RunRequest, request.id) is not None
    assert session.get(Run, run.id) is not None
    assert run.run_request_id == request.id


def test_one_current_projection_per_request(session: Session) -> None:
    request = make_run_request()
    session.add_all([request, make_run(request)])
    session.flush()
    assert_rejected(session, Run(
        run_request_id=request.id,
        state="RECEIVED",
        contract_version="1.0.0-draft.1",
        review_required=True,
        retry_limit=3,
    ))


@pytest.mark.parametrize("state", TERMINAL_RUN_STATES)
def test_terminal_states_require_a_terminal_timestamp_and_attribution(
    session: Session, state: str
) -> None:
    request = make_run_request()
    assert_rejected(
        session,
        request,
        make_run(request, state, terminal_at=None, terminal_actor_type=None,
                 terminal_actor_id=None),
    )


def test_non_terminal_states_may_not_claim_terminal_attribution(
    session: Session,
) -> None:
    request = make_run_request()
    assert_rejected(
        session,
        request,
        make_run(request, "SCORING", terminal_at=datetime.now(UTC),
                 terminal_actor_type="SYSTEM", terminal_actor_id="x"),
    )


def test_unknown_terminal_actor_type_is_rejected(session: Session) -> None:
    request = make_run_request()
    assert_rejected(
        session, request, make_run(request, "COMPLETED", terminal_actor_type="ROBOT")
    )


@pytest.mark.parametrize(
    ("state", "code"),
    [(state, code) for state, codes in FAILURE_CODES.items() for code in codes],
)
def test_every_contract_failure_code_is_accepted(
    session: Session, state: str, code: str
) -> None:
    request = make_run_request()
    run = make_run(request, state, failure_code=code)
    session.add_all([request, run])
    session.flush()
    assert run.failure_code == code


@pytest.mark.parametrize(
    ("state", "code"),
    [
        ("FAILED_INPUT", "INPUT_NEW_REASON"),
        ("FAILED_MODEL", "MODEL_ADDITIONAL_FAILURE"),
        ("FAILED_EXECUTION", "EXECUTION_NEW_RUNNER_REASON"),
        ("FAILED_INFRASTRUCTURE", "INFRASTRUCTURE_NEW_CAPACITY_REASON"),
        ("FAILED_SECURITY", "SECURITY_NEW_POLICY_REASON"),
    ],
)
def test_unknown_uppercase_additive_failure_code_is_accepted(
    session: Session, state: str, code: str
) -> None:
    request = make_run_request()
    run = make_run(request, state, failure_code=code)
    session.add_all([request, run])
    session.flush()
    assert run.failure_code == code


@pytest.mark.parametrize(
    "code",
    [
        "INPUT_",
        "INPUT_lowercase",
        "INPUT_BAD-VALUE",
        "INPUT BAD VALUE",
        "INPUT__DOUBLE",
        " INPUT_BAD_VALUE",
        "INPUT_BAD_VALUE ",
    ],
)
def test_malformed_same_family_failure_code_is_rejected(
    session: Session, code: str
) -> None:
    request = make_run_request()
    assert_rejected(
        session, request, make_run(request, "FAILED_INPUT", failure_code=code)
    )


def test_failure_code_from_another_family_is_rejected(session: Session) -> None:
    request = make_run_request()
    assert_rejected(
        session,
        request,
        make_run(request, "FAILED_INPUT", failure_code="MODEL_OUTPUT_INVALID"),
    )


def test_non_failed_state_may_not_carry_a_failure_code(session: Session) -> None:
    request = make_run_request()
    assert_rejected(
        session, request, make_run(request, "COMPLETED", failure_code="INPUT_MALFORMED")
    )


@pytest.mark.parametrize("code", ABSTENTION_CODES)
def test_every_abstention_code_is_accepted(session: Session, code: str) -> None:
    request = make_run_request()
    run = make_run(request, "ABSTAINED", abstention_code=code)
    session.add_all([request, run])
    session.flush()
    assert run.abstention_code == code


def test_unknown_abstention_code_is_rejected(session: Session) -> None:
    request = make_run_request()
    assert_rejected(
        session, request, make_run(request, "ABSTAINED", abstention_code="GAVE_UP")
    )


@pytest.mark.parametrize("code", CANCELLATION_CODES)
def test_every_cancellation_code_is_accepted(session: Session, code: str) -> None:
    request = make_run_request()
    run = make_run(request, "CANCELLED", cancellation_code=code)
    session.add_all([request, run])
    session.flush()
    assert run.cancellation_code == code


def test_unknown_cancellation_code_is_rejected(session: Session) -> None:
    request = make_run_request()
    assert_rejected(
        session, request, make_run(request, "CANCELLED", cancellation_code="BORED")
    )


def test_regeneration_lineage_points_at_the_completed_parent(session: Session) -> None:
    parent_request = make_run_request()
    parent_run = make_run(parent_request, "COMPLETED")
    session.add_all([parent_request, parent_run])
    session.flush()

    child_request = make_run_request()
    child_run = make_run(child_request, parent_run=parent_run)
    session.add_all([child_request, child_run])
    session.flush()

    assert child_run.parent_run_id == parent_run.id
    assert child_run.id != parent_run.id
    assert child_run.state == "RECEIVED"


def test_a_run_may_not_be_its_own_parent(session: Session) -> None:
    request = make_run_request()
    run = make_run(request)
    session.add_all([request, run])
    session.flush()
    run.parent_run_id = run.id
    assert_rejected(session, run)


def test_run_defaults_match_the_contract_initial_projection(session: Session) -> None:
    request = make_run_request()
    run = Run(run_request=request, contract_version="1.0.0-draft.1", retry_limit=0)
    session.add_all([request, run])
    session.flush()
    session.expire(run)
    assert run.state == "RECEIVED"
    assert run.repair_attempts_used == 0
    assert run.retry_attempts_used == 0
    assert run.step_attempts_used == 0
    assert run.version == 0
    assert run.review_required is True
    assert run.terminal_at is None
