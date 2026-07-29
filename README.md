# TestGap Miner

TestGap Miner is a Java/JUnit regression-test generation system built around an execution-backed workflow:

1. accept Defects4J or GitHub bug context;
2. localise relevant repository files;
3. generate a test-only patch;
4. compile and execute it against buggy and fixed revisions;
5. perform at most one bounded repair attempt;
6. package evidence for human review.

## MVP boundaries

- Java and JUnit only.
- Defects4J-first benchmark workflow.
- Public GitHub demonstration.
- Draft pull requests and comments only.
- No auto-merge, production-code modification, enterprise tenancy, billing, or unrestricted tools.

## Authoritative specifications

Project specifications are stored under `docs/specifications/`.

The TestGap Miner PRD and Agent 1/A2 manager decisions outrank generic platform research when they conflict.

## Initial repository state

This repository was bootstrapped from an empty GitHub repository. No application implementation is implied by the presence of this documentation.
