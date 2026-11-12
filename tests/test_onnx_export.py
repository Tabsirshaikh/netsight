"""Deterministic numerical and offline orchestration tests for ONNX inference."""

from __future__ import annotations

import numpy as np
import pytest

from netsight.detect.onnx_export import (
    _clip_boxes,
    benchmark,
    postprocess,
    predict_image_onnx,
)


def test_postprocess_hand_case() -> None:
    logits = np.array([[[2.0], [-2.0], [0.0]]])
    boxes = np.array([[[0.5, 0.5, 0.4, 0.2], [0.25, 0.25, 0.2, 0.1], [0.8, 0.6, 0.2, 0.4]]])
    result_boxes, scores = postprocess(logits, boxes, [(100, 200)], threshold=0)[0]
    # Sigmoid(2), sigmoid(0), sigmoid(-2), in descending order.
    np.testing.assert_allclose(scores, [0.8807970779778823, 0.5, 0.11920292202211755])
    np.testing.assert_allclose(
        result_boxes, [[60, 40, 140, 60], [140, 40, 180, 80], [30, 20, 70, 30]]
    )
    selected, selected_scores = postprocess(logits, boxes, [(100, 200)], 0.5)[0]
    np.testing.assert_allclose(selected, result_boxes[:2])
    np.testing.assert_allclose(selected_scores, scores[:2])
    selected, selected_scores = postprocess(logits, boxes, [(100, 200)], 0, top_k=1)[0]
    np.testing.assert_allclose(selected, [[60, 40, 140, 60]])
    np.testing.assert_allclose(selected_scores, [0.8807970779778823])


def test_multiclass_query_mapping_and_stable_sigmoid() -> None:
    logits = np.array([[[-1000, 1000], [0, -1000]]], dtype=float)
    boxes = np.array([[[0.5, 0.5, 1, 1], [0.25, 0.25, 0.5, 0.5]]])
    with np.errstate(over="raise"):
        actual, scores = postprocess(logits, boxes, [(10, 20)], 0.5)[0]
    np.testing.assert_allclose(actual, [[0, 0, 20, 10], [0, 0, 10, 5]])
    np.testing.assert_allclose(scores, [1, 0.5])


def test_clip_boxes_hand_case() -> None:
    boxes = np.array([[-2, -3, 12, 15], [1, 1, 1.5, 3], [3, 2, 4, 3]], dtype=float)
    actual, scores, labels = _clip_boxes(boxes, np.array([0.9, 0.8, 0.7]), 10, 8)
    np.testing.assert_array_equal(actual, [[0, 0, 8, 10], [3, 2, 4, 3]])
    np.testing.assert_array_equal(scores, [0.9, 0.7])
    np.testing.assert_array_equal(labels, [0, 0])


@pytest.mark.parametrize(
    ("logits", "boxes", "sizes", "threshold", "top_k"),
    [
        (np.zeros((1, 3)), np.zeros((1, 3, 4)), [(10, 20)], 0.5, 300),
        (np.zeros((1, 3, 1)), np.zeros((1, 2, 4)), [(10, 20)], 0.5, 300),
        (np.zeros((1, 3, 1)), np.zeros((1, 3, 4)), [(0, 20)], 0.5, 300),
        (np.zeros((1, 3, 1)), np.zeros((1, 3, 4)), [(10, 20)], 1.1, 300),
        (np.zeros((1, 3, 1)), np.zeros((1, 3, 4)), [(10, 20)], 0.5, 0),
    ],
)
def test_postprocess_invalid_input(logits, boxes, sizes, threshold, top_k) -> None:
    with pytest.raises(ValueError):
        postprocess(logits, boxes, sizes, threshold, top_k)


def test_predict_image_fake_detector() -> None:
    torch = pytest.importorskip("torch")
    pytest.importorskip("transformers")
    pytest.importorskip("netsight.detect.dfine")

    class FakeDetector:
        calls = 0

        def __call__(self, pixels: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
            assert pixels.dtype == np.float32
            assert pixels.shape[1:] == (3, 640, 640)
            self.calls += 1
            n = len(pixels)
            # This box covers its complete crop after clipping.
            return (
                np.full((n, 1, 1), 2, dtype=np.float32),
                np.tile(np.array([[[0.5, 0.5, 2, 2]]], dtype=np.float32), (n, 1, 1)),
            )

    detector = FakeDetector()
    # Avoid excessive CPU thread scheduling overhead on small test inputs.
    previous_threads = torch.get_num_threads()
    try:
        torch.set_num_threads(1)
        boxes, scores = predict_image_onnx(
            detector, np.full((700, 1000), 127, dtype=np.uint8), batch_size=4
        )
    finally:
        torch.set_num_threads(previous_threads)
    assert detector.calls >= 1
    assert len(boxes) > 0
    assert boxes.shape == (len(scores), 4)
    assert np.all(boxes[:, [0, 2]] >= 0)
    assert np.all(boxes[:, [0, 2]] <= 1000)
    assert np.all(boxes[:, [1, 3]] >= 0)
    assert np.all(boxes[:, [1, 3]] <= 700)
    np.testing.assert_allclose(scores, 0.8807970779778823)


def test_benchmark_accounting(monkeypatch: pytest.MonkeyPatch) -> None:
    import netsight.detect.onnx_export as module

    calls = []
    monkeypatch.setattr(module, "predict_image_onnx", lambda *a, **kw: calls.append(kw))
    times = iter([10.0, 12.0])
    monkeypatch.setattr(module.time, "perf_counter", lambda: next(times))

    class Detector:
        threads = 2

    result = benchmark(
        Detector(),
        [np.empty((100, 200), dtype=np.uint8), np.empty((200, 200), dtype=np.uint8)],
        repeats=2,
    )
    # Four image passes, 120000 pixels, and exactly two seconds.
    assert result == {
        "images": 4,
        "seconds_total": 2.0,
        "seconds_per_image": 0.5,
        "megapixels_per_second": 0.06,
        "threads": 2,
    }
    assert len(calls) == 4
