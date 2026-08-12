from copy import deepcopy
from dataclasses import replace

import pytest

from app.queue import (
    AdministrativeAuthorizationDecision,
    AckReadiness,
    CausationId,
    ClaimOrLeaseId,
    ControlState,
    CorrelationId,
    FailureClassification,
    InMemoryQueueAdapter,
    ProducerResultId,
    PublicationIdentity,
    PublicationState,
    QueueConflictError,
    QueueDeliveryId,
    QueueEnvelope,
    QueueMessageId,
    QueueProducerServiceReference,
    QueueStateError,
    QueueValidationError,
    SemanticRequestId,
    WorkerServiceReference,
    WorkflowAttemptId,
)


PROHIBITED_RUNTIME_IDENTITIES = (
    "Authorization: Bearer secret",
    "Bearer secret",
    "Cookie: session-secret",
    "cookie=session-secret",
    "raw command: rm -rf project",
    "rm -rf project",
    "prompt: explain the complete repository",
    "full prompt and model context",
    "model context: confidential context",
    "repository contents: <embedded source>",
    "diff --git a/file b/file",
    "patch content: ...",
)


def _publication_outcome(runtime, published, state: PublicationState) -> None:
    runtime.record_publication_outcome(
        published.publication_identity,
        state,
        f"provider-outcome-{state.name.lower()}",
    )


def _dead_letter(runtime, published):
    delivery = runtime.deliver(published.queue_message_id)
    runtime.classify_failure(delivery.queue_delivery_id, FailureClassification.POISON)
    runtime.classify_failure(delivery.queue_delivery_id, FailureClassification.POISON)
    return delivery


@pytest.mark.parametrize(
    "change",
    [
        {"contract_version": "1.0.0-draft.1"},
        {"schema_version": "future-schema"},
        {"semantic_request_id": "plain-string"},
        {"semantic_request_id": QueueMessageId("wrong-runtime-type")},
        {"operation_kind": "unsupported.operation"},
        {"publication_state": "unknown-publication-state"},
        {"bounded_metadata": (("trace_label", "Bearer secret"),)},
        {"input_reference": "cookie=session-secret"},
        {"input_reference": "prompt: explain the complete repository"},
    ],
)
def test_direct_envelope_construction_cannot_bypass_publication_validation(
    runtime, validator, raw_envelope, change
) -> None:
    envelope = validator.validate(raw_envelope)

    with pytest.raises(QueueValidationError):
        runtime.publish(replace(envelope, **change))


def test_publication_rejects_non_envelope_values(runtime) -> None:
    with pytest.raises(QueueValidationError, match="QueueEnvelope"):
        runtime.publish("not-an-envelope")  # type: ignore[arg-type]


def test_publication_rejects_conflated_typed_identities(
    runtime, validator, raw_envelope
) -> None:
    envelope = validator.validate(raw_envelope)
    conflated = replace(
        envelope,
        queue_message_id=QueueMessageId(envelope.semantic_request_id.value),
    )

    with pytest.raises(QueueValidationError, match="conflated"):
        runtime.publish(conflated)


def test_publication_rejects_fabricated_claim_binding(
    runtime, validator, raw_envelope
) -> None:
    raw_envelope.update(
        {
            "queue_message_id": "result-message",
            "publication_identity": "result-publication",
            "queue_delivery_id": QueueDeliveryId("fabricated-delivery"),
            "claim_or_lease_id": ClaimOrLeaseId("fabricated-claim"),
            "worker_service_reference": WorkerServiceReference("fabricated-worker"),
            "fence": 42,
            "producer_result_id": ProducerResultId("external-result"),
            "result_phase_or_slot_reference": "workflow-slot-1",
            "result_reference": "result-reference-1",
        }
    )

    with pytest.raises(QueueStateError, match="not current"):
        runtime.publish(validator.validate(raw_envelope))


@pytest.mark.parametrize(
    "field,value",
    [
        ("publication_actor_reference", "Authorization: Bearer secret"),
        ("requester_actor_reference", "Bearer secret"),
        ("input_reference", "raw command: rm -rf project"),
        ("checkpoint_reference", "full prompt and model context"),
        ("evidence_reference_id", "patch/repository-like embedded material"),
        ("integrity_metadata", "raw repository material"),
    ],
)
def test_prohibited_content_is_rejected_from_every_serialized_reference_kind(
    validator, raw_envelope, field, value
) -> None:
    raw_envelope[field] = value

    with pytest.raises(QueueValidationError, match="prohibited"):
        validator.validate(raw_envelope)


