import pytest

from app.queue import (
    AckReadiness,
    ClaimState,
    ControlState,
    FailureClassification,
    QueueStateError,
    WorkerServiceReference,
)


def _dead_letter_poison(runtime, confirmed_published):
    delivery = runtime.deliver(confirmed_published.queue_message_id)
    first = runtime.classify_failure(
        delivery.queue_delivery_id, FailureClassification.POISON
    )
    second = runtime.classify_failure(
        delivery.queue_delivery_id, FailureClassification.POISON
    )
    return delivery, first, second


def test_poison_work_reaches_bounded_dead_letter(runtime, confirmed_published) -> None:
    _, first, second = _dead_letter_poison(runtime, confirmed_published)

    assert first.retry_allowed and not first.dead_lettered
    assert not second.retry_allowed and second.dead_lettered


def test_application_failure_is_not_automatically_poison(
    runtime, confirmed_published
) -> None:
    delivery = runtime.deliver(confirmed_published.queue_message_id)

    decision = runtime.classify_failure(
        delivery.queue_delivery_id, FailureClassification.APPLICATION
    )

    assert not decision.retry_allowed
    assert not decision.dead_lettered


def test_cancellation_is_not_a_retry_classification(
    runtime, confirmed_published
) -> None:
    delivery = runtime.deliver(confirmed_published.queue_message_id)
    runtime.set_control(
        confirmed_published.semantic_request_id, ControlState.CANCELLED
    )

    with pytest.raises(QueueStateError, match="not a retry classification"):
        runtime.classify_failure(
            delivery.queue_delivery_id, FailureClassification.TRANSPORT_RETRYABLE
        )


def test_security_rejection_is_not_ordinary_retry(
    runtime, confirmed_published
) -> None:
    delivery = runtime.deliver(confirmed_published.queue_message_id)

    decision = runtime.classify_failure(
        delivery.queue_delivery_id, FailureClassification.SECURITY_REJECTION
    )

    assert not decision.retry_allowed
    assert not decision.dead_lettered


def test_transport_retry_is_bounded(runtime, confirmed_published) -> None:
    delivery = runtime.deliver(confirmed_published.queue_message_id)

    first = runtime.classify_failure(
        delivery.queue_delivery_id, FailureClassification.TRANSPORT_RETRYABLE
    )
    second = runtime.classify_failure(
        delivery.queue_delivery_id, FailureClassification.TRANSPORT_RETRYABLE
    )

    assert first.retry_allowed
    assert second.dead_lettered


def test_dead_letter_does_not_imply_workflow_terminal_state(
    runtime, confirmed_published
) -> None:
    delivery, _, _ = _dead_letter_poison(runtime, confirmed_published)

    record = runtime.dead_letter(delivery.queue_delivery_id)

    assert record.workflow_terminal is False


def test_redrive_is_explicit_and_creates_new_delivery_identity(
    runtime, confirmed_published, redrive_authorization
) -> None:
    source, _, _ = _dead_letter_poison(runtime, confirmed_published)

    redriven = runtime.redrive(
        confirmed_published.queue_message_id,
        "administrator-1",
        redrive_authorization,
    )

    assert redriven.queue_delivery_id != source.queue_delivery_id


def test_dead_lettered_work_cannot_bypass_redrive_authorization(
    runtime, confirmed_published
) -> None:
    source, _, _ = _dead_letter_poison(runtime, confirmed_published)

    with pytest.raises(QueueStateError, match="explicit redrive"):
        runtime.redeliver(source.queue_delivery_id)
    with pytest.raises(QueueStateError, match="explicit redrive"):
        runtime.deliver(confirmed_published.queue_message_id)


def test_redrive_preserves_semantic_and_original_provenance(
    runtime, confirmed_published, redrive_authorization
) -> None:
    source, _, _ = _dead_letter_poison(runtime, confirmed_published)

    redriven = runtime.redrive(
        source.queue_delivery_id,
        "administrator-1",
        redrive_authorization,
    )

    assert redriven.semantic_request_id == source.semantic_request_id
    assert redriven.queue_message_id == source.queue_message_id
    assert redriven.original_provenance_reference == source.original_provenance_reference
    assert redriven.workflow_attempt_id == source.workflow_attempt_id


@pytest.mark.parametrize(
    "state",
    [ControlState.CANCELLED, ControlState.DELETED, ControlState.REVOKED],
)
def test_cancelled_deleted_or_revoked_work_cannot_redrive(
    runtime, confirmed_published, redrive_authorization, state
) -> None:
    _dead_letter_poison(runtime, confirmed_published)
    runtime.set_control(confirmed_published.semantic_request_id, state)

    with pytest.raises(QueueStateError, match="redriven"):
        runtime.redrive(
            confirmed_published.queue_message_id,
            "administrator-1",
            redrive_authorization,
        )


