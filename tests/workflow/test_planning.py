"""AGW-003 planner-to-localisation orchestration semantics."""

import ast
import dataclasses
import hashlib
import importlib
import json
from pathlib import Path

import pytest

import app.workflow.engine as workflow_engine
import app.workflow.model_provider as model_provider_module
import app.workflow.persistence as workflow_persistence
from app.retrieval import (
    CandidateIdentity,
    ContextBundle,
    ContextBundleIdentity,
    ContextItem,
    ContextItemIdentity,
    FileIdentity,
    Provenance,
    RepositoryIdentity,
    RevisionIdentity,
    TokenBudget,
    TrustLabel,
)
from app.workflow.localisation_adapter import (
    LocalisationBoundaryFailureCode,
    LocalisationRequest,
    LowLocalisationConfidence,
)
from app.workflow.planning import (
    PLANNER_OUTPUT_SCHEMA,
    PLANNER_OUTPUT_SCHEMA_VERSION,
    AbstentionIntent,
    GenerationReadyIntent,
    LocalisationFailureIntent,
    OrchestrationDispositionKind,
    PlanningErrorCode,
    PlanningError,
    PlanningOrchestrationDecision,
    PlanningRequest,
    PlannerFailureIntent,
    PlannerFailureReason,
    ValidatedPlan,
    orchestrate_planning_and_localisation,
    parse_planner_plan,
)
from app.workflow.types import AbstentionCode, RunState, WorkflowStepKind

from app.workflow import (
    DeterministicFakeProvider,
    FallbackPlan,
    InvocationConfiguration,
    LifecycleSnapshot,
    ModelBudget,
    ModelFailureClass,
    ModelIdentity,
    ModelRequest,
    ModelResult,
    ModelResultStatus,
    ModelInvocationResult,
    ModelRuntime,
    PlannerClient,
    ProviderFailureError,
    ProviderInvocationResult,
    ProviderTimeoutError,
    ProviderUsage,
    PromptDefinition,
    PromptRegistry,
    PromptTemplateRef,
    RequestKind,
    StructuredField,
    StructuredFieldType,
    StructuredOutputSchema,
)


REPOSITORY_ID = RepositoryIdentity("01fe25bec239-collab/TestGap-Miner")
REVISION_ID = RevisionIdentity("1c5b8e9be0068c40df1f0144d6c42e53eda7d3e4")
OTHER_REPOSITORY_ID = RepositoryIdentity("01fe25bec239-collab/Other-Miner")
OTHER_REVISION_ID = RevisionIdentity("b" * 40)
QUERY = "Locate the bounded retry handling for workflow transitions"
CORRELATION_REF = "correlation:agw-003-run-1"
PROVENANCE_REF = "provenance:agw-002-planner"

PLANNER_REF = PromptTemplateRef("planner.task", "1.0.0")
PRIMARY = ModelIdentity(
    provider_ref="provider.primary",
    model_id="model.primary",
    configuration_version="cfg-1",
    capability_profile="profile.planner",
)
BUDGET = ModelBudget(4_096, 1_024, retry_budget=0, max_latency_ms=30_000)
CONFIGURATION = InvocationConfiguration(temperature=0, seed=7)
PLANNER_SCHEMA = StructuredOutputSchema(
    (
        StructuredField("summary", StructuredFieldType.STRING),
        StructuredField("score", StructuredFieldType.INTEGER),
    )
)

PLANNER_DEFINITION = PromptDefinition(
    ref=PLANNER_REF,
    template_text="Plan localisation for {task} in {language}",
    variables=("language", "task"),
    metadata={"role": "planner"},
)

CONTENT = "def locate():\n    return 'context'\n"


def plan_payload(**overrides: object) -> str:
    values: dict[str, object] = {
        "schema_version": PLANNER_OUTPUT_SCHEMA_VERSION,
        "repository_id": REPOSITORY_ID.value,
        "revision_id": REVISION_ID.value,
        "query": QUERY,
    }
    values.update(overrides)
    return json.dumps(values, sort_keys=True)


def success_script(payload_text: str | None = None) -> list[object]:
    return [
        ProviderInvocationResult(
            result=ModelResult(
                ModelResultStatus.SUCCESS,
                output_text=payload_text or plan_payload(),
            ),
            usage=ProviderUsage(input_tokens=64, output_tokens=32),
            model_revision="model.primary@rev-1",
        )
    ]


def planner_client(script: list[object]) -> tuple[PlannerClient, DeterministicFakeProvider]:
    provider = DeterministicFakeProvider(script)
    runtime = ModelRuntime(
        registry=PromptRegistry.build([PLANNER_DEFINITION]),
        provider=provider,
        configuration=CONFIGURATION,
        plan=FallbackPlan(primary=PRIMARY),
    )
    return PlannerClient(runtime, PLANNER_REF), provider


def model_request(output_schema: StructuredOutputSchema | None = PLANNER_OUTPUT_SCHEMA) -> ModelRequest:
    return ModelRequest(
        model=PRIMARY,
        prompt=PLANNER_REF,
        variables={"task": "localise failing behaviour", "language": "Python"},
        budget=BUDGET,
        output_schema=output_schema,
        correlation_ref=CORRELATION_REF,
        provenance_ref=PROVENANCE_REF,
    )


