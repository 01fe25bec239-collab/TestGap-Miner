"""Upgrade, downgrade, and re-upgrade the DB-002 revision on PostgreSQL 16."""

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from support import DB_002_TABLES, FORBIDDEN_TABLES


def _tables(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names())


def test_upgrade_downgrade_upgrade_round_trip(
    alembic_config: Config, migrated_engine: Engine
) -> None:
    # The session fixture already upgraded an empty database to head.
    assert DB_002_TABLES <= _tables(migrated_engine)
    assert _tables(migrated_engine) & FORBIDDEN_TABLES == set()

    command.downgrade(alembic_config, "base")
    assert _tables(migrated_engine) & DB_002_TABLES == set()

    command.upgrade(alembic_config, "head")
    restored = inspect(migrated_engine)
    assert DB_002_TABLES <= set(restored.get_table_names())
    assert {
        constraint["name"] for constraint in restored.get_check_constraints("runs")
    } >= {"ck_runs_state_allowed", "ck_runs_repair_attempts_used_range"}
    assert "uq_repository_access_active" in {
        index["name"] for index in restored.get_indexes("repository_access")
    }


def test_downgrade_leaves_the_zero_revision_state(
    alembic_config: Config, migrated_engine: Engine
) -> None:
    command.downgrade(alembic_config, "base")
    try:
        remaining = _tables(migrated_engine)
        assert remaining & DB_002_TABLES == set()
        assert remaining <= {"alembic_version"}
    finally:
        command.upgrade(alembic_config, "head")
