"""Fit detector-score calibrators and evaluate them on held-out detections."""

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from netsight.detect.evaluation import match_detections
from netsight.trust.calibration_metrics import (
    brier_score,
    expected_calibration_error,
    log_loss,
    max_calibration_error,
    reliability_table,
)
from netsight.trust.calibrators import (
    BetaCalibrator,
    IsotonicCalibrator,
    PlattCalibrator,
    TemperatureScaling,
)

type FloatArray = NDArray[np.float64]
type IntArray = NDArray[np.int64]
type ReliabilityRow = dict[str, float | int]


def detection_pairs(
    predictions: list[tuple[NDArray, NDArray]],
    ground_truth: list[NDArray],
    *,
    iou_threshold: float = 0.5,
    min_score: float = 0.0,
) -> tuple[FloatArray, IntArray]:
    """Return score/TP-label pairs, sorted by descending score.

    Missed objects (false negatives) have no score and are not part of score
    calibration; they belong to recall/Pd, which must be reported separately.
    """
    matched = match_detections(predictions, ground_truth, iou_threshold=iou_threshold)
    scores = np.asarray(matched.scores, dtype=np.float64)
    labels = np.asarray(matched.is_tp, dtype=np.int64)
    keep = scores >= min_score
    return scores[keep], labels[keep]


@dataclass(frozen=True)
class CalibrationResult:
    """Held-out performance for one calibration method."""

    method: str
    fitted: bool
    reason: str
    n_fit: int
    test_brier: float
    test_log_loss: float
    test_ece: float
    test_mce: float
    reliability: list[ReliabilityRow]


def _validated_pairs(
    scores: ArrayLike,
    labels: ArrayLike,
    *,
    name: str,
) -> tuple[FloatArray, IntArray]:
    """Validate one nonempty set of probability/label pairs."""
    p = np.asarray(scores, dtype=np.float64)
    y = np.asarray(labels)
    if p.ndim != 1 or y.ndim != 1:
        raise ValueError(f"{name} scores and labels must be one-dimensional")
    if p.size != y.size:
        raise ValueError(f"{name} scores and labels must have matching lengths")
    if p.size == 0:
        raise ValueError(f"{name} arrays must not be empty")
    if not np.all(np.isfinite(p)) or np.any((p < 0.0) | (p > 1.0)):
        raise ValueError(f"{name} scores must be finite probabilities in [0, 1]")
    if not np.all((y == 0) | (y == 1)):
        raise ValueError(f"{name} labels must be binary")
    return p, y.astype(np.int64)


def calibration_report(
    fit_scores: ArrayLike,
    fit_labels: ArrayLike,
    test_scores: ArrayLike,
    test_labels: ArrayLike,
    *,
    methods: Sequence[str] = ("raw", "temperature", "platt", "beta", "isotonic"),
    n_bins: int = 10,
    isotonic_min_samples: int = 200,
) -> list[CalibrationResult]:
    """Fit on fit pairs and evaluate exclusively on held-out test pairs.

    Callers must provide disjoint fit and test data. If this report is used to
    select a method, use a further untouched split for final performance claims.
    """
    fit_p, fit_y = _validated_pairs(fit_scores, fit_labels, name="fit")
    test_p, test_y = _validated_pairs(test_scores, test_labels, name="test")
    if n_bins < 1:
        raise ValueError("n_bins must be positive")

    supported = {"raw", "temperature", "platt", "beta", "isotonic"}
    unknown = set(methods) - supported
    if unknown:
        raise ValueError(f"Unknown calibration methods: {', '.join(sorted(unknown))}")

    results: list[CalibrationResult] = []
    for method in methods:
        if method == "raw":
            probabilities = test_p
        else:
            calibrator: TemperatureScaling | PlattCalibrator | BetaCalibrator | IsotonicCalibrator
            if method == "temperature":
                calibrator = TemperatureScaling()
            elif method == "platt":
                calibrator = PlattCalibrator()
            elif method == "beta":
                calibrator = BetaCalibrator()
            else:
                calibrator = IsotonicCalibrator(min_samples=isotonic_min_samples)

            try:
                calibrator.fit(fit_p, fit_y)
            except ValueError as exc:
                results.append(
                    CalibrationResult(
                        method=method,
                        fitted=False,
                        reason=str(exc),
                        n_fit=int(fit_p.size),
                        test_brier=float("nan"),
                        test_log_loss=float("nan"),
                        test_ece=float("nan"),
                        test_mce=float("nan"),
                        reliability=[],
                    )
                )
                continue
            probabilities = np.asarray(calibrator.predict(test_p), dtype=np.float64)

        rows: list[ReliabilityRow] = [
            {
                "lower": float(row.lower),
                "upper": float(row.upper),
                "count": int(row.count),
                "mean_predicted": float(row.mean_predicted),
                "observed_rate": float(row.observed_rate),
                "ci_low": float(row.ci_low),
                "ci_high": float(row.ci_high),
            }
            for row in reliability_table(probabilities, test_y, n_bins=n_bins)
        ]
        results.append(
            CalibrationResult(
                method=method,
                fitted=True,
                reason="",
                n_fit=int(fit_p.size),
                test_brier=float(brier_score(probabilities, test_y)),
                test_log_loss=float(log_loss(probabilities, test_y)),
                test_ece=float(expected_calibration_error(probabilities, test_y, n_bins=n_bins)),
                test_mce=float(max_calibration_error(probabilities, test_y, n_bins=n_bins)),
                reliability=rows,
            )
        )
    return results


def best_method(results: Sequence[CalibrationResult]) -> str:
    """Choose by held-out Brier, then ECE. Raw scores win if no calibrator beats them."""
    candidates = [result for result in results if result.fitted]
    if not candidates:
        raise ValueError("No fitted calibration methods")
    return min(candidates, key=lambda result: (result.test_brier, result.test_ece)).method


def _markdown_cell(text: str) -> str:
    """Escape table separators and flatten line breaks."""
    return " ".join(text.splitlines()).replace("|", r"\|")


def report_markdown(
    results: Sequence[CalibrationResult],
    *,
    title: str,
) -> str:
    """Render a compact held-out performance table and selection."""
    lines = [
        f"## {' '.join(title.splitlines())}",
        "",
        "| Method | Fitted/reason | Brier | Log loss | ECE | MCE |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for result in results:
        status = "yes" if result.fitted else f"no: {result.reason}"
        metrics = (
            result.test_brier,
            result.test_log_loss,
            result.test_ece,
            result.test_mce,
        )
        values = " | ".join(f"{value:.4f}" for value in metrics)
        lines.append(f"| {_markdown_cell(result.method)} | {_markdown_cell(status)} | {values} |")

    winner = best_method(results) if any(result.fitted for result in results) else "none"
    lines.extend(["", f"Best method: **{_markdown_cell(winner)}**."])
    return "\n".join(lines)
