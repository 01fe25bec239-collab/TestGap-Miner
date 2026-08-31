"""Security-backed inspection of canonical RAG context bundles."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.retrieval.localisation import ContextBundle
from app.security import (
    ModelFacingContextView,
    SecurityContext,
    UntrustedAnalysisResult,
    UntrustedContent,
    analyze_untrusted_content,
    untrusted_content_from_rag_context_item,
)


_CONTEXT_ID_DOMAIN = b"testgap.rag-006.security-context.v1\x00"


@dataclass(frozen=True, slots=True)
class ContextSafetyInspection:
    """Raw RAG data, advisory findings, and Security's derived safe view."""

    bundle: ContextBundle
    untrusted_items: tuple[UntrustedContent, ...]
    analyses: tuple[UntrustedAnalysisResult, ...]
    model_facing_view: ModelFacingContextView | None


def inspect_context_bundle(bundle: ContextBundle) -> ContextSafetyInspection:
    """Keep repository text in Security's untrusted channel without mutation."""

    items = tuple(untrusted_content_from_rag_context_item(item) for item in bundle.items)
    analyses = tuple(analyze_untrusted_content(item) for item in items)
    view = None
    if items:
        digest = hashlib.sha256(
            _CONTEXT_ID_DOMAIN + bundle.context_bundle_id.value.encode("utf-8")
        ).hexdigest()
        view = SecurityContext(
            context_id=f"rag006-{digest}", instructions=(), untrusted_items=items
        ).model_facing_view()
    return ContextSafetyInspection(bundle, items, analyses, view)
