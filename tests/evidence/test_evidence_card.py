"""Contract coverage for the Evidence-owned immutable EvidenceCard projection."""

import ast
import inspect
import json
from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path

import pytest

import app.evidence
import app.evidence.bundle as bundle_module
import app.evidence.card as card_module
import app.evidence.decision as decision_module
from app.evidence import (
    EVIDENCE_CONTRACT_VERSION,
    ArtefactId,
    ArtefactManifest,
    ArtefactManifestFinalizationState,
    ArtefactManifestId,
    ArtefactReference,
    ArtefactType,
    CandidatePatchId,
    CandidateVersionId,
    CompileResult,
    CompileStatus,
    CorrelationId,
    EvidenceAvailability,
    EvidenceBundle,
    EvidenceBundleId,
    EvidenceCard,
    EvidenceCardContext,
    EvidenceCardId,
    EvidenceCardPhaseSummary,
    EvidenceComparison,
    EvidenceCompleteness,
    EvidenceIntegrityState,
    ExecutionEvidence,
    ExecutionEvidenceId,
    ExecutionOutcome,
    ExecutionPhase,
    ExecutionTiming,
    FailureCategory,
    FailureEvidence,
    HumanDecisionId,
    HumanDecisionLink,
    IntegrityMetadata,
    OpaqueReference,
    ProcessExit,
    ProducerResultId,
    QueueDeliveryId,
    QueueMessageId,
    RunId,
    TestCaseResult as ExecutionTestCaseResult,
    TestCaseStatus as ExecutionTestCaseStatus,
    TestResult as ExecutionTestResult,
    TimeoutMetadata,
    WorkflowAttemptId,
    compare_evidence_bundles,
    compare_evidence_cards,
    project_evidence_card,
)


STARTED_AT = datetime(2026, 8, 22, 9, 0, tzinfo=timezone.utc)
ENDED_AT = STARTED_AT + timedelta(seconds=2)
ARTEFACT_CREATED_AT = datetime(2026, 8, 22, 8, 55, tzinfo=timezone.utc)

BUGGY_REVISION = "revision:buggy:abc123"
FIXED_REVISION = "revision:fixed:def456"


def verified(reference: str) -> IntegrityMetadata:
    return IntegrityMetadata(
        EvidenceIntegrityState.VERIFIED,
        OpaqueReference(reference),
    )


def observed(state: EvidenceIntegrityState) -> IntegrityMetadata:
    return IntegrityMetadata(
        state,
        OpaqueReference(f"integrity-observation:{state.value.lower()}"),
    )


def artefact(
    identity: str,
    artefact_type: ArtefactType,
    *,
    availability: EvidenceAvailability = EvidenceAvailability.AVAILABLE,
    integrity_state: EvidenceIntegrityState = EvidenceIntegrityState.VERIFIED,
) -> ArtefactReference:
    integrity = (
        verified(f"integrity:{identity}")
        if integrity_state is EvidenceIntegrityState.VERIFIED
        else observed(integrity_state)
    )
    return ArtefactReference(
        artefact_id=ArtefactId(identity),
        artefact_type=artefact_type,
        availability=availability,
        integrity=integrity,
        content_digest=OpaqueReference(f"digest:{identity}"),
        digest_algorithm=OpaqueReference("digest-algorithm:configured"),
        byte_size=64,
        media_type="text/plain",
        producer_id=OpaqueReference("producer:execution-runner"),
        creation_timestamp=ARTEFACT_CREATED_AT,
        storage_locator=f"locator:{identity}",
    )


def timing() -> ExecutionTiming:
    return ExecutionTiming(
        started_at=STARTED_AT,
        ended_at=ENDED_AT,
        duration=timedelta(seconds=2),
        upstream_fact_reference=OpaqueReference("execution-timing:1"),
    )


def passed_case(reference: str = "test:passes") -> ExecutionTestCaseResult:
    return ExecutionTestCaseResult(
        OpaqueReference(reference),
        ExecutionTestCaseStatus.PASSED,
    )


def failed_case(reference: str = "test:fails") -> ExecutionTestCaseResult:
    return ExecutionTestCaseResult(
        OpaqueReference(reference),
        ExecutionTestCaseStatus.FAILED,
        OpaqueReference(f"failure:{reference}"),
    )


def compile_record(**changes: object) -> ExecutionEvidence:
    values: dict[str, object] = {
        "execution_evidence_id": ExecutionEvidenceId("evidence:compile:1"),
        "producer_result_id": ProducerResultId("producer-result:compile:1"),
        "workflow_attempt_id": WorkflowAttemptId("attempt:1"),
        "candidate_version_id": CandidateVersionId("candidate-version:1"),
        "execution_phase": ExecutionPhase.COMPILE,
        "outcome": ExecutionOutcome.SUCCESS,
        "completeness": EvidenceCompleteness.COMPLETE,
        "command_reference": OpaqueReference("execution-command:compile:1"),
        "execution_fact_reference": OpaqueReference("execution-result:compile:1"),
        "compile_result": CompileResult(
            CompileStatus.SUCCESS,
            error_count=0,
            warning_count=1,
            compiler_metadata_reference=OpaqueReference("compiler-metadata:1"),
        ),
        "run_id": RunId("run:1"),
        "execution_timing": timing(),
        "timeout_metadata": TimeoutMetadata(timed_out=False),
        "process_exit": process_exit(),
        "stdout_artefact": artefact("artefact:compile-stdout:1", ArtefactType.COMPILE_LOG),
        "stderr_artefact": artefact("artefact:compile-stderr:1", ArtefactType.COMPILE_LOG),
        "execution_integrity": verified("integrity:execution:compile:1"),
    }
    values.update(changes)
    return ExecutionEvidence(**values)  # type: ignore[arg-type]


def buggy_record(**changes: object) -> ExecutionEvidence:
    values: dict[str, object] = {
        "execution_evidence_id": ExecutionEvidenceId("evidence:buggy-test:1"),
        "producer_result_id": ProducerResultId("producer-result:buggy-test:1"),
        "workflow_attempt_id": WorkflowAttemptId("attempt:1"),
        "candidate_version_id": CandidateVersionId("candidate-version:1"),
        "execution_phase": ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST,
        "outcome": ExecutionOutcome.SUCCESS,
        "completeness": EvidenceCompleteness.COMPLETE,
        "command_reference": OpaqueReference("execution-command:buggy-test:1"),
        "execution_fact_reference": OpaqueReference("execution-result:buggy-test:1"),
        "test_result": ExecutionTestResult(
            executed_count=1,
            passed_count=1,
            failed_count=0,
            skipped_count=0,
            errored_count=0,
            test_cases=(passed_case(),),
        ),
        "run_id": RunId("run:1"),
        "source_revision": OpaqueReference(BUGGY_REVISION),
        "execution_timing": timing(),
        "timeout_metadata": TimeoutMetadata(timed_out=False),
        "process_exit": process_exit(),
        "stdout_artefact": artefact("artefact:buggy-stdout:1", ArtefactType.TEST_STDOUT),
        "stderr_artefact": artefact("artefact:buggy-stderr:1", ArtefactType.TEST_STDERR),
        "execution_integrity": verified("integrity:execution:buggy-test:1"),
    }
    values.update(changes)
    return ExecutionEvidence(**values)  # type: ignore[arg-type]


def fixed_record(**changes: object) -> ExecutionEvidence:
    values: dict[str, object] = {
        "execution_evidence_id": ExecutionEvidenceId("evidence:fixed-test:1"),
        "producer_result_id": ProducerResultId("producer-result:fixed-test:1"),
        "workflow_attempt_id": WorkflowAttemptId("attempt:1"),
        "candidate_version_id": CandidateVersionId("candidate-version:1"),
        "execution_phase": ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST,
        "outcome": ExecutionOutcome.SUCCESS,
        "completeness": EvidenceCompleteness.COMPLETE,
        "command_reference": OpaqueReference("execution-command:fixed-test:1"),
        "execution_fact_reference": OpaqueReference("execution-result:fixed-test:1"),
        "test_result": ExecutionTestResult(
            executed_count=1,
            passed_count=1,
            failed_count=0,
            skipped_count=0,
            errored_count=0,
            test_cases=(passed_case(),),
        ),
        "run_id": RunId("run:1"),
        "source_revision": OpaqueReference(FIXED_REVISION),
        "execution_timing": timing(),
        "timeout_metadata": TimeoutMetadata(timed_out=False),
        "process_exit": process_exit(),
        "stdout_artefact": artefact("artefact:fixed-stdout:1", ArtefactType.TEST_STDOUT),
        "stderr_artefact": artefact("artefact:fixed-stderr:1", ArtefactType.TEST_STDERR),
        "execution_integrity": verified("integrity:execution:fixed-test:1"),
    }
    values.update(changes)
    return ExecutionEvidence(**values)  # type: ignore[arg-type]


