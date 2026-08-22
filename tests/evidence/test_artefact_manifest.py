"""Contract coverage for the canonical ArtefactReference and ArtefactManifest."""

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone

import pytest

import app.evidence as evidence_public
from app.evidence import (
    ARTEFACT_MANIFEST_CARDINALITY_BOUND,
    ARTEFACT_MANIFEST_SCHEMA_VERSION,
    EVIDENCE_CONTRACT_VERSION,
    ArtefactId,
    ArtefactManifest,
    ArtefactManifestFinalizationState,
    ArtefactManifestId,
    ArtefactReference,
    ArtefactType,
    CandidateVersionId,
    EvidenceAvailability,
    EvidenceComparison,
    EvidenceIntegrityState,
    ExecutionEvidenceId,
    ExecutionPhase,
    IntegrityMetadata,
    OpaqueReference,
    WorkflowAttemptId,
    compare_artefact_manifests,
    compare_artefact_references,
)
from app.evidence.execution import (
    ArtefactId as LegacyArtefactId,
    ArtefactReference as LegacyArtefactReference,
    ArtefactType as LegacyArtefactType,
)


CREATED_AT = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
FINALIZED_AT = CREATED_AT + timedelta(minutes=5)


def reference_kwargs(identity: str = "artefact:1") -> dict[str, object]:
    return {
        "artefact_id": ArtefactId(identity),
        "artefact_type": ArtefactType.TEST_STDOUT,
        "availability": EvidenceAvailability.AVAILABLE,
        "integrity": IntegrityMetadata(
            EvidenceIntegrityState.VERIFIED,
            OpaqueReference(f"integrity:{identity}"),
        ),
        "content_digest": OpaqueReference(f"digest:{identity}"),
        "digest_algorithm": OpaqueReference("digest-algorithm:configured"),
        "byte_size": 128,
        "media_type": "text/plain",
        "producer_id": OpaqueReference("producer:execution-runner"),
        "creation_timestamp": CREATED_AT,
        "storage_locator": f"locator:{identity}",
    }


def reference(identity: str = "artefact:1", **changes: object) -> ArtefactReference:
    values = reference_kwargs(identity)
    values.update(changes)
    return ArtefactReference(**values)  # type: ignore[arg-type]


def unverified_integrity(state: EvidenceIntegrityState) -> IntegrityMetadata:
    return IntegrityMetadata(state, OpaqueReference("integrity-observation:1"))


def manifest(
    manifest_id: str = "manifest:1",
    references: tuple[ArtefactReference, ...] | None = None,
    **changes: object,
) -> ArtefactManifest:
    members = references if references is not None else (
        reference("artefact:m:2"),
        reference("artefact:m:1"),
    )
    values: dict[str, object] = {
        "artefact_manifest_id": ArtefactManifestId(manifest_id),
        "artefact_references": members,
        "creation_timestamp": CREATED_AT,
        "finalization_state": ArtefactManifestFinalizationState.ASSEMBLING,
    }
    values.update(changes)
    return ArtefactManifest(**values)  # type: ignore[arg-type]


def finalized_overrides() -> dict[str, object]:
    return {
        "finalization_state": ArtefactManifestFinalizationState.FINALIZED,
        "producer_provenance_reference": OpaqueReference(
            "producer-result:manifest:1"
        ),
        "manifest_digest": OpaqueReference("manifest-digest:1"),
        "manifest_digest_algorithm": OpaqueReference("digest-algorithm:configured"),
        "integrity_metadata": unverified_integrity(
            EvidenceIntegrityState.UNVERIFIABLE
        ),
        "finalization_timestamp": FINALIZED_AT,
    }


def finalized_manifest(
    manifest_id: str = "manifest:1",
    references: tuple[ArtefactReference, ...] | None = None,
    **changes: object,
) -> ArtefactManifest:
    overrides = finalized_overrides()
    overrides.update(changes)
    return manifest(manifest_id, references, **overrides)


