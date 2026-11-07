"""Tests for held-out detector-score calibration."""

from dataclasses import replace

import numpy as np
import pytest

from netsight.trust.detector_calibration import (
    CalibrationResult,
    best_method,
    calibration_report,
    detection_pairs,
    report_markdown,
)


@pytest.fixture
def simulated_report() -> list[CalibrationResult]:
    """Generate independent fit/test detections with overconfident scores."""
    rng = np.random.default_rng(0)
    scores = rng.uniform(0.5, 0.99, size=5_000)
    labels = (rng.random(5_000) < scores**2).astype(np.int64)
    return calibration_report(
        scores[:3_500],
        labels[:3_500],
        scores[3_500:],
        labels[3_500:],
    )


def test_detection_pairs_and_score_filter() -> None:
    """Matching labels include false alarms but not missed-object scores."""
    ground_truth = [
        np.array([[0, 0, 10, 10], [20, 20, 30, 30]], dtype=float),
        np.array([[5, 5, 15, 15]], dtype=float),
    ]
    predictions = [
        (
            np.array(
                [[20, 20, 30, 30], [40, 40, 50, 50], [0, 0, 10, 10]],
                dtype=float,
            ),
            np.array([0.8, 0.9, 0.95]),
        ),
        (np.array([[5, 5, 15, 15]], dtype=float), np.array([0.7])),
    ]

    scores, labels = detection_pairs(predictions, ground_truth)
    np.testing.assert_allclose(scores, [0.95, 0.9, 0.8, 0.7])
    np.testing.assert_array_equal(labels, [1, 0, 1, 1])
    assert np.issubdtype(scores.dtype, np.floating)
    assert np.issubdtype(labels.dtype, np.integer)

    scores, labels = detection_pairs(predictions, ground_truth, min_score=0.8)
    np.testing.assert_allclose(scores, [0.95, 0.9, 0.8])
    np.testing.assert_array_equal(labels, [1, 0, 1])

    scores, labels = detection_pairs(predictions, ground_truth, min_score=1.0)
    assert scores.size == labels.size == 0


def test_calibrators_improve_held_out_ece(
    simulated_report: list[CalibrationResult],
) -> None:
    """All calibrators improve ECE on detections they did not fit."""
    raw = next(result for result in simulated_report if result.method == "raw")
    assert len(simulated_report) == 5
    for result in simulated_report:
        assert result.fitted, result.reason
        assert result.reason == ""
        assert result.n_fit == 3_500
        assert np.all(
            np.isfinite([result.test_brier, result.test_log_loss, result.test_ece, result.test_mce])
        )
        assert sum(row["count"] for row in result.reliability) == 1_500
        if result.method != "raw":
            assert result.test_ece < raw.test_ece, result.method
    assert best_method(simulated_report) != "raw"


def test_insufficient_fit_samples_are_reported() -> None:
    """A calibrator's fit rejection becomes a failed report row."""
    scores = np.linspace(0.01, 0.99, 100)
    labels = np.tile([0, 1], 50)
    results = calibration_report(
        scores,
        labels,
        scores[:20],
        labels[:20],
        methods=("raw", "isotonic"),
        isotonic_min_samples=10_000,
    )
    raw, isotonic = results
    assert raw.fitted
    assert not isotonic.fitted
    assert isotonic.reason
    assert isotonic.n_fit == 100
    assert isotonic.reliability == []
    assert np.all(
        np.isnan(
            [
                isotonic.test_brier,
                isotonic.test_log_loss,
                isotonic.test_ece,
                isotonic.test_mce,
            ]
        )
    )
    assert best_method(results) == "raw"
    assert isotonic.reason in report_markdown(results, title="Insufficient data")


def test_markdown(simulated_report: list[CalibrationResult]) -> None:
    """Markdown includes all methods, metric headings, and the winner."""
    text = report_markdown(simulated_report, title="Held-out calibration")
    assert text.startswith("## Held-out calibration")
    for result in simulated_report:
        assert f"| {result.method} |" in text
    for heading in ("Brier", "Log loss", "ECE", "MCE"):
        assert heading in text
    assert f"Best method: **{best_method(simulated_report)}**." in text


def test_best_method_ranking(simulated_report: list[CalibrationResult]) -> None:
    """Lowest held-out Brier wins (raw included); Brier ties are broken by ECE."""
    base = simulated_report[0]
    raw = replace(base, method="raw", test_brier=0.0, test_ece=0.0)
    platt = replace(base, method="platt", test_brier=0.2, test_ece=0.03)
    beta = replace(base, method="beta", test_brier=0.2, test_ece=0.02)
    assert best_method([raw, platt, beta]) == "raw"  # raw already perfect: no calibrator
    assert best_method([platt, beta]) == "beta"
    assert best_method([raw]) == "raw"
    with pytest.raises(ValueError, match="No fitted"):
        best_method([])


@pytest.mark.parametrize(
    ("fit_scores", "fit_labels", "test_scores", "test_labels"),
    [
        ([], [], [0.5], [1]),
        ([0.5], [1], [], []),
        ([0.2, 0.8], [0], [0.5], [1]),
        ([0.5], [1], [0.2, 0.8], [0]),
        ([], [0], [0.5], [1]),
        ([0.5], [1], [], [0]),
    ],
)
def test_invalid_array_lengths(
    fit_scores: list[float],
    fit_labels: list[int],
    test_scores: list[float],
    test_labels: list[int],
) -> None:
    """Empty inputs and mismatched lengths fail before fitting."""
    with pytest.raises(ValueError):
        calibration_report(fit_scores, fit_labels, test_scores, test_labels)