def planning_request() -> PlanningRequest:
    return PlanningRequest(REPOSITORY_ID, REVISION_ID, model_request())


class RecordingBoundary:
    """Deterministic fake localisation boundary recording its requests."""

    def __init__(self, results: list[object]) -> None:
        self._results = results
        self.calls: list[LocalisationRequest] = []

    def localise(self, request: LocalisationRequest) -> object:
        self.calls.append(request)
        result = self._results[min(len(self.calls) - 1, len(self._results) - 1)]
        if isinstance(result, Exception):
            raise result
        if isinstance(result, type) and issubclass(result, Exception):
            raise result()
        return result


def context_bundle(
    *,
    repository_id: RepositoryIdentity = REPOSITORY_ID,
    revision_id: RevisionIdentity = REVISION_ID,
    items: tuple[ContextItem, ...] | None = None,
) -> ContextBundle:
    if items is None:
        item = ContextItem(
            context_item_id=ContextItemIdentity("context-001"),
            candidate_id=CandidateIdentity("candidate-001"),
            provenance=Provenance(
                repository_id=repository_id,
                revision_id=revision_id,
                file_identity=FileIdentity("apps/api/app/workflow/planning.py"),
                start_line=1,
                end_line=2,
                content_sha256=hashlib.sha256(CONTENT.encode()).hexdigest(),
            ),
            trust_label=TrustLabel.UNTRUSTED_REPOSITORY_TEXT,
            content=CONTENT,
            token_count=5,
        )
        items = (item,)
    return ContextBundle(
        context_bundle_id=ContextBundleIdentity("bundle-001"),
        repository_id=repository_id,
        revision_id=revision_id,
        items=items,
        token_budget=TokenBudget(
            max_tokens=10, consumed_tokens=sum(i.token_count for i in items)
        ),
    )


def ready_boundary() -> RecordingBoundary:
    return RecordingBoundary([context_bundle()])


def run_orchestration(client: PlannerClient, boundary: RecordingBoundary | None = None):
    boundary = boundary if boundary is not None else ready_boundary()
    decision = orchestrate_planning_and_localisation(
        planner_client=client,
        planning_request=planning_request(),
        localisation_boundary=boundary,
    )
    return decision, boundary


def test_valid_planner_result_yields_generation_ready_intent() -> None:
    client, provider = planner_client(success_script())
    decision, boundary = run_orchestration(client)

    assert decision.kind == OrchestrationDispositionKind.GENERATION_READY
    assert isinstance(decision.generation_ready, GenerationReadyIntent)
    assert provider.calls == 1
    assert len(boundary.calls) == 1
    intent = decision.generation_ready
    assert intent.plan.repository_id == REPOSITORY_ID
    assert intent.plan.revision_id == REVISION_ID
    assert intent.plan.query == QUERY
    assert intent.context_bundle.repository_id == REPOSITORY_ID
    assert intent.context_bundle.revision_id == REVISION_ID


def test_generation_ready_intent_preserves_context_bundle_exactly() -> None:
    bundle = context_bundle()
    client, _ = planner_client(success_script())
    decision, _ = run_orchestration(client, RecordingBoundary([bundle]))

    intent = decision.generation_ready
    assert intent is not None
    assert intent.context_bundle is bundle
    assert intent.context_bundle == bundle
    assert intent.context_bundle.canonical_json() == bundle.canonical_json()


def test_exact_planner_provenance_is_retained() -> None:
    direct_client, _ = planner_client(success_script())
    reference = direct_client.invoke(model_request())

    client, _ = planner_client(success_script())
    decision, _ = run_orchestration(client)
    intent = decision.generation_ready
    assert intent is not None

    invocation = intent.planner_invocation
    assert invocation.request.model == PRIMARY
    assert invocation.request.prompt == PLANNER_REF
    assert invocation.request.correlation_ref == CORRELATION_REF
    assert invocation.request.provenance_ref == PROVENANCE_REF
    assert invocation.configuration == CONFIGURATION
    assert invocation.final_target == PRIMARY
    assert invocation.invocation_digest == reference.invocation_digest
    assert invocation.role == "PLANNER"


def test_equivalent_inputs_produce_equivalent_decisions() -> None:
    first_client, _ = planner_client(success_script())
    second_client, _ = planner_client(success_script())
    first, first_boundary = run_orchestration(first_client)
    second, second_boundary = run_orchestration(second_client)

    assert first == second
    assert first.generation_ready is not None and second.generation_ready is not None
    assert (
        first.generation_ready.plan.semantic_digest
        == second.generation_ready.plan.semantic_digest
    )
    assert first.generation_ready.canonical_json() == (
        second.generation_ready.canonical_json()
    )
    assert first_boundary.calls[0].canonical_dict() == (
        second_boundary.calls[0].canonical_dict()
    )


def test_plan_semantic_digest_is_order_independent() -> None:
    request = planning_request()
    reordered = json.dumps(
        {
            "query": QUERY,
            "revision_id": REVISION_ID.value,
            "repository_id": REPOSITORY_ID.value,
            "schema_version": PLANNER_OUTPUT_SCHEMA_VERSION,
        }
    )
    first = parse_planner_plan(plan_payload(), request)
    second = parse_planner_plan(reordered, request)

    assert first == second
    assert first.semantic_digest == second.semantic_digest
    assert len(first.semantic_digest) == 64


