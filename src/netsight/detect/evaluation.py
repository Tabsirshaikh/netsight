"""Class-agnostic detection metrics for held-out sonar images."""

from dataclasses import dataclass, field
from math import inf

import numpy as np
from numpy.typing import NDArray

type FloatArray = NDArray[np.float64]
type BoolArray = NDArray[np.bool_]
type IntArray = NDArray[np.intp]
type Predictions = list[tuple[FloatArray, FloatArray]]

AREA_SMALL = (0.0, 32.0)
AREA_MEDIUM = (32.0, 96.0)
AREA_LARGE = (96.0, inf)


@dataclass(frozen=True)
class MatchResult:
    """Store score-sorted detections and image-ordered ground-truth metadata."""

    scores: FloatArray
    is_tp: BoolArray
    gt_sizes: FloatArray
    gt_matched_score: FloatArray
    n_images: int
    n_gt: int
    # Global GT indices, or -1 for FPs. Preserve exact size associations at ties.
    _matched_gt_indices: IntArray = field(repr=False)


def _validate_boxes(boxes: FloatArray) -> FloatArray:
    """Return float boxes after validating shape, finiteness, and extent."""
    array = np.asarray(boxes, dtype=np.float64)
    if array.ndim != 2 or array.shape[1] != 4:
        raise ValueError("Boxes must have shape (n, 4).")
    if not np.all(np.isfinite(array)):
        raise ValueError("Box coordinates must be finite.")
    if np.any(array[:, 2:] <= array[:, :2]):
        raise ValueError("Boxes must have positive width and height.")
    return array


def _iou(a: FloatArray, b: FloatArray) -> FloatArray:
    """Compute pairwise IoU for validated boxes."""
    lower = np.maximum(a[:, None, :2], b[None, :, :2])
    upper = np.minimum(a[:, None, 2:], b[None, :, 2:])
    extent = np.maximum(upper - lower, 0.0)
    intersection = extent[..., 0] * extent[..., 1]
    a_extent = a[:, 2:] - a[:, :2]
    b_extent = b[:, 2:] - b[:, :2]
    a_area = a_extent[:, 0] * a_extent[:, 1]
    b_area = b_extent[:, 0] * b_extent[:, 1]
    union = a_area[:, None] + b_area[None, :] - intersection
    return intersection / union


def iou_matrix(a: FloatArray, b: FloatArray) -> FloatArray:
    """Return pairwise intersection-over-union with shape (len(a), len(b))."""
    return _iou(_validate_boxes(a), _validate_boxes(b))


def match_detections(
    predictions: Predictions,
    ground_truth: list[FloatArray],
    *,
    iou_threshold: float = 0.5,
) -> MatchResult:
    """Greedily match detections per image, using stable descending score order."""
    if len(predictions) != len(ground_truth):
        raise ValueError("Predictions and ground truth must have equal lengths.")
    if not np.isfinite(iou_threshold) or not 0.0 <= iou_threshold <= 1.0:
        raise ValueError("IoU threshold must be finite and in [0, 1].")

    score_parts: list[FloatArray] = []
    index_parts: list[IntArray] = []
    size_parts: list[FloatArray] = []
    matched_score_parts: list[FloatArray] = []
    offset = 0

    for (boxes, scores), gt_boxes in zip(predictions, ground_truth, strict=True):
        boxes = _validate_boxes(boxes)
        gt_boxes = _validate_boxes(gt_boxes)
        scores = np.asarray(scores, dtype=np.float64)
        if scores.shape != (len(boxes),):
            raise ValueError("Scores must have shape (n,) matching the boxes.")
        if not np.all(np.isfinite(scores)) or np.any((scores < 0.0) | (scores > 1.0)):
            raise ValueError("Scores must be finite and in [0, 1].")

        order = np.argsort(-scores, kind="stable")
        sorted_scores = scores[order]
        overlaps = _iou(boxes[order], gt_boxes)
        available = np.ones(len(gt_boxes), dtype=np.bool_)
        matched_indices = np.full(len(boxes), -1, dtype=np.intp)
        matched_scores = np.full(len(gt_boxes), np.nan, dtype=np.float64)

        for pred_index, score in enumerate(sorted_scores):
            candidates = np.flatnonzero(available & (overlaps[pred_index] >= iou_threshold))
            if candidates.size:
                gt_index = int(candidates[np.argmax(overlaps[pred_index, candidates])])
                available[gt_index] = False
                matched_indices[pred_index] = offset + gt_index
                matched_scores[gt_index] = score

        extent = gt_boxes[:, 2:] - gt_boxes[:, :2]
        size_parts.append(np.sqrt(extent[:, 0] * extent[:, 1]))
        matched_score_parts.append(matched_scores)
        score_parts.append(sorted_scores)
        index_parts.append(matched_indices)
        offset += len(gt_boxes)

    scores = np.concatenate(score_parts) if score_parts else np.empty(0, dtype=np.float64)
    indices = np.concatenate(index_parts) if index_parts else np.empty(0, dtype=np.intp)
    order = np.argsort(-scores, kind="stable")
    indices = indices[order]

    return MatchResult(
        scores=scores[order],
        is_tp=indices >= 0,
        gt_sizes=np.concatenate(size_parts) if size_parts else np.empty(0, dtype=np.float64),
        gt_matched_score=(
            np.concatenate(matched_score_parts)
            if matched_score_parts
            else np.empty(0, dtype=np.float64)
        ),
        n_images=len(ground_truth),
        n_gt=offset,
        _matched_gt_indices=indices,
    )


