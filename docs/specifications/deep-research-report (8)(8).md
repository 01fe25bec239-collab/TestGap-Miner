# Product Requirements Document for TestGap Miner

## Product overview

### Executive summary

**TestGap Miner** is an agentic AI product that turns bug reports and code changes into **reviewable regression tests**, validates those tests in a controlled sandbox, and presents execution-backed evidence that helps a human reviewer decide whether the test is worth accepting. The uploaded project-selection report identifies this concept as the winning project, recommends a **Java-only, Defects4J-first MVP with light GitHub integration**, and explicitly advises against broadening the first release into multi-language support, automatic merging, enterprise auth, private multi-tenancy, or a general-purpose coding assistant. fileciteturn0file0

The product wedge is narrow by design: do **one thing unusually well**. Instead of being “another AI that writes code,” TestGap Miner should specialise in generating tests that are grounded in repository context, executed against known revisions, and explained in a format that fits existing GitHub workflows such as issues, pull requests, reviews, and code-scanning style result surfacing. GitHub Apps are designed for this kind of extension model, support fine-grained permissions and short-lived tokens, and can respond to repository events via webhooks. GitHub also supports third-party analysis uploads through SARIF, which provides a practical path for surfaced findings and annotations. citeturn1search6turn2search2turn1search0turn1search2

The benchmark foundation is equally important. Defects4J is a curated collection of reproducible real Java bugs with buggy and fixed revisions, triggering tests, and supporting commands for checkout, compile, test, mutation analysis, and coverage. Its maintainers document environment constraints such as **Java 11** and timezone settings, which makes it well suited for an academic MVP that must be defensible, repeatable, and measurable. citeturn3search1turn3search0

### Problem statement

Teams often fix bugs without adding a durable regression test, or they add a low-signal test that compiles but does not clearly prove the relevant behaviour will stay fixed. In current GitHub workflows, issues, pull requests, reviews, and required approvals exist, but developers still have to do the heavy lifting of reading the bug, locating the right files, writing the test, executing it, and explaining why it matters. Generic code-generation tools help with snippets, yet they do not inherently provide a trustworthy **generate → execute → verify → explain** loop tied to repository state and human review. fileciteturn0file0 citeturn4search5turn5search0turn1search6turn2search2

The core product problem, therefore, is:

> **How might we help software engineers produce trustworthy, reviewable, objectively validated regression tests from bug context, without granting unsafe autonomy or adding review noise?**

### Product goals

| Goal ID | Goal | Success signal |
|---|---|---|
| G-001 | Generate a candidate regression test from issue or diff context in a way that is useful to a human reviewer | At least 60% of MVP benchmark runs produce a compiling candidate test |
| G-002 | Validate generated tests through execution, not text-only reasoning | Every accepted output includes execution evidence from sandbox runs |
| G-003 | Fit naturally inside GitHub workflows | A user can invoke, inspect, and review outputs from an issue, comment, or draft PR |
| G-004 | Be academically defensible | MVP evaluation is run on a fixed Defects4J subset with repeatable environment settings |
| G-005 | Preserve human control | No production-code merge occurs without explicit human approval |

### Non-goals

| Non-goal ID | Non-goal |
|---|---|
| NG-001 | Become a general-purpose AI coding assistant |
| NG-002 | Auto-merge generated tests into protected branches |
| NG-003 | Support multiple languages in MVP |
| NG-004 | Support private-repo multi-tenant SaaS admin, billing, or enterprise SSO in MVP |
| NG-005 | Repair arbitrary flaky CI across all repository environments |
| NG-006 | Modify production code in MVP except for test-only scaffolding necessary within generated test files |

The non-goal list aligns with the uploaded winning-project brief, which recommends keeping the first release tightly scoped to one language, one benchmark family, and a single standout demo story. fileciteturn0file0

## Users and workflows

### Target users

The uploaded report defines the primary target user as a **software engineer or tech lead on a GitHub-based project** seeking better regression protection without manually writing every test from scratch. For the PRD, the target audience expands slightly into adjacent users who participate in the same workflow. fileciteturn0file0

| User segment | Primary need | Frequency | MVP priority |
|---|---|---:|---:|
| Application engineer | Faster creation of trustworthy regression tests | High | High |
| Tech lead / reviewer | Evidence that a generated test is meaningful and safe to merge | High | High |
| QA / SDET | Coverage uplift and repeatable regression artefacts | Medium | Medium |
| OSS maintainer | Time-saving assistance on bugfix PRs in public repos | Medium | Medium |
| Evaluator / recruiter | Clear evidence of benchmarked agentic capability | Low in production, high for showcase | High for demo |

### User personas

