import numpy as np
import pytest
from helpers.swaths import smooth_swath

from netsight.qc.quality import SEVERITY, compute_quality


def inputs(n=10):
    return dict(
        times=np.datetime64("2026-11-06T12:00:00") + np.arange(n).astype("timedelta64[s]"),
        ping_numbers=np.arange(100, 100 + n),
        roll_deg=np.zeros(n),
        pitch_deg=np.zeros(n),
        altitude_m=np.full(n, 5.0),
        slant_range_m=np.full(n, 50.0),
        swath=smooth_swath(n),
        gap_rows=np.zeros(n, bool),
        repaired_rows=np.zeros(n, bool),
        nav_missing=np.zeros(n, bool),
    )


def test_clean_data_scores_one():
    qm = compute_quality(**inputs())
    np.testing.assert_allclose(qm.q, 1.0)
    assert not any(f.any() for f in qm.flags.values())


def test_roll_spike_penalises_attitude_and_rate():
    kw = inputs()
    kw["roll_deg"][3] = 8.0
    qm = compute_quality(**kw)
    assert qm.flags["attitude"][3] and qm.flags["attitude_rate"][3] and qm.flags["attitude_rate"][4]
    assert qm.q[3] == pytest.approx((1 - SEVERITY["attitude"]) * (1 - SEVERITY["attitude_rate"]))
    assert qm.q[4] == pytest.approx(1 - SEVERITY["attitude_rate"])


def test_altitude_jump_missing_and_towfish_height():
    kw = inputs()
    kw["altitude_m"][5] = 12.0
    kw["altitude_m"][8] = np.nan
    qm = compute_quality(**kw)
    assert qm.flags["altitude_jump"][5] and qm.flags["altitude_jump"][6]
    assert qm.flags["towfish_height"][5]  # 12/50 = 0.24 > 0.20
    assert qm.flags["altitude_missing"][8]


def test_ping_gap_and_nav_missing_recorded_without_penalty():
    kw = inputs()
    kw["ping_numbers"][6:] += 5
    kw["nav_missing"][2] = True
    qm = compute_quality(**kw)
    assert qm.flags["ping_gap"][6] and qm.flags["nav_missing"][2]
    assert qm.q[6] == pytest.approx(1.0) and qm.q[2] == pytest.approx(1.0)


def test_stripe_row_flagged_but_not_its_neighbours():
    kw = inputs()
    kw["swath"][4] = np.random.default_rng(9).normal(100, 30, kw["swath"].shape[1])
    qm = compute_quality(**kw)
    assert qm.flags["stripe"][4]
    assert not qm.flags["stripe"][3] and not qm.flags["stripe"][5]


def test_dropout_gap_zeroes_q_and_summary_counts():
    kw = inputs()
    kw["gap_rows"][7] = True
    kw["repaired_rows"][1] = True
    qm = compute_quality(**kw)
    assert qm.q[7] == 0.0
    assert qm.q[1] == pytest.approx(1 - SEVERITY["repaired"])
    s = qm.summary()
    assert s["flag_counts"]["dropout"] == 1 and 0 < s["mean_q"] < 1
