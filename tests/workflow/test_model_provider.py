import ast
import json
from dataclasses import fields, replace as dataclass_replace
from pathlib import Path

import pytest

from app.workflow import (
    AttemptedTarget,
    CriticClient,
    DeterministicFakeProvider,
    FallbackPlan,
    GeneratorClient,
    InvocationConfiguration,
    ModelBudget,
    ModelDomainError,
    ModelDomainErrorCode,
    ModelFailureClass,
    ModelIdentity,
    ModelInvocationResult,
    ModelProvider,
    ModelRequest,
    ModelResult,
    ModelResultStatus,
    ModelRuntime,
    ModelRuntimeError,
    PlannerClient,
    ProviderFailureError,
    ProviderInvocationResult,
    ProviderTimeoutError,
    PromptDefinition,
    PromptRegistry,
    PromptTemplateRef,
    ProviderUsage,
    RetryableCondition,
    StructuredField,
    StructuredFieldType,
    StructuredOutputSchema,
    StructuredValidationStatus,
    validate_structured_output,
)
from app.workflow.model_domain import (
    MAX_STRUCTURED_OUTPUT_BYTES,
    ModelDomainErrorCode as _DomainCodeAlias,
)
from app.workflow import model_provider


PRIMARY = ModelIdentity(
    provider_ref="provider.primary",
    model_id="model.primary",
    configuration_version="cfg-1",
    capability_profile="profile.test",
)
SECONDARY = ModelIdentity(
    provider_ref="provider.secondary",
    model_id="model.secondary",
    configuration_version="cfg-1",
)
PLANNER_REF = PromptTemplateRef("planner.task", "1.0.0")
GENERATOR_REF = PromptTemplateRef("generator.patch", "2.1.0")
CRITIC_REF = PromptTemplateRef("critic.review", "1.5.0")
BUDGET = ModelBudget(4_096, 1_024, retry_budget=1, max_latency_ms=30_000)
CONFIG = InvocationConfiguration(temperature=0, seed=7)
SCHEMA = StructuredOutputSchema(
    (
        StructuredField("summary", StructuredFieldType.STRING),
        StructuredField("score", StructuredFieldType.INTEGER),
    )
)

PLANNER_DEFINITION = PromptDefinition(
    ref=PLANNER_REF,
    template_text="Plan {task} in {language}",
    variables=("language", "task"),
    metadata={"role": "planner"},
)
GENERATOR_DEFINITION = PromptDefinition(
    ref=GENERATOR_REF,
    template_text="Patch {task} in {language}",
    variables=("language", "task"),
    metadata={"role": "generator"},
)
CRITIC_DEFINITION = PromptDefinition(
    ref=CRITIC_REF,
    template_text="Review {task} in {language}",
    variables=("language", "task"),
    metadata={"role": "critic"},
)


def registry() -> PromptRegistry:
    return PromptRegistry.build(
        [PLANNER_DEFINITION, GENERATOR_DEFINITION, CRITIC_DEFINITION]
    )


def request(
    *,
    prompt: PromptTemplateRef = PLANNER_REF,
    model: ModelIdentity = PRIMARY,
    budget: ModelBudget = BUDGET,
    output_schema: StructuredOutputSchema | None = None,
    variables: object = (("task", "localise strings"), ("language", "Java")),
) -> ModelRequest:
    return ModelRequest(
        model=model,
        prompt=prompt,
        variables=variables,  # type: ignore[arg-type]
        budget=budget,
        output_schema=output_schema,
        correlation_ref="correlation:agw-002",
        provenance_ref="provenance:agw-002",
    )


def plan(**overrides: object) -> FallbackPlan:
    values: dict[str, object] = {
        "primary": PRIMARY,
        "fallbacks": (SECONDARY,),
    }
    values.update(overrides)
    return FallbackPlan(**values)  # type: ignore[arg-type]


def runtime(
    script: object, **overrides: object
) -> tuple[ModelRuntime, DeterministicFakeProvider]:
    provider = overrides.pop(
        "provider", DeterministicFakeProvider(script)  # type: ignore[arg-type]
    )
    instance = ModelRuntime(
        registry=registry(),
        provider=provider,  # type: ignore[arg-type]
        configuration=overrides.pop("configuration", CONFIG),  # type: ignore[arg-type]
        plan=overrides.pop("plan", plan()),  # type: ignore[arg-type]
    )
    return instance, provider  # type: ignore[return-value]


def success(
    text: str = "ok",
    *,
    usage: ProviderUsage | None = None,
    revision: str | None = None,
) -> ProviderInvocationResult:
    return ProviderInvocationResult(
        ModelResult(ModelResultStatus.SUCCESS, output_text=text),
        usage=usage,
        model_revision=revision,
    )


def planner_client(rt: ModelRuntime) -> PlannerClient:
    return PlannerClient(rt, PLANNER_REF)


def zero_retry_budget() -> ModelBudget:
    return ModelBudget(4_096, 1_024, retry_budget=0)


