from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timedelta, timezone

import pytest

from app.evidence import (
    CandidateFinalizationState,
    CandidatePatch,
    CandidatePatchId,
    CandidateVersion,
    CandidateVersionId,
    ChangedFile,
    CorrelationId,
    EvidenceComparison,
    ExecutionEvidenceId,
    GenerationProvenance,
    OpaqueReference,
    ProducerResultId,
    QueueMessageId,
    RunId,
    WorkflowAttemptId,
    compare_candidate_patches,
    compare_candidate_versions,
    validate_candidate_lineage,
    validate_candidate_patch_version,
)


GENERATED_AT = datetime(2026, 8, 13, 8, 0, tzinfo=timezone.utc)
FINALIZED_AT = GENERATED_AT + timedelta(seconds=1)


def generation() -> GenerationProvenance:
    return GenerationProvenance(
        generator_reference=OpaqueReference("generator:testgap-workflow"),
        tool_version_reference=OpaqueReference("generator-version:1.2.3"),
        generated_at=GENERATED_AT,
    )


def changed_files() -> list[ChangedFile]:
    return [
        ChangedFile("tests/test_beta.py", "adds the regression assertion"),
        ChangedFile("tests/test_alpha.py", "adds the failing fixture"),
    ]


def candidate_patch(**changes: object) -> CandidatePatch:
    values: dict[str, object] = {
        "candidate_patch_id": CandidatePatchId("candidate-patch:0"),
        "candidate_version_id": CandidateVersionId("candidate-version:0"),
        "run_id": RunId("run:1"),
        "workflow_attempt_id": WorkflowAttemptId("attempt:1"),
        "source_repository": OpaqueReference("repository:example/project"),
        "source_revision": OpaqueReference("revision:buggy:abc123"),
        "target_reference_revision": OpaqueReference("revision:fixed:def456"),
        "patch_digest": OpaqueReference("patch-digest:supplied-value"),
        "digest_algorithm": OpaqueReference("digest-policy:security-approved"),
        "patch_content_reference": OpaqueReference("patch-content:logical-reference"),
        "test_only_scope": True,
        "test_only_scope_reference": OpaqueReference("validation:test-only:1"),
        "changed_files_manifest": changed_files(),
        "generation_provenance": generation(),
        "configuration_version": OpaqueReference("configuration:2026-08-13"),
        "model_identifier": OpaqueReference("model:provider-neutral:model-v1"),
        "prompt_template_version": OpaqueReference("prompt-template:testgen:v3"),
        "localisation_provenance_reference": OpaqueReference("localisation:result:1"),
        "correlation_id": CorrelationId("correlation:1"),
        "finalization_state": CandidateFinalizationState.FINALIZED,
        "finalized_at": FINALIZED_AT,
    }
    values.update(changes)
    return CandidatePatch(**values)  # type: ignore[arg-type]


def candidate_version(**changes: object) -> CandidateVersion:
    values: dict[str, object] = {
        "candidate_version_id": CandidateVersionId("candidate-version:0"),
        "candidate_patch_id": CandidatePatchId("candidate-patch:0"),
        "run_id": RunId("run:1"),
        "workflow_attempt_id": WorkflowAttemptId("attempt:1"),
        "repair_level": 0,
        "parent_candidate_version_id": None,
        "producer_result_id": None,
        "generation_provenance": generation(),
        "source_repository": OpaqueReference("repository:example/project"),
        "source_revision": OpaqueReference("revision:buggy:abc123"),
        "target_reference_revision": OpaqueReference("revision:fixed:def456"),
        "configuration_version": OpaqueReference("configuration:2026-08-13"),
        "model_identifier": OpaqueReference("model:provider-neutral:model-v1"),
        "prompt_template_version": OpaqueReference("prompt-template:testgen:v3"),
        "localisation_provenance_reference": OpaqueReference("localisation:result:1"),
        "correlation_id": CorrelationId("correlation:1"),
        "finalization_state": CandidateFinalizationState.FINALIZED,
        "finalized_at": FINALIZED_AT,
    }
    values.update(changes)
    return CandidateVersion(**values)  # type: ignore[arg-type]


def repaired_version(**changes: object) -> CandidateVersion:
    values: dict[str, object] = {
        "candidate_version_id": CandidateVersionId("candidate-version:1"),
        "candidate_patch_id": CandidatePatchId("candidate-patch:1"),
        "repair_level": 1,
        "parent_candidate_version_id": CandidateVersionId("candidate-version:0"),
    }
    values.update(changes)
    return candidate_version(**values)