def test_localisation_receives_the_validated_intent_only_once() -> None:
    client, _ = planner_client(success_script())
    boundary = ready_boundary()
    run_orchestration(client, boundary)

    assert len(boundary.calls) == 1
    request = boundary.calls[0]
    assert isinstance(request, LocalisationRequest)
    assert request.repository_id == REPOSITORY_ID
    assert request.revision_id == REVISION_ID
    assert request.query == QUERY


@pytest.mark.parametrize(
    ("status", "extra"),
    [
        (ModelResultStatus.REFUSAL, {"refusal_reason": "declined"}),
        (ModelResultStatus.TIMEOUT, {}),
        (ModelResultStatus.BUDGET_EXCEEDED, {}),
        (
            ModelResultStatus.PROVIDER_OR_MODEL_FAILURE,
            {"failure_class": ModelFailureClass.RATE_LIMITED},
        ),
        (ModelResultStatus.ABSTENTION, {}),
    ],
)
def test_non_success_model_results_never_reach_localisation(status, extra) -> None:
    script = [ProviderInvocationResult(result=ModelResult(status, **extra))]
    client, provider = planner_client(script)
    boundary = ready_boundary()

    decision, _ = run_orchestration(client, boundary)

    assert provider.calls == 1
    assert boundary.calls == []
    assert decision.kind == OrchestrationDispositionKind.PLANNER_FAILURE
    failure = decision.planner_failure
    assert failure is not None
    assert failure.reason == PlannerFailureReason.MODEL_RESULT_NOT_SUCCESSFUL
    assert failure.status == status
    expected_class = extra.get("failure_class")
    assert failure.failure_class == expected_class
    assert failure.detail_code is None
    assert decision.abstention is None


def test_provider_timeout_exception_is_typed_not_raised() -> None:
    script = [ProviderTimeoutError()]
    client, _ = planner_client(script)
    decision, boundary = run_orchestration(client)

    assert decision.kind == OrchestrationDispositionKind.PLANNER_FAILURE
    failure = decision.planner_failure
    assert failure is not None
    assert failure.status == ModelResultStatus.TIMEOUT
    assert boundary.calls == []


def test_provider_failure_exception_is_typed_not_raised() -> None:
    script = [ProviderFailureError(ModelFailureClass.MODEL_UNAVAILABLE)]
    client, _ = planner_client(script)
    decision, _ = run_orchestration(client)

    failure = decision.planner_failure
    assert failure is not None
    assert failure.status == ModelResultStatus.PROVIDER_OR_MODEL_FAILURE
    assert failure.failure_class == ModelFailureClass.MODEL_UNAVAILABLE


def test_budget_rejection_is_preserved_not_converted() -> None:
    script = [
        ProviderInvocationResult(
            result=ModelResult(
                ModelResultStatus.SUCCESS, output_text=plan_payload()
            ),
            usage=ProviderUsage(
                input_tokens=BUDGET.max_input_tokens + 1,
                output_tokens=8,
            ),
        )
    ]
    client, _ = planner_client(script)
    decision, boundary = run_orchestration(client)

    failure = decision.planner_failure
    assert failure is not None
    assert decision.kind == OrchestrationDispositionKind.PLANNER_FAILURE
    assert failure.status == ModelResultStatus.BUDGET_EXCEEDED
    assert failure.reason == PlannerFailureReason.MODEL_RESULT_NOT_SUCCESSFUL
    assert boundary.calls == []


@pytest.mark.parametrize(
    "payload",
    [
        "not json at all",
        "{}",
        json.dumps({"schema_version": PLANNER_OUTPUT_SCHEMA_VERSION}),
        json.dumps({**json.loads(plan_payload()), "query": 42}),
        json.dumps({**json.loads(plan_payload()), "repository_id": None}),
    ],
)
def test_malformed_structured_output_fails_closed_before_localisation(payload) -> None:
    client, _ = planner_client(
        [
            ProviderInvocationResult(
                result=ModelResult(ModelResultStatus.SUCCESS, output_text=payload)
            )
        ]
    )
    decision, boundary = run_orchestration(client)

    assert boundary.calls == []
    failure = decision.planner_failure
    assert failure is not None
    assert decision.kind == OrchestrationDispositionKind.PLANNER_FAILURE


def test_runtime_schema_enforcement_flags_hidden_reasoning_field() -> None:
    adversarial = json.dumps(
        {**json.loads(plan_payload()), "chain_of_thought": "do not store"}
    )
    client, _ = planner_client(success_script(adversarial))
    decision, _ = run_orchestration(client)

    failure = decision.planner_failure
    assert failure is not None
    assert failure.status == ModelResultStatus.INVALID_STRUCTURED_OUTPUT
    assert failure.reason == PlannerFailureReason.MODEL_RESULT_NOT_SUCCESSFUL


