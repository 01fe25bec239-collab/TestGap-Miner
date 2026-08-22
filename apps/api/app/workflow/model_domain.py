"""Pure provider-neutral model and prompt domain values."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, NoReturn


MAX_IDENTIFIER_LENGTH: Final = 128
MAX_TEMPLATE_BYTES: Final = 262_144
MAX_TEMPLATE_VARIABLES: Final = 64
MAX_VARIABLE_VALUE_BYTES: Final = 16_384
MAX_VARIABLE_PAYLOAD_BYTES: Final = 65_536
MAX_METADATA_ENTRIES: Final = 32
MAX_METADATA_VALUE_BYTES: Final = 4_096
MAX_METADATA_PAYLOAD_BYTES: Final = 16_384
MAX_REGISTRY_ENTRIES: Final = 1_024
MAX_SCHEMA_FIELDS: Final = 128
MAX_STRUCTURED_OUTPUT_BYTES: Final = 1_048_576
MAX_INPUT_TOKENS: Final = 2_000_000
MAX_OUTPUT_TOKENS: Final = 200_000
MAX_RETRY_BUDGET: Final = 10
MAX_LATENCY_MS: Final = 3_600_000

_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+\-]*\Z")
_VARIABLE_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


class ModelDomainErrorCode(StrEnum):
    INVALID_IDENTITY = "INVALID_IDENTITY"
    INVALID_PROMPT_DEFINITION = "INVALID_PROMPT_DEFINITION"
    PROMPT_VERSION_CONFLICT = "PROMPT_VERSION_CONFLICT"
    INVALID_MODEL_BUDGET = "INVALID_MODEL_BUDGET"
    INVALID_MODEL_REQUEST = "INVALID_MODEL_REQUEST"
    PROMPT_NOT_FOUND = "PROMPT_NOT_FOUND"
    INVALID_STRUCTURED_SCHEMA = "INVALID_STRUCTURED_SCHEMA"
    INVALID_RESULT_SHAPE = "INVALID_RESULT_SHAPE"


class ModelDomainError(ValueError):
    """One deterministic rejection type with a small stable code taxonomy."""

    def __init__(self, code: ModelDomainErrorCode, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code.value}: {detail}")


class StructuredFieldType(StrEnum):
    STRING = "STRING"
    INTEGER = "INTEGER"
    NUMBER = "NUMBER"
    BOOLEAN = "BOOLEAN"
    OBJECT = "OBJECT"
    ARRAY = "ARRAY"


class StructuredValidationStatus(StrEnum):
    VALID = "VALID"
    MALFORMED = "MALFORMED"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    UNEXPECTED_FIELD = "UNEXPECTED_FIELD"


class ModelResultStatus(StrEnum):
    SUCCESS = "SUCCESS"
    REFUSAL = "REFUSAL"
    ABSTENTION = "ABSTENTION"
    PROVIDER_OR_MODEL_FAILURE = "PROVIDER_OR_MODEL_FAILURE"
    INVALID_STRUCTURED_OUTPUT = "INVALID_STRUCTURED_OUTPUT"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    TIMEOUT = "TIMEOUT"
    VALIDATION_FAILURE = "VALIDATION_FAILURE"


class ModelFailureClass(StrEnum):
    TRANSPORT_FAILURE = "TRANSPORT_FAILURE"
    RATE_LIMITED = "RATE_LIMITED"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    PROVIDER_INTERNAL_ERROR = "PROVIDER_INTERNAL_ERROR"
    MODEL_ERROR = "MODEL_ERROR"


@dataclass(frozen=True, slots=True)
class ModelIdentity:
    provider_ref: str
    model_id: str
    configuration_version: str
    capability_profile: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "provider_ref",
            _normalize_identifier("provider_ref", self.provider_ref),
        )
        object.__setattr__(
            self, "model_id", _normalize_identifier("model_id", self.model_id)
        )
        if self.capability_profile is not None:
            object.__setattr__(
                self,
                "capability_profile",
                _normalize_identifier(
                    "capability_profile", self.capability_profile
                ),
            )
        object.__setattr__(
            self,
            "configuration_version",
            _normalize_identifier(
                "configuration_version", self.configuration_version
            ),
        )

    def canonical_dict(self) -> dict[str, str | None]:
        return {
            "capability_profile": self.capability_profile,
            "configuration_version": self.configuration_version,
            "model_id": self.model_id,
            "provider_ref": self.provider_ref,
        }

    def canonical_json(self) -> str:
        return _canonical_json(self.canonical_dict())


@dataclass(frozen=True, slots=True)
class PromptTemplateRef:
    template_id: str
    version: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "template_id",
            _normalize_identifier("template_id", self.template_id),
        )
        object.__setattr__(
            self, "version", _normalize_identifier("version", self.version)
        )

    def canonical_dict(self) -> dict[str, str]:
        return {"template_id": self.template_id, "version": self.version}


@dataclass(frozen=True, slots=True)
class PromptDefinition:
    ref: PromptTemplateRef
    template_text: str
    variables: tuple[str, ...] | Iterable[str] = ()
    metadata: (
        tuple[tuple[str, str], ...]
        | Mapping[str, str]
        | Iterable[tuple[str, str]]
    ) = ()

    def __post_init__(self) -> None:
        if not isinstance(self.ref, PromptTemplateRef):
            _raise(
                ModelDomainErrorCode.INVALID_PROMPT_DEFINITION,
                "ref must be a PromptTemplateRef",
            )
        if not isinstance(self.template_text, str) or not self.template_text.strip():
            _raise(
                ModelDomainErrorCode.INVALID_PROMPT_DEFINITION,
                "template_text must be nonempty",
            )
        if _domain_byte_length(
            "template_text",
            self.template_text,
            ModelDomainErrorCode.INVALID_PROMPT_DEFINITION,
        ) > MAX_TEMPLATE_BYTES:
            _raise(
                ModelDomainErrorCode.INVALID_PROMPT_DEFINITION,
                f"template_text exceeds {MAX_TEMPLATE_BYTES} bytes",
            )
        object.__setattr__(
            self,
            "variables",
            _normalize_names(
                self.variables,
                code=ModelDomainErrorCode.INVALID_PROMPT_DEFINITION,
                maximum=MAX_TEMPLATE_VARIABLES,
                label="declared variable",
            ),
        )
        object.__setattr__(self, "metadata", _normalize_metadata(self.metadata))

    def _semantic_dict(self) -> dict[str, object]:
        return {
            "metadata": dict(self.metadata),
            "template_text": self.template_text,
            "variables": list(self.variables),
        }

    @property
    def content_digest(self) -> str:
        return hashlib.sha256(
            _canonical_json(self._semantic_dict()).encode("utf-8")
        ).hexdigest()

    def canonical_dict(self) -> dict[str, object]:
        return {
            "content_digest": self.content_digest,
            "metadata": dict(self.metadata),
            "ref": self.ref.canonical_dict(),
            "template_text": self.template_text,
            "variables": list(self.variables),
        }

    def canonical_json(self) -> str:
        return _canonical_json(self.canonical_dict())


@dataclass(frozen=True, slots=True, init=False)
class PromptRegistry:
    _entries: tuple[PromptDefinition, ...]

    def __init__(self, *args: object, **kwargs: object) -> None:
        _raise(
            ModelDomainErrorCode.INVALID_PROMPT_DEFINITION,
            "PromptRegistry must be created with PromptRegistry.build",
        )

    @classmethod
    def build(cls, entries: Iterable[PromptDefinition]) -> PromptRegistry:
        if isinstance(entries, (str, bytes)):
            _raise(
                ModelDomainErrorCode.INVALID_PROMPT_DEFINITION,
                "registry entries must be prompt definitions",
            )
        try:
            supplied = tuple(entries)
        except TypeError:
            _raise(
                ModelDomainErrorCode.INVALID_PROMPT_DEFINITION,
                "registry entries must be iterable",
            )
        if len(supplied) > MAX_REGISTRY_ENTRIES:
            _raise(
                ModelDomainErrorCode.INVALID_PROMPT_DEFINITION,
                f"registry exceeds {MAX_REGISTRY_ENTRIES} entries",
            )
        by_ref: dict[PromptTemplateRef, PromptDefinition] = {}
        for definition in supplied:
            if not isinstance(definition, PromptDefinition):
                _raise(
                    ModelDomainErrorCode.INVALID_PROMPT_DEFINITION,
                    "registry entries must be PromptDefinition values",
                )
            previous = by_ref.get(definition.ref)
            if previous is not None:
                if previous != definition:
                    _raise(
                        ModelDomainErrorCode.PROMPT_VERSION_CONFLICT,
                        f"conflicting prompt identity {definition.ref.template_id}@{definition.ref.version}",
                    )
                continue
            by_ref[definition.ref] = definition
        ordered = tuple(
            sorted(
                by_ref.values(),
                key=lambda entry: (entry.ref.template_id, entry.ref.version),
            )
        )
        registry = object.__new__(cls)
        object.__setattr__(registry, "_entries", ordered)
        return registry

    @property
    def entries(self) -> tuple[PromptDefinition, ...]:
        return self._validated_entries()

    def lookup(self, ref: PromptTemplateRef) -> PromptDefinition:
        if not isinstance(ref, PromptTemplateRef):
            _raise(
                ModelDomainErrorCode.PROMPT_NOT_FOUND,
                "prompt reference must be a PromptTemplateRef",
            )
        for entry in self._validated_entries():
            if entry.ref == ref:
                return entry
        _raise(
            ModelDomainErrorCode.PROMPT_NOT_FOUND,
            f"prompt {ref.template_id}@{ref.version} is not registered",
        )

    def canonical_json(self) -> str:
        return _canonical_json(
            {"entries": [entry.canonical_dict() for entry in self._validated_entries()]}
        )

    def _validated_entries(self) -> tuple[PromptDefinition, ...]:
        try:
            entries = self._entries
        except AttributeError:
            _raise(
                ModelDomainErrorCode.INVALID_PROMPT_DEFINITION,
                "registry has no validated entries",
            )
        return PromptRegistry.build(entries)._entries


@dataclass(frozen=True, slots=True, init=False)
class PromptVariables:
    items: tuple[tuple[str, str], ...]

    def __init__(self, *args: object, **kwargs: object) -> None:
        _raise(
            ModelDomainErrorCode.INVALID_MODEL_REQUEST,
            "PromptVariables must be created with PromptVariables.build",
        )

    @classmethod
    def build(
        cls, values: Mapping[str, str] | Iterable[tuple[str, str]]
    ) -> PromptVariables:
        pairs = _pairs(values, ModelDomainErrorCode.INVALID_MODEL_REQUEST)
        if len(pairs) > MAX_TEMPLATE_VARIABLES:
            _raise(
                ModelDomainErrorCode.INVALID_MODEL_REQUEST,
                f"variable count exceeds {MAX_TEMPLATE_VARIABLES}",
            )
        normalized: dict[str, str] = {}
        total = 0
        for raw_name, value in pairs:
            name = _normalize_variable_name(
                raw_name, ModelDomainErrorCode.INVALID_MODEL_REQUEST
            )
            if name in normalized:
                _raise(
                    ModelDomainErrorCode.INVALID_MODEL_REQUEST,
                    f"duplicate variable {name}",
                )
            if not isinstance(value, str):
                _raise(
                    ModelDomainErrorCode.INVALID_MODEL_REQUEST,
                    f"variable {name} value must be a string",
                )
            size = _domain_byte_length(
                f"variable {name}",
                value,
                ModelDomainErrorCode.INVALID_MODEL_REQUEST,
            )
            if size > MAX_VARIABLE_VALUE_BYTES:
                _raise(
                    ModelDomainErrorCode.INVALID_MODEL_REQUEST,
                    f"variable {name} exceeds {MAX_VARIABLE_VALUE_BYTES} bytes",
                )
            total += _byte_length(name) + size
            if total > MAX_VARIABLE_PAYLOAD_BYTES:
                _raise(
                    ModelDomainErrorCode.INVALID_MODEL_REQUEST,
                    f"variable payload exceeds {MAX_VARIABLE_PAYLOAD_BYTES} bytes",
                )
            normalized[name] = value
        prompt_variables = object.__new__(cls)
        object.__setattr__(
            prompt_variables, "items", tuple(sorted(normalized.items()))
        )
        return prompt_variables

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(name for name, _ in self._validated_items())

    def canonical_dict(self) -> dict[str, str]:
        return dict(self._validated_items())

    def _validated_items(self) -> tuple[tuple[str, str], ...]:
        try:
            items = self.items
        except AttributeError:
            _raise(
                ModelDomainErrorCode.INVALID_MODEL_REQUEST,
                "variables have no validated items",
            )
        return PromptVariables.build(items).items


@dataclass(frozen=True, slots=True)
class ModelBudget:
    max_input_tokens: int
    max_output_tokens: int
    retry_budget: int = 0
    max_latency_ms: int | None = None

    def __post_init__(self) -> None:
        _bounded_integer(
            "max_input_tokens",
            self.max_input_tokens,
            minimum=1,
            maximum=MAX_INPUT_TOKENS,
        )
        _bounded_integer(
            "max_output_tokens",
            self.max_output_tokens,
            minimum=1,
            maximum=MAX_OUTPUT_TOKENS,
        )
        _bounded_integer(
            "retry_budget",
            self.retry_budget,
            minimum=0,
            maximum=MAX_RETRY_BUDGET,
        )
        if self.max_latency_ms is not None:
            _bounded_integer(
                "max_latency_ms",
                self.max_latency_ms,
                minimum=1,
                maximum=MAX_LATENCY_MS,
            )

    def canonical_dict(self) -> dict[str, int | None]:
        return {
            "max_input_tokens": self.max_input_tokens,
            "max_latency_ms": self.max_latency_ms,
            "max_output_tokens": self.max_output_tokens,
            "retry_budget": self.retry_budget,
        }


@dataclass(frozen=True, slots=True)
class StructuredField:
    name: str
    field_type: StructuredFieldType
    required: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "name",
            _normalize_variable_name(
                self.name, ModelDomainErrorCode.INVALID_STRUCTURED_SCHEMA
            ),
        )
        if not isinstance(self.field_type, StructuredFieldType):
            _raise(
                ModelDomainErrorCode.INVALID_STRUCTURED_SCHEMA,
                f"field {self.name} has an invalid type",
            )
        if type(self.required) is not bool:
            _raise(
                ModelDomainErrorCode.INVALID_STRUCTURED_SCHEMA,
                f"field {self.name} required must be a bool",
            )


@dataclass(frozen=True, slots=True)
class StructuredOutputSchema:
    fields: tuple[StructuredField, ...] | Iterable[StructuredField]
    allow_additional_fields: bool = False

    def __post_init__(self) -> None:
        if type(self.allow_additional_fields) is not bool:
            _raise(
                ModelDomainErrorCode.INVALID_STRUCTURED_SCHEMA,
                "allow_additional_fields must be a bool",
            )
        if isinstance(self.fields, (str, bytes)):
            _raise(
                ModelDomainErrorCode.INVALID_STRUCTURED_SCHEMA,
                "fields must be StructuredField values",
            )
        try:
            supplied = tuple(self.fields)
        except TypeError:
            _raise(
                ModelDomainErrorCode.INVALID_STRUCTURED_SCHEMA,
                "fields must be iterable",
            )
        if len(supplied) > MAX_SCHEMA_FIELDS:
            _raise(
                ModelDomainErrorCode.INVALID_STRUCTURED_SCHEMA,
                f"field count exceeds {MAX_SCHEMA_FIELDS}",
            )
        names: set[str] = set()
        for field in supplied:
            if not isinstance(field, StructuredField):
                _raise(
                    ModelDomainErrorCode.INVALID_STRUCTURED_SCHEMA,
                    "fields must be StructuredField values",
                )
            if field.name in names:
                _raise(
                    ModelDomainErrorCode.INVALID_STRUCTURED_SCHEMA,
                    f"duplicate field {field.name}",
                )
            names.add(field.name)
        object.__setattr__(
            self, "fields", tuple(sorted(supplied, key=lambda field: field.name))
        )

    def canonical_dict(self) -> dict[str, object]:
        return {
            "allow_additional_fields": self.allow_additional_fields,
            "fields": [
                {
                    "name": field.name,
                    "required": field.required,
                    "type": field.field_type.value,
                }
                for field in self.fields
            ],
        }

    def canonical_json(self) -> str:
        return _canonical_json(self.canonical_dict())


@dataclass(frozen=True, slots=True)
class StructuredValidationResult:
    status: StructuredValidationStatus
    field: str | None = None
    detail: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, StructuredValidationStatus):
            _invalid_result("status must be a StructuredValidationStatus")
        if self.status == StructuredValidationStatus.VALID:
            if self.field is not None or self.detail is not None:
                _invalid_result("VALID structured output cannot carry an error")
            return
        object.__setattr__(
            self,
            "detail",
            _normalize_bounded_text(
                "detail",
                self.detail,
                1_024,
                ModelDomainErrorCode.INVALID_RESULT_SHAPE,
            ),
        )
        if self.field is not None:
            if not isinstance(self.field, str):
                _invalid_result("structured validation field must be a string")
            try:
                field_size = _byte_length(self.field)
            except UnicodeEncodeError:
                _invalid_result("structured validation field contains invalid Unicode")
            if field_size > MAX_STRUCTURED_OUTPUT_BYTES:
                _invalid_result("structured validation field exceeds the output bound")
        if self.status in {
            StructuredValidationStatus.MISSING_REQUIRED_FIELD,
            StructuredValidationStatus.UNEXPECTED_FIELD,
        } and self.field is None:
            _invalid_result(f"{self.status.value} requires a field")


@dataclass(frozen=True, slots=True)
class ModelRequest:
    model: ModelIdentity
    prompt: PromptTemplateRef
    variables: PromptVariables | Mapping[str, str] | Iterable[tuple[str, str]]
    budget: ModelBudget
    output_schema: StructuredOutputSchema | None = None
    correlation_ref: str | None = None
    provenance_ref: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.model, ModelIdentity):
            _raise(
                ModelDomainErrorCode.INVALID_MODEL_REQUEST,
                "model must be a ModelIdentity",
            )
        if not isinstance(self.prompt, PromptTemplateRef):
            _raise(
                ModelDomainErrorCode.INVALID_MODEL_REQUEST,
                "prompt must be a PromptTemplateRef",
            )
        source = (
            self.variables._validated_items()
            if isinstance(self.variables, PromptVariables)
            else self.variables
        )
        object.__setattr__(self, "variables", PromptVariables.build(source))
        if not isinstance(self.budget, ModelBudget):
            _raise(
                ModelDomainErrorCode.INVALID_MODEL_REQUEST,
                "budget must be a ModelBudget",
            )
        if self.output_schema is not None and not isinstance(
            self.output_schema, StructuredOutputSchema
        ):
            _raise(
                ModelDomainErrorCode.INVALID_MODEL_REQUEST,
                "output_schema must be a StructuredOutputSchema",
            )
        for name in ("correlation_ref", "provenance_ref"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(
                    self,
                    name,
                    _normalize_bounded_text(
                        name,
                        value,
                        255,
                        ModelDomainErrorCode.INVALID_MODEL_REQUEST,
                    ),
                )

    def canonical_dict(self) -> dict[str, object]:
        variables = self.variables
        assert isinstance(variables, PromptVariables)
        return {
            "budget": self.budget.canonical_dict(),
            "correlation_ref": self.correlation_ref,
            "model": self.model.canonical_dict(),
            "output_schema": (
                self.output_schema.canonical_dict()
                if self.output_schema is not None
                else None
            ),
            "prompt": self.prompt.canonical_dict(),
            "provenance_ref": self.provenance_ref,
            "variables": variables.canonical_dict(),
        }

    def canonical_json(self) -> str:
        return _canonical_json(self.canonical_dict())


@dataclass(frozen=True, slots=True)
class ModelResult:
    status: ModelResultStatus
    output_text: str | None = None
    refusal_reason: str | None = None
    failure_class: ModelFailureClass | None = None
    structured_validation: StructuredValidationResult | None = None
    detail: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, ModelResultStatus):
            _invalid_result("status must be a ModelResultStatus")
        if self.detail is not None:
            object.__setattr__(
                self,
                "detail",
                _normalize_bounded_text(
                    "detail",
                    self.detail,
                    1_024,
                    ModelDomainErrorCode.INVALID_RESULT_SHAPE,
                ),
            )

        if self.status == ModelResultStatus.SUCCESS:
            if not isinstance(self.output_text, str):
                _invalid_result("SUCCESS requires output_text")
            if _domain_byte_length(
                "SUCCESS output_text",
                self.output_text,
                ModelDomainErrorCode.INVALID_RESULT_SHAPE,
            ) > MAX_STRUCTURED_OUTPUT_BYTES:
                _invalid_result("SUCCESS output_text exceeds the output bound")
            if self.refusal_reason is not None or self.failure_class is not None:
                _invalid_result("SUCCESS cannot carry refusal or provider failure")
            if self.structured_validation is not None and (
                not isinstance(
                    self.structured_validation, StructuredValidationResult
                )
                or self.structured_validation.status
                != StructuredValidationStatus.VALID
            ):
                _invalid_result("SUCCESS structured validation must be VALID")
            return

        if self.output_text is not None:
            _invalid_result(f"{self.status.value} cannot carry output_text")
        if self.status == ModelResultStatus.REFUSAL:
            object.__setattr__(
                self,
                "refusal_reason",
                _normalize_bounded_text(
                    "refusal_reason",
                    self.refusal_reason,
                    1_024,
                    ModelDomainErrorCode.INVALID_RESULT_SHAPE,
                ),
            )
            if self.failure_class is not None or self.structured_validation is not None:
                _invalid_result("REFUSAL cannot carry provider or schema failure")
            return
        if self.status == ModelResultStatus.PROVIDER_OR_MODEL_FAILURE:
            if not isinstance(self.failure_class, ModelFailureClass):
                _invalid_result(
                    "PROVIDER_OR_MODEL_FAILURE requires a failure_class"
                )
            if self.refusal_reason is not None or self.structured_validation is not None:
                _invalid_result("provider failure cannot carry refusal or schema failure")
            return
        if self.status == ModelResultStatus.INVALID_STRUCTURED_OUTPUT:
            if (
                not isinstance(
                    self.structured_validation, StructuredValidationResult
                )
                or self.structured_validation.status
                == StructuredValidationStatus.VALID
            ):
                _invalid_result(
                    "INVALID_STRUCTURED_OUTPUT requires a non-VALID validation"
                )
            if self.refusal_reason is not None or self.failure_class is not None:
                _invalid_result("structured failure cannot carry refusal or provider failure")
            return
        if any(
            value is not None
            for value in (
                self.refusal_reason,
                self.failure_class,
                self.structured_validation,
            )
        ):
            _invalid_result(f"{self.status.value} carries contradictory fields")


def validate_model_request(
    request: ModelRequest, registry: PromptRegistry
) -> PromptDefinition:
    """Return the exact referenced definition or reject the request."""

    if not isinstance(request, ModelRequest):
        _raise(
            ModelDomainErrorCode.INVALID_MODEL_REQUEST,
            "request must be a ModelRequest",
        )
    if not isinstance(registry, PromptRegistry):
        _raise(
            ModelDomainErrorCode.INVALID_MODEL_REQUEST,
            "registry must be a PromptRegistry",
        )
    registry._validated_entries()
    definition = registry.lookup(request.prompt)
    variables = request.variables
    if not isinstance(variables, PromptVariables):
        _raise(
            ModelDomainErrorCode.INVALID_MODEL_REQUEST,
            "request variables must be PromptVariables",
        )
    variables._validated_items()
    expected = set(definition.variables)
    actual = set(variables.names)
    missing = sorted(expected - actual)
    if missing:
        _raise(
            ModelDomainErrorCode.INVALID_MODEL_REQUEST,
            f"missing prompt variable {missing[0]}",
        )
    unexpected = sorted(actual - expected)
    if unexpected:
        _raise(
            ModelDomainErrorCode.INVALID_MODEL_REQUEST,
            f"unexpected prompt variable {unexpected[0]}",
        )
    return definition


def validate_structured_output(
    output: object, schema: StructuredOutputSchema
) -> StructuredValidationResult:
    """Validate JSON object text without provider or external schema behavior."""

    if not isinstance(schema, StructuredOutputSchema):
        raise TypeError("schema must be a StructuredOutputSchema")
    if not isinstance(output, str):
        return _validation(
            StructuredValidationStatus.MALFORMED, "output must be JSON text"
        )
    try:
        output_size = _byte_length(output)
    except UnicodeEncodeError:
        return _validation(
            StructuredValidationStatus.MALFORMED,
            "output contains invalid Unicode",
        )
    if output_size > MAX_STRUCTURED_OUTPUT_BYTES:
        return _validation(
            StructuredValidationStatus.MALFORMED,
            "output exceeds the structured-output bound",
        )
    try:
        parsed = json.loads(
            output,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_json_constant,
            parse_int=_parse_json_integer,
        )
    except (ValueError, UnicodeError, OverflowError, RecursionError):
        return _validation(StructuredValidationStatus.MALFORMED, "invalid JSON")
    issue = _parsed_json_issue(parsed)
    if issue == "invalid Unicode":
        return _validation(StructuredValidationStatus.MALFORMED, issue)
    if issue is not None:
        return _validation(StructuredValidationStatus.SCHEMA_MISMATCH, issue)
    if not isinstance(parsed, dict):
        return _validation(
            StructuredValidationStatus.SCHEMA_MISMATCH,
            "expected an object root",
        )

    expected = {field.name: field for field in schema.fields}
    for field in schema.fields:
        if field.required and field.name not in parsed:
            return _validation(
                StructuredValidationStatus.MISSING_REQUIRED_FIELD,
                f"missing required field {field.name}",
                field.name,
            )
    if not schema.allow_additional_fields:
        unexpected = sorted(set(parsed) - set(expected))
        if unexpected:
            name = unexpected[0]
            return _validation(
                StructuredValidationStatus.UNEXPECTED_FIELD,
                "unexpected field",
                name,
            )
    for name in sorted(set(parsed) & set(expected)):
        if not _matches_type(parsed[name], expected[name].field_type):
            return _validation(
                StructuredValidationStatus.SCHEMA_MISMATCH,
                f"field {name} must be {expected[name].field_type.value}",
                name,
            )
    return StructuredValidationResult(StructuredValidationStatus.VALID)


def _normalize_identifier(name: str, value: object) -> str:
    normalized = _normalize_bounded_text(
        name,
        value,
        MAX_IDENTIFIER_LENGTH,
        ModelDomainErrorCode.INVALID_IDENTITY,
    )
    if _IDENTIFIER.fullmatch(normalized) is None:
        _raise(
            ModelDomainErrorCode.INVALID_IDENTITY,
            f"{name} contains invalid characters",
        )
    return normalized


def _normalize_variable_name(
    value: object, code: ModelDomainErrorCode
) -> str:
    normalized = _normalize_bounded_text(
        "variable name", value, 64, code
    )
    if _VARIABLE_NAME.fullmatch(normalized) is None:
        _raise(code, f"invalid variable name {normalized}")
    return normalized


def _normalize_names(
    values: Iterable[str],
    *,
    code: ModelDomainErrorCode,
    maximum: int,
    label: str,
) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        _raise(code, f"{label}s must be an iterable of names")
    try:
        supplied = tuple(values)
    except TypeError:
        _raise(code, f"{label}s must be iterable")
    if len(supplied) > maximum:
        _raise(code, f"{label} count exceeds {maximum}")
    normalized: set[str] = set()
    for value in supplied:
        name = _normalize_variable_name(value, code)
        if name in normalized:
            _raise(code, f"duplicate {label} {name}")
        normalized.add(name)
    return tuple(sorted(normalized))


def _normalize_metadata(
    values: Mapping[str, str] | Iterable[tuple[str, str]],
) -> tuple[tuple[str, str], ...]:
    pairs = _pairs(values, ModelDomainErrorCode.INVALID_PROMPT_DEFINITION)
    if len(pairs) > MAX_METADATA_ENTRIES:
        _raise(
            ModelDomainErrorCode.INVALID_PROMPT_DEFINITION,
            f"metadata count exceeds {MAX_METADATA_ENTRIES}",
        )
    normalized: dict[str, str] = {}
    total = 0
    for raw_name, value in pairs:
        name = _normalize_variable_name(
            raw_name, ModelDomainErrorCode.INVALID_PROMPT_DEFINITION
        )
        if name in normalized:
            _raise(
                ModelDomainErrorCode.INVALID_PROMPT_DEFINITION,
                f"duplicate metadata key {name}",
            )
        if not isinstance(value, str):
            _raise(
                ModelDomainErrorCode.INVALID_PROMPT_DEFINITION,
                f"metadata {name} value must be a string",
            )
        size = _domain_byte_length(
            f"metadata {name}",
            value,
            ModelDomainErrorCode.INVALID_PROMPT_DEFINITION,
        )
        if size > MAX_METADATA_VALUE_BYTES:
            _raise(
                ModelDomainErrorCode.INVALID_PROMPT_DEFINITION,
                f"metadata {name} exceeds {MAX_METADATA_VALUE_BYTES} bytes",
            )
        total += _byte_length(name) + size
        if total > MAX_METADATA_PAYLOAD_BYTES:
            _raise(
                ModelDomainErrorCode.INVALID_PROMPT_DEFINITION,
                f"metadata payload exceeds {MAX_METADATA_PAYLOAD_BYTES} bytes",
            )
        normalized[name] = value
    return tuple(sorted(normalized.items()))


def _pairs(
    values: Mapping[str, str] | Iterable[tuple[str, str]],
    code: ModelDomainErrorCode,
) -> tuple[tuple[object, object], ...]:
    source: object = values.items() if isinstance(values, Mapping) else values
    if isinstance(source, (str, bytes)):
        _raise(code, "expected name/value pairs")
    try:
        pairs = tuple(source)  # type: ignore[arg-type]
    except TypeError:
        _raise(code, "expected iterable name/value pairs")
    for pair in pairs:
        if not isinstance(pair, (tuple, list)) or len(pair) != 2:
            _raise(code, "expected name/value pairs")
    return tuple((pair[0], pair[1]) for pair in pairs)


def _normalize_bounded_text(
    name: str,
    value: object,
    maximum: int,
    code: ModelDomainErrorCode,
) -> str:
    if not isinstance(value, str):
        _raise(code, f"{name} must be a string")
    normalized = value.strip()
    if not normalized:
        _raise(code, f"{name} must be nonempty")
    try:
        size = _byte_length(normalized)
    except UnicodeEncodeError:
        _raise(code, f"{name} contains invalid Unicode")
    if size > maximum:
        _raise(code, f"{name} exceeds {maximum} bytes")
    return normalized


def _bounded_integer(
    name: str, value: object, *, minimum: int, maximum: int
) -> None:
    if type(value) is not int or not minimum <= value <= maximum:
        _raise(
            ModelDomainErrorCode.INVALID_MODEL_BUDGET,
            f"{name} must be an integer from {minimum} to {maximum}",
        )


def _matches_type(value: object, expected: StructuredFieldType) -> bool:
    if expected == StructuredFieldType.STRING:
        return isinstance(value, str)
    if expected == StructuredFieldType.INTEGER:
        return type(value) is int
    if expected == StructuredFieldType.NUMBER:
        return type(value) is int or (
            type(value) is float and math.isfinite(value)
        )
    if expected == StructuredFieldType.BOOLEAN:
        return type(value) is bool
    if expected == StructuredFieldType.OBJECT:
        return isinstance(value, dict)
    return isinstance(value, list)


class _InvalidJsonValue(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for name, value in pairs:
        if name in result:
            raise _InvalidJsonValue
        result[name] = value
    return result


def _reject_json_constant(_: str) -> None:
    raise _InvalidJsonValue


def _parse_json_integer(value: str) -> int:
    # ponytail: CPython's 4,300-digit safety ceiling; add explicit numeric schema
    # bounds if larger integers become a domain requirement.
    if len(value.removeprefix("-")) > 4_300:
        raise _InvalidJsonValue
    try:
        return int(value)
    except ValueError:
        raise _InvalidJsonValue from None


def _parsed_json_issue(value: object) -> str | None:
    pending = [value]
    while pending:
        current = pending.pop()
        if type(current) is float and not math.isfinite(current):
            return "non-finite numbers are not valid structured output"
        if isinstance(current, str):
            try:
                current.encode("utf-8")
            except UnicodeEncodeError:
                return "invalid Unicode"
        elif isinstance(current, dict):
            pending.extend(current.keys())
            pending.extend(current.values())
        elif isinstance(current, list):
            pending.extend(current)
    return None


def _validation(
    status: StructuredValidationStatus,
    detail: str,
    field: str | None = None,
) -> StructuredValidationResult:
    return StructuredValidationResult(status, field, detail)


def _invalid_result(detail: str) -> NoReturn:
    _raise(ModelDomainErrorCode.INVALID_RESULT_SHAPE, detail)


def _raise(code: ModelDomainErrorCode, detail: str) -> NoReturn:
    raise ModelDomainError(code, detail)


def _byte_length(value: str) -> int:
    return len(value.encode("utf-8"))


def _domain_byte_length(
    name: str, value: str, code: ModelDomainErrorCode
) -> int:
    try:
        return _byte_length(value)
    except UnicodeEncodeError:
        _raise(code, f"{name} contains invalid Unicode")


def _canonical_json(value: object) -> str:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
