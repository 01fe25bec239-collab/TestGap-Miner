"""Workflow-owned boundary over durable Retrieval localisation values.

This module defines the narrow adapter protocol between the Workflow
orchestrator and the Retrieval (RAG) side. The boundary receives a
validated bounded localisation request and may return only already
durable public RAG contract values (``app.retrieval.ContextBundle``) or
an explicit low-confidence marker.

The Workflow side verifies the returned value's type and its exact
repository/revision binding, and fails closed on malformed or
adversarial results. This module performs no ranking or scoring, no
filesystem crawling, no network behavior, and never infers a mutable
HEAD/branch revision.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final, Protocol, runtime_checkable

from app.retrieval import ContextBundle, RepositoryIdentity, RevisionIdentity


MAX_LOCALISATION_QUERY_BYTES: Final = 16_384


class LocalisationBoundaryFailureCode(StrEnum):
    """Stable fail-closed codes for rejected localisation boundary usage."""

    INVALID_REQUEST = "INVALID_REQUEST"
    MALFORMED_RESULT = "MALFORMED_RESULT"
    REPOSITORY_MISMATCH = "REPOSITORY_MISMATCH"
    REVISION_MISMATCH = "REVISION_MISMATCH"
    BOUNDARY_ERROR = "BOUNDARY_ERROR"


@dataclass(frozen=True, slots=True)
class LocalisationRequest:
    """Validated bounded localisation intent handed across the boundary."""

    repository_id: RepositoryIdentity
    revision_id: RevisionIdentity
    query: str

    def __post_init__(self) -> None:
        if type(self.repository_id) is not RepositoryIdentity:
            raise TypeError("repository_id must be a RepositoryIdentity")
        if type(self.revision_id) is not RevisionIdentity:
            raise TypeError("revision_id must be a RevisionIdentity")
        object.__setattr__(self, "query", validated_query_text(self.query))

    def canonical_dict(self) -> dict[str, str]:
        return {
            "query": self.query,
            "repository_id": self.repository_id.value,
            "revision_id": self.revision_id.value,
        }


@dataclass(frozen=True, slots=True)
class LowLocalisationConfidence:
    """Explicit boundary marker for below-workflow localisation confidence."""


class LocalisationResolutionKind(StrEnum):
    CONTEXT_AVAILABLE = "CONTEXT_AVAILABLE"
    LOW_LOCALISATION_CONFIDENCE = "LOW_LOCALISATION_CONFIDENCE"
    BOUNDARY_FAILURE = "BOUNDARY_FAILURE"


@dataclass(frozen=True, slots=True)
class LocalisationResolution:
    """Typed outcome of one validated localisation boundary call."""

    kind: LocalisationResolutionKind
    context_bundle: ContextBundle | None = None
    failure_code: LocalisationBoundaryFailureCode | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, LocalisationResolutionKind):
            raise TypeError("kind must be a LocalisationResolutionKind")
        if self.kind == LocalisationResolutionKind.CONTEXT_AVAILABLE:
            if type(self.context_bundle) is not ContextBundle:
                raise TypeError(
                    "CONTEXT_AVAILABLE requires an exact ContextBundle"
                )
            if self.failure_code is not None:
                raise ValueError("CONTEXT_AVAILABLE cannot carry a failure code")
            return
        if self.context_bundle is not None:
            raise ValueError(f"{self.kind.value} cannot carry a ContextBundle")
        if self.kind == LocalisationResolutionKind.BOUNDARY_FAILURE:
            if not isinstance(
                self.failure_code, LocalisationBoundaryFailureCode
            ):
                raise TypeError(
                    "BOUNDARY_FAILURE requires a LocalisationBoundaryFailureCode"
                )


@runtime_checkable
class LocalisationBoundary(Protocol):
    """Narrow RAG-side protocol; returns durable contract values only."""

    def localise(self, request: LocalisationRequest) -> object:
        """Return a repository/revision-bound ContextBundle or a marker."""
        ...


def invoke_localisation(
    boundary: object, request: object
) -> LocalisationResolution:
    """Invoke one localisation boundary call and fail closed on anything
    that is not a correctly bound durable result.

    This function is total over adversarial inputs: malformed boundaries,
    raising boundaries, and malformed results are reported as typed
    failures instead of leaking exceptions.
    """

    if not isinstance(request, LocalisationRequest):
        return _failure(LocalisationBoundaryFailureCode.INVALID_REQUEST)
    entrypoint = getattr(boundary, "localise", None)
    if not callable(entrypoint):
        return _failure(LocalisationBoundaryFailureCode.BOUNDARY_ERROR)
    try:
        raw = entrypoint(request)
    except Exception:
        return _failure(LocalisationBoundaryFailureCode.BOUNDARY_ERROR)
    return resolve_localisation_result(raw, request)


def resolve_localisation_result(
    raw: object, request: LocalisationRequest
) -> LocalisationResolution:
    """Validate one already-invoked boundary value against the request."""

    try:
        if isinstance(raw, LowLocalisationConfidence):
            return LocalisationResolution(
                LocalisationResolutionKind.LOW_LOCALISATION_CONFIDENCE
            )
        if type(raw) is not ContextBundle:
            return _failure(LocalisationBoundaryFailureCode.MALFORMED_RESULT)
        if raw.repository_id != request.repository_id:
            return _failure(LocalisationBoundaryFailureCode.REPOSITORY_MISMATCH)
        if raw.revision_id != request.revision_id:
            return _failure(LocalisationBoundaryFailureCode.REVISION_MISMATCH)
        return LocalisationResolution(
            LocalisationResolutionKind.CONTEXT_AVAILABLE,
            context_bundle=raw,
        )
    except Exception:
        return _failure(LocalisationBoundaryFailureCode.MALFORMED_RESULT)


def validated_query_text(value: object) -> str:
    """Validate one bounded nonempty query without outer whitespace."""

    if type(value) is not str or not value or value != value.strip():
        raise ValueError("localisation query must be nonempty text without outer whitespace")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeEncodeError as error:
        raise ValueError("localisation query must be valid UTF-8 text") from error
    if size > MAX_LOCALISATION_QUERY_BYTES:
        raise ValueError(
            f"localisation query exceeds {MAX_LOCALISATION_QUERY_BYTES} UTF-8 bytes"
        )
    return value


def _failure(code: LocalisationBoundaryFailureCode) -> LocalisationResolution:
    return LocalisationResolution(
        LocalisationResolutionKind.BOUNDARY_FAILURE,
        failure_code=code,
    )
