# Agent 1 Project Decomposition and Prompt Index

## Project summary

TestGap Miner is a Java/JUnit regression-test generation system whose value comes from an execution-backed loop: intake bug context, localise relevant files, generate a test-only patch, execute on buggy and fixed revisions, perform at most one repair, package evidence, and preserve human review. The benchmark core is Defects4J; GitHub App integration provides the product workflow.

## Current-state assessment

No repository snapshot or verified implementation handoff was supplied with the source documentation. Therefore, every component starts as **UNVERIFIED**. Each Agent 2 prompt requires repository inspection before implementation and forbids assuming that a documented feature already exists.

## Specification resolutions

- The PRD and winning-project brief are authoritative over generic reports.
- Generic document RAG becomes repository-code localisation.
- Generic multi-tenant database design is reduced to user/GitHub-installation/repository scoping; enterprise tenancy and billing remain post-MVP.
- Generic Deep Research evaluation metrics are adapted to execution-backed code metrics.
- LangGraph-style explicit orchestration is selected over an open-ended agent swarm.
- FastAPI + PostgreSQL + Alembic is the backend persistence baseline.
- The deployment target is Vercel + minimal AWS managed services, with local Docker Compose for development.

## Agent 2 prompt index

| Agent 2 ID | Specialist | Paired Agent 3 | Execution class | Prompt file |
|---|---|---|---|---|
| A2-DATABASE | Database Component Manager | A3-DATABASE | SEQUENTIAL FOUNDATION, then PARALLEL_WITH_CONSTRAINTS | `A2_DATABASE_MANAGER.md` |
| A2-AUTH | Authentication and Authorization Component Manager | A3-AUTH | PARALLEL_WITH_CONSTRAINTS after DB identity draft | `A2_AUTH_MANAGER.md` |
| A2-BACKEND | Backend API Component Manager | A3-BACKEND | PARALLEL_WITH_CONSTRAINTS after DB/API contract draft | `A2_BACKEND_MANAGER.md` |
| A2-RAG | Repository Retrieval and Localisation Manager | A3-RAG | PARALLEL_WITH_CONSTRAINTS after context contract draft | `A2_RAG_MANAGER.md` |
| A2-AGENT-WORKFLOW | Agentic Workflow Component Manager | A3-AGENT-WORKFLOW | SEQUENTIAL CORE with parallel scaffolding after contracts | `A2_AGENT_WORKFLOW_MANAGER.md` |
| A2-UI | Frontend and UI Component Manager | A3-UI | PARALLEL_WITH_CONSTRAINTS after API/auth contracts freeze | `A2_UI_MANAGER.md` |
| A2-SECURITY | Security Component Manager | A3-SECURITY | PARALLEL_WITH_CONSTRAINTS plus FINAL SECURITY GATE | `A2_SECURITY_MANAGER.md` |
| A2-EVALUATION | Evaluation and Testing Component Manager | A3-EVALUATION | PARALLEL_WITH_CONSTRAINTS; FINAL QUALITY GATE after workflow | `A2_EVALUATION_MANAGER.md` |
| A2-DEPLOYMENT | Deployment and Platform Component Manager | A3-DEPLOYMENT | PARALLEL_WITH_CONSTRAINTS; deployment after integration candidates | `A2_DEPLOYMENT_MANAGER.md` |
| A2-INTEGRATION | Final Integration and Release Manager | A3-INTEGRATION | FINAL_INTEGRATION_ONLY with early contract coordination | `A2_INTEGRATION_MANAGER.md` |

## Dependency graph

```text
A2-DATABASE ───────┬────────> A2-AUTH ─────────┐
                   ├────────> A2-BACKEND ──────┼──────────────┐
                   ├────────> A2-RAG ──────────┤              │
                   └────────> A2-EVALUATION ───┤              │
                                               v              │
A2-DEPLOYMENT (scaffold early) ───────> A2-AGENT-WORKFLOW <───┘
          │                                      │
          ├──────────────────────────────────────┼──> A2-UI
          │                                      ├──> A2-EVALUATION full runs
          │                                      └──> A2-SECURITY validation
          └─────────────────────────────────────────> A2-SECURITY platform checks

All integration-ready handoffs ─────────────────────> A2-INTEGRATION
A2-SECURITY + A2-EVALUATION + A2-DEPLOYMENT gates ──> A2-INTEGRATION release decision
```

## Parallelization plan

1. Database contract begins first.
2. Auth, Backend, RAG, Deployment scaffolding, Evaluation dataset work, and Security threat modelling may proceed in separate worktrees once their required contract drafts are available.
3. Agent Workflow starts with its state/queue/evidence contracts, then consumes Database, RAG, Auth, Backend, and Deployment interfaces.
4. UI starts after Auth/API/Evidence contracts freeze; it may use fixtures while backend implementation continues.
5. Security and Evaluation run continuously but perform final gates only on the integrated release candidate.
6. Integration is final-integration-only, except for early maintenance of the contract registry and merge plan.

## Recommended merge order

1. Database migrations and domain contracts.
2. Auth identity/GitHub-App contracts.
3. Backend control-plane/API contract.
4. RAG/localisation contract and deterministic baseline.
5. Agent Workflow core and sandbox interfaces.
6. Evaluation harness and metrics.
7. UI against frozen contracts.
8. Deployment/container/CI infrastructure.
9. Security remediations approved by component owners.
10. Final Integration release branch, E2E fixes, gates, and tag.

## Shared coordination rule

No specialist may solve a dependency by editing another specialist's protected files. Use dependency requests and contract versioning. Final Integration may coordinate owner-approved fixes, but it may not waive mandatory security, evaluation, migration, or human-control gates.
