"""Choose training tiles from labelled images (no deep-learning dependencies).

Rules (docs/research/step2/tiling_and_resolution.md):
- a box is kept in a tile if at least `min_visible` of it is inside, or if its visible part is
  still at least `min_keep_px` on both sides (large objects cut by the tile edge);
- a tile that cuts an object without keeping it is left out entirely, so the detector never
  learns that part of an object is background;
- empty tiles are sampled as negatives at `neg_ratio` per positive tile.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from netsight.datasets.detection import DetectionSample
from netsight.detect.tiling import Tile, make_tiles

EMPTY = np.zeros((0, 4), dtype=float)


@dataclass(frozen=True)
class TrainTile:
    sample_index: int
    tile: Tile
    boxes: np.ndarray  # (n, 4) in tile coordinates


def keep_boxes(
    boxes: np.ndarray,
    tile: Tile,
    *,
    min_visible: float = 0.5,
    min_keep_px: float = 32.0,
    min_size_px: float = 2.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(kept boxes in tile coordinates, kept indices, indices of objects cut but not kept)."""
    boxes = np.asarray(boxes, dtype=float).reshape(-1, 4)
    if not len(boxes):
        return EMPTY.copy(), np.zeros(0, int), np.zeros(0, int)
    clipped = boxes.copy()
    clipped[:, [0, 2]] = np.clip(clipped[:, [0, 2]], tile.x0, tile.x1)
    clipped[:, [1, 3]] = np.clip(clipped[:, [1, 3]], tile.y0, tile.y1)
    sides = np.maximum(clipped[:, 2:] - clipped[:, :2], 0.0)
    area = sides.prod(axis=1)
    full = np.maximum(boxes[:, 2:] - boxes[:, :2], 0.0).prod(axis=1)
    visible = np.divide(area, full, out=np.zeros_like(area), where=full > 0)
    intersects = area > 0
    big_enough = np.all(sides >= min_keep_px, axis=1)
    kept = intersects & ((visible >= min_visible) | big_enough) & np.all(
        sides >= min_size_px, axis=1
    )
    offset = np.array([tile.x0, tile.y0, tile.x0, tile.y0], dtype=float)
    return clipped[kept] - offset, np.flatnonzero(kept), np.flatnonzero(intersects & ~kept)


def _pick(items: list[TrainTile], n: int, rng: np.random.Generator) -> list[TrainTile]:
    if n >= len(items):
        return list(items)
    idx = np.sort(rng.choice(len(items), size=n, replace=False))
    return [items[i] for i in idx]


def build_train_tiles(
    samples: Sequence[DetectionSample],
    tile_px: int,
    *,
    overlap: float = 0.25,
    neg_ratio: float = 1.0,
    max_tiles: int | None = None,
    min_negatives: int = 0,
    rng: np.random.Generator,
) -> list[TrainTile]:
    if tile_px < 1:
        raise ValueError("tile_px must be >= 1")
    if neg_ratio < 0 or min_negatives < 0:
        raise ValueError("neg_ratio and min_negatives must be >= 0")
    positives: list[TrainTile] = []
    negatives: list[TrainTile] = []
    for i, s in enumerate(samples):
        for tile in make_tiles(s.width, s.height, tile_w=tile_px, tile_h=tile_px, overlap=overlap):
            local, kept, cut = keep_boxes(s.boxes, tile)
            if cut.size:
                continue  # would teach "object part = background"
            (positives if kept.size else negatives).append(TrainTile(i, tile, local))
    n_neg = min(len(negatives), max(round(neg_ratio * len(positives)), min_negatives))
    if max_tiles is not None and len(positives) + n_neg > max_tiles:
        total = len(positives) + n_neg
        n_pos = round(max_tiles * len(positives) / total)
        positives = _pick(positives, n_pos, rng)
        n_neg = max_tiles - n_pos
    chosen = positives + _pick(negatives, n_neg, rng)
    return sorted(chosen, key=lambda t: (t.sample_index, t.tile.y0, t.tile.x0))
