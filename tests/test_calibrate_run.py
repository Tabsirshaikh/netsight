import numpy as np

from netsight.detect.calibrate_run import load_predictions, save_predictions


def test_prediction_round_trip_keeps_empty_images(tmp_path):
    preds = [
        (np.array([[0, 0, 10, 10], [5, 5, 9, 9]]), np.array([0.9, 0.2])),
        (np.zeros((0, 4)), np.zeros(0)),
        (np.array([[1, 1, 3, 3]]), np.array([0.5])),
    ]
    gts = [np.array([[0, 0, 10, 10]]), np.zeros((0, 4)), np.zeros((0, 4))]
    save_predictions(tmp_path / "s.npz", preds, gts)
    got_preds, got_gts = load_predictions(tmp_path / "s.npz")
    assert len(got_preds) == 3 and len(got_gts) == 3
    for (b, s), (gb, gs) in zip(preds, got_preds, strict=True):
        assert np.array_equal(b, gb) and np.array_equal(s, gs)
    for g, gg in zip(gts, got_gts, strict=True):
        assert np.array_equal(g, gg)
