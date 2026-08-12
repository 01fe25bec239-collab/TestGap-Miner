import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path

import pytest

from app.workflow import (
    ModelBudget,
    ModelDomainError,
    ModelDomainErrorCode,
    ModelFailureClass,
    ModelIdentity,
    ModelRequest,
    ModelResult,
    ModelResultStatus,
    PromptDefinition,
    PromptRegistry,
    PromptTemplateRef,
    PromptVariables,
    StructuredField,
    StructuredFieldType,
    StructuredOutputSchema,
    StructuredValidationResult,
    StructuredValidationStatus,
    validate_model_request,
    validate_structured_output,
)
from app.workflow.model_domain import (
    MAX_INPUT_TOKENS,
    MAX_LATENCY_MS,
    MAX_OUTPUT_TOKENS,
    MAX_REGISTRY_ENTRIES,
    MAX_RETRY_BUDGET,
    MAX_SCHEMA_FIELDS,
    MAX_TEMPLATE_VARIABLES,
    MAX_VARIABLE_PAYLOAD_BYTES,
    MAX_VARIABLE_VALUE_BYTES,
)
from app.workflow import model_domain


MODEL = ModelIdentity(
    provider_ref="provider.test",
    model_id="model.test",
    capability_profile="structured.test",
    configuration_version="cfg-1",
)
PROMPT_REF = PromptTemplateRef("candidate.plan", "1.0.0")
BUDGET = ModelBudget(4_096, 1_024, retry_budget=1, max_latency_ms=30_000)


def prompt_definition(
    *,
    ref: PromptTemplateRef = PROMPT_REF,
    text: str = "Plan for {project} in {language}",
    variables: object = ("project", "language"),
    metadata: object = (("purpose", "planning"),),
) -> PromptDefinition:
    return PromptDefinition(
        ref=ref,
        template_text=text,
        variables=variables,  # type: ignore[arg-type]
        metadata=metadata,  # type: ignore[arg-type]
    )


def model_request(
    *,
    prompt: PromptTemplateRef = PROMPT_REF,
    variables: object = (("project", "Lang"), ("language", "Java")),
    output_schema: StructuredOutputSchema | None = None,
) -> ModelRequest:
    return ModelRequest(
        model=MODEL,
        prompt=prompt,
        variables=variables,  # type: ignore[arg-type]
        budget=BUDGET,
        output_schema=output_schema,
        correlation_ref="correlation:test",
        provenance_ref="provenance:test",
    )


def structured_schema() -> StructuredOutputSchema:
    return StructuredOutputSchema(
        (
            StructuredField("count", StructuredFieldType.INTEGER),
            StructuredField("name", StructuredFieldType.STRING),
            StructuredField(
                "enabled", StructuredFieldType.BOOLEAN, required=False
            ),
        )
    )


def assert_error(
    code: ModelDomainErrorCode, operation  # type: ignore[no-untyped-def]
) -> None:
    with pytest.raises(ModelDomainError) as raised:
        operation()
    assert raised.value.code == code


def test_model_identity_is_provider_neutral_normalized_and_deterministic() -> None:
    normalized = ModelIdentity(
        provider_ref=" provider.test ",
        model_id=" model.test ",
        capability_profile=" structured.test ",
        configuration_version=" cfg-1 ",
    )
    assert normalized == MODEL
    assert normalized.canonical_json() == MODEL.canonical_json()
    assert "provider.test" in MODEL.canonical_json()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("provider_ref", "Ａ"),
        ("model_id", "K"),
        ("capability_profile", "Ａ"),
        ("configuration_version", "K"),
    ],
)
def test_model_identity_rejects_compatibility_unicode(
    field: str, value: str
) -> None:
    source: dict[str, str | None] = {
        "provider_ref": "provider.test",
        "model_id": "model.test",
        "capability_profile": "structured.test",
        "configuration_version": "cfg-1",
    }
    source[field] = value
    assert_error(
        ModelDomainErrorCode.INVALID_IDENTITY,
        lambda: ModelIdentity(**source),  # type: ignore[arg-type]
    )


