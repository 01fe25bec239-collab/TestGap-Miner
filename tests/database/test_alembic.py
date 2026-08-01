from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.db.models import Base
from support import DB_002_TABLES, FORBIDDEN_TABLES

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "apps/api/alembic.ini"
VERSIONS_PATH = ROOT / "apps/api/alembic/versions"
GUIDE_PATH = ROOT / "docs/data/database-schema.md"


def test_exactly_one_alembic_head_exists() -> None:
    config = Config(CONFIG_PATH)
    assert Path(config.get_main_option("script_location")).is_dir()
    heads = ScriptDirectory.from_config(config).get_heads()
    assert len(heads) == 1


def test_the_single_revision_is_the_db_002_base_revision() -> None:
    script = ScriptDirectory.from_config(Config(CONFIG_PATH))
    revisions = list(script.walk_revisions())
    assert len(revisions) == 1
    revision = revisions[0]
    assert revision.down_revision is None
    assert revision.doc == "create DB-002 core entities"
    assert len(list(VERSIONS_PATH.glob("*.py"))) == 1


def test_alembic_metadata_contains_every_db_002_model() -> None:
    assert set(Base.metadata.tables) == DB_002_TABLES


def test_the_revision_creates_no_forbidden_table_and_seeds_no_data() -> None:
    source = next(VERSIONS_PATH.glob("*.py")).read_text()
    for table in FORBIDDEN_TABLES:
        assert f"'{table}'" not in source
    assert "op.bulk_insert" not in source
    assert "op.execute" not in source
    for table in DB_002_TABLES:
        assert f"op.drop_table('{table}')" in source


def test_documented_alembic_commands_use_explicit_config() -> None:
    commands = [
        line
        for line in GUIDE_PATH.read_text().splitlines()
        if line.startswith("uv run --project apps/api alembic")
    ]
    assert commands
    assert all("-c apps/api/alembic.ini" in command for command in commands)