def test_success_without_schema_still_parses_fail_closed() -> None:
    adversarial = json.dumps(
        {**json.loads(plan_payload()), "hidden_scratchpad": "reasoning"}
    )
    client, _ = planner_client(success_script(adversarial))
    request = PlanningRequest(REPOSITORY_ID, REVISION_ID, model_request(None))
    decision = orchestrate_planning_and_localisation(
        planner_client=client,
        planning_request=request,
        localisation_boundary=ready_boundary(),
    )

    failure = decision.planner_failure
    assert failure is not None
    assert failure.reason == PlannerFailureReason.PLAN_PARSE_REJECTED
    assert failure.status == ModelResultStatus.INVALID_STRUCTURED_OUTPUT
    assert failure.detail_code == PlanningErrorCode.MALFORMED_PLANNER_OUTPUT.value


def test_unsupported_schema_version_in_success_output_is_rejected() -> None:
    stale = plan_payload(schema_version="testgap.planner-plan.v0")
    client, _ = planner_client(success_script(stale))
    request = PlanningRequest(REPOSITORY_ID, REVISION_ID, model_request(None))
    decision = orchestrate_planning_and_localisation(
        planner_client=client,
        planning_request=request,
        localisation_boundary=ready_boundary(),
    )

    failure = decision.planner_failure
    assert failure is not None
    assert failure.status == ModelResultStatus.INVALID_STRUCTURED_OUTPUT
    assert failure.detail_code == (
        PlanningErrorCode.UNSUPPORTED_PLAN_SCHEMA_VERSION.value
    )


def test_plan_claiming_foreign_repository_is_rejected() -> None:
    foreign = plan_payload(repository_id=OTHER_REPOSITORY_ID.value)
    client, _ = planner_client(success_script(foreign))
    request = PlanningRequest(REPOSITORY_ID, REVISION_ID, model_request(None))
    decision = orchestrate_planning_and_localisation(
        planner_client=client,
        planning_request=request,
        localisation_boundary=ready_boundary(),
    )

    failure = decision.planner_failure
    assert failure is not None
    assert failure.status == ModelResultStatus.INVALID_STRUCTURED_OUTPUT
    assert failure.detail_code == PlanningErrorCode.PLAN_IDENTITY_MISMATCH.value


def test_parse_planner_plan_is_total_over_adversarial_values() -> None:
    request = planning_request()
    for value in (None, 42, b"{}", object()):
        with pytest.raises(PlanningError) as raised:
            parse_planner_plan(value, request)
        assert raised.value.code == PlanningErrorCode.MALFORMED_PLANNER_OUTPUT


def test_unsupported_schema_version_is_reported_distinctly() -> None:
    stale = plan_payload(schema_version="testgap.planner-plan.v0")
    with pytest.raises(PlanningError) as raised:
        parse_planner_plan(stale, planning_request())
    assert raised.value.code == PlanningErrorCode.UNSUPPORTED_PLAN_SCHEMA_VERSION


def test_invalid_query_in_plan_fails_closed() -> None:
    request = planning_request()
    for query in ("", "   padded   ", 42, None, "x" * 20_000):
        payload = plan_payload(query=query)
        with pytest.raises(PlanningError) as raised:
            parse_planner_plan(payload, request)
        assert raised.value.code == PlanningErrorCode.MALFORMED_PLANNER_OUTPUT


def test_low_confidence_marker_abstains_without_context() -> None:
    client, _ = planner_client(success_script())
    decision, boundary = run_orchestration(
        client, RecordingBoundary([LowLocalisationConfidence()])
    )

    assert decision.kind == OrchestrationDispositionKind.ABSTENTION
    assert decision.abstention == AbstentionIntent(
        AbstentionCode.INSUFFICIENT_LOCALISATION_CONFIDENCE,
        WorkflowStepKind.LOCALISE,
    )
    assert len(boundary.calls) == 1


def test_empty_context_abstains_with_insufficient_context() -> None:
    client, _ = planner_client(success_script())
    decision, _ = run_orchestration(
        client, RecordingBoundary([context_bundle(items=())])
    )

    assert decision.kind == OrchestrationDispositionKind.ABSTENTION
    assert decision.abstention == AbstentionIntent(
        AbstentionCode.INSUFFICIENT_CONTEXT,
        WorkflowStepKind.LOCALISE,
    )


@pytest.mark.parametrize(
    "result",
    [None, 42, "bundle", {}, object(), context_bundle(repository_id=OTHER_REPOSITORY_ID)],
)
def test_repository_mismatch_and_garbage_fail_closed(result) -> None:
    client, _ = planner_client(success_script())
    decision, _ = run_orchestration(client, RecordingBoundary([result]))

    assert decision.kind == OrchestrationDispositionKind.LOCALISATION_FAILURE
    assert decision.generation_ready is None
    assert decision.abstention is None


def test_revision_mismatch_fails_closed() -> None:
    drifted = context_bundle(revision_id=OTHER_REVISION_ID)
    client, _ = planner_client(success_script())
    decision, _ = run_orchestration(client, RecordingBoundary([drifted]))

    failure = decision.localisation_failure
    assert failure is not None
    assert failure.failure_code == LocalisationBoundaryFailureCode.REVISION_MISMATCH


