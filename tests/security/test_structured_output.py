import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from app.security import (
    MAX_CONTROL_SCAN_DEPTH,
    SecurityError,
    SecurityErrorCode,
    StructuredOutputSecurityResult,
    validate_model_action_output,
)
from app.workflow.model_domain import (
    MAX_STRUCTURED_OUTPUT_BYTES,
    StructuredField,
    StructuredFieldType,
    StructuredOutputSchema,
    StructuredValidationStatus,
    validate_structured_output,
)


CORPUS_PATH = Path(__file__).with_name("fixtures") / "sec002_adversarial.json"
CORPUS_SCHEMA_VERSION = "testgap.sec002-adversarial.v1"


def load_corpus() -> list[dict[str, object]]:
    raw = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    if raw.get("schema_version") != CORPUS_SCHEMA_VERSION:
        pytest.fail("unsupported adversarial corpus schema_version")
    return list(raw["cases"])


CLOSED_SCHEMA = StructuredOutputSchema(
    (StructuredField("answer", StructuredFieldType.STRING),),
    allow_additional_fields=False,
)
OPEN_SCHEMA = StructuredOutputSchema(
    (StructuredField("answer", StructuredFieldType.STRING),),
    allow_additional_fields=True,
)


def reserved_key_payload(key: str, placement: str = "nested_object") -> str:
    if placement == "top_level":
        return json.dumps({key: {"value": True}})
    if placement == "nested_object":
        return json.dumps({"answer": "ok", "meta": {"deep": {key: {"enabled": True}}}})
    if placement == "array_nested":
        return json.dumps({"answer": "ok", "steps": [{"name": "a"}, {key: 1}]})
    if placement == "deep_chain":
        return json.dumps({"answer": "ok", "a": {"b": {"c": {"d": {key: "x"}}}}})
    raise ValueError(placement)


@pytest.mark.parametrize(
    "key",
    [
        "system_policy",
        "developer_policy",
        "tool_permissions",
        "allowed_paths",
        "network",
        "command",
        "credentials",
        "secrets",
    ],
)
def test_reserved_control_plane_keys_are_rejected_at_every_placement(key: str) -> None:
    for placement in ("top_level", "nested_object", "array_nested", "deep_chain"):
        result = validate_model_action_output(reserved_key_payload(key, placement), OPEN_SCHEMA)
        assert result.accepted is False, (key, placement)
        assert result.reason == SecurityErrorCode.UNTRUSTED_POLICY_MUTATION, (key, placement)
        assert (
            result.control_plane_key == "reserved_control_plane_policy"
        ), (key, placement)


@pytest.mark.parametrize(
    ("key", "classification"),
    [
        ("SYSTEM_POLICY", "reserved_control_plane_policy"),
        ("System_Policy", "reserved_control_plane_policy"),
        ("sYsTeM_pOlIcY", "reserved_control_plane_policy"),
        ("NETWORK", "reserved_control_plane_policy"),
        ("Workflow_State", "reserved_workflow_state"),
        ("RAG_BUDGET", "reserved_rag_budget"),
    ],
)
def test_attacker_key_text_is_never_echoed_in_control_plane_rejections(
    key: str, classification: str
) -> None:
    payload = json.dumps({"answer": "ok", "meta": {"deep": {key: {"enabled": True}}}})
    result = validate_model_action_output(payload, OPEN_SCHEMA)
    assert result.accepted is False
    assert result.control_plane_key == classification
    assert result.field is None
    assert result.detail == (
        f"reserved key rejected at nesting depth 2; classification {classification}"
    )
    residual_detail = str(result.detail).replace(classification, "")
    assert key.casefold() not in residual_detail


@pytest.mark.parametrize("key", ["workflow_state"])
def test_workflow_state_keys_map_to_their_own_reason(key: str) -> None:
    result = validate_model_action_output(reserved_key_payload(key, "nested_object"), OPEN_SCHEMA)
    assert result.accepted is False
    assert result.reason == SecurityErrorCode.WORKFLOW_STATE_MUTATION


SYNTHETIC_TOKEN = "sk-" + "S3NTIN3LTOKEN" * 4


