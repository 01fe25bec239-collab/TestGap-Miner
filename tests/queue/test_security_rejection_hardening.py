"""Sticky Queue-side security-rejection hardening invariants (QUEUE-006).

Proves that once active Queue work is classified
``FailureClassification.SECURITY_REJECTION``, the affected semantic request
obtains an irreversible Queue-owned blocked disposition that no ordinary
public Queue operation can bypass, while all pre-existing ordinary Queue
semantics are preserved.
"""

import pytest

from app.queue import (
    AckReadiness,
    ClaimState,
    ControlState,
    FailureClassification,
    PublicationState,
    ProducerResultId,
    QueueConflictError,
    QueueStateError,
    WorkerServiceReference,
)


def _ready_readiness(runtime) -> AckReadiness:
    return AckReadiness(True, runtime.required_durable_effects)


def _security_rejected_delivery(runtime, confirmed_published):
    delivery = runtime.deliver(confirmed_published.queue_message_id)
    decision = runtime.classify_failure(
        delivery.queue_delivery_id,
        FailureClassification.SECURITY_REJECTION,
    )
    return delivery, decision


def _alternate_occurrence_for_same_semantic_request(validator, raw_envelope, runtime):
    raw = dict(raw_envelope)
    raw["queue_message_id"] = "message-alternate-occurrence"
    raw["publication_identity"] = "publication-alternate-occurrence"
    envelope = validator.validate(raw)
    runtime.publish(envelope)
    runtime.record_publication_outcome(
        envelope.publication_identity,
        PublicationState.CONFIRMED_SUCCESS,
        "provider-publication-success-alternate",
    )
    return envelope


def _dead_letter_poison(runtime, confirmed_published):
    delivery = runtime.deliver(confirmed_published.queue_message_id)
    runtime.classify_failure(delivery.queue_delivery_id, FailureClassification.POISON)
    runtime.classify_failure(delivery.queue_delivery_id, FailureClassification.POISON)
    return delivery


# ---------------------------------------------------------------------------
# Mandatory security-rejection invariants
# ---------------------------------------------------------------------------


def test_security_rejection_retry_is_denied(runtime, confirmed_published) -> None:
    delivery, decision = _security_rejected_delivery(runtime, confirmed_published)

    assert (decision.retry_allowed, decision.dead_lettered) == (False, False)


@pytest.mark.parametrize(
    "classification",
    [
        FailureClassification.TRANSPORT_RETRYABLE,
        FailureClassification.POISON,
        FailureClassification.APPLICATION,
    ],
)
def test_ordinary_reclassification_cannot_reenter_after_security_rejection(
    runtime, confirmed_published, classification
) -> None:
    delivery, _ = _security_rejected_delivery(runtime, confirmed_published)

    with pytest.raises(QueueStateError, match="re-enter ordinary retry"):
        runtime.classify_failure(delivery.queue_delivery_id, classification)

    assert not runtime._failure_counts
    with pytest.raises(KeyError):
        runtime.dead_letter(delivery.queue_delivery_id)


def test_security_rejection_redelivery_is_denied(runtime, confirmed_published) -> None:
    delivery, _ = _security_rejected_delivery(runtime, confirmed_published)

    with pytest.raises(QueueStateError, match="cannot receive a new delivery"):
        runtime.redeliver(delivery.queue_delivery_id)
    with pytest.raises(QueueStateError, match="cannot receive a new delivery"):
        runtime.deliver(confirmed_published.queue_message_id)


def test_security_rejection_new_claim_is_denied(runtime, claimed) -> None:
    delivery, claim = claimed

    decision = runtime.classify_failure(
        delivery.queue_delivery_id, FailureClassification.SECURITY_REJECTION
    )

    assert (decision.retry_allowed, decision.dead_lettered) == (False, False)
    assert not runtime.can_process(delivery.queue_delivery_id)
    with pytest.raises(QueueStateError, match="cannot be claimed"):
        runtime.claim(delivery.queue_delivery_id, WorkerServiceReference("worker-2"))
    assert not runtime.can_produce_protected_effect(claim.claim_or_lease_id)


