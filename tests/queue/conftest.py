from collections.abc import Callable

import pytest

from app.queue import (
    QUEUE_CONTRACT_VERSION,
    AdministrativeAuthorizationDecision,
    DurableEffect,
    EnvelopeValidator,
    InMemoryQueueAdapter,
    ProducerResultId,
    PublicationIdentity,
    PublicationState,
    QueueRuntimeLimits,
    ResultBinding,
    RetryPolicy,
    WorkflowAttemptId,
)


@pytest.fixture
def validator() -> EnvelopeValidator:
    return EnvelopeValidator(
        supported_schema_versions=frozenset({"queue-test-v1"}),
        allowed_operations=frozenset({"test.execute"}),
        allowed_metadata_keys=frozenset({"trace_label", "priority"}),
        limits=QueueRuntimeLimits(
            max_field_length=128,
            max_envelope_bytes=4096,
            max_metadata_items=2,
            max_metadata_key_length=32,
            max_metadata_value_length=32,
        ),
    )


@pytest.fixture
def raw_envelope() -> dict[str, object]:
    return {
        "contract_version": QUEUE_CONTRACT_VERSION,
        "schema_version": "queue-test-v1",
        "semantic_request_id": "semantic-1",
        "queue_message_id": "message-1",
        "operation_kind": "test.execute",
        "queue_producer_service_reference": "producer-1",
        "publication_actor_reference": "publisher-1",
        "requester_actor_reference": "requester-1",
        "authorization_context_reference": "auth-context-1",
        "policy_version": "policy-test-v1",
        "workflow_attempt_id": "workflow-attempt-owned-1",
        "publication_identity": "publication-1",
        "publication_state": PublicationState.NOT_ATTEMPTED.value,
        "original_provenance_reference": "provenance-1",
    }


@pytest.fixture
def runtime(validator: EnvelopeValidator) -> InMemoryQueueAdapter:
    return InMemoryQueueAdapter(
        validator=validator,
        retry_policy=RetryPolicy(
            max_transport_attempts=2,
            max_poison_attempts=2,
            max_redrives=1,
        ),
        required_durable_effects=frozenset(
            {
                DurableEffect.ACCEPTED_RESULT,
                DurableEffect.WORKFLOW_STATE,
                DurableEffect.PROVENANCE,
                DurableEffect.AUDIT,
            }
        ),
    )


@pytest.fixture
def published(
    validator: EnvelopeValidator,
    raw_envelope: dict[str, object],
    runtime: InMemoryQueueAdapter,
):
    envelope = validator.validate(raw_envelope)
    runtime.publish(envelope)
    return envelope


@pytest.fixture
def confirmed_published(runtime: InMemoryQueueAdapter, published):
    runtime.record_publication_outcome(
        published.publication_identity,
        PublicationState.CONFIRMED_SUCCESS,
        "provider-publication-success-1",
    )
    return published


@pytest.fixture
def claimed(runtime: InMemoryQueueAdapter, confirmed_published):
    delivery = runtime.deliver(confirmed_published.queue_message_id)
    from app.queue import WorkerServiceReference

    claim = runtime.claim(delivery.queue_delivery_id, WorkerServiceReference("worker-1"))
    return delivery, claim


@pytest.fixture
def binding_factory(published) -> Callable[..., ResultBinding]:
    def make(**changes: object) -> ResultBinding:
        values = {
            "producer_result_id": ProducerResultId("result-owned-1"),
            "semantic_request_id": published.semantic_request_id,
            "queue_message_id": published.queue_message_id,
            "workflow_attempt_id": WorkflowAttemptId("workflow-attempt-owned-1"),
            "result_phase_or_slot_reference": "workflow-result-slot-1",
            "result_reference": "result-reference-1",
        }
        values.update(changes)
        return ResultBinding(**values)  # type: ignore[arg-type]

    return make


@pytest.fixture
def publication_id() -> PublicationIdentity:
    return PublicationIdentity("publication-1")


@pytest.fixture
def redrive_authorization() -> AdministrativeAuthorizationDecision:
    return AdministrativeAuthorizationDecision(
        authorized=True,
        authorization_context_reference="current-redrive-auth-1",
        policy_version="current-redrive-policy-1",
        decision_reference="current-redrive-decision-1",
    )
