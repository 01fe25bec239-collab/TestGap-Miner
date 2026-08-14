# CONTRACT-RAG-001 — Repository Localisation and Context Contract

## 1. Metadata and normative scope

| Field | Value |
|---|---|
| Contract ID | `CONTRACT-RAG-001` |
| Version | `1.0.0-draft.1` |
| Status | `DRAFT / INITIAL_IMPLEMENTATION / A2_RAG_REVIEW_REQUIRED / NOT_A4_REVIEWED` |
| Owner | `A2-RAG — Repository Retrieval, Localisation, Ranking, and Context Assembly Component Manager` |
| Implementation agent | `A3-RAG — Repository Retrieval / Localisation Implementation Agent` |
| Consumer | `A2-AGENT-WORKFLOW`, without ownership of RAG definitions |
| Workflow dependency | `CONTRACT-WORKFLOW-001@1.0.0-draft.1` is consumed unchanged |
| Runtime status | `CONTRACT_AND_BASELINE_DATASET_ONLY / PRODUCTION_RETRIEVER_NOT_IMPLEMENTED` |

Normative terms **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are used as in
RFC 2119. The machine-testable implementation is the public API in
`app.retrieval`.

This contract freezes provider-neutral values for a pinned repository manifest,
ranked file candidates, bounded context, and labelled localisation evaluation
input. It does not select or implement an indexer, retriever, model, provider,
database, or Workflow runtime.

## 2. Scope and non-scope

In scope:

- explicit identity domains and pinned Git revision identity;
- immutable localisation/context value objects and fail-closed validation;
- structured, algorithm-neutral candidate ranking explanations;
- repository source provenance and an explicit trust label;
- deterministic ordering, equality, and canonical JSON;
- bounded token-accounting values with overflow rejection;
- a small labelled dataset with explicit relevant file identities.

Out of scope:

- repository crawling, discovery, ingestion, indexing, persistence, or APIs;
- BM25, ripgrep, AST, embedding, vector, hybrid, or LLM retrieval/ranking;
- provider-specific tokenization or model calls;
- Workflow, Queue, Evidence, Evaluation, or Security runtime behavior;
- prompt-injection defense, secure-retrieval completion, and production readiness.

## 3. Identity model

The following immutable types are distinct identity domains even if two values
contain identical text:

| Domain | Type | Validation |
|---|---|---|
| Repository | `RepositoryIdentity` | Explicit bounded ASCII identifier; never inferred from a filesystem path |
| Revision | `RevisionIdentity` | Full lowercase 40-hex SHA-1 or 64-hex SHA-256 Git object identity; abbreviations fail |
| File | `FileIdentity` | Canonical repository-relative ASCII POSIX path |
| Candidate | `CandidateIdentity` | Explicit candidate identity |
| Context item | `ContextItemIdentity` | Explicit selected-context identity |
| Context bundle | `ContextBundleIdentity` | Explicit bundle identity |
| Dataset | `DatasetIdentity` | Explicit dataset identity |
| Dataset case | `DatasetCaseIdentity` | Explicit case identity |

An identity type MUST NOT stand in for another type. Repository identity MUST
NOT be inferred from a local checkout path. Revision identity MUST be pinned and
MUST NOT be a branch name, tag name, symbolic revision, or abbreviated object
identity.

`FileIdentity` is a canonical repository-relative POSIX file path. It MUST NOT
represent the repository root (`.`), be absolute, contain NUL, backslashes, or
`.` / `..` path components. Malformed identities fail closed with
`INVALID_FILE_IDENTITY`; they are not stripped, normalized, or resolved against
the filesystem.

## 4. RepositoryManifest

`RepositoryManifest` contains:

- `repository_id: RepositoryIdentity`;
- `revision_id: RevisionIdentity`;
- `files: tuple[ManifestFile, ...]`.

Each `ManifestFile` binds a `FileIdentity` to a lowercase SHA-256 content digest.
Files are sorted by file identity during construction because manifest order has
no semantic meaning. This representation is manually constructible and requires
no production indexer or filesystem crawl.

An exact duplicate file binding raises `DUPLICATE_IDENTITY`. Reuse of a file
identity with a different digest raises `IDENTITY_CONFLICT`. Neither case can
silently overwrite an earlier binding.

## 5. CandidateFile and ranking explanation

`CandidateFile` contains its own `CandidateIdentity`, repository identity,
revision identity, file identity, and a `RankingExplanation`. Candidate identity
is not a repository, revision, Workflow run, execution, or context-item identity.

`RankingExplanation` contains:

- a positive bounded `rank`;
- a bounded integer `score` in producer-selected score units;
- one or more `RankingSignal` values.

Each signal has a machine-readable `signal` name, signed integer
`contribution`, and bounded explanatory `detail`. Signal names are unique and
sorted canonically. The fields explain supplied ranking facts; they do not
define a retrieval algorithm or require contributions to sum to the score.

`ordered_candidates()` validates a candidate collection and orders it by
`(rank, candidate_id)`. An exact repeated candidate raises
`DUPLICATE_IDENTITY`; the same candidate identity bound to different candidate
data raises `IDENTITY_CONFLICT`.

## 6. Provenance and trust

`Provenance` binds repository identity, pinned revision identity, file identity,
inclusive positive start/end lines, and lowercase SHA-256 of the exact selected
text encoded as UTF-8, including all leading and trailing whitespace. End line
MUST NOT precede start line. `ContextItem` validates that its exact, unmodified
text matches the provenance digest.

Repository source text is untrusted input. The deliberately narrow RAG-001 trust
vocabulary is:

- `UNTRUSTED_REPOSITORY_TEXT`.

