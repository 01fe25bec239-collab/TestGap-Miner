from dataclasses import FrozenInstanceError, fields, replace
import json

import pytest

import app.evidence as evidence_domain
import app.evidence.reference as reference_module
from app.evidence import (
    EVIDENCE_CONTRACT_VERSION,
    ArtefactId,
    ArtefactManifestId,
    CandidatePatchId,
    CandidateVersionId,
    CorrelationId,
    EvidenceBundleId,
    EvidenceCardId,
    EvidenceComparison,
    EvidenceReference,
    EvidenceReferenceId,
    ExecutionEvidenceId,
    HumanDecisionId,
    HumanDecisionLinkId,
    OpaqueReference,
    ProducerResultId,
    QueueDeliveryId,
    QueueMessageId,
    RunId,
    WorkflowAttemptId,
    compare_evidence_references,
)


SUPPORTED_TARGETS = [
    (EvidenceBundleId, "EVIDENCE_BUNDLE"),
    (EvidenceCardId, "EVIDENCE_CARD"),
    (ExecutionEvidenceId, "EXECUTION_EVIDENCE"),
    (ArtefactManifestId, "ARTEFACT_MANIFEST"),
    (ArtefactId, "ARTEFACT_REFERENCE"),
    (CandidateVersionId, "CANDIDATE_VERSION"),
]

RELATED_PROVENANCE_FIELDS = [
    ("run_id", RunId),
    ("workflow_attempt_id", WorkflowAttemptId),
    ("producer_result_id", ProducerResultId),
    ("queue_message_id", QueueMessageId),
    ("queue_delivery_id", QueueDeliveryId),
    ("correlation_id", CorrelationId),
]


def reference(**changes: object) -> EvidenceReference:
    values: dict[str, object] = {
        "evidence_reference_id": EvidenceReferenceId("evidence-reference:1"),
        "target": EvidenceBundleId("evidence-bundle:v1"),
        "run_id": None,
        "workflow_attempt_id": None,
        "producer_result_id": None,
        "queue_message_id": None,
        "queue_delivery_id": None,
        "correlation_id": None,
        "accepted_result_reference": None,
    }
    values.update(changes)
    return EvidenceReference(**values)  # type: ignore[arg-type]


def fully_provenanced() -> EvidenceReference:
    return reference(
        run_id=RunId("run:1"),
        workflow_attempt_id=WorkflowAttemptId("attempt:1"),
        producer_result_id=ProducerResultId("producer-result:1"),
        queue_message_id=QueueMessageId("queue-message:1"),
        queue_delivery_id=QueueDeliveryId("queue-delivery:1"),
        correlation_id=CorrelationId("correlation:1"),
        accepted_result_reference=OpaqueReference("accepted-result:opaque:1"),
    )


# A. ID construction


def test_valid_caller_supplied_reference_id_is_accepted() -> None:
    ref = reference(evidence_reference_id=EvidenceReferenceId("opaque-ref:abc"))

    assert isinstance(ref.evidence_reference_id, EvidenceReferenceId)
    assert ref.evidence_reference_id.value == "opaque-ref:abc"


@pytest.mark.parametrize("malformed", ["", "   ", "\t\n"])
def test_empty_or_whitespace_only_reference_id_is_rejected(
    malformed: str,
) -> None:
    with pytest.raises(ValueError, match="nonempty string"):
        EvidenceReferenceId(malformed)


def test_non_string_reference_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="nonempty string"):
        EvidenceReferenceId(7)  # type: ignore[arg-type]


def test_foreign_identity_cannot_substitute_for_reference_identity() -> None:
    with pytest.raises(TypeError, match="EvidenceReferenceId"):
        reference(evidence_reference_id=QueueMessageId("queue-message:1"))


# B. Type identity separation