def test_provider_protocol_is_satisfied_by_fake_and_rejects_others() -> None:
    assert isinstance(DeterministicFakeProvider([success()]), ModelProvider)

    class NotProvider:
        pass

    assert not isinstance(NotProvider(), ModelProvider)


def test_planner_generator_critic_clients_share_one_runtime_core() -> None:
    rt, provider = runtime(
        [success("plan"), success("patch"), success("review")]
    )
    clients = (
        (PlannerClient(rt, PLANNER_REF), PLANNER_REF),
        (GeneratorClient(rt, GENERATOR_REF), GENERATOR_REF),
        (CriticClient(rt, CRITIC_REF), CRITIC_REF),
    )
    for client, ref in clients:
        result = client.invoke(request(prompt=ref))
        assert result.role == type(client).role
        assert result.outcome.status == ModelResultStatus.SUCCESS
    assert provider.calls == 3


def test_role_clients_reject_foreign_prompt_identities() -> None:
    rt, provider = runtime([success()])
    for client, ref in (
        (PlannerClient(rt, PLANNER_REF), GENERATOR_REF),
        (GeneratorClient(rt, GENERATOR_REF), CRITIC_REF),
        (CriticClient(rt, CRITIC_REF), PLANNER_REF),
    ):
        with pytest.raises(ModelRuntimeError):
            client.invoke(request(prompt=ref))
    assert provider.calls == 0


def test_role_prompt_identities_are_distinct_registry_entries() -> None:
    entries = registry().entries
    assert {entry.ref for entry in entries} == {
        PLANNER_REF,
        GENERATOR_REF,
        CRITIC_REF,
    }


def test_prompt_identity_is_template_id_plus_version() -> None:
    rt, provider = runtime([success()])
    stale = PromptTemplateRef(PLANNER_REF.template_id, "9.9.9")
    with pytest.raises(ModelDomainError) as raised:
        planner_client(rt).invoke(request(prompt=stale))
    assert raised.value.code == ModelDomainErrorCode.PROMPT_NOT_FOUND
    assert provider.calls == 0


def test_registry_snapshot_is_immutable_against_input_mutation() -> None:
    source = [PLANNER_DEFINITION]
    frozen = PromptRegistry.build(source)
    rt = ModelRuntime(
        registry=frozen,
        provider=DeterministicFakeProvider([success()]),
        configuration=CONFIG,
        plan=FallbackPlan(primary=PRIMARY),
    )
    source.clear()
    assert frozen.entries == (PLANNER_DEFINITION,)
    assert frozen.lookup(PLANNER_REF) is PLANNER_DEFINITION
    result = planner_client(rt).invoke(request())
    assert result.prompt_definition is PLANNER_DEFINITION


def test_identical_same_version_registration_converges() -> None:
    converged = PromptRegistry.build([PLANNER_DEFINITION, PLANNER_DEFINITION])
    assert converged.entries == (PLANNER_DEFINITION,)
    reordered = PromptRegistry.build(
        [
            PLANNER_DEFINITION,
            PromptDefinition(
                ref=PLANNER_REF,
                template_text="Plan {task} in {language}",
                variables=["task", "language"],
                metadata={"role": "planner"},
            ),
        ]
    )
    assert reordered.entries == (PLANNER_DEFINITION,)


def test_conflicting_same_version_definition_fails_closed() -> None:
    conflict = PromptDefinition(
        ref=PLANNER_REF,
        template_text="Different {task} {language}",
        variables=("language", "task"),
    )
    with pytest.raises(ModelDomainError) as raised:
        PromptRegistry.build([PLANNER_DEFINITION, conflict])
    assert raised.value.code == ModelDomainErrorCode.PROMPT_VERSION_CONFLICT


def test_attempts_attribute_provider_model_and_configuration_versions() -> None:
    rt, _ = runtime(
        [success(usage=ProviderUsage(11, 22), revision="rev-2026.01.01")]
    )
    result = planner_client(rt).invoke(request())
    attempt = result.attempts[0]
    assert isinstance(attempt, AttemptedTarget)
    assert attempt.target == PRIMARY
    assert attempt.target.provider_ref == "provider.primary"
    assert attempt.target.model_id == "model.primary"
    assert attempt.target.configuration_version == "cfg-1"
    assert attempt.model_revision == "rev-2026.01.01"
    assert attempt.usage == ProviderUsage(11, 22)


def test_prompt_correlation_and_provenance_are_preserved() -> None:
    rt, _ = runtime([success()])
    result = planner_client(rt).invoke(request())
    assert result.request.correlation_ref == "correlation:agw-002"
    assert result.request.provenance_ref == "provenance:agw-002"
    assert result.prompt_definition.ref == PLANNER_REF
    assert result.prompt_definition.content_digest == (
        PLANNER_DEFINITION.content_digest
    )