def test_repository_mismatch_takes_deterministic_precedence() -> None:
    drifted = context_bundle(
        repository_id=OTHER_REPOSITORY_ID, revision_id=OTHER_REVISION_ID
    )
    client, _ = planner_client(success_script())
    decision, _ = run_orchestration(client, RecordingBoundary([drifted]))

    failure = decision.localisation_failure
    assert failure is not None
    assert failure.failure_code == LocalisationBoundaryFailureCode.REPOSITORY_MISMATCH


def test_raising_boundary_becomes_typed_failure() -> None:
    client, _ = planner_client(success_script())
    decision, _ = run_orchestration(
        client, RecordingBoundary([RuntimeError("provider internals")])
    )

    failure = decision.localisation_failure
    assert failure is not None
    assert failure.failure_code == LocalisationBoundaryFailureCode.BOUNDARY_ERROR


def test_adversarial_result_shape_fails_closed() -> None:
    class ExplodingBundle:
        """Object that mimics a bundle until any attribute comparison."""

        context_bundle_id = None

        def __getattr__(self, name: str) -> object:
            raise RuntimeError("adversarial attribute access")

    client, _ = planner_client(success_script())
    decision, _ = run_orchestration(
        client, RecordingBoundary([ExplodingBundle()])
    )

    assert decision.kind == OrchestrationDispositionKind.LOCALISATION_FAILURE
    failure = decision.localisation_failure
    assert failure is not None
    assert failure.failure_code == LocalisationBoundaryFailureCode.MALFORMED_RESULT


def test_no_generator_execution_or_persistence_side_effects(monkeypatch) -> None:
    def _forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("orchestration must stay read-only")

    monkeypatch.setattr(workflow_persistence, "persist_transition", _forbidden)
    monkeypatch.setattr(workflow_engine, "evaluate_transition", _forbidden)
    monkeypatch.setattr(
        workflow_engine, "schedule_retry", _forbidden, raising=False
    )
    monkeypatch.setattr(
        model_provider_module.GeneratorClient, "invoke", _forbidden
    )

    snapshot = LifecycleSnapshot(
        state=RunState.PLANNING,
        repair_attempts_used=0,
        retry_attempts_used=0,
        retry_limit=3,
        request_kind=RequestKind.GITHUB,
        review_required=True,
    )
    client, _ = planner_client(success_script())
    decision = orchestrate_planning_and_localisation(
        planner_client=client,
        planning_request=planning_request(),
        localisation_boundary=ready_boundary(),
    )
    after = LifecycleSnapshot(
        state=snapshot.state,
        repair_attempts_used=snapshot.repair_attempts_used,
        retry_attempts_used=snapshot.retry_attempts_used,
        retry_limit=snapshot.retry_limit,
        request_kind=snapshot.request_kind,
        review_required=snapshot.review_required,
    )
    assert snapshot == after
    assert decision.kind == OrchestrationDispositionKind.GENERATION_READY


def test_decision_carries_exactly_one_payload() -> None:
    with pytest.raises(TypeError):
        PlanningOrchestrationDecision(OrchestrationDispositionKind.GENERATION_READY)
    with pytest.raises(ValueError):
        PlanningOrchestrationDecision(
            OrchestrationDispositionKind.ABSTENTION,
            abstention=AbstentionIntent(
                AbstentionCode.INSUFFICIENT_CONTEXT, WorkflowStepKind.LOCALISE
            ),
            planner_failure=PlannerFailureIntent(PlannerFailureReason.INVOCATION_ERROR),
        )
    with pytest.raises(TypeError):
        PlanningOrchestrationDecision(
            OrchestrationDispositionKind.LOCALISATION_FAILURE,
            abstention=AbstentionIntent(
                AbstentionCode.INSUFFICIENT_CONTEXT, WorkflowStepKind.LOCALISE
            ),
        )


def test_coordinator_rejects_caller_misuse_with_typed_error() -> None:
    client, _ = planner_client(success_script())
    with pytest.raises(PlanningError) as raised:
        orchestrate_planning_and_localisation(
            planner_client=client,
            planning_request=None,
            localisation_boundary=ready_boundary(),
        )
    assert raised.value.code == PlanningErrorCode.INVALID_PLANNING_REQUEST
    assert isinstance(raised.value, ValueError)


def test_planning_request_requires_exact_domain_types() -> None:
    with pytest.raises(TypeError):
        PlanningRequest("repo", REVISION_ID, model_request())  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        PlanningRequest(REPOSITORY_ID, "rev", model_request())  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        PlanningRequest(REPOSITORY_ID, REVISION_ID, "request")  # type: ignore[arg-type]


def test_prompt_registry_missing_template_fails_inside_planner_boundary() -> None:
    stale_ref = PromptTemplateRef("planner.task", "9.9.9")
    provider = DeterministicFakeProvider(success_script())
    runtime = ModelRuntime(
        registry=PromptRegistry.build([PLANNER_DEFINITION]),
        provider=provider,
        configuration=CONFIGURATION,
        plan=FallbackPlan(primary=PRIMARY),
    )
    stale_client = PlannerClient(runtime, stale_ref)
    request = ModelRequest(
        model=PRIMARY,
        prompt=stale_ref,
        variables={"task": "task", "language": "Python"},
        budget=BUDGET,
        output_schema=PLANNER_OUTPUT_SCHEMA,
    )
    stale_request = PlanningRequest(REPOSITORY_ID, REVISION_ID, request)
    decision = orchestrate_planning_and_localisation(
        planner_client=stale_client,
        planning_request=stale_request,
        localisation_boundary=ready_boundary(),
    )

    assert decision.kind == OrchestrationDispositionKind.PLANNER_FAILURE
    failure = decision.planner_failure
    assert failure is not None
    assert failure.reason == PlannerFailureReason.INVOCATION_ERROR
    assert provider.calls == 0