def test_single_canonical_artefactreference_implementation_is_shared() -> None:
    from app.evidence import ArtefactReference as PublicArtefactReference
    from app.evidence import ArtefactType as PublicArtefactType

    assert LegacyArtefactReference is PublicArtefactReference is ArtefactReference
    assert LegacyArtefactType is PublicArtefactType is ArtefactType
    assert LegacyArtefactId is ArtefactId


def test_durable_public_package_exports_remain_public() -> None:
    assert "EVIDENCE_CONTRACT_VERSION" in evidence_public.__all__
    for name in (
        "EVIDENCE_CONTRACT_VERSION",
        "ARTEFACT_MANIFEST_CARDINALITY_BOUND",
        "ARTEFACT_MANIFEST_SCHEMA_VERSION",
        "ArtefactId",
        "ArtefactManifest",
        "ArtefactManifestFinalizationState",
        "ArtefactManifestId",
        "ArtefactReference",
        "ArtefactType",
        "CandidatePatch",
        "CandidateVersion",
        "ExecutionEvidence",
        "EvidenceAvailability",
        "EvidenceCompleteness",
        "EvidenceIntegrityState",
        "HumanDecisionLink",
        "IntegrityMetadata",
        "OpaqueReference",
        "compare_artefact_manifests",
        "compare_artefact_references",
        "compare_candidate_patches",
        "compare_candidate_versions",
        "compare_execution_evidence",
        "compare_human_decision_links",
        "validate_candidate_lineage",
        "validate_candidate_patch_version",
    ):
        assert name in evidence_public.__all__
        assert getattr(evidence_public, name) is not None
    for name in evidence_public.__all__:
        assert hasattr(evidence_public, name)


def test_valid_complete_artefact_reference_retains_all_supplied_facts() -> None:
    artefact = reference(
        candidate_version_id=CandidateVersionId("candidate-version:1"),
        execution_evidence_id=ExecutionEvidenceId("evidence:test:1"),
        redaction_state=OpaqueReference("redaction-policy-ref:1"),
    )

    assert artefact.artefact_id == ArtefactId("artefact:1")
    assert artefact.artefact_type is ArtefactType.TEST_STDOUT
    assert artefact.availability_state is EvidenceAvailability.AVAILABLE
    assert artefact.integrity_state is EvidenceIntegrityState.VERIFIED
    assert artefact.content_digest == OpaqueReference("digest:artefact:1")
    assert artefact.digest_algorithm == OpaqueReference("digest-algorithm:configured")
    assert artefact.byte_size == 128
    assert artefact.media_type == "text/plain"
    assert artefact.producer_id == OpaqueReference("producer:execution-runner")
    assert artefact.creation_timestamp == CREATED_AT
    assert artefact.storage_locator == "locator:artefact:1"
    assert artefact.candidate_version_id == CandidateVersionId("candidate-version:1")
    assert artefact.execution_evidence_id == ExecutionEvidenceId("evidence:test:1")
    assert artefact.redaction_state == OpaqueReference("redaction-policy-ref:1")
    assert artefact.contract_version == EVIDENCE_CONTRACT_VERSION


def test_optional_linkages_default_to_none() -> None:
    artefact = reference()

    assert artefact.candidate_version_id is None
    assert artefact.execution_evidence_id is None
    assert artefact.redaction_state is None


@pytest.mark.parametrize("identity", ["", "   "])
def test_artefact_id_must_be_nonempty(identity: str) -> None:
    with pytest.raises(ValueError, match="nonempty string"):
        ArtefactId(identity)


@pytest.mark.parametrize(
    "locator",
    [
        "logs/stdout.txt",
        "/tmp/stdout.txt",
        r"logs\stdout.txt",
        "./stdout.txt",
        "../stdout.txt",
        "s3://bucket/item",
        "gs://bucket/item",
        "https://example.test/item",
        "file:///tmp/stdout.txt",
    ],
)
def test_artefact_identity_cannot_conflate_a_physical_locator(locator: str) -> None:
    with pytest.raises(ValueError, match="storage locator"):
        ArtefactId(locator)


