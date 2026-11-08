"""Correct survey pixel geometry before detection."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy.ndimage import zoom

from netsight.trust.geometry_gate import (
    AspectProfile,
    GeometryEnvelope,
    geometry_reasons,
    suggest_resampling,
)

type Prediction = tuple[np.ndarray, np.ndarray]
type Predictor = Callable[[np.ndarray], Prediction]
type CorrectionSource = Literal["metadata", "estimated", "none"]


def _positive_finite(**values: float) -> None:
    """Reject nonpositive or nonfinite geometry values."""
    for name, value in values.items():
        if not np.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be positive and finite")


def spacing_from_metadata(
    *,
    range_m: float,
    samples_per_side: int,
    ping_rate_hz: float,
    speed_mps: float,
) -> tuple[float, float]:
    """Return along-track and across-track spacing in metres per pixel."""
    _positive_finite(
        range_m=range_m,
        samples_per_side=samples_per_side,
        ping_rate_hz=ping_rate_hz,
        speed_mps=speed_mps,
    )
    return speed_mps / ping_rate_hz, range_m / samples_per_side


def factors_from_spacing(
    along_m: float,
    across_m: float,
    *,
    target_m: float,
) -> tuple[float, float]:
    """Return square-pixel factors, each clipped independently to [0.25, 4.0].

    Clipping can prevent the requested spacing or square geometry being reached.
    """
    _positive_finite(along_m=along_m, across_m=across_m, target_m=target_m)
    row_scale = float(np.clip(along_m / across_m, 0.25, 4.0))
    scale = float(np.clip(across_m / target_m, 0.25, 4.0))
    return row_scale, scale


def resample_image(image: np.ndarray, row_scale: float, scale: float) -> np.ndarray:
    """Resample a 2-D image linearly, preserving its dtype and intensity range."""
    _positive_finite(row_scale=row_scale, scale=scale)
    if row_scale == 1.0 and scale == 1.0:
        return image
    if image.ndim != 2 or image.size == 0:
        raise ValueError("image must be a nonempty 2-D array")
    result = zoom(image, (row_scale * scale, scale), order=1)
    np.clip(result, image.min(), image.max(), out=result)
    return result


def boxes_to_original(
    boxes: np.ndarray,
    row_scale: float,
    scale: float,
) -> np.ndarray:
    """Map xyxy boxes from resampled coordinates to original coordinates."""
    _positive_finite(row_scale=row_scale, scale=scale)
    result = np.array(boxes, dtype=np.float64, copy=True)
    result[..., [0, 2]] /= scale
    result[..., [1, 3]] /= row_scale * scale
    return result


@dataclass(frozen=True)
class SurveyCorrection:
    """Record survey-wide resampling factors and geometry diagnostics."""

    row_scale: float
    scale: float
    source: CorrectionSource
    reasons_before: list[str]
    reasons_after: list[str] | None
    n_boxes_first_pass: int


def _profile(predictions: Sequence[Prediction], min_score: float) -> AspectProfile:
    """Pool detections into a deterministic survey profile."""
    if predictions:
        boxes = np.concatenate([boxes for boxes, _ in predictions], axis=0)
        scores = np.concatenate([scores for _, scores in predictions], axis=0)
    else:
        boxes = np.empty((0, 4), dtype=np.float64)
        scores = np.empty(0, dtype=np.float64)
    return AspectProfile.from_boxes(boxes, scores, min_score=min_score, seed=0)


def _resampled_predictions(
    predict: Predictor,
    images: Sequence[np.ndarray],
    row_scale: float,
    scale: float,
) -> tuple[list[Prediction], list[Prediction]]:
    """Return detector-space and original-space predictions."""
    measured: list[Prediction] = []
    original: list[Prediction] = []
    for image in images:
        boxes, scores = predict(resample_image(image, row_scale, scale))
        measured.append((boxes, scores))
        original.append((boxes_to_original(boxes, row_scale, scale), scores))
    return measured, original


def two_pass_predict(
    predict: Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]],
    images: Sequence[np.ndarray],
    envelope: GeometryEnvelope,
    *,
    spacing: tuple[float, float] | None = None,
    target_m: float | None = None,
    min_boxes: int = 30,
    min_score: float = 0.3,
) -> tuple[list[tuple[np.ndarray, np.ndarray]], SurveyCorrection]:
    """Predict using metadata or a survey-wide first-pass geometry estimate.

    Metadata skips the original-image pass, so its before diagnostics are empty
    and its first-pass count is zero. After diagnostics describe only an
    estimated correction, in the detector's resampled coordinate system.
    """
    if spacing is not None and target_m is not None:
        row_scale, scale = factors_from_spacing(*spacing, target_m=target_m)
        _, predictions = _resampled_predictions(predict, images, row_scale, scale)
        return predictions, SurveyCorrection(
            row_scale=row_scale,
            scale=scale,
            source="metadata",
            reasons_before=[],
            reasons_after=None,
            n_boxes_first_pass=0,
        )

    first_pass = [predict(image) for image in images]
    profile = _profile(first_pass, min_score)
    reasons_before = geometry_reasons(profile, envelope, min_boxes=min_boxes)
    n_boxes = sum(len(boxes) for boxes, _ in first_pass)
    n_qualified = sum(int(np.count_nonzero(scores >= min_score)) for _, scores in first_pass)
    row_scale, scale = suggest_resampling(profile, envelope)
    if n_qualified < min_boxes or (row_scale == 1.0 and scale == 1.0):
        return first_pass, SurveyCorrection(
            row_scale=1.0,
            scale=1.0,
            source="none",
            reasons_before=reasons_before,
            reasons_after=None,
            n_boxes_first_pass=n_boxes,
        )

    measured, predictions = _resampled_predictions(predict, images, row_scale, scale)
    reasons_after = geometry_reasons(_profile(measured, min_score), envelope, min_boxes=min_boxes)
    return predictions, SurveyCorrection(
        row_scale=row_scale,
        scale=scale,
        source="estimated",
        reasons_before=reasons_before,
        reasons_after=reasons_after,
        n_boxes_first_pass=n_boxes,
    )