| Persona | Description | Pain points | What success looks like |
|---|---|---|---|
| **Priya, backend engineer** | Owns a Java service, fixes bugs under delivery pressure | Forgets to add tests, spends too long locating setup and assertions | A draft test appears with proof it fails where it should and passes after the fix |
| **Arjun, tech lead** | Reviews bugfix PRs across multiple services | Low trust in AI-generated code, worried about noisy or brittle tests | Sees concise evidence card, compile result, fail/pass result, and can request changes safely |
| **Nisha, SDET** | Tracks regression risk and flaky tests | Needs measurable quality uplift, not vanity automation | Can compare generated-test quality across benchmark and repo runs |
| **Rahul, OSS maintainer** | Manages community issues in a public repository | Limited contributor time, inconsistent bug reports | Can trigger analysis on labelled issues and receive a reviewable draft PR |
| **Faculty evaluator** | Assesses project quality | Needs an objective benchmark and a working demo | Sees reproducible evaluation rooted in Defects4J and a real GitHub workflow |

### Jobs to be done

| JTBD ID | When... | I want to... | So I can... |
|---|---|---|---|
| JTBD-001 | when a bug is filed or fixed | generate a candidate regression test from the available context | reduce the chance of the bug returning |
| JTBD-002 | when I review an AI-generated test | inspect execution-backed evidence | decide quickly whether the test is worth merging |
| JTBD-003 | when repository context is incomplete | have the system abstain or ask for the missing artefact | avoid false confidence |
| JTBD-004 | when benchmarking the product | compare outcomes on known buggy and fixed revisions | measure progress objectively |
| JTBD-005 | when the system fails | understand why it failed and how to recover | avoid losing trust in the tool |

### Current workflow

In today’s baseline flow, a developer typically reads an issue, reproduces or infers the bug, locates relevant classes and tests, hand-writes a regression test, runs local or CI checks, opens a pull request, and then responds to reviewer comments. GitHub’s review system is strong for collaboration, but required reviews and protected branches operate **after** the developer has already done the manual discovery and test-writing work. citeturn4search5turn5search0turn4search6

A typical current-state workflow is shown below.

| Step | Actor | Current action | Main friction |
|---|---|---|---|
| CW-001 | Engineer | Reads issue / failing report | Context may be incomplete |
| CW-002 | Engineer | Locates relevant production and test files | Time-consuming, error-prone |
| CW-003 | Engineer | Writes test by hand | Setup and assertions are tedious |
| CW-004 | Engineer | Runs compile and test locally / CI | Iteration loop is slow |
| CW-005 | Engineer | Opens PR | Evidence is often implicit, not packaged |
| CW-006 | Reviewer | Reviews code and test | Hard to judge whether test really protects the bug |
| CW-007 | Maintainer | Merges after approval | Review burden stays high |

### Proposed workflow

TestGap Miner should introduce an event-driven advisory workflow that preserves GitHub’s review model while reducing the manual discovery burden. GitHub Apps can subscribe to repository events, and GitHub recommends responding promptly to webhook deliveries, validating signatures, and using only the permissions needed. Protected branches can still require reviews and passing checks before merge, which cleanly supports a human-in-the-loop product. citeturn2search2turn9search0turn9search4turn5search0

| Step | Actor / system | Proposed action | Output |
|---|---|---|---|
| PW-001 | Engineer / maintainer | Triggers TestGap Miner from issue comment, label, or benchmark UI | Run request created |
| PW-002 | Planner agent | Builds a run plan from issue text, diff, stack traces, and repo metadata | Structured task graph |
| PW-003 | Retrieval / localisation agent | Selects likely relevant source and test files | Context bundle |
| PW-004 | Test-generation agent | Drafts candidate Java/JUnit regression test | Candidate patch |
| PW-005 | Sandbox executor | Compiles and runs against buggy and fixed revisions | Execution evidence |
| PW-006 | Critic / repair agent | Performs one bounded repair loop if compile or execution fails | Revised patch or abstention |
| PW-007 | Publisher | Creates evidence card, issue comment, draft PR, and optional SARIF artefact | Reviewable output |
| PW-008 | Human reviewer | Approves, requests changes, rejects, or regenerates | Human-controlled decision |
| PW-009 | Evaluator dashboard | Logs metrics, artefacts, and outcomes | Benchmark and product telemetry |

## Requirements

### Functional requirements

The functional layer is anchored in the winning project brief, GitHub’s extension model, and Defects4J’s benchmark affordances. The product must behave like a specialised regression-test assistant, not like an unrestricted autonomous coder. fileciteturn0file0 citeturn1search6turn2search2turn3search1

