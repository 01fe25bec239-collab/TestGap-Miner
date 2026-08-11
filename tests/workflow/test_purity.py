import ast
import importlib
from pathlib import Path
from types import MappingProxyType

import app.workflow as workflow


FORBIDDEN_IMPORTS = {
    "app.api",
    "app.db",
    "app.evidence",
    "app.execution",
    "app.queue",
    "fastapi",
    "httpx",
    "psycopg",
    "requests",
    "sqlalchemy",
    "subprocess",
}


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module)
    return modules


def test_workflow_source_import_graph_excludes_runtime_layers() -> None:
    package_root = Path(workflow.__file__).parent
    imports = {
        module
        for source in (
            package_root / "types.py",
            package_root / "engine.py",
            package_root / "checkpoint.py",
        )
        for module in imported_modules(source)
    }

    assert not {
        module
        for module in imports
        if any(
            module == forbidden or module.startswith(f"{forbidden}.")
            for forbidden in FORBIDDEN_IMPORTS
        )
    }


def test_public_package_import_has_no_runtime_configuration_prerequisites(
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    for name in (
        "DATABASE_URL",
        "SUPABASE_URL",
        "REDIS_URL",
        "OPENAI_API_KEY",
        "GITHUB_TOKEN",
    ):
        monkeypatch.delenv(name, raising=False)

    assert importlib.reload(workflow).RunState.RECEIVED == "RECEIVED"


def test_transition_topology_is_not_mutable_global_state() -> None:
    assert isinstance(workflow.ALLOWED_TRANSITIONS, MappingProxyType)
