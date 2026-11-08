"""Paired comparison of two models on the same test images, with bootstrap intervals.

    python -m netsight.detect.compare_run --a <dump dir> --b <dump dir> [--iou 0.5]

Images are resampled with replacement (the same draw for both models), so the interval is for
the AP difference B - A on these test images. Images from one recording are correlated, so this
interval is optimistic; with only 1-3 recordings per test set a recording-level bootstrap is not
possible.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from netsight.detect.calibrate_run import load_predictions
from netsight.detect.evaluation import match_detections


def per_image(path: Path, iou: float) -> list[tuple[np.ndarray, np.ndarray, int]]:
    """Matched (scores, is_tp, n_gt) for each image; matching never crosses images."""
    preds, gts = load_predictions(path)
    out = []
    for p, g in zip(preds, gts, strict=True):
        m = match_detections([p], [g], iou_threshold=iou)
        out.append((np.asarray(m.scores, float), np.asarray(m.is_tp, bool), int(m.n_gt)))
    return out


def ap_from(images: list[tuple], idx: np.ndarray) -> float:
    """All-point interpolated AP (as netsight.detect.evaluation.average_precision)."""
    n_gt = sum(images[i][2] for i in idx)
    if n_gt == 0:
        return float("nan")
    scores = np.concatenate([images[i][0] for i in idx])
    is_tp = np.concatenate([images[i][1] for i in idx])
    if not scores.size:
        return 0.0
    is_tp = is_tp[np.argsort(-scores, kind="stable")]
    tp = np.cumsum(is_tp, dtype=float)
    fp = np.cumsum(~is_tp, dtype=float)
    recall = np.concatenate(([0.0], tp / n_gt, [1.0]))
    precision = np.concatenate(([0.0], tp / (tp + fp), [0.0]))
    precision = np.maximum.accumulate(precision[::-1])[::-1]
    return float(np.sum(np.diff(recall) * precision[1:]))


def compare(
    a_dir: Path, b_dir: Path, *, iou: float = 0.5, n_boot: int = 1000, seed: int = 0
) -> dict:
    sets_a = json.loads((a_dir / "info.json").read_text(encoding="utf-8"))["sets"]
    sets_b = json.loads((b_dir / "info.json").read_text(encoding="utf-8"))["sets"]
    rng = np.random.default_rng(seed)
    rows = {}
    for key in sorted(k for k in sets_a if k in sets_b and k.startswith("test_")):
        a, b = per_image(a_dir / f"{key}.npz", iou), per_image(b_dir / f"{key}.npz", iou)
        if len(a) != len(b):
            raise ValueError(f"{key}: different test images ({len(a)} vs {len(b)})")
        full = np.arange(len(a))
        diffs = []
        for _ in range(n_boot):
            idx = rng.integers(0, len(a), len(a))
            diffs.append(ap_from(b, idx) - ap_from(a, idx))
        lo, hi = np.nanpercentile(diffs, [2.5, 97.5])
        rows[key[5:]] = {
            "a": ap_from(a, full),
            "b": ap_from(b, full),
            "diff": ap_from(b, full) - ap_from(a, full),
            "ci": (lo, hi),
        }
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--a", type=Path, required=True)
    ap.add_argument("--b", type=Path, required=True)
    ap.add_argument("--iou", type=float, default=0.5)
    ap.add_argument("--n-boot", type=int, default=1000)
    args = ap.parse_args(argv)
    print(f"| Test set | A AP@{args.iou} | B AP@{args.iou} | B - A | 95% CI |")
    print("|---|---|---|---|---|")
    for name, r in compare(args.a, args.b, iou=args.iou, n_boot=args.n_boot).items():
        lo, hi = r["ci"]
        print(
            f"| {name} | {r['a']:.3f} | {r['b']:.3f} | {r['diff']:+.3f} | {lo:+.3f} to {hi:+.3f} |"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
