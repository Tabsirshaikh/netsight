"""Regression test on a real NOAA KMALL file: #IIP and the first ping (both swaths) of
0000_20210502_132355_EX2101_MB.kmall (Okeanos Explorer EM304, Blake Plateau; NCEI, public
domain). The first reader version rejected multi-fan pings and could not read this file."""

from pathlib import Path

import numpy as np

from netsight.io.kmall import read_kmall

DATA = Path(__file__).parent / "data" / "noaa_ex2101_em304_1ping.kmall"


def test_real_em304_dual_swath_ping():
    rec = read_kmall(DATA)
    # dual swath: the ping's two "fans" are two full-width swaths one behind the other
    assert rec.sonar_model == "EM304" and rec.number_of_pings == 2
    p = rec.pings[0]
    assert len(p.depth) == 800 and p.valid.mean() > 0.9
    assert 700 < np.median(p.depth[p.valid]) < 1100  # Blake Plateau depths, metres
    assert np.nanmin(p.across_track) < -1500 and np.nanmax(p.across_track) > 1500
    assert 28 < p.latitude < 29 and -79 < p.longitude < -78
    assert not any("missing" in n for n in rec.notes)
