import pytest

from app.queue import (
    QUEUE_CONTRACT_VERSION,
    CorrelationId,
    EnvelopeValidator,
    QueueDeliveryId,
    QueueMessageId,
    QueueRuntimeLimits,
    QueueValidationError,
    SemanticRequestId,
)


def test_supported_contract_and_schema_are_accepted(validator, raw_envelope) -> None:
    envelope = validator.validate(raw_envelope)

    assert envelope.contract_version == QUEUE_CONTRACT_VERSION
    assert envelope.schema_version == "queue-test-v1"
    assert isinstance(envelope.semantic_request_id, SemanticRequestId)


def test_unknown_schema_is_rejected(validator, raw_envelope) -> None:
    raw_envelope["schema_version"] = "future-schema"

    with pytest.raises(QueueValidationError, match="schema"):
        validator.validate(raw_envelope)


def test_wrong_contract_version_is_rejected(validator, raw_envelope) -> None:
    raw_envelope["contract_version"] = "1.0.0-draft.1"

    with pytest.raises(QueueValidationError, match="contract"):
        validator.validate(raw_envelope)


def test_unknown_envelope_field_is_rejected(validator, raw_envelope) -> None:
    raw_envelope["future_semantic_switch"] = True

    with pytest.raises(QueueValidationError, match="unknown envelope"):
        validator.validate(raw_envelope)


def test_unknown_operation_kind_is_rejected(validator, raw_envelope) -> None:
    raw_envelope["operation_kind"] = "workflow.complete"

    with pytest.raises(QueueValidationError, match="operation kind"):
        validator.validate(raw_envelope)


@pytest.mark.parametrize(
    "field,value",
    [
        ("publication_state", "provider_says_maybe"),
        ("retry_classification", "workflow_retry"),
    ],
)
def test_unknown_semantic_state_values_are_rejected(
    validator, raw_envelope, field, value
) -> None:
    raw_envelope[field] = value

    with pytest.raises(QueueValidationError, match="unknown"):
        validator.validate(raw_envelope)


@pytest.mark.parametrize(
    "field,value",
    [
        ("access_token", "secret"),
        ("authorization_header", "Bearer secret"),
        ("repository", b"raw repository"),
        ("patch", "diff --git"),
        ("prompt", "do something"),
        ("command", "rm something"),
        ("evidence_bytes", b"evidence"),
    ],
)
def test_prohibited_payload_fields_are_rejected(
    validator, raw_envelope, field, value
) -> None:
    raw_envelope[field] = value

    with pytest.raises(QueueValidationError, match="prohibited"):
        validator.validate(raw_envelope)


@pytest.mark.parametrize(
    "metadata",
    [
        {"unknown": "value"},
        {"trace_label": {"nested": "object"}},
        {"trace_label": ["list"]},
        {"trace_label": b"bytes"},
        {"trace_label": "Authorization: Bearer secret"},
    ],
)
def test_arbitrary_nested_or_secret_metadata_is_rejected(
    validator, raw_envelope, metadata
) -> None:
    raw_envelope["bounded_metadata"] = metadata

    with pytest.raises(QueueValidationError):
        validator.validate(raw_envelope)


def test_metadata_cardinality_and_value_bounds_are_enforced(
    validator, raw_envelope
) -> None:
    raw_envelope["bounded_metadata"] = {
        "trace_label": "x" * 33,
        "priority": 1,
    }
    with pytest.raises(QueueValidationError, match="value"):
        validator.validate(raw_envelope)

    too_small = EnvelopeValidator(
        frozenset({"queue-test-v1"}),
        frozenset({"test.execute"}),
        frozenset({"trace_label", "priority"}),
        QueueRuntimeLimits(128, 4096, 1, 32, 32),
    )
    raw_envelope["bounded_metadata"] = {"trace_label": "x", "priority": 1}
    with pytest.raises(QueueValidationError, match="item bound"):
        too_small.validate(raw_envelope)


def test_total_envelope_byte_bound_is_enforced(raw_envelope) -> None:
    validator = EnvelopeValidator(
        frozenset({"queue-test-v1"}),
        frozenset({"test.execute"}),
        frozenset(),
        QueueRuntimeLimits(128, 10, 1, 32, 32),
    )

    with pytest.raises(QueueValidationError, match="byte bound"):
        validator.validate(raw_envelope)


def test_security_policy_hook_fails_closed(raw_envelope) -> None:
    validator = EnvelopeValidator(
        frozenset({"queue-test-v1"}),
        frozenset({"test.execute"}),
        frozenset({"priority"}),
        QueueRuntimeLimits(128, 4096, 2, 32, 32),
        security_policy=lambda key, value: value != 9,
    )
    raw_envelope["bounded_metadata"] = {"priority": 9}

    with pytest.raises(QueueValidationError, match="Security policy"):
        validator.validate(raw_envelope)


def test_message_and_delivery_identities_are_distinct_types() -> None:
    message = QueueMessageId("same-text")
    delivery = QueueDeliveryId("same-text")

    assert message != delivery
    assert not isinstance(message, QueueDeliveryId)


def test_trace_identity_does_not_become_semantic_identity() -> None:
    assert CorrelationId("same-text") != SemanticRequestId("same-text")