def test_unknown_model_identity_fails_inside_planner_boundary() -> None:
    foreign_model = ModelIdentity(
        provider_ref="provider.other",
        model_id="model.other",
        configuration_version="cfg-9",
    )
    provider = DeterministicFakeProvider(success_script())
    runtime = ModelRuntime(
        registry=PromptRegistry.build([PLANNER_DEFINITION]),
        provider=provider,
        configuration=CONFIGURATION,
        plan=FallbackPlan(primary=foreign_model),
    )
    mismatched = PlannerClient(runtime, PLANNER_REF)
    request = PlanningRequest(
        REPOSITORY_ID, REVISION_ID, model_request()
    )
    decision = orchestrate_planning_and_localisation(
        planner_client=mismatched,
        planning_request=request,
        localisation_boundary=ready_boundary(),
    )

    assert decision.kind == OrchestrationDispositionKind.PLANNER_FAILURE
    assert decision.planner_failure is not None
    assert decision.planner_failure.reason == PlannerFailureReason.INVOCATION_ERROR
    assert provider.calls == 0


def test_schema_has_no_hidden_fields_and_plan_is_minimal() -> None:
    assert PLANNER_OUTPUT_SCHEMA.allow_additional_fields is False
    assert [field.name for field in PLANNER_OUTPUT_SCHEMA.fields] == [
        "query",
        "repository_id",
        "revision_id",
        "schema_version",
    ]
    assert [field.name for field in dataclasses.fields(ValidatedPlan)] == [
        "schema_version",
        "repository_id",
        "revision_id",
        "query",
    ]
    assert [field.name for field in dataclasses.fields(GenerationReadyIntent)] == [
        "plan",
        "context_bundle",
        "planner_invocation",
    ]


def test_new_workflow_modules_are_pure_and_network_free() -> None:
    forbidden = {
        "app.api",
        "app.db",
        "app.evidence",
        "app.execution",
        "app.queue",
        "datetime",
        "httpx",
        "os",
        "pathlib",
        "psycopg",
        "random",
        "requests",
        "secrets",
        "socket",
        "sqlalchemy",
        "subprocess",
        "time",
        "urllib",
        "uuid",
    }
    sources = [
        Path(importlib.import_module("app.workflow.planning").__file__ or ""),
        Path(
            importlib.import_module("app.workflow.localisation_adapter").__file__
            or ""
        ),
    ]
    for source in sources:
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        modules = set()
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules.add(node.module)
            elif isinstance(node, ast.Name):
                names.add(node.id)
            elif isinstance(node, ast.Attribute):
                names.add(node.attr)
        assert not (modules & forbidden), source
        assert not (names & {"GeneratorClient", "persist_transition", "evaluate_transition", "uuid4", "random", "now", "urandom"}), source


def test_only_durable_rag_public_contract_names_are_consumed() -> None:
    retrieval = importlib.import_module("app.retrieval")
    consumed: set[str] = set()
    for module_name in ("app.workflow.planning", "app.workflow.localisation_adapter"):
        module = importlib.import_module(module_name)
        tree = ast.parse(Path(module.__file__ or "").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.level == 0
                and node.module == "app.retrieval"
            ):
                consumed.update(alias.name for alias in node.names)
    assert consumed <= set(retrieval.__all__)


# ---------------------------------------------------------------------------
# AGW003-A2-F002: fabricated model invocations must fail closed.
# ---------------------------------------------------------------------------


class FabricatingClient:
    """Planner double returning a canned raw invocation value."""

    role = PlannerClient.role

    def __init__(self, value: object) -> None:
        self._value = value
        self.calls = 0

    def invoke(self, request: object) -> object:
        self.calls += 1
        return self._value


def materialised_fields() -> dict[str, object]:
    """Fully valid planner invocation fields produced by the AGW-002 runtime."""

    client, _ = planner_client(success_script())
    invocation = client.invoke(model_request())
    return {
        "role": invocation.role,
        "request": invocation.request,
        "configuration": invocation.configuration,
        "plan": invocation.plan,
        "prompt_definition": invocation.prompt_definition,
        "invocation_digest": invocation.invocation_digest,
        "attempts": invocation.attempts,
        "outcome": invocation.outcome,
        "fallback_exhausted": invocation.fallback_exhausted,
    }


def fabricated_invocation(**overrides: object) -> ModelInvocationResult:
    instance = object.__new__(ModelInvocationResult)
    for name, value in {**materialised_fields(), **overrides}.items():
        object.__setattr__(instance, name, value)
    return instance


