from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.db.models import Base
from support import DB_002_TABLES, DB_003_TABLES, DB_CURRENT_TABLES, FORBIDDEN_TABLES

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "apps/api/alembic.ini"
VERSIONS_PATH = ROOT / "apps/api/alembic/versions"
GUIDE_PATH = ROOT / "docs/data/database-schema.md"


def test_exactly_one_alembic_head_exists() -> None:
    config = Config(CONFIG_PATH)
    assert Path(config.get_main_option("script_location")).is_dir()
    heads = ScriptDirectory.from_config(config).get_heads()
    assert heads == ["e7b4c2d9a631"]


def test_the_two_revisions_form_one_linear_chain() -> None:
    script = ScriptDirectory.from_config(Config(CONFIG_PATH))
    revisions = list(script.walk_revisions())
    assert len(revisions) == 2
    db_003, db_002 = revisions
    assert db_003.revision == "e7b4c2d9a631"
    assert db_003.down_revision == "ad3f80907336"
    assert db_003.doc == "create DB-003 workflow persistence"
    assert db_002.revision == "ad3f80907336"
    assert db_002.down_revision is None
    assert db_002.doc == "create DB-002 core entities"
    assert len(list(VERSIONS_PATH.glob("*.py"))) == 2


def test_alembic_metadata_contains_every_current_model() -> None:
    assert set(Base.metadata.tables) == DB_CURRENT_TABLES


def test_db_002_revision_remains_the_historical_seven_table_base() -> None:
    source = (
        VERSIONS_PATH / "ad3f80907336_create_db_002_core_entities.py"
    ).read_text()
    for table in DB_003_TABLES | FORBIDDEN_TABLES:
        assert f"'{table}'" not in source
        assert f'"{table}"' not in source
    assert "op.bulk_insert" not in source
    for table in DB_002_TABLES:
        assert f"op.drop_table('{table}')" in source


def test_db_003_revision_creates_only_the_authorized_tables() -> None:
    source = (
        VERSIONS_PATH / "e7b4c2d9a631_create_db_003_workflow_persistence.py"
    ).read_text()
    for table in FORBIDDEN_TABLES:
        assert f"'{table}'" not in source
        assert f'"{table}"' not in source
    assert "op.bulk_insert" not in source
    for table in DB_003_TABLES:
        assert f'op.create_table(\n        "{table}"' in source
        assert f'op.drop_table("{table}")' in source
    for table in DB_002_TABLES:
        assert f'op.create_table(\n        "{table}"' not in source


def test_documented_alembic_commands_use_explicit_config() -> None:
    commands = [
        line
        for line in GUIDE_PATH.read_text().splitlines()
        if line.startswith("uv run --project apps/api alembic")
    ]
    assert commands
    assert all("-c apps/api/alembic.ini" in command for command in commands)
