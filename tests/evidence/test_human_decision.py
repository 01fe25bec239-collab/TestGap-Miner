from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timedelta, timezone
import json

import pytest

from app.evidence import (
    EVIDENCE_CONTRACT_VERSION,
    CandidateVersionId,
    DecisionDisposition,
    EvidenceBundleId,
    EvidenceCardId,
    EvidenceComparison,
    ExecutionEvidenceId,
    HumanDecision,
    HumanDecisionId,
    HumanDecisionLink,
    HumanDecisionLinkId,
    OpaqueReference,
    QueueDeliveryId,
    QueueMessageId,
    RunId,
    WorkflowAttemptId,
    compare_human_decisions,
    validate_human_decision_link_binding,
)


DECIDED_AT = datetime(2026, 8, 14, 9, 30, tzinfo=timezone.utc)
MAX_REFERENCE_BYTES = 16_384


def decision(**changes: object) -> HumanDecision:
    values: dict[str, object] = {
        "human_decision_id": HumanDecisionId("human-decision:1"),
        "human_actor_reference": OpaqueReference("auth-human:provider:subject-123"),
        "decision_timestamp": DECIDED_AT,
        "disposition": DecisionDisposition.APPROVED,
        "rationale_reference": None,
    }
    values.update(changes)
    return HumanDecision(**values)  # type: ignore[arg-type]


def decision_link(**changes: object) -> HumanDecisionLink:
    values: dict[str, object] = {
        "human_decision_link_id": HumanDecisionLinkId("decision-link:1"),
        "human_decision_id": HumanDecisionId("human-decision:1"),
        "reviewed_evidence_bundle_id": EvidenceBundleId("evidence-bundle:v3"),
        "reviewed_evidence_card_id": EvidenceCardId("evidence-card:v3"),
        "human_actor_reference": OpaqueReference("auth-human:provider:subject-123"),
        "decision_timestamp": DECIDED_AT,
        "disposition": DecisionDisposition.APPROVED,
        "workflow_event_or_result_reference": OpaqueReference("workflow-event:1"),
        "rationale_reference": None,
    }
    values.update(changes)
    return HumanDecisionLink(**values)  # type: ignore[arg-type]


def test_exact_six_field_shape_and_link_only_fields_are_absent() -> None:
    names = tuple(field.name for field in fields(HumanDecision))

    assert names == (
        "human_decision_id",
        "human_actor_reference",
        "decision_timestamp",
        "disposition",
        "rationale_reference",
        "contract_version",
    )
    assert not set(names) & {
        "reviewed_evidence_bundle_id",
        "reviewed_evidence_card_id",
        "workflow_event_or_result_reference",
        "regeneration_child_run_reference",
        "user_id",
        "auth_subject_id",
        "database_id",
    }


def test_caller_supplied_identity_and_references_are_preserved() -> None:
    identity = HumanDecisionId("human-decision:preserved")
    actor = OpaqueReference("auth-human:opaque:preserved")
    rationale = OpaqueReference("rationale:preserved")

    value = decision(
        human_decision_id=identity,
        human_actor_reference=actor,
        rationale_reference=rationale,
    )

    assert value.human_decision_id is identity
    assert value.human_actor_reference is actor
    assert value.rationale_reference is rationale


def test_decision_is_effectively_immutable_and_export_is_detached() -> None:
    value = decision()

    assert not hasattr(value, "__dict__")
    with pytest.raises(FrozenInstanceError):
        value.disposition = DecisionDisposition.REJECTED  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        value.human_actor_reference.value = "changed"  # type: ignore[misc]

    exported = value.to_domain_dict()
    actor = exported["human_actor_reference"]
    assert isinstance(actor, dict)
    actor["value"] = "changed"
    assert value.human_actor_reference.value == "auth-human:provider:subject-123"


def test_timestamp_validation_and_canonical_instant_normalization() -> None:
    offset = timezone(timedelta(hours=5, minutes=30))
    equivalent = decision(decision_timestamp=DECIDED_AT.astimezone(offset))

    assert decision().to_domain_json() == equivalent.to_domain_json()
    assert json.loads(decision().to_domain_json())["decision_timestamp"].endswith("Z")
    with pytest.raises(ValueError, match="timezone-aware"):
        decision(decision_timestamp=datetime(2026, 8, 14, 9, 30))
    with pytest.raises(TypeError, match="must be a datetime"):
        decision(decision_timestamp="2026-08-14T09:30:00Z")


def test_actor_reference_bound_and_opaque_semantics() -> None:
    bounded = OpaqueReference("a" * MAX_REFERENCE_BYTES)
    assert decision(human_actor_reference=bounded).human_actor_reference is bounded

    with pytest.raises(ValueError, match="human_actor_reference exceeds"):
        decision(
            human_actor_reference=OpaqueReference("a" * (MAX_REFERENCE_BYTES + 1))
        )
    with pytest.raises(ValueError, match="nonempty"):
        OpaqueReference("   ")
    with pytest.raises(TypeError, match="human_actor_reference"):
        decision(human_actor_reference="user:parsed")


def test_optional_rationale_reference_bound() -> None:
    assert decision().rationale_reference is None
    bounded = OpaqueReference("r" * MAX_REFERENCE_BYTES)
    assert decision(rationale_reference=bounded).rationale_reference is bounded

    with pytest.raises(ValueError, match="rationale_reference exceeds"):
        decision(
            rationale_reference=OpaqueReference("r" * (MAX_REFERENCE_BYTES + 1))
        )