def manifest(**changes: object) -> ArtefactManifest:
    values: dict[str, object] = {
        "artefact_manifest_id": ArtefactManifestId("artefact-manifest:1"),
        "artefact_references": (
            artefact("artefact:manifest:2", ArtefactType.TEST_STDOUT),
            artefact("artefact:manifest:1", ArtefactType.CONTEXT_MANIFEST),
        ),
        "creation_timestamp": ARTEFACT_CREATED_AT,
        "finalization_state": ArtefactManifestFinalizationState.ASSEMBLING,
        "candidate_version_id": CandidateVersionId("candidate-version:1"),
        "workflow_attempt_id": WorkflowAttemptId("attempt:1"),
    }
    values.update(changes)
    return ArtefactManifest(**values)  # type: ignore[arg-type]


def finalized_manifest(**changes: object) -> ArtefactManifest:
    values = {
        "finalization_state": ArtefactManifestFinalizationState.FINALIZED,
        "producer_provenance_reference": OpaqueReference("producer-provenance:1"),
        "manifest_digest": OpaqueReference("manifest-digest:1"),
        "manifest_digest_algorithm": OpaqueReference("digest-algorithm:configured"),
        "integrity_metadata": verified("integrity:artefact-manifest:1"),
        "finalization_timestamp": ARTEFACT_CREATED_AT + timedelta(seconds=1),
    }
    values.update(changes)
    return manifest(**values)


def bundle_values(**changes: object) -> dict[str, object]:
    values: dict[str, object] = {
        "evidence_bundle_id": EvidenceBundleId("bundle:1"),
        "candidate_patch_id": CandidatePatchId("patch:1"),
        "candidate_version_id": CandidateVersionId("candidate-version:1"),
        "completeness": EvidenceCompleteness.PARTIAL,
        "run_id": RunId("run:1"),
        "run_request_id": OpaqueReference("run-request:1"),
        "workflow_attempt_id": WorkflowAttemptId("attempt:1"),
        "workflow_step": OpaqueReference("workflow-step:1"),
        "producer_id": OpaqueReference("producer:runner-host"),
        "runner_id": OpaqueReference("runner:host-1"),
        "source_repository": OpaqueReference("repo:testgap/example"),
        "source_revision": OpaqueReference(BUGGY_REVISION),
        "selected_context_manifest": OpaqueReference("context-manifest:1"),
        "configuration_version": OpaqueReference("configuration:v1"),
        "model_identifier": OpaqueReference("model:test-model"),
        "prompt_template_version": OpaqueReference("prompt-template:v1"),
        "producer_schema_version": OpaqueReference("producer-schema:v1"),
    }
    values.update(changes)
    return values


def bundle(**changes: object) -> EvidenceBundle:
    return EvidenceBundle(**bundle_values(**changes))  # type: ignore[arg-type]


def aggregate_bundle(**changes: object) -> EvidenceBundle:
    values = bundle_values(
        target_reference_revision=OpaqueReference(FIXED_REVISION),
        execution_evidence=[compile_record(), buggy_record(), fixed_record()],
    )
    values.update(changes)
    return EvidenceBundle(**values)  # type: ignore[arg-type]


def complete_bundle(**changes: object) -> EvidenceBundle:
    values = bundle_values(
        completeness=EvidenceCompleteness.COMPLETE,
        target_reference_revision=OpaqueReference(FIXED_REVISION),
        execution_evidence=[compile_record(), buggy_record(), fixed_record()],
        integrity_metadata=verified("integrity:bundle:1"),
    )
    values.update(changes)
    return EvidenceBundle(**values)  # type: ignore[arg-type]


def process_exit() -> ProcessExit:
    return ProcessExit(
        exit_code=0,
        upstream_fact_reference=OpaqueReference("process-exit:1"),
    )


CARD_ID_VALUE = "evidence-card:v1"


def card_id(value: str = CARD_ID_VALUE) -> EvidenceCardId:
    return EvidenceCardId(value)


FIXED_UNAVAILABLE_REASON = OpaqueReference("reference-fix-not-provided")
FIXED_UNAVAILABLE = {
    ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST: FIXED_UNAVAILABLE_REASON,
}


def project(
    value: EvidenceBundle,
    **changes: object,
) -> EvidenceCard:
    options: dict[str, object] = {
        "evidence_card_id": card_id(),
        "ai_generated": True,
        "human_review_required": True,
    }
    options.update(changes)
    return project_evidence_card(value, **options)  # type: ignore[arg-type]


def manual_card(base: EvidenceCard | None = None, **overrides: object) -> EvidenceCard:
    """Reconstruct a card through its own constructor for invariant testing."""
    source = base if base is not None else project(aggregate_bundle())
    values: dict[str, object] = {
        "evidence_card_id": source.evidence_card_id,
        "reviewed_evidence_bundle_id": source.reviewed_evidence_bundle_id,
        "candidate_patch_id": source.candidate_patch_id,
        "candidate_version_id": source.candidate_version_id,
        "completeness": source.completeness,
        "integrity_state": source.integrity_state,
        "selected_files_manifest_summary": source.selected_files_manifest_summary,
        "review_context": source.review_context,
        "execution_summaries": source.execution_summaries,
        "artefact_references": source.artefact_references,
        "ai_generated": source.ai_generated,
        "human_review_required": source.human_review_required,
        "explanation_or_rationale_reference": source.explanation_or_rationale_reference,
        "confidence_reference": source.confidence_reference,
        "uncertainty_flag": source.uncertainty_flag,
        "uncertainty_category": source.uncertainty_category,
        "assessment_producer": source.assessment_producer,
        "calibration_metadata": source.calibration_metadata,
        "governing_contract_version": source.governing_contract_version,
    }
    values.update(overrides)
    return EvidenceCard(**values)  # type: ignore[arg-type]


LEGACY_EXPORTS = frozenset(
    {
        "ARTEFACT_MANIFEST_CARDINALITY_BOUND",
        "ARTEFACT_MANIFEST_SCHEMA_VERSION",
        "EVIDENCE_CONTRACT_VERSION",
        "QUEUE_CONTRACT_VERSION",
        "WORKFLOW_CONTRACT_VERSION",
        "ArtefactId",
        "ArtefactManifest",
        "ArtefactManifestFinalizationState",
        "ArtefactManifestId",
        "ArtefactReference",
        "ArtefactType",
        "CandidateFinalizationState",
        "CandidatePatch",
        "CandidatePatchId",
        "CandidateVersion",
        "CandidateVersionId",
        "ChangedFile",
        "CompileStatus",
        "CompileResult",
        "CorrelationId",
        "DecisionDisposition",
        "EvidenceAvailability",
        "EvidenceBundle",
        "EvidenceBundleId",
        "EvidenceCardId",
        "EvidenceComparison",
        "EvidenceCompleteness",
        "EvidenceIntegrityState",
        "ExecutionEvidence",
        "ExecutionEvidenceId",
        "ExecutionOutcome",
        "ExecutionPhase",
        "ExecutionTiming",
        "FailureCategory",
        "FailureEvidence",
        "GenerationProvenance",
        "HumanDecisionId",
        "HumanDecisionLink",
        "HumanDecisionLinkId",
        "IntegrityMetadata",
        "OpaqueReference",
        "ProcessExit",
        "ProducerResultId",
        "QueueDeliveryId",
        "QueueMessageId",
        "ResourceCategory",
        "ResourceEnforcementStatus",
        "ResourceObservation",
        "ResourceValue",
        "RunId",
        "TestCaseResult",
        "TestCaseStatus",
        "TestResult",
        "TimeoutMetadata",
        "WorkflowAttemptId",
        "compare_artefact_manifests",
        "compare_artefact_references",
        "compare_candidate_patches",
        "compare_candidate_versions",
        "compare_evidence_bundles",
        "compare_execution_evidence",
        "compare_human_decision_links",
        "validate_candidate_lineage",
        "validate_candidate_patch_version",
    }
)

CARD_EXPORTS = frozenset(
    {
        "EvidenceCard",
        "EvidenceCardContext",
        "EvidenceCardPhaseSummary",
        "compare_evidence_cards",
        "project_evidence_card",
    }
)

