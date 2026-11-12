"""Self-training data: the model labels unlabelled survey images itself (no ground truth used).

An image is kept only when every detection is either confident (score >= --high) or clearly
background (score < --low), so an object the model is unsure about is never taught as
background. Confident boxes become pseudo-labels.

    python -m netsight.detect.pseudo_label --model runs/proxy_base/model \
        --sets ghostvision_shift,mine --out runs/pseudo_proxy_base.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def select(boxes: np.ndarray, scores: np.ndarray, high: float, low: float) -> np.ndarray | None:
    """Pseudo boxes for one image, or None when an ambiguous detection makes it unusable."""
    scores = np.asarray(scores, float).reshape(-1)
    boxes = np.asarray(boxes, float).reshape(-1, 4)
    if np.any((scores >= low) & (scores < high)):
        return None
    return boxes[scores >= high]


def main(argv: list[str] | None = None) -> int:
    import torch
    from transformers import AutoImageProcessor, DFineForObjectDetection

    from netsight.config import data_dir
    from netsight.detect.pilot import build_splits
    from netsight.detect.pixel_cache import PixelCache
    from netsight.detect.tta import predict_image_tta

    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--sets", required=True, help="test set names, comma-separated")
    p.add_argument("--out", required=True)
    p.add_argument("--high", type=float, default=0.5)
    p.add_argument("--low", type=float, default=0.15)
    a = p.parse_args(argv)
    root = data_dir()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = DFineForObjectDetection.from_pretrained(root / a.model).to(device).eval()
    processor = AutoImageProcessor.from_pretrained(root / a.model)
    test = build_splits(root)["test"]
    pixels = PixelCache(root / "cache" / "pixels")
    out: dict = {"model": a.model, "high": a.high, "low": a.low, "sets": {}}
    for name in a.sets.split(","):
        rows, n_box = [], 0
        for s in test[name]:
            with torch.inference_mode():
                b, sc = predict_image_tta(
                    model,
                    processor,
                    np.asarray(pixels.get(s), np.uint8),
                    tile_px=640,
                    device=device,
                    views="hflip",
                )
            kept = select(b, sc, a.high, a.low)
            if kept is not None:
                rows.append(
                    {
                        "member": s.member,
                        "zip_path": s.zip_path,
                        "boxes": np.round(kept, 2).tolist(),
                    }
                )
                n_box += len(kept)
        out["sets"][name] = rows
        print(
            name, f"{len(rows)} of {len(test[name])} images kept, {n_box} pseudo boxes", flush=True
        )
    Path(root / a.out).write_text(json.dumps(out), "utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
