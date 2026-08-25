"""DB-004 Evidence metadata persistence: candidates, executions, artefacts.

Physical storage for ``CONTRACT-EVIDENCE-001@1.0.0-draft.3`` candidate
patch/version lineage, phase-specific execution evidence, immutable artefact
references, and artefact manifests.

Every table below stores bounded provenance metadata and opaque references
only. There is no column for repository bytes, ContextItem content, patch
bytes, raw stdout/stderr, execution logs, artefact payloads, or any credential
material; captured streams survive only as ``artefact_references`` rows whose
provider-neutral storage locator points at object storage Database never
implements.

Evidence records are INSERT / CONVERGE / CONFLICT values, not mutable
projections, so every table is physically append-only.
"""

from datetime import datetime
import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, sql_in

EVIDENCE_CONTRACT_VERSION = "CONTRACT-EVIDENCE-001@1.0.0-draft.3"
ARTEFACT_MANIFEST_SCHEMA_VERSION = "ARTEFACT-MANIFEST-SCHEMA-V1"

CANDIDATE_FINALIZATION_STATES = ("CREATED", "FINALIZED")
EXECUTION_PHASES = (
    "COMPILE",
    "BUGGY_OR_TARGET_REVISION_TEST",
    "FIXED_OR_REFERENCE_REVISION_TEST",
)
EXECUTION_OUTCOMES = (
    "SUCCESS",
    "COMPILATION_FAILURE",
    "TEST_FAILURE",
    "TIMEOUT",
    "CANCELLATION",
    "RESOURCE_BREACH",
    "RUNNER_ERROR",
    "UNAVAILABLE",
    "NOT_RUN",
)
FAILURE_CATEGORIES = (
    "COMPILATION_FAILURE",
    "TEST_FAILURE",
    "TIMEOUT",
    "CANCELLATION",
    "RESOURCE_BREACH",
    "RUNNER_ERROR",
)
COMPLETENESS_STATES = (
    "COMPLETE",
    "PARTIAL",
    "UNAVAILABLE",
    "INVALID",
    "CONFLICTING",
    "REDACTED",
    "DELETED_OR_TOMBSTONED",
)
INTEGRITY_STATES = (
    "VERIFIED",
    "UNVERIFIABLE",
    "CORRUPT",
    "TAMPERED",
    "MISSING",
    "DELETED",
)
AVAILABILITY_STATES = (
    "AVAILABLE",
    "UNAVAILABLE",
    "EXPIRED",
    "REDACTED",
    "DELETED_OR_TOMBSTONED",
)
COMPILE_STATUSES = ("SUCCESS", "FAILURE", "NOT_COMPLETED")
TEST_CASE_STATUSES = ("PASSED", "FAILED", "SKIPPED", "ERRORED")
RESOURCE_CATEGORIES = (
    "CPU_TIME",
    "MEMORY_BYTES",
    "DISK_TEMP_WORKSPACE_BYTES",
    "PROCESS_COUNT",
    "FILE_COUNT",
    "STDOUT_BYTES",
    "STDERR_BYTES",
    "TIMEOUT",
    "OTHER",
)
RESOURCE_ENFORCEMENT_STATUSES = (
    "NOT_ENFORCED",
    "CAPTURE_BOUND_ENFORCED",
    "SUPERVISOR_TIMEOUT_ENFORCED",
    "EXTERNAL_ENFORCED",
)
ARTEFACT_TYPES = (
    "CANDIDATE_PATCH",
    "COMPILE_LOG",
    "TEST_STDOUT",
    "TEST_STDERR",
    "EXECUTION_LOG",
    "CONTEXT_MANIFEST",
    "PUBLICATION_PAYLOAD",
    "CUSTOM_OUTPUT",
)
MANIFEST_FINALIZATION_STATES = ("ASSEMBLING", "FINALIZED")
# Metadata roles binding execution-linked artefacts; the byte payloads live in
# object storage, never here.
ARTEFACT_ROLES = ("STDOUT", "STDERR", "COMPILE_DIAGNOSTIC", "OUTPUT")

IDENTITY_LENGTH = 255
MAX_REFERENCE_BYTES = 16_384
MAX_MEDIA_TYPE_LENGTH = 255
MAX_STORAGE_LOCATOR_BYTES = 16_384
MAX_CHANGED_PATH_BYTES = 4_096
MAX_CHANGE_SUMMARY_BYTES = 16_384
MAX_JSONB_BYTES = 65_536


def bounded_reference(column: str, maximum_bytes: int = MAX_REFERENCE_BYTES) -> str:
    """Check-constraint text bounding one opaque reference column."""
    return f"octet_length({column}) <= {maximum_bytes}"