FORBIDDEN_RUNTIME_MEMBERS = (
    "ack",
    "approve",
    "authorize",
    "claim",
    "connect",
    "cursor",
    "download",
    "execute",
    "migrate",
    "nack",
    "open",
    "presign",
    "publish",
    "redact",
    "render",
    "retry",
    "route",
    "score",
    "session",
    "style",
    "submit",
    "subprocess",
    "transition",
    "upload",
)

FORBIDDEN_SOURCE_TOKENS = (
    "subprocess",
    "sqlalchemy",
    "boto3",
    "socket",
    "httpx",
    "requests",
    "uuid",
    "secrets",
    "random.",
    "datetime.now",
    "time.time",
    "fastapi",
    "presign",
)

ALLOWED_CARD_IMPORT_ROOTS = frozenset(
    {"__future__", "json", "collections", "dataclasses", "typing"}
)

UNCERTAINTY_NON_NORMATIVE_EXAMPLES = (
    "MODEL_HALLUCINATION_RISK",
    "TEST_FLAKINESS",
    "PARTIAL_EXECUTION",
    "UNRESOLVED_DEPENDENCY",
    "AMBIGUOUS_SPECIFICATION",
)


def test_valid_bundle_projects_review_card() -> None:
    value = aggregate_bundle()
    supplied = card_id()
    result = project(value, evidence_card_id=supplied)
    assert isinstance(result, EvidenceCard)
    assert result.evidence_card_id is supplied
    assert result.reviewed_evidence_bundle_id == EvidenceBundleId("bundle:1")
    assert result.candidate_patch_id == CandidatePatchId("patch:1")
    assert result.candidate_version_id == CandidateVersionId("candidate-version:1")
    assert result.completeness is EvidenceCompleteness.PARTIAL
    assert result.integrity_state is None
    assert result.selected_files_manifest_summary.value == "context-manifest:1"
    assert len(result.execution_summaries) == 3
    assert result.governing_contract_version == EVIDENCE_CONTRACT_VERSION


def test_canonical_evidence_card_id_is_reused_not_redeclared() -> None:
    assert app.evidence.EvidenceCardId is decision_module.EvidenceCardId
    assert card_module.EvidenceCardId is decision_module.EvidenceCardId
    value = project(aggregate_bundle())
    assert isinstance(value.evidence_card_id, decision_module.EvidenceCardId)
    assert type(value.evidence_card_id) is decision_module.EvidenceCardId
    for forbidden in (
        "EvidenceCardIdV2",
        "CardIdentity",
        "ReviewCardId",
        "EvidenceProjectionId",
    ):
        assert not hasattr(app.evidence, forbidden), forbidden


def test_caller_supplied_card_identity_retained_without_generation() -> None:
    supplied = card_id("evidence-card:caller-owned")
    first = project(aggregate_bundle(), evidence_card_id=supplied)
    second = project(aggregate_bundle(), evidence_card_id=supplied)
    assert first.evidence_card_id is supplied
    assert second.evidence_card_id is supplied
    generators = [
        name
        for name, member in vars(card_module).items()
        if callable(member)
        and any(token in name.lower() for token in ("generate", "mint"))
    ]
    for owner in (EvidenceCard, EvidenceCardContext, EvidenceCardPhaseSummary):
        generators += [
            name
            for name, member in vars(owner).items()
            if callable(member)
            and any(token in name.lower() for token in ("generate", "mint", "new_"))
        ]
    assert not generators
    source = inspect.getsource(card_module)
    for token in ("uuid", "secrets", "random.", "time.time"):
        assert token not in source, token


def test_exact_evidence_bundle_binding() -> None:
    value = bundle(evidence_bundle_id=EvidenceBundleId("bundle:exact"))
    result = project(value, missing_phase_reasons=FIXED_UNAVAILABLE)
    assert result.reviewed_evidence_bundle_id is value.evidence_bundle_id
    assert result.reviewed_evidence_bundle_id == EvidenceBundleId("bundle:exact")
    assert result.review_context.run_id is value.run_id
    assert result.review_context.workflow_attempt_id is value.workflow_attempt_id


def test_no_latest_bundle_inference_exists() -> None:
    signature = inspect.signature(project_evidence_card)
    parameters = list(signature.parameters.values())
    assert parameters[0].name == "bundle"
    assert parameters[0].default is inspect.Parameter.empty
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in parameters[1:]
    )
    assert not hasattr(card_module, "latest_bundle")
    assert not hasattr(card_module, "resolve_latest")
    one = project(bundle(evidence_bundle_id=EvidenceBundleId("bundle:one")),
                  evidence_card_id=card_id("evidence-card:one"),
                  missing_phase_reasons=FIXED_UNAVAILABLE)
    two = project(bundle(evidence_bundle_id=EvidenceBundleId("bundle:two")),
                  evidence_card_id=card_id("evidence-card:two"),
                  missing_phase_reasons=FIXED_UNAVAILABLE)
    assert one.reviewed_evidence_bundle_id == EvidenceBundleId("bundle:one")
    assert two.reviewed_evidence_bundle_id == EvidenceBundleId("bundle:two")


