import numpy as np
import pytest

from netsight.trust.baselines import (
    b2_combine_passes,
    b2_hand_set_pd,
    b3_shadow_filter,
    rel_range_from_image_x,
)


def test_b2_shape():
    pd = b2_hand_set_pd([0.0, 0.5, 0.85, 1.0, 1.2])
    assert pd[0] == 0.0  # nadir gap
    assert pd[2] == pytest.approx(0.95 / 2)  # midpoint
    assert pd[1] > pd[2] > pd[3]
    assert pd[4] == 0.0  # beyond range


def test_b2_max_combination():
    np.testing.assert_allclose(b2_combine_passes([[0.2, 0.9], [0.6, 0.1]]), [0.6, 0.9])


def test_rel_range():
    np.testing.assert_allclose(rel_range_from_image_x([0, 50, 100], 100), [1, 0, 1])
    np.testing.assert_allclose(rel_range_from_image_x([0, 100], 100, nadir="left"), [0, 1])
    with pytest.raises(ValueError):
        rel_range_from_image_x([1], 10, nadir="up")


def test_b3():
    np.testing.assert_allclose(b3_shadow_filter([0.9, 0.8], [True, False]), [0.9, 0.0])
    with pytest.raises(ValueError):
        b3_shadow_filter([0.9], [True, False])
