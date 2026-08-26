"""Deterministic tests for Evaluation-owned localisation metric primitives.

No model calls, no network, no thresholds: these tests pin exact
numerator/denominator evidence, fail-closed input policy, immutability,
and compatibility with the frozen localisation baseline dataset.
"""

import hashlib
import typing
from dataclasses import FrozenInstanceError
from fractions import Fraction
from pathlib import Path

import pytest

import evaluation.localisation_metrics as localisation_metrics
from app.retrieval import (
    FileIdentity,
    RepositoryIdentity,
    load_localisation_dataset,
)
from evaluation.localisation_metrics import (
    LocalisationMetricError,
    LocalisationMetricErrorCode,
    RecallAtKResult,
    ReciprocalRankResult,
    macro_average,
    recall_at_k,
    reciprocal_rank,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = (
    REPO_ROOT / "evaluation" / "datasets" / "localisation" / "LOCALISATION_BASELINE_V1.json"
)

MODEL_DOMAIN = FileIdentity("apps/api/app/workflow/model_domain.py")
QUEUE_ENVELOPE = FileIdentity("apps/api/app/queue/envelope.py")
QUEUE_IDENTITIES = FileIdentity("apps/api/app/queue/identities.py")
RETRIEVAL_MODULE = FileIdentity("apps/api/app/retrieval/localisation.py")
UNRELATED = FileIdentity("docs/unrelated/notes.md")


def assert_metric_error(code: LocalisationMetricErrorCode, operation) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(LocalisationMetricError) as raised:
        operation()
    assert raised.value.code is code
    assert raised.value.detail


# --------------------------------------------------------------------------
# Recall@K
# --------------------------------------------------------------------------


def test_perfect_recall_at_k() -> None:
    result = recall_at_k((MODEL_DOMAIN, QUEUE_ENVELOPE), (MODEL_DOMAIN, QUEUE_ENVELOPE), 2)
    assert isinstance(result, RecallAtKResult)
    assert result.k == 2
    assert result.numerator == 2
    assert result.denominator == 2
    assert result.score == Fraction(1, 1)


def test_partial_recall_at_k() -> None:
    result = recall_at_k((MODEL_DOMAIN, UNRELATED), (MODEL_DOMAIN, QUEUE_ENVELOPE), 2)
    assert result.numerator == 1
    assert result.denominator == 2
    assert result.score == Fraction(1, 2)
    truncated_out = recall_at_k((UNRELATED, MODEL_DOMAIN), (MODEL_DOMAIN,), 1)
    assert truncated_out.numerator == 0
    assert truncated_out.score == Fraction(0, 1)


def test_zero_hit_recall_at_k() -> None:
    result = recall_at_k((UNRELATED, RETRIEVAL_MODULE), (MODEL_DOMAIN, QUEUE_ENVELOPE), 2)
    assert result.numerator == 0
    assert result.denominator == 2
    assert result.score == Fraction(0, 1)


def test_k_greater_than_prediction_length_is_valid() -> None:
    result = recall_at_k((QUEUE_IDENTITIES,), (QUEUE_IDENTITIES, MODEL_DOMAIN), 10)
    assert result.k == 10
    assert result.numerator == 1
    assert result.denominator == 2
    assert result.score == Fraction(1, 2)


def test_multi_relevant_ground_truth_recall_at_k() -> None:
    full = recall_at_k(
        (QUEUE_IDENTITIES, UNRELATED, QUEUE_ENVELOPE),
        (QUEUE_ENVELOPE, QUEUE_IDENTITIES),
        3,
    )
    assert full.numerator == 2
    assert full.denominator == 2
    partial = recall_at_k(
        (QUEUE_IDENTITIES, UNRELATED, QUEUE_ENVELOPE),
        (QUEUE_ENVELOPE, QUEUE_IDENTITIES),
        1,
    )
    assert partial.numerator == 1
    assert partial.denominator == 2
    assert partial.score == Fraction(1, 2)


def test_empty_predictions_with_valid_ground_truth_recall_at_k() -> None:
    result = recall_at_k((), (MODEL_DOMAIN,), 3)
    assert result.k == 3
    assert result.numerator == 0
    assert result.denominator == 1
    assert result.score == Fraction(0, 1)


@pytest.mark.parametrize("invalid_k", [0])
def test_zero_k_fails_closed(invalid_k: int) -> None:
    assert_metric_error(
        LocalisationMetricErrorCode.INVALID_K,
        lambda: recall_at_k((MODEL_DOMAIN,), (MODEL_DOMAIN,), invalid_k),
    )


@pytest.mark.parametrize("invalid_k", [-1, -100])
def test_negative_k_fails_closed(invalid_k: int) -> None:
    assert_metric_error(
        LocalisationMetricErrorCode.INVALID_K,
        lambda: recall_at_k((MODEL_DOMAIN,), (MODEL_DOMAIN,), invalid_k),
    )


@pytest.mark.parametrize("invalid_k", ["3", 2.0, 2.5, None, Fraction(3, 1)])
def test_non_integer_k_fails_closed(invalid_k: object) -> None:
    assert_metric_error(
        LocalisationMetricErrorCode.INVALID_K,
        lambda: recall_at_k((MODEL_DOMAIN,), (MODEL_DOMAIN,), invalid_k),
    )


@pytest.mark.parametrize("invalid_k", [True, False])
def test_bool_k_fails_closed(invalid_k: bool) -> None:
    assert_metric_error(
        LocalisationMetricErrorCode.INVALID_K,
        lambda: recall_at_k((MODEL_DOMAIN,), (MODEL_DOMAIN,), invalid_k),
    )


def test_empty_relevant_identities_fail_closed() -> None:
    assert_metric_error(
        LocalisationMetricErrorCode.EMPTY_GROUND_TRUTH,
        lambda: recall_at_k((MODEL_DOMAIN,), (), 1),
    )
    assert_metric_error(
        LocalisationMetricErrorCode.EMPTY_GROUND_TRUTH,
        lambda: recall_at_k((MODEL_DOMAIN,), [], 1),
    )
    assert_metric_error(
        LocalisationMetricErrorCode.EMPTY_GROUND_TRUTH,
        lambda: reciprocal_rank((MODEL_DOMAIN,), ()),
    )
    assert_metric_error(
        LocalisationMetricErrorCode.EMPTY_GROUND_TRUTH,
        lambda: reciprocal_rank((MODEL_DOMAIN,), []),
    )


def test_duplicate_predictions_fail_closed() -> None:
    assert_metric_error(
        LocalisationMetricErrorCode.DUPLICATE_PREDICTION,
        lambda: recall_at_k((MODEL_DOMAIN, MODEL_DOMAIN), (MODEL_DOMAIN,), 2),
    )
    assert_metric_error(
        LocalisationMetricErrorCode.DUPLICATE_PREDICTION,
        lambda: reciprocal_rank((MODEL_DOMAIN, MODEL_DOMAIN), (MODEL_DOMAIN,)),
    )


def test_duplicate_predictions_beyond_k_still_fail_closed() -> None:
    # The duplicate occurs outside the scored window but must still poison the run.
    assert_metric_error(
        LocalisationMetricErrorCode.DUPLICATE_PREDICTION,
        lambda: recall_at_k((MODEL_DOMAIN, UNRELATED, MODEL_DOMAIN), (MODEL_DOMAIN,), 1),
    )
    assert_metric_error(
        LocalisationMetricErrorCode.DUPLICATE_PREDICTION,
        lambda: recall_at_k((MODEL_DOMAIN, UNRELATED, MODEL_DOMAIN), (UNRELATED,), 2),
    )


def test_duplicate_relevant_identities_fail_closed() -> None:
    assert_metric_error(
        LocalisationMetricErrorCode.DUPLICATE_RELEVANT_IDENTITY,
        lambda: recall_at_k((MODEL_DOMAIN,), (MODEL_DOMAIN, MODEL_DOMAIN), 1),
    )
    assert_metric_error(
        LocalisationMetricErrorCode.DUPLICATE_RELEVANT_IDENTITY,
        lambda: reciprocal_rank((MODEL_DOMAIN,), (MODEL_DOMAIN, MODEL_DOMAIN)),
    )


def test_duplicate_ground_truth_in_list_and_tuple_forms_fail_closed() -> None:
    assert_metric_error(
        LocalisationMetricErrorCode.DUPLICATE_RELEVANT_IDENTITY,
        lambda: recall_at_k((MODEL_DOMAIN,), [QUEUE_ENVELOPE, QUEUE_ENVELOPE], 1),
    )
    assert_metric_error(
        LocalisationMetricErrorCode.DUPLICATE_RELEVANT_IDENTITY,
        lambda: reciprocal_rank((MODEL_DOMAIN,), (UNRELATED, UNRELATED)),
    )


# --------------------------------------------------------------------------
# Unordered ground-truth collections (A1 input boundary)
# --------------------------------------------------------------------------


def test_recall_at_k_accepts_set_ground_truth() -> None:
    result = recall_at_k((MODEL_DOMAIN, UNRELATED), {MODEL_DOMAIN, QUEUE_ENVELOPE}, 2)
    assert result.numerator == 1
    assert result.denominator == 2
    assert result.score == Fraction(1, 2)
    perfect = recall_at_k((QUEUE_IDENTITIES, QUEUE_ENVELOPE), {QUEUE_IDENTITIES}, 2)
    assert perfect.numerator == 1
    assert perfect.denominator == 1
    assert perfect.score == Fraction(1, 1)


def test_recall_at_k_accepts_frozenset_ground_truth() -> None:
    result = recall_at_k(
        (MODEL_DOMAIN, UNRELATED), frozenset({MODEL_DOMAIN, QUEUE_ENVELOPE}), 2
    )
    assert result.numerator == 1
    assert result.denominator == 2
    assert result.score == Fraction(1, 2)


def test_reciprocal_rank_accepts_set_ground_truth() -> None:
    result = reciprocal_rank((UNRELATED, MODEL_DOMAIN, QUEUE_ENVELOPE), {QUEUE_ENVELOPE})
    assert result.first_relevant_rank == 3
    assert result.numerator == 1
    assert result.denominator == 3
    assert result.score == Fraction(1, 3)
    no_hit = reciprocal_rank((RETRIEVAL_MODULE,), {MODEL_DOMAIN})
    assert no_hit.first_relevant_rank is None
    assert no_hit.score == Fraction(0, 1)


def test_reciprocal_rank_accepts_frozenset_ground_truth() -> None:
    result = reciprocal_rank(
        (UNRELATED, MODEL_DOMAIN), frozenset({MODEL_DOMAIN, QUEUE_ENVELOPE})
    )
    assert result.first_relevant_rank == 2
    assert result.score == Fraction(1, 2)


@pytest.mark.parametrize(
    "ground_truth_form",
    [
        pytest.param(lambda members: tuple(members), id="tuple"),
        pytest.param(lambda members: list(members), id="list"),
        pytest.param(lambda members: set(members), id="set"),
        pytest.param(lambda members: frozenset(members), id="frozenset"),
    ],
)
def test_unordered_multi_relevant_ground_truth_matches_ordered_exact_results(
    ground_truth_form,
) -> None:  # type: ignore[no-untyped-def]
    members = (QUEUE_ENVELOPE, MODEL_DOMAIN)
    for predictions, k in (
        ((MODEL_DOMAIN, UNRELATED, QUEUE_ENVELOPE), 3),
        ((QUEUE_ENVELOPE, UNRELATED, MODEL_DOMAIN), 2),
        ((UNRELATED,), 5),
    ):
        ordered = recall_at_k(predictions, members, k)
        unordered = recall_at_k(predictions, ground_truth_form(members), k)
        assert unordered == ordered
        assert unordered.canonical_dict() == ordered.canonical_dict()
        assert unordered.score == ordered.score
        rank_ordered = reciprocal_rank(predictions, members)
        rank_unordered = reciprocal_rank(predictions, ground_truth_form(members))
        assert rank_unordered == rank_ordered
        assert rank_unordered.canonical_dict() == rank_ordered.canonical_dict()


def test_empty_set_and_frozenset_ground_truth_fail_closed() -> None:
    assert_metric_error(
        LocalisationMetricErrorCode.EMPTY_GROUND_TRUTH,
        lambda: recall_at_k((MODEL_DOMAIN,), set(), 1),
    )
    assert_metric_error(
        LocalisationMetricErrorCode.EMPTY_GROUND_TRUTH,
        lambda: recall_at_k((MODEL_DOMAIN,), frozenset(), 1),
    )
    assert_metric_error(
        LocalisationMetricErrorCode.EMPTY_GROUND_TRUTH,
        lambda: reciprocal_rank((MODEL_DOMAIN,), set()),
    )
    assert_metric_error(
        LocalisationMetricErrorCode.EMPTY_GROUND_TRUTH,
        lambda: reciprocal_rank((MODEL_DOMAIN,), frozenset()),
    )


def test_wrong_identity_inside_unordered_ground_truth_fails_closed() -> None:
    assert_metric_error(
        LocalisationMetricErrorCode.INVALID_RELEVANT_IDENTITY,
        lambda: recall_at_k((MODEL_DOMAIN,), {MODEL_DOMAIN, "apps/api/app/queue/envelope.py"}, 1),
    )
    assert_metric_error(
        LocalisationMetricErrorCode.INVALID_RELEVANT_IDENTITY,
        lambda: reciprocal_rank((MODEL_DOMAIN,), frozenset({None})),
    )


def test_prediction_set_and_frozenset_remain_rejected() -> None:
    assert_metric_error(
        LocalisationMetricErrorCode.INVALID_PREDICTIONS,
        lambda: recall_at_k({MODEL_DOMAIN, UNRELATED}, (MODEL_DOMAIN,), 1),
    )
    assert_metric_error(
        LocalisationMetricErrorCode.INVALID_PREDICTIONS,
        lambda: recall_at_k(frozenset({MODEL_DOMAIN}), (MODEL_DOMAIN,), 1),
    )
    assert_metric_error(
        LocalisationMetricErrorCode.INVALID_PREDICTIONS,
        lambda: reciprocal_rank({MODEL_DOMAIN}, (MODEL_DOMAIN,)),
    )
    assert_metric_error(
        LocalisationMetricErrorCode.INVALID_PREDICTIONS,
        lambda: reciprocal_rank(frozenset({MODEL_DOMAIN}), (MODEL_DOMAIN,)),
    )


def test_caller_owned_set_ground_truth_is_never_mutated() -> None:
    caller_set = {MODEL_DOMAIN, QUEUE_ENVELOPE}
    before = set(caller_set)
    caller_frozenset = frozenset({QUEUE_IDENTITIES})

    recall_at_k([UNRELATED, MODEL_DOMAIN], caller_set, 2)
    reciprocal_rank([QUEUE_IDENTITIES, UNRELATED], caller_frozenset)

    assert caller_set == before
    assert len(caller_set) == 2
    assert caller_set == {MODEL_DOMAIN, QUEUE_ENVELOPE}
    assert caller_frozenset == frozenset({QUEUE_IDENTITIES})


def test_repeated_executions_with_equivalent_ground_truth_sets_are_deterministic() -> None:
    def compute() -> tuple[RecallAtKResult, ReciprocalRankResult]:
        ground_truth = {MODEL_DOMAIN, QUEUE_ENVELOPE}
        return (
            recall_at_k((QUEUE_ENVELOPE, UNRELATED, MODEL_DOMAIN), ground_truth, 3),
            reciprocal_rank((UNRELATED, QUEUE_ENVELOPE, MODEL_DOMAIN), ground_truth),
        )

    baseline = compute()
    for _ in range(10):
        assert compute() == baseline
    assert baseline[0].canonical_dict() == {"denominator": 2, "k": 3, "numerator": 2}
    assert baseline[0].score == Fraction(1, 1)
    assert baseline[1].canonical_dict() == {
        "denominator": 2,
        "first_relevant_rank": 2,
        "numerator": 1,
    }
    equivalent_forms = [
        compute()[0].score,
        recall_at_k(
            (QUEUE_ENVELOPE, UNRELATED, MODEL_DOMAIN),
            (QUEUE_ENVELOPE, MODEL_DOMAIN),
            3,
        ).score,
    ]
    assert all(score == baseline[0].score for score in equivalent_forms)


@pytest.mark.parametrize(
    "wrong_value",
    [
        "apps/api/app/workflow/model_domain.py",
        Path("apps/api/app/workflow/model_domain.py"),
        RepositoryIdentity("01fe25bec239-collab/TestGap-Miner"),
        None,
    ],
)
def test_wrong_prediction_identity_type_fails_closed(wrong_value: object) -> None:
    assert_metric_error(
        LocalisationMetricErrorCode.INVALID_PREDICTIONS,
        lambda: recall_at_k((wrong_value,), (MODEL_DOMAIN,), 1),
    )
    assert_metric_error(
        LocalisationMetricErrorCode.INVALID_PREDICTIONS,
        lambda: reciprocal_rank((wrong_value,), (MODEL_DOMAIN,)),
    )


@pytest.mark.parametrize(
    "wrong_value",
    [
        "apps/api/app/workflow/model_domain.py",
        Path("apps/api/app/workflow/model_domain.py"),
        RepositoryIdentity("01fe25bec239-collab/TestGap-Miner"),
        None,
    ],
)
def test_wrong_relevant_identity_type_fails_closed(wrong_value: object) -> None:
    assert_metric_error(
        LocalisationMetricErrorCode.INVALID_RELEVANT_IDENTITY,
        lambda: recall_at_k((MODEL_DOMAIN,), (wrong_value,), 1),
    )
    assert_metric_error(
        LocalisationMetricErrorCode.INVALID_RELEVANT_IDENTITY,
        lambda: reciprocal_rank((MODEL_DOMAIN,), (wrong_value,)),
    )


def test_unordered_containers_fail_closed() -> None:
    assert_metric_error(
        LocalisationMetricErrorCode.INVALID_PREDICTIONS,
        lambda: recall_at_k({MODEL_DOMAIN}, (MODEL_DOMAIN,), 1),
    )
    assert_metric_error(
        LocalisationMetricErrorCode.INVALID_PREDICTIONS,
        lambda: recall_at_k("apps/a.py", (MODEL_DOMAIN,), 1),
    )
    assert_metric_error(
        LocalisationMetricErrorCode.INVALID_RELEVANT_IDENTITY,
        lambda: recall_at_k((MODEL_DOMAIN,), {"apps/api/app/workflow/model_domain.py"}, 1),
    )
    assert_metric_error(
        LocalisationMetricErrorCode.INVALID_RELEVANT_IDENTITY,
        lambda: reciprocal_rank((MODEL_DOMAIN,), {"a": MODEL_DOMAIN}),
    )


# --------------------------------------------------------------------------
# Reciprocal Rank
# --------------------------------------------------------------------------


def test_rank_one_hit() -> None:
    result = reciprocal_rank((MODEL_DOMAIN, UNRELATED), (MODEL_DOMAIN,))
    assert isinstance(result, ReciprocalRankResult)
    assert result.first_relevant_rank == 1
    assert result.numerator == 1
    assert result.denominator == 1
    assert result.score == Fraction(1, 1)


def test_later_rank_hit() -> None:
    second = reciprocal_rank((UNRELATED, MODEL_DOMAIN), (MODEL_DOMAIN,))
    assert second.first_relevant_rank == 2
    assert second.numerator == 1
    assert second.denominator == 2
    assert second.score == Fraction(1, 2)
    third = reciprocal_rank((QUEUE_ENVELOPE, UNRELATED, MODEL_DOMAIN), (MODEL_DOMAIN,))
    assert third.first_relevant_rank == 3
    assert third.denominator == 3
    assert third.score == Fraction(1, 3)


def test_first_relevant_rank_only() -> None:
    result = reciprocal_rank(
        (UNRELATED, MODEL_DOMAIN, QUEUE_ENVELOPE), (MODEL_DOMAIN, QUEUE_ENVELOPE)
    )
    assert result.first_relevant_rank == 2
    assert result.numerator == 1
    assert result.denominator == 2


def test_no_hit_is_exact_zero() -> None:
    result = reciprocal_rank((UNRELATED, RETRIEVAL_MODULE), (MODEL_DOMAIN,))
    assert result.first_relevant_rank is None
    assert result.numerator == 0
    assert result.denominator == len((UNRELATED, RETRIEVAL_MODULE)) + 1
    assert result.score == Fraction(0, 1)


def test_empty_predictions_reciprocal_rank_is_exact_zero() -> None:
    result = reciprocal_rank((), (MODEL_DOMAIN,))
    assert result.first_relevant_rank is None
    assert result.numerator == 0
    assert result.denominator == 1
    assert result.score == Fraction(0, 1)


def test_duplicate_predictions_after_first_relevant_hit_fail_closed() -> None:
    assert_metric_error(
        LocalisationMetricErrorCode.DUPLICATE_PREDICTION,
        lambda: reciprocal_rank((MODEL_DOMAIN, UNRELATED, MODEL_DOMAIN), (MODEL_DOMAIN,)),
    )
    assert_metric_error(
        LocalisationMetricErrorCode.DUPLICATE_PREDICTION,
        lambda: reciprocal_rank((MODEL_DOMAIN, QUEUE_ENVELOPE, QUEUE_ENVELOPE), (MODEL_DOMAIN,)),
    )


# --------------------------------------------------------------------------
# Foundation properties
# --------------------------------------------------------------------------


def test_exact_score_reproducibility_from_numerator_and_denominator() -> None:
    recall_result = recall_at_k((MODEL_DOMAIN, UNRELATED), (MODEL_DOMAIN, QUEUE_ENVELOPE), 2)
    rank_result = reciprocal_rank((UNRELATED, RETRIEVAL_MODULE, MODEL_DOMAIN), (MODEL_DOMAIN,))
    for result in (recall_result, rank_result):
        assert isinstance(result.score, Fraction)
        assert result.score == Fraction(result.numerator, result.denominator)
        assert result.score * result.denominator == result.numerator
    assert rank_result.score == Fraction(1, 3)
    assert float(rank_result.score) == 1 / 3


def test_results_are_immutable_value_objects() -> None:
    result = recall_at_k((MODEL_DOMAIN,), (MODEL_DOMAIN,), 1)
    with pytest.raises(FrozenInstanceError):
        result.numerator = 99  # type: ignore[misc]
    rank = reciprocal_rank((MODEL_DOMAIN,), (MODEL_DOMAIN,))
    with pytest.raises(FrozenInstanceError):
        rank.denominator = 99  # type: ignore[misc]


def test_deterministic_repeated_results() -> None:
    def compute() -> tuple[RecallAtKResult, ReciprocalRankResult]:
        return (
            recall_at_k(
                (FileIdentity("apps/api/app/queue/envelope.py"), UNRELATED),
                (FileIdentity("apps/api/app/queue/envelope.py"), MODEL_DOMAIN),
                2,
            ),
            reciprocal_rank(
                (UNRELATED, FileIdentity("apps/api/app/queue/envelope.py")),
                (FileIdentity("apps/api/app/queue/envelope.py"),),
            ),
        )

    first = compute()
    second = compute()
    assert first == second
    assert first[0].canonical_dict() == second[0].canonical_dict()
    assert first[1].canonical_dict() == second[1].canonical_dict()
    assert first[0].canonical_dict() == {"denominator": 2, "k": 2, "numerator": 1}
    assert first[1].canonical_dict() == {
        "denominator": 2,
        "first_relevant_rank": 2,
        "numerator": 1,
    }


def test_inputs_are_never_mutated() -> None:
    predictions_list = [MODEL_DOMAIN, UNRELATED, QUEUE_ENVELOPE]
    predictions_snapshot = list(predictions_list)
    relevant_tuple = (QUEUE_ENVELOPE,)
    case = load_localisation_dataset(DATASET_PATH).cases[0]
    relevant_before = case.relevant_file_identities

    recall_at_k(predictions_list, relevant_tuple, 3)
    reciprocal_rank(predictions_list, relevant_tuple)

    assert predictions_list == predictions_snapshot
    assert predictions_list[0] is MODEL_DOMAIN
    assert predictions_list[1] is UNRELATED
    assert predictions_list[2] is QUEUE_ENVELOPE
    assert relevant_tuple == (QUEUE_ENVELOPE,)
    assert case.relevant_file_identities == relevant_before
    assert len(case.relevant_file_identities) >= 1


def test_macro_average_is_exact_and_fail_closed() -> None:
    scores = [Fraction(1, 1), Fraction(1, 2), Fraction(1, 3)]
    averaged = macro_average(scores)
    assert averaged == Fraction(11, 18)
    assert macro_average((scores[0],)) == Fraction(1, 1)
    assert_metric_error(LocalisationMetricErrorCode.INVALID_SCORES, lambda: macro_average(()))
    assert_metric_error(
        LocalisationMetricErrorCode.INVALID_SCORES, lambda: macro_average([0.5])  # type: ignore[list-item]
    )
    assert_metric_error(
        LocalisationMetricErrorCode.INVALID_SCORES, lambda: macro_average([True])  # type: ignore[list-item]
    )


# --------------------------------------------------------------------------
# Annotation resolution
# --------------------------------------------------------------------------


def test_private_raise_annotation_resolves_to_noreturn() -> None:
    hints = typing.get_type_hints(localisation_metrics._raise)
    assert hints["code"] is LocalisationMetricErrorCode
    assert hints["detail"] is str
    assert hints["return"] is typing.NoReturn


# --------------------------------------------------------------------------
# Frozen baseline dataset compatibility
# --------------------------------------------------------------------------


def test_baseline_localisation_dataset_compatibility() -> None:
    dataset = load_localisation_dataset(DATASET_PATH)
    assert len(dataset.cases) == 2
    cases_by_id = {case.case_id.value: case for case in dataset.cases}

    single = cases_by_id["RAG-BASELINE-001"]
    assert single.relevant_file_identities == (MODEL_DOMAIN,)
    recall_hit = recall_at_k((MODEL_DOMAIN, UNRELATED), single.relevant_file_identities, 2)
    assert recall_hit.canonical_dict() == {"denominator": 1, "k": 2, "numerator": 1}
    assert recall_hit.score == Fraction(1, 1)
    assert reciprocal_rank((UNRELATED, MODEL_DOMAIN), single.relevant_file_identities).score == (
        Fraction(1, 2)
    )

    multi = cases_by_id["RAG-BASELINE-002"]
    assert set(multi.relevant_file_identities) == {QUEUE_ENVELOPE, QUEUE_IDENTITIES}
    recall_at_1 = recall_at_k(
        (QUEUE_IDENTITIES, UNRELATED), multi.relevant_file_identities, 1
    )
    assert recall_at_1.canonical_dict() == {"denominator": 2, "k": 1, "numerator": 1}
    recall_at_2 = recall_at_k(
        (QUEUE_IDENTITIES, UNRELATED), multi.relevant_file_identities, 2
    )
    assert recall_at_2.numerator == 1
    assert recall_at_2.denominator == 2
    assert reciprocal_rank((QUEUE_IDENTITIES, UNRELATED), multi.relevant_file_identities).score == (
        Fraction(1, 1)
    )
    assert macro_average([recall_hit.score, recall_at_1.score]) == Fraction(3, 4)


def test_frozen_baseline_dataset_remains_unchanged() -> None:
    before_bytes = DATASET_PATH.read_bytes()
    before_sha256 = hashlib.sha256(before_bytes).hexdigest()

    dataset = load_localisation_dataset(DATASET_PATH)
    reparsed = load_localisation_dataset(DATASET_PATH)
    assert dataset.canonical_json() == reparsed.canonical_json()
    for case in dataset.cases:
        recall_at_k(case.relevant_file_identities, case.relevant_file_identities, 1)
        reciprocal_rank(case.relevant_file_identities, case.relevant_file_identities)

    after_sha256 = hashlib.sha256(DATASET_PATH.read_bytes()).hexdigest()
    assert DATASET_PATH.read_bytes() == before_bytes
    assert after_sha256 == before_sha256
