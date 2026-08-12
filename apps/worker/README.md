# TestGap worker execution foundation

This standalone, standard-library-only Rust crate provides raw execution
facts and provider-neutral Java/JUnit/Defects4J adapters for a future worker
runtime.

## Implemented

- direct executable plus explicit argument-vector execution (no inserted shell)
- explicit working directory and `ClearAndSet` / `InheritAndOverride` environment policy
- monotonic wall-clock timeout and cooperative cancellation polling
- direct-child termination and reaping after timeout or cancellation
- concurrently drained, independently bounded raw stdout and stderr capture
- deterministic exit/failure classification and duration measurement
- provider-neutral resource-limit requests and observations
- a self-contained Rust process fixture and integration tests
- Java compilation through a configurable `javac` executable, explicit argv,
  platform-aware classpath joining, and an allowlisted `-d` / `-classpath`
  surface
- JUnitCore-style invocation through a configurable Java executable, runner
  main class, classpaths, and class-level test targets
- Defects4J `compile`, `test`, and `test -t <class::method>` command invocation
- deterministic adapter classification for success/failure, unavailable tools,
  timeouts, cancellation, and runner failures while preserving the complete
  underlying `ExecutionResult`
- conservative parsing of JUnitCore `OK (N test[s])` and
  `Tests run: N, Failures: N` summaries and Defects4J `Failing tests: N`
- conservative ASCII Java class/method and Defects4J project/test identifier
  validation, kept separate from opaque filesystem-path handling
- a bounded `runtime_conformance` binary that probes local Java, javac, JUnitCore,
  and Defects4J through `ProcessSupervisor`, preserves raw execution facts, and
  distinguishes `TESTED`, `ENVIRONMENT_BLOCKED`, and `FAIL`
- real Java compilation, marker execution, timeout, cancellation, and bounded
  output checks when Java and javac are locally available
- opt-in real JUnitCore checks from `TESTGAP_JUNIT_CLASSPATH` and opt-in
  Defects4J compile/test checks from `TESTGAP_DEFECTS4J_WORKDIR`; neither input
  is searched for or downloaded

Spawn failure wins when no process starts. While a child is active, the
supervisor checks cancellation before timeout; the first observed terminating
condition remains primary. Therefore cancellation wins if both are observed
in the same poll. Additional cleanup or capture failures are retained after
the primary failure.

CPU, memory, disk/temp-workspace, process-count, file-count, and custom future
limits are preserved as requests but reported as `NotEnforced` with no
fabricated usage. Output bounds are reported as `CaptureBoundEnforced`; the
wall-clock timeout is reported as `SupervisorTimeoutEnforced`.

## Explicitly not implemented

- secure sandbox, network isolation, filesystem sandbox, or container isolation
- cgroups, namespaces, or descendant process-tree isolation
- CPU, memory, disk, filesystem, or process-count OS enforcement
- Queue integration, Workflow orchestration, Database persistence, or Evidence semantics
- Workflow lifecycle transitions or a full Defects4J benchmark harness
- production worker security or production readiness

`Child::kill` terminates only the direct child and is not a sandbox or a
portable process-tree guarantee.

The deterministic `cargo test` suite uses controlled local Rust behavior and
does not require external runtimes. Run local conformance separately:

```text
cargo run --bin runtime_conformance
```

`TESTGAP_JUNIT_CLASSPATH` supplies an existing local JUnit classpath.
`TESTGAP_DEFECTS4J_BIN` may select an existing Defects4J executable, and
`TESTGAP_DEFECTS4J_WORKDIR` supplies an existing checkout for compile/test.

Report meanings are deliberately narrow:

- `IMPLEMENTED`: the bounded local conformance harness and detection paths
- `TESTED`: the applicable external runtime operation was actually invoked in
  that report run
- `ENVIRONMENT_BLOCKED`: a required executable, classpath, or checkout was not
  available or configured; this is not a fabricated pass
- `NOT IMPLEMENTED`: secure sandboxing, production resource isolation, Queue,
  Workflow, Database, Evidence, Evaluation, Security, and Deployment behavior

No JUnit jars, Java runtime, or Defects4J installation are downloaded,
installed, or treated as a permanent project guarantee.
