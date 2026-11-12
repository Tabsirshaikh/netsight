"""Object classifier for detector boxes (stage 2: the detector finds, this names).

Classes follow plan section 8.4 where public data exists. Most classes come from a single
dataset, so a classifier can score highly by recognising the SONAR instead of the OBJECT. The
honest test is therefore cross-dataset: whole sources are held out and their objects must still
get the right class (e.g. wrecks from AI4Shipwrecks with no AI4Shipwrecks crops in training).

    python -m netsight.classify.crops --out runs/classifier_v0
"""

from __future__ import annotations

import argparse
import io
import json
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np

TAXONOMY = {
    ("ghostvision_crabpot", "Crab-Pot"): "trap_pot",
    ("mine_detection_sss", "MILCO"): "mine_like",
    ("mine_detection_sss", "NOMBO"): "other_object",
    ("aquascan_1k", "Human"): "person",
    ("sctd", "human"): "person",
    ("sctd", "ship"): "wreck",
    ("ai4shipwrecks", "shipwreck"): "wreck",
    ("aperturelab_sss", "wreck"): "wreck",
    ("sctd", "aircraft"): "aircraft",
    ("subpipe_mini2", "Pipeline"): "pipe",
    ("aperturelab_sss", "pipe"): "pipe",
    ("aperturelab_sss", "natural"): "rock",
    ("boulders", "Boulder"): "rock",
    ("aperturelab_sss", "ghost_net"): "ghost_net",
    ("aperturelab_sss", "rope_line"): "rope_line",
    ("aperturelab_sss", "container"): "container",
    ("aperturelab_sss", "tire"): "tire",
}
SIZE = 96
# Sources held out completely for the cross-dataset test: (dataset_id, label) -> expected class.
HELD_OUT = {
    ("ai4shipwrecks", "shipwreck"),
    ("sctd", "human"),
    ("boulders", "Boulder"),
    ("subpipe_mini2", "Pipeline"),
}


def crop(image: np.ndarray, box, pad: float = 0.25) -> np.ndarray:
    """Square crop around a box with padding, resized to SIZE x SIZE (uint8)."""
    from PIL import Image

    h, w = image.shape[:2]
    x0, y0, x1, y1 = (float(v) for v in box)
    side = max(x1 - x0, y1 - y0) * (1 + 2 * pad) + 4
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    a0, b0 = int(max(cx - side / 2, 0)), int(max(cy - side / 2, 0))
    a1, b1 = int(min(cx + side / 2, w)), int(min(cy + side / 2, h))
    patch = image[b0:b1, a0:a1]
    if patch.size == 0:
        patch = np.zeros((2, 2), np.uint8)
    return np.asarray(Image.fromarray(patch).resize((SIZE, SIZE), Image.BILINEAR), np.uint8)


