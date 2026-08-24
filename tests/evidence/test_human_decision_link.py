from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timedelta, timezone
import json

import pytest

import app.evidence as evidence_domain
from app.evidence import (
    EVIDENCE_CONTRACT_VERSION,
    CandidatePatchId,
    CandidateVersionId,
    DecisionDisposition,
    EvidenceBundleId,
    EvidenceCardId,
    EvidenceComparison,
    ExecutionEvidenceId,
    HumanDecisionId,
    HumanDecisionLink,
    HumanDecisionLinkId,
    OpaqueReference,
    QueueDeliveryId,
    QueueMessageId,
    RunId,
    WorkflowAttemptId,
    compare_human_decision_links,
)


DECIDED_AT = datetime(2026, 8, 14, 9, 30, tzinfo=timezone.utc)
MAX_REFERENCE_BYTES = 16_384


def decision_link(**changes: object) -> HumanDecisionLink:
    values: dict[str, object] = {
        "human_decision_link_id": HumanDecisionLinkId("decision-link:1"),
        "human_decision_id": HumanDecisionId("human-decision:1"),
        "reviewed_evidence_bundle_id": EvidenceBundleId("evidence-bundle:v3"),
        "reviewed_evidence_card_id": EvidenceCardId("evidence-card:v3"),
        "human_actor_reference": OpaqueReference("auth-human:provider:subject-123"),
        "decision_timestamp": DECIDED_AT,
        "disposition": DecisionDisposition.APPROVED,
        "rationale_reference": None,
        "workflow_event_or_result_reference": OpaqueReference(
            "workflow-event:review-recorded:1"
        ),
        "regeneration_child_run_reference": None,
    }
    values.update(changes)
    return HumanDecisionLink(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "disposition",
    [
        DecisionDisposition.APPROVED,
        DecisionDisposition.REJECTED,
        DecisionDisposition.DISMISSED,
        DecisionDisposition.OUT_OF_SCOPE,
        DecisionDisposition.REGENERATION_REQUESTED,
    ],
)
def test_exact_disposition_vocabulary_constructs_valid_links(
    disposition: DecisionDisposition,
) -> None:
    child_run = (
        RunId("run:regeneration-child:1")
        if disposition is DecisionDisposition.REGENERATION_REQUESTED
        else None
    )

    link = decision_link(
        disposition=disposition,
        regeneration_child_run_reference=child_run,
    )

    assert link.disposition is disposition
    assert link.regeneration_child_run_reference == child_run


def test_typed_identities_and_exact_reviewed_versions_are_preserved() -> None:
    link = decision_link()

    assert link.human_decision_link_id == HumanDecisionLinkId("decision-link:1")
    assert link.human_decision_id == HumanDecisionId("human-decision:1")
    assert link.human_decision_link_id != link.human_decision_id
    assert link.reviewed_evidence_bundle_id == EvidenceBundleId("evidence-bundle:v3")
    assert link.reviewed_evidence_card_id == EvidenceCardId("evidence-card:v3")


def test_human_actor_reference_is_preserved_without_parsing() -> None:
    opaque = OpaqueReference("service-looking-value:machine:installation-7")

    link = decision_link(human_actor_reference=opaque)

    assert link.human_actor_reference is opaque
    assert link.human_actor_reference.value == opaque.value


def test_blank_opaque_actor_reference_is_rejected() -> None:
    with pytest.raises(ValueError, match="nonempty"):
        OpaqueReference("   ")


def test_oversized_actor_reference_is_rejected() -> None:
    with pytest.raises(ValueError, match="human_actor_reference exceeds"):
        decision_link(
            human_actor_reference=OpaqueReference("x" * (MAX_REFERENCE_BYTES + 1))
        )


def test_actor_reference_requires_the_opaque_reference_type() -> None:
    with pytest.raises(TypeError, match="human_actor_reference"):
        decision_link(human_actor_reference="auth-human:1")


def test_timezone_aware_decision_timestamp_is_preserved() -> None:
    assert decision_link().decision_timestamp is DECIDED_AT


def test_naive_decision_timestamp_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        decision_link(decision_timestamp=datetime(2026, 8, 14, 9, 30))


def test_non_datetime_decision_timestamp_is_rejected() -> None:
    with pytest.raises(TypeError, match="must be a datetime"):
        decision_link(decision_timestamp="2026-08-14T09:30:00Z")


def test_disposition_outside_the_exact_vocabulary_is_rejected() -> None:
    with pytest.raises(TypeError, match="DecisionDisposition"):
        decision_link(disposition="PUBLISHED")
    with pytest.raises(ValueError):
        DecisionDisposition("PUBLISHED")


