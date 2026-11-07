"""Tests for tiling, coordinate transforms, and suppression."""

from dataclasses import FrozenInstanceError

import numpy as np
import pytest
from numpy.testing import assert_allclose, assert_array_equal

from netsight.detect.tiling import (
    Tile,
    boxes_for_tile,
    make_tiles,
    merge_detections,
    nms,
    scale_boxes,
    to_image_coords,
)


def test_make_tiles_shifted_last_window_and_coverage() -> None:
    tiles = make_tiles(1000, 640, tile_w=640, tile_h=640, overlap=0.25)
    assert tiles == [Tile(0, 0, 640, 640, 0), Tile(360, 0, 1000, 640, 1)]
    covered = np.zeros((640, 1000), dtype=bool)
    for tile in tiles:
        assert tile.x1 - tile.x0 == 640
        assert tile.y1 - tile.y0 == 640
        covered[tile.y0 : tile.y1, tile.x0 : tile.x1] = True
    assert covered.all()


def test_small_and_exact_fit_images() -> None:
    assert make_tiles(200, 300, tile_w=640, tile_h=640) == [Tile(0, 0, 200, 300, 0)]
    assert make_tiles(640, 640, tile_w=640, tile_h=640) == [Tile(0, 0, 640, 640, 0)]
    tiles = make_tiles(200, 1000, tile_w=640, tile_h=640)
    assert tiles == [Tile(0, 0, 200, 640, 0), Tile(0, 360, 200, 1000, 1)]


def test_zero_overlap_and_row_major_order() -> None:
    tiles = make_tiles(1280, 1280, tile_w=640, tile_h=640, overlap=0)
    assert tiles == [
        Tile(0, 0, 640, 640, 0),
        Tile(640, 0, 1280, 640, 1),
        Tile(0, 640, 640, 1280, 2),
        Tile(640, 640, 1280, 1280, 3),
    ]
    shifted = make_tiles(1500, 640, tile_w=640, tile_h=640, overlap=0)
    assert [tile.x0 for tile in shifted] == [0, 640, 860]


def test_no_duplicate_aligned_last_window() -> None:
    tiles = make_tiles(1600, 640, tile_w=640, tile_h=640)
    assert [tile.x0 for tile in tiles] == [0, 480, 960]
    assert len({(t.x0, t.y0, t.x1, t.y1) for t in tiles}) == len(tiles)


def test_stride_rounding_and_minimum() -> None:
    rounded = make_tiles(9, 1, tile_w=5, tile_h=1, overlap=0.5)
    assert [tile.x0 for tile in rounded] == [0, 2, 4]
    tiny_stride = make_tiles(4, 1, tile_w=2, tile_h=1, overlap=0.99)
    assert [tile.x0 for tile in tiny_stride] == [0, 1, 2]


def test_tile_is_frozen() -> None:
    tile = Tile(0, 0, 10, 10, 0)
    with pytest.raises(FrozenInstanceError):
        tile.x0 = 1


@pytest.mark.parametrize(
    ("width", "height", "tile_w", "tile_h", "overlap"),
    [
        (0, 640, 640, 640, 0.25),
        (640, -1, 640, 640, 0.25),
        (640, 640, 0, 640, 0.25),
        (640, 640, 640, -1, 0.25),
        (640, 640, 640, 640, -0.1),
        (640, 640, 640, 640, 1.0),
        (640, 640, 640, 640, float("nan")),
    ],
)
def test_make_tiles_invalid(
    width: int, height: int, tile_w: int, tile_h: int, overlap: float
) -> None:
    with pytest.raises(ValueError):
        make_tiles(width, height, tile_w=tile_w, tile_h=tile_h, overlap=overlap)


def test_boxes_for_tile_visibility_size_and_labels() -> None:
    tile = Tile(100, 100, 200, 200, 0)
    boxes = np.array(
        [
            [110, 120, 130, 150],  # Fully inside.
            [90, 120, 110, 140],  # Half visible.
            [99, 150, 101, 170],  # Visible side is only one pixel.
            [0, 0, 10, 10],  # No intersection.
        ],
        dtype=float,
    )
    labels = np.array([7, 8, 9, 10], dtype=np.int64)
    local, kept_labels = boxes_for_tile(boxes, labels, tile)
    assert_allclose(local, [[10, 20, 30, 50], [0, 20, 10, 40]])
    assert_array_equal(kept_labels, [7, 8])
    stricter, stricter_labels = boxes_for_tile(boxes, labels, tile, min_visible=0.6)
    assert_allclose(stricter, [[10, 20, 30, 50]])
    assert_array_equal(stricter_labels, [7])
    assert_allclose(
        to_image_coords(local, tile),
        [[110, 120, 130, 150], [100, 120, 110, 140]],
    )
    assert_allclose(boxes[1], [90, 120, 110, 140])


