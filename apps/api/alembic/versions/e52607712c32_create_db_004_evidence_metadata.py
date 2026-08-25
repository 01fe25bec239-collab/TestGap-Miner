"""create DB-004 evidence metadata

Revision ID: e52607712c32
Revises: e7b4c2d9a631
Create Date: 2026-08-22 21:41:46.974430
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'e52607712c32'
down_revision: str | Sequence[str] | None = 'e7b4c2d9a631'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # DB-004 only: RAG context-selection metadata plus Evidence-owned
    # candidate, execution, artefact, and manifest metadata. No seed data, no
    # object-storage dependency, and no byte-payload column anywhere.
    op.create_table('rag_context_bundles',
    sa.Column('context_bundle_id', sa.String(length=256), nullable=False),
    sa.Column('repository_id', sa.String(length=256), nullable=False),
    sa.Column('revision_id', sa.String(length=64), nullable=False),
    sa.Column('contract_version', sa.String(length=64), nullable=False),
    sa.Column('max_tokens', sa.Integer(), nullable=False),
    sa.Column('consumed_tokens', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('consumed_tokens <= max_tokens', name=op.f('ck_rag_context_bundles_consumed_tokens_within_budget')),
    sa.CheckConstraint('consumed_tokens BETWEEN 0 AND 2000000', name=op.f('ck_rag_context_bundles_consumed_tokens_range')),
    sa.CheckConstraint('max_tokens BETWEEN 1 AND 2000000', name=op.f('ck_rag_context_bundles_max_tokens_range')),
    sa.PrimaryKeyConstraint('context_bundle_id', name=op.f('pk_rag_context_bundles'))
    )
    op.create_table('rag_context_items',
    sa.Column('context_item_id', sa.String(length=256), nullable=False),
    sa.Column('context_bundle_id', sa.String(length=256), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('candidate_id', sa.String(length=256), nullable=False),
    sa.Column('file_identity', sa.Text(), nullable=False),
    sa.Column('start_line', sa.Integer(), nullable=False),
    sa.Column('end_line', sa.Integer(), nullable=False),
    sa.Column('content_sha256', sa.String(length=64), nullable=False),
    sa.Column('trust_label', sa.Text(), nullable=False),
    sa.Column('token_count', sa.Integer(), nullable=False),
    sa.CheckConstraint("trust_label IN ('UNTRUSTED_REPOSITORY_TEXT')", name=op.f('ck_rag_context_items_trust_label_allowed')),
    sa.CheckConstraint('end_line >= start_line', name=op.f('ck_rag_context_items_end_line_not_before_start')),
    sa.CheckConstraint('octet_length(file_identity) <= 4096', name=op.f('ck_rag_context_items_file_identity_bounded')),
    sa.CheckConstraint('position >= 1', name=op.f('ck_rag_context_items_position_positive')),
    sa.CheckConstraint('start_line > 0', name=op.f('ck_rag_context_items_start_line_positive')),
    sa.CheckConstraint('token_count > 0', name=op.f('ck_rag_context_items_token_count_positive')),
    sa.ForeignKeyConstraint(['context_bundle_id'], ['rag_context_bundles.context_bundle_id'], name=op.f('fk_rag_context_items_context_bundle_id_rag_context_bundles')),
    sa.PrimaryKeyConstraint('context_item_id', name=op.f('pk_rag_context_items')),
    sa.UniqueConstraint('context_bundle_id', 'position', name='uq_rag_context_items_bundle_position')
    )
    op.create_index(op.f('ix_rag_context_items_context_bundle_id'), 'rag_context_items', ['context_bundle_id'], unique=False)
    op.create_table('candidate_patch_records',
    sa.Column('candidate_patch_id', sa.String(length=255), nullable=False),
    sa.Column('candidate_version_id', sa.String(length=255), nullable=False),
    sa.Column('run_id', sa.Uuid(), nullable=False),
    sa.Column('workflow_attempt_id', sa.Uuid(), nullable=False),
    sa.Column('source_repository', sa.Text(), nullable=False),
    sa.Column('source_revision', sa.Text(), nullable=False),
    sa.Column('target_reference_revision', sa.Text(), nullable=True),
    sa.Column('patch_digest', sa.Text(), nullable=False),
    sa.Column('digest_algorithm', sa.Text(), nullable=False),
    sa.Column('test_only_scope', sa.Boolean(), nullable=False),
    sa.Column('test_only_scope_reference', sa.Text(), nullable=False),
    sa.Column('generator_reference', sa.Text(), nullable=False),
    sa.Column('tool_version_reference', sa.Text(), nullable=False),
    sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('configuration_version', sa.Text(), nullable=False),
    sa.Column('finalization_state', sa.String(length=16), nullable=False),
    sa.Column('finalized_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('patch_content_reference', sa.Text(), nullable=True),
    sa.Column('model_identifier', sa.Text(), nullable=True),
    sa.Column('prompt_template_version', sa.Text(), nullable=True),
    sa.Column('localisation_provenance_reference', sa.Text(), nullable=True),
    sa.Column('correlation_id', sa.String(length=255), nullable=True),
    sa.Column('contract_version', sa.String(length=64), nullable=False),
    sa.CheckConstraint("(finalization_state = 'FINALIZED') = (finalized_at IS NOT NULL)", name=op.f('ck_candidate_patch_records_finalized_at_matches_state')),
    sa.CheckConstraint("finalization_state IN ('CREATED', 'FINALIZED')", name=op.f('ck_candidate_patch_records_finalization_state_allowed')),
    sa.CheckConstraint('octet_length(configuration_version) <= 16384', name=op.f('ck_candidate_patch_records_configuration_version_bounded')),
    sa.CheckConstraint('octet_length(digest_algorithm) <= 16384', name=op.f('ck_candidate_patch_records_digest_algorithm_bounded')),
    sa.CheckConstraint('octet_length(generator_reference) <= 16384', name=op.f('ck_candidate_patch_records_generator_reference_bounded')),
    sa.CheckConstraint('octet_length(localisation_provenance_reference) <= 16384', name=op.f('ck_candidate_patch_records_localisation_provenance_bounded')),
    sa.CheckConstraint('octet_length(model_identifier) <= 16384', name=op.f('ck_candidate_patch_records_model_identifier_bounded')),
    sa.CheckConstraint('octet_length(patch_content_reference) <= 16384', name=op.f('ck_candidate_patch_records_patch_content_reference_bounded')),
    sa.CheckConstraint('octet_length(patch_digest) <= 16384', name=op.f('ck_candidate_patch_records_patch_digest_bounded')),
    sa.CheckConstraint('octet_length(prompt_template_version) <= 16384', name=op.f('ck_candidate_patch_records_prompt_template_version_bounded')),
    sa.CheckConstraint('octet_length(source_repository) <= 16384', name=op.f('ck_candidate_patch_records_source_repository_bounded')),
    sa.CheckConstraint('octet_length(source_revision) <= 16384', name=op.f('ck_candidate_patch_records_source_revision_bounded')),
    sa.CheckConstraint('octet_length(target_reference_revision) <= 16384', name=op.f('ck_candidate_patch_records_target_reference_revision_bounded')),
    sa.CheckConstraint('octet_length(test_only_scope_reference) <= 16384', name=op.f('ck_candidate_patch_records_test_only_scope_reference_bounded')),
    sa.CheckConstraint('octet_length(tool_version_reference) <= 16384', name=op.f('ck_candidate_patch_records_tool_version_reference_bounded')),
    sa.ForeignKeyConstraint(['run_id'], ['runs.id'], name=op.f('fk_candidate_patch_records_run_id_runs')),
    sa.ForeignKeyConstraint(['workflow_attempt_id'], ['workflow_step_attempts.id'], name='fk_candidate_patch_records_workflow_attempt_id'),
    sa.PrimaryKeyConstraint('candidate_patch_id', name=op.f('pk_candidate_patch_records')),
    sa.UniqueConstraint('candidate_version_id', name=op.f('uq_candidate_patch_records_candidate_version_id'))
    )
    op.create_index(op.f('ix_candidate_patch_records_run_id'), 'candidate_patch_records', ['run_id'], unique=False)
    op.create_index(op.f('ix_candidate_patch_records_workflow_attempt_id'), 'candidate_patch_records', ['workflow_attempt_id'], unique=False)
    op.create_table('candidate_changed_files',
    sa.Column('candidate_patch_id', sa.String(length=255), nullable=False),
    sa.Column('path', sa.Text(), nullable=False),
    sa.Column('change_summary', sa.Text(), nullable=False),
    sa.CheckConstraint("path <> ''", name=op.f('ck_candidate_changed_files_path_nonempty')),
    sa.CheckConstraint("path NOT LIKE '/%%'", name=op.f('ck_candidate_changed_files_path_repository_relative')),
    sa.CheckConstraint('octet_length(change_summary) <= 16384', name=op.f('ck_candidate_changed_files_change_summary_bounded')),
    sa.CheckConstraint('octet_length(path) <= 4096', name=op.f('ck_candidate_changed_files_path_bounded')),
    sa.ForeignKeyConstraint(['candidate_patch_id'], ['candidate_patch_records.candidate_patch_id'], name='fk_candidate_changed_files_candidate_patch_id'),
    sa.PrimaryKeyConstraint('candidate_patch_id', 'path', name=op.f('pk_candidate_changed_files'))
    )
    op.create_table('candidate_version_records',
    sa.Column('candidate_version_id', sa.String(length=255), nullable=False),
    sa.Column('candidate_patch_id', sa.String(length=255), nullable=False),
    sa.Column('run_id', sa.Uuid(), nullable=False),
    sa.Column('workflow_attempt_id', sa.Uuid(), nullable=False),
    sa.Column('producer_result_id', sa.String(length=255), nullable=True),
    sa.Column('repair_level', sa.Integer(), nullable=False),
    sa.Column('parent_candidate_version_id', sa.String(length=255), nullable=True),
    sa.Column('source_repository', sa.Text(), nullable=False),
    sa.Column('source_revision', sa.Text(), nullable=False),
    sa.Column('target_reference_revision', sa.Text(), nullable=True),
    sa.Column('generator_reference', sa.Text(), nullable=False),
    sa.Column('tool_version_reference', sa.Text(), nullable=False),
    sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('configuration_version', sa.Text(), nullable=False),
    sa.Column('finalization_state', sa.String(length=16), nullable=False),
    sa.Column('finalized_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('model_identifier', sa.Text(), nullable=True),
    sa.Column('prompt_template_version', sa.Text(), nullable=True),
    sa.Column('localisation_provenance_reference', sa.Text(), nullable=True),
    sa.Column('correlation_id', sa.String(length=255), nullable=True),
    sa.Column('contract_version', sa.String(length=64), nullable=False),
    sa.CheckConstraint("finalization_state IN ('CREATED', 'FINALIZED')", name=op.f('ck_candidate_version_records_finalization_state_allowed')),
    sa.CheckConstraint('(repair_level = 0 AND parent_candidate_version_id IS NULL) OR (repair_level = 1 AND parent_candidate_version_id IS NOT NULL)', name=op.f('ck_candidate_version_records_lineage_shape_matches_repair_level')),
    sa.CheckConstraint('octet_length(configuration_version) <= 16384', name=op.f('ck_candidate_version_records_configuration_version_bounded')),
    sa.CheckConstraint('octet_length(generator_reference) <= 16384', name=op.f('ck_candidate_version_records_generator_reference_bounded')),
    sa.CheckConstraint('octet_length(localisation_provenance_reference) <= 16384', name=op.f('ck_candidate_version_records_localisation_provenance_bounded')),
    sa.CheckConstraint('octet_length(model_identifier) <= 16384', name=op.f('ck_candidate_version_records_model_identifier_bounded')),
    sa.CheckConstraint('octet_length(prompt_template_version) <= 16384', name=op.f('ck_candidate_version_records_prompt_template_version_bounded')),
    sa.CheckConstraint('octet_length(source_repository) <= 16384', name=op.f('ck_candidate_version_records_source_repository_bounded')),
    sa.CheckConstraint('octet_length(source_revision) <= 16384', name=op.f('ck_candidate_version_records_source_revision_bounded')),
    sa.CheckConstraint('octet_length(target_reference_revision) <= 16384', name=op.f('ck_candidate_version_records_target_reference_revision_bounded')),
    sa.CheckConstraint('octet_length(tool_version_reference) <= 16384', name=op.f('ck_candidate_version_records_tool_version_reference_bounded')),
    sa.CheckConstraint('parent_candidate_version_id IS NULL OR parent_candidate_version_id <> candidate_version_id', name=op.f('ck_candidate_version_records_parent_not_self')),
    sa.CheckConstraint('repair_level IN (0, 1)', name=op.f('ck_candidate_version_records_repair_level_allowed')),
    sa.ForeignKeyConstraint(['candidate_patch_id'], ['candidate_patch_records.candidate_patch_id'], name='fk_candidate_version_records_candidate_patch_id'),
    sa.ForeignKeyConstraint(['parent_candidate_version_id'], ['candidate_version_records.candidate_version_id'], name='fk_candidate_version_records_parent_candidate_version'),
    sa.ForeignKeyConstraint(['run_id'], ['runs.id'], name=op.f('fk_candidate_version_records_run_id_runs')),
    sa.ForeignKeyConstraint(['workflow_attempt_id'], ['workflow_step_attempts.id'], name='fk_candidate_version_records_workflow_attempt_id'),
    sa.PrimaryKeyConstraint('candidate_version_id', name=op.f('pk_candidate_version_records'))
    )
    op.create_index(op.f('ix_candidate_version_records_candidate_patch_id'), 'candidate_version_records', ['candidate_patch_id'], unique=False)
    op.create_index(op.f('ix_candidate_version_records_parent_candidate_version_id'), 'candidate_version_records', ['parent_candidate_version_id'], unique=False)
    op.create_index(op.f('ix_candidate_version_records_run_id'), 'candidate_version_records', ['run_id'], unique=False)
    op.create_index(op.f('ix_candidate_version_records_workflow_attempt_id'), 'candidate_version_records', ['workflow_attempt_id'], unique=False)
    op.create_table('execution_evidence_records',
    sa.Column('execution_evidence_id', sa.String(length=255), nullable=False),
    sa.Column('producer_result_id', sa.String(length=255), nullable=False),
    sa.Column('queue_message_id', sa.String(length=255), nullable=True),
    sa.Column('queue_delivery_id', sa.String(length=255), nullable=True),
    sa.Column('correlation_id', sa.String(length=255), nullable=True),
    sa.Column('candidate_version_id', sa.String(length=255), nullable=False),
    sa.Column('run_id', sa.Uuid(), nullable=True),
    sa.Column('workflow_attempt_id', sa.Uuid(), nullable=False),
    sa.Column('execution_phase', sa.String(length=64), nullable=False),
    sa.Column('outcome', sa.String(length=64), nullable=False),
    sa.Column('completeness', sa.String(length=32), nullable=False),
    sa.Column('command_reference', sa.Text(), nullable=False),
    sa.Column('execution_fact_reference', sa.Text(), nullable=False),
    sa.Column('source_revision', sa.Text(), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('duration_microseconds', sa.BigInteger(), nullable=True),
    sa.Column('timing_fact_reference', sa.Text(), nullable=True),
    sa.Column('timeout_timed_out', sa.Boolean(), nullable=True),
    sa.Column('timeout_classification', sa.Text(), nullable=True),
    sa.Column('timeout_limit_microseconds', sa.BigInteger(), nullable=True),
    sa.Column('timeout_fact_reference', sa.Text(), nullable=True),
    sa.Column('exit_code', sa.Integer(), nullable=True),
    sa.Column('signal_number', sa.Integer(), nullable=True),
    sa.Column('signal_name', sa.String(length=255), nullable=True),
    sa.Column('exit_fact_reference', sa.Text(), nullable=True),
    sa.Column('integrity_state', sa.String(length=16), nullable=True),
    sa.Column('integrity_verification_reference', sa.Text(), nullable=True),
    sa.Column('runtime_metadata_reference', sa.Text(), nullable=True),
    sa.Column('sandbox_metadata_reference', sa.Text(), nullable=True),
    sa.Column('environment_metadata_reference', sa.Text(), nullable=True),
    sa.Column('flake_indication_reference', sa.Text(), nullable=True),
    sa.Column('failure_category', sa.String(length=64), nullable=True),
    sa.Column('failure_reference', sa.Text(), nullable=True),
    sa.Column('secondary_failures', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('compile_status', sa.String(length=16), nullable=True),
    sa.Column('compile_error_count', sa.Integer(), nullable=True),
    sa.Column('compile_warning_count', sa.Integer(), nullable=True),
    sa.Column('compile_metadata_reference', sa.Text(), nullable=True),
    sa.Column('test_executed_count', sa.Integer(), nullable=True),
    sa.Column('test_passed_count', sa.Integer(), nullable=True),
    sa.Column('test_failed_count', sa.Integer(), nullable=True),
    sa.Column('test_skipped_count', sa.Integer(), nullable=True),
    sa.Column('test_errored_count', sa.Integer(), nullable=True),
    sa.Column('test_failure_summary_reference', sa.Text(), nullable=True),
    sa.Column('contract_version', sa.String(length=64), nullable=False),
    sa.CheckConstraint("CASE WHEN execution_phase = 'COMPILE' THEN compile_status IS NOT NULL AND test_executed_count IS NULL AND test_passed_count IS NULL AND test_failed_count IS NULL AND test_skipped_count IS NULL AND test_errored_count IS NULL AND test_failure_summary_reference IS NULL ELSE compile_status IS NULL AND compile_error_count IS NULL AND compile_warning_count IS NULL AND compile_metadata_reference IS NULL END", name=op.f('ck_execution_evidence_records_phase_structured_result_shape')),
    sa.CheckConstraint("CASE WHEN outcome = 'SUCCESS' THEN compile_status IS NULL OR compile_status = 'SUCCESS' WHEN outcome = 'COMPILATION_FAILURE' THEN compile_status IS NULL OR compile_status = 'FAILURE' ELSE compile_status IS NULL OR compile_status = 'NOT_COMPLETED' END", name=op.f('ck_execution_evidence_records_compile_status_matches_outcome')),
    sa.CheckConstraint("CASE outcome WHEN 'COMPILATION_FAILURE' THEN failure_category = 'COMPILATION_FAILURE' WHEN 'TEST_FAILURE' THEN failure_category = 'TEST_FAILURE' WHEN 'TIMEOUT' THEN failure_category = 'TIMEOUT' WHEN 'CANCELLATION' THEN failure_category = 'CANCELLATION' WHEN 'RESOURCE_BREACH' THEN failure_category = 'RESOURCE_BREACH' WHEN 'RUNNER_ERROR' THEN failure_category = 'RUNNER_ERROR' ELSE failure_category IS NULL AND failure_reference IS NULL AND secondary_failures IS NULL END", name=op.f('ck_execution_evidence_records_failure_evidence_matches_outcome')),
    sa.CheckConstraint("NOT (outcome = 'COMPILATION_FAILURE' AND execution_phase <> 'COMPILE') AND NOT (outcome = 'TEST_FAILURE' AND execution_phase = 'COMPILE')", name=op.f('ck_execution_evidence_records_phase_outcome_compatible')),
    sa.CheckConstraint("NOT (outcome = 'SUCCESS' AND (COALESCE(test_failed_count, 0) > 0 OR COALESCE(test_errored_count, 0) > 0))", name=op.f('ck_execution_evidence_records_success_has_no_test_failures')),
    sa.CheckConstraint("compile_status IN ('SUCCESS', 'FAILURE', 'NOT_COMPLETED')", name=op.f('ck_execution_evidence_records_compile_status_allowed')),
    sa.CheckConstraint("completeness IN ('COMPLETE', 'PARTIAL', 'UNAVAILABLE', 'INVALID', 'CONFLICTING', 'REDACTED', 'DELETED_OR_TOMBSTONED')", name=op.f('ck_execution_evidence_records_completeness_allowed')),
    sa.CheckConstraint("execution_phase IN ('COMPILE', 'BUGGY_OR_TARGET_REVISION_TEST', 'FIXED_OR_REFERENCE_REVISION_TEST')", name=op.f('ck_execution_evidence_records_execution_phase_allowed')),
    sa.CheckConstraint("failure_category IN ('COMPILATION_FAILURE', 'TEST_FAILURE', 'TIMEOUT', 'CANCELLATION', 'RESOURCE_BREACH', 'RUNNER_ERROR')", name=op.f('ck_execution_evidence_records_failure_category_allowed')),
    sa.CheckConstraint("integrity_state <> 'VERIFIED' OR integrity_verification_reference IS NOT NULL", name=op.f('ck_execution_evidence_records_integrity_verification_required')),
    sa.CheckConstraint("integrity_state IN ('VERIFIED', 'UNVERIFIABLE', 'CORRUPT', 'TAMPERED', 'MISSING', 'DELETED')", name=op.f('ck_execution_evidence_records_integrity_state_allowed')),
    sa.CheckConstraint("jsonb_typeof(secondary_failures) = 'array'", name=op.f('ck_execution_evidence_records_secondary_failures_is_array')),
    sa.CheckConstraint("outcome IN ('SUCCESS', 'COMPILATION_FAILURE', 'TEST_FAILURE', 'TIMEOUT', 'CANCELLATION', 'RESOURCE_BREACH', 'RUNNER_ERROR', 'UNAVAILABLE', 'NOT_RUN')", name=op.f('ck_execution_evidence_records_outcome_allowed')),
    sa.CheckConstraint('duration_microseconds IS NULL OR duration_microseconds >= 0', name=op.f('ck_execution_evidence_records_duration_non_negative')),
    sa.CheckConstraint('ended_at IS NULL OR started_at IS NULL OR ended_at >= started_at', name=op.f('ck_execution_evidence_records_ended_at_not_before_started_at')),
    sa.CheckConstraint('octet_length(command_reference) <= 16384', name=op.f('ck_execution_evidence_records_command_reference_bounded')),
    sa.CheckConstraint('octet_length(compile_metadata_reference) <= 16384', name=op.f('ck_execution_evidence_records_compile_metadata_bounded')),
    sa.CheckConstraint('octet_length(environment_metadata_reference) <= 16384', name=op.f('ck_execution_evidence_records_environment_metadata_bounded')),
    sa.CheckConstraint('octet_length(execution_fact_reference) <= 16384', name=op.f('ck_execution_evidence_records_execution_fact_reference_bounded')),
    sa.CheckConstraint('octet_length(exit_fact_reference) <= 16384', name=op.f('ck_execution_evidence_records_exit_fact_reference_bounded')),
    sa.CheckConstraint('octet_length(failure_reference) <= 16384', name=op.f('ck_execution_evidence_records_failure_reference_bounded')),
    sa.CheckConstraint('octet_length(flake_indication_reference) <= 16384', name=op.f('ck_execution_evidence_records_flake_indication_bounded')),
    sa.CheckConstraint('octet_length(integrity_verification_reference) <= 16384', name=op.f('ck_execution_evidence_records_integrity_verification_bounded')),
    sa.CheckConstraint('octet_length(runtime_metadata_reference) <= 16384', name=op.f('ck_execution_evidence_records_runtime_metadata_bounded')),
    sa.CheckConstraint('octet_length(sandbox_metadata_reference) <= 16384', name=op.f('ck_execution_evidence_records_sandbox_metadata_bounded')),
    sa.CheckConstraint('octet_length(secondary_failures::text) <= 65536', name=op.f('ck_execution_evidence_records_secondary_failures_bounded')),
    sa.CheckConstraint('octet_length(signal_name) <= 255', name=op.f('ck_execution_evidence_records_signal_name_bounded')),
    sa.CheckConstraint('octet_length(source_revision) <= 16384', name=op.f('ck_execution_evidence_records_source_revision_bounded')),
    sa.CheckConstraint('octet_length(test_failure_summary_reference) <= 16384', name=op.f('ck_execution_evidence_records_test_failure_summary_bounded')),
    sa.CheckConstraint('octet_length(timing_fact_reference) <= 16384', name=op.f('ck_execution_evidence_records_timing_fact_reference_bounded')),
    sa.CheckConstraint('octet_length(timeout_classification) <= 16384', name=op.f('ck_execution_evidence_records_timeout_classification_bounded')),
    sa.CheckConstraint('octet_length(timeout_fact_reference) <= 16384', name=op.f('ck_execution_evidence_records_timeout_fact_reference_bounded')),
    sa.CheckConstraint('signal_number IS NULL OR signal_number > 0', name=op.f('ck_execution_evidence_records_signal_number_positive')),
    sa.CheckConstraint('test_executed_count IS NULL OR test_executed_count >= COALESCE(test_passed_count, 0) + COALESCE(test_failed_count, 0) + COALESCE(test_skipped_count, 0) + COALESCE(test_errored_count, 0)', name=op.f('ck_execution_evidence_records_test_counts_within_executed')),
    sa.CheckConstraint('timeout_limit_microseconds IS NULL OR timeout_limit_microseconds >= 0', name=op.f('ck_execution_evidence_records_timeout_limit_non_negative')),
    sa.CheckConstraint('timeout_timed_out IS NOT TRUE OR timeout_classification IS NOT NULL', name=op.f('ck_execution_evidence_records_timeout_requires_classification')),
    sa.ForeignKeyConstraint(['candidate_version_id'], ['candidate_version_records.candidate_version_id'], name='fk_execution_evidence_records_candidate_version_id'),
    sa.ForeignKeyConstraint(['run_id'], ['runs.id'], name=op.f('fk_execution_evidence_records_run_id_runs')),
    sa.ForeignKeyConstraint(['workflow_attempt_id'], ['workflow_step_attempts.id'], name='fk_execution_evidence_records_workflow_attempt_id'),
    sa.PrimaryKeyConstraint('execution_evidence_id', name=op.f('pk_execution_evidence_records'))
    )
    op.create_index(op.f('ix_execution_evidence_records_candidate_version_id'), 'execution_evidence_records', ['candidate_version_id'], unique=False)
    op.create_index(op.f('ix_execution_evidence_records_run_id'), 'execution_evidence_records', ['run_id'], unique=False)
    op.create_index(op.f('ix_execution_evidence_records_workflow_attempt_id'), 'execution_evidence_records', ['workflow_attempt_id'], unique=False)
    op.create_table('artefact_manifests',
    sa.Column('artefact_manifest_id', sa.String(length=255), nullable=False),
    sa.Column('creation_timestamp', sa.DateTime(timezone=True), nullable=False),
    sa.Column('finalization_state', sa.String(length=16), nullable=False),
    sa.Column('candidate_version_id', sa.String(length=255), nullable=True),
    sa.Column('execution_evidence_id', sa.String(length=255), nullable=True),
    sa.Column('workflow_attempt_id', sa.Uuid(), nullable=True),
    sa.Column('execution_phase', sa.String(length=64), nullable=True),
    sa.Column('producer_provenance_reference', sa.Text(), nullable=True),
    sa.Column('manifest_digest', sa.Text(), nullable=True),
    sa.Column('manifest_digest_algorithm', sa.Text(), nullable=True),
    sa.Column('integrity_state', sa.String(length=16), nullable=True),
    sa.Column('integrity_verification_reference', sa.Text(), nullable=True),
    sa.Column('finalization_timestamp', sa.DateTime(timezone=True), nullable=True),
    sa.Column('contract_version', sa.String(length=64), nullable=False),
    sa.Column('schema_version', sa.String(length=64), nullable=False),
    sa.CheckConstraint("execution_phase IN ('COMPILE', 'BUGGY_OR_TARGET_REVISION_TEST', 'FIXED_OR_REFERENCE_REVISION_TEST')", name=op.f('ck_artefact_manifests_execution_phase_allowed')),
    sa.CheckConstraint("finalization_state <> 'ASSEMBLING' OR finalization_timestamp IS NULL", name=op.f('ck_artefact_manifests_assembling_has_no_finalization_timestamp')),
    sa.CheckConstraint("finalization_state <> 'FINALIZED' OR ( finalization_timestamp IS NOT NULL AND producer_provenance_reference IS NOT NULL AND manifest_digest IS NOT NULL AND manifest_digest_algorithm IS NOT NULL AND integrity_state IS NOT NULL)", name=op.f('ck_artefact_manifests_finalized_requires_final_metadata')),
    sa.CheckConstraint("finalization_state IN ('ASSEMBLING', 'FINALIZED')", name=op.f('ck_artefact_manifests_finalization_state_allowed')),
    sa.CheckConstraint("integrity_state <> 'VERIFIED' OR integrity_verification_reference IS NOT NULL", name=op.f('ck_artefact_manifests_verified_integrity_requires_reference')),
    sa.CheckConstraint("integrity_state IN ('VERIFIED', 'UNVERIFIABLE', 'CORRUPT', 'TAMPERED', 'MISSING', 'DELETED')", name=op.f('ck_artefact_manifests_integrity_state_allowed')),
    sa.CheckConstraint('(manifest_digest IS NULL) = (manifest_digest_algorithm IS NULL)', name=op.f('ck_artefact_manifests_manifest_digest_pairing')),
    sa.CheckConstraint('finalization_timestamp IS NULL OR finalization_timestamp >= creation_timestamp', name=op.f('ck_artefact_manifests_finalization_not_before_creation')),
    sa.CheckConstraint('octet_length(integrity_verification_reference) <= 16384', name=op.f('ck_artefact_manifests_integrity_verification_reference_bounded')),
    sa.CheckConstraint('octet_length(manifest_digest) <= 16384', name=op.f('ck_artefact_manifests_manifest_digest_bounded')),
    sa.CheckConstraint('octet_length(manifest_digest_algorithm) <= 16384', name=op.f('ck_artefact_manifests_manifest_digest_algorithm_bounded')),
    sa.CheckConstraint('octet_length(producer_provenance_reference) <= 16384', name=op.f('ck_artefact_manifests_producer_provenance_reference_bounded')),
    sa.ForeignKeyConstraint(['candidate_version_id'], ['candidate_version_records.candidate_version_id'], name='fk_artefact_manifests_candidate_version_id'),
    sa.ForeignKeyConstraint(['execution_evidence_id'], ['execution_evidence_records.execution_evidence_id'], name='fk_artefact_manifests_execution_evidence_id'),
    sa.ForeignKeyConstraint(['workflow_attempt_id'], ['workflow_step_attempts.id'], name='fk_artefact_manifests_workflow_attempt_id'),
    sa.PrimaryKeyConstraint('artefact_manifest_id', name=op.f('pk_artefact_manifests'))
    )
    op.create_index(op.f('ix_artefact_manifests_candidate_version_id'), 'artefact_manifests', ['candidate_version_id'], unique=False)
    op.create_index(op.f('ix_artefact_manifests_execution_evidence_id'), 'artefact_manifests', ['execution_evidence_id'], unique=False)
    op.create_index(op.f('ix_artefact_manifests_workflow_attempt_id'), 'artefact_manifests', ['workflow_attempt_id'], unique=False)
    op.create_table('artefact_references',
    sa.Column('artefact_id', sa.String(length=255), nullable=False),
    sa.Column('artefact_type', sa.String(length=32), nullable=False),
    sa.Column('availability_state', sa.String(length=32), nullable=False),
    sa.Column('integrity_state', sa.String(length=16), nullable=False),
    sa.Column('integrity_verification_reference', sa.Text(), nullable=True),
    sa.Column('content_digest', sa.Text(), nullable=False),
    sa.Column('digest_algorithm', sa.Text(), nullable=False),
    sa.Column('byte_size', sa.BigInteger(), nullable=False),
    sa.Column('media_type', sa.String(length=255), nullable=False),
    sa.Column('producer_id', sa.Text(), nullable=False),
    sa.Column('creation_timestamp', sa.DateTime(timezone=True), nullable=False),
    sa.Column('storage_locator', sa.Text(), nullable=False),
    sa.Column('candidate_version_id', sa.String(length=255), nullable=True),
    sa.Column('execution_evidence_id', sa.String(length=255), nullable=True),
    sa.Column('redaction_state', sa.Text(), nullable=True),
    sa.Column('contract_version', sa.String(length=64), nullable=False),
    sa.CheckConstraint("artefact_type IN ('CANDIDATE_PATCH', 'COMPILE_LOG', 'TEST_STDOUT', 'TEST_STDERR', 'EXECUTION_LOG', 'CONTEXT_MANIFEST', 'PUBLICATION_PAYLOAD', 'CUSTOM_OUTPUT')", name=op.f('ck_artefact_references_artefact_type_allowed')),
    sa.CheckConstraint("availability_state IN ('AVAILABLE', 'UNAVAILABLE', 'EXPIRED', 'REDACTED', 'DELETED_OR_TOMBSTONED')", name=op.f('ck_artefact_references_availability_state_allowed')),
    sa.CheckConstraint("integrity_state <> 'VERIFIED' OR integrity_verification_reference IS NOT NULL", name=op.f('ck_artefact_references_verified_integrity_requires_reference')),
    sa.CheckConstraint("integrity_state IN ('VERIFIED', 'UNVERIFIABLE', 'CORRUPT', 'TAMPERED', 'MISSING', 'DELETED')", name=op.f('ck_artefact_references_integrity_state_allowed')),
    sa.CheckConstraint('byte_size >= 0', name=op.f('ck_artefact_references_byte_size_non_negative')),
    sa.CheckConstraint('octet_length(content_digest) <= 16384', name=op.f('ck_artefact_references_content_digest_bounded')),
    sa.CheckConstraint('octet_length(digest_algorithm) <= 16384', name=op.f('ck_artefact_references_digest_algorithm_bounded')),
    sa.CheckConstraint('octet_length(producer_id) <= 16384', name=op.f('ck_artefact_references_producer_id_bounded')),
    sa.CheckConstraint('octet_length(redaction_state) <= 16384', name=op.f('ck_artefact_references_redaction_state_bounded')),
    sa.CheckConstraint('octet_length(storage_locator) <= 16384', name=op.f('ck_artefact_references_storage_locator_bounded')),
    sa.CheckConstraint('storage_locator <> artefact_id::text', name=op.f('ck_artefact_references_storage_locator_distinct_from_identity')),
    sa.ForeignKeyConstraint(['candidate_version_id'], ['candidate_version_records.candidate_version_id'], name='fk_artefact_references_candidate_version_id'),
    sa.ForeignKeyConstraint(['execution_evidence_id'], ['execution_evidence_records.execution_evidence_id'], name='fk_artefact_references_execution_evidence_id'),
    sa.PrimaryKeyConstraint('artefact_id', name=op.f('pk_artefact_references'))
    )
    op.create_index(op.f('ix_artefact_references_candidate_version_id'), 'artefact_references', ['candidate_version_id'], unique=False)
    op.create_index(op.f('ix_artefact_references_execution_evidence_id'), 'artefact_references', ['execution_evidence_id'], unique=False)
    op.create_table('execution_resource_observations',
    sa.Column('execution_evidence_id', sa.String(length=255), nullable=False),
    sa.Column('ordinal', sa.Integer(), nullable=False),
    sa.Column('resource_category', sa.String(length=64), nullable=False),
    sa.Column('enforcement_status', sa.String(length=64), nullable=False),
    sa.Column('terminated_execution', sa.Boolean(), nullable=False),
    sa.Column('configured_amount', sa.BigInteger(), nullable=True),
    sa.Column('configured_unit', sa.String(length=64), nullable=True),
    sa.Column('configuration_reference', sa.Text(), nullable=True),
    sa.Column('observed_amount', sa.BigInteger(), nullable=True),
    sa.Column('observed_unit', sa.String(length=64), nullable=True),
    sa.Column('breached', sa.Boolean(), nullable=True),
    sa.Column('truncated', sa.Boolean(), nullable=True),
    sa.Column('fact_reference', sa.Text(), nullable=True),
    sa.Column('other_category', sa.String(length=255), nullable=True),
    sa.CheckConstraint("(resource_category = 'OTHER') = (other_category IS NOT NULL)", name=op.f('ck_execution_resource_observations_other_category_shape')),
    sa.CheckConstraint("NOT (enforcement_status = 'NOT_ENFORCED' AND terminated_execution)", name=op.f('ck_execution_resource_observations_not_enforced_no_termination')),
    sa.CheckConstraint("enforcement_status IN ('NOT_ENFORCED', 'CAPTURE_BOUND_ENFORCED', 'SUPERVISOR_TIMEOUT_ENFORCED', 'EXTERNAL_ENFORCED')", name=op.f('ck_execution_resource_observations_enforcement_status_allowed')),
    sa.CheckConstraint("resource_category IN ('CPU_TIME', 'MEMORY_BYTES', 'DISK_TEMP_WORKSPACE_BYTES', 'PROCESS_COUNT', 'FILE_COUNT', 'STDOUT_BYTES', 'STDERR_BYTES', 'TIMEOUT', 'OTHER')", name=op.f('ck_execution_resource_observations_resource_category_allowed')),
    sa.CheckConstraint('(configured_amount IS NULL) = (configured_unit IS NULL)', name=op.f('ck_execution_resource_observations_configured_value_pairing')),
    sa.CheckConstraint('(observed_amount IS NULL) = (observed_unit IS NULL)', name=op.f('ck_execution_resource_observations_observed_value_pairing')),
    sa.CheckConstraint('configured_amount IS NOT NULL OR configuration_reference IS NOT NULL', name=op.f('ck_execution_resource_observations_configuration_present')),
    sa.CheckConstraint('octet_length(configuration_reference) <= 16384', name=op.f('ck_execution_resource_observations_configuration_ref_bounded')),
    sa.CheckConstraint('octet_length(fact_reference) <= 16384', name=op.f('ck_execution_resource_observations_fact_reference_bounded')),
    sa.CheckConstraint('octet_length(other_category) <= 255', name=op.f('ck_execution_resource_observations_other_category_bounded')),
    sa.CheckConstraint('ordinal >= 1', name=op.f('ck_execution_resource_observations_ordinal_positive')),
    sa.ForeignKeyConstraint(['execution_evidence_id'], ['execution_evidence_records.execution_evidence_id'], name='fk_execution_resource_observations_execution_evidence_id'),
    sa.PrimaryKeyConstraint('execution_evidence_id', 'ordinal', name=op.f('pk_execution_resource_observations'))
    )
    op.create_table('execution_test_case_results',
    sa.Column('execution_evidence_id', sa.String(length=255), nullable=False),
    sa.Column('ordinal', sa.Integer(), nullable=False),
    sa.Column('test_reference', sa.Text(), nullable=False),
    sa.Column('case_status', sa.String(length=16), nullable=False),
    sa.Column('failure_reference', sa.Text(), nullable=True),
    sa.CheckConstraint("case_status IN ('PASSED', 'FAILED', 'SKIPPED', 'ERRORED')", name=op.f('ck_execution_test_case_results_case_status_allowed')),
    sa.CheckConstraint("failure_reference IS NULL OR case_status IN ('FAILED', 'ERRORED')", name=op.f('ck_execution_test_case_results_failure_reference_failing_only')),
    sa.CheckConstraint('octet_length(failure_reference) <= 16384', name=op.f('ck_execution_test_case_results_failure_reference_bounded')),
    sa.CheckConstraint('octet_length(test_reference) <= 16384', name=op.f('ck_execution_test_case_results_test_reference_bounded')),
    sa.CheckConstraint('ordinal >= 1', name=op.f('ck_execution_test_case_results_ordinal_positive')),
    sa.ForeignKeyConstraint(['execution_evidence_id'], ['execution_evidence_records.execution_evidence_id'], name='fk_execution_test_case_results_execution_evidence_id'),
    sa.PrimaryKeyConstraint('execution_evidence_id', 'ordinal', name=op.f('pk_execution_test_case_results')),
    sa.UniqueConstraint('execution_evidence_id', 'test_reference', name='uq_execution_test_case_results_evidence_reference')
    )
    op.create_table('artefact_manifest_members',
    sa.Column('artefact_manifest_id', sa.String(length=255), nullable=False),
    sa.Column('artefact_id', sa.String(length=255), nullable=False),
    sa.ForeignKeyConstraint(['artefact_id'], ['artefact_references.artefact_id'], name=op.f('fk_artefact_manifest_members_artefact_id_artefact_references')),
    sa.ForeignKeyConstraint(['artefact_manifest_id'], ['artefact_manifests.artefact_manifest_id'], name='fk_artefact_manifest_members_manifest'),
    sa.PrimaryKeyConstraint('artefact_manifest_id', 'artefact_id', name=op.f('pk_artefact_manifest_members'))
    )
    op.create_table('execution_artefact_roles',
    sa.Column('execution_evidence_id', sa.String(length=255), nullable=False),
    sa.Column('artefact_id', sa.String(length=255), nullable=False),
    sa.Column('role', sa.String(length=32), nullable=False),
    sa.CheckConstraint("role IN ('STDOUT', 'STDERR', 'COMPILE_DIAGNOSTIC', 'OUTPUT')", name=op.f('ck_execution_artefact_roles_role_allowed')),
    sa.ForeignKeyConstraint(['artefact_id'], ['artefact_references.artefact_id'], name=op.f('fk_execution_artefact_roles_artefact_id_artefact_references')),
    sa.ForeignKeyConstraint(['execution_evidence_id'], ['execution_evidence_records.execution_evidence_id'], name='fk_execution_artefact_roles_execution_evidence_id'),
    sa.PrimaryKeyConstraint('execution_evidence_id', 'artefact_id', name=op.f('pk_execution_artefact_roles'))
    )
    op.create_index('uq_execution_artefact_roles_stream_role', 'execution_artefact_roles', ['execution_evidence_id', 'role'], unique=True, postgresql_where=sa.text("role IN ('STDOUT', 'STDERR')"))

    # Evidence metadata is INSERT / CONVERGE / CONFLICT, never a mutable
    # projection: reject every UPDATE and DELETE physically.
    op.execute(
        """
        CREATE FUNCTION db004_reject_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'db-004 evidence metadata rows are immutable';
        END;
        $$
        """
    )
    for table in (
        "rag_context_bundles",
        "rag_context_items",
        "candidate_patch_records",
        "candidate_changed_files",
        "candidate_version_records",
        "execution_evidence_records",
        "execution_test_case_results",
        "execution_resource_observations",
        "artefact_references",
        "execution_artefact_roles",
        "artefact_manifests",
        "artefact_manifest_members",
    ):
        op.execute(
            f"CREATE TRIGGER trg_db004_immutable BEFORE UPDATE OR DELETE"
            f" ON {table} FOR EACH ROW EXECUTE FUNCTION"
            f" db004_reject_mutation()"
        )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_db004_immutable ON artefact_manifest_members")
    op.execute("DROP TRIGGER trg_db004_immutable ON artefact_manifests")
    op.execute("DROP TRIGGER trg_db004_immutable ON execution_artefact_roles")
    op.execute("DROP TRIGGER trg_db004_immutable ON execution_resource_observations")
    op.execute("DROP TRIGGER trg_db004_immutable ON execution_test_case_results")
    op.execute("DROP TRIGGER trg_db004_immutable ON artefact_references")
    op.execute("DROP TRIGGER trg_db004_immutable ON execution_evidence_records")
    op.execute("DROP TRIGGER trg_db004_immutable ON candidate_version_records")
    op.execute("DROP TRIGGER trg_db004_immutable ON candidate_changed_files")
    op.execute("DROP TRIGGER trg_db004_immutable ON candidate_patch_records")
    op.execute("DROP TRIGGER trg_db004_immutable ON rag_context_items")
    op.execute("DROP TRIGGER trg_db004_immutable ON rag_context_bundles")
    op.execute("DROP FUNCTION db004_reject_mutation()")
    op.drop_index('uq_execution_artefact_roles_stream_role', table_name='execution_artefact_roles', postgresql_where=sa.text("role IN ('STDOUT', 'STDERR')"))
    op.drop_table('execution_artefact_roles')
    op.drop_table('artefact_manifest_members')
    op.drop_table('execution_test_case_results')
    op.drop_table('execution_resource_observations')
    op.drop_index(op.f('ix_artefact_references_execution_evidence_id'), table_name='artefact_references')
    op.drop_index(op.f('ix_artefact_references_candidate_version_id'), table_name='artefact_references')
    op.drop_table('artefact_references')
    op.drop_index(op.f('ix_artefact_manifests_workflow_attempt_id'), table_name='artefact_manifests')
    op.drop_index(op.f('ix_artefact_manifests_execution_evidence_id'), table_name='artefact_manifests')
    op.drop_index(op.f('ix_artefact_manifests_candidate_version_id'), table_name='artefact_manifests')
    op.drop_table('artefact_manifests')
    op.drop_index(op.f('ix_execution_evidence_records_workflow_attempt_id'), table_name='execution_evidence_records')
    op.drop_index(op.f('ix_execution_evidence_records_run_id'), table_name='execution_evidence_records')
    op.drop_index(op.f('ix_execution_evidence_records_candidate_version_id'), table_name='execution_evidence_records')
    op.drop_table('execution_evidence_records')
    op.drop_index(op.f('ix_candidate_version_records_workflow_attempt_id'), table_name='candidate_version_records')
    op.drop_index(op.f('ix_candidate_version_records_run_id'), table_name='candidate_version_records')
    op.drop_index(op.f('ix_candidate_version_records_parent_candidate_version_id'), table_name='candidate_version_records')
    op.drop_index(op.f('ix_candidate_version_records_candidate_patch_id'), table_name='candidate_version_records')
    op.drop_table('candidate_version_records')
    op.drop_table('candidate_changed_files')
    op.drop_index(op.f('ix_candidate_patch_records_workflow_attempt_id'), table_name='candidate_patch_records')
    op.drop_index(op.f('ix_candidate_patch_records_run_id'), table_name='candidate_patch_records')
    op.drop_table('candidate_patch_records')
    op.drop_index(op.f('ix_rag_context_items_context_bundle_id'), table_name='rag_context_items')
    op.drop_table('rag_context_items')
    op.drop_table('rag_context_bundles')