@pytest.mark.parametrize(
    "value",
    [
        "cookie=session-secret",
        "Cookie: session-secret",
        "rm -rf project",
        "raw command: rm -rf project",
        "prompt: explain the complete repository",
        "full prompt and model context",
        "model context: complete hidden context",
        "repository contents: complete source tree",
        "diff --git a/source.py b/source.py",
        "patch content: replace complete source",
        "Authorization: Bearer secret",
        "Bearer secret",
    ],
)
def test_a4_prohibited_input_reference_probes_fail_closed(
    validator, raw_envelope, value
) -> None:
    raw_envelope["input_reference"] = value

    with pytest.raises(QueueValidationError, match="prohibited"):
        validator.validate(raw_envelope)


@pytest.mark.parametrize(
    "field,value",
    [
        ("checkpoint_reference", "Cookie: session-secret"),
        ("result_reference", "prompt: reveal model context"),
        ("evidence_reference_id", "repository contents: source"),
        ("original_provenance_reference", "patch content: source patch"),
        ("cancellation_intent_reference", "raw command: rm -rf project"),
        ("authorization_context_reference", "Authorization: Bearer secret"),
        ("policy_version", "full prompt and model context"),
        ("requester_actor_reference", "cookie=session-secret"),
        ("correlation_id", "diff --git a/source b/source"),
    ],
)
def test_prohibited_content_guard_covers_other_serialized_references(
    validator, raw_envelope, field, value
) -> None:
    raw_envelope[field] = value

    with pytest.raises(QueueValidationError, match="prohibited"):
        validator.validate(raw_envelope)


def test_security_hook_applies_outside_metadata(raw_envelope) -> None:
    from app.queue import EnvelopeValidator, QueueRuntimeLimits

    validator = EnvelopeValidator(
        frozenset({"queue-test-v1"}),
        frozenset({"test.execute"}),
        frozenset(),
        QueueRuntimeLimits(128, 4096, 2, 32, 32),
        security_policy=lambda field, value: field != "input_reference",
    )
    raw_envelope["input_reference"] = "opaque-input-1"

    with pytest.raises(QueueValidationError, match="Security policy"):
        validator.validate(raw_envelope)


@pytest.mark.parametrize("value", PROHIBITED_RUNTIME_IDENTITIES)
def test_claim_rejects_prohibited_worker_service_reference_without_state_change(
    runtime, confirmed_published, value
) -> None:
    delivery = runtime.deliver(confirmed_published.queue_message_id)

    with pytest.raises(QueueValidationError, match="prohibited"):
        runtime.claim(delivery.queue_delivery_id, WorkerServiceReference(value))

    claim = runtime.claim(
        delivery.queue_delivery_id, WorkerServiceReference("valid-worker")
    )
    assert claim.claim_or_lease_id == ClaimOrLeaseId("claim-1")
    assert claim.fence == 1


def test_claim_security_hook_is_invoked_and_rejection_leaves_no_claim(
    runtime, confirmed_published
) -> None:
    calls = []
    delivery = runtime.deliver(confirmed_published.queue_message_id)

    def security_policy(field, value):
        calls.append((field, value))
        return value != "rejected-worker"

    runtime.validator = replace(runtime.validator, security_policy=security_policy)

    with pytest.raises(QueueValidationError, match="Security policy"):
        runtime.claim(
            delivery.queue_delivery_id, WorkerServiceReference("rejected-worker")
        )

    assert calls == [("worker_service_reference", "rejected-worker")]
    claim = runtime.claim(
        delivery.queue_delivery_id, WorkerServiceReference("accepted-worker")
    )
    assert claim.claim_or_lease_id == ClaimOrLeaseId("claim-1")
    assert claim.fence == 1


@pytest.mark.parametrize("value", PROHIBITED_RUNTIME_IDENTITIES)
def test_accept_result_rejects_prohibited_producer_result_id_without_state_change(
    runtime, claimed, binding_factory, value
) -> None:
    _, claim = claimed
    producer_result_id = ProducerResultId(value)

    with pytest.raises(QueueValidationError, match="prohibited"):
        runtime.accept_result(
            claim.claim_or_lease_id,
            binding_factory(producer_result_id=producer_result_id),
            "submission-prohibited-result-id",
        )

    assert producer_result_id not in runtime._accepted_results
    assert producer_result_id not in runtime._result_submissions