class CandidatePatchRecord(Base):
    """One durable CandidatePatch value keyed by its own patch identity."""

    __tablename__ = "candidate_patch_records"
    __table_args__ = (
        sa.CheckConstraint(
            sql_in("finalization_state", CANDIDATE_FINALIZATION_STATES),
            name="finalization_state_allowed",
        ),
        sa.CheckConstraint(
            "(finalization_state = 'FINALIZED') = (finalized_at IS NOT NULL)",
            name="finalized_at_matches_state",
        ),
        sa.CheckConstraint(bounded_reference("source_repository"), name="source_repository_bounded"),
        sa.CheckConstraint(bounded_reference("source_revision"), name="source_revision_bounded"),
        sa.CheckConstraint(bounded_reference("target_reference_revision"), name="target_reference_revision_bounded"),
        sa.CheckConstraint(bounded_reference("patch_digest"), name="patch_digest_bounded"),
        sa.CheckConstraint(bounded_reference("digest_algorithm"), name="digest_algorithm_bounded"),
        sa.CheckConstraint(bounded_reference("test_only_scope_reference"), name="test_only_scope_reference_bounded"),
        sa.CheckConstraint(bounded_reference("generator_reference"), name="generator_reference_bounded"),
        sa.CheckConstraint(bounded_reference("tool_version_reference"), name="tool_version_reference_bounded"),
        sa.CheckConstraint(bounded_reference("configuration_version"), name="configuration_version_bounded"),
        sa.CheckConstraint(bounded_reference("patch_content_reference"), name="patch_content_reference_bounded"),
        sa.CheckConstraint(bounded_reference("model_identifier"), name="model_identifier_bounded"),
        sa.CheckConstraint(bounded_reference("prompt_template_version"), name="prompt_template_version_bounded"),
        sa.CheckConstraint(bounded_reference("localisation_provenance_reference"), name="localisation_provenance_bounded"),
        sa.ForeignKeyConstraint(
            ("workflow_attempt_id",),
            ("workflow_step_attempts.id",),
            name="fk_candidate_patch_records_workflow_attempt_id",
        ),
    )

    # Evidence-owned logical patch identity; never collapsed into a version.
    candidate_patch_id: Mapped[str] = mapped_column(
        sa.String(IDENTITY_LENGTH), primary_key=True
    )
    # The versioned instance this patch value belongs to.
    candidate_version_id: Mapped[str] = mapped_column(
        sa.String(IDENTITY_LENGTH), unique=True
    )

    # DB-003 owns these durable identities; unmappable opaque strings fail
    # closed inside DB-004 persistence instead of being reinterpreted.
    run_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("runs.id"), index=True)
    workflow_attempt_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(), index=True)

    source_repository: Mapped[str] = mapped_column(sa.Text)
    source_revision: Mapped[str] = mapped_column(sa.Text)
    target_reference_revision: Mapped[str | None] = mapped_column(sa.Text)

    patch_digest: Mapped[str] = mapped_column(sa.Text)
    digest_algorithm: Mapped[str] = mapped_column(sa.Text)
    test_only_scope: Mapped[bool]
    test_only_scope_reference: Mapped[str] = mapped_column(sa.Text)

    generator_reference: Mapped[str] = mapped_column(sa.Text)
    tool_version_reference: Mapped[str] = mapped_column(sa.Text)
    generated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    configuration_version: Mapped[str] = mapped_column(sa.Text)

    finalization_state: Mapped[str] = mapped_column(sa.String(16))
    finalized_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))

    patch_content_reference: Mapped[str | None] = mapped_column(sa.Text)
    model_identifier: Mapped[str | None] = mapped_column(sa.Text)
    prompt_template_version: Mapped[str | None] = mapped_column(sa.Text)
    localisation_provenance_reference: Mapped[str | None] = mapped_column(sa.Text)
    correlation_id: Mapped[str | None] = mapped_column(sa.String(255))
    contract_version: Mapped[str] = mapped_column(sa.String(64))

    changed_files: Mapped[list["CandidateChangedFile"]] = relationship(
        back_populates="patch", order_by="CandidateChangedFile.path"
    )


class CandidateChangedFile(Base):
    """Normalized changed-file metadata; deterministic reconstruction by path."""

    __tablename__ = "candidate_changed_files"
    __table_args__ = (
        sa.CheckConstraint("path <> ''", name="path_nonempty"),
        sa.CheckConstraint("path NOT LIKE '/%'", name="path_repository_relative"),
        sa.CheckConstraint(
            f"octet_length(path) <= {MAX_CHANGED_PATH_BYTES}", name="path_bounded"
        ),
        sa.CheckConstraint(
            f"octet_length(change_summary) <= {MAX_CHANGE_SUMMARY_BYTES}",
            name="change_summary_bounded",
        ),
        sa.ForeignKeyConstraint(
            ("candidate_patch_id",),
            ("candidate_patch_records.candidate_patch_id",),
            name="fk_candidate_changed_files_candidate_patch_id",
        ),
    )

    candidate_patch_id: Mapped[str] = mapped_column(
        sa.String(IDENTITY_LENGTH), primary_key=True
    )
    path: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    change_summary: Mapped[str] = mapped_column(sa.Text)

    patch: Mapped[CandidatePatchRecord] = relationship(back_populates="changed_files")


