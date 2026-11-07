import numpy as np

import netsight.detect.tta as tta
from netsight.detect.tta import predict_image_tta, weighted_box_fusion


def test_wbf_averages_agreeing_views_and_halves_single_view_boxes():
    a = (np.array([[0, 0, 10, 10], [50, 50, 60, 60]]), np.array([0.8, 0.6]))
    b = (np.array([[2, 0, 12, 10]]), np.array([0.8]))
    boxes, scores = weighted_box_fusion([a[0], b[0]], [a[1], b[1]])
    assert np.allclose(boxes[0], [1, 0, 11, 10]) and np.isclose(scores[0], 0.8)
    assert np.allclose(boxes[1], [50, 50, 60, 60]) and np.isclose(scores[1], 0.3)


def test_wbf_takes_one_box_per_view():
    boxes, scores = weighted_box_fusion(
        [np.array([[0, 0, 10, 10], [0, 0, 10, 11]])], [np.array([0.9, 0.5])]
    )
    assert len(boxes) == 2  # a single view never fuses with itself


def test_wbf_empty():
    boxes, scores = weighted_box_fusion([np.zeros((0, 4))] * 2, [np.zeros(0)] * 2)
    assert boxes.shape == (0, 4) and scores.shape == (0,)


def test_flipped_views_are_mapped_back(monkeypatch):
    image = np.zeros((100, 200), np.uint8)
    image[10:20, 30:50] = 255  # one bright object

    def fake_predict(model, processor, view, **kw):
        ys, xs = np.nonzero(view)
        return np.array([[xs.min(), ys.min(), xs.max() + 1, ys.max() + 1]], float), np.array([0.9])

    monkeypatch.setattr(tta, "predict_image", fake_predict)
    boxes, scores = predict_image_tta(None, None, image, tile_px=640, views="hvflip")
    assert len(boxes) == 1
    assert np.allclose(boxes[0], [30, 10, 50, 20]) and np.isclose(scores[0], 0.9)
