"""Immutable Evidence-owned bindings from review subjects to durable identities."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, TypeAlias

from app.retrieval import ContextBundleIdentity, ContextItemIdentity

from .artefact import ArtefactId
from .candidate import CandidatePatchId
from .decision import EvidenceBundleId, EvidenceCardId
from .execution import (
    EVIDENCE_CONTRACT_VERSION,
    CandidateVersionId,
    EvidenceComparison,
    ExecutionEvidenceId,
    _Identifier,
)


class TraceabilityLinkId(_Identifier):
    """Caller-supplied Evidence-owned identity for one traceability binding."""


class TraceabilitySubject(StrEnum):
    RATIONALE = "RATIONALE"
    FIELD = "FIELD"
    REFERENCE = "REFERENCE"


_ReviewScope: TypeAlias = EvidenceCardId | EvidenceBundleId
_TraceSource: TypeAlias = (
    EvidenceCardId
    | EvidenceBundleId
    | ExecutionEvidenceId
    | CandidatePatchId
    | CandidateVersionId
    | ArtefactId
    | ContextBundleIdentity
    | ContextItemIdentity
)


_SCOPE_KIND_BY_EXACT_TYPE: Final[dict[type, str]] = {
    EvidenceCardId: "EVIDENCE_CARD",
    EvidenceBundleId: "EVIDENCE_BUNDLE",
}

_SOURCE_KIND_BY_EXACT_TYPE: Final[dict[type, str]] = {
    EvidenceCardId: "EVIDENCE_CARD",
    EvidenceBundleId: "EVIDENCE_BUNDLE",
    ExecutionEvidenceId: "EXECUTION_EVIDENCE",
    CandidatePatchId: "CANDIDATE_PATCH",
    CandidateVersionId: "CANDIDATE_VERSION",
    ArtefactId: "ARTEFACT_REFERENCE",
    ContextBundleIdentity: "CONTEXT_BUNDLE",
    ContextItemIdentity: "CONTEXT_ITEM",
}


def _kind_for(value: object, kinds: dict[type, str], name: str) -> str:
    kind = kinds.get(type(value))
    if kind is None:
        raise TypeError(f"{name} has an unsupported identity type")
    return kind


def _canonical_sources(
    values: Iterable[_TraceSource],
) -> tuple[_TraceSource, ...]:
    if isinstance(values, (str, bytes, bytearray, dict)):
        raise TypeError("sources must be an iterable of supported identity objects")
    try:
        sources = tuple(values)
    except TypeError as error:
        raise TypeError("sources must be iterable") from error
    if not sources:
        raise ValueError("sources must contain at least one identity")

    keyed: list[tuple[str, str, _TraceSource]] = []
    seen: set[tuple[str, str]] = set()
    for source in sources:
        kind = _kind_for(source, _SOURCE_KIND_BY_EXACT_TYPE, "source")
        key = (kind, source.value)
        if key in seen:
            raise ValueError("duplicate traceability source binding")
        seen.add(key)
        keyed.append((kind, source.value, source))
    return tuple(source for _, _, source in sorted(keyed, key=lambda item: item[:2]))


@dataclass(frozen=True, slots=True)
class TraceabilityLink:
    """One immutable review-scope binding to exact durable source identities."""

    traceability_link_id: TraceabilityLinkId
    review_scope: _ReviewScope
    subject: TraceabilitySubject
    sources: tuple[_TraceSource, ...] | Iterable[_TraceSource]
    contract_version: str = EVIDENCE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if type(self.traceability_link_id) is not TraceabilityLinkId:
            raise TypeError("traceability_link_id must be a TraceabilityLinkId")
        _kind_for(self.review_scope, _SCOPE_KIND_BY_EXACT_TYPE, "review_scope")
        if type(self.subject) is not TraceabilitySubject:
            raise TypeError("subject must be a TraceabilitySubject")
        if self.contract_version != EVIDENCE_CONTRACT_VERSION:
            raise ValueError("unsupported Evidence contract version")
        object.__setattr__(self, "sources", _canonical_sources(self.sources))

    @property
    def review_scope_kind(self) -> str:
        return _kind_for(self.review_scope, _SCOPE_KIND_BY_EXACT_TYPE, "review_scope")

    def to_domain_dict(self) -> dict[str, object]:
        return {
            "traceability_link_id": self.traceability_link_id.value,
            "review_scope": {
                "kind": self.review_scope_kind,
                "value": self.review_scope.value,
            },
            "subject": self.subject.value,
            "sources": [
                {
                    "kind": _kind_for(source, _SOURCE_KIND_BY_EXACT_TYPE, "source"),
                    "value": source.value,
                }
                for source in self.sources
            ],
            "contract_version": self.contract_version,
        }

    def to_domain_json(self) -> str:
        return json.dumps(
            self.to_domain_dict(),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )


def compare_traceability_links(
    existing: TraceabilityLink,
    incoming: TraceabilityLink,
) -> EvidenceComparison:
    """Classify convergence without mutating or rebinding either link."""
    if type(existing) is not TraceabilityLink or type(incoming) is not TraceabilityLink:
        raise TypeError("existing and incoming must be TraceabilityLink values")
    if existing.traceability_link_id != incoming.traceability_link_id:
        return EvidenceComparison.DISTINCT_IDENTITY
    if existing.to_domain_json() == incoming.to_domain_json():
        return EvidenceComparison.EQUIVALENT
    return EvidenceComparison.CONFLICTING
