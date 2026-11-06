import json
import math

import numpy as np
import pytest
from helpers.synth_xtf import write_synthetic_xtf

from netsight.io.xtf import read_xtf
from netsight.normalise.swath import choose_ground_resolution, normalise_record


def test_choose_ground_resolution_never_upsamples():
    assert choose_ground_resolution(0.1) == 0.10
    assert choose_ground_resolution(0.03) == 0.05
    assert choose_ground_resolution(0.015) == 0.02
    assert choose_ground_resolution(2.0) == 0.50


def test_normalise_synthetic_xtf(tmp_path):
    rec = read_xtf(write_synthetic_xtf(tmp_path / "a.xtf", n_pings=12, n_samples=500))
    sw = normalise_record(rec)
    n_bins = math.ceil(math.sqrt(50**2 - 5**2) / 0.1)
    assert sw.ground_res_m == 0.10
    assert sw.port.shape == (12, n_bins) and sw.stbd.shape == (12, n_bins)
    assert sw.grazing_deg.shape == (12, n_bins)
    np.testing.assert_allclose(sw.altitude_m, 5.0)
    assert set(sw.altitude_source) == {"recorded"}
    assert sw.not_searched_port[:, :3].all() and not sw.not_searched_port[:, 50:-1].any()
    np.testing.assert_allclose(sw.quality.q, 1.0)
    assert set(sw.nav_source) == {"sensor"}


def test_dropout_rows_become_not_searched(tmp_path):
    rec = read_xtf(write_synthetic_xtf(tmp_path / "d.xtf", n_pings=12))
    for p in rec.pings[4:8]:
        p.port[:] = 0
        p.stbd[:] = 0
    sw = normalise_record(rec)
    assert sw.not_searched_port[4:8].all() and sw.not_searched_stbd[4:8].all()
    assert (sw.quality.q[4:8] == 0).all()


def test_metadata_and_npz_round_trip(tmp_path):
    sw = normalise_record(read_xtf(write_synthetic_xtf(tmp_path / "m.xtf", n_pings=6)))
    assert np.isfinite(sw.port[:, 50:-1]).all()  # short surveys are not wiped out
    meta = sw.metadata()
    json.dumps(meta)
    assert meta["n_pings"] == 6 and meta["ground_res_m"] == 0.10
    assert meta["sensor"]["source_format"] == "xtf"
    out = sw.to_npz(tmp_path / "m_swath.npz")
    with np.load(out) as z:
        np.testing.assert_array_equal(z["port"], sw.port)
        assert json.loads(str(z["metadata"]))["n_pings"] == 6


def test_no_altitude_anywhere_raises(tmp_path):
    rec = read_xtf(write_synthetic_xtf(tmp_path / "z.xtf", n_pings=3))
    for p in rec.pings:
        p.altitude_m = float("nan")
        p.port[:] = 0
        p.stbd[:] = 0
    with pytest.raises(ValueError, match="altitude"):
        normalise_record(rec)