@pytest.mark.parametrize(
    "operation",
    [
        lambda: PromptTemplateRef("Ａ", "1"),
        lambda: PromptTemplateRef("prompt", "K"),
        lambda: PromptVariables.build({"Ａ": "value"}),
        lambda: prompt_definition(metadata={"K": "value"}),
        lambda: StructuredField("Ａ", StructuredFieldType.STRING),
    ],
)
def test_prompt_and_schema_identities_reject_compatibility_unicode(
    operation,
) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ModelDomainError):
        operation()


def test_ascii_identity_whitespace_canonicalization_remains_deterministic() -> None:
    assert PromptTemplateRef(" prompt ", " 1 ") == PromptTemplateRef("prompt", "1")


@pytest.mark.parametrize(
    "values",
    [
        {"provider_ref": ""},
        {"provider_ref": "   "},
        {"model_id": ""},
        {"model_id": "model test"},
        {"configuration_version": ""},
        {"configuration_version": "version?"},
    ],
)
def test_model_identity_rejects_empty_or_malformed_values(
    values: dict[str, str],
) -> None:
    source = {
        "provider_ref": "provider.test",
        "model_id": "model.test",
        "configuration_version": "cfg-1",
    }
    source.update(values)
    assert_error(
        ModelDomainErrorCode.INVALID_IDENTITY, lambda: ModelIdentity(**source)
    )


def test_prompt_definition_normalizes_semantically_unordered_content() -> None:
    first = prompt_definition(
        variables=["project", "language"],
        metadata={"purpose": "planning", "stage": "initial"},
    )
    second = prompt_definition(
        variables=["language", "project"],
        metadata={"stage": "initial", "purpose": "planning"},
    )
    assert first == second
    assert first.content_digest == second.content_digest
    assert first.canonical_json() == second.canonical_json()


def test_prompt_content_change_changes_digest() -> None:
    original = prompt_definition()
    assert prompt_definition(text="Different {project} {language}").content_digest != (
        original.content_digest
    )
    assert prompt_definition(variables=("project",)).content_digest != (
        original.content_digest
    )
    assert prompt_definition(metadata={"purpose": "repair"}).content_digest != (
        original.content_digest
    )


@pytest.mark.parametrize(
    "operation",
    [
        lambda: PromptTemplateRef("", "1"),
        lambda: PromptTemplateRef("prompt", ""),
        lambda: prompt_definition(text="  "),
        lambda: prompt_definition(variables=("project", "project")),
        lambda: prompt_definition(variables=("not valid",)),
    ],
)
def test_prompt_identity_and_definition_reject_invalid_values(operation) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ModelDomainError):
        operation()


def test_domain_values_defensively_copy_inputs_and_are_frozen() -> None:
    declared = ["project", "language"]
    metadata = {"purpose": "planning"}
    definition = prompt_definition(variables=declared, metadata=metadata)
    request_values = {"project": "Lang", "language": "Java"}
    request = model_request(variables=request_values)
    registry_input = [definition]
    registry = PromptRegistry.build(registry_input)

    declared.append("later")
    metadata["purpose"] = "changed"
    request_values["project"] = "Changed"
    registry_input.clear()

    assert definition.variables == ("language", "project")
    assert definition.metadata == (("purpose", "planning"),)
    assert request.variables.canonical_dict()["project"] == "Lang"
    assert registry.lookup(PROMPT_REF) == definition
    with pytest.raises(FrozenInstanceError):
        MODEL.model_id = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        registry._entries = ()  # type: ignore[misc]
    with pytest.raises(AttributeError):
        registry.entries.append(definition)  # type: ignore[attr-defined]