def test_equivalent_invocations_have_identical_deterministic_representations() -> None:
    left_rt, _ = runtime(
        [success()],
        configuration=InvocationConfiguration(seed=7, temperature=0),
    )
    right_rt, _ = runtime(
        [success()],
        configuration=InvocationConfiguration(temperature=0.0, seed=7),
    )
    left = planner_client(left_rt).invoke(
        request(variables={"language": "Java", "task": "localise strings"})
    )
    right = planner_client(right_rt).invoke(
        request(variables=[["task", "localise strings"], ["language", "Java"]])
    )
    assert left.invocation_digest == right.invocation_digest
    assert left.invocation_digest == (
        planner_client(left_rt).invoke(request()).invocation_digest
    )
    assert left.configuration.canonical_json() == right.configuration.canonical_json()
    assert left.plan.canonical_json() == right.plan.canonical_json()

    changed_seed_rt, _ = runtime(
        [success()], configuration=InvocationConfiguration(seed=8)
    )
    changed_seed = planner_client(changed_seed_rt).invoke(request())
    assert changed_seed.invocation_digest != left.invocation_digest

    other_identity = ModelIdentity("provider.primary", "model.primary", "cfg-2")
    changed_version_rt, _ = runtime(
        [success()],
        plan=FallbackPlan(primary=other_identity, fallbacks=(SECONDARY,)),
    )
    changed_version = planner_client(changed_version_rt).invoke(
        request(model=other_identity)
    )
    assert changed_version.invocation_digest != left.invocation_digest

    changed_variable_rt, _ = runtime([success()])
    changed_variable = planner_client(changed_variable_rt).invoke(
        request(variables={"language": "Rust", "task": "localise strings"})
    )
    assert changed_variable.invocation_digest != left.invocation_digest

    changed_ref_rt, _ = runtime([success()])
    changed_ref = planner_client(changed_ref_rt).invoke(
        dataclass_replace(request(), correlation_ref="correlation:other")
    )
    assert changed_ref.invocation_digest != left.invocation_digest

    reordered_plan_rt, _ = runtime(
        [success()],
        plan=FallbackPlan(primary=PRIMARY, fallbacks=(SECONDARY,)),
    )
    flipped_plan_rt, _ = runtime(
        [success()],
        plan=FallbackPlan(
            primary=PRIMARY,
            fallbacks=(
                ModelIdentity("provider.secondary", "model.secondary.alt", "cfg-1"),
            ),
        ),
    )
    assert planner_client(reordered_plan_rt).invoke(request()).invocation_digest != (
        planner_client(flipped_plan_rt).invoke(request()).invocation_digest
    )


def test_invocation_configuration_is_bounded_and_canonical() -> None:
    assert InvocationConfiguration().canonical_json() == (
        '{"allow_tool_calls":false,"seed":null,"temperature":null}'
    )
    bounded = InvocationConfiguration(
        temperature=2.0, seed=2_147_483_647, allow_tool_calls=True
    )
    assert json.loads(bounded.canonical_json()) == {
        "allow_tool_calls": True,
        "seed": 2_147_483_647,
        "temperature": 2.0,
    }
    assert bounded == InvocationConfiguration(
        temperature=2, seed=2_147_483_647, allow_tool_calls=True
    )
    for invalid in (
        {"temperature": True},
        {"temperature": "0.5"},
        {"temperature": float("nan")},
        {"temperature": float("inf")},
        {"temperature": -0.1},
        {"temperature": 2.5},
        {"seed": True},
        {"seed": -1},
        {"seed": 2_147_483_648},
        {"seed": 1.5},
        {"allow_tool_calls": 1},
    ):
        with pytest.raises(ModelRuntimeError):
            InvocationConfiguration(**invalid)  # type: ignore[arg-type]


def test_tool_call_allowance_defaults_off_and_is_explicit() -> None:
    assert InvocationConfiguration().allow_tool_calls is False
    enabled = InvocationConfiguration(allow_tool_calls=True)
    assert '"allow_tool_calls":true' in enabled.canonical_json()


def test_unstructured_success_passes_output_text_through() -> None:
    rt, _ = runtime([success("plain analysis")])
    result = planner_client(rt).invoke(request())
    assert result.outcome.status == ModelResultStatus.SUCCESS
    assert result.outcome.output_text == "plain analysis"
    assert result.outcome.structured_validation is None
    assert result.fallback_exhausted is False


def test_structured_success_requires_valid_payload() -> None:
    rt, _ = runtime([success('{"score":4,"summary":"done"}')])
    result = planner_client(rt).invoke(request(output_schema=SCHEMA))
    assert result.outcome.status == ModelResultStatus.SUCCESS
    assert result.outcome.structured_validation is not None
    assert (
        result.outcome.structured_validation.status
        == StructuredValidationStatus.VALID
    )
    assert result.attempts[0].outcome.status == ModelResultStatus.SUCCESS


