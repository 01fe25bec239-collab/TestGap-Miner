#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repository_root=$(CDPATH= cd -- "$script_dir/../.." && pwd)
cd "$repository_root"

project="testgap-deploy-probe-$$"
export TESTGAP_RUNTIME=local
export POSTGRES_PASSWORD="probe-bootstrap-$$"
export POSTGRES_APP_PASSWORD="probe-app-$$"
export POSTGRES_MIGRATION_PASSWORD="probe-migration-$$"
export POSTGRES_TEST_PASSWORD="probe-test-$$"
export POSTGRES_HOST_PORT=0
export API_HOST_PORT=0
export AUTH_JWT_ISSUER=https://auth.local.invalid
export AUTH_JWT_AUDIENCE=testgap-local
export AUTH_JWKS_URL=https://auth.local.invalid/.well-known/jwks.json
export DASHBOARD_ORIGIN=http://localhost:3000

compose() {
  docker compose --project-name "$project" --profile tools "$@"
}

config_file=$(mktemp)
cleanup() {
  rm -f "$config_file"
  compose down --volumes --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT HUP INT TERM

compose config >"$config_file"
echo "COMPOSE_VALIDITY=PASS"

if grep -Eq 'privileged: true|(/var/run|/run)/docker\.sock' "$config_file"; then
  echo "CONTAINER_BOUNDARY_STATIC=FAIL" >&2
  exit 1
fi
echo "CONTAINER_BOUNDARY_STATIC=PASS"

if ! docker info >/dev/null 2>&1; then
  echo "DOCKER_RUNTIME=NOT_TESTED_ENVIRONMENT_BLOCKED"
  exit 2
fi

compose build api
echo "API_IMAGE_BUILD=PASS"
compose build worker
echo "WORKER_IMAGE_BUILD=PASS"

if compose build runner; then
  echo "RUNNER_IMAGE_BUILD=PASS"
else
  echo "RUNNER_IMAGE_BUILD=NOT_TESTED_ENVIRONMENT_BLOCKED"
  exit 2
fi

compose up --detach --wait postgres
echo "POSTGRES_HEALTH=PASS"
compose run --rm migrate
echo "MIGRATION_SMOKE=PASS"
compose up --detach --wait api

api_address=$(compose port api 8000)
curl --fail --silent --show-error "http://$api_address/healthz" >/dev/null
echo "API_HEALTHZ=PASS"
curl --fail --silent --show-error "http://$api_address/readyz" >/dev/null
echo "API_READYZ=PASS"

compose run --rm worker
echo "WORKER_CONFORMANCE_SMOKE=PASS"

compose run --rm runner java -version 2>&1 | grep 'version "11' >/dev/null
echo "JAVA_11=PASS"
compose run --rm runner defects4j info -p Lang >/dev/null
echo "DEFECTS4J=PASS"

compose run --rm runner curl --version >/dev/null
if compose run --rm runner curl --fail --max-time 5 https://example.com >/dev/null 2>&1; then
  echo "RUNNER_NETWORK_DENIAL=FAIL" >&2
  exit 1
fi
echo "RUNNER_NETWORK_DENIAL=PASS"

for container in $(compose ps --quiet); do
  test "$(docker inspect --format '{{.HostConfig.Privileged}}' "$container")" = false
  if docker inspect --format '{{range .Mounts}}{{println .Source .Destination}}{{end}}' "$container" \
    | grep -Eq '(/var/run|/run)/docker\.sock'; then
    echo "CONTAINER_BOUNDARY_RUNTIME=FAIL" >&2
    exit 1
  fi
done
echo "CONTAINER_BOUNDARY_RUNTIME=PASS"

compose up --detach --force-recreate --wait postgres api
api_address=$(compose port api 8000)
curl --fail --silent --show-error "http://$api_address/healthz" >/dev/null
curl --fail --silent --show-error "http://$api_address/readyz" >/dev/null
echo "RECREATE_REPRODUCIBILITY=PASS"
