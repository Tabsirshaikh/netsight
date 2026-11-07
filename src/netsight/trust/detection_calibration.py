"""Multidimensional detection ECE following Kuppers et al. (2020)."""

from collections.abc import Sequence
from dataclasses import dataclass
from operator import index
from typing import TypedDict

import numpy as np
from numpy.typing import ArrayLike, NDArray


class BinSummary(TypedDict):
    """Calibration statistics for one joint bin."""

    bin: tuple[int, ...]
    count: int
    mean_p: float
    observed_rate: float
    gap: float


@dataclass(frozen=True)
class DEceResult:
    """Detection calibration error and joint-bin diagnostics."""

    d_ece: float
    n_used: int
    n_dropped: int
    n_bins_used: int
    n_bins_sparse: int
    worst_bins: list[BinSummary]


def _positive_integer(value: int, name: str) -> int:
    """Validate an integer-valued configuration argument."""
    try:
        result = index(value)
    except TypeError as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if result < 1:
        raise ValueError(f"{name} must be a positive integer")
    return result


def _uniform_bins(
    values: NDArray[np.float64],
    lo: float,
    hi: float,
    count: int,
) -> NDArray[np.int64]:
    """Assign values to uniform bins, clipping both endpoints."""
    clipped = np.clip(values, lo, hi)
    # Scaling first avoids overflow in hi - lo for large finite ranges.
    scale = max(abs(lo), abs(hi))
    if scale:
        positions = (clipped / scale - lo / scale) / (hi / scale - lo / scale)
    else:
        positions = np.zeros_like(clipped)
    return np.clip(np.floor(positions * count), 0, count - 1).astype(np.int64)


def detection_ece(
    p: ArrayLike,
    y: ArrayLike,
    features: ArrayLike | None = None,
    *,
    n_bins: int = 10,
    feature_bins: int = 5,
    feature_ranges: Sequence[tuple[float, float]] | None = None,
    min_bin_count: int = 1,
) -> DEceResult:
    """Compute count-weighted ECE over confidence and feature joint bins.

    NaN rows are dropped before inferring feature ranges. Sparse bins are
    excluded from both the numerator and denominator. Worst bins are ranked
    by count times absolute calibration gap, with lexicographic tie-breaking.
    Infinite feature values and non-finite range endpoints are rejected.
    """
    n_bins = _positive_integer(n_bins, "n_bins")
    feature_bins = _positive_integer(feature_bins, "feature_bins")
    min_bin_count = _positive_integer(min_bin_count, "min_bin_count")

    probabilities = np.asarray(p, dtype=np.float64)
    outcomes = np.asarray(y, dtype=np.float64)
    if probabilities.ndim != 1 or outcomes.ndim != 1:
        raise ValueError("p and y must be one-dimensional")
    if probabilities.shape != outcomes.shape:
        raise ValueError("p and y lengths differ")
    if np.any((probabilities < 0) | (probabilities > 1)):
        raise ValueError("p must lie in [0, 1] or be NaN")
    if np.any(~(np.isnan(outcomes) | (outcomes == 0) | (outcomes == 1))):
        raise ValueError("y must contain only 0, 1, or NaN")

    n = probabilities.size
    if features is None:
        properties = np.empty((n, 0), dtype=np.float64)
    else:
        properties = np.asarray(features, dtype=np.float64)
        if properties.ndim != 2 or properties.shape[0] != n:
            raise ValueError("features must be two-dimensional with n rows")
        if np.any(np.isinf(properties)):
            raise ValueError("features must be finite or NaN")

    k = properties.shape[1]
    ranges: NDArray[np.float64] | None = None
    if feature_ranges is not None:
        ranges = np.asarray(feature_ranges, dtype=np.float64)
        if k == 0 and ranges.shape == (0,):
            ranges = ranges.reshape(0, 2)
        if ranges.shape != (k, 2):
            raise ValueError("feature_ranges must contain one (lo, hi) pair per feature")
        if np.any(~np.isfinite(ranges)) or np.any(ranges[:, 0] >= ranges[:, 1]):
            raise ValueError("feature ranges must have finite endpoints with lo < hi")

    valid = ~np.isnan(probabilities) & ~np.isnan(outcomes) & ~np.isnan(properties).any(axis=1)
    n_dropped = int(n - np.count_nonzero(valid))
    probabilities = probabilities[valid]
    outcomes = outcomes[valid]
    properties = properties[valid]

    if probabilities.size == 0:
        return DEceResult(float("nan"), 0, n_dropped, 0, 0, [])

    columns = [_uniform_bins(probabilities, 0.0, 1.0, n_bins)]
    for j in range(k):
        values = properties[:, j]
        if ranges is None:
            lo, hi = float(values.min()), float(values.max())
        else:
            lo, hi = float(ranges[j, 0]), float(ranges[j, 1])
        if lo == hi:
            columns.append(np.zeros(values.size, dtype=np.int64))
        else:
            columns.append(_uniform_bins(values, lo, hi, feature_bins))

    joint_bins = np.column_stack(columns)
    unique_bins, inverse, counts = np.unique(
        joint_bins, axis=0, return_inverse=True, return_counts=True
    )
    # Flatten for compatibility with NumPy versions returning shaped inverse indices.
    inverse = inverse.reshape(-1)
    sum_p = np.bincount(inverse, weights=probabilities)
    sum_y = np.bincount(inverse, weights=outcomes)
    counted = counts >= min_bin_count
    n_used = int(counts[counted].sum())
    n_bins_used = int(np.count_nonzero(counted))
    n_bins_sparse = int(np.count_nonzero(~counted))

    summaries: list[BinSummary] = []
    weighted_error = 0.0
    for i in np.flatnonzero(counted):
        count = int(counts[i])
        mean_p = float(sum_p[i] / count)
        observed_rate = float(sum_y[i] / count)
        gap = abs(observed_rate - mean_p)
        weighted_error += count * gap
        summaries.append(
            {
                "bin": tuple(int(component) for component in unique_bins[i]),
                "count": count,
                "mean_p": mean_p,
                "observed_rate": observed_rate,
                "gap": gap,
            }
        )

    summaries.sort(key=lambda item: (-item["count"] * item["gap"], item["bin"]))
    return DEceResult(
        d_ece=weighted_error / n_used if n_used else float("nan"),
        n_used=n_used,
        n_dropped=n_dropped,
        n_bins_used=n_bins_used,
        n_bins_sparse=n_bins_sparse,
        worst_bins=summaries[:5],
    )