def average_precision(
    match: MatchResult,
    *,
    size_range: tuple[float, float] | None = None,
) -> float:
    """Compute all-point interpolated AP, optionally for sizes in [lo, hi).

    Matches to GT outside the size range are ignored; unmatched predictions
    still count as false positives. Return NaN when no GT is in range.
    """
    selected_gt = np.ones(match.n_gt, dtype=np.bool_)
    if size_range is not None:
        lo, hi = size_range
        if np.isnan(lo) or np.isnan(hi) or not 0.0 <= lo < hi:
            raise ValueError("Size range must satisfy 0 <= lo < hi.")
        selected_gt = (match.gt_sizes >= lo) & (match.gt_sizes < hi)

    n_gt = int(np.count_nonzero(selected_gt))
    if n_gt == 0:
        return float("nan")

    keep = np.ones(len(match.scores), dtype=np.bool_)
    if size_range is not None:
        keep[match.is_tp] = selected_gt[match._matched_gt_indices[match.is_tp]]

    is_tp = match.is_tp[keep]
    if is_tp.size == 0:
        return 0.0

    tp = np.cumsum(is_tp, dtype=np.float64)
    fp = np.cumsum(~is_tp, dtype=np.float64)
    recall = tp / n_gt
    precision = tp / (tp + fp)
    recall = np.concatenate(([0.0], recall, [1.0]))
    precision = np.concatenate(([0.0], precision, [0.0]))
    precision = np.maximum.accumulate(precision[::-1])[::-1]
    return float(np.sum(np.diff(recall) * precision[1:]))


def recall_at_fp_per_image(
    match: MatchResult,
    fp_per_image: float,
) -> tuple[float, float]:
    """Return recall and the lowest feasible inclusive score threshold.

    Equal-score detections enter together. Return (0, inf) if no nonempty
    detection prefix fits the budget; recall is zero when there is no GT.
    """
    if np.isnan(fp_per_image) or fp_per_image < 0.0:
        raise ValueError("FP per image must be nonnegative and not NaN.")
    if match.n_images == 0 or match.scores.size == 0:
        return 0.0, inf

    tp = np.cumsum(match.is_tp, dtype=np.int64)
    fp = np.cumsum(~match.is_tp, dtype=np.int64)
    group_ends = np.flatnonzero(np.concatenate((match.scores[:-1] != match.scores[1:], [True])))
    feasible = group_ends[fp[group_ends] / match.n_images <= fp_per_image]
    if feasible.size == 0:
        return 0.0, inf

    end = int(feasible[-1])
    recall = float(tp[end] / match.n_gt) if match.n_gt else 0.0
    return recall, float(match.scores[end])


def froc(
    match: MatchResult,
    fp_per_image_points: tuple[float, ...] = (0.1, 0.25, 0.5, 1, 2, 4, 8),
) -> list[tuple[float, float, float]]:
    """Return requested FP/image budgets with their recalls and thresholds."""
    return [(point, *recall_at_fp_per_image(match, point)) for point in fp_per_image_points]