@pytest.mark.parametrize(
    ("output", "validation_status", "field"),
    [
        ('{"score"', StructuredValidationStatus.MALFORMED, None),
        ('{"summary":"x"}', StructuredValidationStatus.MISSING_REQUIRED_FIELD, "score"),
        (
            '{"score":1,"summary":"x","extra":true}',
            StructuredValidationStatus.UNEXPECTED_FIELD,
            "extra",
        ),
        (
            '{"score":"1","summary":"x"}',
            StructuredValidationStatus.SCHEMA_MISMATCH,
            "score",
        ),
        ('{"score":true,"summary":"x"}', StructuredValidationStatus.SCHEMA_MISMATCH, "score"),
    ],
)
def test_malformed_structured_output_never_progresses_as_success(
    output: str, validation_status: StructuredValidationStatus, field: str | None
) -> None:
    rt, provider = runtime([success(output)])
    result = planner_client(rt).invoke(request(output_schema=SCHEMA))
    assert result.outcome.status == ModelResultStatus.INVALID_STRUCTURED_OUTPUT
    assert result.outcome.output_text is None
    assert result.outcome.structured_validation is not None
    assert result.outcome.structured_validation.status == validation_status
    assert result.outcome.structured_validation.field == field
    assert provider.calls == 1
    assert result.fallback_exhausted is False


def test_oversized_structured_output_fails_closed_at_every_boundary() -> None:
    oversized_summary = '{"score":1,"summary":"' + "x" * (
        MAX_STRUCTURED_OUTPUT_BYTES + 1
    ) + '"}'
    rejected = validate_structured_output(oversized_summary, SCHEMA)
    assert rejected.status == StructuredValidationStatus.MALFORMED
    with pytest.raises(ModelDomainError):
        ModelResult(ModelResultStatus.SUCCESS, output_text="x" * (
            MAX_STRUCTURED_OUTPUT_BYTES + 1
        ))

    class _OversizedClaimProvider:
        def invoke(
            self,
            request: object,
            definition: object,
            configuration: object,
        ) -> ProviderInvocationResult:
            raise ModelDomainError(
                _DomainCodeAlias.INVALID_RESULT_SHAPE,
                "SUCCESS output_text exceeds the output bound",
            )

    rt = ModelRuntime(
        registry=registry(),
        provider=_OversizedClaimProvider(),  # type: ignore[arg-type]
        configuration=CONFIG,
        plan=FallbackPlan(primary=PRIMARY),
    )
    result = planner_client(rt).invoke(
        request(output_schema=SCHEMA, budget=zero_retry_budget())
    )
    assert result.outcome.status == ModelResultStatus.PROVIDER_OR_MODEL_FAILURE
    assert result.outcome.failure_class == ModelFailureClass.PROVIDER_INTERNAL_ERROR


def test_refusal_is_terminal_without_retry_or_fallback() -> None:
    refusal = ProviderInvocationResult(
        ModelResult(ModelResultStatus.REFUSAL, refusal_reason="policy violation")
    )
    rt, provider = runtime([refusal])
    result = planner_client(rt).invoke(
        request(budget=ModelBudget(4_096, 1_024, retry_budget=3))
    )
    assert result.outcome.status == ModelResultStatus.REFUSAL
    assert result.outcome.refusal_reason == "policy violation"
    assert len(result.attempts) == 1
    assert provider.calls == 1
    assert result.fallback_exhausted is False


def test_abstention_is_distinct_from_every_other_outcome() -> None:
    others = {
        ModelResultStatus.SUCCESS,
        ModelResultStatus.REFUSAL,
        ModelResultStatus.TIMEOUT,
        ModelResultStatus.PROVIDER_OR_MODEL_FAILURE,
        ModelResultStatus.INVALID_STRUCTURED_OUTPUT,
        ModelResultStatus.BUDGET_EXCEEDED,
        ModelResultStatus.VALIDATION_FAILURE,
    }
    assert ModelResultStatus.ABSTENTION not in others

    abstention = ProviderInvocationResult(
        ModelResult(ModelResultStatus.ABSTENTION, detail="insufficient context")
    )
    rt, _ = runtime([abstention])
    result = planner_client(rt).invoke(request())
    assert result.outcome.status == ModelResultStatus.ABSTENTION
    assert result.outcome.detail == "insufficient context"
    assert result.outcome.output_text is None
    assert result.attempts[-1].target == PRIMARY
    assert result.fallback_exhausted is False

    with pytest.raises(ModelDomainError):
        ModelResult(
            ModelResultStatus.ABSTENTION,
            failure_class=ModelFailureClass.MODEL_ERROR,
        )
    with pytest.raises(ModelDomainError):
        ModelResult(ModelResultStatus.ABSTENTION, output_text="looks like success")
    with pytest.raises(ModelDomainError):
        ModelResult(ModelResultStatus.ABSTENTION, refusal_reason="not a refusal")


def test_timeout_boundary_retries_then_falls_back_in_order() -> None:
    rt, provider = runtime(
        [ProviderTimeoutError(), ProviderTimeoutError(), success("recovered")]
    )
    result = planner_client(rt).invoke(request())
    statuses = [attempt.outcome.status for attempt in result.attempts]
    assert statuses == [
        ModelResultStatus.TIMEOUT,
        ModelResultStatus.TIMEOUT,
        ModelResultStatus.SUCCESS,
    ]
    assert [attempt.target for attempt in result.attempts] == [
        PRIMARY,
        PRIMARY,
        SECONDARY,
    ]
    assert [attempt.attempt_number for attempt in result.attempts] == [1, 2, 1]
    assert result.final_target == SECONDARY
    assert result.fallback_exhausted is False
    assert provider.calls == 3


