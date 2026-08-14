# CONTRACT-SEC-001 — Security Baseline, Policy Boundaries, and System Safety Contract

## Metadata and Normative Scope

| Field | Value |
|---|---|
| Contract ID | `CONTRACT-SEC-001` |
| Version | `1.0.0-draft.1` |
| Status | `DRAFT / A2_SECURITY_REVIEW_PASSED / A4_REVIEW_PASSED` |
| Owner | `A2-SECURITY — Security Component Manager` |
| Authoring Subordinate | `A3-SECURITY — Subordinate Security Contract Authoring Agent` |
| Task | `SEC-001-CONTRACT-SEC-001-DRAFT-001-A3-CORRECTION-002` |
| Parent Task | `SEC-001-CONTRACT-SEC-001-DRAFT-001` |
| Foundation Task | `SEC-001-TESTGAP-CURRENT-MAIN-THREAT-MODEL-001` |
| Authorized Baseline | `7a3aee9b5bfe48e769c6013ba45090806fb5b5c1` |
| Required Branch | `agent2/security-contract-sec-001-draft` |
| Worktree | `/Users/omkar/Documents/TestGap-Miner-wt-security-contract-sec-001-draft` |
| Implementation Readiness | `NOT_IMPLEMENTATION_READY` |
| Runtime Status | `NO_RUNTIME_CODE_AUTHORIZED / UNTOUCHED` |
| Security Acceptance Status | `CONTRACT_DRAFT_ACCEPTED / FINAL_SYSTEM_SECURITY_ACCEPTANCE_NOT_GRANTED` |
| Production Readiness | `NO` |

The terms **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** in this document are normative as defined in RFC 2119.

### Contract Status & Draft Disclaimer

This document is a **DRAFT ONLY** (`CONTRACT-SEC-001@1.0.0-draft.1`).

- It defines Security requirements, policy boundaries, classification rules, redaction semantics, and safety invariants for TestGap-Miner.
- The presence of any security requirement in this document does **NOT** prove or imply that the requirement is currently implemented in application source code, infrastructure, or deployment configurations.
- Merging runtime code or merged component contracts does **NOT** automatically grant Security acceptance.
- Unsupported completion claims or claims of production readiness are strictly forbidden.
- Production readiness remains **NO**.

---

## Authoritative Security Foundation (SEC-001 Threat Model Baseline)

This contract normatively encodes the accepted `SEC-001` current-main threat-model foundation. The accepted High and Critical findings MUST remain visible and MUST NOT be silently downgraded, ignored, or marked resolved without authorized Security re-assessment:

1. **HF-001 (CRITICAL)**: Worker sandbox/isolation gap. Execution currently relies on host/process-level containment without hardened, disposable, non-root container or virtualized sandbox isolation.
2. **HF-002 (HIGH)**: Queue `SECURITY_REJECTION` is not sticky. A security-rejected job or message could potentially be re-queued, retried, or delivered to non-security validation handlers without a fail-closed terminal disposition.
3. **HF-003 (HIGH)**: Queue redrive current-authorization provenance gap. Administrative redrive operations can re-execute messages using stale authorization context or missing current actor re-validation.
4. **HF-004 (HIGH)**: Evidence integrity, authenticity, and storage gap. Evidence references and unkeyed digests lack producer authenticity proofs, making payloads susceptible to substitution, unverified claims, or unauthorized storage state changes.
5. **HF-005 (HIGH)**: Production Auth shared-correlation/multi-instance gap. Browser session correlation and callback handles rely on single-node/local state assumptions that do not support secure multi-instance production deployment (`AUTH_RUNTIME_SAFETY_CLASS: LOCAL_NON_PRODUCTION_ONLY`).
6. **HF-006 (HIGH)**: Prerequisite risk for future RAG / untrusted-content / prompt injection. Untrusted issue descriptions, PR comments, and repository source code lack isolation boundaries, context minimization, and prompt injection defenses prior to future LLM integration.
7. **HF-007 (HIGH)**: Prerequisite risk for GitHub webhook and publication security. Webhook ingestion and draft/comment publication lack full durable replay protection, mandatory payload verification, and strict publication-time authorization checks.
8. **HF-008 (HIGH)**: Prerequisite risk for browser CSP and XSS hardening. Browser dashboard surfaces lack strict Content Security Policy (CSP), anti-amplification controls, and complete output encoding before exposure to untrusted content.

Prerequisite risks (HF-006, HF-007, HF-008) must NOT be transformed into claims that currently absent flows (such as RAG ingestion) are already exploitable end-to-end; rather, they serve as mandatory pre-conditions that MUST be satisfied before such features are enabled or deployed to production.

---

## 1. Data / Payload Classification

Security establishes explicit data classifications for all data types handled across TestGap-Miner. Where classification is unknown for a sensitive path or field, components MUST **fail closed**.

