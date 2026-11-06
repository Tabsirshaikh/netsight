import numpy as np
import pytest

from netsight.radiometry.gain import across_track_equalise, to_log


def test_equalisation_flattens_range_falloff():
    rng = np.random.default_rng(0)
    base = 100.0 + rng.normal(0, 5, (300, 200))
    falloff = 1.0 / (1.0 + np.arange(200) / 50.0)
    out = across_track_equalise(base * falloff, block=100)
    col_means = out.mean(axis=0)
    assert col_means.std() / col_means.mean() < 0.01
    assert out.dtype == np.float32


def test_equalisation_keeps_nan_columns_nan():
    sw = np.ones((10, 5))
    sw[:, 0] = np.nan
    out = across_track_equalise(sw)
    assert np.isnan(out[:, 0]).all() and np.isfinite(out[:, 1:]).all()


def test_to_log():
    out = to_log(np.array([1.0, 100.0, 0.0, np.nan]))
    assert out[0] == pytest.approx(0.0) and out[1] == pytest.approx(20.0)
    assert out[2] == pytest.approx(-30.0) and np.isnan(out[3])
