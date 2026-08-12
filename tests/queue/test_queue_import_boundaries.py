import ast
from pathlib import Path

import app.queue as queue


PROVIDER_IMPORTS = {
    "boto3",
    "celery",
    "confluent_kafka",
    "kafka",
    "nats",
    "pika",
    "redis",
    "supabase",
}
RUNTIME_LAYER_IMPORTS = {
    "app.api",
    "app.db",
    "app.workflow",
    "app.execution",
    "app.evidence",
}


def test_queue_source_has_no_provider_or_runtime_layer_imports() -> None:
    package_root = Path(queue.__file__).parent
    imported: set[str] = set()
    for source in package_root.glob("*.py"):
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported.add(node.module)

    forbidden = PROVIDER_IMPORTS | RUNTIME_LAYER_IMPORTS
    assert not {
        module
        for module in imported
        if any(module == item or module.startswith(f"{item}.") for item in forbidden)
    }
