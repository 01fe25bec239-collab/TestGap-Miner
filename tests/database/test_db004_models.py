"""DB-004 physical schema behavior: immutability, boundaries, vocabularies."""

from types import SimpleNamespace

import pytest
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.db.db004_persistence import (
    persist_artefact_manifest_metadata,
    persist_candidate_metadata,
    persist_context_bundle_metadata,
    persist_execution_evidence_metadata,
)
from app.db.models import Base
from app.db.models.context import ContextBundle as ContextBundleRow
from app.db.models.context import ContextBundleItem as ContextBundleItemRow
from app.db.models.evidence import (
    EVIDENCE_CONTRACT_VERSION,
    ARTEFACT_MANIFEST_SCHEMA_VERSION,
    ArtefactManifestRecord,
    CandidateChangedFile,
    ArtefactReferenceRecord,
    CandidatePatchRecord,
    CandidateVersionRecord,
    ExecutionEvidenceRecord,
)
from app.evidence.artefact import ArtefactId
from app.evidence.execution import (
    ResourceCategory,
    ResourceEnforcementStatus,
    ResourceObservation,
    ResourceValue,
)
from db004_support import (
    REVISION_40,
    make_artefact_manifest,
    make_artefact_reference,
    make_candidate_patch,
    make_candidate_version,
    make_context_bundle,
    make_execution_evidence,
)
from support import (
    DB_004_TABLES,
    assert_rejected,
    make_attempt,
    make_run,
    make_run_request,
    make_step,
    secret_named_columns,
)


def _workflow(session: Session) -> SimpleNamespace:
    request = make_run_request()
    run = make_run(request)
    session.add_all([request, run])
    session.flush()
    step = make_step(run, kind="GENERATE_CANDIDATE")
    session.add(step)
    session.flush()
    attempt = make_attempt(step)
    session.add(attempt)
    session.flush()
    return SimpleNamespace(request=request, run=run, step=step, attempt=attempt)


def _candidate_chain(session: Session) -> SimpleNamespace:
    workflow = _workflow(session)
    run_id = str(workflow.run.id)
    patch_row, version_row = persist_candidate_metadata(
        session,
        patch=make_candidate_patch(run_id, str(workflow.attempt.id)),
        version=make_candidate_version(run_id, str(workflow.attempt.id)),
    )
    return SimpleNamespace(
        workflow=workflow, patch_row=patch_row, version_row=version_row
    )


def _seed_everything(session: Session) -> None:
    """One durable row in every DB-004 table."""
    chain = _candidate_chain(session)
    attempt_id = str(chain.workflow.attempt.id)
    stdout = make_artefact_reference(
        artefact_id=ArtefactId("art.m.stdout"),
        artefact_type="TEST_STDOUT",
        storage_locator="object-store://m/stdout",
    )
    stderr = make_artefact_reference(
        artefact_id=ArtefactId("art.m.stderr"),
        artefact_type="TEST_STDERR",
        storage_locator="object-store://m/stderr",
    )
    evidence = make_execution_evidence(
        workflow_attempt_id=attempt_id,
        stdout_artefact=stdout,
        stderr_artefact=stderr,
        resource_observations=(
            ResourceObservation(
                category=ResourceCategory.MEMORY_BYTES,
                enforcement_status=ResourceEnforcementStatus.CAPTURE_BOUND_ENFORCED,
                terminated_execution=False,
                configured_value=ResourceValue(amount=536_870_912, unit="bytes"),
                observed_value=ResourceValue(amount=1_048_576, unit="bytes"),
                breached=False,
            ),
        ),
    )
    persist_execution_evidence_metadata(session, evidence)
    persist_artefact_manifest_metadata(session, make_artefact_manifest(members=(stdout,)))
    persist_context_bundle_metadata(session, make_context_bundle())


# One surviving row (identity) per DB-004 table.
IMMUTABLE_ROWS = {
    "rag_context_bundles": {"context_bundle_id": "context-bundle-1"},
    "rag_context_items": {"context_item_id": "context-item-1"},
    "candidate_patch_records": {"candidate_patch_id": "candidate-patch-1"},
    "candidate_changed_files": {
        "candidate_patch_id": "candidate-patch-1",
        "path": "src/test/java/ExampleTest.java",
    },
    "candidate_version_records": {"candidate_version_id": "candidate-version-1"},
    "execution_evidence_records": {"execution_evidence_id": "execution-evidence-1"},
    "execution_test_case_results": {
        "execution_evidence_id": "execution-evidence-1",
        "ordinal": 1,
    },
    "execution_resource_observations": {
        "execution_evidence_id": "execution-evidence-1",
        "ordinal": 1,
    },
    "artefact_references": {"artefact_id": "art.m.stdout"},
    "execution_artefact_roles": {
        "execution_evidence_id": "execution-evidence-1",
        "artefact_id": "art.m.stdout",
    },
    "artefact_manifests": {"artefact_manifest_id": "manifest-1"},
    "artefact_manifest_members": {
        "artefact_manifest_id": "manifest-1",
        "artefact_id": "art.m.stdout",
    },
}


