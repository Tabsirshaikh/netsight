"""Where does the detector lose objects on held-out surveys? (CPU, from a prediction dump)

For every ground-truth object, at the survey-level operating threshold (label-free count rule,
1 false alarm per image) the object is exactly one of:
- hit: a flagged detection with IoU >= 0.5;
- box_mismatch: a flagged detection overlaps (IoU 0.1-0.5) but its box differs (convention or
  localisation: better boxes or consistent labels would fix it);
- low_score: the detector proposed it (IoU >= 0.3, any score) but below the threshold
  (ranking/confidence: better scores or calibration per survey would fix it);
- never_proposed: no proposal with IoU >= 0.1 at any score (the model does not see it: needs
  more/varied training data, resolution or a different model).
Flagged false alarms are split into duplicate (overlaps an already-hit object), near_object
(IoU 0.1-0.5 with an object) and background.

    python -m netsight.detect.error_breakdown --dump runs/calib_v0.4
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np

CATS = ("hit", "box_mismatch", "low_score", "never_proposed")


def _iou(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    if not len(a) or not len(b):
        return np.zeros((len(a), len(b)))
    ix = np.clip(
        np.minimum(a[:, None, 2], b[None, :, 2]) - np.maximum(a[:, None, 0], b[None, :, 0]), 0, None
    )
    iy = np.clip(
        np.minimum(a[:, None, 3], b[None, :, 3]) - np.maximum(a[:, None, 1], b[None, :, 1]), 0, None
    )
    inter = ix * iy
    area_a = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1])
    area_b = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    return inter / np.maximum(area_a[:, None] + area_b[None, :] - inter, 1e-9)


def breakdown(preds, gts, groups, budget: float = 1.0) -> dict:
    from netsight.detect.operating_run import count_threshold

    thr = {}
    for g in sorted(set(groups)):
        idx = [i for i, x in enumerate(groups) if x == g]
        thr[g] = count_threshold(np.concatenate([preds[i][1] for i in idx]), len(idx), budget)
    gt_cat: Counter = Counter()
    by_size: dict[str, Counter] = {}
    fp_cat: Counter = Counter()
    sizes = np.concatenate(
        [
            np.sqrt(
                np.prod(
                    np.diff(np.asarray(g, float).reshape(-1, 2, 2), axis=1).reshape(-1, 2), axis=1
                )
            )
            for g in gts
            if len(g)
        ]
        or [np.zeros(0)]
    )
    edges = np.quantile(sizes, [1 / 3, 2 / 3]) if sizes.size else np.array([0, 0])
    for (boxes, scores), gt, g in zip(preds, gts, groups, strict=True):
        boxes = np.asarray(boxes, float).reshape(-1, 4)
        scores = np.asarray(scores, float).reshape(-1)
        gt = np.asarray(gt, float).reshape(-1, 4)
        flagged = scores >= thr[g]
        m = _iou(gt, boxes)
        hit_by = set()
        for j in range(len(gt)):
            side = float(np.sqrt((gt[j, 2] - gt[j, 0]) * (gt[j, 3] - gt[j, 1])))
            size = "small" if side < edges[0] else "medium" if side < edges[1] else "large"
            row = m[j] if len(boxes) else np.zeros(0)
            fl = row[flagged] if len(row) else row
            if fl.size and fl.max() >= 0.5:
                c = "hit"
                hit_by.add(int(np.flatnonzero(flagged)[np.argmax(fl)]))
            elif fl.size and fl.max() >= 0.1:
                c = "box_mismatch"
            elif row.size and row.max() >= 0.3:
                c = "low_score"
            else:
                c = "never_proposed"
            gt_cat[c] += 1
            by_size.setdefault(size, Counter())[c] += 1
        for k in np.flatnonzero(flagged):
            best = m[:, k].max() if len(gt) else 0.0
            if best >= 0.5 and k not in hit_by:
                fp_cat["duplicate"] += 1
            elif best >= 0.5:
                continue
            elif best >= 0.1:
                fp_cat["near_object"] += 1
            else:
                fp_cat["background"] += 1
    n = sum(gt_cat.values())
    return {
        "objects": n,
        "share": {c: round(gt_cat[c] / n, 3) if n else None for c in CATS},
        "by_size": {
            s: {c: round(v[c] / max(sum(v.values()), 1), 3) for c in CATS} | {"n": sum(v.values())}
            for s, v in sorted(by_size.items())
        },
        "size_edges_px": [round(float(e), 1) for e in edges],
        "false_alarms": dict(fp_cat),
    }


def main(argv: list[str] | None = None) -> int:
    from netsight.config import data_dir
    from netsight.demo.run_survey import _groups, _load_set

    p = argparse.ArgumentParser()
    p.add_argument("--dump", default="runs/calib_v0.4")
    p.add_argument("--out", default=None)
    a = p.parse_args(argv)
    dump = data_dir() / a.dump
    info = json.loads((dump / "info.json").read_text("utf-8"))
    res = {}
    for name in sorted(info["sets"]):
        if not name.startswith("test_"):
            continue
        preds, gts = _load_set(dump / f"{name}.npz")
        res[name] = breakdown(preds, gts, _groups(dump / f"{name}.npz", len(preds)))
        print(name, json.dumps(res[name]))
    out = Path(a.out) if a.out else dump / "error_breakdown.json"
    out.write_text(json.dumps(res, indent=2), "utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