def test_absent_rationale_reference_is_valid() -> None:
    link = HumanDecisionLink(
        human_decision_link_id=HumanDecisionLinkId("decision-link:without-rationale"),
        human_decision_id=HumanDecisionId("human-decision:without-rationale"),
        reviewed_evidence_bundle_id=EvidenceBundleId("evidence-bundle:v3"),
        reviewed_evidence_card_id=EvidenceCardId("evidence-card:v3"),
        human_actor_reference=OpaqueReference("auth-human:1"),
        decision_timestamp=DECIDED_AT,
        disposition=DecisionDisposition.APPROVED,
        workflow_event_or_result_reference=OpaqueReference("workflow-event:1"),
    )

    assert link.rationale_reference is None


def test_bounded_rationale_reference_is_preserved_exactly() -> None:
    rationale = OpaqueReference("rationale-record:review-comment:42")

    assert decision_link(rationale_reference=rationale).rationale_reference is rationale


@pytest.mark.parametrize("value", ["", "   "])
def test_blank_rationale_reference_is_rejected(value: str) -> None:
    with pytest.raises(ValueError, match="nonempty"):
        decision_link(rationale_reference=OpaqueReference(value))


def test_oversized_rationale_reference_is_rejected() -> None:
    with pytest.raises(ValueError, match="rationale_reference exceeds"):
        decision_link(
            rationale_reference=OpaqueReference("x" * (MAX_REFERENCE_BYTES + 1))
        )


def test_workflow_event_or_result_reference_is_opaque_and_preserved() -> None:
    reference = OpaqueReference("workflow-result:human-review:987")

    link = decision_link(workflow_event_or_result_reference=reference)

    assert link.workflow_event_or_result_reference is reference


def test_oversized_workflow_reference_is_rejected() -> None:
    with pytest.raises(ValueError, match="workflow_event_or_result_reference exceeds"):
        decision_link(
            workflow_event_or_result_reference=OpaqueReference(
                "x" * (MAX_REFERENCE_BYTES + 1)
            )
        )


def test_regeneration_request_requires_child_run_reference() -> None:
    with pytest.raises(ValueError, match="requires regeneration_child_run_reference"):
        decision_link(disposition=DecisionDisposition.REGENERATION_REQUESTED)


@pytest.mark.parametrize(
    "disposition",
    [
        DecisionDisposition.APPROVED,
        DecisionDisposition.REJECTED,
        DecisionDisposition.DISMISSED,
        DecisionDisposition.OUT_OF_SCOPE,
    ],
)
def test_non_regeneration_disposition_rejects_child_run(
    disposition: DecisionDisposition,
) -> None:
    with pytest.raises(ValueError, match="applies only"):
        decision_link(
            disposition=disposition,
            regeneration_child_run_reference=RunId("run:unexpected-child"),
        )


def test_link_is_effectively_immutable() -> None:
    link = decision_link()

    with pytest.raises(FrozenInstanceError):
        link.disposition = DecisionDisposition.REJECTED  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        link.human_actor_reference.value = "auth-human:changed"  # type: ignore[misc]


def test_domain_dict_mutation_does_not_change_the_link() -> None:
    link = decision_link()
    domain = link.to_domain_dict()
    actor = domain["human_actor_reference"]
    assert isinstance(actor, dict)

    actor["value"] = "auth-human:changed"

    assert link.human_actor_reference.value == "auth-human:provider:subject-123"


def test_canonical_serialization_is_deterministic_and_timezone_normalized() -> None:
    offset = timezone(timedelta(hours=5, minutes=30))
    first = decision_link()
    second = decision_link(decision_timestamp=DECIDED_AT.astimezone(offset))

    assert first.to_domain_json() == second.to_domain_json()
    assert json.loads(first.to_domain_json())["decision_timestamp"].endswith("Z")


def test_same_id_and_semantic_content_are_equivalent() -> None:
    first = decision_link()
    second = decision_link()

    assert (
        compare_human_decision_links(first, second) is EvidenceComparison.EQUIVALENT
    )


@pytest.mark.parametrize(
    "change",
    [
        {"disposition": DecisionDisposition.REJECTED},
        {"human_actor_reference": OpaqueReference("auth-human:other")},
        {"human_decision_id": HumanDecisionId("human-decision:other")},
        {"reviewed_evidence_bundle_id": EvidenceBundleId("evidence-bundle:v4")},
        {"reviewed_evidence_card_id": EvidenceCardId("evidence-card:v4")},
        {"decision_timestamp": DECIDED_AT + timedelta(seconds=1)},
        {"rationale_reference": OpaqueReference("rationale-record:other")},
        {
            "workflow_event_or_result_reference": OpaqueReference(
                "workflow-event:other"
            )
        },
    ],
)
def test_same_id_with_changed_semantic_content_is_conflicting(
    change: dict[str, object],
) -> None:
    existing = decision_link()
    changed = replace(existing, **change)

    assert (
        compare_human_decision_links(existing, changed)
        is EvidenceComparison.CONFLICTING
    )