class CandidateVersionRecord(Base):
    """One durable CandidateVersion lineage instance.

    Lineage metadata only: ``repair_level`` records candidate lineage and
    never enforces or represents Workflow's repair allowance policy.
    """

    __tablename__ = "candidate_version_records"
    __table_args__ = (
        sa.CheckConstraint(
            sql_in("finalization_state", CANDIDATE_FINALIZATION_STATES),
            name="finalization_state_allowed",
        ),
        sa.CheckConstraint("repair_level IN (0, 1)", name="repair_level_allowed"),
        sa.CheckConstraint(
            "(repair_level = 0 AND parent_candidate_version_id IS NULL)"
            " OR (repair_level = 1 AND parent_candidate_version_id IS NOT NULL)",
            name="lineage_shape_matches_repair_level",
        ),
        sa.CheckConstraint(
            "parent_candidate_version_id IS NULL"
            " OR parent_candidate_version_id <> candidate_version_id",
            name="parent_not_self",
        ),
        sa.CheckConstraint(bounded_reference("source_repository"), name="source_repository_bounded"),
        sa.CheckConstraint(bounded_reference("source_revision"), name="source_revision_bounded"),
        sa.CheckConstraint(bounded_reference("target_reference_revision"), name="target_reference_revision_bounded"),
        sa.CheckConstraint(bounded_reference("generator_reference"), name="generator_reference_bounded"),
        sa.CheckConstraint(bounded_reference("tool_version_reference"), name="tool_version_reference_bounded"),
        sa.CheckConstraint(bounded_reference("configuration_version"), name="configuration_version_bounded"),
        sa.CheckConstraint(bounded_reference("model_identifier"), name="model_identifier_bounded"),
        sa.CheckConstraint(bounded_reference("prompt_template_version"), name="prompt_template_version_bounded"),
        sa.CheckConstraint(bounded_reference("localisation_provenance_reference"), name="localisation_provenance_bounded"),
        sa.ForeignKeyConstraint(
            ("candidate_patch_id",),
            ("candidate_patch_records.candidate_patch_id",),
            name="fk_candidate_version_records_candidate_patch_id",
        ),
        sa.ForeignKeyConstraint(
            ("parent_candidate_version_id",),
            ("candidate_version_records.candidate_version_id",),
            name="fk_candidate_version_records_parent_candidate_version",
        ),
        sa.ForeignKeyConstraint(
            ("workflow_attempt_id",),
            ("workflow_step_attempts.id",),
            name="fk_candidate_version_records_workflow_attempt_id",
        ),
    )

    # Evidence-owned versioned identity for this candidate instance.
    candidate_version_id: Mapped[str] = mapped_column(
        sa.String(IDENTITY_LENGTH), primary_key=True
    )
    # Distinct patch identity binding; a foreign key, never a substitution.
    candidate_patch_id: Mapped[str] = mapped_column(
        sa.String(IDENTITY_LENGTH), index=True
    )

    run_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("runs.id"), index=True)
    workflow_attempt_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(), index=True)

    # Opaque A2-EXECUTION result reference. Optional by contract: a candidate
    # MUST be persistable before Execution mints any result identity.
    producer_result_id: Mapped[str | None] = mapped_column(sa.String(IDENTITY_LENGTH))

    repair_level: Mapped[int]
    parent_candidate_version_id: Mapped[str | None] = mapped_column(
        sa.String(IDENTITY_LENGTH), index=True
    )

    source_repository: Mapped[str] = mapped_column(sa.Text)
    source_revision: Mapped[str] = mapped_column(sa.Text)
    target_reference_revision: Mapped[str | None] = mapped_column(sa.Text)

    generator_reference: Mapped[str] = mapped_column(sa.Text)
    tool_version_reference: Mapped[str] = mapped_column(sa.Text)
    generated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    configuration_version: Mapped[str] = mapped_column(sa.Text)

    finalization_state: Mapped[str] = mapped_column(sa.String(16))
    finalized_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))

    model_identifier: Mapped[str | None] = mapped_column(sa.Text)
    prompt_template_version: Mapped[str | None] = mapped_column(sa.Text)
    localisation_provenance_reference: Mapped[str | None] = mapped_column(sa.Text)
    correlation_id: Mapped[str | None] = mapped_column(sa.String(255))
    contract_version: Mapped[str] = mapped_column(sa.String(64))