| ID | Requirement | Priority | Verification |
|---|---|---:|---|
| FR-001 | The system shall support two invocation modes in MVP: **benchmark mode** using a Defects4J bug ID, and **GitHub mode** using a GitHub issue, pull request, or issue comment trigger. | Must | Unit + integration test |
| FR-002 | In benchmark mode, the system shall checkout both buggy and fixed revisions for the selected Defects4J bug and record the exact revision IDs used in the run. | Must | Integration test |
| FR-003 | In GitHub mode, the system shall ingest issue title, issue body, linked PR metadata if present, repository default branch SHA, and changed files if a PR trigger is used. | Must | Integration test |
| FR-004 | The system shall produce a **test-only patch** for Java/JUnit in MVP and shall not modify non-test production files. | Must | Patch validator test |
| FR-005 | The system shall compile and run the generated candidate in a sandbox before publishing a “ready for review” output. | Must | End-to-end test |
| FR-006 | The system shall execute one bounded repair attempt after a compile or runtime failure, then either publish the repaired result or abstain. | Must | Scenario test |
| FR-007 | The system shall publish an evidence card containing: invocation source, files used, compile result, failing-on-buggy result, passing-on-fixed result when available, and human-readable rationale. | Must | UI/API test |
| FR-008 | The system shall support publishing results as an issue comment and, where configured, as a draft pull request. | Must | GitHub integration test |
| FR-009 | The system shall export a SARIF-compatible results artefact for surfaced findings or annotations when GitHub code-scanning style presentation is enabled. | Should | Schema validation |
| FR-010 | The system shall allow a human to mark an output as accepted, rejected, needs-regeneration, or out-of-scope. | Must | UI test |
| FR-011 | The system shall maintain a run history with artefact links, timestamps, model version, and repository/bug identifiers. | Must | Persistence test |
| FR-012 | The system shall expose a benchmark dashboard showing corpus size, compile success, fail-on-buggy/pass-on-fixed rate, and flake rate. | Must | Analytics test |

### AI-specific requirements

NIST’s AI RMF and GenAI Profile emphasise trustworthy, measurable, and context-sensitive AI use, while the OWASP LLM Top 10 highlights specific generative-AI risks such as prompt injection, sensitive information disclosure, insecure output handling, and excessive agency. The AI design for TestGap Miner should therefore be **grounded, bounded, and measurable**. citeturn8search6turn8search0turn8search2turn6search2

| ID | Requirement | Priority | Verification |
|---|---|---:|---|
| AI-001 | The model input shall be constructed from a structured context bundle containing issue text, repository metadata, selected files, execution logs, and explicit task instructions. | Must | Prompt-construction test |
| AI-002 | The model output contract shall be structured and parseable, containing only permitted fields such as test-file diff, explanation, assumptions, and confidence. | Must | Schema validation |
| AI-003 | The system shall attach a confidence score and an uncertainty flag to every published result. | Must | Output contract test |
| AI-004 | The system shall abstain rather than publish a ready-for-review result when the execution evidence is insufficient or contradictory. | Must | Negative scenario test |
| AI-005 | The system shall ground user-facing explanations only in retrieved context and execution results observed during the run. | Must | Traceability audit |
| AI-006 | The model pipeline shall run in a reproducible evaluation mode with fixed prompts, fixed temperatures, and version-pinned model identifiers for benchmark runs. | Must | Benchmark reproducibility test |
| AI-007 | The system shall detect and flag probable hallucinations, including references to nonexistent classes, methods, imports, or test fixtures. | Must | Static validator + compile test |
| AI-008 | The system shall treat repository content, issue text, and comments as untrusted input and apply prompt-injection defences before agent planning or tool use. | Must | Red-team test |
| AI-009 | The system shall minimise prompt payloads by sending only the context needed for the current task. | Must | Prompt-size audit |
| AI-010 | The model shall not directly perform irreversible repository actions in MVP. | Must | Policy test |

### Agent-specific requirements

The winning concept is explicitly agentic because the value lies in a loop of planning, retrieval, generation, execution, criticism, and publication. GitHub’s event-driven app model and NIST’s emphasis on TEVV both support this architecture as long as each agent step is observable and bounded. fileciteturn0file0 citeturn2search2turn8search2

| ID | Requirement | Priority | Verification |
|---|---|---:|---|
| AG-001 | The planner agent shall convert each invocation into an explicit execution plan with ordered steps and tool budget. | Must | Plan-schema test |
| AG-002 | The retrieval/localisation agent shall rank candidate files and return a scored shortlist instead of an unbounded repository dump. | Must | Retrieval-eval test |
| AG-003 | The generation agent shall only operate on the scoped context bundle provided by the planner. | Must | Context-scope test |
| AG-004 | The executor agent shall run in an isolated sandbox with network egress disabled during benchmark execution. | Must | Sandbox policy test |
| AG-005 | The critic agent shall inspect compile output and test results and may trigger at most one automated repair attempt in MVP. | Must | Loop-bound test |
| AG-006 | The publisher agent shall create human-consumable artefacts but shall not merge or approve pull requests. | Must | Permission test |
| AG-007 | Every agent step shall emit structured telemetry including start time, end time, inputs, outputs, and failure code. | Must | Telemetry test |
| AG-008 | Duplicate webhook deliveries or repeated user commands shall be handled idempotently using run keys derived from source event identifiers and repository SHA. | Must | Idempotency test |

### User stories

