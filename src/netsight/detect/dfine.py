"""D-FINE detector (Hugging Face transformers): tile training and SAHI-style inference.

Needs the optional ML stack (torch, transformers, pillow). Product models must start from the
COCO-only checkpoints (Apache-2.0); D-FINE's Objects365 weights are not commercially cleared.
"""

from __future__ import annotations

import io
import math
import zipfile
from collections import OrderedDict
from collections.abc import Sequence

import numpy as np
import torch
from PIL import Image
from torch.utils.data import Dataset

from netsight.datasets.detection import DetectionSample
from netsight.detect.tiling import make_tiles, merge_detections
from netsight.detect.training_tiles import TrainTile

PRODUCT_CHECKPOINT = "ustc-community/dfine-small-coco"
NET_INPUT = 640


class ImageCache:
    """Decoded greyscale images, read from zip members (zip handles kept open)."""

    def __init__(self, max_images: int = 512) -> None:
        self._zips: dict[str, zipfile.ZipFile] = {}
        self._images: OrderedDict[tuple[str, str], np.ndarray] = OrderedDict()
        self.max_images = max_images

    def get(self, sample: DetectionSample) -> np.ndarray:
        key = (sample.zip_path, sample.member)
        if key in self._images:
            self._images.move_to_end(key)
            return self._images[key]
        z = self._zips.get(sample.zip_path)
        if z is None:
            z = self._zips[sample.zip_path] = zipfile.ZipFile(sample.zip_path)
        img = np.asarray(Image.open(io.BytesIO(z.read(sample.member))).convert("L"), np.uint8)
        self._images[key] = img
        if len(self._images) > self.max_images:
            self._images.popitem(last=False)
        return img


def _rgb(grey: np.ndarray) -> np.ndarray:
    return np.repeat(grey[:, :, None], 3, axis=2)


def _clip(result: dict, h: int, w: int, min_side: float = 1.0):
    """DETR boxes can extend past the frame: clip to it and drop degenerate boxes."""
    boxes = result["boxes"].float().cpu().numpy().reshape(-1, 4)
    scores = result["scores"].float().cpu().numpy().reshape(-1)
    boxes[:, [0, 2]] = boxes[:, [0, 2]].clip(0, w)
    boxes[:, [1, 3]] = boxes[:, [1, 3]].clip(0, h)
    keep = ((boxes[:, 2] - boxes[:, 0]) >= min_side) & ((boxes[:, 3] - boxes[:, 1]) >= min_side)
    return boxes[keep], scores[keep], np.zeros(int(keep.sum()), dtype=np.int64)


def _coco(boxes: np.ndarray) -> list[dict]:
    return [
        {"bbox": [float(b[0]), float(b[1]), float(b[2] - b[0]), float(b[3] - b[1])],
         "category_id": 0, "area": float((b[2] - b[0]) * (b[3] - b[1])), "iscrowd": 0}
        for b in boxes
    ]


class TileDataset(Dataset):
    """Training tiles -> (pixel_values, labels) in the format DFineForObjectDetection expects."""

    def __init__(
        self,
        samples: Sequence[DetectionSample],
        tiles: Sequence[TrainTile],
        processor,
        *,
        augment: bool,
        seed: int = 0,
        cache: ImageCache | None = None,
    ) -> None:
        self.samples, self.tiles, self.processor = samples, tiles, processor
        self.augment = augment
        self.rng = np.random.default_rng(seed)
        self.cache = cache or ImageCache()

    def __len__(self) -> int:
        return len(self.tiles)

    def __getitem__(self, i: int):
        t = self.tiles[i]
        img = self.cache.get(self.samples[t.sample_index])
        crop = img[t.tile.y0 : t.tile.y1, t.tile.x0 : t.tile.x1].astype(np.float32)
        boxes = t.boxes.copy()
        h, w = crop.shape
        if self.augment:
            if self.rng.random() < 0.5:  # port/starboard mirror
                crop = crop[:, ::-1]
                boxes[:, [0, 2]] = w - boxes[:, [2, 0]]
            if self.rng.random() < 0.5:  # along-track reversal
                crop = crop[::-1, :]
                boxes[:, [1, 3]] = h - boxes[:, [3, 1]]
            crop = crop * self.rng.uniform(0.8, 1.2) + self.rng.uniform(-15, 15)  # gain change
        crop = np.clip(crop, 0, 255).astype(np.uint8)
        enc = self.processor(
            images=[_rgb(np.ascontiguousarray(crop))],
            annotations=[{"image_id": i, "annotations": _coco(boxes)}],
            return_tensors="pt",
        )
        return enc["pixel_values"][0], enc["labels"][0]


