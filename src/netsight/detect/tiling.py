"""Tile sonar images and merge detections in original-image coordinates."""

from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
Metric = Literal["iou", "ios"]
Detections = tuple[FloatArray, FloatArray, IntArray]
TileDetections = tuple["Tile", FloatArray, FloatArray, IntArray]


@dataclass(frozen=True)
class Tile:
    """An exclusive-ended pixel window in the original image."""

    x0: int
    y0: int
    x1: int
    y1: int
    index: int


def _axis_starts(length: int, tile_size: int, overlap: float) -> list[int]:
    """Return unique starts, anchoring the final window at the edge."""
    if length <= tile_size:
        return [0]
    stride = max(1, round(tile_size * (1.0 - overlap)))
    last = length - tile_size
    starts = list(range(0, last + 1, stride))
    if starts[-1] != last:
        starts.append(last)
    return starts


def make_tiles(
    width: int,
    height: int,
    *,
    tile_w: int,
    tile_h: int,
    overlap: float = 0.25,
) -> list[Tile]:
    """Build row-major windows without padding or duplicate windows."""
    if width < 1 or height < 1:
        raise ValueError("Image dimensions must be positive.")
    if tile_w < 1 or tile_h < 1:
        raise ValueError("Tile dimensions must be positive.")
    if not 0.0 <= overlap < 1.0:
        raise ValueError("overlap must be in [0, 1).")

    xs = _axis_starts(width, tile_w, overlap)
    ys = _axis_starts(height, tile_h, overlap)
    return [
        Tile(x, y, min(x + tile_w, width), min(y + tile_h, height), index)
        for index, (x, y) in enumerate((x, y) for y in ys for x in xs)
    ]


def _as_boxes(boxes: FloatArray) -> FloatArray:
    """Normalize boxes and validate their shape."""
    result = np.asarray(boxes, dtype=np.float64)
    if result.ndim != 2 or result.shape[1] != 4:
        raise ValueError("boxes must have shape (n, 4).")
    return result


def _as_labels(labels: IntArray, count: int) -> IntArray:
    """Normalize labels and validate their length."""
    result = np.asarray(labels, dtype=np.int64)
    if result.ndim != 1 or len(result) != count:
        raise ValueError("labels must have shape (n,) matching boxes.")
    return result


def _as_scores(scores: FloatArray, count: int) -> FloatArray:
    """Normalize scores and validate their length."""
    result = np.asarray(scores, dtype=np.float64)
    if result.ndim != 1 or len(result) != count:
        raise ValueError("scores must have shape (n,) matching boxes.")
    return result


def _validate_nms(iou_threshold: float, metric: str) -> None:
    """Validate shared suppression options, including for empty inputs."""
    if metric not in ("iou", "ios"):
        raise ValueError("metric must be 'iou' or 'ios'.")
    if not 0.0 <= iou_threshold <= 1.0:
        raise ValueError("iou_threshold must be in [0, 1].")


def boxes_for_tile(
    boxes: FloatArray,
    labels: IntArray,
    tile: Tile,
    *,
    min_visible: float = 0.5,
    min_size_px: float = 2.0,
) -> tuple[FloatArray, IntArray]:
    """Clip original-image boxes and return retained tile-local boxes."""
    if not 0.0 <= min_visible <= 1.0:
        raise ValueError("min_visible must be in [0, 1].")
    if not np.isfinite(min_size_px) or min_size_px < 0.0:
        raise ValueError("min_size_px must be finite and nonnegative.")

    boxes = _as_boxes(boxes)
    labels = _as_labels(labels, len(boxes))
    clipped = boxes.copy()
    clipped[:, [0, 2]] = np.clip(clipped[:, [0, 2]], tile.x0, tile.x1)
    clipped[:, [1, 3]] = np.clip(clipped[:, [1, 3]], tile.y0, tile.y1)

    original_sides = np.maximum(boxes[:, 2:] - boxes[:, :2], 0.0)
    original_area = np.prod(original_sides, axis=1)
    sides = np.maximum(clipped[:, 2:] - clipped[:, :2], 0.0)
    clipped_area = np.prod(sides, axis=1)
    visible = np.divide(
        clipped_area,
        original_area,
        out=np.zeros_like(clipped_area),
        where=original_area > 0.0,
    )
    keep = (clipped_area > 0.0) & (visible >= min_visible) & np.all(sides >= min_size_px, axis=1)
    local = clipped[keep] - np.array([tile.x0, tile.y0, tile.x0, tile.y0])
    return local, labels[keep]


