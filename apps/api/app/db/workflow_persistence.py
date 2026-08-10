"""Physical DB-003 event append and run-projection CAS primitives."""

import uuid
from collections.abc import Mapping

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.db.models.workflow import Run, RunEvent


class ProducerEventConflictError(RuntimeError):
    """A producer event ID was reused with different canonical content."""


class RunProjectionConflictError(RuntimeError):
    """A run projection did not match the caller's expected state/version."""


RUN_PROJECTION_MUTABLE_FIELDS = frozenset(
    {
        "state",
        "repair_attempts_used",
        "retry_attempts_used",
        "step_attempts_used",
        "terminal_at",
        "failure_code",
        "abstention_code",
        "cancellation_code",
        "terminal_actor_type",
        "terminal_actor_id",
        "checkpoint_ref",
    }
)


def append_run_event(session: Session, event: RunEvent) -> RunEvent:
    """Append a transient event under the run row lock, without committing."""
    if not sa.inspect(event).transient:
        raise ValueError("event must be transient")
    if event.run_id is None or not event.producer_event_id:
        raise ValueError("run_id and producer_event_id are required")

    run_id = session.scalar(
        sa.select(Run.id).where(Run.id == event.run_id).with_for_update()
    )
    if run_id is None:
        raise LookupError(f"run not found: {event.run_id}")

    existing = session.scalar(
        sa.select(RunEvent).where(
            RunEvent.run_id == event.run_id,
            RunEvent.producer_event_id == event.producer_event_id,
        )
    )
    if existing is not None:
        if (
            existing.producer_event_fingerprint_version
            == event.producer_event_fingerprint_version
            and existing.producer_event_fingerprint
            == event.producer_event_fingerprint
        ):
            return existing
        raise ProducerEventConflictError(
            f"conflicting producer event: {event.run_id}/{event.producer_event_id}"
        )

    event.sequence = session.scalar(
        sa.select(sa.func.coalesce(sa.func.max(RunEvent.sequence), 0) + 1).where(
            RunEvent.run_id == event.run_id
        )
    )
    session.add(event)
    session.flush()
    return event


def compare_and_swap_run(
    session: Session,
    *,
    run_id: uuid.UUID,
    expected_state: str,
    expected_version: int,
    updates: Mapping[str, object],
) -> Run:
    """Apply an allowlisted projection mutation and increment version once."""
    unknown = set(updates) - RUN_PROJECTION_MUTABLE_FIELDS
    if unknown:
        raise ValueError(f"unsupported run projection fields: {sorted(unknown)}")
    if not updates:
        raise ValueError("at least one projection field is required")

    run = session.scalar(
        sa.update(Run)
        .where(
            Run.id == run_id,
            Run.state == expected_state,
            Run.version == expected_version,
        )
        .values(
            **updates,
            version=Run.version + 1,
            updated_at=sa.func.now(),
        )
        .returning(Run)
    )
    if run is None:
        raise RunProjectionConflictError(
            f"run projection conflict: {run_id}/{expected_state}/{expected_version}"
        )
    return run
