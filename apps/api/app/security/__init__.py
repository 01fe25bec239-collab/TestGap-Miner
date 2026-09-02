"""Public Security foundation API for prompt and untrusted-content defense.

Security-owned, provider-neutral utilities implementing the structural
instruction/data boundary, trust-labelled untrusted content, bounded security
contexts, immutable tool/action allowlists, structured-output rejection
semantics, and redaction-safe derived text. Detection is defense-in-depth;
structural authorization never depends on keyword matching.
"""

from .redaction import (
    MAX_REDACTION_INPUT_BYTES,
    RedactionOutcome,
    RedactionResult,
    SecretFinding,
    SecretKind,
    SecretScanResult,
    redact_text,
    scan_text,
)
from .tool_policy import (
    MAX_ACTION_NAME_LENGTH,
    MAX_ACTIONS_PER_TOOL,
    MAX_PATH_BYTES,
    MAX_POLICY_ID_LENGTH,
    MAX_REQUEST_PATHS,
    MAX_SCOPES_PER_TOOL,
    MAX_TOOLS,
    MAX_TOOL_NAME_LENGTH,
    ROOT_SCOPE,
    CapabilityRequest,
    ToolActionScope,
    ToolAuthorizationDecision,
    ToolPolicy,
    evaluate_capability_request,
    validate_repository_relative_path,
)
from .untrusted_content import (
    MAX_CONTENT_BYTES,
    MAX_DETAIL_BYTES,
    MAX_FINDINGS,
    MAX_IDENTIFIER_LENGTH,
    MAX_INSTRUCTIONS,
    MAX_INSTRUCTION_BYTES,
    MAX_ITEMS,
    MAX_MODEL_FACING_BYTES,
    MAX_PROVENANCE_REF_LENGTH,
    MAX_TOTAL_BYTES,
    ContentSourceKind,
    HiddenCharacterCategory,
    HiddenCharacterHit,
    InjectionSignal,
    InjectionSignalKind,
    ModelFacingContextView,
    SecurityContext,
    SecurityError,
    SecurityErrorCode,
    TrustedInstruction,
    UntrustedAnalysisResult,
    UntrustedContent,
    UntrustedContentTrust,
    analyze_untrusted_content,
    bounded_detail,
    find_hidden_characters,
    hidden_character_category,
    render_inert_text,
    untrusted_content_from_rag_context_item,
    untrusted_trust_from_rag_label,
)

_STRUCTURED_OUTPUT_EXPORTS = frozenset(
    {
        "MAX_CONTROL_SCAN_DEPTH",
        "MAX_CONTROL_SCAN_NODES",
        "StructuredOutputSecurityResult",
        "validate_model_action_output",
    }
)


def __getattr__(name: str) -> object:
    if name not in _STRUCTURED_OUTPUT_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from importlib import import_module

    value = getattr(import_module(".structured_output", __name__), name)
    globals()[name] = value
    return value


__all__ = [
    "MAX_ACTION_NAME_LENGTH",
    "MAX_ACTIONS_PER_TOOL",
    "MAX_CONTROL_SCAN_DEPTH",
    "MAX_CONTROL_SCAN_NODES",
    "MAX_CONTENT_BYTES",
    "MAX_DETAIL_BYTES",
    "MAX_FINDINGS",
    "MAX_IDENTIFIER_LENGTH",
    "MAX_INSTRUCTIONS",
    "MAX_INSTRUCTION_BYTES",
    "MAX_ITEMS",
    "MAX_MODEL_FACING_BYTES",
    "MAX_PATH_BYTES",
    "MAX_POLICY_ID_LENGTH",
    "MAX_PROVENANCE_REF_LENGTH",
    "MAX_REDACTION_INPUT_BYTES",
    "MAX_REQUEST_PATHS",
    "MAX_SCOPES_PER_TOOL",
    "MAX_TOOLS",
    "MAX_TOOL_NAME_LENGTH",
    "MAX_TOTAL_BYTES",
    "ROOT_SCOPE",
    "CapabilityRequest",
    "ContentSourceKind",
    "HiddenCharacterCategory",
    "HiddenCharacterHit",
    "InjectionSignal",
    "InjectionSignalKind",
    "ModelFacingContextView",
    "RedactionOutcome",
    "RedactionResult",
    "SecretFinding",
    "SecretKind",
    "SecretScanResult",
    "SecurityContext",
    "SecurityError",
    "SecurityErrorCode",
    "StructuredOutputSecurityResult",
    "ToolActionScope",
    "ToolAuthorizationDecision",
    "ToolPolicy",
    "TrustedInstruction",
    "UntrustedAnalysisResult",
    "UntrustedContent",
    "UntrustedContentTrust",
    "analyze_untrusted_content",
    "bounded_detail",
    "evaluate_capability_request",
    "find_hidden_characters",
    "hidden_character_category",
    "redact_text",
    "render_inert_text",
    "scan_text",
    "untrusted_content_from_rag_context_item",
    "untrusted_trust_from_rag_label",
    "validate_model_action_output",
    "validate_repository_relative_path",
]