| Data / Payload Class | Queue Payload Entry | Log Entry | Model Context Entry | Evidence Persistence | Redaction Required | Public Disclosure Allowed |
|---|---|---|---|---|---|---|
| **Secrets** (signing keys, API keys, webhook secrets, DB passwords) | **PROHIBITED** | **PROHIBITED** | **PROHIBITED** | **PROHIBITED** | **ALWAYS** | **PROHIBITED** |
| **Credentials / Session Material** (OAuth tokens, PKCE verifiers, session cookies, auth headers) | **PROHIBITED** | **PROHIBITED** | **PROHIBITED** | **PROHIBITED** | **ALWAYS** | **PROHIBITED** |
| **Access / Refresh Tokens** | **PROHIBITED** | **PROHIBITED** | **PROHIBITED** | **PROHIBITED** | **ALWAYS** | **PROHIBITED** |
| **Authentication / Authorization Material** (opaque handles, grant IDs) | Allowed (Opaque Ref Only) | Redacted / Minimized | **PROHIBITED** | Opaque Ref Only | Yes (if raw) | **PROHIBITED** |
| **Repository Source / Content** | **PROHIBITED** (Ref Only) | **PROHIBITED** (Ref Only) | Restricted / Bounded | **PROHIBITED** (Ref Only) | If secrets detected | Restricted / Governed |
| **Issue / PR / User-Supplied Content** | **PROHIBITED** (Ref Only) | Sanitized / Truncated | Restricted / Isolated | **PROHIBITED** (Ref Only) | Sanitized | Restricted / Governed |
| **Model Prompts / Context** | **PROHIBITED** (Ref Only) | Redacted / Truncated | Allowed (Isolated) | **PROHIBITED** (Ref Only) | Yes | **PROHIBITED** |
| **Model Results / Output** | **PROHIBITED** (Ref Only) | Bounded / Redacted | Input to Validation | Opaque Ref / Manifest | Yes | Conditional / Governed |
| **Execution Input / Argv** | Bounded Allowlist | Bounded / Redacted | **PROHIBITED** | Opaque Ref / Manifest | Yes | **PROHIBITED** |
| **Execution Stdout / Stderr** | **PROHIBITED** (Ref Only) | **PROHIBITED** (Ref Only) | **PROHIBITED** | Opaque Ref (Artefact) | Yes | **PROHIBITED** |
| **Evidence Metadata** | Allowed (Opaque Ref) | Bounded | **PROHIBITED** | Persisted (Canonical) | Yes | Bounded / Governed |
| **Evidence Artefacts** | **PROHIBITED** (Ref Only) | **PROHIBITED** (Ref Only) | **PROHIBITED** | Persisted (Object Store) | Yes | **PROHIBITED** |
| **Queue Metadata** | Allowed (Envelope) | Bounded | **PROHIBITED** | Provenance Ref | Yes | **PROHIBITED** |
| **Queue Payload Content** | Allowlist Scalars Only | **PROHIBITED** | **PROHIBITED** | **PROHIBITED** | Yes | **PROHIBITED** |
| **Security / Audit Events** | Opaque Ref Only | Bounded / Redacted | **PROHIBITED** | Persisted (Audit) | Yes | **PROHIBITED** |
| **Public-Safe Output** (e.g. status summary) | Allowed | Allowed | N/A | Allowed | Verified Safe | Allowed |

---

## 2. Trust / Provenance Labels

Security normatively distinguishes system states and data provenance. Components MUST NOT treat these labels as synonyms.

- `TRUSTED`: Component or data verified by explicit cryptographic or security-enforced mechanisms.
- `AUTHENTICATED`: Principal or entity whose identity has been verified by an identity provider.
- `AUTHORIZED`: Principal explicitly granted permission for a specific action on a specific resource tuple.
- `UNTRUSTED`: External or unverified data source (user input, PR content, raw webhooks, raw LLM output).
- `REPOSITORY_CONTROLLED`: Data sourced from a git repository; subject to untrusted instruction checks.
- `USER_SUPPLIED`: Direct input from an external user or web request.
- `PROVIDER_SUPPLIED`: Data returned from an external API provider (e.g. GitHub API, Supabase Auth).
- `MODEL_GENERATED`: Text, diffs, or code produced by an AI model; inherently untrusted until validated.
- `EXECUTION_PRODUCED`: Output or log material generated by candidate execution in a runner environment.
- `SYSTEM_GENERATED`: Metadata generated internally by trusted system control planes.
- `PUBLIC_SAFE`: Content classified as eligible for specifically authorized disclosure channels under applicable Security policy.

### Mandatory Non-Conflation Axioms

1. `AUTHENTICATED != AUTHORIZED`: Authentication proves identity; it does NOT grant authorization for any action or repository tuple.
2. `HASHED != AUTHENTICATED`: A checksum or hash proves data consistency only; it does NOT establish producer authenticity or trust.
3. `INTEGRITY_CHECKED != AUTHENTICATED_PRODUCER`: Verifying byte integrity does NOT prove the identity or trustworthiness of the producer.
4. `MODEL_GENERATED != TRUSTED`: Model outputs are unverified candidate data and MUST NOT be executed, trusted, or published without validation.
5. `REPOSITORY_CONTROLLED != SAFE_INSTRUCTION`: Code or configuration files in a repository must NOT be treated as trusted system instructions.
6. `TRACE_REFERENCE != IDENTITY`: Tracing values (`X-Request-ID`, `X-Correlation-ID`) are operational metadata and MUST NOT serve as principal identities.
7. `TRACE_REFERENCE != AUTHORITY`: A trace reference grants zero permission or capability.
8. A provenance or reference string alone MUST NOT establish identity, authority, or authenticity.
9. `PUBLIC_SAFE != TRUSTED / AUTHORIZED / AUTHENTIC`: `PUBLIC_SAFE` means ONLY that content is eligible for the specifically authorized disclosure channel under the applicable Security policy. `PUBLIC_SAFE` MUST NOT imply `TRUSTED`, `AUTHENTICATED`, `AUTHORIZED`, `AUTHENTIC`, `INTEGRITY_VERIFIED`, `SAFE_INSTRUCTION`, `MODEL_SAFE`, or `TOOL_AUTHORIZED`. Public disclosure classification is independent from identity, provenance, instruction trust, and execution authority.
10. `TRACE_REFERENCE != REDRIVE_AUTHORITY`: An administrator actor reference alone is trace metadata and MUST NOT grant queue redrive authority.

