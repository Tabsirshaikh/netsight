import numpy as np
import pytest

torch = pytest.importorskip("torch")

from netsight.detect.dfine import _targets, sonar_augment  # noqa: E402


def test_targets_carry_class_label():
    t = _targets(np.array([[0, 0, 10, 10]], float), 100, 100, label=3)
    assert t["class_labels"].tolist() == [3]


def test_sonar_augment_keeps_shape_and_valid_boxes():
    rng = np.random.default_rng(0)
    crop = np.full((200, 160), 80, np.float32)
    crop[90:110, 70:90] = 220
    boxes = np.array([[70, 90, 90, 110]], float)
    for _ in range(200):
        out, b = sonar_augment(crop, boxes, rng)
        assert out.shape == crop.shape
        assert b.shape[1] == 4 and len(b) <= 1
        if len(b):
            assert (b[:, 2] > b[:, 0]).all() and (b[:, 3] > b[:, 1]).all()
            assert b[0, 0] == pytest.approx(70) and b[0, 2] == pytest.approx(90)  # x unchanged
            y0, y1 = int(round(b[0, 1])), int(round(b[0, 3]))
            assert out[y0 + 2 : y1 - 2, 72:88].mean() > out[:20].mean()  # object still under box
