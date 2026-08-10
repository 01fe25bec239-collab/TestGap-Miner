"""Workflow run-request, current-run, and DB-003 history persistence.

Every state value, counter bound, identity rule, and lifecycle meaning below
comes from ``CONTRACT-WORKFLOW-001@1.0.0-draft.1``. DB-002 owns the durable
request record and current run projection. DB-003 owns normalized workflow
steps, attempts, and ordered append-only run events.

Nothing here orchestrates transitions. The check constraints describe which
projection rows and stored transition-history pairs are representable; they do
not decide when a Workflow transition should occur.

No raw prompt, repository byte, patch byte, execution log, or secret is stored.
"""

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, sql_in
from app.db.models.auth import AuthSubject, Repository

REQUEST_KINDS = ("GITHUB", "BENCHMARK")

# Exact canonical RunState values in contract declaration order. Declaration
# order carries no transition meaning.
RUN_STATES = (
    "RECEIVED",
    "VALIDATING",
    "QUEUED",
    "PLANNING",
    "LOCALISING",
    "GENERATING",
    "EXECUTING_BUGGY",
    "EXECUTING_FIXED",
    "REPAIRING",
    "SCORING",
    "PUBLISHING",
    "AWAITING_HUMAN_REVIEW",
    "COMPLETED",
    "ABSTAINED",
    "FAILED_INPUT",
    "FAILED_MODEL",
    "FAILED_EXECUTION",
    "FAILED_INFRASTRUCTURE",
    "FAILED_SECURITY",
    "CANCELLED",
)

TERMINAL_RUN_STATES = (
    "COMPLETED",
    "ABSTAINED",
    "FAILED_INPUT",
    "FAILED_MODEL",
    "FAILED_EXECUTION",
    "FAILED_INFRASTRUCTURE",
    "FAILED_SECURITY",
    "CANCELLED",
)

# Failure codes are checked by their contract family rather than by a frozen
# list, because the contract lets a consumer preserve an unknown additive code
# while requiring the terminal state to stay the compatibility boundary.
FAILURE_CODE_PREFIXES = {
    "FAILED_INPUT": "INPUT_",
    "FAILED_MODEL": "MODEL_",
    "FAILED_EXECUTION": "EXECUTION_",
    "FAILED_INFRASTRUCTURE": "INFRASTRUCTURE_",
    "FAILED_SECURITY": "SECURITY_",
}

FAILURE_CODES = {
    "FAILED_INPUT": (
        "INPUT_MALFORMED",
        "INPUT_SOURCE_UNSUPPORTED",
        "INPUT_REFERENCE_INVALID",
        "INPUT_SCOPE_VIOLATION",
    ),
    "FAILED_MODEL": (
        "MODEL_PROVIDER_UNAVAILABLE",
        "MODEL_OUTPUT_INVALID",
        "MODEL_BUDGET_EXHAUSTED",
        "MODEL_POLICY_REFUSAL",
    ),
    "FAILED_EXECUTION": (
        "EXECUTION_COMPILE_ERROR",
        "EXECUTION_TIMEOUT",
        "EXECUTION_NONDETERMINISTIC",
        "EXECUTION_RUNNER_ERROR",
    ),
    "FAILED_INFRASTRUCTURE": (
        "INFRASTRUCTURE_DATABASE",
        "INFRASTRUCTURE_OBJECT_STORE",
        "INFRASTRUCTURE_QUEUE",
        "INFRASTRUCTURE_CAPACITY",
        "INFRASTRUCTURE_RETRY_EXHAUSTED",
    ),
    "FAILED_SECURITY": (
        "SECURITY_AUTHORIZATION_DENIED",
        "SECURITY_SECRET_DETECTED",
        "SECURITY_TOOL_POLICY_VIOLATION",
        "SECURITY_PRODUCTION_EDIT_ATTEMPT",
        "SECURITY_NETWORK_POLICY_VIOLATION",
    ),
}

# Closed enumerations: the contract requires exactly one of each list.
ABSTENTION_CODES = (
    "UNSUPPORTED_LANGUAGE_OR_TEST_FRAMEWORK",
    "BUG_NOT_REPRODUCED",
    "INSUFFICIENT_LOCALISATION_CONFIDENCE",
    "INSUFFICIENT_CONTEXT",
    "NO_SAFE_TEST_ONLY_PATCH",
    "REPAIR_LIMIT_EXHAUSTED",
    "EVIDENCE_INCONCLUSIVE",
    "PUBLICATION_NOT_JUSTIFIED",
)