def test_deterministic_serialization() -> None:
    left = project(aggregate_bundle())
    right = project(aggregate_bundle())
    assert left == right
    serialized = left.to_domain_json()
    assert serialized == right.to_domain_json()
    assert "0x" not in serialized
    reparsed = json.loads(serialized)
    assert reparsed["evidence_card_id"] == {"value": CARD_ID_VALUE}
    assert reparsed["reviewed_evidence_bundle_id"] == {"value": "bundle:1"}
    assert reparsed["completeness"] == "PARTIAL"
    assert reparsed["ai_generated"] is True
    assert reparsed["human_review_required"] is True
    assert reparsed["governing_contract_version"] == EVIDENCE_CONTRACT_VERSION
    canonical = json.dumps(
        left.to_domain_dict(),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    assert canonical == serialized


def test_input_order_and_insertion_order_do_not_change_representation() -> None:
    base = project(aggregate_bundle())
    summaries = list(base.execution_summaries)
    references = [
        artefact("artefact:zulu:1", ArtefactType.CUSTOM_OUTPUT),
        artefact("artefact:alpha:1", ArtefactType.CUSTOM_OUTPUT),
    ]
    forward = manual_card(
        execution_summaries=summaries,
        artefact_references=references,
    )
    backward = manual_card(
        execution_summaries=list(reversed(summaries)),
        artefact_references=list(reversed(references)),
    )
    assert forward.to_domain_json() == backward.to_domain_json()
    declaration_order = list(ExecutionPhase)
    assert [summary.phase for summary in forward.execution_summaries] == declaration_order
    keys = [item.artefact_id.value for item in forward.artefact_references]
    assert keys == sorted(keys)


def test_card_and_nested_values_are_immutable() -> None:
    value = project(aggregate_bundle())
    snapshot = value.to_domain_json()
    with pytest.raises(FrozenInstanceError):
        value.completeness = EvidenceCompleteness.INVALID  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        value.review_context.run_id = RunId("run:mutated")  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        value.execution_summaries[0].outcome = ExecutionOutcome.SUCCESS  # type: ignore[misc]
    replaced = replace(value, ai_generated=False)
    assert replaced is not value
    assert replaced.ai_generated is False
    assert value.ai_generated is True
    assert value.to_domain_json() == snapshot


def test_caller_input_mutation_cannot_mutate_card() -> None:
    records = [compile_record()]
    value = bundle(execution_evidence=records)
    card = project(value, missing_phase_reasons=FIXED_UNAVAILABLE)
    records.append(buggy_record())
    records.clear()
    projected_phases = {
        summary.phase
        for summary in card.execution_summaries
        if summary.outcome is not None
    }
    assert projected_phases == {ExecutionPhase.COMPILE}

    base = project(aggregate_bundle())
    summaries = list(base.execution_summaries)
    references = list(base.artefact_references)
    manual = manual_card(base, execution_summaries=summaries, artefact_references=references)
    summaries.clear()
    references.append(artefact("artefact:intruder:1", ArtefactType.CUSTOM_OUTPUT))
    assert manual.to_domain_json() == base.to_domain_json()


def test_duplicate_projection_converges_equivalently() -> None:
    existing = project(aggregate_bundle())
    incoming = project(aggregate_bundle())
    assert existing is not incoming
    assert compare_evidence_cards(existing, incoming) is EvidenceComparison.EQUIVALENT


def test_same_card_id_material_difference_is_conflicting_without_mutation() -> None:
    existing = project(
        aggregate_bundle(),
        explanation_or_rationale_reference=OpaqueReference("rationale:a"),
    )
    incoming = replace(
        existing,
        explanation_or_rationale_reference=OpaqueReference("rationale:b"),
    )
    existing_snapshot = existing.to_domain_json()
    incoming_snapshot = incoming.to_domain_json()
    assert compare_evidence_cards(existing, incoming) is EvidenceComparison.CONFLICTING
    assert existing.to_domain_json() == existing_snapshot
    assert incoming.to_domain_json() == incoming_snapshot


def test_different_card_id_is_distinct_identity() -> None:
    existing = project(aggregate_bundle())
    other = replace(existing, evidence_card_id=card_id("evidence-card:v2"))
    assert compare_evidence_cards(existing, other) is EvidenceComparison.DISTINCT_IDENTITY


def test_compile_success_summary_projection() -> None:
    card = project(aggregate_bundle())
    summary = card.phase_summaries_by_phase[ExecutionPhase.COMPILE]
    assert summary.execution_evidence_id == ExecutionEvidenceId("evidence:compile:1")
    assert summary.outcome is ExecutionOutcome.SUCCESS
    assert summary.completeness is EvidenceCompleteness.COMPLETE
    assert summary.compile_status is CompileStatus.SUCCESS
    assert summary.failure_category is None
    assert summary.executed_count is None and summary.passed_count is None
    assert summary.integrity_state is EvidenceIntegrityState.VERIFIED


def test_compile_failure_summary_projection() -> None:
    failing_compile = compile_record(
        outcome=ExecutionOutcome.COMPILATION_FAILURE,
        compile_result=CompileResult(
            CompileStatus.FAILURE,
            error_count=3,
            warning_count=0,
        ),
        process_exit=ProcessExit(
            exit_code=1,
            upstream_fact_reference=OpaqueReference("process-exit:compile-failed"),
        ),
        failure=FailureEvidence(
            FailureCategory.COMPILATION_FAILURE,
            OpaqueReference("failure-ref:compile:1"),
        ),
    )
    value = bundle(
        execution_evidence=[
            failing_compile,
            buggy_record(),
            fixed_record(),
        ],
        target_reference_revision=OpaqueReference(FIXED_REVISION),
    )
    summary = project(value).phase_summaries_by_phase[ExecutionPhase.COMPILE]
    assert summary.outcome is ExecutionOutcome.COMPILATION_FAILURE
    assert summary.compile_status is CompileStatus.FAILURE
    assert summary.failure_category is FailureCategory.COMPILATION_FAILURE
    assert summary.outcome is not ExecutionOutcome.SUCCESS


def test_buggy_test_summary_projection() -> None:
    failing_buggy = buggy_record(
        outcome=ExecutionOutcome.TEST_FAILURE,
        failure=FailureEvidence(
            FailureCategory.TEST_FAILURE,
            OpaqueReference("failure-ref:buggy-test:1"),
        ),
        test_result=ExecutionTestResult(
            executed_count=2,
            passed_count=1,
            failed_count=1,
            skipped_count=0,
            errored_count=0,
            test_cases=(passed_case(), failed_case()),
        ),
    )
    value = bundle(execution_evidence=[failing_buggy])
    summary = project(value, missing_phase_reasons=FIXED_UNAVAILABLE).phase_summaries_by_phase[
        ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST
    ]
    assert summary.outcome is ExecutionOutcome.TEST_FAILURE
    assert summary.failure_category is FailureCategory.TEST_FAILURE
    assert summary.executed_count == 2
    assert summary.passed_count == 1
    assert summary.failed_count == 1
    assert summary.skipped_count == 0
    assert summary.errored_count == 0
    assert summary.compile_status is None
    assert summary.integrity_state is EvidenceIntegrityState.VERIFIED


def test_fixed_reference_test_summary_projection() -> None:
    value = aggregate_bundle()
    summary = project(value).phase_summaries_by_phase[
        ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST
    ]
    assert summary.execution_evidence_id == ExecutionEvidenceId("evidence:fixed-test:1")
    assert summary.outcome is ExecutionOutcome.SUCCESS
    assert summary.completeness is EvidenceCompleteness.COMPLETE
    assert summary.executed_count == 1
    assert summary.passed_count == 1
    assert summary.failed_count == 0
    assert summary.skipped_count == 0
    assert summary.errored_count == 0
    assert summary.integrity_state is EvidenceIntegrityState.VERIFIED


def test_non_success_outcomes_are_projected_verbatim() -> None:
    timed_out = buggy_record(
        outcome=ExecutionOutcome.TIMEOUT,
        timeout_metadata=TimeoutMetadata(
            timed_out=True,
            classification=OpaqueReference("timeout-class:1"),
            configured_limit=timedelta(seconds=30),
        ),
        failure=FailureEvidence(
            FailureCategory.TIMEOUT,
            OpaqueReference("failure-ref:timeout:1"),
        ),
    )
    value = bundle(execution_evidence=[timed_out])
    summary = project(value, missing_phase_reasons=FIXED_UNAVAILABLE).phase_summaries_by_phase[
        ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST
    ]
    assert summary.outcome is ExecutionOutcome.TIMEOUT
    assert summary.failure_category is FailureCategory.TIMEOUT
    assert summary.outcome is not ExecutionOutcome.SUCCESS


def test_missing_compile_phase_is_represented_honestly() -> None:
    value = bundle(execution_evidence=[buggy_record()])
    summary = project(
        value,
        missing_phase_reasons=FIXED_UNAVAILABLE,
    ).phase_summaries_by_phase[ExecutionPhase.COMPILE]
    assert summary.phase is ExecutionPhase.COMPILE
    assert summary.execution_evidence_id is None
    assert summary.outcome is None
    assert summary.compile_status is None
    assert summary.completeness is None
    assert summary.integrity_state is None
    assert summary.failure_category is None
    assert summary.unavailable_reason is None


def test_missing_buggy_phase_is_represented_honestly() -> None:
    value = bundle(execution_evidence=[compile_record()])
    summary = project(
        value,
        missing_phase_reasons=FIXED_UNAVAILABLE,
    ).phase_summaries_by_phase[
        ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST
    ]
    assert summary.execution_evidence_id is None
    assert summary.outcome is None
    assert summary.passed_count is None
    assert summary.failed_count is None
    assert summary.outcome is not ExecutionOutcome.SUCCESS
    assert summary.unavailable_reason is None


def test_missing_fixed_phase_without_reason_fails_closed() -> None:
    with pytest.raises(ValueError, match="requires an explicit"):
        project(bundle(execution_evidence=[compile_record(), buggy_record()]))
    with pytest.raises(ValueError, match="requires an explicit"):
        project(bundle())
    with pytest.raises(ValueError, match="requires an explicit"):
        project(bundle(execution_evidence=[buggy_record()]))


def test_missing_fixed_phase_does_not_synthesize_pass() -> None:
    value = bundle(execution_evidence=[compile_record(), buggy_record()])
    card = project(value, missing_phase_reasons=FIXED_UNAVAILABLE)
    summary = card.phase_summaries_by_phase[
        ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST
    ]
    assert summary.unavailable_reason is FIXED_UNAVAILABLE_REASON
    assert summary.execution_evidence_id is None
    assert summary.outcome is None
    assert summary.passed_count is None
    for item in card.execution_summaries:
        if item.execution_evidence_id is None:
            assert item.outcome is None, item.phase
            assert item.passed_count is None, item.phase
    absent_outcomes = {
        item.phase: item.outcome
        for item in card.execution_summaries
        if item.execution_evidence_id is None
    }
    assert ExecutionOutcome.SUCCESS not in set(absent_outcomes.values())


def test_empty_bundle_represents_every_phase_as_absent_without_success() -> None:
    card = project(bundle(), missing_phase_reasons=FIXED_UNAVAILABLE)
    assert len(card.execution_summaries) == 3
    assert all(summary.outcome is None for summary in card.execution_summaries)
    assert all(
        summary.execution_evidence_id is None for summary in card.execution_summaries
    )
    serialized = card.to_domain_json()
    assert '"SUCCESS"' not in serialized
    assert '"PASSED"' not in serialized
    assert '"VERIFIED"' not in serialized


def test_unavailable_reason_for_present_fixed_phase_fails_closed() -> None:
    with pytest.raises(ValueError, match="contradicts supplied execution"):
        project(
            aggregate_bundle(),
            missing_phase_reasons={
                ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST: (
                    OpaqueReference("why")
                )
            },
        )


def test_explicit_fixed_reference_unavailable_reason_is_preserved() -> None:
    reason = OpaqueReference("reference-fix-not-provided")
    card = project(
        bundle(),
        missing_phase_reasons={ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST: reason},
    )
    summary = card.phase_summaries_by_phase[
        ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST
    ]
    assert summary.unavailable_reason is reason
    assert summary.unavailable_reason.value == "reference-fix-not-provided"
    assert summary.outcome is None
    assert summary.execution_evidence_id is None


def test_missing_phase_reason_order_does_not_change_representation() -> None:
    compile_reason = OpaqueReference("reason:compile-absent")
    fixed_reason = OpaqueReference("reason:reference-fix-not-provided")
    left = project(
        bundle(),
        missing_phase_reasons={
            ExecutionPhase.COMPILE: compile_reason,
            ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST: fixed_reason,
        },
    )
    right = project(
        bundle(),
        missing_phase_reasons={
            ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST: fixed_reason,
            ExecutionPhase.COMPILE: compile_reason,
        },
    )
    assert left.to_domain_json() == right.to_domain_json()


def test_unavailable_reason_for_present_phase_fails_closed() -> None:
    with pytest.raises(ValueError, match="unavailable reason"):
        project(
            aggregate_bundle(),
            missing_phase_reasons={ExecutionPhase.COMPILE: OpaqueReference("why")},
        )


def test_absent_phase_summary_rejects_execution_facts() -> None:
    with pytest.raises(ValueError, match="absent execution phase"):
        EvidenceCardPhaseSummary(
            phase=ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST,
            outcome=ExecutionOutcome.SUCCESS,
        )
    with pytest.raises(ValueError, match="absent execution phase"):
        EvidenceCardPhaseSummary(
            phase=ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST,
            passed_count=12,
        )
    with pytest.raises(ValueError, match="absent execution phase"):
        EvidenceCardPhaseSummary(
            phase=ExecutionPhase.COMPILE,
            compile_status=CompileStatus.SUCCESS,
        )


def test_present_phase_summary_requires_supplied_facts() -> None:
    with pytest.raises(ValueError, match="requires"):
        EvidenceCardPhaseSummary(
            phase=ExecutionPhase.COMPILE,
            execution_evidence_id=ExecutionEvidenceId("evidence:compile:9"),
        )


def test_unavailable_reason_applies_only_to_absent_phase() -> None:
    with pytest.raises(ValueError, match="applies only"):
        EvidenceCardPhaseSummary(
            phase=ExecutionPhase.COMPILE,
            execution_evidence_id=ExecutionEvidenceId("evidence:compile:9"),
            outcome=ExecutionOutcome.SUCCESS,
            completeness=EvidenceCompleteness.COMPLETE,
            compile_status=CompileStatus.SUCCESS,
            unavailable_reason=OpaqueReference("why"),
        )


def test_phase_summary_shape_is_respected_per_phase_kind() -> None:
    with pytest.raises(ValueError, match="test count facts"):
        EvidenceCardPhaseSummary(
            phase=ExecutionPhase.COMPILE,
            execution_evidence_id=ExecutionEvidenceId("evidence:compile:9"),
            outcome=ExecutionOutcome.SUCCESS,
            completeness=EvidenceCompleteness.COMPLETE,
            compile_status=CompileStatus.SUCCESS,
            executed_count=4,
        )
    with pytest.raises(ValueError, match="compile status"):
        EvidenceCardPhaseSummary(
            phase=ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST,
            execution_evidence_id=ExecutionEvidenceId("evidence:buggy-test:9"),
            outcome=ExecutionOutcome.SUCCESS,
            completeness=EvidenceCompleteness.COMPLETE,
            compile_status=CompileStatus.SUCCESS,
        )


def test_absent_fixed_reference_summary_requires_explicit_reason() -> None:
    with pytest.raises(ValueError, match="requires an explicit unavailable reason"):
        EvidenceCardPhaseSummary(
            phase=ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST
        )
    reason = OpaqueReference("reference-fix-not-provided")
    absent_with_reason = EvidenceCardPhaseSummary(
        phase=ExecutionPhase.FIXED_OR_REFERENCE_REVISION_TEST,
        unavailable_reason=reason,
    )
    assert absent_with_reason.execution_evidence_id is None
    assert absent_with_reason.outcome is None
    assert absent_with_reason.unavailable_reason is reason


def test_absent_non_fixed_phase_summaries_remain_valid_without_reason() -> None:
    compile_summary = EvidenceCardPhaseSummary(phase=ExecutionPhase.COMPILE)
    assert compile_summary.phase is ExecutionPhase.COMPILE
    assert compile_summary.execution_evidence_id is None
    assert compile_summary.unavailable_reason is None
    buggy_summary = EvidenceCardPhaseSummary(
        phase=ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST
    )
    assert buggy_summary.phase is ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST
    assert buggy_summary.execution_evidence_id is None
    assert buggy_summary.unavailable_reason is None


def test_direct_construction_requires_every_known_phase_once() -> None:
    base = project(aggregate_bundle())
    summaries = list(base.execution_summaries)
    with pytest.raises(ValueError, match="duplicate semantic execution phase"):
        manual_card(base, execution_summaries=[summaries[0], summaries[0], summaries[2]])
    with pytest.raises(ValueError, match="exactly one summary per known execution phase"):
        manual_card(base, execution_summaries=[summaries[0]])


@pytest.mark.parametrize(
    "state",
    [
        EvidenceCompleteness.PARTIAL,
        EvidenceCompleteness.UNAVAILABLE,
        EvidenceCompleteness.CONFLICTING,
        EvidenceCompleteness.REDACTED,
        EvidenceCompleteness.DELETED_OR_TOMBSTONED,
    ],
)
def test_completeness_states_are_preserved_exactly(state: EvidenceCompleteness) -> None:
    value = bundle(completeness=state)
    card = project(value, missing_phase_reasons=FIXED_UNAVAILABLE)
    assert card.completeness is state
    assert json.loads(card.to_domain_json())["completeness"] == state.value


def test_tombstoned_bundle_keeps_tombstone_review_semantics() -> None:
    card = project(
        bundle(completeness=EvidenceCompleteness.DELETED_OR_TOMBSTONED),
        missing_phase_reasons=FIXED_UNAVAILABLE,
    )
    assert card.completeness is EvidenceCompleteness.DELETED_OR_TOMBSTONED
    assert card.completeness is not EvidenceCompleteness.COMPLETE
    assert card.to_domain_json()


def test_invalid_evidence_never_becomes_a_normal_review_card() -> None:
    with pytest.raises(ValueError, match="INVALID"):
        project(bundle(completeness=EvidenceCompleteness.INVALID))
    valid = project(bundle(), missing_phase_reasons=FIXED_UNAVAILABLE)
    with pytest.raises(ValueError, match="INVALID"):
        replace(valid, completeness=EvidenceCompleteness.INVALID)


def test_exact_bundle_integrity_state_is_preserved() -> None:
    supplied = verified("integrity:bundle:supplied")
    value = bundle(integrity_metadata=supplied)
    card = project(value, missing_phase_reasons=FIXED_UNAVAILABLE)
    assert card.integrity_state is EvidenceIntegrityState.VERIFIED
    assert card.integrity_state is supplied.state
    unverifiable = observed(EvidenceIntegrityState.UNVERIFIABLE)
    other = project(
        bundle(integrity_metadata=unverifiable),
        missing_phase_reasons=FIXED_UNAVAILABLE,
    )
    assert other.integrity_state is unverifiable.state


def test_verified_integrity_stays_verified() -> None:
    card = project(complete_bundle())
    assert card.integrity_state is EvidenceIntegrityState.VERIFIED


@pytest.mark.parametrize(
    "state",
    [
        EvidenceIntegrityState.UNVERIFIABLE,
        EvidenceIntegrityState.CORRUPT,
        EvidenceIntegrityState.TAMPERED,
        EvidenceIntegrityState.MISSING,
        EvidenceIntegrityState.DELETED,
    ],
)
def test_unverified_integrity_states_never_become_verified(
    state: EvidenceIntegrityState,
) -> None:
    metadata = observed(state)
    card = project(
        bundle(integrity_metadata=metadata),
        missing_phase_reasons=FIXED_UNAVAILABLE,
    )
    assert card.integrity_state is state
    assert card.integrity_state is not EvidenceIntegrityState.VERIFIED


def test_absent_bundle_integrity_is_represented_honestly() -> None:
    card = project(bundle(), missing_phase_reasons=FIXED_UNAVAILABLE)
    assert card.integrity_state is None
    assert json.loads(card.to_domain_json())["integrity_state"] is None


def test_unverified_evidence_is_never_labelled_verified() -> None:
    card = project(
        bundle(integrity_metadata=observed(EvidenceIntegrityState.UNVERIFIABLE)),
        missing_phase_reasons=FIXED_UNAVAILABLE,
    )
    assert '"VERIFIED"' not in card.to_domain_json()


def test_unexecuted_candidate_is_never_execution_backed_success() -> None:
    card = project(bundle(), missing_phase_reasons=FIXED_UNAVAILABLE)
    assert all(
        summary.outcome is not ExecutionOutcome.SUCCESS
        for summary in card.execution_summaries
    )
    assert all(summary.outcome is None for summary in card.execution_summaries)
    assert '"SUCCESS"' not in card.to_domain_json()
    assert '"PASSED"' not in card.to_domain_json()


def test_card_existence_does_not_imply_execution_success() -> None:
    card = project(
        bundle(completeness=EvidenceCompleteness.UNAVAILABLE),
        missing_phase_reasons=FIXED_UNAVAILABLE,
    )
    assert isinstance(card, EvidenceCard)
    assert card.completeness is EvidenceCompleteness.UNAVAILABLE
    assert all(summary.outcome is None for summary in card.execution_summaries)


def test_complete_does_not_imply_workflow_success() -> None:
    failing_buggy = buggy_record(
        outcome=ExecutionOutcome.TEST_FAILURE,
        failure=FailureEvidence(
            FailureCategory.TEST_FAILURE,
            OpaqueReference("failure-ref:buggy-test:complete"),
        ),
        test_result=ExecutionTestResult(
            executed_count=1,
            failed_count=1,
            test_cases=(failed_case(),),
        ),
    )
    card = project(
        complete_bundle(
            execution_evidence=[compile_record(), failing_buggy],
        ),
        missing_phase_reasons=FIXED_UNAVAILABLE,
    )
    assert card.completeness is EvidenceCompleteness.COMPLETE
    buggy_summary = card.phase_summaries_by_phase[
        ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST
    ]
    assert buggy_summary.outcome is ExecutionOutcome.TEST_FAILURE
    for forbidden in ("transition", "authorize", "approve", "run_state", "advance"):
        assert not hasattr(card, forbidden), forbidden


def test_logical_artefact_references_are_preserved() -> None:
    supplied_manifest = finalized_manifest()
    records = [compile_record(), buggy_record(), fixed_record()]
    value = bundle_values(
        target_reference_revision=OpaqueReference(FIXED_REVISION),
        execution_evidence=records,
        artefact_manifest=supplied_manifest,
    )
    bundle_instance = EvidenceBundle(**value)  # type: ignore[arg-type]
    card = project(bundle_instance)
    expected = {
        "artefact:manifest:1",
        "artefact:manifest:2",
        "artefact:compile-stdout:1",
        "artefact:compile-stderr:1",
        "artefact:buggy-stdout:1",
        "artefact:buggy-stderr:1",
        "artefact:fixed-stdout:1",
        "artefact:fixed-stderr:1",
    }
    assert {reference.artefact_id.value for reference in card.artefact_references} == (
        expected
    )
    by_identity = {
        reference.artefact_id.value: reference for reference in card.artefact_references
    }
    assert by_identity["artefact:compile-stdout:1"] is records[0].stdout_artefact
    manifest_reference = next(
        reference
        for reference in supplied_manifest.artefact_references
        if reference.artefact_id.value == "artefact:manifest:1"
    )
    assert by_identity["artefact:manifest:1"] is manifest_reference
    assert isinstance(card.artefact_references, tuple)


def test_identical_duplicate_artefact_references_converge() -> None:
    duplicated = artefact("artefact:twin:1", ArtefactType.TEST_STDOUT)
    card = manual_card(artefact_references=[duplicated, replace(duplicated)])
    twins = [
        reference
        for reference in card.artefact_references
        if reference.artefact_id.value == "artefact:twin:1"
    ]
    assert len(twins) == 1
    assert twins[0] == duplicated


def test_conflicting_duplicate_artefact_identity_fails_closed() -> None:
    first = artefact("artefact:clash:1", ArtefactType.TEST_STDOUT)
    second = replace(first, content_digest=OpaqueReference("digest:changed"))
    with pytest.raises(ValueError, match="conflicting duplicate logical artefact"):
        manual_card(artefact_references=[first, second])


def test_artefact_references_remain_immutable() -> None:
    card = project(aggregate_bundle())
    with pytest.raises(FrozenInstanceError):
        card.artefact_references = ()  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        card.artefact_references[0].byte_size = 1  # type: ignore[misc]


def test_no_signed_url_generation_or_locator_transformation() -> None:
    card = project(aggregate_bundle(artefact_manifest=finalized_manifest()))
    for owner in (card_module, EvidenceCard, EvidenceCardContext, EvidenceCardPhaseSummary):
        for member in ("presign", "sign_url", "signed_url", "download_url", "url_for"):
            assert not hasattr(owner, member), member
    for reference in card.artefact_references:
        assert reference.storage_locator.startswith("locator:")
        assert not reference.storage_locator.startswith(("http://", "https://", "s3://"))
        assert reference.storage_locator == f"locator:{reference.artefact_id.value}"


def test_confidence_absence_is_preserved() -> None:
    card = project(bundle(), missing_phase_reasons=FIXED_UNAVAILABLE)
    assert card.confidence_reference is None
    assert json.loads(card.to_domain_json())["confidence_reference"] is None


def test_confidence_reference_is_preserved_opaquely() -> None:
    supplied = OpaqueReference("confidence-assessment:external:v1")
    card = project(
        bundle(),
        confidence_reference=supplied,
        missing_phase_reasons=FIXED_UNAVAILABLE,
    )
    assert card.confidence_reference is supplied
    assert card.confidence_reference.value == "confidence-assessment:external:v1"


def test_no_numeric_confidence_scale_is_invented() -> None:
    with pytest.raises(TypeError, match="OpaqueReference"):
        project(bundle(), confidence_reference=0.87, missing_phase_reasons=FIXED_UNAVAILABLE)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="OpaqueReference"):
        project(bundle(), confidence_reference=87, missing_phase_reasons=FIXED_UNAVAILABLE)  # type: ignore[arg-type]
    card_field_names = {field.name for field in fields(EvidenceCard)}
    for invented in (
        "confidence_score",
        "probability",
        "percent_confidence",
        "confidence_scale",
    ):
        assert invented not in card_field_names, invented
    source = inspect.getsource(card_module)
    assert "high/medium/low" not in source