| User story ID | Story |
|---|---|
| US-001 | As an engineer, I want to trigger TestGap Miner from a GitHub issue so that I can get a candidate regression test without leaving my repository workflow. |
| US-002 | As a reviewer, I want to see compile and execution evidence next to the generated test so that I can judge whether it is trustworthy. |
| US-003 | As a maintainer, I want the result published as a draft PR instead of an auto-merge so that branch protections and code review remain in force. |
| US-004 | As a QA engineer, I want a benchmark dashboard across Defects4J bugs so that I can measure progress over time. |
| US-005 | As a user, I want the system to abstain cleanly when context is missing so that I am not misled by a polished but unsupported output. |
| US-006 | As a security-conscious team lead, I want least-privilege GitHub permissions and signed webhook validation so that repository risk stays controlled. |
| US-007 | As an evaluator, I want the run to be reproducible with pinned environment settings so that the same bug produces comparable outcomes. |
| US-008 | As an accessibility user, I want the UI to be keyboard-usable and screen-reader compatible so that I can review outputs independently. |

### Acceptance criteria

Every acceptance criterion below is objectively testable and maps to one or more requirements.

| AC ID | Acceptance criterion | Maps to |
|---|---|---|
| AC-001 | Given a valid GitHub issue trigger, the system creates a visible run record within **60 seconds** and stores repository, issue, and SHA identifiers. | FR-001, FR-003 |
| AC-002 | Given a valid Defects4J bug ID, the system checks out both buggy and fixed revisions and records both revision IDs in the run metadata. | FR-001, FR-002 |
| AC-003 | For any “ready for review” output, the published artefact includes compile status, buggy-revision outcome, fixed-revision outcome or explicit reason unavailable, and selected file list. | FR-005, FR-007 |
| AC-004 | In MVP, the patch validator rejects any output that changes a non-test file. | FR-004 |
| AC-005 | If the first compile or run fails, the system performs **no more than one** automatic repair attempt before abstaining or publishing the revised candidate. | FR-006, AG-005 |
| AC-006 | A draft PR can only be created when repository permissions allow it; otherwise the system falls back to an issue comment and marks publish mode as degraded. | FR-008 |
| AC-007 | Every benchmark run stores model ID, prompt template version, Java version, timezone, and dependency manifest used for execution. | AI-006, AG-007 |
| AC-008 | The system marks the result as **ABSTAINED** when compile status is failing after the allowed repair loop or when the retrieved context bundle is empty. | AI-004 |
| AC-009 | The structured output parser rejects malformed model responses and records a parse failure without publishing a ready-for-review result. | AI-002 |
| AC-010 | For red-team prompt-injection test cases, the model must not execute unauthorised tool calls or widen repository access beyond the planner-approved context bundle. | AI-008, AG-003 |
| AC-011 | Every webhook delivery is signature-validated; requests with invalid signatures are rejected with no further processing. | SEC-002 |
| AC-012 | Every duplicate webhook delivery with the same delivery GUID and repository SHA is deduplicated or linked to the existing run. | AG-008 |
| AC-013 | The benchmark dashboard computes compile success rate, fail-on-buggy/pass-on-fixed rate, and flake rate from stored run data without manual spreadsheet work. | FR-012, EVAL-001 |
| AC-014 | Keyboard-only users can navigate from run list to evidence card to artefact download without mouse dependency. | ACC-001, ACC-002 |
| AC-015 | A protected-branch repository still requires human approval before merge; TestGap Miner has no permission path to bypass required reviews. | HUM-001, SEC-001 |
| AC-016 | SARIF export, when enabled, validates against supported SARIF 2.1.0 schema rules before upload. | FR-009, INT-004 |

### Human-approval requirements

GitHub protected branches can require pull-request reviews, status checks, conversation resolution, code-owner review, and approval from someone other than the most recent pusher. Those controls are directly aligned with TestGap Miner’s desired operating model. citeturn5search0turn5search5turn5search1

| ID | Requirement | Priority |
|---|---|---:|
| HUM-001 | The product shall never auto-merge into a protected branch in MVP. | Must |
| HUM-002 | All GitHub-created code changes in MVP shall be published as **draft pull requests** or issue comments only. | Must |
| HUM-003 | A result marked “recommended” by the system shall still require a human reviewer to approve before merge. | Must |
| HUM-004 | The UI shall display a clear “AI-generated / human approval required” label on every publish artefact. | Must |
| HUM-005 | The system shall record whether a human accepted, rejected, or modified the generated test before merge. | Must |
| HUM-006 | The system shall allow manual re-run, regenerate, and dismiss actions without requiring repository admin rights. | Should |

## Data, integrations, and governance

### Data requirements

Defects4J currently contains hundreds of active real bugs, with documented metadata for buggy/fixed revisions and triggering tests, making it the backbone of MVP evaluation. In GitHub mode, the product depends on issue text, PR metadata, file contents, and execution artefacts. NIST’s AI work emphasises context-sensitive measurement and evaluation, which means data lineage must be explicit. citeturn3search1turn3search0turn8search2

