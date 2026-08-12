import pytest

from app.queue import (
    ProducerResultId,
    PublicationIdentity,
    PublicationState,
    QueueConflictError,
    QueueMessageId,
    SemanticRequestId,
    WorkerServiceReference,
)


def test_message_semantic_identity_mismatch_is_rejected(
    validator, raw_envelope, runtime
) -> None:
    first = validator.validate(raw_envelope)
    runtime.publish(first)
    raw_envelope["semantic_request_id"] = "semantic-conflict"
    raw_envelope["publication_identity"] = "publication-2"

    with pytest.raises(QueueConflictError, match="message"):
        runtime.publish(validator.validate(raw_envelope))


def test_message_operation_binding_mismatch_is_rejected(
    validator, raw_envelope, runtime
) -> None:
    other_validator = type(validator)(
        validator.supported_schema_versions,
        frozenset({"test.execute", "other.operation"}),
        validator.allowed_metadata_keys,
        validator.limits,
    )
    runtime = type(runtime)(
        other_validator, runtime.retry_policy, runtime.required_durable_effects
    )
    runtime.publish(other_validator.validate(raw_envelope))
    raw_envelope["operation_kind"] = "other.operation"
    raw_envelope["publication_identity"] = "publication-2"

    with pytest.raises(QueueConflictError, match="message"):
        runtime.publish(other_validator.validate(raw_envelope))


def test_redelivery_creates_new_delivery_identity(runtime, confirmed_published) -> None:
    first = runtime.deliver(confirmed_published.queue_message_id)
    second = runtime.redeliver(first.queue_delivery_id)

    assert second.queue_delivery_id != first.queue_delivery_id
    assert second.queue_message_id == first.queue_message_id
    assert second.redelivery_number == 1


def test_redelivery_does_not_create_workflow_attempt(
    runtime, confirmed_published
) -> None:
    first = runtime.deliver(confirmed_published.queue_message_id)
    second = runtime.redeliver(first.queue_delivery_id)

    assert first.workflow_attempt_id is confirmed_published.workflow_attempt_id
    assert second.workflow_attempt_id is confirmed_published.workflow_attempt_id


def test_redelivery_without_attempt_keeps_attempt_absent(
    validator, raw_envelope, runtime
) -> None:
    raw_envelope.pop("workflow_attempt_id")
    envelope = validator.validate(raw_envelope)
    runtime.publish(envelope)
    runtime.record_publication_outcome(
        envelope.publication_identity,
        PublicationState.CONFIRMED_SUCCESS,
        "provider-publication-success-without-attempt",
    )

    first = runtime.deliver(envelope.queue_message_id)
    second = runtime.redeliver(first.queue_delivery_id)

    assert first.workflow_attempt_id is None
    assert second.workflow_attempt_id is None


def test_duplicate_same_result_binding_converges(
    runtime, claimed, binding_factory
) -> None:
    _, claim = claimed
    binding = binding_factory()

    first = runtime.accept_result(claim.claim_or_lease_id, binding, "submission-1")
    second = runtime.accept_result(claim.claim_or_lease_id, binding, "submission-1")

    assert first is second


def test_duplicate_conflicting_result_fails_closed_and_preserves_accepted(
    runtime, claimed, binding_factory
) -> None:
    _, claim = claimed
    accepted = binding_factory()
    runtime.accept_result(claim.claim_or_lease_id, accepted, "submission-1")
    conflict = binding_factory(result_reference="different-reference")

    with pytest.raises(QueueConflictError, match="conflicting"):
        runtime.accept_result(claim.claim_or_lease_id, conflict, "submission-2")

    assert runtime.accepted_result(accepted.producer_result_id) is accepted


def test_result_identity_is_externally_supplied_and_stable_across_replacement(
    runtime, claimed, binding_factory
) -> None:
    delivery, first_claim = claimed
    accepted = binding_factory(producer_result_id=ProducerResultId("external-result"))
    runtime.accept_result(first_claim.claim_or_lease_id, accepted, "submission-1")
    replacement = runtime.claim(
        delivery.queue_delivery_id, WorkerServiceReference("worker-2")
    )

    converged = runtime.accept_result(
        replacement.claim_or_lease_id, accepted, "submission-2"
    )

    assert converged.producer_result_id == ProducerResultId("external-result")


def test_uncertain_publication_preserves_history_until_resolution(
    runtime, published
) -> None:
    outcome = runtime.record_publication_outcome(
        published.publication_identity,
        PublicationState.RESULT_UNCERTAIN,
        "provider-timeout-1",
    )

    assert outcome.state == PublicationState.RESULT_UNCERTAIN
    assert runtime.publication(published.publication_identity).state == (
        PublicationState.RESULT_UNCERTAIN
    )
    resolved = runtime.record_publication_outcome(
        published.publication_identity,
        PublicationState.CONFIRMED_FAILURE,
        "provider-reconciliation-1",
    )

    assert resolved.state == PublicationState.CONFIRMED_FAILURE
    assert [item.state for item in runtime.publication_history(published.publication_identity)] == [
        PublicationState.RESULT_UNCERTAIN,
        PublicationState.CONFIRMED_FAILURE,
    ]


@pytest.mark.parametrize(
    "state",
    [
        PublicationState.REJECTED_BEFORE_ACCEPTANCE,
        PublicationState.CONFIRMED_FAILURE,
        PublicationState.CONFIRMED_SUCCESS,
    ],
)
def test_publication_outcomes_remain_distinct(runtime, published, state) -> None:
    assert runtime.record_publication_outcome(
        published.publication_identity, state, f"provider-outcome-{state.value}"
    ).state == state


def test_duplicate_publication_reconciles_without_overwriting_success(
    runtime, published
) -> None:
    runtime.record_publication_outcome(
        published.publication_identity,
        PublicationState.CONFIRMED_SUCCESS,
        "provider-success-1",
    )

    duplicate = runtime.publish(published)

    assert duplicate.state == PublicationState.CONFIRMED_SUCCESS
    assert runtime.publication(published.publication_identity).state == (
        PublicationState.CONFIRMED_SUCCESS
    )


def test_conflicting_publication_identity_binding_is_rejected(
    validator, raw_envelope, runtime
) -> None:
    runtime.publish(validator.validate(raw_envelope))
    raw_envelope["queue_message_id"] = "other-message"

    with pytest.raises(QueueConflictError, match="publication identity"):
        runtime.publish(validator.validate(raw_envelope))


def test_queue_message_binding_cannot_be_overwritten(runtime, published) -> None:
    assert published.queue_message_id == QueueMessageId("message-1")
    assert published.semantic_request_id == SemanticRequestId("semantic-1")
    assert runtime.publish(published).publication_identity == PublicationIdentity(
        "publication-1"
    )