def test_same_id_with_changed_regeneration_child_is_conflicting() -> None:
    existing = decision_link(
        disposition=DecisionDisposition.REGENERATION_REQUESTED,
        regeneration_child_run_reference=RunId("run:regeneration-child:1"),
    )
    changed = replace(
        existing,
        regeneration_child_run_reference=RunId("run:regeneration-child:2"),
    )

    assert (
        compare_human_decision_links(existing, changed)
        is EvidenceComparison.CONFLICTING
    )


def test_different_link_ids_are_distinct_identities() -> None:
    existing = decision_link()
    independent = decision_link(
        human_decision_link_id=HumanDecisionLinkId("decision-link:2")
    )

    assert (
        compare_human_decision_links(existing, independent)
        is EvidenceComparison.DISTINCT_IDENTITY
    )


@pytest.mark.parametrize(
    "wrong_identity",
    [
        HumanDecisionId("human-decision:wrong-type"),
        EvidenceBundleId("evidence-bundle:wrong-type"),
        EvidenceCardId("evidence-card:wrong-type"),
        CandidatePatchId("candidate-patch:wrong-type"),
        CandidateVersionId("candidate-version:wrong-type"),
        ExecutionEvidenceId("execution-evidence:wrong-type"),
        RunId("run:wrong-type"),
        WorkflowAttemptId("workflow-attempt:wrong-type"),
        QueueMessageId("queue-message:wrong-type"),
        QueueDeliveryId("queue-delivery:wrong-type"),
        OpaqueReference("auth-human:wrong-type"),
    ],
)
def test_other_identity_types_cannot_substitute_for_link_identity(
    wrong_identity: object,
) -> None:
    with pytest.raises(TypeError, match="HumanDecisionLinkId"):
        decision_link(human_decision_link_id=wrong_identity)


def test_link_identity_cannot_substitute_for_human_decision_identity() -> None:
    with pytest.raises(TypeError, match="HumanDecisionId"):
        decision_link(human_decision_id=HumanDecisionLinkId("decision-link:other"))


@pytest.mark.parametrize(
    "change",
    [
        {"human_decision_id": HumanDecisionId("decision-link:1")},
        {"reviewed_evidence_bundle_id": EvidenceBundleId("decision-link:1")},
        {"reviewed_evidence_card_id": EvidenceCardId("decision-link:1")},
        {"human_actor_reference": OpaqueReference("decision-link:1")},
        {
            "workflow_event_or_result_reference": OpaqueReference("decision-link:1")
        },
    ],
)
def test_link_identity_cannot_copy_related_identity_or_reference_values(
    change: dict[str, object],
) -> None:
    with pytest.raises(ValueError, match="distinct|must not copy"):
        decision_link(**change)


def test_unsupported_contract_version_fails_closed() -> None:
    with pytest.raises(ValueError, match="unsupported Evidence contract version"):
        decision_link(contract_version="CONTRACT-EVIDENCE-001@2.0.0")


def test_contract_field_shape_is_exact_and_secret_free() -> None:
    field_names = tuple(field.name for field in fields(HumanDecisionLink))

    assert field_names == (
        "human_decision_link_id",
        "human_decision_id",
        "reviewed_evidence_bundle_id",
        "reviewed_evidence_card_id",
        "human_actor_reference",
        "decision_timestamp",
        "disposition",
        "workflow_event_or_result_reference",
        "rationale_reference",
        "regeneration_child_run_reference",
        "contract_version",
    )
    assert decision_link().contract_version == EVIDENCE_CONTRACT_VERSION
    assert not set(field_names) & {
        "password",
        "password_hash",
        "oauth_code",
        "authorization_code",
        "access_token",
        "refresh_token",
        "session_cookie",
        "session_token",
        "github_app_private_key",
        "github_app_jwt",
        "installation_token",
        "provider_api_key",
        "authorization_header",
        "credential",
        "secret",
    }


def test_no_direct_out_of_contract_linkage_or_authority_semantics_exist() -> None:
    names = {field.name for field in fields(HumanDecisionLink)}
    names.update(name for name in dir(HumanDecisionLink) if not name.startswith("__"))

    assert not names & {
        "run_id",
        "workflow_attempt_id",
        "candidate_version_id",
        "queue_message_id",
        "queue_delivery_id",
        "execution_evidence_id",
        "producer_result_id",
        "actor_type",
        "finalization_state",
        "completeness",
        "is_authorized",
        "can_publish",
        "can_transition",
        "permission",
        "grant",
        "capability",
        "role",
        "current_session_valid",
        "current_authentication",
        "current_authorization",
        "save",
        "delete",
    }


def test_out_of_scope_evidence_aggregates_and_human_decision_are_not_implemented() -> None:
    assert not hasattr(evidence_domain, "HumanDecision")


def test_construction_requires_no_database_queue_auth_or_rag_runtime() -> None:
    link = decision_link()

    assert link.human_decision_link_id.value == "decision-link:1"
