import numpy as np
import pytest

from netsight.trust.coverage import multipass_grid, not_searched_mask, searched_fraction


def _waterfall(rng):
    img = rng.normal(120, 25, (200, 300)).clip(0, 255)
    img[:, 140:160] = rng.normal(8, 3, (200, 20)).clip(0, 255)  # water column at nadir
    img[:, 290:] = 0  # lost far range, blank
    img[50:80, 30:70] = rng.normal(55, 15, (30, 40)).clip(0, 255)  # dark sediment: searched
    return img.astype(np.uint8)


def test_mask_marks_nadir_and_lost_range_but_not_dark_seabed():
    m = not_searched_mask(_waterfall(np.random.default_rng(0)), waterfall=True)
    assert m[:, 145:155].all() and m[:, 292:].all()
    assert not m[55:75, 35:65].any()
    assert not m[:, 10:30].any()


def test_mosaic_mode_only_marks_blank_no_data():
    img = _waterfall(np.random.default_rng(1))
    m = not_searched_mask(img, waterfall=False)
    assert m[:, 292:].all()  # no-data border
    assert not m[:, 145:155].all()  # no column rule on mosaics


def test_searched_fraction_per_cell():
    mask = np.zeros((90, 90), bool)
    mask[:, :30] = True  # left third not searched
    f = searched_fraction(mask, (3, 3))
    np.testing.assert_allclose(f[:, 0], 0.0)
    np.testing.assert_allclose(f[:, 1:], 1.0)


def test_multipass_interval_on_overlap():
    # two passes on the same 2 x 2 map cells; pass B covers only the right column
    a = np.array([[0.5, 0.5], [0.5, 0.5]])
    b = np.array([[np.nan, 0.6], [np.nan, 0.6]])
    lo, hi, n = multipass_grid([a, b])
    np.testing.assert_allclose(lo, [[0.5, 0.6], [0.5, 0.6]])
    np.testing.assert_allclose(hi, [[0.5, 0.8], [0.5, 0.8]])
    np.testing.assert_array_equal(n, [[1, 2], [1, 2]])


def test_multipass_needs_same_shape():
    with pytest.raises(ValueError):
        multipass_grid([np.zeros((2, 2)), np.zeros((3, 2))])