@pytest.mark.parametrize(
    "identity",
    ["artefact:stdout:01", "artifact_01.test+v2@example", "A-1"],
)
def test_valid_opaque_artefact_ids(identity: str) -> None:
    assert ArtefactId(identity).value == identity


def test_exact_content_digest_value_is_preserved_without_normalization() -> None:
    exact_digest = "BgR0vA9f-UPPER_mixed=="

    artefact = reference(content_digest=OpaqueReference(exact_digest))

    assert artefact.content_digest.value == exact_digest


def test_digest_algorithm_is_represented_without_security_approval() -> None:
    approved_shaped = reference(digest_algorithm=OpaqueReference("sha-256"))
    unapproved_shaped = reference(digest_algorithm=OpaqueReference("unapproved-alg"))

    assert approved_shaped.digest_algorithm.value == "sha-256"
    assert unapproved_shaped.digest_algorithm.value == "unapproved-alg"


def test_byte_size_zero_is_accepted() -> None:
    assert reference(byte_size=0).byte_size == 0


@pytest.mark.parametrize("invalid", [-1, True, False, 1.5, "128"])
def test_invalid_byte_size_values_fail_closed(invalid: object) -> None:
    with pytest.raises(ValueError, match="byte_size"):
        reference(byte_size=invalid)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "media_type",
    ["text/plain", "application/json", "text/x-diff", "application/vnd.x+json"],
)
def test_valid_media_types_are_accepted(media_type: str) -> None:
    assert reference(media_type=media_type).media_type == media_type


@pytest.mark.parametrize(
    "invalid",
    ["", "   ", "nosubtype", "/json", "text/", "text plain", "text/plain\n"],
)
def test_invalid_media_types_fail_closed(invalid: str) -> None:
    with pytest.raises(ValueError, match="media_type"):
        reference(media_type=invalid)


def test_oversized_media_type_fails_closed() -> None:
    with pytest.raises(ValueError, match="255 bytes"):
        reference(media_type="text/" + "a" * 300)


def test_media_type_carries_no_content_safety_claim() -> None:
    artefact = reference(
        media_type="text/plain",
        byte_size=10**9,
        content_digest=OpaqueReference("opaque-unverified-blob-digest"),
    )

    assert artefact.media_type == "text/plain"
    assert artefact.byte_size == 10**9


def test_producer_provenance_is_preserved_opaquely() -> None:
    producer = OpaqueReference("producer:runner-host-a:job-42")

    assert reference(producer_id=producer).producer_id == producer


def test_optional_candidate_version_linkage_is_supported() -> None:
    linkage = CandidateVersionId("candidate-version:7")

    assert reference(candidate_version_id=linkage).candidate_version_id == linkage


def test_optional_execution_evidence_linkage_is_supported() -> None:
    linkage = ExecutionEvidenceId("evidence:test:7")

    assert reference(execution_evidence_id=linkage).execution_evidence_id == linkage


def test_timezone_aware_creation_timestamp_is_accepted() -> None:
    aware = datetime(2026, 8, 21, 14, 30, tzinfo=timezone(timedelta(hours=2)))

    assert reference(creation_timestamp=aware).creation_timestamp == aware


def test_naive_creation_timestamp_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        reference(creation_timestamp=datetime(2026, 8, 21, 12, 0))


def test_availability_and_integrity_are_orthogonal_dimensions() -> None:
    independent = reference(
        availability=EvidenceAvailability.AVAILABLE,
        integrity=unverified_integrity(EvidenceIntegrityState.CORRUPT),
    )
    verified_but_unreachable = reference(
        availability=EvidenceAvailability.UNAVAILABLE,
        integrity=IntegrityMetadata(
            EvidenceIntegrityState.VERIFIED,
            OpaqueReference("integrity:historical"),
        ),
    )
    expired_missing = reference(
        availability=EvidenceAvailability.EXPIRED,
        integrity=unverified_integrity(EvidenceIntegrityState.MISSING),
    )

    assert independent.availability is EvidenceAvailability.AVAILABLE
    assert independent.integrity_state is EvidenceIntegrityState.CORRUPT
    assert verified_but_unreachable.availability is EvidenceAvailability.UNAVAILABLE
    assert (
        verified_but_unreachable.integrity_state is EvidenceIntegrityState.VERIFIED
    )
    assert expired_missing.integrity_state is EvidenceIntegrityState.MISSING


