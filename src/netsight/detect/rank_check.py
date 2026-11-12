"""Is "proposed but scored low" real, or chance overlap from 100 proposals per image?

For each test object: the best score among proposals with IoU >= 0.3, and its rank among all
proposals in the image. Control: the same box moved to a random position in the same image
(seeded); chance of a proposal with IoU >= 0.3 there, and its score. Also recall when the
budget grows (1, 2, 3, 5, 10 flagged per image) to see how much a better ranking could recover.

    python -m netsight.detect.rank_check --dump runs/calib_v0.4
"""

from __future__ import annotations

import argparse
import json

import numpy as np

from netsight.detect.error_breakdown import _iou


def analyse(preds, gts, groups, rng) -> dict:
    from netsight.detect.operating_run import count_threshold

    real_s, ctrl_s, ranks = [], [], []
    recall_at = {}
    for budget in (1, 2, 3, 5, 10):
        thr = {}
        for g in sorted(set(groups)):
            idx = [i for i, x in enumerate(groups) if x == g]
            thr[g] = count_threshold(np.concatenate([preds[i][1] for i in idx]), len(idx), budget)
        k = n = 0
        for (b, s), gt, g in zip(preds, gts, groups, strict=True):
            gt = np.asarray(gt, float).reshape(-1, 4)
            b = np.asarray(b, float).reshape(-1, 4)
            m = _iou(gt, b[s >= thr[g]])
            n += len(gt)
            k += int((m.max(1) >= 0.5).sum()) if m.size else 0
        recall_at[budget] = round(k / max(n, 1), 3)
    for (b, s), gt in zip(preds, gts, strict=True):
        gt = np.asarray(gt, float).reshape(-1, 4)
        b = np.asarray(b, float).reshape(-1, 4)
        s = np.asarray(s, float)
        if not len(gt):
            continue
        W = max(b[:, 2].max() if len(b) else 1, gt[:, 2].max())
        H = max(b[:, 3].max() if len(b) else 1, gt[:, 3].max())
        order = np.argsort(-s)
        rank_of = np.empty(len(s), int)
        rank_of[order] = np.arange(len(s))
        m = _iou(gt, b)
        for j in range(len(gt)):
            hit = np.flatnonzero(m[j] >= 0.3) if len(b) else np.zeros(0, int)
            real_s.append(float(s[hit].max()) if hit.size else 0.0)
            ranks.append(int(rank_of[hit].min()) if hit.size else 999)
            w, h = gt[j, 2] - gt[j, 0], gt[j, 3] - gt[j, 1]
            x = rng.uniform(0, max(W - w, 1))
            y = rng.uniform(0, max(H - h, 1))
            c = _iou(np.array([[x, y, x + w, y + h]]), b)[0] if len(b) else np.zeros(0)
            ch = np.flatnonzero(c >= 0.3)
            ctrl_s.append(float(s[ch].max()) if ch.size else 0.0)
    real_s, ctrl_s, ranks = map(np.asarray, (real_s, ctrl_s, ranks))
    return {
        "objects": int(len(real_s)),
        "proposed_real": round(float((real_s > 0).mean()), 3),
        "proposed_random_control": round(float((ctrl_s > 0).mean()), 3),
        "median_score_real_if_proposed": round(float(np.median(real_s[real_s > 0])), 3)
        if (real_s > 0).any()
        else None,
        "median_score_control_if_proposed": round(float(np.median(ctrl_s[ctrl_s > 0])), 3)
        if (ctrl_s > 0).any()
        else None,
        "rank_in_image_quantiles_p25_p50_p75": [
            int(v) for v in np.quantile(ranks, [0.25, 0.5, 0.75])
        ],
        "share_rank_top1": round(float((ranks == 0).mean()), 3),
        "share_rank_top5": round(float((ranks < 5).mean()), 3),
        "share_rank_top20": round(float((ranks < 20).mean()), 3),
        "recall_iou50_at_budget_per_image": recall_at,
    }


def main(argv: list[str] | None = None) -> int:
    from netsight.config import data_dir
    from netsight.demo.run_survey import _groups, _load_set

    p = argparse.ArgumentParser()
    p.add_argument("--dump", default="runs/calib_v0.4")
    a = p.parse_args(argv)
    dump = data_dir() / a.dump
    info = json.loads((dump / "info.json").read_text("utf-8"))
    rng = np.random.default_rng(0)
    out = {}
    for name in sorted(info["sets"]):
        if name.startswith("test_"):
            preds, gts = _load_set(dump / f"{name}.npz")
            out[name] = analyse(preds, gts, _groups(dump / f"{name}.npz", len(preds)), rng)
            print(name, json.dumps(out[name]))
    (dump / "rank_check.json").write_text(json.dumps(out, indent=2), "utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