def test_timeout_results_are_typed_with_stable_details() -> None:
    rt, _ = runtime([ProviderTimeoutError()])
    result = planner_client(rt).invoke(request(budget=zero_retry_budget()))
    assert result.outcome.status == ModelResultStatus.TIMEOUT
    assert result.outcome.detail == "provider exceeded the configured latency bound"


def test_provider_failure_boundary_preserves_failure_class() -> None:
    rt, _ = runtime([ProviderFailureError(ModelFailureClass.RATE_LIMITED)])
    result = planner_client(rt).invoke(request(budget=zero_retry_budget()))
    assert result.outcome.status == ModelResultStatus.PROVIDER_OR_MODEL_FAILURE
    assert result.outcome.failure_class == ModelFailureClass.RATE_LIMITED
    assert result.outcome.detail == "provider reported a typed failure"

    rt_transport, _ = runtime([ProviderFailureError()])
    transport_result = planner_client(rt_transport).invoke(
        request(budget=zero_retry_budget())
    )
    assert transport_result.outcome.failure_class == (
        ModelFailureClass.PROVIDER_INTERNAL_ERROR
    )


class _BrokenProvider:
    def invoke(self, *args: object, **kwargs: object) -> object:
        raise ValueError("arbitrary provider internals")


def test_arbitrary_provider_exceptions_are_translated_fail_closed() -> None:
    rt = ModelRuntime(
        registry=registry(),
        provider=_BrokenProvider(),  # type: ignore[arg-type]
        configuration=CONFIG,
        plan=FallbackPlan(primary=PRIMARY),
    )
    result = planner_client(rt).invoke(request(budget=zero_retry_budget()))
    assert result.outcome.status == ModelResultStatus.PROVIDER_OR_MODEL_FAILURE
    assert result.outcome.failure_class == ModelFailureClass.PROVIDER_INTERNAL_ERROR
    assert result.outcome.detail == "provider invocation failed"
    assert "arbitrary provider internals" not in (result.outcome.detail or "")


class _GarbageShapeProvider:
    def invoke(self, *args: object, **kwargs: object) -> object:
        return {"result": "not a typed result"}


def test_invalid_provider_result_shape_fails_closed() -> None:
    rt = ModelRuntime(
        registry=registry(),
        provider=_GarbageShapeProvider(),  # type: ignore[arg-type]
        configuration=CONFIG,
        plan=FallbackPlan(primary=PRIMARY),
    )
    result = planner_client(rt).invoke(request(budget=zero_retry_budget()))
    assert result.outcome.status == ModelResultStatus.PROVIDER_OR_MODEL_FAILURE
    assert result.outcome.detail == "invalid provider result shape"
    assert result.outcome.failure_class == ModelFailureClass.PROVIDER_INTERNAL_ERROR


class _FabricatedResultProvider:
    def __init__(self, rogue: object) -> None:
        self._rogue = rogue

    def invoke(self, *args: object, **kwargs: object) -> object:
        del args, kwargs
        return self._rogue


def _fabricated_provider_result(**slots: object) -> ProviderInvocationResult:
    rogue = object.__new__(ProviderInvocationResult)
    for name, value in slots.items():
        object.__setattr__(rogue, name, value)
    return rogue


def fabricated_shape_runtime(rogue: object) -> ModelRuntime:
    return ModelRuntime(
        registry=registry(),
        provider=_FabricatedResultProvider(rogue),  # type: ignore[arg-type]
        configuration=CONFIG,
        plan=FallbackPlan(primary=PRIMARY),
    )


def assert_fabricated_shape_fails_closed(result: ModelInvocationResult) -> None:
    assert result.outcome.status == ModelResultStatus.PROVIDER_OR_MODEL_FAILURE
    assert result.outcome.failure_class == ModelFailureClass.PROVIDER_INTERNAL_ERROR
    assert result.outcome.detail == "invalid provider result shape"
    assert result.outcome.output_text is None
    for attempt in result.attempts:
        assert attempt.attempt_number == 1
        assert attempt.usage is None
        assert attempt.model_revision is None
        assert attempt.outcome.status == ModelResultStatus.PROVIDER_OR_MODEL_FAILURE
    assert [attempt.target for attempt in result.attempts] == [PRIMARY]
    assert result.final_target == PRIMARY
    assert result.fallback_exhausted is True


def test_fabricated_provider_result_instance_never_escapes_attribute_error() -> None:
    rogue = object.__new__(ProviderInvocationResult)
    assert isinstance(rogue, ProviderInvocationResult)
    rt = fabricated_shape_runtime(rogue)
    result = planner_client(rt).invoke(request(budget=zero_retry_budget()))
    assert_fabricated_shape_fails_closed(result)