def test_confidence_metadata_does_not_imply_proof() -> None:
    card = project(
        bundle(completeness=EvidenceCompleteness.UNAVAILABLE),
        confidence_reference=OpaqueReference("confidence-assessment:opaque:1"),
        uncertainty_flag=True,
        uncertainty_category=OpaqueReference("uncertainty-category:opaque:v1"),
        assessment_producer=OpaqueReference("assessment-producer:model-x"),
        calibration_metadata=OpaqueReference("calibration:methodology-v1"),
        missing_phase_reasons=FIXED_UNAVAILABLE,
    )
    assert card.completeness is EvidenceCompleteness.UNAVAILABLE
    assert card.integrity_state is None
    assert all(summary.outcome is None for summary in card.execution_summaries)
    serialized = card.to_domain_json()
    assert '"VERIFIED"' not in serialized
    assert '"COMPLETE"' not in serialized
    for forbidden in ("transition", "authorize", "progress", "promote"):
        assert not hasattr(card, forbidden), forbidden


def test_uncertainty_flag_is_preserved_exactly() -> None:
    assert (
        project(bundle(), missing_phase_reasons=FIXED_UNAVAILABLE).uncertainty_flag
        is False
    )
    flagged = project(
        bundle(), uncertainty_flag=True, missing_phase_reasons=FIXED_UNAVAILABLE
    )
    assert flagged.uncertainty_flag is True
    with pytest.raises(TypeError, match="bool"):
        manual_card(uncertainty_flag="yes")  # type: ignore[arg-type]


