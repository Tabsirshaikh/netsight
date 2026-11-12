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
from netsight.detect.tiling import full_image_pass_allowed, make_tiles, merge_detections
from netsight.detect.training_tiles import TrainTile

PRODUCT_CHECKPOINT = "ustc-community/dfine-small-coco"
NET_INPUT = 640


class ImageCache:
    """Decoded greyscale images, read from zip members (zip handles kept open)."""

    def __init__(self, max_images: int = 512) -> None:
        self._zips: dict[str, zipfile.ZipFile] = {}
        self._images: OrderedDict[tuple[str, str], np.ndarray] = OrderedDict()
        self.max_images = max_images

    def __getstate__(self):  # DataLoader workers get an empty cache of their own
        return {"max_images": self.max_images}

    def __setstate__(self, state):
        self.__init__(state["max_images"])

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


def to_pixels(crops: Sequence[np.ndarray], size: int = NET_INPUT) -> torch.Tensor:
    """Greyscale uint8 crops -> (n, 3, size, size) floats in [0, 1].

    Same scaling as D-FINE's RTDetrImageProcessor (resize to 640x640, rescale 1/255, no mean/std
    normalisation) but done with one tensor resize instead of the processor's per-image path.
    """
    out = []
    for c in crops:
        a = np.ascontiguousarray(c)
        if not a.flags.writeable:  # memory-mapped cache pages are read-only
            a = a.copy()
        t = torch.from_numpy(a).float().div_(255.0)[None, None]
        t = torch.nn.functional.interpolate(
            t, size=(size, size), mode="bilinear", align_corners=False, antialias=True
        )
        out.append(t[0].expand(3, -1, -1))
    return torch.stack(out)


def _targets(boxes: np.ndarray, h: int, w: int, label: int = 0) -> dict:
    """Tile-pixel boxes -> D-FINE training targets (normalised centre x, y, width, height)."""
    b = np.asarray(boxes, dtype=np.float32).reshape(-1, 4)
    cxcywh = np.column_stack(
        [
            (b[:, 0] + b[:, 2]) / 2 / w,
            (b[:, 1] + b[:, 3]) / 2 / h,
            (b[:, 2] - b[:, 0]) / w,
            (b[:, 3] - b[:, 1]) / h,
        ]
    )
    return {
        "class_labels": torch.full((len(b),), label, dtype=torch.long),
        "boxes": torch.from_numpy(cxcywh.astype(np.float32)).reshape(-1, 4),
    }


def sonar_augment(
    crop: np.ndarray, boxes: np.ndarray, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray]:
    """Physically motivated side-scan augmentation (each part with its own probability).

    - multiplicative speckle (gamma, 3-10 looks): different sonars and settings;
    - along-track blur (rows, sigma 0.5-1.5 px): beam width / ping-rate differences;
    - along-track stretch (rows x 0.8-1.25, size kept): vessel speed / ping-rate differences,
      the pixel-aspect shift measured on the Contact recording. Objects that would be cut to
      less than half their area leave the tile unchanged.
    """
    from scipy.ndimage import gaussian_filter1d, zoom

    out = crop.astype(np.float32)
    if rng.random() < 0.5:
        looks = rng.uniform(3, 10)
        out = out * rng.gamma(looks, 1 / looks, size=out.shape).astype(np.float32)
    if rng.random() < 0.3:
        out = gaussian_filter1d(out, sigma=rng.uniform(0.5, 1.5), axis=0)
    if rng.random() < 0.3:
        h, w = out.shape
        f = float(np.exp(rng.uniform(np.log(0.8), np.log(1.25))))
        z = zoom(out, (f, 1.0), order=1)
        zb = boxes.astype(np.float64) * [1, f, 1, f]
        zh = z.shape[0]
        if f < 1:
            pad = np.full((h, w), float(np.median(out)), dtype=np.float32)
            oy = int(rng.integers(0, h - zh + 1))
            pad[oy : oy + zh] = z
            return pad, zb + [0, oy, 0, oy]
        oy = int(rng.integers(0, zh - h + 1))
        moved = zb - [0, oy, 0, oy]
        clipped = np.clip(moved, 0, [w, h, w, h])
        area = np.prod(np.maximum(moved[:, 2:] - moved[:, :2], 0), axis=1)
        kept = np.prod(np.maximum(clipped[:, 2:] - clipped[:, :2], 0), axis=1)
        vis = np.divide(kept, area, out=np.zeros_like(kept), where=area > 0)
        if np.any((vis > 0) & (vis < 0.5)):
            return out, boxes
        return z[oy : oy + h], clipped[vis >= 0.5]
    return out, boxes