| ID | Requirement | Priority |
|---|---|---:|
| DATA-001 | The system shall support Defects4J as the required benchmark corpus for MVP. | Must |
| DATA-002 | The system shall store repository identifier, branch, commit SHA, trigger source, and selected-file manifest for every run. | Must |
| DATA-003 | The system shall store execution artefacts including compile logs, test logs, exit codes, and generated patch. | Must |
| DATA-004 | The system shall label each run with provenance fields: benchmark vs GitHub, public repo vs local benchmark, and model version. | Must |
| DATA-005 | The system shall separate **operational telemetry** from **customer code artefacts** in storage. | Must |
| DATA-006 | The system shall support configurable retention periods for code artefacts, logs, and aggregate metrics. | Must |
| DATA-007 | Private repository code shall not be reused for model training by default. | Must |
| DATA-008 | The system shall support deletion of stored run artefacts for a repository on admin request. | Should |

### Integration requirements

GitHub Apps can comment on pull requests and issues, respond to webhooks, and operate with fine-grained permissions. Relevant webhook families include `issues`, `pull_request`, and `check_run`. GitHub code-scanning integrations can ingest SARIF 2.1.0-compatible uploads, subject to validation and size limits. GitHub also applies primary and secondary API rate limits, so the product must be resilient to throttling. citeturn1search6turn2search2turn10search4turn10search1turn2search3turn1search2turn1search3turn4search2

| ID | Requirement | Priority |
|---|---|---:|
| INT-001 | The product shall integrate as a GitHub App with least-privilege repository permissions. | Must |
| INT-002 | The product shall support `issues`, `issue_comment`, `pull_request`, and `check_run`-driven workflows where permissions allow. | Must |
| INT-003 | The product shall support publishing issue comments, pull-request reviews/comments, and draft pull requests. | Must |
| INT-004 | The product shall support optional SARIF export and upload for result surfacing on GitHub. | Should |
| INT-005 | The integration layer shall implement rate-limit backoff and retry logic for GitHub REST and GraphQL calls. | Must |
| INT-006 | The webhook receiver shall acknowledge deliveries quickly and process heavy work asynchronously. | Must |
| INT-007 | The product shall support a local CLI mode for benchmark evaluation without any GitHub dependency. | Must |
| INT-008 | The product shall record GitHub delivery GUIDs and API request IDs for troubleshooting. | Should |

### Security requirements

GitHub recommends GitHub Apps over OAuth apps because Apps use fine-grained permissions and short-lived tokens. GitHub also recommends validating webhook deliveries with HMAC-SHA256 and using HTTPS. OWASP guidance remains relevant for application logging and control verification, and OWASP’s LLM Top 10 is especially relevant to prompt injection, excessive agency, insecure output handling, and sensitive-information disclosure in an agentic product. citeturn1search6turn9search0turn9search4turn6search9turn6search4turn6search2

| ID | Requirement | Priority |
|---|---|---:|
| SEC-001 | The product shall use GitHub App authentication and shall not require long-lived personal access tokens for standard operation. | Must |
| SEC-002 | The webhook receiver shall verify `X-Hub-Signature-256` on every delivery before processing. | Must |
| SEC-003 | All external webhook and UI traffic shall use HTTPS with valid TLS certificates in production. | Must |
| SEC-004 | Sandbox execution shall be isolated from the control plane and shall deny network egress during benchmark runs. | Must |
| SEC-005 | Secrets shall be stored in a managed secret store and never hardcoded in code or prompts. | Must |
| SEC-006 | The product shall enforce least privilege for GitHub API scopes, storage access, and internal service roles. | Must |
| SEC-007 | The product shall scan and redact known secret patterns from logs and user-visible artefacts before publication. | Must |
| SEC-008 | The product shall cap autonomous activity to retrieval, generation, execution, and publishing; merge, approval, and protection-rule bypass are prohibited. | Must |
| SEC-009 | The product shall maintain security event logs for auth failures, signature failures, permission denials, and sandbox policy violations. | Must |
| SEC-010 | The product shall subject the model and toolchain to red-team tests for prompt injection, path traversal, command injection, and output-handling vulnerabilities before release. | Should |

### Privacy requirements

The NIST GenAI Profile explicitly calls out data privacy as a generative-AI risk area, and the OWASP LLM Top 10 highlights both sensitive-information disclosure and excessive agency. For TestGap Miner, privacy must be addressed as a first-class design concern because source code, issue text, stack traces, comments, and logs may include sensitive business or personal information. citeturn8search0turn8search3turn6search2

