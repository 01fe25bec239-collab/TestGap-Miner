"""Workflow-owned secure generator orchestration over the AGW-002 runtime.

This module owns the smallest bounded Workflow orchestration connecting an
AGW-003 :class:`GenerationReadyIntent` to the already-merged provider-neutral
:class:`GeneratorClient`, producing exactly one typed disposition: a bounded
model-generated proposal or a preserved failure with model/runtime status and
failure-class attribution intact.

The post-invocation gate is semantic, not merely structural: a returned
:class:`ModelInvocationResult` is accepted only when it is provably the answer
to the exact :class:`ModelRequest` this module issued, bound to the pinned
generator model identity, prompt identity/version, prompt definition, and
fallback-plan primary, with legitimately configured fallback attribution still
allowed.

Repository context remains ``UNTRUSTED_REPOSITORY_TEXT``. Every context item
reaches the model-facing request only through the existing Security-owned
untrusted-content boundary, and trusted workflow instructions stay structurally
separated from untrusted repository data via :class:`SecurityContext`. Planner
provenance carried by the intent is cross-bound to the plan it claims to have
produced before any generator invocation. The module performs no execution, no
persistence, no lifecycle transitions, no filesystem access, and no network
behavior; it never selects a provider.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from app.retrieval import (
    ContextBundle,
    ContextBundleIdentity,
    ContextItem,
    RepositoryIdentity,
    RevisionIdentity,
    TokenBudget,
)
from app.security.untrusted_content import (
    ModelFacingContextView,
    SecurityContext,
    SecurityError,
    SecurityErrorCode,
    TrustedInstruction,
    UntrustedContentTrust,
    untrusted_content_from_rag_context_item,
)

from .localisation_adapter import validated_query_text
from .model_domain import (
    ModelBudget,
    ModelDomainError,
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
    GeneratorClient,
    InvocationConfiguration,
    ModelInvocationResult,
)
from .planning import (
    GenerationReadyIntent,
    PlanningRequest,
    ValidatedPlan,
    _invocation_shape_is_valid,
    parse_planner_plan,
)


GENERATION_OUTPUT_SCHEMA_VERSION: Final = "testgap.generation-proposal.v1"
MAX_PROPOSAL_TEXT_BYTES: Final = 262_144

_TASK_INSTRUCTION_VARIABLE: Final = "task_instruction"
_REPOSITORY_DATA_VARIABLE: Final = "repository_data"
_REPOSITORY_ID_VARIABLE: Final = "repository_id"
_REVISION_ID_VARIABLE: Final = "revision_id"
_QUERY_VARIABLE: Final = "query"

GENERATION_OUTPUT_SCHEMA: Final[StructuredOutputSchema] = StructuredOutputSchema(
    (
        StructuredField("proposal_text", StructuredFieldType.STRING),
        StructuredField("schema_version", StructuredFieldType.STRING),
    )
)


class GenerationErrorCode(StrEnum):
    INVALID_GENERATION_REQUEST = "INVALID_GENERATION_REQUEST"
    MALFORMED_GENERATOR_OUTPUT = "MALFORMED_GENERATOR_OUTPUT"
    UNSUPPORTED_PROPOSAL_SCHEMA_VERSION = "UNSUPPORTED_PROPOSAL_SCHEMA_VERSION"
    PROPOSAL_TEXT_EXCEEDS_BOUND = "PROPOSAL_TEXT_EXCEEDS_BOUND"


class GenerationError(ValueError):
    """One deterministic fail-closed rejection with a stable code."""

    def __init__(self, code: GenerationErrorCode, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code.value}: {detail}")


class GenerationBindingCode(StrEnum):
    GENERATION_READY_INTENT_TYPE_INVALID = "GENERATION_READY_INTENT_TYPE_INVALID"
    GENERATION_READY_INTENT_NOT_MATERIALISED = (
        "GENERATION_READY_INTENT_NOT_MATERIALISED"
    )
    PLAN_TYPE_INVALID = "PLAN_TYPE_INVALID"
    CONTEXT_BUNDLE_TYPE_INVALID = "CONTEXT_BUNDLE_TYPE_INVALID"
    REPOSITORY_MISMATCH = "REPOSITORY_MISMATCH"
    REVISION_MISMATCH = "REVISION_MISMATCH"
    CONTEXT_EMPTY = "CONTEXT_EMPTY"
    PLANNER_PROVENANCE_INVALID = "PLANNER_PROVENANCE_INVALID"
    PLANNER_PROVENANCE_NOT_BOUND_TO_PLAN = "PLANNER_PROVENANCE_NOT_BOUND_TO_PLAN"
    PLANNER_STATUS_NOT_SUCCESSFUL = "PLANNER_STATUS_NOT_SUCCESSFUL"


class GenerationDispositionKind(StrEnum):
    PROPOSAL = "PROPOSAL"
    GENERATOR_FAILURE = "GENERATOR_FAILURE"
    SECURITY_CONTEXT_REJECTION = "SECURITY_CONTEXT_REJECTION"
    INVALID_GENERATION_BINDING = "INVALID_GENERATION_BINDING"


class GeneratorFailureReason(StrEnum):
    MODEL_RESULT_NOT_SUCCESSFUL = "MODEL_RESULT_NOT_SUCCESSFUL"
    PROPOSAL_PARSE_REJECTED = "PROPOSAL_PARSE_REJECTED"
    INVOCATION_SHAPE_INVALID = "INVOCATION_SHAPE_INVALID"
    INVOCATION_ERROR = "INVOCATION_ERROR"


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    """Pinned generation inputs preserved exactly from owners and AGW-003.

    The generator model identity, prompt identity/version, budget, and
    correlation/provenance references are caller-supplied owner values;
    none are generated or substituted here. The invocation configuration
    remains owned by the caller's AGW-002 runtime.
    """

    intent: GenerationReadyIntent
    task_instruction: TrustedInstruction
    model: ModelIdentity
    prompt_ref: PromptTemplateRef
    budget: ModelBudget
    correlation_ref: str | None = None
    provenance_ref: str | None = None

    def __post_init__(self) -> None:
        if type(self.intent) is not GenerationReadyIntent:
            raise TypeError("intent must be a GenerationReadyIntent")
        if type(self.task_instruction) is not TrustedInstruction:
            raise TypeError("task_instruction must be a TrustedInstruction")
        if not isinstance(self.model, ModelIdentity):
            raise TypeError("model must be a ModelIdentity")
        if not isinstance(self.prompt_ref, PromptTemplateRef):
            raise TypeError("prompt_ref must be a PromptTemplateRef")
        if not isinstance(self.budget, ModelBudget):
            raise TypeError("budget must be a ModelBudget")
        for name in ("correlation_ref", "provenance_ref"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, str):
                raise TypeError(f"{name} must be a string or None")


@dataclass(frozen=True, slots=True)
class GenerationProposal:
    """Bounded model-produced proposal text.

    The proposal is semantically MODEL_GENERATED, UNTRUSTED, and
    UNVALIDATED_FOR_EXECUTION. It is never Evidence, never a candidate
    patch or version, and never execution authority.
    """

    schema_version: str
    proposal_text: str

    def __post_init__(self) -> None:
        if self.schema_version != GENERATION_OUTPUT_SCHEMA_VERSION:
            raise GenerationError(
                GenerationErrorCode.UNSUPPORTED_PROPOSAL_SCHEMA_VERSION,
                f"unsupported proposal schema version {self.schema_version!r}",
            )
        text = self.proposal_text
        if type(text) is not str or not text.strip():
            raise GenerationError(
                GenerationErrorCode.MALFORMED_GENERATOR_OUTPUT,
                "proposal_text must be nonempty",
            )
        try:
            size = len(text.encode("utf-8"))
        except UnicodeEncodeError as error:
            raise GenerationError(
                GenerationErrorCode.MALFORMED_GENERATOR_OUTPUT,
                "proposal_text contains invalid Unicode",
            ) from error
        if size > MAX_PROPOSAL_TEXT_BYTES:
            raise GenerationError(
                GenerationErrorCode.PROPOSAL_TEXT_EXCEEDS_BOUND,
                f"proposal_text exceeds {MAX_PROPOSAL_TEXT_BYTES} bytes",
            )

    @property
    def trust_label(self) -> UntrustedContentTrust:
        return UntrustedContentTrust.MODEL_GENERATED

    @property
    def execution_authorized(self) -> bool:
        return False

    @property
    def validated_for_execution(self) -> bool:
        return False

    def canonical_dict(self) -> dict[str, object]:
        return {
            "proposal_text": self.proposal_text,
            "schema_version": self.schema_version,
            "trust_label": self.trust_label.value,
        }

    def canonical_json(self) -> str:
        return _canonical_json(self.canonical_dict())


@dataclass(frozen=True, slots=True)
class GeneratedProposalOutcome:
    """Typed successful-model outcome with exact preserved attribution."""

    proposal: GenerationProposal
    intent: GenerationReadyIntent
    generator_invocation: ModelInvocationResult
    security_context_id: str
    security_view: ModelFacingContextView

    def __post_init__(self) -> None:
        if not isinstance(self.proposal, GenerationProposal):
            raise TypeError("proposal must be a GenerationProposal")
        if type(self.intent) is not GenerationReadyIntent:
            raise TypeError("intent must be a GenerationReadyIntent")
        if type(self.generator_invocation) is not ModelInvocationResult:
            raise TypeError(
                "generator_invocation must be a ModelInvocationResult"
            )
        if (
            type(self.security_context_id) is not str
            or not self.security_context_id.strip()
        ):
            raise ValueError(
                "security_context_id must be a nonempty string"
            )
        if type(self.security_view) is not ModelFacingContextView:
            raise TypeError(
                "security_view must be a ModelFacingContextView"
            )


@dataclass(frozen=True, slots=True)
class GeneratorFailureIntent:
    """Typed generator failure; runtime distinctions are preserved.

    ``detail_code`` carries only stable workflow-side taxonomy values and
    never provider internals, refusal prose, or hidden reasoning.
    """

    reason: GeneratorFailureReason
    status: ModelResultStatus | None = None
    failure_class: ModelFailureClass | None = None
    fallback_exhausted: bool = False
    detail_code: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.reason, GeneratorFailureReason):
            raise TypeError("reason must be a GeneratorFailureReason")
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
class SecurityContextRejection:
    """Fail-closed rejection raised by the Security-owned boundary."""

    error_code: SecurityErrorCode | None = None

    def __post_init__(self) -> None:
        if self.error_code is not None and not isinstance(
            self.error_code, SecurityErrorCode
        ):
            raise TypeError(
                "error_code must be a SecurityErrorCode or None"
            )


@dataclass(frozen=True, slots=True)
class InvalidGenerationBinding:
    """Fail-closed rejection of a malformed generation-ready binding."""

    detail_code: str | None = None

    def __post_init__(self) -> None:
        if self.detail_code is not None and (
            type(self.detail_code) is not str or not self.detail_code.strip()
        ):
            raise ValueError("detail_code must be a nonempty string or None")


@dataclass(frozen=True, slots=True)
class GenerationOrchestrationDecision:
    """Exactly one typed orchestration disposition for one attempt."""

    kind: GenerationDispositionKind
    generated: GeneratedProposalOutcome | None = None
    failure: GeneratorFailureIntent | None = None
    security_rejection: SecurityContextRejection | None = None
    invalid_binding: InvalidGenerationBinding | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, GenerationDispositionKind):
            raise TypeError("kind must be a GenerationDispositionKind")
        payloads = {
            GenerationDispositionKind.PROPOSAL: (
                self.generated,
                GeneratedProposalOutcome,
                ("failure", "security_rejection", "invalid_binding"),
            ),
            GenerationDispositionKind.GENERATOR_FAILURE: (
                self.failure,
                GeneratorFailureIntent,
                ("generated", "security_rejection", "invalid_binding"),
            ),
            GenerationDispositionKind.SECURITY_CONTEXT_REJECTION: (
                self.security_rejection,
                SecurityContextRejection,
                ("generated", "failure", "invalid_binding"),
            ),
            GenerationDispositionKind.INVALID_GENERATION_BINDING: (
                self.invalid_binding,
                InvalidGenerationBinding,
                ("generated", "failure", "security_rejection"),
            ),
        }
        payload, expected_type, forbidden = payloads[self.kind]
        if not isinstance(payload, expected_type):
            raise TypeError(
                f"{self.kind.value} requires a {expected_type.__name__} payload"
            )
        for name in forbidden:
            if getattr(self, name) is not None:
                raise ValueError(f"{self.kind.value} cannot carry {name}")


def parse_generator_proposal(output_text: object) -> GenerationProposal:
    """Parse one SUCCESS structured generator output into a proposal.

    Parsing fails closed on malformed JSON text, unexpected fields,
    unsupported schema versions, empty proposals, invalid Unicode, and
    oversized proposal text.
    """

    if not isinstance(output_text, str):
        raise GenerationError(
            GenerationErrorCode.MALFORMED_GENERATOR_OUTPUT,
            "generator output must be JSON text",
        )
    validation = validate_structured_output(output_text, GENERATION_OUTPUT_SCHEMA)
    if validation.status != StructuredValidationStatus.VALID:
        raise GenerationError(
            GenerationErrorCode.MALFORMED_GENERATOR_OUTPUT,
            f"generator output rejected: {validation.status.value}",
        )
    try:
        parsed = json.loads(output_text)
    except ValueError as error:  # pragma: no cover - schema already validated
        raise GenerationError(
            GenerationErrorCode.MALFORMED_GENERATOR_OUTPUT,
            "generator output is not parsable JSON",
        ) from error
    return GenerationProposal(
        schema_version=parsed.get("schema_version"),
        proposal_text=parsed.get("proposal_text"),
    )


def orchestrate_generation(
    *,
    generator_client: object,
    generation_request: GenerationRequest,
) -> GenerationOrchestrationDecision:
    """Run one bounded secure generation attempt and return its decision.

    The coordinator never raises on hostile in-process values or downstream
    failures: fabricated intents, security rejections, malformed invocations,
    and malformed outputs become typed decisions. Only caller misuse of the
    pinned request argument raises a typed :class:`GenerationError`.
    """

    if not isinstance(generation_request, GenerationRequest):
        raise GenerationError(
            GenerationErrorCode.INVALID_GENERATION_REQUEST,
            "generation_request must be a GenerationRequest",
        )
    intent = generation_request.intent
    binding_code = _generation_binding_failure(intent)
    if binding_code is not None:
        return _decision(InvalidGenerationBinding(binding_code))
    try:
        context_id, view = _build_security_view(
            generation_request.task_instruction, intent.context_bundle
        )
    except SecurityError as error:
        return _decision(SecurityContextRejection(error.code))
    except Exception:
        return _decision(SecurityContextRejection())
    try:
        model_request = _build_model_request(generation_request, view)
    except ModelDomainError as error:
        return _decision(InvalidGenerationBinding(error.code.value))
    except Exception:
        return _decision(InvalidGenerationBinding())
    try:
        entrypoint = getattr(generator_client, "invoke", None)
    except Exception:
        entrypoint = None
    if not callable(entrypoint):
        return _decision(
            GeneratorFailureIntent(GeneratorFailureReason.INVOCATION_ERROR)
        )
    try:
        invocation = entrypoint(model_request)
    except Exception:
        return _decision(
            GeneratorFailureIntent(GeneratorFailureReason.INVOCATION_ERROR)
        )
    if not _generator_invocation_is_bound(
        invocation,
        request=model_request,
        model=generation_request.model,
        prompt_ref=generation_request.prompt_ref,
    ):
        return _decision(
            GeneratorFailureIntent(
                GeneratorFailureReason.INVOCATION_SHAPE_INVALID
            )
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
            GeneratorFailureIntent(
                GeneratorFailureReason.MODEL_RESULT_NOT_SUCCESSFUL,
                status=status,
                failure_class=failure_class,
                fallback_exhausted=invocation.fallback_exhausted,
            )
        )
    try:
        proposal = parse_generator_proposal(outcome.output_text)
    except GenerationError as error:
        return _decision(
            GeneratorFailureIntent(
                GeneratorFailureReason.PROPOSAL_PARSE_REJECTED,
                status=ModelResultStatus.INVALID_STRUCTURED_OUTPUT,
                fallback_exhausted=invocation.fallback_exhausted,
                detail_code=error.code.value,
            )
        )
    return _decision(
        GeneratedProposalOutcome(
            proposal=proposal,
            intent=intent,
            generator_invocation=invocation,
            security_context_id=context_id,
            security_view=view,
        )
    )


def _build_security_view(
    instruction: TrustedInstruction, bundle: ContextBundle
) -> tuple[str, ModelFacingContextView]:
    """Route pinned repository context through the Security boundary only.

    Every bundle item becomes Security-owned untrusted content preserving
    its raw bytes and provenance; the single trusted instruction stays on
    the separate instruction channel. Any Security-owned rejection or
    adversarial failure propagates to the fail-closed caller.
    """

    items = tuple(
        untrusted_content_from_rag_context_item(item) for item in bundle.items
    )
    context = SecurityContext(
        context_id=_security_context_id(bundle),
        instructions=(instruction,),
        untrusted_items=items,
    )
    return context.context_id, context.model_facing_view()


def _security_context_id(bundle: ContextBundle) -> str:
    derivation = "|".join(
        (
            bundle.context_bundle_id.value,
            bundle.repository_id.value,
            bundle.revision_id.value,
        )
    )
    digest = hashlib.sha256(derivation.encode("utf-8")).hexdigest()[:32]
    return f"genctx-{digest}"


def _build_model_request(
    request: GenerationRequest, view: ModelFacingContextView
) -> ModelRequest:
    intent = request.intent
    return ModelRequest(
        model=request.model,
        prompt=request.prompt_ref,
        variables={
            _TASK_INSTRUCTION_VARIABLE: view.instruction_channel,
            _REPOSITORY_DATA_VARIABLE: view.untrusted_data_channel,
            _REPOSITORY_ID_VARIABLE: intent.plan.repository_id.value,
            _REVISION_ID_VARIABLE: intent.plan.revision_id.value,
            _QUERY_VARIABLE: intent.plan.query,
        },
        budget=request.budget,
        output_schema=GENERATION_OUTPUT_SCHEMA,
        correlation_ref=request.correlation_ref,
        provenance_ref=request.provenance_ref,
    )


def _generation_binding_failure(intent: object) -> str | None:
    """Total fail-closed validation of one generation-ready binding.

    Fabricated or partially initialised values (for example via
    ``object.__new__``), missing fields, malformed nested fields, drifted
    identities, and adversarial attribute access all produce a stable
    failure code instead of leaking raw exceptions through the public
    orchestration boundary.
    """

    if type(intent) is not GenerationReadyIntent:
        return GenerationBindingCode.GENERATION_READY_INTENT_TYPE_INVALID.value
    try:
        return _binding_checks(intent)
    except Exception:
        return (
            GenerationBindingCode.GENERATION_READY_INTENT_NOT_MATERIALISED.value
        )


def _binding_checks(intent: GenerationReadyIntent) -> str | None:
    plan = intent.plan
    bundle = intent.context_bundle
    if type(plan) is not ValidatedPlan:
        return GenerationBindingCode.PLAN_TYPE_INVALID.value
    if (
        type(plan.repository_id) is not RepositoryIdentity
        or type(plan.revision_id) is not RevisionIdentity
        or type(plan.schema_version) is not str
        or not plan.schema_version.strip()
    ):
        return GenerationBindingCode.PLAN_TYPE_INVALID.value
    validated_query_text(plan.query)
    if type(bundle) is not ContextBundle:
        return GenerationBindingCode.CONTEXT_BUNDLE_TYPE_INVALID.value
    items = bundle.items
    if (
        type(bundle.context_bundle_id) is not ContextBundleIdentity
        or type(bundle.repository_id) is not RepositoryIdentity
        or type(bundle.revision_id) is not RevisionIdentity
        or type(bundle.token_budget) is not TokenBudget
        or type(items) is not tuple
        or not all(type(item) is ContextItem for item in items)
    ):
        return GenerationBindingCode.CONTEXT_BUNDLE_TYPE_INVALID.value
    if bundle.repository_id != plan.repository_id:
        return GenerationBindingCode.REPOSITORY_MISMATCH.value
    if bundle.revision_id != plan.revision_id:
        return GenerationBindingCode.REVISION_MISMATCH.value
    if not items:
        return GenerationBindingCode.CONTEXT_EMPTY.value
    if not _invocation_shape_is_valid(intent.planner_invocation):
        return GenerationBindingCode.PLANNER_PROVENANCE_INVALID.value
    if intent.planner_invocation.outcome.status != ModelResultStatus.SUCCESS:
        return GenerationBindingCode.PLANNER_STATUS_NOT_SUCCESSFUL.value
    return _planner_provenance_cross_binding_failure(intent)


def _planner_provenance_cross_binding_failure(
    intent: GenerationReadyIntent,
) -> str | None:
    """Bind planner provenance to the carried plan, not merely its shape.

    AGW-003's invocation gate is intentionally structural; a fabricated
    intent could otherwise combine one valid plan/bundle with a different
    individually valid planner invocation. Only durable values already
    carried by the intent are consumed: the planner outcome must re-parse,
    under AGW-003's own parser and the plan's pinned identities, to
    exactly the carried plan; the prompt definition must be the one
    referenced by the planner request; and every attributed attempt must
    belong to the invocation's own fallback plan.

    The directly provable AGW-002 runtime attribution relationships are
    also enforced: the requested model must equal the fallback-plan
    primary (silent substitution is forbidden at the runtime boundary),
    and a successful invocation must carry actual attempt attribution —
    non-empty attempts whose final target is the final target and whose
    final outcome is exactly the top-level outcome.
    """

    unbound = (
        GenerationBindingCode.PLANNER_PROVENANCE_NOT_BOUND_TO_PLAN.value
    )
    invocation = intent.planner_invocation
    try:
        replay_request = PlanningRequest(
            intent.plan.repository_id,
            intent.plan.revision_id,
            invocation.request,
        )
        reparsed = parse_planner_plan(
            invocation.outcome.output_text, replay_request
        )
        if reparsed != intent.plan:
            return unbound
        if invocation.prompt_definition.ref != invocation.request.prompt:
            return unbound
        if invocation.request.model != invocation.plan.primary:
            return unbound
        if not _final_attempt_attribution_is_consistent(invocation):
            return unbound
        targets = invocation.plan.targets
        if any(
            attempt.target not in targets
            for attempt in invocation.attempts
        ):
            return unbound
    except Exception:
        return unbound
    return None


def _final_attempt_attribution_is_consistent(
    invocation: ModelInvocationResult,
) -> bool:
    """Prove actual, consistent final attempt attribution for one result.

    A genuine invocation through the AGW-002 runtime always attributes at
    least one attempted target, ends on that last attributed target, and
    reports exactly that attempt's outcome as the top-level outcome.
    A fully materialised result with ``attempts=()`` is therefore never
    accepted as an attributed success, regardless of its other fields.
    """

    attempts = invocation.attempts
    if not attempts:
        return False
    if invocation.final_target != attempts[-1].target:
        return False
    return attempts[-1].outcome == invocation.outcome


def _generator_invocation_is_valid(value: object) -> bool:
    """Structural half of the generator invocation gate.

    Proves the value is a fully materialised, exact-typed invocation
    result. Semantic binding to the issued :class:`ModelRequest` is
    proven separately by :func:`_generator_invocation_is_bound`.
    """

    if type(value) is not ModelInvocationResult:
        return False
    try:
        return _generator_invocation_is_materialised(value)
    except Exception:
        return False


def _generator_invocation_is_bound(
    value: object,
    *,
    request: ModelRequest,
    model: ModelIdentity,
    prompt_ref: PromptTemplateRef,
) -> bool:
    """Fail-closed semantic binding of one returned generator invocation.

    A structurally valid result is still rejected unless it is the answer
    to the exact request this orchestration issued: same request,
    generator model identity, prompt identity/version, prompt definition,
    and fallback-plan primary. A legitimately configured fallback remains
    allowed — the final target may differ from the primary — but every
    attributed attempt must belong to the invocation's own plan.
    Fabricated, substituted, or otherwise unrelated well-formed values
    fail closed here before any proposal can be accepted.
    """

    if not _generator_invocation_is_valid(value):
        return False
    assert isinstance(value, ModelInvocationResult)
    try:
        return _generator_invocation_semantics_bind(
            value, request=request, model=model, prompt_ref=prompt_ref
        )
    except Exception:
        return False


def _generator_invocation_semantics_bind(
    invocation: ModelInvocationResult,
    *,
    request: ModelRequest,
    model: ModelIdentity,
    prompt_ref: PromptTemplateRef,
) -> bool:
    """Prove the invocation is bound to this attempt's pinned identity.

    Beyond identity binding, a genuine invocation through the AGW-002
    runtime must carry actual attempt attribution: non-empty attempts,
    ending on the final attributed target, whose final outcome is exactly
    the top-level invocation outcome. A fully materialised SUCCESS result
    with ``attempts=()`` is a fabricated-success shape and fails closed.
    """

    if invocation.role != GeneratorClient.role:
        return False
    if type(invocation.prompt_definition.ref) is not PromptTemplateRef:
        return False
    if invocation.request != request:
        return False
    if invocation.request.model != model:
        return False
    if invocation.request.prompt != prompt_ref:
        return False
    if invocation.prompt_definition.ref != prompt_ref:
        return False
    if invocation.plan.primary != model:
        return False
    configuration_provenance = invocation.configuration.canonical_dict()
    if set(configuration_provenance) != {
        "allow_tool_calls",
        "seed",
        "temperature",
    }:
        return False
    targets = invocation.plan.targets
    if any(attempt.target not in targets for attempt in invocation.attempts):
        return False
    return _final_attempt_attribution_is_consistent(invocation)


def _generator_invocation_is_materialised(
    invocation: ModelInvocationResult,
) -> bool:
    """Verify one exact-typed generator invocation is fully materialised."""

    outcome = invocation.outcome
    digest = invocation.invocation_digest
    if invocation.role != GeneratorClient.role:
        return False
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
    if type(invocation.fallback_exhausted) is not bool:
        return False
    if type(invocation.request) is not ModelRequest:
        return False
    if type(invocation.configuration) is not InvocationConfiguration:
        return False
    if type(invocation.plan) is not FallbackPlan:
        return False
    if type(invocation.prompt_definition) is not PromptDefinition:
        return False
    if not isinstance(invocation.prompt_definition.ref, PromptTemplateRef):
        return False
    attempts = invocation.attempts
    if type(attempts) is not tuple or not all(
        type(attempt) is AttemptedTarget for attempt in attempts
    ):
        return False
    final_target = invocation.final_target
    if type(final_target) is not ModelIdentity:
        return False
    if type(invocation.request.prompt) is not PromptTemplateRef:
        return False
    if not (
        isinstance(invocation.request.prompt.canonical_dict(), dict)
        and isinstance(invocation.configuration.canonical_dict(), dict)
        and isinstance(final_target.canonical_dict(), dict)
    ):
        return False
    return True


def _decision(payload: object) -> GenerationOrchestrationDecision:
    if isinstance(payload, GeneratedProposalOutcome):
        return GenerationOrchestrationDecision(
            GenerationDispositionKind.PROPOSAL,
            generated=payload,
        )
    if isinstance(payload, GeneratorFailureIntent):
        return GenerationOrchestrationDecision(
            GenerationDispositionKind.GENERATOR_FAILURE,
            failure=payload,
        )
    if isinstance(payload, SecurityContextRejection):
        return GenerationOrchestrationDecision(
            GenerationDispositionKind.SECURITY_CONTEXT_REJECTION,
            security_rejection=payload,
        )
    assert isinstance(payload, InvalidGenerationBinding)
    return GenerationOrchestrationDecision(
        GenerationDispositionKind.INVALID_GENERATION_BINDING,
        invalid_binding=payload,
    )


def _canonical_json(value: object) -> str:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
