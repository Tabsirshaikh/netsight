import math

import numpy as np
import pytest

from netsight.trust.bounds import (
    clopper_pearson,
    one_sided_lower,
    poisson_upper,
    zero_miss_trials,
)
from netsight.trust.operating_point import select_operating_point

# --- exact binomial / Poisson bounds -------------------------------------------------------


def test_clopper_pearson_known_values():
    assert clopper_pearson(5, 10) == pytest.approx((0.187086, 0.812914), abs=1e-6)
    low, high = clopper_pearson(0, 10)
    assert low == 0.0 and high == pytest.approx(1 - 0.025 ** (1 / 10), abs=1e-9)
    low, high = clopper_pearson(10, 10)
    assert high == 1.0 and low == pytest.approx(0.025 ** (1 / 10), abs=1e-9)


def test_clopper_pearson_empty_is_nan():
    assert all(math.isnan(b) for b in clopper_pearson(0, 0))


@pytest.mark.parametrize(("pd", "n"), [(0.90, 29), (0.95, 59), (0.99, 299)])
def test_zero_miss_trials_match_plan(pd, n):
    # plan section 9: 29 / 59 / 299 effective independent trials at 95% confidence
    assert zero_miss_trials(pd) == n
    assert one_sided_lower(n, n) >= pd
    assert one_sided_lower(n - 1, n - 1) < pd


def test_one_sided_lower_with_misses():
    assert one_sided_lower(0, 10) == 0.0
    # solves 10 p^9 (1 - p) + p^10 = 0.05 by hand: p ~ 0.606
    assert one_sided_lower(9, 10) == pytest.approx(0.606, abs=0.002)


def test_poisson_upper_zero_events():
    assert poisson_upper(0, 1.0) == pytest.approx(-math.log(0.05))
    assert poisson_upper(0, 10.0) == pytest.approx(-math.log(0.05) / 10)


@pytest.mark.parametrize(
    "call",
    [
        lambda: clopper_pearson(11, 10),
        lambda: clopper_pearson(-1, 10),
        lambda: clopper_pearson(1, 10, alpha=1.5),
        lambda: one_sided_lower(3, 2),
        lambda: zero_miss_trials(1.0),
        lambda: zero_miss_trials(0.0),
        lambda: poisson_upper(-1, 1.0),
        lambda: poisson_upper(1, 0.0),
    ],
)
def test_bound_input_errors(call):
    with pytest.raises(ValueError):
        call()


# --- operating point at a false-alarm budget ------------------------------------------------


def _hand_case():
    # area 10 km2, delta 0.05: Poisson upper bound is 0.300 for 0 FA, 0.474 for 1 FA and
    # 0.630 for 2 FA (per km2), so a 0.5 FA/km2 budget allows at most one false alarm.
    scores = [0.95, 0.7, 0.3, 0.9, 0.8, 0.6, 0.2]
    real = [0, 0, 0, 1, 1, 1, 1]
    surveys = ["A", "A", "B", "A", "B", "B", "A"]
    return scores, real, surveys, {"A": 4.0, "B": 6.0}


def test_hand_computed_operating_point():
    scores, real, surveys, area = _hand_case()
    op = select_operating_point(scores, real, surveys, area, budget_fa_per_km2=0.5)
    assert op.feasible and op.threshold == 0.8
    assert op.fa_count == 1 and op.area_km2 == 10.0
    assert op.fa_rate == pytest.approx(0.1)
    assert op.fa_rate_upper == pytest.approx(0.47439, abs=1e-4)
    assert (op.tp, op.positives) == (2, 4) and op.recall == 0.5
    assert op.recall_ci == pytest.approx(clopper_pearson(2, 4))
    assert op.n_surveys == 2


def test_generous_budget_keeps_everything():
    scores, real, surveys, area = _hand_case()
    op = select_operating_point(scores, real, surveys, area, budget_fa_per_km2=100.0)
    assert op.threshold == 0.2 and op.recall == 1.0 and op.fa_count == 3


def test_too_little_area_is_infeasible_not_guessed():
    scores, real, surveys, _ = _hand_case()
    op = select_operating_point(
        scores, real, surveys, {"A": 0.004, "B": 0.006}, budget_fa_per_km2=1.0
    )
    assert not op.feasible and op.threshold == math.inf
    assert op.tp == 0 and op.recall == 0.0
    # the area needed to certify the budget with zero false alarms
    assert op.min_area_km2 == pytest.approx(-math.log(0.05) / 1.0)


def test_unknown_outcomes_excluded_and_counted():
    scores, real, surveys, area = _hand_case()
    scores = [*scores, 0.99]
    real = [*real, np.nan]
    surveys = [*surveys, "A"]
    op = select_operating_point(scores, real, surveys, area, budget_fa_per_km2=0.5)
    assert op.n_unknown == 1 and op.threshold == 0.8 and op.fa_count == 1


def test_survey_without_contacts_still_adds_area():
    scores, real, surveys, area = _hand_case()
    op = select_operating_point(
        scores, real, surveys, {**area, "C": 10.0}, budget_fa_per_km2=0.5
    )
    assert op.area_km2 == 20.0 and op.n_surveys == 3


def test_ties_are_kept_together():
    op = select_operating_point(
        [0.9, 0.5, 0.5], [1, 1, 0], ["A", "A", "A"], {"A": 1000.0}, budget_fa_per_km2=0.01
    )
    # a threshold of 0.5 must include both tied contacts, true and false
    assert op.threshold == 0.5 and op.fa_count == 1 and op.tp == 2


@pytest.mark.parametrize(
    "kwargs",
    [
        {"surveys": ["A", "A", "Z", "A", "B", "B", "A"]},  # survey without an area
        {"area": {"A": 4.0, "B": 0.0}},
        {"budget": 0.0},
        {"delta": 1.0},
        {"real": [0, 0, 2, 1, 1, 1, 1]},
        {"scores": [0.95, 0.7, np.nan, 0.9, 0.8, 0.6, 0.2]},
    ],
)
def test_operating_point_input_errors(kwargs):
    scores, real, surveys, area = _hand_case()
    with pytest.raises(ValueError):
        select_operating_point(
            kwargs.get("scores", scores),
            kwargs.get("real", real),
            kwargs.get("surveys", surveys),
            kwargs.get("area", area),
            budget_fa_per_km2=kwargs.get("budget", 0.5),
            delta=kwargs.get("delta", 0.05),
        )
