"""Security boundary over Workflow-owned structured-output validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Final

from app.security.untrusted_content import (
    SecurityError,
    SecurityErrorCode,
    bounded_detail,
)
from app.workflow.model_domain import (
    StructuredOutputSchema,
    StructuredValidationResult,
    StructuredValidationStatus,
    validate_structured_output,
)


MAX_CONTROL_SCAN_DEPTH: Final = 32
MAX_CONTROL_SCAN_NODES: Final = 4_096

_RESERVED_CONTROL_PLANE_KEYS: Final[dict[str, SecurityErrorCode]] = {
    "system_policy": SecurityErrorCode.UNTRUSTED_POLICY_MUTATION,
    "developer_policy": SecurityErrorCode.UNTRUSTED_POLICY_MUTATION,
    "tool_permissions": SecurityErrorCode.UNTRUSTED_POLICY_MUTATION,
    "allowed_paths": SecurityErrorCode.UNTRUSTED_POLICY_MUTATION,
    "network": SecurityErrorCode.UNTRUSTED_POLICY_MUTATION,
    "command": SecurityErrorCode.UNTRUSTED_POLICY_MUTATION,
    "credentials": SecurityErrorCode.UNTRUSTED_POLICY_MUTATION,
    "secrets": SecurityErrorCode.UNTRUSTED_POLICY_MUTATION,
    "workflow_state": SecurityErrorCode.WORKFLOW_STATE_MUTATION,
    "rag_budget": SecurityErrorCode.RAG_BUDGET_MUTATION,
}

_CONTROL_PLANE_KEY_CLASSIFICATION: Final[dict[SecurityErrorCode, str]] = {
    SecurityErrorCode.UNTRUSTED_POLICY_MUTATION: "reserved_control_plane_policy",
    SecurityErrorCode.WORKFLOW_STATE_MUTATION: "reserved_workflow_state",
    SecurityErrorCode.RAG_BUDGET_MUTATION: "reserved_rag_budget",
}

_UNTRUSTED_ORIGIN_FIELD_CLASSIFICATION: Final = "untrusted_origin_field"


@dataclass(frozen=True, slots=True)
class StructuredOutputSecurityResult:
    accepted: bool
    workflow_status: StructuredValidationStatus | None = None
    reason: SecurityErrorCode | None = None
    field: str | None = None
    control_plane_key: str | None = None
    detail: str | None = None


class _StrictJsonRejected(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _StrictJsonRejected
        result[key] = value
    return result


def _reject_constant(_: str) -> None:
    raise _StrictJsonRejected


def validate_model_action_output(
    output: object, schema: StructuredOutputSchema
) -> StructuredOutputSecurityResult:
    """Validate model output through Workflow's boundary, then structurally.

    The Workflow-owned ``validate_structured_output`` is consumed unchanged.
    This boundary independently rejects any attempt to introduce reserved
    control-plane authority through nested untrusted object keys, regardless
    of schema conformance. Rejection is structural and never depends on
    keyword scanning of string values.
    """

    if not isinstance(schema, StructuredOutputSchema):
        raise SecurityError(
            SecurityErrorCode.INVALID_SECURITY_INPUT,
            "schema must be a StructuredOutputSchema",
        )
    workflow_result = validate_structured_output(output, schema)
    if not isinstance(output, str):
        return _malformed(workflow_result.status, "structured output must be JSON text")
    try:
        parsed = json.loads(
            output,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (ValueError, RecursionError):
        return _malformed(
            workflow_result.status, "strict parse of structured output failed closed"
        )
    offending = _find_reserved_control_key(parsed)
    if offending is not None:
        key, depth = offending
        return _control_plane_rejection(key, depth, workflow_result.status)
    if workflow_result.status != StructuredValidationStatus.VALID:
        detail = f"workflow structured validation reported {workflow_result.status.value}"
        safe_field = _schema_attributed_field(workflow_result, schema)
        if safe_field is not None:
            detail = f"{detail}; field {safe_field}"
        else:
            detail = (
                f"{detail}; field classification "
                f"{_UNTRUSTED_ORIGIN_FIELD_CLASSIFICATION}"
            )
        return StructuredOutputSecurityResult(
            accepted=False,
            workflow_status=workflow_result.status,
            reason=SecurityErrorCode.MALFORMED_STRUCTURED_OUTPUT,
            field=safe_field,
            detail=bounded_detail(detail),
        )
    return StructuredOutputSecurityResult(
        accepted=True,
        workflow_status=StructuredValidationStatus.VALID,
    )


def _schema_attributed_field(
    workflow_result: StructuredValidationResult, schema: StructuredOutputSchema
) -> str | None:
    """Return the reported field identifier only when schema-attributed.

    Workflow reports attacker-invented keys for UNEXPECTED_FIELD; such
    identifiers are never demonstrably from the trusted schema and are
    replaced by a constant safe classification upstream of this helper.
    """

    field_name = workflow_result.field
    if not isinstance(field_name, str):
        return None
    if workflow_result.status == StructuredValidationStatus.UNEXPECTED_FIELD:
        return None
    if any(field.name == field_name for field in schema.fields):
        return field_name
    return None


def _malformed(
    workflow_status: StructuredValidationStatus, detail: str
) -> StructuredOutputSecurityResult:
    return StructuredOutputSecurityResult(
        accepted=False,
        workflow_status=workflow_status,
        reason=SecurityErrorCode.MALFORMED_STRUCTURED_OUTPUT,
        detail=bounded_detail(detail),
    )


def _control_plane_rejection(
    key: str, depth: int, workflow_status: StructuredValidationStatus
) -> StructuredOutputSecurityResult:
    """Reject reserved control-plane keys without echoing attacker bytes.

    The matched key text is attacker-supplied, so only a stable constant
    classification is surfaced; the key text itself never reaches the result.
    """

    reason = _RESERVED_CONTROL_PLANE_KEYS[key.casefold()]
    del key
    classification = _CONTROL_PLANE_KEY_CLASSIFICATION[reason]
    return StructuredOutputSecurityResult(
        accepted=False,
        workflow_status=workflow_status,
        reason=reason,
        control_plane_key=classification,
        detail=bounded_detail(
            f"reserved key rejected at nesting depth {depth}; "
            f"classification {classification}"
        ),
    )


def _find_reserved_control_key(value: object) -> tuple[str, int] | None:
    pending: list[tuple[object, int]] = [(value, 0)]
    visited = 0
    while pending:
        current, depth = pending.pop()
        visited += 1
        if visited > MAX_CONTROL_SCAN_NODES or depth > MAX_CONTROL_SCAN_DEPTH:
            raise SecurityError(
                SecurityErrorCode.CONTEXT_BOUND_EXCEEDED,
                "structured output exceeds the security scan bound",
            )
        if isinstance(current, dict):
            for key, child in current.items():
                folded = key.casefold() if isinstance(key, str) else ""
                if folded in _RESERVED_CONTROL_PLANE_KEYS:
                    return (key, depth)
                pending.append((child, depth + 1))
        elif isinstance(current, list):
            pending.extend((item, depth + 1) for item in current)
    return None


__all__ = [
    "MAX_CONTROL_SCAN_DEPTH",
    "MAX_CONTROL_SCAN_NODES",
    "StructuredOutputSecurityResult",
    "validate_model_action_output",
]
