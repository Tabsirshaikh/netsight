"""Hand-computed checks for calibration metrics and input handling."""

import math

import numpy as np
import pytest

from netsight.trust.calibration_metrics import (
    brier_score,
    calibration_summary,
    expected_calibration_error,
    log_loss,
    max_calibration_error,
    reliability_table,
    wilson_interval,
)


def test_perfectly_calibrated_toy_data() -> None:
    p = [0.25] * 4 + [0.75] * 4
    y = [1, 0, 0, 0, 1, 1, 1, 0]

    assert expected_calibration_error(p, y, n_bins=2) == 0.0
    assert max_calibration_error(p, y, n_bins=2) == 0.0
    bins = reliability_table(p, y, n_bins=2)
    assert [bin_.count for bin_ in bins] == [4, 4]
    assert [bin_.observed_rate for bin_ in bins] == [0.25, 0.75]


def test_hand_computed_brier_and_log_loss() -> None:
    p = [0.25, 0.5, 0.75]
    y = [0, 1, 1]

    assert brier_score(p, y) == pytest.approx(0.125)
    assert log_loss(p, y) == pytest.approx(-math.log(9.0 / 32.0) / 3.0)


def test_hand_computed_calibration_errors() -> None:
    p = [0.0, 0.25, 0.75]
    y = [0, 1, 0]

    # First-bin gap: |1/2 - 1/8| = 3/8; second-bin gap: 3/4.
    assert expected_calibration_error(p, y, n_bins=2) == pytest.approx(0.5)
    assert max_calibration_error(p, y, n_bins=2) == pytest.approx(0.75)


def test_nan_pairs_are_dropped_and_counted() -> None:
    p = [0.25, np.nan, 0.9, 0.75, np.nan]
    y = [0, 1, np.nan, 1, np.nan]

    summary = calibration_summary(p, y, n_bins=2)
    assert summary["n"] == 2
    assert summary["n_dropped"] == 3
    assert summary["positives"] == 1
    assert summary["base_rate"] == 0.5
    assert summary["brier"] == pytest.approx(1.0 / 16.0)
    assert summary["log_loss"] == pytest.approx(-math.log(0.75))
    assert summary["ece"] == pytest.approx(0.25)
    assert summary["mce"] == pytest.approx(0.25)
    assert sum(bin_.count for bin_ in reliability_table(p, y)) == 2


@pytest.mark.parametrize(
    ("p", "y"),
    [
        ([np.nan, np.nan], [np.nan, np.nan]),
        ([np.nan, 0.5], [1, np.nan]),
        ([], []),
    ],
)
def test_no_remaining_pairs(p: list[float], y: list[float]) -> None:
    assert math.isnan(brier_score(p, y))
    assert math.isnan(log_loss(p, y))
    assert math.isnan(expected_calibration_error(p, y))
    assert math.isnan(max_calibration_error(p, y))
    assert reliability_table(p, y) == []

    summary = calibration_summary(p, y)
    assert summary["n"] == 0
    assert summary["n_dropped"] == len(p)
    assert summary["positives"] == 0
    for key in ("brier", "log_loss", "ece", "mce", "base_rate"):
        assert math.isnan(summary[key])


def test_one_lands_in_last_uniform_bin() -> None:
    bins = reliability_table([0.0, 0.5, 1.0], [0, 1, 1], n_bins=2)

    assert len(bins) == 2
    assert (bins[-1].lower, bins[-1].upper) == (0.5, 1.0)
    assert bins[-1].count == 2
    assert bins[-1].mean_predicted == 0.75


def test_quantile_bins_have_equal_counts() -> None:
    p = np.linspace(0.0, 1.0, 100)
    bins = reliability_table(p, np.zeros(100), n_bins=10, strategy="quantile")

    assert [bin_.count for bin_ in bins] == [10] * 10
    assert bins[0].lower == 0.0
    assert bins[-1].upper == 1.0


def test_quantile_bins_deduplicate_edges() -> None:
    bins = reliability_table([0.5] * 8, [0, 1] * 4, strategy="quantile")

    assert sum(bin_.count for bin_ in bins) == 8
    assert all(bin_.lower < bin_.upper for bin_ in bins)
    assert len(bins) == 1


def test_wilson_intervals() -> None:
    low, high = wilson_interval(0, 10)
    assert low == 0.0
    assert 0.0 < high < 1.0

    low, high = wilson_interval(10, 10)
    assert 0.0 < low < 1.0
    assert high == 1.0

    assert wilson_interval(5, 10) == pytest.approx((0.2366, 0.7634), abs=1e-3)
    assert all(math.isnan(bound) for bound in wilson_interval(0, 0))


@pytest.mark.parametrize(
    ("p", "y"),
    [
        ([0.5], [0, 1]),
        ([1.2], [1]),
        ([-0.1], [0]),
        ([np.inf], [1]),
        ([0.5], [2]),
        ([1.2], [np.nan]),
        ([np.nan], [2]),
    ],
)
def test_invalid_pairs_raise(p: list[float], y: list[float]) -> None:
    for metric in (
        brier_score,
        log_loss,
        reliability_table,
        expected_calibration_error,
        max_calibration_error,
        calibration_summary,
    ):
        with pytest.raises(ValueError):
            metric(p, y)


@pytest.mark.parametrize(
    "kwargs",
    [{"strategy": "unknown"}, {"n_bins": 0}],
)
def test_invalid_binning_raises(kwargs: dict[str, str | int]) -> None:
    for metric in (
        reliability_table,
        expected_calibration_error,
        max_calibration_error,
        calibration_summary,
    ):
        with pytest.raises(ValueError):
            metric([0.5], [1], **kwargs)
        with pytest.raises(ValueError):
            metric([], [], **kwargs)


@pytest.mark.parametrize(("successes", "n"), [(11, 10), (-1, 10), (0, -1)])
def test_invalid_wilson_counts_raise(successes: int, n: int) -> None:
    with pytest.raises(ValueError):
        wilson_interval(successes, n)


def test_bool_outcomes_and_flattening() -> None:
    assert brier_score([[0.25, 0.75]], [[False], [True]]) == 0.0625


def test_log_loss_clips_endpoints() -> None:
    eps = 1e-6
    expected = -(math.log(eps) + math.log1p(-(1.0 - eps))) / 2.0
    assert log_loss([0.0, 1.0], [1, 0], eps=eps) == pytest.approx(expected)


@pytest.mark.parametrize("bad_y", [math.inf, -math.inf])
def test_infinite_outcome_raises(bad_y: float) -> None:
    # Only NaN means "no outcome known"; an infinite outcome is invalid data, not a drop.
    with pytest.raises(ValueError):
        brier_score([0.5, 0.5], [1.0, bad_y])