---

## 3. Redaction Semantics

Redaction rules govern data before persistence, Queue serialization, logging, human display, and Evidence publication.

### Policy-Driven Redaction Rules & Requirements

1. **Authoritative Classification Source**: The Data / Payload Classification table in Section 1 is authoritative for redaction requirements across all storage and communication sinks.
2. **Mandatory Redaction for Protected Classes**: Data classes marked `ALWAYS` or `YES` for redaction in Section 1 MUST undergo applicable security redaction scanning before writing to protected sinks, disk, database, object storage, Queue envelopes, log channels, display surfaces, or Evidence publication.
3. **Conditional Classes**: Data classes marked conditional (e.g. `If secrets detected`, `Sanitized`, `Bounded / Redacted`) MUST be evaluated according to active Security classification policy before persistence or exposure.
4. **Public-Safe & Exempt Metadata**: `PUBLIC_SAFE` data and policy-exempt structured metadata MAY bypass content redaction only where explicitly allowed by classification policy.
5. **Unknown Classification Fail-Closed**: If data classification is unknown on a potentially sensitive path or field, components MUST fail closed (block publication/persistence and flag for security audit).
6. **Pre-Serialization & Pre-Logging Redaction**: Queue producers MUST redact payload fields prior to envelope serialization. Log formatters MUST redact credentials, tokens, cookies, secrets, and raw payload bytes.
7. **Encoded / Derived Secret Handling**: Redaction engines MUST scan for base64-encoded, hex-encoded, URL-encoded, and truncated secret patterns in addition to raw secret strings.
8. **Mandatory Secret Exclusion**: Secrets, credentials, access/refresh tokens, and signing keys MUST ALWAYS be excluded or redacted; raw secrets MUST NEVER be written to logs, Queue payloads, model context, or Evidence persistence.
9. **Bounded Redaction Result Vocabulary**:
   - `REDACTED_CLEAN`: Scanning completed; sensitive patterns sanitized.
   - `NO_SECRETS_DETECTED`: Scanning completed; no sensitive patterns found.
   - `REDACTION_FAILED_FAIL_CLOSED`: Scanning failed or encountered unresolvable input; content blocked.
   - `UNSCANNABLE_CONTENT_BLOCKED`: Binary or unparseable content blocked from non-artefact text channels.
10. **REDACTED Meaning Limitation**: `REDACTED` indicates sanitization was attempted; it does **NOT** automatically imply `PUBLIC_SAFE`, `COMPLETE`, `AUTHENTIC`, or `VERIFIED`.

---

## 4. Security Event Semantics

Security events represent security-relevant occurrences across system components.

### Bounded Security Event Envelope

Every Security Event MUST conform to the bounded, secret-free envelope schema:

- `event_id`: Opaque UUID string.
- `event_type` / `event_version`: Stable string identifier and version (e.g. `SECURITY_POLICY_VIOLATION@1.0`).
- `occurred_at`: UTC timestamp (RFC 3339).
- `source_component`: Originating component identifier (`AUTH`, `QUEUE`, `EXECUTION`, `EVIDENCE`, `API`, `WORKFLOW`).
- `environment`: Deployment/execution environment identifier (`development`, `test`, `production`).
- `actor_type`: Bounded enum (`HUMAN_USER`, `GITHUB_APP_INSTALLATION`, `SYSTEM_SERVICE`, `UNAUTHENTICATED`).
- `actor_reference`: Approved opaque actor reference (never raw credentials or PII).
- `affected_resource_reference`: Opaque resource/repo reference.
- `reason_category`: Bounded classification (`UNAUTHORIZED_ACCESS`, `SECRET_DETECTED`, `INTEGRITY_MISMATCH`, `STALE_WORKER_ATTEMPT`, `PATH_TRAVERSAL_ATTEMPT`, `POISON_WORK_REJECTION`, `RATE_LIMIT_EXCEEDED`).
- `decision_outcome`: `BLOCKED`, `DENIED`, `REJECTED`, `FLAGGED`.
- `severity`: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.
- `blocking_effect`: Boolean indicating whether the protected operation was stopped.
- `policy_version`: Active Security policy version identifier.
- `correlation_id`: Opaque tracing reference (where safe).
- `redaction_status`: `REDACTED_CLEAN` or `NO_SECRETS_DETECTED` (or versioned compatible representation).

### Explicit Security Event Envelope Bounds

The Security Event envelope is bounded. Every contract and event version MUST explicitly define:
- Maximum length for each string and reference field;
- Maximum cardinality for bounded collections (if any);
- Maximum serialized event-envelope size;
- Permitted character set and encoding constraints where necessary.

Oversized, malformed, unbounded, or indeterminate mandatory Security events MUST fail closed for protected operations. Versioned limits MUST be supplied by Security policy; contracts MUST NOT leave event fields or envelope sizes unconstrained.

### Explicit Payload Prohibitions

Security Event envelopes MUST NEVER contain:
- Raw access tokens, refresh tokens, authorization codes, PKCE verifiers, session cookies;
- Authorization headers (`Bearer ...`);
- Signing keys, private keys, webhook secrets;
- Raw provider payload dumps;
- Raw secret-bearing execution stdout/stderr.

