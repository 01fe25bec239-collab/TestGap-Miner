"""Make the repository-local `evaluation` package importable.

The pytest run is rooted at the repository, but only `apps/api` is installed
into the environment, so the root is not otherwise on `sys.path`.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