`ContextItem` rejects raw or unknown label strings; callers supply the enum
value. Provenance and a digest provide source linkage and integrity evidence.
They do not make source text trustworthy and do not constitute a Security
policy or prompt-injection defense.

## 7. ContextItem

`ContextItem` is one bounded selected unit and contains:

- its own `ContextItemIdentity`;
- the distinct `CandidateIdentity` from which it was selected;
- validated `Provenance`;
- `TrustLabel`;
- non-empty bounded UTF-8 `content`;
- positive bounded supplied `token_count`.

Source content MAY contain leading or trailing spaces, tabs, and newlines,
including content consisting only of whitespace. CONTRACT-RAG-001 MUST preserve
the supplied string exactly and MUST NOT strip, normalize, or otherwise mutate
it.

The contract validates a future producer's supplied token count. It performs no
provider-specific tokenization.

## 8. TokenBudget and ContextBundle

`TokenBudget` exposes `max_tokens`, `consumed_tokens`, `remaining_tokens`, and
`within_budget`. Values are exact integers; booleans, floats, negatives, zero
maximum, and values above `2_000_000` fail. Exact-boundary consumption succeeds.
Consumption above the maximum raises `INVALID_TOKEN_BUDGET`.

`ContextBundle` contains an explicit bundle, repository, and revision identity;
an ordered tuple of context items; and a token budget. Input item order is
semantically meaningful and is preserved in canonical output. Sets and mappings
are rejected as unordered inputs.

Every item's repository/revision provenance MUST match the bundle. The declared
`consumed_tokens` MUST equal the sum of represented item `token_count` values.
Overflow or mismatch fails closed; the bundle never truncates or mutates content
to hide overflow.

An exact repeated context-item identity raises `DUPLICATE_IDENTITY`; the same
identity bound to different item data raises `IDENTITY_CONFLICT`.

## 9. Determinism and serialization

All public domain values are frozen dataclasses with deterministic equality.
Semantically unordered collections (manifest files, ranking signals, candidates,
dataset cases, and relevant ground-truth files) receive documented stable sort
orders. Semantically ordered context items preserve supplied order.

`canonical_json()` uses UTF-8 text, sorted object keys, no non-deterministic
metadata, and stable list ordering. Contract-value JSON is compact. Dataset JSON
uses two-space indentation, sorted keys, and one terminal newline. Serialization
is a deterministic comparison/transport representation, not a cryptographic
canonicalization standard.

## 10. Duplicate, conflict, and validation behavior

Validation is fail closed and uses `LocalisationContractError` with a stable
`LocalisationErrorCode` vocabulary. Invalid values are not silently coerced.

- exact repetition of an identity/binding: `DUPLICATE_IDENTITY`;
- reuse of an identity with different bound data: `IDENTITY_CONFLICT`;
- malformed identities, revisions, paths, ranking, provenance, trust, context,
  budget, or dataset values: their corresponding `INVALID_*` code.

No public collection uses identity-keyed overwrite behavior.

## 11. Labelled localisation baseline dataset

The initial dataset is
`evaluation/datasets/localisation/LOCALISATION_BASELINE_V1.json` with schema
version `testgap.localisation-baseline.v1`. It is a schema and future metric-input
fixture, not a production benchmark or retrieval-performance claim.

Each case contains exactly:

```json
{
  "case_id": "explicit dataset case identity",
  "query": "localisation target text",
  "relevant_file_identities": ["one or more repository-relative file identities"],
  "repository_id": "explicit repository identity",
  "revision_id": "full pinned Git object identity"
}
```

The checked-in dataset contains one single-relevant-file case and one
multiple-relevant-file case. Ground truth is justified by repository definitions
named directly by each query. It does not contain measured predictions or
scores.

Parsing rejects malformed JSON, duplicate JSON keys, unknown/missing fields,
unsupported schema versions, malformed identities, zero ground-truth files,
duplicate relevant files, and duplicate/conflicting case identities. Cases and
relevant files are sorted by identity during validated construction, so loading
is deterministic. Dataset files MUST be UTF-8; decoding failures fail closed as
`INVALID_DATASET`.

## 12. Evaluation input compatibility

Recall@K input compatibility is `PASS`: Evaluation can take a ranked sequence of
predicted `FileIdentity` values, select its first K values, and compare their set
intersection with a case's non-empty `relevant_file_identities`.

MRR input compatibility is `PASS`: Evaluation can enumerate the same ranked
predicted file identities from rank one and identify the first value present in
the case's ground-truth identity set.

This contract provides inputs only. It defines no Evaluation-owned metric
implementation, K value, aggregation rule, performance score, or acceptance
threshold.

## 13. Workflow consumer boundary

Workflow MAY consume validated `RepositoryManifest`, `CandidateFile`,
`ContextItem`, and `ContextBundle` values as bounded input to later orchestration.
Workflow does not own these definitions and MUST NOT need knowledge of RAG
indexing, retrieval, ranking, embedding, storage, or provider implementation to
consume them.

This contract does not modify or redefine `CONTRACT-WORKFLOW-001`, does not claim
that Workflow currently consumes a concrete bundle, and does not implement
Workflow runtime behavior.

## 14. Security and production boundary

RAG-001 makes provenance and the untrusted classification explicit and
preservable. Security-owned sanitization, isolation, injection detection,
authorization, and policy remain outside this contract.

| Claim | Status |
|---|---|
| Prompt-injection defense complete | `NO` |
| Secure retrieval complete | `NO` |
| Production ready | `NO` |
| Production retriever implemented | `NO` |
| Indexing runtime implemented | `NO` |
| Embeddings or vector database implemented | `NO` |