@pytest.mark.parametrize(
    "foreign_type",
    [
        EvidenceBundleId,
        EvidenceCardId,
        ExecutionEvidenceId,
        ArtefactManifestId,
        ArtefactId,
        CandidateVersionId,
        WorkflowAttemptId,
        RunId,
        QueueMessageId,
        QueueDeliveryId,
        ProducerResultId,
        CorrelationId,
        HumanDecisionId,
        HumanDecisionLinkId,
        CandidatePatchId,
    ],
)
def test_reference_identity_is_distinct_from_every_other_namespace(
    foreign_type: type,
) -> None:
    same_text = "shared-text"

    assert EvidenceReferenceId(same_text) != foreign_type(same_text)
    assert foreign_type(same_text) != EvidenceReferenceId(same_text)


# C. Related-id collision


def test_reference_id_copying_bound_target_value_fails_closed() -> None:
    for target_type, _ in SUPPORTED_TARGETS:
        with pytest.raises(ValueError, match="distinct"):
            reference(
                evidence_reference_id=EvidenceReferenceId("shared-value"),
                target=target_type("shared-value"),
            )


@pytest.mark.parametrize(
    ("field_name", "identity_type"),
    [
        *RELATED_PROVENANCE_FIELDS,
        ("accepted_result_reference", None),
    ],
)
def test_reference_id_copying_related_provenance_fails_closed(
    field_name: str,
    identity_type: type | None,
) -> None:
    value = (
        OpaqueReference("shared-value")
        if identity_type is None
        else identity_type("shared-value")
    )
    collision: dict[str, object] = {field_name: value}

    with pytest.raises(ValueError, match="distinct|must not copy"):
        reference(
            evidence_reference_id=EvidenceReferenceId("shared-value"),
            **collision,
        )


def test_binding_with_colliding_provenance_does_not_mutate_the_supplied_ids() -> None:
    attempt = WorkflowAttemptId("shared-value")
    target = EvidenceCardId("evidence-card:v1")

    with pytest.raises(ValueError):
        reference(
            evidence_reference_id=EvidenceReferenceId("shared-value"),
            target=target,
            workflow_attempt_id=attempt,
        )

    assert attempt.value == "shared-value"
    assert target.value == "evidence-card:v1"


# D. Caller id preservation


def test_exact_caller_supplied_identity_object_is_retained() -> None:
    supplied = EvidenceReferenceId("caller-supplied:42")

    ref = reference(evidence_reference_id=supplied)

    assert ref.evidence_reference_id is supplied


def test_no_generated_identity_appears_for_repeated_construction() -> None:
    first = reference()
    second = reference()

    assert (
        first.evidence_reference_id
        == second.evidence_reference_id
        == EvidenceReferenceId("evidence-reference:1")
    )


# E. Each supported target


@pytest.mark.parametrize(("target_type", "expected_kind"), SUPPORTED_TARGETS)
def test_every_supported_target_binds_independently(
    target_type: type,
    expected_kind: str,
) -> None:
    target = target_type(f"{expected_kind.lower()}:identity")

    bound = reference(target=target)

    assert bound.target is target
    assert bound.target_kind == expected_kind
    assert bound.to_domain_dict()["target"] == {
        "kind": expected_kind,
        "value": f"{expected_kind.lower()}:identity",
    }


# F. Unsupported targets


def test_unsupported_target_types_fail_closed() -> None:
    unsupported = [
        CandidatePatchId("candidate-patch:1"),
        HumanDecisionId("human-decision:1"),
        HumanDecisionLinkId("human-decision-link:1"),
        QueueMessageId("queue-message:1"),
        "evidence-bundle:v1",
        OpaqueReference("evidence-bundle:v1"),
        EvidenceReferenceId("evidence-reference:nested"),
    ]

    for candidate in unsupported:
        with pytest.raises(TypeError, match="supported Evidence-owned target"):
            reference(target=candidate)


def test_unsupported_target_subclasses_fail_closed() -> None:
    class SpecialisedBundleId(EvidenceBundleId):
        pass

    with pytest.raises(TypeError, match="supported Evidence-owned target"):
        reference(target=SpecialisedBundleId("evidence-bundle:special"))


