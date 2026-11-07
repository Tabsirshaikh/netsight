"""Compute calibration metrics while excluding pairs with unknown outcomes."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.stats import norm


@dataclass(frozen=True)
class ReliabilityBin:
    """Non-empty reliability bin with a Wilson confidence interval."""

    lower: float
    upper: float
    count: int
    mean_predicted: float
    observed_rate: float
    ci_low: float
    ci_high: float


def _validate_pairs(
    p: ArrayLike, y: ArrayLike
) -> tuple[NDArray[np.float64], NDArray[np.float64], int]:
    """Flatten and validate inputs, then drop pairs containing NaN."""
    probabilities = np.asarray(p, dtype=np.float64).reshape(-1)
    outcomes = np.asarray(y, dtype=np.float64).reshape(-1)

    if probabilities.size != outcomes.size:
        raise ValueError("p and y must have the same length.")
    if np.any((probabilities < 0.0) | (probabilities > 1.0)):
        raise ValueError("p must contain probabilities in [0, 1].")

    # NaN means "no outcome known" and is dropped below; anything else must be 0 or 1.
    known_outcomes = ~np.isnan(outcomes)
    if np.any(known_outcomes & (outcomes != 0.0) & (outcomes != 1.0)):
        raise ValueError("y values must be 0, 1 or NaN.")

    keep = ~(np.isnan(probabilities) | np.isnan(outcomes))
    n_dropped = int(probabilities.size - np.count_nonzero(keep))
    return probabilities[keep], outcomes[keep], n_dropped


def brier_score(p: ArrayLike, y: ArrayLike) -> float:
    """Return mean squared probability error."""
    probabilities, outcomes, _ = _validate_pairs(p, y)
    if probabilities.size == 0:
        return float("nan")
    return float(np.mean((probabilities - outcomes) ** 2))


def log_loss(p: ArrayLike, y: ArrayLike, *, eps: float = 1e-12) -> float:
    """Return mean negative log-likelihood with clipped probabilities."""
    probabilities, outcomes, _ = _validate_pairs(p, y)
    if not 0.0 < eps < 0.5:
        raise ValueError("eps must be strictly between 0 and 0.5.")
    if probabilities.size == 0:
        return float("nan")

    clipped = np.clip(probabilities, eps, 1.0 - eps)
    return float(-np.mean(outcomes * np.log(clipped) + (1.0 - outcomes) * np.log1p(-clipped)))


def wilson_interval(successes: int, n: int, *, alpha: float = 0.05) -> tuple[float, float]:
    """Return the Wilson score interval at confidence level 1 - alpha."""
    if n < 0 or not 0 <= successes <= n:
        raise ValueError("Require n >= 0 and successes in [0, n].")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be strictly between 0 and 1.")
    if n == 0:
        return float("nan"), float("nan")

    z = float(norm.ppf(1.0 - alpha / 2.0))
    z_squared = z * z
    rate = successes / n
    denominator = 1.0 + z_squared / n
    center = (rate + z_squared / (2.0 * n)) / denominator
    radius = z * np.sqrt(rate * (1.0 - rate) / n + z_squared / (4.0 * n * n)) / denominator

    low = 0.0 if successes == 0 else float(np.clip(center - radius, 0.0, 1.0))
    high = 1.0 if successes == n else float(np.clip(center + radius, 0.0, 1.0))
    return low, high


def reliability_table(
    p: ArrayLike,
    y: ArrayLike,
    *,
    n_bins: int = 10,
    strategy: str = "uniform",
    alpha: float = 0.05,
) -> list[ReliabilityBin]:
    """Return non-empty, left-closed bins; the final bin includes its upper edge."""
    probabilities, outcomes, _ = _validate_pairs(p, y)
    if n_bins < 1:
        raise ValueError("n_bins must be at least 1.")
    if strategy not in {"uniform", "quantile"}:
        raise ValueError("strategy must be 'uniform' or 'quantile'.")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be strictly between 0 and 1.")
    if probabilities.size == 0:
        return []

    if strategy == "uniform":
        edges = np.linspace(0.0, 1.0, n_bins + 1)
    else:
        edges = np.quantile(probabilities, np.linspace(0.0, 1.0, n_bins + 1))
        edges[0] = 0.0
        edges[-1] = 1.0
        edges = np.unique(edges)

    # Searching only interior edges also assigns p == 1 to the final bin.
    assignments = np.searchsorted(edges[1:-1], probabilities, side="right")
    bins: list[ReliabilityBin] = []
    for index in range(edges.size - 1):
        mask = assignments == index
        count = int(np.count_nonzero(mask))
        if count == 0:
            continue

        successes = int(np.sum(outcomes[mask]))
        ci_low, ci_high = wilson_interval(successes, count, alpha=alpha)
        bins.append(
            ReliabilityBin(
                lower=float(edges[index]),
                upper=float(edges[index + 1]),
                count=count,
                mean_predicted=float(np.mean(probabilities[mask])),
                observed_rate=float(np.mean(outcomes[mask])),
                ci_low=ci_low,
                ci_high=ci_high,
            )
        )
    return bins


def expected_calibration_error(
    p: ArrayLike,
    y: ArrayLike,
    *,
    n_bins: int = 10,
    strategy: str = "uniform",
) -> float:
    """Return the count-weighted absolute calibration error."""
    bins = reliability_table(p, y, n_bins=n_bins, strategy=strategy)
    count = sum(bin_.count for bin_ in bins)
    if count == 0:
        return float("nan")
    return float(
        sum((bin_.count / count) * abs(bin_.observed_rate - bin_.mean_predicted) for bin_ in bins)
    )


def max_calibration_error(
    p: ArrayLike,
    y: ArrayLike,
    *,
    n_bins: int = 10,
    strategy: str = "uniform",
) -> float:
    """Return the largest absolute calibration error among non-empty bins."""
    bins = reliability_table(p, y, n_bins=n_bins, strategy=strategy)
    return max(
        (abs(bin_.observed_rate - bin_.mean_predicted) for bin_ in bins),
        default=float("nan"),
    )


def calibration_summary(
    p: ArrayLike,
    y: ArrayLike,
    *,
    n_bins: int = 10,
    strategy: str = "uniform",
) -> dict[str, int | float]:
    """Return sample counts, base rate, and calibration metrics."""
    probabilities, outcomes, n_dropped = _validate_pairs(p, y)
    n = int(probabilities.size)
    return {
        "n": n,
        "n_dropped": n_dropped,
        "positives": int(np.count_nonzero(outcomes == 1.0)),
        "brier": brier_score(probabilities, outcomes),
        "log_loss": log_loss(probabilities, outcomes),
        "ece": expected_calibration_error(
            probabilities, outcomes, n_bins=n_bins, strategy=strategy
        ),
        "mce": max_calibration_error(probabilities, outcomes, n_bins=n_bins, strategy=strategy),
        "base_rate": float(np.mean(outcomes)) if n else float("nan"),
    }
