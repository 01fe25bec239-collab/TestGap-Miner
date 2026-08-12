import pytest

from app.queue import (
    AckReadiness,
    ClaimState,
    ControlState,
    DurableEffect,
    QueueConflictError,
    QueueStateError,
    WorkerServiceReference,
)


ALL_READY = frozenset(
    {
        DurableEffect.ACCEPTED_RESULT,
        DurableEffect.WORKFLOW_STATE,
        DurableEffect.PROVENANCE,
        DurableEffect.AUDIT,
    }
)


def test_valid_current_claim_can_produce_protected_effect(runtime, claimed) -> None:
    _, claim = claimed

    assert runtime.can_produce_protected_effect(claim.claim_or_lease_id)


def test_replacement_makes_previous_claim_stale(runtime, claimed) -> None:
    delivery, old_claim = claimed
    new_claim = runtime.claim(
        delivery.queue_delivery_id, WorkerServiceReference("worker-2")
    )

    assert runtime.claim_record(old_claim.claim_or_lease_id).state == ClaimState.REPLACED
    assert not runtime.can_produce_protected_effect(old_claim.claim_or_lease_id)
    assert new_claim.fence > old_claim.fence


def test_stale_claim_cannot_produce_protected_effect(
    runtime, claimed, binding_factory
) -> None:
    delivery, old_claim = claimed
    runtime.claim(delivery.queue_delivery_id, WorkerServiceReference("worker-2"))

    with pytest.raises(QueueStateError, match="protected effect"):
        runtime.accept_result(
            old_claim.claim_or_lease_id, binding_factory(), "submission-stale"
        )


def test_stale_claim_cannot_acknowledge_success(runtime, claimed) -> None:
    delivery, old_claim = claimed
    runtime.claim(delivery.queue_delivery_id, WorkerServiceReference("worker-2"))

    assert not runtime.acknowledge(
        delivery.queue_delivery_id,
        old_claim.claim_or_lease_id,
        AckReadiness(True, ALL_READY),
    )


def test_confirmed_lease_loss_blocks_protected_effect(
    runtime, claimed, binding_factory
) -> None:
    _, claim = claimed
    runtime.confirm_lease_loss(claim.claim_or_lease_id)

    assert not runtime.can_produce_protected_effect(claim.claim_or_lease_id)
    with pytest.raises(QueueStateError):
        runtime.accept_result(
            claim.claim_or_lease_id, binding_factory(), "submission-lost"
        )


def test_renewal_uncertainty_pauses_protected_effects(runtime, claimed) -> None:
    _, claim = claimed

    uncertain = runtime.mark_renewal_uncertain(claim.claim_or_lease_id)

    assert uncertain.state == ClaimState.RENEWAL_UNCERTAIN
    assert not runtime.can_produce_protected_effect(claim.claim_or_lease_id)


def test_confirmed_lease_loss_is_irreversible(runtime, claimed) -> None:
    _, claim = claimed
    runtime.confirm_lease_loss(claim.claim_or_lease_id)

    with pytest.raises(QueueStateError, match="irreversible"):
        runtime.mark_renewal_uncertain(claim.claim_or_lease_id)


def test_lease_loss_before_acknowledgement_blocks_ack(runtime, claimed) -> None:
    delivery, claim = claimed
    runtime.confirm_lease_loss(claim.claim_or_lease_id)

    assert not runtime.acknowledgement_eligible(
        delivery.queue_delivery_id,
        claim.claim_or_lease_id,
        AckReadiness(True, ALL_READY),
    )


def test_execution_success_without_durable_readiness_is_not_ack_eligible(
    runtime, claimed
) -> None:
    delivery, claim = claimed

    assert not runtime.acknowledgement_eligible(
        delivery.queue_delivery_id,
        claim.claim_or_lease_id,
        AckReadiness(True, frozenset()),
    )


def test_complete_external_durable_readiness_enables_ack(runtime, claimed) -> None:
    delivery, claim = claimed

    assert runtime.acknowledge(
        delivery.queue_delivery_id,
        claim.claim_or_lease_id,
        AckReadiness(True, ALL_READY),
    )


def test_execution_failure_is_not_ack_eligible(runtime, claimed) -> None:
    delivery, claim = claimed

    assert not runtime.acknowledgement_eligible(
        delivery.queue_delivery_id,
        claim.claim_or_lease_id,
        AckReadiness(False, ALL_READY),
    )


def test_conflicting_result_is_not_ack_eligible(
    runtime, claimed, binding_factory
) -> None:
    delivery, claim = claimed
    runtime.accept_result(claim.claim_or_lease_id, binding_factory(), "submission-1")
    with pytest.raises(QueueConflictError):
        runtime.accept_result(
            claim.claim_or_lease_id,
            binding_factory(result_reference="conflict"),
            "submission-2",
        )

    assert not runtime.acknowledgement_eligible(
        delivery.queue_delivery_id,
        claim.claim_or_lease_id,
        AckReadiness(True, ALL_READY),
    )


def test_cancellation_before_processing_blocks(runtime, confirmed_published) -> None:
    delivery = runtime.deliver(confirmed_published.queue_message_id)
    runtime.set_control(
        confirmed_published.semantic_request_id, ControlState.CANCELLED
    )

    assert not runtime.can_process(delivery.queue_delivery_id)
    with pytest.raises(QueueStateError):
        runtime.claim(delivery.queue_delivery_id, WorkerServiceReference("worker"))


def test_cancellation_before_protected_effect_blocks(
    runtime, claimed, binding_factory
) -> None:
    _, claim = claimed
    runtime.set_control(binding_factory().semantic_request_id, ControlState.CANCELLED)

    with pytest.raises(QueueStateError):
        runtime.accept_result(
            claim.claim_or_lease_id, binding_factory(), "submission-cancelled"
        )


def test_cancellation_before_acknowledgement_blocks(runtime, claimed) -> None:
    delivery, claim = claimed
    runtime.set_control(delivery.semantic_request_id, ControlState.CANCELLED)

    assert not runtime.acknowledge(
        delivery.queue_delivery_id,
        claim.claim_or_lease_id,
        AckReadiness(True, ALL_READY),
    )


def test_redelivery_cannot_reactivate_cancelled_work(
    runtime, confirmed_published
) -> None:
    first = runtime.deliver(confirmed_published.queue_message_id)
    runtime.set_control(
        confirmed_published.semantic_request_id, ControlState.CANCELLED
    )
    redelivery = runtime.redeliver(first.queue_delivery_id)

    assert not runtime.can_process(redelivery.queue_delivery_id)
    with pytest.raises(QueueStateError, match="reactivate"):
        runtime.set_control(
            confirmed_published.semantic_request_id, ControlState.ACTIVE
        )
