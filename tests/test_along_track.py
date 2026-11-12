import numpy as np
import pytest

from netsight.normalise.along_track import ping_distances, robust_spacing, square_waterfall


def _track(n, step, kind="projected"):
    y = np.arange(n) * step
    return np.zeros(n), y, [kind] * n


def test_distances_projected_and_latlon():
    x, y, k = _track(4, 0.2)
    d = ping_distances(x, y, k)
    assert np.isnan(d[0]) and d[1:] == pytest.approx([0.2] * 3)
    lat = np.array([10.0, 10.0 + 1 / 111320])
    assert ping_distances(np.zeros(2), lat, ["latlon"] * 2)[1] == pytest.approx(1.0)


def test_missing_nav_is_filled_with_median():
    x, y, k = _track(10, 0.2)
    k[5] = "none"
    s, frac = robust_spacing(ping_distances(x, y, k), window=3)
    assert s == pytest.approx([0.2] * 10)
    assert frac == pytest.approx(0.7)  # first ping, plus both intervals touching the gap


def test_square_pixels_double_rows_when_pings_are_twice_the_pixel():
    x, y, k = _track(101, 0.2)
    img = np.tile(np.arange(101, dtype=np.uint8)[:, None], (1, 5))
    sq = square_waterfall(img, x, y, k, across_m=0.1)
    assert sq.image.shape == (201, 5)
    assert sq.stretch == pytest.approx(201 / 101)
    assert sq.image[2, 0] == 1 and sq.image[200, 0] == 100  # row 2 = ping 1, last = last ping
    assert sq.ping_of_row(100) == pytest.approx(50.0)
    assert sq.native_along_m == pytest.approx(0.2)


def test_object_becomes_square():
    """A 1 m x 1 m object imaged with 0.25 m pings and 0.1 m range bins is 4 rows x 10 cols;
    after correction it is 10 x 10."""
    x, y, k = _track(40, 0.25)
    img = np.zeros((40, 30), np.uint8)
    img[20:24, 10:20] = 200
    sq = square_waterfall(img, x, y, k, across_m=0.1)
    rows = np.flatnonzero(sq.image[:, 15] > 100)
    assert 9 <= len(rows) <= 11


def test_implausible_navigation_rejected():
    x, y, k = _track(10, 50.0)  # 50 m per ping
    with pytest.raises(ValueError):
        square_waterfall(np.zeros((10, 4)), x, y, k, across_m=0.1)
