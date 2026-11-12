"""Check that the ONNX export gives the same detections as PyTorch, and time CPU inference.

    python -m netsight.detect.onnx_parity --model runs/research_v0.4/model \
        --onnx runs/onnx_v0.4/model.onnx --images 8 --out runs/onnx_v0.4/parity.json
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import time
from pathlib import Path

import numpy as np


def _match(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Best IoU of each box in ``a`` against ``b``."""
    if not len(a) or not len(b):
        return np.zeros(len(a))
    ix = np.clip(
        np.minimum(a[:, None, 2], b[None, :, 2]) - np.maximum(a[:, None, 0], b[None, :, 0]), 0, None
    )
    iy = np.clip(
        np.minimum(a[:, None, 3], b[None, :, 3]) - np.maximum(a[:, None, 1], b[None, :, 1]), 0, None
    )
    inter = ix * iy
    area = lambda x: (x[:, 2] - x[:, 0]) * (x[:, 3] - x[:, 1])  # noqa: E731
    return (inter / (area(a)[:, None] + area(b)[None, :] - inter + 1e-9)).max(1)


def main(argv: list[str] | None = None) -> int:
    import torch
    from transformers import AutoImageProcessor, DFineForObjectDetection

    from netsight.config import data_dir
    from netsight.detect.dfine import predict_image
    from netsight.detect.onnx_export import OnnxDetector, predict_image_onnx
    from netsight.detect.pilot import build_splits
    from netsight.detect.pixel_cache import PixelCache

    p = argparse.ArgumentParser()
    p.add_argument("--model", default="runs/research_v0.4/model")
    p.add_argument("--onnx", default="runs/onnx_v0.4/model.onnx")
    p.add_argument("--images", type=int, default=8)
    p.add_argument("--threads", type=int, default=None)
    p.add_argument("--out", default="runs/onnx_v0.4/parity.json")
    a = p.parse_args(argv)
    root = data_dir()
    model = DFineForObjectDetection.from_pretrained(root / a.model).eval()
    processor = AutoImageProcessor.from_pretrained(root / a.model)
    det = OnnxDetector(root / a.onnx, threads=a.threads)
    pixels = PixelCache(root / "cache" / "pixels")
    test = build_splits(root)["test"]
    images = []
    for name in ("aquascan", "ghostvision", "mine", "sctd"):
        images += [np.asarray(pixels.get(s), np.uint8) for s in test[name][: a.images // 4]]
    rows, t_torch, t_onnx, mpix = [], 0.0, 0.0, 0.0
    for im in images:
        t0 = time.perf_counter()
        with torch.inference_mode():
            bt, st = predict_image(model, processor, im, tile_px=640, device="cpu")
        t1 = time.perf_counter()
        bo, so = predict_image_onnx(det, im, tile_px=640)
        t2 = time.perf_counter()
        t_torch += t1 - t0
        t_onnx += t2 - t1
        mpix += im.size / 1e6
        keep_t, keep_o = st >= 0.3, so >= 0.3
        iou = _match(bt[keep_t], bo[keep_o])
        rows.append(
            {
                "shape": list(im.shape),
                "torch_dets_0.3": int(keep_t.sum()),
                "onnx_dets_0.3": int(keep_o.sum()),
                "min_iou_torch_to_onnx": float(iou.min()) if iou.size else None,
                "top_score_diff": float(
                    abs((st.max() if st.size else 0) - (so.max() if so.size else 0))
                ),
            }
        )
    out = {
        "images": len(images),
        "per_image": rows,
        "cpu": platform.processor(),
        "cpu_count": os.cpu_count(),
        "threads": a.threads,
        "torch_cpu_seconds_per_image": t_torch / len(images),
        "onnx_cpu_seconds_per_image": t_onnx / len(images),
        "onnx_megapixels_per_second": mpix / t_onnx,
        "all_counts_equal": all(r["torch_dets_0.3"] == r["onnx_dets_0.3"] for r in rows),
        "max_top_score_diff": max(r["top_score_diff"] for r in rows),
    }
    Path(root / a.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "per_image"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
