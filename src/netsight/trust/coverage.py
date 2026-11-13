"""Where a survey searched nothing, and how several passes combine (plan 16 items 5 and 6).

"Not searched" is deliberately strict, so it never hides real seabed: only no-data (flat,
near-black pixels: mosaic holidays, blank borders, fully black acoustic shadows) and, on
waterfalls, whole across-track columns far darker than the image's typical column (water
column at nadir, lost far range). Dark sediment and weak far range stay "searched"; the
injection Pd measures how well they are searched. (Checked on held-out images of six
datasets, 2026-11-13; the looser seabed mask used for target placement marked dark sediment
and weak far range as unsearchable.)

Multi-pass: per map cell, the plan's honest interval [max over passes, 1 - prod(1 - Pd)]:
the lower end assumes misses repeat on every pass (same object, same aspect), the upper end
assumes they are independent.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

COLUMN_FRACTION = 0.3  # a column below 30% of the typical column level is not searched
NOT_SEARCHED_CELL = 0.05  # cells with less searched area than this are "not_searched"


def not_searched_mask(image: np.ndarray, *, waterfall: bool) -> NDArray[np.bool_]:
    """True where the sonar returned nothing usable (see module docstring)."""
    from scipy.ndimage import median_filter, uniform_filter

    x = np.asarray(image, dtype=np.float64)
    if x.ndim != 2:
        raise ValueError("expected a single-channel image")
    dark = x <= 3
    # a near-black pixel in a mostly near-black neighbourhood (speckle on real seabed is not)
    mask = dark & (uniform_filter(dark.astype(np.float64), 9) >= 0.6)
    if waterfall and x.shape[1] >= 10:
        col = median_filter(np.median(x, axis=0), size=5, mode="nearest")
        bright = col[col > np.percentile(col, 10)]
        level = float(np.median(bright)) if bright.size else 0.0
        if level > 0:
            mask |= (col < COLUMN_FRACTION * level)[None, :]
    return mask


def searched_fraction(mask: np.ndarray, grid: tuple[int, int]) -> NDArray[np.float64]:
    """Fraction of searched pixels in each cell of a rows x cols grid over the image."""
    rows, cols = grid
    h, w = mask.shape
    out = np.zeros((rows, cols))
    for r in range(rows):
        for c in range(cols):
            cell = mask[r * h // rows : (r + 1) * h // rows, c * w // cols : (c + 1) * w // cols]
            out[r, c] = 1.0 - float(cell.mean()) if cell.size else 0.0
    return out


def multipass_grid(
    passes: Sequence[np.ndarray],
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.int64]]:
    """Per cell: (max Pd, independent-miss Pd, number of passes with a value). NaN = no data."""
    stack = np.stack([np.asarray(p, float) for p in passes]) if passes else np.zeros((0, 0, 0))
    if len({np.asarray(p).shape for p in passes}) > 1:
        raise ValueError("all pass grids must have the same shape")
    valid = np.isfinite(stack)
    n = valid.sum(axis=0)
    filled = np.where(valid, stack, 0.0)
    lo = np.where(n > 0, filled.max(axis=0), np.nan)
    hi = np.where(n > 0, 1 - np.prod(1 - filled, axis=0), np.nan)
    return lo, hi, n