def test_uncertainty_category_is_preserved_verbatim() -> None:
    supplied = OpaqueReference("uncertainty-category:team-local:v7")
    card = project(
        bundle(),
        uncertainty_category=supplied,
        missing_phase_reasons=FIXED_UNAVAILABLE,
    )
    assert card.uncertainty_category is supplied
    assert card.uncertainty_category.value == "uncertainty-category:team-local:v7"


def test_no_frozen_uncertainty_taxonomy_enum_is_created() -> None:
    source = inspect.getsource(card_module)
    for example in UNCERTAINTY_NON_NORMATIVE_EXAMPLES:
        assert example not in source, example
    enum_classes = [
        name
        for name, member in vars(card_module).items()
        if isinstance(member, type)
        and issubclass(member, Enum)
        and member.__module__ == card_module.__name__
    ]
    assert enum_classes == []


def test_assessment_producer_and_calibration_metadata_are_preserved() -> None:
    producer = OpaqueReference("assessment-producer:component-y")
    calibration = OpaqueReference("calibration:model-z-methodology-v2")
    card = project(
        bundle(),
        assessment_producer=producer,
        calibration_metadata=calibration,
        missing_phase_reasons=FIXED_UNAVAILABLE,
    )
    assert card.assessment_producer is producer
    assert card.calibration_metadata is calibration
    assert project(bundle(), missing_phase_reasons=FIXED_UNAVAILABLE).assessment_producer is None
    assert project(bundle(), missing_phase_reasons=FIXED_UNAVAILABLE).calibration_metadata is None