def test_valid_initial_candidate_patch_preserves_supplied_facts() -> None:
    patch = candidate_patch()

    assert patch.candidate_patch_id == CandidatePatchId("candidate-patch:0")
    assert patch.candidate_version_id == CandidateVersionId("candidate-version:0")
    assert patch.test_only_scope is True
    assert patch.patch_digest.value == "patch-digest:supplied-value"
    assert patch.digest_algorithm.value == "digest-policy:security-approved"
    assert patch.patch_content_reference.value == "patch-content:logical-reference"
    assert patch.finalization_state is CandidateFinalizationState.FINALIZED


def test_valid_initial_candidate_version_is_finalized_before_execution() -> None:
    version = candidate_version()

    assert version.repair_level == 0
    assert version.parent_candidate_version_id is None
    assert version.producer_result_id is None
    assert version.finalization_state is CandidateFinalizationState.FINALIZED


def test_patch_and_version_context_agree() -> None:
    validate_candidate_patch_version(candidate_patch(), candidate_version())


def test_contradictory_patch_version_context_fails_closed() -> None:
    with pytest.raises(ValueError, match="source_revision"):
        validate_candidate_patch_version(
            candidate_patch(),
            candidate_version(source_revision=OpaqueReference("revision:different")),
        )


def test_initial_candidate_rejects_parent() -> None:
    with pytest.raises(ValueError, match="initial candidate must not have a parent"):
        candidate_version(
            parent_candidate_version_id=CandidateVersionId("candidate-version:parent")
        )


def test_valid_repaired_candidate_references_prior_version() -> None:
    initial = candidate_version()
    repaired = repaired_version()

    validate_candidate_lineage(initial, repaired)
    assert repaired.parent_candidate_version_id == initial.candidate_version_id
    assert repaired.candidate_patch_id != initial.candidate_patch_id
    assert repaired.candidate_version_id != initial.candidate_version_id


def test_repaired_candidate_requires_parent() -> None:
    with pytest.raises(ValueError, match="repaired candidate requires a parent"):
        candidate_version(repair_level=1, parent_candidate_version_id=None)


def test_candidate_version_rejects_self_parent() -> None:
    with pytest.raises(ValueError, match="must not be its own parent"):
        candidate_version(
            repair_level=1,
            parent_candidate_version_id=CandidateVersionId("candidate-version:0"),
        )


@pytest.mark.parametrize("repair_level", [-1, 2, True, False, 1.0, "1"])
def test_candidate_version_rejects_unsupported_repair_level(
    repair_level: object,
) -> None:
    with pytest.raises(ValueError, match="integer 0 or 1"):
        candidate_version(repair_level=repair_level)


def test_candidate_version_accepts_opaque_producer_result_when_supplied() -> None:
    version = candidate_version(producer_result_id=ProducerResultId("producer-result:1"))

    assert version.producer_result_id == ProducerResultId("producer-result:1")


def test_producer_result_is_neither_required_nor_synthesized() -> None:
    first = candidate_version()
    second = candidate_version()

    assert first.producer_result_id is None
    assert second.producer_result_id is None


def test_repair_creation_does_not_mutate_prior_version() -> None:
    initial = candidate_version()
    original = initial.to_domain_json()
    repaired = repaired_version()

    validate_candidate_lineage(initial, repaired)
    assert initial.to_domain_json() == original
    assert initial.repair_level == 0
    assert initial.parent_candidate_version_id is None


@pytest.mark.parametrize("identity", ["", "   "])
def test_empty_candidate_patch_identity_is_rejected(identity: str) -> None:
    with pytest.raises(ValueError, match="nonempty"):
        CandidatePatchId(identity)


@pytest.mark.parametrize("identity", ["", "   "])
def test_empty_candidate_version_identity_is_rejected(identity: str) -> None:
    with pytest.raises(ValueError, match="nonempty"):
        CandidateVersionId(identity)


def test_identity_types_are_not_interchangeable() -> None:
    assert CandidatePatchId("same") != CandidateVersionId("same")
    assert CandidatePatchId("same") != ExecutionEvidenceId("same")
    assert CandidatePatchId("same") != ProducerResultId("same")
    assert CandidatePatchId("same") != QueueMessageId("same")
    assert CandidateVersionId("same") != ExecutionEvidenceId("same")
    assert CandidateVersionId("same") != ProducerResultId("same")
    assert CandidateVersionId("same") != QueueMessageId("same")

    with pytest.raises(TypeError, match="candidate_patch_id"):
        candidate_patch(candidate_patch_id=QueueMessageId("queue-message:1"))
    with pytest.raises(TypeError, match="candidate_patch_id"):
        candidate_patch(candidate_patch_id=ExecutionEvidenceId("evidence:1"))
    with pytest.raises(TypeError, match="candidate_version_id"):
        candidate_version(candidate_version_id=ExecutionEvidenceId("evidence:1"))
    with pytest.raises(TypeError, match="candidate_patch_id"):
        candidate_version(candidate_patch_id=QueueMessageId("queue-message:1"))


