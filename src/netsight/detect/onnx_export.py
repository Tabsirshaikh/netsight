"""Export D-FINE to ONNX and run tiled, offline CPU inference.

Torch, transformers, and ONNX Runtime are imported only by operations that need
them. Post-processing itself requires only NumPy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any

import numpy as np


def _positive_int(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value < 1:
        raise ValueError(f"{name} must be a positive integer")


def export_onnx(model_dir: Path, out_path: Path, *, opset: int = 17) -> Path:
    """Export a local save_pretrained directory, including provenance metadata."""
    _positive_int(opset, "opset")
    model_dir = Path(model_dir)
    out_path = Path(out_path)
    if not model_dir.is_dir():
        raise ValueError(f"Model directory does not exist: {model_dir}")
    if out_path.suffix.lower() != ".onnx":
        raise ValueError("out_path must have an .onnx suffix")

    import torch
    from transformers import DFineForObjectDetection

    from netsight.detect.dfine import NET_INPUT

    manifest_path = model_dir / "manifest.json"
    manifest: dict[str, Any] = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError("manifest.json must contain a JSON object")

    class ExportWrapper(torch.nn.Module):
        def __init__(self, model: torch.nn.Module) -> None:
            super().__init__()
            self.model = model

        def forward(self, pixel_values: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
            output = self.model(pixel_values=pixel_values)
            return output.logits, output.pred_boxes

    model = DFineForObjectDetection.from_pretrained(model_dir, local_files_only=True)
    wrapper = ExportWrapper(model.cpu().float().eval()).eval()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    dummy = torch.zeros((1, 3, NET_INPUT, NET_INPUT), dtype=torch.float32)
    with torch.inference_mode():
        torch.onnx.export(
            wrapper,
            (dummy,),
            str(out_path),
            opset_version=opset,
            input_names=["pixel_values"],
            output_names=["logits", "pred_boxes"],
            dynamic_axes={
                "pixel_values": {0: "batch"},
                "logits": {0: "batch"},
                "pred_boxes": {0: "batch"},
            },
            # Use the legacy exporter, which honors dynamic_axes across torch versions.
            dynamo=False,
        )

    with out_path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    metadata: dict[str, Any] = {
        "source": str(model_dir),
        "sha256": digest,
        "opset": opset,
        "input_size": NET_INPUT,
        "torch_version": str(torch.__version__),
    }
    for key in ("model_id", "manifest_sha256"):
        if key in manifest:
            metadata[key] = manifest[key]
    out_path.with_suffix(".json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    return out_path


def postprocess(
    logits: np.ndarray,
    pred_boxes: np.ndarray,
    target_sizes: list[tuple[int, int]],
    threshold: float,
    top_k: int = 300,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Apply sigmoid and global query/class top-k, then scale cxcywh boxes.

    Threshold comparison is inclusive. Equal scores retain flattened query/class
    order. Boxes are not clipped here, matching HF post-processing.
    """
    logits = np.asarray(logits)
    pred_boxes = np.asarray(pred_boxes)
    if logits.ndim != 3 or logits.shape[2] < 1:
        raise ValueError("logits must have shape (N, Q, C) with C >= 1")
    if pred_boxes.shape != (*logits.shape[:2], 4):
        raise ValueError("pred_boxes must have shape (N, Q, 4) matching logits")
    if not np.isfinite(logits).all() or not np.isfinite(pred_boxes).all():
        raise ValueError("logits and pred_boxes must be finite")
    if not np.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")
    _positive_int(top_k, "top_k")
    sizes = np.asarray(target_sizes, dtype=np.float64)
    if sizes.shape != (logits.shape[0], 2) or not np.isfinite(sizes).all():
        raise ValueError("target_sizes must contain one finite (height, width) per image")
    if np.any(sizes <= 0):
        raise ValueError("target heights and widths must be positive")

    # This form of sigmoid cannot overflow for large negative logits.
    values = logits.astype(np.float64)
    exp_negative_abs = np.exp(-np.abs(values))
    probabilities = np.where(
        values >= 0,
        1 / (1 + exp_negative_abs),
        exp_negative_abs / (1 + exp_negative_abs),
    )
    results = []
    classes = logits.shape[2]
    for batch, (height, width) in enumerate(sizes):
        flat = probabilities[batch].reshape(-1)
        indices = np.argsort(-flat, kind="stable")[:top_k]
        scores = flat[indices]
        keep = scores >= threshold
        scores = scores[keep]
        boxes = pred_boxes[batch, indices[keep] // classes].astype(np.float64)
        centers = boxes[:, :2]
        half_sides = boxes[:, 2:] / 2
        xyxy = np.concatenate((centers - half_sides, centers + half_sides), axis=1)
        xyxy *= np.array([width, height, width, height])
        results.append((xyxy, scores))
    return results


class OnnxDetector:
    """An ONNX Runtime session restricted to the CPU execution provider."""

    def __init__(self, onnx_path: Path | str, *, threads: int | None = None) -> None:
        if threads is not None:
            _positive_int(threads, "threads")
        if not Path(onnx_path).is_file():
            raise ValueError(f"ONNX file does not exist: {onnx_path}")

        import onnxruntime as ort

        options = ort.SessionOptions()
        if threads is not None:
            options.intra_op_num_threads = threads
        self.threads = threads
        self.session = ort.InferenceSession(
            str(onnx_path),
            sess_options=options,
            providers=["CPUExecutionProvider"],
        )

    def __call__(self, pixel_values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        from netsight.detect.dfine import NET_INPUT

        if (
            not isinstance(pixel_values, np.ndarray)
            or pixel_values.dtype != np.float32
            or pixel_values.ndim != 4
            or pixel_values.shape[0] < 1
            or pixel_values.shape[1:] != (3, NET_INPUT, NET_INPUT)
            or not np.isfinite(pixel_values).all()
        ):
            raise ValueError("pixel_values must be finite float32 with shape (N, 3, 640, 640)")
        logits, boxes = self.session.run(
            ["logits", "pred_boxes"],
            {"pixel_values": np.ascontiguousarray(pixel_values)},
        )
        return logits, boxes


def _clip_boxes(
    boxes: np.ndarray, scores: np.ndarray, height: int, width: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Clip boxes to crop bounds and remove sides shorter than one pixel."""
    boxes = boxes.copy()
    boxes[:, [0, 2]] = np.clip(boxes[:, [0, 2]], 0, width)
    boxes[:, [1, 3]] = np.clip(boxes[:, [1, 3]], 0, height)
    keep = (boxes[:, 2] - boxes[:, 0] >= 1) & (boxes[:, 3] - boxes[:, 1] >= 1)
    return boxes[keep], scores[keep], np.zeros(np.count_nonzero(keep), dtype=np.int64)


def predict_image_onnx(
    detector: OnnxDetector,
    image: np.ndarray,
    *,
    tile_px: int = 640,
    overlap: float = 0.25,
    full_image: bool = True,
    threshold: float = 0.01,
    batch_size: int = 4,
    max_detections: int = 100,
) -> tuple[np.ndarray, np.ndarray]:
    """Run the existing greyscale preprocessing and tile merge using ONNX outputs."""
    _positive_int(tile_px, "tile_px")
    _positive_int(batch_size, "batch_size")
    _positive_int(max_detections, "max_detections")
    if not np.isfinite(overlap) or not 0 <= overlap < 1:
        raise ValueError("overlap must be between 0 (inclusive) and 1 (exclusive)")
    if not np.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")
    if (
        not isinstance(image, np.ndarray)
        or image.ndim != 2
        or image.dtype != np.uint8
        or min(image.shape) < 1
    ):
        raise ValueError("image must be a nonempty greyscale uint8 array")

    from netsight.detect.dfine import to_pixels
    from netsight.detect.tiling import (
        full_image_pass_allowed,
        make_tiles,
        merge_detections,
    )

    height, width = image.shape
    tiles = list(make_tiles(width, height, tile_w=tile_px, tile_h=tile_px, overlap=overlap))

    def infer(crops: list[np.ndarray]) -> list[tuple[np.ndarray, np.ndarray, np.ndarray]]:
        logits, boxes = detector(to_pixels(crops).numpy())
        sizes = [crop.shape for crop in crops]
        results = postprocess(logits, boxes, sizes, threshold)
        return [
            _clip_boxes(boxes, scores, h, w)
            for (boxes, scores), (h, w) in zip(results, sizes, strict=True)
        ]

    per_tile = []
    for start in range(0, len(tiles), batch_size):
        batch = tiles[start : start + batch_size]
        crops = [image[t.y0 : t.y1, t.x0 : t.x1] for t in batch]
        for tile, result in zip(batch, infer(crops), strict=True):
            per_tile.append((tile, *result))

    full_result = None
    if full_image and full_image_pass_allowed(width, height, n_tiles=len(tiles)):
        full_result = infer([image])[0]
    boxes, scores, _ = merge_detections(
        per_tile,
        iou_threshold=0.5,
        class_agnostic=True,
        full_image=full_result,
    )
    order = np.argsort(-scores, kind="stable")[:max_detections]
    return boxes[order], scores[order]


def benchmark(
    detector: OnnxDetector,
    images: list[np.ndarray],
    *,
    tile_px: int = 640,
    repeats: int = 1,
) -> dict[str, int | float | None]:
    """Measure end-to-end inference, including preprocessing and tile merging."""
    _positive_int(repeats, "repeats")
    _positive_int(tile_px, "tile_px")
    if not images:
        raise ValueError("images must not be empty")
    start = time.perf_counter()
    for _ in range(repeats):
        for image in images:
            predict_image_onnx(detector, image, tile_px=tile_px)
    seconds = time.perf_counter() - start
    if seconds <= 0:
        raise ValueError("Benchmark elapsed time must be positive")
    count = len(images) * repeats
    megapixels = sum(image.size for image in images) * repeats / 1_000_000
    return {
        "images": count,
        "seconds_total": seconds,
        "seconds_per_image": seconds / count,
        "megapixels_per_second": megapixels / seconds,
        "threads": getattr(detector, "threads", None),
    }


def main(argv: list[str] | None = None) -> None:
    """Export a model or benchmark local raster images (first band)."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    export_parser = commands.add_parser("export")
    export_parser.add_argument("model_dir", type=Path)
    export_parser.add_argument("out_path", type=Path)
    bench_parser = commands.add_parser("bench")
    bench_parser.add_argument("onnx_path", type=Path)
    bench_parser.add_argument("images", nargs="+", type=Path)
    bench_parser.add_argument("--threads", type=int)
    args = parser.parse_args(argv)
    if args.command == "export":
        result = {"onnx_path": str(export_onnx(args.model_dir, args.out_path))}
    else:
        import rasterio

        detector = OnnxDetector(args.onnx_path, threads=args.threads)
        images = []
        for path in args.images:
            with rasterio.open(path) as dataset:
                images.append(dataset.read(1))
        result = benchmark(detector, images)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
