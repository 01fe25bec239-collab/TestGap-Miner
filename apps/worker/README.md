# TestGap worker process-supervision foundation

This standalone, standard-library-only Rust crate provides raw execution
facts for a future worker runtime.

## Implemented

- direct executable plus explicit argument-vector execution (no inserted shell)
- explicit working directory and `ClearAndSet` / `InheritAndOverride` environment policy
- monotonic wall-clock timeout and cooperative cancellation polling
- direct-child termination and reaping after timeout or cancellation
- concurrently drained, independently bounded raw stdout and stderr capture
- deterministic exit/failure classification and duration measurement
- provider-neutral resource-limit requests and observations
- a self-contained Rust process fixture and integration tests

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
- Java, JUnit, Defects4J, or benchmark harnesses
- production worker security or production readiness

`Child::kill` terminates only the direct child and is not a sandbox or a
portable process-tree guarantee.
