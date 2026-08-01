"""create DB-002 core entities

Revision ID: ad3f80907336
Revises: 
Create Date: 2026-08-01 19:43:55.593515
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'ad3f80907336'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # DB-002 only: canonical identity, repository context, and the workflow
    # run-request/current-run projections. No seed data, no DB-003 table.
    op.create_table('github_installations',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('github_installation_id', sa.BigInteger(), nullable=False),
    sa.Column('github_account_id', sa.BigInteger(), nullable=False),
    sa.Column('account_type', sa.Text(), nullable=False),
    sa.Column('status', sa.Text(), nullable=False),
    sa.Column('installed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('suspended_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_synced_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("account_type IN ('USER', 'ORGANIZATION')", name=op.f('ck_github_installations_account_type_allowed')),
    sa.CheckConstraint("status <> 'DELETED' OR deleted_at IS NOT NULL", name=op.f('ck_github_installations_deleted_at_present')),
    sa.CheckConstraint("status <> 'SUSPENDED' OR suspended_at IS NOT NULL", name=op.f('ck_github_installations_suspended_at_present')),
    sa.CheckConstraint("status IN ('ACTIVE', 'SUSPENDED', 'DELETED')", name=op.f('ck_github_installations_status_allowed')),
    sa.CheckConstraint('github_installation_id > 0 AND github_account_id > 0', name=op.f('ck_github_installations_github_ids_positive')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_github_installations')),
    sa.UniqueConstraint('github_installation_id', name=op.f('uq_github_installations_github_installation_id'))
    )
    op.create_table('repositories',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('github_repository_id', sa.BigInteger(), nullable=False),
    sa.Column('status', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_synced_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('ACTIVE', 'ARCHIVED', 'INACCESSIBLE', 'DELETED')", name=op.f('ck_repositories_status_allowed')),
    sa.CheckConstraint('github_repository_id > 0', name=op.f('ck_repositories_github_id_positive')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_repositories')),
    sa.UniqueConstraint('github_repository_id', name=op.f('uq_repositories_github_repository_id'))
    )
    op.create_table('users',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('status', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('suspended_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deprovisioned_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("status <> 'DEPROVISIONED' OR deprovisioned_at IS NOT NULL", name=op.f('ck_users_deprovisioned_at_present')),
    sa.CheckConstraint("status <> 'SUSPENDED' OR suspended_at IS NOT NULL", name=op.f('ck_users_suspended_at_present')),
    sa.CheckConstraint("status IN ('ACTIVE', 'SUSPENDED', 'DEPROVISIONED')", name=op.f('ck_users_status_allowed')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users'))
    )
    op.create_table('auth_subjects',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('issuer', sa.Text(), nullable=False),
    sa.Column('subject', sa.Text(), nullable=False),
    sa.Column('provider_name', sa.Text(), nullable=True),
    sa.Column('provider_account_id', sa.Text(), nullable=True),
    sa.Column('status', sa.Text(), nullable=False),
    sa.Column('linked_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("status <> 'REVOKED' OR revoked_at IS NOT NULL", name=op.f('ck_auth_subjects_revoked_at_present')),
    sa.CheckConstraint("status IN ('ACTIVE', 'REVOKED')", name=op.f('ck_auth_subjects_status_allowed')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_auth_subjects_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_auth_subjects')),
    sa.UniqueConstraint('issuer', 'subject', name=op.f('uq_auth_subjects_issuer_subject'))
    )
    op.create_index(op.f('ix_auth_subjects_user_id'), 'auth_subjects', ['user_id'], unique=False)
    op.create_table('repository_access',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('installation_id', sa.Uuid(), nullable=False),
    sa.Column('repository_id', sa.Uuid(), nullable=False),
    sa.Column('status', sa.Text(), nullable=False),
    sa.Column('authorization_source', sa.Text(), nullable=False),
    sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_verified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('expired_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("authorization_source IN ('GITHUB_VERIFIED')", name=op.f('ck_repository_access_authorization_source_allowed')),
    sa.CheckConstraint("status <> 'ACTIVE' OR (expired_at IS NULL AND revoked_at IS NULL)", name=op.f('ck_repository_access_active_not_terminated')),
    sa.CheckConstraint("status <> 'EXPIRED' OR ((expires_at IS NOT NULL OR expired_at IS NOT NULL) AND revoked_at IS NULL)", name=op.f('ck_repository_access_expiry_distinct_from_revocation')),
    sa.CheckConstraint("status <> 'REVOKED' OR revoked_at IS NOT NULL", name=op.f('ck_repository_access_revoked_at_present')),
    sa.CheckConstraint("status IN ('ACTIVE', 'REVOKED', 'EXPIRED')", name=op.f('ck_repository_access_status_allowed')),
    sa.ForeignKeyConstraint(['installation_id'], ['github_installations.id'], name=op.f('fk_repository_access_installation_id_github_installations')),
    sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], name=op.f('fk_repository_access_repository_id_repositories')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_repository_access_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_repository_access'))
    )
    op.create_index(op.f('ix_repository_access_installation_id'), 'repository_access', ['installation_id'], unique=False)
    op.create_index(op.f('ix_repository_access_repository_id'), 'repository_access', ['repository_id'], unique=False)
    op.create_index(op.f('ix_repository_access_user_id'), 'repository_access', ['user_id'], unique=False)
    op.create_index('uq_repository_access_active', 'repository_access', ['user_id', 'installation_id', 'repository_id'], unique=True, postgresql_where=sa.text("status = 'ACTIVE'"))
    op.create_table('run_requests',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('request_kind', sa.Text(), nullable=False),
    sa.Column('idempotency_key', sa.String(length=128), nullable=False),
    sa.Column('idempotency_key_version', sa.Integer(), nullable=False),
    sa.Column('request_fingerprint', sa.String(length=128), nullable=False),
    sa.Column('github_delivery_guid', sa.Text(), nullable=True),
    sa.Column('github_repository_id', sa.BigInteger(), nullable=True),
    sa.Column('repository_sha', sa.String(length=64), nullable=True),
    sa.Column('benchmark_project_id', sa.Text(), nullable=True),
    sa.Column('benchmark_bug_id', sa.Text(), nullable=True),
    sa.Column('configuration_version', sa.Text(), nullable=False),
    sa.Column('model_id', sa.Text(), nullable=False),
    sa.Column('prompt_template_version', sa.Text(), nullable=False),
    sa.Column('repository_id', sa.Uuid(), nullable=True),
    sa.Column('requested_by_subject', sa.Uuid(), nullable=True),
    sa.Column('correlation_id', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("CASE request_kind WHEN 'GITHUB' THEN github_delivery_guid IS NOT NULL AND github_repository_id IS NOT NULL AND repository_sha IS NOT NULL AND benchmark_project_id IS NULL AND benchmark_bug_id IS NULL WHEN 'BENCHMARK' THEN benchmark_project_id IS NOT NULL AND benchmark_bug_id IS NOT NULL AND github_delivery_guid IS NULL ELSE false END", name=op.f('ck_run_requests_kind_field_shape')),
    sa.CheckConstraint("request_kind IN ('GITHUB', 'BENCHMARK')", name=op.f('ck_run_requests_request_kind_allowed')),
    sa.CheckConstraint('github_repository_id IS NULL OR github_repository_id > 0', name=op.f('ck_run_requests_github_repository_id_positive')),
    sa.CheckConstraint('idempotency_key_version >= 1', name=op.f('ck_run_requests_idempotency_key_version_positive')),
    sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], name=op.f('fk_run_requests_repository_id_repositories')),
    sa.ForeignKeyConstraint(['requested_by_subject'], ['auth_subjects.id'], name=op.f('fk_run_requests_requested_by_subject_auth_subjects')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_run_requests')),
    sa.UniqueConstraint('idempotency_key_version', 'idempotency_key', name=op.f('uq_run_requests_idempotency_key_version_idempotency_key'))
    )
    op.create_index(op.f('ix_run_requests_repository_id'), 'run_requests', ['repository_id'], unique=False)
    op.create_index(op.f('ix_run_requests_requested_by_subject'), 'run_requests', ['requested_by_subject'], unique=False)
    op.create_table('runs',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('run_request_id', sa.Uuid(), nullable=False),
    sa.Column('state', sa.Text(), nullable=False),
    sa.Column('contract_version', sa.String(length=64), nullable=False),
    sa.Column('review_required', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('repair_attempts_used', sa.Integer(), server_default='0', nullable=False),
    sa.Column('retry_attempts_used', sa.Integer(), server_default='0', nullable=False),
    sa.Column('retry_limit', sa.Integer(), nullable=False),
    sa.Column('step_attempts_used', sa.Integer(), server_default='0', nullable=False),
    sa.Column('version', sa.Integer(), server_default='0', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('terminal_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('failure_code', sa.Text(), nullable=True),
    sa.Column('abstention_code', sa.Text(), nullable=True),
    sa.Column('cancellation_code', sa.Text(), nullable=True),
    sa.Column('terminal_actor_type', sa.Text(), nullable=True),
    sa.Column('terminal_actor_id', sa.String(length=255), nullable=True),
    sa.Column('checkpoint_ref', sa.String(length=512), nullable=True),
    sa.Column('parent_run_id', sa.Uuid(), nullable=True),
    sa.CheckConstraint("(state IN ('COMPLETED', 'ABSTAINED', 'FAILED_INPUT', 'FAILED_MODEL', 'FAILED_EXECUTION', 'FAILED_INFRASTRUCTURE', 'FAILED_SECURITY', 'CANCELLED')) = (terminal_at IS NOT NULL)", name=op.f('ck_runs_terminal_at_matches_state')),
    sa.CheckConstraint("CASE WHEN state = 'ABSTAINED' THEN abstention_code IN ('UNSUPPORTED_LANGUAGE_OR_TEST_FRAMEWORK', 'BUG_NOT_REPRODUCED', 'INSUFFICIENT_LOCALISATION_CONFIDENCE', 'INSUFFICIENT_CONTEXT', 'NO_SAFE_TEST_ONLY_PATCH', 'REPAIR_LIMIT_EXHAUSTED', 'EVIDENCE_INCONCLUSIVE', 'PUBLICATION_NOT_JUSTIFIED') ELSE abstention_code IS NULL END", name=op.f('ck_runs_abstention_code_matches_state')),
    sa.CheckConstraint("CASE WHEN state = 'CANCELLED' THEN cancellation_code IN ('USER_REQUESTED', 'SUPERSEDED', 'OPERATOR_REQUESTED', 'SYSTEM_SHUTDOWN') ELSE cancellation_code IS NULL END", name=op.f('ck_runs_cancellation_code_matches_state')),
    sa.CheckConstraint("CASE WHEN state IN ('COMPLETED', 'ABSTAINED', 'FAILED_INPUT', 'FAILED_MODEL', 'FAILED_EXECUTION', 'FAILED_INFRASTRUCTURE', 'FAILED_SECURITY', 'CANCELLED') THEN terminal_actor_type IS NOT NULL AND terminal_actor_id IS NOT NULL ELSE terminal_actor_type IS NULL AND terminal_actor_id IS NULL END", name=op.f('ck_runs_terminal_actor_matches_state')),
    sa.CheckConstraint("CASE state WHEN 'FAILED_INPUT' THEN failure_code IS NOT NULL AND failure_code ~ '^INPUT_[A-Z0-9]+(_[A-Z0-9]+)*$' WHEN 'FAILED_MODEL' THEN failure_code IS NOT NULL AND failure_code ~ '^MODEL_[A-Z0-9]+(_[A-Z0-9]+)*$' WHEN 'FAILED_EXECUTION' THEN failure_code IS NOT NULL AND failure_code ~ '^EXECUTION_[A-Z0-9]+(_[A-Z0-9]+)*$' WHEN 'FAILED_INFRASTRUCTURE' THEN failure_code IS NOT NULL AND failure_code ~ '^INFRASTRUCTURE_[A-Z0-9]+(_[A-Z0-9]+)*$' WHEN 'FAILED_SECURITY' THEN failure_code IS NOT NULL AND failure_code ~ '^SECURITY_[A-Z0-9]+(_[A-Z0-9]+)*$' ELSE failure_code IS NULL END", name=op.f('ck_runs_failure_code_matches_state')),
    sa.CheckConstraint("state IN ('RECEIVED', 'VALIDATING', 'QUEUED', 'PLANNING', 'LOCALISING', 'GENERATING', 'EXECUTING_BUGGY', 'EXECUTING_FIXED', 'REPAIRING', 'SCORING', 'PUBLISHING', 'AWAITING_HUMAN_REVIEW', 'COMPLETED', 'ABSTAINED', 'FAILED_INPUT', 'FAILED_MODEL', 'FAILED_EXECUTION', 'FAILED_INFRASTRUCTURE', 'FAILED_SECURITY', 'CANCELLED')", name=op.f('ck_runs_state_allowed')),
    sa.CheckConstraint("terminal_actor_type IS NULL OR terminal_actor_type IN ('SYSTEM', 'WORKFLOW', 'WORKER', 'HUMAN')", name=op.f('ck_runs_terminal_actor_type_allowed')),
    sa.CheckConstraint('parent_run_id IS NULL OR parent_run_id <> id', name=op.f('ck_runs_parent_run_id_not_self')),
    sa.CheckConstraint('repair_attempts_used BETWEEN 0 AND 1', name=op.f('ck_runs_repair_attempts_used_range')),
    sa.CheckConstraint('retry_attempts_used >= 0 AND retry_attempts_used <= retry_limit', name=op.f('ck_runs_retry_attempts_used_range')),
    sa.CheckConstraint('retry_limit >= 0', name=op.f('ck_runs_retry_limit_non_negative')),
    sa.CheckConstraint('step_attempts_used >= 0', name=op.f('ck_runs_step_attempts_used_non_negative')),
    sa.CheckConstraint('version >= 0', name=op.f('ck_runs_version_non_negative')),
    sa.ForeignKeyConstraint(['parent_run_id'], ['runs.id'], name=op.f('fk_runs_parent_run_id_runs')),
    sa.ForeignKeyConstraint(['run_request_id'], ['run_requests.id'], name=op.f('fk_runs_run_request_id_run_requests')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_runs')),
    sa.UniqueConstraint('run_request_id', name=op.f('uq_runs_run_request_id'))
    )
    op.create_index(op.f('ix_runs_parent_run_id'), 'runs', ['parent_run_id'], unique=False)


def downgrade() -> None:
    # Complete reversal to the zero-revision state while unconsumed.
    op.drop_index(op.f('ix_runs_parent_run_id'), table_name='runs')
    op.drop_table('runs')
    op.drop_index(op.f('ix_run_requests_requested_by_subject'), table_name='run_requests')
    op.drop_index(op.f('ix_run_requests_repository_id'), table_name='run_requests')
    op.drop_table('run_requests')
    op.drop_index('uq_repository_access_active', table_name='repository_access', postgresql_where=sa.text("status = 'ACTIVE'"))
    op.drop_index(op.f('ix_repository_access_user_id'), table_name='repository_access')
    op.drop_index(op.f('ix_repository_access_repository_id'), table_name='repository_access')
    op.drop_index(op.f('ix_repository_access_installation_id'), table_name='repository_access')
    op.drop_table('repository_access')
    op.drop_index(op.f('ix_auth_subjects_user_id'), table_name='auth_subjects')
    op.drop_table('auth_subjects')
    op.drop_table('users')
    op.drop_table('repositories')
    op.drop_table('github_installations')