@pytest.mark.parametrize("disposition", list(DecisionDisposition))
def test_exact_disposition_vocabulary_constructs(
    disposition: DecisionDisposition,
) -> None:
    assert decision(disposition=disposition).disposition is disposition


@pytest.mark.parametrize("value", ["PUBLISHED", "MERGED", "SUPERSEDED", "CANCELLED"])
def test_out_of_vocabulary_dispositions_are_rejected(value: str) -> None:
    with pytest.raises(ValueError):
        DecisionDisposition(value)
    with pytest.raises(TypeError, match="DecisionDisposition"):
        decision(disposition=value)


def test_contract_version_accepts_current_and_rejects_unsupported() -> None:
    assert decision().contract_version == EVIDENCE_CONTRACT_VERSION
    with pytest.raises(ValueError, match="unsupported Evidence contract version"):
        decision(contract_version="CONTRACT-EVIDENCE-001@2.0.0")


@pytest.mark.parametrize(
    "change",
    [
        {"human_actor_reference": OpaqueReference("auth-human:other")},
        {"decision_timestamp": DECIDED_AT + timedelta(seconds=1)},
        {"disposition": DecisionDisposition.REJECTED},
        {"rationale_reference": OpaqueReference("rationale:other")},
    ],
)
def test_same_id_changed_semantic_content_conflicts(
    change: dict[str, object],
) -> None:
    existing = decision()
    incoming = replace(existing, **change)

    assert compare_human_decisions(existing, incoming) is EvidenceComparison.CONFLICTING


def test_identity_convergence_and_distinction() -> None:
    assert compare_human_decisions(decision(), decision()) is EvidenceComparison.EQUIVALENT
    assert compare_human_decisions(
        decision(),
        decision(human_decision_id=HumanDecisionId("human-decision:2")),
    ) is EvidenceComparison.DISTINCT_IDENTITY


@pytest.mark.parametrize(
    "wrong_identity",
    [
        HumanDecisionLinkId("decision-link:wrong"),
        EvidenceBundleId("bundle:wrong"),
        EvidenceCardId("card:wrong"),
        CandidateVersionId("candidate:wrong"),
        ExecutionEvidenceId("execution:wrong"),
        RunId("run:wrong"),
        WorkflowAttemptId("attempt:wrong"),
        QueueMessageId("message:wrong"),
        QueueDeliveryId("delivery:wrong"),
        OpaqueReference("opaque:wrong"),
        "human-decision:wrong",
    ],
)
def test_foreign_identity_domains_cannot_substitute_for_decision_identity(
    wrong_identity: object,
) -> None:
    with pytest.raises(TypeError, match="HumanDecisionId"):
        decision(human_decision_id=wrong_identity)


def test_comparison_rejects_wrong_domain_objects() -> None:
    with pytest.raises(TypeError, match="existing"):
        compare_human_decisions(decision_link(), decision())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="incoming"):
        compare_human_decisions(decision(), decision_link())  # type: ignore[arg-type]


def test_matching_link_binding_passes_for_equivalent_timestamp_instants() -> None:
    offset = timezone(timedelta(hours=5, minutes=30))
    validate_human_decision_link_binding(
        decision(),
        decision_link(decision_timestamp=DECIDED_AT.astimezone(offset)),
    )


@pytest.mark.parametrize(
    "change",
    [
        {"human_decision_id": HumanDecisionId("human-decision:other")},
        {"human_actor_reference": OpaqueReference("auth-human:other")},
        {"decision_timestamp": DECIDED_AT + timedelta(seconds=1)},
        {"disposition": DecisionDisposition.REJECTED},
        {"rationale_reference": OpaqueReference("rationale:other")},
    ],
)
def test_link_binding_rejects_each_shared_semantic_mismatch(
    change: dict[str, object],
) -> None:
    changed_name = next(iter(change))
    with pytest.raises(ValueError, match=changed_name):
        validate_human_decision_link_binding(decision(), decision_link(**change))


def test_link_binding_rejects_wrong_domain_objects() -> None:
    with pytest.raises(TypeError, match="decision"):
        validate_human_decision_link_binding(decision_link(), decision_link())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="link"):
        validate_human_decision_link_binding(decision(), decision())  # type: ignore[arg-type]


def test_regeneration_decision_requires_no_child_run() -> None:
    value = decision(disposition=DecisionDisposition.REGENERATION_REQUESTED)

    assert value.disposition is DecisionDisposition.REGENERATION_REQUESTED
    assert not hasattr(value, "regeneration_child_run_reference")
    with pytest.raises(ValueError, match="requires regeneration_child_run_reference"):
        decision_link(disposition=DecisionDisposition.REGENERATION_REQUESTED)


def test_no_authority_lifecycle_cardinality_or_mutation_semantics_exist() -> None:
    names = {field.name for field in fields(HumanDecision)}
    names.update(name for name in dir(HumanDecision) if not name.startswith("__"))

    assert not names & {
        "current",
        "latest",
        "winner",
        "superseded",
        "replacement",
        "can_publish",
        "can_merge",
        "can_transition",
        "is_authorized",
        "links",
        "link_count",
        "primary_link",
        "current_link",
        "save",
        "delete",
        "update",
    }
