import numpy as np
import pytest

from netsight.datasets.relabel import corrected, drop_ignored, evaluate


def _rec():
    return {
        "candidates": [[0, 0, 10, 10], [20, 20, 30, 30], [40, 40, 50, 50], [60, 60, 70, 70]],
        "source": ["label", "label", "model", "model"],
        "answer": {
            "candidates": [
                {"id": 1, "verdict": "object"},
                {"id": 2, "verdict": "not_object"},
                {"id": 3, "verdict": "object"},
                {"id": 4, "verdict": "unsure"},
            ],
            "missed": [{"object_box": [80, 80, 90, 90]}],
        },
    }


def test_rules():
    gt, ig, c = corrected(_rec(), np.array([[0, 0, 10, 10], [20, 20, 30, 30]], float))
    assert gt.tolist() == [[0, 0, 10, 10], [40, 40, 50, 50], [80, 80, 90, 90]]
    assert ig.tolist() == [[20, 20, 30, 30], [60, 60, 70, 70]]
    assert c == {"kept": 1, "added": 1, "missed_added": 1, "ignored_label": 1, "ignored_unsure": 1}


def test_ignore_region_removes_detection_only_without_gt():
    gt = np.array([[0, 0, 10, 10]], float)
    ig = np.array([[20, 20, 30, 30]], float)
    b = np.array([[0, 0, 10, 10], [20, 20, 30, 30], [50, 50, 60, 60]], float)
    kb, ks = drop_ignored(b, np.array([0.9, 0.8, 0.7]), gt, ig)
    assert kb.tolist() == [[0, 0, 10, 10], [50, 50, 60, 60]]
    assert ks.tolist() == [0.9, 0.7]


def test_evaluate_ignore_raises_ap_when_false_alarm_is_ignored():
    gt = [np.array([[0, 0, 10, 10]], float)]
    preds = [(np.array([[20, 20, 30, 30], [0, 0, 10, 10]], float), np.array([0.9, 0.5]))]
    assert evaluate(preds, gt) == pytest.approx(0.5)
    assert evaluate(preds, gt, [np.array([[20, 20, 30, 30]], float)]) == pytest.approx(1.0)