CANCELLATION_CODES = (
    "USER_REQUESTED",
    "SUPERSEDED",
    "OPERATOR_REQUESTED",
    "SYSTEM_SHUTDOWN",
)

TERMINAL_ACTOR_TYPES = ("SYSTEM", "WORKFLOW", "WORKER", "HUMAN")

WORKFLOW_STEP_KINDS = (
    "VALIDATE_INPUT",
    "PLAN",
    "LOCALISE",
    "GENERATE_CANDIDATE",
    "EXECUTE_BUGGY",
    "EXECUTE_FIXED",
    "REPAIR_CANDIDATE",
    "SCORE_EVIDENCE",
    "PUBLISH_DRAFT",
    "HUMAN_REVIEW",
)

ALLOWED_RUN_TRANSITIONS = (
    ("RECEIVED", "VALIDATING"),
    ("RECEIVED", "CANCELLED"),
    ("VALIDATING", "QUEUED"),
    ("VALIDATING", "FAILED_INPUT"),
    ("VALIDATING", "FAILED_INFRASTRUCTURE"),
    ("VALIDATING", "FAILED_SECURITY"),
    ("VALIDATING", "CANCELLED"),
    ("QUEUED", "PLANNING"),
    ("QUEUED", "FAILED_INFRASTRUCTURE"),
    ("QUEUED", "FAILED_SECURITY"),
    ("QUEUED", "CANCELLED"),
    ("PLANNING", "LOCALISING"),
    ("PLANNING", "ABSTAINED"),
    ("PLANNING", "FAILED_MODEL"),
    ("PLANNING", "FAILED_INFRASTRUCTURE"),
    ("PLANNING", "FAILED_SECURITY"),
    ("PLANNING", "CANCELLED"),
    ("LOCALISING", "GENERATING"),
    ("LOCALISING", "ABSTAINED"),
    ("LOCALISING", "FAILED_MODEL"),
    ("LOCALISING", "FAILED_INFRASTRUCTURE"),
    ("LOCALISING", "FAILED_SECURITY"),
    ("LOCALISING", "CANCELLED"),
    ("GENERATING", "EXECUTING_BUGGY"),
    ("GENERATING", "ABSTAINED"),
    ("GENERATING", "FAILED_MODEL"),
    ("GENERATING", "FAILED_INFRASTRUCTURE"),
    ("GENERATING", "FAILED_SECURITY"),
    ("GENERATING", "CANCELLED"),
    ("EXECUTING_BUGGY", "EXECUTING_FIXED"),
    ("EXECUTING_BUGGY", "REPAIRING"),
    ("EXECUTING_BUGGY", "ABSTAINED"),
    ("EXECUTING_BUGGY", "FAILED_EXECUTION"),
    ("EXECUTING_BUGGY", "FAILED_INFRASTRUCTURE"),
    ("EXECUTING_BUGGY", "FAILED_SECURITY"),
    ("EXECUTING_BUGGY", "CANCELLED"),
    ("EXECUTING_FIXED", "REPAIRING"),
    ("EXECUTING_FIXED", "SCORING"),
    ("EXECUTING_FIXED", "ABSTAINED"),
    ("EXECUTING_FIXED", "FAILED_EXECUTION"),
    ("EXECUTING_FIXED", "FAILED_INFRASTRUCTURE"),
    ("EXECUTING_FIXED", "FAILED_SECURITY"),
    ("EXECUTING_FIXED", "CANCELLED"),
    ("REPAIRING", "EXECUTING_BUGGY"),
    ("REPAIRING", "ABSTAINED"),
    ("REPAIRING", "FAILED_MODEL"),
    ("REPAIRING", "FAILED_INFRASTRUCTURE"),
    ("REPAIRING", "FAILED_SECURITY"),
    ("REPAIRING", "CANCELLED"),
    ("SCORING", "PUBLISHING"),
    ("SCORING", "AWAITING_HUMAN_REVIEW"),
    ("SCORING", "COMPLETED"),
    ("SCORING", "ABSTAINED"),
    ("SCORING", "FAILED_INFRASTRUCTURE"),
    ("SCORING", "FAILED_SECURITY"),
    ("SCORING", "CANCELLED"),
    ("PUBLISHING", "AWAITING_HUMAN_REVIEW"),
    ("PUBLISHING", "COMPLETED"),
    ("PUBLISHING", "FAILED_INFRASTRUCTURE"),
    ("PUBLISHING", "FAILED_SECURITY"),
    ("PUBLISHING", "CANCELLED"),
    ("AWAITING_HUMAN_REVIEW", "COMPLETED"),
)