def run_fabricated(value: object) -> PlanningOrchestrationDecision:
    boundary = ready_boundary()
    decision = orchestrate_planning_and_localisation(
        planner_client=FabricatingClient(value),
        planning_request=planning_request(),
        localisation_boundary=boundary,
    )
    assert boundary.calls == []
    assert decision.kind == OrchestrationDispositionKind.PLANNER_FAILURE
    failure = decision.planner_failure
    assert failure is not None
    assert failure.reason == PlannerFailureReason.INVOCATION_SHAPE_INVALID
    return decision


@pytest.mark.parametrize(
    "removed",
    [
        "role",
        "request",
        "configuration",
        "plan",
        "prompt_definition",
        "invocation_digest",
        "attempts",
        "outcome",
        "fallback_exhausted",
    ],
)
def test_partially_fabricated_invocation_fails_closed(removed: str) -> None:
    fields = materialised_fields()
    del fields[removed]
    instance = object.__new__(ModelInvocationResult)
    for name, value in fields.items():
        object.__setattr__(instance, name, value)

    decision = run_fabricated(instance)
    assert decision.planner_failure is not None
    assert decision.planner_failure.fallback_exhausted is False


def test_bare_fabricated_invocation_fails_closed() -> None:
    decision = run_fabricated(object.__new__(ModelInvocationResult))
    assert decision.planner_failure is not None
    assert decision.planner_failure.status is None


@pytest.mark.parametrize(
    "malformed",
    [
        {"outcome": 42},
        {"outcome": "SUCCESS"},
        {"outcome": object.__new__(ModelResult)},
        {"role": "GENERATOR"},
        {"role": None},
        {"invocation_digest": ""},
        {"invocation_digest": "   "},
        {"invocation_digest": None},
        {"fallback_exhausted": "false"},
        {"fallback_exhausted": None},
        {"request": object.__new__(ModelRequest)},
        {"request": 42},
        {"configuration": object.__new__(InvocationConfiguration)},
        {"plan": object.__new__(FallbackPlan)},
        {"prompt_definition": 42},
        {"attempts": ("garbage",)},
        {"attempts": 7},
    ],
)
def test_malformed_invocation_field_fails_closed(malformed: dict[str, object]) -> None:
    run_fabricated(fabricated_invocation(**malformed))


def test_adversarial_invocation_attribute_access_fails_closed() -> None:
    class ExplodingValue:
        def __getattr__(self, name: str) -> object:
            raise RuntimeError("adversarial attribute access")

    class ExplodingSequence:
        def __iter__(self):
            raise KeyError("adversarial iteration")

    run_fabricated(
        fabricated_invocation(outcome=ExplodingValue(), fallback_exhausted=True)
    )
    run_fabricated(fabricated_invocation(attempts=ExplodingSequence()))
    run_fabricated(
        fabricated_invocation(request={"prompt": {"canonical_dict": None}})
    )


def test_substitute_invocation_type_is_rejected_not_traversed() -> None:
    class Impostor(ModelInvocationResult):
        pass

    impostor = object.__new__(Impostor)
    object.__setattr__(
        impostor,
        "outcome",
        property(lambda self: (_ for _ in ()).throw(RuntimeError("boom"))),
    )
    run_fabricated(impostor)


# ---------------------------------------------------------------------------
# AGW003-A2-F003: GenerationReadyIntent domain invariants.
# ---------------------------------------------------------------------------


def ready_intent_components():
    client, _ = planner_client(success_script())
    invocation = client.invoke(model_request())
    plan = parse_planner_plan(invocation.outcome.output_text, planning_request())
    return plan, context_bundle(), invocation


def rebuilt_invocation(**overrides: object) -> ModelInvocationResult:
    return fabricated_invocation(**overrides)


def test_valid_matching_generation_ready_construction_is_accepted() -> None:
    plan, bundle, invocation = ready_intent_components()
    intent = GenerationReadyIntent(
        plan=plan, context_bundle=bundle, planner_invocation=invocation
    )

    assert intent.plan is plan
    assert intent.context_bundle is bundle
    assert intent.planner_invocation is invocation


def test_direct_construction_with_foreign_repository_bundle_fails_closed() -> None:
    plan, _, invocation = ready_intent_components()
    with pytest.raises(ValueError):
        GenerationReadyIntent(
            plan=plan,
            context_bundle=context_bundle(repository_id=OTHER_REPOSITORY_ID),
            planner_invocation=invocation,
        )


def test_direct_construction_with_drifted_revision_bundle_fails_closed() -> None:
    plan, _, invocation = ready_intent_components()
    with pytest.raises(ValueError):
        GenerationReadyIntent(
            plan=plan,
            context_bundle=context_bundle(revision_id=OTHER_REVISION_ID),
            planner_invocation=invocation,
        )


def test_direct_construction_with_empty_context_fails_closed() -> None:
    plan, _, invocation = ready_intent_components()
    with pytest.raises(ValueError):
        GenerationReadyIntent(
            plan=plan,
            context_bundle=context_bundle(items=()),
            planner_invocation=invocation,
        )


def test_direct_construction_with_non_success_invocation_fails_closed() -> None:
    plan, bundle, _ = ready_intent_components()
    refusal = rebuilt_invocation(
        outcome=ModelResult(ModelResultStatus.REFUSAL, refusal_reason="declined"),
    )
    with pytest.raises(ValueError):
        GenerationReadyIntent(
            plan=plan, context_bundle=bundle, planner_invocation=refusal
        )


