"""DB-004 test factories for RAG and Evidence domain values.

`tests` is not an importable package, so these helpers live beside `support`
and build validated CONTRACT-RAG-001 / CONTRACT-EVIDENCE-001 domain objects
that the DB-004 persistence functions consume read-only.
"""

import hashlib
from datetime import UTC, datetime, timedelta

from app.evidence.artefact import (
    ArtefactId,
    ArtefactManifest,
    ArtefactManifestFinalizationState,
    ArtefactReference,
    ArtefactType,
)
from app.evidence.candidate import (
    CandidateFinalizationState,
    CandidatePatch,
    CandidatePatchId,
    CandidateVersion,
    ChangedFile,
    GenerationProvenance,
)
from app.evidence.execution import (
    CandidateVersionId,
    CompileResult,
    CompileStatus,
    ExecutionEvidence,
    ExecutionEvidenceId,
    ExecutionOutcome,
    ExecutionPhase,
    ExecutionTiming,
    IntegrityMetadata,
    OpaqueReference,
    ProducerResultId,
    RunId,
    TestCaseResult,
    TestCaseStatus,
    TestResult,
    TimeoutMetadata,
    WorkflowAttemptId,
)
from app.retrieval.localisation import (
    CandidateIdentity,
    ContextBundle,
    ContextBundleIdentity,
    ContextItem,
    ContextItemIdentity,
    FileIdentity,
    Provenance,
    RepositoryIdentity,
    RevisionIdentity,
    TokenBudget,
    TrustLabel,
)

REVISION_40 = "ab" * 20
CONTEXT_CONTENT = "class Example {\n    int answer = 42;\n}\n"
GENERATED_AT = datetime(2026, 8, 22, 12, 0, 0, tzinfo=UTC)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# RAG context values
# ---------------------------------------------------------------------------


def make_context_item(
    *,
    context_item_id: str = "context-item-1",
    candidate_id: str = "candidate-1",
    file_identity: str = "src/main/java/Example.java",
    start_line: int = 1,
    end_line: int = 3,
    content: str = CONTEXT_CONTENT,
    token_count: int = 12,
    repository_id: str = "benchmark-repo",
    revision_id: str = REVISION_40,
) -> ContextItem:
    return ContextItem(
        context_item_id=ContextItemIdentity(context_item_id),
        candidate_id=CandidateIdentity(candidate_id),
        provenance=Provenance(
            repository_id=RepositoryIdentity(repository_id),
            revision_id=RevisionIdentity(revision_id),
            file_identity=FileIdentity(file_identity),
            start_line=start_line,
            end_line=end_line,
            content_sha256=sha256_hex(content),
        ),
        trust_label=TrustLabel.UNTRUSTED_REPOSITORY_TEXT,
        content=content,
        token_count=token_count,
    )


def make_context_bundle(
    *, context_bundle_id: str = "context-bundle-1", items=None, max_tokens: int = 512
) -> ContextBundle:
    items = tuple(items) if items is not None else (make_context_item(),)
    consumed = sum(item.token_count for item in items)
    first = items[0]
    return ContextBundle(
        context_bundle_id=ContextBundleIdentity(context_bundle_id),
        repository_id=first.provenance.repository_id,
        revision_id=first.provenance.revision_id,
        items=items,
        token_budget=TokenBudget(max_tokens=max_tokens, consumed_tokens=consumed),
    )


# ---------------------------------------------------------------------------
# Candidate patch/version values
# ---------------------------------------------------------------------------


def _generation_provenance() -> GenerationProvenance:
    return GenerationProvenance(
        generator_reference=OpaqueReference("generator://test-generator-v1"),
        tool_version_reference=OpaqueReference("tool://javac-21.0.1"),
        generated_at=GENERATED_AT,
    )