_TERMINAL = sql_in("state", TERMINAL_RUN_STATES)

_FAILURE_CODE_CHECK = (
    "CASE state "
    + " ".join(
        f"WHEN {state!r} THEN failure_code IS NOT NULL"
        f" AND failure_code ~ '^{prefix}[A-Z0-9]+(_[A-Z0-9]+)*$'"
        for state, prefix in FAILURE_CODE_PREFIXES.items()
    )
    + " ELSE failure_code IS NULL END"
)

_ALLOWED_TRANSITION_CHECK = (
    "event_type <> 'STATE_TRANSITIONED' OR ("
    + " OR ".join(
        f"(from_state = {source!r} AND to_state = {target!r})"
        for source, target in ALLOWED_RUN_TRANSITIONS
    )
    + ")"
)

_EVENT_REASON_CHECK = (
    "CASE "
    + " ".join(
        "WHEN event_type = 'STATE_TRANSITIONED'"
        f" AND to_state = {state!r} THEN failure_code IS NOT NULL"
        f" AND failure_code ~ '^{prefix}[A-Z0-9]+(_[A-Z0-9]+)*$'"
        " AND abstention_code IS NULL AND cancellation_code IS NULL"
        for state, prefix in FAILURE_CODE_PREFIXES.items()
    )
    + " WHEN event_type = 'STATE_TRANSITIONED' AND to_state = 'ABSTAINED'"
    f" THEN failure_code IS NULL AND {sql_in('abstention_code', ABSTENTION_CODES)}"
    " AND cancellation_code IS NULL"
    " WHEN event_type = 'STATE_TRANSITIONED' AND to_state = 'CANCELLED'"
    f" THEN failure_code IS NULL AND abstention_code IS NULL"
    f" AND {sql_in('cancellation_code', CANCELLATION_CODES)}"
    " ELSE failure_code IS NULL AND abstention_code IS NULL"
    " AND cancellation_code IS NULL END"
)


class RunRequest(Base):
    """Immutable durable invocation record and idempotency boundary."""

    __tablename__ = "run_requests"
    __table_args__ = (
        # Versioned composition: the key version is part of the unique scope so
        # a future composition version cannot collide with a stored key.
        sa.UniqueConstraint("idempotency_key_version", "idempotency_key"),
        sa.CheckConstraint(
            sql_in("request_kind", REQUEST_KINDS), name="request_kind_allowed"
        ),
        sa.CheckConstraint(
            "idempotency_key_version >= 1", name="idempotency_key_version_positive"
        ),
        sa.CheckConstraint(
            "CASE request_kind"
            " WHEN 'GITHUB' THEN github_delivery_guid IS NOT NULL"
            " AND github_repository_id IS NOT NULL"
            " AND repository_sha IS NOT NULL"
            " AND benchmark_project_id IS NULL"
            " AND benchmark_bug_id IS NULL"
            " WHEN 'BENCHMARK' THEN benchmark_project_id IS NOT NULL"
            " AND benchmark_bug_id IS NOT NULL"
            " AND github_delivery_guid IS NULL"
            " ELSE false END",
            name="kind_field_shape",
        ),
        sa.CheckConstraint(
            "github_repository_id IS NULL OR github_repository_id > 0",
            name="github_repository_id_positive",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    request_kind: Mapped[str] = mapped_column(sa.Text)

    # Bounded digest of the versioned canonical composition.
    idempotency_key: Mapped[str] = mapped_column(sa.String(128))
    idempotency_key_version: Mapped[int] = mapped_column(sa.Integer, default=1)
    # Digest of the full canonical payload, used to tell an idempotent replay
    # apart from a conflicting payload reusing the same key.
    request_fingerprint: Mapped[str] = mapped_column(sa.String(128))

    # External identifiers. None of these may populate or masquerade as a UUID.
    github_delivery_guid: Mapped[str | None] = mapped_column(sa.Text)
    github_repository_id: Mapped[int | None] = mapped_column(sa.BigInteger)
    repository_sha: Mapped[str | None] = mapped_column(sa.String(64))
    benchmark_project_id: Mapped[str | None] = mapped_column(sa.Text)
    benchmark_bug_id: Mapped[str | None] = mapped_column(sa.Text)

    configuration_version: Mapped[str] = mapped_column(sa.Text)
    model_id: Mapped[str] = mapped_column(sa.Text)
    prompt_template_version: Mapped[str] = mapped_column(sa.Text)

    # Repository scope stays an internal repository relation for both request
    # kinds; a benchmark identifier is never overloaded to carry it.
    repository_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("repositories.id"), index=True
    )
    # Auth-owned identity reference. Nullable because a benchmark or
    # system-initiated request has no human subject.
    requested_by_subject: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("auth_subjects.id"), index=True
    )
    correlation_id: Mapped[str | None] = mapped_column(sa.String(255))
    created_at: Mapped[datetime] = mapped_column(server_default=sa.func.now())

    repository: Mapped[Repository | None] = relationship()
    subject: Mapped[AuthSubject | None] = relationship()
    run: Mapped["Run"] = relationship(back_populates="run_request")