def test_available_with_unverifiable_integrity_is_valid() -> None:
    artefact = reference(
        integrity=unverified_integrity(EvidenceIntegrityState.UNVERIFIABLE),
    )

    assert artefact.availability is EvidenceAvailability.AVAILABLE
    assert artefact.integrity_state is EvidenceIntegrityState.UNVERIFIABLE


def test_available_does_not_imply_verified() -> None:
    artefact = reference(
        integrity=unverified_integrity(EvidenceIntegrityState.TAMPERED),
    )

    assert artefact.availability_state is EvidenceAvailability.AVAILABLE
    assert artefact.integrity_state is not EvidenceIntegrityState.VERIFIED
    assert artefact.integrity_state is EvidenceIntegrityState.TAMPERED


def test_completed_deletion_combination_remains_valid() -> None:
    tombstone = reference(
        availability=EvidenceAvailability.DELETED_OR_TOMBSTONED,
        integrity=unverified_integrity(EvidenceIntegrityState.DELETED),
    )

    assert tombstone.availability_state is EvidenceAvailability.DELETED_OR_TOMBSTONED
    assert tombstone.integrity_state is EvidenceIntegrityState.DELETED


def test_redacted_availability_accepts_redaction_metadata_reference() -> None:
    redacted = reference(
        availability=EvidenceAvailability.REDACTED,
        redaction_state=OpaqueReference("redaction-policy-ref:redacted-run"),
    )

    assert redacted.redaction_state == OpaqueReference("redaction-policy-ref:redacted-run")


def test_storage_locator_must_differ_from_artefact_identity() -> None:
    with pytest.raises(ValueError, match="distinct from the artefact identity"):
        reference(identity="artefact:twin", storage_locator="artefact:twin")


@pytest.mark.parametrize(
    "locator",
    [
        "s3://bucket/key",
        "gs://bucket/key",
        "azure://container/blob",
        "file:///var/data/key",
        "https://cdn.example.test/key",
        "/var/data/key",
        "relative/path/key",
    ],
)
def test_storage_locator_is_opaque_provider_neutral_data(locator: str) -> None:
    assert reference(storage_locator=locator).storage_locator == locator


def test_empty_or_nul_storage_locator_fails_closed() -> None:
    with pytest.raises(ValueError, match="nonempty"):
        reference(storage_locator="   ")
    with pytest.raises(ValueError, match="NUL"):
        reference(storage_locator="locator\0x")


def test_serialization_is_deterministic_across_timezone_spellings() -> None:
    utc = reference()
    shifted = reference(
        creation_timestamp=datetime(
            2026, 8, 21, 14, 0, tzinfo=timezone(timedelta(hours=2))
        ),
    )

    assert utc.to_domain_json() == shifted.to_domain_json()
    assert '"creation_timestamp":"2026-08-21T12:00:00Z"' in utc.to_domain_json()


def test_domain_representation_is_immutable_and_stable() -> None:
    artefact = reference()

    snapshot = artefact.to_domain_dict()
    assert artefact.to_domain_json() == artefact.to_domain_json()
    snapshot["byte_size"] = 999
    assert artefact.byte_size == 128
    assert "byte_size" not in artefact.to_domain_dict() or (
        artefact.to_domain_dict()["byte_size"] == 128
    )
    with pytest.raises(FrozenInstanceError):
        artefact.byte_size = 999  # type: ignore[misc]


def test_constructor_never_synthesizes_an_identity() -> None:
    kwargs = reference_kwargs("artefact:synthetic")
    kwargs["artefact_id"] = "artefact:synthetic"

    with pytest.raises(TypeError, match="artefact_id"):
        ArtefactReference(**kwargs)  # type: ignore[arg-type]


