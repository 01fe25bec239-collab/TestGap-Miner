"""Deterministic in-memory Queue adapter (test/reference only)."""

from __future__ import annotations

from dataclasses import replace

from .envelope import EnvelopeValidator, QueueEnvelope
from .identities import (
    ClaimOrLeaseId,
    ProducerResultId,
    PublicationIdentity,
    QueueDeliveryId,
    QueueMessageId,
    SemanticRequestId,
    WorkerServiceReference,
    WorkflowAttemptId,
)
from .models import (
    AdministrativeAuthorizationDecision,
    AckReadiness,
    ClaimRecord,
    ClaimState,
    ControlState,
    DeadLetterRecord,
    DeliveryRecord,
    DurableEffect,
    FailureClassification,
    PublicationRecord,
    PublicationOutcomeRecord,
    PublicationState,
    QueueConflictError,
    QueueStateError,
    ResultBinding,
    ResultSubmissionRecord,
    RedriveRecord,
    RetryDecision,
    RetryPolicy,
)


class InMemoryQueueAdapter:
    """Non-durable, process-local conformance adapter; never a production Queue."""

    classification = "TEST / REFERENCE ONLY"

    def __init__(
        self,
        validator: EnvelopeValidator,
        retry_policy: RetryPolicy,
        required_durable_effects: frozenset[DurableEffect],
    ) -> None:
        if not isinstance(required_durable_effects, frozenset) or not required_durable_effects:
            raise ValueError("required durable effects must be an explicit nonempty frozenset")
        if any(not isinstance(effect, DurableEffect) for effect in required_durable_effects):
            raise TypeError("required durable effects must contain DurableEffect values")
        if not isinstance(validator, EnvelopeValidator):
            raise TypeError("validator must be an EnvelopeValidator")
        self.validator = validator
        self.retry_policy = retry_policy
        self.required_durable_effects = required_durable_effects
        self._messages: dict[QueueMessageId, QueueEnvelope] = {}
        self._publications: dict[PublicationIdentity, PublicationRecord] = {}
        self._publication_history: dict[
            PublicationIdentity, list[PublicationOutcomeRecord]
        ] = {}
        self._deliveries: dict[QueueDeliveryId, DeliveryRecord] = {}
        self._claims: dict[ClaimOrLeaseId, ClaimRecord] = {}
        self._current_claim: dict[QueueMessageId, ClaimOrLeaseId] = {}
        self._controls: dict[SemanticRequestId, ControlState] = {}
        self._accepted_results: dict[ProducerResultId, ResultBinding] = {}
        self._result_slots: dict[
            tuple[SemanticRequestId, QueueMessageId, WorkflowAttemptId, str],
            ProducerResultId,
        ] = {}
        self._result_submissions: dict[
            ProducerResultId, list[ResultSubmissionRecord]
        ] = {}
        self._conflicted_messages: set[QueueMessageId] = set()
        self._security_rejected_requests: set[SemanticRequestId] = set()
        self._failure_counts: dict[
            tuple[QueueDeliveryId, FailureClassification], int
        ] = {}
        self._dead_letters: dict[QueueDeliveryId, DeadLetterRecord] = {}
        self._redrive_counts: dict[QueueMessageId, int] = {}
        self._redrives: dict[QueueDeliveryId, RedriveRecord] = {}
        self._acknowledged: set[QueueDeliveryId] = set()
        self._delivery_sequence = 0
        self._claim_sequence = 0
        self._fence_sequence = 0

    def publish(self, envelope: QueueEnvelope) -> PublicationRecord:
        envelope = self.validator.validate_envelope(envelope)
        publication_id = envelope.publication_identity
        if publication_id is None:
            raise QueueStateError("publication identity is required")
        if envelope.publication_state != PublicationState.NOT_ATTEMPTED.value:
            raise QueueStateError("new publication intent must be not attempted")
        if envelope.claim_or_lease_id is not None:
            self._validate_claimed_envelope(envelope)
        existing_message = self._messages.get(envelope.queue_message_id)
        if existing_message is not None and existing_message != envelope:
            raise QueueConflictError("Queue message has a conflicting binding")
        existing = self._publications.get(publication_id)
        if existing is not None:
            if (
                existing.semantic_request_id != envelope.semantic_request_id
                or existing.queue_message_id != envelope.queue_message_id
            ):
                raise QueueConflictError("publication identity has a conflicting binding")
            return existing
        self._messages[envelope.queue_message_id] = envelope
        self._controls.setdefault(envelope.semantic_request_id, ControlState.ACTIVE)
        record = PublicationRecord(
            publication_id,
            envelope.semantic_request_id,
            envelope.queue_message_id,
            PublicationState.NOT_ATTEMPTED,
        )
        self._publications[publication_id] = record
        self._publication_history[publication_id] = []
        return record

    def record_publication_outcome(
        self,
        publication_identity: PublicationIdentity,
        state: PublicationState,
        outcome_reference: str,
    ) -> PublicationRecord:
        self.validator.validate_identity(
            "publication_identity", publication_identity, PublicationIdentity
        )
        if type(state) is not PublicationState:
            raise TypeError("state must be a PublicationState")
        self.validator.validate_reference("publication_outcome_reference", outcome_reference)
        if state == PublicationState.NOT_ATTEMPTED:
            raise QueueStateError("state is not a provider publication outcome")
        current = self._publications[publication_identity]
        if state in {
            PublicationState.REJECTED_BEFORE_ACCEPTANCE,
            PublicationState.CONFIRMED_FAILURE,
        } and any(
            delivery.queue_message_id == current.queue_message_id
            for delivery in self._deliveries.values()
        ):
            raise QueueConflictError(
                "provider delivery occurrence conflicts with publication failure"
            )
        reconcilable = {
            PublicationState.NOT_ATTEMPTED,
            PublicationState.RESULT_UNCERTAIN,
        }
        if current.state not in reconcilable and current.state != state:
            raise QueueConflictError("publication outcome cannot be overwritten")
        if current.state == PublicationState.RESULT_UNCERTAIN and state not in {
            PublicationState.RESULT_UNCERTAIN,
            PublicationState.REJECTED_BEFORE_ACCEPTANCE,
            PublicationState.CONFIRMED_FAILURE,
            PublicationState.CONFIRMED_SUCCESS,
            PublicationState.CONFIRMED_DUPLICATE_REQUEST,
        }:
            raise QueueConflictError("uncertain publication cannot resolve to that state")
        updated = replace(current, state=state)
        self._publications[publication_identity] = updated
        outcome = PublicationOutcomeRecord(
            publication_identity, state, outcome_reference
        )
        history = self._publication_history[publication_identity]
        if outcome not in history:
            history.append(outcome)
        return updated

    def publication_history(
        self, publication_identity: PublicationIdentity
    ) -> tuple[PublicationOutcomeRecord, ...]:
        self.validator.validate_identity(
            "publication_identity", publication_identity, PublicationIdentity
        )
        return tuple(self._publication_history[publication_identity])

    def publication(self, publication_identity: PublicationIdentity) -> PublicationRecord:
        self.validator.validate_identity(
            "publication_identity", publication_identity, PublicationIdentity
        )
        return self._publications[publication_identity]

    def deliver(self, queue_message_id: QueueMessageId) -> DeliveryRecord:
        self.validator.validate_identity(
            "queue_message_id", queue_message_id, QueueMessageId
        )
        publication = self._publication_for_message(queue_message_id)
        if publication.state not in {
            PublicationState.CONFIRMED_SUCCESS,
            PublicationState.CONFIRMED_DUPLICATE_REQUEST,
        }:
            raise QueueStateError("publication state does not establish delivery")
        return self._create_delivery(queue_message_id, None)

    def record_provider_delivery_occurrence(
        self, queue_message_id: QueueMessageId, provider_delivery_reference: str
    ) -> DeliveryRecord:
        self.validator.validate_identity(
            "queue_message_id", queue_message_id, QueueMessageId
        )
        reference = self.validator.validate_reference(
            "provider_delivery_reference", provider_delivery_reference
        )
        publication = self._publication_for_message(queue_message_id)
        if publication.state not in {
            PublicationState.RESULT_UNCERTAIN,
            PublicationState.CONFIRMED_SUCCESS,
            PublicationState.CONFIRMED_DUPLICATE_REQUEST,
        }:
            raise QueueStateError("publication state prohibits provider delivery")
        return self._create_delivery(queue_message_id, reference)

    def _create_delivery(
        self,
        queue_message_id: QueueMessageId,
        provider_delivery_reference: str | None,
        *,
        redrive: bool = False,
    ) -> DeliveryRecord:
        envelope = self._messages[queue_message_id]
        if envelope.semantic_request_id in self._security_rejected_requests:
            raise QueueStateError(
                "security-rejected semantic work cannot receive a new delivery"
            )
        if not redrive and self._dead_letter_for_message(queue_message_id) is not None:
            raise QueueStateError("dead-lettered work requires explicit redrive")
        self._delivery_sequence += 1
        prior = sum(
            record.queue_message_id == queue_message_id
            for record in self._deliveries.values()
        )
        delivery = DeliveryRecord(
            QueueDeliveryId(f"delivery-{self._delivery_sequence}"),
            envelope.semantic_request_id,
            queue_message_id,
            envelope.workflow_attempt_id,
            envelope.original_provenance_reference
            or f"publication:{envelope.publication_identity.value}",
            provider_delivery_reference
            or f"in-memory-provider-delivery-{self._delivery_sequence}",
            prior,
        )
        self._deliveries[delivery.queue_delivery_id] = delivery
        return delivery

    def redeliver(self, queue_delivery_id: QueueDeliveryId) -> DeliveryRecord:
        self.validator.validate_identity(
            "queue_delivery_id", queue_delivery_id, QueueDeliveryId
        )
        source = self._deliveries[queue_delivery_id]
        return self._create_delivery(source.queue_message_id, None)

    def can_process(self, queue_delivery_id: QueueDeliveryId) -> bool:
        self.validator.validate_identity(
            "queue_delivery_id", queue_delivery_id, QueueDeliveryId
        )
        delivery = self._deliveries[queue_delivery_id]
        return (
            delivery.semantic_request_id not in self._security_rejected_requests
            and queue_delivery_id not in self._dead_letters
            and queue_delivery_id not in self._acknowledged
            and self.control_state(delivery.semantic_request_id) == ControlState.ACTIVE
        )

    def set_control(
        self, semantic_request_id: SemanticRequestId, state: ControlState
    ) -> None:
        self.validator.validate_identity(
            "semantic_request_id", semantic_request_id, SemanticRequestId
        )
        if not isinstance(state, ControlState):
            raise TypeError("state must be a ControlState")
        current = self._controls.get(semantic_request_id, ControlState.ACTIVE)
        if semantic_request_id in self._security_rejected_requests:
            if state == ControlState.ACTIVE:
                raise QueueStateError(
                    "security-rejected work cannot be reactivated"
                )
        elif current != ControlState.ACTIVE and state == ControlState.ACTIVE:
            raise QueueStateError("Queue control cannot reactivate invalid work")
        self._controls[semantic_request_id] = state

    def control_state(self, semantic_request_id: SemanticRequestId) -> ControlState:
        self.validator.validate_identity(
            "semantic_request_id", semantic_request_id, SemanticRequestId
        )
        return self._controls.get(semantic_request_id, ControlState.ACTIVE)

    def claim(
        self,
        queue_delivery_id: QueueDeliveryId,
        worker_service_reference: WorkerServiceReference,
    ) -> ClaimRecord:
        self.validator.validate_identity(
            "worker_service_reference",
            worker_service_reference,
            WorkerServiceReference,
        )
        self.validator.validate_identity(
            "queue_delivery_id", queue_delivery_id, QueueDeliveryId
        )
        delivery = self._deliveries[queue_delivery_id]
        if not self.can_process(queue_delivery_id):
            raise QueueStateError("controlled work cannot be claimed")
        previous_id = self._current_claim.get(delivery.queue_message_id)
        if previous_id is not None:
            previous = self._claims[previous_id]
            if previous.state in {
                ClaimState.CURRENT,
                ClaimState.RENEWAL_UNCERTAIN,
            }:
                self._claims[previous_id] = replace(previous, state=ClaimState.REPLACED)
        self._claim_sequence += 1
        self._fence_sequence += 1
        claim = ClaimRecord(
            ClaimOrLeaseId(f"claim-{self._claim_sequence}"),
            queue_delivery_id,
            worker_service_reference,
            self._fence_sequence,
            ClaimState.CURRENT,
        )
        self._claims[claim.claim_or_lease_id] = claim
        self._current_claim[delivery.queue_message_id] = claim.claim_or_lease_id
        return claim

    def claim_record(self, claim_or_lease_id: ClaimOrLeaseId) -> ClaimRecord:
        self.validator.validate_identity(
            "claim_or_lease_id", claim_or_lease_id, ClaimOrLeaseId
        )
        return self._claims[claim_or_lease_id]

    def mark_renewal_uncertain(self, claim_or_lease_id: ClaimOrLeaseId) -> ClaimRecord:
        self.validator.validate_identity(
            "claim_or_lease_id", claim_or_lease_id, ClaimOrLeaseId
        )
        claim = self._claims[claim_or_lease_id]
        if claim.state == ClaimState.CONFIRMED_LEASE_LOST:
            raise QueueStateError("confirmed lease loss is irreversible")
        if claim.state != ClaimState.CURRENT:
            raise QueueStateError("only the current claim may request renewal")
        updated = replace(claim, state=ClaimState.RENEWAL_UNCERTAIN)
        self._claims[claim_or_lease_id] = updated
        return updated

    def confirm_lease_loss(self, claim_or_lease_id: ClaimOrLeaseId) -> ClaimRecord:
        self.validator.validate_identity(
            "claim_or_lease_id", claim_or_lease_id, ClaimOrLeaseId
        )
        claim = self._claims[claim_or_lease_id]
        updated = replace(claim, state=ClaimState.CONFIRMED_LEASE_LOST)
        self._claims[claim_or_lease_id] = updated
        return updated

    def can_produce_protected_effect(self, claim_or_lease_id: ClaimOrLeaseId) -> bool:
        self.validator.validate_identity(
            "claim_or_lease_id", claim_or_lease_id, ClaimOrLeaseId
        )
        claim = self._claims[claim_or_lease_id]
        delivery = self._deliveries[claim.queue_delivery_id]
        return (
            claim.state == ClaimState.CURRENT
            and self._current_claim.get(delivery.queue_message_id) == claim_or_lease_id
            and claim.queue_delivery_id not in self._dead_letters
            and claim.queue_delivery_id not in self._acknowledged
            and delivery.semantic_request_id not in self._security_rejected_requests
            and self.control_state(delivery.semantic_request_id) == ControlState.ACTIVE
        )

    def accept_result(
        self,
        claim_or_lease_id: ClaimOrLeaseId,
        binding: ResultBinding,
        submission_occurrence_reference: str,
    ) -> ResultBinding:
        if type(binding) is not ResultBinding:
            raise TypeError("binding must be a ResultBinding")
        for name, identity_type in (
            ("claim_or_lease_id", ClaimOrLeaseId),
            ("producer_result_id", ProducerResultId),
            ("semantic_request_id", SemanticRequestId),
            ("queue_message_id", QueueMessageId),
            ("workflow_attempt_id", WorkflowAttemptId),
        ):
            value = (
                claim_or_lease_id
                if name == "claim_or_lease_id"
                else getattr(binding, name)
            )
            self.validator.validate_identity(name, value, identity_type)
        self.validator.validate_reference(
            "result_phase_or_slot_reference",
            binding.result_phase_or_slot_reference,
        )
        self.validator.validate_reference("result_reference", binding.result_reference)
        occurrence = self.validator.validate_reference(
            "submission_occurrence_reference", submission_occurrence_reference
        )
        claim = self._claims[claim_or_lease_id]
        delivery = self._deliveries[claim.queue_delivery_id]
        envelope = self._messages[delivery.queue_message_id]
        if not self.can_produce_protected_effect(claim_or_lease_id):
            raise QueueStateError("claim cannot produce a protected effect")
        if (
            binding.semantic_request_id != delivery.semantic_request_id
            or binding.queue_message_id != delivery.queue_message_id
            or binding.workflow_attempt_id != delivery.workflow_attempt_id
        ):
            raise QueueConflictError("result binding does not match the delivery")
        slot = (
            binding.semantic_request_id,
            binding.queue_message_id,
            binding.workflow_attempt_id,
            binding.result_phase_or_slot_reference,
        )
        slot_result = self._result_slots.get(slot)
        if slot_result is not None and slot_result != binding.producer_result_id:
            self._conflicted_messages.add(delivery.queue_message_id)
            raise QueueConflictError("Workflow result slot has a conflicting result identity")
        existing = self._accepted_results.get(binding.producer_result_id)
        if existing is None:
            self._accepted_results[binding.producer_result_id] = binding
            self._result_slots[slot] = binding.producer_result_id
            accepted = binding
        elif existing != binding:
            self._conflicted_messages.add(delivery.queue_message_id)
            raise QueueConflictError("producer result identity has a conflicting binding")
        else:
            accepted = existing
        submission = ResultSubmissionRecord(
            binding,
            occurrence,
            delivery.queue_delivery_id,
            claim.worker_service_reference,
            claim.claim_or_lease_id,
            claim.fence,
            envelope.contract_version,
            envelope.schema_version,
            envelope.integrity_metadata,
        )
        submissions = self._result_submissions.setdefault(
            binding.producer_result_id, []
        )
        if submission not in submissions:
            submissions.append(submission)
        return accepted

    def accepted_result(self, result_id: ProducerResultId) -> ResultBinding:
        self.validator.validate_identity("producer_result_id", result_id, ProducerResultId)
        return self._accepted_results[result_id]

    def result_submissions(
        self, result_id: ProducerResultId
    ) -> tuple[ResultSubmissionRecord, ...]:
        self.validator.validate_identity("producer_result_id", result_id, ProducerResultId)
        return tuple(self._result_submissions[result_id])

    def acknowledgement_eligible(
        self,
        queue_delivery_id: QueueDeliveryId,
        claim_or_lease_id: ClaimOrLeaseId,
        readiness: AckReadiness,
    ) -> bool:
        self.validator.validate_identity(
            "queue_delivery_id", queue_delivery_id, QueueDeliveryId
        )
        self.validator.validate_identity(
            "claim_or_lease_id", claim_or_lease_id, ClaimOrLeaseId
        )
        if type(readiness) is not AckReadiness:
            raise TypeError("readiness must be an AckReadiness")
        delivery = self._deliveries[queue_delivery_id]
        claim = self._claims[claim_or_lease_id]
        return (
            readiness.execution_succeeded is True
            and self.required_durable_effects <= readiness.ready_effects
            and claim.queue_delivery_id == queue_delivery_id
            and delivery.semantic_request_id not in self._security_rejected_requests
            and self.can_produce_protected_effect(claim_or_lease_id)
            and delivery.queue_message_id not in self._conflicted_messages
        )

    def acknowledge(
        self,
        queue_delivery_id: QueueDeliveryId,
        claim_or_lease_id: ClaimOrLeaseId,
        readiness: AckReadiness,
    ) -> bool:
        if not self.acknowledgement_eligible(
            queue_delivery_id, claim_or_lease_id, readiness
        ):
            return False
        self._acknowledged.add(queue_delivery_id)
        return True

    def classify_failure(
        self,
        queue_delivery_id: QueueDeliveryId,
        classification: FailureClassification,
    ) -> RetryDecision:
        self.validator.validate_identity(
            "queue_delivery_id", queue_delivery_id, QueueDeliveryId
        )
        if not isinstance(classification, FailureClassification):
            raise TypeError("classification must be a FailureClassification")
        delivery = self._deliveries[queue_delivery_id]
        if queue_delivery_id in self._dead_letters:
            raise QueueStateError("dead-letter disposition is immutable")
        if self.control_state(delivery.semantic_request_id) != ControlState.ACTIVE:
            raise QueueStateError("controlled work is not a retry classification")
        if delivery.semantic_request_id in self._security_rejected_requests:
            if classification == FailureClassification.SECURITY_REJECTION:
                return RetryDecision(False, False)
            raise QueueStateError(
                "security-rejected work cannot re-enter ordinary retry classification"
            )
        if classification == FailureClassification.SECURITY_REJECTION:
            self._establish_security_rejection(delivery)
            return RetryDecision(False, False)
        if classification == FailureClassification.APPLICATION:
            return RetryDecision(False, False)
        key = (queue_delivery_id, classification)
        count = self._failure_counts.get(key, 0) + 1
        self._failure_counts[key] = count
        limit = (
            self.retry_policy.max_poison_attempts
            if classification == FailureClassification.POISON
            else self.retry_policy.max_transport_attempts
        )
        if count < limit:
            return RetryDecision(True, False)
        dead_letter = DeadLetterRecord(delivery, classification)
        self._dead_letters[queue_delivery_id] = dead_letter
        for claim_id, claim in self._claims.items():
            if claim.queue_delivery_id == queue_delivery_id and claim.state in {
                ClaimState.CURRENT,
                ClaimState.RENEWAL_UNCERTAIN,
            }:
                self._claims[claim_id] = replace(claim, state=ClaimState.REVOKED)
        return RetryDecision(False, True)

    def _establish_security_rejection(self, delivery: DeliveryRecord) -> None:
        """Make a security rejection sticky for the whole semantic request.

        Queue-owned transport disposition: revokes every authoritative claim
        tied to the semantic request and is never removable by ordinary
        public operations.
        """
        self._security_rejected_requests.add(delivery.semantic_request_id)
        for claim_id, claim in self._claims.items():
            if claim.state not in {
                ClaimState.CURRENT,
                ClaimState.RENEWAL_UNCERTAIN,
            }:
                continue
            claim_delivery = self._deliveries.get(claim.queue_delivery_id)
            if (
                claim_delivery is not None
                and claim_delivery.semantic_request_id == delivery.semantic_request_id
            ):
                self._claims[claim_id] = replace(claim, state=ClaimState.REVOKED)

    def dead_letter(
        self, identity: QueueDeliveryId | QueueMessageId
    ) -> DeadLetterRecord:
        if type(identity) not in (QueueDeliveryId, QueueMessageId):
            raise TypeError("identity must be a QueueDeliveryId or QueueMessageId")
        self.validator.validate_identity("identity", identity, type(identity))
        if type(identity) is QueueDeliveryId:
            return self._dead_letters[identity]
        if type(identity) is QueueMessageId:
            record = self._dead_letter_for_message(identity)
            if record is not None:
                return record
        raise KeyError(identity)

    def redrive(
        self,
        source_identity: QueueDeliveryId | QueueMessageId,
        actor_reference: str,
        authorization_decision: AdministrativeAuthorizationDecision | None,
    ) -> DeliveryRecord:
        if type(source_identity) not in (QueueDeliveryId, QueueMessageId):
            raise TypeError(
                "source_identity must be a QueueDeliveryId or QueueMessageId"
            )
        self.validator.validate_identity(
            "source_identity", source_identity, type(source_identity)
        )
        actor = self.validator.validate_reference(
            "replay_or_redrive_actor_reference", actor_reference
        )
        if type(authorization_decision) is not AdministrativeAuthorizationDecision:
            raise QueueStateError("current redrive authorization is required")
        authorization_context = self.validator.validate_reference(
            "authorization_context_reference",
            authorization_decision.authorization_context_reference,
        )
        policy_version = self.validator.validate_reference(
            "policy_version", authorization_decision.policy_version
        )
        decision_reference = self.validator.validate_reference(
            "authorization_decision_reference",
            authorization_decision.decision_reference,
        )
        if not authorization_decision.authorized:
            raise QueueStateError("current redrive authorization is required")
        dead_letter = (
            self._dead_letters.get(source_identity)
            if type(source_identity) is QueueDeliveryId
            else self._dead_letter_for_message(source_identity)
            if type(source_identity) is QueueMessageId
            else None
        )
        if dead_letter is None:
            raise QueueStateError("only dead-lettered work may be redriven")
        queue_message_id = dead_letter.source_delivery.queue_message_id
        semantic_request_id = dead_letter.source_delivery.semantic_request_id
        if self.control_state(semantic_request_id) != ControlState.ACTIVE:
            raise QueueStateError("controlled work cannot be redriven")
        if semantic_request_id in self._security_rejected_requests:
            raise QueueStateError("security-rejected work cannot be redriven")
        self.validator.validate_envelope(self._messages[queue_message_id])
        count = self._redrive_counts.get(queue_message_id, 0)
        if count >= self.retry_policy.max_redrives:
            raise QueueStateError("redrive limit exhausted")
        self._redrive_counts[queue_message_id] = count + 1
        delivery = self._create_delivery(queue_message_id, None, redrive=True)
        self._redrives[delivery.queue_delivery_id] = RedriveRecord(
            actor,
            dead_letter.source_delivery.original_provenance_reference,
            dead_letter.source_delivery.queue_delivery_id,
            queue_message_id,
            semantic_request_id,
            delivery.queue_delivery_id,
            dead_letter.classification,
            authorization_context,
            policy_version,
            decision_reference,
        )
        return delivery

    def redrive_record(self, queue_delivery_id: QueueDeliveryId) -> RedriveRecord:
        self.validator.validate_identity(
            "queue_delivery_id", queue_delivery_id, QueueDeliveryId
        )
        return self._redrives[queue_delivery_id]

    def _dead_letter_for_message(
        self, queue_message_id: QueueMessageId
    ) -> DeadLetterRecord | None:
        return next(
            (
                record
                for record in reversed(tuple(self._dead_letters.values()))
                if record.source_delivery.queue_message_id == queue_message_id
            ),
            None,
        )

    def _publication_for_message(
        self, queue_message_id: QueueMessageId
    ) -> PublicationRecord:
        envelope = self._messages[queue_message_id]
        assert envelope.publication_identity is not None
        return self._publications[envelope.publication_identity]

    def _validate_claimed_envelope(self, envelope: QueueEnvelope) -> None:
        assert envelope.claim_or_lease_id is not None
        claim = self._claims.get(envelope.claim_or_lease_id)
        if claim is None or not self.can_produce_protected_effect(claim.claim_or_lease_id):
            raise QueueStateError("envelope claim is not current")
        delivery = self._deliveries[claim.queue_delivery_id]
        if (
            envelope.queue_delivery_id != delivery.queue_delivery_id
            or envelope.worker_service_reference != claim.worker_service_reference
            or envelope.fence != claim.fence
            or envelope.semantic_request_id != delivery.semantic_request_id
            or envelope.queue_message_id != delivery.queue_message_id
            or envelope.workflow_attempt_id != delivery.workflow_attempt_id
        ):
            raise QueueConflictError("envelope claim binding is invalid")
