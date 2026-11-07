"""Survey-level nonparametric bootstrap intervals."""

from collections.abc import Callable, Hashable
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray


@dataclass(frozen=True)
class BootstrapResult:
    """A point estimate and survey-bootstrap percentile interval."""

    estimate: float
    low: float
    high: float
    n_boot_used: int
    n_boot_nan: int
    n_groups: int


def _validate(
    groups: ArrayLike,
    arrays: tuple[ArrayLike, ...],
    n_boot: int,
    alpha: float,
) -> tuple[list[NDArray[np.intp]], tuple[NDArray[Any], ...]]:
    """Validate alignment and collect row indices for each survey."""
    ids = np.asarray(groups, dtype=object)
    values = tuple(np.asarray(array) for array in arrays)
    if ids.ndim != 1:
        raise ValueError("groups must be one-dimensional.")
    if any(array.ndim == 0 or array.shape[0] != ids.size for array in values):
        raise ValueError("All arrays must have the same row count as groups.")
    if isinstance(n_boot, bool) or not isinstance(n_boot, int) or n_boot < 1:
        raise ValueError("n_boot must be a positive integer.")
    if not np.isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError("alpha must lie strictly between 0 and 1.")

    grouped: dict[Hashable, list[int]] = {}
    for index, survey in enumerate(ids):
        try:
            # Treat repeated floating NaN identifiers as one survey.
            key = ("netsight_nan_id",) if isinstance(survey, float) and np.isnan(survey) else survey
            grouped.setdefault(key, []).append(index)
        except TypeError as exc:
            raise ValueError("Survey identifiers must be hashable.") from exc
    if len(grouped) < 2:
        raise ValueError("Bootstrap requires at least two surveys.")
    blocks = [np.asarray(rows, dtype=np.intp) for rows in grouped.values()]
    return blocks, values


def survey_bootstrap(
    metric: Callable[..., float],
    groups: ArrayLike,
    *arrays: ArrayLike,
    n_boot: int = 2000,
    alpha: float = 0.05,
    rng: np.random.Generator,
) -> BootstrapResult:
    """Resample whole surveys and compute a percentile confidence interval."""
    blocks, values = _validate(groups, arrays, n_boot, alpha)
    estimate = float(metric(*values))
    replicates: list[float] = []
    n_nan = 0
    for _ in range(n_boot):
        selected = rng.integers(0, len(blocks), size=len(blocks))
        rows = np.concatenate([blocks[int(index)] for index in selected])
        value = float(metric(*(array[rows] for array in values)))
        if np.isnan(value):
            n_nan += 1
        else:
            replicates.append(value)
    if replicates:
        low, high = np.quantile(replicates, [alpha / 2, 1 - alpha / 2])
    else:
        low = high = np.nan
    return BootstrapResult(
        estimate=estimate,
        low=float(low),
        high=float(high),
        n_boot_used=len(replicates),
        n_boot_nan=n_nan,
        n_groups=len(blocks),
    )
