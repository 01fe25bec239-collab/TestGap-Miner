"""Run the common Queue conformance cases against the reference adapter."""

from __future__ import annotations

from dataclasses import dataclass, replace

import pytest

from app.queue import (
    QUEUE_CONTRACT_VERSION,
    AdministrativeAuthorizationDecision,
    DeliveryRecord,
    DurableEffect,
    EnvelopeValidator,
    FailureClassification,
    InMemoryQueueAdapter,
    ProducerResultId,
    PublicationState,
    QueueDeliveryId,
    QueueEnvelope,
    QueueMessageId,
    QueueRuntimeLimits,
    RedriveRecord,
    ResultBinding,
    RetryDecision,
    RetryPolicy,
    SemanticRequestId,
    WorkflowAttemptId,
)
from provider_conformance import CASES_BY_NAME, CONFORMANCE_CASES, ConformanceCase


REQUIRED_EFFECTS = frozenset(
    {
        DurableEffect.ACCEPTED_RESULT,
        DurableEffect.WORKFLOW_STATE,
        DurableEffect.PROVENANCE,
        DurableEffect.AUDIT,
    }
)


@dataclass(frozen=True, slots=True)
class InMemorySubject:
    adapter: InMemoryQueueAdapter
    validator: EnvelopeValidator
    raw_envelope: dict[str, object]
    required_durable_effects: frozenset[DurableEffect]
    retry_policy: RetryPolicy

    def validate_raw(self, **changes: object) -> QueueEnvelope:
        raw = dict(self.raw_envelope)
        raw.update(changes)
        if getattr(self.adapter, "discard_unknown_semantic_extensions", False):
            raw.pop("future_semantic_switch", None)
        return self.validator.validate(raw)

    def make_envelope(self, **changes: object) -> QueueEnvelope:
        return self.validate_raw(**changes)

    def make_binding(
        self, envelope: QueueEnvelope, **changes: object
    ) -> ResultBinding:
        values = {
            "producer_result_id": ProducerResultId("result-owned-1"),
            "semantic_request_id": envelope.semantic_request_id,
            "queue_message_id": envelope.queue_message_id,
            "workflow_attempt_id": envelope.workflow_attempt_id,
            "result_phase_or_slot_reference": "workflow-result-slot-1",
            "result_reference": "result-reference-1",
        }
        values.update(changes)
        return ResultBinding(**values)  # type: ignore[arg-type]

    def redrive_authorization(self) -> AdministrativeAuthorizationDecision:
        return AdministrativeAuthorizationDecision(
            authorized=True,
            authorization_context_reference="current-redrive-auth-1",
            policy_version="current-redrive-policy-1",
            decision_reference="current-redrive-decision-1",
        )