### Versioned Compatibility Mapping & Foreign Representations

Component-specific redaction and Security Event representations MAY map to the normative `CONTRACT-SEC-001` semantic states through an explicit versioned compatibility mapping. Existing accepted foreign-contract values (such as Auth's accepted `SECRET_FREE` redaction status) remain valid until their owning contract/runtime is separately migrated. This contract-authoring task does NOT require an Auth runtime rename.

### Pipeline Status & Sink Failure

- A durable global Security-event pipeline does **NOT** currently exist (`SECURITY_EVENT_PIPELINE: NOT_IMPLEMENTED`). This contract does NOT create a durable global Security-event pipeline claim.
- Where a Security Event is mandatory for a protected operation (e.g. logging a security rejection during execution), failure of the event sink MUST cause the protected operation to **fail closed**.

---

## 5. Integrity vs Authenticity

Security normatively enforces the distinction between integrity verification policy outcomes, MAC verification, asymmetric signature attribution, and producer authenticity.

| Dimension | Mechanism | What It Proves | What It CANNOT Prove |
|---|---|---|---|
| **Checksum / Hash Integrity** | Unkeyed digest (SHA-256) | Content consistency against accidental corruption | Producer identity, authorization, origin, authenticity, non-repudiation |
| **Completeness** | Manifest field validation | All declared components are present | Authenticity or non-repudiation of individual components |
| **Provenance Reference** | Opaque identifier linkage | Traceability to originating record ID | That referenced record was created by a trusted producer |
| **Message Authentication Code (MAC)** | Shared-key HMAC | Integrity and origin authentication relative to possession of a shared key | Non-repudiation (multiple shared-key holders can generate valid MACs), producer identity (unless approved key-to-producer binding exists), authorization |
| **Digital Signature** | Asymmetric Public Key Signature | Origin authentication and stronger attribution (when approved asymmetric key-to-producer identity binding and custody policy exists) | Application authorization; non-repudiation (unless Security policy & custody model explicitly support it) |

### Normative MAC and Digital Signature Semantics

1. **Message Authentication Code (MAC)**:
   - Verifies content integrity and origin authentication relative to possession of a shared key.
   - MUST NOT be claimed to provide non-repudiation, because multiple holders of the shared key can generate valid MACs.
   - Does NOT establish producer identity unless an approved key-to-producer binding policy explicitly establishes it.

2. **Digital Signature**:
   - MAY support origin authentication and stronger attribution ONLY when an approved asymmetric key-to-producer identity binding and custody policy exists.
   - MUST NOT automatically imply application authorization.
   - Non-repudiation MUST NOT be claimed unless the approved Security policy and key custody/provenance model specifically support that property.

### VERIFIED and Integrity Policy Semantics

`VERIFIED` means that the applicable Security-approved integrity verification policy succeeded.

`VERIFIED` or an opaque verification reference alone MUST NOT establish:
- Producer identity;
- Authorization;
- Trusted origin;
- Cryptographic authenticity;
- Non-repudiation.

Those stronger properties exist only if the referenced approved verification policy explicitly establishes authenticated cryptographic provenance under an asymmetric key binding policy. An unkeyed digest or hash (e.g. SHA-256) establishes content consistency and integrity only, and does NOT establish authenticity or non-repudiation.

---

## 6. Cryptographic / Key Ownership Boundary

Security exclusively owns Security cryptographic policy, cryptographic algorithm selection, Security cryptographic canonicalization policy, and key custody semantics. Security does NOT generically own all domain canonicalization (e.g. Queue domain serialization, Evidence content canonicalization, or Execution domain serialization).

### Cryptographic Verification Policy Requirements

Every approved cryptographic verification policy MUST bind or identify:
1. **Algorithm Identifier & Version**: Explicit cryptographic algorithm and version specification.
2. **Canonicalization Policy Identifier & Version**: Security cryptographic canonicalization policy identifier and version.
3. **Key Identifier & Version**: Unique key identifier and key version.
4. **Environment**: Execution/deployment environment (`development`, `test`, `production`).
5. **Producer / Key Binding**: Explicit key-to-producer identity binding where authenticity or attribution is claimed.
6. **Key Lifecycle State**: Bounded key lifecycle state from the required vocabulary: `ACTIVE`, `RETIRED`, `REVOKED`.
7. **Rotation Semantics**: Policy for scheduled and emergency key rotation.
8. **Historical Verification Rules**: Explicit verification rules for historical material created under rotated or retired keys.
9. **Revoked-Key Handling**: Immediate fail-closed invalidation for signatures or MACs produced by or evaluated against revoked keys.
10. **Fail-Closed Verification Behavior**: Any verification failure, key state mismatch, or unknown key MUST result in an immediate `FAIL_CLOSED` outcome, terminating the operation and emitting a Security Event.

### Provider Neutrality and Environment Separation

- **Provider Selection**: Concrete Key Management Service (KMS) selection (AWS KMS, GCP KMS, Azure Key Vault, HashiCorp Vault, etc.) is **UNSELECTED / EXTERNAL** (`KMS_PROVIDER: UNSELECTED`). No KMS provider is chosen by this draft.
- **Environment Separation**: Test environments MUST use isolated ephemeral test keys. Production keys MUST NEVER be loaded into local or CI environments.

---

## 7. Command / Tool / Path Policy

Security defines strict path containment and executable execution controls for worker runtime environments, explicitly distinguishing executable/toolchain paths from repository/candidate data paths.

### A. Executable / Toolchain Path Policy

Executables MAY reside outside the candidate workspace ONLY when their canonical resolved location is explicitly authorized by the Execution/Security tool policy.

Executable authorization MUST require:
1. **Approved Canonical Executable Location**: Canonical resolved absolute path of the executable.
2. **Explicit Executable / Tool Allowlist**: Strict allowlist of authorized binary paths. Execution of arbitrary or unlisted binaries is prohibited.
3. **Optional Hash / Signature Verification**: Binary hash or digital signature MAY be evaluated as additional integrity evidence, but path authorization MUST NOT be granted based on a hash alone.
4. **Symlink-Safe Resolution**: Path resolution MUST verify symlinks and canonical paths to prevent executable substitution.
5. **Structured Execution Only**: Invoking subprocesses via shell interpreters (`sh -c`, `bash -c`, `cmd.exe`) is **PROHIBITED**. All execution MUST use structured, array-based `executable + argv` execution models (`execve`).
6. **Argv Control Limitation**: Structured `argv` is a positive input control only and MUST NOT be treated as a complete sandbox solution.

### B. Repository / Candidate / Generated Data Path Policy

All repository source code, candidate build artifacts, generated test logs, and ephemeral worker data MUST remain strictly confined to the authorized disposable workspace directory unless an explicit, separately approved runtime mount exists.

Path handling MUST strictly enforce:
1. **Canonical Workspace Confinement**: Candidate data operations MUST occur entirely within the assigned disposable workspace directory.
2. **Traversal Rejection**: Path parameters containing `..`, leading slashes, path traversal sequences, or unauthorized absolute host paths MUST be rejected (`FAIL_CLOSED`).
3. **Symlink Escape Prevention**: Symlinks pointing outside the candidate workspace directory MUST be rejected (`FAIL_CLOSED`).
4. **Host-Path Access Rejection**: Unauthorized access to host system directories (`/etc`, `/var`, `/usr`, `/home`, host root) by candidate data operations is strictly prohibited.
5. **Environment Scrubbing**: Inherited host environment variables MUST be scrubbed. Only an explicit allowlist of environment variables MAY be passed to child processes. Secret-bearing environment variables MUST NOT be passed to candidate execution environments.
6. **Workspace Cleanup**: Child processes MUST be confined to their assigned workspace and automatic workspace purge MUST be enforced upon completion, failure, or cancellation.

---

## 8. Sandbox / Resource Policy

Security defines mandatory production requirements for worker execution containment.

### Production Sandbox Isolation Requirements

Production execution MUST enforce:
- Disposable isolated execution containers/VMs per attempt;
- Complete filesystem isolation (read-only root filesystem, isolated ephemeral `/tmp`);
- Network isolation (default zero outbound network access during test execution);
- Non-root user execution (`nobody` or unprivileged dedicated uid/gid);
- Restricted host mounts (no host socket, device, or sensitive system mounts);
- Strict CPU quotas, Memory quotas, Disk/workspace quotas;
- Process-count limits (`pids_limit`) and File-count limits;
- Monitored execution timeouts and cooperative/forced cancellation;
- Descendant process group containment and killing (`SIGKILL` process tree cleanup);
- Automatic workspace purge upon completion, failure, or compromise.

### Current Sandbox Completion Status

Current runtime mechanisms (timeout enforcement, log output truncation, process-group termination) do **NOT** satisfy secure-sandbox completion:

```yaml
SECURE_SANDBOX_COMPLETE: NO
RESOURCE_ISOLATION_COMPLETE: NO
```

---

## 9. Queue Security Policy

Security defines mandatory validation and fence semantics for asynchronous Queue operations.

1. **Publication-Time Validation**: Producers MUST perform strict schema validation, allowlist enforcement, and secret redaction before enqueueing.
2. **Payload Allowlisting**: Queue payloads MUST contain scalar metadata and opaque references only. Prohibited contents include credentials, tokens, cookies, raw source code, patches, prompts, full logs, and execution binaries.
3. **Sticky Security Rejection**: When a message or attempt is rejected for a security violation (`SECURITY_REJECTION`), the rejection disposition MUST be **sticky** and **fail-closed**.
   - A security-rejected work item MUST NOT remain eligible for protected effects, result acceptance, or queue acknowledgement.
   - Ordinary Queue redelivery or transport retry MUST NOT re-evaluate a security-rejected message unless a separately authorized Security-corrected transition explicitly permits recovery.
4. **Delivery Authenticity & Authorization Freshness**: Queue receipt does NOT establish authorization. Current authorization MUST be re-validated prior to executing protected effects.
5. **Fence Semantics**: Monotonic claim fences MUST gate all worker results. Stale or replaced workers holding expired leases MUST be rejected.
6. **Redrive Authorization Provenance**: Administrative redrive operations MUST require fresh authorization and explicit redrive authorization provenance. An administrator actor reference alone is trace metadata and MUST NOT grant redrive authority.
   - Redrive authorization provenance MUST bind at minimum:
     - Authenticated actor/principal reference;
     - `REDRIVE` action;
     - Source message / dead-letter / resource identity;
     - Authorization decision / context reference;
     - Applicable repository / tenant / resource scope (where relevant);
     - Policy version;
     - Decision freshness / expiry;
     - Revocation and current-authorization validation.
   - Stored references or caller-supplied booleans MUST NOT themselves establish authority.
   - Authorization semantics remain owned by A2-AUTH; Queue redrive implementation remains owned by A2-QUEUE.
7. **Queue Provider Status**:
   ```yaml
   QUEUE_PROVIDER: UNSELECTED
   PRODUCTION_QUEUE_PROVIDER: NOT_IMPLEMENTED
   PHYSICAL_QUEUE_DURABILITY: NOT_IMPLEMENTED
   ```

---

## 10. RAG / Untrusted Content Policy

Security establishes future mandatory controls for untrusted external content and Retrieval-Augmented Generation (RAG) flows.

1. **Untrusted Content Sources**: Repository source code, issue bodies, PR descriptions, PR comments, build logs, and external documents are classified as `UNTRUSTED`.
2. **Instruction / Data Separation**: Untrusted content MUST NEVER be concatenated directly into system prompt instruction channels without boundary markers and prompt isolation controls.
3. **Prompt Injection & Content Processing Defenses**: Direct and indirect prompt injection defenses, context minimization, encoded instruction detection, and policy-driven control character handling MUST be enforced before feeding data to AI models.
4. **Unicode & Control-Character Policy**: Universal destructive character stripping is NOT required. Components MUST enforce policy that can:
   - Detect;
   - Classify;
   - Normalize where semantics permit;
   - Escape or render inertly;
   - Annotate;
   - Reject or fail closed;
   according to content type and trust boundary.
   For repository and source code content, components MUST NOT silently mutate canonical source provenance. A sanitized model-facing representation MUST remain attributable to its raw source through approved opaque provenance or Evidence references.
5. **RAG Provenance Preservation Through Transformations**:
   Every:
   - Retrieved source unit;
   - Extracted section;
   - Derived chunk;
   - Normalized/sanitized representation;
   - Model-context fragment
   MUST retain or carry an approved opaque reference to:
   - Originating source / provenance;
   - Applicable trust label;
   - Transformation lineage and version (where relevant).

   Provenance and trust information MUST remain available across all lifecycle stages:
   `retrieval` -> `chunking` -> `context construction` -> `model invocation` -> `output validation` -> `tool authorization / downstream decision`.

   A derived or sanitized representation MUST NOT silently lose or upgrade its source trust classification.
6. **Output Validation & Abstention**: Model outputs MUST undergo strict structural validation before tool invocation or downstream handling. If model output requests unauthorized tools, system file access, or secret exfiltration, the workflow MUST fail closed (`ABSTAINED` / `FAILED_SECURITY`).
7. **Current Availability Status**:
   ```yaml
   CONTRACT-RAG-001: ABSENT / NOT CURRENTLY AVAILABLE
   RAG_UNTRUSTED_CONTENT_SECURITY_READY: NO
   ```

---

## 11. Browser / API Security Policy

Security defines browser headers, API session rules, cookie classifications, and correlation classifications.

### Auth Cookie Classifications & Posture

Auth session and handle cookies are distinguished by role and custody rules. Universal `HttpOnly` requirement across all Auth cookies is incorrect and MUST NOT be required where doing so contradicts accepted provider/browser architecture (`CONTRACT-AUTH-001`). Note: Host-only and Path are independent concepts (host-only = no `Domain` attribute).

1. **`PROVIDER_SESSION_COOKIE`**:
   - Provider-managed session material (e.g. `@supabase/ssr` cookies named `sb-<project_ref>-auth-token`).
   - Browser-readable where required by accepted provider/browser architecture (`NOT` required to be `HttpOnly`).
   - Enforces `SameSite=Lax`.
   - Enforces `Secure` in every non-local environment, with `http://localhost:3000` as the single authorized exception.
   - Host-only cookie (no `Domain` attribute).
   - `Path=/` (or as required by owning Auth contract).
   - Provider-managed rotation and lifetime; no custom duplicate token store.
   - MUST NOT be accepted as an API credential by FastAPI (Bearer-only API authorization).
2. **`AUTH_CONTEXT_HANDLE` (`OPAQUE_AUTH_CONTEXT_HANDLE`)**:
   - Internal Auth context fence identifier.
   - Opaque (>=128-bit CSPRNG).
   - `HttpOnly`.
   - `Secure` in every non-local environment (outside exact `http://localhost:3000` exception).
   - `SameSite=Lax`.
   - Host-only cookie (no `Domain` attribute).
   - `Path=/`.
   - Browser-session scoped.
   - Free of identity, authorization, generation, access token, or credential material. Never exposed to browser JS, analytics, logs, or tracing.
3. **`AUTH_SESSION_BINDING_HANDLE` (`OPAQUE_AUTH_SESSION_BINDING_HANDLE`)**:
   - Opaque session binding handle for cross-context synchronization fences.
   - Opaque (>=128-bit CSPRNG).
   - `HttpOnly`.
   - `Secure` in every non-local environment (outside exact `http://localhost:3000` exception).
   - `SameSite=Lax`.
   - Host-only cookie (no `Domain` attribute).
   - `Path=/`.
   - Lifetime <= Auth context; new handle issued for each successful session establishment.
   - Free of access/refresh tokens, provider session bytes, authorization code, PKCE verifier, intended return path, identity claim, or authorization capability. Never exposed to browser JS, analytics, logs, or tracing.
4. **`AUTH_CALLBACK_CORRELATION_HANDLE`**:
   - Auth-owned opaque correlation handle cookie for OAuth callback synchronization.
   - Server-only / server-validated handle (`HttpOnly`).
   - Enforces `SameSite=Lax`.
   - Enforces `Secure` in every non-local environment (outside exact `http://localhost:3000` exception).
   - Host-only cookie (no `Domain` attribute).
   - Callback-path restricted: `Path=/auth/callback`. MUST NOT use `Path=/` for this handle.
   - Opaque (>=128-bit CSPRNG).
   - Free of authorization code, access tokens, refresh tokens, PKCE verifier, provider session, intended return path, provider payload, or credentials.
5. **`LOCAL_SIGN_OUT_TOMBSTONE`**:
   - Deny-only local marker indicating an intentional sign-out for immediate client-side fencing prior to server synchronization.
   - Browser-readable (**NOT** `HttpOnly`).
   - Enforces `SameSite=Lax`.
   - Enforces `Secure` in every non-local environment (outside exact `http://localhost:3000` exception).
   - Host-only cookie (no `Domain` attribute).
   - `Path=/`.
   - Browser-session scoped.
   - MUST NOT contain identity, authorization, generation, access token, or credential material. Cannot grant authentication; absence alone proves nothing; stale callbacks cannot clear it; provider events cannot clear it.

### Content Security Policy & Browser Hardening

1. **Content Security Policy (CSP)**: Production web surfaces MUST enforce a strict CSP prohibiting `unsafe-inline`, `unsafe-eval`, and unauthorized external script sources (preserving HF-008 prerequisite).
2. **XSS / Rendering Security**: All user-supplied content, repository text, and execution outputs rendered in the UI MUST be context-encoded to prevent Cross-Site Scripting (XSS).
3. **Header Classification**:
   - `X-Request-ID`: Classified as `TRACE_ONLY / SECURITY_RELEVANT_METADATA`.
   - `X-Correlation-ID`: Classified as `TRACE_ONLY / SECURITY_RELEVANT_METADATA`.
   - These headers MUST NEVER be treated as user identity, tenant identity, repository identity, semantic request identity, authorization, authentication, or capability.
4. **Readiness Probe Anti-Amplification**: Dependency-backed readiness endpoints (`/readyz`) MUST incorporate rate limits and anti-amplification controls to prevent denial-of-service against backend databases or Auth providers.
5. **Auth Current State**:
   ```yaml
   CROSS_ENTRYPOINT_CORRELATION: FIXED
   AUTH_RUNTIME_SAFETY_CLASS: LOCAL_NON_PRODUCTION_ONLY
   PRODUCTION_MULTI_INSTANCE_AUTH_READY: NO
   ```

---

## 12. Disclosure / Retention / Deletion

Security governs data retention policy, redaction rules, least disclosure rules, and security acceptance of retention ceilings. Retention/deletion ownership boundaries are explicitly partitioned:
- **A2-SECURITY**: Owns retention and deletion Security POLICY.
- **A2-EVIDENCE**: Owns Evidence deletion and tombstone SEMANTIC STATES.
- **A2-DEPLOYMENT**: Executes physical byte deletion on storage infrastructure.
- **A2-DATABASE**: Owns physical metadata persistence and tombstone implementation.

1. **Least Disclosure & Retention**: Systems MUST retain only the minimum data required for security auditing and operational execution.
2. **Policy-Bound Retention**: Logs, model context, execution traces, Queue metadata, and Evidence records MUST be assigned explicit retention ceilings under Security policy.
3. **Deletion Authorization**: Permanent deletion or purging of Evidence/artefacts requires authorized Security policy approval.
4. **Tombstone Semantics**: When Evidence or logs are deleted, a bounded audit tombstone MAY remain to record historical execution existence (under A2-EVIDENCE semantic states and A2-DATABASE physical persistence). Tombstone state MUST NOT be confused with proof that all historical physical copies were erased unless the underlying storage provider guarantees cryptographic erasure.
5. **Secret Revocation / Rotation**: In the event of secret exposure in logs or persistence, immediate secret revocation and credential rotation MUST be triggered.

---

## 13. Release Gates and Security Status

Security defines explicit status semantics for release evaluation:
- `PASS`: Requirement verified complete by empirical evidence and accepted by Security.
- `FAIL`: Requirement evaluated and failed security constraints.
- `NOT_TESTED`: Requirement specified but lacks empirical verification.
- `NOT_IMPLEMENTED`: Requirement specified but runtime implementation is absent.
- `BLOCKED`: Requirement cannot proceed due to unresolved dependencies or risk findings.
- `PASS_WITH_ACCEPTED_RISK`: Requirement conditionally accepted under explicit risk sign-off.

### Mandatory Release Gate Values

The initial Security state for TestGap-Miner is normatively recorded as follows:

```yaml
SECURE_SANDBOX_COMPLETE: NO
RESOURCE_ISOLATION_COMPLETE: NO
PRODUCTION_MULTI_INSTANCE_AUTH_READY: NO
PRODUCTION_QUEUE_DURABILITY_READY: NO
RAG_UNTRUSTED_CONTENT_SECURITY_READY: NO
EVIDENCE_AUTHENTICITY_READY: NO
SUPPLY_CHAIN_SECURITY_READY: NO
FULL_SECURITY_ACCEPTANCE: NO
PRODUCTION_READY: NO
```

This contract MUST forbid any unsupported claims of completion or production readiness.

---

## Cross-Component Ownership

Security respects component boundaries and does NOT seize implementation or domain semantic ownership from runtime component managers. Security policy may constrain these components but MUST NOT seize their semantic or implementation ownership:

- **A2-SECURITY**: Security policy, Security data classifications, cryptographic algorithm policy, Security cryptographic canonicalization policy, MAC/signature/key-custody requirements, redaction policy, retention/deletion Security policy, Security event policy, final Security acceptance. Security does NOT generically own all domain canonicalization.
- **A2-EXECUTION**: Worker runtime, runner sandbox implementation, process execution, Execution-result/domain serialization, and implementation behavior.
- **A2-QUEUE**: Queue transport implementation, message delivery engine, Queue-envelope/domain serialization, and Queue canonicalization semantics within Security constraints.
- **A2-AUTH**: Auth adapter implementation, session management, OAuth integration, and identity/authorization semantics.
- **A2-EVIDENCE**: Evidence structure, artefact manifest, provenance linking, canonical Evidence content/equality, Evidence logical digest field semantics, Evidence availability/integrity states, and Evidence deletion/tombstone semantic states.
- **A2-DEPLOYMENT**: Infrastructure provisioning, CI/CD pipelines, cloud storage buckets, secret injection, physical storage execution, and physical byte deletion.
- **A2-RAG**: Future RAG indexing and retrieval implementation.
- **A2-BACKEND**: FastAPI routes, HTTP error handling, control plane implementation.
- **A2-DATABASE**: Physical SQL schema, ORM models, migrations, persistence transactions, and physical metadata persistence/tombstone implementation.
- **A2-AGENT-WORKFLOW**: Run lifecycle state machine, repair allowance enforcement.
- **A2-UI**: Browser/UI implementation and visual presentation.
- **A2-INTEGRATION**: Independent integration acceptance.

---

## SEC001 Cross-Component Remediation Requests

The remediation requests `SEC001-XC-001` through `SEC001-XC-012` remain cross-component requests to foreign component managers. This Security contract states the normative security requirements those components MUST satisfy, but does NOT modify foreign application source code or foreign component contracts:

- `SEC001-XC-001`:
  - **OWNER**: `A2-EXECUTION / A2-DEPLOYMENT`
  - **SUBJECT**: `secure sandbox, executable/path confinement and resource isolation`
- `SEC001-XC-002`:
  - **OWNER**: `A2-EXECUTION / A2-EVIDENCE`
  - **SUBJECT**: `stdout/stderr secret redaction before Evidence persistence/display`
- `SEC001-XC-003`:
  - **OWNER**: `A2-QUEUE`
  - **SUBJECT**: `sticky SECURITY_REJECTION and protected effect/result/ack denial`
- `SEC001-XC-004`:
  - **OWNER**: `A2-QUEUE / A2-AUTH`
  - **SUBJECT**: `trusted current authorization provenance for administrative redrive (binding actor, REDRIVE action, source message/resource identity, decision reference, scope, policy version, freshness, and current authorization validation; stored references or booleans alone grant no authority)`
- `SEC001-XC-005`:
  - **OWNER**: `A2-DATABASE / A2-AGENT-WORKFLOW`
  - **SUBJECT**: `same-run causation constraint`
- `SEC001-XC-006`:
  - **OWNER**: `A2-DATABASE / A2-AGENT-WORKFLOW`
  - **SUBJECT**: `complete durable Workflow immutability semantics`
- `SEC001-XC-007`:
  - **OWNER**: `A2-BACKEND / A2-DEPLOYMENT`
  - **SUBJECT**: `readiness endpoint anti-amplification`
- `SEC001-XC-008`:
  - **OWNER**: `A2-UI / A2-DEPLOYMENT / A2-AUTH`
  - **SUBJECT**: `CSP/browser/XSS hardening`
- `SEC001-XC-009`:
  - **OWNER**: `A2-EVIDENCE / A2-SECURITY`
  - **SUBJECT**: `trusted Evidence persistence and Security-approved authenticity policy`
- `SEC001-XC-010`:
  - **OWNER**: `A2-DEPLOYMENT`
  - **SUBJECT**: `supply-chain provenance/scanning gates`
- `SEC001-XC-011`:
  - **OWNER**: `A2-AUTH / A2-INTEGRATION / A2-DEPLOYMENT`
  - **SUBJECT**: `production shared Auth correlation/synchronization and independent real-browser/network acceptance`
- `SEC001-XC-012`:
  - **OWNER**: `A2-RAG / A2-AGENT-WORKFLOW`
  - **SUBJECT**: `RAG/untrusted-content Security prerequisites`

---

## SEC-002 Blocked Status Preservation

SEC-002 (Prompt and Untrusted Content Security) remains **BLOCKED**.

Preserved blocking factors:
- `CONTRACT-RAG-001` is ABSENT / NOT CURRENTLY AVAILABLE.
- RAG runtime is ABSENT.
- Repository, issue, and PR ingestion pipeline is ABSENT.
- Indexing, retrieval, and localization runtime is ABSENT.
- Provenance and trust-label implementation is ABSENT.
- Prompt injection defense implementation is ABSENT.
- Model and tool authorization runtime is ABSENT.

---

## No Provider Selection

No provider selections are made by this draft:
- Security Provider: `UNSELECTED`
- Queue Provider: `UNSELECTED`
- Auth Correlation Provider: `UNSELECTED`
- KMS Provider: `UNSELECTED`
- Model Provider: `UNSELECTED`
- Object Storage Provider: `UNSELECTED`
- SIEM / Security Log Provider: `UNSELECTED`

Provider selection requires separate authorization.