class ExecutionEvidenceRecord(Base):
    """One phase-specific ExecutionEvidence record without any log bytes."""

    __tablename__ = "execution_evidence_records"
    __table_args__ = (
        sa.CheckConstraint(sql_in("execution_phase", EXECUTION_PHASES), name="execution_phase_allowed"),
        sa.CheckConstraint(sql_in("outcome", EXECUTION_OUTCOMES), name="outcome_allowed"),
        sa.CheckConstraint(sql_in("completeness", COMPLETENESS_STATES), name="completeness_allowed"),
        sa.CheckConstraint(sql_in("integrity_state", INTEGRITY_STATES), name="integrity_state_allowed"),
        sa.CheckConstraint(sql_in("failure_category", FAILURE_CATEGORIES), name="failure_category_allowed"),
        sa.CheckConstraint(sql_in("compile_status", COMPILE_STATUSES), name="compile_status_allowed"),
        sa.CheckConstraint(
            "ended_at IS NULL OR started_at IS NULL OR ended_at >= started_at",
            name="ended_at_not_before_started_at",
        ),
        sa.CheckConstraint(
            "duration_microseconds IS NULL OR duration_microseconds >= 0",
            name="duration_non_negative",
        ),
        sa.CheckConstraint(
            "timeout_timed_out IS NOT TRUE OR timeout_classification IS NOT NULL",
            name="timeout_requires_classification",
        ),
        sa.CheckConstraint(
            "timeout_limit_microseconds IS NULL OR timeout_limit_microseconds >= 0",
            name="timeout_limit_non_negative",
        ),
        sa.CheckConstraint(
            "signal_number IS NULL OR signal_number > 0",
            name="signal_number_positive",
        ),
        sa.CheckConstraint(
            "integrity_state <> 'VERIFIED'"
            " OR integrity_verification_reference IS NOT NULL",
            name="integrity_verification_required",
        ),
        sa.CheckConstraint(
            f"jsonb_typeof(secondary_failures) = 'array'",
            name="secondary_failures_is_array",
        ),
        sa.CheckConstraint(
            f"octet_length(secondary_failures::text) <= {MAX_JSONB_BYTES}",
            name="secondary_failures_bounded",
        ),
        # Exactly the phase-appropriate structured result is representable.
        sa.CheckConstraint(
            "CASE WHEN execution_phase = 'COMPILE' THEN"
            " compile_status IS NOT NULL"
            " AND test_executed_count IS NULL AND test_passed_count IS NULL"
            " AND test_failed_count IS NULL AND test_skipped_count IS NULL"
            " AND test_errored_count IS NULL"
            " AND test_failure_summary_reference IS NULL"
            " ELSE compile_status IS NULL AND compile_error_count IS NULL"
            " AND compile_warning_count IS NULL"
            " AND compile_metadata_reference IS NULL END",
            name="phase_structured_result_shape",
        ),
        sa.CheckConstraint(
            "CASE WHEN outcome = 'SUCCESS' THEN compile_status IS NULL"
            " OR compile_status = 'SUCCESS'"
            " WHEN outcome = 'COMPILATION_FAILURE' THEN compile_status IS NULL"
            " OR compile_status = 'FAILURE'"
            " ELSE compile_status IS NULL OR compile_status = 'NOT_COMPLETED' END",
            name="compile_status_matches_outcome",
        ),
        sa.CheckConstraint(
            "test_executed_count IS NULL OR test_executed_count >="
            " COALESCE(test_passed_count, 0) + COALESCE(test_failed_count, 0)"
            " + COALESCE(test_skipped_count, 0) + COALESCE(test_errored_count, 0)",
            name="test_counts_within_executed",
        ),
        sa.CheckConstraint(
            "NOT (outcome = 'SUCCESS' AND (COALESCE(test_failed_count, 0) > 0"
            " OR COALESCE(test_errored_count, 0) > 0))",
            name="success_has_no_test_failures",
        ),
        sa.CheckConstraint(
            "NOT (outcome = 'COMPILATION_FAILURE' AND execution_phase <> 'COMPILE')"
            " AND NOT (outcome = 'TEST_FAILURE' AND execution_phase = 'COMPILE')",
            name="phase_outcome_compatible",
        ),
        sa.CheckConstraint(
            "CASE outcome"
            " WHEN 'COMPILATION_FAILURE' THEN failure_category = 'COMPILATION_FAILURE'"
            " WHEN 'TEST_FAILURE' THEN failure_category = 'TEST_FAILURE'"
            " WHEN 'TIMEOUT' THEN failure_category = 'TIMEOUT'"
            " WHEN 'CANCELLATION' THEN failure_category = 'CANCELLATION'"
            " WHEN 'RESOURCE_BREACH' THEN failure_category = 'RESOURCE_BREACH'"
            " WHEN 'RUNNER_ERROR' THEN failure_category = 'RUNNER_ERROR'"
            " ELSE failure_category IS NULL AND failure_reference IS NULL"
            " AND secondary_failures IS NULL END",
            name="failure_evidence_matches_outcome",
        ),
        sa.CheckConstraint(bounded_reference("command_reference"), name="command_reference_bounded"),
        sa.CheckConstraint(bounded_reference("execution_fact_reference"), name="execution_fact_reference_bounded"),
        sa.CheckConstraint(bounded_reference("source_revision"), name="source_revision_bounded"),
        sa.CheckConstraint(bounded_reference("timeout_classification"), name="timeout_classification_bounded"),
        sa.CheckConstraint(bounded_reference("timeout_fact_reference"), name="timeout_fact_reference_bounded"),
        sa.CheckConstraint(bounded_reference("signal_name", 255), name="signal_name_bounded"),
        sa.CheckConstraint(bounded_reference("exit_fact_reference"), name="exit_fact_reference_bounded"),
        sa.CheckConstraint(bounded_reference("integrity_verification_reference"), name="integrity_verification_bounded"),
        sa.CheckConstraint(bounded_reference("runtime_metadata_reference"), name="runtime_metadata_bounded"),
        sa.CheckConstraint(bounded_reference("sandbox_metadata_reference"), name="sandbox_metadata_bounded"),
        sa.CheckConstraint(bounded_reference("environment_metadata_reference"), name="environment_metadata_bounded"),
        sa.CheckConstraint(bounded_reference("flake_indication_reference"), name="flake_indication_bounded"),
        sa.CheckConstraint(bounded_reference("failure_reference"), name="failure_reference_bounded"),
        sa.CheckConstraint(bounded_reference("compile_metadata_reference"), name="compile_metadata_bounded"),
        sa.CheckConstraint(bounded_reference("test_failure_summary_reference"), name="test_failure_summary_bounded"),
        sa.CheckConstraint(bounded_reference("timing_fact_reference"), name="timing_fact_reference_bounded"),
        sa.ForeignKeyConstraint(
            ("candidate_version_id",),
            ("candidate_version_records.candidate_version_id",),
            name="fk_execution_evidence_records_candidate_version_id",
        ),
        sa.ForeignKeyConstraint(
            ("workflow_attempt_id",),
            ("workflow_step_attempts.id",),
            name="fk_execution_evidence_records_workflow_attempt_id",
        ),
    )

    execution_evidence_id: Mapped[str] = mapped_column(
        sa.String(IDENTITY_LENGTH), primary_key=True
    )
    # Opaque A2-EXECUTION result slot reference for this attempt and phase.
    producer_result_id: Mapped[str] = mapped_column(sa.String(IDENTITY_LENGTH))

    # Opaque queue/tracing provenance carried through Execution. These are
    # bounded opaque metadata columns only: no Queue foreign key, no part in
    # Evidence identity, and never conflated with producer_result_id.
    queue_message_id: Mapped[str | None] = mapped_column(sa.String(255))
    queue_delivery_id: Mapped[str | None] = mapped_column(sa.String(255))
    correlation_id: Mapped[str | None] = mapped_column(sa.String(255))

    candidate_version_id: Mapped[str] = mapped_column(
        sa.String(IDENTITY_LENGTH), index=True
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(sa.ForeignKey("runs.id"), index=True)
    workflow_attempt_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(), index=True)

    execution_phase: Mapped[str] = mapped_column(sa.String(64))
    outcome: Mapped[str] = mapped_column(sa.String(64))
    completeness: Mapped[str] = mapped_column(sa.String(32))
    command_reference: Mapped[str] = mapped_column(sa.Text)
    execution_fact_reference: Mapped[str] = mapped_column(sa.Text)
    source_revision: Mapped[str | None] = mapped_column(sa.Text)

    started_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    duration_microseconds: Mapped[int | None] = mapped_column(sa.BigInteger())
    timing_fact_reference: Mapped[str | None] = mapped_column(sa.Text)

    timeout_timed_out: Mapped[bool | None]
    timeout_classification: Mapped[str | None] = mapped_column(sa.Text)
    timeout_limit_microseconds: Mapped[int | None] = mapped_column(sa.BigInteger())
    timeout_fact_reference: Mapped[str | None] = mapped_column(sa.Text)

    exit_code: Mapped[int | None]
    signal_number: Mapped[int | None]
    signal_name: Mapped[str | None] = mapped_column(sa.String(255))
    exit_fact_reference: Mapped[str | None] = mapped_column(sa.Text)

    integrity_state: Mapped[str | None] = mapped_column(sa.String(16))
    integrity_verification_reference: Mapped[str | None] = mapped_column(sa.Text)

    runtime_metadata_reference: Mapped[str | None] = mapped_column(sa.Text)
    sandbox_metadata_reference: Mapped[str | None] = mapped_column(sa.Text)
    environment_metadata_reference: Mapped[str | None] = mapped_column(sa.Text)
    flake_indication_reference: Mapped[str | None] = mapped_column(sa.Text)

    failure_category: Mapped[str | None] = mapped_column(sa.String(64))
    failure_reference: Mapped[str | None] = mapped_column(sa.Text)
    secondary_failures: Mapped[list[dict[str, object]] | None] = mapped_column(JSONB)

    compile_status: Mapped[str | None] = mapped_column(sa.String(16))
    compile_error_count: Mapped[int | None]
    compile_warning_count: Mapped[int | None]
    compile_metadata_reference: Mapped[str | None] = mapped_column(sa.Text)

    test_executed_count: Mapped[int | None]
    test_passed_count: Mapped[int | None]
    test_failed_count: Mapped[int | None]
    test_skipped_count: Mapped[int | None]
    test_errored_count: Mapped[int | None]
    test_failure_summary_reference: Mapped[str | None] = mapped_column(sa.Text)

    contract_version: Mapped[str] = mapped_column(sa.String(64))

    test_cases: Mapped[list["ExecutionTestCaseResult"]] = relationship(
        back_populates="evidence", order_by="ExecutionTestCaseResult.ordinal"
    )
    resource_observations: Mapped[list["ExecutionResourceObservation"]] = relationship(
        back_populates="evidence", order_by="ExecutionResourceObservation.ordinal"
    )
    artefact_roles: Mapped[list["ExecutionArtefactRole"]] = relationship(
        back_populates="evidence"
    )