def _subject(adapter_type: type[InMemoryQueueAdapter] = InMemoryQueueAdapter) -> InMemorySubject:
    validator = EnvelopeValidator(
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
    retry_policy = RetryPolicy(
        max_transport_attempts=2,
        max_poison_attempts=2,
        max_redrives=1,
    )
    adapter = adapter_type(
        validator=validator,
        retry_policy=retry_policy,
        required_durable_effects=REQUIRED_EFFECTS,
    )
    return InMemorySubject(
        adapter=adapter,
        validator=validator,
        raw_envelope={
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
            "workflow_attempt_id": WorkflowAttemptId("workflow-attempt-owned-1"),
            "publication_identity": "publication-1",
            "publication_state": PublicationState.NOT_ATTEMPTED.value,
            "original_provenance_reference": "provenance-1",
        },
        required_durable_effects=REQUIRED_EFFECTS,
        retry_policy=retry_policy,
    )


@pytest.mark.parametrize("case", CONFORMANCE_CASES, ids=lambda case: case.name)
def test_in_memory_queue_conformance(case: ConformanceCase) -> None:
    case.run(_subject())


# --- test-of-tests: deliberately broken subjects the harness must reject ------
#
# These wrap the reference adapter's public boundary and corrupt exactly one
# semantic property each. Everything else stays as conforming as possible, so a
# rejection proves the conformance case tests that property specifically.


class _BrokenRedeliveryProvenance(InMemoryQueueAdapter):
    """Redelivery fabricates unrelated original provenance."""

    def redeliver(self, queue_delivery_id: QueueDeliveryId) -> DeliveryRecord:
        return replace(
            super().redeliver(queue_delivery_id),
            original_provenance_reference="unrelated-provenance-fabricated",
        )


class _BrokenPoisonRetryDecision(InMemoryQueueAdapter):
    """Terminal poison exhaustion contradicts itself: retry_allowed and dead_lettered."""

    def classify_failure(
        self, queue_delivery_id: QueueDeliveryId, classification: FailureClassification
    ) -> RetryDecision:
        decision = super().classify_failure(queue_delivery_id, classification)
        if decision.dead_lettered:
            return replace(decision, retry_allowed=True)
        return decision


class _BrokenSecurityRetryDecision(InMemoryQueueAdapter):
    """Base: SECURITY_REJECTION returns one wrong RetryDecision field."""

    broken_field = ""

    def classify_failure(
        self, queue_delivery_id: QueueDeliveryId, classification: FailureClassification
    ) -> RetryDecision:
        decision = super().classify_failure(queue_delivery_id, classification)
        if classification is FailureClassification.SECURITY_REJECTION:
            return replace(decision, **{self.broken_field: True})
        return decision


class _BrokenSecurityRetryAllowed(_BrokenSecurityRetryDecision):
    broken_field = "retry_allowed"


class _BrokenSecurityDeadLettered(_BrokenSecurityRetryDecision):
    broken_field = "dead_lettered"


class _BrokenSecurityWorkflowTerminal(_BrokenSecurityRetryDecision):
    broken_field = "workflow_terminal"


class _BrokenRedrive(InMemoryQueueAdapter):
    """Base: corrupt the redriven delivery and/or its RedriveRecord.

    ``delivery_changes`` / ``record_changes`` are applied to the values returned
    by the public redrive boundary; an alias table keeps ``redrive_record``
    reachable when the delivery identity itself is corrupted.
    """

    delivery_changes: dict[str, object] = {}
    record_changes: dict[str, object] = {}

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self._alias: dict[QueueDeliveryId, QueueDeliveryId] = {}

    def _corrupt(self, real: DeliveryRecord, **changes: object) -> DeliveryRecord:
        broken = replace(real, **changes)  # type: ignore[arg-type]
        self._alias[broken.queue_delivery_id] = real.queue_delivery_id
        return broken

    def redrive(self, source_identity, actor_reference, authorization_decision):
        real = super().redrive(source_identity, actor_reference, authorization_decision)
        if not self.delivery_changes:
            return real
        return self._corrupt(real, **self.delivery_changes)

    def redrive_record(self, queue_delivery_id: QueueDeliveryId) -> RedriveRecord:
        real = super().redrive_record(
            self._alias.get(queue_delivery_id, queue_delivery_id)
        )
        return replace(
            real,
            new_queue_delivery_id=queue_delivery_id,
            **self.record_changes,  # type: ignore[arg-type]
        )


class _BrokenRedriveDeliveryId(_BrokenRedrive):
    """Reuses the source QueueDeliveryId as the redriven transport identity."""

    def redrive(self, source_identity, actor_reference, authorization_decision):
        real = super().redrive(source_identity, actor_reference, authorization_decision)
        source = InMemoryQueueAdapter.redrive_record(
            self, real.queue_delivery_id
        ).source_queue_delivery_id
        return self._corrupt(real, queue_delivery_id=source)


class _BrokenRedriveSemanticId(_BrokenRedrive):
    delivery_changes = {
        "semantic_request_id": SemanticRequestId("semantic-redrive-mutated")
    }
    record_changes = {
        "semantic_request_id": SemanticRequestId("semantic-redrive-mutated")
    }


class _BrokenRedriveQueueMessageId(_BrokenRedrive):
    delivery_changes = {"queue_message_id": QueueMessageId("message-redrive-mutated")}
    record_changes = {"source_queue_message_id": QueueMessageId("message-redrive-mutated")}


class _BrokenRedriveProvenance(_BrokenRedrive):
    delivery_changes = {"original_provenance_reference": "provenance-redrive-dropped"}
    record_changes = {"original_provenance_reference": "provenance-redrive-dropped"}


class _BrokenRedriveAuthAttribution(_BrokenRedrive):
    record_changes = {
        "authorization_context_reference": "unrelated-auth-context",
        "authorization_decision_reference": "unrelated-auth-decision",
    }


class _BrokenRedriveFailureClassification(_BrokenRedrive):
    record_changes = {
        "source_failure_classification": FailureClassification.TRANSPORT_RETRYABLE
    }


class _BrokenRedriveBound(InMemoryQueueAdapter):
    """Permits unbounded administrative redrive by forgetting the redrive count."""

    def redrive(self, source_identity, actor_reference, authorization_decision):
        self._redrive_counts.clear()
        return super().redrive(
            source_identity, actor_reference, authorization_decision
        )


class _BrokenSecurityRedriveBypass(InMemoryQueueAdapter):
    """Lets sticky SECURITY_REJECTION work become redrive eligible again."""

    def redrive(self, source_identity, actor_reference, authorization_decision):
        rejected = set(self._security_rejected_requests)
        self._security_rejected_requests.clear()
        try:
            return super().redrive(
                source_identity, actor_reference, authorization_decision
            )
        finally:
            self._security_rejected_requests.update(rejected)


class _BrokenExistingClaimEffectCutoff(InMemoryQueueAdapter):
    """Treats a pre-existing claim as active after Queue cancellation."""

    def can_produce_protected_effect(self, claim_or_lease_id):
        claim = self._claims[claim_or_lease_id]
        delivery = self._deliveries[claim.queue_delivery_id]
        state = self._controls.pop(delivery.semantic_request_id, None)
        try:
            return super().can_produce_protected_effect(claim_or_lease_id)
        finally:
            if state is not None:
                self._controls[delivery.semantic_request_id] = state


class _BrokenExistingClaimAckCutoff(InMemoryQueueAdapter):
    """Treats a pre-existing claim as ACK-eligible after Queue cancellation."""

    def acknowledgement_eligible(self, queue_delivery_id, claim_or_lease_id, readiness):
        delivery = self._deliveries[queue_delivery_id]
        state = self._controls.pop(delivery.semantic_request_id, None)
        try:
            return super().acknowledgement_eligible(
                queue_delivery_id, claim_or_lease_id, readiness
            )
        finally:
            if state is not None:
                self._controls[delivery.semantic_request_id] = state


class _BrokenUnknownSemanticExtension(InMemoryQueueAdapter):
    """Silently discards an unknown contract-controlled envelope field."""

    discard_unknown_semantic_extensions = True


class _BrokenRedeliveryResultFork(InMemoryQueueAdapter):
    """Forks an accepted result identity only for an actual redelivery."""

    def accept_result(self, claim_or_lease_id, binding, submission_occurrence_reference):
        accepted = super().accept_result(
            claim_or_lease_id, binding, submission_occurrence_reference
        )
        claim = self._claims[claim_or_lease_id]
        delivery = self._deliveries[claim.queue_delivery_id]
        occurrences = [
            item
            for item in self._deliveries.values()
            if item.queue_message_id == delivery.queue_message_id
        ]
        if len(occurrences) > 1:
            fork = replace(
                accepted,
                producer_result_id=ProducerResultId("result-redelivery-fork"),
            )
            self._accepted_results[fork.producer_result_id] = fork
            return fork
        return accepted


# Each entry: label, broken adapter, the conformance cases it must fail.
# The first case is the primary detection case for that corruption.
BROKEN_SUBJECTS = (
    ("BROKEN_REDELIVERY_PROVENANCE", _BrokenRedeliveryProvenance,
     ("redelivery_preserves_original_provenance",)),
    ("BROKEN_POISON_RETRY_DECISION", _BrokenPoisonRetryDecision,
     ("poison_retry_decision_semantics", "bounded_transport_retry",
      "bounded_administrative_redrive")),
    ("BROKEN_SECURITY_RETRY_ALLOWED", _BrokenSecurityRetryAllowed,
     ("security_rejection_retry_decision",)),
    ("BROKEN_SECURITY_DEAD_LETTERED", _BrokenSecurityDeadLettered,
     ("security_rejection_retry_decision",)),
    ("BROKEN_SECURITY_WORKFLOW_TERMINAL", _BrokenSecurityWorkflowTerminal,
     ("security_rejection_retry_decision",)),
    ("BROKEN_REDRIVE_DELIVERY_ID", _BrokenRedriveDeliveryId,
     ("authorized_ordinary_redrive", "bounded_administrative_redrive")),
    ("BROKEN_REDRIVE_SEMANTIC_ID", _BrokenRedriveSemanticId,
     ("authorized_ordinary_redrive",)),
    ("BROKEN_REDRIVE_QUEUE_MESSAGE_ID", _BrokenRedriveQueueMessageId,
     ("authorized_ordinary_redrive",)),
    ("BROKEN_REDRIVE_PROVENANCE", _BrokenRedriveProvenance,
     ("authorized_ordinary_redrive",)),
    ("BROKEN_REDRIVE_AUTH_ATTRIBUTION", _BrokenRedriveAuthAttribution,
     ("authorized_ordinary_redrive",)),
    ("BROKEN_REDRIVE_FAILURE_CLASSIFICATION", _BrokenRedriveFailureClassification,
     ("authorized_ordinary_redrive",)),
    ("BROKEN_REDRIVE_BOUND", _BrokenRedriveBound,
     ("bounded_administrative_redrive",)),
    ("SECURITY_REDRIVE_BYPASS", _BrokenSecurityRedriveBypass,
     ("redrive_cannot_bypass_security_rejection",)),
    ("BROKEN_EXISTING_CLAIM_EFFECT_CUTOFF", _BrokenExistingClaimEffectCutoff,
     ("non_active_control_cutoff",)),
    ("BROKEN_EXISTING_CLAIM_ACK_CUTOFF", _BrokenExistingClaimAckCutoff,
     ("non_active_control_cutoff",)),
    ("BROKEN_UNKNOWN_SEMANTIC_EXTENSION", _BrokenUnknownSemanticExtension,
     ("unknown_semantic_extension",)),
    ("BROKEN_REDELIVERY_RESULT_FORK", _BrokenRedeliveryResultFork,
     ("duplicate_result_across_redelivery",)),
)

_BROKEN_IDS = [label for label, _, _ in BROKEN_SUBJECTS]


@pytest.mark.parametrize(
    "adapter_type, case_names",
    [(adapter_type, names) for _, adapter_type, names in BROKEN_SUBJECTS],
    ids=_BROKEN_IDS,
)
def test_broken_subject_is_rejected(
    adapter_type: type[InMemoryQueueAdapter], case_names: tuple[str, ...]
) -> None:
    """A subject with corrupt Queue semantics must not receive conformance PASS.

    Any raised outcome is a conformance failure: a violated assertion, a missing
    expected rejection, or the Queue boundary refusing the corrupted state.
    """
    for case_name in case_names:
        with pytest.raises((Exception, pytest.fail.Exception)):
            CASES_BY_NAME[case_name].run(_subject(adapter_type))


@pytest.mark.parametrize(
    "adapter_type, case_names",
    [(adapter_type, names) for _, adapter_type, names in BROKEN_SUBJECTS],
    ids=_BROKEN_IDS,
)
def test_broken_subject_is_otherwise_conforming(
    adapter_type: type[InMemoryQueueAdapter], case_names: tuple[str, ...]
) -> None:
    """Detection is specific: each broken subject still passes every other case."""
    for case in CONFORMANCE_CASES:
        if case.name not in case_names:
            case.run(_subject(adapter_type))
