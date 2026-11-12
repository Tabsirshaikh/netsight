"""Hand-computed checks for multibeam AVG and image formation."""

from dataclasses import replace

import numpy as np
import pytest
import rasterio

from netsight.io.multibeam import MultibeamPing
from netsight.normalise.backscatter import (
    AngularResponse,
    BackscatterGrid,
    beam_positions_en,
    fit_angular_response,
    fit_moving,
    grid_backscatter,
    incidence_angle_deg,
    normalise_ping,
    write_grid_geotiff,
)


def ping(across=(0.0,), along=None, values=None, **kw):
    """Build a fully specified synthetic ping."""
    across = np.asarray(across, dtype=float)
    n = len(across)
    args = dict(
        time=np.datetime64("2025-01-01", "ns"),
        latitude=0.0,
        longitude=3.0,
        heading=0.0,
        sound_speed=1500.0,
        across_track=across,
        along_track=np.zeros(n) if along is None else np.asarray(along, dtype=float),
        depth=np.full(n, 10.0),
        backscatter=np.full(n, -20.0) if values is None else np.asarray(values, dtype=float),
        valid=np.ones(n, dtype=bool),
        beam_flags=np.zeros(n, dtype=np.uint8),
    )
    args.update(kw)
    return MultibeamPing(**args)


def test_incidence():
    np.testing.assert_allclose(
        incidence_angle_deg([0, 10, -10, 1, 1, np.nan], [10, 10, 10, 0, np.inf, 10]),
        [0, 45, 45, np.nan, np.nan, np.nan],
        equal_nan=True,
    )


def test_curve_flattening():
    angles = np.arange(5.0, 71.0)
    levels = -20 + 10 * np.cos(np.radians(angles)) ** 2
    p = ping(10 * np.tan(np.radians(angles)), values=levels)
    ar = fit_angular_response([p], bin_deg=0.5, min_count=1)
    np.testing.assert_allclose(normalise_ping(p, ar), ar.reference_db, atol=0.1)
    # Inclusive window on the angles as computed (30 deg may round to 29.999999).
    computed = incidence_angle_deg(p.across_track, p.depth)
    inside = (computed >= 30) & (computed <= 60)
    expected = 10 * np.log10(np.mean(10 ** (levels[inside] / 10)))
    assert ar.reference_db == pytest.approx(expected)


def test_power_average_empty_bins_and_invalid():
    p = ping([10, 10, 0], values=[-10, -20, 100], valid=np.array([True, True, False]))
    ar = fit_angular_response(p, bin_deg=10, min_count=2)
    expected = 10 * np.log10(0.055)
    assert expected == pytest.approx(-12.596373105, abs=1e-8)
    assert ar.mean_db[4] == pytest.approx(expected)
    assert ar.reference_db == pytest.approx(expected)
    assert ar.count[4] == 2
    assert ar.count[0] == 0
    assert np.isnan(ar.correction_db([5, -1, 76, np.nan])).all()
    assert np.isnan(normalise_ping(p, ar)[2])
    sparse = fit_angular_response(p, min_count=3)
    assert np.isnan(sparse.reference_db)
    assert np.isnan(sparse.mean_db).all()


def test_bin_endpoints_and_positions():
    ar = AngularResponse(np.array([0, 30, 60]), np.array([-20, -10]), np.array([1, 1]), -15)
    np.testing.assert_allclose(ar.correction_db([0, 30, 60, 61]), [5, -5, -5, np.nan])
    p = ping([10], along=[2])
    east, north = beam_positions_en(p, 0, 3)
    np.testing.assert_allclose([east[0], north[0]], [10, 2])
    east, north = beam_positions_en(replace(p, heading=90), 0, 3)
    np.testing.assert_allclose([east[0], north[0]], [2, -10], atol=1e-12)
    offset = replace(p, latitude=1 / 111320, longitude=3 + 2 / 111320)
    east, north = beam_positions_en(offset, 0, 3)
    np.testing.assert_allclose([east[0], north[0]], [12, 3], atol=1e-8)
    east, north = beam_positions_en(replace(p, latitude=np.nan), 0, 3)
    assert np.isnan(east).all() and np.isnan(north).all()


