import subprocess
import sys
from pathlib import Path


API_ROOT = Path(__file__).parents[2] / "apps" / "api"


def run_fresh_python(program: str) -> None:
    completed = subprocess.run(
        [sys.executable, "-c", program],
        cwd=API_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


WORKFLOW_UNLOADED = """
import sys
assert "app.workflow" not in sys.modules
assert not any(name.startswith("app.workflow.") for name in sys.modules)
"""


def test_package_import_is_workflow_neutral() -> None:
    run_fresh_python("import app.security\n" + WORKFLOW_UNLOADED)


def test_rag_needed_package_exports_are_workflow_neutral() -> None:
    run_fresh_python(
        """
from app.security import (
    ModelFacingContextView,
    SecurityContext,
    UntrustedAnalysisResult,
    UntrustedContent,
    analyze_untrusted_content,
    untrusted_content_from_rag_context_item,
)
"""
        + WORKFLOW_UNLOADED
    )


def test_untrusted_content_submodule_import_is_workflow_neutral() -> None:
    run_fresh_python("import app.security.untrusted_content\n" + WORKFLOW_UNLOADED)


def test_redaction_behavior_is_workflow_neutral() -> None:
    run_fresh_python(
        """
from app.security import RedactionOutcome, redact_text

result = redact_text("password=hunter2")
assert result.outcome is RedactionOutcome.REDACTED_CLEAN
assert result.safe_text == "[REDACTED:ASSIGNMENT_SECRET]"
"""
        + WORKFLOW_UNLOADED
    )


def test_untrusted_content_behavior_is_workflow_neutral() -> None:
    run_fresh_python(
        """
from app.security import (
    ContentSourceKind,
    UntrustedContent,
    UntrustedContentTrust,
    analyze_untrusted_content,
)

content = UntrustedContent(
    content_id="content-1",
    trust_label=UntrustedContentTrust.UNTRUSTED_REPOSITORY_TEXT,
    source_kind=ContentSourceKind.REPOSITORY_SOURCE,
    content="ordinary repository evidence",
)
result = analyze_untrusted_content(content)
assert result.content_id == "content-1"
assert result.flagged is False
"""
        + WORKFLOW_UNLOADED
    )


def test_structured_output_exports_are_lazy_compatible_cached_and_operational() -> None:
    run_fresh_python(
        """
import sys
import app.security as security

names = (
    "MAX_CONTROL_SCAN_DEPTH",
    "MAX_CONTROL_SCAN_NODES",
    "StructuredOutputSecurityResult",
    "validate_model_action_output",
)
assert "app.security.structured_output" not in sys.modules
assert "app.workflow" not in sys.modules

from app.security import (
    MAX_CONTROL_SCAN_DEPTH,
    MAX_CONTROL_SCAN_NODES,
    StructuredOutputSecurityResult,
    validate_model_action_output,
)
from app.security import structured_output
from app.workflow.model_domain import (
    StructuredField,
    StructuredFieldType,
    StructuredOutputSchema,
)

resolved = (
    MAX_CONTROL_SCAN_DEPTH,
    MAX_CONTROL_SCAN_NODES,
    StructuredOutputSecurityResult,
    validate_model_action_output,
)
for name, value in zip(names, resolved, strict=True):
    assert value is getattr(structured_output, name)
    assert value is getattr(security, name)
    assert security.__dict__[name] is value

schema = StructuredOutputSchema(
    (StructuredField("answer", StructuredFieldType.STRING),),
    allow_additional_fields=False,
)
result = validate_model_action_output('{"answer":"ok"}', schema)
assert isinstance(result, StructuredOutputSecurityResult)
assert result.accepted is True
"""
    )


def test_unknown_attribute_and_all_remain_compatible_and_neutral() -> None:
    run_fresh_python(
        """
import app.security as security

structured_names = {
    "MAX_CONTROL_SCAN_DEPTH",
    "MAX_CONTROL_SCAN_NODES",
    "StructuredOutputSecurityResult",
    "validate_model_action_output",
}
ordinary_names = {
    "ModelFacingContextView",
    "SecurityContext",
    "SecurityError",
    "UntrustedAnalysisResult",
    "UntrustedContent",
    "analyze_untrusted_content",
    "redact_text",
    "untrusted_content_from_rag_context_item",
}
assert structured_names | ordinary_names <= set(security.__all__)
try:
    security.not_a_public_security_export
except AttributeError as error:
    assert "not_a_public_security_export" in str(error)
else:
    raise AssertionError("unknown package attribute did not raise AttributeError")
"""
        + WORKFLOW_UNLOADED
    )