def test_canonical_representation_uses_contract_state_field_names() -> None:
    artefact = reference(
        candidate_version_id=CandidateVersionId("candidate-version:1"),
        redaction_state=OpaqueReference("redaction-policy-ref:1"),
    )

    domain = artefact.to_domain_dict()

    assert set(domain) == {
        "artefact_id",
        "artefact_type",
        "availability_state",
        "integrity_state",
        "integrity_verification_reference",
        "content_digest",
        "digest_algorithm",
        "byte_size",
        "media_type",
        "producer_id",
        "creation_timestamp",
        "storage_locator",
        "candidate_version_id",
        "execution_evidence_id",
        "redaction_state",
        "contract_version",
    }
    assert domain["artefact_id"] == {"value": "artefact:1"}
    assert domain["artefact_type"] == "TEST_STDOUT"
    assert domain["availability_state"] == "AVAILABLE"
    assert domain["integrity_state"] == "VERIFIED"
    assert domain["integrity_verification_reference"] == {
        "value": "integrity:artefact:1"
    }
    assert domain["content_digest"] == {"value": "digest:artefact:1"}
    assert domain["byte_size"] == 128
    assert domain["creation_timestamp"] == "2026-08-21T12:00:00Z"
    assert "availability" not in domain
    assert "integrity" not in domain


def test_canonical_json_emits_contract_state_field_names() -> None:
    payload = reference(
        integrity=unverified_integrity(EvidenceIntegrityState.CORRUPT),
    ).to_domain_json()

    assert '"availability_state":"AVAILABLE"' in payload
    assert '"integrity_state":"CORRUPT"' in payload
    assert (
        '"integrity_verification_reference":{"value":"integrity-observation:1"}'
        in payload
    )
    assert '"availability"' not in payload
    assert '"integrity"' not in payload


def test_comparison_uses_the_corrected_canonical_representation() -> None:
    base = reference()
    same_states = replace(base)
    changed_verification_reference = replace(
        base,
        integrity=IntegrityMetadata(
            EvidenceIntegrityState.VERIFIED,
            OpaqueReference("integrity:different"),
        ),
    )
    changed_integrity_state = replace(
        base,
        integrity=unverified_integrity(EvidenceIntegrityState.CORRUPT),
    )
    changed_availability_state = replace(
        base,
        availability=EvidenceAvailability.UNAVAILABLE,
    )

    assert compare_artefact_references(base, same_states) is EvidenceComparison.EQUIVALENT
    assert (
        compare_artefact_references(base, changed_verification_reference)
        is EvidenceComparison.CONFLICTING
    )
    assert (
        compare_artefact_references(base, changed_integrity_state)
        is EvidenceComparison.CONFLICTING
    )
    assert (
        compare_artefact_references(base, changed_availability_state)
        is EvidenceComparison.CONFLICTING
    )


def test_manifest_canonical_representation_nests_contract_shaped_members() -> None:
    domain = finalized_manifest().to_domain_dict()
    members = domain["artefact_references"]

    assert isinstance(members, list)
    first = members[0]
    assert isinstance(first, dict)
    assert "availability_state" in first
    assert "integrity_state" in first
    assert "availability" not in first
    assert "integrity" not in first


def test_same_identity_and_same_content_converge() -> None:
    existing = reference()
    incoming = reference()

    assert compare_artefact_references(existing, incoming) is EvidenceComparison.EQUIVALENT


def test_same_identity_with_different_content_conflicts() -> None:
    existing = reference()
    incoming = replace(existing, content_digest=OpaqueReference("digest:different"))

    assert compare_artefact_references(existing, incoming) is EvidenceComparison.CONFLICTING
    assert existing.content_digest == OpaqueReference("digest:artefact:1")


def test_different_identity_is_distinct_even_with_equal_content() -> None:
    assert (
        compare_artefact_references(reference("artefact:a"), reference("artefact:b"))
        is EvidenceComparison.DISTINCT_IDENTITY
    )