def test_candidate_patch_and_version_ids_are_preserved_exactly() -> None:
    patch_id = CandidatePatchId("patch:caller-supplied")
    version_id = CandidateVersionId("candidate-version:caller-supplied")
    value = bundle(candidate_patch_id=patch_id, candidate_version_id=version_id)
    card = project(value, missing_phase_reasons=FIXED_UNAVAILABLE)
    assert card.candidate_patch_id is patch_id
    assert card.candidate_version_id is version_id
    assert type(card.candidate_patch_id) is CandidatePatchId
    assert type(card.candidate_version_id) is CandidateVersionId


def test_no_candidate_lineage_is_synthesized() -> None:
    card = project(bundle(), missing_phase_reasons=FIXED_UNAVAILABLE)
    card_field_names = {field.name for field in fields(EvidenceCard)}
    context_field_names = {field.name for field in fields(EvidenceCardContext)}
    for synthesized in (
        "parent_candidate_version_id",
        "repair_level",
        "repair_attempts_used",
    ):
        assert synthesized not in card_field_names, synthesized
        assert synthesized not in context_field_names, synthesized
    assert not hasattr(card, "lineage")


def test_invocation_provenance_is_preserved() -> None:
    value = bundle(
        run_id=RunId("run:r-77"),
        run_request_id=OpaqueReference("run-request:rq-77"),
        workflow_attempt_id=WorkflowAttemptId("attempt:a-77"),
        workflow_step=OpaqueReference("workflow-step:s-77"),
        queue_message_id=QueueMessageId("queue-message:q-77"),
        queue_delivery_id=QueueDeliveryId("queue-delivery:d-77"),
        correlation_id=CorrelationId("correlation:k-77"),
        causation_id=OpaqueReference("causation:c-77"),
        claim_or_lease_id=OpaqueReference("claim-or-lease:lease-77"),
        publication_identity=OpaqueReference("publication:p-77"),
        human_decision_id=HumanDecisionId("human-decision:h-77"),
    )
    context = project(value, missing_phase_reasons=FIXED_UNAVAILABLE).review_context
    assert context.run_id == RunId("run:r-77")
    assert context.run_request_id.value == "run-request:rq-77"
    assert context.workflow_attempt_id == WorkflowAttemptId("attempt:a-77")
    assert context.workflow_step.value == "workflow-step:s-77"
    assert context.queue_message_id == QueueMessageId("queue-message:q-77")
    assert context.queue_delivery_id == QueueDeliveryId("queue-delivery:d-77")
    assert context.correlation_id == CorrelationId("correlation:k-77")
    assert context.causation_id.value == "causation:c-77"
    assert context.claim_or_lease_id.value == "claim-or-lease:lease-77"
    assert context.publication_identity.value == "publication:p-77"
    assert context.human_decision_id == HumanDecisionId("human-decision:h-77")
    absent = project(bundle(), missing_phase_reasons=FIXED_UNAVAILABLE).review_context
    assert absent.queue_message_id is None
    assert absent.queue_delivery_id is None
    assert absent.human_decision_id is None


def test_source_repository_and_revision_provenance_is_preserved() -> None:
    value = bundle(
        source_repository=OpaqueReference("repo:testgap/other"),
        source_revision=OpaqueReference("revision:buggy:zzz999"),
    )
    context = project(value, missing_phase_reasons=FIXED_UNAVAILABLE).review_context
    assert context.source_repository.value == "repo:testgap/other"
    assert context.source_revision.value == "revision:buggy:zzz999"


def test_target_reference_provenance_is_preserved_where_supplied() -> None:
    without_target = project(bundle(), missing_phase_reasons=FIXED_UNAVAILABLE)
    assert without_target.review_context.target_reference_revision is None
    supplied = OpaqueReference(FIXED_REVISION)
    with_target = project(
        bundle(target_reference_revision=supplied),
        missing_phase_reasons=FIXED_UNAVAILABLE,
    )
    assert with_target.review_context.target_reference_revision is supplied


def test_selected_context_manifest_provenance_is_preserved() -> None:
    supplied = OpaqueReference("context-manifest:v9")
    value = bundle(selected_context_manifest=supplied)
    card = project(value, missing_phase_reasons=FIXED_UNAVAILABLE)
    assert card.selected_files_manifest_summary is supplied
    assert card.review_context.selected_context_manifest is supplied
    assert isinstance(card.selected_files_manifest_summary, OpaqueReference)


def test_configuration_model_and_prompt_provenance_is_preserved() -> None:
    value = bundle(
        producer_id=OpaqueReference("producer:host-a"),
        runner_id=OpaqueReference("runner:instance-42"),
        configuration_version=OpaqueReference("configuration:rc-2"),
        model_identifier=OpaqueReference("model:gpt-x"),
        prompt_template_version=OpaqueReference("prompt-template:v12"),
        producer_schema_version=OpaqueReference("producer-schema:v3"),
    )
    context = project(value, missing_phase_reasons=FIXED_UNAVAILABLE).review_context
    assert context.producer_id.value == "producer:host-a"
    assert context.runner_id.value == "runner:instance-42"
    assert context.configuration_version.value == "configuration:rc-2"
    assert context.model_identifier.value == "model:gpt-x"
    assert context.prompt_template_version.value == "prompt-template:v12"
    assert context.producer_schema_version.value == "producer-schema:v3"


def test_ai_generated_flag_is_preserved_exactly() -> None:
    assert (
        project(bundle(), ai_generated=True, missing_phase_reasons=FIXED_UNAVAILABLE).ai_generated
        is True
    )
    assert (
        project(bundle(), ai_generated=False, missing_phase_reasons=FIXED_UNAVAILABLE).ai_generated
        is False
    )
    with pytest.raises(TypeError, match="ai_generated"):
        project(bundle(), ai_generated="true", missing_phase_reasons=FIXED_UNAVAILABLE)  # type: ignore[arg-type]


def test_human_review_required_flag_is_preserved_exactly() -> None:
    assert (
        project(
            bundle(),
            human_review_required=True,
            missing_phase_reasons=FIXED_UNAVAILABLE,
        ).human_review_required
        is True
    )
    assert (
        project(
            bundle(),
            human_review_required=False,
            missing_phase_reasons=FIXED_UNAVAILABLE,
        ).human_review_required
        is False
    )
    with pytest.raises(TypeError, match="human_review_required"):
        project(
            bundle(),
            human_review_required=1,  # type: ignore[arg-type]
            missing_phase_reasons=FIXED_UNAVAILABLE,
        )


def test_human_review_required_creates_no_human_decision() -> None:
    card = project(
        bundle(), human_review_required=True, missing_phase_reasons=FIXED_UNAVAILABLE
    )
    for forbidden in (
        "human_decision",
        "human_decision_link",
        "disposition",
        "human_actor_reference",
    ):
        assert not hasattr(card, forbidden), forbidden
    card_field_names = {field.name for field in fields(EvidenceCard)}
    context_field_names = {field.name for field in fields(EvidenceCardContext)}
    assert not card_field_names & {"disposition", "human_actor_reference"}
    assert not context_field_names & {"disposition", "human_actor_reference"}


