import json
import math

import numpy as np
import pytest
from helpers.synth_xtf import seabed_row, write_synthetic_xtf

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
    g_last = math.sqrt((499.5 * 0.1) ** 2 - 5.0**2)
    n_bins = math.floor(g_last / 0.1 + 0.5)
    assert sw.ground_res_m == 0.10
    assert sw.port.shape == (12, n_bins) and sw.stbd.shape == (12, n_bins)
    assert sw.grazing_deg.shape == (12, n_bins)
    np.testing.assert_allclose(sw.altitude_m, 5.0)
    assert set(sw.altitude_source) == {"recorded"}
    assert sw.not_searched_port[:, :3].all() and not sw.not_searched_port[:, 50:].any()
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
    assert np.isfinite(sw.port[:, 50:]).all()  # short surveys are not wiped out
    meta = sw.metadata()
    json.dumps(meta)
    assert meta["n_pings"] == 6 and meta["ground_res_m"] == 0.10
    assert meta["sensor"]["source_format"] == "xtf"
    out = sw.to_npz(tmp_path / "m_swath.npz")
    with np.load(out) as z:
        np.testing.assert_array_equal(z["port"], sw.port)
        assert json.loads(str(z["metadata"]))["n_pings"] == 6
        assert z["coord_kind"].tolist() == sw.coord_kind
        assert z["nav_source"].tolist() == sw.nav_source
        assert z["altitude_source"].tolist() == sw.altitude_source
        np.testing.assert_array_equal(z["quality_q"], sw.quality.q)
        for name, flag in sw.quality.flags.items():
            np.testing.assert_array_equal(z[f"flag_{name}"], flag)
        np.testing.assert_array_equal(z["equalise_rejected_port"], sw.equalise_rejected_port)
        np.testing.assert_array_equal(z["equalise_rejected_stbd"], sw.equalise_rejected_stbd)


def test_no_altitude_anywhere_raises(tmp_path):
    rec = read_xtf(write_synthetic_xtf(tmp_path / "z.xtf", n_pings=3))
    for p in rec.pings:
        p.altitude_m = float("nan")
        p.port[:] = 0
        p.stbd[:] = 0
    with pytest.raises(ValueError, match="altitude"):
        normalise_record(rec)


def test_varying_range_scale_tracks_each_group_with_its_own_spacing(tmp_path):
    rec = read_xtf(write_synthetic_xtf(tmp_path / "v.xtf", n_pings=12, n_samples=500))
    for i, p in enumerate(rec.pings):
        p.altitude_m = float("nan")
        if i >= 6:
            p.slant_range_m = 75.0
            row = seabed_row(500, 0.15, 7.5, ping=i).astype(np.float32)
            p.port, p.stbd = row.copy(), row.copy()
    sw = normalise_record(rec)
    assert set(sw.altitude_source) == {"bottom_track"}
    assert np.all(np.abs(sw.altitude_m[:6] - 5.0) <= 0.1 + 1e-9)
    assert np.all(np.abs(sw.altitude_m[6:] - 7.5) <= 0.15 + 1e-9)


def test_one_side_dropout_keeps_the_other_side(tmp_path):
    rec = read_xtf(write_synthetic_xtf(tmp_path / "s.xtf", n_pings=12))
    for p in rec.pings:
        p.stbd[:] = 0
    sw = normalise_record(rec)
    assert not sw.not_searched_port[:, 50:].any()
    assert np.isfinite(sw.port[:, 50:]).all()
    assert sw.not_searched_stbd.all() and np.isnan(sw.stbd).all()
    assert (sw.quality.q > 0).all()
    assert sw.quality.flags["side_dropout"].all() and not sw.quality.flags["dropout"].any()
    assert any("starboard channel has no usable data" in n for n in sw.provenance.notes)
    assert not any("port channel has no usable data" in n for n in sw.provenance.notes)
    assert rec.provenance.notes == [n for n in rec.provenance.notes if "usable data" not in n]


def test_per_side_repair_and_gap_at_the_same_row(tmp_path):
    rec = read_xtf(write_synthetic_xtf(tmp_path / "r.xtf", n_pings=14))
    rec.pings[4].port[:] = 0  # single-row dropout on port: repaired
    for p in rec.pings[3:9]:  # long run on starboard: gap
        p.stbd[:] = 0
    for p in rec.pings[11:]:  # both sides: gap
        p.port[:] = 0
        p.stbd[:] = 0
    sw = normalise_record(rec)
    f = sw.quality.flags
    assert sw.not_searched_stbd[3:9].all() and not sw.not_searched_port[4, 50:].any()
    assert np.isfinite(sw.port[4, 50:]).all()
    assert f["side_dropout"][3:9].all() and not f["side_dropout"][[0, 2, 9, 10, 11, 12, 13]].any()
    assert f["repaired"][4] and not f["repaired"][[3, 5, 11, 12, 13]].any()
    assert f["dropout"][11:].all() and not f["dropout"][:11].any()
    assert sw.not_searched_port[11:].all() and sw.not_searched_stbd[11:].all()
    assert (sw.quality.q[11:] == 0).all() and (sw.quality.q[3:9] > 0).all()


def test_missing_nav_keeps_nan_coordinates(tmp_path):
    rec = read_xtf(write_synthetic_xtf(tmp_path / "n.xtf", n_pings=6, nav="missing"))
    sw = normalise_record(rec)
    assert np.isnan(sw.x).all() and np.isnan(sw.y).all()
    assert sw.quality.flags["nav_missing"].all()
    assert set(sw.nav_source) == {"missing"}


def test_equalise_rejections_are_not_coverage(tmp_path):
    rec = read_xtf(write_synthetic_xtf(tmp_path / "e.xtf", n_pings=12))
    for p in rec.pings:
        p.port[295:305] = 0  # zero columns: finite data, but the equaliser cannot level them
    sw = normalise_record(rec)
    assert sw.equalise_rejected_port.any() and not sw.equalise_rejected_stbd.any()
    assert not (sw.not_searched_port & sw.equalise_rejected_port).any()
    assert not sw.not_searched_port[:, 50:].any()
    meta = sw.metadata()
    assert meta["equalise_rejected_cells"]["port"] == int(sw.equalise_rejected_port.sum())
    assert meta["equalise_rejected_cells"]["stbd"] == 0


def test_altitude_above_slant_range_raises_clear_error(tmp_path):
    rec = read_xtf(write_synthetic_xtf(tmp_path / "h.xtf", n_pings=4))
    for p in rec.pings:
        p.altitude_m = 80.0
        p.port[:] = 0
        p.stbd[:] = 0
    with pytest.raises(ValueError, match="altitude exceeds slant range"):
        normalise_record(rec)


@pytest.mark.parametrize("bad", [0.0, -0.1])
def test_non_positive_ground_resolution_raises(tmp_path, bad):
    rec = read_xtf(write_synthetic_xtf(tmp_path / "g.xtf", n_pings=4))
    with pytest.raises(ValueError, match="ground_res_m"):
        normalise_record(rec, ground_res_m=bad)


def test_metadata_uses_python_floats_and_npz_path_has_extension(tmp_path):
    sw = normalise_record(read_xtf(write_synthetic_xtf(tmp_path / "p.xtf", n_pings=6)))
    meta = sw.metadata()
    assert type(meta["ground_res_m"]) is float
    assert type(meta["not_searched_fraction"]) is float
    out = sw.to_npz(tmp_path / "noext")
    assert out == tmp_path / "noext.npz" and out.exists()