@pytest.mark.parametrize(
    "changes",
    [
        {"candidate_patch_id": CandidatePatchId("candidate-version:0")},
        {"candidate_patch_id": CandidatePatchId("run:1")},
        {"candidate_patch_id": CandidatePatchId("attempt:1")},
        {"candidate_patch_id": CandidatePatchId("correlation:1")},
    ],
)
def test_candidate_patch_rejects_reused_related_identity_values(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ValueError, match="distinct from every related identity"):
        candidate_patch(**changes)


def test_candidate_version_rejects_reused_producer_result_identity_value() -> None:
    with pytest.raises(ValueError, match="distinct from every related identity"):
        candidate_version(
            producer_result_id=ProducerResultId("candidate-version:0")
        )


def test_changed_file_manifest_is_sorted_and_detached_from_input() -> None:
    supplied = changed_files()
    patch = candidate_patch(changed_files_manifest=supplied)
    supplied.clear()

    assert isinstance(patch.changed_files_manifest, tuple)
    assert [item.path for item in patch.changed_files_manifest] == [
        "tests/test_alpha.py",
        "tests/test_beta.py",
    ]


def test_duplicate_changed_file_path_fails_closed() -> None:
    with pytest.raises(ValueError, match="paths must be unique"):
        candidate_patch(
            changed_files_manifest=(
                ChangedFile("tests/test_same.py", "first supplied fact"),
                ChangedFile("tests/test_same.py", "conflicting supplied fact"),
            )
        )


@pytest.mark.parametrize(
    "path",
    [
        "",
        "   ",
        " trailing.py ",
        "/absolute.py",
        "../escape.py",
        "tests//empty.py",
        "tests/./same.py",
        "bad\0.py",
    ],
)
def test_malformed_changed_file_paths_are_rejected(path: str) -> None:
    with pytest.raises(ValueError):
        ChangedFile(path, "summary")


def test_changed_file_values_are_bounded() -> None:
    with pytest.raises(ValueError, match="exceeds"):
        ChangedFile("tests/test.py", "x" * 16_385)


def test_changed_file_manifest_count_is_bounded() -> None:
    files = (
        ChangedFile(f"tests/generated/test_{index}.py", "supplied change")
        for index in range(4_097)
    )

    with pytest.raises(ValueError, match="exceeds 4096 entries"):
        candidate_patch(changed_files_manifest=files)


def test_manifest_reverse_order_has_identical_canonical_content() -> None:
    files = changed_files()
    first = candidate_patch(changed_files_manifest=files)
    second = candidate_patch(changed_files_manifest=reversed(files))

    assert first.changed_files_manifest == second.changed_files_manifest
    assert first.to_domain_json() == second.to_domain_json()
    assert compare_candidate_patches(first, second) is EvidenceComparison.EQUIVALENT


def test_same_patch_identity_with_changed_manifest_is_conflicting() -> None:
    existing = candidate_patch()
    changed = candidate_patch(
        changed_files_manifest=(
            ChangedFile("tests/test_alpha.py", "different supplied summary"),
            ChangedFile("tests/test_beta.py", "adds the regression assertion"),
        )
    )

    assert (
        compare_candidate_patches(existing, changed)
        is EvidenceComparison.CONFLICTING
    )


def test_candidate_patch_comparison_keeps_distinct_identities_independent() -> None:
    existing = candidate_patch()
    independent = replace(
        existing,
        candidate_patch_id=CandidatePatchId("candidate-patch:independent"),
    )

    assert (
        compare_candidate_patches(existing, independent)
        is EvidenceComparison.DISTINCT_IDENTITY
    )


def test_candidate_version_duplicate_converges_and_provenance_change_conflicts() -> None:
    existing = candidate_version()
    duplicate = candidate_version()
    changed = candidate_version(
        model_identifier=OpaqueReference("model:provider-neutral:different")
    )

    assert (
        compare_candidate_versions(existing, duplicate)
        is EvidenceComparison.EQUIVALENT
    )
    assert (
        compare_candidate_versions(existing, changed)
        is EvidenceComparison.CONFLICTING
    )


