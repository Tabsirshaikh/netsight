"""Baselines NetSight is compared against (plan section 12.2).

B0 raw detector score and B1 temperature scaling live in ``netsight.trust.calibrators``
(identity and ``TemperatureScaling``). This module adds:

- B2: a hand-set logistic Pd curve over across-track position, combined across passes by taking
  the maximum (the approach in the SIH "Sagar-Netra" style Pd grid). Nothing is fitted to data.
- B3: the shadow-required hazard-picking rule: a contact without a measurable shadow is dropped.

Each baseline is a plain function so the evaluation harness can score it exactly like NetSight.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray


def b2_hand_set_pd(
    rel_range: ArrayLike,
    *,
    pd_max: float = 0.95,
    midpoint: float = 0.85,
    steepness: float = 12.0,
    nadir_gap: float = 0.05,
) -> NDArray[np.float64]:
    """Hand-set Pd versus relative ground range (0 = nadir, 1 = maximum range).

    Pd falls logistically towards far range and is zero inside the nadir gap. The defaults are a
    typical hand choice; they are deliberately not fitted.
    """
    r = np.asarray(rel_range, dtype=np.float64)
    pd = pd_max / (1 + np.exp(steepness * (r - midpoint)))
    return np.where((r < nadir_gap) | (r > 1), 0.0, pd)


def b2_combine_passes(pds: Sequence[ArrayLike]) -> NDArray[np.float64]:
    """Max across passes (B2's rule). It ignores the extra chance a second look gives, and
    also ignores correlated misses; NetSight reports the [max, independence] interval instead."""
    stack = np.stack([np.asarray(p, dtype=np.float64) for p in pds])
    return np.nanmax(stack, axis=0)


def rel_range_from_image_x(x_centre: ArrayLike, width: int, *, nadir: str = "centre") -> NDArray:
    """Relative ground range from an image column for a waterfall with nadir at ``nadir``
    ("centre", "left" or "right")."""
    x = np.asarray(x_centre, dtype=np.float64) / float(width)
    if nadir == "centre":
        return np.abs(x - 0.5) * 2
    if nadir == "left":
        return x
    if nadir == "right":
        return 1 - x
    raise ValueError("nadir must be 'centre', 'left' or 'right'")


def b3_shadow_filter(scores: ArrayLike, shadow_present: ArrayLike) -> NDArray[np.float64]:
    """Shadow-required rule: keep the detector score when a shadow was measured, else 0."""
    s = np.asarray(scores, dtype=np.float64)
    keep = np.asarray(shadow_present, dtype=bool)
    if s.shape != keep.shape:
        raise ValueError("scores and shadow_present must have the same shape")
    return np.where(keep, s, 0.0)
