# DEFECTS4J_MVP_V1 — frozen golden benchmark manifest

Task: `EVAL-001-BENCHMARK-GOLDEN-MANIFEST-001`
Owner: A2-EVALUATION
Status: repository-local foundation complete; Defects4J runtime verification outstanding

## 1. Objective

Freeze the MVP benchmark **dataset identity** for TestGap Miner: which
Defects4J bugs are in the evaluation corpus, how each case is identified, which
metadata is verified versus merely asserted, and what may never change without a
new manifest version.

This document and the manifest own benchmark dataset identity and its
validation, and nothing else. No evidence schema, execution schema, metric
computation, release threshold, harness or runtime is defined here.

## 2. Versions

| Field | Value |
| --- | --- |
| Corpus | Defects4J |
| Corpus release | 3.0.1 |
| Manifest corpus identifier | `DEFECTS4J_3_0_1` |
| Manifest version | `DEFECTS4J_MVP_V1` |
| Schema version | `testgap.defects4j.golden-manifest.v1` |
| Language | `JAVA` |
| Test ecosystem | `JUNIT` |
| Required Java major | `11` |
| Required timezone | `America/Los_Angeles` |

Java 11 and `America/Los_Angeles` come from Defects4J's own reproducibility
constraints and from PRD requirement REL-001; they are recorded in the manifest
so that any future execution run must pin them rather than discover them.

## 3. Case-selection methodology

**Methodology ID:** `STRATIFIED_PROJECT_POSITION_V1`

Stratify the corpus across six Defects4J project domains, then take two active
bugs per project **purely by ordinal position** within that project's active bug
list:

| Position rule | Meaning |
| --- | --- |
| `FIRST_ACTIVE_BUG_BY_ORDINAL_POSITION` | Ordinal 1 |
| `MEDIAN_ACTIVE_BUG_BY_ORDINAL_POSITION` | `floor((N + 1) / 2)`, where `N` is the pinned project's active-bug count |

For odd `N`, the median rule selects the unique middle active bug. For even
`N`, it selects the **lower of the two middle active bugs**.

Position is the only selector. Neither TestGap Miner behaviour, retrieval
quality, model identity, generated-test outcome, compile duration nor bug
difficulty may influence membership.

### Project strata and domain balance

| Project | Domain category | Cases |
| --- | --- | --- |
| Chart | `CHARTING_RENDERING_DATA` | 2 |
| Gson | `JSON_SERIALIZATION` | 2 |
| Jsoup | `HTML_PARSING_DOM` | 2 |
| Lang | `LANGUAGE_TEXT_UTILITIES` | 2 |
| Math | `NUMERIC_ALGORITHMS` | 2 |
| Time | `DATE_TIME_LOGIC` | 2 |

Six domains, two cases each: small enough to run inside the MVP performance
budget, heterogeneous enough that a result is not an artifact of one library's
style.

### Authoritative selection provenance

Membership was independently checked against `rjust/defects4j` tag `v3.0.1`,
using the README active-bug table and
`framework/projects/<Project>/active-bugs.csv`:

| Project | Active IDs | Count | Median ordinal | Selected median bug |
| --- | --- | ---: | ---: | ---: |
| Chart | `1-26` | 26 | 13 | 13 |
| Gson | `1-18` | 18 | 9 | 9 |
| Jsoup | `1-93` | 93 | 47 | 47 |
| Lang | `1,3-17,19-24,26-47,49-65` | 61 | 31 | 34 |
| Math | `1-106` | 106 | 53 | 53 |
| Time | `1-20,22-27` | 26 | 13 | 13 |

Bug 1 is the first active bug selected for all six projects. This verification
is membership/provenance evidence only; it does not verify triggering tests,
source revisions, failure shapes or any runtime result.

## 4. The frozen twelve-case set