def test_security_rejection_existing_current_claim_authority_is_revoked(
    runtime, claimed, binding_factory
) -> None:
    delivery, claim = claimed

    runtime.classify_failure(
        delivery.queue_delivery_id, FailureClassification.SECURITY_REJECTION
    )

    assert runtime.claim_record(claim.claim_or_lease_id).state == ClaimState.REVOKED
    assert not runtime.can_produce_protected_effect(claim.claim_or_lease_id)
    with pytest.raises(QueueStateError, match="protected effect"):
        runtime.accept_result(
            claim.claim_or_lease_id, binding_factory(), "submission-after-rejection"
        )
    assert binding_factory().producer_result_id not in runtime._accepted_results


def test_security_rejection_existing_renewal_uncertain_claim_authority_is_revoked(
    runtime, claimed
) -> None:
    delivery, claim = claimed
    runtime.mark_renewal_uncertain(claim.claim_or_lease_id)

    runtime.classify_failure(
        delivery.queue_delivery_id, FailureClassification.SECURITY_REJECTION
    )

    assert runtime.claim_record(claim.claim_or_lease_id).state == ClaimState.REVOKED
    assert not runtime.can_produce_protected_effect(claim.claim_or_lease_id)


def test_security_rejection_renewal_and_reclaim_are_denied(runtime, claimed) -> None:
    delivery, claim = claimed
    runtime.classify_failure(
        delivery.queue_delivery_id, FailureClassification.SECURITY_REJECTION
    )

    with pytest.raises(QueueStateError, match="renewal"):
        runtime.mark_renewal_uncertain(claim.claim_or_lease_id)
    with pytest.raises(QueueStateError, match="cannot be claimed"):
        runtime.claim(delivery.queue_delivery_id, WorkerServiceReference("worker-2"))
    assert not runtime.can_produce_protected_effect(claim.claim_or_lease_id)


def test_security_rejection_ack_eligibility_is_denied(runtime, claimed) -> None:
    delivery, claim = claimed
    runtime.classify_failure(
        delivery.queue_delivery_id, FailureClassification.SECURITY_REJECTION
    )

    assert not runtime.acknowledgement_eligible(
        delivery.queue_delivery_id,
        claim.claim_or_lease_id,
        _ready_readiness(runtime),
    )


def test_execution_success_with_durable_readiness_cannot_override_security_rejection_for_ack(
    runtime, claimed
) -> None:
    delivery, claim = claimed
    runtime.classify_failure(
        delivery.queue_delivery_id, FailureClassification.SECURITY_REJECTION
    )

    assert not runtime.acknowledge(
        delivery.queue_delivery_id,
        claim.claim_or_lease_id,
        _ready_readiness(runtime),
    )
    assert delivery.queue_delivery_id not in runtime._acknowledged


def test_previously_dead_lettered_work_cannot_be_generically_redriven_after_security_rejection(
    runtime, validator, raw_envelope, redrive_authorization, confirmed_published
) -> None:
    poisoned = _dead_letter_poison(runtime, confirmed_published)
    alternate = _alternate_occurrence_for_same_semantic_request(
        validator, raw_envelope, runtime
    )
    active = runtime.deliver(alternate.queue_message_id)

    decision = runtime.classify_failure(
        active.queue_delivery_id, FailureClassification.SECURITY_REJECTION
    )
    assert (decision.retry_allowed, decision.dead_lettered) == (False, False)

    with pytest.raises(QueueStateError, match="cannot be redriven"):
        runtime.redrive(
            poisoned.queue_delivery_id, "administrator-1", redrive_authorization
        )
    with pytest.raises(QueueStateError, match="cannot be redriven"):
        runtime.redrive(
            confirmed_published.queue_message_id,
            "administrator-1",
            redrive_authorization,
        )

    dead_letter = runtime.dead_letter(poisoned.queue_delivery_id)
    assert dead_letter.classification == FailureClassification.POISON
    assert len(runtime._deliveries) == 2


def test_control_active_reactivation_cannot_bypass_security_rejection(
    runtime, confirmed_published
) -> None:
    delivery, _ = _security_rejected_delivery(runtime, confirmed_published)

    with pytest.raises(QueueStateError, match="reactivat"):
        runtime.set_control(confirmed_published.semantic_request_id, ControlState.ACTIVE)
    assert not runtime.can_process(delivery.queue_delivery_id)
    with pytest.raises(QueueStateError, match="cannot receive a new delivery"):
        runtime.redeliver(delivery.queue_delivery_id)

    runtime.set_control(confirmed_published.semantic_request_id, ControlState.CANCELLED)
    with pytest.raises(QueueStateError, match="reactivat"):
        runtime.set_control(confirmed_published.semantic_request_id, ControlState.ACTIVE)
    assert not runtime.can_process(delivery.queue_delivery_id)


