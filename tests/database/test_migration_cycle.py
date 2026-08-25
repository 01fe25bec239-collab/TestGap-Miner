"""Fresh, populated, downgrade, and re-upgrade cycles on PostgreSQL 16."""

import uuid

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, select
from sqlalchemy.engine import Engine

from app.db.models import Run, RunRequest
from support import (
    DB_002_TABLES,
    DB_003_TABLES,
    DB_004_TABLES,
    DB_CURRENT_TABLES,
    FORBIDDEN_TABLES,
)

POST_DB_002_TABLES = DB_003_TABLES | DB_004_TABLES


def _tables(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names())


def test_upgrade_downgrade_upgrade_round_trip(
    alembic_config: Config, migrated_engine: Engine
) -> None:
    # The session fixture already upgraded an empty database to head.
    assert DB_CURRENT_TABLES <= _tables(migrated_engine)
    assert _tables(migrated_engine) & FORBIDDEN_TABLES == set()

    command.downgrade(alembic_config, "base")
    assert _tables(migrated_engine) & DB_CURRENT_TABLES == set()

    command.upgrade(alembic_config, "head")
    restored = inspect(migrated_engine)
    assert DB_CURRENT_TABLES <= set(restored.get_table_names())
    assert {
        constraint["name"] for constraint in restored.get_check_constraints("runs")
    } >= {"ck_runs_state_allowed", "ck_runs_repair_attempts_used_range"}
    assert "uq_repository_access_active" in {
        index["name"] for index in restored.get_indexes("repository_access")
    }


def test_populated_db_002_upgrade_downgrade_and_reupgrade(
    alembic_config: Config, migrated_engine: Engine
) -> None:
    request_id = uuid.uuid4()
    run_id = uuid.uuid4()
    key = f"migration-{uuid.uuid4().hex}"

    command.downgrade(alembic_config, "ad3f80907336")
    try:
        assert DB_002_TABLES <= _tables(migrated_engine)
        assert _tables(migrated_engine) & POST_DB_002_TABLES == set()

        with migrated_engine.begin() as connection:
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

        command.upgrade(alembic_config, "head")
        assert DB_CURRENT_TABLES <= _tables(migrated_engine)
        with migrated_engine.connect() as connection:
            assert connection.scalar(
                select(RunRequest.id).where(RunRequest.id == request_id)
            ) == request_id
            assert connection.scalar(select(Run.id).where(Run.id == run_id)) == run_id

        command.downgrade(alembic_config, "ad3f80907336")
        assert DB_002_TABLES <= _tables(migrated_engine)
        assert _tables(migrated_engine) & POST_DB_002_TABLES == set()
        with migrated_engine.connect() as connection:
            assert connection.scalar(
                select(RunRequest.id).where(RunRequest.id == request_id)
            ) == request_id
            assert connection.scalar(select(Run.id).where(Run.id == run_id)) == run_id

        command.upgrade(alembic_config, "head")
        assert DB_CURRENT_TABLES <= _tables(migrated_engine)
        assert ScriptDirectory.from_config(alembic_config).get_heads() == [
            "e52607712c32"
        ]
    finally:
        command.upgrade(alembic_config, "head")


def test_downgrade_leaves_the_zero_revision_state(
    alembic_config: Config, migrated_engine: Engine
) -> None:
    command.downgrade(alembic_config, "base")
    try:
        remaining = _tables(migrated_engine)
        assert remaining & DB_CURRENT_TABLES == set()
        assert remaining <= {"alembic_version"}
    finally:
        command.upgrade(alembic_config, "head")