def make_candidate_patch(
    run_id: str, attempt_id: str, **overrides
) -> CandidatePatch:
    values = dict(
        candidate_patch_id=CandidatePatchId("candidate-patch-1"),
        candidate_version_id=CandidateVersionId("candidate-version-1"),
        run_id=RunId(run_id),
        workflow_attempt_id=WorkflowAttemptId(attempt_id),
        source_repository=OpaqueReference("github://example/example-repo"),
        source_revision=OpaqueReference(REVISION_40),
        patch_digest=OpaqueReference("sha256:" + "cd" * 32),
        digest_algorithm=OpaqueReference("SHA-256"),
        test_only_scope=True,
        test_only_scope_reference=OpaqueReference("scope-ref://patch-1"),
        changed_files_manifest=(
            ChangedFile(path="src/test/java/ExampleTest.java",
                        change_summary="added failing assertions for bug 1"),
        ),
        generation_provenance=_generation_provenance(),
        configuration_version=OpaqueReference("config-v1"),
        finalization_state=CandidateFinalizationState.CREATED,
    )
    values.update(overrides)
    return CandidatePatch(**values)


def make_candidate_version(
    run_id: str,
    attempt_id: str,
    *,
    repair_level: int = 0,
    parent_candidate_version_id=None,
    producer_result_id=None,
    candidate_version_id: str = "candidate-version-1",
    candidate_patch_id: str = "candidate-patch-1",
    **overrides,
) -> CandidateVersion:
    values = dict(
        candidate_version_id=CandidateVersionId(candidate_version_id),
        candidate_patch_id=CandidatePatchId(candidate_patch_id),
        run_id=RunId(run_id),
        workflow_attempt_id=WorkflowAttemptId(attempt_id),
        repair_level=repair_level,
        parent_candidate_version_id=(
            CandidateVersionId(parent_candidate_version_id)
            if parent_candidate_version_id is not None
            else None
        ),
        producer_result_id=(
            ProducerResultId(producer_result_id)
            if producer_result_id is not None
            else None
        ),
        generation_provenance=_generation_provenance(),
        source_repository=OpaqueReference("github://example/example-repo"),
        source_revision=OpaqueReference(REVISION_40),
        configuration_version=OpaqueReference("config-v1"),
        finalization_state=CandidateFinalizationState.CREATED,
    )
    values.update(overrides)
    return CandidateVersion(**values)


# ---------------------------------------------------------------------------
# Artefact references and manifests
# ---------------------------------------------------------------------------


def make_integrity(state="UNVERIFIABLE", verification_reference=None):
    from app.evidence.execution import EvidenceIntegrityState

    integrity_state = EvidenceIntegrityState(state)
    if isinstance(verification_reference, str):
        verification_reference = OpaqueReference(verification_reference)
    return IntegrityMetadata(
        state=integrity_state, verification_reference=verification_reference
    )


def make_artefact_reference(**overrides) -> ArtefactReference:
    values = dict(
        artefact_id=ArtefactId("artefact.stdout.1"),
        artefact_type=ArtefactType.TEST_STDOUT,
        availability="AVAILABLE",
        integrity=make_integrity(),
        content_digest=OpaqueReference("sha256:" + "ef" * 32),
        digest_algorithm=OpaqueReference("SHA-256"),
        byte_size=2048,
        media_type="text/plain",
        producer_id=OpaqueReference("producer://execution-runner-1"),
        creation_timestamp=GENERATED_AT,
        storage_locator="object-store://bucket/evidence/artefact-stdout-1",
    )
    values.update(overrides)
    if isinstance(values.get("availability"), str):
        from app.evidence.execution import EvidenceAvailability

        values["availability"] = EvidenceAvailability(values["availability"])
    if isinstance(values.get("artefact_type"), str):
        values["artefact_type"] = ArtefactType(values["artefact_type"])
    if isinstance(values.get("content_digest"), str):
        values["content_digest"] = OpaqueReference(values["content_digest"])
    if isinstance(values.get("producer_id"), str):
        values["producer_id"] = OpaqueReference(values["producer_id"])
    return ArtefactReference(**values)