def test_attacker_unexpected_field_name_is_suppressed_from_result() -> None:
    payload = json.dumps({"answer": "ok", SYNTHETIC_TOKEN: True})
    result = validate_model_action_output(payload, CLOSED_SCHEMA)
    assert result.accepted is False
    assert result.reason == SecurityErrorCode.MALFORMED_STRUCTURED_OUTPUT
    assert result.workflow_status == StructuredValidationStatus.UNEXPECTED_FIELD
    assert result.field is None
    assert result.detail == (
        "workflow structured validation reported UNEXPECTED_FIELD; "
        "field classification untrusted_origin_field"
    )
    rendered = repr(result) + str(result)
    assert SYNTHETIC_TOKEN not in rendered
    assert SYNTHETIC_TOKEN not in str(result.detail)
    assert SYNTHETIC_TOKEN not in str(result.field)


@pytest.mark.parametrize("payload", ['{"answer":"ok","extra":true}', '{"answer":42}'])
def test_schema_attributed_fields_are_propagated_but_attacker_keys_are_not(
    payload: str,
) -> None:
    result = validate_model_action_output(payload, CLOSED_SCHEMA)
    assert result.accepted is False
    if result.workflow_status == StructuredValidationStatus.UNEXPECTED_FIELD:
        assert result.field is None
    else:
        assert result.field == "answer"


def test_security_error_from_scan_bound_never_echoes_payload_bytes() -> None:
    deep_payload = "[" * 96 + json.dumps(SYNTHETIC_TOKEN) + "]" * 96
    with pytest.raises(SecurityError) as raised:
        validate_model_action_output(deep_payload, OPEN_SCHEMA)
    assert raised.value.code == SecurityErrorCode.CONTEXT_BOUND_EXCEEDED
    rendered_error = repr(raised.value) + str(raised.value)
    assert SYNTHETIC_TOKEN not in rendered_error
    assert SYNTHETIC_TOKEN not in raised.value.detail


def test_rag_budget_keys_map_to_their_own_reason() -> None:
    result = validate_model_action_output(reserved_key_payload("rag_budget", "array_nested"), CLOSED_SCHEMA)
    assert result.accepted is False
    assert result.reason == SecurityErrorCode.RAG_BUDGET_MUTATION


@pytest.mark.parametrize(
    "payload",
    [
        '{"answer":"ok","meta":{"SYSTEM_POLICY":{"priority":"highest"}}}',
        '{"Workflow_State":"PLANNING"}',
        '{"answer":"ok","NETWork":true}',
    ],
)
def test_case_variants_of_reserved_keys_are_rejected(payload: str) -> None:
    result = validate_model_action_output(payload, OPEN_SCHEMA)
    assert result.accepted is False
    assert result.reason in {
        SecurityErrorCode.UNTRUSTED_POLICY_MUTATION,
        SecurityErrorCode.WORKFLOW_STATE_MUTATION,
    }


def test_valid_output_is_accepted_and_consumes_workflow_boundary_unchanged() -> None:
    payload = '{"answer":"the candidate patch applies cleanly"}'
    direct = validate_structured_output(payload, CLOSED_SCHEMA)
    secured = validate_model_action_output(payload, CLOSED_SCHEMA)
    assert direct.status == StructuredValidationStatus.VALID
    assert secured.accepted is True
    assert secured.workflow_status == StructuredValidationStatus.VALID
    assert secured.reason is None
    assert secured.detail is None


def test_optional_fields_and_open_schemas_stay_valid_without_reserved_keys() -> None:
    schema = StructuredOutputSchema(
        (
            StructuredField("answer", StructuredFieldType.STRING),
            StructuredField("confidence", StructuredFieldType.NUMBER, required=False),
        ),
        allow_additional_fields=True,
    )
    result = validate_model_action_output('{"answer":"ok","confidence":0.9}', schema)
    assert result.accepted is True


@pytest.mark.parametrize(
    "payload",
    [
        "{not json",
        "",
        "null",
        '"just a string"',
        "[1, 2, 3]",
        "{}",
        '{"answer":42}',
        '{"answer":"a","answer":"b"}',
        '{"answer":"ok","extra":true}',
        '{"answer":true}',
        '{"answer":["not-a-string"]}',
        "NaN",
        "Infinity",
        '{"answer":"ok","x":01}',
    ],
)
def test_malformed_and_schema_invalid_outputs_fail_closed(payload: str) -> None:
    result = validate_model_action_output(payload, CLOSED_SCHEMA)
    assert result.accepted is False
    assert result.reason == SecurityErrorCode.MALFORMED_STRUCTURED_OUTPUT