class ExecutionTestCaseResult(Base):
    """One individual test-case fact; canonical order reconstructs the list."""

    __tablename__ = "execution_test_case_results"
    __table_args__ = (
        sa.UniqueConstraint(
            "execution_evidence_id",
            "test_reference",
            name="uq_execution_test_case_results_evidence_reference",
        ),
        sa.CheckConstraint(sql_in("case_status", TEST_CASE_STATUSES), name="case_status_allowed"),
        sa.CheckConstraint(
            "failure_reference IS NULL OR case_status IN ('FAILED', 'ERRORED')",
            name="failure_reference_failing_only",
        ),
        sa.CheckConstraint("ordinal >= 1", name="ordinal_positive"),
        sa.CheckConstraint(bounded_reference("test_reference"), name="test_reference_bounded"),
        sa.CheckConstraint(bounded_reference("failure_reference"), name="failure_reference_bounded"),
        sa.ForeignKeyConstraint(
            ("execution_evidence_id",),
            ("execution_evidence_records.execution_evidence_id",),
            name="fk_execution_test_case_results_execution_evidence_id",
        ),
    )

    execution_evidence_id: Mapped[str] = mapped_column(
        sa.String(IDENTITY_LENGTH), primary_key=True
    )
    ordinal: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    test_reference: Mapped[str] = mapped_column(sa.Text)
    case_status: Mapped[str] = mapped_column(sa.String(16))
    failure_reference: Mapped[str | None] = mapped_column(sa.Text)

    evidence: Mapped[ExecutionEvidenceRecord] = relationship(
        back_populates="test_cases"
    )


