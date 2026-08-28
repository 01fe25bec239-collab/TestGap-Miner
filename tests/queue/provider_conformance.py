"""Reusable provider-neutral Queue conformance cases."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any, Protocol

import pytest

from app.queue import (
    AckReadiness,
    AdministrativeAuthorizationDecision,
    ClaimOrLeaseId,
    ClaimState,
    ControlState,
    DurableEffect,
    FailureClassification,
    ProducerResultId,
    PublicationState,
    QueueConflictError,
    QueueDeliveryId,
    QueueEnvelope,
    QueueMessageId,
    QueueStateError,
    QueueValidationError,
    ResultBinding,
    RetryDecision,
    RetryPolicy,
    SemanticRequestId,
    WorkerServiceReference,
    WorkflowAttemptId,
)


class QueueConformanceSubject(Protocol):
    """Construction seam supplied by each provider-specific test module."""

    adapter: Any
    required_durable_effects: frozenset[DurableEffect]
    retry_policy: RetryPolicy

    def make_envelope(self, **changes: object) -> QueueEnvelope: ...

    def validate_raw(self, **changes: object) -> QueueEnvelope: ...

    def make_binding(
        self, envelope: QueueEnvelope, **changes: object
    ) -> ResultBinding: ...

    def redrive_authorization(self) -> AdministrativeAuthorizationDecision: ...


@dataclass(frozen=True, slots=True)
class ConformanceCase:
    name: str
    run: Callable[[QueueConformanceSubject], None]


def _confirmed(subject: QueueConformanceSubject, **changes: object) -> QueueEnvelope:
    envelope = subject.make_envelope(**changes)
    subject.adapter.publish(envelope)
    subject.adapter.record_publication_outcome(
        envelope.publication_identity,
        PublicationState.CONFIRMED_SUCCESS,
        f"provider-confirmed-{envelope.queue_message_id.value}",
    )
    return envelope


def _delivered(subject: QueueConformanceSubject, **changes: object):
    envelope = _confirmed(subject, **changes)
    return envelope, subject.adapter.deliver(envelope.queue_message_id)


def _claimed(subject: QueueConformanceSubject):
    envelope, delivery = _delivered(subject)
    claim = subject.adapter.claim(
        delivery.queue_delivery_id, WorkerServiceReference("worker-1")
    )
    return envelope, delivery, claim


def _ready(subject: QueueConformanceSubject, succeeded: bool = True) -> AckReadiness:
    return AckReadiness(succeeded, subject.required_durable_effects)


def _exhaust(
    subject: QueueConformanceSubject,
    delivery,
    classification: FailureClassification = FailureClassification.POISON,
) -> list[RetryDecision]:
    """Drive one delivery to dead-letter through the public failure boundary."""
    return [
        subject.adapter.classify_failure(delivery.queue_delivery_id, classification)
        for _ in range(
            subject.retry_policy.max_poison_attempts
            if classification is FailureClassification.POISON
            else subject.retry_policy.max_transport_attempts
        )
    ]


def _dead_letter(
    subject: QueueConformanceSubject,
    classification: FailureClassification = FailureClassification.POISON,
):
    envelope, delivery = _delivered(subject)
    return envelope, delivery, _exhaust(subject, delivery, classification)


def _decision(decision: RetryDecision) -> tuple[bool, bool, bool]:
    return (
        decision.retry_allowed,
        decision.dead_lettered,
        decision.workflow_terminal,
    )


def stable_semantic_request_identity(subject: QueueConformanceSubject) -> None:
    envelope, first = _delivered(subject)
    second = subject.adapter.redeliver(first.queue_delivery_id)
    assert first.semantic_request_id == second.semantic_request_id
    assert second.semantic_request_id == envelope.semantic_request_id


def stable_queue_message_identity(subject: QueueConformanceSubject) -> None:
    envelope, first = _delivered(subject)
    second = subject.adapter.redeliver(first.queue_delivery_id)
    assert first.queue_message_id == second.queue_message_id
    assert second.queue_message_id == envelope.queue_message_id


def distinct_delivery_redelivery_identity(subject: QueueConformanceSubject) -> None:
    _, first = _delivered(subject)
    second = subject.adapter.redeliver(first.queue_delivery_id)
    assert type(first.queue_delivery_id) is QueueDeliveryId
    assert type(second.queue_delivery_id) is QueueDeliveryId
    assert first.queue_delivery_id != second.queue_delivery_id


def claim_replacement_fence(subject: QueueConformanceSubject) -> None:
    _, delivery, first = _claimed(subject)
    second = subject.adapter.claim(
        delivery.queue_delivery_id, WorkerServiceReference("worker-2")
    )
    assert first.claim_or_lease_id != second.claim_or_lease_id
    assert second.fence > first.fence
    assert subject.adapter.claim_record(first.claim_or_lease_id).state is ClaimState.REPLACED
    assert second.state is ClaimState.CURRENT


def lease_uncertainty_and_confirmed_loss(subject: QueueConformanceSubject) -> None:
    _, _, claim = _claimed(subject)
    assert claim.state is ClaimState.CURRENT

    uncertain = subject.adapter.mark_renewal_uncertain(claim.claim_or_lease_id)
    assert uncertain.state is ClaimState.RENEWAL_UNCERTAIN
    assert not subject.adapter.can_produce_protected_effect(claim.claim_or_lease_id)

    lost = subject.adapter.confirm_lease_loss(claim.claim_or_lease_id)
    assert lost.state is ClaimState.CONFIRMED_LEASE_LOST
    assert not subject.adapter.can_produce_protected_effect(claim.claim_or_lease_id)
    with pytest.raises(QueueStateError, match="irreversible"):
        subject.adapter.mark_renewal_uncertain(claim.claim_or_lease_id)
    assert not subject.adapter.can_produce_protected_effect(claim.claim_or_lease_id)


def stale_claim_protected_effect_rejection(subject: QueueConformanceSubject) -> None:
    envelope, delivery, first = _claimed(subject)
    subject.adapter.claim(delivery.queue_delivery_id, WorkerServiceReference("worker-2"))
    assert not subject.adapter.can_produce_protected_effect(first.claim_or_lease_id)
    with pytest.raises(QueueStateError):
        subject.adapter.accept_result(
            first.claim_or_lease_id,
            subject.make_binding(envelope),
            "stale-submission",
        )


def stale_claim_ack_rejection(subject: QueueConformanceSubject) -> None:
    _, delivery, first = _claimed(subject)
    subject.adapter.claim(delivery.queue_delivery_id, WorkerServiceReference("worker-2"))
    assert not subject.adapter.acknowledge(
        delivery.queue_delivery_id, first.claim_or_lease_id, _ready(subject)
    )


def duplicate_delivery_binding(subject: QueueConformanceSubject) -> None:
    envelope, first = _delivered(subject)
    second = subject.adapter.redeliver(first.queue_delivery_id)
    assert (
        first.semantic_request_id,
        first.queue_message_id,
        first.workflow_attempt_id,
    ) == (
        second.semantic_request_id,
        second.queue_message_id,
        second.workflow_attempt_id,
    ) == (
        envelope.semantic_request_id,
        envelope.queue_message_id,
        envelope.workflow_attempt_id,
    )


def duplicate_equivalent_result_convergence(subject: QueueConformanceSubject) -> None:
    envelope, delivery, first_claim = _claimed(subject)
    binding = subject.make_binding(envelope)
    accepted = subject.adapter.accept_result(
        first_claim.claim_or_lease_id, binding, "submission-1"
    )
    replacement = subject.adapter.claim(
        delivery.queue_delivery_id, WorkerServiceReference("worker-2")
    )
    recovered = subject.adapter.accept_result(
        replacement.claim_or_lease_id, binding, "submission-2"
    )
    assert recovered == accepted == binding
    assert recovered.producer_result_id == binding.producer_result_id


def duplicate_result_across_redelivery(subject: QueueConformanceSubject) -> None:
    envelope, first_delivery, first_claim = _claimed(subject)
    binding = subject.make_binding(envelope)
    accepted = subject.adapter.accept_result(
        first_claim.claim_or_lease_id, binding, "submission-first-delivery"
    )
    redelivery = subject.adapter.redeliver(first_delivery.queue_delivery_id)
    assert redelivery.queue_delivery_id != first_delivery.queue_delivery_id
    assert redelivery.semantic_request_id == first_delivery.semantic_request_id
    assert redelivery.queue_message_id == first_delivery.queue_message_id
    assert redelivery.workflow_attempt_id == first_delivery.workflow_attempt_id
    redelivery_claim = subject.adapter.claim(
        redelivery.queue_delivery_id, WorkerServiceReference("worker-redelivery")
    )
    recovered = subject.adapter.accept_result(
        redelivery_claim.claim_or_lease_id,
        binding,
        "submission-redelivery",
    )
    assert recovered == accepted == binding
    assert subject.adapter.accepted_result(recovered.producer_result_id) == accepted


def conflicting_result_identity_rejection(subject: QueueConformanceSubject) -> None:
    envelope, delivery, claim = _claimed(subject)
    accepted = subject.make_binding(envelope)
    subject.adapter.accept_result(claim.claim_or_lease_id, accepted, "submission-1")
    replacement = subject.adapter.claim(
        delivery.queue_delivery_id, WorkerServiceReference("worker-2")
    )
    with pytest.raises(QueueConflictError):
        subject.adapter.accept_result(
            replacement.claim_or_lease_id,
            subject.make_binding(
                envelope, producer_result_id=ProducerResultId("result-conflict")
            ),
            "submission-2",
        )
    assert subject.adapter.accepted_result(accepted.producer_result_id) == accepted


def conflicting_result_binding_rejection(subject: QueueConformanceSubject) -> None:
    envelope, _, claim = _claimed(subject)
    accepted = subject.make_binding(envelope)
    subject.adapter.accept_result(claim.claim_or_lease_id, accepted, "submission-1")
    with pytest.raises(QueueConflictError):
        subject.adapter.accept_result(
            claim.claim_or_lease_id,
            subject.make_binding(envelope, result_reference="different-result-reference"),
            "submission-2",
        )


def ack_execution_success_required(subject: QueueConformanceSubject) -> None:
    _, delivery, claim = _claimed(subject)
    assert not subject.adapter.acknowledgement_eligible(
        delivery.queue_delivery_id, claim.claim_or_lease_id, _ready(subject, False)
    )


def ack_durable_readiness_required(subject: QueueConformanceSubject) -> None:
    _, delivery, claim = _claimed(subject)
    assert not subject.adapter.acknowledgement_eligible(
        delivery.queue_delivery_id,
        claim.claim_or_lease_id,
        AckReadiness(True, frozenset()),
    )


def commit_before_ack_boundary(subject: QueueConformanceSubject) -> None:
    _, delivery, claim = _claimed(subject)
    one_missing = subject.required_durable_effects - {
        next(iter(subject.required_durable_effects))
    }
    assert not subject.adapter.acknowledgement_eligible(
        delivery.queue_delivery_id,
        claim.claim_or_lease_id,
        AckReadiness(True, frozenset(one_missing)),
    )
    assert subject.adapter.acknowledgement_eligible(
        delivery.queue_delivery_id, claim.claim_or_lease_id, _ready(subject)
    )


def ack_success(subject: QueueConformanceSubject) -> None:
    _, delivery, claim = _claimed(subject)
    assert subject.adapter.acknowledge(
        delivery.queue_delivery_id, claim.claim_or_lease_id, _ready(subject)
    )
    assert not subject.adapter.can_process(delivery.queue_delivery_id)


def bounded_transport_retry(subject: QueueConformanceSubject) -> None:
    _, _, decisions = _dead_letter(
        subject, FailureClassification.TRANSPORT_RETRYABLE
    )
    assert all(_decision(decision) == (True, False, False) for decision in decisions[:-1])
    assert _decision(decisions[-1]) == (False, True, False)


def bounded_poison_dead_letter(subject: QueueConformanceSubject) -> None:
    _, delivery, decisions = _dead_letter(subject)
    assert all(decision.retry_allowed for decision in decisions[:-1])
    assert decisions[-1].dead_lettered
    assert subject.adapter.dead_letter(delivery.queue_delivery_id).classification is (
        FailureClassification.POISON
    )


def dead_letter_no_workflow_terminality(subject: QueueConformanceSubject) -> None:
    _, delivery, decisions = _dead_letter(subject)
    record = subject.adapter.dead_letter(delivery.queue_delivery_id)
    assert decisions[-1].workflow_terminal is False
    assert record.workflow_terminal is False


def non_active_control_cutoff(subject: QueueConformanceSubject) -> None:
    for index, state in enumerate(
        (
            ControlState.CANCELLED,
            ControlState.REVOKED,
            ControlState.DELETED,
            ControlState.SUPERSEDED,
        ),
        start=1,
    ):
        envelope, delivery = _delivered(
            subject,
            semantic_request_id=f"semantic-control-{index}",
            queue_message_id=f"message-control-{index}",
            workflow_attempt_id=f"attempt-control-{index}",
            publication_identity=f"publication-control-{index}",
        )
        claim = subject.adapter.claim(
            delivery.queue_delivery_id, WorkerServiceReference(f"worker-{index}")
        )
        binding = subject.make_binding(
            envelope,
            producer_result_id=ProducerResultId(f"result-control-{index}"),
        )
        subject.adapter.set_control(envelope.semantic_request_id, state)
        assert not subject.adapter.can_process(delivery.queue_delivery_id)
        assert not subject.adapter.can_produce_protected_effect(claim.claim_or_lease_id)
        with pytest.raises(QueueStateError):
            subject.adapter.accept_result(
                claim.claim_or_lease_id, binding, f"submission-control-{index}"
            )
        readiness = _ready(subject)
        assert not subject.adapter.acknowledgement_eligible(
            delivery.queue_delivery_id, claim.claim_or_lease_id, readiness
        )
        assert not subject.adapter.acknowledge(
            delivery.queue_delivery_id, claim.claim_or_lease_id, readiness
        )
        with pytest.raises(QueueStateError):
            subject.adapter.claim(
                delivery.queue_delivery_id, WorkerServiceReference(f"worker-{index}")
            )


def security_rejection_sticky(subject: QueueConformanceSubject) -> None:
    envelope, delivery = _delivered(subject)
    subject.adapter.classify_failure(
        delivery.queue_delivery_id, FailureClassification.SECURITY_REJECTION
    )
    with pytest.raises(QueueStateError):
        subject.adapter.classify_failure(
            delivery.queue_delivery_id, FailureClassification.TRANSPORT_RETRYABLE
        )
    with pytest.raises(QueueStateError):
        subject.adapter.set_control(envelope.semantic_request_id, ControlState.ACTIVE)
    with pytest.raises(QueueStateError):
        subject.adapter.redeliver(delivery.queue_delivery_id)


def security_rejection_revokes_authority(subject: QueueConformanceSubject) -> None:
    envelope, delivery, claim = _claimed(subject)
    subject.adapter.classify_failure(
        delivery.queue_delivery_id, FailureClassification.SECURITY_REJECTION
    )
    assert subject.adapter.claim_record(claim.claim_or_lease_id).state is ClaimState.REVOKED
    assert not subject.adapter.can_produce_protected_effect(claim.claim_or_lease_id)
    with pytest.raises(QueueStateError):
        subject.adapter.accept_result(
            claim.claim_or_lease_id,
            subject.make_binding(envelope),
            "submission-after-security-rejection",
        )
    assert not subject.adapter.acknowledge(
        delivery.queue_delivery_id, claim.claim_or_lease_id, _ready(subject)
    )


def redrive_cannot_bypass_security_rejection(subject: QueueConformanceSubject) -> None:
    envelope, poisoned, _ = _dead_letter(subject)
    alternate = _confirmed(
        subject,
        semantic_request_id=envelope.semantic_request_id.value,
        queue_message_id="message-security-occurrence",
        workflow_attempt_id="attempt-security-occurrence",
        publication_identity="publication-security-occurrence",
    )
    active = subject.adapter.deliver(alternate.queue_message_id)
    subject.adapter.classify_failure(
        active.queue_delivery_id, FailureClassification.SECURITY_REJECTION
    )
    with pytest.raises(QueueStateError):
        subject.adapter.redrive(
            poisoned.queue_delivery_id,
            "administrator-1",
            subject.redrive_authorization(),
        )
    assert subject.adapter.dead_letter(poisoned.queue_delivery_id).classification is (
        FailureClassification.POISON
    )


def unknown_contract_version(subject: QueueConformanceSubject) -> None:
    with pytest.raises(QueueValidationError):
        subject.validate_raw(contract_version="unsupported-contract")


def unknown_schema_version(subject: QueueConformanceSubject) -> None:
    with pytest.raises(QueueValidationError):
        subject.validate_raw(schema_version="unsupported-schema")


def unknown_semantic_extension(subject: QueueConformanceSubject) -> None:
    with pytest.raises(QueueValidationError):
        subject.validate_raw(future_semantic_switch=True)


def prohibited_payload_field_classes(subject: QueueConformanceSubject) -> None:
    prohibited = {
        "credentials": "secret",
        "access_token": "secret",
        "authorization_header": "secret",
        "repository": "repository-data",
        "archive": b"archive-data",
        "patch": "patch-data",
        "prompt": "prompt-data",
        "model_context": "context-data",
        "evidence_bytes": b"evidence-data",
        "artefact_bytes": b"artefact-data",
        "command": "command-data",
    }
    for field, value in prohibited.items():
        with pytest.raises(QueueValidationError, match="prohibited"):
            subject.validate_raw(**{field: value})


def prohibited_content_smuggling(subject: QueueConformanceSubject) -> None:
    for field, value in (
        ("input_reference", "Authorization: Bearer secret"),
        ("result_reference", "diff --git a/file b/file"),
        ("evidence_reference_id", "full prompt text"),
        ("original_provenance_reference", "evidence bytes embedded here"),
        ("integrity_metadata", "raw command: rm -rf target"),
    ):
        with pytest.raises(QueueValidationError, match="prohibited"):
            subject.validate_raw(**{field: value})


def identity_non_conflation(subject: QueueConformanceSubject) -> None:
    value = "shared-identity-text"
    typed = (
        SemanticRequestId(value),
        QueueMessageId(value),
        QueueDeliveryId(value),
        ClaimOrLeaseId(value),
        WorkflowAttemptId(value),
        ProducerResultId(value),
    )
    assert len({type(identity) for identity in typed}) == len(typed)
    assert all(left != right for index, left in enumerate(typed) for right in typed[index + 1 :])
    with pytest.raises(QueueValidationError, match="conflated"):
        subject.validate_raw(
            semantic_request_id=value,
            queue_message_id=value,
        )

    envelope = _confirmed(subject, evidence_reference_id=value)
    assert envelope.evidence_reference_id == value
    assert envelope.evidence_reference_id != envelope.queue_message_id
    with pytest.raises((TypeError, QueueValidationError)):
        subject.adapter.deliver(envelope.evidence_reference_id)
    with pytest.raises(QueueValidationError):
        subject.adapter.deliver(SemanticRequestId(envelope.queue_message_id.value))


def redelivery_preserves_original_provenance(subject: QueueConformanceSubject) -> None:
    """Redelivery is a new transport occurrence of unchanged semantic work."""
    envelope, first = _delivered(subject)
    second = subject.adapter.redeliver(first.queue_delivery_id)

    assert second.semantic_request_id == first.semantic_request_id
    assert second.semantic_request_id == envelope.semantic_request_id
    assert second.queue_message_id == first.queue_message_id
    assert second.queue_message_id == envelope.queue_message_id
    if envelope.workflow_attempt_id is not None:
        assert second.workflow_attempt_id == first.workflow_attempt_id
        assert second.workflow_attempt_id == envelope.workflow_attempt_id
    assert second.queue_delivery_id != first.queue_delivery_id

    provenance = second.original_provenance_reference
    assert isinstance(provenance, str) and provenance.strip()
    assert provenance == first.original_provenance_reference
    if envelope.original_provenance_reference:
        assert provenance == envelope.original_provenance_reference

    third = subject.adapter.redeliver(second.queue_delivery_id)
    assert third.original_provenance_reference == provenance
    assert third.queue_delivery_id not in {
        first.queue_delivery_id,
        second.queue_delivery_id,
    }


def poison_retry_decision_semantics(subject: QueueConformanceSubject) -> None:
    """The complete returned RetryDecision, not just its side effects."""
    _, delivery, decisions = _dead_letter(subject)
    for decision in decisions[:-1]:
        assert _decision(decision) == (True, False, False)
    assert _decision(decisions[-1]) == (False, True, False)
    record = subject.adapter.dead_letter(delivery.queue_delivery_id)
    assert record.classification is FailureClassification.POISON
    assert record.workflow_terminal is False


def security_rejection_retry_decision(subject: QueueConformanceSubject) -> None:
    """SECURITY_REJECTION is neither ordinary retry, dead-letter, nor terminal."""
    _, delivery = _delivered(subject)
    first = subject.adapter.classify_failure(
        delivery.queue_delivery_id, FailureClassification.SECURITY_REJECTION
    )
    assert _decision(first) == (False, False, False)

    repeated = subject.adapter.classify_failure(
        delivery.queue_delivery_id, FailureClassification.SECURITY_REJECTION
    )
    assert _decision(repeated) == (False, False, False)

    with pytest.raises(KeyError):
        subject.adapter.dead_letter(delivery.queue_delivery_id)
    with pytest.raises(QueueStateError):
        subject.adapter.redrive(
            delivery.queue_delivery_id,
            "administrator-security",
            subject.redrive_authorization(),
        )


def authorized_ordinary_redrive(subject: QueueConformanceSubject) -> None:
    """A non-security dead letter is administratively redrivable."""
    envelope, poisoned, decisions = _dead_letter(subject)
    assert decisions[-1].dead_lettered

    authorization = subject.redrive_authorization()
    assert authorization.authorized is True
    with pytest.raises(QueueStateError):
        subject.adapter.redrive(poisoned.queue_delivery_id, "administrator-1", None)
    with pytest.raises(QueueStateError):
        subject.adapter.redrive(
            poisoned.queue_delivery_id,
            "administrator-1",
            replace(authorization, authorized=False),
        )

    redriven = subject.adapter.redrive(
        poisoned.queue_delivery_id, "administrator-1", authorization
    )

    assert type(redriven.queue_delivery_id) is QueueDeliveryId
    assert redriven.queue_delivery_id != poisoned.queue_delivery_id
    assert redriven.semantic_request_id == envelope.semantic_request_id
    assert redriven.queue_message_id == envelope.queue_message_id
    assert redriven.original_provenance_reference == (
        poisoned.original_provenance_reference
    )
    assert subject.adapter.can_process(redriven.queue_delivery_id)

    record = subject.adapter.redrive_record(redriven.queue_delivery_id)
    assert record.new_queue_delivery_id == redriven.queue_delivery_id
    assert record.source_queue_delivery_id == poisoned.queue_delivery_id
    assert record.source_queue_message_id == envelope.queue_message_id
    assert record.semantic_request_id == envelope.semantic_request_id
    assert record.original_provenance_reference == (
        poisoned.original_provenance_reference
    )
    assert record.source_failure_classification is FailureClassification.POISON
    assert record.authorization_context_reference == (
        authorization.authorization_context_reference
    )
    assert record.policy_version == authorization.policy_version
    assert record.authorization_decision_reference == authorization.decision_reference
    assert record.replay_or_redrive_actor_reference == "administrator-1"


def bounded_administrative_redrive(subject: QueueConformanceSubject) -> None:
    """Administrative redrive is bounded by the configured allowance."""
    _, delivery, _ = _dead_letter(subject)
    for _ in range(subject.retry_policy.max_redrives):
        delivery = subject.adapter.redrive(
            delivery.queue_delivery_id,
            "administrator-1",
            subject.redrive_authorization(),
        )
        assert _decision(_exhaust(subject, delivery)[-1]) == (False, True, False)
    with pytest.raises(QueueStateError):
        subject.adapter.redrive(
            delivery.queue_delivery_id,
            "administrator-1",
            subject.redrive_authorization(),
        )


CONFORMANCE_CASES = tuple(
    ConformanceCase(name, run)
    for name, run in (
        ("stable_semantic_request_identity", stable_semantic_request_identity),
        ("stable_queue_message_identity", stable_queue_message_identity),
        ("distinct_delivery_redelivery_identity", distinct_delivery_redelivery_identity),
        ("redelivery_preserves_original_provenance", redelivery_preserves_original_provenance),
        ("claim_replacement_fence", claim_replacement_fence),
        ("lease_uncertainty_and_confirmed_loss", lease_uncertainty_and_confirmed_loss),
        ("stale_claim_protected_effect_rejection", stale_claim_protected_effect_rejection),
        ("stale_claim_ack_rejection", stale_claim_ack_rejection),
        ("duplicate_delivery_binding", duplicate_delivery_binding),
        ("duplicate_equivalent_result_convergence", duplicate_equivalent_result_convergence),
        ("duplicate_result_across_redelivery", duplicate_result_across_redelivery),
        ("conflicting_result_identity_rejection", conflicting_result_identity_rejection),
        ("conflicting_result_binding_rejection", conflicting_result_binding_rejection),
        ("ack_execution_success_required", ack_execution_success_required),
        ("ack_durable_readiness_required", ack_durable_readiness_required),
        ("commit_before_ack_boundary", commit_before_ack_boundary),
        ("ack_success", ack_success),
        ("bounded_transport_retry", bounded_transport_retry),
        ("bounded_poison_dead_letter", bounded_poison_dead_letter),
        ("poison_retry_decision_semantics", poison_retry_decision_semantics),
        ("dead_letter_no_workflow_terminality", dead_letter_no_workflow_terminality),
        ("non_active_control_cutoff", non_active_control_cutoff),
        ("security_rejection_sticky", security_rejection_sticky),
        ("security_rejection_revokes_authority", security_rejection_revokes_authority),
        ("security_rejection_retry_decision", security_rejection_retry_decision),
        ("authorized_ordinary_redrive", authorized_ordinary_redrive),
        ("bounded_administrative_redrive", bounded_administrative_redrive),
        ("redrive_cannot_bypass_security_rejection", redrive_cannot_bypass_security_rejection),
        ("unknown_contract_version", unknown_contract_version),
        ("unknown_schema_version", unknown_schema_version),
        ("unknown_semantic_extension", unknown_semantic_extension),
        ("prohibited_payload_field_classes", prohibited_payload_field_classes),
        ("prohibited_content_smuggling", prohibited_content_smuggling),
        ("identity_non_conflation", identity_non_conflation),
    )
)


CASES_BY_NAME = {case.name: case for case in CONFORMANCE_CASES}