@pytest.mark.parametrize("table_name", sorted(IMMUTABLE_ROWS))
def test_updates_are_physically_rejected(session: Session, table_name: str) -> None:
    _seed_everything(session)
    table = Base.metadata.tables[table_name]
    identity = IMMUTABLE_ROWS[table_name]
    where = [table.columns[key] == value for key, value in identity.items()]
    target = next(iter(table.columns.values()))
    with pytest.raises(DBAPIError), session.begin_nested():
        session.execute(sa.update(table).where(*where).values({target.name: target}))


@pytest.mark.parametrize("table_name", sorted(IMMUTABLE_ROWS))
def test_deletes_are_physically_rejected(session: Session, table_name: str) -> None:
    _seed_everything(session)
    table = Base.metadata.tables[table_name]
    where = [
        table.columns[key] == value for key, value in IMMUTABLE_ROWS[table_name].items()
    ]
    with pytest.raises(DBAPIError), session.begin_nested():
        session.execute(sa.delete(table).where(*where))


# ---------------------------------------------------------------------------
# Storage-boundary inspections
# ---------------------------------------------------------------------------


def test_db004_has_no_byte_payload_columns(migrated_engine: Engine) -> None:
    inspector = inspect(migrated_engine)
    for table_name in sorted(DB_004_TABLES):
        for column in inspector.get_columns(table_name):
            column_type = str(column["type"]).upper()
            assert "BYTEA" not in column_type, (table_name, column["name"])
            assert "LARGEBINARY" not in column_type, (table_name, column["name"])
            if "JSONB" in column_type:
                assert (table_name, column["name"]) == (
                    "execution_evidence_records",
                    "secondary_failures",
                )


def test_db004_has_no_raw_content_or_secret_column_names() -> None:
    names = [
        column.name
        for table_name in sorted(DB_004_TABLES)
        for column in Base.metadata.tables[table_name].columns
    ]
    assert secret_named_columns(names) == []
    # Digests *of* content are metadata; raw payloads would use these shapes.
    banned_exact = {
        "content",
        "text",
        "item_content",
        "context_content",
        "raw_repository",
        "repository_bytes",
        "patch_bytes",
        "log_bytes",
        "artefact_bytes",
        "evidence_bytes",
    }
    offenders = [
        n
        for n in names
        if n in banned_exact or any(b in n for b in ("blob", "payload"))
    ]
    assert offenders == []


def test_every_db004_timestamp_is_timezone_aware(migrated_engine: Engine) -> None:
    inspector = inspect(migrated_engine)
    naive = [
        f"{table_name}.{column['name']}"
        for table_name in sorted(DB_004_TABLES)
        for column in inspector.get_columns(table_name)
        if str(column["type"]).startswith("TIMESTAMP") and not column["type"].timezone
    ]
    assert naive == []


def test_stream_role_uniqueness_is_partial(migrated_engine: Engine) -> None:
    indexes = {
        index["name"]: index
        for index in inspect(migrated_engine).get_indexes("execution_artefact_roles")
    }
    stream = indexes["uq_execution_artefact_roles_stream_role"]
    assert stream["unique"] is True
    assert "STDOUT" in str(stream.get("dialect_options", {}))


# ---------------------------------------------------------------------------
# Physical vocabulary and shape boundaries
# ---------------------------------------------------------------------------


def _bundle_parent(session: Session) -> None:
    session.add(
        ContextBundleRow(
            context_bundle_id="bundle-parent",
            repository_id="benchmark-repo",
            revision_id=REVISION_40,
            contract_version="1.0.0-draft.1",
            max_tokens=10,
            consumed_tokens=1,
        )
    )
    session.flush()


def test_unknown_trust_label_is_rejected(session: Session) -> None:
    _bundle_parent(session)
    assert_rejected(
        session,
        ContextBundleItemRow(
            context_item_id="item-x",
            context_bundle_id="bundle-parent",
            position=1,
            candidate_id="candidate-x",
            file_identity="src/X.java",
            start_line=1,
            end_line=1,
            content_sha256="0" * 64,
            trust_label="TOTALLY_TRUSTED",
            token_count=1,
        ),
    )


def _version_row(chain: SimpleNamespace, **overrides) -> CandidateVersionRecord:
    values = dict(
        candidate_version_id="version-extra",
        candidate_patch_id="candidate-patch-1",
        run_id=chain.version_row.run_id,
        workflow_attempt_id=chain.workflow.attempt.id,
        repair_level=0,
        parent_candidate_version_id=None,
        source_repository="sr",
        source_revision="sr",
        generator_reference="g",
        tool_version_reference="t",
        generated_at=chain.version_row.generated_at,
        configuration_version="cfg",
        finalization_state="CREATED",
        finalized_at=None,
        contract_version=EVIDENCE_CONTRACT_VERSION,
    )
    values.update(overrides)
    return CandidateVersionRecord(**values)


