"""Flip test-time augmentation for the tiled detector.

Training mirrors tiles across track (port/starboard) and along track, so the same flips at test
time give the model extra independent looks. Views are merged by weighted box fusion (WBF:
clusters of overlapping boxes are averaged; a box seen in only some views loses score) or NMS.
"""

from __future__ import annotations

import numpy as np

from netsight.detect.dfine import predict_image
from netsight.detect.tiling import nms

VIEWS = {
    "none": ((False, False),),
    "hflip": ((False, False), (True, False)),
    "hvflip": ((False, False), (True, False), (False, True), (True, True)),
}


def _iou(box: np.ndarray, boxes: np.ndarray) -> np.ndarray:
    lo = np.maximum(box[:2], boxes[:, :2])
    hi = np.minimum(box[2:], boxes[:, 2:])
    inter = np.prod(np.maximum(hi - lo, 0.0), axis=1)
    area = np.prod(np.maximum(box[2:] - box[:2], 0.0))
    areas = np.prod(np.maximum(boxes[:, 2:] - boxes[:, :2], 0.0), axis=1)
    union = area + areas - inter
    return np.divide(inter, union, out=np.zeros_like(inter), where=union > 0)


def weighted_box_fusion(
    view_boxes: list[np.ndarray], view_scores: list[np.ndarray], *, iou_threshold: float = 0.55
) -> tuple[np.ndarray, np.ndarray]:
    """Fuse detections from several views; score = sum of member scores / number of views.

    Each fused box takes at most one box per view (the highest-scoring unclaimed overlap).
    """
    n_views = len(view_boxes)
    boxes = np.concatenate([np.asarray(b, float).reshape(-1, 4) for b in view_boxes])
    scores = np.concatenate([np.asarray(s, float).reshape(-1) for s in view_scores])
    view = np.concatenate([np.full(len(s), v) for v, s in enumerate(view_scores)]).astype(int)
    order = np.argsort(-scores, kind="stable")
    boxes, scores, view = boxes[order], scores[order], view[order]
    free = np.ones(len(scores), bool)
    out_b, out_s = [], []
    for i in range(len(scores)):
        if not free[i]:
            continue
        cand = np.flatnonzero(free)
        overlap = _iou(boxes[i], boxes[cand])
        members = [i]
        used = {view[i]}
        for j in cand[np.argsort(-scores[cand], kind="stable")]:
            if j != i and view[j] not in used and overlap[np.searchsorted(cand, j)] > iou_threshold:
                members.append(j)
                used.add(view[j])
        free[members] = False
        w = scores[members]
        out_b.append((boxes[members] * w[:, None]).sum(0) / w.sum())
        out_s.append(w.sum() / n_views)
    if not out_b:
        return np.zeros((0, 4)), np.zeros(0)
    b, s = np.array(out_b), np.array(out_s)
    keep = np.argsort(-s, kind="stable")
    return b[keep], s[keep]


def predict_image_tta(
    model,
    processor,
    image: np.ndarray,
    *,
    tile_px: int,
    views: str = "hflip",
    merge: str = "wbf",
    max_detections: int = 100,
    device: str = "cuda",
    **kwargs,
) -> tuple[np.ndarray, np.ndarray]:
    h, w = image.shape[:2]
    all_b, all_s = [], []
    for flip_x, flip_y in VIEWS[views]:
        view = image[:, ::-1] if flip_x else image
        view = view[::-1, :] if flip_y else view
        b, s = predict_image(
            model,
            processor,
            np.ascontiguousarray(view),
            tile_px=tile_px,
            device=device,
            max_detections=max_detections,
            **kwargs,
        )
        b = np.asarray(b, float).reshape(-1, 4).copy()
        if flip_x:
            b[:, [0, 2]] = w - b[:, [2, 0]]
        if flip_y:
            b[:, [1, 3]] = h - b[:, [3, 1]]
        all_b.append(b)
        all_s.append(np.asarray(s, float).reshape(-1))
    if len(all_b) == 1:
        return all_b[0], all_s[0]
    if merge == "wbf":
        boxes, scores = weighted_box_fusion(all_b, all_s)
    elif merge == "nms":
        boxes, scores = np.concatenate(all_b), np.concatenate(all_s)
        keep = nms(boxes, scores, iou_threshold=0.5)
        boxes, scores = boxes[keep], scores[keep]
    else:
        raise ValueError(f"unknown merge {merge!r}")
    return boxes[:max_detections], np.clip(scores[:max_detections], 0.0, 1.0)
