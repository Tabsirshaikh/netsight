"""Exact bounds for headline claims: Clopper-Pearson (binomial) and Poisson upper bounds.

Plan rule: any headline bound uses Clopper-Pearson; Wilson is only for descriptive plots.
"""

from __future__ import annotations

import math

from scipy.stats import beta, chi2


def _check_alpha(alpha: float) -> None:
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must be in (0, 1), got {alpha}")


def _check_counts(k: int, n: int) -> None:
    if n < 0 or not 0 <= k <= n:
        raise ValueError(f"need n >= 0 and 0 <= k <= n, got k={k}, n={n}")


def clopper_pearson(k: int, n: int, *, alpha: float = 0.05) -> tuple[float, float]:
    """Two-sided exact interval for a binomial proportion; (nan, nan) when n == 0."""
    _check_counts(k, n)
    _check_alpha(alpha)
    if n == 0:
        return math.nan, math.nan
    low = 0.0 if k == 0 else float(beta.ppf(alpha / 2, k, n - k + 1))
    high = 1.0 if k == n else float(beta.ppf(1 - alpha / 2, k + 1, n - k))
    return low, high


def one_sided_lower(k: int, n: int, *, alpha: float = 0.05) -> float:
    """One-sided exact lower bound (e.g. for Pd): P(true rate >= bound) >= 1 - alpha."""
    _check_counts(k, n)
    _check_alpha(alpha)
    if n == 0:
        return math.nan
    return 0.0 if k == 0 else float(beta.ppf(alpha, k, n - k + 1))


def zero_miss_trials(pd: float, *, alpha: float = 0.05) -> int:
    """Independent trials with zero misses needed for the lower bound on Pd to reach `pd`."""
    if not 0.0 < pd < 1.0:
        raise ValueError(f"pd must be in (0, 1), got {pd}")
    _check_alpha(alpha)
    n = math.ceil(math.log(alpha) / math.log(pd))
    while one_sided_lower(n, n, alpha=alpha) < pd:  # guard against float rounding at ceil
        n += 1
    return n


def poisson_upper(k: int, exposure: float, *, alpha: float = 0.05) -> float:
    """One-sided exact upper bound on a Poisson rate per unit exposure (e.g. FA per km2)."""
    if k < 0:
        raise ValueError(f"k must be >= 0, got {k}")
    if not exposure > 0:
        raise ValueError(f"exposure must be > 0, got {exposure}")
    _check_alpha(alpha)
    return float(chi2.ppf(1 - alpha, 2 * (k + 1)) / 2 / exposure)
