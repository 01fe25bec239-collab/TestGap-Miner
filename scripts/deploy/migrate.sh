#!/bin/sh
set -eu

if [ -z "${MIGRATION_DATABASE_URL:-}" ]; then
  echo "MIGRATION_DATABASE_URL is required for migrations" >&2
  exit 1
fi

if [ ! -f apps/api/alembic.ini ]; then
  echo "Alembic configuration is not available: apps/api/alembic.ini is Database-owned" >&2
  exit 1
fi

if ! /opt/venv/bin/alembic --version >/dev/null 2>&1; then
  echo "Alembic is not available in the locked API project" >&2
  exit 1
fi

/opt/venv/bin/alembic -c apps/api/alembic.ini upgrade head