class ExecutionResourceObservation(Base):
    """Typed runtime resource observation supplied by A2-EXECUTION."""

    __tablename__ = "execution_resource_observations"
    __table_args__ = (
        sa.CheckConstraint(sql_in("resource_category", RESOURCE_CATEGORIES), name="resource_category_allowed"),
        sa.CheckConstraint(sql_in("enforcement_status", RESOURCE_ENFORCEMENT_STATUSES), name="enforcement_status_allowed"),
        sa.CheckConstraint(
            "(configured_amount IS NULL) = (configured_unit IS NULL)",
            name="configured_value_pairing",
        ),
        sa.CheckConstraint(
            "(observed_amount IS NULL) = (observed_unit IS NULL)",
            name="observed_value_pairing",
        ),
        sa.CheckConstraint(
            "configured_amount IS NOT NULL OR configuration_reference IS NOT NULL",
            name="configuration_present",
        ),
        sa.CheckConstraint(
            "(resource_category = 'OTHER') = (other_category IS NOT NULL)",
            name="other_category_shape",
        ),
        sa.CheckConstraint(
            "NOT (enforcement_status = 'NOT_ENFORCED' AND terminated_execution)",
            name="not_enforced_no_termination",
        ),
        sa.CheckConstraint("ordinal >= 1", name="ordinal_positive"),
        sa.CheckConstraint(bounded_reference("configuration_reference"), name="configuration_ref_bounded"),
        sa.CheckConstraint(bounded_reference("fact_reference"), name="fact_reference_bounded"),
        sa.CheckConstraint(bounded_reference("other_category", 255), name="other_category_bounded"),
        sa.ForeignKeyConstraint(
            ("execution_evidence_id",),
            ("execution_evidence_records.execution_evidence_id",),
            name="fk_execution_resource_observations_execution_evidence_id",
        ),
    )

    execution_evidence_id: Mapped[str] = mapped_column(
        sa.String(IDENTITY_LENGTH), primary_key=True
    )
    ordinal: Mapped[int] = mapped_column(sa.Integer, primary_key=True)

    resource_category: Mapped[str] = mapped_column(sa.String(64))
    enforcement_status: Mapped[str] = mapped_column(sa.String(64))
    terminated_execution: Mapped[bool]

    configured_amount: Mapped[int | None] = mapped_column(sa.BigInteger())
    configured_unit: Mapped[str | None] = mapped_column(sa.String(64))
    configuration_reference: Mapped[str | None] = mapped_column(sa.Text)

    observed_amount: Mapped[int | None] = mapped_column(sa.BigInteger())
    observed_unit: Mapped[str | None] = mapped_column(sa.String(64))

    breached: Mapped[bool | None]
    truncated: Mapped[bool | None]
    fact_reference: Mapped[str | None] = mapped_column(sa.Text)
    other_category: Mapped[str | None] = mapped_column(sa.String(255))

    evidence: Mapped[ExecutionEvidenceRecord] = relationship(
        back_populates="resource_observations"
    )