@pytest.mark.parametrize(
    "changes,match",
    [
        ({"producer_result_id": "result-only"}, "result submission"),
        ({"cancellation_actor_reference": "actor-only"}, "cancellation"),
        ({"cancellation_intent_reference": "intent-only"}, "cancellation"),
        ({"replay_or_redrive_actor_reference": "admin-only"}, "redrive"),
        ({"checkpoint_reference": "checkpoint-1", "workflow_attempt_id": None}, "checkpoint"),
        ({"publication_identity": None}, "publication"),
    ],
)
def test_conditional_field_groups_fail_closed(
    validator, raw_envelope, changes, match
) -> None:
    raw_envelope.update(changes)

    with pytest.raises(QueueValidationError, match=match):
        validator.validate(raw_envelope)


def test_second_local_publish_preserves_not_attempted(runtime, published) -> None:
    assert runtime.publish(published).state == PublicationState.NOT_ATTEMPTED
    assert runtime.publication(published.publication_identity).state == (
        PublicationState.NOT_ATTEMPTED
    )


def test_authoritative_duplicate_outcome_is_explicit_and_attributable(
    runtime, published
) -> None:
    outcome = runtime.record_publication_outcome(
        published.publication_identity,
        PublicationState.CONFIRMED_DUPLICATE_REQUEST,
        "provider-recognized-duplicate-1",
    )

    assert outcome.state == PublicationState.CONFIRMED_DUPLICATE_REQUEST
    assert runtime.publication_history(published.publication_identity)[0].outcome_reference == (
        "provider-recognized-duplicate-1"
    )


@pytest.mark.parametrize(
    "definitive",
    [
        PublicationState.REJECTED_BEFORE_ACCEPTANCE,
        PublicationState.CONFIRMED_FAILURE,
        PublicationState.CONFIRMED_SUCCESS,
        PublicationState.CONFIRMED_DUPLICATE_REQUEST,
    ],
)
def test_uncertain_publication_reconciles_only_through_attributable_outcome(
    runtime, published, definitive
) -> None:
    runtime.record_publication_outcome(
        published.publication_identity,
        PublicationState.RESULT_UNCERTAIN,
        "provider-timeout-1",
    )

    resolved = runtime.record_publication_outcome(
        published.publication_identity,
        definitive,
        "provider-reconciliation-1",
    )

    assert resolved.state == definitive
    assert len(runtime.publication_history(published.publication_identity)) == 2


def test_confirmed_publication_outcome_cannot_be_overwritten(runtime, published) -> None:
    _publication_outcome(runtime, published, PublicationState.CONFIRMED_SUCCESS)

    with pytest.raises(QueueConflictError, match="overwritten"):
        _publication_outcome(runtime, published, PublicationState.CONFIRMED_FAILURE)


@pytest.mark.parametrize(
    "state",
    [
        PublicationState.NOT_ATTEMPTED,
        PublicationState.REJECTED_BEFORE_ACCEPTANCE,
        PublicationState.CONFIRMED_FAILURE,
        PublicationState.RESULT_UNCERTAIN,
    ],
)
def test_delivery_is_forbidden_without_valid_publication_occurrence(
    runtime, published, state
) -> None:
    if state != PublicationState.NOT_ATTEMPTED:
        _publication_outcome(runtime, published, state)

    with pytest.raises(QueueStateError, match="delivery"):
        runtime.deliver(published.queue_message_id)


def test_uncertain_publication_requires_explicit_provider_delivery_occurrence(
    runtime, published
) -> None:
    _publication_outcome(runtime, published, PublicationState.RESULT_UNCERTAIN)

    delivery = runtime.record_provider_delivery_occurrence(
        published.queue_message_id, "provider-delivery-occurrence-1"
    )

    assert delivery.provider_delivery_reference == "provider-delivery-occurrence-1"