| Case ID | Project | Bug | Buggy rev | Fixed rev | Selection reason |
| --- | --- | --- | --- | --- | --- |
| `D4J-CHART-001` | Chart | 1 | `1b` | `1f` | first |
| `D4J-CHART-013` | Chart | 13 | `13b` | `13f` | median |
| `D4J-GSON-001` | Gson | 1 | `1b` | `1f` | first |
| `D4J-GSON-009` | Gson | 9 | `9b` | `9f` | median |
| `D4J-JSOUP-001` | Jsoup | 1 | `1b` | `1f` | first |
| `D4J-JSOUP-047` | Jsoup | 47 | `47b` | `47f` | median |
| `D4J-LANG-001` | Lang | 1 | `1b` | `1f` | first |
| `D4J-LANG-034` | Lang | 34 | `34b` | `34f` | median |
| `D4J-MATH-001` | Math | 1 | `1b` | `1f` | first |
| `D4J-MATH-053` | Math | 53 | `53b` | `53f` | median |
| `D4J-TIME-001` | Time | 1 | `1b` | `1f` | first |
| `D4J-TIME-013` | Time | 13 | `13b` | `13f` | median |

Total: **12 selected, 0 excluded.**

## 5. Why selection precedes model outcomes

The corpus was frozen **before any TestGap Miner model benchmark outcome
existed**. There is therefore no path by which a case could have been picked
because the product happens to do well on it.

The manifest records this structurally as
`selection.frozen_before_model_outcomes: true`, and the validator rejects a
manifest where that flag is anything other than `true`.

### No-result-cherry-picking rule

A case must never be removed, replaced or substituted because it is difficult,
because checkout or compile fails, because a trigger is hard to reproduce, or
because a model or retrieval strategy performs badly on it. Those are
**execution outcomes**: they are recorded as smoke or run evidence, never as
corpus-selection reasons.

Concretely, none of the following is a legitimate reason to touch corpus
membership: slow compile, failed compile, failed checkout, difficult trigger,
poor retrieval, poor model performance, or benchmark execution being
inconvenient.

## 6. Revision representation

Each case records two distinct things, and never conflates them:

**A. Canonical Defects4J revision identity** — `1b` / `1f`. Always present.
These are sufficient to identify the corpus revision, and the validator checks
each against the case's `bug_id` (`<bug_id>b`, `<bug_id>f`), rejects the two
being identical, and rejects a mismatch.

**B. Exact upstream VCS revision** — only when actually queried and verified:

```json
"buggy_revision": {
  "defects4j_version_id": "1b",
  "source_revision": { "status": "UNVERIFIED", "value": null, "vcs": "UNKNOWN" }
}
```

`vcs` is `GIT`, `SVN` or `UNKNOWN`. `VERIFIED` requires `GIT` or `SVN` plus a
non-empty exact upstream identifier. Git values must be 40-character lowercase
hex SHAs; SVN values are opaque strings, so numeric revisions such as `2264`
remain exact. `UNVERIFIED` requires a `null` value and may not assert a revision.
The same verified VCS revision may not appear as both buggy and fixed. At V1
every source revision is `UNVERIFIED` because no Defects4J runtime was available.

## 7. Triggering-test verification states

```json
"triggering_tests": { "status": "UNVERIFIED", "values": [] }
```

| Status | Rule |
| --- | --- |
| `VERIFIED` | `values` must contain at least one test, sorted, with no duplicates |
| `UNVERIFIED` | `values` must be empty |

Triggering tests are never inferred from issue text, class names or convention.
At V1 all twelve cases are `UNVERIFIED` with empty values. Future authoritative
runtime results (`tests.trigger`, `tests.trigger.cause`, revision IDs and
modified classes) belong in separately versioned evidence bound to this V1,
never as an in-place edit to the manifest.

Failure shape uses the same envelope and is `UNVERIFIED` / `null` throughout V1
— i.e. `UNKNOWN_UNVERIFIED`. No claim is made about bug or failure shape,
because no objective metadata supports one yet.

## 8. Exclusion semantics

Every case makes inclusion unambiguous through three fields:

| `selected` | `exclusion_state` | `exclusion_reason` | Valid? |
| --- | --- | --- | --- |
| `true` | `NOT_EXCLUDED` | `null` | yes |
| `false` | `EXCLUDED` | non-empty string | yes |
| `true` | `EXCLUDED` | any | **rejected** |
| `false` | `NOT_EXCLUDED` | any | **rejected** |
| `false` | `EXCLUDED` | empty / missing | **rejected** |
| `true` | `NOT_EXCLUDED` | non-null | **rejected** |

V1 has no exclusions, but the model is supported and tested so that a future
version can express one without a schema change.

