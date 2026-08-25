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

fail() {
  echo "$1" >&2
  exit 1
}

compose config >"$config_file"
echo "COMPOSE_VALIDITY=PASS"

cfg=$(cat "$config_file")

if grep -Eq 'privileged: true|(/var/run|/run)/docker\.sock' "$config_file"; then
  fail "CONTAINER_BOUNDARY_STATIC=FAIL"
fi
echo "CONTAINER_BOUNDARY_STATIC=PASS"

service_block() {
  awk -v header="$1" '
    index($0, header) == 1 {inblk = 1; next}
    inblk && (/^[^ ]/ || /^  [A-Za-z0-9_-]+:/) {inblk = 0}
    inblk {print}
  ' "$config_file"
}

expect_match() {
  printf '%s\n' "$1" | grep -Eq "$2" || fail "$3=FAIL"
}

reject_match() {
  if printf '%s\n' "$1" | grep -Eq "$2"; then
    fail "$3=FAIL"
  fi
}

worker_block=$(service_block "  worker:")
runner_block=$(service_block "  runner:")
volumes_block=$(awk '/^volumes:/{inblk=1; next} inblk && /^[^ ]/{inblk=0} inblk{print}' "$config_file")

reject_match "$cfg" 'runner-workspace' "STATIC_PERSISTENT_EXECUTION_VOLUME"
volumes_entry_count=$(printf '%s\n' "$volumes_block" | grep -Ec '^  [A-Za-z0-9_-]+:' || true)
[ "$volumes_entry_count" = "1" ] || fail "STATIC_VOLUMES_POSTGRES_ONLY=FAIL"
printf '%s\n' "$volumes_block" | grep -Eq '^  postgres-data:' || fail "STATIC_VOLUMES_POSTGRES_ONLY=FAIL"
reject_match "$volumes_block" 'workspace' "STATIC_NO_EXECUTION_NAMED_VOLUME"

static_sandbox_asserts() {
  blk=$1
  svc=$2
  ws_size=$3
  expect_match "$blk" '^    network_mode: none$' "STATIC_NETWORK_NONE_$svc"
  expect_match "$blk" '^    read_only: true$' "STATIC_READ_ONLY_ROOT_$svc"
  expect_match "$blk" '^    init: true$' "STATIC_INIT_$svc"
  expect_match "$blk" '^    cap_drop:$' "STATIC_CAP_DROP_$svc"
  expect_match "$blk" '^      - ALL$' "STATIC_CAP_DROP_ALL_$svc"
  expect_match "$blk" '^    security_opt:$' "STATIC_SECURITY_OPT_$svc"
  expect_match "$blk" '^      - no-new-privileges:true$' "STATIC_NO_NEW_PRIVILEGES_$svc"
  expect_match "$blk" '^    pids_limit: [1-9]' "STATIC_PIDS_LIMIT_$svc"
  expect_match "$blk" '^    mem_limit: ' "STATIC_MEM_LIMIT_$svc"
  expect_match "$blk" '^    cpus: ' "STATIC_CPUS_$svc"
  expect_match "$blk" "^      - /workspace:size=${ws_size},mode=1777\$" "STATIC_WORKSPACE_TMPFS_BOUND_$svc"
  expect_match "$blk" '^      - /tmp:size=' "STATIC_TMP_TMPFS_BOUND_$svc"
  reject_match "$blk" '^    volumes:' "STATIC_NO_MOUNTS_$svc"
  reject_match "$blk" 'privileged' "STATIC_NOT_PRIVILEGED_$svc"
}

static_sandbox_asserts "$worker_block" worker 256m
echo "STATIC_SANDBOX_WORKER=PASS"
static_sandbox_asserts "$runner_block" runner 512m
echo "STATIC_SANDBOX_RUNNER=PASS"

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
  fail "RUNNER_NETWORK_DENIAL=FAIL"
fi
echo "RUNNER_NETWORK_DENIAL=PASS"

attempt_absent() {
  if docker ps -a --format '{{.Names}}' | grep -Fxq "$1"; then
    fail "$2=FAIL"
  fi
}

worker_uid=$(compose run --rm --name "$project-w-uid" worker id -u)
if [ "$worker_uid" = "0" ]; then
  fail "NON_ROOT_WORKER=FAIL"