class ExecutionArtefactRole(Base):
    """Role metadata linking an execution to an already-referenced artefact."""

    __tablename__ = "execution_artefact_roles"
    __table_args__ = (
        sa.CheckConstraint(sql_in("role", ARTEFACT_ROLES), name="role_allowed"),
        # Captured streams are single per execution; diagnostics and outputs
        # are collections.
        sa.Index(
            "uq_execution_artefact_roles_stream_role",
            "execution_evidence_id",
            "role",
            unique=True,
            postgresql_where=sa.text("role IN ('STDOUT', 'STDERR')"),
        ),
        sa.ForeignKeyConstraint(
            ("execution_evidence_id",),
            ("execution_evidence_records.execution_evidence_id",),
            name="fk_execution_artefact_roles_execution_evidence_id",
        ),
    )

    execution_evidence_id: Mapped[str] = mapped_column(
        sa.String(IDENTITY_LENGTH), primary_key=True
    )
    artefact_id: Mapped[str] = mapped_column(
        sa.ForeignKey("artefact_references.artefact_id"), primary_key=True
    )
    role: Mapped[str] = mapped_column(sa.String(32))

    evidence: Mapped[ExecutionEvidenceRecord] = relationship(
        back_populates="artefact_roles"
    )


class ArtefactReferenceRecord(Base):
    """Immutable logical reference to one stored artefact; never its bytes."""

    __tablename__ = "artefact_references"
    __table_args__ = (
        sa.CheckConstraint(sql_in("artefact_type", ARTEFACT_TYPES), name="artefact_type_allowed"),
        sa.CheckConstraint(sql_in("availability_state", AVAILABILITY_STATES), name="availability_state_allowed"),
        sa.CheckConstraint(sql_in("integrity_state", INTEGRITY_STATES), name="integrity_state_allowed"),
        sa.CheckConstraint("byte_size >= 0", name="byte_size_non_negative"),
        # Identity and physical locator are distinct concepts by contract.
        sa.CheckConstraint(
            "storage_locator <> artefact_id::text",
            name="storage_locator_distinct_from_identity",
        ),
        sa.CheckConstraint(
            "integrity_state <> 'VERIFIED'"
            " OR integrity_verification_reference IS NOT NULL",
            name="verified_integrity_requires_reference",
        ),
        sa.CheckConstraint(bounded_reference("content_digest"), name="content_digest_bounded"),
        sa.CheckConstraint(bounded_reference("digest_algorithm"), name="digest_algorithm_bounded"),
        sa.CheckConstraint(bounded_reference("producer_id"), name="producer_id_bounded"),
        sa.CheckConstraint(
            f"octet_length(storage_locator) <= {MAX_STORAGE_LOCATOR_BYTES}",
            name="storage_locator_bounded",
        ),
        sa.CheckConstraint(bounded_reference("redaction_state"), name="redaction_state_bounded"),
        sa.ForeignKeyConstraint(
            ("candidate_version_id",),
            ("candidate_version_records.candidate_version_id",),
            name="fk_artefact_references_candidate_version_id",
        ),
        sa.ForeignKeyConstraint(
            ("execution_evidence_id",),
            ("execution_evidence_records.execution_evidence_id",),
            name="fk_artefact_references_execution_evidence_id",
        ),
    )

    artefact_id: Mapped[str] = mapped_column(sa.String(IDENTITY_LENGTH), primary_key=True)
    artefact_type: Mapped[str] = mapped_column(sa.String(32))
    availability_state: Mapped[str] = mapped_column(sa.String(32))
    integrity_state: Mapped[str] = mapped_column(sa.String(16))
    integrity_verification_reference: Mapped[str | None] = mapped_column(sa.Text)

    content_digest: Mapped[str] = mapped_column(sa.Text)
    digest_algorithm: Mapped[str] = mapped_column(sa.Text)
    byte_size: Mapped[int] = mapped_column(sa.BigInteger())
    media_type: Mapped[str] = mapped_column(sa.String(MAX_MEDIA_TYPE_LENGTH))
    producer_id: Mapped[str] = mapped_column(sa.Text)
    creation_timestamp: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    storage_locator: Mapped[str] = mapped_column(sa.Text)

    candidate_version_id: Mapped[str | None] = mapped_column(
        sa.String(IDENTITY_LENGTH), index=True
    )
    execution_evidence_id: Mapped[str | None] = mapped_column(
        sa.String(IDENTITY_LENGTH), index=True
    )
    redaction_state: Mapped[str | None] = mapped_column(sa.Text)
    contract_version: Mapped[str] = mapped_column(sa.String(64))


