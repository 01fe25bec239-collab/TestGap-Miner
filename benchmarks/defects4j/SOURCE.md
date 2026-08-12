# Defects4J benchmark corpus — source and provenance

This directory holds TestGap Miner's frozen benchmark **dataset identity**. It
does not vendor Defects4J itself.

## Corpus

| Field | Value |
| --- | --- |
| Corpus | Defects4J |
| Corpus release | 3.0.1 |
| Manifest corpus identifier | `DEFECTS4J_3_0_1` |
| Official project | `rjust/defects4j` |
| Upstream tag/ref | `v3.0.1` |
| Upstream license | MIT |
| Language | JAVA |
| Test ecosystem | JUNIT |
| Required Java major (for Defects4J execution) | 11 |
| Required timezone | `America/Los_Angeles` |

## What is checked in here

| File | Purpose |
| --- | --- |
| `DEFECTS4J_MVP_V1.json` | The immutable V1 golden manifest, in canonical form |
| `DEFECTS4J_MVP_V1.sha256` | SHA-256 of the manifest file, in `shasum -a 256` format |
| `SOURCE.md` | This provenance and licensing record |

Only the minimal metadata required for reproducible case identity is recorded.
Defects4J source repositories, benchmark project checkouts and bug archives are
**not** vendored into TestGap Miner, and must never be committed here.

## Provenance, recorded separately per metadata class

| Metadata class | Provenance at V1 |
| --- | --- |
| Project / bug membership | Independently checked against `rjust/defects4j` tag `v3.0.1`, using the README active-bug table and `framework/projects/<Project>/active-bugs.csv` |
| Canonical b/f revision IDs | Defects4J canonical version-id convention (`<bug_id>b` / `<bug_id>f`), validated structurally against each case `bug_id` |
| Queried source revision IDs | `NOT_QUERIED` — no usable Defects4J runtime on the authoring host; recorded as `UNVERIFIED`, `vcs: UNKNOWN`, with a `null` value |
| Triggering tests | `NOT_QUERIED` — recorded as `UNVERIFIED` with an empty list; never inferred from issue text or class names |
| Modified-class metadata | `NOT_QUERIED` — not used at V1 |
| Local smoke execution evidence | See `docs/evaluation/DEFECTS4J_MVP_V1_SMOKE.md`; no smoke run has been performed |

Selection uses ordinal 1 for the first active bug and
`median_ordinal = floor((N + 1) / 2)` for the median, where `N` is the active-bug
count in the pinned ordering. Thus even-sized sets select the lower middle bug.

| Project | Active IDs | Count | Median ordinal | Selected median bug |
| --- | --- | ---: | ---: | ---: |
| Chart | `1-26` | 26 | 13 | 13 |
| Gson | `1-18` | 18 | 9 | 9 |
| Jsoup | `1-93` | 93 | 47 | 47 |
| Lang | `1,3-17,19-24,26-47,49-65` | 61 | 31 | 34 |
| Math | `1-106` | 106 | 53 | 53 |
| Time | `1-20,22-27` | 26 | 13 | 13 |

The first selected bug is bug 1 for every project. This check establishes only
selection membership. It does not verify triggering tests, source revisions or
failure shapes.

Canonical Defects4J version IDs identify the corpus revisions. Optional
upstream revisions are VCS-neutral: `SVN` values preserve opaque identifiers
such as `2264`, while `GIT` values must be 40-character lowercase hex SHAs.
`UNVERIFIED` source revisions must carry a null value and may not assert an
upstream revision.

## Immutability

After A2 acceptance, the bytes of `DEFECTS4J_MVP_V1.json` and its matching
`DEFECTS4J_MVP_V1.sha256` are immutable. Runtime verification must be recorded
as separately versioned evidence bound to V1; it must not promote any V1
`UNVERIFIED` field in place. A golden-manifest change requires a newly
authorized explicit version such as `DEFECTS4J_MVP_V2`; V2 is not created here.

## Validation

```sh
uv run --project apps/api --frozen --group test \
  python -m evaluation.defects4j_manifest validate \
  benchmarks/defects4j/DEFECTS4J_MVP_V1.json
```

The checksum is also independently checkable with the system tool:

```sh
cd benchmarks/defects4j && shasum -a 256 -c DEFECTS4J_MVP_V1.sha256
```