@pytest.mark.parametrize(
    ("field", "kind"),
    [
        ("candidate_version_id", CandidateVersionId),
        ("execution_evidence_id", ExecutionEvidenceId),
    ],
)
def test_artefact_identity_does_not_absorb_other_identity_kinds(
    field: str,
    kind: type,
) -> None:
    with pytest.raises(ValueError, match="distinct from every related identity"):
        reference(**{field: kind("artefact:1")})


def test_verified_integrity_requires_verification_reference() -> None:
    with pytest.raises(ValueError, match="verification reference"):
        reference(integrity=IntegrityMetadata(EvidenceIntegrityState.VERIFIED))


def test_contract_version_is_enforced() -> None:
    with pytest.raises(ValueError, match="unsupported Evidence contract version"):
        reference(contract_version="CONTRACT-EVIDENCE-001@1.0.0-draft.2")


def test_all_contract_required_artefact_type_categories_exist() -> None:
    assert {category.value for category in ArtefactType} == {
        "CANDIDATE_PATCH",
        "COMPILE_LOG",
        "TEST_STDOUT",
        "TEST_STDERR",
        "EXECUTION_LOG",
        "CONTEXT_MANIFEST",
        "PUBLICATION_PAYLOAD",
        "CUSTOM_OUTPUT",
    }


def test_valid_assembling_manifest() -> None:
    assembled = manifest()

    assert assembled.finalization_state is ArtefactManifestFinalizationState.ASSEMBLING
    assert assembled.finalization_timestamp is None
    assert assembled.finalized is False
    assert [item.artefact_id.value for item in assembled.artefact_references] == [
        "artefact:m:1",
        "artefact:m:2",
    ]


def test_valid_finalized_manifest() -> None:
    finalized = finalized_manifest()

    assert finalized.finalized is True
    assert finalized.finalization_timestamp == FINALIZED_AT
    assert finalized.producer_provenance_reference == OpaqueReference(
        "producer-result:manifest:1"
    )
    assert finalized.manifest_digest == OpaqueReference("manifest-digest:1")
    assert finalized.manifest_digest_algorithm == OpaqueReference(
        "digest-algorithm:configured"
    )
    assert finalized.integrity_metadata is not None
    assert (
        finalized.integrity_metadata.state
        is EvidenceIntegrityState.UNVERIFIABLE
    )


def test_assembling_manifest_may_omit_final_metadata() -> None:
    assembled = manifest()

    assert assembled.finalization_state is ArtefactManifestFinalizationState.ASSEMBLING
    assert assembled.producer_provenance_reference is None
    assert assembled.manifest_digest is None
    assert assembled.manifest_digest_algorithm is None
    assert assembled.integrity_metadata is None
    assert assembled.finalization_timestamp is None


@pytest.mark.parametrize(
    ("missing_field", "expected_message"),
    [
        (
            "producer_provenance_reference",
            "FINALIZED manifest requires producer_provenance_reference",
        ),
        ("manifest_digest", "FINALIZED manifest requires manifest_digest"),
        (
            "manifest_digest_algorithm",
            "FINALIZED manifest requires manifest_digest_algorithm",
        ),
        ("integrity_metadata", "FINALIZED manifest requires integrity_metadata"),
        (
            "finalization_timestamp",
            "FINALIZED manifest requires finalization_timestamp",
        ),
    ],
)
def test_finalized_manifest_requires_each_final_metadata_value(
    missing_field: str,
    expected_message: str,
) -> None:
    with pytest.raises(ValueError, match=expected_message):
        finalized_manifest(**{missing_field: None})


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
def test_finalized_manifest_does_not_require_verified_integrity(
    state: EvidenceIntegrityState,
) -> None:
    finalized = finalized_manifest(integrity_metadata=unverified_integrity(state))

    assert finalized.finalized is True
    assert finalized.integrity_metadata is not None
    assert finalized.integrity_metadata.state is state


def test_manifest_membership_order_is_canonical_under_input_ordering() -> None:
    first = manifest(references=(reference("artefact:b"), reference("artefact:a")))
    second = manifest(references=(reference("artefact:a"), reference("artefact:b")))

    assert first.artefact_references == second.artefact_references
    assert first.to_domain_json() == second.to_domain_json()


