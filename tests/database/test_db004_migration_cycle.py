"""DB-003 -> DB-004 upgrade, downgrade, and re-upgrade cycles."""

import uuid
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, select, text
from sqlalchemy.engine import Engine

from app.db.models import Run, RunRequest
from support import (
    DB_002_TABLES,
    DB_003_TABLES,
    DB_004_TABLES,
    DB_CURRENT_TABLES,
    FORBIDDEN_TABLES,
)

ROOT = Path(__file__).resolve().parents[2]
DB_003_REVISION = "e7b4c2d9a631"
DB_004_REVISION = "e52607712c32"


def _tables(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names())


def _trigger_count(engine: Engine) -> int:
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT count(*) FROM pg_trigger WHERE tgname = 'trg_db004_immutable'")
        ).scalar_one()


def test_exactly_one_head_exists_on_this_branch() -> None:
    heads = ScriptDirectory.from_config(Config(str(ROOT / "apps/api/alembic.ini"))).get_heads()
    assert heads == [DB_004_REVISION]


def test_db004_upgrade_creates_tables_and_immutability_triggers(
    alembic_config: Config, migrated_engine: Engine
) -> None:
    command.downgrade(alembic_config, DB_003_REVISION)
    tables = _tables(migrated_engine)
    assert DB_003_TABLES <= tables
    assert tables & DB_004_TABLES == set()
    assert _trigger_count(migrated_engine) == 0

    try:
        command.upgrade(alembic_config, "head")
        upgraded = _tables(migrated_engine)
        assert DB_004_TABLES <= upgraded
        assert DB_003_TABLES <= upgraded
        assert upgraded - {"alembic_version"} == DB_CURRENT_TABLES
        assert upgraded & FORBIDDEN_TABLES == set()
        assert _trigger_count(migrated_engine) == len(DB_004_TABLES)
    finally:
        command.upgrade(alembic_config, "head")


def test_db004_constraints_and_indexes_are_present(
    alembic_config: Config, migrated_engine: Engine
) -> None:
    inspector = inspect(migrated_engine)

    checks = {
        constraint["name"]
        for constraint in inspector.get_check_constraints(
            "candidate_version_records"
        )
    }
    assert "ck_candidate_version_records_lineage_shape_matches_repair_level" in checks

    manifest_checks = {
        constraint["name"]
        for constraint in inspector.get_check_constraints("artefact_manifests")
    }
    assert "ck_artefact_manifests_finalized_requires_final_metadata" in manifest_checks

    artefact_checks = {
        constraint["name"]
        for constraint in inspector.get_check_constraints("artefact_references")
    }
    assert (
        "ck_artefact_references_storage_locator_distinct_from_identity"
        in artefact_checks
    )

    indexes = {
        index["name"]: index
        for index in inspector.get_indexes("execution_artefact_roles")
    }
    stream = indexes["uq_execution_artefact_roles_stream_role"]
    assert stream["unique"] is True


def test_populated_rows_survive_the_db004_round_trip(
    alembic_config: Config, migrated_engine: Engine
) -> None:
    request_id, run_id = _seed_workflow(migrated_engine)
    assert DB_004_TABLES <= _tables(migrated_engine)

    try:
        command.downgrade(alembic_config, DB_003_REVISION)
        downgraded = _tables(migrated_engine)
        assert downgraded & DB_004_TABLES == set()
        assert DB_002_TABLES | DB_003_TABLES <= downgraded
        assert _trigger_count(migrated_engine) == 0
        with migrated_engine.connect() as connection:
            assert connection.scalar(select(Run.id).where(Run.id == run_id)) == run_id

        command.upgrade(alembic_config, "head")
        assert DB_004_TABLES <= _tables(migrated_engine)
        with migrated_engine.connect() as connection:
            assert (
                connection.scalar(select(Run.id).where(Run.id == run_id)) == run_id
            )
            assert (
                connection.scalar(
                    select(RunRequest.id).where(RunRequest.id == request_id)
                )
                == request_id
            )
    finally:
        command.upgrade(alembic_config, "head")


def _seed_workflow(engine: Engine):
    request_id = uuid.uuid4()
    run_id = uuid.uuid4()
    key = f"db004-{uuid.uuid4().hex}"
    with engine.begin() as connection:
        connection.execute(
            RunRequest.__table__.insert().values(
                id=request_id,
                request_kind="BENCHMARK",
                idempotency_key=key,
                idempotency_key_version=1,
                request_fingerprint="f" * 64,
                benchmark_project_id="Lang",
                benchmark_bug_id="1",
                configuration_version="cfg-1",
                model_id="model-1",
                prompt_template_version="prompt-1",
            )
        )
        connection.execute(
            Run.__table__.insert().values(
                id=run_id,
                run_request_id=request_id,
                state="RECEIVED",
                contract_version="1.0.0-draft.1",
                review_required=True,
                repair_attempts_used=0,
                retry_attempts_used=0,
                retry_limit=3,
                step_attempts_used=0,
                version=0,
            )
        )
    return request_id, run_id
