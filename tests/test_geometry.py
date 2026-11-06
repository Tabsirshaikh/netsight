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


def test_bottom_track_all_water_gives_nan():
    alt = bottom_track(np.zeros((3, 100)), 0.1)
    assert np.isnan(alt).all()


def test_fuse_altitude_prefers_agreeing_recorded_value():
    alt, src = fuse_altitude(np.array([5.0, 5.0, np.nan, 9.0]), np.array([5.2, np.nan, 4.8, 5.0]))
    np.testing.assert_allclose(alt, [5.0, 5.0, 4.8, 5.0])
    assert src == ["recorded", "recorded", "bottom_track", "bottom_track"]
    alt2, src2 = fuse_altitude(np.array([np.nan]), np.array([np.nan]))
    assert math.isnan(alt2[0]) and src2 == ["missing"]


def test_ground_range_conversion_leaves_nadir_gap_nan():
    row = seabed_row(500, 0.1, 5.0)
    grid = ground_range_grid(math.sqrt(50**2 - 5**2), 0.1)
    out = to_ground_range(row, 0.1, 5.0, grid)
    assert out.shape == grid.shape and out.dtype == np.float32
    assert np.isnan(out[:3]).all()  # inside the nadir gap
    assert np.isfinite(out[20:-2]).all()
    assert np.nanmean(out[20:]) == pytest.approx(np.mean(row[60:]), rel=0.05)


def test_ground_range_without_altitude_is_all_nan():
    grid = ground_range_grid(10.0, 0.5)
    assert np.isnan(to_ground_range(np.ones(100), 0.1, math.nan, grid)).all()


def test_grazing_angle():
    g = grazing_angle_deg(np.array([5.0, 50.0]), 5.0)
    assert g[0] == pytest.approx(45.0) and g[1] == pytest.approx(math.degrees(math.atan(0.1)))