def test_duplicate_member_artefact_identity_fails_closed() -> None:
    duplicate = reference("artefact:same")

    with pytest.raises(ValueError, match="duplicate artefact identities"):
        manifest(references=(duplicate, reference("artefact:same")))


def test_membership_input_collections_do_not_mutate_after_construction() -> None:
    members = [reference("artefact:list:1"), reference("artefact:list:2")]
    assembled = manifest(references=members)
    members.clear()

    assert len(assembled.artefact_references) == 2
    assert isinstance(assembled.artefact_references, tuple)


def test_unordered_membership_inputs_are_rejected() -> None:
    with pytest.raises(TypeError, match="ordered iterable"):
        manifest(references={reference("artefact:set:1")})  # type: ignore[arg-type]


def test_manifest_representation_is_immutable() -> None:
    finalized = finalized_manifest()

    with pytest.raises(FrozenInstanceError):
        finalized.finalization_state = (  # type: ignore[misc]
            ArtefactManifestFinalizationState.ASSEMBLING
        )
    with pytest.raises(FrozenInstanceError):
        finalized.artefact_references[0].byte_size = 1  # type: ignore[misc]


def test_optional_candidate_execution_and_workflow_linkage() -> None:
    linked = manifest(
        candidate_version_id=CandidateVersionId("candidate-version:1"),
        execution_evidence_id=ExecutionEvidenceId("evidence:test:1"),
        workflow_attempt_id=WorkflowAttemptId("attempt:1"),
        execution_phase=ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST,
    )

    assert linked.candidate_version_id == CandidateVersionId("candidate-version:1")
    assert linked.execution_evidence_id == ExecutionEvidenceId("evidence:test:1")
    assert linked.workflow_attempt_id == WorkflowAttemptId("attempt:1")
    assert linked.execution_phase is ExecutionPhase.BUGGY_OR_TARGET_REVISION_TEST


def test_producer_provenance_reference_is_preserved() -> None:
    provenance = OpaqueReference("producer-result:compile:1")

    assert manifest(producer_provenance_reference=provenance).producer_provenance_reference == provenance


def test_manifest_digest_metadata_requires_digest_and_algorithm() -> None:
    paired = manifest(
        manifest_digest=OpaqueReference("manifest-digest:1"),
        manifest_digest_algorithm=OpaqueReference("digest-algorithm:configured"),
    )
    assert paired.manifest_digest == OpaqueReference("manifest-digest:1")

    with pytest.raises(ValueError, match="digest and algorithm"):
        manifest(manifest_digest=OpaqueReference("manifest-digest:1"))
    with pytest.raises(ValueError, match="digest and algorithm"):
        manifest(manifest_digest_algorithm=OpaqueReference("digest-algorithm:configured"))


def test_integrity_metadata_is_independent_of_members_and_digests() -> None:
    empty_integrity = manifest(integrity_metadata=None)
    assert empty_integrity.integrity_metadata is None

    unverifiable = manifest(
        integrity_metadata=unverified_integrity(EvidenceIntegrityState.UNVERIFIABLE),
    )
    assert unverifiable.integrity_metadata is not None
    assert unverifiable.integrity_metadata.state is EvidenceIntegrityState.UNVERIFIABLE
    assert all(
        item.integrity_state is EvidenceIntegrityState.VERIFIED
        for item in unverifiable.artefact_references
    )


def test_manifest_creation_timestamp_must_be_aware() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        manifest(creation_timestamp=datetime(2026, 8, 21, 12, 0))


def test_finalization_timestamp_must_be_aware_when_supplied() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        finalized_manifest(finalization_timestamp=datetime(2026, 8, 21, 12, 5))


def test_assembling_manifest_cannot_carry_finalization_timestamp() -> None:
    with pytest.raises(ValueError, match="must not carry finalization_timestamp"):
        manifest(finalization_timestamp=FINALIZED_AT)