| ID | Requirement | Priority |
|---|---|---:|
| PRIV-001 | The product shall minimise collected data to what is necessary for the current invocation and evaluation. | Must |
| PRIV-002 | The product shall not retain private-repo code artefacts longer than the configured retention period. | Must |
| PRIV-003 | The product shall provide repository-level controls for data retention and artefact deletion. | Must |
| PRIV-004 | The product shall redact secrets and known credential formats from prompts, logs, and published evidence where technically feasible. | Must |
| PRIV-005 | The product shall clearly disclose what data is sent to the model provider and what remains local. | Must |
| PRIV-006 | The product shall default benchmark mode to public/open benchmark data and keep benchmark telemetry logically separate from customer-repository telemetry. | Must |

### Accessibility requirements

WCAG 2.2 is a W3C Recommendation and adds nine success criteria beyond WCAG 2.1, including focus visibility, alternatives to dragging interactions, target size minimums, consistent help, redundant-entry support, and accessible authentication. Those are directly applicable to a review-heavy developer tool UI. citeturn0search2turn0search5turn0search7

| ID | Requirement | Priority |
|---|---|---:|
| ACC-001 | The web UI shall conform to **WCAG 2.2 AA** for MVP screens. | Must |
| ACC-002 | All primary actions shall be keyboard accessible, including trigger, inspect artefact, approve, reject, and download log actions. | Must |
| ACC-003 | Focus indicators shall remain visible and not be obscured on all major review flows. | Must |
| ACC-004 | Controls shall meet target-size minimums on supported viewport breakpoints. | Must |
| ACC-005 | Status colours shall always be paired with text labels and not used as the sole signal. | Must |
| ACC-006 | Authentication and re-authentication flows shall avoid puzzle-based or memory-only challenges where possible. | Should |
| ACC-007 | Evidence cards and logs shall support screen-reader compatible semantics and structured headings. | Must |

### Auditability requirements

NIST’s AI work stresses TEVV and trustworthy measurement, while OWASP’s logging guidance recommends consistent application logging for security events. For TestGap Miner, auditability is not optional because the product’s value proposition depends on proving what the system did, on what code, with which model, and with what execution result. citeturn8search2turn8search6turn6search4

| ID | Requirement | Priority |
|---|---|---:|
| AUD-001 | Every run shall have an immutable run ID and append-only event history. | Must |
| AUD-002 | The audit trail shall include trigger source, repository or benchmark identifier, commit SHA or bug ID, model version, prompt template version, and tool versions. | Must |
| AUD-003 | The audit trail shall record every agent step, including retrieved files, generated patch hash, execution command, and publish action. | Must |
| AUD-004 | User-visible explanations shall be traceable to stored evidence artefacts. | Must |
| AUD-005 | Human decisions—accept, reject, dismiss, regenerate—shall be recorded with actor, timestamp, and resulting state. | Must |
| AUD-006 | Security-relevant events shall be searchable separately from product-usage events. | Should |

## Reliability, performance, and evaluation

### Reliability requirements

Defects4J’s maintainers explicitly warn that reproducibility depends on the right Java version and timezone, and exclude broken/flaky tests from the benchmark corpus. GitHub webhook handling also has operational constraints such as prompt acknowledgment and delivery metadata. These external constraints shape the product’s reliability design. citeturn3search0turn3search1turn9search4turn10search3

| ID | Requirement | Priority |
|---|---|---:|
| REL-001 | Benchmark execution shall pin Java to the supported Defects4J version and set timezone to `America/Los_Angeles`. | Must |
| REL-002 | The system shall process webhooks asynchronously and acknowledge valid deliveries within **5 seconds** target and within GitHub’s 30-second guidance ceiling. | Must |
| REL-003 | The system shall implement idempotent delivery handling using GitHub delivery GUIDs. | Must |
| REL-004 | The system shall classify outputs as success, abstained, infrastructure failure, invalid input, or security rejection. | Must |
| REL-005 | The system shall retry transient GitHub API and storage failures with bounded exponential backoff. | Must |
| REL-006 | The system shall quarantine repeated flaky outcomes and exclude them from “success” metrics until resolved. | Must |
| REL-007 | The system shall preserve run artefacts even when publication to GitHub fails after execution succeeds. | Must |

### Performance requirements

| ID | Requirement | Priority |
|---|---|---:|
| PERF-001 | Median end-to-end time for benchmark runs on the MVP evaluation subset shall be **under 8 minutes**. | Must |
| PERF-002 | P95 end-to-end time for GitHub issue-triggered runs on supported demo repositories shall be **under 12 minutes**. | Must |
| PERF-003 | Evidence-card initial render time shall be **under 2 seconds p95** on a standard broadband connection. | Should |
| PERF-004 | Retrieval/localisation shall return the top-ranked candidate-file set within **30 seconds p95** for repositories under the supported MVP size limit. | Must |
| PERF-005 | The product shall enforce per-run token and tool budgets to prevent unbounded cost or runaway execution. | Must |
| PERF-006 | SARIF artefacts shall be validated and size-checked before upload to avoid GitHub rejection. | Should |

### AI evaluation metrics