class ArtefactManifestRecord(Base):
    """Logical manifest grouping artefact references under EVIDENCE-009 rules."""

    __tablename__ = "artefact_manifests"
    __table_args__ = (
        sa.CheckConstraint(
            sql_in("finalization_state", MANIFEST_FINALIZATION_STATES),
            name="finalization_state_allowed",
        ),
        sa.CheckConstraint(
            sql_in("integrity_state", INTEGRITY_STATES), name="integrity_state_allowed"
        ),
        sa.CheckConstraint(
            sql_in("execution_phase", EXECUTION_PHASES), name="execution_phase_allowed"
        ),
        sa.CheckConstraint(
            "finalization_state <> 'ASSEMBLING' OR finalization_timestamp IS NULL",
            name="assembling_has_no_finalization_timestamp",
        ),
        sa.CheckConstraint(
            "finalization_state <> 'FINALIZED' OR ("
            " finalization_timestamp IS NOT NULL"
            " AND producer_provenance_reference IS NOT NULL"
            " AND manifest_digest IS NOT NULL"
            " AND manifest_digest_algorithm IS NOT NULL"
            " AND integrity_state IS NOT NULL)",
            name="finalized_requires_final_metadata",
        ),
        sa.CheckConstraint(
            "(manifest_digest IS NULL) = (manifest_digest_algorithm IS NULL)",
            name="manifest_digest_pairing",
        ),
        sa.CheckConstraint(
            "integrity_state <> 'VERIFIED'"
            " OR integrity_verification_reference IS NOT NULL",
            name="verified_integrity_requires_reference",
        ),
        sa.CheckConstraint(
            "finalization_timestamp IS NULL"
            " OR finalization_timestamp >= creation_timestamp",
            name="finalization_not_before_creation",
        ),
        sa.CheckConstraint(bounded_reference("producer_provenance_reference"), name="producer_provenance_reference_bounded"),
        sa.CheckConstraint(bounded_reference("manifest_digest"), name="manifest_digest_bounded"),
        sa.CheckConstraint(bounded_reference("manifest_digest_algorithm"), name="manifest_digest_algorithm_bounded"),
        sa.CheckConstraint(bounded_reference("integrity_verification_reference"), name="integrity_verification_reference_bounded"),
        sa.ForeignKeyConstraint(
            ("candidate_version_id",),
            ("candidate_version_records.candidate_version_id",),
            name="fk_artefact_manifests_candidate_version_id",
        ),
        sa.ForeignKeyConstraint(
            ("execution_evidence_id",),
            ("execution_evidence_records.execution_evidence_id",),
            name="fk_artefact_manifests_execution_evidence_id",
        ),
        sa.ForeignKeyConstraint(
            ("workflow_attempt_id",),
            ("workflow_step_attempts.id",),
            name="fk_artefact_manifests_workflow_attempt_id",
        ),
    )

    artefact_manifest_id: Mapped[str] = mapped_column(
        sa.String(IDENTITY_LENGTH), primary_key=True
    )
    creation_timestamp: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    finalization_state: Mapped[str] = mapped_column(sa.String(16))

    candidate_version_id: Mapped[str | None] = mapped_column(
        sa.String(IDENTITY_LENGTH), index=True
    )
    execution_evidence_id: Mapped[str | None] = mapped_column(
        sa.String(IDENTITY_LENGTH), index=True
    )
    workflow_attempt_id: Mapped[uuid.UUID | None] = mapped_column(sa.Uuid(), index=True)
    execution_phase: Mapped[str | None] = mapped_column(sa.String(64))
    producer_provenance_reference: Mapped[str | None] = mapped_column(sa.Text)

    manifest_digest: Mapped[str | None] = mapped_column(sa.Text)
    manifest_digest_algorithm: Mapped[str | None] = mapped_column(sa.Text)
    integrity_state: Mapped[str | None] = mapped_column(sa.String(16))
    integrity_verification_reference: Mapped[str | None] = mapped_column(sa.Text)
    finalization_timestamp: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )

    contract_version: Mapped[str] = mapped_column(sa.String(64))
    schema_version: Mapped[str] = mapped_column(sa.String(64))

    members: Mapped[list["ArtefactManifestMember"]] = relationship(
        back_populates="manifest", order_by="ArtefactManifestMember.artefact_id"
    )


class ArtefactManifestMember(Base):
    """Relational membership; order carries no meaning and no bound applies."""

    __tablename__ = "artefact_manifest_members"
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ("artefact_manifest_id",),
            ("artefact_manifests.artefact_manifest_id",),
            name="fk_artefact_manifest_members_manifest",
        ),
    )

    artefact_manifest_id: Mapped[str] = mapped_column(
        sa.String(IDENTITY_LENGTH), primary_key=True
    )
    artefact_id: Mapped[str] = mapped_column(
        sa.ForeignKey("artefact_references.artefact_id"), primary_key=True
    )

    manifest: Mapped[ArtefactManifestRecord] = relationship(back_populates="members")