def collate(batch):
    pixels = torch.stack([b[0] for b in batch])
    return pixels, [b[1] for b in batch]


def load_model(checkpoint: str = PRODUCT_CHECKPOINT, *, num_labels: int = 1):
    from transformers import AutoImageProcessor, DFineForObjectDetection

    processor = AutoImageProcessor.from_pretrained(checkpoint)
    model = DFineForObjectDetection.from_pretrained(
        checkpoint,
        num_labels=num_labels,
        id2label={i: f"class_{i}" if num_labels > 1 else "object" for i in range(num_labels)},
        label2id={("object" if num_labels == 1 else f"class_{i}"): i for i in range(num_labels)},
        ignore_mismatched_sizes=True,
    )
    return model, processor


@torch.no_grad()
def predict_image(
    model,
    processor,
    image: np.ndarray,
    *,
    tile_px: int,
    overlap: float = 0.25,
    full_image: bool = True,
    threshold: float = 0.01,
    batch_size: int = 8,
    max_detections: int = 100,
    device: str = "cuda",
) -> tuple[np.ndarray, np.ndarray]:
    """SAHI-style inference: overlapping tiles plus one whole-image pass, merged with NMS."""
    model.eval()
    h, w = image.shape[:2]
    tiles = make_tiles(w, h, tile_w=tile_px, tile_h=tile_px, overlap=overlap)
    crops = [(t, image[t.y0 : t.y1, t.x0 : t.x1]) for t in tiles]
    per_tile = []
    for start in range(0, len(crops), batch_size):
        chunk = crops[start : start + batch_size]
        enc = processor(images=[_rgb(c) for _, c in chunk], return_tensors="pt")
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device == "cuda"):
            out = model(pixel_values=enc["pixel_values"].to(device))
        results = processor.post_process_object_detection(
            out, threshold=threshold, target_sizes=[c.shape[:2] for _, c in chunk]
        )
        for (t, c), r in zip(chunk, results, strict=True):
            per_tile.append((t, *_clip(r, c.shape[0], c.shape[1])))
    full = None
    if full_image and len(tiles) > 1:
        enc = processor(images=[_rgb(image)], return_tensors="pt")
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device == "cuda"):
            out = model(pixel_values=enc["pixel_values"].to(device))
        (r,) = processor.post_process_object_detection(out, threshold=threshold,
                                                       target_sizes=[(h, w)])
        full = _clip(r, h, w)
    boxes, scores, _ = merge_detections(per_tile, iou_threshold=0.5, class_agnostic=True,
                                        full_image=full)
    return boxes[:max_detections], np.clip(scores[:max_detections], 0.0, 1.0)


def make_optimizer(model, lr: float, *, backbone_lr_factor: float = 0.1,
                   weight_decay: float = 1e-4):
    backbone = [p for n, p in model.named_parameters() if "backbone" in n and p.requires_grad]
    rest = [p for n, p in model.named_parameters() if "backbone" not in n and p.requires_grad]
    return torch.optim.AdamW(
        [{"params": backbone, "lr": lr * backbone_lr_factor}, {"params": rest, "lr": lr}],
        weight_decay=weight_decay,
    )


def warmup_cosine(step: int, total: int, warmup: int) -> float:
    if step < warmup:
        return (step + 1) / warmup
    progress = (step - warmup) / max(1, total - warmup)
    return 0.5 * (1 + math.cos(math.pi * min(1.0, progress)))
