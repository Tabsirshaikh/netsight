"""Corrected test labels (v2) from model-assisted review, and evaluation with ignore regions.

Rules (fixed before results were seen):
- original label confirmed "object": kept with its ORIGINAL box (keeps each dataset's box style);
- detector candidate confirmed "object": added, with the detector's box;
- reviewer-found missed object: added, with the reviewer's object box;
- "unsure" candidates and original labels judged "not_object": IGNORE regions - detections there
  count neither as hits nor as false alarms (PASCAL VOC "difficult" handling); nothing original
  is deleted on one model's word;
- a later reviewer (e.g. GPT re-check) overrides an earlier one for the images it reviewed.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from pathlib import Path

import numpy as np

from netsight.detect.error_breakdown import _iou


def load_reviews(paths: Iterable[Path]) -> dict[int, dict]:
    """index -> review record; later paths override earlier ones; first record wins within a
    path (parallel workers can overlap at their meeting point)."""
    out: dict[int, dict] = {}
    for path in paths:
        seen: dict[int, dict] = {}
        for f in sorted(Path(path).glob("review*.jsonl")):
            for line in f.open(encoding="utf-8"):
                r = json.loads(line)
                if "error" in r.get("answer", {}):
                    continue
                seen.setdefault(r["index"], r)
        out.update(seen)
    return out


def corrected(record: dict, original: np.ndarray) -> tuple[np.ndarray, np.ndarray, dict]:
    """(gt boxes, ignore boxes, counts) for one reviewed image."""
    cand = np.asarray(record["candidates"], float).reshape(-1, 4)
    verdicts = {c.get("id"): c for c in record["answer"].get("candidates", [])}
    gt, ignore = [], []
    counts = {"kept": 0, "added": 0, "missed_added": 0, "ignored_label": 0, "ignored_unsure": 0}
    for k, src in enumerate(record["source"], 1):
        v = verdicts.get(k, {}).get("verdict", "unsure")
        box = cand[k - 1]
        if src == "label":
            if v == "object":
                gt.append(box)
                counts["kept"] += 1
            else:
                ignore.append(box)
                counts["ignored_label"] += 1
        elif v == "object":
            gt.append(box)
            counts["added"] += 1
        elif v == "unsure":
            ignore.append(box)
            counts["ignored_unsure"] += 1
    for m in record["answer"].get("missed", []) or []:
        b = m.get("object_box")
        if b and len(b) == 4 and b[2] > b[0] and b[3] > b[1]:
            gt.append(np.asarray(b, float))
            counts["missed_added"] += 1
    # Original labels beyond the candidate cap (max 24) are kept unchanged.
    orig = np.asarray(original, float).reshape(-1, 4)
    n_lab = sum(1 for s in record["source"] if s == "label")
    for b in orig[n_lab:]:
        gt.append(b)
        counts["kept"] += 1
    as_arr = lambda x: np.asarray(x, float).reshape(-1, 4)  # noqa: E731
    return as_arr(gt), as_arr(ignore), counts


def drop_ignored(
    boxes: np.ndarray, scores: np.ndarray, gt: np.ndarray, ignore: np.ndarray, iou: float = 0.3
) -> tuple[np.ndarray, np.ndarray]:
    """Remove detections that overlap an ignore region and no ground-truth box."""
    boxes = np.asarray(boxes, float).reshape(-1, 4)
    scores = np.asarray(scores, float).reshape(-1)
    if not len(ignore) or not len(boxes):
        return boxes, scores
    hit_ignore = _iou(boxes, ignore).max(1) >= iou
    hit_gt = _iou(boxes, gt).max(1) >= iou if len(gt) else np.zeros(len(boxes), bool)
    keep = ~hit_ignore | hit_gt
    return boxes[keep], scores[keep]


def evaluate(
    preds: Sequence[tuple[np.ndarray, np.ndarray]],
    gts: Sequence[np.ndarray],
    ignores: Sequence[np.ndarray] | None = None,
    iou: float = 0.5,
) -> float:
    """AP with ignore regions."""
    from netsight.detect.evaluation import average_precision, match_detections

    if ignores is not None:
        preds = [
            drop_ignored(b, s, g, ig) for (b, s), g, ig in zip(preds, gts, ignores, strict=True)
        ]
    return average_precision(match_detections(list(preds), list(gts), iou_threshold=iou))
