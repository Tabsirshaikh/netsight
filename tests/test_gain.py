import numpy as np
import pytest

from netsight.radiometry.gain import _block_slices, across_track_equalise, to_log


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


def test_block_slices_merge_short_tail():
    assert _block_slices(401, 200) == [slice(0, 200), slice(200, 401)]
    assert _block_slices(403, 200) == [slice(0, 200), slice(200, 403)]
    assert _block_slices(400, 200) == [slice(0, 200), slice(200, 400)]
    assert _block_slices(300, 200) == [slice(0, 200), slice(200, 300)]  # tail == block // 2 kept
    assert _block_slices(150, 200) == [slice(0, 150)]
    assert _block_slices(0, 200) == []


@pytest.mark.parametrize("n_pings", [401, 403])
def test_short_tail_rows_are_not_flattened(n_pings):
    rng = np.random.default_rng(1)
    base = 100.0 + rng.normal(0, 5, (n_pings, 200))
    falloff = 1.0 / (1.0 + np.arange(200) / 50.0)
    out = across_track_equalise(base * falloff, block=200)
    row_std = out.std(axis=1)
    tail = n_pings % 200
    assert row_std[-tail:].mean() > 0.9 * row_std[:200].mean()


def test_median_level_resists_short_along_track_feature():
    rng = np.random.default_rng(2)
    sw = 1.0 + rng.normal(0, 0.01, (200, 40))
    sw[70:130, 10:20] *= 3.0  # 30% of the block's pings, 10 columns
    out = across_track_equalise(sw, block=200)
    feature = out[70:130, 10:20].mean()
    background = np.delete(out, slice(10, 20), axis=1).mean()
    assert feature / background >= 2.5


def test_min_count_gives_nan_for_sparse_columns():
    sw = np.ones((20, 4))
    sw[:, 1] = np.nan
    sw[3, 1] = 5.0  # lone sample
    sw[:15, 2] = np.nan  # 5 finite values
    out = across_track_equalise(sw, block=20, min_count=10)
    assert np.isnan(out[:, 1]).all() and np.isnan(out[:, 2]).all()
    assert np.isfinite(out[:, [0, 3]]).all()
    out_lax = across_track_equalise(sw, block=20, min_count=1)
    assert np.isfinite(out_lax[3, 1]) and np.isfinite(out_lax[15:, 2]).all()


@pytest.mark.parametrize("kwargs", [{"block": 0}, {"block": -5}, {"min_count": 0}])
def test_invalid_parameters_raise(kwargs):
    with pytest.raises(ValueError):
        across_track_equalise(np.ones((10, 3)), **kwargs)


def test_to_log():
    out = to_log(np.array([1.0, 100.0, 0.0, np.nan]))
    assert out[0] == pytest.approx(0.0) and out[1] == pytest.approx(20.0)
    assert out[2] == pytest.approx(-30.0) and np.isnan(out[3])