@pytest.mark.parametrize("payload", [None, 42, 3.14, b'{"answer":"x"}', [], {}, object()])
def test_non_text_outputs_fail_closed(payload: object) -> None:
    result = validate_model_action_output(payload, CLOSED_SCHEMA)
    assert result.accepted is False
    assert result.reason == SecurityErrorCode.MALFORMED_STRUCTURED_OUTPUT


def test_oversized_outputs_fail_closed() -> None:
    oversized = '{"answer":"' + "x" * (MAX_STRUCTURED_OUTPUT_BYTES + 16) + '"}'
    result = validate_model_action_output(oversized, CLOSED_SCHEMA)
    assert result.accepted is False
    assert result.reason == SecurityErrorCode.MALFORMED_STRUCTURED_OUTPUT


def test_scan_depth_bound_fails_closed() -> None:
    deep = "[" * 96 + "]" * 96
    with pytest.raises(SecurityError) as raised:
        validate_model_action_output(deep, OPEN_SCHEMA)
    assert raised.value.code == SecurityErrorCode.CONTEXT_BOUND_EXCEEDED


def test_node_count_bound_fails_closed() -> None:
    wide = "[" + ",".join(["0"] * 6_000) + "]"
    with pytest.raises(SecurityError) as raised:
        validate_model_action_output(wide, OPEN_SCHEMA)
    assert raised.value.code == SecurityErrorCode.CONTEXT_BOUND_EXCEEDED


def test_schema_type_rejection_is_required_for_non_schema_inputs() -> None:
    with pytest.raises(SecurityError) as raised:
        validate_model_action_output('{"answer":"ok"}', "not a schema")  # type: ignore[arg-type]
    assert raised.value.code == SecurityErrorCode.INVALID_SECURITY_INPUT


def test_structural_detection_is_independent_from_keyword_content() -> None:
    hostile_structure = '{"answer":"ok","notes":{"rag_budget":{"max_tokens":9}}}'
    rejected = validate_model_action_output(hostile_structure, OPEN_SCHEMA)
    assert rejected.accepted is False
    assert rejected.reason == SecurityErrorCode.RAG_BUDGET_MUTATION

    renamed_structure = '{"answer":"ok","notes":{"budget_notes":{"max_tokens":9}}}'
    accepted = validate_model_action_output(renamed_structure, OPEN_SCHEMA)
    assert accepted.accepted is True

    keyword_prose = '{"answer":"the manual documents rag_budget network command credentials"}'
    prose_result = validate_model_action_output(keyword_prose, OPEN_SCHEMA)
    assert prose_result.accepted is True


def test_string_values_are_never_scanned_as_control_plane() -> None:
    payload = json.dumps(
        {
            "answer": "policy notes: system_policy tool_permissions allowed_paths network command "
            "workflow_state rag_budget credentials secrets",
        }
    )
    result = validate_model_action_output(payload, OPEN_SCHEMA)
    assert result.accepted is True


def test_trusted_schema_declaring_reserved_name_still_loses_to_structure() -> None:
    conflicting_schema = StructuredOutputSchema(
        (StructuredField("network", StructuredFieldType.BOOLEAN),),
        allow_additional_fields=False,
    )
    result = validate_model_action_output('{"network":true}', conflicting_schema)
    assert result.accepted is False
    assert result.reason == SecurityErrorCode.UNTRUSTED_POLICY_MUTATION


def test_corpus_structured_cases_are_rejected_with_expected_reasons() -> None:
    checked = 0
    for case_data in load_corpus():
        expected_reason = case_data["expected_structured_reason"]
        if expected_reason is None:
            continue
        checked += 1
        result = validate_model_action_output(str(case_data["structured_payload"]), CLOSED_SCHEMA)
        assert result.accepted is False, case_data["case_id"]
        assert result.reason is not None
        assert result.reason.value == expected_reason, case_data["case_id"]
    assert checked >= 4


def test_security_results_resist_mutation() -> None:
    result = validate_model_action_output("{broken", CLOSED_SCHEMA)
    assert isinstance(result, StructuredOutputSecurityResult)
    with pytest.raises(FrozenInstanceError):
        result.accepted = True  # type: ignore[misc]
