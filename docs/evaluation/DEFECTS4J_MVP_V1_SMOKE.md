# DEFECTS4J_MVP_V1 — reproducibility smoke record

Manifest version: `DEFECTS4J_MVP_V1`
Corpus: Defects4J 3.0.1 (`DEFECTS4J_3_0_1`)
Task: `EVAL-001-BENCHMARK-GOLDEN-MANIFEST-001`

## Result

**`DEFECTS4J_RUNTIME_REQUIRED`**

**`REPRODUCIBILITY_SMOKE_COMPLETE` is NOT claimed.** No Defects4J checkout,
compile or triggering-test execution has been attempted, because no Defects4J
runtime exists on the authoring host.

## Environment evidence

Captured in the task worktree at commit
`2ffbd75900fb4bd8da1104b3b7862d80243e9302`.

| Fact | Value |
| --- | --- |
| Worktree commit | `2ffbd75900fb4bd8da1104b3b7862d80243e9302` |
| Operating system | macOS 26.5.2 (build 25F84) |
| Kernel / architecture | Darwin 25.5.0, `arm64` |
| `defects4j` on `PATH` | **not found** |
| Defects4J version | **not determinable — not installed** |
| Java major | **11** (satisfies the requirement) |
| `TZ` | **unset** |

### `command -v defects4j`

```
$ command -v defects4j
$ echo $?
1
```

No output, exit status 1.

### `java -version`

```
$ java -version
openjdk version "11.0.29" 2025-10-21 LTS
OpenJDK Runtime Environment Corretto-11.0.29.7.1 (build 11.0.29+7-LTS)
OpenJDK 64-Bit Server VM Corretto-11.0.29.7.1 (build 11.0.29+7-LTS, mixed mode)
```

Amazon Corretto 11, `arm64`, at
`/Library/Java/JavaVirtualMachines/amazon-corretto-11.jdk/Contents/Home`. This
is the only JVM installed, and it **is** the Java major version Defects4J
execution requires.

### `TZ`

```
$ printf 'TZ=%s\n' "${TZ:-<unset>}"
TZ=<unset>
```

`TZ` is unset in the ambient shell. This is not itself a blocker: smoke commands
would export `TZ=America/Los_Angeles` per-process, without mutating the host.

### Installation search

The following locations were checked and contain no Defects4J installation:

```
/Users/omkar/defects4j
/Users/omkar/.defects4j
/Users/omkar/tools/defects4j
/Users/omkar/Documents/defects4j
/usr/local/defects4j
/opt/defects4j
/opt/homebrew/bin/defects4j
/usr/local/bin/defects4j
```

Every directory on `PATH` was also scanned for an executable named
`defects4j`; there were no hits.

## Blocker summary

| Requirement for a usable V1 reproducibility runtime | State |
| --- | --- |
| Defects4J 3.0.1 available | **NOT MET** — not installed |
| Defects4J initialized (`defects4j info -p Lang`) | **NOT MET** — cannot run, not installed |
| Java major 11 for Defects4J execution | MET — Corretto 11.0.29 |
| Smoke process uses `TZ=America/Los_Angeles` | Would be set per-process at smoke time |

One of four conditions is met. The runtime is **not usable**, so no smoke claim
is made.

## Actions deliberately not performed

Per task constraints, and because these would mutate the host system:

- Defects4J was **not** installed, downloaded, cloned or initialized.
- Java was **not** installed, replaced, or switched.
- No system-wide environment variable was modified; `TZ` was read, never set
  globally.
- No benchmark project checkout was created, and none was committed.

## Predeclared smoke subset (not executed)

Frozen before any execution outcome was observed:

| Case ID | Project | Bug | Buggy rev | Fixed rev | Status |
| --- | --- | --- | --- | --- | --- |
| `D4J-GSON-001` | Gson | 1 | `1b` | `1f` | NOT_ATTEMPTED — runtime unavailable |
| `D4J-LANG-001` | Lang | 1 | `1b` | `1f` | NOT_ATTEMPTED — runtime unavailable |
| `D4J-MATH-001` | Math | 1 | `1b` | `1f` | NOT_ATTEMPTED — runtime unavailable |

Three different project domains, chosen independently of any TestGap Miner or
model outcome.

## Consequences for the manifest

Because no authoritative Defects4J metadata could be queried, every case in
`DEFECTS4J_MVP_V1` records:

- `triggering_tests`: `{"status": "UNVERIFIED", "values": []}`
- `buggy_revision.source_revision`: `{"status": "UNVERIFIED", "value": null, "vcs": "UNKNOWN"}`
- `fixed_revision.source_revision`: `{"status": "UNVERIFIED", "value": null, "vcs": "UNKNOWN"}`
- `failure_shape`: `{"status": "UNVERIFIED", "value": null}`

Nothing was inferred from issue text, class names or naming convention. The
canonical `<bug_id>b` / `<bug_id>f` version IDs are sufficient to identify each
corpus revision and are the only revision metadata asserted.

Corpus membership is **unaffected** by this blocker. No case was added, removed,
substituted or reordered because of the environment.

## What would complete this record

On a host with Defects4J 3.0.1 installed and initialized, and Java 11 active:

```sh
export TZ=America/Los_Angeles
defects4j info -p Lang

# metadata for all twelve frozen cases, before any compile smoke
defects4j query -p Lang -q "bug.id,revision.id.buggy,revision.id.fixed,tests.trigger"

# per-case smoke, in a disposable directory outside this worktree
work=$(mktemp -d)
defects4j checkout -p Lang -v 1b -w "$work/lang-1b" && defects4j compile -w "$work/lang-1b"
defects4j checkout -p Lang -v 1f -w "$work/lang-1f" && defects4j compile -w "$work/lang-1f"
rm -rf "$work"
```

Record checkout, compile, trigger-metadata availability and triggering-test
results **separately for the buggy and the fixed revision** of each attempted
case in separately versioned evidence bound to `DEFECTS4J_MVP_V1`; do not edit
the accepted V1 bytes. A failing case is smoke evidence and must not be
substituted or removed.

If queried Defects4J 3.0.1 metadata ever contradicts a frozen case identity,
stop and report `SPECIFICATION_CONFLICT` with the exact metadata evidence rather
than editing the case.

## Repository-local validation is unaffected

The manifest, validator and tests require no Defects4J runtime, no network and
no LLM call. Both of these pass on this host:

```sh
uv run --project apps/api --frozen --group test \
  python -m evaluation.defects4j_manifest validate \
  benchmarks/defects4j/DEFECTS4J_MVP_V1.json

uv run --project apps/api --frozen --group test \
  python -m pytest tests/evaluation -q
```
