"""Choose and freeze a detection threshold at a false-alarm budget (FA per km2).

Method: Learn-then-Test with fixed-sequence testing. For each candidate threshold t, from the
strictest downward, test H0: "false-alarm rate at t exceeds the budget" using the exact
Poisson upper bound on false alarms per km2 at level `delta`. Because the false-alarm count
can only grow as t falls, testing in that order controls the error without a multiplicity
correction; the chosen threshold is the lowest t whose H0 is rejected.

Assumptions, stated in every report: false alarms behave like a Poisson process over the
calibration area (no survey-to-survey over-dispersion), and new surveys are drawn like the
calibration surveys. The recall interval is contact-level Clopper-Pearson; a survey-cluster
interval comes from `netsight.trust.bootstrap`.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike

from netsight.trust.bounds import clopper_pearson, poisson_upper


@dataclass(frozen=True)
class OperatingPoint:
    threshold: float  # flag contacts with score >= threshold; inf means flag none
    feasible: bool  # False when the calibration area cannot certify the budget at all
    budget_fa_per_km2: float
    delta: float
    area_km2: float
    n_surveys: int
    fa_count: int
    fa_rate: float
    fa_rate_upper: float
    tp: int
    positives: int
    recall: float
    recall_ci: tuple[float, float]
    n_unknown: int  # contacts with no known outcome: flagged, but not counted either way
    min_area_km2: float  # area needed to certify the budget even with zero false alarms


def select_operating_point(
    scores: ArrayLike,
    is_real: ArrayLike,
    surveys: Sequence[str],
    survey_area_km2: Mapping[str, float],
    *,
    budget_fa_per_km2: float,
    delta: float = 0.05,
    alpha: float = 0.05,
) -> OperatingPoint:
    """Lowest threshold whose false-alarm rate is below budget with confidence 1 - delta."""
    s = np.asarray(scores, dtype=float).reshape(-1)
    y = np.asarray(is_real, dtype=float).reshape(-1)
    surveys = list(surveys)
    if not (s.size == y.size == len(surveys)):
        raise ValueError("scores, is_real and surveys must have the same length")
    if not np.all(np.isfinite(s)):
        raise ValueError("scores must be finite")
    known = ~np.isnan(y)
    if np.any(known & (y != 0) & (y != 1)):
        raise ValueError("is_real values must be 0, 1 or NaN (unknown)")
    missing = sorted(set(surveys) - set(survey_area_km2))
    if missing:
        raise ValueError(f"no searched area given for surveys: {missing}")
    areas = np.asarray(list(survey_area_km2.values()), dtype=float)
    if areas.size == 0 or not np.all(np.isfinite(areas) & (areas > 0)):
        raise ValueError("every survey area must be a finite number > 0 km2")
    if not budget_fa_per_km2 > 0:
        raise ValueError("budget_fa_per_km2 must be > 0")
    if not 0.0 < delta < 1.0:
        raise ValueError("delta must be in (0, 1)")

    area = float(areas.sum())
    false_sorted = np.sort(s[known & (y == 0)])
    real_scores = s[known & (y == 1)]

    def fa_at(t: float) -> int:
        return int(false_sorted.size - np.searchsorted(false_sorted, t, side="left"))

    def passes(t: float) -> bool:
        return poisson_upper(fa_at(t), area, alpha=delta) <= budget_fa_per_km2

    threshold = math.inf
    feasible = passes(math.inf)
    if feasible:
        for t in np.unique(s[known])[::-1]:
            if not passes(float(t)):
                break
            threshold = float(t)

    fa = fa_at(threshold)
    tp = int(np.count_nonzero(real_scores >= threshold))
    positives = int(real_scores.size)
    return OperatingPoint(
        threshold=threshold,
        feasible=feasible,
        budget_fa_per_km2=float(budget_fa_per_km2),
        delta=float(delta),
        area_km2=area,
        n_surveys=len(survey_area_km2),
        fa_count=fa,
        fa_rate=fa / area,
        fa_rate_upper=poisson_upper(fa, area, alpha=delta),
        tp=tp,
        positives=positives,
        recall=tp / positives if positives else math.nan,
        recall_ci=clopper_pearson(tp, positives, alpha=alpha),
        n_unknown=int(np.count_nonzero(~known)),
        min_area_km2=-math.log(delta) / budget_fa_per_km2,
    )
