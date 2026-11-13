import numpy as np
import pytest

from netsight.detect.operating_run import count_threshold
from netsight.trust.area_budget import equivalent_image_budget, searched_area_km2


def test_searched_area_counts_only_insonified_seabed():
    image = np.zeros((100, 200), np.uint8)
    image[:, 100:] = 120  # right half is seabed, left half is dark water column
    area = searched_area_km2([image], [0.5])  # 0.5 m pixels -> 0.25 m2 per pixel
    # local-mean mask spreads ~15 px into the dark half; allow that margin
    assert 100 * 100 * 0.25 / 1e6 <= area <= 100 * 116 * 0.25 / 1e6


def test_searched_area_sums_images_with_their_own_pixel_size():
    a = np.full((10, 10), 100, np.uint8)
    assert searched_area_km2([a, a], [1.0, 2.0]) == pytest.approx((100 + 400) / 1e6)


def test_searched_area_rejects_bad_pixel_size():
    with pytest.raises(ValueError):
        searched_area_km2([np.full((4, 4), 100, np.uint8)], [0.0])
    with pytest.raises(ValueError):
        searched_area_km2([np.full((4, 4), 100, np.uint8)], [])


def test_area_budget_uses_the_count_rule_with_km2_as_the_unit():
    scores = np.array([0.9, 0.8, 0.7, 0.4])
    # 3 false alarms per km2 over 0.7 km2 -> at most floor(2.1) = 2 flagged
    t = count_threshold(scores, 0.7, 3.0)
    assert np.count_nonzero(scores >= t) == 2


def test_equivalent_image_budget_is_flagged_allowance_per_image():
    assert equivalent_image_budget(500.0, 0.004, 4) == pytest.approx(0.5)
    assert equivalent_image_budget(0.0, 0.004, 4) == 0.0