fi
worker_image_user=$(docker inspect --format '{{.Config.User}}' testgap-worker:local)
case "$worker_image_user" in
  "" | "root" | "0" | ":0" | "root:0" | "0:0") fail "NON_ROOT_WORKER_IMAGE=FAIL" ;;
esac
echo "NON_ROOT_WORKER=PASS"

runner_uid=$(compose run --rm --name "$project-r-uid" runner id -u)
if [ "$runner_uid" = "0" ]; then
  fail "NON_ROOT_RUNNER=FAIL"
fi
runner_image_user=$(docker inspect --format '{{.Config.User}}' testgap-defects4j-runner:3.0.1)
case "$runner_image_user" in
  "" | "root" | "0" | ":0" | "root:0" | "0:0") fail "NON_ROOT_RUNNER_IMAGE=FAIL" ;;
esac
echo "NON_ROOT_RUNNER=PASS"

compose run --rm --name "$project-w-tooling" worker sh -c 'command -v getent && command -v bash && command -v timeout' >/dev/null \
  || fail "WORKER_PROBE_TOOLING_MISSING=FAIL"
echo "WORKER_PROBE_TOOLING=PASS"

if compose run --rm --name "$project-w-dns" worker getent hosts example.com >/dev/null 2>&1; then
  fail "WORKER_NETWORK_DENIAL_DNS=FAIL"
fi
if compose run --rm --name "$project-w-tcp" worker timeout 10 bash -c ': </dev/tcp/example.com/443' >/dev/null 2>&1; then
  fail "WORKER_NETWORK_DENIAL_TCP=FAIL"
fi
echo "WORKER_NETWORK_DENIAL=PASS"

if compose run --rm --name "$project-r-dns" runner getent hosts example.com >/dev/null 2>&1; then
  fail "RUNNER_NETWORK_DENIAL_DNS=FAIL"
fi
echo "RUNNER_NETWORK_DENIAL_DNS=PASS"

marker="sec003-marker-$$"

worker_a_out=$(compose run --rm --name "$project-w-attempt-a" worker \
  sh -c "printf '%s\n' '$marker' > /workspace/sec003_marker && cat /workspace/sec003_marker")
printf '%s\n' "$worker_a_out" | grep -q "$marker" || fail "ATTEMPT_A_MARKER_WRITE_WORKER=FAIL"
attempt_absent "$project-w-attempt-a" "ATTEMPT_A_DISPOSAL_WORKER"
if ! compose run --rm --name "$project-w-attempt-b" worker sh -c 'test ! -e /workspace/sec003_marker'; then
  fail "CROSS_ATTEMPT_STATE_LEAK=YES"
fi
attempt_absent "$project-w-attempt-b" "ATTEMPT_B_DISPOSAL_WORKER"
echo "CROSS_ATTEMPT_ISOLATION_WORKER=PASS"

runner_a_out=$(compose run --rm --name "$project-r-attempt-a" runner \
  sh -c "printf '%s\n' '$marker' > /workspace/sec003_marker && cat /workspace/sec003_marker")
printf '%s\n' "$runner_a_out" | grep -q "$marker" || fail "ATTEMPT_A_MARKER_WRITE_RUNNER=FAIL"
attempt_absent "$project-r-attempt-a" "ATTEMPT_A_DISPOSAL_RUNNER"
if ! compose run --rm --name "$project-r-attempt-b" runner sh -c 'test ! -e /workspace/sec003_marker'; then
  fail "CROSS_ATTEMPT_STATE_LEAK=YES"
fi
attempt_absent "$project-r-attempt-b" "ATTEMPT_B_DISPOSAL_RUNNER"
echo "CROSS_ATTEMPT_ISOLATION_RUNNER=PASS"

compose run --rm --name "$project-w-success" worker sh -c ':' >/dev/null
attempt_absent "$project-w-success" "SUCCESS_CONTAINER_DISPOSAL_WORKER"
if compose run --rm --name "$project-w-failure" worker sh -c 'exit 7' >/dev/null 2>&1; then
  fail "FAILURE_ATTEMPT_UNEXPECTED_SUCCESS_WORKER=FAIL"
fi
attempt_absent "$project-w-failure" "FAILURE_CONTAINER_DISPOSAL_WORKER"
echo "DISPOSAL_WORKER=PASS"