def test_partially_fabricated_provider_result_shapes_fail_closed() -> None:
    valid = ModelResult(ModelResultStatus.SUCCESS, output_text="ok")
    rogues = (
        _fabricated_provider_result(),
        _fabricated_provider_result(result=valid),
        _fabricated_provider_result(usage=None),
        _fabricated_provider_result(model_revision=None),
        _fabricated_provider_result(result="not a typed result"),
        _fabricated_provider_result(result=valid, usage="invalid"),
        _fabricated_provider_result(result=valid, model_revision=17),
        _fabricated_provider_result(result=valid, model_revision="bad revision!"),
    )
    for rogue in rogues:
        rt = fabricated_shape_runtime(rogue)
        result = planner_client(rt).invoke(request(budget=zero_retry_budget()))
        assert_fabricated_shape_fails_closed(result)


def test_precall_declared_budget_impossibility_never_reaches_the_provider() -> None:
    rt, provider = runtime([success()])
    result = planner_client(rt).invoke(
        request(),
        declared_input_tokens=BUDGET.max_input_tokens + 1,
    )
    assert result.outcome.status == ModelResultStatus.BUDGET_EXCEEDED
    assert result.attempts == ()
    assert result.final_target == PRIMARY
    assert provider.calls == 0

    exact = planner_client(rt).invoke(
        request(), declared_input_tokens=BUDGET.max_input_tokens
    )
    assert exact.outcome.status == ModelResultStatus.SUCCESS

    with pytest.raises(ModelRuntimeError):
        planner_client(rt).invoke(request(), declared_input_tokens=-1)
    with pytest.raises(ModelRuntimeError):
        planner_client(rt).invoke(request(), declared_input_tokens=True)  # type: ignore[arg-type]


def test_post_call_usage_contradiction_fails_closed_as_budget_exceeded() -> None:
    over_output = success(usage=ProviderUsage(10, BUDGET.max_output_tokens + 1))
    rt, provider = runtime([over_output])
    result = planner_client(rt).invoke(request())
    assert result.outcome.status == ModelResultStatus.BUDGET_EXCEEDED
    assert result.outcome.output_text is None
    assert result.attempts[0].usage == ProviderUsage(10, BUDGET.max_output_tokens + 1)
    assert provider.calls == 1

    over_input = success(usage=ProviderUsage(BUDGET.max_input_tokens + 1, 1))
    rt_input, _ = runtime(
        [over_input], plan=FallbackPlan(primary=PRIMARY)
    )
    input_result = planner_client(rt_input).invoke(request())
    assert input_result.outcome.status == ModelResultStatus.BUDGET_EXCEEDED

    with pytest.raises(ModelRuntimeError):
        ProviderUsage(-1, 0)
    with pytest.raises(ModelRuntimeError):
        ProviderUsage(0, -5)
    with pytest.raises(ModelRuntimeError):
        ProviderUsage(True, 1)
    with pytest.raises(ModelRuntimeError):
        ProviderUsage(1, True)


def test_malformed_nested_provider_usage_fails_closed_at_construction() -> None:
    def outcome() -> ModelResult:
        return ModelResult(ModelResultStatus.ABSTENTION)

    for malformed_usage in ("invalid", 17, {"input_tokens": 1}, True):
        with pytest.raises(ModelRuntimeError):
            ProviderInvocationResult(
                outcome(),
                usage=malformed_usage,  # type: ignore[arg-type]
            )
        with pytest.raises(ModelRuntimeError):
            AttemptedTarget(
                target=PRIMARY,
                attempt_number=1,
                outcome=outcome(),
                usage=malformed_usage,  # type: ignore[arg-type]
            )

    with pytest.raises(ModelRuntimeError):
        ProviderInvocationResult(outcome(), model_revision=True)
    with pytest.raises(ModelRuntimeError):
        AttemptedTarget(
            target=PRIMARY,
            attempt_number=1,
            outcome=outcome(),
            model_revision="bad revision!",
        )


class _MalformedNestedUsageProvider:
    def invoke(self, *args: object, **kwargs: object) -> object:
        return ProviderInvocationResult(
            ModelResult(ModelResultStatus.SUCCESS, output_text="ok"),
            usage="invalid",  # type: ignore[arg-type]
        )


def test_malformed_nested_usage_never_escapes_runtime_as_attribute_error() -> None:
    rt = ModelRuntime(
        registry=registry(),
        provider=_MalformedNestedUsageProvider(),  # type: ignore[arg-type]
        configuration=CONFIG,
        plan=FallbackPlan(primary=PRIMARY),
    )
    result = planner_client(rt).invoke(request(budget=zero_retry_budget()))
    assert result.outcome.status == ModelResultStatus.PROVIDER_OR_MODEL_FAILURE
    assert result.outcome.failure_class == ModelFailureClass.PROVIDER_INTERNAL_ERROR
    assert result.attempts[0].outcome.status == (
        ModelResultStatus.PROVIDER_OR_MODEL_FAILURE
    )
    assert result.attempts[0].usage is None


