#!/bin/sh
set -eu

case "${TESTGAP_RUNTIME:-}" in
  local|ci) ;;
  *)
    echo "TESTGAP_RUNTIME must be local or ci; refusing test database initialization" >&2
    exit 1
    ;;
esac

: "${POSTGRES_APP_PASSWORD:?POSTGRES_APP_PASSWORD must be set}"
: "${POSTGRES_MIGRATION_PASSWORD:?POSTGRES_MIGRATION_PASSWORD must be set}"
: "${POSTGRES_TEST_PASSWORD:?POSTGRES_TEST_PASSWORD must be set}"

psql --username postgres --dbname postgres --set ON_ERROR_STOP=1 <<'SQL'
\getenv app_password POSTGRES_APP_PASSWORD
\getenv migration_password POSTGRES_MIGRATION_PASSWORD
\getenv test_password POSTGRES_TEST_PASSWORD

SELECT 'CREATE ROLE testgap_app LOGIN'
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'testgap_app')
\gexec
SELECT 'CREATE ROLE testgap_migrator LOGIN'
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'testgap_migrator')
\gexec
SELECT 'CREATE ROLE testgap_test LOGIN'
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'testgap_test')
\gexec

ALTER ROLE testgap_app WITH LOGIN PASSWORD :'app_password'
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS NOINHERIT;
ALTER ROLE testgap_migrator WITH LOGIN PASSWORD :'migration_password'
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS NOINHERIT;
ALTER ROLE testgap_test WITH LOGIN PASSWORD :'test_password'
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS NOINHERIT;

SELECT 'CREATE DATABASE testgap_test OWNER testgap_migrator'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'testgap_test')
\gexec

ALTER DATABASE testgap OWNER TO testgap_migrator;
ALTER DATABASE testgap_test OWNER TO testgap_migrator;
REVOKE CONNECT, TEMPORARY ON DATABASE testgap FROM PUBLIC;
REVOKE CONNECT, TEMPORARY ON DATABASE testgap_test FROM PUBLIC;
REVOKE CONNECT ON DATABASE postgres FROM PUBLIC;
REVOKE CONNECT ON DATABASE template1 FROM PUBLIC;
REVOKE ALL PRIVILEGES ON DATABASE testgap FROM testgap_app, testgap_test;
REVOKE ALL PRIVILEGES ON DATABASE testgap_test FROM testgap_app, testgap_test;
GRANT CONNECT ON DATABASE testgap TO testgap_app, testgap_migrator;
GRANT CONNECT ON DATABASE testgap_test TO testgap_test, testgap_migrator;
SQL

psql --username postgres --dbname testgap --set ON_ERROR_STOP=1 <<'SQL'
REVOKE ALL ON SCHEMA public FROM PUBLIC, testgap_test;
GRANT USAGE ON SCHEMA public TO testgap_app;
GRANT USAGE, CREATE ON SCHEMA public TO testgap_migrator;
ALTER DEFAULT PRIVILEGES FOR ROLE testgap_migrator IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO testgap_app;
ALTER DEFAULT PRIVILEGES FOR ROLE testgap_migrator IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO testgap_app;
SQL

psql --username postgres --dbname testgap_test --set ON_ERROR_STOP=1 <<'SQL'
REVOKE ALL ON SCHEMA public FROM PUBLIC, testgap_app;
GRANT USAGE ON SCHEMA public TO testgap_test;
GRANT USAGE, CREATE ON SCHEMA public TO testgap_migrator;
ALTER DEFAULT PRIVILEGES FOR ROLE testgap_migrator IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO testgap_test;
ALTER DEFAULT PRIVILEGES FOR ROLE testgap_migrator IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO testgap_test;
SQL