def test_redrive_does_not_reuse_stale_claim(
    runtime, confirmed_published, redrive_authorization
) -> None:
    source = runtime.deliver(confirmed_published.queue_message_id)
    old_claim = runtime.claim(source.queue_delivery_id, WorkerServiceReference("worker-1"))
    runtime.classify_failure(source.queue_delivery_id, FailureClassification.POISON)
    runtime.classify_failure(source.queue_delivery_id, FailureClassification.POISON)
    redriven = runtime.redrive(
        confirmed_published.queue_message_id,
        "administrator-1",
        redrive_authorization,
    )

    assert not runtime.acknowledgement_eligible(
        redriven.queue_delivery_id,
        old_claim.claim_or_lease_id,
        AckReadiness(True, runtime.required_durable_effects),
    )


def test_dead_letter_revokes_source_claim_effect_and_ack_authority(
    runtime, confirmed_published, binding_factory
) -> None:
    source = runtime.deliver(confirmed_published.queue_message_id)
    claim = runtime.claim(source.queue_delivery_id, WorkerServiceReference("worker-1"))
    runtime.classify_failure(source.queue_delivery_id, FailureClassification.POISON)
    runtime.classify_failure(source.queue_delivery_id, FailureClassification.POISON)

    assert runtime.claim_record(claim.claim_or_lease_id).state == ClaimState.REVOKED
    assert not runtime.can_produce_protected_effect(claim.claim_or_lease_id)
    with pytest.raises(QueueStateError, match="protected effect"):
        runtime.accept_result(
            claim.claim_or_lease_id, binding_factory(), "submission-after-dead-letter"
        )
    assert not runtime.acknowledge(
        source.queue_delivery_id,
        claim.claim_or_lease_id,
        AckReadiness(True, runtime.required_durable_effects),
    )


def test_redriven_delivery_requires_new_claim_for_ack_and_protected_work(
    runtime, confirmed_published, redrive_authorization
) -> None:
    source = runtime.deliver(confirmed_published.queue_message_id)
    source_claim = runtime.claim(
        source.queue_delivery_id, WorkerServiceReference("worker-source")
    )
    runtime.classify_failure(source.queue_delivery_id, FailureClassification.POISON)
    runtime.classify_failure(source.queue_delivery_id, FailureClassification.POISON)
    redriven = runtime.redrive(
        confirmed_published.queue_message_id,
        "administrator-1",
        redrive_authorization,
    )

    assert not runtime.can_produce_protected_effect(source_claim.claim_or_lease_id)
    assert not runtime.acknowledgement_eligible(
        redriven.queue_delivery_id,
        source_claim.claim_or_lease_id,
        AckReadiness(True, runtime.required_durable_effects),
    )
    new_claim = runtime.claim(
        redriven.queue_delivery_id, WorkerServiceReference("worker-redrive")
    )
    assert new_claim.queue_delivery_id == redriven.queue_delivery_id
    assert new_claim.claim_or_lease_id != source_claim.claim_or_lease_id
    assert new_claim.fence > source_claim.fence
    assert runtime.can_produce_protected_effect(new_claim.claim_or_lease_id)
    assert runtime.acknowledgement_eligible(
        redriven.queue_delivery_id,
        new_claim.claim_or_lease_id,
        AckReadiness(True, runtime.required_durable_effects),
    )


def test_redriven_delivery_has_independent_retry_and_dead_letter_disposition(
    runtime, confirmed_published, redrive_authorization
) -> None:
    source, _, _ = _dead_letter_poison(runtime, confirmed_published)
    source_dead_letter = runtime.dead_letter(source.queue_delivery_id)
    redriven = runtime.redrive(
        confirmed_published.queue_message_id,
        "administrator-1",
        redrive_authorization,
    )

    first = runtime.classify_failure(
        redriven.queue_delivery_id, FailureClassification.TRANSPORT_RETRYABLE
    )
    second = runtime.classify_failure(
        redriven.queue_delivery_id, FailureClassification.TRANSPORT_RETRYABLE
    )

    assert first.retry_allowed and not first.dead_lettered
    assert second.dead_lettered and not second.retry_allowed
    redrive_dead_letter = runtime.dead_letter(redriven.queue_delivery_id)
    assert redrive_dead_letter is not source_dead_letter
    assert redrive_dead_letter.classification == FailureClassification.TRANSPORT_RETRYABLE
    assert runtime.dead_letter(source.queue_delivery_id) is source_dead_letter
    assert source_dead_letter.classification == FailureClassification.POISON


def test_redrive_limit_is_bounded(
    runtime, confirmed_published, redrive_authorization
) -> None:
    _dead_letter_poison(runtime, confirmed_published)
    runtime.redrive(
        confirmed_published.queue_message_id,
        "administrator-1",
        redrive_authorization,
    )

    with pytest.raises(QueueStateError, match="limit"):
        runtime.redrive(
            confirmed_published.queue_message_id,
            "administrator-1",
            redrive_authorization,
        )
