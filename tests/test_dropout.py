import numpy as np

from netsight.qc.dropout import repair_dropouts


def make():
    sw = np.tile(np.linspace(10, 20, 50), (20, 1))
    return sw


def test_isolated_bad_row_is_interpolated():
    sw = make()
    sw[3] = 0
    res = repair_dropouts(sw)
    np.testing.assert_allclose(res.data[3], sw[2])
    assert res.repaired_rows[3] and not res.gap_rows.any()


def test_long_gap_is_kept_as_not_searched():
    sw = make()
    sw[10:15] = 0
    res = repair_dropouts(sw)
    assert np.isnan(res.data[10:15]).all()
    assert res.gap_rows[10:15].all() and not res.repaired_rows.any()


def test_edge_bad_row_cannot_be_interpolated():
    sw = make()
    sw[0] = np.nan
    res = repair_dropouts(sw)
    assert res.gap_rows[0] and np.isnan(res.data[0]).all()


def test_good_data_untouched():
    sw = make()
    res = repair_dropouts(sw)
    np.testing.assert_array_equal(res.data, sw.astype(np.float32))
    assert not res.repaired_rows.any() and not res.gap_rows.any()
