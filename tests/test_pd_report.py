import math

import pytest

from netsight.trust.injection import Trial
from netsight.trust.pd_report import pd_table, range_bin, realism_check


def _t(score, group="s1", kind="block", stratum="smooth", rel_x=0.5):
    return Trial(0, group, kind, "parametric", (0, 0, 1, 1), 0.1, stratum, rel_x, 1.0, score)


def test_pd_table_uses_each_surveys_own_threshold():
    trials = [_t(0.6, "a"), _t(0.6, "b"), _t(0.0, "a")]
    rows = pd_table(trials, {"a": 0.5, "b": 0.7}, by=("kind",))
    assert rows == [pytest.approx(rows[0])]
    (row,) = rows
    assert row["n"] == 3 and row["detected"] == 1
    assert row["pd"] == pytest.approx(1 / 3)


def test_pd_lower_bound_zero_miss():
    trials = [_t(0.9) for _ in range(29)]
    (row,) = pd_table(trials, {"s1": 0.5}, by=("kind",), alpha=0.05)
    # 29 of 29 detected: one-sided 95% lower bound is 0.05 ** (1 / 29)
    assert row["pd_lower"] == pytest.approx(0.05 ** (1 / 29), rel=1e-6)


def test_zero_score_never_detected_even_at_zero_threshold():
    (row,) = pd_table([_t(0.0)], {"s1": 0.0}, by=("kind",))
    assert row["detected"] == 0


def test_missing_threshold_rejected():
    with pytest.raises(ValueError):
        pd_table([_t(0.5, "x")], {"s1": 0.1})


def test_range_bins():
    key = range_bin([0, 0.5, 1.0])
    assert key(_t(0.1, rel_x=0.2)) == "0.00-0.50"
    assert key(_t(0.1, rel_x=0.7)) == "0.50-1.00"
    assert key(_t(0.1, rel_x=1.0)) == "0.50-1.00"
    rows = pd_table(
        [_t(0.9, rel_x=0.2), _t(0.0, rel_x=0.8)], {"s1": 0.5}, by=("range",), key_fn={"range": key}
    )
    assert [r["pd"] for r in rows] == [1.0, 0.0]


def test_realism_verdicts():
    assert realism_check(50, 100, 48, 100)["verdict"] == "consistent"
    assert realism_check(95, 100, 30, 100)["verdict"] == "optimistic"
    assert realism_check(5, 100, 60, 100)["verdict"] == "pessimistic"
    r = realism_check(0, 0, 5, 10)
    assert r["verdict"] == "insufficient" and math.isnan(r["injected_pd"])
