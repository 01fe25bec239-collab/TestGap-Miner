"""Deterministic planning domain and planner-to-localisation orchestration.

This module owns the smallest bounded Workflow orchestration connecting
the AGW-002 :class:`PlannerClient` to a validated planning result, the
Workflow-owned localisation boundary, and exactly one typed disposition:
a generation-ready intent or a safe abstention intent, with model/runtime
failure distinctions preserved.

The module performs no patch generation, no persistence, no lifecycle
transitions, no network behavior, and no filesystem access. The existing
lifecycle engine remains authoritative; this module only returns typed
orchestration intentions for it to act on.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from app.retrieval import (
    ContextBundle,
    LocalisationContractError,
    RepositoryIdentity,
    RevisionIdentity,
)

from .localisation_adapter import (
    LocalisationBoundary,
    LocalisationBoundaryFailureCode,
    LocalisationRequest,
    LocalisationResolutionKind,
    invoke_localisation,
    validated_query_text,
)
from .model_domain import (
    ModelFailureClass,
    ModelIdentity,
    ModelRequest,
    ModelResult,
    ModelResultStatus,
    PromptDefinition,
    PromptTemplateRef,
    StructuredField,
    StructuredFieldType,
    StructuredOutputSchema,
    StructuredValidationStatus,
    validate_structured_output,
)
from .model_provider import (
    AttemptedTarget,
    FallbackPlan,
    InvocationConfiguration,
    ModelInvocationResult,
    PlannerClient,
)
from .types import AbstentionCode, WorkflowStepKind


PLANNER_OUTPUT_SCHEMA_VERSION: Final = "testgap.planner-plan.v1"

PLANNER_OUTPUT_SCHEMA: Final[StructuredOutputSchema] = StructuredOutputSchema(
    (
        StructuredField("query", StructuredFieldType.STRING),
        StructuredField("repository_id", StructuredFieldType.STRING),
        StructuredField("revision_id", StructuredFieldType.STRING),
        StructuredField("schema_version", StructuredFieldType.STRING),
    )
)


class PlanningErrorCode(StrEnum):
    INVALID_PLANNING_REQUEST = "INVALID_PLANNING_REQUEST"
    MALFORMED_PLANNER_OUTPUT = "MALFORMED_PLANNER_OUTPUT"
    UNSUPPORTED_PLAN_SCHEMA_VERSION = "UNSUPPORTED_PLAN_SCHEMA_VERSION"
    PLAN_IDENTITY_MISMATCH = "PLAN_IDENTITY_MISMATCH"


class PlanningError(ValueError):
    """One deterministic fail-closed rejection with a stable code."""

    def __init__(self, code: PlanningErrorCode, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code.value}: {detail}")


class OrchestrationDispositionKind(StrEnum):
    GENERATION_READY = "GENERATION_READY"
    ABSTENTION = "ABSTENTION"
    PLANNER_FAILURE = "PLANNER_FAILURE"
    LOCALISATION_FAILURE = "LOCALISATION_FAILURE"


class PlannerFailureReason(StrEnum):
    MODEL_RESULT_NOT_SUCCESSFUL = "MODEL_RESULT_NOT_SUCCESSFUL"
    PLAN_PARSE_REJECTED = "PLAN_PARSE_REJECTED"
    INVOCATION_SHAPE_INVALID = "INVOCATION_SHAPE_INVALID"
    INVOCATION_ERROR = "INVOCATION_ERROR"


@dataclass(frozen=True, slots=True)
class PlanningRequest:
    """Pinned orchestration inputs preserved from the caller and AGW-002.

    The model request carries the exact AGW-002 provenance (model
    identity, prompt reference, variables, budget, correlation and
    provenance references). No identity is generated here.
    """

    repository_id: RepositoryIdentity
    revision_id: RevisionIdentity
    model_request: ModelRequest

    def __post_init__(self) -> None:
        if type(self.repository_id) is not RepositoryIdentity:
            raise TypeError("repository_id must be a RepositoryIdentity")
        if type(self.revision_id) is not RevisionIdentity:
            raise TypeError("revision_id must be a RevisionIdentity")
        if not isinstance(self.model_request, ModelRequest):
            raise TypeError("model_request must be a ModelRequest")

    def canonical_dict(self) -> dict[str, object]:
        return {
            "model_request": self.model_request.canonical_dict(),
            "repository_id": self.repository_id.value,
            "revision_id": self.revision_id.value,
        }


@dataclass(frozen=True, slots=True)
class ValidatedPlan:
    """Immutable semantic planning result with deterministic provenance."""

    schema_version: str
    repository_id: RepositoryIdentity
    revision_id: RevisionIdentity
    query: str

    def __post_init__(self) -> None:
        if type(self.schema_version) is not str or not self.schema_version.strip():
            raise ValueError("schema_version must be a nonempty string")
        if type(self.repository_id) is not RepositoryIdentity:
            raise TypeError("repository_id must be a RepositoryIdentity")
        if type(self.revision_id) is not RevisionIdentity:
            raise TypeError("revision_id must be a RevisionIdentity")
        object.__setattr__(self, "query", validated_query_text(self.query))

    def canonical_dict(self) -> dict[str, str]:
        return {
            "query": self.query,
            "repository_id": self.repository_id.value,
            "revision_id": self.revision_id.value,
            "schema_version": self.schema_version,
        }

    def canonical_json(self) -> str:
        return _canonical_json(self.canonical_dict())

    @property
    def semantic_digest(self) -> str:
        """Deterministic content digest over the plan semantics only."""

        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def parse_planner_plan(
    output_text: object, request: PlanningRequest
) -> ValidatedPlan:
    """Parse one SUCCESS structured planner output into a validated plan.

    Parsing fails closed on malformed JSON text, unsupported schema
    versions, identities that are invalid or do not exactly match the
    pinned request, and malformed queries.
    """

    if not isinstance(request, PlanningRequest):
        raise PlanningError(
            PlanningErrorCode.INVALID_PLANNING_REQUEST,
            "request must be a PlanningRequest",
        )
    if not isinstance(output_text, str):
        raise PlanningError(
            PlanningErrorCode.MALFORMED_PLANNER_OUTPUT,
            "planner output must be JSON text",
        )
    validation = validate_structured_output(output_text, PLANNER_OUTPUT_SCHEMA)
    if validation.status != StructuredValidationStatus.VALID:
        raise PlanningError(
            PlanningErrorCode.MALFORMED_PLANNER_OUTPUT,
            f"planner output rejected: {validation.status.value}",
        )
    try:
        parsed = json.loads(output_text)
    except ValueError as error:  # pragma: no cover - schema already validated
        raise PlanningError(
            PlanningErrorCode.MALFORMED_PLANNER_OUTPUT,
            "planner output is not parsable JSON",
        ) from error
    schema_version = parsed.get("schema_version")
    if schema_version != PLANNER_OUTPUT_SCHEMA_VERSION:
        raise PlanningError(
            PlanningErrorCode.UNSUPPORTED_PLAN_SCHEMA_VERSION,
            f"unsupported planner schema version {schema_version!r}",
        )
    try:
        repository_id = RepositoryIdentity(parsed.get("repository_id"))
        revision_id = RevisionIdentity(parsed.get("revision_id"))
    except LocalisationContractError as error:
        raise PlanningError(
            PlanningErrorCode.MALFORMED_PLANNER_OUTPUT,
            "planner plan identity is invalid",
        ) from error
    if (
        repository_id != request.repository_id
        or revision_id != request.revision_id
    ):
        raise PlanningError(
            PlanningErrorCode.PLAN_IDENTITY_MISMATCH,
            "planner plan does not match the pinned repository/revision",
        )
    try:
        query = validated_query_text(parsed.get("query"))
    except ValueError as error:
        raise PlanningError(
            PlanningErrorCode.MALFORMED_PLANNER_OUTPUT,
            str(error),
        ) from error
    return ValidatedPlan(
        schema_version=schema_version,
        repository_id=repository_id,
        revision_id=revision_id,
        query=query,
    )


@dataclass(frozen=True, slots=True)
class GenerationReadyIntent:
    """Generation-ready orchestration intent with immutable attribution.

    Carries which planner/model invocation produced the plan, which
    repository/revision was localised, and the exact ContextBundle being
    passed forward.

    Construction fails closed unless the bundle is exactly bound to the
    planned repository/revision and carries nonempty context, and the
    invocation is semantically a successful planner invocation.
    """

    plan: ValidatedPlan
    context_bundle: ContextBundle
    planner_invocation: ModelInvocationResult

    def __post_init__(self) -> None:
        if not isinstance(self.plan, ValidatedPlan):
            raise TypeError("plan must be a ValidatedPlan")
        if type(self.context_bundle) is not ContextBundle:
            raise TypeError("context_bundle must be an exact ContextBundle")
        if not _invocation_shape_is_valid(self.planner_invocation):
            raise TypeError(
                "planner_invocation must be a fully materialised "
                "planner-role ModelInvocationResult"
            )
        outcome = self.planner_invocation.outcome
        if outcome.status != ModelResultStatus.SUCCESS:
            raise ValueError(
                "planner_invocation must carry a SUCCESS model result"
            )
        if self.context_bundle.repository_id != self.plan.repository_id:
            raise ValueError(
                "context_bundle repository identity does not match the plan"
            )
        if self.context_bundle.revision_id != self.plan.revision_id:
            raise ValueError(
                "context_bundle revision identity does not match the plan"
            )
        if not self.context_bundle.items:
            raise ValueError("context_bundle requires nonempty context items")

    def canonical_dict(self) -> dict[str, object]:
        invocation = self.planner_invocation
        return {
            "context_bundle_id": self.context_bundle.context_bundle_id.value,
            "plan": self.plan.canonical_dict(),
            "provenance": {
                "configuration": invocation.configuration.canonical_dict(),
                "invocation_digest": invocation.invocation_digest,
                "model": invocation.final_target.canonical_dict(),
                "prompt": invocation.request.prompt.canonical_dict(),
                "role": invocation.role,
            },
        }

    def canonical_json(self) -> str:
        return _canonical_json(self.canonical_dict())


@dataclass(frozen=True, slots=True)
class AbstentionIntent:
    """Safe abstention intention; lifecycle transition stays upstream."""

    abstention_code: AbstentionCode
    origin: WorkflowStepKind

    def __post_init__(self) -> None:
        if not isinstance(self.abstention_code, AbstentionCode):
            raise TypeError("abstention_code must be an AbstentionCode")
        if self.origin not in (
            WorkflowStepKind.PLAN,
            WorkflowStepKind.LOCALISE,
        ):
            raise ValueError("origin must be PLAN or LOCALISE")


@dataclass(frozen=True, slots=True)
class PlannerFailureIntent:
    """Typed planner failure; provider/runtime distinctions are preserved.

    ``detail_code`` carries only stable workflow-side taxonomy values and
    never provider internals, refusal prose, or hidden reasoning.
    """

    reason: PlannerFailureReason
    status: ModelResultStatus | None = None
    failure_class: ModelFailureClass | None = None
    fallback_exhausted: bool = False
    detail_code: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.reason, PlannerFailureReason):
            raise TypeError("reason must be a PlannerFailureReason")
        if self.status is not None and not isinstance(
            self.status, ModelResultStatus
        ):
            raise TypeError("status must be a ModelResultStatus or None")
        if self.failure_class is not None and not isinstance(
            self.failure_class, ModelFailureClass
        ):
            raise TypeError(
                "failure_class must be a ModelFailureClass or None"
            )
        if type(self.fallback_exhausted) is not bool:
            raise TypeError("fallback_exhausted must be a bool")


@dataclass(frozen=True, slots=True)
class LocalisationFailureIntent:
    """Typed localisation boundary contract violation."""

    failure_code: LocalisationBoundaryFailureCode

    def __post_init__(self) -> None:
        if not isinstance(self.failure_code, LocalisationBoundaryFailureCode):
            raise TypeError(
                "failure_code must be a LocalisationBoundaryFailureCode"
            )


@dataclass(frozen=True, slots=True)
class PlanningOrchestrationDecision:
    """Exactly one typed orchestration disposition for one attempt."""

    kind: OrchestrationDispositionKind
    generation_ready: GenerationReadyIntent | None = None
    abstention: AbstentionIntent | None = None
    planner_failure: PlannerFailureIntent | None = None
    localisation_failure: LocalisationFailureIntent | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, OrchestrationDispositionKind):
            raise TypeError("kind must be an OrchestrationDispositionKind")
        payloads = {
            OrchestrationDispositionKind.GENERATION_READY: (
                self.generation_ready,
                GenerationReadyIntent,
                ("abstention", "planner_failure", "localisation_failure"),
            ),
            OrchestrationDispositionKind.ABSTENTION: (
                self.abstention,
                AbstentionIntent,
                ("generation_ready", "planner_failure", "localisation_failure"),
            ),
            OrchestrationDispositionKind.PLANNER_FAILURE: (
                self.planner_failure,
                PlannerFailureIntent,
                ("generation_ready", "abstention", "localisation_failure"),
            ),
            OrchestrationDispositionKind.LOCALISATION_FAILURE: (
                self.localisation_failure,
                LocalisationFailureIntent,
                ("generation_ready", "abstention", "planner_failure"),
            ),
        }
        payload, expected_type, forbidden = payloads[self.kind]
        if not isinstance(payload, expected_type):
            raise TypeError(
                f"{self.kind.value} requires a {expected_type.__name__} payload"
            )
        for name in forbidden:
            if getattr(self, name) is not None:
                raise ValueError(
                    f"{self.kind.value} cannot carry {name}"
                )


def orchestrate_planning_and_localisation(
    *,
    planner_client: object,
    planning_request: PlanningRequest,
    localisation_boundary: LocalisationBoundary,
) -> PlanningOrchestrationDecision:
    """Run one bounded plan-then-localise attempt and return its decision.

    The coordinator never raises on downstream failures: planner errors,
    malformed results, and adversarial boundary values become typed
    decisions. Only caller misuse of the pinned request raises a typed
    :class:`PlanningError`.
    """

    if not isinstance(planning_request, PlanningRequest):
        raise PlanningError(
            PlanningErrorCode.INVALID_PLANNING_REQUEST,
            "planning_request must be a PlanningRequest",
        )
    entrypoint = getattr(planner_client, "invoke", None)
    if not callable(entrypoint):
        return _decision(
            PlannerFailureIntent(PlannerFailureReason.INVOCATION_ERROR)
        )
    try:
        invocation = entrypoint(planning_request.model_request)
    except Exception:
        return _decision(
            PlannerFailureIntent(PlannerFailureReason.INVOCATION_ERROR)
        )
    if not _invocation_shape_is_valid(invocation):
        return _decision(
            PlannerFailureIntent(PlannerFailureReason.INVOCATION_SHAPE_INVALID)
        )
    assert isinstance(invocation, ModelInvocationResult)
    outcome = invocation.outcome
    status = outcome.status
    if status != ModelResultStatus.SUCCESS:
        failure_class = (
            outcome.failure_class
            if isinstance(outcome.failure_class, ModelFailureClass)
            else None
        )
        return _decision(
            PlannerFailureIntent(
                PlannerFailureReason.MODEL_RESULT_NOT_SUCCESSFUL,
                status=status,
                failure_class=failure_class,
                fallback_exhausted=invocation.fallback_exhausted,
            )
        )
    try:
        plan = parse_planner_plan(outcome.output_text, planning_request)
    except PlanningError as error:
        return _decision(
            PlannerFailureIntent(
                PlannerFailureReason.PLAN_PARSE_REJECTED,
                status=ModelResultStatus.INVALID_STRUCTURED_OUTPUT,
                fallback_exhausted=invocation.fallback_exhausted,
                detail_code=error.code.value,
            )
        )
    resolution = invoke_localisation(
        localisation_boundary,
        LocalisationRequest(
            repository_id=plan.repository_id,
            revision_id=plan.revision_id,
            query=plan.query,
        ),
    )
    if resolution.kind == LocalisationResolutionKind.LOW_LOCALISATION_CONFIDENCE:
        return _decision(
            AbstentionIntent(
                AbstentionCode.INSUFFICIENT_LOCALISATION_CONFIDENCE,
                WorkflowStepKind.LOCALISE,
            )
        )
    if resolution.kind == LocalisationResolutionKind.BOUNDARY_FAILURE:
        return _decision(
            LocalisationFailureIntent(resolution.failure_code)
        )
    bundle = resolution.context_bundle
    assert bundle is not None
    if not bundle.items:
        return _decision(
            AbstentionIntent(
                AbstentionCode.INSUFFICIENT_CONTEXT,
                WorkflowStepKind.LOCALISE,
            )
        )
    return _decision(
        GenerationReadyIntent(
            plan=plan,
            context_bundle=bundle,
            planner_invocation=invocation,
        )
    )


def _decision(payload: object) -> PlanningOrchestrationDecision:
    if isinstance(payload, GenerationReadyIntent):
        return PlanningOrchestrationDecision(
            OrchestrationDispositionKind.GENERATION_READY,
            generation_ready=payload,
        )
    if isinstance(payload, AbstentionIntent):
        return PlanningOrchestrationDecision(
            OrchestrationDispositionKind.ABSTENTION,
            abstention=payload,
        )
    if isinstance(payload, PlannerFailureIntent):
        return PlanningOrchestrationDecision(
            OrchestrationDispositionKind.PLANNER_FAILURE,
            planner_failure=payload,
        )
    assert isinstance(payload, LocalisationFailureIntent)
    return PlanningOrchestrationDecision(
        OrchestrationDispositionKind.LOCALISATION_FAILURE,
        localisation_failure=payload,
    )


def _invocation_shape_is_valid(invocation: object) -> bool:
    """Total fail-closed validation of one planner invocation value.

    Fabricated or partially initialised values (for example via
    ``object.__new__``), missing fields, malformed nested fields, and
    adversarial attribute access all fail closed instead of leaking raw
    exceptions through the public orchestration boundary.
    """

    if type(invocation) is not ModelInvocationResult:
        return False
    try:
        return _invocation_fields_are_materialised(invocation)
    except Exception:
        return False


def _invocation_fields_are_materialised(
    invocation: ModelInvocationResult,
) -> bool:
    """Verify one exact-typed invocation is fully materialised.

    Every attribute read here may raise on partially fabricated values;
    :func:`_invocation_shape_is_valid` contains those failures. Values
    required by generation-ready provenance must also serialise.
    """

    outcome = invocation.outcome
    digest = invocation.invocation_digest
    role = invocation.role
    fallback_exhausted = invocation.fallback_exhausted
    request = invocation.request
    prompt = request.prompt
    configuration = invocation.configuration
    plan = invocation.plan
    prompt_definition = invocation.prompt_definition
    attempts = invocation.attempts
    final_target = invocation.final_target
    if type(outcome) is not ModelResult:
        return False
    status = outcome.status
    failure_class = outcome.failure_class
    output_text = outcome.output_text
    if not isinstance(status, ModelResultStatus):
        return False
    if failure_class is not None and not isinstance(
        failure_class, ModelFailureClass
    ):
        return False
    if output_text is not None and type(output_text) is not str:
        return False
    if not isinstance(digest, str) or not digest.strip():
        return False
    if role != PlannerClient.role:
        return False
    if type(fallback_exhausted) is not bool:
        return False
    if type(request) is not ModelRequest or type(prompt) is not PromptTemplateRef:
        return False
    if type(configuration) is not InvocationConfiguration:
        return False
    if type(plan) is not FallbackPlan:
        return False
    if type(prompt_definition) is not PromptDefinition:
        return False
    if type(attempts) is not tuple or not all(
        type(attempt) is AttemptedTarget for attempt in attempts
    ):
        return False
    if type(final_target) is not ModelIdentity:
        return False
    if type(plan.primary) is not ModelIdentity:
        return False
    if not isinstance(prompt_definition.ref, PromptTemplateRef):
        return False
    prompt_provenance = prompt.canonical_dict()
    configuration_provenance = configuration.canonical_dict()
    target_provenance = final_target.canonical_dict()
    if not (
        isinstance(prompt_provenance, dict)
        and isinstance(configuration_provenance, dict)
        and isinstance(target_provenance, dict)
    ):
        return False
    return True


def _canonical_json(value: object) -> str:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
