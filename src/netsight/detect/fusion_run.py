"""WP4 + WP11 experiment: evidence fusion and baselines B0, B1, B3 on held-out test detections.

Detections (raw score >= 0.1) from the v0.4 prediction dump are labelled real/false by greedy
IoU >= 0.5 matching, evidence is measured on the image, models are fitted on validation and
scored on test. Detections are sampled (seeded) up to --cap per set to bound run time.

    python -m netsight.detect.fusion_run --dump runs/calib_v0.4 --out runs/fusion_v0.4
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def _label(boxes: np.ndarray, scores: np.ndarray, gt: np.ndarray, iou: float = 0.5) -> np.ndarray:
    """Greedy score-ordered matching; True for detections matched to a ground-truth box."""
    from netsight.detect.evaluation import iou_matrix

    out = np.zeros(len(scores), bool)
    gt = np.asarray(gt, float).reshape(-1, 4)
    if not len(gt) or not len(boxes):
        return out
    m = iou_matrix(np.asarray(boxes, float), gt)
    used = np.zeros(len(gt), bool)
    for i in np.argsort(-scores, kind="stable"):
        cand = np.where(~used & (m[i] >= iou))[0]
        if cand.size:
            j = cand[np.argmax(m[i, cand])]
            used[j] = out[i] = True
    return out


def collect(dump: Path, split_name: str, samples, pixels, cap: int, rng) -> dict:
    from netsight.demo.run_survey import _load_set
    from netsight.evidence import evidence_features

    preds, gts = _load_set(dump / f"{split_name}.npz")
    rows = []
    for i, ((boxes, scores), gt) in enumerate(zip(preds, gts, strict=True)):
        keep = scores >= 0.1
        lab = _label(boxes, scores, gt)
        for b, s, y in zip(boxes[keep], scores[keep], lab[keep], strict=True):
            rows.append((i, b, float(s), bool(y)))
    if len(rows) > cap:
        rows = [rows[k] for k in sorted(rng.choice(len(rows), cap, replace=False))]
    feats, scores, labels = [], [], []
    cache: dict[int, np.ndarray] = {}
    for i, b, s, y in rows:
        if i not in cache:
            cache.clear()
            cache[i] = np.asarray(pixels.get(samples[i]), np.uint8)
        ev = evidence_features(cache[i], b).as_dict()
        w, h = max(b[2] - b[0], 1.0), max(b[3] - b[1], 1.0)
        ev["log_side_px"] = float(np.log(np.sqrt(w * h)))
        ev["log_aspect"] = float(np.log(w / h))
        feats.append(ev)
        scores.append(s)
        labels.append(y)
    return {"features": feats, "scores": np.array(scores), "labels": np.array(labels, bool)}


def evaluate(val: dict, test: dict) -> dict:
    from netsight.trust.baselines import b3_shadow_filter
    from netsight.trust.calibration_metrics import brier_score, expected_calibration_error
    from netsight.trust.calibrators import BetaCalibrator, TemperatureScaling
    from netsight.trust.fusion import FEATURE_GROUPS, feature_matrix, fit_fusion, log_loss

    names = [n for g in FEATURE_GROUPS.values() for n in g]
    fv = feature_matrix(val["features"], names)
    ft = feature_matrix(test["features"], names)
    sv, yv, st, yt = val["scores"], val["labels"], test["scores"], test["labels"]

    def metrics(p: np.ndarray) -> dict:
        return {
            "log_loss": log_loss(p, yt),
            "brier": brier_score(p, yt),
            "ece": expected_calibration_error(p, yt),
            "auroc": _auroc(p, yt),
        }

    out = {"n_val": int(len(sv)), "n_test": int(len(st)), "test_real": int(yt.sum())}
    out["B0_raw"] = metrics(st)
    out["B1_temperature"] = metrics(TemperatureScaling().fit(sv, yv).predict(st))
    out["beta_score_only"] = metrics(BetaCalibrator().fit(sv, yv).predict(st))
    full = fit_fusion(sv, fv, yv, names)
    out["fusion_all"] = metrics(full.predict(st, ft))
    out["fusion_weights"] = dict(
        zip(["intercept", "score", *names], map(float, full.coef), strict=True)
    )
    ablation = {}
    for group, cols in FEATURE_GROUPS.items():
        keep = [k for k, n in enumerate(names) if n not in cols]
        m = fit_fusion(sv, fv[:, keep], yv, [names[k] for k in keep])
        ablation[group] = log_loss(m.predict(st, ft[:, keep]), yt) - out["fusion_all"]["log_loss"]
    out["ablation_logloss_increase_without"] = ablation
    shadow = feature_matrix(test["features"], ["shadow_present"])[:, 0] > 0
    b3 = b3_shadow_filter(st, shadow)
    out["B3_shadow_required"] = {
        "real_detections_dropped": int((yt & ~shadow).sum()),
        "real_detections": int(yt.sum()),
        "share_real_dropped": float((yt & ~shadow).sum() / max(yt.sum(), 1)),
        "auroc": _auroc(b3, yt),
    }
    return out


def _auroc(p: np.ndarray, y: np.ndarray) -> float:
    from netsight.trust.withdrawal_eval import auroc

    return auroc(list(map(float, p)), list(map(bool, y)))


def main(argv: list[str] | None = None) -> int:
    from netsight.config import data_dir
    from netsight.detect.pilot import build_splits
    from netsight.detect.pixel_cache import PixelCache

    p = argparse.ArgumentParser()
    p.add_argument("--dump", default="runs/calib_v0.4")
    p.add_argument("--out", default="runs/fusion_v0.4")
    p.add_argument("--cap", type=int, default=800)
    a = p.parse_args(argv)
    root = data_dir()
    dump, out = root / a.dump, root / a.out
    out.mkdir(parents=True, exist_ok=True)
    splits = build_splits(root)
    pixels = PixelCache(root / "cache" / "pixels")
    rng = np.random.default_rng(0)
    info = json.loads((dump / "info.json").read_text(encoding="utf-8"))
    data: dict[str, dict] = {}
    for name in sorted(info["sets"]):
        split, dataset = name.split("_", 1)
        data[name] = collect(dump, name, splits[split][dataset], pixels, a.cap, rng)
        print(name, len(data[name]["scores"]), flush=True)

    def pool(prefix: str, names: list[str]) -> dict:
        parts = [data[f"{prefix}_{n}"] for n in names if f"{prefix}_{n}" in data]
        return {
            "features": [f for d in parts for f in d["features"]],
            "scores": np.concatenate([d["scores"] for d in parts]),
            "labels": np.concatenate([d["labels"] for d in parts]),
        }

    val_sets = [n.split("_", 1)[1] for n in data if n.startswith("val_")]
    test_sets = [n.split("_", 1)[1] for n in data if n.startswith("test_")]
    results = {"pooled": evaluate(pool("val", val_sets), pool("test", test_sets))}
    for t in test_sets:
        v = "ghostvision" if t == "ghostvision_shift" else t
        if f"val_{v}" in data:
            try:
                results[t] = evaluate(data[f"val_{v}"], data[f"test_{t}"])
            except ValueError as exc:
                results[t] = {"error": str(exc)}
    (out / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results["pooled"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
