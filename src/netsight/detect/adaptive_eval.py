"""Evaluate label-free per-survey geometry correction (adaptive_resample) with a trained model.

For each dataset the geometry envelope comes from the model's own boxes on that dataset's
validation surveys (no labels). Every test survey (group) is run through `two_pass_predict`;
AP before (pass 1) and after correction are reported per test set.

    python -m netsight.detect.adaptive_eval --model <dir> --preds <dump dir with val sets>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def envelope_for(pred_dir: Path, dataset: str):
    from netsight.detect.calibrate_run import load_groups, load_predictions
    from netsight.trust.geometry_gate import AspectProfile, GeometryEnvelope

    path = pred_dir / f"val_{dataset}.npz"
    preds, _ = load_predictions(path)
    groups = load_groups(path)
    profiles = []
    for g in sorted(set(groups.tolist())):
        idx = np.flatnonzero(groups == g)
        boxes = np.concatenate([preds[i][0] for i in idx])
        scores = np.concatenate([preds[i][1] for i in idx])
        profiles.append(AspectProfile.from_boxes(boxes, scores))
    return GeometryEnvelope.from_profiles(profiles)


def main(argv: list[str] | None = None) -> int:
    import torch
    from transformers import AutoImageProcessor, DFineForObjectDetection

    from netsight.config import data_dir
    from netsight.detect.adaptive_resample import two_pass_predict
    from netsight.detect.compare_run import ap_from
    from netsight.detect.evaluation import match_detections
    from netsight.detect.pilot import build_splits
    from netsight.detect.pixel_cache import PixelCache
    from netsight.detect.tta import predict_image_tta

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--preds", type=Path, required=True)
    ap.add_argument(
        "--sets", nargs="+", default=["ghostvision", "ghostvision_shift", "aquascan", "mine"]
    )
    ap.add_argument("--tile", type=int, default=640)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = DFineForObjectDetection.from_pretrained(args.model).to(device)
    processor = AutoImageProcessor.from_pretrained(args.model)
    cache = PixelCache(data_dir() / "cache" / "pixels")
    splits = build_splits(data_dir())["test"]

    def predict(img):
        return predict_image_tta(
            model, processor, img, tile_px=args.tile, device=device, views="none"
        )

    rows = []
    with torch.inference_mode():
        for name in args.sets:
            env = envelope_for(args.preds, name.removesuffix("_shift"))
            samples = splits[name]
            before, after, gts, corrections = [], [], [], []
            for g in sorted({s.group for s in samples}):
                group = [s for s in samples if s.group == g]
                images = [cache.get(s) for s in group]
                first = [predict(im) for im in images]
                seen = {id(im): f for im, f in zip(images, first, strict=True)}

                def cached(im, _seen=seen):  # pass 1 reuses `first`; resampled images run anew
                    return _seen[id(im)] if id(im) in _seen else predict(im)

                preds, corr = two_pass_predict(cached, images, env)
                before += first
                after += preds
                gts += [s.boxes for s in group]
                corrections.append(
                    {
                        "group": g,
                        "row_scale": corr.row_scale,
                        "scale": corr.scale,
                        "source": corr.source,
                        "reasons_before": corr.reasons_before,
                        "reasons_after": corr.reasons_after,
                    }
                )
            row = {"set": name, "corrections": corrections}
            for label, p in (("before", before), ("after", after)):
                for iou in (0.5, 0.3):
                    per_img = []
                    for (b, s), gt in zip(p, gts, strict=True):
                        m = match_detections([(b, s)], [gt], iou_threshold=iou)
                        per_img.append((np.asarray(m.scores), np.asarray(m.is_tp), int(m.n_gt)))
                    row[f"{label}_ap{int(iou * 100)}"] = ap_from(per_img, np.arange(len(per_img)))
            rows.append(row)
            print(
                json.dumps(
                    {
                        k: (round(v, 4) if isinstance(v, float) else v)
                        for k, v in row.items()
                        if k != "corrections"
                    }
                ),
                flush=True,
            )
            for c in corrections:
                print(
                    "   ",
                    c["group"],
                    c["source"],
                    round(c["row_scale"], 2),
                    round(c["scale"], 2),
                    flush=True,
                )
    if args.out:
        args.out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