compose run --rm --name "$project-r-success" runner sh -c ':' >/dev/null
attempt_absent "$project-r-success" "SUCCESS_CONTAINER_DISPOSAL_RUNNER"
if compose run --rm --name "$project-r-failure" runner sh -c 'exit 7' >/dev/null 2>&1; then
  fail "FAILURE_ATTEMPT_UNEXPECTED_SUCCESS_RUNNER=FAIL"
fi
attempt_absent "$project-r-failure" "FAILURE_CONTAINER_DISPOSAL_RUNNER"
echo "DISPOSAL_RUNNER=PASS"

compose run --rm --name "$project-w-write" worker \
  sh -c 'touch /workspace/.sec003_write_probe && touch /tmp/.sec003_write_probe'
attempt_absent "$project-w-write" "WRITABLE_PROBE_DISPOSAL_WORKER"
if compose run --rm --name "$project-w-ro" worker sh -c 'touch /usr/.sec003_readonly_probe' >/dev/null 2>&1; then
  fail "READ_ONLY_ROOT_ENFORCED_WORKER=FAIL"
fi
worker_fs_kb=$(compose run --rm --name "$project-w-df" worker df -k -P /workspace /tmp)
worker_ws_kb=$(printf '%s\n' "$worker_fs_kb" | awk '$NF=="/workspace"{print $2}')
worker_tmp_kb=$(printf '%s\n' "$worker_fs_kb" | awk '$NF=="/tmp"{print $2}')
[ "$worker_ws_kb" = "262144" ] || fail "WORKSPACE_SIZE_BOUND_WORKER=FAIL"
[ "$worker_tmp_kb" = "262144" ] || fail "TMP_SIZE_BOUND_WORKER=FAIL"
echo "BOUNDED_WRITABLE_STORAGE_WORKER=PASS"

compose run --rm --name "$project-r-write" runner \
  sh -c 'touch /workspace/.sec003_write_probe && touch /tmp/.sec003_write_probe'
attempt_absent "$project-r-write" "WRITABLE_PROBE_DISPOSAL_RUNNER"
if compose run --rm --name "$project-r-ro" runner sh -c 'touch /opt/defects4j/.sec003_readonly_probe' >/dev/null 2>&1; then
  fail "READ_ONLY_ROOT_ENFORCED_RUNNER=FAIL"
fi
runner_fs_kb=$(compose run --rm --name "$project-r-df" runner df -k -P /workspace /tmp)
runner_ws_kb=$(printf '%s\n' "$runner_fs_kb" | awk '$NF=="/workspace"{print $2}')
runner_tmp_kb=$(printf '%s\n' "$runner_fs_kb" | awk '$NF=="/tmp"{print $2}')
[ "$runner_ws_kb" = "524288" ] || fail "WORKSPACE_SIZE_BOUND_RUNNER=FAIL"
[ "$runner_tmp_kb" = "524288" ] || fail "TMP_SIZE_BOUND_RUNNER=FAIL"
echo "BOUNDED_WRITABLE_STORAGE_RUNNER=PASS"

res_worker="$project-res-worker"
res_runner="$project-res-runner"
compose run --detach --name "$res_worker" worker sleep 60 >/dev/null
compose run --detach --name "$res_runner" runner sleep 60 >/dev/null