def test_moving_windows():
    pings = [ping([10], values=[v]) for v in (-10, -20, -30, -40)]
    fits = fit_moving(pings, window_pings=2, min_count=1)
    # At index 0 the left-clipped window has just ping 0; at 1 it has 0 and 1.
    assert fits[0].reference_db == pytest.approx(-10)
    assert fits[1].reference_db == pytest.approx(10 * np.log10(0.055))
    assert fits[3].reference_db == pytest.approx(10 * np.log10(0.00055))
    reused = fit_moving(pings, window_pings=8, min_count=1)
    assert reused[0] is reused[1]
    assert reused[2] is reused[3]
    assert reused[0] is not reused[2]


def make_grid():
    p1 = ping([0.25, 1.25], along=[0.25, 1.25])
    p2 = ping([0.25, 0.25], along=[0.25, 1.25])
    missing = replace(p1, latitude=np.nan)
    return grid_backscatter(
        [p1, p2, missing],
        [np.array([-10, -20]), np.array([-20, -30]), np.array([100, 100])],
        cell_m=1,
    )


def test_grid_and_image():
    grid = make_grid()
    np.testing.assert_array_equal(grid.count, [[1, 1], [2, 0]])
    np.testing.assert_allclose(
        grid.values_db,
        [[-30, -20], [10 * np.log10(0.055), np.nan]],
        equal_nan=True,
    )
    assert grid.transform_local() == (1, 0, 0, 0, -1, 2)
    assert grid.notes == ("1 pings without navigation skipped",)
    simple = BackscatterGrid(
        np.array([[-20.0, -10.0, 0.0, np.nan]]),
        np.array([[1, 1, 1, 0]]),
        0,
        1,
        1,
        0,
        3,
        (),
    )
    np.testing.assert_array_equal(simple.to_uint8(0, 100), [[1, 128, 255, 0]])
    constant = replace(simple, values_db=np.array([[-10.0, -10.0, -10.0, np.nan]]))
    np.testing.assert_array_equal(constant.to_uint8(), [[1, 1, 1, 0]])


def test_geotiff(tmp_path):
    grid = make_grid()
    path = tmp_path / "backscatter.tif"
    write_grid_geotiff(path, grid, 32631)
    # UTM zone 31 central meridian at the equator is (500000, 0).
    with rasterio.open(path) as dataset:
        assert dataset.transform.c == pytest.approx(500000, abs=1e-6)
        assert dataset.transform.f == pytest.approx(2, abs=1e-6)
        assert dataset.transform.a == 1
        assert dataset.transform.e == -1
        assert dataset.crs.to_epsg() == 32631
        assert np.isnan(dataset.nodata)
        assert "approximation" in dataset.tags()["NETSIGHT_NOTE"]
        np.testing.assert_allclose(dataset.read(1), grid.values_db, atol=1e-6, equal_nan=True)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"bin_deg": 0},
        {"max_angle_deg": np.nan},
        {"min_count": 0},
        {"reference": (60, 30)},
    ],
)
def test_bad_fit_input(kwargs):
    with pytest.raises(ValueError):
        fit_angular_response([], **kwargs)


def test_bad_grid_input():
    p = ping()
    with pytest.raises(ValueError, match="one array"):
        grid_backscatter([p], [])
    with pytest.raises(ValueError, match="cell_m"):
        grid_backscatter([p], [p.backscatter], cell_m=0)
    with pytest.raises(ValueError, match="navigation"):
        grid_backscatter([replace(p, latitude=np.nan)], [p.backscatter])
    with pytest.raises(ValueError, match="geolocated"):
        grid_backscatter([p], [np.array([np.nan])])
    with pytest.raises(ValueError, match="window_pings"):
        fit_moving([p], window_pings=0)
    with pytest.raises(ValueError, match="percentiles"):
        make_grid().to_uint8(99, 1)