def background_crops(image: np.ndarray, boxes: np.ndarray, rng, n: int) -> list[np.ndarray]:
    """Random seabed crops that overlap no labelled box."""
    h, w = image.shape[:2]
    out = []
    for _ in range(n * 10):
        if len(out) >= n:
            break
        s = int(rng.integers(24, max(25, min(h, w) // 3)))
        if s >= min(h, w):
            break
        x, y = int(rng.integers(0, w - s)), int(rng.integers(0, h - s))
        b = np.asarray(boxes, float).reshape(-1, 4)
        if len(b) and np.any((b[:, 0] < x + s) & (b[:, 2] > x) & (b[:, 1] < y + s) & (b[:, 3] > y)):
            continue
        patch = image[y : y + s, x : x + s]
        if patch.mean() < 8:  # blank borders / water column
            continue
        out.append(crop(image, (x, y, x + s, y + s), pad=0))
    return out


def collect(root: Path, rng, per_class_cap: int = 1500):
    """(crops, class names, source keys, split) for every labelled object plus background."""
    from netsight.detect.pilot import build_splits
    from netsight.detect.pixel_cache import PixelCache

    sp = build_splits(root)
    px = PixelCache(root / "cache" / "pixels")
    items = [(s, "train") for s in sp["train"]]
    items += [(s, "val") for v in sp["val"].values() for s in v]
    items += [(s, "test") for k, v in sp["test"].items() if k != "ghostvision_shift" for s in v]
    rng.shuffle(items)
    X, y, src, split = [], [], [], []
    count: Counter = Counter()
    bg_count: Counter = Counter()
    for s, part in items:
        labels = list(s.labels)
        boxes = np.asarray(s.boxes, float).reshape(-1, 4)
        keys = [(s.dataset_id, lab) for lab in labels]
        wanted = [i for i, k in enumerate(keys) if k in TAXONOMY and count[k] < per_class_cap]
        need_bg = bg_count[s.dataset_id] < 400
        if not wanted and not need_bg:
            continue
        img = np.asarray(px.get(s), np.uint8)
        for i in wanted:
            X.append(crop(img, boxes[i]))
            y.append(TAXONOMY[keys[i]])
            src.append(f"{keys[i][0]}:{keys[i][1]}")
            split.append(part)
            count[keys[i]] += 1
        if need_bg:
            for c in background_crops(img, boxes, rng, 2):
                X.append(c)
                y.append("background")
                src.append(f"{s.dataset_id}:background")
                split.append(part)
                bg_count[s.dataset_id] += 1
    bz = root / "raw" / "boulders" / "sss_dataset.zip"
    if bz.exists():
        from PIL import Image

        with zipfile.ZipFile(bz) as z:
            for part, folder in (("train", "train"), ("val", "valid"), ("test", "test")):
                d = json.loads(z.read(f"sss_dataset/{folder}/annotations.json"))
                files = {im["id"]: im["file_name"] for im in d["images"]}
                for a in d["annotations"]:
                    if a["category_id"] != 1 or count[("boulders", "Boulder")] >= per_class_cap:
                        continue
                    img = np.asarray(
                        Image.open(
                            io.BytesIO(
                                z.read(f"sss_dataset/{folder}/images/{files[a['image_id']]}")
                            )
                        ).convert("L")
                    )
                    x, yy, w, h = a["bbox"]
                    X.append(crop(img, (x, yy, x + w, yy + h)))
                    y.append("rock")
                    src.append("boulders:Boulder")
                    split.append(part)
                    count[("boulders", "Boulder")] += 1
    return np.stack(X), np.array(y), np.array(src), np.array(split)


def train_eval(X, y, src, split, classes, train_mask, test_mask, epochs: int = 8, seed: int = 0):
    import torch
    import torchvision

    torch.manual_seed(seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    idx = {c: i for i, c in enumerate(classes)}
    model = torchvision.models.resnet18(weights="IMAGENET1K_V1")
    model.fc = torch.nn.Linear(model.fc.in_features, len(classes))
    model.to(device)
    xt = torch.from_numpy(X).float().div(255).unsqueeze(1).repeat(1, 3, 1, 1)
    xt = (xt - 0.45) / 0.25
    yt = torch.tensor([idx[c] for c in y])
    tr = np.flatnonzero(train_mask)
    counts = np.bincount(yt[tr].numpy(), minlength=len(classes))
    weights = 1.0 / np.maximum(counts[yt[tr].numpy()], 1)
    sampler = torch.utils.data.WeightedRandomSampler(weights, num_samples=len(tr), replacement=True)
    loader = torch.utils.data.DataLoader(list(tr), batch_size=128, sampler=sampler)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-4)
    for _ in range(epochs):
        model.train()
        for b in loader:
            xb = xt[b].to(device)
            if torch.rand(1).item() < 0.5:
                xb = xb.flip(3)
            loss = torch.nn.functional.cross_entropy(model(xb), yt[b].to(device))
            opt.zero_grad()
            loss.backward()
            opt.step()
    model.eval()
    te = np.flatnonzero(test_mask)
    preds = []
    with torch.no_grad():
        for i in range(0, len(te), 256):
            preds.append(model(xt[te[i : i + 256]].to(device)).argmax(1).cpu().numpy())
    pred = np.array([classes[k] for k in np.concatenate(preds)]) if len(te) else np.array([])
    return model, te, pred


def report(y, src, te, pred) -> dict:
    out = {}
    for key in sorted(set(src[te])):
        m = src[te] == key
        truth = y[te][m][0]
        c = Counter(pred[m])
        out[key] = {
            "class": truth,
            "n": int(m.sum()),
            "correct": round(c[truth] / m.sum(), 3),
            "predicted": dict(c.most_common(4)),
        }
    return out


def main(argv: list[str] | None = None) -> int:
    from netsight.config import data_dir

    p = argparse.ArgumentParser()
    p.add_argument("--out", default="runs/classifier_v0")
    p.add_argument("--epochs", type=int, default=8)
    a = p.parse_args(argv)
    root = data_dir()
    out = root / a.out
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(0)
    X, y, src, split = collect(root, rng)
    classes = sorted(set(y))
    print("crops", Counter(y).most_common(), flush=True)
    held = np.array([s in {f"{d}:{lab}" for d, lab in HELD_OUT} for s in src])
    res = {"classes": classes, "n_crops": dict(Counter(y))}
    # A: same-source test (train splits -> test splits): optimistic, sensor can give the class.
    _, te, pred = train_eval(X, y, src, split, classes, split == "train", split == "test", a.epochs)
    res["same_source_test"] = report(y, src, te, pred)
    # B: cross-dataset - held-out sources never seen in training.
    model, te, pred = train_eval(
        X, y, src, split, classes, (split != "test") & ~held, held, a.epochs
    )
    res["cross_dataset_held_out"] = report(y, src, te, pred)
    (out / "results.json").write_text(json.dumps(res, indent=2), "utf-8")
    for k in ("same_source_test", "cross_dataset_held_out"):
        print("==", k)
        for key, v in res[k].items():
            print(
                f"  {key:32s} {v['class']:12s} n={v['n']:4d} correct={v['correct']:.2f} "
                f"{v['predicted']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