def test_security_rejection_invents_no_workflow_terminality(runtime, claimed) -> None:
    delivery, claim = claimed

    decision = runtime.classify_failure(
        delivery.queue_delivery_id, FailureClassification.SECURITY_REJECTION
    )

    assert decision.workflow_terminal is False
    with pytest.raises(KeyError):
        runtime.dead_letter(delivery.queue_delivery_id)
    assert runtime.control_state(delivery.semantic_request_id) == ControlState.ACTIVE


def test_second_provider_delivery_occurrence_cannot_escape_semantic_request_rejection(
    runtime, validator, raw_envelope, confirmed_published
) -> None:
    first, _ = _security_rejected_delivery(runtime, confirmed_published)

    with pytest.raises(QueueStateError, match="cannot receive a new delivery"):
        runtime.record_provider_delivery_occurrence(
            confirmed_published.queue_message_id, "provider-delivery-occurrence-2"
        )

    alternate = _alternate_occurrence_for_same_semantic_request(
        validator, raw_envelope, runtime
    )
    with pytest.raises(QueueStateError, match="cannot receive a new delivery"):
        runtime.deliver(alternate.queue_message_id)
    with pytest.raises(QueueStateError, match="cannot receive a new delivery"):
        runtime.redeliver(first.queue_delivery_id)
    assert all(
        record.queue_message_id != alternate.queue_message_id
        for record in runtime._deliveries.values()
    )


def test_repeated_identical_security_rejection_remains_blocked_without_restoring_authority(
    runtime, claimed
) -> None:
    delivery, claim = claimed
    first = runtime.classify_failure(
        delivery.queue_delivery_id, FailureClassification.SECURITY_REJECTION
    )

    second = runtime.classify_failure(
        delivery.queue_delivery_id, FailureClassification.SECURITY_REJECTION
    )

    assert (first.retry_allowed, first.dead_lettered) == (False, False)
    assert (second.retry_allowed, second.dead_lettered) == (False, False)
    assert second.workflow_terminal is False
    assert runtime.claim_record(claim.claim_or_lease_id).state == ClaimState.REVOKED
    assert not runtime.can_produce_protected_effect(claim.claim_or_lease_id)
    assert not runtime.can_process(delivery.queue_delivery_id)
    with pytest.raises(QueueStateError, match="cannot receive a new delivery"):
        runtime.deliver(delivery.queue_message_id)


def test_protected_result_acceptance_fails_closed_after_security_rejection(
    runtime, claimed, binding_factory
) -> None:
    delivery, claim = claimed
    runtime.classify_failure(
        delivery.queue_delivery_id, FailureClassification.SECURITY_REJECTION
    )

    with pytest.raises(QueueStateError, match="protected effect"):
        runtime.accept_result(
            claim.claim_or_lease_id, binding_factory(), "submission-post-rejection"
        )
    assert runtime._accepted_results == {}


# ---------------------------------------------------------------------------
# Preservation of existing ordinary Queue semantics
# ---------------------------------------------------------------------------


def test_ordinary_transport_retry_bounds_are_preserved(
    runtime, confirmed_published
) -> None:
    delivery = runtime.deliver(confirmed_published.queue_message_id)

    first = runtime.classify_failure(
        delivery.queue_delivery_id, FailureClassification.TRANSPORT_RETRYABLE
    )
    second = runtime.classify_failure(
        delivery.queue_delivery_id, FailureClassification.TRANSPORT_RETRYABLE
    )

    assert first.retry_allowed and not first.dead_lettered
    assert second.dead_lettered and not second.retry_allowed


def test_application_failure_non_retry_behavior_is_preserved_without_stickiness(
    runtime, confirmed_published
) -> None:
    delivery = runtime.deliver(confirmed_published.queue_message_id)

    application_decision = runtime.classify_failure(
        delivery.queue_delivery_id, FailureClassification.APPLICATION
    )
    retry_decision = runtime.classify_failure(
        delivery.queue_delivery_id, FailureClassification.TRANSPORT_RETRYABLE
    )

    assert (application_decision.retry_allowed, application_decision.dead_lettered) == (
        False,
        False,
    )
    assert retry_decision.retry_allowed