def test_empty_boxes() -> None:
    boxes = np.empty((0, 4), dtype=float)
    labels = np.empty(0, dtype=np.int64)
    tile = Tile(100, 200, 300, 400, 0)
    local, kept_labels = boxes_for_tile(boxes, labels, tile)
    assert local.shape == (0, 4)
    assert local.dtype.kind == "f"
    assert kept_labels.shape == (0,)
    assert kept_labels.dtype.kind == "i"
    assert to_image_coords(local, tile).shape == (0, 4)
    assert nms(boxes, np.empty(0)).shape == (0,)
    assert nms(boxes, np.empty(0)).dtype.kind == "i"


@pytest.mark.parametrize("min_visible", [-0.1, 1.1, float("nan")])
def test_invalid_visibility(min_visible: float) -> None:
    with pytest.raises(ValueError):
        boxes_for_tile(
            np.empty((0, 4)),
            np.empty(0, dtype=np.int64),
            Tile(0, 0, 10, 10, 0),
            min_visible=min_visible,
        )


@pytest.mark.parametrize("min_size_px", [-1.0, float("nan"), float("inf")])
def test_invalid_minimum_size(min_size_px: float) -> None:
    with pytest.raises(ValueError):
        boxes_for_tile(
            np.empty((0, 4)),
            np.empty(0, dtype=np.int64),
            Tile(0, 0, 10, 10, 0),
            min_size_px=min_size_px,
        )


def test_nms_high_and_low_iou() -> None:
    # Equal-height boxes have IoU 8/10 and 6/20, respectively.
    high = np.array([[0, 0, 9, 10], [1, 0, 10, 10]], dtype=float)
    low = np.array([[0, 0, 13, 10], [7, 0, 20, 10]], dtype=float)
    scores = np.array([0.6, 0.9])
    assert_array_equal(nms(high, scores), [1])
    assert_array_equal(nms(low, scores), [1, 0])


def test_nms_ios_containment() -> None:
    boxes = np.array([[0, 0, 100, 100], [10, 10, 20, 20]], dtype=float)
    scores = np.array([0.9, 0.8])
    assert_array_equal(nms(boxes, scores, metric="iou"), [0, 1])
    assert_array_equal(nms(boxes, scores, metric="ios"), [0])


def test_nms_stable_ties_and_threshold_boundary() -> None:
    boxes = np.array([[0, 0, 3, 2], [1, 0, 4, 2]], dtype=float)
    scores = np.array([0.8, 0.8])
    assert_array_equal(nms(boxes, scores, iou_threshold=0.5), [0, 1])
    assert_array_equal(nms(boxes, scores, iou_threshold=0.49), [0])


def test_merge_overlapping_tiles_and_full_image() -> None:
    tiles = make_tiles(1000, 640, tile_w=640, tile_h=640)
    per_tile = [
        (
            tiles[0],
            np.array([[400, 100, 500, 200]], dtype=float),
            np.array([0.8]),
            np.array([2], dtype=np.int64),
        ),
        (
            tiles[1],
            np.array([[40, 100, 140, 200]], dtype=float),
            np.array([0.9]),
            np.array([2], dtype=np.int64),
        ),
    ]
    boxes, scores, labels = merge_detections(per_tile)
    assert_allclose(boxes, [[400, 100, 500, 200]])
    assert_allclose(scores, [0.9])
    assert_array_equal(labels, [2])

    full_image = (
        np.array([[400, 100, 500, 200], [50, 50, 950, 600]], dtype=float),
        np.array([0.95, 0.7]),
        np.array([2, 3], dtype=np.int64),
    )
    boxes, scores, labels = merge_detections(per_tile, full_image=full_image)
    assert_allclose(boxes, [[400, 100, 500, 200], [50, 50, 950, 600]])
    assert_allclose(scores, [0.95, 0.7])
    assert_array_equal(labels, [2, 3])