def test_finalized_manifest_requires_finalization_timestamp() -> None:
    with pytest.raises(ValueError, match="requires finalization_timestamp"):
        manifest(
            finalization_state=ArtefactManifestFinalizationState.FINALIZED,
            finalization_timestamp=None,
        )


def test_finalization_before_creation_is_rejected() -> None:
    with pytest.raises(ValueError, match="must not precede manifest creation"):
        finalized_manifest(finalization_timestamp=CREATED_AT - timedelta(seconds=1))


def test_finalization_at_creation_instant_is_allowed() -> None:
    boundary = finalized_manifest(finalization_timestamp=CREATED_AT)

    assert boundary.finalization_timestamp == CREATED_AT


def test_contract_version_is_enforced_on_manifests() -> None:
    with pytest.raises(ValueError, match="unsupported Evidence contract version"):
        manifest(contract_version="CONTRACT-EVIDENCE-001@1.0.0-draft.2")


def test_schema_version_is_enforced_and_distinct_from_the_contract() -> None:
    assert ARTEFACT_MANIFEST_SCHEMA_VERSION != EVIDENCE_CONTRACT_VERSION
    assert manifest().schema_version == ARTEFACT_MANIFEST_SCHEMA_VERSION

    with pytest.raises(ValueError, match="unsupported ArtefactManifest schema version"):
        manifest(schema_version="ARTEFACT-MANIFEST-SCHEMA-V0")


def test_manifest_identity_kinds_remain_separate_from_artefact_identity() -> None:
    assert ArtefactManifestId("shared") != ArtefactId("shared")

    with pytest.raises(
        ValueError,
        match="distinct from member artefact identities",
    ):
        manifest(manifest_id="artefact:m:1")


@pytest.mark.parametrize(
    "colliding_field",
    ["candidate_version_id", "execution_evidence_id", "workflow_attempt_id"],
)
def test_manifest_identity_does_not_absorb_related_identity_kinds(
    colliding_field: str,
) -> None:
    kinds = {
        "candidate_version_id": CandidateVersionId,
        "execution_evidence_id": ExecutionEvidenceId,
        "workflow_attempt_id": WorkflowAttemptId,
    }
    changes = {colliding_field: kinds[colliding_field]("manifest:1")}

    with pytest.raises(ValueError, match="distinct from every related identity"):
        manifest(**changes)


def test_equivalent_finalized_manifests_converge() -> None:
    existing = finalized_manifest()
    incoming = finalized_manifest()

    assert compare_artefact_manifests(existing, incoming) is EvidenceComparison.EQUIVALENT


def test_changed_finalized_membership_under_same_identity_conflicts() -> None:
    existing = finalized_manifest(
        references=(reference("artefact:f:1"), reference("artefact:f:2"))
    )
    changed = replace(
        existing,
        artefact_references=(reference("artefact:f:1"), reference("artefact:f:3")),
    )

    assert compare_artefact_manifests(existing, changed) is EvidenceComparison.CONFLICTING
    assert len(existing.artefact_references) == 2


def test_assembly_to_finalized_transition_is_a_content_change() -> None:
    assembling = manifest()
    finalized = replace(assembling, **finalized_overrides())

    assert assembling.finalized is False
    assert finalized.finalized is True
    assert compare_artefact_manifests(assembling, finalized) is EvidenceComparison.CONFLICTING


def test_distinct_manifest_ids_are_distinct_regardless_of_content() -> None:
    assert (
        compare_artefact_manifests(manifest("manifest:a"), manifest("manifest:b"))
        is EvidenceComparison.DISTINCT_IDENTITY
    )


def test_no_cardinality_bound_is_invented_for_manifests() -> None:
    members = tuple(reference(f"artefact:bulk:{index}") for index in range(500))

    bulk = manifest(references=members)

    assert len(bulk.artefact_references) == 500
    assert ARTEFACT_MANIFEST_CARDINALITY_BOUND == "CONFIGURATION_VALUE_NOT_YET_SELECTED"
    assert not hasattr(evidence_public, "MAX_ARTEFACTS_PER_MANIFEST")