def test_candidate_patch_and_human_decision_namespaces_stay_outside_the_union() -> None:
    supported_types = set(reference_module._TARGET_KIND_BY_EXACT_TYPE)

    assert supported_types == {
        EvidenceBundleId,
        EvidenceCardId,
        ExecutionEvidenceId,
        ArtefactManifestId,
        ArtefactId,
        CandidateVersionId,
    }


# G. Target type distinction


def test_same_target_text_with_different_semantic_types_differ_canonically() -> None:
    bundle_bound = reference(target=EvidenceBundleId("shared-object:1"))
    card_bound = reference(target=EvidenceCardId("shared-object:1"))

    assert bundle_bound.to_domain_dict() != card_bound.to_domain_dict()
    assert bundle_bound.target_kind != card_bound.target_kind
    assert json.loads(bundle_bound.to_domain_json())["target"]["kind"] == (
        "EVIDENCE_BUNDLE"
    )
    assert json.loads(card_bound.to_domain_json())["target"]["kind"] == (
        "EVIDENCE_CARD"
    )


def test_same_reference_id_with_different_target_type_conflicts() -> None:
    existing = reference(target=EvidenceBundleId("shared-object:1"))
    incoming = reference(target=EvidenceCardId("shared-object:1"))

    assert (
        compare_evidence_references(existing, incoming)
        is EvidenceComparison.CONFLICTING
    )


# H. Duplicate convergence


def test_identical_bindings_under_one_reference_id_converge() -> None:
    existing = fully_provenanced()
    incoming = fully_provenanced()

    assert existing is not incoming
    assert (
        compare_evidence_references(existing, incoming)
        is EvidenceComparison.EQUIVALENT
    )


# I. Changed target


def test_same_reference_id_with_changed_target_conflicts() -> None:
    existing = reference(target=EvidenceBundleId("evidence-bundle:v1"))
    rebound = replace(
        existing,
        target=EvidenceBundleId("evidence-bundle:v2"),
    )

    assert (
        compare_evidence_references(existing, rebound)
        is EvidenceComparison.CONFLICTING
    )


# J. Changed provenance


@pytest.mark.parametrize(
    "change",
    [
        {"producer_result_id": ProducerResultId("producer-result:changed")},
        {"workflow_attempt_id": WorkflowAttemptId("attempt:changed")},
        {"run_id": RunId("run:changed")},
        {"queue_message_id": QueueMessageId("queue-message:changed")},
        {"queue_delivery_id": QueueDeliveryId("queue-delivery:changed")},
        {"correlation_id": CorrelationId("correlation:changed")},
        {"accepted_result_reference": OpaqueReference("accepted-result:changed")},
        {"producer_result_id": None},
    ],
)
def test_same_reference_id_with_changed_provenance_conflicts(
    change: dict[str, object],
) -> None:
    existing = fully_provenanced()
    changed = replace(existing, **change)  # type: ignore[arg-type]

    assert (
        compare_evidence_references(existing, changed)
        is EvidenceComparison.CONFLICTING
    )


# K. Different reference


def test_different_reference_ids_are_distinct_identities() -> None:
    existing = fully_provenanced()
    independent = replace(
        existing,
        evidence_reference_id=EvidenceReferenceId("evidence-reference:2"),
    )

    assert (
        compare_evidence_references(existing, independent)
        is EvidenceComparison.DISTINCT_IDENTITY
    )


# L. Determinism


def test_identical_semantic_inputs_serialize_identically() -> None:
    first = fully_provenanced()
    second = fully_provenanced()

    assert first.to_domain_dict() == second.to_domain_dict()
    assert first.to_domain_json() == second.to_domain_json()