def test_merge_class_aware_and_agnostic() -> None:
    per_tile = [
        (
            Tile(100, 200, 740, 840, 0),
            np.array([[0, 0, 20, 20], [0, 0, 20, 20]], dtype=float),
            np.array([0.7, 0.9]),
            np.array([1, 2], dtype=np.int64),
        )
    ]
    boxes, scores, labels = merge_detections(per_tile)
    assert_allclose(boxes, [[100, 200, 120, 220], [100, 200, 120, 220]])
    assert_allclose(scores, [0.9, 0.7])
    assert_array_equal(labels, [2, 1])
    boxes, scores, labels = merge_detections(per_tile, class_agnostic=True)
    assert_allclose(boxes, [[100, 200, 120, 220]])
    assert_allclose(scores, [0.9])
    assert_array_equal(labels, [2])


def test_merge_ios_and_full_image_only() -> None:
    full_image = (
        np.array([[0, 0, 100, 100], [10, 10, 20, 20]], dtype=float),
        np.array([0.9, 0.8]),
        np.array([1, 1], dtype=np.int64),
    )
    assert len(merge_detections([], full_image=full_image)[0]) == 2
    boxes, scores, labels = merge_detections([], full_image=full_image, metric="ios")
    assert_allclose(boxes, [[0, 0, 100, 100]])
    assert_allclose(scores, [0.9])
    assert_array_equal(labels, [1])


def test_merge_empty() -> None:
    empty = (
        np.empty((0, 4)),
        np.empty(0),
        np.empty(0, dtype=np.int64),
    )
    for result in (
        merge_detections([]),
        merge_detections([], full_image=empty),
        merge_detections([(Tile(0, 0, 10, 10, 0), *empty)]),
    ):
        boxes, scores, labels = result
        assert boxes.shape == (0, 4)
        assert scores.shape == (0,)
        assert labels.shape == (0,)
        assert boxes.dtype.kind == scores.dtype.kind == "f"
        assert labels.dtype.kind == "i"


def test_scale_boxes() -> None:
    boxes = np.array([[1, 2, 3, 4]], dtype=float)
    assert_allclose(scale_boxes(boxes, 2.0, 3.0), [[2, 6, 6, 12]])
    assert_allclose(boxes, [[1, 2, 3, 4]])
    assert scale_boxes(np.empty((0, 4)), 2.0, 3.0).shape == (0, 4)


@pytest.mark.parametrize("threshold", [-0.1, 1.1, float("nan")])
def test_invalid_nms_threshold(threshold: float) -> None:
    with pytest.raises(ValueError):
        nms(np.empty((0, 4)), np.empty(0), iou_threshold=threshold)
    with pytest.raises(ValueError):
        merge_detections([], iou_threshold=threshold)


def test_unknown_metric() -> None:
    with pytest.raises(ValueError, match="metric"):
        nms(np.empty((0, 4)), np.empty(0), metric="unknown")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="metric"):
        merge_detections([], metric="unknown")  # type: ignore[arg-type]


def test_mismatched_lengths_and_shapes() -> None:
    boxes = np.array([[0, 0, 10, 10]], dtype=float)
    tile = Tile(0, 0, 20, 20, 0)
    labels = np.array([1], dtype=np.int64)
    scores = np.array([0.9])

    with pytest.raises(ValueError, match="scores"):
        nms(boxes, np.empty(0))
    with pytest.raises(ValueError, match="scores"):
        nms(boxes, scores.reshape(1, 1))
    with pytest.raises(ValueError, match="labels"):
        boxes_for_tile(boxes, np.empty(0, dtype=np.int64), tile)
    with pytest.raises(ValueError, match="labels"):
        boxes_for_tile(boxes, labels.reshape(1, 1), tile)
    with pytest.raises(ValueError, match="scores"):
        merge_detections([(tile, boxes, np.empty(0), labels)])
    with pytest.raises(ValueError, match="labels"):
        merge_detections([], full_image=(boxes, scores, np.empty(0, dtype=np.int64)))
    with pytest.raises(ValueError, match="boxes"):
        to_image_coords(np.empty((0, 3)), tile)
    with pytest.raises(ValueError, match="boxes"):
        scale_boxes(np.empty(4), 1.0, 1.0)
