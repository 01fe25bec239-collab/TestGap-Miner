"""Deterministic Evaluation-owned localisation metric primitives.

Foundation only: Recall@K and Reciprocal Rank computed over RAG
``FileIdentity`` values. This module defines no thresholds, no pass/fail
gates, and no release semantics -- it only produces exact, reproducible
case-level evidence as immutable value objects.

Predictions are an ordered sequence of RAG ``FileIdentity`` values; ground
truth is a non-empty collection (unordered forms such as ``set`` and
``frozenset`` are valid) whose members are scored by membership only, so
accepting unordered ground truth never affects result determinism.

Standard library only. Inputs are never mutated: predicted ordering is
caller-owned and preserved exactly, and caller-owned ground-truth
collections are read without sorting or in-place modification.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable
from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction
from typing import NoReturn

from app.retrieval import FileIdentity


class LocalisationMetricErrorCode(StrEnum):
    INVALID_K = "INVALID_K"
    EMPTY_GROUND_TRUTH = "EMPTY_GROUND_TRUTH"
    INVALID_PREDICTIONS = "INVALID_PREDICTIONS"
    INVALID_RELEVANT_IDENTITY = "INVALID_RELEVANT_IDENTITY"
    DUPLICATE_PREDICTION = "DUPLICATE_PREDICTION"
    DUPLICATE_RELEVANT_IDENTITY = "DUPLICATE_RELEVANT_IDENTITY"
    INVALID_SCORES = "INVALID_SCORES"


class LocalisationMetricError(ValueError):
    """Stable fail-closed error for malformed metric inputs."""

    def __init__(self, code: LocalisationMetricErrorCode, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code.value}: {detail}")


@dataclass(frozen=True, slots=True)
class RecallAtKResult:
    """Exact Recall@K evidence: numerator hits within the first K predictions."""

    k: int
    numerator: int
    denominator: int

    @property
    def score(self) -> Fraction:
        """Exact rational score; derived convenience view of numerator/denominator."""
        return Fraction(self.numerator, self.denominator)

    def canonical_dict(self) -> dict[str, int]:
        return {"denominator": self.denominator, "k": self.k, "numerator": self.numerator}


@dataclass(frozen=True, slots=True)
class ReciprocalRankResult:
    """Exact reciprocal-rank evidence.

    On a hit at rank R (1-based): numerator 1, denominator R. With no hit:
    numerator 0 with the stable convention denominator len(predictions) + 1,
    which is exactly zero and reproducible even for empty predictions.
    """

    numerator: int
    denominator: int
    first_relevant_rank: int | None

    @property
    def score(self) -> Fraction:
        """Exact rational score; derived convenience view of numerator/denominator."""
        return Fraction(self.numerator, self.denominator)

    def canonical_dict(self) -> dict[str, int | None]:
        return {
            "denominator": self.denominator,
            "first_relevant_rank": self.first_relevant_rank,
            "numerator": self.numerator,
        }


def recall_at_k(
    predictions: Iterable[FileIdentity],
    relevant_file_identities: Collection[FileIdentity],
    k: int,
) -> RecallAtKResult:
    """Recall@K of ``predictions[:k]`` against non-empty ground truth.

    Predictions must be an ordered sequence; unordered prediction
    containers fail closed. Ground truth may be any non-empty collection
    of ``FileIdentity`` values (including unordered ``set``/``frozenset``
    forms); ordering semantics never apply to it.

    The whole supplied prediction sequence is duplicate-checked before any
    window is scored; duplicates anywhere (including beyond K) fail closed.
    Ground-truth duplicates fail closed only in duplicate-capable forms
    (list/tuple and other ordered iterables); set/frozenset are inherently
    unique.
    """
    validated_predictions = _validated_predictions(predictions)
    relevant = _validated_relevant(relevant_file_identities)
    validated_k = _validated_k(k)
    relevant_set = frozenset(relevant)
    hits = sum(1 for identity in validated_predictions[:validated_k] if identity in relevant_set)
    return RecallAtKResult(k=validated_k, numerator=hits, denominator=len(relevant))


def reciprocal_rank(
    predictions: Iterable[FileIdentity],
    relevant_file_identities: Collection[FileIdentity],
) -> ReciprocalRankResult:
    """Reciprocal rank of the first relevant prediction (rank numbering starts at 1).

    Predictions must be an ordered sequence; ground truth may be any
    non-empty collection of ``FileIdentity`` values, including unordered
    ``set``/``frozenset`` forms.
    """
    validated_predictions = _validated_predictions(predictions)
    relevant = _validated_relevant(relevant_file_identities)
    relevant_set = frozenset(relevant)
    for position, identity in enumerate(validated_predictions):
        if identity in relevant_set:
            rank = position + 1
            return ReciprocalRankResult(
                numerator=1, denominator=rank, first_relevant_rank=rank
            )
    return ReciprocalRankResult(
        numerator=0, denominator=len(validated_predictions) + 1, first_relevant_rank=None
    )


def macro_average(scores: Iterable[Fraction]) -> Fraction:
    """Exact unweighted mean of case-level scores; empty input fails closed."""
    values = _typed_tuple(scores, Fraction, "scores", LocalisationMetricErrorCode.INVALID_SCORES)
    if not values:
        _raise(LocalisationMetricErrorCode.INVALID_SCORES, "scores must be nonempty")
    total = sum(values, Fraction(0))
    return total / len(values)


def _validated_predictions(predictions: Iterable[object]) -> tuple[FileIdentity, ...]:
    supplied = _typed_tuple(
        predictions, FileIdentity, "predictions", LocalisationMetricErrorCode.INVALID_PREDICTIONS
    )
    if len(frozenset(supplied)) != len(supplied):
        _raise(LocalisationMetricErrorCode.DUPLICATE_PREDICTION, "duplicate predicted file identity")
    return supplied


def _validated_relevant(
    relevant_file_identities: Collection[object],
) -> tuple[FileIdentity, ...]:
    """Validate non-empty ground truth without requiring ordering semantics.

    Unordered collections (``set``/``frozenset``) are valid because ground
    truth carries no ranking semantics; duplicates fail closed only in
    duplicate-capable forms, since a set cannot represent them. The
    caller-owned collection is never sorted or mutated.
    """
    if isinstance(relevant_file_identities, (str, bytes, bytearray, dict)):
        _raise(
            LocalisationMetricErrorCode.INVALID_RELEVANT_IDENTITY,
            "relevant_file_identities must be a collection of FileIdentity values",
        )
    try:
        supplied = tuple(relevant_file_identities)
    except TypeError:
        _raise(
            LocalisationMetricErrorCode.INVALID_RELEVANT_IDENTITY,
            "relevant_file_identities must be iterable",
        )
    if not supplied:
        _raise(LocalisationMetricErrorCode.EMPTY_GROUND_TRUTH, "relevant_file_identities is empty")
    if not all(isinstance(value, FileIdentity) for value in supplied):
        _raise(
            LocalisationMetricErrorCode.INVALID_RELEVANT_IDENTITY,
            "relevant_file_identities must contain only FileIdentity values",
        )
    inherently_unique = isinstance(relevant_file_identities, (set, frozenset))
    if not inherently_unique and len(frozenset(supplied)) != len(supplied):
        _raise(
            LocalisationMetricErrorCode.DUPLICATE_RELEVANT_IDENTITY,
            "duplicate relevant file identity",
        )
    return supplied


def _validated_k(k: object) -> int:
    if type(k) is not int or k < 1:
        _raise(LocalisationMetricErrorCode.INVALID_K, "k must be a positive integer")
    return k


def _typed_tuple(
    values: Iterable[object], expected: type, label: str, code: LocalisationMetricErrorCode
) -> tuple:
    if isinstance(values, (str, bytes, bytearray, set, frozenset, dict)):
        _raise(code, f"{label} must be an ordered iterable of {expected.__name__} values")
    try:
        supplied = tuple(values)
    except TypeError:
        _raise(code, f"{label} must be iterable")
    if not all(isinstance(value, expected) for value in supplied):
        _raise(code, f"{label} must contain only {expected.__name__} values")
    return supplied


def _raise(code: LocalisationMetricErrorCode, detail: str) -> NoReturn:
    raise LocalisationMetricError(code, detail)
