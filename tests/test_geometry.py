import math

import numpy as np
import pytest
from helpers.synth_xtf import seabed_row

from netsight.geometry.slant import (
    bottom_track,
    fuse_altitude,
    grazing_angle_deg,
    ground_range_grid,
    to_ground_range,
)


def test_bottom_track_finds_first_seabed_return():
    m = np.stack([seabed_row(500, 0.1, 5.0, ping=i) for i in range(9)])
    alt = bottom_track(m, 0.1)
    assert alt.shape == (9,)
    np.testing.assert_allclose(alt, 5.0, atol=0.11)


def test_bottom_track_has_no_half_sample_bias():
    # Sample i has centre (i + 0.5) * spacing; the seabed starts at the first centre >= altitude,
    # so the true altitude lies in ((i0 - 0.5) * s, (i0 + 0.5) * s] and i0 * s is unbiased.
    alts = np.arange(4.0, 4.4, 0.013)
    errs = [
        bottom_track(np.stack([seabed_row(300, 0.1, a, ping=i) for i in range(5)]), 0.1)[2] - a
        for a in alts
    ]
    assert abs(np.mean(errs)) < 0.01
    assert np.max(np.abs(errs)) <= 0.0501


def test_bottom_track_all_water_gives_nan():
    alt = bottom_track(np.zeros((3, 100)), 0.1)
    assert np.isnan(alt).all()


def test_fuse_altitude_prefers_agreeing_recorded_value():
    alt, src = fuse_altitude(np.array([5.0, 5.0, np.nan, 9.0]), np.array([5.2, np.nan, 4.8, 5.0]))
    np.testing.assert_allclose(alt, [5.0, 5.0, 4.8, 5.0])
    assert src == ["recorded", "recorded", "bottom_track", "bottom_track"]
    alt2, src2 = fuse_altitude(np.array([np.nan]), np.array([np.nan]))
    assert math.isnan(alt2[0]) and src2 == ["missing"]


def test_fuse_altitude_treats_non_positive_recorded_as_missing():
    alt, src = fuse_altitude(np.array([0.0, -2.0, 0.0]), np.array([0.5, np.nan, np.nan]))
    assert alt[0] == 0.5 and np.isnan(alt[1:]).all()
    assert src == ["bottom_track", "missing", "missing"]


def test_ground_range_conversion_leaves_nadir_gap_nan():
    row = seabed_row(500, 0.1, 5.0)
    grid = ground_range_grid(math.sqrt(50**2 - 5**2), 0.1)
    out = to_ground_range(row, 0.1, 5.0, grid)
    assert out.shape == grid.shape and out.dtype == np.float32
    nadir_ground = math.sqrt((5.0 + 0.05) ** 2 - 5.0**2)  # first seabed sample centre
    assert (grid < nadir_ground).sum() > 3
    assert np.isnan(out[grid < nadir_ground]).all()  # whole nadir gap
    assert np.isfinite(out[20:-2]).all()
    assert np.nanmean(out[20:]) == pytest.approx(np.mean(row[60:]), rel=0.05)


def test_ground_range_interior_dropout_stays_nan():
    row = seabed_row(500, 0.1, 5.0)
    row[200:220] = np.nan
    grid = ground_range_grid(math.sqrt(50**2 - 5**2), 0.1)
    out = to_ground_range(row, 0.1, 5.0, grid)
    g = lambda k: math.sqrt(((k + 0.5) * 0.1) ** 2 - 5.0**2)  # noqa: E731
    in_gap = (grid > g(199)) & (grid < g(220))
    assert in_gap.sum() > 10
    assert np.isnan(out[in_gap]).all()
    assert np.isfinite(out[(grid > g(150)) & (grid < g(199))]).all()
    assert np.isfinite(out[(grid > g(220)) & (grid < g(300))]).all()


def test_ground_range_places_spike_at_its_ground_range():
    row = np.full(500, 100.0)
    row[200] = 1000.0
    grid = ground_range_grid(math.sqrt(50**2 - 5**2), 0.1)
    out = to_ground_range(row, 0.1, 5.0, grid)
    expected = math.sqrt((200.5 * 0.1) ** 2 - 5.0**2)
    assert abs(grid[np.nanargmax(out)] - expected) <= 0.1


def test_ground_range_without_altitude_is_all_nan():
    grid = ground_range_grid(10.0, 0.5)
    assert np.isnan(to_ground_range(np.ones(100), 0.1, math.nan, grid)).all()


def test_grazing_angle():
    g = grazing_angle_deg(np.array([5.0, 50.0]), 5.0)
    assert g[0] == pytest.approx(45.0) and g[1] == pytest.approx(math.degrees(math.atan(0.1)))
