import numpy as np

from netsight.detect.dfine import rescale


def _tile():
    crop = np.full((100, 100), 50.0)
    crop[40:60, 40:60] = 200.0
    return crop, np.array([[40.0, 40.0, 60.0, 60.0]])


def _box_of_bright(img):
    ys, xs = np.nonzero(img > 125)
    return np.array([xs.min(), ys.min(), xs.max() + 1, ys.max() + 1], float)


def test_zoom_out_keeps_size_and_moves_box_with_object():
    crop, boxes = _tile()
    out, b = rescale(crop, boxes, 0.5, np.random.default_rng(0))
    assert out.shape == (100, 100)
    assert np.allclose(b[0][2:] - b[0][:2], [10, 10])
    assert np.allclose(b[0], _box_of_bright(out), atol=1.5)
    assert np.median(out) == 50.0  # padding is the tile median, not mirrored content


def test_zoom_in_keeps_size_and_box_follows_object():
    crop, boxes = _tile()
    for seed in range(5):
        out, b = rescale(crop, boxes, 1.5, np.random.default_rng(seed))
        assert out.shape == (100, 100)
        if len(b):
            assert np.allclose(b[0], _box_of_bright(out), atol=1.5)


def test_zoom_in_that_would_cut_an_object_returns_tile_unchanged():
    crop = np.full((100, 100), 50.0)
    crop[0:30, 0:30] = 200.0
    boxes = np.array([[0.0, 0.0, 30.0, 30.0]])
    cut = 0
    for seed in range(20):
        out, b = rescale(crop, boxes, 1.8, np.random.default_rng(seed))
        if out is crop:
            cut += 1
            assert b is boxes
        else:
            assert all((b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1]) >= 0.5 * 54 * 54 - 1)
    assert cut > 0


def test_empty_boxes():
    out, b = rescale(np.zeros((64, 64)), np.zeros((0, 4)), 1.3, np.random.default_rng(1))
    assert out.shape == (64, 64) and b.shape == (0, 4)
