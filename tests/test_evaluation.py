"""Hand-computed tests for detection evaluation."""

from math import inf

import numpy as np
import pytest
from numpy.typing import NDArray

from netsight.detect.evaluation import (
    AREA_LARGE,
    AREA_MEDIUM,
    AREA_SMALL,
    MatchResult,
    average_precision,
    froc,
    iou_matrix,
    match_detections,
    recall_at_fp_per_image,
)


def boxes(*rows: tuple[float, float, float, float]) -> NDArray[np.float64]:
    """Build a box array, including the empty case."""
    return np.asarray(rows, dtype=np.float64).reshape(-1, 4)


def scores(*values: float) -> NDArray[np.float64]:
    """Build a score array."""
    return np.asarray(values, dtype=np.float64)


@pytest.fixture
def hand_match() -> MatchResult:
    """Provide two images with TP, FP, TP, TP in descending score order."""
    first = boxes((0, 0, 10, 10), (20, 0, 30, 10))
    second = boxes((0, 0, 10, 10))
    predictions = [
        (
            boxes((0, 0, 10, 10), (40, 0, 50, 10), (20, 0, 30, 10)),
            scores(0.9, 0.8, 0.7),
        ),
        (second, scores(0.6)),
    ]
    return match_detections(predictions, [first, second])


def test_iou_matrix() -> None:
    a = boxes((0, 0, 10, 10), (20, 0, 30, 10))
    b = boxes((0, 0, 10, 10), (5, 0, 15, 10))
    # Half-width overlap: intersection 50, union 100 + 100 - 50 = 150.
    np.testing.assert_allclose(iou_matrix(a, b), [[1.0, 1.0 / 3.0], [0.0, 0.0]])
    assert iou_matrix(boxes(), b).shape == (0, 2)
    assert iou_matrix(a, boxes()).shape == (2, 0)


def test_perfect_detector() -> None:
    gt = boxes((0, 0, 10, 10), (20, 0, 30, 10))
    match = match_detections([(gt, scores(0.4, 0.9))], [gt])
    assert average_precision(match) == 1.0
    assert recall_at_fp_per_image(match, 0.0) == (1.0, 0.4)
    np.testing.assert_array_equal(match.scores, [0.9, 0.4])
    assert match.n_images == 1
    assert match.n_gt == 2


def test_hand_computed_ap(hand_match: MatchResult) -> None:
    np.testing.assert_array_equal(hand_match.scores, [0.9, 0.8, 0.7, 0.6])
    np.testing.assert_array_equal(hand_match.is_tp, [True, False, True, True])
    tp = np.cumsum(hand_match.is_tp)
    np.testing.assert_allclose(tp / 3, [1 / 3, 1 / 3, 2 / 3, 1])
    np.testing.assert_allclose(tp / np.arange(1, 5), [1, 1 / 2, 2 / 3, 3 / 4])
    # Recall: 1/3, 1/3, 2/3, 1; precision: 1, 1/2, 2/3, 3/4.
    # Interpolated precision at recall increases: 1, 3/4, 3/4.
    # AP = (1/3)*1 + (1/3)*0.75 + (1/3)*0.75 = 5/6.
    assert average_precision(hand_match) == pytest.approx(5 / 6, abs=1e-9, rel=0)


def test_duplicate_is_false_positive() -> None:
    gt = boxes((0, 0, 10, 10))
    pred = boxes((0, 0, 10, 10), (0, 0, 10, 10))
    match = match_detections([(pred, scores(0.8, 0.7))], [gt])
    np.testing.assert_array_equal(match.is_tp, [True, False])


def test_matched_scores_and_sizes() -> None:
    gt = boxes((0, 0, 10, 10), (20, 0, 40, 20))
    match = match_detections(
        [(boxes((0, 0, 10, 10)), scores(0.75))],
        [gt],
    )
    np.testing.assert_allclose(match.gt_sizes, [10.0, 20.0])
    assert match.gt_matched_score[0] == 0.75
    assert np.isnan(match.gt_matched_score[1])


def test_size_ranges() -> None:
    small = (0.0, 0.0, 10.0, 10.0)
    medium = (100.0, 0.0, 132.0, 32.0)
    large = (200.0, 0.0, 296.0, 96.0)
    missed_small = (400.0, 0.0, 420.0, 20.0)
    false_positive = (500.0, 0.0, 510.0, 10.0)
    match = match_detections(
        [(boxes(medium, false_positive, small, large), scores(0.9, 0.8, 0.7, 0.6))],
        [boxes(small, medium, large, missed_small)],
    )
    # Medium and large matches are ignored: FP, TP gives precision 1/2
    # and maximum recall 1/2 for the two small objects, hence AP 1/4.
    assert average_precision(match, size_range=AREA_SMALL) == pytest.approx(0.25)
    assert average_precision(match, size_range=AREA_MEDIUM) == 1.0
    assert average_precision(match, size_range=AREA_LARGE) == pytest.approx(0.5)
    assert np.isnan(average_precision(match, size_range=(21.0, 31.0)))


def test_size_association_preserved_at_equal_scores() -> None:
    small = (0.0, 0.0, 10.0, 10.0)
    medium = (100.0, 0.0, 140.0, 40.0)
    false_positive = (200.0, 0.0, 210.0, 10.0)
    match = match_detections(
        [(boxes(medium, false_positive, small), scores(0.5, 0.5, 0.5))],
        [boxes(small, medium)],
    )
    assert average_precision(match, size_range=AREA_SMALL) == 0.5
    assert average_precision(match, size_range=AREA_MEDIUM) == 1.0


