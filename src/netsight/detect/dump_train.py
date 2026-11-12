"""Predictions of a model on one dataset's training images (for label review), same format as
calibrate_run dumps: <out>/train_<dataset_id>.npz.

    python -m netsight.detect.dump_train --model runs/research_v0.4/model \
        --dataset mine_detection_sss --out runs/calib_v0.4
"""

from __future__ import annotations

import argparse

import numpy as np


def main(argv: list[str] | None = None) -> int:
    import torch
    from transformers import AutoImageProcessor, DFineForObjectDetection

    from netsight.config import data_dir
    from netsight.detect.calibrate_run import save_predictions
    from netsight.detect.pilot import build_splits
    from netsight.detect.pixel_cache import PixelCache
    from netsight.detect.tta import predict_image_tta

    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--dataset", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    root = data_dir()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = DFineForObjectDetection.from_pretrained(root / a.model).to(device).eval()
    processor = AutoImageProcessor.from_pretrained(root / a.model)
    samples = [s for s in build_splits(root)["train"] if s.dataset_id == a.dataset]
    px = PixelCache(root / "cache" / "pixels")
    with torch.inference_mode():
        preds = [
            predict_image_tta(
                model,
                processor,
                np.asarray(px.get(s), np.uint8),
                tile_px=640,
                device=device,
                views="none",
            )
            for s in samples
        ]
    out = root / a.out
    out.mkdir(parents=True, exist_ok=True)
    save_predictions(
        out / f"train_{a.dataset}.npz",
        preds,
        [s.boxes for s in samples],
        [s.group for s in samples],
    )
    print(a.dataset, len(samples), "training images")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