def test_valid_provider_usage_still_flows_through_the_runtime() -> None:
    usage = ProviderUsage(11, 22)
    rt, _ = runtime([success("done", usage=usage, revision="rev-2026.02.01")])
    result = planner_client(rt).invoke(request())
    assert result.outcome.status == ModelResultStatus.SUCCESS
    assert result.attempts[0].usage is not None
    assert result.attempts[0].usage.input_tokens == 11
    assert result.attempts[0].usage.output_tokens == 22
    assert result.attempts[0].model_revision == "rev-2026.02.01"
    assert result.attempts[0].canonical_dict()["usage"] == {
        "input_tokens": 11,
        "output_tokens": 22,
    }


def test_retry_budget_bounds_total_attempts_exactly_and_exhaustion_stays_failed() -> None:
    rt, provider = runtime([ProviderTimeoutError()])
    result = planner_client(rt).invoke(request(budget=zero_retry_budget()))
    assert provider.calls == 2
    assert [attempt.target for attempt in result.attempts] == [PRIMARY, SECONDARY]
    assert result.fallback_exhausted is True
    assert result.outcome.status == ModelResultStatus.TIMEOUT
    assert result.final_target == SECONDARY

    rt_three, provider_three = runtime([ProviderTimeoutError()])
    exhausted_three = planner_client(rt_three).invoke(
        request(budget=ModelBudget(4_096, 1_024, retry_budget=1))
    )
    assert provider_three.calls == 4
    assert [attempt.target for attempt in exhausted_three.attempts] == [
        PRIMARY,
        PRIMARY,
        SECONDARY,
        SECONDARY,
    ]
    assert exhausted_three.fallback_exhausted is True


def test_fallback_plan_is_explicit_ordered_bounded_and_duplicate_free() -> None:
    ordered = FallbackPlan(
        primary=PRIMARY,
        fallbacks=(SECONDARY, ModelIdentity("provider.third", "model.third", "cfg-1")),
    )
    assert ordered.targets == ordered.targets
    assert ordered.targets[0] == PRIMARY
    assert ordered.retryable == frozenset(
        {RetryableCondition.TIMEOUT, RetryableCondition.PROVIDER_FAILURE}
    )
    with pytest.raises(ModelRuntimeError):
        plan(
            fallbacks=tuple(
                ModelIdentity(f"provider.{index}", f"model.{index}", "cfg-1")
                for index in range(9)
            )
        )
    with pytest.raises(ModelRuntimeError):
        plan(fallbacks=(SECONDARY, SECONDARY))
    with pytest.raises(ModelRuntimeError):
        FallbackPlan(primary=PRIMARY, fallbacks=(SECONDARY,), retryable={"NOPE"})  # type: ignore[arg-type]


def test_policy_gates_structured_output_fallback() -> None:
    default_rt, default_provider = runtime(
        [success('{"score":'), success('{"score":1,"summary":"ok"}')]
    )
    default_result = planner_client(default_rt).invoke(request(output_schema=SCHEMA))
    assert default_result.outcome.status == ModelResultStatus.INVALID_STRUCTURED_OUTPUT
    assert default_provider.calls == 1
    assert default_result.fallback_exhausted is False

    structured_rt, structured_provider = runtime(
        [success('{"score":'), success('{"score":1,"summary":"ok"}')],
        plan=plan(
            fallbacks=(SECONDARY,),
            retryable=frozenset(
                {
                    RetryableCondition.TIMEOUT,
                    RetryableCondition.PROVIDER_FAILURE,
                    RetryableCondition.INVALID_STRUCTURED_OUTPUT,
                }
            ),
        ),
    )
    retried = planner_client(structured_rt).invoke(request(output_schema=SCHEMA))
    assert retried.outcome.status == ModelResultStatus.SUCCESS
    assert structured_provider.calls == 2
    assert retried.attempts[0].outcome.status == (
        ModelResultStatus.INVALID_STRUCTURED_OUTPUT
    )
    assert retried.attempts[1].target == PRIMARY


def test_no_silent_substitution_and_full_target_attribution() -> None:
    rt, _ = runtime([ProviderTimeoutError(), success("secondary answered")])
    mismatched = ModelIdentity("provider.other", "model.other", "cfg-9")

    with pytest.raises(ModelRuntimeError):
        planner_client(rt).invoke(request(model=SECONDARY))
    with pytest.raises(ModelRuntimeError):
        PlannerClient(rt, PLANNER_REF).invoke(request(model=mismatched))

    rt_fallback, provider_fallback = runtime(
        [ProviderTimeoutError(), success("secondary answered")]
    )
    result = planner_client(rt_fallback).invoke(request(budget=zero_retry_budget()))
    assert {attempt.target for attempt in result.attempts} == {PRIMARY, SECONDARY}
    assert result.final_target != result.plan.primary
    assert result.final_target == SECONDARY
    assert result.outcome.output_text == "secondary answered"
    assert provider_fallback.calls == 2