def test_recall_and_froc(hand_match: MatchResult) -> None:
    assert recall_at_fp_per_image(hand_match, 0.0) == (1 / 3, 0.9)
    assert recall_at_fp_per_image(hand_match, 0.49) == (1 / 3, 0.9)
    assert recall_at_fp_per_image(hand_match, 0.5) == (1.0, 0.6)
    assert froc(hand_match, (0.0, 0.25, 0.5, 1.0)) == [
        (0.0, 1 / 3, 0.9),
        (0.25, 1 / 3, 0.9),
        (0.5, 1.0, 0.6),
        (1.0, 1.0, 0.6),
    ]
    assert [point for point, _, _ in froc(hand_match)] == [0.1, 0.25, 0.5, 1, 2, 4, 8]


def test_equal_scores_enter_together() -> None:
    gt = boxes((0, 0, 10, 10))
    pred = boxes((0, 0, 10, 10), (20, 0, 30, 10))
    match = match_detections([(pred, scores(0.5, 0.5))], [gt])
    np.testing.assert_array_equal(match.is_tp, [True, False])
    assert recall_at_fp_per_image(match, 0.0) == (0.0, inf)
    assert recall_at_fp_per_image(match, 1.0) == (1.0, 0.5)


def test_matching_chooses_best_available_gt() -> None:
    gt = boxes((0, 0, 10, 10), (2, 0, 12, 10))
    pred = boxes((2, 0, 12, 10), (2, 0, 12, 10))
    match = match_detections([(pred, scores(0.9, 0.8))], [gt])
    np.testing.assert_array_equal(match.is_tp, [True, True])
    np.testing.assert_allclose(match.gt_matched_score, [0.8, 0.9])


def test_iou_threshold_is_inclusive() -> None:
    gt = boxes((0, 0, 10, 10))
    pred = boxes((0, 0, 5, 10))
    match = match_detections([(pred, scores(0.9))], [gt], iou_threshold=0.5)
    assert match.is_tp.tolist() == [True]


def test_empty_predictions() -> None:
    gt = [boxes((0, 0, 10, 10)), boxes()]
    match = match_detections([(boxes(), scores()), (boxes(), scores())], gt)
    assert average_precision(match) == 0.0
    assert recall_at_fp_per_image(match, 0.0) == (0.0, inf)
    assert match.n_images == 2
    assert np.isnan(match.gt_matched_score).all()


def test_no_ground_truth_or_images() -> None:
    empty = match_detections([], [])
    assert np.isnan(average_precision(empty))
    assert recall_at_fp_per_image(empty, 1.0) == (0.0, inf)
    match = match_detections(
        [(boxes((0, 0, 10, 10)), scores(0.8))],
        [boxes()],
    )
    assert match.is_tp.tolist() == [False]
    assert np.isnan(average_precision(match))
    assert recall_at_fp_per_image(match, 0.0) == (0.0, inf)
    assert recall_at_fp_per_image(match, 1.0) == (0.0, 0.8)


def test_mismatched_image_counts() -> None:
    with pytest.raises(ValueError):
        match_detections([(boxes(), scores())], [])


@pytest.mark.parametrize(
    "bad",
    [
        np.zeros(4),
        np.zeros((1, 3)),
        np.zeros((1, 4, 1)),
        boxes((0, 0, 0, 1)),
        boxes((1, 0, 0, 1)),
        boxes((0, 0, 1, 0)),
        boxes((0, 1, 1, 0)),
        boxes((0, 0, np.nan, 1)),
        boxes((0, 0, inf, 1)),
    ],
)
def test_invalid_boxes(bad: NDArray[np.float64]) -> None:
    valid = boxes((0, 0, 1, 1))
    with pytest.raises(ValueError):
        iou_matrix(bad, valid)
    with pytest.raises(ValueError):
        iou_matrix(valid, bad)
    with pytest.raises(ValueError):
        match_detections([(bad, scores(0.5))], [valid])
    with pytest.raises(ValueError):
        match_detections([(valid, scores(0.5))], [bad])


@pytest.mark.parametrize(
    "bad_scores",
    [
        np.asarray(0.5),
        np.asarray([[0.5]]),
        scores(),
        scores(0.5, 0.6),
        scores(-0.01),
        scores(1.01),
        scores(np.nan),
        scores(inf),
        scores(-inf),
    ],
)
def test_invalid_scores(bad_scores: NDArray[np.float64]) -> None:
    valid = boxes((0, 0, 1, 1))
    with pytest.raises(ValueError):
        match_detections([(valid, bad_scores)], [valid])


@pytest.mark.parametrize("threshold", [-0.1, 1.1, np.nan, inf])
def test_invalid_iou_threshold(threshold: float) -> None:
    with pytest.raises(ValueError):
        match_detections([], [], iou_threshold=threshold)


@pytest.mark.parametrize("size_range", [(-1.0, 1.0), (1.0, 1.0), (2.0, 1.0), (0.0, np.nan)])
def test_invalid_size_range(
    hand_match: MatchResult,
    size_range: tuple[float, float],
) -> None:
    with pytest.raises(ValueError):
        average_precision(hand_match, size_range=size_range)


@pytest.mark.parametrize("budget", [-1.0, np.nan])
def test_invalid_fp_budget(hand_match: MatchResult, budget: float) -> None:
    with pytest.raises(ValueError):
        recall_at_fp_per_image(hand_match, budget)
    with pytest.raises(ValueError):
        froc(hand_match, (budget,))