def test_human_review_required_performs_no_workflow_transition() -> None:
    card = project(
        bundle(), human_review_required=True, missing_phase_reasons=FIXED_UNAVAILABLE
    )
    for forbidden in (
        "transition",
        "advance",
        "progress_run",
        "regenerate",
        "approve",
        "reject",
    ):
        assert not hasattr(card, forbidden), forbidden
        assert not hasattr(card_module, forbidden), forbidden


def test_governing_contract_version_is_exact_draft_three() -> None:
    card = project(bundle(), missing_phase_reasons=FIXED_UNAVAILABLE)
    assert card.governing_contract_version == "CONTRACT-EVIDENCE-001@1.0.0-draft.3"
    assert card.governing_contract_version == EVIDENCE_CONTRACT_VERSION


def test_wrong_governing_contract_version_is_rejected() -> None:
    base = project(bundle(), missing_phase_reasons=FIXED_UNAVAILABLE)
    for unsupported in (
        "CONTRACT-EVIDENCE-001@1.0.0-draft.2",
        "CONTRACT-EVIDENCE-001@1.0.0-draft.4",
        "CONTRACT-EVIDENCE-001@2.0.0",
    ):
        with pytest.raises(ValueError, match="unsupported"):
            manual_card(base, governing_contract_version=unsupported)


def test_new_card_exports_are_public() -> None:
    for name in CARD_EXPORTS:
        assert hasattr(app.evidence, name), name
        assert name in app.evidence.__all__, name


def test_evidence_006_through_010_exports_are_preserved() -> None:
    for name in LEGACY_EXPORTS:
        assert hasattr(app.evidence, name), name
        assert name in app.evidence.__all__, name


def test_evidence_card_id_is_not_aliased_to_foreign_identities() -> None:
    with pytest.raises(ValueError, match="distinct"):
        project(
            bundle(),
            evidence_card_id=card_id("bundle:1"),
            missing_phase_reasons=FIXED_UNAVAILABLE,
        )
    with pytest.raises(ValueError, match="distinct"):
        project(
            bundle(),
            evidence_card_id=card_id("patch:1"),
            missing_phase_reasons=FIXED_UNAVAILABLE,
        )
    with pytest.raises(ValueError, match="distinct"):
        project(
            bundle(),
            evidence_card_id=card_id("candidate-version:1"),
            missing_phase_reasons=FIXED_UNAVAILABLE,
        )
    with pytest.raises(ValueError, match="distinct"):
        project(
            bundle(),
            evidence_card_id=card_id("run:1"),
            missing_phase_reasons=FIXED_UNAVAILABLE,
        )
    with pytest.raises(ValueError, match="distinct"):
        project(
            bundle(),
            evidence_card_id=card_id("attempt:1"),
            missing_phase_reasons=FIXED_UNAVAILABLE,
        )
    with pytest.raises(ValueError, match="distinct"):
        project(
            bundle(queue_message_id=QueueMessageId("queue-message:same")),
            evidence_card_id=card_id("queue-message:same"),
            missing_phase_reasons=FIXED_UNAVAILABLE,
        )
    with pytest.raises(ValueError, match="distinct"):
        project(
            bundle(human_decision_id=HumanDecisionId("human-decision:same")),
            evidence_card_id=card_id("human-decision:same"),
            missing_phase_reasons=FIXED_UNAVAILABLE,
        )
    with pytest.raises(ValueError, match="distinct"):
        project(
            aggregate_bundle(),
            evidence_card_id=card_id("evidence:compile:1"),
        )
    with pytest.raises(ValueError, match="distinct"):
        project(
            aggregate_bundle(artefact_manifest=finalized_manifest()),
            evidence_card_id=card_id("artefact:manifest:1"),
        )


@pytest.mark.parametrize(
    "colliding",
    [
        "producer-result:compile:1",
        "producer-result:buggy-test:1",
        "producer-result:fixed-test:1",
    ],
)
def test_card_id_matching_producer_result_id_is_rejected(colliding: str) -> None:
    value = aggregate_bundle()
    included = {
        record.producer_result_id.value for record in value.execution_evidence
    }
    assert colliding in included
    with pytest.raises(ValueError, match="distinct"):
        project(value, evidence_card_id=card_id(colliding))


def test_card_id_matching_artefact_manifest_id_is_rejected() -> None:
    supplied = finalized_manifest()
    assert supplied.artefact_manifest_id == ArtefactManifestId("artefact-manifest:1")
    with pytest.raises(ValueError, match="distinct"):
        project(
            aggregate_bundle(artefact_manifest=supplied),
            evidence_card_id=card_id("artefact-manifest:1"),
        )


def test_distinct_producer_result_and_manifest_identities_remain_accepted() -> None:
    value = aggregate_bundle(artefact_manifest=finalized_manifest())
    card = project(
        value,
        evidence_card_id=card_id(),
        ai_generated=True,
        human_review_required=True,
    )
    assert card.evidence_card_id == EvidenceCardId(CARD_ID_VALUE)
    assert all(
        record.producer_result_id.value != CARD_ID_VALUE
        for record in value.execution_evidence
    )
    assert value.artefact_manifest is not None
    assert (
        value.artefact_manifest.artefact_manifest_id.value != CARD_ID_VALUE
    )


def test_projection_rejects_wrong_identity_and_bundle_types() -> None:
    with pytest.raises(TypeError, match="EvidenceCardId"):
        project(bundle(), evidence_card_id=EvidenceBundleId("evidence-card:wrong"))  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="bundle"):
        project_evidence_card(
            "not-a-bundle",  # type: ignore[arg-type]
            evidence_card_id=card_id(),
            ai_generated=True,
            human_review_required=True,
        )


def test_no_evidence_bundle_modification_api_is_added() -> None:
    for forbidden in ("to_card", "as_card", "project_card", "evidence_card"):
        assert not hasattr(EvidenceBundle, forbidden), forbidden
        assert not hasattr(bundle_module, forbidden), forbidden
    assert "to_card" not in vars(EvidenceBundle)
    source = inspect.getsource(bundle_module)
    assert "to_card" not in source
    assert "EvidenceCard(" not in source


def test_human_decision_is_exported_without_evidence_card_authority() -> None:
    assert app.evidence.HumanDecision is decision_module.HumanDecision
    assert app.evidence.HumanDecisionLink is decision_module.HumanDecisionLink
    assert not {field.name for field in fields(EvidenceCard)} & {
        "human_decision_id",
        "human_actor_reference",
        "decision_timestamp",
        "disposition",
    }


def test_no_runtime_component_behavior_is_exposed() -> None:
    owners = (
        card_module,
        EvidenceCard,
        EvidenceCardContext,
        EvidenceCardPhaseSummary,
    )
    for owner in owners:
        for member in FORBIDDEN_RUNTIME_MEMBERS:
            assert not hasattr(owner, member), f"{owner}.{member}"
    source = inspect.getsource(card_module)
    for token in FORBIDDEN_SOURCE_TOKENS:
        assert token not in source, token


def test_card_module_depends_only_on_standard_library_and_evidence_domain() -> None:
    tree = ast.parse(inspect.getsource(card_module))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    assert roots <= ALLOWED_CARD_IMPORT_ROOTS


HUMAN_DECISION_TEST_PATH = Path(__file__).with_name("test_human_decision_link.py")


def test_stale_evidence_card_absence_guard_is_removed() -> None:
    assert hasattr(app.evidence, "EvidenceCard")
    source = HUMAN_DECISION_TEST_PATH.read_text(encoding="utf-8")
    assert 'hasattr(evidence_domain, "EvidenceCard")' not in source


def test_human_decision_negative_absence_guard_is_removed() -> None:
    assert hasattr(app.evidence, "HumanDecision")
    source = HUMAN_DECISION_TEST_PATH.read_text(encoding="utf-8")
    assert 'assert not hasattr(evidence_domain, "HumanDecision")' not in source


def test_evidence_bundle_regression_remains_pass() -> None:
    existing = bundle()
    assert compare_evidence_bundles(existing, bundle()) is EvidenceComparison.EQUIVALENT
    moved = replace(existing, evidence_bundle_id=EvidenceBundleId("bundle:moved"))
    assert compare_evidence_bundles(existing, moved) is EvidenceComparison.DISTINCT_IDENTITY
    changed = replace(existing, workflow_step=OpaqueReference("workflow-step:changed"))
    assert compare_evidence_bundles(existing, changed) is EvidenceComparison.CONFLICTING
    assert not hasattr(HumanDecisionLink, "to_card")