@pytest.mark.parametrize(
    "state",
    [
        PublicationState.CONFIRMED_SUCCESS,
        PublicationState.CONFIRMED_DUPLICATE_REQUEST,
    ],
)
def test_definitive_acceptance_states_allow_delivery(runtime, published, state) -> None:
    _publication_outcome(runtime, published, state)

    assert runtime.deliver(published.queue_message_id).queue_message_id == (
        published.queue_message_id
    )


def test_different_result_id_for_same_workflow_slot_fails_closed(
    runtime, claimed, binding_factory
) -> None:
    delivery, first_claim = claimed
    accepted = binding_factory()
    runtime.accept_result(first_claim.claim_or_lease_id, accepted, "submission-1")
    replacement = runtime.claim(
        delivery.queue_delivery_id, WorkerServiceReference("worker-2")
    )

    with pytest.raises(QueueConflictError, match="result slot"):
        runtime.accept_result(
            replacement.claim_or_lease_id,
            binding_factory(producer_result_id=ProducerResultId("different-result")),
            "submission-2",
        )

    assert runtime.accepted_result(accepted.producer_result_id) == accepted


def test_result_submission_provenance_is_append_only_across_recovery(
    runtime, claimed, binding_factory
) -> None:
    delivery, first_claim = claimed
    binding = binding_factory()
    runtime.accept_result(first_claim.claim_or_lease_id, binding, "submission-1")
    replacement = runtime.claim(
        delivery.queue_delivery_id, WorkerServiceReference("worker-2")
    )
    runtime.accept_result(replacement.claim_or_lease_id, binding, "submission-2")

    submissions = runtime.result_submissions(binding.producer_result_id)
    assert [item.submission_occurrence_reference for item in submissions] == [
        "submission-1",
        "submission-2",
    ]
    assert submissions[0].claim_or_lease_id != submissions[1].claim_or_lease_id
    assert all(item.contract_version == "1.0.0-draft.2" for item in submissions)


def test_dead_letter_disposition_cannot_be_reclassified(
    runtime, confirmed_published
) -> None:
    source = _dead_letter(runtime, confirmed_published)
    original = runtime.dead_letter(source.queue_delivery_id)

    with pytest.raises(QueueStateError, match="immutable"):
        runtime.classify_failure(
            source.queue_delivery_id, FailureClassification.TRANSPORT_RETRYABLE
        )

    assert runtime.dead_letter(source.queue_delivery_id) is original
    assert original.classification == FailureClassification.POISON


def test_redrive_record_retains_actor_provenance_binding_and_current_policy(
    runtime, confirmed_published, redrive_authorization
) -> None:
    source = _dead_letter(runtime, confirmed_published)
    delivery = runtime.redrive(
        confirmed_published.queue_message_id,
        "administrator-1",
        redrive_authorization,
    )

    record = runtime.redrive_record(delivery.queue_delivery_id)
    assert record.replay_or_redrive_actor_reference == "administrator-1"
    assert record.original_provenance_reference == source.original_provenance_reference
    assert record.source_queue_delivery_id == source.queue_delivery_id
    assert record.new_queue_delivery_id == delivery.queue_delivery_id
    assert record.source_failure_classification == FailureClassification.POISON
    assert record.semantic_request_id == confirmed_published.semantic_request_id
    assert record.source_queue_message_id == confirmed_published.queue_message_id
    assert record.authorization_context_reference == (
        redrive_authorization.authorization_context_reference
    )
    assert record.policy_version == redrive_authorization.policy_version


@pytest.mark.parametrize("decision", [None, False])
def test_redrive_fails_closed_without_current_authorization(
    runtime, confirmed_published, redrive_authorization, decision
) -> None:
    _dead_letter(runtime, confirmed_published)
    authorization = (
        None
        if decision is None
        else replace(redrive_authorization, authorized=decision)
    )

    with pytest.raises(QueueStateError, match="authorization"):
        runtime.redrive(
            confirmed_published.queue_message_id,
            "administrator-1",
            authorization,
        )


def test_redrive_fails_closed_for_invalid_current_authorization_reference(
    runtime, confirmed_published, redrive_authorization
) -> None:
    _dead_letter(runtime, confirmed_published)
    invalid = replace(
        redrive_authorization,
        authorization_context_reference="Cookie: session-secret",
    )

    with pytest.raises(QueueValidationError, match="prohibited"):
        runtime.redrive(
            confirmed_published.queue_message_id,
            "administrator-1",
            invalid,
        )


