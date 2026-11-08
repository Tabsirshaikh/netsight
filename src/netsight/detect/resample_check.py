"""Test B: does undoing a sensor's pixel stretch recover detection on a shifted recording?

Each image is resampled along the rows (and optionally scaled) before tiled inference, and the
boxes are mapped back, so scores are on the original labels. Inference only.

    python -m netsight.detect.resample_check --model <dir> --set ghostvision_shift \
        --row-scale 1.32 --scale 1.0 --scale 2.0
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def resample(image: np.ndarray, row_scale: float, scale: float) -> np.ndarray:
    from scipy.ndimage import zoom

    return zoom(image, (row_scale * scale, scale), order=1)


def main(argv: list[str] | None = None) -> int:
    import torch
    from transformers import AutoImageProcessor, DFineForObjectDetection

    from netsight.config import data_dir
    from netsight.detect.dfine import ImageCache
    from netsight.detect.evaluation import (
        average_precision,
        match_detections,
        recall_at_fp_per_image,
    )
    from netsight.detect.pilot import build_splits
    from netsight.detect.pixel_cache import PixelCache
    from netsight.detect.tta import predict_image_tta

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--set", nargs="+", default=["ghostvision_shift"])
    ap.add_argument("--split", default="test")
    ap.add_argument("--row-scale", type=float, nargs="+", default=[1.0])
    ap.add_argument("--scale", type=float, nargs="+", default=[1.0])
    ap.add_argument("--tile", type=int, default=640)
    args = ap.parse_args(argv)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = DFineForObjectDetection.from_pretrained(args.model).to(device)
    processor = AutoImageProcessor.from_pretrained(args.model)
    pixel_dir = data_dir() / "cache" / "pixels"
    cache = PixelCache(pixel_dir) if (pixel_dir / "index.json").exists() else ImageCache(2048)
    splits = build_splits(data_dir())[args.split]
    rows = []
    with torch.inference_mode():
        for name in args.set:
            samples = splits[name]
            for rs in args.row_scale:
                for sc in args.scale:
                    preds = []
                    for s in samples:
                        img = cache.get(s)
                        b, p = predict_image_tta(
                            model,
                            processor,
                            resample(img, rs, sc),
                            tile_px=args.tile,
                            device=device,
                            views="none",
                        )
                        b = np.asarray(b, float).reshape(-1, 4) / [sc, rs * sc, sc, rs * sc]
                        preds.append((b, p))
                    gts = [s.boxes for s in samples]
                    row = {"set": name, "row_scale": rs, "scale": sc}
                    for iou in (0.5, 0.3):
                        m = match_detections(preds, gts, iou_threshold=iou)
                        row[f"ap{int(iou * 100)}"] = average_precision(m)
                    row["recall_1fp"] = recall_at_fp_per_image(match_detections(preds, gts), 1.0)[0]
                    rows.append(row)
                    print(
                        json.dumps(
                            {k: round(v, 4) if isinstance(v, float) else v for k, v in row.items()}
                        ),
                        flush=True,
                    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