def test_candidate_version_comparison_keeps_distinct_identities_independent() -> None:
    existing = candidate_version()
    independent = candidate_version(
        candidate_version_id=CandidateVersionId("candidate-version:independent")
    )

    assert (
        compare_candidate_versions(existing, independent)
        is EvidenceComparison.DISTINCT_IDENTITY
    )


def test_provenance_is_provider_neutral_and_preserved_exactly() -> None:
    patch = candidate_patch()
    version = candidate_version()

    for value in (patch, version):
        assert value.source_repository.value == "repository:example/project"
        assert value.source_revision.value == "revision:buggy:abc123"
        assert value.target_reference_revision.value == "revision:fixed:def456"
        assert value.configuration_version.value == "configuration:2026-08-13"
        assert value.model_identifier.value == "model:provider-neutral:model-v1"
        assert value.prompt_template_version.value == "prompt-template:testgen:v3"
        assert value.localisation_provenance_reference.value == "localisation:result:1"


def test_localisation_provenance_is_optional_without_a_rag_schema() -> None:
    patch = candidate_patch(localisation_provenance_reference=None)
    version = candidate_version(localisation_provenance_reference=None)

    assert patch.localisation_provenance_reference is None
    assert version.localisation_provenance_reference is None


def test_test_only_fact_is_preserved_without_path_inference() -> None:
    patch = candidate_patch(test_only_scope=False)

    assert patch.test_only_scope is False
    assert patch.test_only_scope_reference.value == "validation:test-only:1"


def test_raw_patch_bytes_prompt_text_and_runtime_objects_are_not_required() -> None:
    patch_names = {field.name for field in fields(CandidatePatch)}
    version_names = {field.name for field in fields(CandidateVersion)}

    assert "patch_bytes" not in patch_names
    assert "prompt_text" not in patch_names | version_names
    assert "execution_evidence_id" not in version_names
    assert "queue_message_id" not in version_names
    assert "queue_delivery_id" not in version_names
    assert "database_id" not in version_names

    candidate_patch(patch_content_reference=None)
    candidate_version()


def test_candidate_and_nested_values_are_effectively_immutable() -> None:
    patch = candidate_patch()
    version = candidate_version()

    with pytest.raises(FrozenInstanceError):
        patch.test_only_scope = False  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        patch.changed_files_manifest[0].path = "changed.py"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        version.repair_level = 1  # type: ignore[misc]


def test_domain_dict_mutation_does_not_mutate_candidate() -> None:
    patch = candidate_patch()
    domain = patch.to_domain_dict()
    domain["changed_files_manifest"] = []

    assert len(patch.changed_files_manifest) == 2


def test_timezone_equivalent_provenance_serializes_identically() -> None:
    offset = timezone(timedelta(hours=5, minutes=30))
    equivalent_generation = replace(
        generation(), generated_at=GENERATED_AT.astimezone(offset)
    )
    first = candidate_version()
    second = candidate_version(generation_provenance=equivalent_generation)

    assert first.to_domain_json() == second.to_domain_json()


@pytest.mark.parametrize(
    ("state", "finalized_at", "message"),
    [
        (CandidateFinalizationState.CREATED, FINALIZED_AT, "must not have"),
        (CandidateFinalizationState.FINALIZED, None, "requires finalized_at"),
    ],
)
def test_contradictory_finalization_is_rejected(
    state: CandidateFinalizationState,
    finalized_at: datetime | None,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        candidate_version(finalization_state=state, finalized_at=finalized_at)


def test_created_candidate_without_finalization_timestamp_is_valid() -> None:
    patch = candidate_patch(
        finalization_state=CandidateFinalizationState.CREATED,
        finalized_at=None,
    )
    version = candidate_version(
        finalization_state=CandidateFinalizationState.CREATED,
        finalized_at=None,
    )

    assert patch.finalized_at is None
    assert version.finalized_at is None


def test_lineage_validator_rejects_reused_patch_identity() -> None:
    initial = candidate_version()
    repaired = repaired_version(candidate_patch_id=initial.candidate_patch_id)

    with pytest.raises(ValueError, match="distinct candidate_patch_id"):
        validate_candidate_lineage(initial, repaired)


def test_lineage_validator_rejects_wrong_parent_or_run() -> None:
    initial = candidate_version()
    wrong_parent = repaired_version(
        parent_candidate_version_id=CandidateVersionId("candidate-version:other")
    )
    wrong_run = repaired_version(run_id=RunId("run:other"))

    with pytest.raises(ValueError, match="does not identify"):
        validate_candidate_lineage(initial, wrong_parent)
    with pytest.raises(ValueError, match="originating run"):
        validate_candidate_lineage(initial, wrong_run)