def test_registry_lookup_and_canonical_order_are_deterministic() -> None:
    first = prompt_definition(ref=PromptTemplateRef("prompt.a", "1"))
    second = prompt_definition(ref=PromptTemplateRef("prompt.b", "1"))
    left = PromptRegistry.build([second, first])
    right = PromptRegistry.build([first, second])
    assert left.entries == (first, second)
    assert left.lookup(second.ref) is second
    assert left.canonical_json() == right.canonical_json()


def test_registry_entry_count_boundaries() -> None:
    entries = [
        prompt_definition(
            ref=PromptTemplateRef(f"prompt.{index}", "1"),
            variables=(),
            metadata=(),
        )
        for index in range(MAX_REGISTRY_ENTRIES + 1)
    ]
    assert len(PromptRegistry.build(entries[:-1]).entries) == MAX_REGISTRY_ENTRIES
    assert_error(
        ModelDomainErrorCode.INVALID_PROMPT_DEFINITION,
        lambda: PromptRegistry.build(entries),
    )


def test_registry_rejects_exact_duplicates_and_version_conflicts() -> None:
    definition = prompt_definition()
    assert_error(
        ModelDomainErrorCode.INVALID_PROMPT_DEFINITION,
        lambda: PromptRegistry.build([definition, definition]),
    )
    assert_error(
        ModelDomainErrorCode.PROMPT_VERSION_CONFLICT,
        lambda: PromptRegistry.build(
            [definition, prompt_definition(text="Changed {project} {language}")]
        ),
    )


def test_unknown_prompt_lookup_is_a_typed_deterministic_error() -> None:
    registry = PromptRegistry.build([prompt_definition()])
    missing = PromptTemplateRef("missing.prompt", "1")
    for _ in range(2):
        assert_error(
            ModelDomainErrorCode.PROMPT_NOT_FOUND,
            lambda: registry.lookup(missing),
        )


def test_model_budget_accepts_bounded_values_and_zero_retries() -> None:
    assert ModelBudget(1, 1, retry_budget=0).retry_budget == 0
    assert ModelBudget(
        MAX_INPUT_TOKENS,
        MAX_OUTPUT_TOKENS,
        retry_budget=MAX_RETRY_BUDGET,
        max_latency_ms=MAX_LATENCY_MS,
    ).max_latency_ms == MAX_LATENCY_MS


@pytest.mark.parametrize(
    "values",
    [
        {"max_input_tokens": 0},
        {"max_input_tokens": -1},
        {"max_input_tokens": True},
        {"max_input_tokens": 1.5},
        {"max_input_tokens": MAX_INPUT_TOKENS + 1},
        {"max_output_tokens": 0},
        {"max_output_tokens": -1},
        {"max_output_tokens": False},
        {"max_output_tokens": "1"},
        {"max_output_tokens": MAX_OUTPUT_TOKENS + 1},
        {"retry_budget": -1},
        {"retry_budget": True},
        {"retry_budget": MAX_RETRY_BUDGET + 1},
        {"max_latency_ms": 0},
        {"max_latency_ms": -1},
        {"max_latency_ms": True},
        {"max_latency_ms": MAX_LATENCY_MS + 1},
    ],
)
def test_model_budget_rejects_invalid_values(values: dict[str, object]) -> None:
    source: dict[str, object] = {
        "max_input_tokens": 100,
        "max_output_tokens": 50,
        "retry_budget": 0,
        "max_latency_ms": None,
    }
    source.update(values)
    assert_error(
        ModelDomainErrorCode.INVALID_MODEL_BUDGET,
        lambda: ModelBudget(**source),  # type: ignore[arg-type]
    )