def test_repair_level_outside_0_or_1_is_rejected(session: Session) -> None:
    chain = _candidate_chain(session)
    assert_rejected(
        session,
        _version_row(chain, candidate_version_id="version-lvl2", repair_level=2),
    )


def test_self_parenting_version_is_rejected(session: Session) -> None:
    chain = _candidate_chain(session)
    assert_rejected(
        session,
        _version_row(
            chain,
            candidate_version_id="version-selfparent",
            repair_level=1,
            parent_candidate_version_id="version-selfparent",
        ),
    )


def _execution_row(chain: SimpleNamespace, **overrides) -> ExecutionEvidenceRecord:
    values = dict(
        execution_evidence_id="exec-extra",
        producer_result_id="producer-extra",
        candidate_version_id="candidate-version-1",
        run_id=None,
        workflow_attempt_id=chain.workflow.attempt.id,
        execution_phase="COMPILE",
        outcome="SUCCESS",
        completeness="PARTIAL",
        command_reference="command://x",
        execution_fact_reference="fact://x",
        source_revision=None,
        compile_status="SUCCESS",
        contract_version=EVIDENCE_CONTRACT_VERSION,
    )
    values.update(overrides)
    return ExecutionEvidenceRecord(**values)


def test_compile_phase_cannot_carry_a_test_failure(session: Session) -> None:
    chain = _candidate_chain(session)
    assert_rejected(
        session,
        _execution_row(
            chain,
            execution_evidence_id="exec-mixed-phase",
            outcome="TEST_FAILURE",
        ),
    )


def test_success_cannot_carry_failed_tests(session: Session) -> None:
    chain = _candidate_chain(session)
    assert_rejected(
        session,
        _execution_row(
            chain,
            execution_evidence_id="exec-false-success",
            execution_phase="BUGGY_OR_TARGET_REVISION_TEST",
            source_revision="sr",
            test_executed_count=1,
            test_failed_count=1,
        ),
    )


def chain_timestamp():
    from datetime import UTC, datetime

    return datetime(2026, 8, 22, tzinfo=UTC)


def _artefact_row(**overrides) -> ArtefactReferenceRecord:
    values = dict(
        artefact_id="artefact.standalone",
        artefact_type="CUSTOM_OUTPUT",
        availability_state="AVAILABLE",
        integrity_state="UNVERIFIABLE",
        content_digest="sha256:" + "11" * 32,
        digest_algorithm="SHA-256",
        byte_size=128,
        media_type="application/octet-stream",
        producer_id="producer://x",
        creation_timestamp=chain_timestamp(),
        storage_locator="object-store://bucket/standalone",
        contract_version=EVIDENCE_CONTRACT_VERSION,
    )
    values.update(overrides)
    return ArtefactReferenceRecord(**values)


def test_storage_locator_may_not_equal_the_identity(session: Session) -> None:
    assert_rejected(session, _artefact_row(storage_locator="artefact.standalone"))


def test_negative_byte_size_is_rejected(session: Session) -> None:
    assert_rejected(session, _artefact_row(byte_size=-1))


def test_unknown_availability_state_is_rejected(session: Session) -> None:
    assert_rejected(session, _artefact_row(availability_state="SORT_OF_HERE"))


def _manifest_row(**overrides) -> ArtefactManifestRecord:
    values = dict(
        artefact_manifest_id="manifest-standalone",
        creation_timestamp=chain_timestamp(),
        finalization_state="ASSEMBLING",
        contract_version=EVIDENCE_CONTRACT_VERSION,
        schema_version=ARTEFACT_MANIFEST_SCHEMA_VERSION,
    )
    values.update(overrides)
    return ArtefactManifestRecord(**values)


def test_assembling_manifest_cannot_be_finalized(session: Session) -> None:
    assert_rejected(
        session,
        _manifest_row(finalization_timestamp=chain_timestamp()),
    )


def test_finalized_manifest_without_final_metadata_is_rejected(
    session: Session,
) -> None:
    assert_rejected(
        session,
        _manifest_row(
            finalization_state="FINALIZED",
            finalization_timestamp=chain_timestamp(),
        ),
    )


def test_manifest_digest_requires_its_algorithm(session: Session) -> None:
    assert_rejected(
        session,
        _manifest_row(manifest_digest="sha256:" + "22" * 32),
    )


def test_changed_file_path_may_not_be_absolute(session: Session) -> None:
    chain = _candidate_chain(session)
    assert_rejected(
        session,
        CandidateChangedFile(
            candidate_patch_id="candidate-patch-1",
            path="/etc/passwd",
            change_summary="escape attempt",
        ),
    )
