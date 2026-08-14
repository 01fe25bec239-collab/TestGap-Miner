"""Immutable Evidence-domain linkage to historical human review decisions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Final

from .execution import (
    EVIDENCE_CONTRACT_VERSION,
    EvidenceComparison,
    OpaqueReference,
    RunId,
    _Identifier,
    _domain_value,
    _require_optional_type,
    _require_type,
)


MAX_DECISION_REFERENCE_BYTES: Final = 16_384


class HumanDecisionLinkId(_Identifier):
    """Evidence-owned human-decision-link identity."""


class HumanDecisionId(_Identifier):
    """Evidence-owned HumanDecision record identity."""


class EvidenceBundleId(_Identifier):
    """Evidence-owned exact EvidenceBundle version identity."""


class EvidenceCardId(_Identifier):
    """Evidence-owned exact EvidenceCard version identity."""


class DecisionDisposition(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DISMISSED = "DISMISSED"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    REGENERATION_REQUESTED = "REGENERATION_REQUESTED"


@dataclass(frozen=True, slots=True)
class HumanDecisionLink:
    human_decision_link_id: HumanDecisionLinkId
    human_decision_id: HumanDecisionId
    reviewed_evidence_bundle_id: EvidenceBundleId
    reviewed_evidence_card_id: EvidenceCardId
    human_actor_reference: OpaqueReference
    decision_timestamp: datetime
    disposition: DecisionDisposition
    workflow_event_or_result_reference: OpaqueReference
    rationale_reference: OpaqueReference | None = None
    regeneration_child_run_reference: RunId | None = None
    contract_version: str = EVIDENCE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name, expected in (
            ("human_decision_link_id", HumanDecisionLinkId),
            ("human_decision_id", HumanDecisionId),
            ("reviewed_evidence_bundle_id", EvidenceBundleId),
            ("reviewed_evidence_card_id", EvidenceCardId),
            ("human_actor_reference", OpaqueReference),
            ("disposition", DecisionDisposition),
            ("workflow_event_or_result_reference", OpaqueReference),
        ):
            _require_type(getattr(self, name), expected, name)
        _require_optional_type(
            self.rationale_reference,
            OpaqueReference,
            "rationale_reference",
        )
        _require_optional_type(
            self.regeneration_child_run_reference,
            RunId,
            "regeneration_child_run_reference",
        )
        _validate_timestamp(self.decision_timestamp)
        for name in (
            "human_actor_reference",
            "workflow_event_or_result_reference",
        ):
            _validate_reference(getattr(self, name), name)
        if self.rationale_reference is not None:
            _validate_reference(self.rationale_reference, "rationale_reference")
        if self.contract_version != EVIDENCE_CONTRACT_VERSION:
            raise ValueError("unsupported Evidence contract version")
        if self.disposition is DecisionDisposition.REGENERATION_REQUESTED:
            if self.regeneration_child_run_reference is None:
                raise ValueError(
                    "REGENERATION_REQUESTED requires regeneration_child_run_reference"
                )
        elif self.regeneration_child_run_reference is not None:
            raise ValueError(
                "regeneration_child_run_reference applies only to REGENERATION_REQUESTED"
            )
        _validate_identity_separation(self)

    def to_domain_dict(self) -> dict[str, object]:
        return _domain_value(self)  # type: ignore[return-value]

    def to_domain_json(self) -> str:
        return json.dumps(
            self.to_domain_dict(),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )


def compare_human_decision_links(
    existing: HumanDecisionLink,
    incoming: HumanDecisionLink,
) -> EvidenceComparison:
    """Classify immutable link convergence without changing either value."""
    _require_type(existing, HumanDecisionLink, "existing")
    _require_type(incoming, HumanDecisionLink, "incoming")
    if existing.human_decision_link_id != incoming.human_decision_link_id:
        return EvidenceComparison.DISTINCT_IDENTITY
    if existing.to_domain_json() == incoming.to_domain_json():
        return EvidenceComparison.EQUIVALENT
    return EvidenceComparison.CONFLICTING


def _validate_timestamp(value: object) -> None:
    if not isinstance(value, datetime):
        raise TypeError("decision_timestamp must be a datetime")
    if value.utcoffset() is None:
        raise ValueError("decision_timestamp must be timezone-aware")


def _validate_reference(value: OpaqueReference, name: str) -> None:
    if len(value.value.encode("utf-8")) > MAX_DECISION_REFERENCE_BYTES:
        raise ValueError(f"{name} exceeds {MAX_DECISION_REFERENCE_BYTES} bytes")


def _validate_identity_separation(link: HumanDecisionLink) -> None:
    evidence_ids = (
        link.human_decision_link_id.value,
        link.human_decision_id.value,
        link.reviewed_evidence_bundle_id.value,
        link.reviewed_evidence_card_id.value,
    )
    if len(set(evidence_ids)) != len(evidence_ids):
        raise ValueError("HumanDecisionLink Evidence identities must remain distinct")
    link_id = link.human_decision_link_id.value
    if link_id in {
        link.human_actor_reference.value,
        link.workflow_event_or_result_reference.value,
        None
        if link.regeneration_child_run_reference is None
        else link.regeneration_child_run_reference.value,
    }:
        raise ValueError(
            "human_decision_link_id must not copy an externally owned reference"
        )
