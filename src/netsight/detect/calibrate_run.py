"""Detector -> trust layer: calibrate a trained model's scores on real held-out detections.

Step 1 (GPU) dumps predictions on every validation and test set:

    python -m netsight.detect.calibrate_run dump --model runs/research_v0.1/model --out <dir>

Step 2 (CPU) fits calibrators on validation detections and scores them on test detections,
per dataset and with one pooled calibrator (does one calibration transfer across surveys?):

    python -m netsight.detect.calibrate_run report --preds <dir> --out <file.md>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from netsight.trust.detector_calibration import (
    best_method,
    calibration_report,
    detection_pairs,
    report_markdown,
)


def save_predictions(path: Path, preds, gts) -> None:
    """One .npz per set: concatenated boxes with the image index of each row."""

    def stack(rows, width):
        rows = [np.asarray(r, dtype=np.float64).reshape(-1, width) for r in rows]
        idx = np.concatenate([np.full(len(r), i) for i, r in enumerate(rows)] or [np.zeros(0)])
        data = np.concatenate(rows) if rows else np.zeros((0, width))
        return data, idx.astype(np.int64)

    boxes, pidx = stack([b for b, _ in preds], 4)
    scores = np.concatenate(
        [np.asarray(s, dtype=np.float64).reshape(-1) for _, s in preds] or [np.zeros(0)]
    )
    gt, gidx = stack(gts, 4)
    np.savez_compressed(
        path,
        boxes=boxes,
        scores=scores,
        pred_image=pidx,
        gt=gt,
        gt_image=gidx,
        n_images=np.int64(len(gts)),
    )


def load_predictions(path: Path):
    z = np.load(path)
    n = int(z["n_images"])
    preds = [
        (z["boxes"][z["pred_image"] == i], z["scores"][z["pred_image"] == i]) for i in range(n)
    ]
    gts = [z["gt"][z["gt_image"] == i] for i in range(n)]
    return preds, gts


def dump(
    model_dir: Path,
    out: Path,
    tile: int | None,
    limit: int | None,
    views: str = "none",
    merge: str = "wbf",
) -> None:
    import torch
    from transformers import AutoImageProcessor, DFineForObjectDetection

    from netsight.config import data_dir
    from netsight.detect.dfine import ImageCache
    from netsight.detect.pilot import build_splits
    from netsight.detect.pixel_cache import PixelCache
    from netsight.detect.tta import predict_image_tta

    manifest = json.loads((model_dir / "manifest.json").read_text(encoding="utf-8"))
    tile = tile or int(manifest.get("config", {}).get("tile", 640))
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = DFineForObjectDetection.from_pretrained(model_dir).to(device)
    processor = AutoImageProcessor.from_pretrained(model_dir)
    pixel_dir = data_dir() / "cache" / "pixels"
    cache = PixelCache(pixel_dir) if (pixel_dir / "index.json").exists() else ImageCache(2048)
    splits = build_splits(data_dir())
    out.mkdir(parents=True, exist_ok=True)
    info = {
        "model": str(model_dir),
        "model_id": manifest.get("model_id"),
        "tile": tile,
        "tta": views,
        "merge": merge,
        "sets": {},
    }
    with torch.inference_mode():
        for split in ("val", "test"):
            for name, samples in splits[split].items():
                samples = samples[:limit] if limit else samples
                if not samples:
                    continue
                preds = [
                    predict_image_tta(
                        model,
                        processor,
                        cache.get(s),
                        tile_px=tile,
                        device=device,
                        views=views,
                        merge=merge,
                    )
                    for s in samples
                ]
                save_predictions(out / f"{split}_{name}.npz", preds, [s.boxes for s in samples])
                info["sets"][f"{split}_{name}"] = len(samples)
                print(split, name, len(samples), flush=True)
    (out / "info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")


def detection_metrics(pred_dir: Path) -> dict:
    """AP50, AP30, AP50 small and recall at 1 FP/image for every dumped set."""
    from netsight.detect.evaluation import (
        AREA_SMALL,
        average_precision,
        match_detections,
        recall_at_fp_per_image,
    )

    info = json.loads((pred_dir / "info.json").read_text(encoding="utf-8"))
    rows = {}
    for key in info["sets"]:
        preds, gts = load_predictions(pred_dir / f"{key}.npz")
        m = match_detections(preds, gts)
        rows[key] = {
            "ap50": average_precision(m),
            "ap30": average_precision(match_detections(preds, gts, iou_threshold=0.3)),
            "ap50_small": average_precision(m, size_range=AREA_SMALL),
            "recall_1fp": recall_at_fp_per_image(m, 1.0)[0],
        }
    (pred_dir / "detection_metrics.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return rows


def _pairs(path: Path, iou: float, min_score: float):
    preds, gts = load_predictions(path)
    return detection_pairs(preds, gts, iou_threshold=iou, min_score=min_score)


def report(pred_dir: Path, out: Path, iou: float, min_score: float) -> dict:
    info = json.loads((pred_dir / "info.json").read_text(encoding="utf-8"))
    names = sorted(k[5:] for k in info["sets"] if k.startswith("test_"))
    fit = {
        k[4:]: _pairs(pred_dir / f"{k}.npz", iou, min_score)
        for k in info["sets"]
        if k.startswith("val_")
    }
    pooled = (
        np.concatenate([p for p, _ in fit.values()]),
        np.concatenate([y for _, y in fit.values()]),
    )
    lines = [
        f"# Detector score calibration: {info['model_id']}",
        "",
        f"Detections with score >= {min_score}; a detection is correct if IoU >= {iou} with "
        "an unmatched object. Calibrators are fitted on validation detections and scored "
        "on test detections only. Missed objects have no score; they appear in recall, "
        "not here.",
        "",
    ]
    summary = {}
    for name in names:
        test_p, test_y = _pairs(pred_dir / f"test_{name}.npz", iou, min_score)
        if not len(test_p):
            continue
        own = name.removesuffix("_shift")
        for label, (fp, fy) in (("own validation", fit.get(own)), ("pooled validation", pooled)):
            if fp is None or not len(fp) or len(set(fy.tolist())) < 2:
                continue
            res = calibration_report(fp, fy, test_p, test_y)
            lines += [
                report_markdown(res, title=f"{name}: fitted on {label}"),
                f"Fit pairs {len(fp)} ({fy.mean():.1%} correct); test pairs {len(test_p)} "
                f"({test_y.mean():.1%} correct).",
                "",
            ]
            raw = next(r for r in res if r.method == "raw")
            best = next(r for r in res if r.method == best_method(res))
            summary[f"{name}|{label}"] = {
                "raw_ece": raw.test_ece,
                "best": best.method,
                "best_ece": best.test_ece,
                "raw_brier": raw.test_brier,
                "best_brier": best.test_brier,
            }
    out.write_text("\n".join(lines), encoding="utf-8")
    (out.with_suffix(".json")).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dump")
    d.add_argument("--model", type=Path, required=True)
    d.add_argument("--out", type=Path, required=True)
    d.add_argument("--tile", type=int)
    d.add_argument("--limit", type=int, help="images per set (smoke test)")
    d.add_argument("--tta", choices=["none", "hflip", "hvflip"], default="none")
    d.add_argument("--merge", choices=["wbf", "nms"], default="wbf")
    a = sub.add_parser("ap", help="detection metrics of a dump, per set")
    a.add_argument("--preds", type=Path, required=True)
    r = sub.add_parser("report")
    r.add_argument("--preds", type=Path, required=True)
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--iou", type=float, default=0.5)
    r.add_argument("--min-score", type=float, default=0.05)
    args = ap.parse_args(argv)
    if args.cmd == "dump":
        dump(args.model, args.out, args.tile, args.limit, args.tta, args.merge)
    elif args.cmd == "ap":
        for key, row in detection_metrics(args.preds).items():
            print(key, {k: round(v, 4) for k, v in row.items()})
    else:
        for key, row in report(args.preds, args.out, args.iou, args.min_score).items():
            print(key, {k: round(v, 4) if isinstance(v, float) else v for k, v in row.items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
