import numpy as np

from netsight.trust.calibrators import BetaCalibrator
from netsight.trust.reliability import METHODS, reliability_comparison, reliability_svg


def _data(n, rng):
    s = rng.uniform(0.05, 1, n)
    y = rng.random(n) < s**3  # raw score overconfident: true P(real) = score^3
    return s, y


def test_comparison_reports_three_methods_on_held_out_data():
    rng = np.random.default_rng(0)
    vs, vy = _data(4000, rng)
    ts, ty = _data(3000, rng)
    out = reliability_comparison(vs, vy, ts, ty, BetaCalibrator().fit(vs, vy))
    assert list(out["methods"]) == list(METHODS)
    assert out["n_test"] == 3000 and out["positives_test"] == int(ty.sum())
    ece = {k: v["ece"] for k, v in out["methods"].items()}
    assert ece["NetSight (beta)"] < ece["B0 raw score"]
    for method in out["methods"].values():
        bins = method["bins"]
        assert sum(b["count"] for b in bins) == 3000
        assert all(b["ci_low"] <= b["observed_rate"] <= b["ci_high"] for b in bins)


def test_svg_has_one_series_per_method_and_diagonal():
    rng = np.random.default_rng(1)
    vs, vy = _data(2000, rng)
    out = reliability_comparison(vs, vy, vs, vy, BetaCalibrator().fit(vs, vy))
    svg = reliability_svg(out)
    assert svg.startswith("<svg") and svg.count("<polyline") == 3
    assert "Perfect calibration" in svg and "B1 temperature" in svg