## 9. Immutability and the V2 policy

After A2 acceptance, `DEFECTS4J_MVP_V1.json` bytes and the matching
`DEFECTS4J_MVP_V1.sha256` are immutable.

- Do **not** edit V1 to promote source revisions, triggering tests, failure
  shapes or any other `UNVERIFIED` metadata.
- Record future runtime verification as separately versioned evidence bound to
  `DEFECTS4J_MVP_V1`.
- If the golden manifest must change, create a new explicit version such as
  `DEFECTS4J_MVP_V2` under future authorization. V2 is not implemented here.
- The checksum lives in a sidecar file, not inside the JSON, so there is no
  self-referential digest.

## 10. Validation

The validator is standard-library only — no new dependency was added, and none
is needed.

```sh
# structure + canonical form + checksum
uv run --project apps/api --frozen --group test \
  python -m evaluation.defects4j_manifest validate \
  benchmarks/defects4j/DEFECTS4J_MVP_V1.json

# the test suite
uv run --project apps/api --frozen --group test \
  python -m pytest tests/evaluation -q
```

`canonicalize` prints canonical bytes to stdout and never rewrites a checked-in
file:

```sh
uv run --project apps/api --frozen --group test \
  python -m evaluation.defects4j_manifest canonicalize \
  benchmarks/defects4j/DEFECTS4J_MVP_V1.json
```

### What the validator rejects

Duplicate case ID; duplicate project/bug identity; missing project; missing bug
ID; missing buggy or fixed revision; a revision ID that does not match its bug
ID; identical buggy/fixed identities; malformed revision structure; unsupported
language; unsupported test ecosystem; missing or unversioned manifest; a
manifest/case version mismatch; an unrecognized schema version; an invalid
exclusion state; selected-and-excluded; excluded-without-reason;
unselected-without-exclusion; an invalid triggering-test verification state;
`VERIFIED` triggering tests with an empty list; duplicate or unsorted triggering
tests; unsorted or duplicate case ordering; an invalid VCS type; a malformed Git
SHA; an asserted value under `UNVERIFIED`; the same verified VCS revision used as
both buggy and fixed revision; a
filename/version mismatch; a non-canonical file; a checksum mismatch; and
duplicate JSON keys.

Validation fails deterministically and reports **every** problem found, with an
actionable message. Invalid records are never silently normalized.

### Canonical form

UTF-8, two-space indent, sorted keys, cases ordered by `benchmark_case_id`,
triggering tests sorted, exactly one trailing newline, no timestamps and no
machine-specific absolute paths. The checked-in V1 file is already canonical,
and a test asserts it.

## 11. Predeclared smoke subset

Frozen **before** observing any execution outcome:

`D4J-GSON-001`, `D4J-LANG-001`, `D4J-MATH-001`

Three different project domains, independent of model outcomes, small enough for
environment verification. A failing smoke case is **evidence**, not grounds for
removal or substitution.

## 12. Current runtime and smoke state

**`DEFECTS4J_RUNTIME_REQUIRED`** — no smoke run has been performed.

`defects4j` is not installed on the authoring host. Java 11 is present, which
satisfies half the requirement, but the benchmark itself is absent and was
deliberately not installed. Full environment evidence is in
[`DEFECTS4J_MVP_V1_SMOKE.md`](DEFECTS4J_MVP_V1_SMOKE.md).

This blocks metadata verification and reproducibility smoke only. It does not
affect the manifest, the validator or the tests, none of which require a
Defects4J runtime.

## 13. Limitations

- **Selection membership was independently checked from Defects4J 3.0.1
  active-bug metadata, but no runtime metadata was queried.** If a future query
  contradicts a frozen case identity, that is a `SPECIFICATION_CONFLICT` to be
  reported — not a silent case replacement or V1 edit.
- **No triggering tests, source commits or failure shapes are recorded.** All
  are explicitly `UNVERIFIED`.
- **No reproducibility smoke evidence exists.** Checkout, compile and
  trigger-execution behaviour for all twelve cases is unknown.
- The membership check does not imply runtime verification of triggering tests,
  source revisions or failure shapes.
- The manifest deliberately carries no evidence schema, execution schema, metric
  definition or release threshold. Those belong to later, separately owned work.