def test_request_variables_are_normalized_and_duplicates_are_rejected() -> None:
    first = PromptVariables.build(
        [("project", "Lang"), ("language", "Java")]
    )
    second = PromptVariables.build(
        [("language", "Java"), ("project", "Lang")]
    )
    assert first == second
    assert first.items == (("language", "Java"), ("project", "Lang"))
    assert_error(
        ModelDomainErrorCode.INVALID_MODEL_REQUEST,
        lambda: PromptVariables.build([("project", "a"), ("project", "b")]),
    )
    assert_error(
        ModelDomainErrorCode.INVALID_MODEL_REQUEST,
        lambda: PromptVariables.build([("invalid name", "a")]),
    )


@pytest.mark.parametrize(
    ("domain_type", "code"),
    [
        (PromptRegistry, ModelDomainErrorCode.INVALID_PROMPT_DEFINITION),
        (PromptVariables, ModelDomainErrorCode.INVALID_MODEL_REQUEST),
    ],
)
def test_init_false_domain_values_reject_direct_construction(
    domain_type: type, code: ModelDomainErrorCode
) -> None:
    assert_error(code, domain_type)


def test_all_init_false_domain_values_have_guarded_constructors() -> None:
    guarded = {
        value
        for value in vars(model_domain).values()
        if isinstance(value, type)
        and is_dataclass(value)
        and not value.__dataclass_params__.init
    }
    assert guarded == {PromptRegistry, PromptVariables}
    for domain_type in guarded:
        with pytest.raises(ModelDomainError):
            domain_type()


def test_request_variable_bounds_are_enforced() -> None:
    assert_error(
        ModelDomainErrorCode.INVALID_MODEL_REQUEST,
        lambda: PromptVariables.build(
            [(f"value_{index}", "x") for index in range(MAX_TEMPLATE_VARIABLES + 1)]
        ),
    )


def test_variable_value_byte_boundaries() -> None:
    exact = PromptVariables.build({"value": "x" * MAX_VARIABLE_VALUE_BYTES})
    assert len(exact.canonical_dict()["value"].encode("utf-8")) == (
        MAX_VARIABLE_VALUE_BYTES
    )
    assert_error(
        ModelDomainErrorCode.INVALID_MODEL_REQUEST,
        lambda: PromptVariables.build(
            {"value": "x" * (MAX_VARIABLE_VALUE_BYTES + 1)}
        ),
    )


