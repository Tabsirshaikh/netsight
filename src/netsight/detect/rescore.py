"""Re-score saved predictions on corrected test labels (original / conservative v2 / generous v2).

    python -m netsight.detect.rescore --set mine --reviews relabel_gemini_mine,relabel_sol_mine \
        --dumps calib_v0.1,calib_v0.2,calib_v0.3,calib_v0.4
"""

from __future__ import annotations

import argparse
import json

import numpy as np


def main(argv: list[str] | None = None) -> int:
    from netsight.config import data_dir
    from netsight.datasets.relabel import corrected, evaluate, load_reviews
    from netsight.demo.run_survey import _load_set

    p = argparse.ArgumentParser()
    p.add_argument("--set", required=True)
    p.add_argument("--reviews", required=True, help="review folders, later ones override")
    p.add_argument("--dumps", required=True)
    p.add_argument("--out", default=None)
    a = p.parse_args(argv)
    R = data_dir() / "runs"
    rv = load_reviews([R / f for f in a.reviews.split(",")])
    rows = {}
    labels: dict = {}
    for dump in a.dumps.split(","):
        path = R / dump / f"test_{a.set}.npz"
        if not path.exists():
            continue
        preds, gts = _load_set(path)
        if not labels:
            for mode in ("conservative", "generous"):
                g, ig = [], []
                for i, orig in enumerate(gts):
                    if i in rv:
                        x, y, _ = corrected(rv[i], orig, mode)
                    else:
                        x, y = np.asarray(orig, float).reshape(-1, 4), np.zeros((0, 4))
                    g.append(x)
                    ig.append(y)
                labels[mode] = (g, ig)
            labels["original"] = ([np.asarray(x, float).reshape(-1, 4) for x in gts], None)
        row = {}
        for mode, (g, ig) in labels.items():
            for iou in (0.5, 0.3):
                row[f"{mode}@{iou}"] = round(evaluate(preds, g, ig, iou), 3)
        rows[dump] = row
        print(dump, json.dumps(row), flush=True)
    meta = {
        m: {
            "objects": int(sum(len(x) for x in g)),
            "ignore_regions": int(sum(len(x) for x in ig)) if ig else 0,
        }
        for m, (g, ig) in labels.items()
    }
    print("labels", json.dumps(meta))
    out = R / (a.out or f"rescore_{a.set}.json")
    out.write_text(
        json.dumps({"labels": meta, "scores": rows, "reviewed_images": len(rv)}, indent=2), "utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