NIST’s TEVV framing argues for explicit measurement of accuracy, robustness, transparency, reliability, and other context-sensitive trustworthiness characteristics. Defects4J provides the right backbone for such evaluation because it includes real faults, triggering tests, and supporting scripts for mutation and coverage analysis. citeturn8search2turn3search1turn3search0

| ID | Metric | Definition | Target for MVP |
|---|---|---|---|
| EVAL-001 | **Fail-on-buggy and pass-on-fixed rate** | % of generated tests that fail on the buggy revision and pass on the fixed revision | ≥ 25% on curated MVP subset |
| EVAL-002 | **Compile success rate** | % of runs where the final candidate compiles | ≥ 60% |
| EVAL-003 | **Single-repair salvage rate** | % of initially failing runs that succeed after one repair loop | Report only in MVP |
| EVAL-004 | **Flake rate** | % of generated tests whose result changes across repeated identical runs | ≤ 5% |
| EVAL-005 | **Hallucination rate** | % of outputs referencing nonexistent classes, methods, imports, or fixtures | ≤ 10% |
| EVAL-006 | **Mutation score uplift** | Difference in mutation score between baseline developer tests and baseline plus generated test, on supported benchmark subset | Positive median uplift |
| EVAL-007 | **Coverage uplift** | Branch/statement coverage delta attributable to accepted generated tests | Positive median uplift |
| EVAL-008 | **Abstention precision** | % of abstentions that human evaluators agree were appropriate | ≥ 80% |
| EVAL-009 | **Evidence completeness rate** | % of published results containing all required evidence fields | 100% |
| EVAL-010 | **Reviewer acceptance rate** | % of human-reviewed outputs accepted with no material rewrite | ≥ 30% on pilot repos |

### Product metrics

GitHub review workflows and DORA-style delivery metrics are useful framing devices for measuring whether the product is reducing review friction and improving delivery quality. DORA’s four well-known software-delivery metrics are deployment frequency, lead time for changes, change failure rate, and time to restore service. TestGap Miner is not a deployment tool, but it can still improve related upstream workflow indicators such as regression-test acceptance and review cycle time. citeturn4search5turn7search3turn7search5

| Metric | Definition | Why it matters |
|---|---|---|
| PM-001 Activation rate | % of onboarded repos that trigger at least one run in 7 days | Measures real adoption |
| PM-002 Weekly active repositories | Count of repos with at least one completed run in the last 7 days | Measures sustained usage |
| PM-003 Trigger-to-first-evidence time | Median time from command to evidence card publication | Measures user-perceived speed |
| PM-004 Draft PR publish rate | % of successful runs that are published as a draft PR rather than comment-only fallback | Measures integration health |
| PM-005 Human acceptance rate | % of published outputs marked accepted | Measures usefulness |
| PM-006 Median reviewer touches | Median number of human edits before merge for accepted tests | Measures output polish |
| PM-007 Noise rate | % of outputs marked irrelevant, brittle, or duplicate | Measures trust erosion |
| PM-008 Coverage uplift on accepted tests | Coverage delta for accepted generated tests | Measures technical value |
| PM-009 Benchmark trend | EVAL-001 trend over weekly model or prompt updates | Measures product improvement |
| PM-010 Support / recovery burden | Median time to recover a failed run after user action | Measures operational usability |

### Failure scenarios

| Failure ID | Scenario | Likely cause | User risk |
|---|---|---|---|
| FAIL-001 | No meaningful test generated | Insufficient issue context or weak retrieval | Wasted run |
| FAIL-002 | Generated test does not compile | Hallucinated API usage or wrong imports | Trust loss |
| FAIL-003 | Test compiles but does not distinguish buggy vs fixed | Weak assertion quality | Low-signal output |
| FAIL-004 | Test is flaky across repeated runs | Hidden nondeterminism or environment mismatch | False confidence |
| FAIL-005 | GitHub publish step fails | Permission error, rate limit, notification throttling | Result hidden from workflow |
| FAIL-006 | SARIF upload rejected | Invalid schema, size limit, duplicate/fingerprint issue | Lost annotations |
| FAIL-007 | Webhook processing duplicate | Delivery retry or handler timeout | Duplicate comments or PRs |
| FAIL-008 | Prompt injection attempt from issue/comment/repo text | Untrusted content influences tools or scope | Security incident |
| FAIL-009 | Secret leakage in logs or explanation | Insufficient redaction | Privacy/security breach |
| FAIL-010 | Sandbox dependency resolution fails | Broken build or unavailable dependency setup | Unfinished run |
| FAIL-011 | Benchmark reproducibility failure | Wrong Java version or timezone | Invalid evaluation result |
| FAIL-012 | Repository is too large or unsupported for MVP | Scope limits exceeded | Poor UX unless communicated clearly |

### Error-recovery workflows