class Run(Base):
    """Current run projection reconstructable from DB-003 transition events."""

    __tablename__ = "runs"
    __table_args__ = (
        sa.CheckConstraint(sql_in("state", RUN_STATES), name="state_allowed"),
        sa.CheckConstraint(
            "repair_attempts_used BETWEEN 0 AND 1",
            name="repair_attempts_used_range",
        ),
        sa.CheckConstraint("retry_limit >= 0", name="retry_limit_non_negative"),
        sa.CheckConstraint(
            "retry_attempts_used >= 0 AND retry_attempts_used <= retry_limit",
            name="retry_attempts_used_range",
        ),
        sa.CheckConstraint(
            "step_attempts_used >= 0", name="step_attempts_used_non_negative"
        ),
        sa.CheckConstraint("version >= 0", name="version_non_negative"),
        sa.CheckConstraint(
            f"({_TERMINAL}) = (terminal_at IS NOT NULL)",
            name="terminal_at_matches_state",
        ),
        sa.CheckConstraint(_FAILURE_CODE_CHECK, name="failure_code_matches_state"),
        sa.CheckConstraint(
            "CASE WHEN state = 'ABSTAINED'"
            f" THEN {sql_in('abstention_code', ABSTENTION_CODES)}"
            " ELSE abstention_code IS NULL END",
            name="abstention_code_matches_state",
        ),
        sa.CheckConstraint(
            "CASE WHEN state = 'CANCELLED'"
            f" THEN {sql_in('cancellation_code', CANCELLATION_CODES)}"
            " ELSE cancellation_code IS NULL END",
            name="cancellation_code_matches_state",
        ),
        sa.CheckConstraint(
            f"CASE WHEN {_TERMINAL}"
            " THEN terminal_actor_type IS NOT NULL AND terminal_actor_id IS NOT NULL"
            " ELSE terminal_actor_type IS NULL AND terminal_actor_id IS NULL END",
            name="terminal_actor_matches_state",
        ),
        sa.CheckConstraint(
            "terminal_actor_type IS NULL OR "
            + sql_in("terminal_actor_type", TERMINAL_ACTOR_TYPES),
            name="terminal_actor_type_allowed",
        ),
        sa.CheckConstraint(
            "parent_run_id IS NULL OR parent_run_id <> id", name="parent_run_id_not_self"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # One current projection per durable request; regeneration creates a new
    # request and a new run rather than a second run under the same request.
    run_request_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("run_requests.id"), unique=True
    )
    state: Mapped[str] = mapped_column(sa.Text, default="RECEIVED")
    contract_version: Mapped[str] = mapped_column(sa.String(64))
    review_required: Mapped[bool] = mapped_column(default=True, server_default=sa.true())

    repair_attempts_used: Mapped[int] = mapped_column(
        sa.Integer, default=0, server_default="0"
    )
    retry_attempts_used: Mapped[int] = mapped_column(
        sa.Integer, default=0, server_default="0"
    )
    retry_limit: Mapped[int] = mapped_column(sa.Integer)
    step_attempts_used: Mapped[int] = mapped_column(
        sa.Integer, default=0, server_default="0"
    )
    version: Mapped[int] = mapped_column(sa.Integer, default=0, server_default="0")

    created_at: Mapped[datetime] = mapped_column(server_default=sa.func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=sa.func.now(), onupdate=sa.func.now()
    )
    terminal_at: Mapped[datetime | None]

    failure_code: Mapped[str | None] = mapped_column(sa.Text)
    abstention_code: Mapped[str | None] = mapped_column(sa.Text)
    cancellation_code: Mapped[str | None] = mapped_column(sa.Text)
    # Auth-owned human identity shape stays provisional, so attribution is a
    # bounded opaque value rather than a foreign key.
    terminal_actor_type: Mapped[str | None] = mapped_column(sa.Text)
    terminal_actor_id: Mapped[str | None] = mapped_column(sa.String(255))

    # Opaque reference only: never repository, patch, prompt, or log bytes.
    checkpoint_ref: Mapped[str | None] = mapped_column(sa.String(512))
    parent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("runs.id"), index=True
    )

    run_request: Mapped[RunRequest] = relationship(back_populates="run")
    parent_run: Mapped["Run | None"] = relationship(remote_side=[id])
    workflow_steps: Mapped[list["WorkflowStep"]] = relationship(
        back_populates="run"
    )
    events: Mapped[list["RunEvent"]] = relationship(
        back_populates="run", foreign_keys="RunEvent.run_id"
    )