def to_image_coords(boxes: FloatArray, tile: Tile) -> FloatArray:
    """Translate tile-local boxes to original-image coordinates."""
    boxes = _as_boxes(boxes)
    return boxes + np.array([tile.x0, tile.y0, tile.x0, tile.y0])


def nms(
    boxes: FloatArray,
    scores: FloatArray,
    *,
    iou_threshold: float = 0.5,
    metric: Metric = "iou",
) -> IntArray:
    """Greedily suppress overlaps above the threshold, with stable score ties."""
    _validate_nms(iou_threshold, metric)
    boxes = _as_boxes(boxes)
    scores = _as_scores(scores, len(boxes))

    areas = np.prod(np.maximum(boxes[:, 2:] - boxes[:, :2], 0.0), axis=1)
    order = np.argsort(-scores, kind="stable")
    kept: list[int] = []

    while order.size:
        current = int(order[0])
        kept.append(current)
        rest = order[1:]
        low = np.maximum(boxes[current, :2], boxes[rest, :2])
        high = np.minimum(boxes[current, 2:], boxes[rest, 2:])
        intersection = np.prod(np.maximum(high - low, 0.0), axis=1)
        if metric == "iou":
            denominator = areas[current] + areas[rest] - intersection
        else:
            denominator = np.minimum(areas[current], areas[rest])
        overlap = np.divide(
            intersection,
            denominator,
            out=np.zeros_like(intersection),
            where=denominator > 0.0,
        )
        order = rest[overlap <= iou_threshold]

    return np.asarray(kept, dtype=np.int64)


def merge_detections(
    per_tile: list[TileDetections],
    *,
    iou_threshold: float = 0.5,
    metric: Metric = "iou",
    class_agnostic: bool = False,
    full_image: Detections | None = None,
) -> Detections:
    """Map and merge detections; resized inputs must first be scaled back."""
    _validate_nms(iou_threshold, metric)
    groups: list[Detections] = []
    for tile, boxes, scores, labels in per_tile:
        mapped = to_image_coords(boxes, tile)
        groups.append((mapped, _as_scores(scores, len(mapped)), _as_labels(labels, len(mapped))))
    if full_image is not None:
        boxes, scores, labels = full_image
        boxes = _as_boxes(boxes)
        groups.append((boxes, _as_scores(scores, len(boxes)), _as_labels(labels, len(boxes))))

    if not groups:
        return (
            np.empty((0, 4), dtype=np.float64),
            np.empty(0, dtype=np.float64),
            np.empty(0, dtype=np.int64),
        )

    boxes = np.concatenate([group[0] for group in groups], axis=0)
    scores = np.concatenate([group[1] for group in groups])
    labels = np.concatenate([group[2] for group in groups])

    if class_agnostic:
        kept = nms(boxes, scores, iou_threshold=iou_threshold, metric=metric)
    else:
        class_kept: list[IntArray] = []
        for label in np.unique(labels):
            indices = np.flatnonzero(labels == label)
            selected = nms(
                boxes[indices],
                scores[indices],
                iou_threshold=iou_threshold,
                metric=metric,
            )
            class_kept.append(indices[selected])
        kept = np.sort(np.concatenate(class_kept)) if class_kept else np.empty(0, dtype=np.int64)
        kept = kept[np.argsort(-scores[kept], kind="stable")]

    return boxes[kept], scores[kept], labels[kept]


def scale_boxes(boxes: FloatArray, sx: float, sy: float) -> FloatArray:
    """Scale x and y coordinates without modifying the input."""
    boxes = _as_boxes(boxes)
    return boxes * np.array([sx, sy, sx, sy], dtype=np.float64)


FULL_IMAGE_MAX_ASPECT = 2.0


def full_image_pass_allowed(
    width: int, height: int, *, n_tiles: int, max_aspect: float = FULL_IMAGE_MAX_ASPECT
) -> bool:
    """Add a whole-image pass only when the image was tiled and resizing it to the square
    network input would not distort it badly (a 5000x500 waterfall would shrink 10:1)."""
    aspect = max(width, height) / max(1, min(width, height))
    return n_tiles > 1 and aspect <= max_aspect