def test_prohibited_redrive_actor_content_fails_closed(
    runtime, confirmed_published, redrive_authorization
) -> None:
    _dead_letter(runtime, confirmed_published)

    with pytest.raises(QueueValidationError, match="prohibited"):
        runtime.redrive(
            confirmed_published.queue_message_id,
            "Authorization: Bearer secret",
            redrive_authorization,
        )


@pytest.mark.parametrize("value", PROHIBITED_RUNTIME_IDENTITIES)
def test_set_control_rejects_prohibited_semantic_request_id_without_state_change(
    runtime, value
) -> None:
    runtime.set_control(SemanticRequestId("existing-control"), ControlState.CANCELLED)
    before = deepcopy(runtime._controls)

    with pytest.raises(QueueValidationError, match="prohibited"):
        runtime.set_control(SemanticRequestId(value), ControlState.DELETED)

    assert runtime._controls == before


def test_set_control_security_hook_is_invoked_and_rejection_writes_no_state(
    runtime,
) -> None:
    calls = []

    def security_policy(field, value):
        calls.append((field, value))
        return False

    runtime.validator = replace(runtime.validator, security_policy=security_policy)

    with pytest.raises(QueueValidationError, match="Security policy"):
        runtime.set_control(
            SemanticRequestId("otherwise-valid-semantic-request"),
            ControlState.CANCELLED,
        )

    assert calls == [
        ("semantic_request_id", "otherwise-valid-semantic-request")
    ]
    assert runtime._controls == {}


PUBLIC_BOUNDARY_SENTINEL = "Authorization: Bearer queue-boundary-sentinel"


@pytest.mark.parametrize(
    "field,value",
    [
        ("contract_version", PUBLIC_BOUNDARY_SENTINEL),
        ("schema_version", PUBLIC_BOUNDARY_SENTINEL),
        ("semantic_request_id", SemanticRequestId(PUBLIC_BOUNDARY_SENTINEL)),
        ("queue_message_id", QueueMessageId(PUBLIC_BOUNDARY_SENTINEL)),
        ("operation_kind", PUBLIC_BOUNDARY_SENTINEL),
        (
            "queue_producer_service_reference",
            QueueProducerServiceReference(PUBLIC_BOUNDARY_SENTINEL),
        ),
        ("publication_actor_reference", PUBLIC_BOUNDARY_SENTINEL),
        ("requester_actor_reference", PUBLIC_BOUNDARY_SENTINEL),
        ("authorization_context_reference", PUBLIC_BOUNDARY_SENTINEL),
        ("policy_version", PUBLIC_BOUNDARY_SENTINEL),
        ("queue_delivery_id", QueueDeliveryId(PUBLIC_BOUNDARY_SENTINEL)),
        ("correlation_id", CorrelationId(PUBLIC_BOUNDARY_SENTINEL)),
        ("causation_id", CausationId(PUBLIC_BOUNDARY_SENTINEL)),
        ("workflow_attempt_id", WorkflowAttemptId(PUBLIC_BOUNDARY_SENTINEL)),
        ("claim_or_lease_id", ClaimOrLeaseId(PUBLIC_BOUNDARY_SENTINEL)),
        (
            "worker_service_reference",
            WorkerServiceReference(PUBLIC_BOUNDARY_SENTINEL),
        ),
        ("producer_result_id", ProducerResultId(PUBLIC_BOUNDARY_SENTINEL)),
        ("evidence_reference_id", PUBLIC_BOUNDARY_SENTINEL),
        ("input_reference", PUBLIC_BOUNDARY_SENTINEL),
        ("checkpoint_reference", PUBLIC_BOUNDARY_SENTINEL),
        ("result_reference", PUBLIC_BOUNDARY_SENTINEL),
        ("result_phase_or_slot_reference", PUBLIC_BOUNDARY_SENTINEL),
        ("publication_identity", PublicationIdentity(PUBLIC_BOUNDARY_SENTINEL)),
        ("publication_state", PUBLIC_BOUNDARY_SENTINEL),
        ("retry_classification", PUBLIC_BOUNDARY_SENTINEL),
        ("cancellation_actor_reference", PUBLIC_BOUNDARY_SENTINEL),
        ("cancellation_intent_reference", PUBLIC_BOUNDARY_SENTINEL),
        ("replay_or_redrive_actor_reference", PUBLIC_BOUNDARY_SENTINEL),
        ("original_provenance_reference", PUBLIC_BOUNDARY_SENTINEL),
        ("integrity_metadata", PUBLIC_BOUNDARY_SENTINEL),
        ("bounded_metadata", (("trace_label", PUBLIC_BOUNDARY_SENTINEL),)),
    ],
)
def test_publish_rejects_public_boundary_sentinel_from_every_textual_field(
    runtime, validator, raw_envelope, field, value
) -> None:
    envelope = validator.validate(raw_envelope)

    with pytest.raises(QueueValidationError):
        runtime.publish(replace(envelope, **{field: value}))

    assert runtime._messages == {}
    assert runtime._publications == {}
    assert runtime._controls == {}