class WorkflowStep(Base):
    """One immutable semantic step occurrence within a run."""

    __tablename__ = "workflow_steps"
    __table_args__ = (
        sa.UniqueConstraint("run_id", "kind", "occurrence"),
        # Supports the run/step/kind composite event-attribution foreign key.
        sa.UniqueConstraint("run_id", "id", "kind"),
        sa.CheckConstraint(sql_in("kind", WORKFLOW_STEP_KINDS), name="kind_allowed"),
        sa.CheckConstraint("occurrence > 0", name="occurrence_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("runs.id"), index=True)
    kind: Mapped[str] = mapped_column(sa.String(64))
    occurrence: Mapped[int] = mapped_column(sa.Integer)
    created_at: Mapped[datetime] = mapped_column(server_default=sa.func.now())
    input_reference: Mapped[str] = mapped_column(sa.String(512))
    input_version: Mapped[str] = mapped_column(sa.String(128))

    run: Mapped[Run] = relationship(back_populates="workflow_steps")
    attempts: Mapped[list["WorkflowStepAttempt"]] = relationship(
        back_populates="step"
    )


class WorkflowStepAttempt(Base):
    """One zero-based attempt under a WorkflowStep occurrence."""

    __tablename__ = "workflow_step_attempts"
    __table_args__ = (
        sa.UniqueConstraint("step_id", "attempt_index"),
        sa.CheckConstraint("attempt_index >= 0", name="attempt_index_non_negative"),
        sa.CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at",
            name="ended_at_not_before_started_at",
        ),
        sa.CheckConstraint(
            "(ended_at IS NULL AND outcome IS NULL)"
            " OR (ended_at IS NOT NULL AND outcome IS NOT NULL)",
            name="completion_shape",
        ),
        sa.CheckConstraint(
            sql_in("actor_type", TERMINAL_ACTOR_TYPES), name="actor_type_allowed"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    step_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("workflow_steps.id"), index=True
    )
    attempt_index: Mapped[int] = mapped_column(sa.Integer)
    started_at: Mapped[datetime]
    ended_at: Mapped[datetime | None]
    outcome: Mapped[str | None] = mapped_column(sa.String(128))
    actor_type: Mapped[str] = mapped_column(sa.String(32))
    actor_id: Mapped[str] = mapped_column(sa.String(255))
    error_reference: Mapped[str | None] = mapped_column(sa.String(512))
    evidence_reference: Mapped[str | None] = mapped_column(sa.String(512))

    step: Mapped[WorkflowStep] = relationship(back_populates="attempts")


class RunEvent(Base):
    """One ordered, producer-idempotent, append-only event in a run timeline."""

    __tablename__ = "run_events"
    __table_args__ = (
        sa.UniqueConstraint("run_id", "sequence"),
        sa.UniqueConstraint("run_id", "producer_event_id"),
        sa.ForeignKeyConstraint(
            ("run_id", "step_id", "step_kind"),
            ("workflow_steps.run_id", "workflow_steps.id", "workflow_steps.kind"),
        ),
        sa.ForeignKeyConstraint(
            ("step_id", "attempt_index"),
            ("workflow_step_attempts.step_id", "workflow_step_attempts.attempt_index"),
        ),
        sa.CheckConstraint("sequence > 0", name="sequence_positive"),
        sa.CheckConstraint(
            "CASE WHEN event_type = 'STATE_TRANSITIONED'"
            " THEN from_state IS NOT NULL AND to_state IS NOT NULL"
            " ELSE from_state IS NULL AND to_state IS NULL END",
            name="transition_state_shape",
        ),
        sa.CheckConstraint(
            "from_state IS NULL OR " + sql_in("from_state", RUN_STATES),
            name="from_state_allowed",
        ),
        sa.CheckConstraint(
            "to_state IS NULL OR " + sql_in("to_state", RUN_STATES),
            name="to_state_allowed",
        ),
        sa.CheckConstraint(_ALLOWED_TRANSITION_CHECK, name="transition_pair_allowed"),
        sa.CheckConstraint(
            "(step_id IS NULL) = (step_kind IS NULL)",
            name="step_attribution_shape",
        ),
        sa.CheckConstraint(
            "attempt_index IS NULL OR (step_id IS NOT NULL AND step_kind IS NOT NULL)",
            name="attempt_attribution_shape",
        ),
        sa.CheckConstraint(
            sql_in("actor_type", TERMINAL_ACTOR_TYPES), name="actor_type_allowed"
        ),
        sa.CheckConstraint(_EVENT_REASON_CHECK, name="terminal_reason_matches_target"),
        sa.CheckConstraint(
            "producer_event_fingerprint_version > 0",
            name="fingerprint_version_positive",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(payload) = 'object'", name="payload_is_object"
        ),
        sa.CheckConstraint(
            "octet_length(payload::text) <= 65536", name="payload_bounded"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("runs.id"), index=True)
    sequence: Mapped[int] = mapped_column(sa.Integer)
    event_type: Mapped[str] = mapped_column(sa.String(128))
    from_state: Mapped[str | None] = mapped_column(sa.String(64))
    to_state: Mapped[str | None] = mapped_column(sa.String(64))
    step_id: Mapped[uuid.UUID | None]
    step_kind: Mapped[str | None] = mapped_column(sa.String(64))
    attempt_index: Mapped[int | None] = mapped_column(sa.Integer)
    actor_type: Mapped[str] = mapped_column(sa.String(32))
    actor_id: Mapped[str] = mapped_column(sa.String(255))
    occurred_at: Mapped[datetime]
    recorded_at: Mapped[datetime] = mapped_column(server_default=sa.func.now())
    correlation_id: Mapped[str | None] = mapped_column(sa.String(255))
    causation_event_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("run_events.id")
    )
    producer_event_id: Mapped[str] = mapped_column(sa.String(255))
    contract_version: Mapped[str] = mapped_column(sa.String(64))
    payload_schema_version: Mapped[str] = mapped_column(sa.String(64))
    payload: Mapped[dict[str, object]] = mapped_column(
        JSONB, server_default=sa.text("'{}'::jsonb")
    )
    producer_event_fingerprint: Mapped[str] = mapped_column(sa.String(128))
    producer_event_fingerprint_version: Mapped[int] = mapped_column(sa.Integer)
    failure_code: Mapped[str | None] = mapped_column(sa.String(128))
    abstention_code: Mapped[str | None] = mapped_column(sa.String(64))
    cancellation_code: Mapped[str | None] = mapped_column(sa.String(64))

    run: Mapped[Run] = relationship(back_populates="events", foreign_keys=[run_id])