def make_artefact_manifest(members=(), **overrides) -> ArtefactManifest:
    from app.evidence.artefact import ArtefactManifestId

    values = dict(
        artefact_manifest_id=ArtefactManifestId("manifest-1"),
        artefact_references=tuple(members),
        creation_timestamp=GENERATED_AT,
        finalization_state=ArtefactManifestFinalizationState.ASSEMBLING,
    )
    values.update(overrides)
    return ArtefactManifest(**values)


def make_finalized_manifest_fields():
    """Required EVIDENCE-009 final metadata for a FINALIZED manifest."""
    return {
        "finalization_timestamp": GENERATED_AT + timedelta(minutes=5),
        "producer_provenance_reference": OpaqueReference(
            "producer-result://slot-1"
        ),
        "manifest_digest": OpaqueReference("sha256:" + "9a" * 32),
        "manifest_digest_algorithm": OpaqueReference("SHA-256"),
        "integrity_metadata": make_integrity(
            state="VERIFIED", verification_reference="verify-ref://manifest-1"
        ),
    }


# ---------------------------------------------------------------------------
# Execution evidence values
# ---------------------------------------------------------------------------


def _passed_test_result() -> TestResult:
    return TestResult(
        executed_count=2,
        passed_count=2,
        test_cases=(
            TestCaseResult(
                test_reference=OpaqueReference("test://ExampleTest.testAnswer"),
                status=TestCaseStatus.PASSED,
            ),
            TestCaseResult(
                test_reference=OpaqueReference("test://ExampleTest.testOther"),
                status=TestCaseStatus.PASSED,
            ),
        ),
    )


def make_execution_evidence(**overrides) -> ExecutionEvidence:
    values = dict(
        execution_evidence_id=ExecutionEvidenceId("execution-evidence-1"),
        producer_result_id=ProducerResultId("producer-result-1"),
        workflow_attempt_id=WorkflowAttemptId("attempt-placeholder"),
        candidate_version_id=CandidateVersionId("candidate-version-1"),
        execution_phase=ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST,
        outcome=ExecutionOutcome.SUCCESS,
        completeness="PARTIAL",
        command_reference=OpaqueReference("command://mvn-test-1"),
        execution_fact_reference=OpaqueReference("execution-fact://run-1"),
        source_revision=OpaqueReference(REVISION_40),
        test_result=_passed_test_result(),
        execution_timing=ExecutionTiming(
            started_at=GENERATED_AT,
            ended_at=GENERATED_AT + timedelta(seconds=30),
            duration=timedelta(seconds=30),
        ),
        timeout_metadata=TimeoutMetadata(timed_out=False),
        process_exit=None,
        execution_integrity=None,
    )
    values.update(overrides)
    if isinstance(values.get("completeness"), str):
        from app.evidence.execution import EvidenceCompleteness

        values["completeness"] = EvidenceCompleteness(values["completeness"])
    if isinstance(values.get("execution_phase"), str):
        values["execution_phase"] = ExecutionPhase(values["execution_phase"])
    if isinstance(values.get("outcome"), str):
        values["outcome"] = ExecutionOutcome(values["outcome"])
    if isinstance(values.get("workflow_attempt_id"), str):
        values["workflow_attempt_id"] = WorkflowAttemptId(
            values["workflow_attempt_id"]
        )
    return ExecutionEvidence(**values)


def make_compile_evidence(**overrides) -> ExecutionEvidence:
    overrides.setdefault("execution_phase", ExecutionPhase.COMPILE)
    overrides.setdefault("outcome", ExecutionOutcome.SUCCESS)
    overrides.setdefault(
        "compile_result", CompileResult(status=CompileStatus.SUCCESS)
    )
    overrides.setdefault("test_result", None)
    overrides.setdefault("source_revision", None)
    return make_execution_evidence(**overrides)


def make_fixed_execution_evidence(**overrides) -> ExecutionEvidence:
    overrides.setdefault(
        "execution_phase", ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST
    )
    overrides.setdefault(
        "execution_evidence_id", ExecutionEvidenceId("execution-evidence-fixed")
    )
    overrides.setdefault(
        "producer_result_id", ProducerResultId("producer-result-fixed")
    )
    return make_execution_evidence(**overrides)
