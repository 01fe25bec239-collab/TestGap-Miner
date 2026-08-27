import json
from dataclasses import FrozenInstanceError, fields, replace

import pytest

from app.evidence import traceability as traceability_module
from app.evidence.artefact import ArtefactId, ArtefactReference
from app.evidence.candidate import CandidatePatch, CandidatePatchId
from app.evidence.decision import EvidenceBundleId, EvidenceCardId
from app.evidence.execution import (
    EVIDENCE_CONTRACT_VERSION,
    CandidateVersionId,
    EvidenceComparison,
    ExecutionEvidence,
    ExecutionEvidenceId,
    OpaqueReference,
    QueueMessageId,
)
from app.evidence.traceability import (
    TraceabilityLink,
    TraceabilityLinkId,
    TraceabilitySubject,
    compare_traceability_links,
)
from app.retrieval import (
    ContextBundle,
    ContextBundleIdentity,
    ContextItem,
    ContextItemIdentity,
)


def link(**overrides: object) -> TraceabilityLink:
    values: dict[str, object] = {
        "traceability_link_id": TraceabilityLinkId("traceability:1"),
        "review_scope": EvidenceCardId("card:1"),
        "subject": TraceabilitySubject.RATIONALE,
        "sources": [ContextItemIdentity("context-item:1")],
    }
    values.update(overrides)
    return TraceabilityLink(**values)  # type: ignore[arg-type]


def test_caller_supplied_link_id_is_preserved_without_generation() -> None:
    supplied = TraceabilityLinkId("caller:stable")
    links = [link(traceability_link_id=supplied) for _ in range(3)]

    assert all(value.traceability_link_id is supplied for value in links)
    assert not set(dir(traceability_module)) & {"uuid", "random", "secrets", "time"}


@pytest.mark.parametrize("malformed", ["", " ", 7])
def test_link_id_rejects_malformed_values(malformed: object) -> None:
    with pytest.raises(ValueError, match="nonempty string"):
        TraceabilityLinkId(malformed)  # type: ignore[arg-type]


def test_wrong_link_id_domain_and_subclass_fail_closed() -> None:
    class SpecialLinkId(TraceabilityLinkId):
        pass

    for unsupported in (QueueMessageId("same"), SpecialLinkId("special"), "raw"):
        with pytest.raises(TypeError, match="TraceabilityLinkId"):
            link(traceability_link_id=unsupported)


def test_subject_enum_is_exact_and_rejects_text() -> None:
    assert tuple(TraceabilitySubject) == (
        TraceabilitySubject.RATIONALE,
        TraceabilitySubject.FIELD,
        TraceabilitySubject.REFERENCE,
    )
    assert [value.value for value in TraceabilitySubject] == [
        "RATIONALE",
        "FIELD",
        "REFERENCE",
    ]
    with pytest.raises(TypeError, match="TraceabilitySubject"):
        link(subject="RATIONALE")


@pytest.mark.parametrize(
    ("scope", "kind"),
    [
        (EvidenceCardId("scope:card"), "EVIDENCE_CARD"),
        (EvidenceBundleId("scope:bundle"), "EVIDENCE_BUNDLE"),
    ],
)
def test_exact_review_scope_is_preserved(scope: object, kind: str) -> None:
    value = link(review_scope=scope)

    assert value.review_scope is scope
    assert value.review_scope_kind == kind
    assert value.to_domain_dict()["review_scope"] == {
        "kind": kind,
        "value": scope.value,  # type: ignore[union-attr]
    }


def test_scope_type_is_semantic_even_when_text_matches() -> None:
    existing = link(review_scope=EvidenceCardId("scope:same"))
    incoming = link(review_scope=EvidenceBundleId("scope:same"))

    assert existing.to_domain_dict() != incoming.to_domain_dict()
    assert compare_traceability_links(existing, incoming) is EvidenceComparison.CONFLICTING


