#!/bin/sh
set -eu

if [ "${1:-}" != "--yes" ] || [ "$#" -ne 1 ]; then
  echo "Usage: TESTGAP_RUNTIME=local $0 --yes" >&2
  exit 2
fi

if [ "${TESTGAP_RUNTIME:-}" != "local" ]; then
  echo "TESTGAP_RUNTIME=local is required; refusing to reset" >&2
  exit 1
fi

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repository_root=$(CDPATH= cd -- "$script_dir/../.." && pwd)
cd "$repository_root"

exec docker compose --project-name testgap-miner down --volumes --remove-orphans