inspect_attempt_container() {
  cname=$1
  label=$2
  [ "$(docker inspect --format '{{.HostConfig.Privileged}}' "$cname")" = "false" ] \
    || fail "PRIVILEGED_$label=FAIL"
  [ "$(docker inspect --format '{{.HostConfig.NetworkMode}}' "$cname")" = "none" ] \
    || fail "NETWORK_NONE_RUNTIME_$label=FAIL"
  [ "$(docker inspect --format '{{.HostConfig.ReadonlyRootfs}}' "$cname")" = "true" ] \
    || fail "READ_ONLY_ROOT_RUNTIME_$label=FAIL"
  runtime_user=$(docker inspect --format '{{.Config.User}}' "$cname")
  case "$runtime_user" in
    "" | "root" | "0" | ":0" | "root:0" | "0:0") fail "NON_ROOT_RUNTIME_$label=FAIL" ;;
  esac
  cap_drop_list=$(docker inspect --format '{{range .HostConfig.CapDrop}}{{println .}}{{end}}' "$cname")
  printf '%s\n' "$cap_drop_list" | grep -Fxq ALL || fail "CAP_DROP_ALL_RUNTIME_$label=FAIL"
  cap_add_count=$(docker inspect --format '{{len .HostConfig.CapAdd}}' "$cname")
  [ "$cap_add_count" = "0" ] || fail "CAP_ADD_EMPTY_$label=FAIL"
  security_opt_list=$(docker inspect --format '{{range .HostConfig.SecurityOpt}}{{println .}}{{end}}' "$cname")
  printf '%s\n' "$security_opt_list" | grep -Fxq 'no-new-privileges:true' || fail "NO_NEW_PRIVILEGES_RUNTIME_$label=FAIL"
  nano_cpus=$(docker inspect --format '{{.HostConfig.NanoCpus}}' "$cname")
  [ "$nano_cpus" -gt 0 ] 2>/dev/null || fail "CPU_BOUND_$label=FAIL"
  memory_bytes=$(docker inspect --format '{{.HostConfig.Memory}}' "$cname")
  [ "$memory_bytes" -gt 0 ] 2>/dev/null || fail "MEMORY_BOUND_$label=FAIL"
  pids_limit=$(docker inspect --format '{{.HostConfig.PidsLimit}}' "$cname")
  [ "$pids_limit" -gt 0 ] 2>/dev/null || fail "PID_BOUND_$label=FAIL"
  [ "$(docker inspect --format '{{len .HostConfig.Devices}}' "$cname")" = "0" ] \
    || fail "DEVICE_PASSTHROUGH_$label=FAIL"
  pid_mode=$(docker inspect --format '{{.HostConfig.PidMode}}' "$cname")
  [ -z "$pid_mode" ] || fail "HOST_PID_NAMESPACE_$label=FAIL"
  mount_types=$(docker inspect --format '{{range .Mounts}}{{println .Type}}{{end}}' "$cname")
  if printf '%s\n' "$mount_types" | grep -Fxq bind; then
    fail "HOST_MOUNT_$label=FAIL"
  fi
  mounts_json=$(docker inspect --format '{{json .Mounts}}' "$cname")
  if printf '%s\n' "$mounts_json" | grep -Eq '(/var/run|/run)/(docker|containerd)\.sock'; then
    fail "RUNTIME_SOCKET_$label=FAIL"
  fi
  echo "SANDBOX_RUNTIME_BOUNDARY_$label=PASS"
}

inspect_attempt_container "$res_worker" WORKER
inspect_attempt_container "$res_runner" RUNNER

docker rm --force "$res_worker" "$res_runner" >/dev/null
attempt_absent "$res_worker" "RESOURCE_PROBE_DISPOSAL_WORKER"
attempt_absent "$res_runner" "RESOURCE_PROBE_DISPOSAL_RUNNER"
echo "RESOURCE_AND_HOST_BOUNDARY_DISPOSAL=PASS"

for container in $(compose ps --quiet); do
  test "$(docker inspect --format '{{.HostConfig.Privileged}}' "$container")" = false
  if docker inspect --format '{{range .Mounts}}{{println .Source .Destination}}{{end}}' "$container" \
    | grep -Eq '(/var/run|/run)/docker\.sock'; then
    fail "CONTAINER_BOUNDARY_RUNTIME=FAIL"
  fi
done
echo "CONTAINER_BOUNDARY_RUNTIME=PASS"

compose up --detach --force-recreate --wait postgres api
api_address=$(compose port api 8000)
curl --fail --silent --show-error "http://$api_address/healthz" >/dev/null
curl --fail --silent --show-error "http://$api_address/readyz" >/dev/null
echo "RECREATE_REPRODUCIBILITY=PASS"

compose down --volumes --remove-orphans >/dev/null
if [ -n "$(docker ps -a --filter "label=com.docker.compose.project=$project" -q)" ]; then
  fail "ORPHAN_CONTAINER=YES"
fi
if [ -n "$(docker volume ls --filter "label=com.docker.compose.project=$project" -q)" ]; then
  fail "ORPHAN_VOLUME=YES"
fi
if [ -n "$(docker network ls --filter "label=com.docker.compose.project=$project" -q)" ]; then
  fail "ORPHAN_NETWORK=YES"
fi
echo "PROBE_CLEANUP_ORPHANS=NONE"