def test_unsupported_scope_and_supported_scope_subclass_fail_closed() -> None:
    class SpecialCardId(EvidenceCardId):
        pass

    unsupported = [
        "card:1",
        OpaqueReference("card:1"),
        ContextBundleIdentity("card:1"),
        CandidatePatchId("card:1"),
        SpecialCardId("card:1"),
    ]
    for scope in unsupported:
        with pytest.raises(TypeError, match="unsupported identity type"):
            link(review_scope=scope)


@pytest.mark.parametrize(
    ("source", "kind"),
    [
        (EvidenceCardId("source:card"), "EVIDENCE_CARD"),
        (EvidenceBundleId("source:bundle"), "EVIDENCE_BUNDLE"),
        (ExecutionEvidenceId("source:execution"), "EXECUTION_EVIDENCE"),
        (CandidatePatchId("source:patch"), "CANDIDATE_PATCH"),
        (CandidateVersionId("source:version"), "CANDIDATE_VERSION"),
        (ArtefactId("source:artefact"), "ARTEFACT_REFERENCE"),
        (ContextBundleIdentity("source:context-bundle"), "CONTEXT_BUNDLE"),
        (ContextItemIdentity("source:context-item"), "CONTEXT_ITEM"),
    ],
)
def test_every_supported_source_mapping_preserves_exact_object(
    source: object,
    kind: str,
) -> None:
    value = link(sources=[source])

    assert value.sources[0] is source
    assert value.to_domain_dict()["sources"] == [
        {"kind": kind, "value": source.value}  # type: ignore[union-attr]
    ]


def test_context_identities_are_preserved_without_context_content() -> None:
    bundle_id = ContextBundleIdentity("context-bundle:exact")
    item_id = ContextItemIdentity("context-item:exact")
    value = link(sources=[item_id, bundle_id])

    assert any(source is bundle_id for source in value.sources)
    assert any(source is item_id for source in value.sources)
    assert "repository-content-sentinel" not in value.to_domain_json()
    assert all(
        type(source) in (ContextBundleIdentity, ContextItemIdentity)
        for source in value.sources
    )


def test_supported_source_subclass_fails_closed() -> None:
    class SpecialExecutionId(ExecutionEvidenceId):
        pass

    with pytest.raises(TypeError, match="unsupported identity type"):
        link(sources=[SpecialExecutionId("execution:special")])


@pytest.mark.parametrize(
    "source",
    [
        "plain string source",
        b"bytes",
        bytearray(b"bytes"),
        OpaqueReference("opaque:raw-text"),
        QueueMessageId("queue:1"),
        object.__new__(ContextItem),
        object.__new__(ContextBundle),
        object.__new__(CandidatePatch),
        object.__new__(ExecutionEvidence),
        object.__new__(ArtefactReference),
    ],
)
def test_raw_values_and_domain_objects_fail_closed_as_sources(source: object) -> None:
    with pytest.raises(TypeError):
        link(sources=[source])


