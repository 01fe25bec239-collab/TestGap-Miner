# Local stack

The default Compose stack is PostgreSQL 16 plus the FastAPI API. Migration,
worker conformance, and the Defects4J 3.0.1 Java 11 runner are one-shot tools in
the `tools` profile; the worker is not a daemon.

```sh
cp .env.example .env
# Replace every <...> password placeholder with a URL-safe local value.
docker compose config
docker compose build api worker runner
docker compose up -d --wait postgres
docker compose --profile tools run --rm migrate
docker compose up -d --wait api
curl --fail http://127.0.0.1:8000/healthz
curl --fail http://127.0.0.1:8000/readyz
docker compose --profile tools run --rm worker
docker compose --profile tools run --rm runner java -version
docker compose --profile tools run --rm runner defects4j info -p Lang
```

Run the complete isolated probe with `scripts/deploy/probe-local-stack.sh`. It
uses a unique Compose project, ephemeral credentials and host ports, and removes
its volumes on exit. Reset the ordinary local stack only with:

```sh
TESTGAP_RUNTIME=local scripts/deploy/local-reset.sh --yes
```

API, worker, migration, and runner containers are non-root, capability-free,
read-only except for bounded tmpfs or named-volume paths, and use process and
memory limits. The runner has no Docker network and no host mounts. PostgreSQL
retains the existing bootstrap, migration, application, and test role split.

This is a local containment foundation, not a complete secure sandbox. Named
volume disk quotas, per-attempt disposal, descendant process-tree enforcement,
production providers, and full supply-chain pinning remain outside this slice.