def test_serialization_is_sorted_and_address_independent() -> None:
    domain_json = fully_provenanced().to_domain_json()
    parsed = json.loads(domain_json)

    assert domain_json == json.dumps(
        parsed,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    assert list(json.loads(domain_json)) == sorted(json.loads(domain_json))
    assert "contract_version" in parsed
    assert parsed["evidence_reference_id"] == {"value": "evidence-reference:1"}


# M. Immutability


def test_reference_is_effectively_immutable() -> None:
    ref = fully_provenanced()

    with pytest.raises(FrozenInstanceError):
        ref.target = EvidenceCardId("evidence-card:other")  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        ref.evidence_reference_id = EvidenceReferenceId("evidence-reference:x")  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        ref.producer_result_id = ProducerResultId("producer-result:other")  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        ref.evidence_reference_id.value = "mutated"  # type: ignore[misc]


def test_domain_dict_mutation_does_not_change_the_reference() -> None:
    ref = fully_provenanced()
    domain = ref.to_domain_dict()
    target_entry = domain["target"]
    assert isinstance(target_entry, dict)

    target_entry["value"] = "tampered"

    assert ref.target.value == "evidence-bundle:v1"


def test_no_rebinding_mutator_exists() -> None:
    surface = {name for name in dir(EvidenceReference) if not name.startswith("__")}
    field_names = {field.name for field in fields(EvidenceReference)}

    assert not surface & {"rebind", "update_target", "set_target"}
    assert not field_names & {"rebind", "update_target", "set_target"}


# N. Queue opacity


def test_queue_facing_surface_exposes_only_the_opaque_reference_id() -> None:
    ref = fully_provenanced()
    queue_value = ref.queue_reference_id

    assert queue_value is ref.evidence_reference_id
    assert isinstance(queue_value, EvidenceReferenceId)
    assert queue_value.value == "evidence-reference:1"
    assert queue_value is not ref.target
    assert not hasattr(queue_value, "target")
    assert not hasattr(queue_value, "target_kind")
    assert not hasattr(queue_value, "producer_result_id")
    assert not hasattr(queue_value, "accepted_result_reference")


def test_two_targets_sharing_text_expose_the_same_queue_face_only() -> None:
    bundle_bound = reference(target=EvidenceBundleId("shared-object:1"))
    card_bound = reference(
        evidence_reference_id=bundle_bound.evidence_reference_id,
        target=EvidenceCardId("shared-object:1"),
    )

    assert (
        bundle_bound.queue_reference_id.value
        == card_bound.queue_reference_id.value
    )
    assert bundle_bound.target_kind != card_bound.target_kind


# O. Hash does not imply authenticity


DIGEST_LIKE = OpaqueReference(
    "sha-256-looking-opaque:3a7bd3e2360a3d29eea436fcfb7e44c735d117c42d1c1835420b6b9942af4cb3"
)


def test_digest_like_provenance_remains_merely_an_opaque_value() -> None:
    ref = reference(accepted_result_reference=DIGEST_LIKE)

    assert ref.accepted_result_reference is DIGEST_LIKE
    names = {field.name for field in fields(EvidenceReference)}
    names.update(name for name in dir(EvidenceReference) if not name.startswith("__"))

    assert not names & {
        "authenticated",
        "is_authenticated",
        "trusted",
        "verified_producer",
        "is_verified",
        "authorized",
        "is_authorized",
        "integrity_state",
        "digest_algorithm",
    }


def test_digest_like_provenance_grants_no_comparison_privileges() -> None:
    plain = reference(accepted_result_reference=OpaqueReference("plain-ref:1"))
    digested = reference(accepted_result_reference=DIGEST_LIKE)

    assert (
        compare_evidence_references(plain, digested)
        is EvidenceComparison.CONFLICTING
    )


def test_reference_module_selects_no_crypto_or_generation_utilities() -> None:
    module_names = set(dir(reference_module))

    assert not module_names & {
        "hashlib",
        "hmac",
        "sha256",
        "sha512",
        "uuid",
        "random",
        "secrets",
        "time",
    }


def test_no_invented_evidence_local_numeric_provenance_bound_is_enforced() -> None:
    supplied = OpaqueReference("accepted-result:opaque:" + "x" * 20_000)

    ref = reference(accepted_result_reference=supplied)

    assert ref.accepted_result_reference is supplied
    bound = ref.accepted_result_reference
    assert isinstance(bound, OpaqueReference)
    assert bound.value == supplied.value
    assert len(bound.value.encode("utf-8")) > 16_384
    assert not set(dir(reference_module)) & {
        "MAX_ACCEPTED_RESULT_REFERENCE_BYTES",
        "MAX_REFERENCE_BYTES",
        "MAX_PROVENANCE_BYTES",
        "MAX_EVIDENCE_REFERENCE_BYTES",
    }


# P. Contract version


def test_governing_contract_version_defaults_to_the_consumed_draft() -> None:
    ref = reference()

    assert ref.contract_version == "CONTRACT-EVIDENCE-001@1.0.0-draft.3"
    assert ref.contract_version == EVIDENCE_CONTRACT_VERSION


def test_explicit_correct_contract_version_is_accepted() -> None:
    ref = reference(contract_version="CONTRACT-EVIDENCE-001@1.0.0-draft.3")

    assert ref.contract_version == EVIDENCE_CONTRACT_VERSION


def test_wrong_contract_version_fails_closed() -> None:
    with pytest.raises(ValueError, match="unsupported Evidence contract version"):
        reference(contract_version="CONTRACT-EVIDENCE-001@2.0.0")


# Q. No internal generation


def test_identity_never_generated_by_the_domain_module() -> None:
    supplied = EvidenceReferenceId("stable-caller-supplied:id")
    constructed = [reference(evidence_reference_id=supplied) for _ in range(8)]

    assert all(bound.evidence_reference_id is supplied for bound in constructed)
    assert not set(dir(reference_module)) & {"uuid", "random", "secrets", "time"}


# R. Input immutability


def test_construction_and_comparison_preserve_supplied_inputs_exactly() -> None:
    ref_id = EvidenceReferenceId("evidence-reference:r")
    target = EvidenceBundleId("evidence-bundle:v1")
    producer_result = ProducerResultId("producer-result:p")
    accepted = OpaqueReference("accepted-result:a")
    before = (
        ref_id.value,
        target.value,
        producer_result.value,
        accepted.value,
    )

    existing = reference(
        evidence_reference_id=ref_id,
        target=target,
        producer_result_id=producer_result,
        accepted_result_reference=accepted,
    )
    _ = existing.to_domain_dict()
    _ = existing.to_domain_json()
    _ = compare_evidence_references(existing, existing)

    assert (
        ref_id.value,
        target.value,
        producer_result.value,
        accepted.value,
    ) == before
    assert existing.run_id is None
    assert existing.workflow_attempt_id is None


def test_field_shape_is_the_smallest_required_binding() -> None:
    field_names = tuple(field.name for field in fields(EvidenceReference))

    assert field_names == (
        "evidence_reference_id",
        "target",
        "run_id",
        "workflow_attempt_id",
        "producer_result_id",
        "queue_message_id",
        "queue_delivery_id",
        "correlation_id",
        "accepted_result_reference",
        "contract_version",
    )


def test_public_exports_expose_the_new_domain_surface() -> None:
    assert evidence_domain.EvidenceReferenceId is EvidenceReferenceId
    assert evidence_domain.EvidenceReference is EvidenceReference
    assert (
        evidence_domain.compare_evidence_references
        is compare_evidence_references
    )


def test_construction_requires_no_database_queue_workflow_or_storage_runtime() -> None:
    ref = reference()

    assert ref.queue_reference_id.value == "evidence-reference:1"
    assert not hasattr(reference_module, "sqlalchemy")
    assert not hasattr(reference_module, "alembic")
