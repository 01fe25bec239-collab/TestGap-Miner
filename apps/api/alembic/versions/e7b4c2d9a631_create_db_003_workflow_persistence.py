"""create DB-003 workflow persistence

Revision ID: e7b4c2d9a631
Revises: ad3f80907336
Create Date: 2026-08-10
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e7b4c2d9a631"
down_revision: str | Sequence[str] | None = "ad3f80907336"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workflow_steps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("occurrence", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("input_reference", sa.String(length=512), nullable=False),
        sa.Column("input_version", sa.String(length=128), nullable=False),
        sa.CheckConstraint(
            "kind IN ('VALIDATE_INPUT', 'PLAN', 'LOCALISE',"
            " 'GENERATE_CANDIDATE', 'EXECUTE_BUGGY', 'EXECUTE_FIXED',"
            " 'REPAIR_CANDIDATE', 'SCORE_EVIDENCE', 'PUBLISH_DRAFT',"
            " 'HUMAN_REVIEW')",
            name=op.f("ck_workflow_steps_kind_allowed"),
        ),
        sa.CheckConstraint(
            "occurrence > 0", name=op.f("ck_workflow_steps_occurrence_positive")
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["runs.id"],
            name=op.f("fk_workflow_steps_run_id_runs"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workflow_steps")),
        sa.UniqueConstraint(
            "run_id",
            "id",
            "kind",
            name=op.f("uq_workflow_steps_run_id_id_kind"),
        ),
        sa.UniqueConstraint(
            "run_id",
            "kind",
            "occurrence",
            name=op.f("uq_workflow_steps_run_id_kind_occurrence"),
        ),
    )
    op.create_index(
        op.f("ix_workflow_steps_run_id"),
        "workflow_steps",
        ["run_id"],
        unique=False,
    )

    op.create_table(
        "workflow_step_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("step_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_index", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.String(length=128), nullable=True),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.String(length=255), nullable=False),
        sa.Column("error_reference", sa.String(length=512), nullable=True),
        sa.Column("evidence_reference", sa.String(length=512), nullable=True),
        sa.CheckConstraint(
            "actor_type IN ('SYSTEM', 'WORKFLOW', 'WORKER', 'HUMAN')",
            name=op.f("ck_workflow_step_attempts_actor_type_allowed"),
        ),
        sa.CheckConstraint(
            "attempt_index >= 0",
            name=op.f("ck_workflow_step_attempts_attempt_index_non_negative"),
        ),
        sa.CheckConstraint(
            "(ended_at IS NULL AND outcome IS NULL)"
            " OR (ended_at IS NOT NULL AND outcome IS NOT NULL)",
            name=op.f("ck_workflow_step_attempts_completion_shape"),
        ),
        sa.CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at",
            name=op.f("ck_workflow_step_attempts_ended_at_not_before_started_at"),
        ),
        sa.ForeignKeyConstraint(
            ["step_id"],
            ["workflow_steps.id"],
            name=op.f("fk_workflow_step_attempts_step_id_workflow_steps"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workflow_step_attempts")),
        sa.UniqueConstraint(
            "step_id",
            "attempt_index",
            name=op.f("uq_workflow_step_attempts_step_id_attempt_index"),
        ),
    )
    op.create_index(
        op.f("ix_workflow_step_attempts_step_id"),
        "workflow_step_attempts",
        ["step_id"],
        unique=False,
    )

    op.create_table(
        "run_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("from_state", sa.String(length=64), nullable=True),
        sa.Column("to_state", sa.String(length=64), nullable=True),
        sa.Column("step_id", sa.Uuid(), nullable=True),
        sa.Column("step_kind", sa.String(length=64), nullable=True),
        sa.Column("attempt_index", sa.Integer(), nullable=True),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.String(length=255), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("correlation_id", sa.String(length=255), nullable=True),
        sa.Column("causation_event_id", sa.Uuid(), nullable=True),
        sa.Column("producer_event_id", sa.String(length=255), nullable=False),
        sa.Column("contract_version", sa.String(length=64), nullable=False),
        sa.Column("payload_schema_version", sa.String(length=64), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "producer_event_fingerprint", sa.String(length=128), nullable=False
        ),
        sa.Column("producer_event_fingerprint_version", sa.Integer(), nullable=False),
        sa.Column("failure_code", sa.String(length=128), nullable=True),
        sa.Column("abstention_code", sa.String(length=64), nullable=True),
        sa.Column("cancellation_code", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "actor_type IN ('SYSTEM', 'WORKFLOW', 'WORKER', 'HUMAN')",
            name=op.f("ck_run_events_actor_type_allowed"),
        ),
        sa.CheckConstraint(
            "attempt_index IS NULL OR (step_id IS NOT NULL AND step_kind IS NOT NULL)",
            name=op.f("ck_run_events_attempt_attribution_shape"),
        ),
        sa.CheckConstraint(
            "from_state IS NULL OR from_state IN ('RECEIVED', 'VALIDATING',"
            " 'QUEUED', 'PLANNING', 'LOCALISING', 'GENERATING',"
            " 'EXECUTING_BUGGY', 'EXECUTING_FIXED', 'REPAIRING', 'SCORING',"
            " 'PUBLISHING', 'AWAITING_HUMAN_REVIEW', 'COMPLETED', 'ABSTAINED',"
            " 'FAILED_INPUT', 'FAILED_MODEL', 'FAILED_EXECUTION',"
            " 'FAILED_INFRASTRUCTURE', 'FAILED_SECURITY', 'CANCELLED')",
            name=op.f("ck_run_events_from_state_allowed"),
        ),
        sa.CheckConstraint(
            "octet_length(payload::text) <= 65536",
            name=op.f("ck_run_events_payload_bounded"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(payload) = 'object'",
            name=op.f("ck_run_events_payload_is_object"),
        ),
        sa.CheckConstraint(
            "producer_event_fingerprint_version > 0",
            name=op.f("ck_run_events_fingerprint_version_positive"),
        ),
        sa.CheckConstraint(
            "sequence > 0", name=op.f("ck_run_events_sequence_positive")
        ),
        sa.CheckConstraint(
            "(step_id IS NULL) = (step_kind IS NULL)",
            name=op.f("ck_run_events_step_attribution_shape"),
        ),
        sa.CheckConstraint(
            "CASE"
            " WHEN event_type = 'STATE_TRANSITIONED' AND to_state = 'FAILED_INPUT'"
            " THEN failure_code IS NOT NULL"
            " AND failure_code ~ '^INPUT_[A-Z0-9]+(_[A-Z0-9]+)*$'"
            " AND abstention_code IS NULL AND cancellation_code IS NULL"
            " WHEN event_type = 'STATE_TRANSITIONED' AND to_state = 'FAILED_MODEL'"
            " THEN failure_code IS NOT NULL"
            " AND failure_code ~ '^MODEL_[A-Z0-9]+(_[A-Z0-9]+)*$'"
            " AND abstention_code IS NULL AND cancellation_code IS NULL"
            " WHEN event_type = 'STATE_TRANSITIONED'"
            " AND to_state = 'FAILED_EXECUTION' THEN failure_code IS NOT NULL"
            " AND failure_code ~ '^EXECUTION_[A-Z0-9]+(_[A-Z0-9]+)*$'"
            " AND abstention_code IS NULL AND cancellation_code IS NULL"
            " WHEN event_type = 'STATE_TRANSITIONED'"
            " AND to_state = 'FAILED_INFRASTRUCTURE' THEN failure_code IS NOT NULL"
            " AND failure_code ~ '^INFRASTRUCTURE_[A-Z0-9]+(_[A-Z0-9]+)*$'"
            " AND abstention_code IS NULL AND cancellation_code IS NULL"
            " WHEN event_type = 'STATE_TRANSITIONED' AND to_state = 'FAILED_SECURITY'"
            " THEN failure_code IS NOT NULL"
            " AND failure_code ~ '^SECURITY_[A-Z0-9]+(_[A-Z0-9]+)*$'"
            " AND abstention_code IS NULL AND cancellation_code IS NULL"
            " WHEN event_type = 'STATE_TRANSITIONED' AND to_state = 'ABSTAINED'"
            " THEN failure_code IS NULL"
            " AND abstention_code IN ('UNSUPPORTED_LANGUAGE_OR_TEST_FRAMEWORK',"
            " 'BUG_NOT_REPRODUCED', 'INSUFFICIENT_LOCALISATION_CONFIDENCE',"
            " 'INSUFFICIENT_CONTEXT', 'NO_SAFE_TEST_ONLY_PATCH',"
            " 'REPAIR_LIMIT_EXHAUSTED', 'EVIDENCE_INCONCLUSIVE',"
            " 'PUBLICATION_NOT_JUSTIFIED') AND cancellation_code IS NULL"
            " WHEN event_type = 'STATE_TRANSITIONED' AND to_state = 'CANCELLED'"
            " THEN failure_code IS NULL AND abstention_code IS NULL"
            " AND cancellation_code IN ('USER_REQUESTED', 'SUPERSEDED',"
            " 'OPERATOR_REQUESTED', 'SYSTEM_SHUTDOWN')"
            " ELSE failure_code IS NULL AND abstention_code IS NULL"
            " AND cancellation_code IS NULL END",
            name=op.f("ck_run_events_terminal_reason_matches_target"),
        ),
        sa.CheckConstraint(
            "to_state IS NULL OR to_state IN ('RECEIVED', 'VALIDATING', 'QUEUED',"
            " 'PLANNING', 'LOCALISING', 'GENERATING', 'EXECUTING_BUGGY',"
            " 'EXECUTING_FIXED', 'REPAIRING', 'SCORING', 'PUBLISHING',"
            " 'AWAITING_HUMAN_REVIEW', 'COMPLETED', 'ABSTAINED', 'FAILED_INPUT',"
            " 'FAILED_MODEL', 'FAILED_EXECUTION', 'FAILED_INFRASTRUCTURE',"
            " 'FAILED_SECURITY', 'CANCELLED')",
            name=op.f("ck_run_events_to_state_allowed"),
        ),
        sa.CheckConstraint(
            "CASE WHEN event_type = 'STATE_TRANSITIONED'"
            " THEN from_state IS NOT NULL AND to_state IS NOT NULL"
            " ELSE from_state IS NULL AND to_state IS NULL END",
            name=op.f("ck_run_events_transition_state_shape"),
        ),
        sa.CheckConstraint(
            "event_type <> 'STATE_TRANSITIONED' OR ("
            "(from_state = 'RECEIVED' AND to_state IN ('VALIDATING', 'CANCELLED')) OR"
            " (from_state = 'VALIDATING' AND to_state IN ('QUEUED', 'FAILED_INPUT',"
            " 'FAILED_INFRASTRUCTURE', 'FAILED_SECURITY', 'CANCELLED')) OR"
            " (from_state = 'QUEUED' AND to_state IN ('PLANNING',"
            " 'FAILED_INFRASTRUCTURE', 'FAILED_SECURITY', 'CANCELLED')) OR"
            " (from_state = 'PLANNING' AND to_state IN ('LOCALISING', 'ABSTAINED',"
            " 'FAILED_MODEL', 'FAILED_INFRASTRUCTURE', 'FAILED_SECURITY',"
            " 'CANCELLED')) OR"
            " (from_state = 'LOCALISING' AND to_state IN ('GENERATING', 'ABSTAINED',"
            " 'FAILED_MODEL', 'FAILED_INFRASTRUCTURE', 'FAILED_SECURITY',"
            " 'CANCELLED')) OR"
            " (from_state = 'GENERATING' AND to_state IN ('EXECUTING_BUGGY',"
            " 'ABSTAINED', 'FAILED_MODEL', 'FAILED_INFRASTRUCTURE',"
            " 'FAILED_SECURITY', 'CANCELLED')) OR"
            " (from_state = 'EXECUTING_BUGGY' AND to_state IN ('EXECUTING_FIXED',"
            " 'REPAIRING', 'ABSTAINED', 'FAILED_EXECUTION',"
            " 'FAILED_INFRASTRUCTURE', 'FAILED_SECURITY', 'CANCELLED')) OR"
            " (from_state = 'EXECUTING_FIXED' AND to_state IN ('REPAIRING',"
            " 'SCORING', 'ABSTAINED', 'FAILED_EXECUTION', 'FAILED_INFRASTRUCTURE',"
            " 'FAILED_SECURITY', 'CANCELLED')) OR"
            " (from_state = 'REPAIRING' AND to_state IN ('EXECUTING_BUGGY',"
            " 'ABSTAINED', 'FAILED_MODEL', 'FAILED_INFRASTRUCTURE',"
            " 'FAILED_SECURITY', 'CANCELLED')) OR"
            " (from_state = 'SCORING' AND to_state IN ('PUBLISHING',"
            " 'AWAITING_HUMAN_REVIEW', 'COMPLETED', 'ABSTAINED',"
            " 'FAILED_INFRASTRUCTURE', 'FAILED_SECURITY', 'CANCELLED')) OR"
            " (from_state = 'PUBLISHING' AND to_state IN ('AWAITING_HUMAN_REVIEW',"
            " 'COMPLETED', 'FAILED_INFRASTRUCTURE', 'FAILED_SECURITY',"
            " 'CANCELLED')) OR"
            " (from_state = 'AWAITING_HUMAN_REVIEW' AND to_state = 'COMPLETED'))",
            name=op.f("ck_run_events_transition_pair_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["causation_event_id"],
            ["run_events.id"],
            name=op.f("fk_run_events_causation_event_id_run_events"),
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["runs.id"], name=op.f("fk_run_events_run_id_runs")
        ),
        sa.ForeignKeyConstraint(
            ["run_id", "step_id", "step_kind"],
            ["workflow_steps.run_id", "workflow_steps.id", "workflow_steps.kind"],
            name=op.f("fk_run_events_run_id_step_id_step_kind_workflow_steps"),
        ),
        sa.ForeignKeyConstraint(
            ["step_id", "attempt_index"],
            [
                "workflow_step_attempts.step_id",
                "workflow_step_attempts.attempt_index",
            ],
            name=op.f(
                "fk_run_events_step_id_attempt_index_workflow_step_attempts"
            ),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_run_events")),
        sa.UniqueConstraint(
            "run_id",
            "producer_event_id",
            name=op.f("uq_run_events_run_id_producer_event_id"),
        ),
        sa.UniqueConstraint(
            "run_id", "sequence", name=op.f("uq_run_events_run_id_sequence")
        ),
    )
    op.create_index(
        op.f("ix_run_events_run_id"), "run_events", ["run_id"], unique=False
    )

    op.execute(
        """
        CREATE FUNCTION db003_reject_workflow_step_update()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'workflow_steps rows are immutable';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_db003_workflow_steps_immutable
        BEFORE UPDATE ON workflow_steps
        FOR EACH ROW EXECUTE FUNCTION db003_reject_workflow_step_update()
        """
    )

    op.execute(
        """
        CREATE FUNCTION db003_enforce_attempt_immutability()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'workflow attempts cannot be deleted';
            END IF;

            IF OLD.ended_at IS NOT NULL THEN
                RAISE EXCEPTION 'completed workflow attempts are immutable';
            END IF;

            IF NEW.id IS DISTINCT FROM OLD.id
               OR NEW.step_id IS DISTINCT FROM OLD.step_id
               OR NEW.attempt_index IS DISTINCT FROM OLD.attempt_index
               OR NEW.started_at IS DISTINCT FROM OLD.started_at
               OR NEW.actor_type IS DISTINCT FROM OLD.actor_type
               OR NEW.actor_id IS DISTINCT FROM OLD.actor_id THEN
                RAISE EXCEPTION 'workflow attempt identity fields are immutable';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_db003_workflow_attempts_immutable
        BEFORE UPDATE OR DELETE ON workflow_step_attempts
        FOR EACH ROW EXECUTE FUNCTION db003_enforce_attempt_immutability()
        """
    )

    op.execute(
        """
        CREATE FUNCTION db003_reject_run_event_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'run_events rows are append-only';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_db003_run_events_append_only
        BEFORE UPDATE OR DELETE ON run_events
        FOR EACH ROW EXECUTE FUNCTION db003_reject_run_event_mutation()
        """
    )

    op.execute(
        """
        CREATE FUNCTION db003_protect_terminal_run_facts()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF OLD.state IN (
                'COMPLETED', 'ABSTAINED', 'FAILED_INPUT', 'FAILED_MODEL',
                'FAILED_EXECUTION', 'FAILED_INFRASTRUCTURE', 'FAILED_SECURITY',
                'CANCELLED'
            ) AND (
                NEW.state IS DISTINCT FROM OLD.state
                OR NEW.terminal_at IS DISTINCT FROM OLD.terminal_at
                OR NEW.failure_code IS DISTINCT FROM OLD.failure_code
                OR NEW.abstention_code IS DISTINCT FROM OLD.abstention_code
                OR NEW.cancellation_code IS DISTINCT FROM OLD.cancellation_code
                OR NEW.terminal_actor_type IS DISTINCT FROM OLD.terminal_actor_type
                OR NEW.terminal_actor_id IS DISTINCT FROM OLD.terminal_actor_id
            ) THEN
                RAISE EXCEPTION 'terminal run facts are immutable';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_db003_runs_terminal_immutable
        BEFORE UPDATE ON runs
        FOR EACH ROW EXECUTE FUNCTION db003_protect_terminal_run_facts()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_db003_runs_terminal_immutable ON runs")
    op.execute("DROP FUNCTION db003_protect_terminal_run_facts()")
    op.execute("DROP TRIGGER trg_db003_run_events_append_only ON run_events")
    op.execute("DROP FUNCTION db003_reject_run_event_mutation()")
    op.execute(
        "DROP TRIGGER trg_db003_workflow_attempts_immutable"
        " ON workflow_step_attempts"
    )
    op.execute("DROP FUNCTION db003_enforce_attempt_immutability()")
    op.execute("DROP TRIGGER trg_db003_workflow_steps_immutable ON workflow_steps")
    op.execute("DROP FUNCTION db003_reject_workflow_step_update()")
    op.drop_index(op.f("ix_run_events_run_id"), table_name="run_events")
    op.drop_table("run_events")
    op.drop_index(
        op.f("ix_workflow_step_attempts_step_id"),
        table_name="workflow_step_attempts",
    )
    op.drop_table("workflow_step_attempts")
    op.drop_index(op.f("ix_workflow_steps_run_id"), table_name="workflow_steps")
    op.drop_table("workflow_steps")