@pytest.mark.parametrize("sources", [[], (), "raw", b"raw", bytearray(b"raw")])
def test_source_collection_must_be_nonempty_typed_identities(sources: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        link(sources=sources)


def test_source_order_is_canonical_and_comparison_equivalent() -> None:
    first = ExecutionEvidenceId("execution:z")
    second = ContextItemIdentity("context:a")
    forward = link(sources=[first, second])
    backward = link(sources=[second, first])

    assert forward.sources == backward.sources
    assert forward.sources == (second, first)
    assert forward.to_domain_json() == backward.to_domain_json()
    assert forward.to_domain_json() == forward.to_domain_json()
    assert compare_traceability_links(forward, backward) is EvidenceComparison.EQUIVALENT


def test_duplicate_source_binding_is_rejected_not_deduplicated() -> None:
    with pytest.raises(ValueError, match="duplicate traceability source"):
        link(
            sources=[
                ExecutionEvidenceId("execution:duplicate"),
                ExecutionEvidenceId("execution:duplicate"),
            ]
        )


def test_same_text_in_different_source_domains_does_not_collapse() -> None:
    bundle = EvidenceBundleId("shared:text")
    context = ContextBundleIdentity("shared:text")
    value = link(sources=[bundle, context])

    assert len(value.sources) == 2
    assert {entry["kind"] for entry in value.to_domain_dict()["sources"]} == {
        "EVIDENCE_BUNDLE",
        "CONTEXT_BUNDLE",
    }


def test_changing_only_same_text_source_domain_conflicts() -> None:
    existing = link(sources=[EvidenceBundleId("shared:text")])
    incoming = link(sources=[ContextBundleIdentity("shared:text")])

    assert compare_traceability_links(existing, incoming) is EvidenceComparison.CONFLICTING


@pytest.mark.parametrize(
    "incoming",
    [
        link(review_scope=EvidenceCardId("card:changed")),
        link(subject=TraceabilitySubject.FIELD),
        link(sources=[ContextItemIdentity("context-item:changed")]),
        link(
            sources=[
                ContextItemIdentity("context-item:1"),
                ArtefactId("artefact:added"),
            ]
        ),
    ],
)
def test_same_link_id_with_changed_binding_conflicts(incoming: TraceabilityLink) -> None:
    assert compare_traceability_links(link(), incoming) is EvidenceComparison.CONFLICTING


def test_comparison_converges_same_binding_and_distinguishes_other_id() -> None:
    assert compare_traceability_links(link(), link()) is EvidenceComparison.EQUIVALENT
    other = link(traceability_link_id=TraceabilityLinkId("traceability:other"))
    assert compare_traceability_links(link(), other) is EvidenceComparison.DISTINCT_IDENTITY


def test_caller_list_mutation_cannot_change_constructed_link() -> None:
    first = ContextItemIdentity("context-item:1")
    supplied = [first]
    value = link(sources=supplied)
    snapshot = value.to_domain_json()

    supplied.append(ArtefactId("artefact:later"))

    assert value.sources == (first,)
    assert value.to_domain_json() == snapshot


def test_link_and_held_identities_are_immutable_and_slotted() -> None:
    value = link()

    with pytest.raises(FrozenInstanceError):
        value.subject = TraceabilitySubject.FIELD  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        value.traceability_link_id.value = "changed"  # type: ignore[misc]
    assert not hasattr(value, "__dict__")


def test_contract_version_accepts_only_current_evidence_contract() -> None:
    assert link().contract_version == EVIDENCE_CONTRACT_VERSION
    assert link(contract_version=EVIDENCE_CONTRACT_VERSION).contract_version == (
        "CONTRACT-EVIDENCE-001@1.0.0-draft.3"
    )
    with pytest.raises(ValueError, match="unsupported Evidence contract version"):
        link(contract_version="CONTRACT-EVIDENCE-001@2.0.0")


def test_serialization_contains_only_required_semantic_binding() -> None:
    value = link()
    domain = value.to_domain_dict()

    assert tuple(field.name for field in fields(TraceabilityLink)) == (
        "traceability_link_id",
        "review_scope",
        "subject",
        "sources",
        "contract_version",
    )
    assert domain == json.loads(value.to_domain_json())
    assert value.to_domain_json() == json.dumps(
        domain,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    forbidden = {
        "verified",
        "approved",
        "accepted",
        "trusted",
        "true",
        "complete",
        "publishable",
        "workflow_state",
        "security_state",
    }
    assert forbidden.isdisjoint(domain)


def test_compare_rejects_wrong_domain_objects() -> None:
    with pytest.raises(TypeError, match="TraceabilityLink"):
        compare_traceability_links(link(), object())  # type: ignore[arg-type]


def test_replace_preserves_canonical_immutability() -> None:
    original = link()
    changed = replace(original, subject=TraceabilitySubject.REFERENCE)

    assert original.subject is TraceabilitySubject.RATIONALE
    assert changed.subject is TraceabilitySubject.REFERENCE