def test_every_public_adapter_text_boundary_rejects_prohibited_sentinel(
    runtime, binding_factory
) -> None:
    sentinel = PUBLIC_BOUNDARY_SENTINEL
    valid_delivery = QueueDeliveryId("valid-delivery")
    valid_message = QueueMessageId("valid-message")
    valid_claim = ClaimOrLeaseId("valid-claim")
    valid_publication = PublicationIdentity("valid-publication")
    valid_result = ProducerResultId("valid-result")
    readiness = AckReadiness(True, runtime.required_durable_effects)
    binding = binding_factory()

    def authorization(**changes):
        values = {
            "authorized": True,
            "authorization_context_reference": "valid-authorization-context",
            "policy_version": "valid-policy-version",
            "decision_reference": "valid-decision-reference",
        }
        values.update(changes)
        return AdministrativeAuthorizationDecision(**values)

    calls = {
        "record_publication_outcome.publication_identity": lambda: runtime.record_publication_outcome(
            PublicationIdentity(sentinel),
            PublicationState.CONFIRMED_SUCCESS,
            "valid-outcome",
        ),
        "record_publication_outcome.outcome_reference": lambda: runtime.record_publication_outcome(
            valid_publication, PublicationState.CONFIRMED_SUCCESS, sentinel
        ),
        "publication_history.publication_identity": lambda: runtime.publication_history(
            PublicationIdentity(sentinel)
        ),
        "publication.publication_identity": lambda: runtime.publication(
            PublicationIdentity(sentinel)
        ),
        "deliver.queue_message_id": lambda: runtime.deliver(QueueMessageId(sentinel)),
        "record_provider_delivery_occurrence.queue_message_id": lambda: runtime.record_provider_delivery_occurrence(
            QueueMessageId(sentinel), "valid-provider-delivery"
        ),
        "record_provider_delivery_occurrence.provider_delivery_reference": lambda: runtime.record_provider_delivery_occurrence(
            valid_message, sentinel
        ),
        "redeliver.queue_delivery_id": lambda: runtime.redeliver(
            QueueDeliveryId(sentinel)
        ),
        "can_process.queue_delivery_id": lambda: runtime.can_process(
            QueueDeliveryId(sentinel)
        ),
        "set_control.semantic_request_id": lambda: runtime.set_control(
            SemanticRequestId(sentinel), ControlState.CANCELLED
        ),
        "control_state.semantic_request_id": lambda: runtime.control_state(
            SemanticRequestId(sentinel)
        ),
        "claim.queue_delivery_id": lambda: runtime.claim(
            QueueDeliveryId(sentinel), WorkerServiceReference("valid-worker")
        ),
        "claim.worker_service_reference": lambda: runtime.claim(
            valid_delivery, WorkerServiceReference(sentinel)
        ),
        "claim_record.claim_or_lease_id": lambda: runtime.claim_record(
            ClaimOrLeaseId(sentinel)
        ),
        "mark_renewal_uncertain.claim_or_lease_id": lambda: runtime.mark_renewal_uncertain(
            ClaimOrLeaseId(sentinel)
        ),
        "confirm_lease_loss.claim_or_lease_id": lambda: runtime.confirm_lease_loss(
            ClaimOrLeaseId(sentinel)
        ),
        "can_produce_protected_effect.claim_or_lease_id": lambda: runtime.can_produce_protected_effect(
            ClaimOrLeaseId(sentinel)
        ),
        "accept_result.claim_or_lease_id": lambda: runtime.accept_result(
            ClaimOrLeaseId(sentinel), binding, "valid-submission"
        ),
        "accept_result.binding.producer_result_id": lambda: runtime.accept_result(
            valid_claim,
            binding_factory(producer_result_id=ProducerResultId(sentinel)),
            "valid-submission",
        ),
        "accept_result.binding.semantic_request_id": lambda: runtime.accept_result(
            valid_claim,
            binding_factory(semantic_request_id=SemanticRequestId(sentinel)),
            "valid-submission",
        ),
        "accept_result.binding.queue_message_id": lambda: runtime.accept_result(
            valid_claim,
            binding_factory(queue_message_id=QueueMessageId(sentinel)),
            "valid-submission",
        ),
        "accept_result.binding.workflow_attempt_id": lambda: runtime.accept_result(
            valid_claim,
            binding_factory(workflow_attempt_id=WorkflowAttemptId(sentinel)),
            "valid-submission",
        ),
        "accept_result.binding.result_phase_or_slot_reference": lambda: runtime.accept_result(
            valid_claim,
            binding_factory(result_phase_or_slot_reference=sentinel),
            "valid-submission",
        ),
        "accept_result.binding.result_reference": lambda: runtime.accept_result(
            valid_claim,
            binding_factory(result_reference=sentinel),
            "valid-submission",
        ),
        "accept_result.submission_occurrence_reference": lambda: runtime.accept_result(
            valid_claim, binding, sentinel
        ),
        "accepted_result.result_id": lambda: runtime.accepted_result(
            ProducerResultId(sentinel)
        ),
        "result_submissions.result_id": lambda: runtime.result_submissions(
            ProducerResultId(sentinel)
        ),
        "acknowledgement_eligible.queue_delivery_id": lambda: runtime.acknowledgement_eligible(
            QueueDeliveryId(sentinel), valid_claim, readiness
        ),
        "acknowledgement_eligible.claim_or_lease_id": lambda: runtime.acknowledgement_eligible(
            valid_delivery, ClaimOrLeaseId(sentinel), readiness
        ),
        "acknowledge.queue_delivery_id": lambda: runtime.acknowledge(
            QueueDeliveryId(sentinel), valid_claim, readiness
        ),
        "acknowledge.claim_or_lease_id": lambda: runtime.acknowledge(
            valid_delivery, ClaimOrLeaseId(sentinel), readiness
        ),
        "classify_failure.queue_delivery_id": lambda: runtime.classify_failure(
            QueueDeliveryId(sentinel), FailureClassification.TRANSPORT_RETRYABLE
        ),
        "dead_letter.queue_delivery_id": lambda: runtime.dead_letter(
            QueueDeliveryId(sentinel)
        ),
        "dead_letter.queue_message_id": lambda: runtime.dead_letter(
            QueueMessageId(sentinel)
        ),
        "redrive.source_queue_delivery_id": lambda: runtime.redrive(
            QueueDeliveryId(sentinel), "valid-actor", authorization()
        ),
        "redrive.source_queue_message_id": lambda: runtime.redrive(
            QueueMessageId(sentinel), "valid-actor", authorization()
        ),
        "redrive.actor_reference": lambda: runtime.redrive(
            valid_message, sentinel, authorization()
        ),
        "redrive.authorization_context_reference": lambda: runtime.redrive(
            valid_message,
            "valid-actor",
            authorization(authorization_context_reference=sentinel),
        ),
        "redrive.policy_version": lambda: runtime.redrive(
            valid_message,
            "valid-actor",
            authorization(policy_version=sentinel),
        ),
        "redrive.decision_reference": lambda: runtime.redrive(
            valid_message,
            "valid-actor",
            authorization(decision_reference=sentinel),
        ),
        "redrive_record.queue_delivery_id": lambda: runtime.redrive_record(
            QueueDeliveryId(sentinel)
        ),
    }
    audited = {label.partition(".")[0] for label in calls} | {"publish"}
    public = {
        name
        for name, member in vars(InMemoryQueueAdapter).items()
        if callable(member) and not name.startswith("_")
    }

    assert audited == public
    for label, call in calls.items():
        before = deepcopy(runtime.__dict__)
        with pytest.raises(QueueValidationError):
            call()
        assert runtime.__dict__ == before, label