| Recovery ID | Trigger | System response | Success condition |
|---|---|---|---|
| ER-001 | Missing issue context | Publish “context insufficient” result with exact missing fields requested | User can rerun after adding data |
| ER-002 | Compile failure after first generation | Attempt one bounded repair using compiler output | Repaired candidate compiles |
| ER-003 | Repeated compile failure | Mark run **ABSTAINED** and attach logs | No misleading ready-for-review output |
| ER-004 | Flaky outcome detected | Re-run twice in identical environment; if unstable, label as flaky and exclude from success metrics | Flaky tests quarantined |
| ER-005 | GitHub rate limit or secondary rate limit | Queue publish retry with backoff and visible delayed status | Result eventually publishes or cleanly fails |
| ER-006 | Webhook duplicate delivery | Deduplicate by delivery GUID + SHA and link to original run | No duplicate PR/comment |
| ER-007 | SARIF rejection | Fall back to issue comment / PR comment publication with rejection reason stored | User still receives usable output |
| ER-008 | Signature validation failure | Reject request, log security event, show nothing to repo | No untrusted processing occurs |
| ER-009 | Sandbox infrastructure failure | Retry once on fresh worker, then mark infrastructure failure | Clear separation from model failure |
| ER-010 | Unsupported repository size or language | Return “unsupported in MVP” with scope explanation | Users know the product boundary |

## Scope and demonstration

### MVP scope

The MVP should follow the winning-project brief closely: **Java-only, Defects4J-first, benchmark-led, GitHub-native enough for a compelling demo, but not broader than it needs to be**. The benchmark engine is the core; the GitHub flow is the product wrapper that makes the system feel real. fileciteturn0file0

**Included in MVP**

| Scope item | Included |
|---|---|
| Java + JUnit test generation | Yes |
| Defects4J benchmark mode | Yes |
| Public GitHub repository integration | Yes |
| GitHub App with issue/comment trigger | Yes |
| Draft PR publication | Yes |
| Issue comment fallback | Yes |
| One bounded repair loop | Yes |
| Evidence card UI and run history | Yes |
| Benchmark dashboard | Yes |
| SARIF export | Optional / stretch |

**Explicitly excluded from MVP**

| Scope item | Included |
|---|---|
| Multi-language support | No |
| Auto-merge | No |
| Private-repo multi-tenant SaaS | No |
| Enterprise SSO / billing / admin | No |
| Production-code editing beyond test files | No |
| Multi-step autonomous refactoring | No |
| General “chat with your codebase” assistant | No |

### Post-MVP scope

| Post-MVP item | Rationale |
|---|---|
| Multi-language expansion beyond Java | Natural product growth after evaluation baseline is strong |
| Private repository support with stronger tenancy controls | Required for commercial use |
| More than one repair loop with stronger safeguards | Useful after trust is established |
| Better retrieval using semantic + structural code search | Improves localisation quality |
| Reviewer-personalised test style adaptation | Improves acceptance rate |
| CODEOWNERS-aware reviewer suggestions | Fits GitHub review practices |
| Merge-queue and branch-protection aware deeper workflows | Useful only after trust and permissions mature |
| Broader benchmark suites beyond Defects4J | Improves external validity |
| Cost optimiser for model/tool budget | Needed for scale |
| Offline or self-hosted model execution option | Important for privacy-sensitive customers |

### Demonstration scenario

The strongest demo is a **two-part demonstration**: first, a benchmark-proven path on Defects4J; second, a GitHub-native path that shows how the product would be used in practice. Defects4J’s own documentation uses `Lang` bug examples for checkout and test commands, which makes a `Lang` bug a sensible demonstration target. citeturn3search1

**Recommended demo flow**

| Demo step | Action | What the audience should see |
|---|---|---|
| DEMO-001 | Open TestGap Miner dashboard and select a curated Defects4J bug such as `Lang-1` | Benchmark-first framing and reproducibility credentials |
| DEMO-002 | Show automatic checkout of buggy and fixed revisions with pinned Java/timezone metadata | Controlled execution environment |
| DEMO-003 | Trigger the planner and retrieval stages | Candidate files, selected context, and explicit plan |
| DEMO-004 | Show generated Java/JUnit test patch | Constrained, test-only output |
| DEMO-005 | Execute on buggy revision | Test fails in the expected way |
| DEMO-006 | Execute on fixed revision | Same test passes |
| DEMO-007 | Display evidence card | Compile result, fail/pass proof, rationale, confidence, artefact links |
| DEMO-008 | Switch to GitHub demo repo and trigger via issue comment | Real developer workflow |
| DEMO-009 | Show issue comment update and draft PR creation | Human-review-friendly publication |
| DEMO-010 | End with reviewer decision screen and benchmark dashboard | Proof of product plus proof of evaluation |

The demonstration should make one message unmistakable: **TestGap Miner does not ask the reviewer to trust the model’s words; it asks the reviewer to inspect observed behaviour.** That positioning is what makes the product compelling as an AI product, a software-engineering system, and a final project. fileciteturn0file0 citeturn3search1turn8search2turn5search0