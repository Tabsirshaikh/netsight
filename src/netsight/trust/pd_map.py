"""Aggregate target-injection trials into spatial detection-probability bounds."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from math import floor, isfinite, isnan, prod

import numpy as np
from numpy.typing import ArrayLike, NDArray

from netsight.trust.bounds import one_sided_lower


@dataclass(frozen=True)
class PdCell:
    """Detection statistics for one spatial cell and target stratum."""

    ix: int
    iy: int
    stratum: str
    n_trials: int
    n_detected: int
    pd_mean: float
    pd_lower: float
    confidence: float
    status: str


def aggregate_trials(
    x_m: ArrayLike,
    y_m: ArrayLike,
    detected: ArrayLike,
    *,
    cell_size_m: float,
    origin: tuple[float, float] = (0.0, 0.0),
    strata: Sequence[str] | None = None,
    alpha: float = 0.10,
    min_trials: int = 29,
) -> list[PdCell]:
    """Group trials by cell and stratum, with exact lower bounds.

    The default bound has 90% confidence. The default trial threshold is 29:
    29 zero-miss trials reach a 0.90 lower bound at 95% confidence.
    """
    if not isfinite(cell_size_m) or cell_size_m <= 0:
        raise ValueError("cell_size_m must be finite and positive")
    if not 0 < alpha < 1:
        raise ValueError("alpha must be in (0, 1)")
    if min_trials < 1:
        raise ValueError("min_trials must be at least 1")
    if len(origin) != 2 or not all(isfinite(value) for value in origin):
        raise ValueError("origin must contain two finite coordinates")

    x = np.asarray(x_m, dtype=np.float64)
    y = np.asarray(y_m, dtype=np.float64)
    outcomes = np.asarray(detected)
    if x.ndim != 1 or y.ndim != 1 or outcomes.ndim != 1:
        raise ValueError("trial inputs must be one-dimensional")
    if len(x) != len(y) or len(x) != len(outcomes):
        raise ValueError("trial input lengths must match")
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise ValueError("trial coordinates must be finite")
    if not np.all(np.isin(outcomes, (0, 1))):
        raise ValueError("detected values must be 0 or 1")

    labels = ["all"] * len(x) if strata is None else list(strata)
    if len(labels) != len(x):
        raise ValueError("strata length must match trial inputs")

    counts: dict[tuple[int, int, str], tuple[int, int]] = {}
    origin_x, origin_y = origin
    for x_value, y_value, outcome, label in zip(x, y, outcomes, labels, strict=True):
        ix = floor((float(x_value) - origin_x) / cell_size_m)
        iy = floor((float(y_value) - origin_y) / cell_size_m)
        key = (ix, iy, label)
        n, k = counts.get(key, (0, 0))
        counts[key] = (n + 1, k + int(outcome))

    cells: list[PdCell] = []
    for ix, iy, label in sorted(counts, key=lambda key: (key[2], key[1], key[0])):
        n, k = counts[(ix, iy, label)]
        cells.append(
            PdCell(
                ix=ix,
                iy=iy,
                stratum=label,
                n_trials=n,
                n_detected=k,
                pd_mean=k / n,
                pd_lower=one_sided_lower(k, n, alpha=alpha),
                confidence=1 - alpha,
                status="ok" if n >= min_trials else "insufficient_trials",
            )
        )
    return cells


def combine_passes(pds: Iterable[float]) -> tuple[float, float]:
    """Bound combined Pd using correlated and independent miss assumptions."""
    values: list[float] = []
    for pd in pds:
        value = float(pd)
        if isnan(value):
            continue
        if not 0 <= value <= 1:
            raise ValueError("pass probabilities must be in [0, 1] or NaN")
        values.append(value)

    if not values:
        return float("nan"), float("nan")
    return max(values), 1 - prod(1 - value for value in values)


def pd_grid(
    cells: Iterable[PdCell],
    stratum: str,
    *,
    field: str = "pd_lower",
) -> tuple[NDArray[np.float64], tuple[int, int]]:
    """Build a dense stratum grid and return its minimum cell indices."""
    if field not in {"pd_lower", "pd_mean", "n_trials"}:
        raise ValueError("field must be pd_lower, pd_mean, or n_trials")

    selected = [cell for cell in cells if cell.stratum == stratum]
    if not selected:
        raise ValueError(f"no cells for stratum {stratum!r}")

    ix_min = min(cell.ix for cell in selected)
    ix_max = max(cell.ix for cell in selected)
    iy_min = min(cell.iy for cell in selected)
    iy_max = max(cell.iy for cell in selected)
    grid = np.full(
        (iy_max - iy_min + 1, ix_max - ix_min + 1),
        np.nan,
        dtype=np.float64,
    )
    for cell in selected:
        grid[cell.iy - iy_min, cell.ix - ix_min] = getattr(cell, field)
    return grid, (ix_min, iy_min)