def test_multibyte_variable_values_are_bounded_by_utf8_bytes() -> None:
    exact_value = "é" * (MAX_VARIABLE_VALUE_BYTES // 2)
    assert len(exact_value) < MAX_VARIABLE_VALUE_BYTES
    assert PromptVariables.build({"value": exact_value}).canonical_dict() == {
        "value": exact_value
    }
    assert_error(
        ModelDomainErrorCode.INVALID_MODEL_REQUEST,
        lambda: PromptVariables.build({"value": exact_value + "a"}),
    )


def test_aggregate_variable_payload_byte_boundaries() -> None:
    exact_values = {
        "a": "x" * MAX_VARIABLE_VALUE_BYTES,
        "b": "x" * MAX_VARIABLE_VALUE_BYTES,
        "c": "x" * MAX_VARIABLE_VALUE_BYTES,
        "d": "x" * (MAX_VARIABLE_PAYLOAD_BYTES - 3 * MAX_VARIABLE_VALUE_BYTES - 4),
    }
    exact = PromptVariables.build(exact_values)
    assert sum(
        len(name.encode("utf-8")) + len(value.encode("utf-8"))
        for name, value in exact.items
    ) == MAX_VARIABLE_PAYLOAD_BYTES
    over = dict(exact_values)
    over["d"] += "x"
    assert_error(
        ModelDomainErrorCode.INVALID_MODEL_REQUEST,
        lambda: PromptVariables.build(over),
    )


def test_model_request_rejects_structurally_incomplete_variables() -> None:
    incomplete = object.__new__(PromptVariables)
    assert_error(
        ModelDomainErrorCode.INVALID_MODEL_REQUEST,
        lambda: ModelRequest(MODEL, PROMPT_REF, incomplete, BUDGET),
    )


def test_request_validation_never_leaks_attribute_error_for_incomplete_values() -> None:
    request = model_request()
    object.__setattr__(request, "variables", object.__new__(PromptVariables))
    assert_error(
        ModelDomainErrorCode.INVALID_MODEL_REQUEST,
        lambda: validate_model_request(
            request, PromptRegistry.build([prompt_definition()])
        ),
    )
    assert_error(
        ModelDomainErrorCode.INVALID_PROMPT_DEFINITION,
        lambda: validate_model_request(request, object.__new__(PromptRegistry)),
    )


@pytest.mark.parametrize(
    "operation",
    [
        lambda: prompt_definition(text="invalid \ud800"),
        lambda: PromptVariables.build({"value": "invalid \ud800"}),
        lambda: prompt_definition(metadata={"key": "invalid \ud800"}),
        lambda: StructuredValidationResult("VALID"),
        lambda: StructuredValidationResult(
            StructuredValidationStatus.VALID, detail="contradictory"
        ),
    ],
)
def test_invalid_public_domain_construction_is_typed(operation) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ModelDomainError):
        operation()
    assert_error(
        ModelDomainErrorCode.INVALID_MODEL_REQUEST,
        lambda: PromptVariables.build(
            [("project", "x" * (MAX_VARIABLE_VALUE_BYTES + 1))]
        ),
    )
    per_value = min(MAX_VARIABLE_VALUE_BYTES, MAX_VARIABLE_PAYLOAD_BYTES // 4)
    assert_error(
        ModelDomainErrorCode.INVALID_MODEL_REQUEST,
        lambda: PromptVariables.build(
            [(f"value_{index}", "x" * per_value) for index in range(5)]
        ),
    )


def test_request_to_prompt_validation_accepts_exact_reference_and_variables() -> None:
    definition = prompt_definition()
    registry = PromptRegistry.build([definition])
    assert validate_model_request(model_request(), registry) is definition


@pytest.mark.parametrize(
    ("candidate_request", "code", "detail"),
    [
        (
            model_request(variables={"project": "Lang"}),
            ModelDomainErrorCode.INVALID_MODEL_REQUEST,
            "missing prompt variable language",
        ),
        (
            model_request(
                variables={
                    "project": "Lang",
                    "language": "Java",
                    "extra": "value",
                }
            ),
            ModelDomainErrorCode.INVALID_MODEL_REQUEST,
            "unexpected prompt variable extra",
        ),
        (
            model_request(prompt=PromptTemplateRef("candidate.plan", "2.0.0")),
            ModelDomainErrorCode.PROMPT_NOT_FOUND,
            "prompt candidate.plan@2.0.0 is not registered",
        ),
    ],
)
def test_request_to_prompt_validation_fails_closed(
    candidate_request: ModelRequest, code: ModelDomainErrorCode, detail: str
) -> None:
    with pytest.raises(ModelDomainError) as raised:
        validate_model_request(
            candidate_request, PromptRegistry.build([prompt_definition()])
        )
    assert (raised.value.code, raised.value.detail) == (code, detail)


def test_equivalent_requests_and_schemas_have_identical_canonical_output() -> None:
    schema_left = StructuredOutputSchema(
        [
            StructuredField("name", StructuredFieldType.STRING),
            StructuredField("count", StructuredFieldType.INTEGER),
        ]
    )
    schema_right = StructuredOutputSchema(
        [
            StructuredField("count", StructuredFieldType.INTEGER),
            StructuredField("name", StructuredFieldType.STRING),
        ]
    )
    left = model_request(
        variables={"project": "Lang", "language": "Java"},
        output_schema=schema_left,
    )
    right = model_request(
        variables={"language": "Java", "project": "Lang"},
        output_schema=schema_right,
    )
    assert left == right
    assert left.canonical_json() == right.canonical_json()
    assert schema_left.canonical_json() == schema_right.canonical_json()


def test_schema_field_count_boundaries() -> None:
    fields_at_limit = [
        StructuredField(f"field_{index}", StructuredFieldType.STRING)
        for index in range(MAX_SCHEMA_FIELDS)
    ]
    assert len(StructuredOutputSchema(fields_at_limit).fields) == MAX_SCHEMA_FIELDS
    assert_error(
        ModelDomainErrorCode.INVALID_STRUCTURED_SCHEMA,
        lambda: StructuredOutputSchema(
            fields_at_limit
            + [StructuredField("field_over", StructuredFieldType.STRING)]
        ),
    )


def test_structured_output_valid_and_optional_field_semantics() -> None:
    schema = structured_schema()
    assert validate_structured_output('{"name":"x","count":1}', schema) == (
        StructuredValidationResult(StructuredValidationStatus.VALID)
    )
    assert validate_structured_output(
        '{"enabled":true,"count":1,"name":"x"}', schema
    ).status == StructuredValidationStatus.VALID


@pytest.mark.parametrize(
    ("output", "status", "field"),
    [
        ("{", StructuredValidationStatus.MALFORMED, None),
        ('{"name":"a","name":"b","count":1}', StructuredValidationStatus.MALFORMED, None),
        ("[]", StructuredValidationStatus.SCHEMA_MISMATCH, None),
        ('{"name":"x"}', StructuredValidationStatus.MISSING_REQUIRED_FIELD, "count"),
        (
            '{"name":"x","count":1,"extra":true}',
            StructuredValidationStatus.UNEXPECTED_FIELD,
            "extra",
        ),
        ('{"name":"x","count":"1"}', StructuredValidationStatus.SCHEMA_MISMATCH, "count"),
        ('{"name":"x","count":true}', StructuredValidationStatus.SCHEMA_MISMATCH, "count"),
    ],
)
def test_structured_output_failure_classification(
    output: str, status: StructuredValidationStatus, field: str | None
) -> None:
    result = validate_structured_output(output, structured_schema())
    assert (result.status, result.field) == (status, field)


@pytest.mark.parametrize("root", ['"text"', "1", "true", "null", "[]"])
def test_scalar_and_array_roots_are_schema_mismatches(root: str) -> None:
    assert validate_structured_output(root, structured_schema()).status == (
        StructuredValidationStatus.SCHEMA_MISMATCH
    )


def test_missing_required_field_precedes_unexpected_field() -> None:
    result = validate_structured_output(
        '{"name":"x","extra":1}', structured_schema()
    )
    assert (result.status, result.field) == (
        StructuredValidationStatus.MISSING_REQUIRED_FIELD,
        "count",
    )


def test_invalid_unexpected_key_is_typed_as_unexpected_field() -> None:
    schema = StructuredOutputSchema([StructuredField("a", StructuredFieldType.INTEGER)])
    result = validate_structured_output('{"a":1,"bad-key":2}', schema)
    assert (result.status, result.field) == (
        StructuredValidationStatus.UNEXPECTED_FIELD,
        "bad-key",
    )


def test_giant_json_integer_returns_a_typed_non_valid_result() -> None:
    schema = StructuredOutputSchema([StructuredField("a", StructuredFieldType.INTEGER)])
    result = validate_structured_output('{"a":' + "9" * 5_000 + "}", schema)
    assert result.status == StructuredValidationStatus.MALFORMED


@pytest.mark.parametrize("value", ['{"a":"\ud800"}', '{"a":"\\ud800"}'])
def test_unpaired_surrogate_returns_a_typed_non_valid_result(value: str) -> None:
    schema = StructuredOutputSchema([StructuredField("a", StructuredFieldType.STRING)])
    result = validate_structured_output(value, schema)
    assert result.status == StructuredValidationStatus.MALFORMED


@pytest.mark.parametrize(
    ("token", "status"),
    [
        ("NaN", StructuredValidationStatus.MALFORMED),
        ("Infinity", StructuredValidationStatus.MALFORMED),
        ("-Infinity", StructuredValidationStatus.MALFORMED),
        ("1e400", StructuredValidationStatus.SCHEMA_MISMATCH),
    ],
)
def test_non_standard_and_non_finite_numbers_are_never_valid(
    token: str, status: StructuredValidationStatus
) -> None:
    schema = StructuredOutputSchema(
        [StructuredField("value", StructuredFieldType.NUMBER)]
    )
    assert validate_structured_output(
        f'{{"value":{token}}}', schema
    ).status == status


@pytest.mark.parametrize(
    ("output", "schema"),
    [
        (
            '{"value":{"nested":[1e400]}}',
            StructuredOutputSchema(
                [StructuredField("value", StructuredFieldType.OBJECT)]
            ),
        ),
        (
            '{"value":[{"nested":1e400}]}',
            StructuredOutputSchema(
                [StructuredField("value", StructuredFieldType.ARRAY)]
            ),
        ),
        (
            '{"name":"x","extra":{"nested":1e400}}',
            StructuredOutputSchema(
                [StructuredField("name", StructuredFieldType.STRING)],
                allow_additional_fields=True,
            ),
        ),
    ],
)
def test_nested_and_additional_non_finite_numbers_are_never_valid(
    output: str, schema: StructuredOutputSchema
) -> None:
    assert validate_structured_output(output, schema).status == (
        StructuredValidationStatus.SCHEMA_MISMATCH
    )


@pytest.mark.parametrize(
    ("field_type", "value"),
    [
        (StructuredFieldType.NUMBER, "true"),
        (StructuredFieldType.NUMBER, "false"),
        (StructuredFieldType.INTEGER, "true"),
        (StructuredFieldType.INTEGER, "false"),
    ],
)
def test_booleans_do_not_satisfy_number_or_integer(
    field_type: StructuredFieldType, value: str
) -> None:
    schema = StructuredOutputSchema([StructuredField("value", field_type)])
    assert validate_structured_output(
        f'{{"value":{value}}}', schema
    ).status == StructuredValidationStatus.SCHEMA_MISMATCH


@pytest.mark.parametrize(
    ("field_type", "value"),
    [
        (StructuredFieldType.STRING, '"x"'),
        (StructuredFieldType.INTEGER, "1"),
        (StructuredFieldType.NUMBER, "1.5"),
        (StructuredFieldType.BOOLEAN, "true"),
        (StructuredFieldType.OBJECT, "{}"),
        (StructuredFieldType.ARRAY, "[]"),
    ],
)
def test_every_structured_field_type_is_supported(
    field_type: StructuredFieldType, value: str
) -> None:
    schema = StructuredOutputSchema([StructuredField("value", field_type)])
    assert validate_structured_output(
        f'{{"value":{value}}}', schema
    ).status == StructuredValidationStatus.VALID


def test_additional_fields_are_only_allowed_explicitly() -> None:
    schema = StructuredOutputSchema(
        [StructuredField("name", StructuredFieldType.STRING)],
        allow_additional_fields=True,
    )
    assert validate_structured_output(
        '{"name":"x","extra":1}', schema
    ).status == StructuredValidationStatus.VALID


def test_structured_validation_is_deterministic() -> None:
    operation = lambda: validate_structured_output(  # noqa: E731
        '{"z":1,"name":"x","count":1}', structured_schema()
    )
    expected = operation()
    assert [operation() for _ in range(10)] == [expected] * 10
    assert (expected.status, expected.field) == (
        StructuredValidationStatus.UNEXPECTED_FIELD,
        "z",
    )


def test_all_model_result_outcomes_have_valid_distinct_shapes() -> None:
    valid = StructuredValidationResult(StructuredValidationStatus.VALID)
    invalid = StructuredValidationResult(
        StructuredValidationStatus.SCHEMA_MISMATCH,
        "count",
        "field count must be INTEGER",
    )
    results = {
        ModelResult(ModelResultStatus.SUCCESS, output_text="ok"),
        ModelResult(
            ModelResultStatus.SUCCESS,
            output_text='{"count":1}',
            structured_validation=valid,
        ),
        ModelResult(ModelResultStatus.REFUSAL, refusal_reason="policy refusal"),
        ModelResult(
            ModelResultStatus.PROVIDER_OR_MODEL_FAILURE,
            failure_class=ModelFailureClass.TRANSPORT_FAILURE,
        ),
        ModelResult(
            ModelResultStatus.INVALID_STRUCTURED_OUTPUT,
            structured_validation=invalid,
        ),
        ModelResult(ModelResultStatus.BUDGET_EXCEEDED, detail="input budget"),
        ModelResult(ModelResultStatus.TIMEOUT, detail="latency budget"),
        ModelResult(ModelResultStatus.VALIDATION_FAILURE, detail="request invalid"),
    }
    assert {result.status for result in results} == set(ModelResultStatus)
    assert ModelResultStatus.REFUSAL != ModelResultStatus.PROVIDER_OR_MODEL_FAILURE


@pytest.mark.parametrize(
    "operation",
    [
        lambda: ModelResult(ModelResultStatus.SUCCESS),
        lambda: ModelResult(
            ModelResultStatus.SUCCESS,
            output_text="ok",
            failure_class=ModelFailureClass.MODEL_ERROR,
        ),
        lambda: ModelResult(
            ModelResultStatus.SUCCESS,
            output_text="ok",
            refusal_reason="no",
        ),
        lambda: ModelResult(ModelResultStatus.REFUSAL),
        lambda: ModelResult(
            ModelResultStatus.REFUSAL,
            refusal_reason="no",
            failure_class=ModelFailureClass.TRANSPORT_FAILURE,
        ),
        lambda: ModelResult(ModelResultStatus.PROVIDER_OR_MODEL_FAILURE),
        lambda: ModelResult(
            ModelResultStatus.INVALID_STRUCTURED_OUTPUT,
            structured_validation=StructuredValidationResult(
                StructuredValidationStatus.VALID
            ),
        ),
        lambda: ModelResult(ModelResultStatus.INVALID_STRUCTURED_OUTPUT),
        lambda: ModelResult(
            ModelResultStatus.BUDGET_EXCEEDED,
            failure_class=ModelFailureClass.MODEL_ERROR,
        ),
        lambda: ModelResult(
            ModelResultStatus.TIMEOUT,
            failure_class=ModelFailureClass.TRANSPORT_FAILURE,
        ),
        lambda: ModelResult(ModelResultStatus.TIMEOUT, output_text="late"),
        lambda: ModelResult(
            ModelResultStatus.VALIDATION_FAILURE,
            output_text="contradictory success payload",
        ),
    ],
)
def test_model_result_rejects_contradictory_shapes(operation) -> None:  # type: ignore[no-untyped-def]
    assert_error(ModelDomainErrorCode.INVALID_RESULT_SHAPE, operation)


def test_model_domain_has_no_provider_runtime_or_cross_component_dependency() -> None:
    source = Path(__file__).parents[2] / "apps/api/app/workflow/model_domain.py"
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module
    }
    forbidden = {
        "app.db",
        "app.queue",
        "app.execution",
        "app.evidence",
        "sqlalchemy",
        "httpx",
        "requests",
        "subprocess",
        "os",
        "random",
        "time",
        "openai",
        "anthropic",
    }
    assert not {
        module
        for module in imports
        if any(module == item or module.startswith(f"{item}.") for item in forbidden)
    }
    request_fields = {field.name for field in fields(ModelRequest)}
    assert not request_fields & {
        "api_key",
        "credential",
        "client",
        "transport",
        "provider_callable",
    }
