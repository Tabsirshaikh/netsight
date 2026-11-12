"""Dataset quality audit: near-duplicate images across splits, and label sanity.

Near duplicates use a 64-bit difference hash (dHash) of each image resized to 9x8 grey; two images
with Hamming distance <= 4 are treated as the same picture (also catches re-encoded or slightly
shifted copies). Leakage = a test or validation image whose near duplicate is in training.

    python -m netsight.datasets.quality_check --out runs/quality_v0.4.json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter

import numpy as np


def dhash(image: np.ndarray) -> int:
    from PIL import Image

    small = np.asarray(
        Image.fromarray(np.asarray(image, np.uint8)).resize((9, 8), Image.BILINEAR), dtype=np.int16
    )
    bits = (small[:, 1:] > small[:, :-1]).ravel()
    return int(sum(1 << i for i, b in enumerate(bits) if b))


def thumb(image: np.ndarray, size: int = 48) -> np.ndarray:
    """Zero-mean, unit-norm thumbnail for content comparison."""
    from PIL import Image

    t = np.asarray(
        Image.fromarray(np.asarray(image, np.uint8)).resize((size, size), Image.BILINEAR),
        dtype=np.float64,
    ).ravel()
    t -= t.mean()
    n = np.linalg.norm(t)
    return t / n if n > 0 else t


def confirmed(pairs, q_thumbs, r_thumbs, min_corr: float = 0.97) -> int:
    """Count hash candidates whose thumbnails also correlate >= min_corr (same picture)."""
    return sum(float(q_thumbs[i] @ r_thumbs[j]) >= min_corr for i, j, _ in pairs)


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def near_pairs(query: list[int], ref: list[int], max_dist: int = 4) -> list[tuple[int, int, int]]:
    """(query index, ref index, distance) for the closest ref within max_dist."""
    if not ref:
        return []
    r = np.array(ref, dtype=np.uint64)
    out = []
    for i, q in enumerate(query):
        x = np.bitwise_xor(r, np.uint64(q))
        d = np.array([int(v).bit_count() for v in x])
        j = int(d.argmin())
        if d[j] <= max_dist:
            out.append((i, j, int(d[j])))
    return out


def label_sanity(samples) -> dict:
    c: Counter = Counter()
    for s in samples:
        b = np.asarray(s.boxes, float).reshape(-1, 4)
        c["images"] += 1
        c["boxes"] += len(b)
        c["empty_images"] += int(len(b) == 0)
        if len(b):
            w, h = b[:, 2] - b[:, 0], b[:, 3] - b[:, 1]
            c["degenerate_boxes(<2px)"] += int(((w < 2) | (h < 2)).sum())
            c["negative_coords"] += int((b < 0).any(axis=1).sum())
            ious = []
            for i in range(len(b)):
                for j in range(i + 1, len(b)):
                    ix = max(0, min(b[i, 2], b[j, 2]) - max(b[i, 0], b[j, 0]))
                    iy = max(0, min(b[i, 3], b[j, 3]) - max(b[i, 1], b[j, 1]))
                    inter = ix * iy
                    u = w[i] * h[i] + w[j] * h[j] - inter
                    ious.append(inter / u if u > 0 else 0)
            c["duplicate_boxes(IoU>0.9)"] += int(sum(v > 0.9 for v in ious))
    return dict(c)


def main(argv: list[str] | None = None) -> int:
    from netsight.config import data_dir
    from netsight.detect.pilot import build_splits
    from netsight.detect.pixel_cache import PixelCache

    p = argparse.ArgumentParser()
    p.add_argument("--out", default="runs/quality_v0.4.json")
    a = p.parse_args(argv)
    root = data_dir()
    splits = build_splits(root)
    pixels = PixelCache(root / "cache" / "pixels")
    hashes: dict[tuple[str, str], list[int]] = {}
    report: dict = {}
    thumbs: dict[tuple[str, str], list] = {}
    train_by_id: dict[str, list] = {}
    for s in splits["train"]:
        train_by_id.setdefault(s.dataset_id, []).append(s)
    id_of: dict[str, str] = {}
    for split in ("val", "test"):
        for name, samples in splits[split].items():
            if samples:
                id_of[name] = samples[0].dataset_id
            imgs = [pixels.get(s) for s in samples]
            hashes[(split, name)] = [dhash(x) for x in imgs]
            thumbs[(split, name)] = [thumb(x) for x in imgs]
            report.setdefault(name, {})[f"{split}_labels"] = label_sanity(samples)
    train_hash, train_thumb = {}, {}
    for i, v in train_by_id.items():
        imgs = [pixels.get(s) for s in v]
        train_hash[i] = [dhash(x) for x in imgs]
        train_thumb[i] = [thumb(x) for x in imgs]
    for name in report:
        tr = train_hash.get(id_of.get(name, ""), [])
        report[name]["train_images"] = len(tr)
        report[name]["train_labels"] = label_sanity(train_by_id.get(id_of.get(name, ""), []))
        dup_train = len(tr) - len(set(tr))
        report[name]["train_exact_hash_duplicates"] = dup_train
        for split in ("val", "test"):
            q = hashes.get((split, name), [])
            pairs = near_pairs(q, tr)
            report[name][f"{split}_images"] = len(q)
            report[name][f"{split}_hash_candidates_vs_train"] = len(pairs)
            report[name][f"{split}_confirmed_duplicates_of_train"] = confirmed(
                pairs, thumbs.get((split, name), []), train_thumb.get(id_of.get(name, ""), [])
            )
            if split == "test":
                v = hashes.get(("val", name), [])
                vp = near_pairs(q, v)
                report[name]["test_confirmed_duplicates_of_val"] = confirmed(
                    vp, thumbs[(split, name)], thumbs.get(("val", name), [])
                )
    (root / a.out).write_text(json.dumps(report, indent=2), "utf-8")
    for name, r in report.items():
        print(name, json.dumps({k: v for k, v in r.items() if "labels" not in k}))
        for k, v in r.items():
            if "labels" in k:
                print("   ", k, v)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
