from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.db.metadata import metadata

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "apps/api/alembic.ini"
VERSIONS_PATH = ROOT / "apps/api/alembic/versions"
GUIDE_PATH = ROOT / "docs/data/database-scaffold.md"


def test_alembic_bootstrap_has_zero_heads_and_no_revisions() -> None:
    config = Config(CONFIG_PATH)
    assert Path(config.get_main_option("script_location")).is_dir()
    assert ScriptDirectory.from_config(config).get_heads() == []
    assert list(VERSIONS_PATH.glob("*.py")) == []
    assert list(metadata.tables) == []


def test_documented_alembic_commands_use_explicit_config() -> None:
    commands = [
        line
        for line in GUIDE_PATH.read_text().splitlines()
        if line.startswith("uv run --project apps/api alembic")
    ]
    assert commands
    assert all("-c apps/api/alembic.ini" in command for command in commands)