def test_direct_construction_with_wrong_invocation_role_fails_closed() -> None:
    plan, bundle, _ = ready_intent_components()
    foreign_role = rebuilt_invocation(role="GENERATOR")
    with pytest.raises(TypeError):
        GenerationReadyIntent(
            plan=plan, context_bundle=bundle, planner_invocation=foreign_role
        )


def test_direct_construction_with_fabricated_invocation_fails_closed() -> None:
    plan, bundle, _ = ready_intent_components()
    with pytest.raises(TypeError):
        GenerationReadyIntent(
            plan=plan,
            context_bundle=bundle,
            planner_invocation=object.__new__(ModelInvocationResult),
        )


# ---------------------------------------------------------------------------
# AGW003-A2-F001 (C2 ruling): model-level planner abstention is a typed
# planner non-success and never a Workflow abstention.
# ---------------------------------------------------------------------------


def abstention_script() -> list[object]:
    return [
        ProviderInvocationResult(result=ModelResult(ModelResultStatus.ABSTENTION))
    ]


def test_planner_model_abstention_is_a_typed_planner_failure() -> None:
    client, provider = planner_client(abstention_script())
    boundary = ready_boundary()

    decision = orchestrate_planning_and_localisation(
        planner_client=client,
        planning_request=planning_request(),
        localisation_boundary=boundary,
    )

    assert provider.calls == 1
    assert boundary.calls == []
    assert decision.kind == OrchestrationDispositionKind.PLANNER_FAILURE
    failure = decision.planner_failure
    assert failure is not None
    assert failure.reason == PlannerFailureReason.MODEL_RESULT_NOT_SUCCESSFUL
    assert failure.status == ModelResultStatus.ABSTENTION
    assert failure.failure_class is None
    assert failure.detail_code is None
    assert failure.fallback_exhausted is False


@pytest.mark.parametrize("fallback_exhausted", [False, True])
def test_planner_model_abstention_preserves_fallback_exhausted_exactly(
    fallback_exhausted: bool,
) -> None:
    invocation = fabricated_invocation(
        outcome=ModelResult(ModelResultStatus.ABSTENTION),
        fallback_exhausted=fallback_exhausted,
    )
    boundary = ready_boundary()

    decision = orchestrate_planning_and_localisation(
        planner_client=FabricatingClient(invocation),
        planning_request=planning_request(),
        localisation_boundary=boundary,
    )

    assert boundary.calls == []
    assert decision.kind == OrchestrationDispositionKind.PLANNER_FAILURE
    failure = decision.planner_failure
    assert failure is not None
    assert failure.status == ModelResultStatus.ABSTENTION
    assert failure.failure_class is None
    assert failure.fallback_exhausted is fallback_exhausted


def test_no_abstention_intent_or_code_for_model_abstention() -> None:
    client, _ = planner_client(abstention_script())

    decision = orchestrate_planning_and_localisation(
        planner_client=client,
        planning_request=planning_request(),
        localisation_boundary=ready_boundary(),
    )

    assert decision.abstention is None
    assert decision.generation_ready is None
    assert decision.localisation_failure is None
    payload = decision.planner_failure
    assert isinstance(payload, PlannerFailureIntent)
    assert all(
        field.name != "abstention_code"
        for field in dataclasses.fields(PlannerFailureIntent)
    )
    assert payload.status == ModelResultStatus.ABSTENTION


def test_model_abstention_distinct_from_low_localisation_confidence() -> None:
    model_abstention, _ = run_orchestration(
        planner_client(abstention_script())[0]
    )

    low_confidence_client, _ = planner_client(success_script())
    low_confidence, low_boundary = run_orchestration(
        low_confidence_client, RecordingBoundary([LowLocalisationConfidence()])
    )

    assert model_abstention.kind == OrchestrationDispositionKind.PLANNER_FAILURE
    assert model_abstention.planner_failure is not None
    assert model_abstention.planner_failure.status == ModelResultStatus.ABSTENTION
    assert model_abstention.abstention is None
    assert len(low_boundary.calls) == 1
    assert low_confidence.kind == OrchestrationDispositionKind.ABSTENTION
    assert low_confidence.planner_failure is None
    assert low_confidence.abstention == AbstentionIntent(
        AbstentionCode.INSUFFICIENT_LOCALISATION_CONFIDENCE,
        WorkflowStepKind.LOCALISE,
    )
    assert model_abstention != low_confidence


def test_model_abstention_distinct_from_insufficient_context() -> None:
    model_abstention, _ = run_orchestration(
        planner_client(abstention_script())[0]
    )

    empty_context_client, _ = planner_client(success_script())
    empty_context, _ = run_orchestration(
        empty_context_client, RecordingBoundary([context_bundle(items=())])
    )

    assert model_abstention.kind == OrchestrationDispositionKind.PLANNER_FAILURE
    assert model_abstention.abstention is None
    assert empty_context.kind == OrchestrationDispositionKind.ABSTENTION
    assert empty_context.planner_failure is None
    assert empty_context.abstention == AbstentionIntent(
        AbstentionCode.INSUFFICIENT_CONTEXT,
        WorkflowStepKind.LOCALISE,
    )
    assert model_abstention != empty_context
