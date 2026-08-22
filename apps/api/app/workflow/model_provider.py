"""Provider-neutral model invocation runtime for Workflow.

This module bridges the pure values in ``model_domain`` to bounded
invocation semantics: a narrow provider protocol, deterministic
invocation configuration, structured-output enforcement, budget
boundaries, explicit bounded fallback, and safe model-level abstention.

No production model provider exists or is selected. The only bundled
implementation is :class:`DeterministicFakeProvider`, an offline
deterministic provider double for unit tests. This module performs no
network, SDK, credential, randomness, or wall-clock behavior and never
selects a real vendor.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Iterable
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import ClassVar, Final, Protocol, runtime_checkable

from .model_domain import (
    MAX_IDENTIFIER_LENGTH,
    MAX_INPUT_TOKENS,
    MAX_OUTPUT_TOKENS,
    ModelFailureClass,
    ModelIdentity,
    ModelRequest,
    ModelResult,
    ModelResultStatus,
    PromptDefinition,
    PromptRegistry,
    PromptTemplateRef,
    StructuredValidationStatus,
    validate_model_request,
    validate_structured_output,
)

__all__ = [
    "MAX_FALLBACK_TARGETS",
    "MAX_SEED",
    "MAX_TEMPERATURE",
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
]


MAX_TEMPERATURE: Final = 2.0
MAX_SEED: Final = 2_147_483_647
MAX_FALLBACK_TARGETS: Final = 8

_UNSET_PROVIDER_SLOT: Final[object] = object()

_IDENTIFIER_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+\-]*\Z")


class ModelRuntimeError(RuntimeError):
    """Raised when a caller misuses the runtime boundary (programmer error)."""


class ProviderTimeoutError(Exception):
    """Raised by providers when an invocation exceeds its latency bound."""


class ProviderFailureError(Exception):
    """Raised by providers to report a typed provider-side failure."""

    def __init__(
        self,
        failure_class: ModelFailureClass = ModelFailureClass.PROVIDER_INTERNAL_ERROR,
    ) -> None:
        if not isinstance(failure_class, ModelFailureClass):
            raise TypeError("failure_class must be a ModelFailureClass")
        self.failure_class = failure_class
        super().__init__(failure_class.value)


class RetryableCondition(StrEnum):
    TIMEOUT = "TIMEOUT"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"
    INVALID_STRUCTURED_OUTPUT = "INVALID_STRUCTURED_OUTPUT"

    @classmethod
    def for_status(cls, status: ModelResultStatus) -> RetryableCondition | None:
        if status == ModelResultStatus.TIMEOUT:
            return cls.TIMEOUT
        if status == ModelResultStatus.PROVIDER_OR_MODEL_FAILURE:
            return cls.PROVIDER_FAILURE
        if status == ModelResultStatus.INVALID_STRUCTURED_OUTPUT:
            return cls.INVALID_STRUCTURED_OUTPUT
        return None


_TERMINAL_STATUSES: Final[frozenset[ModelResultStatus]] = frozenset(
    {
        ModelResultStatus.SUCCESS,
        ModelResultStatus.REFUSAL,
        ModelResultStatus.ABSTENTION,
        ModelResultStatus.BUDGET_EXCEEDED,
        ModelResultStatus.VALIDATION_FAILURE,
    }
)
_DEFAULT_RETRYABLE: Final[frozenset[RetryableCondition]] = frozenset(
    {RetryableCondition.TIMEOUT, RetryableCondition.PROVIDER_FAILURE}
)


@dataclass(frozen=True, slots=True)
class InvocationConfiguration:
    """Explicit provider-neutral invocation configuration.

    Only semantics that can be validated deterministically without a
    selected provider are representable. Configuration identity remains
    owned by ``ModelIdentity.configuration_version``.
    """

    temperature: float | None = None
    seed: int | None = None
    allow_tool_calls: bool = False

    def __post_init__(self) -> None:
        if self.temperature is not None:
            value = self.temperature
            if type(value) not in (int, float):
                raise ModelRuntimeError("temperature must be a number")
            normalized = float(value)
            if not math.isfinite(normalized):
                raise ModelRuntimeError("temperature must be finite")
            if not 0 <= normalized <= MAX_TEMPERATURE:
                raise ModelRuntimeError(
                    f"temperature must be between 0 and {MAX_TEMPERATURE}"
                )
            object.__setattr__(self, "temperature", normalized)
        if self.seed is not None:
            if type(self.seed) is not int or not 0 <= self.seed <= MAX_SEED:
                raise ModelRuntimeError(
                    f"seed must be an integer from 0 to {MAX_SEED}"
                )
        if type(self.allow_tool_calls) is not bool:
            raise ModelRuntimeError("allow_tool_calls must be a bool")

    def canonical_dict(self) -> dict[str, float | int | bool | None]:
        return {
            "allow_tool_calls": self.allow_tool_calls,
            "seed": self.seed,
            "temperature": self.temperature,
        }

    def canonical_json(self) -> str:
        return _canonical_json(self.canonical_dict())


@dataclass(frozen=True, slots=True)
class ProviderUsage:
    """Validated provider-neutral token usage counters."""

    input_tokens: int
    output_tokens: int

    def __post_init__(self) -> None:
        for name, value in (
            ("input_tokens", self.input_tokens),
            ("output_tokens", self.output_tokens),
        ):
            if type(value) is not int:
                raise ModelRuntimeError(f"{name} must be an integer")
            if value < 0:
                raise ModelRuntimeError(f"{name} must be non-negative")
        if self.input_tokens > MAX_INPUT_TOKENS:
            raise ModelRuntimeError("input_tokens exceeds the domain bound")
        if self.output_tokens > MAX_OUTPUT_TOKENS:
            raise ModelRuntimeError("output_tokens exceeds the domain bound")

    def canonical_dict(self) -> dict[str, int]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }


@dataclass(frozen=True, slots=True)
class ProviderInvocationResult:
    """Typed outcome returned across the provider protocol boundary."""

    result: ModelResult
    usage: ProviderUsage | None = None
    model_revision: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.result, ModelResult):
            raise ModelRuntimeError("result must be a ModelResult")
        if self.usage is not None and not isinstance(self.usage, ProviderUsage):
            raise ModelRuntimeError("usage must be a ProviderUsage or None")
        if self.model_revision is not None:
            object.__setattr__(
                self,
                "model_revision",
                _normalize_identifier("model_revision", self.model_revision),
            )


@runtime_checkable
class ModelProvider(Protocol):
    """Narrow provider-neutral invocation protocol.

    Implementations accept the typed request, the resolved prompt
    definition, and the deterministic configuration, and return a typed
    result. No provider SDK types may appear here.
    """

    def invoke(
        self,
        request: ModelRequest,
        definition: PromptDefinition,
        configuration: InvocationConfiguration,
    ) -> ProviderInvocationResult:
        """Invoke the model once and return a typed provider result."""
        ...


@dataclass(frozen=True, slots=True)
class FallbackPlan:
    """Immutable ordered fallback policy over explicit model targets."""

    primary: ModelIdentity
    fallbacks: tuple[ModelIdentity, ...] | Iterable[ModelIdentity] = ()
    retryable: Iterable[RetryableCondition] | frozenset[RetryableCondition] = (
        _DEFAULT_RETRYABLE
    )

    def __post_init__(self) -> None:
        if not isinstance(self.primary, ModelIdentity):
            raise ModelRuntimeError("primary must be a ModelIdentity")
        if isinstance(self.fallbacks, (str, bytes)):
            raise ModelRuntimeError("fallbacks must be ModelIdentity targets")
        try:
            supplied = tuple(self.fallbacks)
        except TypeError as error:
            raise ModelRuntimeError("fallbacks must be iterable") from error
        if len(supplied) > MAX_FALLBACK_TARGETS:
            raise ModelRuntimeError(f"fallback count exceeds {MAX_FALLBACK_TARGETS}")
        for target in supplied:
            if not isinstance(target, ModelIdentity):
                raise ModelRuntimeError("fallbacks must be ModelIdentity targets")
        seen = [self.primary, *supplied]
        if len({target.canonical_json() for target in seen}) != len(seen):
            raise ModelRuntimeError("fallback plan contains duplicate targets")
        object.__setattr__(self, "fallbacks", supplied)
        try:
            conditions = frozenset(self.retryable)
        except TypeError as error:
            raise ModelRuntimeError("retryable must be iterable") from error
        for condition in conditions:
            if not isinstance(condition, RetryableCondition):
                raise ModelRuntimeError("retryable must be RetryableCondition values")
        object.__setattr__(self, "retryable", conditions)

    @property
    def targets(self) -> tuple[ModelIdentity, ...]:
        return (self.primary, *self.fallbacks)

    def canonical_dict(self) -> dict[str, object]:
        return {
            "fallbacks": [target.canonical_dict() for target in self.fallbacks],
            "primary": self.primary.canonical_dict(),
            "retryable": sorted(condition.value for condition in self.retryable),
        }

    def canonical_json(self) -> str:
        return _canonical_json(self.canonical_dict())


@dataclass(frozen=True, slots=True)
class AttemptedTarget:
    """One attributed attempt against one explicit plan target."""

    target: ModelIdentity
    attempt_number: int
    outcome: ModelResult
    usage: ProviderUsage | None = None
    model_revision: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.target, ModelIdentity):
            raise ModelRuntimeError("target must be a ModelIdentity")
        if type(self.attempt_number) is not int or self.attempt_number < 1:
            raise ModelRuntimeError("attempt_number must be a positive integer")
        if not isinstance(self.outcome, ModelResult):
            raise ModelRuntimeError("outcome must be a ModelResult")
        if self.usage is not None and not isinstance(self.usage, ProviderUsage):
            raise ModelRuntimeError("usage must be a ProviderUsage or None")
        if self.model_revision is not None:
            object.__setattr__(
                self,
                "model_revision",
                _normalize_identifier("model_revision", self.model_revision),
            )

    def canonical_dict(self) -> dict[str, object]:
        return {
            "attempt_number": self.attempt_number,
            "model_revision": self.model_revision,
            "outcome": {
                "detail": self.outcome.detail,
                "refusal_reason": self.outcome.refusal_reason,
                "status": self.outcome.status.value,
            },
            "target": self.target.canonical_dict(),
            "usage": (
                self.usage.canonical_dict() if self.usage is not None else None
            ),
        }

    def canonical_json(self) -> str:
        return _canonical_json(self.canonical_dict())


@dataclass(frozen=True, slots=True)
class ModelInvocationResult:
    """Fully attributed outcome of one bounded runtime invocation."""

    role: str
    request: ModelRequest
    configuration: InvocationConfiguration
    plan: FallbackPlan
    prompt_definition: PromptDefinition
    invocation_digest: str
    attempts: tuple[AttemptedTarget, ...]
    outcome: ModelResult
    fallback_exhausted: bool

    @property
    def final_target(self) -> ModelIdentity:
        if not self.attempts:
            return self.plan.primary
        return self.attempts[-1].target


class ModelRuntime:
    """Shared provider-neutral invocation core.

    Enforces pre-call validation, structured-output enforcement, budget
    boundaries, bounded retries, and the explicit fallback plan. Every
    attempted target keeps full attribution; no substitution is silent.
    """

    def __init__(
        self,
        *,
        registry: PromptRegistry,
        provider: ModelProvider,
        configuration: InvocationConfiguration,
        plan: FallbackPlan,
    ) -> None:
        if not isinstance(registry, PromptRegistry):
            raise ModelRuntimeError("registry must be a PromptRegistry")
        registry.entries
        if not isinstance(provider, ModelProvider):
            raise ModelRuntimeError("provider must satisfy ModelProvider")
        if not isinstance(configuration, InvocationConfiguration):
            raise ModelRuntimeError(
                "configuration must be an InvocationConfiguration"
            )
        if not isinstance(plan, FallbackPlan):
            raise ModelRuntimeError("plan must be a FallbackPlan")
        self._registry = registry
        self._provider = provider
        self._configuration = configuration
        self._plan = plan

    @property
    def plan(self) -> FallbackPlan:
        return self._plan

    @property
    def configuration(self) -> InvocationConfiguration:
        return self._configuration

    def invoke(
        self,
        role: str,
        request: ModelRequest,
        *,
        declared_input_tokens: int | None = None,
    ) -> ModelInvocationResult:
        if not isinstance(role, str) or not role.strip():
            raise ModelRuntimeError("role must be a nonempty string")
        if not isinstance(request, ModelRequest):
            raise ModelRuntimeError("request must be a ModelRequest")
        if request.model != self._plan.primary:
            raise ModelRuntimeError(
                "request model does not match the primary plan target; "
                "silent substitution is forbidden"
            )
        definition = validate_model_request(request, self._registry)
        digest = _invocation_digest(request, self._configuration, self._plan)
        if declared_input_tokens is not None:
            if type(declared_input_tokens) is not int or declared_input_tokens < 0:
                raise ModelRuntimeError(
                    "declared_input_tokens must be a non-negative integer"
                )
            if declared_input_tokens > request.budget.max_input_tokens:
                return self._finalize(
                    role=role,
                    request=request,
                    definition=definition,
                    digest=digest,
                    attempts=(),
                    outcome=ModelResult(
                        ModelResultStatus.BUDGET_EXCEEDED,
                        detail="declared input tokens exceed the request budget",
                    ),
                    fallback_exhausted=False,
                )
        attempts: list[AttemptedTarget] = []
        attempts_allowed = request.budget.retry_budget + 1
        for target in self._plan.targets:
            effective = (
                request if target == request.model else replace(request, model=target)
            )
            for attempt_number in range(1, attempts_allowed + 1):
                outcome, usage, revision = self._invoke_provider(effective, definition)
                attempts.append(
                    AttemptedTarget(
                        target=target,
                        attempt_number=attempt_number,
                        outcome=outcome,
                        usage=usage,
                        model_revision=revision,
                    )
                )
                if outcome.status in _TERMINAL_STATUSES:
                    return self._finalize(
                        role=role,
                        request=request,
                        definition=definition,
                        digest=digest,
                        attempts=attempts,
                        outcome=outcome,
                        fallback_exhausted=False,
                    )
                condition = RetryableCondition.for_status(outcome.status)
                if condition is None or condition not in self._plan.retryable:
                    return self._finalize(
                        role=role,
                        request=request,
                        definition=definition,
                        digest=digest,
                        attempts=attempts,
                        outcome=outcome,
                        fallback_exhausted=False,
                    )
        return self._finalize(
            role=role,
            request=request,
            definition=definition,
            digest=digest,
            attempts=attempts,
            outcome=attempts[-1].outcome,
            fallback_exhausted=True,
        )

    def _invoke_provider(
        self, request: ModelRequest, definition: PromptDefinition
    ) -> tuple[ModelResult, ProviderUsage | None, str | None]:
        try:
            raw = self._provider.invoke(request, definition, self._configuration)
        except ProviderTimeoutError:
            return (
                ModelResult(
                    ModelResultStatus.TIMEOUT,
                    detail="provider exceeded the configured latency bound",
                ),
                None,
                None,
            )
        except ProviderFailureError as error:
            return (
                ModelResult(
                    ModelResultStatus.PROVIDER_OR_MODEL_FAILURE,
                    failure_class=error.failure_class,
                    detail="provider reported a typed failure",
                ),
                None,
                None,
            )
        except Exception:
            return (
                ModelResult(
                    ModelResultStatus.PROVIDER_OR_MODEL_FAILURE,
                    failure_class=ModelFailureClass.PROVIDER_INTERNAL_ERROR,
                    detail="provider invocation failed",
                ),
                None,
                None,
            )
        if not isinstance(raw, ProviderInvocationResult):
            return (
                ModelResult(
                    ModelResultStatus.PROVIDER_OR_MODEL_FAILURE,
                    failure_class=ModelFailureClass.PROVIDER_INTERNAL_ERROR,
                    detail="invalid provider result shape",
                ),
                None,
                None,
            )
        outcome = getattr(raw, "result", _UNSET_PROVIDER_SLOT)
        usage = getattr(raw, "usage", _UNSET_PROVIDER_SLOT)
        revision = getattr(raw, "model_revision", _UNSET_PROVIDER_SLOT)
        if (
            not isinstance(outcome, ModelResult)
            or not (usage is None or isinstance(usage, ProviderUsage))
            or not (revision is None or isinstance(revision, str))
        ):
            return (
                ModelResult(
                    ModelResultStatus.PROVIDER_OR_MODEL_FAILURE,
                    failure_class=ModelFailureClass.PROVIDER_INTERNAL_ERROR,
                    detail="invalid provider result shape",
                ),
                None,
                None,
            )
        if revision is not None:
            try:
                revision = _normalize_identifier("model_revision", revision)
            except ModelRuntimeError:
                return (
                    ModelResult(
                        ModelResultStatus.PROVIDER_OR_MODEL_FAILURE,
                        failure_class=ModelFailureClass.PROVIDER_INTERNAL_ERROR,
                        detail="invalid provider result shape",
                    ),
                    None,
                    None,
                )
        if usage is not None and (
            usage.output_tokens > request.budget.max_output_tokens
            or usage.input_tokens > request.budget.max_input_tokens
        ):
            return (
                ModelResult(
                    ModelResultStatus.BUDGET_EXCEEDED,
                    detail="provider usage contradicts the request budget",
                ),
                usage,
                revision,
            )
        schema = request.output_schema
        if outcome.status == ModelResultStatus.SUCCESS and schema is not None:
            validation = validate_structured_output(outcome.output_text, schema)
            if validation.status == StructuredValidationStatus.VALID:
                outcome = ModelResult(
                    ModelResultStatus.SUCCESS,
                    output_text=outcome.output_text,
                    structured_validation=validation,
                )
            else:
                outcome = ModelResult(
                    ModelResultStatus.INVALID_STRUCTURED_OUTPUT,
                    structured_validation=validation,
                )
        return outcome, usage, revision

    def _finalize(
        self,
        *,
        role: str,
        request: ModelRequest,
        definition: PromptDefinition,
        digest: str,
        attempts: tuple[AttemptedTarget, ...] | list[AttemptedTarget],
        outcome: ModelResult,
        fallback_exhausted: bool,
    ) -> ModelInvocationResult:
        return ModelInvocationResult(
            role=role.strip(),
            request=request,
            configuration=self._configuration,
            plan=self._plan,
            prompt_definition=definition,
            invocation_digest=digest,
            attempts=tuple(attempts),
            outcome=outcome,
            fallback_exhausted=fallback_exhausted,
        )


class _RoleBoundClient:
    """Thin semantic client binding one role to one prompt template.

    Foreign prompt identities (a different ``template_id``) are rejected
    here as caller misuse. A stale version of the bound template is
    delegated to the runtime, whose registry lookup fails closed with
    ``PROMPT_NOT_FOUND`` before any provider call.
    """

    role: ClassVar[str]

    def __init__(
        self, runtime: ModelRuntime, prompt_ref: PromptTemplateRef
    ) -> None:
        if not isinstance(runtime, ModelRuntime):
            raise ModelRuntimeError("runtime must be a ModelRuntime")
        if not isinstance(prompt_ref, PromptTemplateRef):
            raise ModelRuntimeError("prompt_ref must be a PromptTemplateRef")
        self._runtime = runtime
        self._prompt_ref = prompt_ref

    @property
    def prompt_ref(self) -> PromptTemplateRef:
        return self._prompt_ref

    def invoke(
        self,
        request: ModelRequest,
        *,
        declared_input_tokens: int | None = None,
    ) -> ModelInvocationResult:
        if not isinstance(request, ModelRequest):
            raise ModelRuntimeError("request must be a ModelRequest")
        if request.prompt.template_id != self._prompt_ref.template_id:
            raise ModelRuntimeError(
                f"{self.role} client is bound to prompt "
                f"{self._prompt_ref.template_id}@{self._prompt_ref.version}"
            )
        return self._runtime.invoke(
            self.role, request, declared_input_tokens=declared_input_tokens
        )


class PlannerClient(_RoleBoundClient):
    role: ClassVar[str] = "PLANNER"


class GeneratorClient(_RoleBoundClient):
    role: ClassVar[str] = "GENERATOR"


class CriticClient(_RoleBoundClient):
    role: ClassVar[str] = "CRITIC"


class DeterministicFakeProvider:
    """Offline deterministic provider double for unit tests.

    Responses are consumed from an immutable script in order; once the
    script is exhausted the last response repeats deterministically.
    Script entries are :class:`ProviderInvocationResult` values or
    exception instances/subclasses to raise. There is no network, SDK,
    credential, randomness, or wall-clock behavior, and no provider
    selection logic.
    """

    def __init__(
        self, script: Iterable[ProviderInvocationResult | Exception]
    ) -> None:
        steps = tuple(script)
        if not steps:
            raise ValueError("script must contain at least one response")
        for step in steps:
            if isinstance(step, Exception):
                continue
            if isinstance(step, type) and issubclass(step, Exception):
                continue
            if not isinstance(step, ProviderInvocationResult):
                raise TypeError(
                    "script entries must be ProviderInvocationResult or Exception"
                )
        self._steps = steps
        self._cursor = 0

    @property
    def calls(self) -> int:
        return self._cursor

    def invoke(
        self,
        request: ModelRequest,
        definition: PromptDefinition,
        configuration: InvocationConfiguration,
    ) -> ProviderInvocationResult:
        del request, definition, configuration
        index = min(self._cursor, len(self._steps) - 1)
        self._cursor += 1
        step = self._steps[index]
        if isinstance(step, Exception):
            raise step
        if isinstance(step, type) and issubclass(step, Exception):
            raise step()
        return step


def _normalize_identifier(name: str, value: object) -> str:
    if not isinstance(value, str):
        raise ModelRuntimeError(f"{name} must be a string")
    normalized = value.strip()
    if not normalized or len(normalized) > MAX_IDENTIFIER_LENGTH:
        raise ModelRuntimeError(f"{name} has an invalid length")
    if _IDENTIFIER_PATTERN.fullmatch(normalized) is None:
        raise ModelRuntimeError(f"{name} contains invalid characters")
    return normalized


def _invocation_digest(
    request: ModelRequest,
    configuration: InvocationConfiguration,
    plan: FallbackPlan,
) -> str:
    payload = _canonical_json(
        {
            "configuration": configuration.canonical_dict(),
            "plan": plan.canonical_dict(),
            "request": request.canonical_dict(),
        }
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