def rescale(
    crop: np.ndarray,
    boxes: np.ndarray,
    factor: float,
    rng: np.random.Generator,
    *,
    min_visible: float = 0.5,
) -> tuple[np.ndarray, np.ndarray]:
    """Zoom a tile by `factor`, keeping its size, so objects appear smaller or larger.

    Zoom-out pads with the tile's median (no mirrored, unlabelled copies of objects); zoom-in
    takes a random window. If the window would cut an object to less than `min_visible` of its
    area the tile is returned unchanged: a half-visible object labelled as background would
    teach the wrong thing.
    """
    from scipy.ndimage import zoom

    h, w = crop.shape
    z = zoom(crop, factor, order=1)
    zb = boxes.astype(np.float64) * factor
    zh, zw = z.shape
    if factor < 1:
        out = np.full((h, w), float(np.median(crop)), dtype=crop.dtype)
        oy, ox = int(rng.integers(0, h - zh + 1)), int(rng.integers(0, w - zw + 1))
        out[oy : oy + zh, ox : ox + zw] = z
        return out, zb + [ox, oy, ox, oy]
    oy, ox = int(rng.integers(0, zh - h + 1)), int(rng.integers(0, zw - w + 1))
    moved = zb - [ox, oy, ox, oy]
    clipped = np.clip(moved, 0, [w, h, w, h])
    area = np.prod(np.maximum(moved[:, 2:] - moved[:, :2], 0), axis=1)
    kept = np.prod(np.maximum(clipped[:, 2:] - clipped[:, :2], 0), axis=1)
    visible = np.divide(kept, area, out=np.zeros_like(kept), where=area > 0)
    if np.any((visible > 0) & (visible < min_visible)):
        return crop, boxes
    return z[oy : oy + h, ox : ox + w], clipped[visible >= min_visible]


class TileDataset(Dataset):
    """Training tiles -> (pixel_values, labels) in the format DFineForObjectDetection expects.

    Augmentation randomness is seeded per (seed, item), so DataLoader workers never repeat each
    other and a re-run reproduces the same augmentations.
    """

    def __init__(
        self,
        samples: Sequence[DetectionSample],
        tiles: Sequence[TrainTile],
        *,
        augment: bool,
        seed: int = 0,
        cache: ImageCache | None = None,
        scale_range: tuple[float, float] | None = None,
        label_of: dict[str, int] | None = None,
        sonar_aug: bool = False,
    ) -> None:
        self.samples, self.tiles = samples, tiles
        self.label_of = label_of  # dataset_id -> class index (class per dataset)
        self.sonar_aug = sonar_aug
        self.augment, self.seed = augment, seed
        self.scale_range = scale_range  # e.g. (0.5, 1.5): random zoom, half of the items
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
            rng = np.random.default_rng([self.seed, i])
            if rng.random() < 0.5:  # port/starboard mirror
                crop = crop[:, ::-1]
                boxes[:, [0, 2]] = w - boxes[:, [2, 0]]
            if rng.random() < 0.5:  # along-track reversal
                crop = crop[::-1, :]
                boxes[:, [1, 3]] = h - boxes[:, [3, 1]]
            if self.scale_range is not None and rng.random() < 0.5:  # target-size change
                lo, hi = self.scale_range
                crop, boxes = rescale(
                    crop, boxes, float(np.exp(rng.uniform(np.log(lo), np.log(hi)))), rng
                )
            if self.sonar_aug:
                crop, boxes = sonar_augment(crop, boxes, rng)
            crop = crop * rng.uniform(0.8, 1.2) + rng.uniform(-15, 15)  # gain change
        crop = np.clip(crop, 0, 255).astype(np.uint8)
        label = 0
        if self.label_of is not None:
            label = self.label_of[self.samples[t.sample_index].dataset_id]
        return to_pixels([crop])[0], _targets(boxes, h, w, label)


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
    batch_size: int = 16,
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
        pixels = to_pixels([c for _, c in chunk]).to(device, non_blocking=True)
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device == "cuda"):
            out = model(pixel_values=pixels)
        results = processor.post_process_object_detection(
            out, threshold=threshold, target_sizes=[c.shape[:2] for _, c in chunk]
        )
        for (t, c), r in zip(chunk, results, strict=True):
            per_tile.append((t, *_clip(r, c.shape[0], c.shape[1])))
    full = None
    if full_image and full_image_pass_allowed(w, h, n_tiles=len(tiles)):
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device == "cuda"):
            out = model(pixel_values=to_pixels([image]).to(device))
        (r,) = processor.post_process_object_detection(
            out, threshold=threshold, target_sizes=[(h, w)]
        )
        full = _clip(r, h, w)
    boxes, scores, _ = merge_detections(
        per_tile, iou_threshold=0.5, class_agnostic=True, full_image=full
    )
    return boxes[:max_detections], np.clip(scores[:max_detections], 0.0, 1.0)


def make_optimizer(
    model, lr: float, *, backbone_lr_factor: float = 0.1, weight_decay: float = 1e-4
):
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