def test_deterministic_fake_provider_is_repeatable_and_bounded() -> None:
    def fresh() -> DeterministicFakeProvider:
        return DeterministicFakeProvider(
            [success("first"), ProviderTimeoutError(), success("final")]
        )

    provider = fresh()
    assert provider.invoke(None, None, None) == success("first")  # type: ignore[arg-type]
    with pytest.raises(ProviderTimeoutError):
        provider.invoke(None, None, None)  # type: ignore[arg-type]
    assert provider.invoke(None, None, None) == success("final")  # type: ignore[arg-type]
    assert provider.invoke(None, None, None) == success("final")  # type: ignore[arg-type]
    assert provider.calls == 4

    twin = fresh()
    assert twin.invoke(None, None, None) == success("first")  # type: ignore[arg-type]
    with pytest.raises(ProviderTimeoutError):
        twin.invoke(None, None, None)  # type: ignore[arg-type]

    with pytest.raises(ValueError):
        DeterministicFakeProvider([])
    with pytest.raises(TypeError):
        DeterministicFakeProvider(["not a scripted response"])  # type: ignore[list-item]


def test_runtime_result_shape_is_complete() -> None:
    rt, _ = runtime([success("done")])
    result = planner_client(rt).invoke(request())
    assert isinstance(result, ModelInvocationResult)
    assert result.role == "PLANNER"
    assert result.configuration == CONFIG
    assert result.plan.targets == (PRIMARY, SECONDARY)
    assert result.request == request()
    assert result.invocation_digest
    assert bytes.fromhex(result.invocation_digest)


_FORBIDDEN_CONCEPTS = (
    "chain_of_thought",
    "reasoning_trace",
    "hidden_reasoning",
    "internal_reasoning",
    "scratchpad",
)

_RUNTIME_VALUE_TYPES = (
    InvocationConfiguration,
    ProviderUsage,
    ProviderInvocationResult,
    FallbackPlan,
    AttemptedTarget,
    ModelInvocationResult,
)

_ALLOWED_IMPORTS = {
    "__future__",
    "hashlib",
    "json",
    "math",
    "re",
    "collections.abc",
    "dataclasses",
    "enum",
    "typing",
}

_FORBIDDEN_IMPORT_PREFIXES = (
    "app.retrieval",
    "app.execution",
    "app.evidence",
    "app.queue",
    "app.db",
    "app.api",
    "openai",
    "anthropic",
    "httpx",
    "requests",
    "urllib",
    "socket",
    "subprocess",
    "os",
    "random",
    "time",
    "boto3",
    "google",
    "vertexai",
)


def _module_imports() -> tuple[set[str], list[str]]:
    source = Path(model_provider.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(model_provider.__file__))
    absolute: set[str] = set()
    relative: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            absolute.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                relative.append(node.module or "")
            elif node.module:
                absolute.add(node.module)
    return absolute, relative


def test_no_hidden_chain_of_thought_fields_exist() -> None:
    for domain_type in _RUNTIME_VALUE_TYPES:
        names = {field.name for field in fields(domain_type)}
        offenders = {
            name for name in names for concept in _FORBIDDEN_CONCEPTS if concept in name
        }
        assert not offenders, (domain_type, offenders)

    source = Path(model_provider.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(model_provider.__file__))
    identifiers = {
        node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
    } | {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert not identifiers & set(_FORBIDDEN_CONCEPTS)


def test_module_imports_stay_provider_neutral_without_network_or_layers() -> None:
    absolute, relative = _module_imports()
    assert absolute <= _ALLOWED_IMPORTS
    assert relative == ["model_domain"]
    for forbidden in _FORBIDDEN_IMPORT_PREFIXES:
        assert not any(
            name == forbidden or name.startswith(f"{forbidden}.")
            for name in absolute
        )

    for domain_type in _RUNTIME_VALUE_TYPES:
        names = {field.name for field in fields(domain_type)}
        assert not names & {"api_key", "apikey", "credential", "client_secret"}


def test_public_exports_expose_the_runtime_api() -> None:
    import app.workflow

    expected = {
        "AttemptedTarget",
        "CriticClient",
        "DeterministicFakeProvider",
        "FallbackPlan",
        "GeneratorClient",
        "InvocationConfiguration",
        "ModelInvocationResult",
        "ModelProvider",
        "ModelRuntime",
        "ModelRuntimeError",
        "PlannerClient",
        "ProviderFailureError",
        "ProviderInvocationResult",
        "ProviderTimeoutError",
        "ProviderUsage",
        "RetryableCondition",
    }
    assert expected <= set(app.workflow.__all__)
    for name in expected:
        assert getattr(app.workflow, name) is getattr(model_provider, name)


def test_existing_domain_semantics_remain_intact_through_the_runtime() -> None:
    valid = validate_structured_output('{"score":1,"summary":"x"}', SCHEMA)
    assert valid.status == StructuredValidationStatus.VALID

    rt, _ = runtime([success()])
    result = PlannerClient(rt, PLANNER_REF).invoke(
        request(output_schema=None, budget=ModelBudget(64, 32, retry_budget=0))
    )
    assert result.prompt_definition == PLANNER_DEFINITION