def test_poison_dead_letter_and_authorized_non_security_redrive_are_preserved(
    runtime, confirmed_published, redrive_authorization
) -> None:
    source = runtime.deliver(confirmed_published.queue_message_id)
    old_claim = runtime.claim(
        source.queue_delivery_id, WorkerServiceReference("worker-1")
    )

    poison_first = runtime.classify_failure(
        source.queue_delivery_id, FailureClassification.POISON
    )
    poison_second = runtime.classify_failure(
        source.queue_delivery_id, FailureClassification.POISON
    )

    assert poison_first.retry_allowed
    assert poison_second.dead_lettered
    record = runtime.dead_letter(source.queue_delivery_id)
    assert record.classification == FailureClassification.POISON
    assert record.workflow_terminal is False

    redriven = runtime.redrive(
        confirmed_published.queue_message_id,
        "administrator-1",
        redrive_authorization,
    )
    assert redriven.semantic_request_id == source.semantic_request_id
    assert redriven.original_provenance_reference == (
        source.original_provenance_reference
    )
    new_claim = runtime.claim(
        redriven.queue_delivery_id, WorkerServiceReference("worker-redrive")
    )
    assert new_claim.fence > old_claim.fence
    assert runtime.can_produce_protected_effect(new_claim.claim_or_lease_id)
    assert runtime.acknowledgement_eligible(
        redriven.queue_delivery_id,
        new_claim.claim_or_lease_id,
        _ready_readiness(runtime),
    )


@pytest.mark.parametrize(
    "state",
    [ControlState.CANCELLED, ControlState.REVOKED, ControlState.DELETED],
)
def test_non_active_control_states_remain_available_and_restrictive(
    runtime, confirmed_published, state
) -> None:
    delivery = runtime.deliver(confirmed_published.queue_message_id)
    runtime.set_control(confirmed_published.semantic_request_id, state)

    assert not runtime.can_process(delivery.queue_delivery_id)
    with pytest.raises(QueueStateError, match="cannot be claimed"):
        runtime.claim(delivery.queue_delivery_id, WorkerServiceReference("worker-1"))


def test_cancellation_reactivation_rule_without_security_rejection_is_preserved(
    runtime, confirmed_published
) -> None:
    delivery = runtime.deliver(confirmed_published.queue_message_id)
    runtime.set_control(confirmed_published.semantic_request_id, ControlState.CANCELLED)

    with pytest.raises(
        QueueStateError, match="Queue control cannot reactivate invalid work"
    ):
        runtime.set_control(confirmed_published.semantic_request_id, ControlState.ACTIVE)
    assert not runtime.can_process(delivery.queue_delivery_id)


def test_publication_reconciliation_is_preserved(runtime, published) -> None:
    runtime.record_publication_outcome(
        published.publication_identity,
        PublicationState.RESULT_UNCERTAIN,
        "provider-timeout-preservation",
    )
    resolved = runtime.record_publication_outcome(
        published.publication_identity,
        PublicationState.CONFIRMED_SUCCESS,
        "provider-reconciliation-preservation",
    )

    assert resolved.state == PublicationState.CONFIRMED_SUCCESS
    with pytest.raises(QueueConflictError, match="overwritten"):
        runtime.record_publication_outcome(
            published.publication_identity,
            PublicationState.CONFIRMED_FAILURE,
            "provider-conflicting-outcome",
        )


def test_duplicate_result_binding_convergence_is_preserved(
    runtime, claimed, binding_factory
) -> None:
    _, claim = claimed
    binding = binding_factory()

    accepted_first = runtime.accept_result(
        claim.claim_or_lease_id, binding, "submission-duplicate-1"
    )
    accepted_second = runtime.accept_result(
        claim.claim_or_lease_id, binding, "submission-duplicate-2"
    )

    assert accepted_first == accepted_second == binding
    replacement_binding = binding_factory(
        producer_result_id=ProducerResultId("result-conflicting")
    )
    with pytest.raises(QueueConflictError):
        runtime.accept_result(
            claim.claim_or_lease_id,
            replacement_binding,
            "submission-conflicting",
        )
